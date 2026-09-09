#!/usr/bin/env python3
"""Hardware-free refusal, framing and ambiguous-mutation recovery tests."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import inhibited_network_acceptance as acceptance
from validate_wtp_contract import frame

BOOT = "b" * 32
DEVICE = "d" * 32
CAPS = dict(engine=acceptance.ENGINE, modes=["tone"], profiles=["rf-events/1"],
            max_events=1, max_job_duration_ns=str(acceptance.DURATION),
            minimum_arm_lead_ns="100000000", maximum_arm_ahead_ns="60000000000",
            maximum_arm_uncertainty_ns=str(acceptance.BUDGET),
            minimum_lease_ms=5000, maximum_lease_ms=60000,
            frequency_ranges=[dict(minimum_nhz=str(acceptance.FREQUENCY),
                                   maximum_nhz=str(acceptance.FREQUENCY))])


class Log:
    def __init__(self):
        self.rows = []

    def record(self, kind, value):
        self.rows.append((kind, copy.deepcopy(value)))


class FakePeer:
    def __init__(self, fault=None):
        self.args = types.SimpleNamespace(boot_id=BOOT, device_id=DEVICE)
        self.evidence = Log()
        self.calls = []
        self.fault = fault
        self.status = dict(boot_id=BOOT, state="empty", owner_id=None,
                           job_id=None, output_active=False, terminal_records=[])

    def open(self):
        self.calls.append("reconnect")

    def request(self, op, body, expected_error=None):
        self.calls.append(op)
        if op == "STATUS":
            return copy.deepcopy(self.status)
        if op == "CLAIM":
            self.status["owner_id"] = body["owner_id"]
            return {"owner_id": body["owner_id"]}
        if op == "LOAD":
            self.status.update(state="loaded", job_id=body["job_id"])
            if self.fault == "other_job":
                self.status["job_id"] = "e" * 32
            if self.fault == "unknown":
                self.status["output_active"] = None
            if self.fault in ("load_reply_lost", "other_job", "unknown"):
                raise TimeoutError("ambiguous LOAD")
        if op == "ABORT":
            self.status["state"] = "aborted"
            self.status["terminal_records"] = [dict(job_id=self.status["job_id"],
                                                    state="aborted", output_active=False)]
        if op == "RELEASE":
            self.status.update(state="empty", owner_id=None, job_id=None)
        if op == "GET_CLOCK":
            return dict(state="unsynchronized", leap="normal", uncertainty_ns="1", utc_now_ns="1000")
        return {}


def browser_baseline(*args, **kwargs):
    return 200, dict(job=dict(boot_id=BOOT, state="empty", output_active=False,
                              owner_id=None, job_id=None, terminal_records=[]),
                     standalone=dict(enabled=False, engine=acceptance.ENGINE),
                     network=dict(deployment_identity_matches=True))


class AcceptanceTests(unittest.TestCase):
    def test_plan_has_no_io_or_required_credentials(self):
        with patch.object(acceptance.socket, "socket", side_effect=AssertionError("network opened")), \
                patch.object(sys, "argv", ["acceptance"]), patch("builtins.print") as output:
            acceptance.main()
        self.assertFalse(json.loads(output.call_args.args[0])["execution"])

    def test_run_requires_explicit_binding(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/inhibited_network_acceptance.py"),
                                 "--run"], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires explicit", result.stderr)

    def test_job_is_a_complete_bounded_contract_request(self):
        peer = acceptance.Peer(types.SimpleNamespace(), Log())
        value = dict(type="request", protocol="WTP/1", session_id="a" * 32,
                     request_id="c" * 32, op="LOAD", body=acceptance.job_value("1" * 32))
        self.assertEqual(peer.validator.errors(value, peer.schema), [])
        self.assertEqual(sum(int(e["duration_ns"]) for e in value["body"]["events"]), acceptance.DURATION)

    def test_caps_refuse_physical_engine_and_incompatible_limits(self):
        acceptance.check_caps(CAPS)
        for key, value in (("engine", "pio"), ("max_job_duration_ns", "1"),
                           ("max_events", 0), ("maximum_arm_ahead_ns", "1"),
                           ("maximum_arm_uncertainty_ns", "1"), ("maximum_lease_ms", 5000),
                           ("frequency_ranges", [])):
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                acceptance.check_caps(dict(CAPS, **{key: value}))

    def test_authority_requires_explicit_inactive_matching_identity(self):
        status = FakePeer().status
        acceptance.check_status(status, BOOT, unowned=True)
        for key, value in (("boot_id", "f" * 32), ("output_active", None),
                           ("output_active", "false"), ("output_active", 0),
                           ("output_active", True), ("owner_id", "f" * 32),
                           ("job_id", "a" * 32), ("state", "failed")):
            with self.subTest(key=key, value=value), self.assertRaises(RuntimeError):
                acceptance.check_status(dict(status, **{key: value}), BOOT, unowned=True)

    def test_clock_refuses_unusable_state_or_uncertainty(self):
        clock = dict(state="synchronized", leap="normal", uncertainty_ns="100000000", utc_now_ns="1000")
        self.assertEqual(acceptance.check_clock(clock), 1000 + acceptance.LEAD)
        for key, value in (("state", "unsynchronized"), ("leap", "unknown"),
                           ("uncertainty_ns", "1"), ("uncertainty_ns", "500000001")):
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                acceptance.check_clock(dict(clock, **{key: value}))

    @patch.object(acceptance, "browser", side_effect=browser_baseline)
    def test_loaded_cancel_has_terminal_and_unowned_proof(self, _):
        peer = FakePeer()
        acceptance.run_case(peer, "abort_loaded")
        self.assertEqual(peer.calls.count("LOAD"), 1)
        self.assertEqual(peer.calls.count("ABORT"), 1)
        self.assertNotIn("ARM", peer.calls)
        self.assertEqual(peer.evidence.rows[-1], ("case_pass", {"case": "abort_loaded"}))

    @patch.object(acceptance, "browser", side_effect=browser_baseline)
    def test_ambiguous_load_reconciles_without_duplicate_submission(self, _):
        peer = FakePeer("load_reply_lost")
        with self.assertRaises(TimeoutError):
            acceptance.run_case(peer, "abort_loaded")
        self.assertEqual(peer.calls.count("LOAD"), 1)
        self.assertEqual(peer.calls[-5:], ["ABORT", "STATUS", "STATUS", "RELEASE", "STATUS"])
        self.assertEqual(peer.evidence.rows[-1][0], "cleanup_confirmed")
        self.assertNotIn("case_pass", [k for k, _ in peer.evidence.rows])

    @patch.object(acceptance, "browser", side_effect=browser_baseline)
    def test_unknown_or_different_job_blocks_cleanup_mutations(self, _):
        for fault in ("unknown", "other_job"):
            with self.subTest(fault=fault):
                peer = FakePeer(fault)
                with self.assertRaises(TimeoutError):
                    acceptance.run_case(peer, "abort_loaded")
                self.assertNotIn("ABORT", peer.calls)
                self.assertNotIn("RELEASE", peer.calls)
                self.assertEqual(peer.evidence.rows[-1][0], "cleanup_unconfirmed")

    @patch.object(acceptance, "browser", side_effect=browser_baseline)
    def test_invalid_clock_never_arms_and_cleans_loaded_job(self, _):
        peer = FakePeer()
        with self.assertRaises(RuntimeError):
            acceptance.run_case(peer, "abort_armed")
        self.assertNotIn("ARM", peer.calls)
        self.assertIn("ABORT", peer.calls)
        self.assertEqual(peer.evidence.rows[-1][0], "cleanup_confirmed")

    def test_unowned_gate_precedes_claim(self):
        peer = FakePeer()
        peer.status["owner_id"] = "f" * 32
        with self.assertRaises(RuntimeError):
            acceptance.run_case(peer, "abort_loaded")
        self.assertEqual(peer.calls, ["STATUS"])

    def test_strict_framing_rejects_corruption_without_resynchronizing(self):
        peer = acceptance.Peer(types.SimpleNamespace(boot_id=BOOT), Log())
        class Stream:
            def settimeout(self, timeout):
                pass
            def sendall(self, data):
                self.request = json.loads(data[16:])
            def recv(self, count):
                response = dict(self.request, type="response", ok=True, body={})
                data = b"X" + frame(json.dumps(response).encode())[1:]
                return data[:count]
        peer.stream = Stream()
        with self.assertRaisesRegex(RuntimeError, "invalid frame"):
            peer.request("PING", {})


if __name__ == "__main__":
    unittest.main()
