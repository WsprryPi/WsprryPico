#!/usr/bin/env python3
"""Create or validate one immutable Phase 11.6 physical attempt packet."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from phase11_6.plan import canonical, digest, validate


SCHEMA = "phase11.6-attempt-v3"
LEGACY_SCHEMA = "phase11.6-attempt-v2"
DIRECT_TOOLS = (
    "src/phase11_6/live.py",
    "src/phase11_6/plan.py",
    "scripts/run_phase11_6_packet.py",
    "scripts/run_phase11_6_production.py",
    "scripts/phase11_6_attempt.py",
    "scripts/phase11_6_browser_watch.js",
    "scripts/phase11_6_browser_submit.js",
    "scripts/phase11_5_inventory.py",
    "scripts/phase11_5_package9.py",
    "scripts/phase11_5_pilot.py",
    "scripts/phase11_5_rf_reservation.py",
    "scripts/rf_wtp.py",
    "scripts/validate_wtp_contract.py",
)
LEGACY_TOOLS = (
    "src/phase11_6/live.py",
    "scripts/run_phase11_6_packet.py",
    "scripts/run_phase11_6_production.py",
    "scripts/phase11_6_browser_watch.js",
    "scripts/phase11_6_browser_submit.js",
)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def packet_digest(packet):
    return hashlib.sha256(canonical(packet)).hexdigest()


def job_digest(job):
    return hashlib.sha256(canonical(job)).hexdigest()


def tool_hashes(root, paths):
    return {relative: file_hash(root / relative) for relative in paths}


def attempt_job_id(plan, job, sequence):
    value = f"phase11.6:{digest(plan)}:{job['id']}:{sequence}".encode()
    return hashlib.sha256(value).hexdigest()[:32]


def effective_job(plan, job, sequence):
    value = copy.deepcopy(job["expected_job"])
    if job["submission_path"] != "production":
        value["job_id"] = attempt_job_id(plan, job, sequence)
    return value


def effective_compact_request(plan, job, sequence):
    if job["submission_path"] != "browser_compact":
        return None
    value = copy.deepcopy(job["compact_request"])
    value["job_id"] = attempt_job_id(plan, job, sequence)
    return value


def check(packet, plan, root):
    if (packet.get("schema") not in {SCHEMA, LEGACY_SCHEMA}
            or packet.get("plan_sha256") != digest(plan)):
        raise ValueError("attempt schema/plan")
    jobs = [job for part in plan["packets"] for job in part["jobs"]
            if job["id"] == packet.get("job_id")]
    if len(jobs) != 1:
        raise ValueError("attempt job/path")
    job = jobs[0]
    sequence = packet.get("sequence")
    expected_effective = (effective_job(plan, job, sequence)
                          if isinstance(sequence, int) and sequence > 0 else None)
    expected_wtp_id = (None if job["submission_path"] == "production"
                       else expected_effective["job_id"])
    expected_compact = effective_compact_request(plan, job, sequence)
    if (packet.get("planned_jobs") != 1
            or packet.get("planned_rf_seconds") != job["planned_duration_ns"] / 1e9
            or packet.get("maximum_submissions") != 1
            or packet.get("automatic_retries") != 0
            or expected_effective is None
            or not isinstance(packet.get("reason"), str)
            or not packet["reason"]
            or packet.get("plan_expected_job_sha256") != job_digest(job["expected_job"])
            or packet.get("effective_job") != expected_effective
            or packet.get("effective_job_sha256") != job_digest(expected_effective)
            or packet.get("wtp_job_id") != expected_wtp_id
            or packet.get("runtime_job_id") is not
                (job["submission_path"] == "production")
            or packet.get("effective_compact_request") != expected_compact
            or packet.get("effective_compact_request_sha256") !=
                (None if expected_compact is None else job_digest(expected_compact))):
        raise ValueError("attempt budget/reason")
    tools = packet.get("tool_sha256", {})
    expected = tool_hashes(
        root, DIRECT_TOOLS if packet["schema"] == SCHEMA else LEGACY_TOOLS
    )
    if tools != expected:
        raise ValueError("attempt tool identity")
    return job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    create = sub.add_parser("create")
    create.add_argument("--plan", type=Path, required=True)
    create.add_argument("--job-id", required=True)
    create.add_argument("--sequence", type=int, required=True)
    create.add_argument("--reason", required=True)
    create.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("validate")
    verify.add_argument("--plan", type=Path, required=True)
    verify.add_argument("--packet", type=Path, required=True)
    args = parser.parse_args()
    plan = validate(json.loads(args.plan.read_text()))
    root = args.plan.resolve().parent
    if args.action == "create":
        jobs = [job for part in plan["packets"] for job in part["jobs"]
                if job["id"] == args.job_id]
        if len(jobs) != 1:
            raise ValueError("job not found")
        job = jobs[0]
        packet = {
            "schema": SCHEMA,
            "plan_sha256": digest(plan),
            "sequence": args.sequence,
            "job_id": job["id"],
            "wtp_job_id": (None if job["submission_path"] == "production"
                           else attempt_job_id(plan, job, args.sequence)),
            "runtime_job_id": job["submission_path"] == "production",
            "plan_expected_job_sha256": job_digest(job["expected_job"]),
            "effective_job": effective_job(plan, job, args.sequence),
            "effective_compact_request": effective_compact_request(
                plan, job, args.sequence
            ),
            "planned_jobs": 1,
            "planned_rf_seconds": job["planned_duration_ns"] / 1e9,
            "maximum_submissions": 1,
            "automatic_retries": 0,
            "reason": args.reason,
            "tool_sha256": tool_hashes(root, DIRECT_TOOLS),
        }
        packet["effective_job_sha256"] = job_digest(packet["effective_job"])
        packet["effective_compact_request_sha256"] = (
            None if packet["effective_compact_request"] is None
            else job_digest(packet["effective_compact_request"])
        )
        check(packet, plan, root)
        with args.output.open("x") as stream:
            json.dump(packet, stream, indent=2); stream.write("\n")
    else:
        packet = json.loads(args.packet.read_text())
        check(packet, plan, root)
    print(json.dumps({"valid": True, "packet_sha256": packet_digest(packet),
                      "job_id": packet["job_id"], "wtp_job_id": packet["wtp_job_id"]}))


if __name__ == "__main__":
    main()
