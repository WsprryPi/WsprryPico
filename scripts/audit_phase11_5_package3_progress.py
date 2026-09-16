#!/usr/bin/env python3
"""Offline audit of Package 3 network-WTP timeout evidence."""

import argparse
import hashlib
import json
from pathlib import Path

from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_pilot_supervisor import configuration, finished
from phase11_5_package3_progress import BOOT, CASES, PEER_SHA, SOURCE, validate
from phase11_5_r3_v2_admission import maximum_job
from validate_wtp_contract import crc32c, frame


def rows(path):
    values = [json.loads(line) for line in path.read_text().splitlines()]
    require([row["sequence"] for row in values] == list(range(len(values))), "Progress journal sequence")
    require(all(a["monotonic_ns"] < b["monotonic_ns"] for a, b in zip(values, values[1:])),
            "Progress journal monotonic order")
    return values


def frame_payload(raw):
    require(raw[:8] == b"WTPF\x01\x01\x00\x00" and len(raw) >= 17, "WTP frame header")
    size = int.from_bytes(raw[8:12], "big")
    checksum = int.from_bytes(raw[12:16], "big")
    payload = raw[16:]
    require(size == len(payload) and crc32c(payload) == checksum, "WTP frame size/checksum")
    return json.loads(payload)


def http_body(raw):
    head, body = raw.split(b"\r\n\r\n", 1)
    status_line = head.split(b"\r\n", 1)[0].split(b" ", 2)
    require(len(status_line) == 3 and status_line[:2] == [b"HTTP/1.1", b"200"],
            "HTTPS status code")
    lengths = [line.split(b":", 1)[1].strip() for line in head.split(b"\r\n")
               if line.lower().startswith(b"content-length:")]
    require(len(lengths) == 1 and len(body) == int(lengths[0]), "HTTPS Content-Length")
    return json.loads(body)


def paired_message(journal, label, operation, session):
    tx, = [row["value"] for row in journal
           if row["kind"] == "wtp_tx" and row["value"]["label"] == label]
    rx, = [row["value"]["message"] for row in journal
           if row["kind"] == "wtp_message" and row["value"]["label"] == label and
           row["value"]["message"]["type"] == "response"]
    request = frame_payload(bytes.fromhex(tx["hex"]))
    require(request == tx["request"] and request["type"] == "request" and
            request["protocol"] == "WTP/1" and request["session_id"] == session and
            request["op"] == operation and rx["protocol"] == "WTP/1" and
            rx["session_id"] == session and rx["request_id"] == request["request_id"] and
            rx["op"] == operation and rx["ok"] is True,
            "Raw WTP request/response pair: " + label)
    return request, rx


def source_thresholds(root):
    server = (root / "source/server.cpp").read_text()
    endpoint = (root / "source/endpoint.cpp").read_text()
    parser = (root / "source/frame_parser.cpp").read_text()
    app = (root / "source/app.js").read_text()
    expected = {
        "pending_tcp_ms": "pending_since_ms_ >= 10000",
        "activated_tls_ms": "accepted_ms_ >= 10000",
        "http_activation_ms": "accepted_ms_ >= 15000",
        "established_progress_ms": "progress_ms_ >= 30000",
        "failed_alert_ms": "progress_ms_ >= 1000",
        "wtp_output_progress_ms": "last_tx_progress_ms_ >= 5000",
        "wtp_pending_input_ms": "pending_input_since_ms_ >= 5000",
        "partial_frame_ms": "kPartialFrameTimeoutMs = 5000",
        "browser_file_bytes": "file.size > 30000",
    }
    texts = {
        "pending_tcp_ms": server,
        "activated_tls_ms": server,
        "http_activation_ms": server,
        "established_progress_ms": server,
        "failed_alert_ms": server,
        "wtp_output_progress_ms": endpoint,
        "wtp_pending_input_ms": endpoint,
        "partial_frame_ms": parser,
        "browser_file_bytes": app,
    }
    for key, needle in expected.items():
        require(needle in texts[key], "Current source threshold: " + key)
    return {"pending_tcp_ms": 10000, "activated_tls_ms": 10000,
        "http_activation_ms": 15000, "established_progress_ms": 30000,
        "failed_alert_ms": 1000, "wtp_output_progress_ms": 5000,
        "wtp_pending_input_ms": 5000, "partial_frame_ms": 5000,
        "browser_file_bytes": 30000}


