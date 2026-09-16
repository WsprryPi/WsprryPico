#!/usr/bin/env python3
"""Audit the rejected one-job 2.3e retest and its zero-RF restoration."""

import argparse
import json
from pathlib import Path

from audit_phase11_5_package4_unread_retest import fixture_restored
from audit_phase11_5_package4_usb import (console_exchanges, frame_payload, journal_rows,
                                          network_exchanges)
from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_package4_unread_retest import validate
from phase11_5_package4_usb import BOOT, B_BOOT, IMAGE, SOURCE
from phase11_5_pilot import Decoder
from phase11_5_pilot_supervisor import configuration, finished


EXPECTED_PACKET = "10fe965e5ac0e15d58226aaab598ca9671ed0d5009149e5f737b26f6499607ba"
EXPECTED_JOB = "eda66092283064e6539f8ffd59e3cb9d"
EXPECTED_EVIDENCE = {
    "unread-retest.jsonl": "ff8ef6e754aa1266f384808f62af57e355e8e709eaee54a0d901585bcd17ce6c",
    "unread-retest-result.json": "a0071448cbdb22026bfbef8dda4cc947f5d0ef1b532f2c7817d22dce3436e519",
    "before-a.stdout": "823860e77d059e6390ecf0663a0dde1692ce69387a951a2d41e3784fc71f6bac",
    "before-b.stdout": "d844d7b040f67663a5184caa7692a932a9a05a037f25d41bb48975d2c6c913f0",
    "post-completion-a.jsonl": "1c733dcbb39e79d4a2dd351957f3646037e2022ca1179cf4235f3aeb96e599eb",
    "post-failure-release.jsonl": "e80a24bfca7e613bbf4c5ed7b6cf2ae91344ff0459828f70ccdabd8b47c952a3",
    "reconciled-a.stdout": "4ccc778f6ecb38c88cf20df687b651f7bc516a41d4cef374aeb2ccea2597f325",
    "reconciled-b.stdout": "1c59eace39143eb80ee5d6362f7c1d7c0443e89f86eacf586721bedcb69df779",
    "rf-reservation-acquired.json": "ee38f8a16e7af0a4f353ef87eb090c9520764d5fd096310fead392787447650e",
    "rf-reservation-reconciled.json": "29846c0af1c17b6c47e8f985ee03ca5e6fc2a1fb65281581549148db7df39794",
}
EXPECTED_FIXTURE = {
    "packet.json": "0084f965781aaf591f55c6d2a7b6252876d29c8dd455a0ae48d33c9803b828ea",
    "fixture.jsonl": "b366f523ae33231facc25cd1166b93391691baa57ea1f6b7c76316af0ef6d1f1",
    "fixture-state.json": "1369c01240741bea51728276d67eb4926e834fa3144e9c01f97613c852dc665c",
    "capture-ap.pcap": "5ebbafcae83bd388953ce1dd4009e62f17bf082798fff2bcc5525fd655d6a3bd",
    "capture-client.pcap": "0c5ed5b9f9e0b24898f6bb3a48da1f9e46e476540850d6c427adb2f4a523d4e3",
}


