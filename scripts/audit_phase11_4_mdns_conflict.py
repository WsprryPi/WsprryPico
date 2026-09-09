#!/usr/bin/env python3
"""Offline E2/E3 packet and identity audit; no network or device operations."""

import argparse
import json
from pathlib import Path
import socket
import struct


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def dns_name(data, offset):
    labels, visited, end = [], set(), None
    while True:
        require(offset < len(data) and offset not in visited and len(visited) < 128,
                "truncated or cyclic DNS name")
        visited.add(offset)
        size = data[offset]
        if size & 0xC0 == 0xC0:
            require(offset + 1 < len(data), "truncated DNS pointer")
            if end is None:
                end = offset + 2
            offset = ((size & 63) << 8) | data[offset + 1]
            continue
        require(size <= 63 and offset + size + 1 <= len(data), "invalid DNS label")
        offset += 1
        if not size:
            return ".".join(labels).lower(), end if end is not None else offset
        labels.append(data[offset:offset + size].decode("ascii").lower())
        offset += size


def dns(data):
    require(len(data) >= 12, "truncated DNS header")
    ident, flags, nq, na, ns, nr = struct.unpack(">6H", data[:12])
    require(nq + na + ns + nr <= 128, "excessive DNS record count")
    offset, questions, records = 12, [], []
    for _ in range(nq):
        name, offset = dns_name(data, offset)
        require(offset + 4 <= len(data), "truncated question")
        kind, cls = struct.unpack(">HH", data[offset:offset + 4])
        offset += 4
        questions.append(dict(name=name, type=kind, cls=cls))
    for section, count in (("answer", na), ("authority", ns), ("additional", nr)):
        for _ in range(count):
            name, offset = dns_name(data, offset)
            require(offset + 10 <= len(data), "truncated resource record")
            kind, cls, ttl, size = struct.unpack(">HHIH", data[offset:offset + 10])
            offset += 10
            require(offset + size <= len(data), "truncated record data")
            address = socket.inet_ntoa(data[offset:offset + size]) if kind == 1 and size == 4 else None
            records.append(dict(name=name, type=kind, cls=cls, ttl=ttl,
                                address=address, section=section))
            offset += size
    require(offset == len(data), "unparsed DNS trailing bytes")
    return dict(id=ident, flags=flags, questions=questions, records=records)


def pcap(path):
    data = path.read_bytes()
    require(len(data) >= 24 and data[:4] == b"\xd4\xc3\xb2\xa1" and
            struct.unpack("<I", data[20:24])[0] == 1, "expected Ethernet microsecond PCAP")
    data, packets = data[24:], []
    while data:
        require(len(data) >= 16, "truncated capture record")
        sec, usec, size, original = struct.unpack("<4I", data[:16])
        require(size == original and len(data) >= 16 + size, "truncated captured packet")
        wire, data = data[16:16 + size], data[16 + size:]
        require(len(wire) >= 42 and wire[12:14] == b"\x08\x00", "non-IPv4 capture record")
        ip = wire[14:]
        ihl, total = (ip[0] & 15) * 4, struct.unpack(">H", ip[2:4])[0]
        require(ihl >= 20 and total <= len(ip) and ip[9] == 17 and
                struct.unpack(">H", ip[6:8])[0] & 0x3FFF == 0, "invalid or fragmented UDP capture")
        udp = ip[ihl:total]
        require(len(udp) >= 8, "truncated UDP header")
        sport, dport, length, _ = struct.unpack(">4H", udp[:8])
        require(length == len(udp) and (sport == 5353 or dport == 5353), "invalid mDNS UDP length/port")
        packets.append(dict(epoch_ns=sec * 10**9 + usec * 1000,
                            source=socket.inet_ntoa(ip[12:16]), destination=socket.inet_ntoa(ip[16:20]),
                            ttl=ip[8], sport=sport, dport=dport, dns=dns(udp[8:])))
    return packets


