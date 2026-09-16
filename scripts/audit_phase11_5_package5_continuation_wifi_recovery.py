#!/usr/bin/env python3
"""Audit the authorized Package 5 continuation Wi-Fi recovery cycle."""
import argparse
import json
from pathlib import Path

from phase11_5_inventory import require
from phase11_5_package5_http import digest
from phase11_5_package5_continuation_wifi_recovery import validate


def audit(root, expected):
    require(digest(root / "packet.json") == expected,
            "Frozen Package 5 continuation recovery packet")
    packet = validate(json.loads((root / "packet.json").read_text()))
    for name, sha in packet["stage_sha256"].items():
        path = (root / name).resolve()
        require(path.is_relative_to(root) and digest(path) == sha,
                "Package 5 continuation recovery staged input changed")
    raw = (root / "wifi.jsonl").read_text()
    require(raw.endswith("\n"), "Truncated Package 5 continuation recovery trace")
    rows = [json.loads(line) for line in raw.splitlines()]
    require([row["sequence"] for row in rows] == list(range(len(rows))) and
            all(a["monotonic_ns"] <= b["monotonic_ns"] for a, b in zip(rows, rows[1:])) and
            rows[0]["kind"] == "start" and rows[-1]["kind"] == "finish" and
            rows[-1]["value"]["status"] == "RECOVERED_REQUIRES_AUDIT",
            "Package 5 continuation recovery trace/result")
    commands = [bytes.fromhex(row["value"]["hex"])
                for row in rows if row["kind"] == "tx"]
    require(commands.count(b"WIFI OFF\n") == commands.count(b"WIFI ON\n") == 1 and
            commands.index(b"WIFI OFF\n") < commands.index(b"WIFI ON\n") and
            all(command in (b"INFO\n", b"WIFI OFF\n", b"WIFI ON\n")
                for command in commands),
            "Exactly one Package 5 continuation Wi-Fi cycle")
    infos = [row["value"]["value"] for row in rows if row["kind"] == "info"]
    before, final = infos[0], infos[-1]
    require(all(info["device_id"] == packet["device_id"] and
                info["revision"] == packet["source_revision"][:12] and
                info["status"]["boot_id"] == packet["boot_id"] and
                info["status"]["state"] == "empty" and
                info["status"]["output_active"] is False and
                info["status"]["enabled"] is False and
                int(info["allocator_failures"]) == int(info["tls_allocation_failures"]) == 0
                for info in infos) and
            before["network"]["enabled"] is True and
            before["network"]["link_status"] == -3 and not before["network"]["ipv4"] and
            before["status"]["clock_state"] == "unsynchronized" and
            final["network"]["enabled"] is True and final["network"]["link_status"] == 3 and
            final["network"]["ipv4"] == "10.77.15.10" and
            final["status"]["clock_state"] == "synchronized" and
            before["status"]["boot_id"] == final["status"]["boot_id"] == packet["boot_id"] and
            before["status"]["state"] == final["status"]["state"] == "empty" and
            before["status"]["output_active"] is final["status"]["output_active"] is False and
            before["status"]["watermark_utc_ns"] == final["status"]["watermark_utc_ns"] and
            before["status"]["schedules"] == final["status"]["schedules"],
            "Package 5 continuation recovery identity/readiness/configuration")
    return dict(status="PACKAGE5_CONTINUATION_WIFI_RECOVERY_VERIFIED",
                packet_sha256=expected, wifi_cycles=1, boot_id=packet["boot_id"],
                ipv4="10.77.15.10", initial_link_status=-3, final_link_status=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.root.resolve(strict=True), args.packet_sha256), indent=2))


if __name__ == "__main__":
    main()
