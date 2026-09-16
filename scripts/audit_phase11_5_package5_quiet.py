#!/usr/bin/env python3
"""Audit a Console-only Package 5 application-quiet interval."""
import argparse
import json
from pathlib import Path

from phase11_5_inventory import require
from phase11_5_package5_quiet import digest, validate_packet


def audit(root, expected):
    require(digest(root / "packet.json") == expected, "Frozen quiet packet")
    packet = validate_packet(json.loads((root / "packet.json").read_text()))
    for name, sha in packet["stage_sha256"].items():
        path = (root / name).resolve()
        require(path.is_relative_to(root) and digest(path) == sha,
                "Package 5 quiet staged input changed")
    raw = (root / "post-quiet.jsonl").read_text()
    require(raw.endswith("\n"), "Truncated quiet trace")
    rows = [json.loads(line) for line in raw.splitlines()]
    require([row["sequence"] for row in rows] == list(range(len(rows))) and
            all(a["monotonic_ns"] <= b["monotonic_ns"] for a, b in zip(rows, rows[1:])) and
            rows[0]["kind"] == "start" and rows[-1]["kind"] == "finish" and
            all(row["kind"] in {"start", "tx", "rx", "info", "finish"}
                for row in rows), "Quiet trace operations/order")
    infos = [row for row in rows if row["kind"] == "info"]
    result = json.loads((root / "post-quiet-result.json").read_text())
    require(rows[-1]["value"] == result and
            result["status"] == "PACKAGE5_APPLICATION_QUIET_CAPTURED" and
            result["phase"] == packet["post_quiet"]["phase"] and
            result["samples"] == len(infos) >= 13 and
            result["ended_monotonic_ns"] - result["began_monotonic_ns"] >=
            packet["post_quiet"]["seconds"] * 1_000_000_000 and
            max((b["monotonic_ns"] - a["monotonic_ns"] for a, b in zip(infos, infos[1:])),
                default=0) <= 35_000_000_000,
            "Complete 360-second quiet coverage")
    for row in infos:
        info = row["value"]["value"]
        status = info["status"]
        require(status["boot_id"] == packet["boot_id"] and status["state"] == "empty" and
                status["output_active"] is False and status["enabled"] is False and
                row["value"]["host_boot"] == packet["host_boot_id"] and
                row["value"]["throttled"] == "throttled=0x0" and
                info["wtp_input_reserved_bytes"] == 0 and
                int(info["allocator_failures"]) == int(info["tls_allocation_failures"]) == 0,
                "Quiet device identity/authority/resource state")
    final = infos[-1]["value"]["value"]
    require(result["post_live_bytes"] == int(final["heap_allocated_bytes"]) and
            result["allocator_live_bytes"] == int(final["allocator_live_bytes"]) and
            result["allocator_failures"] == int(final["allocator_failures"]) == 0 and
            result["tls_allocation_failures"] == int(final["tls_allocation_failures"]) == 0 and
            result["heap_capacity_bytes"] == int(final["heap_capacity_bytes"]) and
            result["allocator_peak_bytes"] == int(final["allocator_peak_bytes"]) and
            result["heap_capacity_bytes"] - result["allocator_peak_bytes"] >= 32768,
            "Quiet live-memory/reserve result")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.root.resolve(strict=True), args.packet_sha256), indent=2))


if __name__ == "__main__":
    main()
