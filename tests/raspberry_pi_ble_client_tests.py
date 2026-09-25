#!/usr/bin/env python3
"""Deterministic protocol and safety tests for the BlueZ/Raspberry Pi client."""

import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
VECTORS = json.loads((ROOT / "docs/protocol/Field-GATT-v1-vectors.json").read_text())
SPEC = importlib.util.spec_from_file_location("wsprrypico_ble", ROOT / "scripts/wsprrypico_ble.py")
ble = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ble)

DEVICE = "0123456789abcdef0123456789abcdef"
BOOT = "fedcba9876543210fedcba9876543210"
ADDRESS = "2C:CF:67:62:76:68"


def profile(device=DEVICE):
    return {
        "version": 1,
        "device_id": device,
        "wifi": {"ssid": "test-net", "password": "wifi-secret", "time_server": "time.local"},
        "tls": {
            "hostname": "PICO-A.LOCAL.",
            "port": 443,
            "server_certificate": "-----BEGIN CERTIFICATE-----\nAA==\n-----END CERTIFICATE-----\n",
            "server_private_key": "-----BEGIN PRIVATE KEY-----\nAA==\n-----END PRIVATE KEY-----\n",
            "client_ca": "-----BEGIN CERTIFICATE-----\nAA==\n-----END CERTIFICATE-----\n",
        },
    }


def profile_at_serialized_size(target):
    candidate = profile()
    encoded = ble.canonical_profile(candidate)
    needed = target - len(encoded)
    encoded[:] = b"\x00" * len(encoded)
    if needed < 0:
        raise AssertionError("target smaller than base profile")
    for field, maximum in (
        ("server_certificate", 3072),
        ("server_private_key", 2048),
        ("client_ca", 3072),
    ):
        value = candidate["tls"][field]
        count = min(needed, maximum - len(value))
        marker = value.rfind("\n-----END")
        candidate["tls"][field] = value[:marker] + "X" * count + value[marker:]
        needed -= count
    if needed:
        raise AssertionError("target exceeds field capacities")
    return candidate


