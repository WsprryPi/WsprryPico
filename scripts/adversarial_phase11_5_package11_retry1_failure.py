#!/usr/bin/env python3
"""Mutation assessment for the Package 11 Retry 1 failure result."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from phase11_5_inventory import require
from audit_phase11_5_package11_retry1_failure import validate_result


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mutations(value):
    changes = [
        ("status", ("status",), "PASS"),
        ("phase", ("phase11_5_status",), "CLOSED_6_OF_6_FAMILIES"),
        ("packet", ("packet_sha256",), "0" * 64),
        ("authorization", ("authorization",), "PACKAGE11-TWO-HOST-R6-RETRY2"),
        ("dependency", ("dependencies", "attempt1_result_sha256"), "0" * 64),
        ("clock-repair", ("completed_scope", "clock_poll_repair_observed"), False),
        ("warmups", ("completed_scope", "warmup_jobs"), 7),
        ("warmup-duration", ("completed_scope", "warmup_rf_duration_ns"), 7_000_000_000),
        ("classes", ("completed_scope", "production_class_records"), 2),
        ("adjustment", ("completed_scope", "maximum_adjustment_sha256"), "0" * 64),
        ("baseline", ("completed_scope", "matched_baseline_seconds"), 359),
        ("production-ready", ("completed_scope", "production_readiness_passed"), True),
        ("production-arm", ("completed_scope", "production_arm_accepted"), True),
        ("cycle-credit", ("completed_scope", "normal_cycles"), 1),
        ("r6-credit", ("completed_scope", "r6_credit"), True),
        ("timing", ("baseline_timing", "rf_max_service_gap_ns"), 2_849_392),
        ("resource-acceptance", ("baseline_timing", "resource_gate_accepted"), True),
        ("failure-class", ("failure", "classification"), "PRODUCT_FAILURE"),
        ("product-failure", ("failure", "product_failure"), True),
        ("resource-result", ("failure", "resource_result_accepted"), True),
        ("charge", ("actual_budget", "charged_rf_jobs"), 9),
        ("production-charge", ("actual_budget", "production_jobs_armed"), 1),
        ("automatic-retry", ("actual_budget", "automatic_retry_authorized"), True),
        ("cumulative", ("cumulative_package11_budget", "charged_rf_jobs"), 15),
        ("router-cause", ("external_events", "used_as_failure_cause"), True),
        ("capture-drop", ("capture", "client_kernel_drops"), 1),
        ("pico-restoration", ("restoration", "pico_a_empty_unowned_inactive"), False),
        ("reservation", ("restoration", "reservation_released_after_fresh_reconciliation"), False),
        ("host-restoration", ("restoration", "wspr4_fixture_restored"), False),
        ("cleanup", ("restoration", "cleanup_failures"), 1),
        ("evidence", ("evidence_sha256", "campaign.jsonl"), "0" * 64),
    ]
    result = []
    for name, path, replacement in changes:
        candidate = copy.deepcopy(value)
        target = candidate
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = replacement
        result.append((name, candidate))
    return result


def assess(value):
    validate_result(value)
    outcomes = []
    for name, candidate in mutations(value):
        try:
            validate_result(candidate)
        except Exception as error:
            outcomes.append({"name": name, "rejected": True,
                             "error_type": type(error).__name__})
        else:
            outcomes.append({"name": name, "rejected": False})
    require(all(item["rejected"] for item in outcomes),
            "Package 11 Retry 1 failure mutation accepted")
    validate_result(value)
    return {"schema": "phase11.5-package11-retry1-adversarial-v1",
            "status": "PASS", "mutation_count": len(outcomes),
            "all_mutations_rejected": True, "mutations": outcomes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    value = json.loads(args.result.read_text())
    result = assess(value)
    result["result_sha256"] = digest(args.result)
    result["adversarial_script_sha256"] = digest(Path(__file__))
    raw = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(raw)
    print(raw, end="")


if __name__ == "__main__":
    main()
