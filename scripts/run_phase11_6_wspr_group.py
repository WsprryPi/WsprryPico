#!/usr/bin/env python3
"""Execute one immutable three-slot Phase 11.6 WSPR group."""

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

from phase11_5_inventory import require
from phase11_5_rf_reservation import Reservation
from phase11_6.live import (Journal, configure_capture_validator,
                            require_capture_helper, save, settled_inventory,
                            sha256)
from phase11_6.plan import (PEER_DEVICE_ID, PEER_SERIAL, PICO_DEVICE_ID,
                            PICO_SERIAL, digest, validate)
from phase11_6.wspr_group import execute_wspr_group, group_digest, validate_group
from phase11_6_attempt import check as validate_attempt, packet_digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--group-packet", type=Path, required=True)
    parser.add_argument("--group-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--capture-helper", type=Path, required=True)
    parser.add_argument("--qualification-src", type=Path, required=True)
    parser.add_argument("--production-binary", type=Path, required=True)
    parser.add_argument("--enable-rf", action="store_true", required=True)
    args = parser.parse_args()
    if not args.enable_rf:
        print("Plan only; no process, network, USB, SDR or RF access.")
        return 0
    if os.name != "posix" or os.geteuid() != 0:
        raise ValueError("Linux root is required")

    plan = validate(json.loads(args.plan.read_text()))
    root = args.plan.resolve().parent
    require(digest(plan) == args.plan_sha256, "Immutable Phase 11.6 plan")
    group = json.loads(args.group_packet.read_text())
    planned_jobs = validate_group(group, plan, root)
    require(group_digest(group) == args.group_sha256,
            "Immutable Phase 11.6 WSPR group")
    attempts = {}
    for binding in group["attempts"]:
        path = Path(binding["attempt_packet"])
        attempt = json.loads(path.read_text())
        validate_attempt(attempt, plan, root)
        require(packet_digest(attempt) == binding["attempt_packet_sha256"]
                and sha256(path) == binding["attempt_packet_file_sha256"],
                "WSPR attempt packet binding")
        attempts[attempt["job_id"]] = attempt
    require(set(attempts) == {job["id"] for job in planned_jobs},
            "WSPR attempt job set")
    jobs = []
    for planned in planned_jobs:
        job = copy.deepcopy(planned)
        job["expected_job"] = copy.deepcopy(attempts[job["id"]]["effective_job"])
        jobs.append(job)

    output = args.output.resolve()
    output.mkdir(mode=0o700, parents=True)
    require(not output.stat().st_mode & 0o077 and not any(output.iterdir()),
            "Fresh private output root")
    helper = require_capture_helper(args.capture_helper)
    validator = configure_capture_validator(args.qualification_src)
    binary = args.production_binary.resolve(strict=True)
    require(binary.is_file() and os.access(binary, os.X_OK),
            "Reviewed production candidate executable")
    paused = (root / "installed-paused.txt").read_text()
    require("MainPID=0" in paused and "ActiveState=inactive" in paused,
            "Installed WsprryPi service is not authoritatively paused")

    journal = Journal(output / "execution.jsonl")
    reservation = Reservation(args.group_sha256)
    final_values = None
    try:
        journal.emit("start", {
            "plan_sha256": args.plan_sha256,
            "plan_file_sha256": sha256(args.plan),
            "group_packet_sha256": args.group_sha256,
            "group_packet_file_sha256": sha256(args.group_packet),
            "jobs": group["execution_order"],
            "planned_rf_seconds": group["planned_rf_seconds"],
            "capture_helper_sha256": sha256(helper),
            "capture_validator_sha256": validator,
            "production_binary_sha256": sha256(binary),
        })
        label = args.group_sha256[:12]
        before = {
            "a": settled_inventory(root, "phase116-wspr-before-a-" + label,
                                   PICO_SERIAL, PICO_DEVICE_ID, journal),
            "b": settled_inventory(root, "phase116-wspr-before-b-" + label,
                                   PEER_SERIAL, PEER_DEVICE_ID, journal),
        }
        reservation.acquire(before)
        journal.emit("reservation_acquired", json.loads(reservation.path.read_text()))
        result = execute_wspr_group(
            root, plan, jobs, output / "group", helper, binary, journal
        )
        final_values = {
            "a": settled_inventory(root, "phase116-wspr-after-a-" + label,
                                   PICO_SERIAL, PICO_DEVICE_ID, journal),
            "b": settled_inventory(root, "phase116-wspr-after-b-" + label,
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