class FakeBackend:
    def __init__(self, device=DEVICE):
        self.device = device
        self.connected = False
        self.closed = False
        self.callbacks = {}
        self.command_receiver = ble.FrameReceiver(ble.MAX_COMMAND_BYTES)
        self.wtp_receiver = ble.WtpReceiver()
        self.operations = []
        self.profile = bytearray()
        self.generation = 7
        self.fail_write = False
        self.write_responses = []
        self.confirmation_required = False
        self.confirmation_ready = True
        self.force_step_up_not_ready = False
        self.drop_step_up_status = False
        self.apply_generation_response = None
        self.field_session = None
        self.step_up = None

    def connect(self, address, service, timeout, allow_pairing=True):
        if address != ADDRESS or service != ble.UUIDS["service"] or timeout <= 0:
            raise AssertionError("unexpected connection parameters")
        self.allow_pairing = allow_pairing
        self.connected = True

    def read(self, uuid):
        if uuid != ble.UUIDS["identity"]:
            raise AssertionError("unexpected read")
        return json.dumps({"device_id": self.device, "generation": self.generation}).encode()

    def start_notify(self, uuid, callback):
        self.callbacks[uuid] = callback

    def _field_reply(self, request, **fields):
        response = {"version": 1, "request_id": request["request_id"], "ok": True}
        response.update(fields)
        payload = json.dumps(response, separators=(",", ":")).encode()
        for frame in ble.gatt_frames(payload):
            self.callbacks[ble.UUIDS["status"]](bytes(frame))

    def _handle_field(self, request):
        operation = request["operation"]
        self.operations.append(operation)
        if operation == "authorize":
            if request["password"] != "app-secret":
                self._field_reply(request, ok=False, error="authentication_required")
            else:
                self.field_session = request["session_id"]
                self._field_reply(request, generation=self.generation)
        elif operation == "identify":
            self._field_reply(request, identified=True)
        elif operation == "field_status":
            self._field_reply(
                request,
                time_source="controller",
                time_age_ns="12",
                time_uncertainty_ns="34",
                time_disagreement=False,
                indicator="off",
                indicator_fault=False,
            )
        elif operation == "time_challenge":
            self._field_reply(request, nonce=request["nonce"], sampled_monotonic_ns="1")
        elif operation == "time_submit":
            self._field_reply(request, accepted=True)
        elif operation == "open":
            self.profile.clear()
            self.step_up = None
            self._field_reply(request, generation=self.generation, activation="unchanged")
        elif operation == "write":
            if self.fail_write:
                self._field_reply(request, ok=False, error="storage_fault")
            else:
                chunk = __import__("base64").b64decode(request["payload"], validate=True)
                if request["offset"] != len(self.profile):
                    raise AssertionError("noncontiguous profile")
                self.profile.extend(chunk)
                self._field_reply(request, generation=self.generation, activation="unchanged")
        elif operation == "profile_step_up":
            if (
                request["password"] != "app-secret"
                or request["session_id"] != self.field_session
            ):
                self._field_reply(request, ok=False, error="authentication_required")
            else:
                self.step_up = (
                    request["session_id"],
                    request["profile_session_id"],
                    request["apply_request_id"],
                    request["expected_generation"],
                )
                self._field_reply(
                    request,
                    confirmation_required=self.confirmation_required,
                    ready=(
                        False
                        if self.force_step_up_not_ready
                        else not self.confirmation_required or self.confirmation_ready
                    ),
                )
        elif operation == "profile_step_up_status":
            if self.drop_step_up_status:
                return
            if (
                self.step_up is None
                or request["session_id"] != self.step_up[0]
                or request["apply_request_id"] != self.step_up[2]
            ):
                self._field_reply(request, ok=False, error="authentication_required")
            else:
                self._field_reply(
                    request,
                    confirmation_required=self.confirmation_required,
                    ready=(
                        False
                        if self.force_step_up_not_ready
                        else not self.confirmation_required or self.confirmation_ready
                    ),
                )
        elif operation == "apply":
            expected = (
                self.field_session,
                request["session_id"],
                request["request_id"],
                request["expected_generation"],
            )
            if self.step_up != expected:
                self._field_reply(request, ok=False, error="authentication_required")
            else:
                self.step_up = None
                self.generation += 1
                generation = (
                    self.generation
                    if self.apply_generation_response is None
                    else self.apply_generation_response
                )
                self._field_reply(request, generation=generation, activation="pending_delivery")
        elif operation == "cancel":
            self.step_up = None
            self._field_reply(request, generation=self.generation, activation="unchanged")
        else:
            raise AssertionError(f"unexpected operation {operation}")

    def _handle_wtp(self, request):
        if request["op"] == "HELLO":
            body = {
                "selected_version": "WTP/1",
                "device_id": DEVICE,
                "boot_id": BOOT,
                "product": "WsprryPico",
                "firmware_version": "test",
            }
        elif request["op"] == "STATUS":
            body = {
                "boot_id": BOOT,
                "state": "empty",
                "output_active": False,
                "owner_id": None,
                "job_id": None,
                "terminal_records": [],
            }
        else:
            raise AssertionError("unexpected WTP operation")
        response = ble.wtp_frame({
            "type": "response",
            "protocol": "WTP/1",
            "session_id": request["session_id"],
            "request_id": request["request_id"],
            "op": request["op"],
            "ok": True,
            "body": body,
        })
        for offset in range(0, len(response), 19):
            self.callbacks[ble.UUIDS["wtpStatus"]](bytes(response[offset:offset + 19]))

    def write(self, uuid, value, response=True):
        if uuid == ble.UUIDS["command"]:
            self.write_responses.append(response)
            complete = self.command_receiver.receive(value)
            if complete is not None:
                self._handle_field(json.loads(complete))
        elif uuid == ble.UUIDS["wtpCommand"]:
            for request in self.wtp_receiver.receive(value):
                self._handle_wtp(request)
        else:
            raise AssertionError("unexpected characteristic")

    def pump(self, seconds):
        del seconds

    def close(self):
        self.closed = True
        self.connected = False


