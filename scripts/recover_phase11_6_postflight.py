#!/usr/bin/env python3
"""Recover a completed Phase 11.6 job after a postflight inventory race."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from phase11_6.plan import validate
from phase11_6.recovery import recover_postflight_inventory
from phase11_6_attempt import check as validate_attempt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--attempt-packet", type=Path, required=True)
    parser.add_argument("--attempt-root", type=Path, required=True)
    parser.add_argument("--reconciliation", type=Path, required=True)
    parser.add_argument("--capture-helper", type=Path, required=True)
    parser.add_argument("--qualification-src", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = validate(json.loads(args.plan.read_text()))
    attempt = json.loads(args.attempt_packet.read_text())
    job = validate_attempt(attempt, plan, args.plan.resolve().parent)
    if job["id"] != args.job_id or not job["submission_path"].startswith("browser"):
        raise ValueError("Exact browser postflight recovery job")
    result = recover_postflight_inventory(
        args.plan.resolve().parent, plan, job, attempt, args.attempt_packet,
        args.attempt_root, args.reconciliation,
        args.capture_helper.resolve(strict=True), args.qualification_src, args.output,
    )
    print(json.dumps({
        "recovered": True,
        "job_id": result["job_id"],
        "capture_sha256": result["capture"]["capture_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
