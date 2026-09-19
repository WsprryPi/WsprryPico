#!/usr/bin/env python3
"""Run supported-band WSPR jobs as finite consecutive three-slot groups."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from phase11_6.plan import BANDS, DIRECT_MAXIMUM_HZ, digest, validate
from phase11_6.wspr_group import group_digest, require_fixture_namespaces

RESERVATION_PATH = Path("/home/pi/phase11-5-shared-rf-reservation.json")


def save(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".pending")
    with temporary.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


class Journal:
    def __init__(self, path: Path):
        self.path = path
        self.sequence = 0

    def emit(self, kind: str, value: object) -> None:
        row = {
            "sequence": self.sequence,
            "kind": kind,
            "utc_ns": time.time_ns(),
            "monotonic_ns": time.monotonic_ns(),
            "value": value,
        }
        with self.path.open("a") as stream:
            stream.write(json.dumps(row, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.sequence += 1


def run(command: list[str], log: Path) -> subprocess.CompletedProcess:
    with log.open("xb") as output:
        return subprocess.run(command, stdout=output, stderr=subprocess.STDOUT,
                              check=False)


def label(value: str) -> str:
    return value.replace(":", "-").lower()


def reconciliation_binding(execution: Path,
                           browser_result: Path | None = None) -> dict:
    """Recover the exact USB principal after a partial controller transition."""
    if not execution.is_file():
        return {"session": uuid.uuid4().hex, "request_number": 0,
                "expected_job_id": None}
    exchanges = []
    for line in execution.read_text().splitlines():
        row = json.loads(line)
        if row.get("kind") == "usb_controller_exchange":
            exchanges.append(row["value"])
    if not exchanges:
        return {"session": uuid.uuid4().hex, "request_number": 0,
                "expected_job_id": None}
    loads = [value for value in exchanges if value.get("operation") == "LOAD"]
    selected = loads[-1] if loads else exchanges[-1]

    # The browser is deliberately the final mutating principal.  Its retained
    # request may have reached the target even when the response or runner did
    # not, so prefer an observed browser LOAD/LOAD_MESSAGE envelope.
    if browser_result is not None and browser_result.is_file():
        result = json.loads(browser_result.read_text())
        decoded = []
        for request in result.get("requests", []):
            value = request
            if isinstance(request, dict) and isinstance(request.get("postData"), str):
                value = json.loads(request["postData"])
            if isinstance(value, dict):
                decoded.append(value)
        browser_loads = [value for value in decoded
                         if value.get("operation") in {"LOAD", "LOAD_MESSAGE"}]
        if browser_loads:
            selected = browser_loads[-1]
            exchanges = decoded

    session = selected.get("session_id")
    if not isinstance(session, str):
        raise ValueError("Missing reconciliation principal")
    session_exchanges = [value for value in exchanges
                         if value.get("session_id") == session]
    request_numbers = [int(value["request_id"], 16)
                       for value in session_exchanges]
    body = selected.get("body") or {}
    return {"session": session, "request_number": max(request_numbers),
            "expected_job_id": body.get("job_id")}


def reconciliation_disposition(group_hash: str,
                               path: Path = RESERVATION_PATH) -> str:
    """Never reconcile a pre-reservation failure or somebody else's hold."""
    if not path.is_file():
        return "not-required-no-reservation"
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return "not-attempted-unreadable-reservation"
    if value.get("state") == "RELEASED":
        return "not-required-released-reservation"
    if (value.get("state") == "HELD"
            and value.get("packet_sha256") == group_hash):
        return "required-exact-held-reservation"
    return "not-attempted-foreign-or-invalid-reservation"


