#!/usr/bin/env python3
"""Create or validate the hardware-free immutable Phase 11.6 plan and matrix."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from phase11_6.plan import compose, initial_matrix, validate


def write_new(path: Path, value: dict) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    create = subparsers.add_parser("create", help="create a new plan and matrix")
    create.add_argument("plan", type=Path)
    create.add_argument("matrix", type=Path)
    check = subparsers.add_parser("validate", help="validate an existing plan")
    check.add_argument("plan", type=Path)
    args = parser.parse_args()
    if args.action == "create":
        plan = compose()
        write_new(args.plan, plan)
        write_new(args.matrix, initial_matrix(plan))
        print(json.dumps({"plan": str(args.plan), "matrix": str(args.matrix),
                          "planned_jobs": plan["planned_jobs"],
                          "planned_rf_seconds": plan["planned_rf_seconds"]}, indent=2))
    else:
        plan = validate(json.loads(args.plan.read_text()))
        print(json.dumps({"valid": True, "planned_jobs": plan["planned_jobs"],
                          "planned_rf_seconds": plan["planned_rf_seconds"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
