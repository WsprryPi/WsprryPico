#!/usr/bin/env python3

import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from phase11_6.plan import (  # noqa: E402
    COMPANION_BINARY_SHA256,
    COMPANION_SOURCE,
    FIRMWARE_SOURCE,
    FIRMWARE_UF2_SHA256,
    PEER_ACCEPTED_BOOT,
    PICO_ACCEPTED_BOOT,
    compose,
)
from run_phase11_6_batch import closure_jobs  # noqa: E402


class Phase116ClosureExecutionTests(unittest.TestCase):
    def setUp(self):
        self.plan = compose()
        self.closure = json.loads(
            (ROOT / "docs/development/phase11-6-closure-plan.json").read_text()
        )

    def test_exact_closure_slice_resolves_in_frozen_order(self):
        jobs = closure_jobs(self.plan, self.closure)
        self.assertEqual(len(jobs), 82)
        self.assertEqual(jobs[0]["id"], "2200m:FSKCW:1:browser_compact:nominal")
        self.assertEqual(jobs[-1]["id"], "6m:DFCW:2:controller_disconnect:nominal")
        self.assertNotIn("WSPR", {job["mode"] for job in jobs})
        self.assertEqual(
            sum(Decimal(job["planned_duration_ns"]) / Decimal(10**9)
                for job in jobs),
            Decimal("3260.000075"),
        )

    def test_candidate_companion_peer_and_dfcw_polarity_are_exact(self):
        self.assertEqual(FIRMWARE_SOURCE,
                         "0e85ff90571c800450073f7b0bfafd70266f1f44")
        self.assertEqual(FIRMWARE_UF2_SHA256,
                         "9ac5a40fe6d9a44a3a0156621b82801488efecafb9f472ba601dbcbb3e138398")
        self.assertEqual(PICO_ACCEPTED_BOOT, "cab95d7eecad05047fcb1d6806cf9e86")
        self.assertEqual(PEER_ACCEPTED_BOOT, "6684b4b197d80cfa0ce83b3aaf205cb0")
        self.assertEqual(COMPANION_SOURCE,
                         "c39fae35a77afb0f9a1fbe741a4f1fbdf9cbdccf")
        self.assertEqual(COMPANION_BINARY_SHA256,
                         "b8e63947e2e9780f43dc4247869db138f81cc6e2245c99c1fd02ad9de4b33ff6")
        job = next(job for job in closure_jobs(self.plan, self.closure)
                   if job["band"] == "2200m" and job["mode"] == "DFCW")
        on = [event for event in job["expected_job"]["events"] if event["rf_on"]]
        self.assertEqual(int(on[0]["frequency_nhz"]), 137_505_000_000_000)
        self.assertEqual(int(on[1]["frequency_nhz"]), 137_500_000_000_000)

    def test_closure_mutation_is_rejected(self):
        changed = copy.deepcopy(self.closure)
        changed["minimum_remaining_rf_jobs"][0]["sequence"] = 177
        with self.assertRaisesRegex(ValueError, "order"):
            closure_jobs(self.plan, changed)
        changed = copy.deepcopy(self.closure)
        changed["dfcw_polarity"] = "dot-low/dash-high"
        with self.assertRaisesRegex(ValueError, "authorization"):
            closure_jobs(self.plan, changed)

    def test_checked_in_execution_audit_retains_fail_stop_and_repairs(self):
        path = ROOT / "docs/development/phase11-6-closure-execution-results.json"
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            "b1198e1ef61c61d860e32481457f344d9fc87ba558cdb8aa62a50650dca72511",
        )
        value = json.loads(path.read_text())
        self.assertEqual(value["status"], "STOPPED_ON_FIRST_FAILURE")
        self.assertEqual(value["completed_jobs"], 1)
        self.assertEqual(value["completed_rf_seconds"], 45.000001)
        self.assertEqual(value["unexecuted_authorized_jobs"], 80)
        self.assertEqual(value["stop_failure"]["sequence"], 177)
        self.assertFalse(value["stop_failure"]["rf_emitted"])
        self.assertEqual(
            {(row["band"], row["mode"]) for row in value["historical_packet_audits"]},
            {
                ("630m", "QRSS"), ("630m", "FSKCW"), ("630m", "DFCW"),
                ("160m", "QRSS"), ("160m", "DFCW"), ("80m", "DFCW"),
            },
        )
        self.assertTrue(all(row["audit"] == "PASS"
                            for row in value["historical_packet_audits"]))
        repaired = [attempt for row in value["historical_packet_audits"]
                    for attempt in row["attempts"] if "analysis_repair" in attempt]
        self.assertEqual([attempt["sequence"] for attempt in repaired], [27, 32, 36])
        self.assertTrue(all(
            attempt["analysis_repair"]["original_analysis_audit"]
                == "FAIL_ANALYSIS_WTP_JOB_IDENTITY"
            and attempt["analysis_repair"]["replacement_analysis_audit"]
                == "PASS_NEW_ZERO_RF_REANALYSIS"
            for attempt in repaired
        ))

    def test_execution_summary_binds_authoritative_matrix(self):
        summary = json.loads((
            ROOT / "docs/development/phase11-6-closure-execution.json"
        ).read_text())
        matrix_path = ROOT / "docs/development/phase11-6-matrix.json"
        self.assertEqual(
            summary["authoritative_matrix"]["file_sha256"],
            hashlib.sha256(matrix_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(summary["execution"]["completed_rf_seconds"], "45.000001")
        self.assertEqual(summary["execution"]["unexecuted_jobs"], 80)
        self.assertFalse(summary["closure"]["closed"])
        self.assertFalse(summary["closure"]["further_rf_authorized"])


if __name__ == "__main__":
    unittest.main()
