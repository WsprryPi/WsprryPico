#!/usr/bin/env python3
"""Launch one frozen Package 10 runner inside the qualified client fixture."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from phase11_5_inventory import require
from phase11_5_package10 import digest, validate
from phase11_5_network_fixture import Fixture, HOST_BOOT, PREFIX


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no campaign is launched.")
        return
    require(sys.platform == "linux" and os.geteuid() == 0, "Linux root required")
    root = args.root.resolve(strict=True)
    packet_path = root / "packet.json"
    require(digest(packet_path) == args.packet_sha256, "Package 10 packet hash")
    packet = validate(json.loads(packet_path.read_text()))
    require(packet["root"] == str(root) and
            Path("/proc/sys/kernel/random/boot_id").read_text().strip() == HOST_BOOT,
            "Package 10 launch root/host")
    require(not any((root / name).exists() for name in
                    ("campaign.jsonl", "campaign-result.json", "campaign.pcap")),
            "Fresh Package 10 campaign artifacts required")
    fixture = Fixture(root)
    require(fixture.state and not fixture.state.get("restored") and
            fixture.state.get("host_boot") == HOST_BOOT and
            (root / "client-ready").is_file(), "Qualified fixture is not ready")
    client = PREFIX + "-client.service"
    pid = subprocess.run(["systemctl", "show", "-p", "MainPID", "--value", client],
                         check=True, text=True, capture_output=True, timeout=10).stdout.strip()
    require(pid.isdigit() and int(pid) > 1 and
            subprocess.run(["systemctl", "is-active", "--quiet", client]).returncode == 0,
            "Fixture client namespace is not active")
    fixture.unit("campaign", ["nsenter", "-t", pid, "-m", "-n", "/usr/bin/python3",
        str(root / "scripts/phase11_5_package10.py"), "--root", str(root),
        "--packet-sha256", args.packet_sha256, "--run"])
    print(PREFIX + "-campaign.service")


if __name__ == "__main__":
    main()
