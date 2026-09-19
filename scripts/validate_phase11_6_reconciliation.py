#!/usr/bin/env python3
"""Validate the reconciled Phase 11.6 matrix and minimum RF closure plan."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from phase11_6.reconciliation import (  # noqa: E402
    validate_closure_plan,
    validate_public_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("closure_plan", type=Path)
    args = parser.parse_args()
    matrix = json.loads(args.matrix.read_text())
    closure_plan = json.loads(args.closure_plan.read_text())
    validate_public_artifacts(matrix, args.matrix.parent)
    validate_closure_plan(closure_plan, matrix)
    print(json.dumps({
        "valid": True,
        "phase_status": matrix["phase_status"],
        "disposition_counts": matrix["disposition_counts"],
        "minimum_remaining_rf_job_count": closure_plan["minimum_remaining_rf_job_count"],
        "maximum_remaining_rf_seconds": closure_plan["maximum_remaining_rf_seconds"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
