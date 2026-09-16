#!/usr/bin/env python3
"""Independent raw-evidence audit for Package 5 terminal expiry."""
import argparse
import json
from pathlib import Path

from phase11_5_inventory import require
from phase11_5_package5_http import digest
from phase11_5_package5_plan import BOOT, DEVICE, PEER, validate_expiry


def trace(path):
    raw = path.read_text()
    require(raw.endswith("\n"), "Truncated Package 5 expiry trace")
    rows = [json.loads(line) for line in raw.splitlines()]
    require([row["sequence"] for row in rows] == list(range(len(rows))) and
            all(a["monotonic_ns"] <= b["monotonic_ns"] for a, b in zip(rows, rows[1:])),
            "Package 5 expiry trace order")
    return rows


def audit(root, expected):
    require(digest(root / "packet.json") == expected, "Frozen Package 5 expiry packet")
    packet = validate_expiry(json.loads((root / "packet.json").read_text()))
    for name, sha in packet["stage_sha256"].items():
        path = (root / name).resolve()
        require(path.is_relative_to(root) and digest(path) == sha,
                "Package 5 expiry helper changed")
    for name, sha in packet["private_input_sha256"].items():
        path = (root / name).resolve()
        require(path.is_relative_to(root) and digest(path) == sha,
                "Package 5 expiry private input changed")
    parent = trace(root / "expiry.jsonl")
    http = trace(root / "expiry-http.jsonl")
    require(parent[0]["kind"] == http[0]["kind"] == "start" and
            parent[-1]["kind"] == http[-1]["kind"] == "finish" and
            parent[-1]["value"]["status"] == http[-1]["value"]["status"] ==
            "CAPTURED_REQUIRES_AUDIT", "Package 5 expiry dispositions")
    cases = packet["terminal_expiry"]["cases"]
    offered = [row for row in http if row["kind"] == "http_tx"]
    responses = [row for row in http if row["kind"] == "http_response"]
    require(len(offered) == len(responses) == len(cases), "Package 5 expiry HTTP count")
    values = {}
    for case, tx, response in zip(cases, offered, responses):
        require(tx["value"] == case and response["value"]["label"] == case["label"] and
                response["value"]["status"] == 200 and response["value"]["peer_sha256"] == PEER and
                response["monotonic_ns"] - tx["monotonic_ns"] <= 15_000_000_000,
                "Package 5 expiry authenticated request/outcome")
        body = json.loads(bytes.fromhex(response["value"]["body_hex"]))
        require(body["ok"] is True and body["result"]["boot_id"] == BOOT and
                body["result"]["device_id"] == DEVICE, "Package 5 expiry response identity")
        values[case["label"]] = dict(body=body["result"], tx=tx["monotonic_ns"],
                                            response=response["monotonic_ns"])
    status_tx = [row for row in http if row["kind"] == "status_tx"]
    status_responses = [row for row in http if row["kind"] == "status_response"]
    require(len(status_tx) == len(status_responses) == 2,
            "Package 5 expiry authenticated status count")
    status_values = []
    for tx, response in zip(status_tx, status_responses):
        request = bytes.fromhex(tx["value"]["request_hex"])
        body = json.loads(bytes.fromhex(response["value"]["body_hex"]))
        require(request.startswith(b"GET /api/v1/status HTTP/1.1\r\n") and
                response["value"]["status"] == 200 and
                response["value"]["peer_sha256"] == PEER and
                response["monotonic_ns"] - tx["monotonic_ns"] <= 15_000_000_000 and
                body["job"]["boot_id"] == BOOT,
                "Package 5 expiry authenticated status outcome")
        status_values.append(dict(body=body["job"], tx=tx["monotonic_ns"],
                                  response=response["monotonic_ns"]))
    before, after = status_values[0]["body"], status_values[1]["body"]
    initial = packet["terminal_expiry"]["initial_terminal_records"]
    require(before["state"] == after["state"] == "empty" and
            before["output_active"] is after["output_active"] is False and
            before["owner_id"] is after["owner_id"] is None and
            before["job_id"] is after["job_id"] is None and
            before["terminal_records"] == initial and after["terminal_records"] == [],
            "Actual terminal baseline/expiry/final authority")
    quiet = json.loads((root / "terminal-expiry-quiet.json").read_text())
    require(quiet == dict(packet_sha256=expected,
                          began_monotonic_ns=status_values[0]["response"],
                          seconds=packet["terminal_expiry"]["quiet_seconds"]) and
            values["after-hello"]["tx"] - quiet["began_monotonic_ns"] >=
            quiet["seconds"] * 1_000_000_000 and
            status_values[1]["response"] - values["after-hello"]["tx"] <=
            packet["terminal_expiry"]["authenticated_recovery_seconds"] * 1_000_000_000 and
            not any(quiet["began_monotonic_ns"] < row["monotonic_ns"] < values["after-hello"]["tx"]
                    and row["kind"] in {"http_tx", "http_response", "status_tx",
                                        "status_response"} for row in http),
            "Actual 3660-second quiet and authenticated reuse deadline")
    infos = [row for row in parent if row["kind"] == "info"]
    require(len(infos) >= 120 and max(b["monotonic_ns"] - a["monotonic_ns"]
            for a, b in zip(infos, infos[1:])) <= 36_000_000_000,
            "Terminal expiry Console coverage")
    for row in infos:
        info = row["value"]["value"]
        status = info["status"]
        require(info["device_id"] == DEVICE and info["revision"] == packet["source_revision"][:12]
                and status["boot_id"] == BOOT and status["state"] == "empty" and
                status["output_active"] is False and status["enabled"] is False and
                info["core0_stack_guard_valid"] == info["core1_stack_guard_valid"] == 1 and
                int(info["allocator_failures"]) == int(info["tls_allocation_failures"]) == 0,
                "Package 5 expiry continuous identity/authority/resource state")
    final_info = infos[-1]["value"]["value"]
    now = int(final_info["status"]["monotonic_now_ns"])
    require(all(now >= int(record["ended_monotonic_ns"]) and
                now - int(record["ended_monotonic_ns"]) >=
                packet["terminal_expiry"]["source_ttl_seconds"] * 1_000_000_000
                for record in initial), "Every pruned terminal exceeded source TTL")
    require(final_info["status"]["boot_id"] == BOOT and final_info["status"]["state"] == "empty" and
            final_info["status"]["output_active"] is False and int(final_info["allocator_failures"]) == 0 and
            int(final_info["tls_allocation_failures"]) == 0 and
            final_info["heap_capacity_bytes"] - final_info["allocator_peak_bytes"] >= 32768,
            "Package 5 expiry final resource/authority gate")
    return dict(status="PACKAGE5_TERMINAL_EXPIRY_VERIFIED", packet_sha256=expected,
                quiet_seconds=quiet["seconds"], expired_records=len(initial),
                authenticated_recovery_ns=status_values[1]["response"] -
                values["after-hello"]["tx"], console_samples=len(infos),
                final_terminal_records=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.root.resolve(strict=True), args.packet_sha256), indent=2))


if __name__ == "__main__":
    main()
