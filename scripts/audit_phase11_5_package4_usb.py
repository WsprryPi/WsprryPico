#!/usr/bin/env python3
"""Offline reconstruction of Phase 11.5 Package 4 USB/RF evidence."""

import argparse
import json
from pathlib import Path

from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_pilot import Decoder, check_rf_observation
from phase11_5_pilot_supervisor import configuration, finished
from phase11_5_package4_usb import (BOOT, B_BOOT, CASES, IMAGE, PEER_SHA, SOURCE,
                                    validate)
from validate_wtp_contract import crc32c


def journal_rows(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    require(rows and [row["sequence"] for row in rows] == list(range(len(rows))),
            "Package 4 journal sequence")
    require(all(a["monotonic_ns"] <= b["monotonic_ns"] for a, b in zip(rows, rows[1:])),
            "Package 4 journal monotonic order")
    return rows


def frame_payload(raw):
    require(len(raw) >= 17 and raw[:8] == b"WTPF\x01\x01\x00\x00",
            "Package 4 WTP frame header")
    size = int.from_bytes(raw[8:12], "big")
    payload = raw[16:]
    require(size == len(payload) and crc32c(payload) == int.from_bytes(raw[12:16], "big"),
            "Package 4 WTP frame length/CRC")
    return json.loads(payload)


def source_mechanisms(root):
    parser = (root / "src/wtp/frame_parser.cpp").read_text()
    endpoint = (root / "src/wtp/endpoint.cpp").read_text()
    transport = (root / "src/usb/transport.cpp").read_text()
    require("kMaximumPayloadBytes + kFrameHeaderBytes" in parser and
            "kPartialFrameTimeoutMs = 5000" in parser and
            "last_tx_progress_ms_ >= 5000" in endpoint and
            "service_.poll(); // Always serviced" in endpoint and
            "std::min(bytes.size(), kServiceBytes)" in transport and
            "wtp_reset = true" in transport, "Current USB/parser source mechanisms")
    return {"maximum_payload_bytes": 65536, "maximum_wire_bytes": 65552,
            "output_progress_timeout_ms": 5000, "usb_service_bytes": 64,
            "dtr_resets_endpoint": True}


def usb_exchanges(rows):
    requests, responses = {}, {}
    for row in rows:
        if row["kind"] == "usb_wtp_tx":
            case, value = row["value"]["case"], row["value"]["value"]
            request = frame_payload(bytes.fromhex(value["hex"]))
            require(request == value["request"], "USB request raw bytes")
            key = (case, request["request_id"])
            require(key not in requests, "Duplicate USB request journal row")
            requests[key] = request
        elif row["kind"] == "usb_wtp_message":
            case, message = row["value"]["case"], row["value"]["value"]
            if message["type"] == "response":
                key = (case, message["request_id"])
                require(key not in responses, "Duplicate USB response journal row")
                responses[key] = message
    for key, request in requests.items():
        response = responses.get(key)
        require(response is not None and response["protocol"] == "WTP/1" and
                response["session_id"] == request["session_id"] and
                response["op"] == request["op"] and response["ok"] is True,
                "USB request/response pair")
    return list(requests.values()), list(responses.values())


def network_exchanges(rows, session):
    requests = []
    for row in rows:
        if row["kind"] != "network_tx":
            continue
        value = row["value"]
        request = frame_payload(bytes.fromhex(value["hex"]))
        require(request == value["request"] and request["session_id"] == session,
                "Raw network request")
        requests.append(request)
    decoder = Decoder()
    decoded = []
    for row in rows:
        if row["kind"] == "network_rx":
            decoded.extend(decoder.feed(bytes.fromhex(row["value"]["hex"])))
    recorded = [row["value"]["message"] for row in rows if row["kind"] == "network_message"]
    require(not decoder.buffer and decoded == recorded, "Raw network response stream")
    responses = {(message["request_id"], message["op"]): message for message in decoded
                 if message["type"] == "response"}
    require(len(responses) == len(requests) and all(
        (request["request_id"], request["op"]) in responses and
        responses[(request["request_id"], request["op"])]["session_id"] == session and
        responses[(request["request_id"], request["op"])]["ok"] is True
        for request in requests), "Raw network request/response pairing")
    return len(requests), len(decoded)


def console_exchanges(rows):
    pending = None
    count = 0
    for row in rows:
        if row["kind"] == "console_tx":
            require(pending is None and bytes.fromhex(row["value"]["value"]["hex"]) == b"INFO\n",
                    "Console INFO request stream")
            pending = bytearray()
        elif row["kind"] == "console_rx":
            require(pending is not None, "Console response without request")
            pending.extend(bytes.fromhex(row["value"]["value"]["hex"]))
        elif row["kind"] == "info":
            require(pending is not None and json.loads(pending) == row["value"]["value"],
                    "Raw Console INFO response")
            pending = None
            count += 1
    require(pending is None and count > 0, "Complete Console INFO stream")
    return count


def reconciled_final(root, packet_sha, packet, before, before_b):
    require(root is not None, "Partial Package 4 result requires reconciliation evidence")
    reconcile_packet = json.loads((root / "packet.json").read_text())
    require(reconcile_packet["schema"] == "phase11.5-r3-v2-idle-reconcile-v1" and
            reconcile_packet["reservation_packet_sha256"] == packet_sha and
            reconcile_packet["allowed_complete_jobs"] == [packet["jobs"][1]["job_id"]] and
            reconcile_packet["boot_id"] == BOOT and reconcile_packet["b_boot_id"] == B_BOOT and
            reconcile_packet["rf_jobs"] == reconcile_packet["flashes"] ==
            reconcile_packet["wifi_cycles"] == reconcile_packet["configuration_writes"] == 0,
            "Exact zero-RF Package 4 reconciliation packet")
    require(digest(root / "packet.json") ==
            "d0c521b5f4976b9a0af0ed38fc933e07b16a89d4eb7f54e7bd58bc18591e121d",
            "Frozen Package 4 reconciliation packet")
    for name, sha in reconcile_packet["stage_sha256"].items():
        require(digest(root / name) == sha, "Package 4 reconciliation input changed")
    result = json.loads((root / "result.json").read_text())
    require(result["status"] == "RECONCILED_INACTIVE_UNOWNED" and
            result["rf_jobs"] == result["rf_duration_ns_charged"] == 0 and
            result["claim_attempts"] == result["release_attempts"] == 1 and
            result["reservation_released"] is True,
            "Package 4 reconciliation result")
    final = finished(root / "after-a.stdout", "READ_ONLY_INVENTORY")
    final_b = finished(root / "after-b.stdout", "READ_ONLY_INVENTORY")
    require(result["after-a"] == final["wtp"]["STATUS"] and
            result["after-b"] == final_b["wtp"]["STATUS"] and
            configuration(final) == configuration(before) and
            configuration(final_b) == configuration(before_b),
            "Package 4 reconciled inventories")
    released = json.loads((root / "rf-reservation-released.json").read_text())
    require(released["state"] == "RELEASED" and
            released["packet_sha256"] == packet_sha and
            set(released["boards"]) == {"a", "b"},
            "Package 4 reconciled reservation release")
    return final, final_b, released


def running_bracket(rows, packet, job, begin, end):
    network = [row for row in rows if row["kind"] == "network_status" and
               row["value"]["index"] == job]
    info = [row for row in rows if row["kind"] == "info"]
    for name, samples, value in (("network", network, lambda row: row["value"]["value"]),
                                 ("console", info, lambda row: row["value"]["value"])):
        before = [row for row in samples if row["monotonic_ns"] <= begin]
        during = [row for row in samples if begin <= row["monotonic_ns"] <= end]
        after = [row for row in samples if row["monotonic_ns"] >= end]
        selected = [before[-1], *during, after[0]] if before and after else []
        require(before and after and
                begin - before[-1]["monotonic_ns"] <= 2_000_000_000 and
                after[0]["monotonic_ns"] - end <= 2_000_000_000 and
                max((b["monotonic_ns"] - a["monotonic_ns"]
                     for a, b in zip(selected, selected[1:])), default=0) <= 5_000_000_000 and
                (name != "console" or during),
                name + " Package 4 causal bracket")
        for row in selected:
            status = value(row)["status"] if name == "console" else value(row)
            require(status["boot_id"] == BOOT and status["state"] == "running" and
                    status["output_active"] is True, name + " Package 4 Running authority")
            if name == "network":
                require(status["job_id"] == packet["jobs"][job]["job_id"] and
                        status["owner_id"] == packet["owner_id"],
                        "Network Package 4 job/owner authority")
            if name == "console":
                check_rf_observation(value(row))
    return {"network_samples": len(network), "console_samples": len(info)}


def audit(root, reconciliation_root=None):
    packet_sha = digest(root / "packet.json")
    packet = validate(json.loads((root / "packet.json").read_text()))
    for name, sha in packet["stage_sha256"].items():
        require(digest(root / name) == sha, "Package 4 staged input changed")
    for name, spec in packet["remote_copy_inputs"].items():
        require(digest(root / name) == spec["sha256"], "Package 4 private input changed")
    mechanisms = source_mechanisms(root)
    rows = journal_rows(root / "package4.jsonl")
    require(rows[-1]["kind"] == "finish", "Package 4 runner completion record")
    result = json.loads((root / "package4-result.json").read_text())
    require(result == rows[-1]["value"] and result["rf_jobs_charged"] == 2 and
            result["rf_duration_ns_charged"] == 200_000_000_000 and
            result["armed_jobs"] == [job["job_id"] for job in packet["jobs"]],
            "Package 4 result and finite charge")
    complete = result["status"] == "CAPTURED_REQUIRES_AUDIT"
    if complete:
        require(not result["faults"] and result["completed_jobs"] == result["armed_jobs"] and
                [case["id"] for case in result["cases"]] == ["2.3d", "2.3e"] and
                not any(row["kind"] == "failure" for row in rows),
                "Complete Package 4 runner result")
    else:
        failures = [row for row in rows if row["kind"] == "failure"]
        require(result["status"] == "STOPPED_FINAL_STATE_UNVERIFIED" and
                result["faults"] == ["supervisor: ValueError: Unread USB silence probe write"] and
                result["completed_jobs"] == [packet["jobs"][0]["job_id"]] and
                [case["id"] for case in result["cases"]] == ["2.3d"] and
                len(failures) == 1 and failures[0]["value"] == {
                    "worker": "supervisor", "type": "ValueError",
                    "error": "Unread USB silence probe write"},
                "Exact retained Package 4 partial failure")

    before = finished(root / "before-a.stdout", "READ_ONLY_INVENTORY")
    before_b = finished(root / "before-b.stdout", "READ_ONLY_INVENTORY")
    if complete:
        final = finished(root / "final-a.stdout", "READ_ONLY_INVENTORY")
        final_b = finished(root / "final-b.stdout", "READ_ONLY_INVENTORY")
        released = json.loads((root / "rf-reservation-released.json").read_text())
    else:
        final, final_b, released = reconciled_final(
            reconciliation_root, packet_sha, packet, before, before_b)
    require(before["info"]["revision"] == final["info"]["revision"] == SOURCE[:12] and
            before["wtp"]["STATUS"]["boot_id"] == final["wtp"]["STATUS"]["boot_id"] == BOOT and
            before_b["wtp"]["STATUS"]["boot_id"] == final_b["wtp"]["STATUS"]["boot_id"] == B_BOOT and
            configuration(before) == configuration(final) and
            configuration(before_b) == configuration(final_b), "Package 4 identities/configuration")
    for value in (final, final_b):
        status = value["wtp"]["STATUS"]
        require(status["state"] == "empty" and status["job_id"] is None and
                status["owner_id"] is None and status["output_active"] is False and
                value["info"]["status"]["enabled"] is False,
                "Package 4 final inactive/unowned authority")
    require(int(final["info"]["launch_epoch"]) == int(before["info"]["launch_epoch"]) + 2 and
            final["info"]["alarm_irqs"] == before["info"]["alarm_irqs"] + 2 and
            final["info"]["tail_irqs"] == before["info"]["tail_irqs"] + 2 and
            final["info"]["dma_irqs"] > before["info"]["dma_irqs"],
            "Two completed physical RF launches")
    check_rf_observation(final["info"])
    require(final["info"]["allocator_failures"] == before["info"]["allocator_failures"] == "0" and
            final["info"]["tls_allocation_failures"] == before["info"]["tls_allocation_failures"] and
            final["info"]["heap_capacity_bytes"] - final["info"]["allocator_peak_bytes"] >= 32768,
            "Package 4 resource reserve/failures")

    network_tls = [row["value"] for row in rows if row["kind"] == "network_tls"]
    require(len(network_tls) == 1 and network_tls[0]["version"] == "TLSv1.3" and
            network_tls[0]["alpn"] == "wtp/1" and network_tls[0]["peer_sha256"] == PEER_SHA,
            "Package 4 authenticated independent network authority")
    network_request_count, network_message_count = network_exchanges(
        rows, packet["network_session"])
    console_exchange_count = console_exchanges(rows)
    requests, responses = usb_exchanges(rows)
    required = [("HELLO", packet["parser_session"]), ("PING", packet["parser_session"]),
                ("HELLO", packet["parser_recovery"]), ("STATUS", packet["parser_recovery"])]
    if complete:
        required.extend([("HELLO", packet["unread_session"]),
                         ("HELLO", packet["unread_recovery_session"]),
                         ("STATUS", packet["unread_recovery_session"])])
    require(all(any(request["op"] == op and request["session_id"] == session
                        for request in requests) for op, session in required),
            "Package 4 fresh USB HELLO/recovery exchanges")

    parser_start, = [row for row in rows if row["kind"] == "usb_parser_start"]
    parser_end, = [row for row in rows if row["kind"] == "usb_parser_end"]
    parser_recovery, = [row for row in rows if row["kind"] == "usb_parser_recovery"]
    maximum = wtp = None
    from phase11_5_r3_capacity_plan import wtp_capacity_frame
    maximum = wtp_capacity_frame(packet["parser_session"], packet["parser_request"])
    require(parser_start["value"]["payload_bytes"] == 65536 and
            parser_start["value"]["wire_bytes"] == len(maximum) == 65552 and
            parser_start["value"]["sha256"] == digest_bytes(maximum) and
            parser_end["value"]["written_bytes"] == 65552 and
            parser_end["value"]["same_connection_recovery"] is True,
            "2.3d exact maximum parser bytes and recovery")
    parser_decoder = Decoder()
    parser_messages = parser_decoder.feed(b"".join(
        bytes.fromhex(row["value"]["hex"]) for row in rows
        if row["kind"] == "usb_parser_rx" and
        parser_start["monotonic_ns"] <= row["monotonic_ns"] <= parser_end["monotonic_ns"]))
    recorded_parser_messages = [row["value"] for row in rows
        if row["kind"] == "usb_parser_message" and
        parser_start["monotonic_ns"] <= row["monotonic_ns"] <= parser_end["monotonic_ns"]]
    require(not parser_decoder.buffer and parser_messages == recorded_parser_messages and
            len(parser_messages) == 1, "2.3d raw parser response")
    parser_infos = [row["value"]["value"] for row in rows if row["kind"] == "info" and
                    parser_start["monotonic_ns"] <= row["monotonic_ns"] <= parser_end["monotonic_ns"]]
    require(parser_infos and max(info["wtp_input_reserved_bytes"] for info in parser_infos) >= 65552,
            "2.3d directly observed maximum USB parser reservation")
    parser_coverage = running_bracket(rows, packet, 0, parser_start["monotonic_ns"],
                                      parser_recovery["monotonic_ns"])

    unread_start, = [row for row in rows if row["kind"] == "usb_unread_start"]
    unread_offered, = [row for row in rows if row["kind"] == "usb_unread_offered"]
    unread_hold, = [row for row in rows if row["kind"] == "usb_unread_hold_complete"]
    unread_drained, = [row for row in rows if row["kind"] == "usb_unread_drained"]
    require(unread_start["value"]["application_reads"] == 0 and
            unread_offered["value"]["application_reads"] == 0 and
            unread_hold["value"]["application_reads"] == 0 and
            unread_hold["value"]["hold_seconds"] == 12 and
            unread_hold["monotonic_ns"] - unread_offered["monotonic_ns"] >= 12_000_000_000 and
            16 <= unread_offered["value"]["complete_requests"] <= 1024 and
            unread_offered["value"]["written_bytes"] <= unread_start["value"]["maximum_wire_bytes"] and
            unread_drained["value"]["complete_requests"] == unread_offered["value"]["complete_requests"] and
            unread_drained["value"]["response_count"] < unread_drained["value"]["complete_requests"] and
            unread_drained["value"]["captured_bytes"] <= 1048576 and
            unread_drained["value"]["captured_bytes"] ==
            len(bytes.fromhex(unread_drained["value"]["captured_hex"])),
            "2.3e bounded zero-read trigger and response deficit")
    decoder = Decoder()
    captured_messages = decoder.feed(bytes.fromhex(unread_drained["value"]["captured_hex"]))
    require(len(decoder.buffer) == unread_drained["value"]["trailing_response_bytes"] < 65552 and
            [m["request_id"] for m in captured_messages if m["type"] == "response"] ==
            unread_drained["value"]["response_ids"], "2.3e raw delayed USB capture")
    if complete:
        unread_silent, = [row for row in rows if row["kind"] == "usb_unread_silent"]
        unread_recovery, = [row for row in rows if row["kind"] == "usb_unread_recovery"]
        require(unread_silent["value"] == {"probe_hex": unread_silent["value"]["probe_hex"],
                    "silence_seconds": 2, "received_bytes": 0},
                "2.3e pre-DTR silence")
        probe = frame_payload(bytes.fromhex(unread_silent["value"]["probe_hex"]))
        require(probe["session_id"] == packet["unread_session"] and
                probe["request_id"] == packet["unread_probe"] and probe["op"] == "PING",
                "2.3e same-session silence probe")
        unread_coverage = running_bracket(rows, packet, 1, unread_start["monotonic_ns"],
                                          unread_recovery["monotonic_ns"])
    else:
        require(not any(row["kind"] in ("usb_unread_silent", "usb_unread_recovery")
                        for row in rows),
                "Failed 2.3e must not contain missing proof/recovery records")
        unread_coverage = running_bracket(rows, packet, 1, unread_start["monotonic_ns"],
                                          unread_drained["monotonic_ns"])

    completed = [row["value"] for row in rows if row["kind"] == "job_complete"]
    expected_completed = packet["jobs"] if complete else packet["jobs"][:1]
    require([value["job_id"] for value in completed] ==
            [job["job_id"] for job in expected_completed] and
            all(value["status"]["state"] == "complete" and
                value["status"]["output_active"] is False for value in completed),
            "Package 4 runner-observed finite jobs completed inactive")
    if not complete:
        require(any(record["job_id"] == packet["jobs"][1]["job_id"] and
                    record["state"] == "complete" and record["output_active"] is False
                    for record in final["wtp"]["STATUS"]["terminal_records"]),
                "Reconciliation observed the second finite job complete")
    acquired = json.loads((root / "rf-reservation-acquired.json").read_text())
    require(acquired["state"] == "HELD" and released["state"] == "RELEASED" and
            acquired["packet_sha256"] == released["packet_sha256"] == packet_sha and
            set(acquired["boards"]) == set(released["boards"]) == {"a", "b"},
            "Package 4 durable RF reservation lifecycle")

    status = "PACKAGE4_VERIFIED" if complete else "PACKAGE4_PARTIAL_VERIFIED"
    assertions = {"2.3d": "ACCEPTED", "2.3e": "ACCEPTED" if complete else
                  "OPEN_MISSING_SAME_SESSION_SILENCE_AND_DTR_RECOVERY"}
    unread = {"written_bytes": unread_offered["value"]["written_bytes"],
        "complete_requests": unread_drained["value"]["complete_requests"],
        "responses_before_close": unread_drained["value"]["response_count"],
        "hold_seconds": 12, "pre_dtr_probe_silent": complete,
        "fresh_hello_status_recovery": complete, **unread_coverage}
    if not complete:
        unread["failure"] = "Unread USB silence probe write"
        unread["host_output_queue_flush_fix"] = "NOT_PRESENT_IN_FROZEN_PACKET"
    return {"schema": "phase11.5-package4-audit-v1", "status": status,
        "packet_sha256": packet_sha, "source_revision": SOURCE, "image_sha256": IMAGE,
        "boot_id": BOOT, "assertions": assertions,
        "mechanisms": mechanisms, "parser": {"wire_bytes": 65552,
            "maximum_reserved_bytes": max(info["wtp_input_reserved_bytes"] for info in parser_infos),
            "same_connection_recovery": True, "dtr_recovery": True,
            "network_request_count": network_request_count,
            "network_message_count": network_message_count,
            "console_exchange_count": console_exchange_count, **parser_coverage},
        "unread": unread,
        "rf_jobs": 2, "rf_duration_ns": 200_000_000_000,
        "absolute_rf_jobs": packet["absolute_rf_jobs"],
        "absolute_rf_duration_ns": packet["absolute_rf_duration_ns"],
        "fixture_recovery": packet.get("fixture_recovery"),
        "execution_history": packet.get("execution_history"),
        "configuration_preserved": True, "pico_b_unchanged": True,
        "final_inactive_unowned": True, "reservation_released": True,
        "reconciliation_packet_sha256": None if complete else
            digest(reconciliation_root / "packet.json")}


def digest_bytes(value):
    import hashlib
    return hashlib.sha256(value).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--reconciliation-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.root.resolve(strict=True),
                   args.reconciliation_root.resolve(strict=True)
                   if args.reconciliation_root else None)
    raw = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(raw)
    print(raw, end="")


if __name__ == "__main__":
    main()
