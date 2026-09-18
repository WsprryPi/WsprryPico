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
from phase11_6.wspr_group import group_digest


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--start-sequence", type=int, required=True)
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
            path = root / "attempts" / f"attempt-{attempt_sequence:04d}.json"
            result = run([
                sys.executable, str(root / "scripts/phase11_6_attempt.py"), "create",
                "--plan", str(args.plan), "--job-id", job["id"],
                "--sequence", str(attempt_sequence),
                "--reason", "Initial frozen Phase 11.6 consecutive WSPR group",
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
        ], output / f"{sequence:04d}-physical.log")
        if physical.returncode != 0:
            reconciliation = root / "attempts" / f"wspr-{sequence:04d}-reconciliation"
            reconciled = run([
                sys.executable, str(root / "scripts/reconcile_phase11_6.py"),
                "--root", str(root), "--session", uuid.uuid4().hex,
                "--request-number", "0", "--packet-sha256", group_hash,
                "--output", str(reconciliation), "--run",
            ], output / f"{sequence:04d}-reconciliation.log")
            journal.emit("stopped", {
                "stage": "physical", "band": band,
                "returncode": physical.returncode,
                "reconciliation_returncode": reconciled.returncode,
            })
            return physical.returncode or reconciled.returncode or 1

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
