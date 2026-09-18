#!/usr/bin/env python3
"""Deterministic checks for the Phase 11.5 Package 6 closeout."""

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from audit_phase11_5_package6 import R3_GROUPS, validate  # noqa: E402


RESULT_PATH = ROOT / "docs/development/phase11-5-package6-result.json"
MATRIX_PATH = ROOT / "docs/development/phase11-5-completion-matrix.json"
ADVERSARIAL_PATH = ROOT / "docs/development/phase11-5-package6-adversarial-result.json"


class Package6Tests(unittest.TestCase):
    def setUp(self):
        self.result = json.loads(RESULT_PATH.read_text())
        self.matrix = json.loads(MATRIX_PATH.read_text())

    def test_publication_passes_independent_audit(self):
        validate(self.result, self.matrix, ROOT)

    def test_normative_group_partition_is_exact(self):
        members = [item for group in R3_GROUPS.values() for item in group]
        self.assertEqual(len(R3_GROUPS), 14)
        self.assertEqual(len(members), 24)
        self.assertEqual(len(set(members)), 24)
        self.assertEqual(self.result["counts"]["extended_features"], 7)

    def test_closeout_has_no_new_physical_charge(self):
        self.assertEqual(set(self.result["hardware_charge"].values()), {0})
        self.assertEqual(self.result["new_physical_acceptance_assertions"], 0)
        self.assertEqual(self.matrix["family_status"]["R3"],
                         "CLOSED with Package 6 applicability review")
        if (ROOT / "docs/development/phase11-5-package11-retry4-result.json").exists():
            self.assertEqual(self.matrix["status"], "CLOSED")
            self.assertIsNotNone(self.matrix["accepted_configuration"])
        else:
            self.assertIsNone(self.matrix["accepted_configuration"])

    def test_published_adversarial_result_is_reproducible(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "adversarial_phase11_5_package6.py"),
             "--result", str(RESULT_PATH), "--matrix", str(MATRIX_PATH)],
            cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE)
        self.assertEqual(json.loads(completed.stdout),
                         json.loads(ADVERSARIAL_PATH.read_text()))


if __name__ == "__main__":
    unittest.main()
