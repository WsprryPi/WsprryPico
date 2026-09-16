#!/usr/bin/env python3
"""Adversarially test the Package 6 result and completion matrix."""

import argparse
import copy
import json
from pathlib import Path

from audit_phase11_5_package6 import validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    original_result = json.loads(args.result.read_text())
    original_matrix = json.loads(args.matrix.read_text())
    validate(original_result, original_matrix, args.repo.resolve())

    mutations = {
        "candidate-source": lambda r, m: r["candidate"].update(source_revision="0" * 40),
        "candidate-clock": lambda r, m: r["candidate"].update(system_clock_hz=132000000),
        "immutable-hash": lambda r, m: r["evidence_sha256"].update(
            {"phase11-5-package5-result.json": "0" * 64}),
        "source-range": lambda r, m: r["source_impact"]["packages2_4_to_current"].update(
            {"from": "0" * 40}),
        "source-file-list": lambda r, m: r["source_impact"]["packages2_4_to_current"]
            ["changed_production_files"].pop(),
        "source-decision": lambda r, m: r["source_impact"]["packages2_4_to_current"].update(
            {"decision": "unchanged"}),
        "group-remove": lambda r, m: r["r3_groups"].pop("USB"),
        "group-member": lambda r, m: r["r3_groups"]["JOB-MAX"]["assertions"].pop(),
        "group-evidence": lambda r, m: r["r3_groups"]["USB"].update(
            {"evidence": ["phase11-5-package5-result.json"]}),
        "group-disposition": lambda r, m: r["r3_groups"]["RECLAIM"].update(
            {"disposition": "OPEN"}),
        "matrix-r3-row": lambda r, m: next(
            row for row in m["assertions"] if row["id"] == "2.2c").update(
                {"classification": "affected and needing retest"}),
        "feature-evidence": lambda r, m: r["extended_features"]["FEATURE.4"].update(
            {"evidence": ["phase11-5-r3-v2-validation-006.json"]}),
        "feature-disposition": lambda r, m: r["extended_features"]["FEATURE.7"].update(
            {"disposition": "OPEN"}),
        "feature3-resolution": lambda r, m: r["extended_features"]["FEATURE.3"].update(
            {"resolution": "inspection only"}),
        "r1-resource-spread": lambda r, m: r["r1_4_resolution"].update(
            {"maximum_post_difference_bytes": 1025}),
        "matrix-r1-applicability": lambda r, m: next(
            row for row in m["assertions"] if row["id"] == "R1.4").update(
                {"classification": "affected and needing retest"}),
        "failed-attempt-preservation": lambda r, m: r.update(package5_failed_attempts=3),
        "family-status": lambda r, m: r["family_status"].update({"R3": "OPEN"}),
        "accepted-configuration": lambda r, m: m.update(
            accepted_configuration={"source": r["candidate"]["source_revision"]}),
        "family-count": lambda r, m: r["counts"].update(families_closed=4),
        "validation-count": lambda r, m: r["validation"].update(
            registered_ctest_groups=75),
        "hardware-charge": lambda r, m: r["hardware_charge"].update(rf_jobs=1),
        "restoration": lambda r, m: r["restoration"].update(
            reservation_state="HELD"),
        "invented-physical-credit": lambda r, m: r.update(
            new_physical_acceptance_assertions=1),
        "remaining-scope": lambda r, m: r["remaining"].pop(),
    }

    rejected = []
    for name, mutate in mutations.items():
        candidate_result = copy.deepcopy(original_result)
        candidate_matrix = copy.deepcopy(original_matrix)
        mutate(candidate_result, candidate_matrix)
        try:
            validate(candidate_result, candidate_matrix, args.repo.resolve())
        except (AssertionError, KeyError, TypeError, ValueError,
                FileNotFoundError, RuntimeError):
            rejected.append(name)
        else:
            raise AssertionError("Mutation survived: " + name)
    if rejected != list(mutations):
        raise AssertionError("Mutation rejection order/count drift")
    print(json.dumps({
        "schema": "phase11.5-package6-adversarial-v1",
        "status": "PASS",
        "intact_result": "PASS",
        "mutations": len(mutations),
        "rejected": rejected,
        "r3_closed": True,
        "phase11_5_status": "OPEN_3_OF_6",
    }, indent=2))


if __name__ == "__main__":
    main()
