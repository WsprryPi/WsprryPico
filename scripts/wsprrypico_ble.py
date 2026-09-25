#!/usr/bin/env python3
"""Authenticated WsprryPico BLE local control for BlueZ/Linux.

The protocol implementation is dependency-free.  The production adapter imports
dbus-python and PyGObject lazily so deterministic host tests can run elsewhere.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import getpass
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import struct
import sys
import time
from typing import Any, Callable


UUIDS = {
    "service": "7d6b0001-5bf1-4f21-a486-3e8f70c12201",
    "identity": "7d6b0002-5bf1-4f21-a486-3e8f70c12201",
    "command": "7d6b0003-5bf1-4f21-a486-3e8f70c12201",
    "status": "7d6b0004-5bf1-4f21-a486-3e8f70c12201",
    "wtpCommand": "7d6b0005-5bf1-4f21-a486-3e8f70c12201",
    "wtpStatus": "7d6b0006-5bf1-4f21-a486-3e8f70c12201",
}
MAX_PROFILE_BYTES = 7168
FRAGMENT_BYTES = 64
GATT_FRAME_BYTES = 64
GATT_FRAME_HEADER_BYTES = 4
GATT_FRAME_PAYLOAD_BYTES = GATT_FRAME_BYTES - GATT_FRAME_HEADER_BYTES
GATT_FRAME_COUNT = 16
MAX_COMMAND_BYTES = 512
MAX_STATUS_BYTES = 256
WTP_HEADER_BYTES = 16
WTP_MAX_PAYLOAD_BYTES = 65536
WTP_SEGMENT_BYTES = 64
WTP_REASSEMBLY_BYTES = 131072
PROFILE_CONFIRMATION_TIMEOUT_SECONDS = 25.0
PROFILE_CONFIRMATION_POLL_SECONDS = 0.5

_DEVICE_ID = re.compile(r"^[0-9a-f]{32}$")
_ADDRESS = re.compile(r"^(?:[0-9A-F]{2}:){5}[0-9A-F]{2}$")
_OP = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_REMOTE_ERROR = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_DECIMAL = re.compile(r"^(?:0|[1-9][0-9]*)$")
_WTP_STATES = {"empty", "loaded", "armed", "running", "complete", "aborted", "missed", "failed"}


class ClientError(Exception):
    """A stable, non-secret operator-facing error."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def fail(code: str) -> None:
    raise ClientError(code)


def valid_device_id(value: Any) -> bool:
    return isinstance(value, str) and _DEVICE_ID.fullmatch(value) is not None


def normalize_address(value: str) -> str:
    address = value.upper()
    if _ADDRESS.fullmatch(address) is None:
        fail("bluetooth_address")
    return address


def pairing_request_allowed(
    device_path: str, expected_device_path: str, service_uuid: str | None = None
) -> bool:
    return device_path == expected_device_path and (
        service_uuid is None or service_uuid.lower() == UUIDS["service"]
    )


def remote_error(value: Any) -> str:
    return value if isinstance(value, str) and _REMOTE_ERROR.fullmatch(value) else "device_rejected"


def _printable(value: Any, minimum: int, maximum: int) -> bool:
    return (
        isinstance(value, str)
        and minimum <= len(value) <= maximum
        and all(32 <= ord(character) < 127 for character in value)
    )


def _canonical_hostname(value: Any) -> str:
    if not isinstance(value, str):
        fail("hostname")
    name = value[:-1] if value.endswith(".") else value
    name = name.lower()
    label = name[:-6] if name.endswith(".local") else ""
    if (
        not label
        or len(label) > 63
        or re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label) is None
    ):
        fail("hostname")
    return name


def _valid_time_server(value: Any) -> bool:
    if not _printable(value, 1, 253) or re.search(r"[:/\s]", value):
        return False
    parts = value.split(".")
    if len(parts) == 4 and all(re.fullmatch(r"(?:0|[1-9][0-9]{0,2})", part) for part in parts):
        octets = [int(part) for part in parts]
        return all(octet <= 255 for octet in octets) and 0 < octets[0] < 224 and octets[0] != 127
    numeric = all(
        bool((re.fullmatch(r"0[xX][0-9a-fA-F]+", part) or re.fullmatch(r"[0-9]+", part)))
        for part in parts
    )
    if numeric:
        return False
    name = value[:-1] if value.endswith(".") else value
    return bool(name) and all(
        1 <= len(label) <= 63
        and re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label)
        for label in name.split(".")
    )


def _pem(value: Any, begin: str, end: str, maximum: int) -> bool:
    if not isinstance(value, str) or len(value) > maximum or not value.startswith(begin):
        return False
    trimmed = value.rstrip("\r\n")
    return trimmed.endswith(end) and all(
        character in "\r\n" or 32 <= ord(character) < 127 for character in value
    )


