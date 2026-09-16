#!/usr/bin/env python3
"""Audit the bounded Package 5 host cleanup-timer extension."""
import argparse
import json
from pathlib import Path

from phase11_5_inventory import require
from phase11_5_package5_http import digest
from phase11_5_package5_fixture_extend import validate


def audit(root, expected):
    require(digest(root / "packet.json") == expected, "Frozen fixture extension packet")
    packet = validate(json.loads((root / "packet.json").read_text()))
    for name, sha in packet["stage_sha256"].items():
        require(digest(root / name) == sha, "Fixture extension helper changed")
    value = json.loads((root / "extension-result.json").read_text())
    require(value["status"] == "PACKAGE5_FIXTURE_TIMER_EXTENDED" and
            value["packet_sha256"] == expected and value["client_pid"] == packet["client_pid"] and
            value["new_deadline_monotonic_ns"] > value["old_deadline_monotonic_ns"] and
            value["network_or_device_mutations"] == 0,
            "Package 5 fixture extension result")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.root.resolve(strict=True), args.packet_sha256), indent=2))


if __name__ == "__main__":
    main()
