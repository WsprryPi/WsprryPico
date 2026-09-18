"""Opt-in Phase 11.6 network controller and SDR capture adapter.

This module is imported only by an explicit physical entry point.  Planning and
auditing modules do not import it and therefore cannot open hardware.
"""

from __future__ import annotations

import configparser
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.request
import uuid

from phase11_5_inventory import require
from phase11_5_package9 import (ConsoleObserver, UsbStatusObserver, inventory,
                                resource_gate)
from phase11_5_pilot import Decoder
from validate_wtp_contract import frame

from phase11_6.plan import (FIRMWARE_SOURCE, PICO_ACCEPTED_BOOT, PICO_DEVICE_ID,
                            RECEIVER_SERIAL, digest)


HOSTNAME = "wsprrypico-0a60df.local"
ADDRESS = "10.77.15.10"
PORT = 18_443
PEER_SHA256 = "06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016"
CAPTURE_RATE = 250_000
CAPTURE_BANDWIDTH = 200_000
CAPTURE_GAIN = 20
CAPTURE_HELPER_SHA256 = (
    "b98de116d696846b88eea1b3ad3f1b2a471052fa2ca440f4234fec7087dc5a03"
)
MINIMUM_ARM_LEAD_NS = 8_000_000_000
# The browser-owned path must still compile the compact form and complete
# HELLO/CLAIM/LOAD_MESSAGE after the submit marker is written.  The accepted
# image has taken approximately ten seconds to do that under observation, so
# the controller-only eight-second lead is not sufficient for this path.
BROWSER_ARM_LEAD_NS = 20_000_000_000
WTP_ADMISSION_WAIT_SECONDS = 90.0
WTP_ADMISSION_RETRY_SECONDS = 5.0
# A clock that is still near the end of the Pico's SNTP polling interval can
# accept ARM and then legitimately reject the immutable monotonic target after
# the next sample tightens its UTC mapping.  Admit physical attempts only in the
# freshly settled part of the existing 500 ms protocol envelope.
SETTLED_CLOCK_UNCERTAINTY_NS = 10_000_000
CORRECTIVE_MINIMUM_SYNC_AGE_NS = 24_000_000_000
CORRECTIVE_MAXIMUM_SYNC_AGE_NS = 29_000_000_000


class RetryableWtpBusy(ValueError):
    """The authenticated listener is healthy but its prior session is draining."""


def configure_capture_validator(source: Path) -> dict:
    """Bind the external Qualification Harness validator used for raw IQ."""
    source = source.resolve(strict=True)
    package = source / "wsprrypi_qualification"
    files = {
        "capture_metadata.py": package / "capture_metadata.py",
        "capture-metadata.schema.json":
            package / "schemas" / "capture-metadata.schema.json",
    }
    require(source.is_dir() and all(path.is_file() for path in files.values()),
            "Qualification Harness capture validator source")
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    from wsprrypi_qualification.capture_metadata import load_capture_metadata
    require(callable(load_capture_metadata), "Qualification Harness validator import")
    return {name: sha256(path) for name, path in files.items()}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require_capture_helper(path: Path) -> Path:
    """Require the exact reviewed native SDR helper before physical access."""
    helper = path.resolve(strict=True)
    if (not helper.is_file() or not os.access(helper, os.X_OK)
            or sha256(helper) != CAPTURE_HELPER_SHA256):
        raise ValueError("Exact reviewed capture helper identity required")
    return helper


