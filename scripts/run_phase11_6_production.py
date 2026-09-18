#!/usr/bin/env python3
"""Explicitly execute one immutable Phase 11.6 WsprryPi production job."""

import argparse
import copy
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from phase11_6.live import (Journal, configure_capture_validator,
                            execute_production_job, save, settled_inventory,
                            sha256)
from phase11_6.plan import (PEER_DEVICE_ID, PEER_SERIAL, PICO_DEVICE_ID,
                            PICO_SERIAL, digest, validate)
from phase11_5_rf_reservation import Reservation
from phase11_6_attempt import check as validate_attempt, packet_digest


CORRECTIVE_JOB = "160m:QRSS:0:production:nominal"
CORRECTIVE_SEQUENCE = 44
CORRECTIVE_REASON = (
    "Corrective repaired-candidate armed-interval clock-refinement "
    "requalification after verified capture-helper invocation repair"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--attempt-packet", type=Path, required=True)
    parser.add_argument("--attempt-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--capture-helper", type=Path, required=True)
    parser.add_argument("--qualification-src", type=Path, required=True)
    parser.add_argument("--production-binary", type=Path, required=True)
    parser.add_argument("--require-armed-clock-refinement", action="store_true")
    parser.add_argument("--enable-rf", action="store_true", required=True)
    args = parser.parse_args()
    if not args.enable_rf:
        print("Plan only; no process, network, USB, SDR or RF access.")
        return 0
    if os.name != "posix" or os.geteuid() != 0:
        raise ValueError("Linux root is required")
    plan = validate(json.loads(args.plan.read_text()))
    if digest(plan) != args.plan_sha256:
        raise ValueError("Immutable Phase 11.6 plan mismatch")
    jobs = [job for packet in plan["packets"] for job in packet["jobs"]
            if job["id"] == args.job_id]
    if len(jobs) != 1 or jobs[0]["submission_path"] != "production":
        raise ValueError("Exact production job not found")
    attempt = json.loads(args.attempt_packet.read_text())
    validate_attempt(attempt, plan, args.plan.resolve().parent)
    if (packet_digest(attempt) != args.attempt_sha256
            or attempt["job_id"] != args.job_id
            or attempt["runtime_job_id"] is not True):
        raise ValueError("Immutable production attempt packet mismatch")
    if args.require_armed_clock_refinement and not (
            args.job_id == CORRECTIVE_JOB
            and attempt["sequence"] == CORRECTIVE_SEQUENCE
            and attempt["reason"] == CORRECTIVE_REASON
            and attempt["planned_jobs"] == 1
            and attempt["planned_rf_seconds"] == 45.000001
            and attempt["maximum_submissions"] == 1
            and attempt["automatic_retries"] == 0):
        raise ValueError("Exact corrective clock-refinement authorization mismatch")
    job = copy.deepcopy(jobs[0])
    job["expected_job"] = copy.deepcopy(attempt["effective_job"])
    output = args.output.resolve()
    output.mkdir(mode=0o700)
    if output.stat().st_mode & 0o077 or any(output.iterdir()):
        raise ValueError("Fresh private output root required")
    helper = args.capture_helper.resolve(strict=True)
    validator = configure_capture_validator(args.qualification_src)
    binary = args.production_binary.resolve(strict=True)
    journal = Journal(output / "execution.jsonl")
    reservation = Reservation(args.attempt_sha256)
    final_values = None
    try:
        journal.emit("start", {
            "plan_sha256": args.plan_sha256,
            "plan_file_sha256": sha256(args.plan), "job_id": job["id"],
            "capture_helper_sha256": sha256(helper),
            "capture_validator_sha256": validator,
            "production_binary_sha256": sha256(binary),
            "attempt_packet_sha256": args.attempt_sha256,
            "attempt_packet_file_sha256": sha256(args.attempt_packet),
        })
        fixture_root = args.plan.resolve().parent
        label = args.attempt_sha256[:12]
        before = {
            "a": settled_inventory(fixture_root, "phase116-before-a-" + label,
                                   PICO_SERIAL, PICO_DEVICE_ID, journal),
            "b": settled_inventory(fixture_root, "phase116-before-b-" + label,
                                   PEER_SERIAL, PEER_DEVICE_ID, journal),
        }
        reservation.acquire(before)
        journal.emit("reservation_acquired", json.loads(reservation.path.read_text()))
        result = execute_production_job(
            fixture_root, plan, job, output / "job", helper, binary, journal,
            corrective_clock_refinement=args.require_armed_clock_refinement,
        )
        final_values = {
            "a": settled_inventory(fixture_root, "phase116-after-a-" + label,
                                   PICO_SERIAL, PICO_DEVICE_ID, journal),
            "b": settled_inventory(fixture_root, "phase116-after-b-" + label,
                                   PEER_SERIAL, PEER_DEVICE_ID, journal),
        }
        reservation.release(final_values)
        journal.emit("reservation_released", json.loads(reservation.path.read_text()))
        journal.emit("finish", result)
        save(output / "run-result.json", result)
    except BaseException as error:
        journal.emit("failure", {"type": type(error).__name__, "message": str(error)})
        raise
    finally:
        if reservation.held and final_values is None:
            journal.emit("reservation_left_held", json.loads(reservation.path.read_text()))
        reservation.close()
        journal.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
