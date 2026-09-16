#!/usr/bin/env python3
"""Hold one durable two-board RF reservation across Package 7."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from phase11_5_inventory import require
from phase11_5_package7_plan import validate
from phase11_5_rf_reservation import Reservation


def inventory(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    row, = [value for value in rows if value["kind"] == "finish"]
    require(row["value"]["result"] == "READ_ONLY_INVENTORY" and
            time.monotonic_ns() - row["monotonic_ns"] <= 30_000_000_000,
            "Reservation inventory is not fresh")
    return row["value"]


def save(path, value):
    temporary = path.with_suffix(".tmp")
    with temporary.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--reconcile-release", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no RF reservation or device access.")
        return
    require(os.geteuid() == 0, "Reservation holder requires root")
    root = args.root.resolve(strict=True)
    packet_path = root / "packet.json"
    validate(json.loads(packet_path.read_text()))
    packet_hash = hashlib.sha256(packet_path.read_bytes()).hexdigest()
    if args.reconcile_release:
        values = {"a": inventory(root / "final-a.jsonl"),
                  "b": inventory(root / "final-b.jsonl")}
        reservation = Reservation(packet_hash,
            reconciliation=(values, time.monotonic_ns()))
        try:
            reservation.release(values)
            save(root / "reservation-reconciled-release.json", {
                "packet_sha256": packet_hash, "utc_ns": time.time_ns(),
                "monotonic_ns": time.monotonic_ns()})
        finally:
            reservation.close()
        return
    reservation = Reservation(packet_hash)
    try:
        reservation.acquire({"a": inventory(root / "reservation-a.jsonl"),
                             "b": inventory(root / "reservation-b.jsonl")})
        save(root / "reservation-acquired.json", {"packet_sha256": packet_hash,
             "utc_ns": time.time_ns(), "monotonic_ns": time.monotonic_ns()})
        deadline = time.monotonic() + 7200
        while not (root / "release-request").exists():
            require(time.monotonic() < deadline, "Package 7 reservation deadline")
            time.sleep(.1)
        reservation.release({"a": inventory(root / "final-a.jsonl"),
                             "b": inventory(root / "final-b.jsonl")})
        save(root / "reservation-released.json", {"packet_sha256": packet_hash,
             "utc_ns": time.time_ns(), "monotonic_ns": time.monotonic_ns()})
    finally:
        reservation.close()


if __name__ == "__main__":
    main()
