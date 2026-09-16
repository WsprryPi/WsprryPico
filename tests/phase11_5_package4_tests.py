import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit_phase11_5_package4_usb import frame_payload, source_mechanisms
from phase11_5_package4_usb import (BOOT, B_BOOT, CASES, IMAGE, SCHEMA, SOURCE,
                                    flush_unsent_usb_output, validate)
from phase11_5_pilot import DEVICE, SERIAL
from phase11_5_pilot_supervisor import B_DEVICE, B_SERIAL
from validate_wtp_contract import frame


def packet():
    identities = iter(f"{number:032x}" for number in range(1, 20))
    jobs = []
    for case in CASES:
        jobs.append({"case": case, "job_id": next(identities), "profile": "rf-events/1",
            "mode": "tone", "total_duration_ns": "100000000000",
            "allow_frequency_adjustment": True, "events": [{"offset_ns": "0",
                "duration_ns": "100000000000", "rf_on": True,
                "frequency_nhz": "135500000000000"}]})
    value = {"schema": SCHEMA, "scope": SCHEMA,
        "standing_authority": "R3-COMPLETE-20260913-v2", "source_revision": SOURCE,
        "image_sha256": IMAGE, "boot_id": BOOT, "b_boot_id": B_BOOT,
        "serial": SERIAL, "device_id": DEVICE, "b_serial": B_SERIAL,
        "b_device_id": B_DEVICE, "cases": CASES, "runtime_seconds": 360,
        "restoration_seconds": 150, "rf_jobs": 2, "rf_duration_ns": 200_000_000_000,
        "absolute_rf_jobs": 4, "absolute_rf_duration_ns": 400_000_000_000,
        "flashes": 0, "wifi_cycles": 0, "configuration_writes": 0,
        "controlled_reboots": 0, "maximum_renewals": 8, "client_pid": 123,
        "client_netns": "/proc/123/ns/net", "client_mountns": "/proc/123/ns/mnt",
        "address": "10.77.15.10", "port": 18443,
        "shared_rf_reservation": "durable-both-picos-v1", "jobs": jobs,
        "credentials": {"controller": {"ca": "credentials/controller/client-ca.crt",
            "cert": "credentials/controller/client.crt",
            "key": "credentials/controller/client.key"}},
        "usb": {"maximum_payload_bytes": 65536, "maximum_wire_bytes": 65552,
            "parser_write_bytes": 512, "parser_write_pause_ms": 15,
            "unread_max_requests": 1024, "unread_write_seconds": 3,
            "unread_hold_seconds": 12, "unread_capture_bytes": 1048576,
            "silence_seconds": 2}}
    for key in ("inventory_session", "b_session", "network_session", "owner_id",
                "parser_session", "parser_request", "parser_recovery", "unread_session",
                "unread_probe", "unread_recovery_session"):
        value[key] = next(identities)
    return value


class Package4Tests(unittest.TestCase):
    def test_unread_recovery_flushes_only_host_output_and_records_it(self):
        journal = mock.Mock()
        with mock.patch("phase11_5_package4_usb.termios.tcflush") as flush:
            flush_unsent_usb_output(17, journal)
        flush.assert_called_once_with(17, __import__("termios").TCOFLUSH)
        journal.emit.assert_called_once_with("usb_unread_host_output_flushed",
                                             {"dtr_remained_asserted": True})

    def test_exact_profile_and_mutations(self):
        original = packet()
        self.assertIs(validate(original), original)
        mutations = [
            lambda p: p.update(source_revision="f" * 40),
            lambda p: p["jobs"][0].update(total_duration_ns="99999999999"),
            lambda p: p["usb"].update(unread_hold_seconds=5),
            lambda p: p.update(rf_jobs=3),
            lambda p: p.update(b_serial=SERIAL),
            lambda p: p.update(network_session=p["parser_session"]),
        ]
        for change in mutations:
            changed = copy.deepcopy(original)
            change(changed)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate(changed)

    def test_raw_frame_reconstruction_rejects_corruption(self):
        message = {"type": "request", "protocol": "WTP/1", "session_id": "1" * 32,
                   "request_id": "2" * 32, "op": "STATUS", "body": {}}
        raw = frame(json.dumps(message, separators=(",", ":")).encode())
        self.assertEqual(frame_payload(raw), message)
        corrupt = bytearray(raw)
        corrupt[-1] ^= 1
        with self.assertRaises(ValueError):
            frame_payload(bytes(corrupt))

    def test_source_mechanism_bindings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src/wtp").mkdir(parents=True)
            (root / "src/usb").mkdir(parents=True)
            (root / "src/wtp/frame_parser.cpp").write_text(
                "kMaximumPayloadBytes + kFrameHeaderBytes\n"
                "kPartialFrameTimeoutMs = 5000\n")
            (root / "src/wtp/endpoint.cpp").write_text(
                "last_tx_progress_ms_ >= 5000\n"
                "service_.poll(); // Always serviced\n")
            (root / "src/usb/transport.cpp").write_text(
                "std::min(bytes.size(), kServiceBytes)\nwtp_reset = true\n")
            self.assertEqual(source_mechanisms(root)["maximum_wire_bytes"], 65552)
            (root / "src/wtp/endpoint.cpp").write_text("last_tx_progress_ms_ >= 5001\n")
            with self.assertRaises(ValueError):
                source_mechanisms(root)


if __name__ == "__main__":
    unittest.main()
