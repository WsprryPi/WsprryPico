#!/usr/bin/env python3
"""Hardware-free pilot guard, framing and no-retry regressions."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase11_5_pilot import (CLOCK, DEVICE, DURATION, FREQUENCY, SERIAL, Decoder,
                             check_rf_observation, check_status, run_jobs, validate_packet)
from validate_wtp_contract import frame


def packet():
    return dict(schema="phase11.5-pilot-v1", serial=SERIAL, device_id=DEVICE,
                system_clock_hz=CLOCK, revision="a" * 12, uf2_sha256="b" * 64,
                host_boot_id="220e53ca-ca95-4206-9581-dbe28aa1eeb8",
                jobs=[dict(job_id=f"{i:032x}", profile="rf-events/1", mode="tone",
                           total_duration_ns=str(DURATION), allow_frequency_adjustment=True,
                           events=[dict(offset_ns="0", duration_ns=str(DURATION), rf_on=True,
                                        frequency_nhz=str(FREQUENCY))]) for i in range(1, 4)])


class FakePeer:
    def __init__(self, lose_arm=False, active=True):
        self.calls, self.owner, self.job = [], None, None
        self.states = ["empty"]
        self.lose_arm, self.active = lose_arm, active

    def request(self, op, body=None):
        self.calls.append(op)
        if op == "CLAIM":
            self.owner = body["owner_id"]
        elif op == "LOAD":
            self.job, self.states = body["job_id"], ["loaded"]
        elif op == "GET_CLOCK":
            return dict(state="synchronized", leap="normal", uncertainty_ns="1000",
                        utc_now_ns="1800000000000000000")
        elif op == "ARM":
            if self.lose_arm:
                raise TimeoutError("injected lost ARM reply")
            self.states = ["armed", "running", "complete"]
        elif op == "RELEASE":
            self.owner, self.job, self.states = None, None, ["empty"]
        elif op == "STATUS":
            state = self.states.pop(0)
            return dict(boot_id="c" * 32, state=state, owner_id=self.owner, job_id=self.job,
                        output_active=self.active and state == "running")
        return {}


class PilotTests(unittest.TestCase):
    def test_exact_packet_and_no_default_io(self):
        value = packet()
        validate_packet(value)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "packet.json"
            path.write_text(json.dumps(value))
            run = subprocess.run([sys.executable, str(ROOT / "scripts/phase11_5_pilot.py"),
                                  str(path)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn("no hardware accessed", run.stdout)

    def test_reject_broader_scope_and_duplicate_jobs(self):
        for field, wrong in (("serial", "CDDBF8767C506C07"), ("system_clock_hz", 150000000),
                             ("revision", "a" * 12 + "-dirty"), ("host_boot_id", "")):
            value = packet()
            value[field] = wrong
            with self.assertRaises(ValueError):
                validate_packet(value)
        value = packet()
        value["jobs"][0]["events"][0]["duration_ns"] = "20000000000"
        with self.assertRaises(ValueError):
            validate_packet(value)
        value = packet()
        value["jobs"][0]["events"][0]["rf_on"] = 1
        with self.assertRaises(ValueError):
            validate_packet(value)
        value = packet()
        value["jobs"][1] = copy.deepcopy(value["jobs"][0])
        with self.assertRaises(ValueError):
            validate_packet(value)

    def test_split_and_coalesced_frames_without_silent_recovery(self):
        first, second = dict(value=1), dict(value=2)
        data = frame(json.dumps(first).encode()) + frame(json.dumps(second).encode())
        decoder = Decoder()
        self.assertEqual(decoder.feed(data[:7]), [])
        self.assertEqual(decoder.feed(data[7:]), [first, second])
        broken = bytearray(frame(b'{}'))
        broken[-1] ^= 1
        for value in (bytes(broken), b"garbage" + data):
            with self.assertRaises(ValueError):
                Decoder().feed(value)

    def test_finite_lifecycle_and_lost_arm_stop(self):
        peer = FakePeer()
        run_jobs(peer, packet()["jobs"], "c" * 32, lambda _: None, lambda *_: None)
        self.assertEqual(peer.calls.count("LOAD"), 3)
        self.assertEqual(peer.calls.count("ARM"), 3)
        self.assertEqual(peer.calls.count("RELEASE"), 3)
        peer = FakePeer(lose_arm=True)
        with self.assertRaises(TimeoutError):
            run_jobs(peer, packet()["jobs"], "c" * 32, lambda _: None, lambda *_: None)
        self.assertEqual(peer.calls.count("ARM"), 1)
        self.assertEqual(peer.calls.count("LOAD"), 1)
        self.assertNotIn("RELEASE", peer.calls)
        self.assertNotIn("ABORT", peer.calls)

    def test_no_fake_output_or_inactive_terminal(self):
        with self.assertRaises(ValueError):
            run_jobs(FakePeer(active=False), packet()["jobs"], "c" * 32,
                     lambda _: None, lambda *_: None)
        for changed in (dict(output_active=True), dict(boot_id="d" * 32),
                        dict(owner_id="e" * 32)):
            state = dict(boot_id="c" * 32, state="complete", output_active=False,
                         job_id="f" * 32, owner_id=None)
            state.update(changed)
            with self.assertRaises(ValueError):
                check_status(state, "c" * 32, {"complete"}, "f" * 32)

    def test_deadline_and_coverage_failures(self):
        info = dict(dma_errors=0, refill_invalid_reserves=0, exhausted_successor_links=0,
                    refill_irq_unpaired=0, refill_full_predecessor=dict(total_words=16384,
                    remaining_words=4096, observations=1), refill_short_predecessor=None,
                    running_successor_links=1, refill_irq_pairs=1, rf_max_service_gap_ns="2849000")
        check_rf_observation(info)
        for key, value in (("dma_errors", 1), ("refill_irq_unpaired", 1),
                           ("refill_irq_pairs", 0), ("rf_max_service_gap_ns", "2850000")):
            changed = copy.deepcopy(info)
            changed[key] = value
            with self.assertRaises(ValueError):
                check_rf_observation(changed)
        info["refill_full_predecessor"]["remaining_words"] = 4095
        with self.assertRaises(ValueError):
            check_rf_observation(info)


if __name__ == "__main__":
    unittest.main()
