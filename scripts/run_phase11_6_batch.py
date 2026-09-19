#!/usr/bin/env python3
"""Run a finite, stop-on-first-failure slice of the Phase 11.6 campaign."""

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

from phase11_6.plan import digest, validate
from phase11_6_attempt import packet_digest


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


def label(job: dict) -> str:
    return job["id"].replace(":", "-").lower()


def select_jobs(plan: dict, selection: str) -> list[dict]:
    jobs = [job for packet in plan["packets"] for job in packet["jobs"]]
    if selection == "primary-non-wspr":
        return [job for job in jobs
                if job["purpose"] != "abort-authority-integration"
                and job["mode"] != "WSPR"]
    if selection == "primary-wspr":
        return [job for job in jobs
                if job["purpose"] != "abort-authority-integration"
                and job["mode"] == "WSPR"]
    raise ValueError("Unknown batch selection")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--selection", choices=("primary-non-wspr", "primary-wspr"),
                        required=True)
    parser.add_argument("--start-sequence", type=int, required=True)
    parser.add_argument(
        "--reason",
        default="Initial frozen Phase 11.6 primary matrix execution",
    )
    parser.add_argument("--skip-job", action="append", default=[])
    parser.add_argument("--max-jobs", type=int)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--capture-helper", type=Path, required=True)
    parser.add_argument("--qualification-src", type=Path, required=True)
    parser.add_argument("--production-binary", type=Path, required=True)
    parser.add_argument("--wsprd", type=Path, required=True)
    parser.add_argument("--enable-rf", action="store_true", required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise ValueError("Linux root required")
    plan = validate(json.loads(args.plan.read_text()))
    plan_hash = digest(plan)
    root = args.plan.resolve().parent
    output = args.output.resolve()
    output.mkdir(mode=0o700, parents=True)
    if output.stat().st_mode & 0o077 or any(output.iterdir()):
        raise ValueError("Fresh private batch output required")
    journal = Journal(output / "batch.jsonl")
    jobs = [job for job in select_jobs(plan, args.selection)
            if job["id"] not in set(args.skip_job)]
    if args.max_jobs is not None:
        if args.max_jobs <= 0:
            raise ValueError("Positive max-jobs required")
        jobs = jobs[:args.max_jobs]
    if not jobs:
        raise ValueError("Empty batch selection")
    journal.emit("start", {
        "selection": args.selection,
        "plan_sha256": plan_hash,
        "jobs": [job["id"] for job in jobs],
        "planned_jobs": len(jobs),
        "planned_rf_seconds": sum(job["planned_duration_ns"] for job in jobs) / 1e9,
        "automatic_retries": 0,
    })
    sequence = args.start_sequence
    completed = []
    for job in jobs:
        attempt = root / "attempts" / f"attempt-{sequence:04d}.json"
        attempt_root = root / "attempts" / f"{sequence:04d}-{label(job)}"
        analysis_root = root / "attempts" / f"{sequence:04d}-analysis"
        create_log = output / f"{sequence:04d}-attempt-create.log"
        result = run([
            sys.executable, str(root / "scripts/phase11_6_attempt.py"), "create",
            "--plan", str(args.plan), "--job-id", job["id"],
            "--sequence", str(sequence),
            "--reason", args.reason,
            "--output", str(attempt),
        ], create_log)
        if result.returncode != 0:
            journal.emit("stopped", {"stage": "attempt-create", "job_id": job["id"],
                                     "returncode": result.returncode})
            return result.returncode
        attempt_value = json.loads(attempt.read_text())
        attempt_hash = packet_digest(attempt_value)
        journal.emit("attempt", {"sequence": sequence, "job_id": job["id"],
                                 "attempt_packet_sha256": attempt_hash})
        runner = (root / "scripts/run_phase11_6_production.py"
                  if job["submission_path"] == "production"
                  else root / "scripts/run_phase11_6_packet.py")
        command = [
            sys.executable, str(runner), "--plan", str(args.plan),
            "--plan-sha256", plan_hash, "--job-id", job["id"],
            "--attempt-packet", str(attempt), "--attempt-sha256", attempt_hash,
            "--output", str(attempt_root), "--capture-helper", str(args.capture_helper),
            "--qualification-src", str(args.qualification_src), "--enable-rf",
        ]
        if job["submission_path"] == "production":
            command.extend(["--production-binary", str(args.production_binary)])
        physical = run(command, output / f"{sequence:04d}-physical.log")
        if physical.returncode != 0:
            reconciliation = root / "attempts" / f"{sequence:04d}-reconciliation"
            reconciled = run([
                sys.executable, str(root / "scripts/reconcile_phase11_6.py"),
                "--root", str(root), "--session", uuid.uuid4().hex,
                "--request-number", "0", "--packet-sha256", attempt_hash,
                "--output", str(reconciliation), "--authorize-console-abort", "--run",
            ] + (["--expected-job-id", attempt_value["wtp_job_id"]]
                 if attempt_value.get("wtp_job_id") else []),
                output / f"{sequence:04d}-reconciliation.log")
            journal.emit("stopped", {
                "stage": "physical", "sequence": sequence, "job_id": job["id"],
                "returncode": physical.returncode,
                "reconciliation_returncode": reconciled.returncode,
            })
            return physical.returncode or reconciled.returncode or 1
        analysis = run([
            sys.executable, str(root / "scripts/analyze_phase11_6.py"),
            "--plan", str(args.plan), "--job-id", job["id"],
            "--attempt-packet", str(attempt),
            "--run-result", str(attempt_root / "run-result.json"),
            "--capture", str(attempt_root / "job/capture/capture.cf32"),
            "--metadata", str(attempt_root / "job/capture/capture.json"),
            "--output", str(analysis_root), "--wsprd", str(args.wsprd),
            "--qualification-src", str(args.qualification_src),
        ], output / f"{sequence:04d}-analysis.log")
        passed = False
        analysis_file = analysis_root / "analysis.json"
        if analysis_file.is_file():
            passed = json.loads(analysis_file.read_text()).get("passed") is True
        journal.emit("job_complete", {
            "sequence": sequence, "job_id": job["id"],
            "attempt_packet_sha256": attempt_hash,
            "physical_returncode": physical.returncode,
            "analysis_returncode": analysis.returncode,
            "analysis_passed": passed,
        })
        if analysis.returncode != 0 or not passed:
            journal.emit("stopped", {"stage": "analysis", "sequence": sequence,
                                     "job_id": job["id"],
                                     "returncode": analysis.returncode})
            return analysis.returncode or 1
        completed.append(job["id"])
        sequence += 1
    final = {
        "status": "COMPLETE",
        "selection": args.selection,
        "completed_jobs": completed,
        "completed_count": len(completed),
        "next_sequence": sequence,
    }
    save(output / "batch-result.json", final)
    journal.emit("finish", final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