def canonical_profile(value: Any) -> bytearray:
    if not isinstance(value, dict) or set(value) != {"version", "device_id", "wifi", "tls"}:
        fail("profile_format")
    if value.get("version") != 1 or not valid_device_id(value.get("device_id")):
        fail("device_id")
    wifi, tls = value.get("wifi"), value.get("tls")
    if not isinstance(wifi, dict) or set(wifi) != {"ssid", "password", "time_server"}:
        fail("wifi")
    if not isinstance(tls, dict) or set(tls) != {
        "hostname", "port", "server_certificate", "server_private_key", "client_ca"
    }:
        fail("tls")
    if not _printable(wifi.get("ssid"), 1, 32):
        fail("ssid")
    if not _printable(wifi.get("password"), 8, 63):
        fail("password")
    if not _valid_time_server(wifi.get("time_server")):
        fail("time_server")
    hostname = _canonical_hostname(tls.get("hostname"))
    port = tls.get("port")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        fail("port")
    if not _pem(
        tls.get("server_certificate"),
        "-----BEGIN CERTIFICATE-----",
        "-----END CERTIFICATE-----",
        3072,
    ):
        fail("server_certificate")
    key = tls.get("server_private_key")
    if not (
        _pem(key, "-----BEGIN PRIVATE KEY-----", "-----END PRIVATE KEY-----", 2048)
        or _pem(key, "-----BEGIN EC PRIVATE KEY-----", "-----END EC PRIVATE KEY-----", 2048)
    ):
        fail("server_private_key")
    if not _pem(
        tls.get("client_ca"),
        "-----BEGIN CERTIFICATE-----",
        "-----END CERTIFICATE-----",
        3072,
    ):
        fail("client_ca")
    canonical = {
        "version": 1,
        "device_id": value["device_id"],
        "wifi": {
            "ssid": wifi["ssid"],
            "password": wifi["password"],
            "time_server": wifi["time_server"],
        },
        "tls": {
            "hostname": hostname,
            "port": port,
            "server_certificate": tls["server_certificate"],
            "server_private_key": key,
            "client_ca": tls["client_ca"],
        },
    }
    encoded = bytearray(json.dumps(canonical, separators=(",", ":"), ensure_ascii=True).encode("ascii"))
    if len(encoded) > MAX_PROFILE_BYTES:
        encoded[:] = b"\x00" * len(encoded)
        fail("profile_oversize")
    return encoded


