#!/usr/bin/env python3
"""Adversarially assess the sanitized Package 9 failure publication."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from audit_phase11_5_package9_failure import validate_result


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mutations():
    return [
        ("status", lambda v: v.__setitem__("status", "PACKAGE9_COMPLETE_R6_CLOSED")),
        ("phase-status", lambda v: v.__setitem__("phase11_5_status", "CLOSED")),
        ("candidate-source", lambda v: v["candidate"].__setitem__("source_revision", "0" * 40)),
        ("workload-minutes", lambda v: v["completed_workload"].__setitem__(
            "normal_load_seconds", 1799)),
        ("workload-jobs", lambda v: v["completed_workload"].__setitem__("rf_jobs", 10)),
        ("lifecycle", lambda v: v["completed_workload"].__setitem__(
            "production_lifecycles_complete", False)),
        ("gate-limit", lambda v: v["failed_gate"].__setitem__("limit_bytes", 13000)),
        ("gate-baseline", lambda v: v["failed_gate"].__setitem__("baseline_bytes", 56824)),
        ("gate-terminal-count", lambda v: v["failed_gate"].__setitem__(
            "final_terminal_records", 8)),
        ("auditor-status", lambda v: v["closure_auditor"].__setitem__("status", "PASS")),
        ("budget-duration", lambda v: v["cumulative_budget"].__setitem__(
            "charged_rf_duration_ns", 1_200_000_000_001)),
        ("budget-remaining", lambda v: v["cumulative_budget"].__setitem__(
            "remaining_rf_duration_ns", 351_800_000_000)),
        ("flash-count", lambda v: v["cumulative_budget"].__setitem__("flashes", 5)),
        ("reservation", lambda v: v["restoration"].__setitem__(
            "reservation_released", False)),
        ("fixture", lambda v: v["restoration"].__setitem__(
            "host_fixture_restored", False)),
        ("evidence", lambda v: v["evidence_sha256"].__setitem__("campaign.jsonl", "0" * 64)),
    ]


def assess(value):
    validate_result(value)
    rejected = []
    for name, change in mutations():
        altered = copy.deepcopy(value)
        change(altered)
        try:
            validate_result(altered)
        except Exception as error:
            rejected.append({"mutation": name, "rejected": True,
                             "reason": str(error)})
        else:
            raise ValueError("Failure mutation accepted: " + name)
    validate_result(value)
    return {"schema": "phase11.5-package9-failure-adversarial-v1",
        "status": "PASS", "mutation_count": len(rejected),
        "all_mutations_rejected": True, "mutations": rejected,
        "failure_result_sha256": None,
        "adversarial_script_sha256": digest(Path(__file__))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    value = json.loads(args.result.read_text())
    result = assess(value)
    result["failure_result_sha256"] = digest(args.result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
