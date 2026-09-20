#!/usr/bin/env python3
"""Mutation assessment for the Phase 11.7 closure boundaries."""

import argparse
import copy
import json
from pathlib import Path

from audit_phase11_7 import validate


def assess(root, result, pi_root=None):
    validate(root, result, pi_root)

    def set_value(path, value):
        def mutate(candidate):
            target = candidate
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
        return mutate

    def delete_value(path):
        def mutate(candidate):
            target = candidate
            for key in path[:-1]:
                target = target[key]
            del target[path[-1]]
        return mutate

    def add_wspr(candidate):
        candidate["phase11_6"]["accepted_rows"][0]["mode"] = "WSPR"

    def add_remote_ci(candidate):
        candidate["fresh_validation"]["remote_ci"] = {"status": "PASS"}

    mutations = [
        ("schema", set_value(["schema"], "phase11.7-joint-closure-v0")),
        ("status", set_value(["status"], "OPEN")),
        ("phase11_7_flag", set_value(["phase11_7_closed"], False)),
        ("phase11_flag", set_value(["phase11_closed_within_documented_scope"], False)),
        ("pico_revision", set_value(["repositories", "pico", "tested_revision"], "0" * 40)),
        ("pi_revision", set_value(["repositories", "pi", "tested_revision"], "0" * 40)),
        ("pico_pi_pin", set_value(["repositories", "pico", "interop_pi_pin"], "0" * 40)),
        ("pi_pico_pin", set_value(["repositories", "pi", "interop_pico_pin"], "0" * 40)),
        ("pass_count", set_value(["phase11_6", "disposition_counts", "PASS"], 14)),
        ("accepted_row_removed", lambda value: value["phase11_6"]["accepted_rows"].pop()),
        ("wspr_promoted", add_wspr),
        ("row_rebound", set_value(["phase11_6", "accepted_rows", 0, "lineages"],
                                   ["status_admission_current"])),
        ("lineage_identity", set_value(["phase11_6", "lineages", "browser_allocation",
                                        "source_revision"], "0" * 40)),
        ("wspr_count", set_value(["phase11_6", "wspr_rows_accepted"], 1)),
        ("campaign_authority", set_value(["phase11_6", "further_rf_authorized"], True)),
        ("unexecuted_jobs", set_value(["phase11_6", "remaining_unexecuted_jobs"], 79)),
        ("artifact_hash", set_value(["historical_artifact_sha256",
                                     "docs/development/phase11-6-matrix.json"], "0" * 64)),
        ("ledger_slice", lambda value: value["assertion_ledger"].pop()),
        ("ledger_evidence", set_value(["assertion_ledger", 0, "evidence_type"], "")),
        ("phase11_7_applicability", set_value(["assertion_ledger", 6, "applicability"],
                                               "PENDING_FINAL_VALIDATION")),
        ("host_as_target", set_value(["assertion_ledger", 1, "evidence_type"],
                                      "host tests prove target timing")),
        ("disconnect_as_inactive", set_value(["assertion_ledger", 0, "limitations"],
                                              "disconnect proves output inactive")),
        ("validation_failure", set_value(["fresh_validation", "pico_wtp_contract", "status"],
                                          "FAIL")),
        ("ctest_count", set_value(["fresh_validation", "pico_host_ctest", "groups"], 1)),
        ("mutation_count", set_value(["fresh_validation", "adversarial_mutations", "count"], 1)),
        ("unverified_ci_claim", add_remote_ci),
        ("external_docs_modified", set_value(["external_operator_documentation",
                                              "modified_by_phase11_7"], True)),
        ("external_docs_blocker", set_value(["external_operator_documentation",
                                             "blocks_phase11_closure"], True)),
        ("external_followup_removed", lambda value:
         value["external_operator_documentation"]["follow_ups"].pop()),
        ("hardware_operation", set_value(["operations", "hardware_operations"], 1)),
        ("phase12_closed", set_value(["future_work", "phase12"], "CLOSED")),
        ("phase13_closed", set_value(["future_work", "phase13"], "CLOSED")),
        ("operations_missing", delete_value(["operations", "rf_operations"])),
    ]

    rejected = []
    for name, mutate in mutations:
        candidate = copy.deepcopy(result)
        mutate(candidate)
        try:
            validate(root, candidate, pi_root)
        except (AssertionError, KeyError, TypeError):
            rejected.append(name)
        else:
            raise AssertionError(f"Adversarial mutation was accepted: {name}")

    return {
        "schema": "phase11.7-adversarial-result-v1",
        "status": "PASS",
        "mutations": len(mutations),
        "rejected": rejected,
        "hardware_operations": 0,
        "rf_operations": 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path,
                        default=Path("docs/development/phase11-7-result.json"))
    parser.add_argument("--pi-root", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = json.loads(args.result.read_text())
    print(json.dumps(assess(root, result, args.pi_root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