def recovery_rows(path, packet):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    require(rows and all(a["monotonic_ns"] <= b["monotonic_ns"]
                         for a, b in zip(rows, rows[1:])),
            "Recovery evidence order")
    requests = [row["value"]["request"] for row in rows if row["kind"] == "wtp_tx"]
    require([request["op"] for request in requests] ==
            ["HELLO", "STATUS", "CLAIM", "RELEASE", "STATUS"] and
            len({request["request_id"] for request in requests}) == len(requests) and
            len({request["session_id"] for request in requests}) == 1,
            "Exact zero-RF terminal recovery operations")
    for row, request in zip((row for row in rows if row["kind"] == "wtp_tx"), requests):
        require(frame_payload(bytes.fromhex(row["value"]["hex"])) == request,
                "Recovery raw request binding")
    decoder = Decoder()
    raw_messages = []
    for row in rows:
        if row["kind"] == "wtp_rx":
            raw_messages.extend(decoder.feed(bytes.fromhex(row["value"]["hex"])))
    require(not decoder.buffer and raw_messages ==
            [row["value"] for row in rows if row["kind"] == "wtp_message"],
            "Recovery raw response/event binding")
    responses = [message for message in raw_messages if message["type"] == "response"]
    require([message["op"] for message in responses] ==
            ["HELLO", "STATUS", "CLAIM", "RELEASE", "STATUS"] and
            all(message["ok"] is True for message in responses),
            "Recovery responses")
    before, final = responses[1]["body"], responses[-1]["body"]
    require(before["boot_id"] == final["boot_id"] == BOOT and
            before["state"] == "complete" and before["output_active"] is False and
            before["owner_id"] is None and before["job_id"] == EXPECTED_JOB and
            final["state"] == "empty" and final["output_active"] is False and
            final["owner_id"] is None and final["job_id"] is None and
            any(record["job_id"] == EXPECTED_JOB and record["state"] == "complete" and
                record["output_active"] is False for record in final["terminal_records"]),
            "Recovery Complete to Empty authority")
    restored = [row["value"] for row in rows if row["kind"] == "restored"]
    require(restored == [final], "Recovery final summary")
    return before, final