def prepare_attempts_root(root: Path) -> Path:
    attempts = root / "attempts"
    if not attempts.exists():
        attempts.mkdir(mode=0o700)
    if (not attempts.is_dir() or attempts.is_symlink()
            or attempts.stat().st_mode & 0o077):
        raise ValueError("Private regular attempts directory required")
    return attempts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--start-sequence", type=int, required=True)
    parser.add_argument("--attempt-reason", required=True)
    parser.add_argument("--fixture-process", type=int, required=True)
    parser.add_argument("--skip-band", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--capture-helper", type=Path, required=True)
    parser.add_argument("--qualification-src", type=Path, required=True)
    parser.add_argument("--production-binary", type=Path, required=True)
    parser.add_argument("--wsprd", type=Path, required=True)
    parser.add_argument("--enable-rf", action="store_true", required=True)
    args = parser.parse_args()
    if not args.enable_rf or os.geteuid() != 0:
        raise ValueError("Explicit Linux-root RF enablement required")
    plan = validate(json.loads(args.plan.read_text()))
    plan_hash = digest(plan)
    root = args.plan.resolve().parent
    require_fixture_namespaces(args.fixture_process)
    attempts_root = prepare_attempts_root(root)
    output = args.output.resolve()
    output.mkdir(mode=0o700, parents=True)
    if output.stat().st_mode & 0o077 or any(output.iterdir()):
        raise ValueError("Fresh private WSPR batch output required")
    journal = Journal(output / "batch.jsonl")
    bands = [band for band, frequency in BANDS.items()
             if frequency <= DIRECT_MAXIMUM_HZ and band not in set(args.skip_band)]
    if not bands:
        raise ValueError("Empty WSPR band selection")
    jobs_by_band = {
        band: [job for packet in plan["packets"] for job in packet["jobs"]
               if job["band"] == band and job["mode"] == "WSPR"
               and job["purpose"] == "nominal"]
        for band in bands
    }
    if any(len(jobs) != 3 for jobs in jobs_by_band.values()):
        raise ValueError("Incomplete WSPR group in plan")
    journal.emit("start", {
        "selection": "primary-wspr-consecutive-groups",
        "plan_sha256": plan_hash, "bands": bands,
        "planned_jobs": len(bands) * 3,
        "planned_rf_seconds": sum(
            job["planned_duration_ns"] for jobs in jobs_by_band.values() for job in jobs
        ) / 1e9,
        "automatic_retries": 0,
    })

    sequence = args.start_sequence
    completed = []
    for band in bands:
        jobs = jobs_by_band[band]
        attempts = []
        for offset, job in enumerate(jobs):
            attempt_sequence = sequence + offset
            path = attempts_root / f"attempt-{attempt_sequence:04d}.json"
            result = run([
                sys.executable, str(root / "scripts/phase11_6_attempt.py"), "create",
                "--plan", str(args.plan), "--job-id", job["id"],
                "--sequence", str(attempt_sequence),
                "--reason", args.attempt_reason,
                "--output", str(path),
            ], output / f"{attempt_sequence:04d}-attempt-create.log")
            if result.returncode != 0:
                journal.emit("stopped", {"stage": "attempt-create", "band": band,
                                         "returncode": result.returncode})
                return result.returncode
            attempts.append(path)
        group_path = root / "attempts" / f"wspr-group-{sequence:04d}-{band}.json"
        create = [
            sys.executable, str(root / "scripts/phase11_6_wspr_group.py"), "create",
            "--plan", str(args.plan), "--band", band,
        ]
        for path in attempts:
            create.extend(["--attempt-packet", str(path)])
        create.extend(["--output", str(group_path)])
        created = run(create, output / f"{sequence:04d}-group-create.log")
        if created.returncode != 0:
            journal.emit("stopped", {"stage": "group-create", "band": band,
                                     "returncode": created.returncode})
            return created.returncode
        group = json.loads(group_path.read_text())
        group_hash = group_digest(group)
        group_root = root / "attempts" / f"wspr-{sequence:04d}-{band}"
        journal.emit("group", {
            "band": band, "sequences": list(range(sequence, sequence + 3)),
            "jobs": group["execution_order"], "group_packet_sha256": group_hash,
        })
        physical = run([
            sys.executable, str(root / "scripts/run_phase11_6_wspr_group.py"),
            "--plan", str(args.plan), "--plan-sha256", plan_hash,
            "--group-packet", str(group_path), "--group-sha256", group_hash,
            "--output", str(group_root), "--capture-helper", str(args.capture_helper),
            "--qualification-src", str(args.qualification_src),
            "--production-binary", str(args.production_binary), "--enable-rf",
            "--fixture-process", str(args.fixture_process),
        ], output / f"{sequence:04d}-physical.log")
        if physical.returncode != 0:
            disposition = reconciliation_disposition(group_hash)
            reconciliation_returncode = None
            if disposition == "required-exact-held-reservation":
                reconciliation = root / "attempts" / f"wspr-{sequence:04d}-reconciliation"
                binding = reconciliation_binding(
                    group_root / "execution.jsonl",
                    group_root / "group/browser_raw/browser/browser-result.json",
                )
                command = [
                    sys.executable, str(root / "scripts/reconcile_phase11_6.py"),
                    "--root", str(root), "--session", binding["session"],
                    "--request-number", str(binding["request_number"]),
                    "--packet-sha256", group_hash,
                    "--output", str(reconciliation), "--authorize-console-abort", "--run",
                ]
                if binding["expected_job_id"] is not None:
                    command.extend(["--expected-job-id", binding["expected_job_id"]])
                reconciled = run(command, output / f"{sequence:04d}-reconciliation.log")
                reconciliation_returncode = reconciled.returncode
            journal.emit("stopped", {
                "stage": "physical", "band": band,
                "returncode": physical.returncode,
                "reconciliation_disposition": disposition,
                "reconciliation_returncode": reconciliation_returncode,
            })
            return physical.returncode or reconciliation_returncode or 1

        passed = True
        analyses = []
        attempts_by_job = {
            json.loads(path.read_text())["job_id"]: path for path in attempts
        }
        for job in jobs:
            analysis_root = root / "attempts" / (
                f"wspr-{sequence:04d}-{band}-{label(job['submission_path'])}-analysis"
            )
            analyzed = run([
                sys.executable, str(root / "scripts/analyze_phase11_6.py"),
                "--plan", str(args.plan), "--job-id", job["id"],
                "--attempt-packet", str(attempts_by_job[job["id"]]),
                "--run-result", str(group_root / "group" / job["submission_path"]
                                    / "result.json"),
                "--capture", str(group_root / "group" / job["submission_path"]
                                 / "capture/capture.cf32"),
                "--metadata", str(group_root / "group" / job["submission_path"]
                                  / "capture/capture.json"),
                "--output", str(analysis_root), "--wsprd", str(args.wsprd),
                "--qualification-src", str(args.qualification_src),
            ], output / f"{sequence:04d}-{label(job['submission_path'])}-analysis.log")
            analysis_file = analysis_root / "analysis.json"
            analysis_passed = (analyzed.returncode == 0 and analysis_file.is_file()
                               and json.loads(analysis_file.read_text()).get("passed") is True)
            analyses.append({"job_id": job["id"], "returncode": analyzed.returncode,
                             "passed": analysis_passed})
            passed = passed and analysis_passed
        journal.emit("group_complete", {
            "band": band, "group_packet_sha256": group_hash,
            "physical_returncode": physical.returncode, "analyses": analyses,
            "passed": passed,
        })
        if not passed:
            journal.emit("stopped", {"stage": "analysis", "band": band})
            return 1
        completed.append(band)
        sequence += 3

    final = {"status": "COMPLETE", "completed_bands": completed,
             "completed_jobs": len(completed) * 3, "next_sequence": sequence}
    save(output / "batch-result.json", final)
    journal.emit("finish", final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
