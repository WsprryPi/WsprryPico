#!/usr/bin/env python3
"""Offline audit of retained and final Phase 11.6 closure evidence.

This program has no hardware imports.  It checks the six historical rows that
were waiting on packet audit, every successfully completed closure job, and
the first stopped closure attempt.  Raw IQ is retained in place and bound by
SHA-256 rather than copied into the repository.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from phase11_6.plan import (  # noqa: E402
    FIRMWARE_SOURCE,
    PEER_ACCEPTED_BOOT,
    PICO_ACCEPTED_BOOT,
    digest,
    validate,
)
from phase11_6_attempt import check as validate_attempt, packet_digest  # noqa: E402


HISTORICAL_ROWS = {
    ("630m", "QRSS"),
    ("630m", "FSKCW"),
    ("630m", "DFCW"),
    ("160m", "QRSS"),
    ("160m", "DFCW"),
    ("80m", "DFCW"),
}
PATHS = {"production", "browser_compact", "controller_disconnect"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f"JSON object: {path}")
    return value


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def exact_hash(candidates: list[Path], expected: str, label: str) -> Path:
    matches = [path for path in candidates if path.is_file() and sha256(path) == expected]
    require(matches, f"matching {label} SHA-256")
    return matches[0]


def attempt_directory(root: Path, sequence: int, job_id: str) -> Path:
    slug = job_id.replace(":", "-").lower().replace("browser_compact", "browser-compact")
    direct = root / "attempts" / f"{sequence:04d}-{slug}"
    if direct.is_dir():
        return direct
    candidates = [path for path in (root / "attempts").glob(f"{sequence:04d}-*")
                  if path.is_dir() and "analysis" not in path.name
                  and "reconciliation" not in path.name]
    candidates = [path for path in candidates
                  if all(part.lower().replace("_", "-")
                         in path.name.lower().replace("_", "-")
                         for part in job_id.split(":")[:4])]
    require(len(candidates) == 1, f"unique attempt directory {sequence}")
    return candidates[0]


def validate_receiver(capture: dict, metadata: dict, band_hz: int) -> None:
    settings = capture.get("actual_settings", {})
    require(
        capture.get("resolved_device") == {"driver": "sdrplay", "serial": "2404058C60"}
        and settings == {
            "format": "CF32",
            "sample_rate_hz": 250000,
            "bandwidth_hz": 200000,
            "center_frequency_hz": band_hz - 25000,
            "gain_db": 20,
            "channel": 0,
            "agc": False,
            "bias_tee": False,
        }
        and capture.get("overflow_count") == 0
        and capture.get("clipping_samples") == 0
        and capture.get("sample_count", 0) > 0
        and metadata.get("actual_settings") == settings
        and metadata.get("resolved_device") == capture.get("resolved_device")
        and metadata.get("retained_sample_count") == capture.get("sample_count")
        and metadata.get("overflow_count") == 0
        and metadata.get("clipping", {}).get("sample_count") == 0
        and metadata.get("first_read", {}).get("discarded") is True,
        "receiver identity/settings/integrity",
    )


def validate_analysis(analysis: dict, run_result: dict, mode: str,
                      capture_sha: str, metadata_sha: str) -> None:
    result = analysis.get("result", {})
    require(analysis.get("schema") == "phase11.6-analysis-v1",
            "analysis schema")
    require(analysis.get("job_id") == run_result.get("job_id")
            and analysis.get("band") == run_result.get("band")
            and analysis.get("mode") == mode, "analysis matrix-job identity")
    require(analysis.get("wtp_job_id") == run_result.get("wtp_job_id"),
            "analysis WTP job identity")
    require(analysis.get("capture_sha256") == capture_sha
            and analysis.get("metadata_sha256") == metadata_sha,
            "analysis capture/metadata binding")
    require(analysis.get("passed") is True and result.get("passed") is True
            and result.get("issues") == [], "independent analysis pass")
    if analysis.get("physical_result_sha256") is not None:
        require(analysis["physical_result_sha256"] == sha256(
            Path(run_result["_path"])), "analysis physical-result binding")
    if mode == "QRSS":
        require(result.get("alignment_s", -1) >= 0
                and len(result.get("observed_intervals_s", [])) == 3,
                "QRSS content/envelope")
    elif mode == "FSKCW":
        require(4.0 <= result.get("spacing_hz", 0) <= 6.0
                and len(result.get("measurements", [])) == 5,
                "FSKCW content/polarity")
    elif mode == "DFCW":
        measurements = result.get("measurements", [])
        expected = [row.get("expected_hz") for row in measurements]
        # ET E means dot, dash, dot.  The frozen campaign convention therefore
        # requires high, low, high expected carriers.
        require(len(expected) == 3 and expected[0] > expected[1]
                and expected[2] > expected[1]
                and 4.0 <= result.get("spacing_hz", 0) <= 6.0,
                "DFCW dot-high/dash-low content/polarity")
    elif mode == "TONE":
        require(len(result.get("observed_intervals_s", [])) == 1,
                "TONE single interval")
    else:
        raise ValueError("WSPR is outside this closure audit")


def validate_run(root: Path, sequence: int, evidence: dict, lineage: dict,
                 nominal_frequency_hz: int,
                 reanalysis_root: Path | None = None) -> dict:
    job_id = evidence["job_id"]
    directory = attempt_directory(root, sequence, job_id)
    run_path = exact_hash(
        [directory / "run-result.json", directory / "job/result.json"],
        evidence["run_result_sha256"], f"run-result {sequence}")
    run = load(run_path)
    run["_path"] = str(run_path)
    band, mode, _, submission, purpose = job_id.split(":")
    require(
        purpose == "nominal" and run.get("job_id") == job_id
        and run.get("band") == band and run.get("mode") == mode
        and run.get("submission_path") == submission
        and run.get("disposition") == "CAPTURED_REQUIRES_ANALYSIS",
        f"physical job binding {sequence}",
    )
    released = run.get("released_status", {})
    require(
        released.get("boot_id") == lineage["boot_id"]
        and released.get("output_active") is False
        and released.get("owner_id") is None
        and any(record.get("job_id") == run.get("wtp_job_id")
                and record.get("state") == "complete"
                and record.get("output_active") is False
                for record in released.get("terminal_records", [])),
        f"authoritative terminal/release {sequence}",
    )
    observer = run.get("observer", {})
    console = observer.get("console_final", {})
    if console:
        require(
            console.get("revision") == lineage["source_revision"][:12]
            and console.get("system_clock_hz") == lineage["system_clock_hz"]
            and console.get("rf_render_in_ram") is True
            and console.get("dma_errors") == 0
            and console.get("refill_irq_unpaired") == 0
            and console.get("refill_invalid_reserves") == 0
            and console.get("core0_stack_guard_valid") == 1
            and console.get("core1_stack_guard_valid") == 1
            and int(console.get("allocator_failures", "1")) == 0
            and console.get("tls_allocation_failures") == 0,
            f"source/configuration/resource identity {sequence}",
        )
    browser = run.get("browser", {})
    require(browser.get("status") == "PASS"
            and browser.get("page_loaded") is True
            and browser.get("manual_refresh_overlap") is True,
            f"browser observer {sequence}")
    require(run.get("controller_disconnect_after_arm") is True
            if submission == "controller_disconnect" else True,
            f"controller disconnect {sequence}")
    capture = run.get("capture", {})
    capture_path = directory / "job/capture/capture.cf32"
    metadata_path = directory / "job/capture/capture.json"
    require(sha256(capture_path) == evidence["capture_sha256"]
            == capture.get("capture_sha256"), f"capture SHA-256 {sequence}")
    require(sha256(metadata_path) == evidence["metadata_sha256"]
            == capture.get("metadata_sha256"), f"metadata SHA-256 {sequence}")
    metadata = load(metadata_path)
    require(metadata.get("output", {}).get("sha256") == sha256(capture_path),
            f"capture metadata output binding {sequence}")
    validate_receiver(capture, metadata, nominal_frequency_hz)
    candidates = list((root / "attempts").glob(
        f"{sequence:04d}-analysis*/analysis.json"))
    candidates.extend(directory.glob("analysis*/analysis.json"))
    analysis_path = exact_hash(candidates, evidence["analysis_sha256"],
                               f"analysis {sequence}")
    analysis = load(analysis_path)
    analysis_repair = None
    try:
        validate_analysis(
            analysis, run, mode, sha256(capture_path), sha256(metadata_path)
        )
    except ValueError as error:
        if str(error) != "analysis WTP job identity" or reanalysis_root is None:
            raise
        replacement_path = reanalysis_root / f"{sequence:04d}/analysis.json"
        replacement = load(replacement_path)
        validate_analysis(
            replacement, run, mode, sha256(capture_path), sha256(metadata_path)
        )
        analysis_repair = {
            "original_analysis_sha256": sha256(analysis_path),
            "original_analysis_audit": "FAIL_ANALYSIS_WTP_JOB_IDENTITY",
            "replacement_analysis_sha256": sha256(replacement_path),
            "replacement_analysis_audit": "PASS_NEW_ZERO_RF_REANALYSIS",
            "replacement_tool_provenance": replacement["tool_provenance"],
        }
        analysis_path = replacement_path
    execution_hash = evidence.get("execution_sha256") or evidence.get(
        "execution_jsonl_sha256")
    execution_path = directory / "execution.jsonl"
    if execution_hash is not None:
        require(sha256(execution_path) == execution_hash,
                f"execution journal SHA-256 {sequence}")
    attempt_file_hash = evidence.get("attempt_packet_file_sha256")
    if attempt_file_hash is not None:
        attempt_path = root / "attempts" / f"attempt-{sequence:04d}.json"
        require(sha256(attempt_path) == attempt_file_hash,
                f"attempt packet file SHA-256 {sequence}")
        canonical_hash = evidence.get("attempt_packet_sha256")
        if canonical_hash is not None:
            require(packet_digest(load(attempt_path)) == canonical_hash,
                    f"attempt packet canonical SHA-256 {sequence}")
    result = {
        "sequence": sequence,
        "job_id": job_id,
        "attempt_packet_sha256": evidence.get("attempt_packet_sha256"),
        "attempt_packet_file_sha256": attempt_file_hash,
        "execution_sha256": sha256(execution_path),
        "run_result_sha256": sha256(run_path),
        "capture_sha256": sha256(capture_path),
        "metadata_sha256": sha256(metadata_path),
        "analysis_sha256": sha256(analysis_path),
        "lineage": evidence["lineage"],
        "audit": "PASS",
    }
    if analysis_repair is not None:
        result["analysis_repair"] = analysis_repair
    return result


def audit_historical(matrix: dict, root: Path,
                     reanalysis_root: Path | None = None) -> list[dict]:
    results = []
    for row in matrix["rows"]:
        key = (row["band"], row["mode"])
        if key not in HISTORICAL_ROWS:
            continue
        lineage_names = set(row["evidence"]["source_lineages"])
        require(len(lineage_names) == 1, f"single historical lineage {key}")
        lineage_name = next(iter(lineage_names))
        lineage = matrix["evidence_lineages"][lineage_name]
        passing = [value for value in row["evidence"]["attempts"]
                   if value.get("run_result_sha256")]
        require({value.get("submission_path") or value["job_id"].split(":")[3]
                 for value in passing} == PATHS,
                f"three required paths {key}")
        attempts = []
        for value in passing:
            try:
                attempts.append(validate_run(
                    root, value["sequence"], value, lineage,
                    row["nominal_frequency_hz"], reanalysis_root
                ))
            except (KeyError, OSError, ValueError) as error:
                attempts.append({
                    "sequence": value["sequence"],
                    "job_id": value["job_id"],
                    "lineage": value["lineage"],
                    "audit": "FAIL",
                    "reason": str(error),
                })
        status = "PASS" if all(value["audit"] == "PASS" for value in attempts) else "FAIL"
        results.append({
            "band": row["band"],
            "mode": row["mode"],
            "lineage": lineage_name,
            "paths": sorted(PATHS),
            "attempts": attempts,
            "audit": status,
        })
    require({(row["band"], row["mode"]) for row in results} == HISTORICAL_ROWS,
            "complete historical audit row set")
    return results


def audit_final(plan: dict, root: Path) -> tuple[list[dict], dict]:
    batch_root = root / "batches/closure-0176-0257"
    batch_rows = jsonl(batch_root / "batch.jsonl")
    completed = [row["value"] for row in batch_rows
                 if row.get("kind") == "job_complete"]
    require(completed and all(row.get("physical_returncode") == 0
                              and row.get("analysis_returncode") == 0
                              and row.get("analysis_passed") is True
                              for row in completed), "completed batch rows")
    jobs = {job["id"]: job for packet in plan["packets"] for job in packet["jobs"]}
    results = []
    for row in completed:
        sequence = row["sequence"]
        job = jobs[row["job_id"]]
        attempt_path = root / "attempts" / f"attempt-{sequence:04d}.json"
        attempt = load(attempt_path)
        validate_attempt(attempt, plan, root)
        require(packet_digest(attempt) == row["attempt_packet_sha256"],
                f"closure attempt digest {sequence}")
        directory = attempt_directory(root, sequence, row["job_id"])
        run_path = directory / "run-result.json"
        run = load(run_path)
        run["_path"] = str(run_path)
        analysis_path = root / "attempts" / f"{sequence:04d}-analysis/analysis.json"
        analysis = load(analysis_path)
        capture_path = directory / "job/capture/capture.cf32"
        metadata_path = directory / "job/capture/capture.json"
        capture_sha, metadata_sha = sha256(capture_path), sha256(metadata_path)
        require(run.get("capture", {}).get("capture_sha256") == capture_sha
                and run.get("capture", {}).get("metadata_sha256") == metadata_sha,
                f"closure capture binding {sequence}")
        validate_receiver(run["capture"], load(metadata_path),
                          job["nominal_frequency_hz"])
        validate_analysis(analysis, run, job["mode"], capture_sha, metadata_sha)
        console = run["observer"]["console_final"]
        released = run["released_status"]
        require(
            console.get("revision") == FIRMWARE_SOURCE[:12]
            and console.get("status", {}).get("boot_id") == PICO_ACCEPTED_BOOT
            and console.get("system_clock_hz") == 138000000
            and console.get("rf_render_in_ram") is True
            and console.get("dma_errors") == 0
            and console.get("refill_irq_unpaired") == 0
            and console.get("refill_invalid_reserves") == 0
            and int(console.get("allocator_failures", "1")) == 0
            and console.get("tls_allocation_failures") == 0
            and released.get("boot_id") == PICO_ACCEPTED_BOOT
            and released.get("output_active") is False
            and released.get("owner_id") is None,
            f"closure source/boot/resources/release {sequence}",
        )
        results.append({
            "sequence": sequence,
            "job_id": row["job_id"],
            "attempt_packet_sha256": packet_digest(attempt),
            "attempt_packet_file_sha256": sha256(attempt_path),
            "execution_sha256": sha256(directory / "execution.jsonl"),
            "run_result_sha256": sha256(run_path),
            "capture_sha256": capture_sha,
            "metadata_sha256": metadata_sha,
            "analysis_sha256": sha256(analysis_path),
            "lineage": "status_admission_current",
            "audit": "PASS",
        })
    stopped_rows = [row["value"] for row in batch_rows if row.get("kind") == "stopped"]
    require(len(stopped_rows) == 1 and stopped_rows[0].get("stage") == "physical"
            and stopped_rows[0].get("returncode") != 0
            and stopped_rows[0].get("reconciliation_returncode") == 0,
            "single fail-stop with successful reconciliation")
    stopped = stopped_rows[0]
    sequence = stopped["sequence"]
    attempt_path = root / "attempts" / f"attempt-{sequence:04d}.json"
    attempt = load(attempt_path)
    validate_attempt(attempt, plan, root)
    directory = attempt_directory(root, sequence, stopped["job_id"])
    execution = jsonl(directory / "execution.jsonl")
    failures = [row for row in execution if row.get("kind") == "failure"]
    require(len(failures) == 1
            and failures[0]["value"] == {
                "type": "TimeoutError",
                "message": "Independent observer admission deadline",
            }
            and not any(
                row.get("kind") == "capture_ready"
                or (row.get("kind") == "wtp_tx"
                    and row.get("value", {}).get("operation")
                        in {"CLAIM", "LOAD", "ARM"})
                for row in execution
            )
            and not (directory / "run-result.json").exists()
            and not (directory / "job/capture").exists()
            and not (directory / "job/capture/capture.cf32").exists(),
            "stopped attempt was pre-ARM and zero-RF")
    reconciliation_path = root / "attempts" / f"{sequence:04d}-reconciliation/result.json"
    reconciliation = load(reconciliation_path)
    require(
        reconciliation.get("status") == "RECONCILED"
        and reconciliation.get("before", {}).get("boot_id") == PICO_ACCEPTED_BOOT
        and reconciliation.get("before", {}).get("output_active") is False
        and reconciliation.get("before", {}).get("owner_id") is None
        and reconciliation.get("after") == reconciliation.get("before")
        and reconciliation.get("reservation", {}).get("state") == "RELEASED"
        and reconciliation.get("reservation", {}).get("packet_sha256")
            == packet_digest(attempt),
        "stopped attempt authoritative inactive reconciliation",
    )
    failure = {
        "sequence": sequence,
        "job_id": stopped["job_id"],
        "attempt_packet_sha256": packet_digest(attempt),
        "attempt_packet_file_sha256": sha256(attempt_path),
        "execution_sha256": sha256(directory / "execution.jsonl"),
        "reconciliation_sha256": sha256(reconciliation_path),
        "stage": "pre-ARM timing admission",
        "rf_emitted": False,
        "automatic_retry": False,
        "reservation_released_after_authoritative_inactive": True,
        "disposition": "FAIL",
    }
    require(len(results) == 1 and results[0]["sequence"] == 176
            and sequence == 177, "authorized closure prefix accounting")
    return results, failure


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--historical-root", type=Path, required=True)
    parser.add_argument("--reanalysis-root", type=Path)
    parser.add_argument("--execution-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    matrix = load(args.matrix.resolve(strict=True))
    plan = validate(load(args.plan.resolve(strict=True)))
    reanalysis_root = (None if args.reanalysis_root is None
                       else args.reanalysis_root.resolve(strict=True))
    historical = audit_historical(
        matrix, args.historical_root.resolve(strict=True), reanalysis_root
    )
    completed, failure = audit_final(plan, args.execution_root.resolve(strict=True))
    by_row: dict[str, list[dict]] = defaultdict(list)
    for item in completed:
        band, mode = item["job_id"].split(":")[:2]
        by_row[f"{band}:{mode}"].append(item)
    result = {
        "schema": "phase11.6-closure-execution-audit-v1",
        "status": "STOPPED_ON_FIRST_FAILURE",
        "plan_sha256": digest(plan),
        "historical_packet_audits": historical,
        "new_completed_attempts": completed,
        "new_completed_rows": dict(by_row),
        "stop_failure": failure,
        "completed_jobs": len(completed),
        "completed_rf_seconds": sum(
            jobs["planned_duration_ns"] for jobs in (
                job for packet in plan["packets"] for job in packet["jobs"]
                if job["id"] in {value["job_id"] for value in completed}
            )
        ) / 1e9,
        "unexecuted_authorized_jobs": 80,
        "automatic_retries": 0,
        "thresholds_relaxed": False,
        "evidence_rebound": False,
        "dfcw_polarity": "dot-high/dash-low",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": result["status"],
                      "historical_rows": len(historical),
                      "completed_jobs": len(completed),
                      "failure_sequence": failure["sequence"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