def audit(root, fixture_root, require_original_paths=True):
    packet_sha = digest(root / "packet.json")
    require(packet_sha == EXPECTED_PACKET, "Exact failed retest packet")
    packet = validate(json.loads((root / "packet.json").read_text()))
    require(packet["job"]["job_id"] == EXPECTED_JOB, "Exact failed retest job")
    require(all(digest(root / name) == sha for name, sha in EXPECTED_EVIDENCE.items()) and
            all(digest(fixture_root / name) == sha for name, sha in EXPECTED_FIXTURE.items()),
            "Frozen failed retest evidence")
    for name, sha in packet["stage_sha256"].items():
        require(digest(root / name) == sha, "Failed retest staged input changed")
    for name, spec in packet["remote_copy_inputs"].items():
        require(digest(root / name) == spec["sha256"], "Failed retest private input changed")

    rows = journal_rows(root / "unread-retest.jsonl")
    network_request_count, network_message_count = network_exchanges(
        rows, packet["network_session"])
    console_exchange_count = console_exchanges(rows)
    result = json.loads((root / "unread-retest-result.json").read_text())
    fault_rows = [row for row in rows if row["kind"] == "failure"]
    faults = [row["value"] for row in fault_rows]
    require(rows[-1]["kind"] == "finish" and rows[-1]["value"] == result and
            result["status"] == "STOPPED_FINAL_STATE_UNVERIFIED" and
            result["armed_jobs"] == [EXPECTED_JOB] and not result["completed_jobs"] and
            result["rf_jobs_charged"] == 1 and
            result["rf_duration_ns_charged"] == 100_000_000_000 and
            result["case"] is None and result["renewals"] == 0 and
            result["faults"] == [
                "network: ValueError: Console Running authority",
                "supervisor: ValueError: Unread retest Running gate",
                "runner: ValueError: Unread retest observer/authority failure",
                "final-a: ValueError: not authoritatively idle"],
            "Exact failed retest result")
    require([fault["worker"] for fault in faults] ==
            ["network", "supervisor", "runner", "final-a"] and
            not any(row["kind"].startswith("usb_unread") for row in rows),
            "Failure boundary before unread pressure")

    running = next(row for row in rows if row["kind"] == "network_status" and
                   row["value"]["value"]["state"] == "running")
    prior_console = [row for row in rows if row["kind"] == "info" and
                     row["monotonic_ns"] < running["monotonic_ns"]][-1]
    network_status = running["value"]["value"]
    console_status = prior_console["value"]["value"]["status"]
    gap = running["monotonic_ns"] - prior_console["monotonic_ns"]
    require(network_status["boot_id"] == BOOT and network_status["state"] == "running" and
            network_status["output_active"] is True and
            network_status["job_id"] == EXPECTED_JOB and
            network_status["owner_id"] == packet["owner_id"] and
            console_status["boot_id"] == BOOT and console_status["state"] == "armed" and
            console_status["output_active"] is False and 0 < gap < 500_000_000 and
            faults[0]["worker"] == "network" and
            0 <= fault_rows[0]["monotonic_ns"] - running["monotonic_ns"] < 20_000_000,
            "Observer transition race")

    before = finished(root / "before-a.stdout", "READ_ONLY_INVENTORY")
    before_b = finished(root / "before-b.stdout", "READ_ONLY_INVENTORY")
    completed = finished(root / "post-completion-a.jsonl", "READ_ONLY_INVENTORY")
    completed_status = completed["wtp"]["STATUS"]
    require(completed["info"]["revision"] == SOURCE[:12] and
            completed_status["boot_id"] == BOOT and
            completed_status["state"] == "complete" and
            completed_status["output_active"] is False and
            completed_status["owner_id"] is None and completed_status["job_id"] == EXPECTED_JOB and
            any(record["job_id"] == EXPECTED_JOB and record["state"] == "complete" and
                record["output_active"] is False
                for record in completed_status["terminal_records"]),
            "One local completion after harness stop")
    recovery_rows(root / "post-failure-release.jsonl", packet)
    final = finished(root / "reconciled-a.stdout", "READ_ONLY_INVENTORY")
    final_b = finished(root / "reconciled-b.stdout", "READ_ONLY_INVENTORY")
    for value, boot in ((final, BOOT), (final_b, B_BOOT)):
        status = value["wtp"]["STATUS"]
        require(status["boot_id"] == boot and status["state"] == "empty" and
                status["output_active"] is False and status["owner_id"] is None and
                status["job_id"] is None and value["info"]["status"]["enabled"] is False,
                "Failed retest final authority")
    require(configuration(final) == configuration(before) and
            configuration(final_b) == configuration(before_b) and
            final_b["info"]["revision"] == before_b["info"]["revision"] and
            int(final["info"]["launch_epoch"]) == int(before["info"]["launch_epoch"]) + 1 and
            final["info"]["alarm_irqs"] == before["info"]["alarm_irqs"] + 1 and
            final["info"]["tail_irqs"] == before["info"]["tail_irqs"] + 1 and
            final["info"]["allocator_failures"] == before["info"]["allocator_failures"] == "0" and
            all(final["info"][key] == 0 for key in
                ("fault_stage", "fault_hash", "fault_pc", "fault_status")),
            "One healthy launch and preserved configuration")

    acquired = json.loads((root / "rf-reservation-acquired.json").read_text())
    released = json.loads((root / "rf-reservation-reconciled.json").read_text())
    require(acquired["state"] == "HELD" and released["state"] == "RELEASED" and
            acquired["packet_sha256"] == released["packet_sha256"] == packet_sha and
            set(acquired["boards"]) == set(released["boards"]) == {"a", "b"} and
            all(released["boards"][name]["state"] == "empty" for name in ("a", "b")),
            "Failed retest reservation reconciliation")
    fixture_sha = fixture_restored(fixture_root)
    require((not require_original_paths or str(fixture_root) == packet["fixture_root"]) and
            fixture_sha == packet["fixture_packet_sha256"],
            "Failed retest fixture binding/restoration")
    return {
        "schema": "phase11.5-package4-unread-retest-failure-audit-v1",
        "status": "RETEST_FAILURE_VERIFIED",
        "packet_sha256": packet_sha,
        "fixture_packet_sha256": fixture_sha,
        "source_revision": SOURCE,
        "image_sha256": IMAGE,
        "boot_id": BOOT,
        "assertion": {"2.3e": "OPEN_NO_UNREAD_PRESSURE_EXECUTED"},
        "charged_rf_jobs": 1,
        "charged_rf_duration_ns": 100_000_000_000,
        "console_to_network_sample_gap_ns": gap,
        "network_request_count": network_request_count,
        "network_message_count": network_message_count,
        "console_exchange_count": console_exchange_count,
        "job_completed_inactive": True,
        "configuration_preserved": True,
        "pico_b_unchanged": True,
        "reservation_released": True,
        "fixture_restored": True,
    }


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
