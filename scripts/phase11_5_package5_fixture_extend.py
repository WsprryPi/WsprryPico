#!/usr/bin/env python3
"""Restart only the finite host cleanup timer after preserved Package 5 retries."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from phase11_5_inventory import require
from phase11_5_package5_http import digest, save


UNIT = "phase115-closure-cleanup.timer"
OBJECT = "/org/freedesktop/systemd1/unit/phase115_2dclosure_2dcleanup_2etimer"


def deadline():
    raw = subprocess.check_output(["busctl", "get-property", "org.freedesktop.systemd1",
        OBJECT, "org.freedesktop.systemd1.Timer", "NextElapseUSecMonotonic"], text=True,
        timeout=5).split()
    require(len(raw) == 2 and raw[0] == "t", "Cleanup timer deadline")
    return int(raw[1]) * 1000


def validate(packet):
    require(packet["schema"] == packet["scope"] == "phase11.5-package5-fixture-extend-v1" and
            packet["runtime_seconds"] == 30 and packet["timer_on_active_seconds"] == 7800 and
            packet["configuration_writes"] == packet["controlled_reboots"] ==
            packet["wifi_cycles"] == packet["flashes"] == packet["rf_jobs"] == 0,
            "Frozen Package 5 fixture extension")
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no timer change.")
        return
    root = args.root.resolve(strict=True)
    require(os.geteuid() == 0 and digest(root / "packet.json") == args.packet_sha256,
            "Package 5 fixture extension root/hash")
    packet = validate(json.loads((root / "packet.json").read_text()))
    for name, sha in packet["stage_sha256"].items():
        require(digest(root / name) == sha, "Package 5 fixture extension helper changed")
    pid = packet["client_pid"]
    require(Path(f"/proc/{pid}").is_dir() and os.readlink(f"/proc/{pid}/ns/net") ==
            packet["client_netns"] and os.readlink(f"/proc/{pid}/ns/mnt") ==
            packet["client_mountns"], "Package 5 fixture client before extension")
    before = deadline()
    subprocess.run(["systemctl", "restart", UNIT], check=True, timeout=10)
    after = deadline()
    now = time.monotonic_ns()
    require(after > before and
            packet["timer_on_active_seconds"] * 10**9 - 10_000_000_000 <= after - now <=
            packet["timer_on_active_seconds"] * 10**9,
            "Package 5 cleanup timer was not extended to the frozen bound")
    require(Path(f"/proc/{pid}").is_dir() and os.readlink(f"/proc/{pid}/ns/net") ==
            packet["client_netns"] and os.readlink(f"/proc/{pid}/ns/mnt") ==
            packet["client_mountns"], "Package 5 fixture client after extension")
    save(root / "extension-result.json", dict(status="PACKAGE5_FIXTURE_TIMER_EXTENDED",
        packet_sha256=args.packet_sha256, old_deadline_monotonic_ns=before,
        new_deadline_monotonic_ns=after, extended_at_monotonic_ns=now,
        client_pid=pid, network_or_device_mutations=0))


if __name__ == "__main__":
    main()
