#!/usr/bin/env python3
"""Create or validate one immutable three-slot Phase 11.6 WSPR group."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from phase11_6.plan import validate
from phase11_6.wspr_group import compose_group, group_digest, validate_group
from phase11_6_attempt import check as validate_attempt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    create = sub.add_parser("create")
    create.add_argument("--plan", type=Path, required=True)
    create.add_argument("--band", required=True)
    create.add_argument("--attempt-packet", type=Path, action="append", required=True)
    create.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("validate")
    check.add_argument("--plan", type=Path, required=True)
    check.add_argument("--packet", type=Path, required=True)
    args = parser.parse_args()

    plan = validate(json.loads(args.plan.read_text()))
    tool_root = args.plan.resolve().parent
    if args.action == "create":
        if len(args.attempt_packet) != 3:
            raise ValueError("Exactly three WSPR attempt packets are required")
        paths = [path.resolve(strict=True) for path in args.attempt_packet]
        attempts = [json.loads(path.read_text()) for path in paths]
        for attempt in attempts:
            validate_attempt(attempt, plan, tool_root)
        group = compose_group(plan, args.band, attempts, paths, tool_root)
        validate_group(group, plan, tool_root)
        with args.output.open("x") as stream:
            json.dump(group, stream, indent=2, allow_nan=False)
            stream.write("\n")
    else:
        group = json.loads(args.packet.read_text())
        validate_group(group, plan, tool_root)

    print(json.dumps({
        "valid": True,
        "band": group["band"],
        "jobs": group["execution_order"],
        "group_sha256": group_digest(group),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
