#!/usr/bin/env python3
"""Independent raw-evidence audit for Package 5 replay/session capture."""
import argparse
import json
from pathlib import Path

from phase11_5_inventory import require
from phase11_5_package5_http import digest
from phase11_5_package5_plan import BOOT, DEVICE, PEER, validate_retention


def rows(path):
    raw = path.read_text()
    require(raw.endswith("\n"), "Truncated Package 5 trace")
    value = [json.loads(line) for line in raw.splitlines()]
    require([row["sequence"] for row in value] == list(range(len(value))) and
            all(a["monotonic_ns"] <= b["monotonic_ns"] for a, b in zip(value, value[1:])),
            "Package 5 trace sequence/time")
    return value


def audit(root, expected, *, allow_known_final_status_harness_failure=False):
    require(digest(root / "packet.json") == expected, "Frozen Package 5 retained packet")
    packet = validate_retention(json.loads((root / "packet.json").read_text()))
    for name, sha in packet["stage_sha256"].items():
        require(digest(root / name) == sha, "Package 5 retained helper changed")
    parent = rows(root / "retention.jsonl")
    http = rows(root / "retention-http.jsonl")
    disposition = "STOPPED_REQUIRES_DIAGNOSIS" if allow_known_final_status_harness_failure else "CAPTURED_REQUIRES_AUDIT"
    require(parent[0]["kind"] == "start" and parent[-1]["kind"] == "finish" and
            parent[0]["value"]["packet_sha256"] == expected and
            parent[-1]["value"]["status"] == disposition,
            "Package 5 retained parent disposition")
    require(http[0]["kind"] == "start" and http[-1]["kind"] == "finish" and
            http[0]["value"]["packet_sha256"] == expected and
            http[-1]["value"]["status"] == disposition,
            "Package 5 retained client disposition")
    quiet = next(row for row in parent if row["kind"] == "initial_quiet_start")
    offered = [row for row in http if row["kind"] == "http_tx"]
    written = [row for row in http if row["kind"] == "http_write_complete"]
    responses = [row for row in http if row["kind"] == "http_response"]
    cases = packet["retention"]["cases"]
    require(len(offered) == len(written) == len(responses) == len(cases) and
            offered[0]["monotonic_ns"] - quiet["value"]["monotonic_ns"] >=
            packet["retention"]["initial_quiet_seconds"] * 1_000_000_000,
            "Actual initial retention quiet/count")
    if allow_known_final_status_harness_failure:
        require(expected == "2039a76c119c23ebd7cdf36e8052252e58b9fc4b5a7d3283b51018690c829ccc" and
                cases[-1]["label"] == "final-status", "Known Package 5 harness failure identity")
        final_case, final_tx, final_write, final_response = cases[-1], offered[-1], written[-1], responses[-1]
        final_body = json.loads(bytes.fromhex(final_response["value"]["body_hex"]))
        require(final_tx["value"] == final_case and final_write["value"]["label"] == "final-status" and
                final_response["value"]["status"] == 400 and
                final_response["value"]["peer_sha256"] == PEER and
                final_body == {"error": {"code": "unsupported_operation"}},
                "Exact known browser POST STATUS harness failure")
        cases, offered, written, responses = cases[:-1], offered[:-1], written[:-1], responses[:-1]
    summaries = {}
    for case, tx, write, response in zip(cases, offered, written, responses):
        require(tx["value"] == case and write["value"] ==
                dict(label=case["label"], bytes=len(bytes.fromhex(case["wire_hex"]))) and
                tx["monotonic_ns"] <= write["monotonic_ns"] <= response["monotonic_ns"] and
                response["monotonic_ns"] - tx["monotonic_ns"] <= 15_000_000_000,
                "Exact retained HTTP request/write/deadline")
        value = response["value"]
        body = json.loads(bytes.fromhex(value["body_hex"]))
        require(value["label"] == case["label"] and value["status"] == case["expected_status"] and
                value["peer_sha256"] == PEER, "Retained HTTP outcome/peer")
        if case["error_code"]:
            require(body.get("ok") is False and body["error"]["code"] == case["error_code"],
                    "Retained HTTP classified error")
        else:
            require(body["ok"] is True and body["result"]["boot_id"] == BOOT and
                    body["result"]["device_id"] == DEVICE, "Retained HTTP success identity")
        summaries[case["label"]] = dict(body_hex=value["body_hex"], body=body,
                                         monotonic_ns=response["monotonic_ns"])
    require(summaries["session-0"]["body_hex"] == summaries["replay-exact"]["body_hex"],
            "Exact replay response differs")
    require(summaries["session-16-overflow"]["body"]["error"]["code"] == "BUSY" and
            summaries["session-15-reuse"]["body"]["ok"] is True and
            summaries["replay-conflict"]["body"]["error"]["code"] == "REQUEST_ID_REUSE" and
            summaries["replay-evicted"]["body"]["ok"] is True and
            summaries["replay-touched"]["body"]["error"]["code"] == "REQUEST_ID_REUSE",
            "Session/replay capacity and LRU proof")
    expiry = json.loads((root / "retention-expiry-quiet.json").read_text())
    first_expired = next(row for row in offered if row["value"]["phase"] == "expired")
    require(expiry == dict(packet_sha256=expected,
                           began_monotonic_ns=summaries["replay-touched"]["monotonic_ns"],
                           seconds=packet["retention"]["expiry_quiet_seconds"]) and
            first_expired["monotonic_ns"] - expiry["began_monotonic_ns"] >=
            expiry["seconds"] * 1_000_000_000 and
            not any(expiry["began_monotonic_ns"] < row["monotonic_ns"] < first_expired["monotonic_ns"]
                    and row["kind"].startswith("http_") for row in http),
            "Actual replay/session expiry quiet")
    require(all(summaries[label]["body"]["error"]["code"] == "HELLO_REQUIRED"
                for label in ("session-0-expired", "session-15-expired")) and
            summaries["replay-expired"]["body"]["ok"] is True and
            summaries["overflow-now-admitted"]["body"]["ok"] is True,
            "Actual replay/session expiry and reuse")
    status = None
    if not allow_known_final_status_harness_failure:
        status = summaries["final-status"]["body"]["result"]
        require(status["state"] == "empty" and status["output_active"] is False and
                status["owner_id"] is None and status["job_id"] is None,
                "Retained final inactive authority")
    infos = [row for row in parent if row["kind"] == "info"]
    require(len(infos) >= 24 and max(b["monotonic_ns"] - a["monotonic_ns"]
            for a, b in zip(infos, infos[1:])) <= 36_000_000_000,
            "Console quiet/active coverage")
    for row in infos:
        info = row["value"]["value"]
        require(info["status"]["boot_id"] == BOOT and info["status"]["state"] == "empty" and
                info["status"]["output_active"] is False and int(info["allocator_failures"]) == 0 and
                int(info["tls_allocation_failures"]) == 0 and
                info["heap_capacity_bytes"] - info["allocator_peak_bytes"] >= 32768,
                "Retained Console identity/resource gate")
    return dict(status=("PACKAGE5_REPLAY_SESSION_CORE_VERIFIED_STATUS_CONFIRMATION_REQUIRED"
                if allow_known_final_status_harness_failure else "PACKAGE5_REPLAY_SESSION_VERIFIED"), packet_sha256=expected,
                maximum_sessions=16, replay_entries_per_session=8,
                initial_quiet_seconds=packet["retention"]["initial_quiet_seconds"],
                expiry_quiet_seconds=packet["retention"]["expiry_quiet_seconds"],
                cases=len(cases), console_samples=len(infos), authenticated_peer_sha256=PEER,
                final_terminal_records=None if status is None else status["terminal_records"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--allow-known-final-status-harness-failure", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit(args.root.resolve(strict=True), args.packet_sha256,
        allow_known_final_status_harness_failure=args.allow_known_final_status_harness_failure), indent=2))


if __name__ == "__main__":
    main()
