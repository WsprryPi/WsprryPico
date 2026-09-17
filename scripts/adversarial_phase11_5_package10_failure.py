#!/usr/bin/env python3
"""Adversarially assess the sanitized Package 10 failure publication."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from audit_phase11_5_package10_failure import validate_result


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mutations():
    return [
        ("false-closure", lambda v: v.__setitem__("status", "PACKAGE10_COMPLETE_R6_CLOSED")),
        ("phase-status", lambda v: v.__setitem__("phase11_5_status", "CLOSED_6_OF_6_FAMILIES")),
        ("acceptance-credit", lambda v: v.__setitem__("acceptance_credit", 1)),
        ("candidate-source", lambda v: v["candidate"].__setitem__("source_revision", "0" * 40)),
        ("package9-preservation", lambda v: v["diagnosis"].__setitem__(
            "package9_failure_preserved", False)),
        ("false-retest", lambda v: v["diagnosis"].__setitem__(
            "package9_resource_failure_retested", True)),
        ("resource-limit", lambda v: v["diagnosis"].__setitem__("resource_limit_bytes", 13000)),
        ("blocked-stage", lambda v: v["blocked_gate"].__setitem__("stage", "rf")),
        ("fixed-requirement", lambda v: v["blocked_gate"].__setitem__(
            "fixed_acceptance_requirement", False)),
        ("alternate-roles", lambda v: v["blocked_gate"].__setitem__(
            "alternate_roles_tested", False)),
        ("preflight-count", lambda v: v["execution"].__setitem__(
            "corrected_preflight_iterations", 12)),
        ("false-rf-work", lambda v: v["execution"].__setitem__("corrected_rf_jobs", 16)),
        ("false-workload", lambda v: v["execution"].__setitem__("full_workload_completed", True)),
        ("charged-duration", lambda v: v["budget"].__setitem__(
            "charged_rf_duration_ns", 360_800_000_000)),
        ("unused-duration", lambda v: v["budget"].__setitem__(
            "unused_authorized_rf_duration_ns", 119_200_000_000)),
        ("flash-count", lambda v: v["budget"].__setitem__("flashes", 1)),
        ("history-outcome", lambda v: v["preflight_history"][-1].__setitem__(
            "outcome", "PASS")),
        ("history-restoration", lambda v: v["preflight_history"][-1].__setitem__(
            "restored", False)),
        ("history-role", lambda v: v["preflight_history"][-2].__setitem__(
            "roles", v["preflight_history"][-1]["roles"])),
        ("pico-a-output", lambda v: v["final_inventory"]["pico_a"].__setitem__(
            "output_active", True)),
        ("reservation", lambda v: v["restoration"].__setitem__(
            "reservation_released", False)),
        ("fixture", lambda v: v["restoration"].__setitem__(
            "host_fixture_restored", False)),
        ("evidence", lambda v: v["evidence_sha256"].__setitem__(
            "final_client_log", "0" * 64)),
        ("auditor", lambda v: v.__setitem__("auditor_sha256", "0" * 64)),
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
            raise ValueError("Package 10 failure mutation accepted: " + name)
    validate_result(value)
    return {"schema": "phase11.5-package10-failure-adversarial-v1",
        "status": "PASS", "mutation_count": len(rejected),
        "all_mutations_rejected": True, "mutations": rejected,
        "failure_result_sha256": None,
        "adversarial_script_sha256": digest(Path(__file__))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    value = json.loads(args.result.read_text())
    result = assess(value)
    result["failure_result_sha256"] = digest(args.result)
    raw = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(raw)
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