class FramingTests(unittest.TestCase):
    def test_gatt_boundaries_and_order(self):
        for size, expected in ((1, 1), (60, 1), (61, 2), (960, 16)):
            payload = bytes((index % 251 for index in range(size)))
            frames = ble.gatt_frames(payload)
            self.assertEqual(len(frames), expected)
            receiver = ble.FrameReceiver(960)
            self.assertEqual(b"".join(filter(None, (receiver.receive(frame) for frame in frames))), payload)
        with self.assertRaisesRegex(ble.ClientError, "frame_oversize"):
            ble.gatt_frames(bytes(961))
        receiver = ble.FrameReceiver(256)
        with self.assertRaisesRegex(ble.ClientError, "frame_order"):
            receiver.receive(bytes((1, 0, 1, 1, 65)))

    def test_wtp_fragment_crc_and_bounds(self):
        message = {"type": "request", "protocol": "WTP/1", "body": {"value": "x" * 100}}
        frame = ble.wtp_frame(message)
        receiver = ble.WtpReceiver()
        decoded = []
        for offset in range(0, len(frame), 7):
            decoded.extend(receiver.receive(frame[offset:offset + 7]))
        self.assertEqual(decoded, [message])
        corrupt = ble.wtp_frame(message)
        corrupt[-1] ^= 1
        with self.assertRaisesRegex(ble.ClientError, "wtp_crc"):
            ble.WtpReceiver().receive(corrupt)
        with self.assertRaisesRegex(ble.ClientError, "wtp_frame_invalid"):
            ble.WtpReceiver().receive(b"X" * 16)


