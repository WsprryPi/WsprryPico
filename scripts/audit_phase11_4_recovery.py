#!/usr/bin/env python3
"""Offline audit of private Phase 11.4 G4-G7 evidence; performs no device I/O."""

import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from validate_wtp_contract import SchemaValidator, crc32c, loads_strict

SCHEMA = json.loads((Path(__file__).resolve().parents[1] /
                     "docs/protocol/wtp-1.schema.json").read_text())
VALIDATOR = SchemaValidator(SCHEMA)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text())


def frames(data, interrupted=False, tails=None):
    result = []
    while data:
        if interrupted and len(data) < 16:
            if tails is not None:
                tails.append(len(data))
            break  # End of this connection only; never scan for another header.
        require(len(data) >= 16, "truncated WTP header")
        magic, version, encoding, flags, length, crc = struct.unpack(
            ">4sBBHII", data[:16])
        require((magic, version, encoding, flags) == (b"WTPF", 1, 1, 0),
                "invalid WTP header")
        require(0 < length <= 65536, "oversized WTP payload")
        if interrupted and len(data) < 16 + length:
            if tails is not None:
                tails.append(len(data))
            break
        require(len(data) >= 16 + length,
                "truncated or oversized WTP payload")
        payload, data = data[16:16 + length], data[16 + length:]
        require(crc32c(payload) == crc, "WTP CRC mismatch")
        value = loads_strict(payload.decode())
        require(not VALIDATOR.errors(value, SCHEMA), "WTP schema mismatch")
        result.append(value)
    return result


def audit_stream(path, interrupted=False, tails=None):
    """Instrumentation records accepted SSL I/O, with length-prefixed chunks."""
    raw, chunks = path.read_bytes(), []
    while raw:
        require(len(raw) >= 4, "truncated audit length")
        length = struct.unpack(">I", raw[:4])[0]
        require(0 < length <= 65536 and len(raw) >= length + 4,
                "truncated audit chunk")
        chunks.append(raw[4:4 + length])
        raw = raw[4 + length:]
    return frames(b"".join(chunks), interrupted, tails)


def packets(path):
    raw = path.read_bytes()
    require(len(raw) >= 24 and raw[:4] == b"\xd4\xc3\xb2\xa1",
            "expected little-endian microsecond PCAP")
    require(struct.unpack("<I", raw[20:24])[0] == 1, "expected Ethernet PCAP")
    raw = raw[24:]
    result = []
    while raw:
        require(len(raw) >= 16, "truncated PCAP packet header")
        _, _, captured, original = struct.unpack("<IIII", raw[:16])
        require(captured == original and len(raw) >= 16 + captured,
                "truncated PCAP packet")
        packet, raw = raw[16:16 + captured], raw[16 + captured:]
        require(packet[12:14] == b"\x08\x00", "non-IPv4 packet in flow capture")
        ip = packet[14:]
        ihl = (ip[0] & 15) * 4
        require(ip[9] == 6, "non-TCP packet in flow capture")
        total = struct.unpack(">H", ip[2:4])[0]
        tcp = ip[ihl:total]
        sport, dport, seq, ack = struct.unpack(">HHII", tcp[:12])
        size = len(tcp) - ((tcp[12] >> 4) * 4)
        result.append(dict(source=".".join(map(str, ip[12:16])),
                           destination=".".join(map(str, ip[16:20])),
                           sport=sport, dport=dport, seq=seq, ack=ack, size=size))
    return result


def direct(path):
    rows = [json.loads(line) for line in (path / "events.jsonl").read_text().splitlines()]
    passes = [row["value"] for row in rows if row["kind"] == "CASE_PASS"]
    require({p["case"] for p in passes} == {"lost_LOAD", "lost_ARM", "lost_ABORT", "G7"},
            "missing direct case result")
    caps = next(r["value"]["body"] for r in rows if r["kind"] == "wtp_response"
                and r["value"]["op"] == "CAPS")
    require(caps["engine"] == "inhibited-standalone-simulator", "wrong engine")
    result = {}
    for op in ("LOAD", "ARM", "ABORT"):
        request, = frames((path / (op + ".request.bin")).read_bytes())
        require(request["op"] == op, "wrong saved request operation")
        if op == "LOAD":
            job = request["body"]
            require(job["mode"] in caps["modes"] and job["profile"] in caps["profiles"]
                    and len(job["events"]) <= caps["max_events"] and
                    int(job["total_duration_ns"]) <= int(caps["max_job_duration_ns"]),
                    "direct job exceeds CAPS")
            require(all(any(int(r["minimum_nhz"]) <= int(e["frequency_nhz"]) <=
                            int(r["maximum_nhz"]) for r in caps["frequency_ranges"])
                        for e in job["events"]), "direct frequency exceeds CAPS")
        sent = [r["value"] for r in rows if r["kind"] == "network_request" and
                r["value"]["request_id"] == request["request_id"]]
        require(sent == [request], "replay did not preserve exact request")
        flow = packets(path / (op + ".pcap"))
        incoming = [p for p in flow if p["sport"] == 18443 and p["size"]]
        outgoing = [p for p in flow if p["dport"] == 18443 and p["size"]]
        require(incoming and outgoing, "missing request or reply ciphertext")
        require(any(p["ack"] == (q["seq"] + q["size"]) % 2**32
                    for p in incoming for q in outgoing), "server did not ACK request")
        # Captures begin after negotiation. The drop filter must prevent even
        # a cumulative ACK of the first response data segment.
        first = incoming[0]
        start = flow.index(first)
        require(all((p["ack"] - first["seq"]) % 2**32 == 0
                    for p in flow[start:] if p["dport"] == 18443),
                "client acknowledged response data despite drop filter")
        require("0 packets dropped by kernel" in
                (path / (op + ".capture.log")).read_text(), "capture dropped packets")
        result[op] = dict(request_id=request["request_id"],
                          job_id=request["body"]["job_id"], packets=len(flow))
    rejected = {r["value"]["op"]: r["value"]["error"]["code"]
                for r in rows if r["kind"] == "usb_rejected"}
    require(rejected == dict(CLAIM="BUSY", ABORT="NOT_OWNER", RELEASE="NOT_OWNER"),
            "incorrect USB ownership rejection")
    final = [r["value"] for r in rows if r["kind"] == "console INFO"][-1]
    require(final["status"]["suspended"] and not final["status"]["enabled"],
            "Console override did not suspend scheduling")
    return result


