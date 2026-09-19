#!/usr/bin/env python3
"""Run a finite, stop-on-first-failure slice of the Phase 11.6 campaign."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
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


def closure_jobs(plan: dict, closure: dict) -> list[dict]:
    if (closure.get("schema") != "phase11.6-closure-plan-v1"
            or closure.get("phase") != "11.6"
            or closure.get("phase_status") != "OPEN"
            or closure.get("evidence_cutoff_sequence") != 175
            or closure.get("minimum_remaining_rf_job_count") != 82
            or Decimal(str(closure.get("maximum_remaining_rf_seconds")))
                != Decimal("3260.000075")
            or closure.get("automatic_retries") != 0
            or closure.get("wspr_jobs") != 0
            or closure.get("fresh_attempt_packet_per_job") is not True
            or closure.get("dfcw_polarity") != "dot-high/dash-low"):
        raise ValueError("Exact Phase 11.6 closure authorization plan required")
    accepted = plan["accepted_configuration"]
    candidate = closure.get("current_candidate", {})
    companion = closure.get("companion", {})
    peer = closure.get("peer", {})
    if (candidate.get("source_revision") != accepted.get("source_revision")
            or candidate.get("uf2_sha256") != accepted.get("uf2_sha256")
            or candidate.get("boot_id") != accepted.get("accepted_boot_id")
            or candidate.get("pico_serial") != accepted.get("pico_serial")
            or candidate.get("device_id") != accepted.get("device_id")
            or candidate.get("board") != accepted.get("board")
            or candidate.get("system_clock_hz") != accepted.get("system_clock_hz")
            or candidate.get("pio_divider") != accepted.get("pio_divider")
            or candidate.get("engine") != accepted.get("engine")
            or candidate.get("renderer") != accepted.get("renderer")
            or candidate.get("output") != accepted.get("output")
            or companion.get("source_revision")
                != plan["repositories"]["WsprryPi"]
            or companion.get("binary_sha256")
                != plan["amendment"]["companion_binary_sha256"]
            or peer.get("pico_serial") != plan["peer"]["pico_serial"]
            or peer.get("device_id") != plan["peer"]["device_id"]
            or peer.get("boot_id") != plan["peer"]["accepted_boot_id"]):
        raise ValueError("Closure candidate, companion or peer binding mismatch")
    available = [job for packet in plan["packets"] for job in packet["jobs"]]
    resolved = []
    entries = closure.get("minimum_remaining_rf_jobs", [])
    for offset, entry in enumerate(entries):
        matches = [job for job in available
                   if job["band"] == entry.get("band")
                   and job["mode"] == entry.get("mode")
                   and job["submission_path"] == entry.get("submission_path")
                   and job["purpose"] == "nominal"
                   and job["matrix_credit"] is True]
        expected_seconds = Decimal(matches[0]["planned_duration_ns"]) / Decimal(10**9) \
            if len(matches) == 1 else None
        if (len(matches) != 1
                or entry.get("sequence") != 176 + offset
                or entry.get("mode") == "WSPR"
                or Decimal(str(entry.get("maximum_rf_seconds")))
                    != expected_seconds):
            raise ValueError("Closure job order, identity or budget mismatch")
        resolved.append(matches[0])
    if (len(resolved) != 82 or len({job["id"] for job in resolved}) != 82
            or sum(Decimal(job["planned_duration_ns"]) / Decimal(10**9)
                   for job in resolved) != Decimal("3260.000075")):
        raise ValueError("Closure job accounting mismatch")
    return resolved


def select_jobs(plan: dict, selection: str,
                closure: dict | None = None) -> list[dict]:
    jobs = [job for packet in plan["packets"] for job in packet["jobs"]]
    if selection == "closure-plan":
        if closure is None:
            raise ValueError("Closure plan required")
        return closure_jobs(plan, closure)
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
    parser.add_argument("--selection", choices=("primary-non-wspr", "primary-wspr",
                                                  "closure-plan"),
                        required=True)
    parser.add_argument("--closure-plan", type=Path)
    parser.add_argument("--closure-plan-sha256")
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
    closure = None
    closure_file_hash = None
    if args.selection == "closure-plan":
        if args.closure_plan is None or args.closure_plan_sha256 is None:
            raise ValueError("Immutable closure plan arguments required")
        closure_file_hash = hashlib.sha256(args.closure_plan.read_bytes()).hexdigest()
        if closure_file_hash != args.closure_plan_sha256:
            raise ValueError("Immutable closure plan file mismatch")
        closure = json.loads(args.closure_plan.read_text())
        if args.skip_job or args.max_jobs is not None or args.start_sequence != 176:
            raise ValueError("Closure execution cannot skip or truncate jobs")
    root = args.plan.resolve().parent
    output = args.output.resolve()
    output.mkdir(mode=0o700, parents=True)
    if output.stat().st_mode & 0o077 or any(output.iterdir()):
        raise ValueError("Fresh private batch output required")
    journal = Journal(output / "batch.jsonl")
    jobs = [job for job in select_jobs(plan, args.selection, closure)
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
        "closure_plan_file_sha256": closure_file_hash,
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
