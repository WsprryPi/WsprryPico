#!/usr/bin/env python3
"""Offline B2/D2 repeat audit; opens only private evidence files."""

import argparse
import json
from pathlib import Path

from audit_phase11_4_mdns_withdrawal import audit as withdrawal
from audit_phase11_4_recovery import SCHEMA, VALIDATOR, require
from validate_wtp_contract import loads_strict, reject_constant, unique_object

SERVER_SHA = "06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016"


def audit(directory, mac_log):
    # Observer records contain epoch nanoseconds and floating-point durations;
    # they are not WTP messages, whose numeric range is deliberately narrower.
    rows = [json.loads(line, object_pairs_hook=unique_object, parse_constant=reject_constant)
            for line in (directory / "events.jsonl").read_text().splitlines()]

    def selected(kind):
        return [r for r in rows if r["kind"] == kind]

    def one(kind):
        found = selected(kind)
        require(len(found) == 1, "expected exactly one " + kind)
        return found[0]

    require(not any(selected(k) for k in
                    ("CASE_FAILURE", "PEER_RECOVERY_FAILURE", "OUTAGE_LOOKUP_FAILURE",
                     "https_failure", "cleanup_on_begin")),
            "failed attempt cannot become a clean pass through recovery")
    # Report a recorded failure before secondary missing-cleanup/capture gaps.
    result = withdrawal(directory, mac_log)
    require(all(a["epoch_ns"] <= b["epoch_ns"] for a, b in zip(rows, rows[1:])),
            "nonmonotonic evidence timestamps")
    before = selected("console INFO")[0]["value"]
    require(before["revision"] == "5ee5bcf93c56-dirty", "wrong reviewed firmware revision")
    boot = before["status"]["boot_id"]
    address = before["network"]["ipv4"]
    name = before["network"]["configured_hostname"]
    off, on = one("off_begin")["epoch_ns"], one("on_begin")["epoch_ns"]
    require(on - off >= 150 * 10**9, "missing full 150-second outage")
    nss = selected("nss")
    require(one("seed_socket_closed")["epoch_ns"] < nss[0]["value"]["started_ns"],
            "seed socket was not closed before NSS measurements")
    negatives = [r for r in nss if r["value"]["label"].startswith("off-")]
    require(len(negatives) == 6 and
            negatives[0]["value"]["started_ns"] > result["goodbye_epoch_ns"] + 10**9 and
            negatives[-1]["value"]["started_ns"] > off + 145 * 10**9,
            "missing distributed negatives after goodbye grace and beyond original TTL")
    active = one("local_active")
    require(0 < active["value"]["seconds_after_on"] <= 40 and
            on < active["epoch_ns"] <= on + 40 * 10**9,
            "local recovery exceeded original 40-second bound")
    summary = one("recovery_summary")
    passed = one("CASE_PASS")
    require(summary["epoch_ns"] < passed["epoch_ns"] and
            passed["value"]["boot_id"] == boot and
            summary["value"]["peer_failures"] == [], "invalid success summary")
    recovered = [r for r in nss if on < r["epoch_ns"] < summary["epoch_ns"]]
    require(len(recovered) >= 5 and
            summary["value"]["successful_checks"] == len(recovered),
            "missing repeated peer checks")
    for r in nss:
        v = r["value"]
        require(v["started_ns"] < v["ended_ns"] <= r["epoch_ns"], "invalid lookup timestamps")
        if not v["label"].startswith("off-"):
            require(v["exit"] == 0 and
                    {line.split()[0] for line in v["stdout"].splitlines()} == {address},
                    "failed or alternate-address positive lookup")
    https = selected("verified_https")
    for r in https:
        v, body = r["value"], r["value"]["body"]
        s, n, j = body["standalone"], body["network"], body["job"]
        require(v["http"] == 200 and v["server_sha256"] == SERVER_SHA,
                "missing authenticated target HTTP response")
        require(j["boot_id"] == boot and j["state"] == "empty" and
                j["owner_id"] is None and j["job_id"] is None and j["output_active"] is False,
                "HTTPS disagrees with USB authority")
        require(s["boot_id"] == boot and s["storage_healthy"] and
                s["engine"] == "inhibited-standalone-simulator" and s["output_active"] is False,
                "HTTPS standalone identity mismatch")
        for key in ("station", "schedules", "watermark_utc_ns", "expires_utc_s", "enabled", "suspended"):
            require(s[key] == before["status"][key], "HTTPS saved state changed: " + key)
        require(n["ipv4"] == address and n["advertised_hostname"] == name and
                n["mdns_state"] == "active" and n["deployment_identity_matches"],
                "HTTPS discovery mismatch")
        require(body["transport"]["tls_allocation_failures"] == 0,
                "TLS allocation failure observed")
    pairs = []
    for index, r in enumerate(recovered):
        end = recovered[index + 1]["value"]["started_ns"] if index + 1 < len(recovered) else summary["epoch_ns"]
        reads = [h for h in https if r["epoch_ns"] < h["epoch_ns"] < end]
        require(len(reads) == 1, "each recovered NSS result needs its own HTTPS read")
        pairs.append(reads[0])
    require(pairs[-1]["epoch_ns"] - pairs[0]["epoch_ns"] >= 30 * 10**9 and
            summary["value"]["stable_seconds"] >= 30, "stable window shorter than 30 seconds")
    require(any(r["epoch_ns"] < off for r in https), "no authenticated baseline")
    cleanup = one("CLEANUP_VERIFIED")
    final = selected("console INFO")[-1]["value"]
    require(cleanup["epoch_ns"] > passed["epoch_ns"] and cleanup["value"]["peer_recovered"] and
            cleanup["value"]["network"] == final["network"], "cleanup not reconciled")
    require(any(passed["epoch_ns"] < r["epoch_ns"] < cleanup["epoch_ns"] and
                r["value"]["label"] == "cleanup" for r in nss) and
            any(passed["epoch_ns"] < r["epoch_ns"] < cleanup["epoch_ns"] for r in https),
            "cleanup lacks NSS and authenticated peer checks")
    for r in selected("console INFO"):
        for resource in r["value"]["network"]["memory"].values():
            require(0 <= resource["used"] <= resource["peak"] <= resource["capacity"] and
                    resource["errors"] == 0, "network resource bound or allocation failure")
    wire = [loads_strict(line) for line in (directory / "usb-frames.jsonl").read_text().splitlines()]
    requests, responses = selected("wtp_request"), selected("wtp_response")
    require(len(wire) == len(requests) == len(responses), "missing raw USB responses")
    for index, (w, req, res) in enumerate(zip(wire, requests, responses), 1):
        require(not VALIDATOR.errors(w, SCHEMA), "raw USB schema violation")
        require(w["type"] == "response" and w["ok"] and
                req["epoch_ns"] < res["epoch_ns"] and
                w["session_id"] == req["value"]["session"] and
                w["request_id"] == format(index, "032x") and
                w["op"] == req["value"]["op"] == res["value"]["op"] and
                w["body"] == res["value"]["body"], "raw USB response mismatch")
    result.update(scope="bounded B2/D2 recovery repeat", recovered_checks=len(recovered),
                  stable_seconds=(pairs[-1]["epoch_ns"] - pairs[0]["epoch_ns"]) / 1e9,
                  local_active_seconds=active["value"]["seconds_after_on"],
                  final_memory=final["network"]["memory"],
                  limitation="Does not explain historical intermittent failures or establish overnight stability")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("mac_log", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.directory, args.mac_log), indent=2))