def wait_observer_readiness(console: ConsoleObserver, usb: UsbStatusObserver,
                            timeout: float = 95.0, *,
                            maximum_uncertainty_ns: int =
                            SETTLED_CLOCK_UNCERTAINTY_NS,
                            minimum_sync_age_ns: int = 0,
                            maximum_sync_age_ns: int | None = None) -> None:
    """Require independent authority and a freshly settled Pico UTC mapping."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        require(console.failure is None and usb.failure is None,
                "Independent observer admission failure")
        clock = usb.clock
        if (console.latest is not None and usb.latest is not None
                and clock is not None
                and clock.get("state") == "synchronized"
                and clock.get("leap") == "normal"
                and int(clock.get("uncertainty_ns", "999999999"))
                    <= maximum_uncertainty_ns
                and int(clock.get("sync_age_ns", "0")) >= minimum_sync_age_ns
                and (maximum_sync_age_ns is None
                     or int(clock.get("sync_age_ns", "999999999999"))
                     <= maximum_sync_age_ns)):
            return
        time.sleep(0.05)
    raise TimeoutError("Independent observer admission deadline")


def armed_clock_refinement(rows: list[dict], job_id: str) -> dict:
    """Find a strictly better accepted clock sample while the job remains Armed."""
    samples = []
    for row in rows:
        if row.get("kind") != "console_info":
            continue
        info = row.get("value", {}).get("value", {})
        status = info.get("status", {})
        if status.get("state") != "armed":
            continue
        samples.append({
            "sequence": row.get("sequence"),
            "monotonic_ns": row.get("monotonic_ns"),
            "accepted_samples": info.get("network", {}).get("accepted"),
            "utc_now_ns": int(status["utc_now_ns"]),
            "monotonic_now_ns": int(status["monotonic_now_ns"]),
            "sync_age_ns": int(status["sync_age_ns"]),
            "uncertainty_ns": int(status["uncertainty_ns"]),
        })
    for before, after in zip(samples, samples[1:]):
        if (isinstance(before["accepted_samples"], int)
                and isinstance(after["accepted_samples"], int)
                and after["accepted_samples"] > before["accepted_samples"]
                and after["sync_age_ns"] < before["sync_age_ns"]
                and after["uncertainty_ns"] < before["uncertainty_ns"]):
            before_offset = before["utc_now_ns"] - before["monotonic_now_ns"]
            after_offset = after["utc_now_ns"] - after["monotonic_now_ns"]
            return {
                "job_id": job_id,
                "before": before,
                "after": after,
                "utc_monotonic_mapping_change_ns": after_offset - before_offset,
                "uncertainty_reduction_ns": (
                    before["uncertainty_ns"] - after["uncertainty_ns"]
                ),
            }
    raise ValueError("No accepted lower-uncertainty clock sample while Armed")


def settled_inventory(root: Path, label: str, serial: str, device: str,
                      journal: "Journal", *, timeout: float = 30.0) -> dict:
    """Retry read-only inventory while a completed TLS session drains."""
    deadline = time.monotonic() + timeout
    attempt = 0
    while True:
        attempt += 1
        attempt_label = f"{label}-read-{attempt}"
        try:
            value = inventory(root, {}, attempt_label, serial, device, uuid.uuid4().hex)
            journal.emit("inventory_complete", {
                "label": label, "attempt": attempt,
                "evidence_label": attempt_label,
            })
            return value
        except ValueError as error:
            journal.emit("inventory_wait", {
                "label": label, "attempt": attempt,
                "evidence_label": attempt_label,
                "error_type": type(error).__name__, "message": str(error),
            })
            require(time.monotonic() < deadline,
                    "Read-only inventory settlement deadline")
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))


def usb_completion(status_states: set[str], event_states: set[str],
                   status_jobs: set[str], event_jobs: set[str],
                   latest: dict, job_id: str) -> dict:
    """Reduce ordered USB events plus authoritative STATUS to one completion."""
    require(latest.get("boot_id") == PICO_ACCEPTED_BOOT,
            "Independent USB final boot identity")
    terminals = [record for record in latest.get("terminal_records", [])
                 if record.get("job_id") == job_id]
    prior_status_jobs = status_jobs - {job_id}
    prior_terminals = {record.get("job_id") for record in latest.get("terminal_records", [])
                       if record.get("job_id") in prior_status_jobs
                       and record.get("state") == "complete"
                       and record.get("output_active") is False}
    require({"loaded", "armed", "running", "complete"}.issubset(
                status_states | event_states)
            and event_jobs == {job_id}
            and job_id in status_jobs | event_jobs
            and prior_terminals == prior_status_jobs
            and latest.get("output_active") is False
            and latest.get("owner_id") is None
            and len(terminals) == 1
            and terminals[0].get("state") == "complete"
            and terminals[0].get("output_active") is False,
            "Independent USB lifecycle/terminal authority")
    return {
        "status_states": sorted(status_states),
        "event_states": sorted(event_states),
        "terminal": terminals[0],
        "final": latest,
    }


def validate_usb_completion(observer: UsbStatusObserver, job_id: str) -> dict:
    return usb_completion(
        observer.states, observer.event_states, observer.jobs,
        observer.event_jobs, observer.latest or {}, job_id,
    )


def save(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".pending")
    with temporary.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def host_status(port: int, journal: "Journal") -> dict:
    began = time.monotonic_ns()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(
        f"http://127.0.0.1:{port}/api/v1/status", timeout=3
    ) as response:
        raw = response.read(131_073)
        code = response.status
    require(code == 200 and len(raw) <= 131_072, "Production host status bounds")
    value = json.loads(raw)
    journal.emit(
        "production_host_status",
        {"began_monotonic_ns": began, "body_sha256": hashlib.sha256(raw).hexdigest(),
         "value": value},
    )
    return value


def render_production_ini(root: Path, directory: Path, job: dict, port: int) -> Path:
    """Render one private, non-persistent WsprryPi production configuration."""
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    base = root / "production-base.ini"
    require(parser.read(base) == [str(base)], "Production INI baseline")
    mode = job["mode"]
    parser["Operation"]["Mode"] = mode
    parser["Operation"]["Transmit"] = "true"
    parser["Operation"]["Transmit Backend"] = "wtp"
    # This is a one-shot private campaign INI, not the installed service's
    # persistent policy.  Follow is required here so the explicit
    # Transmit=true request survives managed startup policy application.
    parser["Operation"]["Enable on Boot"] = "Follow"
    parser["Operation"]["Use LED"] = "false"
    parser["Operation"]["Use Amp"] = "false"
    parser["Operation"]["Use Shutdown"] = "false"
    parser["Operation"]["Web Port"] = str(port)
    parser["Operation"]["Socket Port"] = str(port + 1)
    parser["Calibration"]["PPM"] = "0.0"
    parser["Experimental"]["Allow Unqualified Frequency"] = "true"
    parser["Experimental"]["Allow Non-Amateur Frequency"] = "true"
    parser["WSPR"]["Call Sign"] = "AA0NT"
    parser["WSPR"]["Grid Square"] = "EM18"
    parser["WSPR"]["TX Power"] = "20"
    parser["WSPR"]["Frequency"] = job["band"]
    parser["WSPR"]["Planner Preference"] = "auto"
    parser["WSPR"]["Use Random Offset"] = "false"
    parser["CW"]["Message"] = job["production_expectation"].get("message") or "ET E"
    parser["CW"]["Base Frequency"] = str(job["nominal_frequency_hz"])
    parser["CW"]["Shift Hz"] = "5"
    parser["CW"]["Dot Seconds"] = "3"
    parser["CW"]["Intra Element Gap"] = "1"
    parser["CW"]["Inter Character Gap"] = "3"
    parser["CW"]["Inter Word Gap"] = "7"
    parser["CW"]["DFCW Intra Element Gap"] = "1"
    parser["CW"]["DFCW Inter Character Gap"] = "3"
    parser["CW"]["DFCW Inter Word Gap"] = "7"
    parser["CW"]["Fade Shape"] = "none"
    parser["CW"]["Fade In Ms"] = "0"
    parser["CW"]["Fade Out Ms"] = "0"
    parser["CW"]["Start Minute"] = "0"
    parser["CW"]["Start Second"] = "0"
    parser["CW"]["Repeat Minutes"] = "2"
    path = directory / "production.ini"
    with path.open("x") as stream:
        parser.write(stream)
        stream.flush()
        os.fsync(stream.fileno())
    return path


def production_command(binary: Path, ini: Path, job: dict) -> list[str]:
    command = [
        str(binary), "--backend", "wtp", "-i", str(ini),
        "--socket-loopback-only", "--socket-loopback-family", "ipv4",
        "--allow-unqualified-frequency", "--allow-non-amateur-frequency",
    ]
    frequency = job["nominal_frequency_hz"]
    message = job["production_expectation"].get("message") or "ET E"
    if job["mode"] == "QRSS":
        command.extend([
            "--qrss-message", message, "--qrss-frequency", str(frequency),
            "--qrss-dot-seconds", "3",
        ])
    elif job["mode"] == "FSKCW":
        command.extend([
            "--fskcw-message", message,
            "--fskcw-mark-frequency", str(frequency + 5),
            "--fskcw-space-frequency", str(frequency),
            "--fskcw-dot-seconds", "3",
        ])
    elif job["mode"] == "DFCW":
        # The retained Pico campaign profile is intentionally reverse DFCW.
        # WsprryPi's conventional default is not changed; explicit frequencies
        # reproduce dot-high/dash-low for this accepted-image matrix only.
        command.extend([
            "--dfcw-message", message,
            "--dfcw-dot-frequency", str(frequency + 5),
            "--dfcw-dash-frequency", str(frequency),
            "--dfcw-dot-seconds", "3",
        ])
    return command


def _tls_messages(root: Path, path: Path) -> tuple[list[dict], list[dict], dict]:
    decoder_path = root / "scripts/phase11_5_tls_observer_decoder.py"
    spec = importlib.util.spec_from_file_location("phase116_tls_decoder", decoder_path)
    require(spec is not None and spec.loader is not None, "TLS observer decoder import")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = module.decode(path.read_bytes())
    candidates = []
    for connection in sorted({row["connection_id"] for row in rows if row["kind"] == 1}):
        directions = []
        for kind in (3, 4):
            decoder, messages = Decoder(), []
            for row in rows:
                if row["connection_id"] == connection and row["kind"] == kind:
                    messages.extend(decoder.feed(row["payload"]))
            require(not decoder.buffer, "Partial production WTP frame")
            directions.append(messages)
        if directions[0]:
            candidates.append((connection, *directions))
    require(len(candidates) == 1, "Production WTP connection count")
    connection, written, received = candidates[0]
    return written, received, {
        "observer_sha256": sha256(root / "observer.so"),
        "decoder_sha256": sha256(decoder_path),
        "record_count": len(rows),
        "connection_id": connection,
        "tls_log_sha256": sha256(path),
    }


class Journal:
    def __init__(self, path: Path):
        self.path = path
        self.stream = path.open("x", buffering=1)
        self.lock = threading.Lock()
        self.sequence = 0

    def emit(self, kind: str, value: object) -> dict:
        with self.lock:
            row = {
                "sequence": self.sequence,
                "kind": kind,
                "monotonic_ns": time.monotonic_ns(),
                "utc_ns": time.time_ns(),
                "value": value,
            }
            self.stream.write(json.dumps(row, separators=(",", ":")) + "\n")
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.sequence += 1
            return row

    def close(self) -> None:
        self.stream.close()


def tls_context(root: Path, role: str, alpn: str) -> ssl.SSLContext:
    credentials = root / "credentials" / role
    context = ssl.create_default_context(cafile=str(credentials / "client-ca.crt"))
    context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.set_ecdh_curve("X25519")
    context.load_cert_chain(credentials / "client.crt", credentials / "client.key")
    context.set_alpn_protocols([alpn])
    return context


class NetworkPeer:
    def __init__(self, root: Path, journal: Journal, *, session: str | None = None,
                 request_number: int = 0):
        self.root = root
        self.journal = journal
        self.session = session or uuid.uuid4().hex
        self.request_number = request_number
        self.stream: ssl.SSLSocket | None = None
        self.decoder = Decoder()
        self.events: list[dict] = []

    def connect(self) -> "NetworkPeer":
        deadline = time.monotonic() + WTP_ADMISSION_WAIT_SECONDS
        attempt = 0
        while True:
            attempt += 1
            raw = socket.create_connection((ADDRESS, PORT), timeout=8)
            try:
                self.stream = tls_context(
                    self.root, "controller", "wtp/1"
                ).wrap_socket(raw, server_hostname=HOSTNAME)
            except BaseException:
                raw.close()
                raise
            require(
                self.stream.selected_alpn_protocol() == "wtp/1"
                and hashlib.sha256(self.stream.getpeercert(binary_form=True)).hexdigest()
                == PEER_SHA256,
                "Phase 11.6 authenticated WTP peer",
            )
            try:
                hello = self.ask(
                    "HELLO",
                    {
                        "versions": ["WTP/1"],
                        "client_name": "phase11-6-conducted-controller",
                        "client_version": "1",
                    },
                )
                break
            except RetryableWtpBusy:
                self.close()
                remaining = deadline - time.monotonic()
                require(remaining > 0, "WTP admission settlement deadline")
                self.journal.emit(
                    "wtp_admission_busy",
                    {"attempt": attempt, "remaining_seconds": remaining},
                )
                time.sleep(min(WTP_ADMISSION_RETRY_SECONDS, remaining))
                self.decoder = Decoder()
        require(
            hello["device_id"] == PICO_DEVICE_ID
            and hello["boot_id"] == PICO_ACCEPTED_BOOT,
            "Phase 11.6 HELLO identity",
        )
        return self

    def close(self) -> None:
        if self.stream is not None:
            self.stream.close()
            self.stream = None

    def ask(self, operation: str, body: dict | None = None, *, expect_ok: bool = True,
            timeout: float = 20) -> dict:
        require(self.stream is not None, "WTP peer is not connected")
        self.request_number += 1
        request = {
            "type": "request",
            "protocol": "WTP/1",
            "session_id": self.session,
            "request_id": f"{self.request_number:032x}",
            "op": operation,
            "body": body or {},
        }
        wire = frame(json.dumps(request, separators=(",", ":")).encode())
        self.journal.emit(
            "wtp_tx",
            {
                "operation": operation,
                "session_id": self.session,
                "request_id": request["request_id"],
                "wire_sha256": hashlib.sha256(wire).hexdigest(),
                "bytes": len(wire),
            },
        )
        self.stream.sendall(wire)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.stream.settimeout(max(0.001, deadline - time.monotonic()))
            block = self.stream.recv(8192)
            require(block, "WTP EOF before response")
            for value in self.decoder.feed(block):
                if value.get("type") == "event":
                    require(value.get("boot_id") == PICO_ACCEPTED_BOOT, "WTP event boot")
                    self.events.append(value)
                    self.journal.emit("wtp_event", value)
                    continue
                require(
                    value.get("session_id") == self.session
                    and value.get("request_id") == request["request_id"]
                    and value.get("op") == operation,
                    "WTP response correlation",
                )
                self.journal.emit("wtp_response", value)
                if (
                    expect_ok
                    and value.get("ok") is False
                    and value.get("error", {}).get("code") == "BUSY"
                    and value.get("error", {}).get("retryable") is True
                ):
                    raise RetryableWtpBusy("retryable WTP admission BUSY")
                require(value.get("ok") is expect_ok, "Unexpected WTP response disposition")
                return value.get("body", {})
        raise TimeoutError("WTP request deadline: " + operation)


class Capture:
    def __init__(self, root: Path, directory: Path, helper: Path, frequency_hz: int,
                 seconds: float, journal: Journal):
        self.root = root
        self.directory = directory
        self.helper = helper
        self.frequency_hz = frequency_hz
        self.seconds = seconds
        self.samples = int(round(seconds * CAPTURE_RATE))
        self.center_hz = frequency_hz - 25_000
        self.journal = journal
        self.process: subprocess.Popen | None = None
        self.output = None

    def start(self) -> None:
        require(self.process is None, "Capture already started")
        self.directory.mkdir(mode=0o700)
        expected_bytes = self.samples * 8
        free = os.statvfs(self.directory).f_bavail * os.statvfs(self.directory).f_frsize
        require(free > expected_bytes + 64_000_000, "Insufficient capture storage")
        output = self.directory / "capture.cf32"
        metadata = self.directory / "capture.json"
        command = [
            str(self.helper),
            "--enable-physical-sdr",
            "sdrplay",
            RECEIVER_SERIAL,
            str(self.center_hz),
            str(self.samples),
            str(CAPTURE_GAIN),
            str(CAPTURE_RATE),
            str(CAPTURE_BANDWIDTH),
            "0",
            "false",
            "false",
            "100000",
            str(int(self.seconds + 15)),
            str(output),
            str(metadata),
            self.directory.name,
        ]
        save(self.directory / "capture-request.json", {"argv": command})
        self.output = (self.directory / "receiver.log").open("x")
        self.process = subprocess.Popen(command, stdout=self.output, stderr=subprocess.STDOUT)
        incomplete = output.with_suffix(output.suffix + ".incomplete")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            require(self.process.poll() is None, "Receiver exited during readiness")
            if incomplete.exists() and incomplete.stat().st_size > 65_536:
                self.journal.emit(
                    "capture_ready",
                    {
                        "directory": self.directory.name,
                        "center_hz": self.center_hz,
                        "samples": self.samples,
                        "helper_sha256": sha256(self.helper),
                    },
                )
                return
            time.sleep(0.05)
        raise TimeoutError("Receiver readiness deadline")

    def finish(self) -> dict:
        require(self.process is not None and self.output is not None, "Capture not started")
        code = self.process.wait(timeout=self.seconds + 25)
        self.output.close()
        require(code == 0, "Receiver capture failed")
        from wsprrypi_qualification.capture_metadata import load_capture_metadata

        metadata_path = self.directory / "capture.json"
        load_capture_metadata(metadata_path)
        metadata = json.loads(metadata_path.read_text())
        iq = self.directory / "capture.cf32"
        expected = {
            "format": "CF32",
            "sample_rate_hz": CAPTURE_RATE,
            "bandwidth_hz": CAPTURE_BANDWIDTH,
            "center_frequency_hz": self.center_hz,
            "gain_db": CAPTURE_GAIN,
            "channel": 0,
            "agc": False,
            "bias_tee": False,
        }
        require(
            metadata.get("actual_settings") == expected
            and metadata.get("resolved_device")
            == {"driver": "sdrplay", "serial": RECEIVER_SERIAL}
            and metadata.get("retained_sample_count") == self.samples
            and metadata.get("overflow_count") == 0
            and metadata.get("clipping", {}).get("sample_count") == 0
            and metadata.get("first_read", {}).get("discarded") is True
            and metadata.get("output", {}).get("sha256") == sha256(iq),
            "Receiver identity/settings/integrity",
        )
        value = {
            "metadata_sha256": sha256(metadata_path),
            "capture_sha256": sha256(iq),
            "sample_count": self.samples,
            "bytes": iq.stat().st_size,
            "actual_settings": expected,
            "resolved_device": metadata["resolved_device"],
            "overflow_count": 0,
            "clipping_samples": 0,
        }
        self.journal.emit("capture_complete", value)
        return value

    def terminate(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=5)
        if self.output is not None and not self.output.closed:
            self.output.close()


class BrowserWatch:
    """Own one real Chromium page lifecycle in the isolated client namespace."""

    def __init__(self, root: Path, directory: Path, job_id: str | None, seconds: float,
                 journal: Journal, *, refresh_interval_s: float = 0.75):
        self.root, self.directory, self.job_id = root, directory, job_id
        self.seconds, self.journal = seconds, journal
        require(0.25 <= refresh_interval_s <= 60.0,
                "Finite browser refresh interval")
        self.refresh_interval_ms = round(refresh_interval_s * 1000)
        self.process: subprocess.Popen | None = None
        self.stdout = self.stderr = None

    def start(self) -> None:
        self.directory.mkdir(mode=0o700)
        require((self.root / "browser-home/.pki/nssdb/cert9.db").is_file()
                and (self.root / "chromium-etc/policies/managed/phase115.json").is_file(),
                "Bound browser trust/profile inputs")
        command = [
            "bwrap", "--ro-bind", "/", "/", "--bind", str(self.directory),
            str(self.directory), "--bind", str(self.root / "browser-home"), "/root",
            "--setenv", "HOME", "/root", "--ro-bind", str(self.root / "chromium-etc"),
            "/etc/chromium", "--tmpfs", "/tmp", "--dev", "/dev", "--proc", "/proc",
            "--unshare-pid", "--die-with-parent", "node",
            str(self.root / "scripts/phase11_6_browser_watch.js"), "--root",
            str(self.directory), "--job-id", self.job_id or "any", "--seconds", str(self.seconds),
            "--refresh-ms", str(self.refresh_interval_ms),
            "--run",
        ]
        self.stdout = (self.directory / "watch.stdout").open("x")
        self.stderr = (self.directory / "watch.stderr").open("x")
        self.process = subprocess.Popen(command, stdout=self.stdout, stderr=self.stderr)
        deadline = time.monotonic() + 50
        while time.monotonic() < deadline:
            require(self.process.poll() is None, "Browser exited during readiness")
            if (self.directory / "browser-ready").exists():
                self.journal.emit("browser_ready", {"job_id": self.job_id,
                    "pid": self.process.pid})
                return
            time.sleep(0.1)
        raise TimeoutError("Browser readiness deadline")

    def finish(self) -> dict:
        require(self.process is not None, "Browser not started")
        (self.directory / "browser-stop").touch(mode=0o600)
        code = self.process.wait(timeout=35)
        self.stdout.close(); self.stderr.close()
        result = json.loads((self.directory / "browser-result.json").read_text())
        require(code == 0 and result.get("status") == "PASS"
                and result.get("page_loaded") is True
                and result.get("manual_refresh_overlap") is True
                and ((self.job_id is not None and self.job_id in result.get("job_ids", []))
                     or (self.job_id is None and result.get("observed_job_id")
                         in result.get("job_ids", []))),
                "Actual browser page lifecycle")
        self.journal.emit("browser_complete", result)
        return result

    def pause(self) -> None:
        """Quiesce page refreshes before the atomic CLAIM/LOAD/ARM window."""
        require(self.process is not None and self.process.poll() is None,
                "Browser not available for pause")
        (self.directory / "browser-pause").touch(mode=0o600)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            require(self.process.poll() is None, "Browser exited during pause")
            if (self.directory / "browser-paused").exists():
                self.journal.emit("browser_paused", {"job_id": self.job_id})
                return
            time.sleep(0.05)
        raise TimeoutError("Browser pause acknowledgement deadline")

    def resume(self) -> None:
        require(self.process is not None and self.process.poll() is None,
                "Browser not available for resume")
        (self.directory / "browser-pause").unlink(missing_ok=True)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            require(self.process.poll() is None, "Browser exited during resume")
            if not (self.directory / "browser-paused").exists():
                self.journal.emit("browser_resumed", {"job_id": self.job_id})
                return
            time.sleep(0.05)
        raise TimeoutError("Browser resume acknowledgement deadline")

    def terminate(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill(); self.process.wait(timeout=5)
        for stream in (self.stdout, self.stderr):
            if stream is not None and not stream.closed:
                stream.close()


class BrowserSubmit:
    """Submit exactly one job through the shipped Chromium page."""

    def __init__(self, root: Path, directory: Path, job: dict, seconds: float,
                 journal: Journal):
        self.root, self.directory, self.job = root, directory, job
        self.seconds, self.journal = seconds, journal
        self.process: subprocess.Popen | None = None
        self.stdout = self.stderr = None

    def start(self) -> None:
        self.directory.mkdir(mode=0o700)
        require((self.root / "browser-home/.pki/nssdb/cert9.db").is_file()
                and (self.root / "chromium-etc/policies/managed/phase115.json").is_file(),
                "Bound browser trust/profile inputs")
        kind = ("raw" if self.job["submission_path"] == "browser_raw"
                else "compact")
        body = (self.job["expected_job"] if kind == "raw"
                else self.job["compact_request"])
        job_path = self.directory / "job.json"
        save(job_path, body)
        command = [
            "bwrap", "--ro-bind", "/", "/", "--bind", str(self.directory),
            str(self.directory), "--bind", str(self.root / "browser-home"), "/root",
            "--setenv", "HOME", "/root", "--ro-bind", str(self.root / "chromium-etc"),
            "/etc/chromium", "--tmpfs", "/tmp", "--dev", "/dev", "--proc", "/proc",
            "--unshare-pid", "--die-with-parent", "node",
            str(self.root / "scripts/phase11_6_browser_submit.js"), "--root",
            str(self.directory), "--kind", kind, "--job", str(job_path), "--run",
        ]
        self.stdout = (self.directory / "submit.stdout").open("x")
        self.stderr = (self.directory / "submit.stderr").open("x")
        self.process = subprocess.Popen(command, stdout=self.stdout, stderr=self.stderr)
        deadline = time.monotonic() + 50
        while time.monotonic() < deadline:
            require(self.process.poll() is None, "Browser submitter exited during readiness")
            if (self.directory / "browser-ready").exists():
                self.journal.emit("browser_submit_ready", {"pid": self.process.pid,
                    "job_id": body["job_id"], "kind": kind})
                return
            time.sleep(0.1)
        raise TimeoutError("Browser submitter readiness deadline")

    def submit(self, target_utc_ns: int) -> None:
        require(self.process is not None and self.process.poll() is None,
                "Browser submitter unavailable")
        save(self.directory / "submit.json", {"start_utc_ns": str(target_utc_ns)})
        self.journal.emit("browser_submit_authorized", {"target_utc_ns": target_utc_ns})

    def finish(self) -> dict:
        require(self.process is not None, "Browser submitter not started")
        code = self.process.wait(timeout=self.seconds + 75)
        self.stdout.close(); self.stderr.close()
        result = json.loads((self.directory / "browser-result.json").read_text())
        expected_id = self.job["expected_job"]["job_id"]
        expected_operation = ("LOAD" if self.job["submission_path"] == "browser_raw"
                              else "LOAD_MESSAGE")
        base_operations = ["HELLO", "CLAIM", expected_operation, "ARM"]
        operations = result.get("operations")
        release_required = result.get("release_required")
        expected_operations = base_operations + (["RELEASE"] if release_required else [])
        terminal = result.get("terminal") or {}
        final = result.get("final") or {}
        require(code == 0 and result.get("status") == "PASS"
                and result.get("job_id") == expected_id
                and result.get("manual_refresh_overlap") is True
                and isinstance(release_required, bool)
                and operations == expected_operations
                and terminal.get("job_id") == expected_id
                and terminal.get("state") in {"complete", "aborted", "missed", "failed"}
                and terminal.get("output_active") is False
                and final.get("output_active") is False
                and final.get("owner_id") is None,
                "Actual browser-owned submission lifecycle")
        self.journal.emit("browser_submit_complete", result)
        return result

    def terminate(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill(); self.process.wait(timeout=5)
        for stream in (self.stdout, self.stderr):
            if stream is not None and not stream.closed:
                stream.close()


def wait_for_terminal(root: Path, journal: Journal, session: str, request_number: int,
                      job_id: str, duration_seconds: float) -> tuple[dict, NetworkPeer]:
    peer = NetworkPeer(root, journal, session=session, request_number=request_number).connect()
    deadline = time.monotonic() + duration_seconds + 25
    seen = set()
    while time.monotonic() < deadline:
        status = peer.ask("STATUS")
        require(status["boot_id"] == PICO_ACCEPTED_BOOT, "Terminal STATUS boot")
        if status.get("job_id") == job_id:
            seen.add(status["state"])
        records = [record for record in status.get("terminal_records", [])
                   if record.get("job_id") == job_id]
        if status.get("job_id") == job_id and status["state"] in {
            "complete", "aborted", "missed", "failed"
        }:
            require(status["output_active"] is False, "Terminal output remains active")
            return {"status": status, "seen_states": sorted(seen), "records": records}, peer
        if records:
            require(records[-1]["output_active"] is False, "Terminal record output active")
            return {"status": status, "seen_states": sorted(seen), "records": records}, peer
        time.sleep(0.5)
    peer.close()
    raise TimeoutError("Authoritative terminal deadline")


def execute_controller_job(root: Path, plan: dict, job: dict, directory: Path,
                           helper: Path, journal: Journal, *, target_utc_ns: int | None = None) -> dict:
    require(job["submission_path"] == "controller_disconnect", "Controller path mismatch")
    directory.mkdir(mode=0o700)
    stop = threading.Event()
    console = ConsoleObserver(journal, stop, PICO_ACCEPTED_BOOT, FIRMWARE_SOURCE)
    usb = UsbStatusObserver(journal, stop, uuid.uuid4().hex, 116,
                            PICO_ACCEPTED_BOOT, observe_clock=True)
    peer = NetworkPeer(root, journal)
    capture = None
    browser = None
    start_events = len(peer.events)
    before = None
    try:
        console.start()
        usb.start()
        wait_observer_readiness(console, usb)
        peer.connect()
        status = peer.ask("STATUS")
        clock = peer.ask("GET_CLOCK")
        require(
            status["boot_id"] == PICO_ACCEPTED_BOOT
            and status["output_active"] is False
            and status["owner_id"] is None
            and clock["state"] == "synchronized"
            and clock["leap"] == "normal"
            and int(clock["uncertainty_ns"]) <= 500_000_000,
            "Controller pre-ARM authority/clock",
        )
        before = status
        # Chromium may need longer than the ARM lead to initialize, so make it
        # ready before starting the bounded receiver span.
        duration = job["planned_duration_ns"] / 1e9
        browser = BrowserWatch(root, directory / "browser",
                               job["expected_job"]["job_id"], duration + 70, journal)
        browser.start()
        capture_seconds = ((max(1.0, (target_utc_ns - time.time_ns()) / 1e9) + 3.0)
                           if target_utc_ns is not None else 18.0) + duration
        capture = Capture(root, directory / "capture", helper,
                          job["nominal_frequency_hz"], capture_seconds, journal)
        capture.start()
        browser.pause()
        arm_clock = peer.ask("GET_CLOCK")
        require(arm_clock["state"] == "synchronized" and arm_clock["leap"] == "normal"
                and int(arm_clock["uncertainty_ns"]) <= 500_000_000,
                "Fresh pre-ARM clock")
        # Establish every observer while the target is authoritatively empty.
        # Cross-principal page initialization before ARM is therefore observed
        # without allowing its startup lifecycle to invalidate a Loaded job.
        owner = peer.session
        peer.ask("CLAIM", {"owner_id": owner, "lease_ms": 60000})
        loaded = peer.ask("LOAD", job["expected_job"])
        require(loaded["job_id"] == job["expected_job"]["job_id"], "LOAD job identity")
        target = target_utc_ns or (
            (int(arm_clock["utc_now_ns"]) + MINIMUM_ARM_LEAD_NS + 999_999_999)
            // 1_000_000_000
            * 1_000_000_000
        )
        require(target - int(arm_clock["utc_now_ns"]) >= MINIMUM_ARM_LEAD_NS, "ARM lead")
        peer.ask(
            "ARM",
            {
                "job_id": job["expected_job"]["job_id"],
                "start_utc_ns": str(target),
                "max_start_uncertainty_ns": "500000000",
            },
        )
        armed_at = time.monotonic_ns()
        browser.resume()
        session, request_number = peer.session, peer.request_number
        peer.close()
        journal.emit(
            "controller_transport_disconnected",
            {"job_id": job["expected_job"]["job_id"], "after_arm_monotonic_ns": armed_at},
        )
        terminal, peer = wait_for_terminal(
            root,
            journal,
            session,
            request_number,
            job["expected_job"]["job_id"],
            job["planned_duration_ns"] / 1e9,
        )
        peer.ask("RELEASE")
        released = peer.ask("STATUS")
        require(
            released["owner_id"] is None and released["output_active"] is False,
            "Controller release authority",
        )
        capture_value = capture.finish()
        browser_value = browser.finish()
        stop.set()
        console.join(10)
        usb.join(10)
        require(
            not console.is_alive()
            and not usb.is_alive()
            and console.failure is None
            and usb.failure is None
            and console.latest is not None
            and usb.latest is not None,
            "Independent observer health",
        )
        resource_gate(console.latest, PICO_ACCEPTED_BOOT, FIRMWARE_SOURCE)
        validate_usb_completion(usb, job["expected_job"]["job_id"])
        result = {
            "schema": "phase11.6-job-result-v1",
            "plan_sha256": digest(plan),
            "job_id": job["id"],
            "wtp_job_id": job["expected_job"]["job_id"],
            "band": job["band"],
            "mode": job["mode"],
            "submission_path": job["submission_path"],
            "planned_duration_ns": job["planned_duration_ns"],
            "target_utc_ns": target,
            "loaded_adjustments": loaded.get("adjustments"),
            "pre_status": before,
            "terminal": terminal,
            "released_status": released,
            "controller_disconnect_after_arm": True,
            "observer": {
                "console_samples": len(console.starts),
                "usb_status_samples": len(usb.starts),
                "usb_states": sorted(usb.states),
                "usb_event_states": sorted(usb.event_states),
                "console_final": console.latest,
                "usb_final": usb.latest,
            },
            "capture": capture_value,
            "browser": browser_value,
            "network_events": peer.events[start_events:],
            "disposition": "CAPTURED_REQUIRES_ANALYSIS",
        }
        save(directory / "result.json", result)
        return result
    finally:
        stop.set()
        peer.close()
        if console.is_alive():
            console.join(10)
        if usb.is_alive():
            usb.join(10)
        if capture is not None:
            capture.terminate()
        if browser is not None:
            browser.terminate()


def execute_browser_job(root: Path, plan: dict, job: dict, directory: Path,
                        helper: Path, journal: Journal,
                        *, target_utc_ns: int | None = None) -> dict:
    """Execute one browser-owned raw or compact job with independent observers."""
    require(job["submission_path"] in {"browser_raw", "browser_compact"},
            "Browser path mismatch")
    directory.mkdir(mode=0o700)
    stop = threading.Event()
    console = ConsoleObserver(journal, stop, PICO_ACCEPTED_BOOT, FIRMWARE_SOURCE)
    usb = UsbStatusObserver(journal, stop, uuid.uuid4().hex, 116,
                            PICO_ACCEPTED_BOOT, observe_clock=True)
    duration = job["planned_duration_ns"] / 1e9
    browser = BrowserSubmit(root, directory / "browser", job, duration + 25, journal)
    capture = None
    try:
        console.start(); usb.start()
        wait_observer_readiness(console, usb)
        status, clock = usb.latest, usb.clock
        require(status["boot_id"] == PICO_ACCEPTED_BOOT
                and status["output_active"] is False and status["owner_id"] is None
                and clock["state"] == "synchronized" and clock["leap"] == "normal"
                and int(clock["uncertainty_ns"]) <= 500_000_000,
                "Browser pre-submit authority/clock")
        browser.start()
        # Retain the whole browser preparation interval as leading quiet plus
        # enough trailing quiet to prove output returned inactive.
        capture_seconds = duration + BROWSER_ARM_LEAD_NS / 1e9 + 10
        capture = Capture(root, directory / "capture", helper,
                          job["nominal_frequency_hz"], capture_seconds, journal)
        capture.start()
        clock_peer = NetworkPeer(root, journal).connect()
        fresh = clock_peer.ask("GET_CLOCK")
        empty = clock_peer.ask("STATUS")
        clock_peer.close()
        require(empty["owner_id"] is None and empty["output_active"] is False
                and fresh["state"] == "synchronized"
                and int(fresh["uncertainty_ns"]) <= 500_000_000,
                "Fresh browser submit clock/authority")
        target = target_utc_ns or (
            (int(fresh["utc_now_ns"]) + BROWSER_ARM_LEAD_NS + 999_999_999)
            // 1_000_000_000 * 1_000_000_000
        )
        require(target - int(fresh["utc_now_ns"]) >= BROWSER_ARM_LEAD_NS,
                "Browser ARM lead")
        browser.submit(target)
        browser_value = browser.finish()
        capture_value = capture.finish()
        final_peer = NetworkPeer(root, journal).connect()
        final = final_peer.ask("STATUS")
        final_peer.close()
        expected_id = job["expected_job"]["job_id"]
        records = [record for record in final.get("terminal_records", [])
                   if record.get("job_id") == expected_id]
        require(records and records[-1]["state"] == "complete"
                and records[-1]["output_active"] is False
                and final["owner_id"] is None and final["output_active"] is False,
                "Browser authoritative completion/release")
        stop.set(); console.join(10); usb.join(10)
        require(not console.is_alive() and not usb.is_alive()
                and console.failure is None and usb.failure is None
                and console.latest is not None and usb.latest is not None,
                "Browser independent observer health")
        resource_gate(console.latest, PICO_ACCEPTED_BOOT, FIRMWARE_SOURCE)
        validate_usb_completion(usb, expected_id)
        result = {
            "schema": "phase11.6-job-result-v1", "plan_sha256": digest(plan),
            "job_id": job["id"], "wtp_job_id": expected_id, "band": job["band"],
            "mode": job["mode"], "submission_path": job["submission_path"],
            "planned_duration_ns": job["planned_duration_ns"],
            "target_utc_ns": target, "terminal_records": records,
            "released_status": final, "controller_disconnect_after_arm": False,
            "observer": {"console_samples": len(console.starts),
                         "usb_status_samples": len(usb.starts),
                         "usb_states": sorted(usb.states),
                         "usb_event_states": sorted(usb.event_states),
                         "console_final": console.latest, "usb_final": usb.latest},
            "capture": capture_value, "browser": browser_value,
            "disposition": "CAPTURED_REQUIRES_ANALYSIS",
        }
        save(directory / "result.json", result)
        return result
    finally:
        stop.set()
        if console.is_alive(): console.join(10)
        if usb.is_alive(): usb.join(10)
        if capture is not None: capture.terminate()
        browser.terminate()


def execute_production_job(root: Path, plan: dict, job: dict, directory: Path,
                           helper: Path, binary: Path, journal: Journal,
                           *, port: int = 31_425,
                           corrective_clock_refinement: bool = False) -> dict:
    """Execute one actual WsprryPi-produced job without installing the candidate."""
    require(job["submission_path"] == "production", "Production path mismatch")
    directory.mkdir(mode=0o700)
    stop = threading.Event()
    console = ConsoleObserver(journal, stop, PICO_ACCEPTED_BOOT, FIRMWARE_SOURCE)
    usb = UsbStatusObserver(journal, stop, uuid.uuid4().hex, 116,
                            PICO_ACCEPTED_BOOT, observe_clock=True)
    duration = job["planned_duration_ns"] / 1e9
    browser = BrowserWatch(root, directory / "browser", None, duration + 190,
                           journal, refresh_interval_s=10.0)
    capture = None
    process = None
    output = None
    binding = None
    host_rows = []
    try:
        require(binary.is_file() and os.access(binary, os.X_OK),
                "Reviewed production candidate executable")
        paused = (root / "installed-paused.txt").read_text()
        require("MainPID=0" in paused and "ActiveState=inactive" in paused,
                "Installed WsprryPi service is not authoritatively paused")
        console.start()
        usb.start()
        if corrective_clock_refinement:
            wait_observer_readiness(
                console,
                usb,
                maximum_uncertainty_ns=500_000_000,
                minimum_sync_age_ns=CORRECTIVE_MINIMUM_SYNC_AGE_NS,
                maximum_sync_age_ns=CORRECTIVE_MAXIMUM_SYNC_AGE_NS,
            )
        else:
            wait_observer_readiness(console, usb)
        initial, clock = usb.latest, usb.clock
        require(initial["owner_id"] is None and initial["output_active"] is False
                and clock["state"] == "synchronized" and clock["leap"] == "normal"
                and int(clock["uncertainty_ns"]) <= 500_000_000,
                "Production preflight authority/clock")
        browser.start()
        # The accepted resource/contention campaign used human-paced browser
        # actions.  Quiesce page refreshes during the production client's
        # CLAIM/LOAD/ARM admission window, then observe the armed/running job.
        browser.pause()
        # WSPR waits for a two-minute boundary.  Select a boundary at least 35
        # seconds out so the application, receiver and observers all precede
        # its LOAD/ARM preparation.  Keyed CLI transients use the application's
        # bounded preparation lead immediately after startup.
        predicted_target = None
        leading = 28.0
        if job["mode"] == "WSPR":
            predicted_target = (
                (time.time_ns() + 35_000_000_000 + 119_999_999_999)
                // 120_000_000_000 * 120_000_000_000
            )
            leading = max(28.0, (predicted_target - time.time_ns()) / 1e9 + 3.0)
        capture = Capture(
            root, directory / "capture", helper, job["nominal_frequency_hz"],
            leading + duration + 12.0, journal,
        )
        capture.start()
        ini = render_production_ini(root, directory, job, port)
        tls_log = directory / "production-tls.bin"
        command = production_command(binary, ini, job)
        environment = dict(
            os.environ,
            TZ="UTC",
            LD_PRELOAD=str(root / "observer.so"),
            PHASE115_TLS_LOG=str(tls_log),
        )
        openssl = root / "production-openssl.cnf"
        if openssl.is_file():
            environment["OPENSSL_CONF"] = str(openssl)
        output = (directory / "production.log").open("xb")
        process = subprocess.Popen(
            command, cwd=directory, stdout=output, stderr=subprocess.STDOUT,
            env=environment,
        )
        journal.emit(
            "production_start",
            {"pid": process.pid, "argv": command, "binary_sha256": sha256(binary),
             "ini_sha256": sha256(ini), "observer_sha256": sha256(root / "observer.so"),
             "predicted_target_utc_ns": predicted_target},
        )
        ready_deadline = time.monotonic() + 50
        while time.monotonic() < ready_deadline:
            require(process.poll() is None, "Production process exited before binding")
            try:
                value = host_status(port, journal)["host"]
            except OSError:
                time.sleep(0.1)
                continue
            host_rows.append(value)
            identity = value.get("identity") or {}
            require(not identity or (
                identity.get("device_id") == PICO_DEVICE_ID
                and identity.get("boot_id") == PICO_ACCEPTED_BOOT
            ), "Production host identity")
            if value.get("job_id") and int(value.get("start_utc_ns", "0")) > 0:
                binding = {
                    "job_id": value["job_id"],
                    "owner_id": value["owner_id"],
                    "session_id": value["session_id"],
                    "start_utc_ns": int(value["start_utc_ns"]),
                    "dispatch_utc_ns": int(value["dispatch_utc_ns"]),
                    "phase": value["phase"],
                }
                break
            time.sleep(0.1)
        require(binding is not None, "Production binding deadline")
        browser.resume()
        if predicted_target is not None:
            require(binding["start_utc_ns"] == predicted_target
                    and binding["start_utc_ns"] % 120_000_000_000 == 0,
                    "Production WSPR slot mapping")
        journal.emit("production_binding", binding)
        deadline = time.monotonic() + duration + leading + 30
        report = None
        production_returncode = None
        while time.monotonic() < deadline:
            production_returncode = process.poll()
            if production_returncode is not None:
                require(production_returncode == 0,
                        "Production process failed after binding")
                journal.emit(
                    "production_orderly_exit_after_binding",
                    {"returncode": production_returncode,
                     "last_host_phase": host_rows[-1].get("phase")},
                )
                break
            try:
                value = host_status(port, journal)["host"]
            except OSError as error:
                # The application intentionally stops its HTTP listener while
                # the child is still crossing the observable process-exit
                # boundary.  Accept that narrow race only for an already-bound
                # child that reaches a clean exit; final Pico terminal evidence
                # below remains authoritative for RF safety and completion.
                try:
                    production_returncode = process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    raise error
                require(production_returncode == 0,
                        "Production listener closed before failed child exit")
                journal.emit(
                    "production_listener_closed_at_orderly_exit",
                    {"returncode": production_returncode,
                     "error_type": type(error).__name__,
                     "last_host_phase": host_rows[-1].get("phase")},
                )
                break
            host_rows.append(value)
            require(value.get("recovery_required") is False
                    and value.get("safety_fault") is False,
                    "Production host safety state")
            candidate = value.get("last_report") or {}
            remote = value.get("remote") or {}
            if candidate.get("job_id") == binding["job_id"]:
                require(candidate.get("outcome") != "failed", "Production job failure")
                if (candidate.get("outcome") == "complete"
                        and remote.get("output_active") is False
                        and value.get("owns") is False):
                    report = candidate
                    break
            time.sleep(0.2)
        require(report is not None or production_returncode == 0,
                "Production completion report/exit deadline")
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=15)
        require(process.returncode == 0, "Production orderly exit")
        output.close()
        output = None
        written, received, wire = _tls_messages(root, tls_log)
        requests = [value for value in written if value.get("type") == "request"]
        require(requests and len({value["request_id"] for value in requests}) == len(requests)
                and len({value["session_id"] for value in requests}) == 1,
                "Production request identity")
        mutations = [value for value in requests
                     if value["op"] in {"CLAIM", "LOAD", "ARM", "ABORT", "RELEASE"}]
        require([value["op"] for value in mutations] ==
                ["CLAIM", "LOAD", "ARM", "RELEASE"],
                "Production mutation order/count")
        load, arm = mutations[1], mutations[2]
        expected = copy.deepcopy(job["expected_job"])
        expected["job_id"] = binding["job_id"]
        require(load["body"] == expected
                and arm["body"]["job_id"] == binding["job_id"]
                and int(arm["body"]["start_utc_ns"]) == binding["start_utc_ns"],
                "Actual production LOAD/ARM differs from frozen job")
        for request in mutations:
            matches = [value for value in received
                       if value.get("type") == "response"
                       and value.get("request_id") == request["request_id"]
                       and value.get("op") == request["op"]]
            require(len(matches) == 1 and matches[0].get("ok") is True,
                    "Production mutation response")
        capture_value = capture.finish()
        browser_value = browser.finish()
        final_peer = NetworkPeer(root, journal).connect()
        final = final_peer.ask("STATUS")
        final_peer.close()
        records = [item for item in final.get("terminal_records", [])
                   if item.get("job_id") == binding["job_id"]]
        require(records and records[-1]["state"] == "complete"
                and records[-1]["output_active"] is False
                and final["owner_id"] is None and final["output_active"] is False,
                "Production authoritative terminal/release")
        stop.set()
        console.join(10)
        usb.join(10)
        require(not console.is_alive() and not usb.is_alive()
                and console.failure is None and usb.failure is None
                and console.latest is not None and usb.latest is not None,
                "Production independent observer health")
        resource_gate(console.latest, PICO_ACCEPTED_BOOT, FIRMWARE_SOURCE)
        validate_usb_completion(usb, binding["job_id"])
        refinement = None
        if corrective_clock_refinement:
            rows = [json.loads(line) for line in journal.path.read_text().splitlines()]
            refinement = armed_clock_refinement(rows, binding["job_id"])
        result = {
            "schema": "phase11.6-job-result-v1", "plan_sha256": digest(plan),
            "job_id": job["id"], "wtp_job_id": binding["job_id"],
            "band": job["band"], "mode": job["mode"],
            "submission_path": "production",
            "planned_duration_ns": job["planned_duration_ns"],
            "target_utc_ns": binding["start_utc_ns"], "binding": binding,
            "production_binary_sha256": sha256(binary),
            "production_ini_sha256": sha256(ini), "production_report": report,
            "production_returncode": process.returncode,
            "tls_wire": wire, "tls_mutations": [value["op"] for value in mutations],
            "actual_load": load["body"], "terminal_records": records,
            "released_status": final,
            "observer": {"console_samples": len(console.starts),
                         "usb_status_samples": len(usb.starts),
                         "usb_states": sorted(usb.states),
                         "usb_event_states": sorted(usb.event_states),
                         "console_final": console.latest, "usb_final": usb.latest},
            "clock_refinement": refinement,
            "capture": capture_value, "browser": browser_value,
            "disposition": "CAPTURED_REQUIRES_ANALYSIS",
        }
        save(directory / "result.json", result)
        return result
    finally:
        stop.set()
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if output is not None and not output.closed:
            output.close()
        if console.is_alive():
            console.join(10)
        if usb.is_alive():
            usb.join(10)
        if capture is not None:
            capture.terminate()
        browser.terminate()