class ClientTests(unittest.TestCase):
    def connected(self):
        backend = FakeBackend()
        client = ble.Client(backend, timeout=0.1)
        identity = client.connect(ADDRESS, DEVICE)
        self.assertEqual(identity, {"device_id": DEVICE, "generation": 7})
        return backend, client

    def test_exact_identity_and_cleanup(self):
        backend = FakeBackend(device="1" * 32)
        client = ble.Client(backend, timeout=0.1)
        with self.assertRaisesRegex(ble.ClientError, "wrong_device"):
            client.connect(ADDRESS, DEVICE)
        self.assertTrue(backend.closed)
        for bad in ("", "2c:cf:67:62:76:6z", "2C:CF:67:62:76"):
            with self.assertRaisesRegex(ble.ClientError, "bluetooth_address"):
                ble.normalize_address(bad)
        for bad in (0, 121, float("inf"), float("nan")):
            with self.assertRaisesRegex(ble.ClientError, "timeout"):
                ble.Client(FakeBackend(), timeout=bad)
        for bad in (0, 26, float("inf"), float("nan")):
            with self.assertRaisesRegex(ble.ClientError, "confirmation_timeout"):
                ble.Client(FakeBackend(), confirmation_timeout=bad)

    def test_pairing_authorization_is_exact(self):
        expected = "/org/bluez/hci0/dev_2C_CF_67_62_76_68"
        self.assertTrue(ble.pairing_request_allowed(expected, expected))
        self.assertTrue(
            ble.pairing_request_allowed(expected, expected, ble.UUIDS["service"].upper())
        )
        self.assertFalse(ble.pairing_request_allowed(expected + "_other", expected))
        self.assertFalse(ble.pairing_request_allowed(expected, expected, ble.UUIDS["identity"]))

    def test_inspect_never_creates_a_provisional_pairing(self):
        backend = FakeBackend()
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                ble.run(
                    ["--address", ADDRESS, "--device-id", DEVICE, "inspect"],
                    backend_factory=lambda adapter: backend,
                ),
                0,
            )
        self.assertFalse(backend.allow_pairing)
        self.assertEqual(json.loads(output.getvalue())["device_id"], DEVICE)
        self.assertTrue(backend.closed)

    def test_unmatched_notification_cannot_satisfy_request(self):
        backend, client = self.connected()
        stale = json.dumps({"version": 1, "request_id": "9" * 32, "ok": True}).encode()
        for frame in ble.gatt_frames(stale):
            backend.callbacks[ble.UUIDS["status"]](bytes(frame))
        self.assertEqual(client._field_responses, {})
        client.authorize("app-secret")
        self.assertFalse(client._field_pending)
        self.assertEqual(client._field_responses, {})

    def test_remote_error_is_a_bounded_identifier(self):
        self.assertEqual(ble.remote_error("storage_fault"), "storage_fault")
        self.assertEqual(ble.remote_error("BUSY"), "BUSY")
        for value in ("", "bad-value", "bad\nvalue", "x" * 65, {"code": "BUSY"}):
            self.assertEqual(ble.remote_error(value), "device_rejected")

    def test_authorized_field_workflow(self):
        backend, client = self.connected()
        client.authorize("app-secret")
        client.identify()
        status = client.field_status()
        self.assertEqual(status["time_source"], "controller")
        client.synchronize_time(1_750_000_000_000)
        self.assertEqual(
            backend.operations,
            ["authorize", "identify", "field_status", "time_challenge", "time_submit"],
        )
        self.assertIn(False, backend.write_responses)
        with self.assertRaisesRegex(ble.ClientError, "local_password") as caught:
            ble.Client(FakeBackend()).authorize("secret")
        self.assertNotIn("secret", str(caught.exception))

    def test_wtp_hello_and_status_use_unchanged_stream(self):
        _, client = self.connected()
        client.authorize("app-secret")
        hello = client.enable_local_control()
        self.assertEqual(hello["device_id"], DEVICE)
        self.assertEqual(client.wtp_status(hello["boot_id"])["state"], "empty")
        with self.assertRaisesRegex(ble.ClientError, "wtp_status_response"):
            client.wtp_status("0" * 32)

    def test_atomic_profile_and_cancel_on_failure(self):
        backend, client = self.connected()
        client.authorize("app-secret")
        encoded = ble.canonical_profile(profile())
        retained = bytes(encoded)
        self.assertEqual(client.provision(encoded, "app-secret"), 8)
        self.assertTrue(all(byte == 0 for byte in encoded))
        self.assertEqual(bytes(backend.profile), retained)
        required = VECTORS["profile_apply"]["required_order"]
        profile_operations = [operation for operation in backend.operations if operation in required]
        self.assertEqual(profile_operations[0], "open")
        self.assertEqual(profile_operations[-2:], ["profile_step_up", "apply"])
        backend.fail_write = True
        rejected = ble.canonical_profile(profile())
        with self.assertRaisesRegex(ble.ClientError, "storage_fault"):
            client.provision(rejected, "app-secret")
        self.assertEqual(backend.operations[-1], "cancel")
        self.assertTrue(all(byte == 0 for byte in rejected))

        backend.fail_write = False
        wrong_password = ble.canonical_profile(profile())
        with self.assertRaisesRegex(ble.ClientError, "authentication_required"):
            client.provision(wrong_password, "wrong-pass")
        self.assertEqual(backend.operations[-1], "cancel")
        self.assertTrue(all(byte == 0 for byte in wrong_password))

    def test_profile_confirmation_and_apply_binding(self):
        backend, client = self.connected()
        client.authorize("app-secret")
        backend.confirmation_required = True
        backend.confirmation_ready = False
        confirmations = []

        def confirm(device_id):
            confirmations.append(device_id)
            backend.confirmation_ready = True

        encoded = ble.canonical_profile(profile())
        self.assertEqual(client.provision(encoded, "app-secret", confirm), 8)
        self.assertEqual(confirmations, [DEVICE])
        self.assertIn("profile_step_up_status", backend.operations)

        direct_apply = {
            "version": 1,
            "operation": "apply",
            "request_id": "a" * 32,
            "session_id": "b" * 32,
            "device_id": DEVICE,
            "expected_generation": client.generation,
        }
        with self.assertRaisesRegex(ble.ClientError, "authentication_required"):
            client.exchange(direct_apply)

        invalid_backend, invalid_client = self.connected()
        invalid_client.authorize("app-secret")
        invalid_backend.force_step_up_not_ready = True
        invalid = ble.canonical_profile(profile())
        with self.assertRaisesRegex(ble.ClientError, "profile_step_up_response"):
            invalid_client.provision(invalid, "app-secret")
        self.assertEqual(invalid_backend.operations[-1], "cancel")

        timeout_backend = FakeBackend()
        timeout_client = ble.Client(
            timeout_backend, timeout=0.1, confirmation_timeout=0.001
        )
        timeout_client.connect(ADDRESS, DEVICE)
        timeout_client.authorize("app-secret")
        timeout_backend.confirmation_required = True
        timeout_backend.confirmation_ready = False
        timeout_backend.drop_step_up_status = True
        pending = ble.canonical_profile(profile())
        with self.assertRaisesRegex(ble.ClientError, "confirmation_timeout"):
            timeout_client.provision(pending, "app-secret")
        self.assertEqual(timeout_backend.operations[-1], "cancel")
        self.assertTrue(all(byte == 0 for byte in pending))

        malformed_backend, malformed_client = self.connected()
        malformed_client.authorize("app-secret")
        malformed_backend.apply_generation_response = "invalid"
        committed = ble.canonical_profile(profile())
        with self.assertRaisesRegex(ble.ClientError, "generation"):
            malformed_client.provision(committed, "app-secret")
        self.assertEqual(malformed_backend.operations[-1], "apply")
        self.assertTrue(all(byte == 0 for byte in committed))

    def test_maximum_profile_transfer(self):
        backend, client = self.connected()
        client.authorize("app-secret")
        encoded = ble.canonical_profile(profile_at_serialized_size(ble.MAX_PROFILE_BYTES))
        self.assertEqual(len(encoded), VECTORS["limits"]["max_profile_bytes"])
        self.assertEqual(client.provision(encoded, "app-secret"), 8)
        self.assertEqual(len(backend.profile), VECTORS["limits"]["max_profile_bytes"])
        self.assertEqual(
            backend.operations.count("write"),
            VECTORS["limits"]["max_profile_bytes"] // VECTORS["limits"]["max_fragment_bytes"],
        )

    def test_second_password_prompt_failure_scrubs_loaded_profile(self):
        backend = FakeBackend()
        loaded = ble.canonical_profile(profile())
        with (
            patch.object(ble, "load_profile_file", return_value=loaded),
            patch.object(ble.getpass, "getpass", side_effect=["app-secret", EOFError]),
        ):
            with self.assertRaisesRegex(ble.ClientError, "password_input"):
                ble.run(
                    [
                        "--address",
                        ADDRESS,
                        "--device-id",
                        DEVICE,
                        "provision",
                        "--profile",
                        "/unused/profile.json",
                    ],
                    backend_factory=lambda adapter: backend,
                )
        self.assertTrue(all(byte == 0 for byte in loaded))
        self.assertTrue(backend.closed)


