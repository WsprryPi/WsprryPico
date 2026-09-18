#!/usr/bin/env python3
"""Mutation assessment for the Retry 3 host-only USB reducer retest."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from phase11_5_inventory import require
from audit_phase11_5_package11_usb_reducer_retest import validate_result


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mutations(value):
    changes = [
        ("status", ("status",), "FAIL"),
        ("packet", ("packet_sha256",), "0" * 64),
        ("journal", ("evidence_sha256", "campaign.jsonl"), "0" * 64),
        ("raw-log", ("evidence_sha256", "campaign.log"), "0" * 64),
        ("runner-source", ("source_sha256", "phase11_5_package9.py"), "0" * 64),
        ("retest-source", ("source_sha256",
            "phase11_5_package11_usb_reducer_retest.py"), "0" * 64),
        ("status-samples", ("usb_status_samples",), 119),
        ("empty-samples", ("usb_status_state_counts", "empty"), 94),
        ("event-count", ("usb_event_count",), 5),
        ("event-complete", ("usb_event_states",),
            ["armed", "empty", "loaded", "running"]),
        ("status-gap", ("maximum_status_gap_ns",), 6_000_000_001),
        ("status-response", ("maximum_status_response_ns",), 5_000_000_001),
        ("terminal", ("matching_terminal_complete_output_inactive",), False),
        ("old-reducer", ("old_status_only_reducer_rejects",), False),
        ("new-reducer", ("repaired_event_and_status_reducer_accepts",), False),
        ("pico", ("pico_access",), True),
        ("usb", ("usb_access",), True),
        ("network", ("network_access",), True),
        ("service", ("service_mutations",), 1),
        ("reservation", ("reservation_access",), True),
        ("rf-job", ("rf_jobs",), 1),
        ("rf-duration", ("rf_duration_ns",), 1),
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
            "Retry 3 USB reducer mutation accepted")
    validate_result(value)
    return {"schema": "phase11.5-package11-retry3-usb-reducer-adversarial-v1",
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
