#!/usr/bin/env python3
"""Produce the authoritative post-execution Phase 11.6 matrix."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path


INPUT_MATRIX_SHA256 = "f5dc043da0cf3b0e398777d07e5e6146b2faf76b5e94c7fed8797a5cbb33467f"
AUDIT_SHA256 = "b1198e1ef61c61d860e32481457f344d9fc87ba558cdb8aa62a50650dca72511"
EXECUTION_PLAN_SHA256 = "1d5c5451d7ac6389f163277342887978b258e4805872f3ec3ec46c5d9872983e"
ORIGIN_COMMIT = "f817fb79ddee50c690089b9964e39bcf0663a65f"
RESULT_NAME = "phase11-6-closure-execution-results.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f"JSON object: {path}")
    return value


def save(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".pending")
    with temporary.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-matrix", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--execution-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(sha256(args.input_matrix) == INPUT_MATRIX_SHA256,
            "exact pre-execution matrix")
    require(sha256(args.audit) == AUDIT_SHA256, "exact closure audit")
    require(sha256(args.execution_plan) == EXECUTION_PLAN_SHA256,
            "exact closure execution plan")
    matrix = load(args.input_matrix)
    audit = load(args.audit)
    require(audit.get("status") == "STOPPED_ON_FIRST_FAILURE"
            and audit.get("completed_jobs") == 1
            and audit.get("stop_failure", {}).get("sequence") == 177,
            "audited closure prefix")

    matrix["reconciled_date"] = "2026-09-19"
    matrix["reconciled_against_origin_devel"] = ORIGIN_COMMIT
    matrix["evidence_cutoff_sequence"] = 177
    matrix["closure_execution"] = {
        "status": "STOPPED_ON_FIRST_FAILURE",
        "authorization_input_commit": ORIGIN_COMMIT,
        "authorization_closure_plan_file_sha256":
            "4733941d6dd6b7ff80b8dceaa819397c12b6e49bd0512df0f902df44cb29b0fe",
        "authorization_matrix_file_sha256": INPUT_MATRIX_SHA256,
        "execution_plan_schema": "phase11.6-plan-v24",
        "execution_plan_sha256":
            "ef6624ccfa3be1b05ec914721071271fe1ef2bdb2afca5bffb200b1812ae279c",
        "execution_plan_file_sha256": EXECUTION_PLAN_SHA256,
        "audit_artifact": RESULT_NAME,
        "audit_artifact_sha256": AUDIT_SHA256,
        "completed_sequences": [176],
        "failed_sequence": 177,
        "failure_stage": "pre-ARM timing admission",
        "rf_jobs_completed": 1,
        "rf_seconds_completed": 45.000001,
        "rf_jobs_failed_after_start": 0,
        "zero_rf_failures": 1,
        "unexecuted_authorized_jobs": 80,
        "automatic_retries": 0,
        "authorization_consumed": True,
        "resume_prohibited_without_new_explicit_scope_and_RF_authorization": True,
    }
    matrix["evidence_lineages"]["status_admission_current"][
        "matrix_credit_from_closure_execution"
    ] = True
    matrix["public_evidence_artifacts"][RESULT_NAME] = AUDIT_SHA256
    matrix["public_evidence_artifacts"][
        "phase11-6-closure-execution-plan.json"
    ] = EXECUTION_PLAN_SHA256

    historical = {(value["band"], value["mode"]): value
                  for value in audit["historical_packet_audits"]}
    completed = audit["new_completed_attempts"][0]
    failure = audit["stop_failure"]
    for row in matrix["rows"]:
        key = (row["band"], row["mode"])
        if key in historical:
            packet = historical[key]
            row["evidence"]["packet_audit"] = {
                "artifact": RESULT_NAME,
                "artifact_sha256": AUDIT_SHA256,
                "result": packet["audit"],
                "attempt_sequences": [value["sequence"]
                                      for value in packet["attempts"]],
            }
            row["assertions"]["packet_audit_complete"] = True
            if packet["audit"] == "PASS":
                row["disposition"] = "PASS"
                row["reason"] = "all three retained paths pass the independent packet audit"
                row["assertions"]["path_evidence_complete"] = True
            else:
                failed = [value for value in packet["attempts"]
                          if value["audit"] == "FAIL"]
                require(len(failed) == 1 and failed[0]["reason"]
                        == "analysis WTP job identity", "exact historical audit failure")
                row["disposition"] = "FAIL"
                row["reason"] = (
                    "independent packet audit found that the production analysis "
                    "WTP job identity does not match the executed WTP job identity"
                )
                row["assertions"]["path_evidence_complete"] = False
        elif key == ("2200m", "FSKCW"):
            row["disposition"] = "FAIL"
            row["reason"] = (
                "browser-compact repair replacement passed, then the required "
                "controller-disconnect replacement failed the frozen pre-ARM timing "
                "admission with zero RF; no retry is authorized"
            )
            row["evidence"]["attempts"].extend([
                {
                    **completed,
                    "status": "ACCEPTED_PACKET_AUDIT",
                    "charged_rf_seconds": 45.000001,
                },
                {
                    **failure,
                    "status": "FAILED_TIMING_ADMISSION_NO_RF",
                    "charged_rf_seconds": 0.0,
                    "lineage": "status_admission_current",
                },
            ])
            row["evidence"]["source_lineages"] = ["status_admission_current"]
            row["evidence"]["packet_audit"] = {
                "artifact": RESULT_NAME,
                "artifact_sha256": AUDIT_SHA256,
                "result": "FAIL",
                "attempt_sequences": [176, 177],
            }
            row["assertions"]["packet_audit_complete"] = True
            row["assertions"]["path_evidence_complete"] = False
        elif key == ("2200m", "DFCW"):
            row["reason"] = (
                "the approved replacement was not reached because execution stopped "
                "at sequence 177; no further RF is authorized"
            )
        elif row["disposition"] == "NOT TESTED":
            row["reason"] = (
                "the authorized batch stopped at sequence 177 before this row; "
                "no retained row attempt exists through sequence 177"
            )

    counts = Counter(row["disposition"] for row in matrix["rows"])
    expected = {
        "PASS": 13,
        "FAIL": 9,
        "BLOCKED": 12,
        "NOT TESTED": 31,
        "UNSUPPORTED_CONFIGURATION": 10,
    }
    require(dict(counts) == expected, "post-execution disposition counts")
    matrix["disposition_counts"] = expected
    save(args.output, matrix)
    print(json.dumps({"valid": True, "disposition_counts": expected}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