def audit(directory):
    rows = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
    def selected(kind):
        return [r for r in rows if r["kind"] == kind]
    initial = selected("console INFO")[0]["value"]
    name, address = initial["network"]["configured_hostname"], initial["network"]["ipv4"]
    boot, device = initial["status"]["boot_id"], initial["device_id"]
    require(initial["status"]["engine"] == "inhibited-standalone-simulator", "wrong engine")
    require({r["value"]["case"] for r in selected("CASE_PASS")} == {"E2", "E3"}, "missing result")
    running, = selected("running_before_conflict")
    conflict, = selected("conflict_during_running")
    complete, = selected("complete_during_conflict")
    recovery, = selected("recovery_begin")
    job, owner = running["value"]["job_id"], running["value"]["owner_id"]
    require(running["epoch_ns"] < conflict["epoch_ns"] < complete["epoch_ns"] < recovery["epoch_ns"],
            "wrong lifecycle order")
    for row, state in ((conflict, "running"), (complete, "complete")):
        for transport in ("tls_status", "usb_status"):
            s = row["value"][transport]
            require((s["boot_id"], s["job_id"], s["owner_id"], s["state"], s["output_active"]) ==
                    (boot, job, owner, state, False), "job/owner/boot changed across conflict")
    requests = [r["value"] for r in selected("network_request")]
    require([r["op"] for r in requests if r["op"] in ("LOAD", "ARM")] == ["LOAD", "ARM"],
            "missing or duplicate submission")
    replies = [r["value"] for r in selected("network_received") if r["value"]["type"] == "response"]
    for request in (r for r in requests if r["op"] in ("LOAD", "ARM")):
        require(request["body"]["job_id"] == job and any(
            (r["session_id"], r["request_id"], r["op"], r["ok"]) ==
            (request["session_id"], request["request_id"], request["op"], True) for r in replies),
            "missing matching job acknowledgement")
    require(all(r["value"]["network"]["configured_hostname"] == name and
                r["value"]["network"]["advertised_hostname"] in ("", name) and
                r["value"]["status"]["boot_id"] == boot for r in selected("console INFO")),
            "rename, configuration or boot change")
    require(conflict["value"]["network"]["mdns_state"] == "conflict" and
            conflict["value"]["network"]["advertised_hostname"] == "", "conflict not latched")
    packets = pcap(directory / "mdns.pcap")
    claims = selected("claimant_packet")
    claimant = claims[0]["value"]["address"]
    require(claimant != address and claims[0]["epoch_ns"] > running["epoch_ns"], "invalid conflict timing/address")
    def answers(source, value, ttl_positive, after=0):
        return [p for p in packets if p["source"] == source and p["epoch_ns"] >= after and
                p["dns"]["flags"] & 0x8000 and any(r["name"] == name and r["address"] == value and
                (r["ttl"] > 0 if ttl_positive else r["ttl"] == 0) for r in p["dns"]["records"])]
    announcements = answers(claimant, claimant, True)
    withdrawals = answers(claimant, claimant, False)
    require(announcements, "no physical claimant announcement")
    require(withdrawals, "no physical claimant withdrawal")
    require(all(p["destination"] == "224.0.0.251" and p["sport"] == p["dport"] == 5353 and
                p["ttl"] == 255 for p in announcements + withdrawals), "incorrect claimant transport")
    require(min(p["epoch_ns"] for p in announcements) < conflict["epoch_ns"] and
            any(p["epoch_ns"] < claims[0]["epoch_ns"] for p in answers(address, address, True)),
            "missing baseline or causal conflict order")
    require(not [p for p in answers(address, address, True, conflict["epoch_ns"])
                 if p["epoch_ns"] < recovery["epoch_ns"]], "Pico advertised while conflicted")
    require(all(r["name"] == name for p in packets if p["source"] == address
                for r in p["dns"]["records"] if r["type"] == 1), "Pico advertised an alternate name")
    stopped = selected("claimant_stopped")[0]
    require(complete["epoch_ns"] < stopped["epoch_ns"] < recovery["epoch_ns"], "wrong withdrawal order")
    require(any(stopped["epoch_ns"] < r["epoch_ns"] < recovery["epoch_ns"] and
                r["value"]["network"]["mdns_state"] == "conflict" for r in selected("console INFO")),
            "no latched conflict observation after withdrawal")
    recovered = answers(address, address, True, recovery["epoch_ns"])
    require(recovered, "no recovered Pico announcement")
    probes = [p for p in packets if p["source"] == address and p["epoch_ns"] >= recovery["epoch_ns"] and
              not p["dns"]["flags"] & 0x8000 and any(q["name"] == name for q in p["dns"]["questions"]) and
              any(r["name"] == name and r["address"] == address and r["section"] == "authority"
                  for r in p["dns"]["records"])]
    require(probes and min(p["epoch_ns"] for p in probes) < min(p["epoch_ns"] for p in recovered),
            "no fresh Pico probing before announcement")
    require(all(any(r["name"] == name and r["address"] == address and r["cls"] & 0x8000
                    for r in p["dns"]["records"]) for p in recovered), "recovery lacks cache flush")
    require(not answers(claimant, claimant, True, recovery["epoch_ns"]), "claimant still active during recovery")
    require("0 packets dropped by kernel" in (directory / "capture.log").read_text(), "capture drops")
    final = selected("CLEANUP_VERIFIED")[-1]["value"]
    require(final["status"]["output_active"] is False and final["status"]["owner_id"] is None and
            final["status"]["job_id"] is None and final["status"]["state"] == "empty" and
            final["status"]["boot_id"] == boot and final["info"]["device_id"] == device and
            final["info"]["network"]["mdns_state"] == "active" and
            final["info"]["network"]["advertised_hostname"] == name, "cleanup incomplete")
    for field in ("station", "schedules", "watermark_utc_ns"):
        require(final["info"]["status"][field] == initial["status"][field], "saved state changed")
    return dict(device_id=device, boot_id=boot, job_id=job, owner_id=owner, hostname=name,
                pico_address=address, claimant_address=claimant, captured_packets=len(packets),
                recovery_probes=len(probes), recovery_announcements=len(recovered), result="PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    print(json.dumps(audit(parser.parse_args().directory), indent=2))
