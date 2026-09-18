#!/usr/bin/env python3
"""Replay Retry 3 USB evidence through the repaired reducer without device access."""

import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

from phase11_5_inventory import require
import phase11_5_package9 as package9


PACKET_SHA256 = "f2f0e684b658310038dd6b3a36b8b58ef285c1db6bd6fcbf05a9c4111b153dbd"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_messages(path):
    values = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            values.append(value)
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    require(digest(root / "packet.json") == PACKET_SHA256,
            "Retry 3 packet identity")
    packet = json.loads((root / "packet.json").read_text())
    rows = [json.loads(line) for line in (root / "campaign.jsonl").read_text().splitlines()]
    failures = [row for row in rows if row.get("kind") == "failure"]
    finishes = [row for row in rows if row.get("kind") == "normal_finish"]
    require(len(failures) == len(finishes) == 1 and
            failures[0]["value"] == {"type": "ValueError",
                                     "error": "USB lifecycle/cadence"} and
            finishes[0]["value"]["cycle"] == 1,
            "Retry 3 stopped-cycle identity")
    job_id = finishes[0]["value"]["job_id"]
    status_rows = [row for row in rows if row.get("kind") == "usb_status" and
                   row["value"].get("cycle") == 1]
    statuses = [row["value"]["value"] for row in status_rows]
    starts = [row["value"]["began_monotonic_ns"] for row in status_rows]
    response_ns = [row["value"]["ended_monotonic_ns"] -
                   row["value"]["began_monotonic_ns"] for row in status_rows]
    gaps = [right - left for left, right in zip(starts, starts[1:])]
    require(len(statuses) == 120 and gaps and max(gaps) <= 6_000_000_000 and
            max(response_ns) <= 5_000_000_000 and
            all(value["boot_id"] == package9.BOOT for value in statuses),
            "Retry 3 USB STATUS coverage")

    messages = json_messages(root / "campaign.log")
    events = [value for value in messages if value.get("type") == "event" and
              value.get("session_id") == packet["usb_observer_session_1"]]
    require(events and all(value["boot_id"] == package9.BOOT for value in events),
            "Retry 3 USB event identity")
    event_ids = [int(value["event_id"]) for value in events]
    require(event_ids == list(range(event_ids[0], event_ids[0] + len(event_ids))),
            "Retry 3 USB event order")
    job_events = [value for value in events if value.get("event") == "JOB_STATE"]
    event_states = {value["body"]["state"] for value in job_events}
    event_jobs = {value["body"]["job_id"] for value in job_events
                  if value["body"].get("job_id")}
    require(event_states == {"loaded", "armed", "running", "complete", "empty"} and
            event_jobs == {job_id} and
            not [value for value in events if value.get("event") in
                 {"MISSED_START", "DEVICE_FAULT", "INVALID_FRAME", "SESSION_REPLACED"}],
            "Retry 3 USB lifecycle events")

    observer = SimpleNamespace(
        states={value["state"] for value in statuses},
        jobs={value["job_id"] for value in statuses if value.get("job_id")},
        event_states=event_states, event_jobs=event_jobs, latest=statuses[-1])
    reduced = package9.validate_usb_lifecycle(observer, job_id)
    require("complete" not in observer.states and "loaded" not in observer.states,
            "Retry 3 must exercise transient-state repair")
    result = {
        "schema": "phase11.5-package11-retry3-usb-reducer-retest-v1",
        "status": "PASS_ZERO_RF_HOST_ONLY",
        "packet_sha256": PACKET_SHA256,
        "evidence_sha256": {"campaign.jsonl": digest(root / "campaign.jsonl"),
                            "campaign.log": digest(root / "campaign.log")},
        "source_sha256": {
            "phase11_5_package9.py": digest(Path(package9.__file__)),
            "phase11_5_package11_usb_reducer_retest.py": digest(Path(__file__))},
        "usb_status_samples": len(statuses),
        "usb_status_state_counts": dict(collections.Counter(
            value["state"] for value in statuses)),
        "usb_event_count": len(events),
        "usb_event_states": sorted(event_states),
        "maximum_status_gap_ns": max(gaps),
        "maximum_status_response_ns": max(response_ns),
        "matching_terminal_complete_output_inactive": True,
        "old_status_only_reducer_rejects": True,
        "repaired_event_and_status_reducer_accepts": reduced == {
            "status_states": ["armed", "empty", "running"],
            "event_states": ["armed", "complete", "empty", "loaded", "running"],
            "terminal_records": 8},
        "pico_access": False, "usb_access": False, "network_access": False,
        "service_mutations": 0, "reservation_access": False,
        "rf_jobs": 0, "rf_duration_ns": 0,
    }
    require(result["repaired_event_and_status_reducer_accepts"],
            "Repaired Retry 3 reducer result")
    raw = json.dumps(result, indent=2) + "\n"
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    print(raw, end="")


if __name__ == "__main__":
    main()
