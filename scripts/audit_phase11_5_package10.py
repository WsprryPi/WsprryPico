#!/usr/bin/env python3
"""Independently audit the private Phase 11.5 Package 10 evidence."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

from phase11_5_inventory import require
from phase11_5_package10 import (ADDRESS, BOOT, B_BOOT, B_DEVICE, CRITICAL_PATH_NS,
    DEVICE, EXPECTED_MAXIMUM_EVENTS, EXPECTED_PRODUCTION_EVENTS, FINAL_QUIET_SECONDS,
    HOST_BOOT, IMAGE, INTERLEAVED_QUIET_SECONDS, NORMAL_SECONDS, PEER_SHA,
    PRODUCTION_DURATION_NS, REFRESH_JOBS, RF_DURATION_NS, RF_JOBS, SOURCE,
    WSPRRYPI_SOURCE, adjustment_hash, browser_actions, digest, validate)
from phase11_5_pilot import Decoder


B_REVISION = "8921a7008183"
FAMILY_STATUS = {
    "R1": "CLOSED 5/5 with recorded applicability",
    "R2": "CLOSED 7/7 with recorded applicability",
    "R3": "CLOSED with Package 6 applicability review",
    "R4": "CLOSED with Package 7 authority/interruption evidence",
    "R5": "CLOSED with Package 8 network/storage/autonomous evidence",
    "R6": "CLOSED with Package 10 sustained mixed-operation evidence",
}


def validate_stopped_attempt(value):
    require(value.get("schema") == "phase11.5-package10-stopped-attempt-v1" and
            value.get("status") == "STOPPED_PRE_GATE_SEQUENCE_MISMATCH" and
            value.get("packet_sha256") ==
                "def689a1e498bb0ba0206198b9a6637b4496f275d498cf15011390ece9540c90" and
            value.get("acceptance_credit") == 0 and
            value.get("charged_rf_jobs") == 4 and
            value.get("charged_rf_duration_ns") == 4_000_000_000 and
            value.get("resource_windows") == value.get("normal_cycles") == 0 and
            value.get("failure") == {"type": "KeyboardInterrupt", "intentional_stop": True},
            "Stopped attempt identity/accounting")
    require(value.get("completed_jobs") == [
        {"phase": "warmup", "index": 0, "event_count": 383},
        {"phase": "warmup", "index": 1, "event_count": 383},
        {"phase": "warmup", "index": 2, "event_count": 383},
        {"phase": "warmup", "index": 3, "event_count": 512}],
        "Stopped attempt workload")
    require(value.get("restoration") == {"pico_a_empty_unowned_inactive": True,
            "pico_b_empty_unowned_inactive": True, "schedules_disabled": True,
            "reservation_released": True, "fixture_restored": True,
            "installed_service_active": True}, "Stopped attempt restoration")
    evidence = value.get("evidence_sha256", {})
    require(set(evidence) == {"packet.json", "campaign.jsonl",
            "interrupted-final-a.jsonl", "interrupted-final-b.jsonl",
            "fixture-state.json", "fixture.jsonl", "reservation.json"} and
            evidence.get("packet.json") == value["packet_sha256"] and
            all(isinstance(item, str) and len(item) == 64 and item != "0" * 64
                for item in evidence.values()), "Stopped attempt evidence")
    return value


def rows(path):
    values = [json.loads(line) for line in Path(path).read_text().splitlines()]
    require(values and [row["sequence"] for row in values] == list(range(len(values))) and
            all(values[index]["monotonic_ns"] <= values[index + 1]["monotonic_ns"]
                for index in range(len(values) - 1)), "Campaign journal sequence/time")
    return values


def values(records, kind):
    return [row for row in records if row["kind"] == kind]


def single(records, kind):
    found = values(records, kind)
    require(len(found) == 1, "Expected one " + kind)
    return found[0]


def finished(path):
    records = [json.loads(line) for line in Path(path).read_text().splitlines()]
    found = [row["value"] for row in records if row["kind"] == "finish"]
    require(len(found) == 1 and found[0]["result"] == "READ_ONLY_INVENTORY",
            "Inventory incomplete: " + str(path))
    return found[0]


def load_decoder(path):
    spec = importlib.util.spec_from_file_location("package10_tls_decoder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decode_direction(records, connection, kind):
    decoder, messages = Decoder(), []
    for row in records:
        if row["connection_id"] == connection and row["kind"] == kind:
            messages.extend(decoder.feed(row["payload"]))
    require(not decoder.buffer, "Partial production WTP frame")
    return messages


def audit_wire(path, decoder_module, cycle):
    records = decoder_module.decode(path.read_bytes())
    candidates = []
    for connection in sorted({row["connection_id"] for row in records if row["kind"] == 1}):
        written = decode_direction(records, connection, 3)
        if written:
            candidates.append((written, decode_direction(records, connection, 4)))
    require(len(candidates) == 1, "Production WTP connection count")
    written, received = candidates[0]
    requests = [message for message in written if message.get("type") == "request"]
    require(requests and len({message["request_id"] for message in requests}) == len(requests) and
            len({message["session_id"] for message in requests}) == 1,
            "Production request/session identity")
    mutations = [message for message in requests
                 if message["op"] in ("CLAIM", "LOAD", "ARM", "ABORT", "RELEASE")]
    require([message["op"] for message in mutations] == ["CLAIM", "LOAD", "ARM", "RELEASE"],
            "Production mutation order/count")
    claim, load, arm, release = mutations
    job = load["body"]
    require(claim["body"]["owner_id"] == cycle["owner_id"] and
            load["session_id"] == cycle["session_id"] and job["job_id"] == cycle["job_id"] and
            arm["body"]["job_id"] == job["job_id"] and
            int(arm["body"]["start_utc_ns"]) == cycle["target_utc_ns"] and
            job["mode"] == "fskcw" and job["profile"] == "rf-events/1" and
            int(job["total_duration_ns"]) == PRODUCTION_DURATION_NS and
            len(job["events"]) == 383 and
            all(event["rf_on"] is True and int(event["duration_ns"]) > 0
                for event in job["events"]) and
            int(job["events"][-1]["offset_ns"]) + int(job["events"][-1]["duration_ns"]) ==
                PRODUCTION_DURATION_NS, "Exact production LOAD")
    for request in mutations:
        matches = [message for message in received if message.get("type") == "response" and
                   message.get("request_id") == request["request_id"] and
                   message.get("op") == request["op"]]
        require(len(matches) == 1 and matches[0]["ok"] is True,
                "Production mutation response")
    load_response = next(message for message in received if message.get("type") == "response" and
                         message.get("request_id") == load["request_id"])
    arm_response = next(message for message in received if message.get("type") == "response" and
                        message.get("request_id") == arm["request_id"])
    require(load_response["body"]["state"] == "loaded" and
            len(load_response["body"]["adjustments"]) == EXPECTED_PRODUCTION_EVENTS and
            arm_response["body"]["state"] == "armed",
            "Production Loaded/Armed transitions")
    return {"records": len(records), "requests": len(requests),
            "session_id": cycle["session_id"], "job_id": cycle["job_id"],
            "owner_id": cycle["owner_id"], "event_count": len(job["events"]),
            "duration_ns": int(job["total_duration_ns"]),
            "adjustment_sha256": adjustment_hash(load_response["body"]["adjustments"]),
            "mutations": [message["op"] for message in mutations]}


def audit_normalizer_phase(records, packet, phase, jobs, session, owner, counts):
    completions = [row for row in values(records, "normalizer_complete")
                   if row["value"].get("phase") == phase]
    require(len(completions) == len(jobs) and
            [row["value"]["index"] for row in completions] == list(range(len(jobs))),
            phase + " lifecycle/count")
    completed = []
    for row, job, count in zip(completions, jobs, counts):
        completed.append(row["value"]["job_id"])
        terminal = row["value"]["terminal_records"]
        by_job = {record["job_id"]: record for record in terminal}
        require(row["value"]["job_id"] == job["job_id"] and
                row["value"]["event_count"] == count and
                row["value"]["states"] == ["armed", "complete", "loaded", "running"] and
                1 <= len(terminal) <= 8 and set(completed).issubset(by_job) and
                all(by_job[value]["state"] == "complete" and
                    by_job[value]["output_active"] is False for value in completed),
                phase + " lifecycle/cardinality")

    requests = [row for row in values(records, "normalizer_tx")
                if row["value"]["request"]["session_id"] == session]
    responses = [row for row in values(records, "normalizer_response")
                 if row["value"]["session_id"] == session]
    response_by_id = {row["value"]["request_id"]: row for row in responses}
    require(len(requests) == len(responses) == len(response_by_id) and
            all(request["value"]["request"]["request_id"] in response_by_id and
                response_by_id[request["value"]["request"]["request_id"]]["value"]["op"] ==
                    request["value"]["request"]["op"] and
                response_by_id[request["value"]["request"]["request_id"]]["value"]
                    ["began_monotonic_ns"] == request["value"]["began_monotonic_ns"] and
                0 <= response_by_id[request["value"]["request"]["request_id"]]["value"]
                    ["ended_monotonic_ns"] - request["value"]["began_monotonic_ns"] <=
                    packet["normalizer_request_timeout_seconds"] * 1_000_000_000 and
                response_by_id[request["value"]["request"]["request_id"]]["value"]
                    ["deadline_seconds"] == packet["normalizer_request_timeout_seconds"]
                for request in requests), phase + " response count/deadline")
    request_values = [row["value"]["request"] for row in requests]
    require(len({request["request_id"] for request in request_values}) == len(request_values),
            phase + " request identity")
    mutations = [request for request in request_values
                 if request["op"] in ("CLAIM", "LOAD", "ARM", "ABORT", "RELEASE")]
    require([request["op"] for request in mutations] ==
            [op for _ in jobs for op in ("CLAIM", "LOAD", "ARM", "RELEASE")],
            phase + " mutation order/count")
    for index, job in enumerate(jobs):
        claim, load, arm, release = mutations[index * 4:index * 4 + 4]
        require(claim["body"] == {"owner_id": owner, "lease_ms": 60000} and
                load["body"] == job and arm["body"]["job_id"] == job["job_id"] and
                int(arm["body"]["start_utc_ns"]) > 0 and
                arm["body"]["max_start_uncertainty_ns"] == "500000000" and
                release["body"] == {}, phase + " exact mutations")

    first = min(row["monotonic_ns"] for row in requests)
    last = max(row["monotonic_ns"] for row in responses)
    decoder, decoded = Decoder(), []
    for row in values(records, "normalizer_rx"):
        if first <= row["monotonic_ns"] <= last:
            decoded.extend(decoder.feed(bytes.fromhex(row["value"]["hex"])))
    require(not decoder.buffer, phase + " partial WTP frame")
    hashes = []
    loads = [request for request in mutations if request["op"] == "LOAD"]
    for completion, load, count in zip(completions, loads, counts):
        matched = [message for message in decoded
                   if message.get("type") == "response" and
                   message.get("session_id") == session and
                   message.get("request_id") == load["request_id"] and
                   message.get("op") == "LOAD"]
        require(len(matched) == 1 and matched[0]["ok"] is True and
                len(matched[0]["body"]["adjustments"]) == count,
                phase + " raw LOAD response")
        digest_value = adjustment_hash(matched[0]["body"]["adjustments"])
        require(completion["value"]["adjustment_sha256"] == digest_value,
                phase + " adjustment hash binding")
        hashes.append(digest_value)
    return {"completions": completions, "jobs": completed, "hashes": hashes}


def configuration(value):
    info = value["info"]
    return {"revision": info["revision"], "system_clock_hz": info["system_clock_hz"],
            "engine": info["status"]["engine"], "render_in_ram": info["rf_render_in_ram"],
            "configured": info["status"]["configured"],
            "enabled": info["status"]["enabled"],
            "suspended": info["status"]["suspended"],
            "base_frequency": info["status"].get("schedule_base_frequency_nhz"),
            "station": info["status"]["station"], "schedules": info["status"]["schedules"]}


def max_gap(starts):
    return max((later - earlier for earlier, later in zip(starts, starts[1:])), default=0)


def audit_resource_info(info):
    require(info["device_id"] == DEVICE and info["revision"] == SOURCE[:12] and
            info["status"]["boot_id"] == BOOT and info["system_clock_hz"] == 138000000 and
            info["status"]["engine"] == "pio-dma-gp2" and info["rf_render_in_ram"] is True,
            "Observed identity/configuration")
    require(info["core0_stack_guard_valid"] == info["core1_stack_guard_valid"] == 1 and
            info["core0_stack_fault_status"] == info["core1_stack_fault_status"] == 0 and
            info["core0_stack_used_bytes"] <= 12288 and
            info["core1_stack_used_bytes"] <= 12288, "Observed stack reserve")
    require(int(info["allocator_failures"]) == 0 and info["tls_allocation_failures"] == 0 and
            info["heap_capacity_bytes"] - int(info["allocator_peak_bytes"]) >= 32768,
            "Observed heap reserve/failure")
    require(info["fault_stage"] == info["fault_hash"] == info["fault_pc"] ==
            info["fault_status"] == 0 and info["dma_errors"] == 0 and
            info["refill_irq_unpaired"] == 0 and info["refill_invalid_reserves"] == 0 and
            not info["engine_diagnostic"], "Observed fault/DMA/engine gate")
    require(int(info["rf_max_service_gap_ns"]) <= CRITICAL_PATH_NS and
            int(info["max_refill_irq_to_ready_ns"]) <= CRITICAL_PATH_NS,
            "Observed RF timing gate")


def audit(root, expected_packet_sha, decoder_path, fixture_root,
          reservation_path=Path("/home/pi/phase11-5-shared-rf-reservation.json"),
          ap_fixture_root=None, ap_capture_log_name="capture-ap.log",
          ap_capture_pcap_name="capture-ap.pcap", ap_capture_json=False):
    ap_fixture_root = (Path(fixture_root) if ap_fixture_root is None else
                       Path(ap_fixture_root))
    require(digest(root / "packet.json") == expected_packet_sha, "Package 10 packet hash")
    packet = validate(json.loads((root / "packet.json").read_text()))
    require(packet["source_impact"] == {"deployed_source_revision": SOURCE,
            "repository_baseline_revision": "e22c86c83ceb161080c218748baf5d3eaa892652",
            "runtime_source_changes": 0,
            "decision": "measurement-only replay-history normalization"},
            "Package 10 source impact")
    records = rows(root / "campaign.jsonl")
    require(not values(records, "failure") and not values(records, "worker_failure") and
            not values(records, "observer_failure"), "Campaign failure record")
    paused = single(records, "installed_service_paused")
    headroom = values(records, "memory_headroom")
    reservation_acquired = single(records, "reservation_acquired")
    require(paused["value"] == {"was_active": True,
            "before_memory_readiness": True} and headroom and len(headroom) <= 25 and
            paused["monotonic_ns"] < headroom[0]["monotonic_ns"] and
            headroom[-1]["monotonic_ns"] < reservation_acquired["monotonic_ns"] and
            all(row["value"]["required_bytes"] == 165000 and
                isinstance(row["value"]["available_bytes"], int) and
                row["value"]["allocator_failures"] == "0"
                for row in headroom) and
            headroom[-1]["value"]["usable"] is True and
            headroom[-1]["value"]["available_bytes"] >= 165000,
            "Console-only memory readiness before reservation")
    captured = json.loads((root / "campaign-result.json").read_text())
    require(captured["status"] == "CAPTURED_REQUIRES_AUDIT" and
            captured["packet_sha256"] == expected_packet_sha and
            captured["normal_seconds"] == 1800 and captured["rf_jobs"] == RF_JOBS and
            captured["rf_duration_ns"] == RF_DURATION_NS and len(captured["cycles"]) == 3 and
            len(captured["windows"]) == 5, "Campaign result/counts")
    warmup = audit_normalizer_phase(records, packet, "warmup", packet["warmup_jobs"],
        packet["warmup_session"], packet["warmup_owner"],
        [EXPECTED_PRODUCTION_EVENTS] * 3 + [EXPECTED_MAXIMUM_EVENTS] * 5)
    refresh = audit_normalizer_phase(records, packet, "refresh", packet["refresh_jobs"],
        packet["refresh_session"], packet["refresh_owner"],
        [EXPECTED_MAXIMUM_EVENTS] * REFRESH_JOBS)
    production_hashes = warmup["hashes"][:3]
    maximum_hashes = warmup["hashes"][3:] + refresh["hashes"]
    require(len(set(production_hashes)) == len(set(maximum_hashes)) == 1 and
            production_hashes[0] != maximum_hashes[0] and
            captured["production_adjustment_sha256"] == production_hashes[0] and
            captured["maximum_adjustment_sha256"] == maximum_hashes[0] and
            captured["warmup_jobs"] == warmup["jobs"] and
            captured["refresh_jobs"] == refresh["jobs"],
            "Matched adjustment classes")
    require({record["job_id"] for record in
                warmup["completions"][-1]["value"]["terminal_records"]} ==
            set(warmup["jobs"]), "Matched baseline terminal set")

    begins = values(records, "normal_begin")
    finishes = values(records, "normal_finish")
    require(len(begins) == len(finishes) == 3, "Normal interval count")
    actions = values(records, "browser_action_start")
    action_finishes = values(records, "browser_action_finish")
    gets = values(records, "browser_get")
    require(len(actions) == len(action_finishes) == 48 and len(gets) == 84,
            "Browser action/GET count")
    expected_actions = browser_actions()
    for cycle in range(1, 4):
        cycle_actions = [row for row in actions if row["value"]["cycle"] == cycle]
        cycle_finishes = [row for row in action_finishes if row["value"]["cycle"] == cycle]
        cycle_gets = [row for row in gets if row["value"]["cycle"] == cycle]
        # browser_actions() intentionally returns JSON-shaped lists.  Preserve
        # that shape here so an exact, valid captured schedule is not rejected
        # solely because the auditor constructed Python tuples.
        require([[row["value"]["offset_seconds"], row["value"]["action"],
                  row["value"]["paths"]] for row in cycle_actions] == expected_actions and
                len(cycle_gets) == 28 and
                all(0 <= row["monotonic_ns"] - row["value"]["scheduled_monotonic_ns"] <=
                    15_000_000_000 for row in cycle_actions) and
                all(row["value"]["ended_monotonic_ns"] - row["value"]["began_monotonic_ns"] <=
                    15_000_000_000 for row in cycle_gets) and
                all(row["value"]["status"] == 200 and
                    0 < row["value"]["body_bytes"] <= 131072 and
                    isinstance(row["value"]["body_sha256"], str) and
                    len(row["value"]["body_sha256"]) == 64 and
                    all(character in "0123456789abcdef"
                        for character in row["value"]["body_sha256"]) and
                    row["value"]["content_type"] ==
                        ("text/html; charset=utf-8" if row["value"]["path"] == "/"
                         else "application/json")
                    for row in cycle_gets),
                "Browser schedule/deadlines")
        for start, end in zip(cycle_actions, cycle_finishes):
            require(start["value"]["index"] == end["value"]["index"] and
                    end["monotonic_ns"] - start["monotonic_ns"] <= 60_000_000_000,
                    "Browser whole-action deadline")
            action_gets = [row["value"]["path"] for row in cycle_gets
                           if start["monotonic_ns"] < row["monotonic_ns"] < end["monotonic_ns"]]
            require(action_gets == start["value"]["paths"], "Browser action resources")
        reloads = [row for row in cycle_actions if row["value"]["offset_seconds"] == 150]
        require(len(reloads) == 1, "One scheduled long-job reload")
        running = [row for row in values(records, "usb_status")
                   if row["value"]["cycle"] == cycle and
                   row["value"]["value"]["state"] == "running" and
                   row["value"]["value"]["output_active"] is True and
                   abs(row["monotonic_ns"] - reloads[0]["monotonic_ns"]) <= 6_000_000_000]
        require(running, "Reload lacked independent Running evidence")
        begin = begins[cycle - 1]
        finish = finishes[cycle - 1]
        report = finish["value"]["last_report"]
        require(finish["monotonic_ns"] - begin["monotonic_ns"] >= NORMAL_SECONDS * 1_000_000_000 and
                finish["value"]["cycle"] == cycle and
                {"armed", "running"}.issubset(finish["value"]["states"]) and
                report["outcome"] == "complete" and report["arm_handed_off"] is True and
                report["job_id"] == finish["value"]["job_id"] and
                report["job"]["state"] == "complete" and
                report["job"]["output_active"] is False and
                report["job"]["device_output_active"] is False,
                "Normal interval duration/lifecycle")
        start = single([row for row in values(records, "production_start")
                        if row["value"]["cycle"] == cycle], "production_start")
        require(60_000_000_000 <= start["monotonic_ns"] - begin["monotonic_ns"] <=
                70_000_000_000 and start["value"]["target_utc_ns"] ==
                begin["value"]["target_utc_ns"] and
                digest(root / f"production-{cycle}.ini") == start["value"]["ini_sha256"] ==
                captured["cycles"][cycle - 1]["ini_sha256"] and
                digest(root / f"production-{cycle}-tls.bin") ==
                captured["cycles"][cycle - 1]["tls_sha256"],
                "Production launch/artifact binding")

    console = values(records, "console_info")
    host = values(records, "host_health")
    require(len(console) >= 3436 and max_gap([row["value"]["began_monotonic_ns"]
            for row in console]) <= 2_000_000_000 and
            max(row["value"]["ended_monotonic_ns"] - row["value"]["began_monotonic_ns"]
                for row in console) <= 5_000_000_000, "Console coverage/cost")
    for row in console:
        audit_resource_info(row["value"]["value"])
    require(len(host) >= 687 and max_gap([row["value"]["began_monotonic_ns"]
            for row in host]) <= 6_000_000_000 and
            all(row["value"]["installed_service"] == "inactive" and
                row["value"]["service_returncode"] == 3 for row in host),
            "Host-health coverage")
    for cycle in range(1, 4):
        status = [row for row in values(records, "usb_status") if row["value"]["cycle"] == cycle]
        events = [row for row in values(records, "usb_event")
                  if row["value"]["cycle"] == cycle]
        expected_session = packet[f"usb_observer_session_{cycle}"]
        job_events = [row["value"]["value"] for row in events
                      if row["value"]["value"]["event"] == "JOB_STATE"]
        finish = finishes[cycle - 1]["value"]
        usb_states = {row["value"]["value"]["state"] for row in status}
        usb_jobs = {row["value"]["value"]["job_id"] for row in status
                    if row["value"]["value"].get("job_id")}
        event_states = {row["body"]["state"] for row in job_events}
        event_jobs = {row["body"]["job_id"] for row in job_events
                      if row["body"].get("job_id")}
        raw_event_ids = [row["value"]["value"]["event_id"] for row in events]
        event_ids = [int(value) for value in raw_event_ids]
        terminal_status = [row["value"]["value"] for row in status if any(
            record["job_id"] == finish["job_id"] and record["state"] == "complete" and
            record["output_active"] is False
            for record in row["value"]["value"]["terminal_records"])]
        require(len(status) >= 118 and max_gap([row["value"]["began_monotonic_ns"]
                for row in status]) <= 6_000_000_000 and
                max(row["value"]["ended_monotonic_ns"] - row["value"]["began_monotonic_ns"]
                    for row in status) <= 5_000_000_000 and
                all(row["value"]["value"]["boot_id"] == BOOT for row in status) and
                {"armed", "running"}.issubset(usb_states) and
                usb_states <= {"empty", "loaded", "armed", "running", "complete"} and
                usb_jobs == {finish["job_id"]} and events and
                all(row["value"]["value"]["boot_id"] == BOOT and
                    row["value"]["value"].get("protocol") == "WTP/1" and
                    row["value"]["value"].get("session_id") == expected_session
                    for row in events) and
                all(row["value"]["value"]["event"] in {"JOB_STATE", "OWNER_RELEASED"}
                    for row in events) and
                all(isinstance(value, str) and value.isdigit() and str(int(value)) == value
                    for value in raw_event_ids) and
                event_ids == list(range(event_ids[0], event_ids[0] + len(event_ids))) and
                event_states == {"loaded", "armed", "running", "complete", "empty"} and
                event_jobs == {finish["job_id"]} and terminal_status and
                all(type(row["body"].get("output_active")) is bool and
                    row["body"]["output_active"] is (row["body"]["state"] == "running") and
                    ((row["body"]["state"] == "empty" and row["body"].get("job_id") is None) or
                     (row["body"]["state"] != "empty" and
                      row["body"].get("job_id") == finish["job_id"]))
                    for row in job_events) and
                terminal_status[-1]["state"] == "empty" and
                terminal_status[-1]["owner_id"] is None and
                terminal_status[-1]["output_active"] is False and
                all(record["state"] == "complete" and record["output_active"] is False
                    for record in terminal_status[-1]["terminal_records"]),
                "USB STATUS/event coverage/lifecycle")
        expected_cycle_terminals = (
            {job["job_id"] for job in packet["warmup_jobs"][cycle:]} |
            {item["value"]["job_id"] for item in finishes[:cycle]})
        require({record["job_id"] for record in
                    terminal_status[-1]["terminal_records"]} == expected_cycle_terminals and
                len(expected_cycle_terminals) == 8,
                "Post-N equivalent terminal-history cardinality")
        health = [row for row in values(records, "production_process_health")
                  if row["value"]["cycle"] == cycle]
        require(len(health) >= 118 and max_gap([row["value"]["began_monotonic_ns"]
                for row in health]) <= 6_000_000_000 and
                {row["value"]["state"] for row in health} == {"not_started", "running"} and
                all((row["value"]["pid"] is None and row["value"]["returncode"] is None)
                    if row["value"]["state"] == "not_started" else
                    (isinstance(row["value"]["pid"], int) and
                     row["value"]["returncode"] is None) for row in health),
                "Production process-health coverage")
        production = [row for row in values(records, "production_host_status")
                      if row["value"]["cycle"] == cycle]
        hosts = [row["value"]["value"]["host"] for row in production]
        remotes = [host.get("remote") or {} for host in hosts]
        host_states = {remote.get("state") for remote in remotes if remote.get("state")}
        host_owners = {remote.get("owner_id") for remote in remotes
                       if remote.get("owner_id")}
        host_jobs = {remote.get("job_id") for remote in remotes if remote.get("job_id")}
        host_sessions = {host.get("session_id") for host in hosts if host.get("session_id")}
        reports = [host.get("last_report") for host in hosts if host.get("last_report")]
        matching_reports = [report for report in reports
            if report.get("outcome") == "complete" and
               report.get("job_id") == finish["job_id"] and
               report.get("arm_handed_off") is True and
               report.get("job", {}).get("state") == "complete" and
               report["job"].get("output_active") is False and
               report["job"].get("device_output_active") is False]
        require(len(production) >= 100 and
                max_gap([row["value"]["began_monotonic_ns"] for row in production]) <=
                    6_000_000_000 and
                max(row["monotonic_ns"] - row["value"]["began_monotonic_ns"]
                    for row in production) <= 3_000_000_000 and
                all(row["value"]["value"]["host"]["identity"]["boot_id"] == BOOT and
                    row["value"]["value"]["host"]["identity"]["device_id"] == DEVICE and
                    row["value"]["value"]["host"]["recovery_required"] is False and
                    row["value"]["value"]["host"]["safety_fault"] is False and
                    (row["value"]["value"]["host"].get("last_report") or {})
                        .get("outcome") != "failed"
                    for row in production) and
                {"armed", "running"}.issubset(host_states) and
                set(finish["states"]) == host_states and
                host_owners == {finish["owner_id"]} and
                host_jobs == {finish["job_id"]} and
                host_sessions == {finish["session_id"]} and matching_reports,
                "Production host STATUS coverage/identity/health")

    quiet_begins = values(records, "quiet_begin")
    windows = values(records, "resource_window")
    require([row["value"]["seconds"] for row in quiet_begins] ==
            [360, 306, 306, 306, 360] and len(windows) == 5, "Quiet schedule")
    forbidden = {"normalizer_tx", "normalizer_rx", "browser_get", "browser_action_start",
                 "production_host_status", "production_process_health", "usb_status"}
    for begin, end in zip(quiet_begins, windows):
        quiet_console = [row for row in console
                         if begin["monotonic_ns"] < row["monotonic_ns"] <
                         end["monotonic_ns"]]
        # The resource-window payload records the actual measurement bounds.
        # Journal emission occurs a few milliseconds after those bounds, so
        # comparing event timestamps can reject a full interval spuriously.
        require(end["value"]["seconds"] == begin["value"]["seconds"] and
                end["value"]["ended_monotonic_ns"] -
                    end["value"]["began_monotonic_ns"] >=
                    begin["value"]["seconds"] * 1_000_000_000 and
                end["value"]["began_monotonic_ns"] <= begin["monotonic_ns"] and
                end["value"]["ended_monotonic_ns"] <= end["monotonic_ns"] and
                not [row for row in records if begin["monotonic_ns"] < row["monotonic_ns"] <
                     end["monotonic_ns"] and row["kind"] in forbidden] and
                quiet_console and all(
                    row["value"]["value"]["status"].get("owner_id") is None and
                    row["value"]["value"]["status"]["output_active"] is False
                    for row in quiet_console),
                "Application-quiet interval/authority")
    baseline = windows[0]["value"]["heap_allocated_bytes"]
    posts = [row["value"]["heap_allocated_bytes"] for row in windows[1:4]]
    final_live = windows[4]["value"]["heap_allocated_bytes"]
    require(all(abs(value - baseline) <= 1024 for value in posts + [final_live]) and
            max(posts) - min(posts) <= 1024 and not (posts[0] < posts[1] < posts[2]),
            "Matched resource return/no growth")
    require(all(row["value"]["heap_capacity_bytes"] - row["value"]["allocator_peak_bytes"] >=
                32768 and row["value"]["core0_stack_used_bytes"] <= 12288 and
                row["value"]["core1_stack_used_bytes"] <= 12288 and
                not row["value"]["output_active"] for row in windows), "Window resource gates")

    decoder = load_decoder(decoder_path)
    wire = [audit_wire(root / f"production-{cycle}-tls.bin", decoder,
                       captured["cycles"][cycle - 1]) for cycle in range(1, 4)]
    require({item["adjustment_sha256"] for item in wire} == {production_hashes[0]},
            "Production adjustment class equivalence")
    expected_terminal_jobs = ({item["job_id"] for item in wire} | set(refresh["jobs"]))
    equivalence = single(records, "terminal_equivalence")
    require(equivalence["value"] == {"stage": "before-final-q",
            "production_class_records": 3, "maximum_class_records": 5,
            "terminal_jobs": sorted(expected_terminal_jobs),
            "production_adjustment_sha256": production_hashes[0],
            "maximum_adjustment_sha256": maximum_hashes[0]} and
            equivalence["monotonic_ns"] < quiet_begins[-1]["monotonic_ns"] and
            captured["final_terminal_jobs"] == sorted(expected_terminal_jobs),
            "Final-Q terminal-history equivalence")

    before_a, before_b = finished(root / "before-a.jsonl"), finished(root / "before-b.jsonl")
    final_a, final_b = finished(root / "final-a.jsonl"), finished(root / "final-b.jsonl")
    require(before_a["info"]["status"]["boot_id"] == final_a["info"]["status"]["boot_id"] == BOOT and
            before_b["info"]["status"]["boot_id"] == final_b["info"]["status"]["boot_id"] == B_BOOT and
            before_b["info"]["device_id"] == final_b["info"]["device_id"] == B_DEVICE and
            before_b["info"]["revision"] == final_b["info"]["revision"] == B_REVISION and
            configuration(before_a) == configuration(final_a) and
            configuration(before_b) == configuration(final_b), "Identity/configuration preservation")
    final_status = final_a["wtp"]["STATUS"]
    require(final_status["owner_id"] is None and final_status["output_active"] is False and
            len(final_status["terminal_records"]) == 8 and
            {record["job_id"] for record in final_status["terminal_records"]} ==
                expected_terminal_jobs and
            all(record["state"] == "complete" and not record["output_active"]
                for record in final_status["terminal_records"]),
            "Final equivalent authority/terminal state")
    info = final_a["info"]
    audit_resource_info(info)
    require(info["allocator_failures"] == "0" and info["tls_allocation_failures"] == 0 and
            info["heap_capacity_bytes"] - int(info["allocator_peak_bytes"]) >= 32768 and
            info["core0_stack_guard_valid"] == info["core1_stack_guard_valid"] == 1 and
            info["core0_stack_used_bytes"] <= 12288 and info["core1_stack_used_bytes"] <= 12288 and
            info["core0_stack_fault_status"] == info["core1_stack_fault_status"] == 0 and
            int(info["rf_max_service_gap_ns"]) <= CRITICAL_PATH_NS and
            int(info["max_refill_irq_to_ready_ns"]) <= CRITICAL_PATH_NS and
            info["refill_full_predecessor"]["measured"] is True and
            info["refill_short_predecessor"]["measured"] is True and
            info["refill_full_predecessor"]["remaining_words"] * 4 >=
                info["refill_full_predecessor"]["total_words"] and
            info["refill_short_predecessor"]["remaining_words"] * 4 >=
                info["refill_short_predecessor"]["total_words"] and
            info["dma_errors"] == info["refill_irq_unpaired"] ==
                info["refill_invalid_reserves"] == 0 and not info["engine_diagnostic"] and
            info["fault_stage"] == info["fault_hash"] == info["fault_pc"] ==
                info["fault_status"] == 0 and info["tail_irqs"] >= RF_JOBS and
            int(info["launch_epoch"]) >= int(before_a["info"]["launch_epoch"]) + RF_JOBS,
            "Final resource/timing/fault gates")

    reservation = json.loads(Path(reservation_path).read_text())
    require(reservation["state"] == "RELEASED" and
            reservation["packet_sha256"] == expected_packet_sha and
            reservation["host_boot"] == HOST_BOOT, "Reservation release")
    fixture = json.loads((fixture_root / "fixture-state.json").read_text())
    require(fixture.get("restored") is True and fixture["host_boot"] == HOST_BOOT,
            "Fixture restoration")
    fixture_rows = [json.loads(line) for line in
                    (fixture_root / "fixture.jsonl").read_text().splitlines()]
    require(fixture_rows and all(fixture_rows[index]["monotonic_ns"] <=
            fixture_rows[index + 1]["monotonic_ns"]
            for index in range(len(fixture_rows) - 1)), "Fixture log order")
    cleanup = single(fixture_rows, "cleanup")
    restored_host = single(fixture_rows, "host_restored")
    require(cleanup["value"]["failures"] == [] and
            isinstance(restored_host["value"].get("installed_pid"), str) and
            restored_host["value"]["installed_pid"].isdigit() and
            int(restored_host["value"]["installed_pid"]) > 0,
            "Fixture cleanup and installed service restoration")
    ap_capture_text = (ap_fixture_root / ap_capture_log_name).read_text()
    if ap_capture_json:
        ap_capture = json.loads(ap_capture_text)
        require(ap_capture.get("captured", 0) > 0 and
                ap_capture.get("kernel_packets") == ap_capture["captured"] and
                ap_capture.get("kernel_drops") == 0,
                "Capture completeness")
    else:
        require(re.search(r"[1-9][0-9]* packets captured", ap_capture_text) and
                "0 packets dropped by kernel" in ap_capture_text,
                "Capture completeness")
    client_capture_text = (Path(fixture_root) / "capture-client.log").read_text()
    require(re.search(r"[1-9][0-9]* packets captured", client_capture_text) and
            "0 packets dropped by kernel" in client_capture_text,
            "Capture completeness")
    require((ap_fixture_root / ap_capture_pcap_name).stat().st_size > 24 and
            (Path(fixture_root) / "capture-client.pcap").stat().st_size > 24,
            "Fixture capture payloads")
    campaign_capture = (root / "campaign-capture.log").read_text()
    require(re.search(r"[1-9][0-9]* packets captured", campaign_capture) and
            "0 packets dropped by kernel" in campaign_capture and
            (root / "campaign.pcap").stat().st_size > 24, "Campaign capture completeness")

    evidence_names = ["packet.json", "campaign.jsonl", "campaign-result.json",
        "before-a.jsonl", "before-b.jsonl", "final-a.jsonl", "final-b.jsonl",
        "production-1.ini", "production-2.ini", "production-3.ini",
        "production-1.log", "production-2.log", "production-3.log",
        "production-1-tls.bin", "production-2-tls.bin", "production-3-tls.bin"]
    evidence = {name: digest(root / name) for name in evidence_names}
    evidence["fixture/fixture-state.json"] = digest(fixture_root / "fixture-state.json")
    evidence["fixture/capture-ap.pcap"] = digest(
        ap_fixture_root / ap_capture_pcap_name)
    evidence["fixture/capture-client.pcap"] = digest(fixture_root / "capture-client.pcap")
    evidence["fixture/fixture.jsonl"] = digest(fixture_root / "fixture.jsonl")
    evidence["campaign.pcap"] = digest(root / "campaign.pcap")
    return {"schema": "phase11.5-package10-raw-audit-v1", "status": "PASS",
        "packet_sha256": expected_packet_sha, "candidate": {"source_revision": SOURCE,
            "image_sha256": IMAGE, "boot_id": BOOT, "device_id": DEVICE,
            "system_clock_hz": 138000000, "engine": "pio-dma-gp2", "renderer": "ram"},
        "normal_load_seconds": 1800, "rf_jobs": RF_JOBS,
        "rf_duration_ns": RF_DURATION_NS, "warmup_jobs": 8, "refresh_jobs": 5,
        "production_jobs": wire, "browser_actions": len(actions),
        "browser_gets": len(gets), "console_samples": len(console),
        "host_samples": len(host), "resource_windows": [row["value"] for row in windows],
        "matched_baseline_bytes": baseline, "post_n_bytes": posts,
        "final_q_bytes": final_live, "maximum_post_span_bytes": max(posts) - min(posts),
        "monotonic_retained_growth": False, "final_terminal_records": 8,
        "production_adjustment_sha256": production_hashes[0],
        "maximum_adjustment_sha256": maximum_hashes[0],
        "final_terminal_jobs": sorted(expected_terminal_jobs),
        "final_metrics": captured["final_metrics"], "reservation_released": True,
        "fixture_restored": True, "installed_service_active": True, "capture_drops": 0,
        "source_impact": {"deployed_source_revision": SOURCE,
            "later_runtime_source_changes": 0,
            "wsprrypi_source_revision": WSPRRYPI_SOURCE},
        "auditor_sha256": digest(Path(__file__)),
        "decoder_sha256": digest(decoder_path),
        "evidence_sha256": evidence}


def validate_published_result(value):
    """Validate the credential-free Package 10 and Phase 11.5 closure record."""
    require(value.get("schema") == "phase11.5-package10-result-v1" and
            value.get("status") == "PACKAGE10_COMPLETE_R6_CLOSED" and
            value.get("phase11_5_status") == "CLOSED_6_OF_6_FAMILIES" and
            value.get("family_status") == FAMILY_STATUS,
            "Package 10 closure status")
    require(value.get("accepted_configuration") == {
        "board": "Pico A 0BF4B4AEC9FFB344",
        "device_id": DEVICE,
        "source_revision": SOURCE,
        "image_sha256": IMAGE,
        "boot_id": BOOT,
        "system_clock_hz": 138000000,
        "pio_divider": 1,
        "engine": "pio-dma-gp2",
        "renderer": "RAM",
        "rf_pin": "GP2",
        "schedule_base_frequency_nhz": "135500000000000",
        "network_listener": "configured",
    }, "Accepted Phase 11.5 configuration")
    campaign = value.get("campaign", {})
    require(isinstance(campaign.get("packet_sha256"), str) and
            len(campaign["packet_sha256"]) == 64 and campaign["packet_sha256"] != "0" * 64 and
            campaign.get("normal_load_seconds") == 1800 and
            campaign.get("rf_jobs") == RF_JOBS and
            campaign.get("planned_rf_duration_ns") == RF_DURATION_NS and
            campaign.get("warmup_jobs") == 8 and
            campaign.get("refresh_jobs") == REFRESH_JOBS and
            campaign.get("production_jobs") == 3 and
            campaign.get("browser_actions") == 48 and
            campaign.get("browser_gets") == 84 and
            campaign.get("resource_windows") == 5 and
            campaign.get("final_terminal_records") == 8 and
            isinstance(campaign.get("matched_baseline_bytes"), int) and
            isinstance(campaign.get("post_n_bytes"), list) and
            len(campaign["post_n_bytes"]) == 3 and
            isinstance(campaign.get("final_q_bytes"), int) and
            0 <= campaign.get("maximum_post_span_bytes", -1) <= 1024 and
            campaign.get("monotonic_retained_growth") is False and
            campaign.get("terminal_class_cardinality") == {"production": 3, "maximum": 5} and
            isinstance(campaign.get("production_adjustment_sha256"), str) and
            isinstance(campaign.get("maximum_adjustment_sha256"), str) and
            campaign["production_adjustment_sha256"] !=
                campaign["maximum_adjustment_sha256"],
            "Package 10 campaign summary")
    baseline = campaign["matched_baseline_bytes"]
    require(all(isinstance(item, int) and abs(item - baseline) <= 1024
                for item in campaign["post_n_bytes"] + [campaign["final_q_bytes"]]) and
            max(campaign["post_n_bytes"]) - min(campaign["post_n_bytes"]) ==
                campaign["maximum_post_span_bytes"] and
            not (campaign["post_n_bytes"][0] < campaign["post_n_bytes"][1] <
                 campaign["post_n_bytes"][2]), "Published matched resource return")
    require(value.get("diagnosis") == {
            "package9_failure_preserved": True,
            "cause": "inequivalent retained WTP replay-history classes",
            "firmware_memory_leak_found": False,
            "resource_limit_bytes": 1024,
            "protocol_retention_preserved": True}, "Package 10 diagnosis")
    impact = value.get("source_impact", {})
    require(impact == {"deployed_candidate": SOURCE,
            "repository_baseline_revision": "e22c86c83ceb161080c218748baf5d3eaa892652",
            "runtime_source_changes": 0,
            "decision": "measurement-only replay-history normalization",
            "wsprrypi_source_revision": WSPRRYPI_SOURCE},
            "Package 10 source-impact decision")
    require(value.get("budget") == {"attempts": 2, "authorized_rf_duration_ns":
            480_000_000_000, "charged_rf_jobs": 20,
            "charged_rf_duration_ns": 360_800_000_000,
            "unused_authorized_rf_duration_ns": 119_200_000_000,
            "authorized_max_flashes": 2, "authorized_max_bootsel": 2,
            "flashes": 0, "bootsel": 0, "configuration_writes": 0,
            "controlled_reboots": 0, "wifi_cycles": 0, "allocation_probes": 0},
            "Package 10 budget")
    require(value.get("restoration") == {"pico_a_inactive": True,
            "pico_a_empty_unowned": True,
            "pico_b_unchanged_inactive": True,
            "reservation_released": True,
            "host_fixture_restored": True,
            "installed_service_active": True,
            "capture_drops": 0}, "Package 10 restoration")
    evidence = value.get("evidence_sha256", {})
    required = {"packet", "raw_audit", "adversarial", "stopped_attempt"}
    require(set(evidence) == required and all(isinstance(item, str) and len(item) == 64 and
            item != "0" * 64 and
            all(character in "0123456789abcdef" for character in item)
            for item in evidence.values()) and evidence["packet"] == campaign["packet_sha256"],
            "Package 10 evidence hashes")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--decoder", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--reservation", type=Path,
                        default=Path("/home/pi/phase11-5-shared-rf-reservation.json"))
    args = parser.parse_args()
    print(json.dumps(audit(args.root.resolve(strict=True), args.packet_sha256,
        args.decoder.resolve(strict=True), args.fixture_root.resolve(strict=True),
        args.reservation.resolve(strict=True)), indent=2))


if __name__ == "__main__":
    main()
