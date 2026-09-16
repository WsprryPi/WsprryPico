#!/usr/bin/env python3
"""Independent Package 5 terminal capacity/LRU audit."""
import argparse
import json
from pathlib import Path

from audit_phase11_5_r3_v2_rf import audit as audit_rf
from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_package5_plan import validate_terminal


def audit(root, expected):
    require(digest(root / "packet.json") == expected, "Frozen Package 5 terminal packet")
    packet = validate_terminal(json.loads((root / "packet.json").read_text()))
    result = audit_rf(root, packet_digest=expected)
    jobs = packet["jobs"]
    expected_ids = [jobs[8]["job_id"], jobs[0]["job_id"]] + [
        jobs[n]["job_id"] for n in range(7, 1, -1)]
    records = result["terminal_records"]
    require(result["rf_jobs"] == 9 and result["rf_duration_ns_charged"] == 9_000_000_000 and
            [record["job_id"] for record in records] == expected_ids and
            all(record["state"] == "complete" and record["output_active"] is False and
                "error" not in record for record in records),
            "Package 5 actual completion capacity/LRU")
    result.update(status="PACKAGE5_TERMINAL_CAPACITY_VERIFIED", family_closed=False,
                  capacity=8, completed_jobs=9, touched_job_id=jobs[0]["job_id"],
                  evicted_job_id=jobs[1]["job_id"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.root.resolve(strict=True), args.packet_sha256), indent=2))


if __name__ == "__main__":
    main()
