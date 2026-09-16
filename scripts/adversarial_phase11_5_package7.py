#!/usr/bin/env python3
"""Adversarially test the sanitized Package 7 closure result."""

import argparse
import copy
import json
from pathlib import Path

from audit_phase11_5_package7 import validate_result


def assess(result):
    """Require the intact result and reject each independently altered result."""
    validate_result(result)
    mutations = {
        "schema": lambda value: value.update(schema="phase11.5-package7-v0"),
        "status": lambda value: value.update(status="PACKAGE7_INCOMPLETE"),
        "phase-count": lambda value: value.update(phase11_5_status="OPEN_3_OF_6_FAMILIES"),
        "family-status": lambda value: value["family_status"].update(R4="OPEN"),
        "missing-row": lambda value: value["accepted_rows"].pop(),
        "duplicate-row": lambda value: value["all_r4_rows"].append(value["all_r4_rows"][0]),
        "candidate-source": lambda value: value["candidate"].update(source_revision="0" * 40),
        "candidate-image": lambda value: value["candidate"].update(image_sha256="0" * 64),
        "candidate-boot": lambda value: value["candidate"].update(boot_id="0" * 32),
        "candidate-device": lambda value: value["candidate"].update(device_id="0" * 32),
        "candidate-clock": lambda value: value["candidate"].update(system_clock_hz=132_000_000),
        "wsprrypi-source": lambda value: value["candidate"].update(
            wsprrypi_source_revision="0" * 40),
        "packet-hash": lambda value: value.update(packet_sha256="0" * 64),
        "rf-budget": lambda value: value["budget"].update(rf_jobs=10),
        "duration-budget": lambda value: value["budget"].update(
            planned_rf_duration_ns=214_000_000_000),
        "attempt-outcome": lambda value: value["budget"]["attempts"][0].update(
            outcome="accepted"),
        "zero-rf-failures": lambda value: value["budget"].update(zero_rf_failures=5),
        "foreign-state": lambda value: value["authority_and_storage"]["foreign_states"].pop(),
        "storage-etag": lambda value: value["authority_and_storage"]["storage_states"]
            ["running"].update(etag='"changed"'),
        "lost-state": lambda value: value["lost_operations"]["ARM"].update(state="running"),
        "lost-job": lambda value: value["lost_operations"]["ABORT"].update(
            job_id=value["lost_operations"]["LOAD"]["job_id"]),
        "lost-packets": lambda value: value["lost_operations"]["LOAD"].update(
            inbound_ciphertext_packets=0),
        "lost-response-ack": lambda value: value["lost_operations"]["ABORT"].update(
            client_response_acknowledged=True),
        "production-state": lambda value: value["production"]["armed"].update(state="running"),
        "production-terminal": lambda value: value["production"]["running"].update(
            terminal="completed"),
        "production-wire": lambda value: value["production"]["running"]["wire"][
            "mutations"].remove("ABORT"),
        "production-request": lambda value: value["production"]["running"].update(
            browser_request_id=value["production"]["armed"]["browser_request_id"]),
        "regression": lambda value: value["regressions"].update(resolver_failure="FAIL"),
        "source-impact": lambda value: value["source_impact"].update(
            pico_runtime_source_changes_after_candidate=1),
        "failure-retention": lambda value: value["failed_attempt_sha256"].popitem(),
        "final-inventory": lambda value: value["final_inventories"]["a"].update(
            state="running"),
        "restoration": lambda value: value["restoration"].update(
            installed_service_active=False),
        "evidence-hash": lambda value: value["evidence_sha256"].update(
            {"direct.jsonl": "0" * 63}),
    }

    rejected = []
    for name, mutate in mutations.items():
        candidate = copy.deepcopy(result)
        mutate(candidate)
        try:
            validate_result(candidate)
        except (AssertionError, KeyError, TypeError, ValueError, RuntimeError):
            rejected.append(name)
        else:
            raise AssertionError("Mutation survived: " + name)
    if rejected != list(mutations):
        raise AssertionError("Mutation rejection order/count drift")
    validate_result(result)
    return {
        "schema": "phase11.5-package7-adversarial-v1",
        "status": "PASS",
        "intact_result_before": "PASS",
        "mutations": len(mutations),
        "rejected": rejected,
        "intact_result_after": "PASS",
        "r4_closed": True,
        "phase11_5_status": "OPEN_4_OF_6",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(assess(json.loads(args.result.read_text())), indent=2))


if __name__ == "__main__":
    main()
