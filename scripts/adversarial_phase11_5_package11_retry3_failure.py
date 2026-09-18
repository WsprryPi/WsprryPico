#!/usr/bin/env python3
"""Mutation assessment for the Package 11 Retry 3 failure result."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from phase11_5_inventory import require
from audit_phase11_5_package11_retry3_failure import validate_result


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mutations(value):
    changes = [
        ("status", ("status",), "PASS"),
        ("phase", ("phase11_5_status",), "CLOSED_6_OF_6_FAMILIES"),
        ("packet", ("packet_sha256",), "0" * 64),
        ("authorization", ("authorization",), "PACKAGE11-TWO-HOST-R6-RETRY4"),
        ("dependency", ("dependencies", "retry2_result_sha256"), "0" * 64),
        ("retention", ("completed_scope", "terminal_retention_records"), 1),
        ("memory", ("completed_scope", "memory_available_bytes"), 164999),
        ("reservation", ("completed_scope", "reservation_acquired"), False),
        ("warmup", ("completed_scope", "warmup_jobs"), 7),
        ("cycle", ("completed_scope", "normal_cycles"), 0),
        ("r6-credit", ("completed_scope", "r6_credit"), True),
        ("runner", ("failure", "runner_message"), "PASS"),
        ("samples", ("failure", "usb_status_samples"), 119),
        ("events", ("failure", "usb_event_count"), 5),
        ("event-complete", ("failure", "usb_event_states"),
            ["armed", "empty", "loaded", "running"]),
        ("cadence", ("failure", "maximum_status_gap_ns"), 6000000001),
        ("terminal", ("failure", "matching_terminal_complete_output_inactive"), False),
        ("classification", ("failure", "classification"), "PRODUCT_FAILURE"),
        ("product", ("failure", "product_failure"), True),
        ("resource", ("failure", "resource_result_accepted"), True),
        ("retest", ("repair", "host_only_retest_status"), "FAIL"),
        ("retest-hash", ("repair", "host_only_retest_result_sha256"), "0" * 64),
        ("adversarial-hash", ("repair", "host_only_retest_adversarial_sha256"),
            "0" * 64),
        ("fresh-rf", ("repair", "fresh_rf_retest_required"), False),
        ("charge", ("actual_budget", "charged_rf_jobs"), 8),
        ("duration", ("actual_budget", "charged_rf_duration_ns"), 8000000000),
        ("retry", ("actual_budget", "automatic_retry_authorized"), True),
        ("cumulative", ("cumulative_package11_budget", "charged_rf_jobs"), 24),
        ("capture", ("capture", "campaign_capture_started"), False),
        ("drop", ("capture", "campaign_kernel_drops"), 1),
        ("pico", ("restoration", "pico_a_empty_unowned_inactive"), False),
        ("released", ("restoration", "reservation_reconciled_released"), False),
        ("host", ("restoration", "wspr4_fixture_restored"), False),
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
            "Package 11 Retry 3 failure mutation accepted")
    validate_result(value)
    return {"schema": "phase11.5-package11-retry3-adversarial-v1",
            "status": "PASS", "mutation_count": len(outcomes),
            "all_mutations_rejected": True, "mutations": outcomes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = json.loads(args.result.read_text())
    result = assess(value)
    result["result_sha256"] = digest(args.result)
    result["adversarial_script_sha256"] = digest(Path(__file__))
    raw = json.dumps(result, indent=2) + "\n"
    args.output.write_text(raw)
    print(raw, end="")


if __name__ == "__main__":
    main()
