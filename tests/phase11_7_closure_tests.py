#!/usr/bin/env python3
"""Deterministic closure and mutation checks for Phase 11.7."""

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from adversarial_phase11_7 import assess  # noqa: E402
from audit_phase11_7 import validate  # noqa: E402


RESULT_PATH = ROOT / "docs/development/phase11-7-result.json"
ADVERSARIAL_PATH = ROOT / "docs/development/phase11-7-adversarial-result.json"
REVIEW_PATH = ROOT / "docs/development/phase11-7-review.md"


class Phase117ClosureTests(unittest.TestCase):
    def setUp(self):
        self.result = json.loads(RESULT_PATH.read_text())

    def test_publication_passes_offline_audit(self):
        validate(ROOT, self.result)

    def test_adversarial_publication_is_reproducible(self):
        self.assertEqual(assess(ROOT, self.result),
                         json.loads(ADVERSARIAL_PATH.read_text()))

    def test_review_names_every_phase_and_authoritative_artifact(self):
        review = REVIEW_PATH.read_text()
        for phase in range(1, 8):
            self.assertIn(f"11.{phase}", review)
        for name in ("phase11-6-scope-disposition.json", "phase11-6-matrix.json",
                     "phase11-5-completion-matrix.json", "phase11-7-result.json"):
            self.assertIn(name, review)
        self.assertIn("No Phase 11.6 WSPR row is accepted", review)
        self.assertIn("no hardware or RF operations", review)

    def test_historical_source_checks_use_fixed_review_cutoffs(self):
        closure = (ROOT / "scripts/audit_phase11_7.py").read_text()
        self.assertNotIn("working_names", closure)
        self.assertIn("PICO_CANDIDATE, PICO_TESTED", closure)
        self.assertIn("PI_BASE, PI_TESTED", closure)
        package6 = (ROOT / "scripts/audit_phase11_5_package6.py").read_text()
        package7 = (ROOT / "tests/phase11_5_package7_tests.py").read_text()
        package8 = (ROOT / "tests/phase11_5_package8_tests.py").read_text()
        self.assertNotIn('f"{CURRENT_SOURCE}..HEAD"', package6)
        self.assertNotIn('source + "..HEAD"', package7)
        self.assertNotIn('package8.SOURCE + "..HEAD"', package8)
        for source in (package6, package7, package8):
            self.assertIn("3b8a6535d8a9a186d090d3105f056b9c52b2d268", source)


if __name__ == "__main__":
    unittest.main()
