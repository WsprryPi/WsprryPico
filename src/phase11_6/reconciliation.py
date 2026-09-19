"""Validation rules for the reconciled Phase 11.6 matrix and closure plan."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
import hashlib
from pathlib import Path

from phase11_6.plan import BANDS, DIRECT_MAXIMUM_HZ, MODES


MATRIX_SCHEMA = "phase11.6-reconciled-matrix-v1"
CLOSURE_PLAN_SCHEMA = "phase11.6-closure-plan-v1"
ALLOWED_DISPOSITIONS = {
    "PASS", "FAIL", "BLOCKED", "NOT TESTED", "UNSUPPORTED_CONFIGURATION"
}
SHA256_HEX = set("0123456789abcdef")


PASS_ROWS = {
    ("2200m", "TONE"),
    ("2200m", "QRSS"),
    ("630m", "TONE"),
    ("160m", "TONE"),
    ("80m", "TONE"),
    ("60m", "TONE"),
    ("40m", "TONE"),
    ("630m", "QRSS"),
    ("630m", "FSKCW"),
    ("630m", "DFCW"),
    ("160m", "QRSS"),
    ("160m", "DFCW"),
    ("80m", "DFCW"),
}

FAIL_ROWS = {
    ("2200m", "WSPR"),
    ("160m", "FSKCW"),
    ("80m", "QRSS"),
    ("80m", "FSKCW"),
    ("60m", "QRSS"),
    ("60m", "FSKCW"),
    ("60m", "DFCW"),
    ("40m", "WSPR"),
    ("2200m", "FSKCW"),
}

AUDIT_BLOCKED_ROWS: set[tuple[str, str]] = set()

REPAIR_BLOCKED_ROWS = {
    ("2200m", "DFCW"),
}

STRUCTURAL_WSPR_BLOCKED_ROWS = {
    (band, "WSPR")
    for band, frequency in BANDS.items()
    if frequency <= DIRECT_MAXIMUM_HZ and band not in {"2200m", "40m"}
}

BLOCKED_ROWS = (
    AUDIT_BLOCKED_ROWS | REPAIR_BLOCKED_ROWS | STRUCTURAL_WSPR_BLOCKED_ROWS
)

NOT_TESTED_ROWS = {
    (band, mode)
    for band, frequency in BANDS.items()
    for mode in MODES
    if frequency <= DIRECT_MAXIMUM_HZ
    and mode != "WSPR"
    and (band, mode) not in PASS_ROWS | FAIL_ROWS | BLOCKED_ROWS
}

UNSUPPORTED_ROWS = {
    (band, mode)
    for band, frequency in BANDS.items()
    for mode in MODES
    if frequency > DIRECT_MAXIMUM_HZ
}


def expected_disposition(band: str, mode: str) -> str:
    key = (band, mode)
    if key in PASS_ROWS:
        return "PASS"
    if key in FAIL_ROWS:
        return "FAIL"
    if key in BLOCKED_ROWS:
        return "BLOCKED"
    if key in NOT_TESTED_ROWS:
        return "NOT TESTED"
    if key in UNSUPPORTED_ROWS:
        return "UNSUPPORTED_CONFIGURATION"
    raise ValueError(f"unclassified Phase 11.6 row: {band}/{mode}")


def remaining_jobs() -> list[dict]:
    """Return the minimum RF list without retrying retained failed rows."""
    jobs: list[dict] = []

    def add(band: str, mode: str, path: str, duration: str, basis: str) -> None:
        jobs.append(
            {
                "sequence": 176 + len(jobs),
                "band": band,
                "mode": mode,
                "submission_path": path,
                "maximum_rf_seconds": duration,
                "basis": basis,
            }
        )

    add("2200m", "FSKCW", "browser_compact", "45.000001", "repair replacement")
    add("2200m", "FSKCW", "controller_disconnect", "45.000001", "repair replacement")
    add("2200m", "DFCW", "controller_disconnect", "39.000001", "repair replacement")

    for band, frequency in BANDS.items():
        if frequency > DIRECT_MAXIMUM_HZ:
            continue
        if band == "2200m":
            continue
        if (band, "TONE") in NOT_TESTED_ROWS:
            add(band, "TONE", "controller_disconnect", "5.000000", "untested row")
        for mode, duration in (("QRSS", "45.000001"),
                               ("FSKCW", "45.000001"),
                               ("DFCW", "39.000001")):
            if (band, mode) not in NOT_TESTED_ROWS:
                continue
            for path in ("production", "browser_compact", "controller_disconnect"):
                add(band, mode, path, duration, "untested row")
    return jobs


def remaining_rf_seconds(jobs: list[dict] | None = None) -> str:
    values = remaining_jobs() if jobs is None else jobs
    return format(sum((Decimal(job["maximum_rf_seconds"]) for job in values),
                      Decimal("0")), "f")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= SHA256_HEX


def validate_matrix(matrix: dict) -> dict:
    _require(matrix.get("schema") == MATRIX_SCHEMA, "reconciled matrix schema")
    _require(matrix.get("phase_status") == "OPEN", "Phase 11.6 must remain open")
    _require(matrix.get("evidence_cutoff_sequence") == 177, "evidence cutoff")
    _require(matrix.get("thresholds_relaxed") is False, "threshold relaxation")
    _require(matrix.get("evidence_rebound") is False, "evidence rebinding")
    _require(matrix.get("dfcw_polarity") == "dot-high/dash-low", "DFCW polarity")
    execution = matrix.get("closure_execution", {})
    _require(
        execution.get("status") == "STOPPED_ON_FIRST_FAILURE"
        and execution.get("completed_sequences") == [176]
        and execution.get("failed_sequence") == 177
        and execution.get("rf_jobs_completed") == 1
        and execution.get("rf_seconds_completed") == 45.000001
        and execution.get("unexecuted_authorized_jobs") == 80
        and execution.get("automatic_retries") == 0
        and execution.get("authorization_consumed") is True,
        "closure execution outcome",
    )
    rows = matrix.get("rows")
    _require(isinstance(rows, list) and len(rows) == len(BANDS) * len(MODES),
             "complete matrix row count")
    keys = [(row.get("band"), row.get("mode")) for row in rows]
    _require(len(set(keys)) == len(keys), "duplicate matrix row")
    _require(set(keys) == {(band, mode) for band in BANDS for mode in MODES},
             "matrix row identities")
    for row in rows:
        disposition = row.get("disposition")
        _require(disposition in ALLOWED_DISPOSITIONS, "row disposition vocabulary")
        _require(disposition == expected_disposition(row["band"], row["mode"]),
                 f"row disposition: {row['band']}/{row['mode']}")
        evidence = row.get("evidence")
        _require(isinstance(evidence, dict), "row evidence object")
        lineages = matrix.get("evidence_lineages")
        _require(isinstance(lineages, dict), "evidence lineages")
        for lineage in evidence.get("source_lineages", []):
            _require(lineage in lineages, "row source lineage")
        for attempt in evidence.get("attempts", []):
            _require(attempt.get("lineage") in lineages, "attempt source lineage")
            for key, value in attempt.items():
                if key.endswith("_sha256"):
                    _require(_is_sha256(value), f"attempt SHA-256: {key}")
        if disposition in {"PASS", "FAIL"} or (row["band"], row["mode"]) in (
                AUDIT_BLOCKED_ROWS | REPAIR_BLOCKED_ROWS):
            _require(bool(evidence.get("attempts")),
                     f"attempt evidence: {row['band']}/{row['mode']}")
        if disposition in {"NOT TESTED", "UNSUPPORTED_CONFIGURATION"}:
            _require(evidence.get("attempts") == [],
                     f"unattempted row evidence: {row['band']}/{row['mode']}")
    actual_counts = Counter(row["disposition"] for row in rows)
    expected_counts = Counter(expected_disposition(band, mode)
                              for band in BANDS for mode in MODES)
    _require(actual_counts == expected_counts, "matrix disposition counts")
    _require(matrix.get("disposition_counts") == dict(expected_counts),
             "recorded disposition counts")
    return matrix


def validate_public_artifacts(matrix: dict, docs_directory: Path) -> dict:
    validate_matrix(matrix)
    docs_directory = docs_directory.resolve(strict=True)
    artifacts = matrix.get("public_evidence_artifacts")
    _require(isinstance(artifacts, dict) and artifacts, "public evidence artifacts")
    for name, expected in artifacts.items():
        _require(_is_sha256(expected), "public evidence SHA-256")
        path = docs_directory / name
        _require(path.is_file() and path.resolve().is_relative_to(docs_directory),
                 "public evidence path")
        _require(hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                 f"public evidence digest: {name}")
    plan_path = docs_directory / "phase11-6-plan.json"
    _require(
        hashlib.sha256(plan_path.read_bytes()).hexdigest()
        == matrix.get("base_plan_file_sha256"),
        "immutable base plan file digest",
    )
    return matrix


def validate_closure_plan(plan: dict, matrix: dict) -> dict:
    validate_matrix(matrix)
    _require(plan.get("schema") == CLOSURE_PLAN_SCHEMA, "closure plan schema")
    _require(plan.get("phase_status") == "OPEN", "closure plan phase status")
    _require(plan.get("evidence_cutoff_sequence") == 175, "closure plan cutoff")
    jobs = plan.get("minimum_remaining_rf_jobs")
    _require(jobs == remaining_jobs(), "minimum remaining RF job list")
    _require(plan.get("minimum_remaining_rf_job_count") == len(jobs) == 82,
             "minimum remaining RF job count")
    _require(plan.get("maximum_remaining_rf_seconds") == remaining_rf_seconds(jobs)
             == "3260.000075", "maximum remaining RF seconds")
    _require(not any(job["mode"] == "WSPR" for job in jobs), "WSPR retry prohibited")
    _require(plan.get("automatic_retries") == 0, "automatic retries")
    _require(plan.get("firmware_flashes") == 0, "firmware flash budget")
    _require(plan.get("bootsel_transitions") == 0, "BOOTSEL budget")
    _require(plan.get("controlled_reboots") == 0, "reboot budget")
    _require(plan.get("configuration_writes") == 0, "configuration-write budget")
    _require(plan.get("closure_after_execution") is False,
             "RF execution cannot itself close Phase 11.6")
    expected_candidate = dict(matrix["evidence_lineages"]["status_admission_current"])
    expected_candidate.pop("matrix_credit_from_closure_execution", None)
    expected_candidate.update({
        "pico_serial": "0BF4B4AEC9FFB344",
        "device_id": "fd6127d11d6aca42a9905fa3fb1bf1d5",
        "hostname": "wsprrypico-0a60df.local",
    })
    _require(plan.get("current_candidate") == expected_candidate,
             "current closure candidate identity")
    _require(plan.get("dfcw_polarity") == "dot-high/dash-low",
             "closure DFCW polarity")
    _require(plan.get("wspr_jobs") == 0, "closure WSPR job count")
    return plan
