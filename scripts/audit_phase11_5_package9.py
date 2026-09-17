#!/usr/bin/env python3
"""Independently audit the private Phase 11.5 Package 9 evidence."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

from phase11_5_inventory import require
from phase11_5_package9 import (ADDRESS, BOOT, B_BOOT, B_DEVICE, CRITICAL_PATH_NS,
    DEVICE, FINAL_QUIET_SECONDS, HOST_BOOT, IMAGE, INTERLEAVED_QUIET_SECONDS,
    NORMAL_SECONDS, PEER_SHA, PRODUCTION_DURATION_NS, RF_DURATION_NS, SOURCE,
    WSPRRYPI_SOURCE, browser_actions, digest, validate)
from phase11_5_pilot import Decoder


PRIOR_SOURCE = "7c5296471250cc06416c79a73c9627aed0eb3624"
B_REVISION = "8921a7008183"
RUNTIME_CHANGES = [
    "src/network/api.cpp",
    "src/network/http.hpp",
    "src/network/pico/server.cpp",
    "src/network/pico/server.hpp",
    "src/standalone/pico/main.cpp",
    "src/usb/reply_priority.hpp",
]
SOURCE_DIFF_SHA256 = "0cccf86e9a22643691fd10129090b3c28ca914fda683d11ca00be8c29149dffe"
FAMILY_STATUS = {
    "R1": "CLOSED 5/5 with recorded applicability",
    "R2": "CLOSED 7/7 with recorded applicability",
    "R3": "CLOSED with Package 6 applicability review",
    "R4": "CLOSED with Package 7 authority/interruption evidence",
    "R5": "CLOSED with Package 8 network/storage/autonomous evidence",
    "R6": "CLOSED with Package 9 sustained mixed-operation evidence",
}


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
    spec = importlib.util.spec_from_file_location("package9_tls_decoder", path)
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
            arm_response["body"]["state"] == "armed",
            "Production Loaded/Armed transitions")
    return {"records": len(records), "requests": len(requests),
            "session_id": cycle["session_id"], "job_id": cycle["job_id"],
            "owner_id": cycle["owner_id"], "event_count": len(job["events"]),
            "duration_ns": int(job["total_duration_ns"]),
            "mutations": [message["op"] for message in mutations]}


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
          reservation_path=Path("/home/pi/phase11-5-shared-rf-reservation.json")):
    require(digest(root / "packet.json") == expected_packet_sha, "Package 9 packet hash")
    packet = validate(json.loads((root / "packet.json").read_text()))
    require(packet["source_impact"] == {"deployed_source_revision": SOURCE,
            "current_repository_revision": SOURCE, "later_runtime_source_changes": 0},
            "Package 9 source impact")
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
            captured["normal_seconds"] == 1800 and captured["rf_jobs"] == 11 and
            captured["rf_duration_ns"] == RF_DURATION_NS and len(captured["cycles"]) == 3 and
            len(captured["windows"]) == 5, "Campaign result/counts")

    normalizer = values(records, "normalizer_complete")
    completed = []
    require(len(normalizer) == 8 and
            [row["value"]["index"] for row in normalizer] == list(range(8)),
            "Normalizer lifecycle/count")
    for row in normalizer:
        completed.append(row["value"]["job_id"])
        terminal = row["value"]["terminal_records"]
        by_job = {record["job_id"]: record for record in terminal}
        require(row["value"]["states"] == ["armed", "complete", "loaded", "running"] and
                1 <= len(terminal) <= 8 and set(completed).issubset(by_job) and
                all(by_job[job]["state"] == "complete" and
                    by_job[job]["output_active"] is False for job in completed),
                "Normalizer lifecycle/cardinality")
    normalizer_requests = [row for row in values(records, "normalizer_tx")
        if row["value"]["request"]["session_id"] == packet["normalizer_session"]]
    normalizer_responses = [row for row in values(records, "normalizer_response")
        if row["value"]["session_id"] == packet["normalizer_session"]]
    response_by_id = {row["value"]["request_id"]: row for row in normalizer_responses}
    require(len(normalizer_requests) == len(normalizer_responses) == len(response_by_id) and
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
                for request in normalizer_requests),
            "Normalizer response count/deadline")
    requests = [row["value"]["request"] for row in normalizer_requests]
    require(len({request["request_id"] for request in requests}) == len(requests),
            "Normalizer request identity")
    mutations = [request for request in requests
                 if request["op"] in ("CLAIM", "LOAD", "ARM", "ABORT", "RELEASE")]
    require([request["op"] for request in mutations] ==
            [op for _ in range(8) for op in ("CLAIM", "LOAD", "ARM", "RELEASE")],
            "Normalizer mutation order/count")
    for index in range(8):
        claim, load, arm, release = mutations[index * 4:index * 4 + 4]
        job = packet["normalizer_jobs"][index]
        require(claim["body"] == {"owner_id": packet["normalizer_owner"], "lease_ms": 60000} and
                load["body"] == job and arm["body"]["job_id"] == job["job_id"] and
                int(arm["body"]["start_utc_ns"]) > 0 and
                arm["body"]["max_start_uncertainty_ns"] == "500000000" and
                release["body"] == {}, "Exact normalizer mutations")

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
        require([(row["value"]["offset_seconds"], row["value"]["action"],
                  row["value"]["paths"]) for row in cycle_actions] == expected_actions and
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
        finish = finishes[cycle - 1]["value"]
        usb_states = {row["value"]["value"]["state"] for row in status}
        usb_jobs = {row["value"]["value"]["job_id"] for row in status
                    if row["value"]["value"].get("job_id")}
        require(len(status) >= 118 and max_gap([row["value"]["began_monotonic_ns"]
                for row in status]) <= 6_000_000_000 and
                max(row["value"]["ended_monotonic_ns"] - row["value"]["began_monotonic_ns"]
                    for row in status) <= 5_000_000_000 and
                all(row["value"]["value"]["boot_id"] == BOOT for row in status) and
                {"loaded", "armed", "running", "complete"}.issubset(usb_states) and
                usb_jobs == {finish["job_id"]},
                "USB STATUS coverage/lifecycle")
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
        require(end["monotonic_ns"] - begin["monotonic_ns"] >=
                begin["value"]["seconds"] * 1_000_000_000 and
                not [row for row in records if begin["monotonic_ns"] < row["monotonic_ns"] <
                     end["monotonic_ns"] and row["kind"] in forbidden] and
                quiet_console and all(
                    row["value"]["value"]["status"]["owner_id"] is None and
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
            all(record["state"] == "complete" and not record["output_active"]
                for record in final_status["terminal_records"]), "Final authority/terminal state")
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
                info["fault_status"] == 0 and info["tail_irqs"] >= 11 and
            int(info["launch_epoch"]) >= int(before_a["info"]["launch_epoch"]) + 11,
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
    for name in ("capture-ap.log", "capture-client.log"):
        text = (fixture_root / name).read_text()
        require(re.search(r"[1-9][0-9]* packets captured", text) and
                "0 packets dropped by kernel" in text, "Capture completeness")
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
    evidence["fixture/capture-ap.pcap"] = digest(fixture_root / "capture-ap.pcap")
    evidence["fixture/capture-client.pcap"] = digest(fixture_root / "capture-client.pcap")
    evidence["fixture/fixture.jsonl"] = digest(fixture_root / "fixture.jsonl")
    evidence["campaign.pcap"] = digest(root / "campaign.pcap")
    return {"schema": "phase11.5-package9-raw-audit-v1", "status": "PASS",
        "packet_sha256": expected_packet_sha, "candidate": {"source_revision": SOURCE,
            "image_sha256": IMAGE, "boot_id": BOOT, "device_id": DEVICE,
            "system_clock_hz": 138000000, "engine": "pio-dma-gp2", "renderer": "ram"},
        "normal_load_seconds": 1800, "rf_jobs": 11,
        "rf_duration_ns": RF_DURATION_NS, "normalizer_jobs": 8,
        "production_jobs": wire, "browser_actions": len(actions),
        "browser_gets": len(gets), "console_samples": len(console),
        "host_samples": len(host), "resource_windows": [row["value"] for row in windows],
        "matched_baseline_bytes": baseline, "post_n_bytes": posts,
        "final_q_bytes": final_live, "maximum_post_span_bytes": max(posts) - min(posts),
        "monotonic_retained_growth": False, "final_terminal_records": 8,
        "final_metrics": captured["final_metrics"], "reservation_released": True,
        "fixture_restored": True, "installed_service_active": True, "capture_drops": 0,
        "source_impact": {"deployed_source_revision": SOURCE,
            "later_runtime_source_changes": 0,
            "wsprrypi_source_revision": WSPRRYPI_SOURCE},
        "auditor_sha256": digest(Path(__file__)),
        "decoder_sha256": digest(decoder_path),
        "evidence_sha256": evidence}


def validate_published_result(value):
    """Validate the credential-free Package 9 and Phase 11.5 closure record."""
    require(value.get("schema") == "phase11.5-package9-result-v1" and
            value.get("status") == "PACKAGE9_COMPLETE_R6_CLOSED" and
            value.get("phase11_5_status") == "CLOSED_6_OF_6_FAMILIES" and
            value.get("family_status") == FAMILY_STATUS,
            "Package 9 closure status")
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
            campaign.get("rf_jobs") == 11 and
            campaign.get("planned_rf_duration_ns") == RF_DURATION_NS and
            campaign.get("normalizer_jobs") == 8 and
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
            campaign.get("monotonic_retained_growth") is False,
            "Package 9 campaign summary")
    baseline = campaign["matched_baseline_bytes"]
    require(all(isinstance(item, int) and abs(item - baseline) <= 1024
                for item in campaign["post_n_bytes"] + [campaign["final_q_bytes"]]) and
            max(campaign["post_n_bytes"]) - min(campaign["post_n_bytes"]) ==
                campaign["maximum_post_span_bytes"] and
            not (campaign["post_n_bytes"][0] < campaign["post_n_bytes"][1] <
                 campaign["post_n_bytes"][2]), "Published matched resource return")
    impact = value.get("source_impact", {})
    require(impact == {"prior_candidate": PRIOR_SOURCE,
            "deployed_candidate": SOURCE,
            "changed_runtime_files": RUNTIME_CHANGES,
            "diff_sha256": SOURCE_DIFF_SHA256,
            "decision": "Static page streaming and bounded Console/HTTP scheduling change "
                        "network resource service only. Package 9 directly covers the changed "
                        "mixed WTP, HTTPS, Console and RF interaction; RF renderer, launch, "
                        "refill, mode compilation and duration arithmetic are unchanged.",
            "later_runtime_source_changes": 0,
            "wsprrypi_source_revision": WSPRRYPI_SOURCE},
            "Package 9 source-impact decision")
    budget = value.get("cumulative_budget", {})
    require(isinstance(budget.get("attempt_count"), int) and
            budget["attempt_count"] >= 1 and
            isinstance(budget.get("charged_rf_jobs"), int) and
            budget["charged_rf_jobs"] >= 11 and
            RF_DURATION_NS <= budget.get("charged_rf_duration_ns", 0) <= 1_200_000_000_000 and
            budget.get("flashes") == budget.get("bootsel") == 6 and
            budget.get("configuration_writes") == budget.get("controlled_reboots") ==
                budget.get("wifi_cycles") == 0,
            "Cumulative Package 9 budget")
    require(value.get("repairs") == {"zero_rf_flashes": 6,
            "incorrect_build_rejected": True,
            "static_page_streaming": True,
            "bounded_console_http_grace_ms_per_second": 500,
            "accepted_configuration_restored": True}, "Package 9 repairs")
    require(value.get("restoration") == {"pico_a_inactive": True,
            "pico_a_schedule_disabled": True,
            "pico_b_unchanged_inactive": True,
            "reservation_released": True,
            "host_fixture_restored": True,
            "installed_service_active": True,
            "capture_drops": 0}, "Package 9 restoration")
    evidence = value.get("evidence_sha256", {})
    required = {"packet", "raw_audit", "adversarial", "attempt_history"}
    require(set(evidence) == required and all(isinstance(item, str) and len(item) == 64 and
            item != "0" * 64 and
            all(character in "0123456789abcdef" for character in item)
            for item in evidence.values()) and evidence["packet"] == campaign["packet_sha256"],
            "Package 9 evidence hashes")
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