class ProfileFileTests(unittest.TestCase):
    def test_canonical_validation_and_device_binding(self):
        encoded = ble.canonical_profile(profile())
        parsed = json.loads(encoded)
        self.assertEqual(parsed["tls"]["hostname"], "pico-a.local")
        changed = profile()
        changed["extra"] = True
        with self.assertRaisesRegex(ble.ClientError, "profile_format"):
            ble.canonical_profile(changed)
        changed = profile("A" * 32)
        with self.assertRaisesRegex(ble.ClientError, "device_id"):
            ble.canonical_profile(changed)

    def test_frozen_profile_transfer_boundaries(self):
        self.assertEqual(VECTORS["protocol"], "Field-GATT/1")
        self.assertEqual(VECTORS["status"], "frozen")
        for entry in VECTORS["profile_transfer_cases"]:
            candidate = profile_at_serialized_size(entry["bytes"])
            if entry["result"] == "accepted":
                encoded = ble.canonical_profile(candidate)
                self.assertEqual(len(encoded), entry["bytes"])
                encoded[:] = b"\x00" * len(encoded)
            else:
                with self.assertRaisesRegex(ble.ClientError, "profile_oversize"):
                    ble.canonical_profile(candidate)

    def test_owner_only_regular_absolute_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text(json.dumps(profile()))
            path.chmod(0o600)
            loaded = ble.load_profile_file(str(path.resolve()))
            self.assertEqual(json.loads(loaded)["device_id"], DEVICE)
            path.chmod(0o640)
            with self.assertRaisesRegex(ble.ClientError, "profile_permissions"):
                ble.load_profile_file(str(path.resolve()))
            path.chmod(0o600)
            link = Path(directory) / "link.json"
            link.symlink_to(path)
            with self.assertRaisesRegex(ble.ClientError, "profile_open"):
                ble.load_profile_file(str(link.absolute()))
            with self.assertRaisesRegex(ble.ClientError, "profile_path_not_absolute"):
                ble.load_profile_file("profile.json")


if __name__ == "__main__":
    unittest.main()