def production(path, mode):
    written = audit_stream(path / "tls-write.bin")
    connections = sorted(path.glob("tls-read-connection-*.bin"))
    tails = []
    if connections:
        require(sum(p.stat().st_size for p in connections) ==
                (path / "tls-read.bin").stat().st_size, "missing connection audit records")
    read = ([r for p in connections for r in audit_stream(p, interrupted=True, tails=tails)]
            if connections else audit_stream(path / "tls-read.bin"))
    armed = read_json(path / "armed.json")
    job, session = armed["job"]["job_id"], armed["host"]["session_id"]
    mutations = [r for r in written if r["op"] in ("LOAD", "ARM")]
    require(Counter(r["op"] for r in mutations) == dict(LOAD=1, ARM=1),
            "missing or duplicate production LOAD/ARM")
    require(all(r["body"]["job_id"] == job and r["session_id"] == session
                for r in mutations), "production submitted a different job/session")
    for request in mutations:
        require(any(r["type"] == "response" and r["request_id"] == request["request_id"]
                    and r["session_id"] == session and r["op"] == request["op"] and r["ok"]
                    for r in read), "production ARM/LOAD lacks received acknowledgement")
    if mode == "fault":
        failed = read_json(path / "blocked.json")["host"]["last_report"]
        for fault in ("dns", "tls"):
            v = read_json(path / (fault + "-recovery.json"))
            s = v["body"]["status"]
            require(v["http"] == 409 and s["remote"] is None and s["job"] is None
                    and s["recovery_required"] and s["last_report"] == failed,
                    "failed reconnect changed failure/unknown state")
        require((path / "dns-failure.bin").stat().st_size > 4 and
                (path / "tls-wrong-name.bin").stat().st_size > 4, "fault did not execute")
        v = read_json(path / "restored-recovery.json")
        require(v["http"] == 200 and v["body"]["ok"] and
                v["body"]["status"]["last_report"] == failed, "recovery lost history")
    elif mode == "restart":
        new = read_json(path / "new-process-observed.json")["host"]
        require(new["session_id"] != session and not new["owns"], "new process adopted ownership")
        v = read_json(path / "new-process-cannot-cancel.json")
        require(v["http"] == 409 and not v["body"]["ok"], "new process cancelled old job")
        require(any(read_json(p)["STATUS"]["state"] == "complete"
                    for p in path.glob("restart-usb-*.json")), "old job completion not observed")
    elif mode in ("boot", "device"):
        suffix = "boot-latched-repeat.json" if mode == "boot" else "device-latched-after-restoring-route.json"
        v = read_json(path / suffix)
        require(v["http"] == 409 and v["body"]["status"]["session_phase"] == "identity_changed",
                "identity fault did not remain latched")
        if mode == "boot":
            require(read_json(path / "new-boot.json")["status"]["boot_id"] !=
                    armed["job"]["boot_id"], "no physical boot change")
        else:
            fixture = read_json(path / "fixture-exchange.json")
            require(fixture["request"]["session_id"] == session and
                    fixture["response"]["body"]["device_id"] !=
                    armed["host"]["identity"]["device_id"], "fixture did not change device identity")
            require(not (path / "fixture-after-hello.bin").read_bytes(),
                    "client submitted to changed-device fixture")
    final = read_json(path / "wtp-after.json")["STATUS"]
    require(final["output_active"] is False and final["owner_id"] is None,
            "cleanup not authoritatively inactive/unowned")
    require(read_json(path / "provider-restored.json")["state"]["outputEnabled"] is False,
            "installed provider not inactive")
    return dict(job_id=job, session_id=session, writes=len(written), reads=len(read),
                load_count=1, arm_count=1, final_boot=final["boot_id"],
                interrupted_read_suffix_bytes=tails)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direct", type=Path, required=True)
    for mode in ("fault", "restart", "boot", "device"):
        parser.add_argument("--" + mode, type=Path, required=True)
    args = parser.parse_args()
    result = {"direct": direct(args.direct)}
    result.update({mode: production(getattr(args, mode), mode)
                   for mode in ("fault", "restart", "boot", "device")})
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
