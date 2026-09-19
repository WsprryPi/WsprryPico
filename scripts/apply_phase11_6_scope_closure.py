#!/usr/bin/env python3
"""Apply the explicit no-further-RF Phase 11.6 acceptance disposition."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


PRE_CLOSURE_MATRIX_SHA256 = (
    "1be962c10b46e9837a65742efebd7505c420345cafb161351d8e60c5a8e86f08"
)
SCOPE_DISPOSITION_SHA256 = (
    "d54924a9f7f819d486e743b875260b41d73031392a02b43d323e5daf009e369b"
)
INPUT_COMMIT = "842e201f9adfb754d4887762ff664183db985e16"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f"JSON object: {path}")
    return value


def save_new(path: Path, value: dict) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def row_id(row: dict) -> str:
    return f"{row['band']}:{row['mode']}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-matrix", type=Path, required=True)
    parser.add_argument("--scope-disposition", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(sha256(args.input_matrix) == PRE_CLOSURE_MATRIX_SHA256,
            "exact pre-closure matrix")
    require(sha256(args.scope_disposition) == SCOPE_DISPOSITION_SHA256,
            "exact scope disposition")
    matrix = load(args.input_matrix)
    decision = load(args.scope_disposition)
    require(matrix.get("phase_status") == "OPEN", "open pre-closure matrix")
    require(matrix.get("disposition_counts") == {
        "PASS": 13,
        "FAIL": 9,
        "BLOCKED": 12,
        "NOT TESTED": 31,
        "UNSUPPORTED_CONFIGURATION": 10,
    }, "exact pre-closure disposition counts")
    accepted = set(decision["accepted_rows"])
    removed_by_disposition = decision["removed_supported_rows"]
    removed = {name for names in removed_by_disposition.values() for name in names}
    boundary = set(decision["configuration_boundary_rows"])
    require(len(accepted) == 13 and len(removed) == 52 and len(boundary) == 10,
            "exact scope counts")
    require(not (accepted & removed or accepted & boundary or removed & boundary),
            "disjoint closure sets")
    rows = matrix["rows"]
    require({row_id(row) for row in rows} == accepted | removed | boundary,
            "complete closure partition")
    for row in rows:
        identity = row_id(row)
        if identity in accepted:
            require(row["disposition"] == "PASS", f"accepted PASS row: {identity}")
            row["phase_acceptance"] = "ACCEPTED"
        elif identity in boundary:
            require(row["disposition"] == "UNSUPPORTED_CONFIGURATION",
                    f"configuration boundary row: {identity}")
            row["phase_acceptance"] = "CONFIGURATION_BOUNDARY"
        else:
            require(identity in removed_by_disposition[row["disposition"]],
                    f"removed row disposition: {identity}")
            row["phase_acceptance"] = "REMOVED_FROM_PHASE_ACCEPTANCE"
    matrix["phase_status"] = "CLOSED_SCOPED"
    matrix["closed_date"] = "2026-09-19"
    matrix["closed_against_origin_devel"] = INPUT_COMMIT
    matrix["scope_disposition"] = {
        "artifact": "phase11-6-scope-disposition.json",
        "artifact_sha256": SCOPE_DISPOSITION_SHA256,
        "accepted_rows": 13,
        "removed_supported_rows": {
            "FAIL": 9,
            "BLOCKED": 12,
            "NOT TESTED": 31,
            "total": 52,
        },
        "configuration_boundary_rows": 10,
        "additional_rf_jobs": 0,
        "additional_rf_seconds": 0,
        "further_rf_authorized": False,
    }
    matrix["public_evidence_artifacts"][
        "phase11-6-scope-disposition.json"
    ] = SCOPE_DISPOSITION_SHA256
    save_new(args.output, matrix)
    print(json.dumps({
        "valid": True,
        "phase_status": matrix["phase_status"],
        "accepted_rows": 13,
        "removed_supported_rows": 52,
        "configuration_boundary_rows": 10,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
