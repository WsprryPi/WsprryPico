#!/usr/bin/env python3
"""Mutation assessment for the Package 11 Retry 2 failure result."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from phase11_5_inventory import require
from audit_phase11_5_package11_retry2_failure import validate_result


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mutations(value):
    changes = [
        ("status", ("status",), "PASS"),
        ("phase", ("phase11_5_status",), "CLOSED_6_OF_6_FAMILIES"),
        ("packet", ("packet_sha256",), "0" * 64),
        ("authorization", ("authorization",), "PACKAGE11-TWO-HOST-R6-RETRY3"),
        ("dependency", ("dependencies", "retry1_result_sha256"), "0" * 64),
        ("credential-repair", ("completed_scope", "credential_repair_observed"), False),
        ("attempts", ("completed_scope", "memory_preflight_attempts"), 24),
        ("reservation", ("completed_scope", "reservation_acquired"), True),
        ("warmup", ("completed_scope", "warmup_jobs"), 1),
        ("r6-credit", ("completed_scope", "r6_credit"), True),
        ("threshold", ("memory_preflight", "required_heap_available_bytes"), 164_000),
        ("maximum", ("memory_preflight", "maximum_observed_bytes"), 165_000),
        ("shortfall", ("memory_preflight", "final_shortfall_bytes"), 0),
        ("allocator", ("memory_preflight", "allocator_failures"), 1),
        ("runner", ("memory_preflight", "runner_message"), "PASS"),
        ("ttl", ("retained_state", "terminal_record_ttl_seconds"), 3599),
        ("records", ("retained_state", "retry2_reconciliation_terminal_records"), 0),
        ("remaining", ("retained_state", "latest_retained_terminal_remaining_ns"), 0),
        ("classification", ("retained_state", "classification"), "PRODUCT_FAILURE"),
        ("product", ("retained_state", "product_failure"), True),
        ("resource", ("retained_state", "resource_result_accepted"), True),
        ("charge", ("actual_budget", "charged_rf_jobs"), 1),
        ("duration", ("actual_budget", "charged_rf_duration_ns"), 1_000_000_000),
        ("retry", ("actual_budget", "automatic_retry_authorized"), True),
        ("cumulative", ("cumulative_package11_budget", "charged_rf_jobs"), 17),
        ("capture", ("capture", "campaign_capture_started"), True),
        ("drop", ("capture", "client_kernel_drops"), 1),
        ("pico", ("restoration", "pico_a_empty_unowned_inactive"), False),
        ("released", ("restoration", "reservation_remained_released"), False),
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
            "Package 11 Retry 2 failure mutation accepted")
    validate_result(value)
    return {"schema": "phase11.5-package11-retry2-adversarial-v1",
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
