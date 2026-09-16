import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit_phase11_5_package4_usb import frame_payload, source_mechanisms
from phase11_5_package4_usb import (BOOT, B_BOOT, CASES, IMAGE, SCHEMA, SOURCE,
                                    flush_unsent_usb_output, validate)
from phase11_5_package4_unread_retest import (
    CASE as RETEST_CASE, PRIOR_PACKET, PRIOR_RESULT, SCHEMA as RETEST_SCHEMA,
    validate as validate_retest, wait_console_running)
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


def retest_packet():
    ids = iter(f"{number:032x}" for number in range(101, 120))
    value = {"schema": RETEST_SCHEMA, "scope": RETEST_SCHEMA,
        "authorization": "USER-REQUESTED-PHYSICAL-RETEST-20260916",
        "standing_authority": "R3-COMPLETE-20260913-v2", "source_revision": SOURCE,
        "image_sha256": IMAGE, "boot_id": BOOT, "b_boot_id": B_BOOT,
        "serial": SERIAL, "device_id": DEVICE, "b_serial": B_SERIAL,
        "b_device_id": B_DEVICE, "case": RETEST_CASE,
        "prior_package4_packet_sha256": PRIOR_PACKET,
        "prior_package4_result_sha256": PRIOR_RESULT,
        "prior_assertion": {"2.3d": "ACCEPTED",
            "2.3e": "OPEN_MISSING_SAME_SESSION_SILENCE_AND_DTR_RECOVERY"},
        "runtime_seconds": 240, "restoration_seconds": 150, "rf_jobs": 1,
        "rf_duration_ns": 100_000_000_000, "flashes": 0, "wifi_cycles": 0,
        "configuration_writes": 0, "controlled_reboots": 0, "maximum_renewals": 4,
        "client_pid": 123, "client_netns": "/proc/123/ns/net",
        "client_mountns": "/proc/123/ns/mnt", "address": "10.77.15.10", "port": 18443,
        "shared_rf_reservation": "durable-both-picos-v1",
        "fixture_root": "/home/pi/phase11-5-package4-unread-fixture-20260916",
        "fixture_packet_sha256":
            "0084f965781aaf591f55c6d2a7b6252876d29c8dd455a0ae48d33c9803b828ea",
        "job": {"case": RETEST_CASE, "job_id": next(ids), "profile": "rf-events/1",
            "mode": "tone", "total_duration_ns": "100000000000",
            "allow_frequency_adjustment": True, "events": [{"offset_ns": "0",
                "duration_ns": "100000000000", "rf_on": True,
                "frequency_nhz": "135500000000000"}]},
        "credentials": {"controller": {"ca": "credentials/controller/client-ca.crt",
            "cert": "credentials/controller/client.crt",
            "key": "credentials/controller/client.key"}},
        "usb": {"maximum_payload_bytes": 65536, "maximum_wire_bytes": 65552,
            "parser_write_bytes": 512, "parser_write_pause_ms": 15,
            "unread_max_requests": 1024, "unread_write_seconds": 3,
            "unread_hold_seconds": 12, "unread_capture_bytes": 1048576,
            "silence_seconds": 2}}
    for key in ("inventory_session", "b_session", "network_session", "owner_id",
                "unread_session", "unread_probe", "unread_recovery_session"):
        value[key] = next(ids)
    return value


def retest2_packet():
    value = retest_packet()
    value.update(retest_attempt=2,
        authorization="USER-REQUESTED-PHYSICAL-RETEST-RETRY-20260916",
        fixture_root="/home/pi/phase11-5-package4-unread-fixture2-20260916",
        fixture_packet_sha256=
            "f4d1dade80f5df59375af02faccfd347158cffe295955b74aa360bf4a30b9e86",
        previous_retest={
            "packet_sha256":
                "10fe965e5ac0e15d58226aaab598ca9671ed0d5009149e5f737b26f6499607ba",
            "result_sha256":
                "a0071448cbdb22026bfbef8dda4cc947f5d0ef1b532f2c7817d22dce3436e519",
            "status": "OPEN_NO_UNREAD_PRESSURE_EXECUTED", "rf_jobs_charged": 1,
            "rf_duration_ns_charged": 100_000_000_000})
    return value


class Package4Tests(unittest.TestCase):
    def test_unread_retest_waits_for_console_running_transition(self):
        running = {"status": {"boot_id": BOOT, "state": "running", "output_active": True}}
        for state in ("empty", "loaded", "armed"):
            with self.subTest(state=state):
                prior = {"status": {"boot_id": BOOT, "state": state,
                                    "output_active": False}}
                latest = {"info": (__import__("time").monotonic_ns(), prior)}
                lock = threading.Lock()
                stop = mock.Mock()
                stop.is_set.return_value = False

                def advance(_seconds):
                    with lock:
                        latest["info"] = (__import__("time").monotonic_ns(), running)

                stop.wait.side_effect = advance
                wait_console_running(latest, lock, stop, timeout_seconds=.1)
                stop.wait.assert_called_once_with(.02)

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

    def test_unread_retest_exact_scope_and_mutations(self):
        original = retest_packet()
        self.assertIs(validate_retest(original), original)
        mutations = [
            lambda p: p.update(rf_jobs=2),
            lambda p: p["job"].update(total_duration_ns="99000000000"),
            lambda p: p["usb"].update(unread_hold_seconds=11),
            lambda p: p.update(prior_package4_packet_sha256="0" * 64),
            lambda p: p.update(network_session=p["unread_session"]),
        ]
        for change in mutations:
            changed = copy.deepcopy(original)
            change(changed)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_retest(changed)

    def test_unread_retest_second_attempt_exact_history(self):
        original = retest2_packet()
        self.assertIs(validate_retest(original), original)
        for change in (
                lambda p: p["previous_retest"].update(rf_jobs_charged=0),
                lambda p: p.update(fixture_packet_sha256="0" * 64),
                lambda p: p.update(authorization="USER-REQUESTED-PHYSICAL-RETEST-20260916")):
            changed = copy.deepcopy(original)
            change(changed)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_retest(changed)

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
