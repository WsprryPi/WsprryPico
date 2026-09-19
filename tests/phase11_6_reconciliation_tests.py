from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from phase11_6.reconciliation import (  # noqa: E402
    AUDIT_BLOCKED_ROWS,
    REPAIR_BLOCKED_ROWS,
    STRUCTURAL_WSPR_BLOCKED_ROWS,
    remaining_jobs,
    remaining_rf_seconds,
    validate_closure_plan,
    validate_public_artifacts,
)


class Phase116ReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = json.loads(
            (ROOT / "docs/development/phase11-6-matrix.json").read_text()
        )
        cls.plan = json.loads(
            (ROOT / "docs/development/phase11-6-closure-plan.json").read_text()
        )

    def test_checked_in_artifacts_validate(self):
        validate_public_artifacts(self.matrix, ROOT / "docs/development")
        validate_closure_plan(self.plan, self.matrix)

    def test_remaining_budget_is_exact(self):
        jobs = remaining_jobs()
        self.assertEqual(len(jobs), 82)
        self.assertEqual(jobs[0]["sequence"], 176)
        self.assertEqual(jobs[-1]["sequence"], 257)
        self.assertEqual(remaining_rf_seconds(jobs), "3260.000075")
        self.assertFalse(any(job["mode"] == "WSPR" for job in jobs))

    def test_block_classes_are_disjoint(self):
        self.assertFalse(AUDIT_BLOCKED_ROWS & REPAIR_BLOCKED_ROWS)
        self.assertFalse(AUDIT_BLOCKED_ROWS & STRUCTURAL_WSPR_BLOCKED_ROWS)
        self.assertFalse(REPAIR_BLOCKED_ROWS & STRUCTURAL_WSPR_BLOCKED_ROWS)


if __name__ == "__main__":
    unittest.main()
