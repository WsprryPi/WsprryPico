#!/usr/bin/env python3
"""Offline audit of the one-job Phase 11.5 assertion 2.3e retest."""

import argparse
import json
from pathlib import Path

from audit_phase11_5_package4_usb import (console_exchanges, digest_bytes, frame_payload,
                                          journal_rows, network_exchanges, source_mechanisms,
                                          usb_exchanges)
from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_package4_unread_retest import CASE, validate
from phase11_5_package4_usb import BOOT, B_BOOT, IMAGE, PEER_SHA, SOURCE
from phase11_5_pilot import Decoder, check_rf_observation
from phase11_5_pilot_supervisor import configuration, finished
from validate_wtp_contract import frame


def running_bracket(rows, packet, begin, end):
    groups = {
        "network": ([row for row in rows if row["kind"] == "network_status"],
                    lambda row: row["value"]["value"]),
        "console": ([row for row in rows if row["kind"] == "info"],
                    lambda row: row["value"]["value"]["status"]),
    }
    counts = {}
    for name, (samples, value) in groups.items():
        before = [row for row in samples if row["monotonic_ns"] <= begin]
        during = [row for row in samples if begin <= row["monotonic_ns"] <= end]
        after = [row for row in samples if row["monotonic_ns"] >= end]
        selected = [before[-1], *during, after[0]] if before and after else []
        require(before and during and after and
                begin - before[-1]["monotonic_ns"] <= 2_000_000_000 and
                after[0]["monotonic_ns"] - end <= 2_000_000_000 and
                max((b["monotonic_ns"] - a["monotonic_ns"]
                     for a, b in zip(selected, selected[1:])), default=0) <= 5_000_000_000,
                name + " unread retest causal bracket")
        for row in selected:
            status = value(row)
            require(status["boot_id"] == BOOT and status["state"] == "running" and
                    status["output_active"] is True, name + " unread Running authority")
            if name == "network":
                require(status["job_id"] == packet["job"]["job_id"] and
                        status["owner_id"] == packet["owner_id"],
                        "Unread network job/owner authority")
        counts[name + "_samples"] = len(samples)
    return counts


def fixture_restored(root):
    packet_sha = digest(root / "packet.json")
    state = json.loads((root / "fixture-state.json").read_text())
    rows = [json.loads(line) for line in (root / "fixture.jsonl").read_text().splitlines()]
    cleanup = [row for row in rows if row["kind"] == "cleanup"]
    restored = [row for row in rows if row["kind"] == "host_restored"]
    require(state["restored"] is True and len(cleanup) == len(restored) == 1 and
            cleanup[0]["value"]["failures"] == [] and
            restored[0]["value"] == state["before"], "Exact host fixture restoration")
    return packet_sha


