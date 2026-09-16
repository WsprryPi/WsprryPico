import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_phase11_5_package3_progress import frame_payload, http_body, source_thresholds
from phase11_5_package3_progress import BOOT, CASES, IMAGE, SCHEMA, SOURCE, validate
from phase11_5_pilot import DEVICE, SERIAL
from phase11_5_r3_tls_plan import BRACKET_POLICY, CASES as TLS_CASES
from phase11_5_r3_v2_rf import PACKAGE3_POLICY, SCHEMA as RF_SCHEMA, validate as validate_rf


class Package3ProgressScopeTests(unittest.TestCase):
    def packet(self):
        packet = {
            "schema": SCHEMA, "scope": SCHEMA, "standing_authority": "R3-COMPLETE-20260913-v2",
            "source_revision": SOURCE, "image_sha256": IMAGE, "boot_id": BOOT,
            "serial": SERIAL, "device_id": DEVICE, "cases": CASES,
            "runtime_seconds": 240, "restoration_seconds": 150, "rf_jobs": 0,
            "rf_duration_ns": 0, "flashes": 0, "wifi_cycles": 0, "configuration_writes": 0,
            "client_pid": 123, "client_netns": "/proc/123/ns/net",
            "client_mountns": "/proc/123/ns/mnt", "address": "10.77.15.10", "port": 18443,
            "credentials": {
                "controller": {"ca": "credentials/controller/client-ca.crt",
                    "cert": "credentials/controller/client.crt",
                    "key": "credentials/controller/client.key"},
                "browser": {"ca": "credentials/browser/client-ca.crt",
                    "cert": "credentials/browser/client.crt",
                    "key": "credentials/browser/client.key"}},
        }
        for index, key in enumerate(("inventory_session", "b_session", "idle_session",
                "partial_session", "output_session", "owner_id", "job_id"), 1):
            packet[key] = f"{index:032x}"
        return packet

    def test_exact_scope_and_mutations(self):
        packet = self.packet()
        self.assertEqual(validate(packet), packet)
        changes = [
            ("source_revision", "0" * 40), ("image_sha256", "0" * 64),
            ("boot_id", "0" * 32), ("cases", CASES[:-1]), ("runtime_seconds", 241),
            ("rf_jobs", 1), ("rf_duration_ns", 1), ("wifi_cycles", 1),
            ("client_netns", "/proc/124/ns/net"), ("address", "10.77.15.11"),
        ]
        for key, value in changes:
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(dict(packet, **{key: value}))
        duplicate = copy.deepcopy(packet)
        duplicate["partial_session"] = duplicate["idle_session"]
        with self.assertRaises(ValueError):
            validate(duplicate)

    def test_current_source_thresholds_and_rejects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source").mkdir()
            for source, target in ((ROOT / "src/network/pico/server.cpp", "server.cpp"),
                    (ROOT / "src/wtp/endpoint.cpp", "endpoint.cpp"),
                    (ROOT / "src/wtp/frame_parser.cpp", "frame_parser.cpp"),
                    (ROOT / "src/network/web/app.js", "app.js")):
                shutil.copyfile(source, root / "source" / target)
            values = source_thresholds(root)
            self.assertEqual(values["established_progress_ms"], 30000)
            self.assertEqual(values["wtp_output_progress_ms"], 5000)
            path = root / "source/endpoint.cpp"
            path.write_text(path.read_text().replace("last_tx_progress_ms_ >= 5000",
                "last_tx_progress_ms_ >= 4999"))
            with self.assertRaisesRegex(ValueError, "wtp_output_progress_ms"):
                source_thresholds(root)

    def test_embedded_http_reason_phrase_is_not_assumed(self):
        body = b'{"transport":{"active":1}}'
        raw = b"HTTP/1.1 200 Response\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body
        self.assertEqual(http_body(raw)["transport"]["active"], 1)
        with self.assertRaisesRegex(ValueError, "status code"):
            http_body(raw.replace(b" 200 ", b" 503 ", 1))

    def test_frame_payload_rejects_corruption(self):
        from validate_wtp_contract import frame
        value = {"type": "request", "protocol": "WTP/1", "session_id": "1" * 32,
            "request_id": "2" * 32, "op": "STATUS", "body": {}}
        raw = frame(json.dumps(value, separators=(",", ":")).encode())
        self.assertEqual(frame_payload(raw), value)
        changed = bytearray(raw)
        changed[-1] ^= 1
        with self.assertRaisesRegex(ValueError, "size/checksum"):
            frame_payload(bytes(changed))


class Package3PressureScopeTests(unittest.TestCase):
    def packet(self):
        jobs = []
        for index in range(2):
            jobs.append({"job_id": f"{index + 10:032x}", "profile": "rf-events/1", "mode": "tone",
                "total_duration_ns": "100000000000", "allow_frequency_adjustment": True,
                "events": [{"offset_ns": "0", "duration_ns": "100000000000", "rf_on": True,
                    "frequency_nhz": "135500000000000"}]})
        packet = {"schema": RF_SCHEMA, "r3_scope": RF_SCHEMA,
            "standing_authority": "R3-COMPLETE-20260913-v2", "serial": SERIAL,
            "device_id": DEVICE, "source_revision": SOURCE, "image_sha256": IMAGE,
            "boot_id": BOOT, "b_boot_id": "8" * 32, "owner_id": "1" * 32,
            "peer_session": "2" * 32, "inventory_session": "3" * 32, "b_session": "4" * 32,
            "runtime_seconds": 660, "restoration_seconds": 150, "maximum_renewals": 12,
            "configuration_writes": 0, "wifi_cycles": 0, "heap_probes": 0, "flashes": 0,
            "jobs": jobs, "closure_policy": PACKAGE3_POLICY,
            "observer_policy": "single-flight-info-v1", "b_role": "unchanged-comparator",
            "shared_rf_reservation": "durable-both-picos-v1", "maximum_initial_terminal_records": 8,
            "not_before_host_monotonic_ns": 1, "pressure_family": "tls",
            "maximum_tcp_connections": 12, "pressure_cases": [list(case) for case in TLS_CASES],
            "observer_bracket_policy": BRACKET_POLICY, "ack_filter_policy": None,
            "contention": {"policy": "native-wtp-and-bounded-pressure-v1", "maximum_https_requests": 1},
        }
        return packet

    def test_current_image_pressure_policy_is_exact(self):
        packet = self.packet()
        self.assertEqual(validate_rf(packet), packet)
        for key, value in (("source_revision", "0" * 40), ("image_sha256", "0" * 64),
                ("boot_id", "0" * 32), ("closure_policy", "phase115-completion-pressure-v1"),
                ("maximum_initial_terminal_records", 9), ("observer_policy", "other")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_rf(dict(packet, **{key: value}))


if __name__ == "__main__":
    unittest.main()
