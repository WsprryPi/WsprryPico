#!/usr/bin/env python3
"""Independent raw-evidence audit for the Package 5 cache normalizer."""
import argparse
import json
from pathlib import Path

from audit_phase11_5_r3_v2_rf import audit as audit_rf
from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_package5_plan import validate_normalizer


def audit(root, expected):
    require(digest(root / "packet.json") == expected,
            "Frozen Package 5 normalizer packet")
    packet = validate_normalizer(json.loads((root / "packet.json").read_text()))
    result = audit_rf(root, packet_digest=expected)
    expected_ids = [job["job_id"] for job in reversed(packet["jobs"])]
    records = result["terminal_records"]
    require(result["rf_jobs"] == 8 and
            result["rf_duration_ns_charged"] == 8_000_000_000 and
            [record["job_id"] for record in records] == expected_ids and
            all(record["state"] == "complete" and record["output_active"] is False and
                "error" not in record for record in records),
            "Package 5 normalized maximum-event terminal content")
    result.update(status="PACKAGE5_NORMALIZER_VERIFIED", normalized_records=8,
                  events_per_record=512, prior_records=
                  packet["initial_terminal_records"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.root.resolve(strict=True), args.packet_sha256), indent=2))


if __name__ == "__main__":
    main()