def audit(root, fixture_root, require_original_paths=True):
    packet_sha = digest(root / "packet.json")
    packet = validate(json.loads((root / "packet.json").read_text()))
    for name, sha in packet["stage_sha256"].items():
        require(digest(root / name) == sha, "Unread retest staged input changed")
    for name, spec in packet["remote_copy_inputs"].items():
        require(digest(root / name) == spec["sha256"], "Unread retest private input changed")
    mechanisms = source_mechanisms(root)
    rows = journal_rows(root / "unread-retest.jsonl")
    require(rows[-1]["kind"] == "finish" and
            not any(row["kind"] == "failure" for row in rows),
            "Unread retest runner completion")
    result = json.loads((root / "unread-retest-result.json").read_text())
    require(result == rows[-1]["value"] and result["status"] == "CAPTURED_REQUIRES_AUDIT" and
            not result["faults"] and result["rf_jobs_charged"] == 1 and
            result["rf_duration_ns_charged"] == 100_000_000_000 and
            result["armed_jobs"] == result["completed_jobs"] == [packet["job"]["job_id"]] and
            result["case"]["id"] == "2.3e" and
            result["case"]["status"] == "CAPTURED_REQUIRES_AUDIT",
            "Unread retest result and finite charge")

    before = finished(root / "before-a.stdout", "READ_ONLY_INVENTORY")
    before_b = finished(root / "before-b.stdout", "READ_ONLY_INVENTORY")
    final = finished(root / "final-a.stdout", "READ_ONLY_INVENTORY")
    final_b = finished(root / "final-b.stdout", "READ_ONLY_INVENTORY")
    require(before["info"]["revision"] == final["info"]["revision"] == SOURCE[:12] and
            before["wtp"]["STATUS"]["boot_id"] == final["wtp"]["STATUS"]["boot_id"] == BOOT and
            before_b["wtp"]["STATUS"]["boot_id"] ==
            final_b["wtp"]["STATUS"]["boot_id"] == B_BOOT and
            configuration(before) == configuration(final) and
            configuration(before_b) == configuration(final_b),
            "Unread retest identities/configuration")
    for value in (final, final_b):
        status = value["wtp"]["STATUS"]
        require(status["state"] == "empty" and status["job_id"] is None and
                status["owner_id"] is None and status["output_active"] is False and
                value["info"]["status"]["enabled"] is False,
                "Unread retest final inactive/unowned authority")
    require(final_b["wtp"]["STATUS"] == before_b["wtp"]["STATUS"] and
            int(final["info"]["launch_epoch"]) == int(before["info"]["launch_epoch"]) + 1 and
            final["info"]["alarm_irqs"] == before["info"]["alarm_irqs"] + 1 and
            final["info"]["tail_irqs"] == before["info"]["tail_irqs"] + 1 and
            final["info"]["dma_irqs"] > before["info"]["dma_irqs"],
            "One completed unread retest RF launch")
    check_rf_observation(final["info"])
    require(final["info"]["allocator_failures"] == before["info"]["allocator_failures"] == "0" and
            final["info"]["tls_allocation_failures"] ==
            before["info"]["tls_allocation_failures"] and
            final["info"]["heap_capacity_bytes"] - final["info"]["allocator_peak_bytes"] >= 32768,
            "Unread retest resource reserve/failures")

    network_tls = [row["value"] for row in rows if row["kind"] == "network_tls"]
    require(len(network_tls) == 1 and network_tls[0]["version"] == "TLSv1.3" and
            network_tls[0]["alpn"] == "wtp/1" and
            network_tls[0]["peer_sha256"] == PEER_SHA,
            "Unread retest authenticated network authority")
    network_request_count, network_message_count = network_exchanges(
        rows, packet["network_session"])
    console_exchange_count = console_exchanges(rows)
    requests, responses = usb_exchanges(rows)
    required = [("HELLO", packet["unread_session"]),
                ("HELLO", packet["unread_recovery_session"]),
                ("STATUS", packet["unread_recovery_session"])]
    require(all(any(request["op"] == op and request["session_id"] == session
                        for request in requests) for op, session in required),
            "Unread retest fresh USB HELLO/recovery exchanges")

    unread_start, = [row for row in rows if row["kind"] == "usb_unread_start"]
    unread_offered, = [row for row in rows if row["kind"] == "usb_unread_offered"]
    unread_hold, = [row for row in rows if row["kind"] == "usb_unread_hold_complete"]
    unread_drained, = [row for row in rows if row["kind"] == "usb_unread_drained"]
    flushed, = [row for row in rows if row["kind"] == "usb_unread_host_output_flushed"]
    unread_silent, = [row for row in rows if row["kind"] == "usb_unread_silent"]
    unread_recovery, = [row for row in rows if row["kind"] == "usb_unread_recovery"]
    require(unread_start["monotonic_ns"] < unread_offered["monotonic_ns"] <
            unread_hold["monotonic_ns"] < unread_drained["monotonic_ns"] <
            flushed["monotonic_ns"] < unread_silent["monotonic_ns"] <
            unread_recovery["monotonic_ns"] and
            unread_start["value"]["application_reads"] == 0 and
            unread_offered["value"]["application_reads"] == 0 and
            unread_hold["value"] == {"hold_seconds": 12, "application_reads": 0} and
            unread_hold["monotonic_ns"] - unread_offered["monotonic_ns"] >= 12_000_000_000 and
            16 <= unread_offered["value"]["complete_requests"] <= 1024 and
            unread_offered["value"]["written_bytes"] <= unread_start["value"]["maximum_wire_bytes"] and
            unread_drained["value"]["complete_requests"] ==
            unread_offered["value"]["complete_requests"] and
            unread_drained["value"]["response_count"] <
            unread_drained["value"]["complete_requests"] and
            unread_drained["value"]["captured_bytes"] <= 1048576 and
            unread_drained["value"]["captured_bytes"] ==
            len(bytes.fromhex(unread_drained["value"]["captured_hex"])) and
            flushed["value"] == {"dtr_remained_asserted": True} and
            unread_silent["value"]["silence_seconds"] == 2 and
            unread_silent["value"]["received_bytes"] == 0,
            "2.3e bounded zero-read, flush, response deficit and silence")
    expected_raw = bytearray()
    for index in range(packet["usb"]["unread_max_requests"]):
        request = {"type": "request", "protocol": "WTP/1",
            "session_id": packet["unread_session"],
            "request_id": __import__("hashlib").sha256(
                f"{packet['unread_session']}:{index}".encode()).hexdigest()[:32],
            "op": "STATUS", "body": {}}
        expected_raw.extend(frame(json.dumps(request, separators=(",", ":")).encode()))
    require(unread_start["value"]["sha256"] == digest_bytes(expected_raw) and
            unread_start["value"]["maximum_wire_bytes"] == len(expected_raw),
            "2.3e exact offered request stream")
    probe = frame_payload(bytes.fromhex(unread_silent["value"]["probe_hex"]))
    require(probe == {"type": "request", "protocol": "WTP/1",
            "session_id": packet["unread_session"], "request_id": packet["unread_probe"],
            "op": "PING", "body": {"token": "after-unread"}},
            "2.3e exact same-session silence probe")
    decoder = Decoder()
    captured_messages = decoder.feed(bytes.fromhex(unread_drained["value"]["captured_hex"]))
    require(len(decoder.buffer) == unread_drained["value"]["trailing_response_bytes"] < 65552 and
            [message["request_id"] for message in captured_messages
             if message["type"] == "response"] == unread_drained["value"]["response_ids"],
            "2.3e raw delayed USB capture")
    coverage = running_bracket(rows, packet, unread_start["monotonic_ns"],
                               unread_recovery["monotonic_ns"])

    completed = [row["value"] for row in rows if row["kind"] == "job_complete"]
    require(len(completed) == 1 and completed[0]["job_id"] == packet["job"]["job_id"] and
            completed[0]["status"]["state"] == "complete" and
            completed[0]["status"]["output_active"] is False,
            "Unread retest finite job completed inactive")
    acquired = json.loads((root / "rf-reservation-acquired.json").read_text())
    released = json.loads((root / "rf-reservation-released.json").read_text())
    require(acquired["state"] == "HELD" and released["state"] == "RELEASED" and
            acquired["packet_sha256"] == released["packet_sha256"] == packet_sha and
            set(acquired["boards"]) == set(released["boards"]) == {"a", "b"},
            "Unread retest reservation lifecycle")
    fixture_sha = fixture_restored(fixture_root)
    require((not require_original_paths or str(fixture_root) == packet["fixture_root"]) and
            fixture_sha == packet["fixture_packet_sha256"],
            "Unread retest fixture packet binding")

    return {"schema": "phase11.5-package4-unread-retest-audit-v1",
        "status": "PACKAGE4_2_3E_VERIFIED", "packet_sha256": packet_sha,
        "fixture_packet_sha256": fixture_sha, "source_revision": SOURCE,
        "image_sha256": IMAGE, "boot_id": BOOT, "assertion": {"2.3e": "ACCEPTED"},
        "mechanisms": mechanisms,
        "unread": {"written_bytes": unread_offered["value"]["written_bytes"],
            "complete_requests": unread_drained["value"]["complete_requests"],
            "responses_before_close": unread_drained["value"]["response_count"],
            "trailing_response_bytes": unread_drained["value"]["trailing_response_bytes"],
            "hold_seconds": 12, "host_output_flushed_with_dtr_asserted": True,
            "pre_dtr_probe_silent": True, "silence_seconds": 2,
            "fresh_hello_status_recovery": True,
            "network_request_count": network_request_count,
            "network_message_count": network_message_count,
            "console_exchange_count": console_exchange_count, **coverage},
        "rf_jobs": 1, "rf_duration_ns": 100_000_000_000,
        "configuration_preserved": True, "pico_b_unchanged": True,
        "final_inactive_unowned": True, "reservation_released": True,
        "fixture_restored": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.root.resolve(strict=True), args.fixture_root.resolve(strict=True))
    raw = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(raw)
    print(raw, end="")


if __name__ == "__main__":
    main()
