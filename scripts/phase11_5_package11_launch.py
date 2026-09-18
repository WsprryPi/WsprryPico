#!/usr/bin/env python3
"""Launch a frozen Package 11 admission or campaign inside its client fixture."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from phase11_5_inventory import require
from phase11_5_package10 import digest
from phase11_5_package11_fixture import Fixture, HOST_BOOT, PREFIX


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no Package 11 runner is launched.")
        return
    require(sys.platform == "linux" and os.geteuid() == 0, "Linux root required")
    root = args.root.resolve(strict=True)
    require(digest(root / "packet.json") == args.packet_sha256 and
            Path("/proc/sys/kernel/random/boot_id").read_text().strip() == HOST_BOOT,
            "Package 11 launch identity")
    packet = json.loads((root / "packet.json").read_text())
    require(packet.get("root") == str(root) and packet.get("schema") in
            ("phase11.5-package11-admission-v1", "phase11.5-package11-fixture-v1"),
            "Package 11 launch packet")
    fixture = Fixture(root)
    require(fixture.state and not fixture.state.get("restored") and
            (root / "client-ready").is_file(), "Package 11 fixture not ready")
    client = PREFIX + "-client.service"
    pid = subprocess.run(["systemctl", "show", "-p", "MainPID", "--value", client],
                         check=True, text=True, capture_output=True, timeout=10).stdout.strip()
    require(pid.isdigit() and int(pid) > 1 and
            subprocess.run(["systemctl", "is-active", "--quiet", client]).returncode == 0,
            "Package 11 client namespace inactive")
    script = ("phase11_5_package11_admission.py" if packet["schema"].endswith("admission-v1")
              else "phase11_5_package11.py")
    fixture.unit("campaign", ["nsenter", "-t", pid, "-m", "-n", "/usr/bin/python3",
        str(root / "scripts" / script), "--root", str(root),
        "--packet-sha256", args.packet_sha256, "--run"])
    print(PREFIX + "-campaign.service")


if __name__ == "__main__":
    main()