def load_profile_file(path_text: str) -> bytearray:
    path = Path(path_text)
    if not path.is_absolute():
        fail("profile_path_not_absolute")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        fail("profile_open")
    raw = bytearray()
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            fail("profile_not_regular")
        if metadata.st_uid != os.geteuid() or metadata.st_mode & 0o077:
            fail("profile_permissions")
        if metadata.st_size <= 0 or metadata.st_size > MAX_PROFILE_BYTES:
            fail("profile_size")
        while len(raw) <= MAX_PROFILE_BYTES:
            chunk = os.read(descriptor, min(4096, MAX_PROFILE_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        if not raw or len(raw) > MAX_PROFILE_BYTES:
            fail("profile_size")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            fail("profile_json")
        return canonical_profile(value)
    finally:
        raw[:] = b"\x00" * len(raw)
        os.close(descriptor)


def gatt_frames(payload: bytes | bytearray) -> list[bytearray]:
    if not payload or len(payload) > GATT_FRAME_PAYLOAD_BYTES * GATT_FRAME_COUNT:
        fail("frame_oversize")
    result: list[bytearray] = []
    offset = 0
    sequence = 0
    while offset < len(payload):
        count = min(GATT_FRAME_PAYLOAD_BYTES, len(payload) - offset)
        flags = (1 if offset == 0 else 0) | (2 if offset + count == len(payload) else 0)
        result.append(bytearray((1, flags, sequence, count)) + payload[offset : offset + count])
        offset += count
        sequence += 1
    return result


class FrameReceiver:
    def __init__(self, maximum: int):
        self.maximum = maximum
        self.reset()

    def reset(self) -> None:
        if hasattr(self, "message"):
            self.message[:] = b"\x00" * len(self.message)
        self.message = bytearray()
        self.next = 0
        self.active = False

    def receive(self, frame: bytes | bytearray) -> bytes | None:
        if (
            len(frame) < GATT_FRAME_HEADER_BYTES
            or len(frame) > GATT_FRAME_BYTES
            or frame[0] != 1
            or frame[1] & ~3
            or frame[3] != len(frame) - GATT_FRAME_HEADER_BYTES
        ):
            self.reset()
            fail("frame_invalid")
        first, last = bool(frame[1] & 1), bool(frame[1] & 2)
        if (
            (first and (self.active or frame[2] != 0))
            or (not first and not self.active)
            or frame[2] != self.next
            or frame[2] >= GATT_FRAME_COUNT
        ):
            self.reset()
            fail("frame_order")
        if first:
            self.reset()
            self.active = True
        payload = frame[GATT_FRAME_HEADER_BYTES:]
        if not payload or len(self.message) + len(payload) > self.maximum:
            self.reset()
            fail("frame_oversize")
        self.message.extend(payload)
        self.next += 1
        if not last:
            return None
        result = bytes(self.message)
        self.reset()
        return result


def crc32c(payload: bytes | bytearray) -> int:
    crc = 0xFFFFFFFF
    for byte in payload:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0x82F63B78 if crc & 1 else 0)
    return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


def wtp_frame(message: dict[str, Any]) -> bytearray:
    payload = bytearray(json.dumps(message, separators=(",", ":")).encode("utf-8"))
    if not payload or len(payload) > WTP_MAX_PAYLOAD_BYTES:
        payload[:] = b"\x00" * len(payload)
        fail("wtp_payload_oversize")
    result = bytearray(struct.pack(">8sII", b"WTPF\x01\x01\x00\x00", len(payload), crc32c(payload)))
    result.extend(payload)
    payload[:] = b"\x00" * len(payload)
    return result


class WtpReceiver:
    def __init__(self):
        self.buffer = bytearray()

    def reset(self) -> None:
        self.buffer[:] = b"\x00" * len(self.buffer)
        self.buffer.clear()

    def receive(self, value: bytes | bytearray) -> list[dict[str, Any]]:
        if not value or len(self.buffer) + len(value) > WTP_REASSEMBLY_BYTES:
            self.reset()
            fail("wtp_frame_oversize")
        self.buffer.extend(value)
        result: list[dict[str, Any]] = []
        while len(self.buffer) >= WTP_HEADER_BYTES:
            magic, length, expected = struct.unpack(">8sII", self.buffer[:WTP_HEADER_BYTES])
            if magic != b"WTPF\x01\x01\x00\x00" or length == 0 or length > WTP_MAX_PAYLOAD_BYTES:
                self.reset()
                fail("wtp_frame_invalid")
            total = WTP_HEADER_BYTES + length
            if len(self.buffer) < total:
                break
            payload = bytearray(self.buffer[WTP_HEADER_BYTES:total])
            retained = bytearray(self.buffer[total:])
            self.buffer[:] = b"\x00" * len(self.buffer)
            self.buffer = retained
            if crc32c(payload) != expected:
                payload[:] = b"\x00" * len(payload)
                self.reset()
                fail("wtp_crc")
            try:
                message = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                payload[:] = b"\x00" * len(payload)
                self.reset()
                fail("wtp_json")
            payload[:] = b"\x00" * len(payload)
            if not isinstance(message, dict):
                self.reset()
                fail("wtp_json")
            result.append(message)
        return result


class Client:
    """Transport-neutral synchronous BLE client."""

    def __init__(
        self,
        backend: Any,
        timeout: float = 30.0,
        confirmation_timeout: float = PROFILE_CONFIRMATION_TIMEOUT_SECONDS,
    ):
        if not math.isfinite(timeout) or timeout <= 0 or timeout > 120:
            fail("timeout")
        if (
            not math.isfinite(confirmation_timeout)
            or confirmation_timeout <= 0
            or confirmation_timeout > PROFILE_CONFIRMATION_TIMEOUT_SECONDS
        ):
            fail("confirmation_timeout")
        self.backend = backend
        self.timeout = timeout
        self.confirmation_timeout = confirmation_timeout
        self.expected_device_id = ""
        self.generation = 0
        self.authorized = False
        self.field_session = ""
        self.wtp_session = ""
        self.status_receiver = FrameReceiver(MAX_STATUS_BYTES)
        self.wtp_receiver = WtpReceiver()
        self._field_responses: dict[str, dict[str, Any]] = {}
        self._wtp_responses: dict[str, dict[str, Any]] = {}
        self._field_pending = ""
        self._wtp_pending = ""
        self._wtp_pending_op = ""
        self._fatal: ClientError | None = None

    def connect(
        self, address: str, expected_device_id: str, allow_pairing: bool = True
    ) -> dict[str, Any]:
        address = normalize_address(address)
        if not valid_device_id(expected_device_id):
            fail("device_id")
        self.backend.connect(address, UUIDS["service"], self.timeout, allow_pairing)
        try:
            identity_bytes = self.backend.read(UUIDS["identity"])
            try:
                identity = json.loads(bytes(identity_bytes).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                fail("identity_format")
            if (
                not isinstance(identity, dict)
                or set(identity) != {"device_id", "generation"}
                or identity.get("device_id") != expected_device_id
                or isinstance(identity.get("generation"), bool)
                or not isinstance(identity.get("generation"), int)
                or identity["generation"] < 0
            ):
                fail("wrong_device")
            self.backend.start_notify(UUIDS["status"], self._on_status)
            self.expected_device_id = expected_device_id
            self.generation = identity["generation"]
            return identity
        except Exception:
            self.close()
            raise

    def _on_status(self, value: bytes) -> None:
        try:
            complete = self.status_receiver.receive(value)
            if complete is None:
                return
            response = json.loads(complete.decode("utf-8"))
            request_id = response.get("request_id") if isinstance(response, dict) else None
            if not valid_device_id(request_id) or not isinstance(response.get("ok"), bool):
                fail("response_invalid")
            if request_id != self._field_pending:
                return
            if request_id in self._field_responses:
                fail("response_duplicate")
            self._field_responses[request_id] = response
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._fatal = ClientError("status_json")
        except ClientError as error:
            self._fatal = error

    def _on_wtp_status(self, value: bytes) -> None:
        try:
            for response in self.wtp_receiver.receive(value):
                if response.get("type") == "event":
                    continue
                request_id = response.get("request_id")
                if (
                    response.get("type") != "response"
                    or response.get("protocol") != "WTP/1"
                    or not valid_device_id(request_id)
                    or not isinstance(response.get("op"), str)
                    or not isinstance(response.get("ok"), bool)
                ):
                    fail("wtp_response_invalid")
                if request_id != self._wtp_pending:
                    continue
                if (
                    response.get("session_id") != self.wtp_session
                    or response.get("op") != self._wtp_pending_op
                ):
                    fail("wtp_response_mismatch")
                if request_id in self._wtp_responses:
                    fail("wtp_response_duplicate")
                self._wtp_responses[request_id] = response
        except ClientError as error:
            self._fatal = error

    def _wait(
        self,
        responses: dict[str, dict[str, Any]],
        request_id: str,
        code: str,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
        while time.monotonic() < deadline:
            if self._fatal:
                error, self._fatal = self._fatal, None
                raise error
            if request_id in responses:
                return responses.pop(request_id)
            self.backend.pump(min(0.05, max(0.0, deadline - time.monotonic())))
        fail(code)

    def exchange(
        self,
        message: dict[str, Any],
        without_response: bool = False,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        request_id = message.get("request_id")
        if not valid_device_id(request_id):
            fail("request_id")
        if self._field_pending:
            fail("busy")
        encoded = bytearray(json.dumps(message, separators=(",", ":")).encode("utf-8"))
        frames: list[bytearray] = []
        self._field_pending = request_id
        try:
            if len(encoded) > MAX_COMMAND_BYTES:
                fail("command_oversize")
            frames = gatt_frames(encoded)
            for frame in frames:
                self.backend.write(UUIDS["command"], frame, response=not without_response)
            response = self._wait(self._field_responses, request_id, "timeout", timeout)
            if response["ok"]:
                return response
            fail(remote_error(response.get("error")))
        finally:
            self._field_responses.pop(request_id, None)
            self._field_pending = ""
            encoded[:] = b"\x00" * len(encoded)
            for frame in frames:
                frame[:] = b"\x00" * len(frame)

    def authorize(self, password: str) -> None:
        if not _printable(password, 8, 63):
            fail("local_password")
        session = secrets.token_hex(16)
        try:
            self.exchange({
                "version": 1,
                "operation": "authorize",
                "request_id": secrets.token_hex(16),
                "session_id": session,
                "device_id": self.expected_device_id,
                "password": password,
            })
            self.authorized = True
            self.field_session = session
        finally:
            password = ""

    def _field(
        self,
        operation: str,
        *,
        without_response: bool = False,
        timeout: float | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        if not self.authorized:
            fail("authentication_required")
        message = {
            "version": 1,
            "operation": operation,
            "request_id": secrets.token_hex(16),
            "session_id": self.field_session,
            "device_id": self.expected_device_id,
        }
        message.update(fields)
        return self.exchange(message, without_response, timeout)

    def identify(self) -> None:
        if self._field("identify").get("identified") is not True:
            fail("identify_response")

    def field_status(self) -> dict[str, Any]:
        response = self._field("field_status")
        if (
            response.get("time_source") not in {"none", "sntp", "controller", "disagreement"}
            or not isinstance(response.get("time_age_ns"), str)
            or _DECIMAL.fullmatch(response["time_age_ns"]) is None
            or not isinstance(response.get("time_uncertainty_ns"), str)
            or _DECIMAL.fullmatch(response["time_uncertainty_ns"]) is None
            or not isinstance(response.get("time_disagreement"), bool)
            or response.get("indicator") not in {"off", "softap_ready", "identify"}
            or not isinstance(response.get("indicator_fault"), bool)
        ):
            fail("field_status_response")
        return {key: value for key, value in response.items() if key not in {"version", "request_id", "ok"}}

    def synchronize_time(self, milliseconds: int | None = None) -> None:
        nonce = secrets.token_hex(16)
        challenge = self._field("time_challenge", nonce=nonce)
        if challenge.get("nonce") != nonce:
            fail("time_challenge_binding")
        sampled = int(time.time_ns() // 1_000_000) if milliseconds is None else milliseconds
        if isinstance(sampled, bool) or not isinstance(sampled, int) or sampled < 0:
            fail("controller_time")
        response = self._field(
            "time_submit",
            without_response=True,
            nonce=nonce,
            utc_ns=str(sampled * 1_000_000),
        )
        if response.get("accepted") is not True:
            fail("controller_time_response")

    def wtp_exchange(self, operation: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self.authorized or not self.wtp_session:
            fail("wtp_unavailable")
        if _OP.fullmatch(operation) is None or not isinstance(body, dict):
            fail("wtp_request")
        if self._wtp_pending:
            fail("wtp_busy")
        request_id = secrets.token_hex(16)
        frame = wtp_frame({
            "type": "request",
            "protocol": "WTP/1",
            "session_id": self.wtp_session,
            "request_id": request_id,
            "op": operation,
            "body": body,
        })
        self._wtp_pending = request_id
        self._wtp_pending_op = operation
        try:
            for offset in range(0, len(frame), WTP_SEGMENT_BYTES):
                self.backend.write(
                    UUIDS["wtpCommand"], frame[offset : offset + WTP_SEGMENT_BYTES]
                )
            response = self._wait(self._wtp_responses, request_id, "wtp_timeout")
            if response.get("op") != operation:
                fail("wtp_response_mismatch")
            if response["ok"] and isinstance(response.get("body"), dict):
                return response["body"]
            error = response.get("error")
            code = error.get("code") if isinstance(error, dict) else None
            fail(remote_error(code))
        finally:
            self._wtp_responses.pop(request_id, None)
            self._wtp_pending = ""
            self._wtp_pending_op = ""
            frame[:] = b"\x00" * len(frame)

    def enable_local_control(self) -> dict[str, Any]:
        if not self.authorized:
            fail("authentication_required")
        try:
            self.backend.start_notify(UUIDS["wtpStatus"], self._on_wtp_status)
            self.wtp_session = secrets.token_hex(16)
            hello = self.wtp_exchange(
                "HELLO", {"versions": ["WTP/1"], "client_name": "WsprryPico BlueZ", "client_version": "1"}
            )
            if (
                hello.get("selected_version") != "WTP/1"
                or hello.get("device_id") != self.expected_device_id
                or not valid_device_id(hello.get("boot_id"))
                or not _printable(hello.get("product"), 1, 64)
                or not _printable(hello.get("firmware_version"), 1, 64)
            ):
                fail("wtp_wrong_device")
            return hello
        except Exception:
            self.close()
            raise

    def wtp_status(self, expected_boot_id: str) -> dict[str, Any]:
        status = self.wtp_exchange("STATUS", {})
        if set(status) != {
            "boot_id",
            "state",
            "output_active",
            "owner_id",
            "job_id",
            "terminal_records",
        }:
            fail("wtp_status_response")
        if (
            status.get("boot_id") != expected_boot_id
            or status.get("state") not in _WTP_STATES
            or not isinstance(status.get("output_active"), bool)
            or (status.get("owner_id") is not None and not valid_device_id(status.get("owner_id")))
            or (status.get("job_id") is not None and not valid_device_id(status.get("job_id")))
            or not isinstance(status.get("terminal_records"), list)
        ):
            fail("wtp_status_response")
        for record in status["terminal_records"]:
            if not isinstance(record, dict) or not {
                "job_id",
                "state",
                "ended_monotonic_ns",
                "output_active",
            }.issubset(record) or set(record) - {
                "job_id",
                "state",
                "ended_monotonic_ns",
                "output_active",
                "error",
            }:
                fail("wtp_status_response")
            error = record.get("error")
            if (
                not valid_device_id(record.get("job_id"))
                or record.get("state") not in _WTP_STATES
                or not isinstance(record.get("ended_monotonic_ns"), str)
                or _DECIMAL.fullmatch(record["ended_monotonic_ns"]) is None
                or not isinstance(record.get("output_active"), bool)
                or (
                    error is not None
                    and (
                        not isinstance(error, dict)
                        or set(error) != {"code", "message", "retryable"}
                        or remote_error(error.get("code")) != error.get("code")
                        or error.get("message") != error.get("code")
                        or not isinstance(error.get("retryable"), bool)
                    )
                )
            ):
                fail("wtp_status_response")
        return status

    @staticmethod
    def _step_up_ready(response: dict[str, Any]) -> tuple[bool, bool]:
        confirmation = response.get("confirmation_required")
        ready = response.get("ready")
        if (
            not isinstance(confirmation, bool)
            or not isinstance(ready, bool)
            or (not confirmation and not ready)
        ):
            fail("profile_step_up_response")
        return confirmation, ready

    def provision(
        self,
        profile: bytearray,
        password: str,
        on_confirmation_required: Callable[[str], None] | None = None,
    ) -> int:
        if not self.authorized:
            fail("authentication_required")
        if not _printable(password, 8, 63):
            fail("local_password")
        try:
            parsed = json.loads(profile.decode("ascii"))
            if parsed.get("device_id") != self.expected_device_id:
                fail("wrong_device")
            session = secrets.token_hex(16)
            opened = False
            apply_accepted = False
            try:
                self._field("open", session_id=session)
                opened = True
                for offset in range(0, len(profile), FRAGMENT_BYTES):
                    end = min(offset + FRAGMENT_BYTES, len(profile))
                    self._field(
                        "write",
                        session_id=session,
                        offset=offset,
                        final=end == len(profile),
                        payload=base64.b64encode(profile[offset:end]).decode("ascii"),
                    )
                apply_request = secrets.token_hex(16)
                step_up = self._field(
                    "profile_step_up",
                    profile_session_id=session,
                    apply_request_id=apply_request,
                    expected_generation=self.generation,
                    password=password,
                )
                password = ""
                confirmation, ready = self._step_up_ready(step_up)
                if confirmation and not ready:
                    if on_confirmation_required is not None:
                        on_confirmation_required(self.expected_device_id)
                    deadline = time.monotonic() + self.confirmation_timeout
                    while not ready:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            fail("confirmation_timeout")
                        self.backend.pump(min(PROFILE_CONFIRMATION_POLL_SECONDS, remaining))
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            fail("confirmation_timeout")
                        try:
                            step_up = self._field(
                                "profile_step_up_status",
                                timeout=min(self.timeout, remaining),
                                apply_request_id=apply_request,
                            )
                        except ClientError as error:
                            if error.code == "timeout":
                                fail("confirmation_timeout")
                            raise
                        confirmation, ready = self._step_up_ready(step_up)
                response = self.exchange({
                    "version": 1,
                    "operation": "apply",
                    "request_id": apply_request,
                    "session_id": session,
                    "device_id": self.expected_device_id,
                    "expected_generation": self.generation,
                })
                apply_accepted = True
                generation = response.get("generation")
                if isinstance(generation, bool) or not isinstance(generation, int) or generation < self.generation:
                    fail("generation")
                self.generation = generation
                return generation
            except Exception:
                if opened and not apply_accepted:
                    try:
                        self._field("cancel", session_id=session)
                    except Exception:
                        pass
                raise
        finally:
            password = ""
            profile[:] = b"\x00" * len(profile)

    def close(self) -> None:
        self.status_receiver.reset()
        self.wtp_receiver.reset()
        self._field_responses.clear()
        self._wtp_responses.clear()
        self._field_pending = ""
        self._wtp_pending = ""
        self._wtp_pending_op = ""
        self._fatal = None
        self.expected_device_id = ""
        self.generation = 0
        self.authorized = False
        self.field_session = ""
        self.wtp_session = ""
        try:
            self.backend.close()
        except Exception:
            pass


class BluezBackend:
    """Small BlueZ D-Bus adapter; it never changes the device Trusted property."""

    BLUEZ = "org.bluez"
    OBJECT_MANAGER = "org.freedesktop.DBus.ObjectManager"
    PROPERTIES = "org.freedesktop.DBus.Properties"
    ADAPTER = "org.bluez.Adapter1"
    DEVICE = "org.bluez.Device1"
    SERVICE = "org.bluez.GattService1"
    CHARACTERISTIC = "org.bluez.GattCharacteristic1"
    AGENT_MANAGER = "org.bluez.AgentManager1"
    AGENT = "org.bluez.Agent1"

    def __init__(self, adapter: str):
        try:
            import dbus  # type: ignore
            import dbus.mainloop.glib  # type: ignore
            import dbus.service  # type: ignore
            from gi.repository import GLib  # type: ignore
        except (ImportError, ValueError):
            fail("bluez_dependencies")
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.dbus, self.GLib = dbus, GLib
        self.bus = dbus.SystemBus()
        self.context = GLib.MainContext.default()
        self.adapter_path = f"/org/bluez/{adapter}"
        self.device_path = ""
        self.characteristics: dict[str, str] = {}
        self.matches: list[Any] = []
        self.agent: Any = None
        self.agent_path = f"/org/wsprrypico/agent_{os.getpid()}_{secrets.token_hex(4)}"

    def _objects(self) -> dict[str, Any]:
        root = self.bus.get_object(self.BLUEZ, "/")
        manager = self.dbus.Interface(root, self.OBJECT_MANAGER)
        return manager.GetManagedObjects()

    def _property(self, path: str, interface: str, name: str) -> Any:
        obj = self.bus.get_object(self.BLUEZ, path)
        properties = self.dbus.Interface(obj, self.PROPERTIES)
        return properties.Get(interface, name)

    def pump(self, seconds: float) -> None:
        deadline = time.monotonic() + max(0.0, seconds)
        while self.context.pending():
            self.context.iteration(False)
        while time.monotonic() < deadline:
            if self.context.pending():
                self.context.iteration(False)
            else:
                time.sleep(min(0.01, deadline - time.monotonic()))

    def _wait(self, predicate: Callable[[], bool], timeout: float, code: str) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            self.pump(min(0.05, deadline - time.monotonic()))
        fail(code)

    def _async(self, interface: Any, method: str, timeout: float, code: str, *arguments: Any) -> None:
        state: dict[str, Any] = {}
        getattr(interface, method)(
            *arguments,
            reply_handler=lambda *unused: state.update(done=True),
            error_handler=lambda error: state.update(done=True, error=error),
        )
        self._wait(lambda: bool(state.get("done")), timeout, code)
        if "error" in state:
            fail(code)

    def _register_agent(self) -> None:
        dbus = self.dbus
        service_uuid = UUIDS["service"]
        agent_interface = self.AGENT
        expected_device_path = self.device_path

        class Agent(dbus.service.Object):
            @staticmethod
            def reject() -> None:
                error = dbus.exceptions.DBusException("device or service rejected")
                error._dbus_error_name = "org.bluez.Error.Rejected"
                raise error

            @dbus.service.method(agent_interface, in_signature="", out_signature="")
            def Release(self) -> None:
                return None

            @dbus.service.method(agent_interface, in_signature="o", out_signature="")
            def RequestAuthorization(self, device: str) -> None:
                if not pairing_request_allowed(str(device), expected_device_path):
                    self.reject()

            @dbus.service.method(agent_interface, in_signature="os", out_signature="")
            def AuthorizeService(self, device: str, uuid: str) -> None:
                if not pairing_request_allowed(str(device), expected_device_path, str(uuid)):
                    self.reject()

            @dbus.service.method(agent_interface, in_signature="", out_signature="")
            def Cancel(self) -> None:
                return None

        self.agent = Agent(self.bus, self.agent_path)
        root = self.bus.get_object(self.BLUEZ, "/org/bluez")
        manager = self.dbus.Interface(root, self.AGENT_MANAGER)
        try:
            manager.RegisterAgent(self.agent_path, "NoInputNoOutput")
            manager.RequestDefaultAgent(self.agent_path)
        except Exception:
            self.agent.remove_from_connection()
            self.agent = None
            fail("pairing_agent")

    def _find_device(self, address: str, service_uuid: str, timeout: float) -> str:
        expected = f"{self.adapter_path}/dev_{address.replace(':', '_')}"
        if expected in self._objects():
            return expected
        adapter_obj = self.bus.get_object(self.BLUEZ, self.adapter_path)
        adapter = self.dbus.Interface(adapter_obj, self.ADAPTER)
        try:
            adapter.SetDiscoveryFilter({
                "Transport": self.dbus.String("le"),
                "UUIDs": self.dbus.Array([self.dbus.String(service_uuid)], signature="s"),
            })
            adapter.StartDiscovery()
        except Exception:
            fail("discovery_start")
        try:
            self._wait(lambda: expected in self._objects(), timeout, "device_not_found")
            return expected
        finally:
            try:
                adapter.StopDiscovery()
            except Exception:
                pass

    def connect(
        self, address: str, service_uuid: str, timeout: float, allow_pairing: bool = True
    ) -> None:
        objects = self._objects()
        if self.adapter_path not in objects or self.ADAPTER not in objects[self.adapter_path]:
            fail("adapter_not_found")
        if not bool(objects[self.adapter_path][self.ADAPTER].get("Powered")):
            fail("adapter_not_powered")
        try:
            self.device_path = self._find_device(address, service_uuid, timeout)
            obj = self.bus.get_object(self.BLUEZ, self.device_path)
            device = self.dbus.Interface(obj, self.DEVICE)
            if not bool(self._property(self.device_path, self.DEVICE, "Paired")):
                if not allow_pairing:
                    fail("pairing_required")
                self._register_agent()
                self._async(device, "Pair", timeout, "pairing_failed")
            if not bool(self._property(self.device_path, self.DEVICE, "Connected")):
                self._async(device, "Connect", timeout, "connect_failed")
            self._wait(
                lambda: bool(self._property(self.device_path, self.DEVICE, "ServicesResolved")),
                timeout,
                "services_timeout",
            )
            objects = self._objects()
            service_paths = {
                path
                for path, interfaces in objects.items()
                if path.startswith(self.device_path + "/")
                and self.SERVICE in interfaces
                and str(interfaces[self.SERVICE].get("UUID", "")).lower() == service_uuid
            }
            if len(service_paths) != 1:
                fail("service_missing")
            self.characteristics = {}
            for path, interfaces in objects.items():
                if self.CHARACTERISTIC not in interfaces:
                    continue
                properties = interfaces[self.CHARACTERISTIC]
                if str(properties.get("Service", "")) not in service_paths:
                    continue
                uuid = str(properties.get("UUID", "")).lower()
                if uuid in self.characteristics:
                    fail("characteristic_duplicate")
                self.characteristics[uuid] = path
            if set(UUIDS.values()) - {service_uuid} - set(self.characteristics):
                fail("characteristic_missing")
        except Exception:
            self.close()
            raise

    def _characteristic(self, uuid: str) -> tuple[str, Any]:
        path = self.characteristics.get(uuid)
        if not path:
            fail("characteristic_missing")
        obj = self.bus.get_object(self.BLUEZ, path)
        return path, self.dbus.Interface(obj, self.CHARACTERISTIC)

    def read(self, uuid: str) -> bytes:
        _, characteristic = self._characteristic(uuid)
        try:
            return bytes(characteristic.ReadValue({}))
        except Exception:
            fail("gatt_read")

    def write(self, uuid: str, value: bytes | bytearray, response: bool = True) -> None:
        _, characteristic = self._characteristic(uuid)
        try:
            characteristic.WriteValue(
                self.dbus.Array([self.dbus.Byte(byte) for byte in value], signature="y"),
                {"type": self.dbus.String("request" if response else "command")},
            )
        except Exception:
            fail("gatt_write")

    def start_notify(self, uuid: str, callback: Callable[[bytes], None]) -> None:
        path, characteristic = self._characteristic(uuid)

        def changed(interface: str, changes: dict[str, Any], invalidated: list[str]) -> None:
            del invalidated
            if str(interface) == self.CHARACTERISTIC and "Value" in changes:
                callback(bytes(changes["Value"]))

        try:
            match = self.bus.add_signal_receiver(
                changed,
                bus_name=self.BLUEZ,
                dbus_interface=self.PROPERTIES,
                signal_name="PropertiesChanged",
                path=path,
                arg0=self.CHARACTERISTIC,
            )
            self.matches.append(match)
            characteristic.StartNotify()
        except Exception:
            if self.matches:
                self.matches.pop().remove()
            fail("gatt_notify")

    def close(self) -> None:
        for match in self.matches:
            try:
                match.remove()
            except Exception:
                pass
        self.matches.clear()
        if self.device_path:
            try:
                obj = self.bus.get_object(self.BLUEZ, self.device_path)
                self.dbus.Interface(obj, self.DEVICE).Disconnect()
            except Exception:
                pass
        self.device_path = ""
        self.characteristics.clear()
        if self.agent is not None:
            try:
                root = self.bus.get_object(self.BLUEZ, "/org/bluez")
                self.dbus.Interface(root, self.AGENT_MANAGER).UnregisterAgent(self.agent_path)
            except Exception:
                pass
            try:
                self.agent.remove_from_connection()
            except Exception:
                pass
            self.agent = None


def _password(prompt: str = "WsprryPico application password: ") -> str:
    try:
        value = getpass.getpass(prompt)
    except (EOFError, KeyboardInterrupt):
        fail("password_input")
    if not _printable(value, 8, 63):
        value = ""
        fail("local_password")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Authenticated WsprryPico BLE local control")
    parser.add_argument("--address", required=True, help="exact WsprryPico BLE address")
    parser.add_argument("--device-id", required=True, help="expected 32-lowercase-hex device ID")
    parser.add_argument("--adapter", default="hci0", help="BlueZ adapter name (default: hci0)")
    parser.add_argument("--timeout", type=float, default=30.0, help="bounded operation timeout in seconds")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "inspect", help="connect to an already-paired controller and verify its exact identity"
    )
    commands.add_parser("status", help="read authenticated field status")
    commands.add_parser("identify", help="run the bounded visual Identify pattern")
    commands.add_parser("sync-time", help="submit controller UTC after a bound challenge")
    commands.add_parser("wtp-status", help="negotiate unchanged WTP/1 and request STATUS")
    provision = commands.add_parser("provision", help="atomically apply a protected profile")
    provision.add_argument("--profile", required=True, help="absolute owner-only canonical profile JSON")
    return parser


def run(arguments: list[str] | None = None, backend_factory: Callable[[str], Any] = BluezBackend) -> int:
    args = _parser().parse_args(arguments)
    address = normalize_address(args.address)
    if not valid_device_id(args.device_id):
        fail("device_id")
    client = Client(backend_factory(args.adapter), args.timeout)
    try:
        identity = client.connect(address, args.device_id, allow_pairing=args.command != "inspect")
        if args.command == "inspect":
            output = {"address": address, "device_id": identity["device_id"], "generation": identity["generation"]}
        else:
            password = _password()
            try:
                client.authorize(password)
            finally:
                password = ""
            if args.command == "status":
                output = client.field_status()
            elif args.command == "identify":
                client.identify()
                output = {"identified": True}
            elif args.command == "sync-time":
                client.synchronize_time()
                output = {"accepted": True}
            elif args.command == "wtp-status":
                hello = client.enable_local_control()
                status = client.wtp_status(hello["boot_id"])
                output = {
                    "hello": {
                        "selected_version": hello["selected_version"],
                        "device_id": hello["device_id"],
                        "boot_id": hello["boot_id"],
                        "product": hello["product"],
                        "firmware_version": hello["firmware_version"],
                    },
                    "status": status,
                }
            elif args.command == "provision":
                profile = load_profile_file(args.profile)
                step_up_password = ""
                try:
                    step_up_password = _password(
                        "Re-enter current local password for profile apply: "
                    )
                    output = {"generation": client.provision(
                        profile,
                        step_up_password,
                        lambda device_id: print(
                            f"USB confirmation required: ACCESS CONFIRM PROFILE {device_id}",
                            file=sys.stderr,
                        ),
                    )}
                finally:
                    step_up_password = ""
                    profile[:] = b"\x00" * len(profile)
            else:
                fail("command")
        print(json.dumps(output, sort_keys=True, separators=(",", ":")))
        return 0
    finally:
        client.close()


def main() -> int:
    try:
        return run()
    except ClientError as error:
        print(f"wsprrypico-ble: {error.code}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("wsprrypico-ble: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