def audit(root):
    packet_sha = digest(root / "packet.json")
    packet = validate(json.loads((root / "packet.json").read_text()))
    for name, sha in packet["stage_sha256"].items():
        require(digest(root / name) == sha, "Package 3 staged input changed")
    for name, spec in packet["remote_copy_inputs"].items():
        require(digest(root / name) == spec["sha256"], "Package 3 private input changed")
    thresholds = source_thresholds(root)
    journal = rows(root / "progress.jsonl")
    require(journal[0]["kind"] != "failure" and journal[-1]["kind"] == "finish" and
            not any(row["kind"] == "failure" for row in journal), "Progress runner completion")
    result = json.loads((root / "progress-result.json").read_text())
    require(result == journal[-1]["value"] and result["status"] == "CAPTURED_REQUIRES_AUDIT" and
            result["rf_jobs"] == 0 and result["rf_duration_ns"] == 0,
            "Progress result identity/zero-RF scope")
    require([case["id"] for case in result["cases"]] == ["2.3a", "2.3b", "2.3c"] and
            all(case["status"] == "PASS" for case in result["cases"]), "Three distinct progress cases")
    inactivity, incomplete, output = result["cases"]
    require(29.0 <= inactivity["elapsed_seconds"] <= 33.5 and inactivity["close_reason"] == 3 and
            inactivity["timeout_delta"] == 1 and inactivity["recovery_seconds"] <= 15,
            "2.3a drained inactivity interval/recovery")
    require(4.8 <= incomplete["elapsed_seconds"] <= 7.5 and incomplete["close_reason"] == 4 and
            incomplete["timeout_delta"] == 0 and incomplete["partial_bytes"] == 8 and
            incomplete["recovery_seconds"] <= 15,
            "2.3b incomplete-input interval/recovery")
    require(4.8 <= output["elapsed_seconds"] <= 25 and output["close_reason"] == 4 and
            output["timeout_delta"] == 0 and output["application_reads_after_load"] == 0 and
            output["recovery_seconds"] <= 15 and output["recovered_state"] == "loaded" and
            output["final_state"] == "empty", "2.3c output-progress interval/recovery")

    tls = [row["value"] for row in journal if row["kind"] == "tls"]
    require(tls and all(value["version"] == "TLSv1.3" and
            value["peer_sha256"] == PEER_SHA and value["alpn"] == "wtp/1" for value in tls),
            "Authenticated WTP peer journal")
    closes = {row["value"]["label"]: row["value"] for row in journal
              if row["kind"] == "target_close"}
    require(set(closes) == {"drained-inactivity", "incomplete-input"} and
            closes["drained-inactivity"]["outcome"] == inactivity["close"] and
            closes["drained-inactivity"]["elapsed_seconds"] == inactivity["elapsed_seconds"] and
            closes["drained-inactivity"]["received_bytes"] == 0 and
            closes["incomplete-input"]["outcome"] == incomplete["close"] and
            closes["incomplete-input"]["elapsed_seconds"] == incomplete["elapsed_seconds"] and
            closes["incomplete-input"]["received_bytes"] == 0,
            "Raw target close intervals")
    infos = {row["value"]["label"]: row["value"]["value"] for row in journal
             if row["kind"] == "info"}
    require(infos["drained-after"]["network_wtp_close_reason"] == 3 and
            infos["incomplete-after"]["network_wtp_close_reason"] == 4 and
            infos["output-after"]["network_wtp_close_reason"] == 4,
            "Raw target close classifications")
    recoveries = {row["value"]["label"]: row["value"] for row in journal
                  if row["kind"] == "recovery"}
    for label, case in (("drained-recovery", inactivity), ("incomplete-recovery", incomplete)):
        require(recoveries[label]["elapsed_seconds"] == case["recovery_seconds"] and
                recoveries[label]["status"]["state"] == "empty" and
                recoveries[label]["status"]["output_active"] is False,
                "Raw authenticated recovery: " + label)

    partial, = [row for row in journal if row["kind"] == "wtp_partial_tx"]
    partial_request = partial["value"]["request"]
    partial_full = frame(json.dumps(partial_request, separators=(",", ":")).encode())
    require(partial_request["type"] == "request" and partial_request["protocol"] == "WTP/1" and
            partial_request["session_id"] == packet["partial_session"] and
            partial_request["op"] == "STATUS" and partial_request["body"] == {} and
            partial["value"]["sent_bytes"] == 8 and
            bytes.fromhex(partial["value"]["sent_hex"]) == partial_full[:8] and
            partial["value"]["full_bytes"] == len(partial_full) and
            partial["value"]["full_sha256"] == hashlib.sha256(partial_full).hexdigest(),
            "2.3b eight bytes of one valid STATUS frame")
    load, = [row for row in journal if row["kind"] == "wtp_tx" and row["value"]["label"] == "no-output-load"]
    receive_window, = [row for row in journal if row["kind"] == "receive_window"]
    require(receive_window["value"]["label"] == "no-output-load" and
            receive_window["value"]["requested"] == 1024 and
            receive_window["value"]["actual"] <= 4096,
            "2.3c receive pressure applied after control setup")
    request = frame_payload(bytes.fromhex(load["value"]["hex"]))
    require(request["op"] == "LOAD" and request["session_id"] == packet["output_session"] and
            request["body"] == maximum_job(packet["job_id"], duration=128_000_000_000) and
            output["load_bytes"] == len(bytes.fromhex(load["value"]["hex"])) and
            load["value"]["application_reads_after_load"] == 0,
            "2.3c one complete maximum LOAD")
    require(not any(row["kind"] == "wtp_rx" and row["value"]["label"] == "no-output-load"
                    for row in journal), "2.3c client did not read the LOAD response")
    https = {row["value"]["label"]: row["value"] for row in journal
             if row["kind"] == "https_status"}
    https_raw = {row["value"]["label"]: row["value"] for row in journal
                 if row["kind"] == "https_raw"}
    for label, active in (("initial", 1), ("drained-before", 2), ("drained-after", 1),
                          ("incomplete-before", 2), ("incomplete-after", 1),
                          ("output-before", 2), ("output-after", 1)):
        require(label in https, "Required authenticated transport sample: " + label)
        value = http_body(bytes.fromhex(https[label]["response_hex"]))
        require(label in https_raw and https[label]["peer_sha256"] == PEER_SHA and
                https_raw[label]["peer_sha256"] == PEER_SHA and
                https_raw[label]["response_hex"] == https[label]["response_hex"] and
                value == https[label]["value"] and value["job"]["boot_id"] == BOOT and
                value["transport"]["active"] == active and value["transport"]["pending"] == 0,
                "Raw authenticated transport sample: " + label)
    require(https["drained-after"]["value"]["transport"]["timeouts"] ==
            https["drained-before"]["value"]["transport"]["timeouts"] + 1 and
            https["incomplete-after"]["value"]["transport"]["timeouts"] ==
            https["incomplete-before"]["value"]["transport"]["timeouts"] and
            https["output-after"]["value"]["transport"]["timeouts"] ==
            https["output-before"]["value"]["transport"]["timeouts"],
            "Independent timeout-counter classification")
    stall, = [row for row in journal if row["kind"] == "output_stall"]
    samples = stall["value"]["samples"]
    wait_infos = [row for row in journal if row["kind"] == "info" and
                  row["value"]["label"] == "output-wait"]
    loaded_before_close = [sample for sample in samples[:-1]
                           if sample["state"] == "loaded" and sample["reason"] != 4]
    require(stall["value"]["application_reads_after_load"] == 0 and
            stall["value"]["elapsed_seconds"] == output["elapsed_seconds"] and
            stall["value"]["load_bytes"] == output["load_bytes"] and
            stall["value"]["load_sha256"] ==
            hashlib.sha256(bytes.fromhex(load["value"]["hex"])).hexdigest() and
            len(samples) == len(wait_infos) >= 3 and
            all(a["monotonic_ns"] < b["monotonic_ns"] for a, b in zip(samples, samples[1:])) and
            all(sample["reason"] != 4 for sample in samples[:-1]) and loaded_before_close and
            samples[-1]["state"] == "loaded" and samples[-1]["reason"] == 4 and
            samples[-1]["monotonic_ns"] - loaded_before_close[0]["monotonic_ns"] >= 4_800_000_000,
            "2.3c queued output remained active before the five-second close")
    for row, sample in zip(wait_infos, samples):
        value = row["value"]["value"]
        memory = value["network"]["memory"]
        require(value["status"]["boot_id"] == BOOT and value["status"]["output_active"] is False and
                value["status"]["state"] == sample["state"] and
                value["network_wtp_close_reason"] == sample["reason"] and
                row["monotonic_ns"] <= sample["monotonic_ns"] <= row["monotonic_ns"] + 100_000_000 and
                all(pool["errors"] == 0 for pool in memory.values()) and
                value["network"]["tx_credit"]["timeouts"] == 0,
                "2.3c raw INFO sample identity and bounded network resources")
    require(any(row["value"]["value"]["status"]["state"] == "loaded" and
                row["value"]["value"]["network_wtp_close_reason"] != 4 and
                row["value"]["value"]["network"]["memory"]["tcp_pcbs"]["used"] >= 1 and
                row["value"]["value"]["network"]["memory"]["tcp_segments"]["used"] >= 1
                for row in wait_infos[:-1]) and
            wait_infos[-1]["value"]["value"]["network"]["memory"]["tcp_pcbs"]["used"] == 0,
            "2.3c response occupied transport resources before endpoint reclamation")
    claim_request, claim_response = paired_message(journal, "output-claim", "CLAIM",
        packet["output_session"])
    require(claim_request["body"] == {"owner_id": packet["owner_id"], "lease_ms": 60000} and
            claim_response["body"]["owner_id"] == packet["owner_id"],
            "2.3c exact authority claim")
    _, recovery_response = paired_message(journal, "output-recovery-status", "STATUS",
        packet["output_session"])
    recovery_status = recovery_response["body"]
    require(recovery_status["state"] == "loaded" and recovery_status["job_id"] == packet["job_id"] and
            recovery_status["owner_id"] == packet["owner_id"] and
            recovery_status["output_active"] is False, "2.3c applied LOAD and retained authority")
    abort_request, _ = paired_message(journal, "output-abort", "ABORT",
        packet["output_session"])
    release_request, _ = paired_message(journal, "output-release", "RELEASE",
        packet["output_session"])
    final_request, final_response = paired_message(journal, "output-final-status", "STATUS",
        packet["output_session"])
    require(abort_request["body"] == {"job_id": packet["job_id"]} and
            release_request["body"] == {} and final_request["body"] == {} and
            final_response["body"]["state"] == "empty" and
            final_response["body"]["owner_id"] is None and
            final_response["body"]["job_id"] is None and
            final_response["body"]["output_active"] is False,
            "2.3c raw ABORT/RELEASE/final authority")

    before_a = finished(root / "before-a.stdout", "READ_ONLY_INVENTORY")
    final_a = finished(root / "final-a.stdout", "READ_ONLY_INVENTORY")
    before_b = finished(root / "before-b.stdout", "READ_ONLY_INVENTORY")
    final_b = finished(root / "final-b.stdout", "READ_ONLY_INVENTORY")
    for value, boot in ((before_a, BOOT), (final_a, BOOT),
                        (before_b, packet["b_boot_id"]), (final_b, packet["b_boot_id"])):
        status = value["wtp"]["STATUS"]
        require(status["boot_id"] == boot and status["state"] == "empty" and
                status["output_active"] is False and status["owner_id"] is status["job_id"] is None and
                value["info"]["status"]["enabled"] is False, "Final board authority")
    require(configuration(before_a) == configuration(final_a) and
            configuration(before_b) == configuration(final_b) and
            before_a["info"]["revision"] == final_a["info"]["revision"] == SOURCE[:12] and
            before_b["info"]["revision"] == final_b["info"]["revision"],
            "Source/configuration preservation")
    counters = ("launch_epoch", "dma_irqs", "alarm_irqs", "tail_irqs")
    require(all(before_a["info"][key] == final_a["info"][key] for key in counters) and
            final_a["info"]["status"]["output_active"] is False,
            "No RF execution or output")
    require(final_a["info"]["allocator_failures"] == before_a["info"]["allocator_failures"] and
            final_a["info"]["tls_allocation_failures"] == before_a["info"]["tls_allocation_failures"],
            "No allocation failure")
    return {"status": "PACKAGE3_PROGRESS_VERIFIED", "packet_sha256": packet_sha,
        "source_revision": packet["source_revision"], "boot_id": packet["boot_id"],
        "assertions": CASES, "thresholds": thresholds, "cases": result["cases"],
        "final_a": result["final_a"], "final_b": result["final_b"],
        "configuration_preserved": True, "rf_jobs": 0, "rf_duration_ns": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.root.resolve(strict=True))
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
