#!/usr/bin/env python3
"""Offline D2 evidence audit. Never opens a network or device endpoint."""

import argparse
import json
from pathlib import Path
import re

from audit_phase11_4_mdns_conflict import pcap, require


def audit(directory, mac_log):
    rows = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]

    def one(kind):
        values = [r for r in rows if r["kind"] == kind]
        require(len(values) == 1, "expected exactly one " + kind)
        return values[0]

    infos = [r for r in rows if r["kind"] == "console INFO"]
    require(len(infos) >= 3, "missing independent Console observations")
    initial, final = infos[0]["value"], infos[-1]["value"]
    name, address = initial["network"]["configured_hostname"], initial["network"]["ipv4"]
    require(name == "wsprrypico-0a60df.local" and address == "192.168.1.47", "wrong target")
    boot = initial["status"]["boot_id"]
    require(initial["network"]["enabled"] and initial["network"]["mdns_state"] == "active" and
            initial["network"]["advertised_hostname"] == name, "invalid discovery baseline")
    controls = [r for r in rows if r["kind"].startswith("console ") and r["kind"] != "console INFO"]
    require([r["kind"] for r in controls] == ["console WIFI OFF", "console WIFI ON"] and
            all(r["value"].get("ok") is True for r in controls), "unexpected Console controls")
    for r in infos:
        v, s = r["value"], r["value"]["status"]
        require(v["device_id"] == "fd6127d11d6aca42a9905fa3fb1bf1d5" and
                v["revision"] == initial["revision"] and v["deployment_identity_matches"] and
                not v["recovery_boot"], "device or deployment changed")
        require(s["boot_id"] == boot and s["engine"] == "inhibited-standalone-simulator" and
                s["output_active"] is False and s["storage_healthy"] and not s["enabled"],
                "unsafe or changed device state")
        require(v["network"]["configured_hostname"] == name, "hostname changed")
        for key in ("station", "schedules", "watermark_utc_ns", "expires_utc_s", "suspended"):
            require(s[key] == initial["status"][key], "saved state changed: " + key)
    off, on = one("off_begin")["epoch_ns"], one("on_begin")["epoch_ns"]
    require(on - off >= 120 * 10**9, "outage did not span advertised TTL")
    require(any(off < r["epoch_ns"] < on and not r["value"]["network"]["enabled"] and
                r["value"]["network"]["advertised_hostname"] == "" for r in infos),
            "missing authoritative disabled state")
    require(final["network"]["enabled"] and final["network"]["mdns_state"] == "active" and
            final["network"]["advertised_hostname"] == name and
            final["network"]["ipv4"] == address, "missing same-name recovery")
    require(final["network"]["mdns_goodbye_attempts"] ==
            initial["network"]["mdns_goodbye_attempts"] + 1 and
            final["network"]["mdns_goodbye_failures"] ==
            initial["network"]["mdns_goodbye_failures"], "unexpected goodbye counters")
    one("CLEANUP_VERIFIED")
    operations = [r["value"]["op"] for r in rows if r["kind"] == "wtp_request"]
    require(set(operations) <= {"HELLO", "CAPS", "STATUS"}, "unexpected WTP mutation")
    require(len({r["value"]["session"] for r in rows if r["kind"] == "wtp_request"}) == 1,
            "USB inspection changed sessions")
    hello = [r["value"]["body"] for r in rows if r["kind"] == "wtp_response" and
             r["value"]["op"] == "HELLO"]
    caps = [r["value"]["body"] for r in rows if r["kind"] == "wtp_response" and
            r["value"]["op"] == "CAPS"]
    require(len(hello) == len(caps) == 1 and hello[0]["device_id"] == initial["device_id"] and
            hello[0]["boot_id"] == boot and caps[0]["engine"] == "inhibited-standalone-simulator",
            "USB identity or capability mismatch")
    statuses = [r["value"]["body"] for r in rows if r["kind"] == "wtp_response" and
                r["value"]["op"] == "STATUS"]
    require(len(statuses) >= 4, "missing USB status observations")
    for s in statuses:
        require(s["boot_id"] == boot and s["output_active"] is False and
                s["owner_id"] is None and s["job_id"] is None and s["state"] == "empty",
                "USB authority not inactive and unowned")
    nss = [r["value"] for r in rows if r["kind"] == "nss"]
    for label in ("before", "restored"):
        selected = [v for v in nss if v["label"] == label]
        require(len(selected) == 1 and selected[0]["exit"] == 0 and
                {line.split()[0] for line in selected[0]["stdout"].splitlines()} == {address},
                "missing exact Linux positive lookup: " + label)
    negative = [v for v in nss if v["label"].startswith("off-")]
    require(len(negative) >= 2 and all(v["exit"] == 2 and not v["stdout"] and
            off < v["started_ns"] < v["ended_ns"] < on for v in negative),
            "Linux negative lookup missing, stale, timed out or outside outage")
    packets = pcap(directory / "mdns.pcap")
    capture_log = (directory / "capture.log").read_text()
    require(re.search(r"\n0 packets dropped by kernel\n", capture_log), "capture loss or missing stats")
    count = re.search(r"(\d+) packets captured", capture_log)
    require(count and int(count[1]) == len(packets), "capture count mismatch")
    pico = [p for p in packets if p["source"] == address]
    require(pico and all(p["source_mac"] == "88:a2:9e:0a:60:df" and p["ttl"] == 255 and
                        p["sport"] == p["dport"] == 5353 for p in pico), "wrong packet origin")
    require(all(r["name"] == name and r["address"] == address
                for p in pico for r in p["dns"]["records"] if r["type"] == 1),
            "Pico advertised an alternate name or address")

    def a_record(record, ttl):
        return record["name"] == name and record["type"] == 1 and record["address"] == address and \
            record["ttl"] == ttl and record["cls"] == 0x8001

    positive = [p for p in pico if p["dns"]["flags"] & 0x8000 and
                any(a_record(r, 120) for r in p["dns"]["records"])]
    require(any(p["epoch_ns"] < off for p in positive), "no captured baseline A response")
    goodbye = [p for p in pico if off <= p["epoch_ns"] < on and
               p["dns"]["flags"] & 0x8000 and
               any(a_record(r, 0) for r in p["dns"]["records"])]
    require(len(goodbye) == 1, "missing or ambiguous Pico goodbye")
    require(any(r["name"] == "47.1.168.192.in-addr.arpa" and r["type"] == 12 and
                r["target"] == name and r["ttl"] == 0 and r["cls"] == 0x8001
                for r in goodbye[0]["dns"]["records"]), "missing matching PTR goodbye")
    require(not any(off <= p["epoch_ns"] < on for p in positive), "positive response during outage")
    announcements = [p for p in positive if p["epoch_ns"] > on]
    require(announcements, "missing actual post-recovery announcement")
    probes = [p for p in pico if on < p["epoch_ns"] < announcements[0]["epoch_ns"] and
              not p["dns"]["flags"] & 0x8000 and
              any(q["name"] == name and q["type"] == 255 for q in p["dns"]["questions"])]
    require(len(probes) == 3, "missing three same-name probe datagrams")
    mac = [json.loads(line) for line in mac_log.read_text().splitlines()]
    callbacks = []
    for row in mac:
        for line in row["text"].splitlines():
            words = line.split()
            if len(words) == 7 and words[1] in ("Add", "Rmv") and words[4] == name + ".":
                require(words[5] == address, "Mac callback used another address")
                callbacks.append((words[1], int(words[6]), row["epoch_ns"]))
    require([r[:2] for r in callbacks] == [("Add", 120), ("Rmv", 0), ("Add", 120)],
            "missing native Mac Add/Remove/re-Add sequence")
    # Different hosts' UTC clocks are not a subsecond latency measurement.
    # Require broad event association only; the report retains raw timestamps.
    require(abs(callbacks[1][2] - goodbye[0]["epoch_ns"]) < 5 * 10**9 and
            abs(callbacks[2][2] - announcements[0]["epoch_ns"]) < 5 * 10**9,
            "Mac callbacks do not correspond to captured lifecycle")
    return dict(result="PASS", scope="D2 orderly withdrawal and recovery", boot_id=boot,
                capture_packets=len(packets), goodbye_epoch_ns=goodbye[0]["epoch_ns"],
                outage_seconds=(on-off)/1e9, probes=len(probes),
                announcements=len(announcements), mac_callbacks=callbacks,
                linux_first_negative=negative[0],
                limitation="No natural TTL-expiry or unexpected-loss claim; D3 is separate")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("mac_log", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.directory, args.mac_log), indent=2))
