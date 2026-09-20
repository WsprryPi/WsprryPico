#!/usr/bin/env python3
"""Deterministic checks for the Phase 11.5 Package 7 publication."""

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from audit_phase11_5_package7 import ALL_ROWS, ROWS, validate_result  # noqa: E402
from audit_phase11_5_package9 import validate_published_result as validate_package9  # noqa: E402


RESULT_PATH = ROOT / "docs/development/phase11-5-package7-result.json"
ADVERSARIAL_PATH = ROOT / "docs/development/phase11-5-package7-adversarial-result.json"
RAW_ADVERSARIAL_PATH = ROOT / "docs/development/phase11-5-package7-raw-adversarial-result.json"
MATRIX_PATH = ROOT / "docs/development/phase11-5-completion-matrix.json"
PHASE11_6_BROWSER_REPAIR_REVIEW = "3b8a6535d8a9a186d090d3105f056b9c52b2d268"


class Package7Tests(unittest.TestCase):
    def setUp(self):
        self.result = json.loads(RESULT_PATH.read_text())
        self.matrix = json.loads(MATRIX_PATH.read_text())

    def test_publication_passes_independent_summary_validation(self):
        validate_result(self.result)

    def test_r4_partition_and_budget_are_exact(self):
        self.assertEqual(len(ROWS), 15)
        self.assertEqual(len(ALL_ROWS), 18)
        self.assertEqual(len(set(ALL_ROWS)), 18)
        self.assertEqual(self.result["budget"]["rf_jobs"], 9)
        self.assertEqual(self.result["budget"]["planned_rf_duration_ns"],
                         213_000_000_000)

    def test_current_matrix_closes_exactly_r4(self):
        rows = [row for row in self.matrix["assertions"] if row["group"] == "R4"]
        self.assertEqual(len(rows), 18)
        self.assertTrue(all(row["classification"] == "accepted/applicable"
                            for row in rows))
        self.assertTrue(all("phase11-5-package7-result.json" in row["evidence"]
                            for row in rows))
        self.assertTrue(self.matrix["family_status"]["R4"].startswith("CLOSED"))
        self.assertTrue(self.matrix["family_status"]["R5"].startswith("CLOSED"))
        if (ROOT / "docs/development/phase11-5-package11-retry4-result.json").exists():
            self.assertTrue(self.matrix["family_status"]["R6"].startswith("CLOSED"))
            self.assertIsNotNone(self.matrix["accepted_configuration"])
        else:
            self.assertTrue(self.matrix["family_status"]["R6"].startswith("OPEN"))
            self.assertIsNone(self.matrix["accepted_configuration"])

    def test_restoration_and_failure_retention_are_complete(self):
        self.assertTrue(all(self.result["restoration"].values()))
        self.assertEqual(len(self.result["failed_attempt_sha256"]), 11)
        self.assertEqual(self.result["family_status"]["R4"], "CLOSED")

    def test_reviewed_pico_source_change_has_package8_impact_review(self):
        source = self.result["candidate"]["source_revision"]
        completed = subprocess.run(
            ["git", "diff", "--name-only",
             source + ".." + PHASE11_6_BROWSER_REPAIR_REVIEW, "--",
             "src", "include", "firmware", "cmake"], cwd=ROOT, check=True,
            text=True, stdout=subprocess.PIPE)
        self.assertEqual(completed.stdout.splitlines(), [
            "src/network/api.cpp",
            "src/network/http.hpp",
            "src/network/pico/server.cpp",
            "src/network/pico/server.hpp",
            "src/phase11_6/__init__.py",
            "src/phase11_6/analysis.py",
            "src/phase11_6/audit.py",
            "src/phase11_6/live.py",
            "src/phase11_6/plan.py",
            "src/phase11_6/recovery.py",
            "src/phase11_6/wspr_group.py",
            "src/rf/pico/pico_pio_dma.cpp",
            "src/rf/pico/pico_pio_dma.hpp",
            "src/rf/pio_dma_sink.cpp",
            "src/rf/pio_dma_sink.hpp",
            "src/rf/stream_engine.cpp",
            "src/rf/stream_engine.hpp",
            "src/standalone/pico/adapters.cpp",
            "src/standalone/pico/adapters.hpp",
            "src/standalone/pico/main.cpp",
            "src/standalone/scheduler.cpp",
            "src/standalone/storage.hpp",
            "src/usb/reply_priority.hpp",
        ])
        impact = json.loads((ROOT / "docs/development/phase11-6-browser-"
                             "allocation-repair-source-impact.json").read_text())
        self.assertEqual(impact["status"], "REQUALIFICATION_REQUIRED")
        self.assertFalse(impact["authorization"]["firmware_deployment"])
        package8 = json.loads((ROOT / "docs/development/phase11-5-package8-result.json").read_text())
        self.assertEqual(package8["source_impact"]["prior_candidate"], source)
        self.assertEqual(package8["source_impact"]["later_pico_runtime_source_changes"], 0)
        self.assertEqual(package8["family_status"]["R4"], "CLOSED")
        package9_path = ROOT / "docs/development/phase11-5-package9-result.json"
        if package9_path.exists():
            package9 = validate_package9(json.loads(package9_path.read_text()))
            self.assertEqual(package9["source_impact"]["prior_candidate"],
                             package8["candidate"]["source_revision"])

    def test_published_adversarial_result_is_reproducible(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "adversarial_phase11_5_package7.py"),
             "--result", str(RESULT_PATH)], cwd=ROOT, check=True, text=True,
            stdout=subprocess.PIPE)
        self.assertEqual(json.loads(completed.stdout),
                         json.loads(ADVERSARIAL_PATH.read_text()))

    def test_private_raw_adversarial_publication_is_complete(self):
        result = json.loads(RAW_ADVERSARIAL_PATH.read_text())
        self.assertEqual(result["schema"], "phase11.5-package7-raw-adversarial-v1")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["mutations"], 21)
        self.assertEqual(len(result["rejected"]), 21)
        self.assertEqual(len(set(result["rejected"])), 21)
        self.assertEqual(result["device_or_network_operations"], 0)


if __name__ == "__main__":
    unittest.main()
