#!/usr/bin/env python3
"""Offline audit of the private Phase 11.5 Package 7 evidence."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

from phase11_5_inventory import require
from phase11_5_package7_plan import (ADDRESS, BOOT, B_BOOT, B_DEVICE, B_SERIAL, DEVICE,
                                     IMAGE, ROWS, SERIAL, SOURCE, WSPRRYPI_SOURCE, identity,
                                     validate as validate_packet)
from phase11_5_pilot import Decoder

DECODER_SHA256 = "5cf410758c48e05bc35f04f394b486f0b210b93e7ab785cedaf1bc7dd689162d"
OBSERVER_SHA256 = "fd70cde276b04aa08e771e12b83335a89aae24e050e2f2c5e56ed6848eb1a7bc"
INSTALLED_SHA256 = "c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273"
INSTALLED_INI_SHA256 = "e4158b2b041355f8cffea0388c8ce286c37d2a66d2d3a6e9c85e3af5f238bbc8"
INHERITED_ROWS = ["browser-armed-abort", "browser-running-abort", "acknowledged-loss"]
ALL_ROWS = ROWS[:13] + INHERITED_ROWS + ROWS[13:]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines()]
    require(rows and [row["sequence"] for row in rows] == list(range(len(rows))),
            "Journal sequence")
    require(all(rows[index]["monotonic_ns"] <= rows[index + 1]["monotonic_ns"]
                for index in range(len(rows) - 1)), "Journal time regression")
    return rows


def values(rows, kind):
    return [row["value"] for row in rows if row["kind"] == kind]


def single(rows, kind):
    found = values(rows, kind)
    require(len(found) == 1, "Expected one " + kind)
    return found[0]


def finished(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines()]
    found = [row["value"] for row in rows if row["kind"] == "finish"]
    require(len(found) == 1 and found[0]["result"] == "READ_ONLY_INVENTORY",
            "Incomplete final inventory")
    return found[0]


def inactive(value, serial, device, boot, revision=None):
    info, status = value["info"], value["wtp"]["STATUS"]
    require(value.get("serial", serial) == serial and
            info["device_id"] == value["wtp"]["HELLO"]["device_id"] == device and
            info["status"]["boot_id"] == value["wtp"]["HELLO"]["boot_id"] ==
            status["boot_id"] == boot, "Final inventory identity")
    if revision is not None:
        require(info["revision"] == revision[:12], "Final source revision")
    require(status["state"] == info["status"]["state"] == "empty" and
            status["owner_id"] is None and status["job_id"] is None and
            status["output_active"] is info["status"]["output_active"] is False and
            info["status"]["enabled"] is False, "Final authority is not Empty")
    return {"device_id": device, "boot_id": boot, "revision": info["revision"],
            "state": status["state"], "output_active": False}


def audit_foreign(rows, expected_states):
    found = values(rows, "foreign_rejected")
    expected_codes = {"CLAIM": "BUSY", "RELEASE": "NOT_OWNER", "ABORT": "NOT_OWNER"}
    require(len(found) == 3 * len(expected_states), "Foreign-control count")
    for state in expected_states:
        state_rows = [row for row in found if row["state"] == state]
        require(len(state_rows) == 3 and {row["op"] for row in state_rows} == set(expected_codes),
                "Foreign-control operation coverage")
        require(all(row["error"]["code"] == expected_codes[row["op"]]
                    for row in state_rows), "Foreign-control precedence")


def audit_storage(rows, states, *, has_baseline=True):
    http = [row for row in rows if row["kind"] == "http"]
    offset = 1 if has_baseline else 0
    require(len(http) == offset + 3 * len(states), "Storage HTTP exchange count")
    if has_baseline:
        baseline = http[0]["value"]
        require(baseline["method"] == "GET" and baseline["status"] == 200,
                "Storage baseline")
    results = {}
    for index, state in enumerate(states):
        start = offset + 3 * index
        before, mutation, after = http[start:start + 3]
        b, m, a = before["value"], mutation["value"], after["value"]
        require(b["method"] == a["method"] == "GET" and
                m["method"] == "PUT" and b["path"] == m["path"] == a["path"] ==
                "/api/v1/config", "Storage operation shape")
        require(b["status"] == a["status"] == 200 and m["status"] == 409 and
                m["body"]["error"]["code"] == "busy", "Storage busy result")
        require(b["body"] == a["body"] and b["headers"]["ETag"] == a["headers"]["ETag"],
                "Storage content or ETag changed")
        results[state] = {"etag": b["headers"]["ETag"], "put_utc_ns": mutation["utc_ns"]}
    return results


def audit_lost(root, rows, op, session, owner, job, state):
    written = [value for value in values(rows, "lost_write_complete") if value["op"] == op]
    effect = [value for value in values(rows, "lost_independent_effect") if value["op"] == op]
    replay = [value for value in values(rows, "lost_replay_pass") if value["op"] == op]
    require(len(written) == len(effect) == len(replay) == 1, "Lost-operation evidence count")
    written, effect, replay = written[0], effect[0], replay[0]
    request = written["request"]
    require(written["delivered_reply_bytes"] == 0 and written["bytes"] == len(bytes.fromhex(written["hex"])) and
            request["op"] == op and request["session_id"] == session and
            request["body"]["job_id"] == job and replay["request_id"] == request["request_id"] and
            replay["job_id"] == job, "Lost-operation request/replay identity")
    status = effect["status"]
    require(status["boot_id"] == BOOT and status["state"] == state and
            status["owner_id"] == owner and status["job_id"] == job and
            status["output_active"] is False, "Lost-operation independent effect")
    require(replay["replay"]["state"] == state and replay["inbound_ciphertext_packets"] > 0,
            "Lost-operation replay result")
    prefix = op.lower()
    require((root / f"{prefix}-request.bin").read_bytes() == bytes.fromhex(written["hex"]),
            "Saved lost-operation request differs")
    capture_log = (root / f"{prefix}-capture.log").read_text()
    packet_text = (root / f"{prefix}-packets.txt").read_text()
    require((root / f"{prefix}.pcap").stat().st_size > 24 and
            re.search(r"[1-9][0-9]* packets captured", capture_log) and
            "0 packets dropped by kernel" in capture_log and packet_text,
            "Lost-operation capture incomplete")
    packet_lines = packet_text.splitlines()
    server = f"{ADDRESS}.18443 > 10.77.15.2."
    server_payload = [index for index, line in enumerate(packet_lines)
                      if server in line and re.search(r"length [1-9][0-9]*$", line)]
    require(len(server_payload) == 1 and "length 53" in packet_lines[server_payload[0]] and
            re.search(r"ack [1-9][0-9]*", packet_lines[server_payload[0]]),
            "Lost-operation server response was not captured")
    client_after = [line for line in packet_lines[server_payload[0] + 1:]
                    if "10.77.15.2." in line and f"> {ADDRESS}.18443" in line]
    client_acks = [int(match.group(1)) for line in client_after
                   if (match := re.search(r"ack ([0-9]+)", line))]
    require(all(ack <= 1 for ack in client_acks),
            "Client acknowledged dropped response data")
    return {"request_id": request["request_id"], "job_id": job,
            "state": state, "inbound_ciphertext_packets": replay["inbound_ciphertext_packets"],
            "server_response_payload_bytes": 53,
            "client_response_acknowledged": False}


def load_decoder(path):
    require(digest(path) == DECODER_SHA256, "TLS observer decoder identity")
    spec = importlib.util.spec_from_file_location("phase115_tls_observer_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decode_direction(rows, connection, kind):
    decoder, messages = Decoder(), []
    for row in rows:
        if row["connection_id"] == connection and row["kind"] == kind:
            messages.extend(decoder.feed(row["payload"]))
    require(not decoder.buffer, "Partial WTP observer frame")
    return messages


def audit_wire(path, decoder_module, passed):
    rows = decoder_module.decode(path.read_bytes())
    connections = sorted({row["connection_id"] for row in rows if row["kind"] == 1})
    candidates = []
    for connection in connections:
        written = decode_direction(rows, connection, 3)
        if written:
            candidates.append((connection, written, decode_direction(rows, connection, 4)))
    require(len(candidates) == 1, "Production WTP connection count")
    _, written, received = candidates[0]
    require(len({message["request_id"] for message in written}) == len(written),
            "Duplicate production request identity")
    require({message["session_id"] for message in written} == {passed["session_id"]},
            "Production WTP session changed")
    mutations = [message for message in written
                 if message["op"] in ("CLAIM", "LOAD", "ARM", "ABORT", "RELEASE")]
    require([message["op"] for message in mutations] ==
            ["CLAIM", "LOAD", "ARM", "ABORT", "RELEASE"],
            "Production mutation order or duplication")
    require(mutations[0]["body"]["owner_id"] == passed["owner_id"] and
            all(message["body"].get("job_id") == passed["job_id"]
                for message in mutations[1:4]), "Production wire authority")
    for request in mutations:
        responses = [message for message in received
                     if message.get("type") == "response" and
                     message.get("request_id") == request["request_id"] and
                     message.get("op") == request["op"]]
        require(len(responses) == 1 and responses[0]["ok"] is True,
                "Production mutation response missing")
    return {"records": len(rows), "requests": len(written),
            "mutations": [message["op"] for message in mutations]}


def audit_production(root, case, packet, decoder_module):
    case_root = root / case
    rows = read_rows(case_root / "production.jsonl")
    selected, passed = single(rows, "production_selected_state"), single(rows, "production_pass")
    require(selected["case"] == passed["case"] == case and
            passed["planned_duration_ns"] == 33_000_000_000, "Production case identity")
    status, host = selected["status"], selected["host"]
    active = case == "running"
    require(status["boot_id"] == BOOT and status["state"] == case and
            status["output_active"] is active and status["job_id"] == passed["job_id"] and
            status["owner_id"] == passed["owner_id"], "Production selected authority")
    stable = {key: status[key] for key in ("state", "job_id", "owner_id", "output_active")}
    require(host["owns"] is True and host["lease_valid"] is True and
            {key: host["remote"][key] for key in stable} == stable and
            host["session_id"] == passed["session_id"], "Production host authority")
    browser = single(rows, "browser_abort_response")
    require(browser["status"] == 200 and browser["body"]["ok"] is True and
            browser["body"]["request_id"] == packet[f"production_{case}_request"],
            "Production browser ABORT")
    require(passed["terminal"] == {"job_id": passed["job_id"],
            "state": "aborted", "ended_monotonic_ns": passed["terminal"]["ended_monotonic_ns"],
            "output_active": False} and passed["last_report"]["outcome"] == "cancelled" and
            passed["last_report"]["job_id"] == passed["job_id"] and
            passed["final"]["state"] == "empty" and passed["final"]["owner_id"] is None and
            passed["final"]["job_id"] is None and passed["final"]["output_active"] is False,
            "Production terminal/release")
    cleanup = single(rows, "production_cleanup")["status"]
    require(cleanup["state"] == "empty" and cleanup["output_active"] is False and
            cleanup["enabled"] is False and cleanup["boot_id"] == BOOT,
            "Production cleanup")
    if case == "running":
        audit_foreign(rows, ["running"])
        storage = audit_storage(rows, ["running"], has_baseline=False)["running"]
    else:
        require(not values(rows, "foreign_rejected") and not values(rows, "storage_rejected"),
                "Unexpected Armed overlap checks")
        storage = None
    wire = audit_wire(case_root / "production-tls.bin", decoder_module, passed)
    return {"job_id": passed["job_id"], "owner_id": passed["owner_id"],
            "session_id": passed["session_id"], "state": case, "terminal": "aborted",
            "browser_request_id": browser["body"]["request_id"], "wire": wire,
            "storage": storage}


def tree_digest(path):
    files = sorted(item for item in path.rglob("*") if item.is_file())
    require(files, "Preserved failure directory is empty")
    value = hashlib.sha256()
    for item in files:
        value.update(str(item.relative_to(path)).encode() + b"\0")
        value.update(bytes.fromhex(digest(item)))
    return value.hexdigest()


def evidence_hashes(root, fixture_root):
    names = ["packet.json", "direct.jsonl", "tail.jsonl", "load-request.bin", "load.pcap",
             "arm-request.bin", "arm.pcap", "abort-request.bin", "abort.pcap",
             "armed/production.jsonl", "armed/production-tls.bin", "armed/case.json",
             "running/production.jsonl", "running/production-tls.bin", "running/case.json",
             "final-a.jsonl", "final-b.jsonl", "post-restoration-a.jsonl",
             "post-restoration-b.jsonl", "reservation-released.json", "installed-before.txt",
             "installed-after.txt", "r4-regressions.log"]
    result = {name: digest(root / name) for name in names}
    result["fixture/fixture-state.json"] = digest(fixture_root / "fixture-state.json")
    return result


def validate_result(result):
    require(result["schema"] == "phase11.5-package7-result-v1" and
            result["status"] == "PACKAGE7_COMPLETE_R4_CLOSED" and
            result["family_status"] == {"R1": "CLOSED", "R2": "CLOSED", "R3": "CLOSED",
                                        "R4": "CLOSED", "R5": "OPEN", "R6": "OPEN"},
            "Package 7 result status")
    require(result["accepted_rows"] == ROWS and result["inherited_rows"] == INHERITED_ROWS and
            result["all_r4_rows"] == ALL_ROWS and len(set(result["all_r4_rows"])) == 18,
            "Package 7 row closure")
    require(result["phase11_5_status"] == "OPEN_4_OF_6_FAMILIES" and
            result["candidate"] == {
                "board": "Pico A 0BF4B4AEC9FFB344",
                "source_revision": SOURCE,
                "image_sha256": IMAGE,
                "boot_id": BOOT,
                "device_id": DEVICE,
                "system_clock_hz": 138_000_000,
                "pio_divider": 1,
                "engine": "pio-dma-gp2",
                "renderer": "RAM",
                "network_listener": "configured",
                "wsprrypi_source_revision": WSPRRYPI_SOURCE,
            } and
            result["packet_sha256"] ==
            "78e3422fbf1638e89062a56da965bd2bacc8fc0c14d603be68bd62d031fab051",
            "Package 7 candidate or packet identity")
    budget = result["budget"]
    expected_attempts = [
        ("direct-state-transition", 1, 12_000_000_000, "retained-failure"),
        ("production-armed-transition", 1, 33_000_000_000, "retained-failure"),
        ("tail-console-schema", 1, 12_000_000_000, "retained-failure"),
        ("tail-queued-event", 1, 12_000_000_000, "retained-failure"),
        ("lost-abort-tail", 1, 12_000_000_000, "accepted"),
        ("production-armed-host-authority", 1, 33_000_000_000, "retained-failure"),
        ("production-armed", 1, 33_000_000_000, "accepted"),
        ("production-running-console-schema", 1, 33_000_000_000, "retained-failure"),
        ("production-running", 1, 33_000_000_000, "accepted"),
    ]
    attempts = [(row["name"], row["rf_jobs"], row["planned_rf_duration_ns"],
                 row["outcome"]) for row in budget["attempts"]]
    require(budget["rf_jobs"] == 9 and budget["planned_rf_duration_ns"] == 213_000_000_000 and
            sum(attempt["rf_jobs"] for attempt in budget["attempts"]) == 9 and
            sum(attempt["planned_rf_duration_ns"] for attempt in budget["attempts"]) ==
            213_000_000_000 and budget["rf_jobs"] <= budget["ceiling_jobs"] == 16 and
            budget["planned_rf_duration_ns"] <= budget["ceiling_duration_ns"] ==
            14_400_000_000_000 and attempts == expected_attempts and
            budget["zero_rf_failures"] == 6, "Package 7 budget accounting")
    authority = result["authority_and_storage"]
    require(authority["foreign_states"] == ["empty", "loaded", "armed", "running"] and
            list(authority["storage_states"]) == ["empty", "loaded", "armed", "running"] and
            all(item["etag"] == authority["storage_states"]["empty"]["etag"] and
                isinstance(item["put_utc_ns"], int)
                for item in authority["storage_states"].values()),
            "Package 7 authority/storage summary")
    lost = result["lost_operations"]
    require(list(lost) == ["LOAD", "ARM", "ABORT"] and
            [lost[op]["state"] for op in lost] == ["loaded", "armed", "aborted"] and
            len({lost[op]["request_id"] for op in lost}) == 3 and
            lost["LOAD"]["job_id"] == lost["ARM"]["job_id"] != lost["ABORT"]["job_id"] and
            all(identity(lost[op]["request_id"], op + " request") and
                identity(lost[op]["job_id"], op + " job") and
                lost[op]["inbound_ciphertext_packets"] > 0 and
                lost[op]["server_response_payload_bytes"] == 53 and
                lost[op]["client_response_acknowledged"] is False for op in lost),
            "Package 7 lost-operation summary")
    production = result["production"]
    require(list(production) == ["armed", "running"] and
            len({production[case]["browser_request_id"] for case in production}) == 2,
            "Package 7 production case set")
    for case in ("armed", "running"):
        value = production[case]
        require(value["state"] == case and value["terminal"] == "aborted" and
                all(identity(value[name], f"production {case} {name}")
                    for name in ("job_id", "owner_id", "session_id", "browser_request_id")) and
                value["wire"]["records"] > 0 and value["wire"]["requests"] > 0 and
                value["wire"]["mutations"] == ["CLAIM", "LOAD", "ARM", "ABORT", "RELEASE"],
                "Package 7 production evidence")
    require(production["armed"]["storage"] is None and
            production["running"]["storage"] == authority["storage_states"]["running"],
            "Package 7 production storage")
    require(result["regressions"] == {
                "source_revision": WSPRRYPI_SOURCE,
                "tcp_reset_eof": "PASS", "resolver_failure": "PASS",
                "backend": "PASS", "production": "PASS", "network_lifecycle": "PASS",
            } and result["source_impact"] == {
                "pico_runtime_source_changes_after_candidate": 0,
                "current_repository_changes": "documentation, auditors and tests only",
                "historical_browser_and_acknowledged_loss_rows": "applicable",
            }, "Package 7 regression or applicability summary")
    failures = result["failed_attempt_sha256"]
    require(len(failures) == 11 and
            all(len(value) == 64 and all(c in "0123456789abcdef" for c in value)
                for value in failures.values()), "Package 7 retained failures")
    expected_a = {"device_id": DEVICE, "boot_id": BOOT, "revision": SOURCE[:12],
                  "state": "empty", "output_active": False}
    require(result["final_inventories"]["a"] == expected_a and
            result["post_restoration_inventories"]["a"] == expected_a,
            "Package 7 final A inventory")
    for key in ("final_inventories", "post_restoration_inventories"):
        require(result[key]["b"]["device_id"] == B_DEVICE and
                result[key]["b"]["boot_id"] == B_BOOT and
                result[key]["b"]["state"] == "empty" and
                result[key]["b"]["output_active"] is False,
                "Package 7 final B inventory")
    restoration_keys = {
        "rf_reservation_released", "fixture_restored", "installed_binary_restored",
        "installed_config_restored", "installed_service_active", "schedules_disabled",
        "both_boards_empty", "recovery_timer_active", "fixture_namespace_absent",
    }
    require(set(result["restoration"]) == restoration_keys and
            all(result["restoration"].values()), "Package 7 restoration")
    require(len(result["evidence_sha256"]) == 24 and
            all(len(value) == 64 and all(c in "0123456789abcdef" for c in value)
                for value in result["evidence_sha256"].values()),
            "Package 7 evidence digest")
    return result


def audit(root, decoder, fixture_root):
    root, fixture_root = Path(root), Path(fixture_root)
    packet = validate_packet(json.loads((root / "packet.json").read_text()))
    packet_hash = digest(root / "packet.json")
    require(packet_hash == "78e3422fbf1638e89062a56da965bd2bacc8fc0c14d603be68bd62d031fab051",
            "Final Package 7 packet identity")
    require(digest(root / "observer.so") == OBSERVER_SHA256, "Production observer identity")
    decoder_module = load_decoder(Path(decoder))

    direct = read_rows(root / "direct.jsonl")
    require(not values(direct, "direct_pass"), "Failed direct attempt was accepted")
    audit_foreign(direct, ["empty", "loaded", "armed"])
    storage = audit_storage(direct, ["empty", "loaded", "armed"])
    arm_write, = [value for value in values(direct, "lost_write_complete") if value["op"] == "ARM"]
    require(storage["armed"]["put_utc_ns"] < int(arm_write["request"]["body"]["start_utc_ns"]),
            "Armed storage response was not before launch")
    lost = {
        "LOAD": audit_lost(root, direct, "LOAD", packet["network_session"], packet["owner_id"],
                           packet["direct_job_id"], "loaded"),
        "ARM": audit_lost(root, direct, "ARM", packet["network_session"], packet["owner_id"],
                          packet["direct_job_id"], "armed"),
    }
    tail = read_rows(root / "tail.jsonl")
    tail_pass = single(tail, "tail_pass")
    lost["ABORT"] = audit_lost(root, tail, "ABORT", packet["tail_network_session"],
                               packet["tail_owner_id"], packet["tail_job_id"], "aborted")
    require(tail_pass["job_id"] == packet["tail_job_id"] and
            tail_pass["planned_duration_ns"] == 12_000_000_000 and
            tail_pass["terminal"]["state"] == "aborted" and
            tail_pass["final"]["state"] == "empty", "Lost-ABORT tail result")
    production = {case: audit_production(root, case, packet, decoder_module)
                  for case in ("armed", "running")}

    regressions = (root / "r4-regressions.log").read_text()
    require(regressions.startswith(WSPRRYPI_SOURCE + "\n") and
            "1122306 WTP backend checks passed" in regressions and
            "6871 production WTP configuration/runtime checks passed" in regressions and
            "web_server_network_lifecycle_test: PASS" in regressions,
            "R4 current-source regressions")
    release = json.loads((root / "reservation-released.json").read_text())
    require(release["packet_sha256"] == packet_hash, "RF reservation release identity")
    final = {"a": inactive(finished(root / "final-a.jsonl"), SERIAL, DEVICE, BOOT, SOURCE),
             "b": inactive(finished(root / "final-b.jsonl"), B_SERIAL, B_DEVICE, B_BOOT)}
    restored = {"a": inactive(finished(root / "post-restoration-a.jsonl"), SERIAL, DEVICE,
                                BOOT, SOURCE),
                "b": inactive(finished(root / "post-restoration-b.jsonl"), B_SERIAL, B_DEVICE,
                                B_BOOT)}
    before, after = (root / "installed-before.txt").read_text(), (root / "installed-after.txt").read_text()
    require(INSTALLED_SHA256 in before and INSTALLED_SHA256 in after and
            INSTALLED_INI_SHA256 in before and INSTALLED_INI_SHA256 in after and
            "ActiveState=active" in after and "SubState=running" in after and
            "Transmit = false" in after and "Transmit Backend = rp1-gpclk" in after and
            "Enable on Boot = Never" in after and "\nactive\nenabled\n" in after and
            "phase115-closure-client" not in after, "Installed service restoration")
    fixture = json.loads((fixture_root / "fixture-state.json").read_text())
    require(fixture.get("restored") is True, "Fixture restoration state")

    charged = [
        ("direct-state-transition", 1, 12_000_000_000, "retained-failure"),
        ("production-armed-transition", 1, 33_000_000_000, "retained-failure"),
        ("tail-console-schema", 1, 12_000_000_000, "retained-failure"),
        ("tail-queued-event", 1, 12_000_000_000, "retained-failure"),
        ("lost-abort-tail", 1, 12_000_000_000, "accepted"),
        ("production-armed-host-authority", 1, 33_000_000_000, "retained-failure"),
        ("production-armed", 1, 33_000_000_000, "accepted"),
        ("production-running-console-schema", 1, 33_000_000_000, "retained-failure"),
        ("production-running", 1, 33_000_000_000, "accepted"),
    ]
    failures = ["failed-direct-preflight-owner-field", "failed-direct-preflight-schedule-shape",
                "failed-direct-preflight-http-name", "failed-direct-renew-owner",
                "failed-armed-systemctl-namespace", "failed-production-armed-transition",
                "failed-tail-console-schema", "failed-tail-queued-event",
                "failed-tail-aborted-admission", "failed-production-armed-host-authority",
                "failed-production-running-console-schema"]
    failure_hashes = {name: tree_digest(root / name) for name in failures}
    result = {
        "schema": "phase11.5-package7-result-v1",
        "status": "PACKAGE7_COMPLETE_R4_CLOSED",
        "phase11_5_status": "OPEN_4_OF_6_FAMILIES",
        "family_status": {"R1": "CLOSED", "R2": "CLOSED", "R3": "CLOSED",
                          "R4": "CLOSED", "R5": "OPEN", "R6": "OPEN"},
        "accepted_rows": ROWS,
        "inherited_rows": INHERITED_ROWS,
        "all_r4_rows": ALL_ROWS,
        "candidate": {"board": "Pico A 0BF4B4AEC9FFB344",
                      "source_revision": SOURCE, "image_sha256": packet["image_sha256"],
                      "boot_id": BOOT, "device_id": DEVICE,
                      "system_clock_hz": 138_000_000, "pio_divider": 1,
                      "engine": "pio-dma-gp2", "renderer": "RAM",
                      "network_listener": "configured",
                      "wsprrypi_source_revision": WSPRRYPI_SOURCE},
        "packet_sha256": packet_hash,
        "budget": {"rf_jobs": packet["rf_jobs"],
                   "planned_rf_duration_ns": packet["rf_duration_ns"],
                   "ceiling_jobs": packet["corrective_amendment"]["standing_packet_ceiling_jobs"],
                   "ceiling_duration_ns": packet["corrective_amendment"]["standing_packet_ceiling_duration_ns"],
                   "attempts": [{"name": name, "rf_jobs": jobs,
                                 "planned_rf_duration_ns": duration, "outcome": outcome}
                                for name, jobs, duration, outcome in charged],
                   "zero_rf_failures": 6},
        "authority_and_storage": {"foreign_states": ["empty", "loaded", "armed", "running"],
                                  "storage_states": storage | {"running": production["running"]["storage"]}},
        "lost_operations": lost,
        "production": production,
        "regressions": {"source_revision": WSPRRYPI_SOURCE, "tcp_reset_eof": "PASS",
                        "resolver_failure": "PASS", "backend": "PASS",
                        "production": "PASS", "network_lifecycle": "PASS"},
        "source_impact": {"pico_runtime_source_changes_after_candidate": 0,
                          "current_repository_changes": "documentation, auditors and tests only",
                          "historical_browser_and_acknowledged_loss_rows": "applicable"},
        "failed_attempt_sha256": failure_hashes,
        "final_inventories": final,
        "post_restoration_inventories": restored,
        "restoration": {"rf_reservation_released": True, "fixture_restored": True,
                        "installed_binary_restored": True, "installed_config_restored": True,
                        "installed_service_active": True, "schedules_disabled": True,
                        "both_boards_empty": True, "recovery_timer_active": True,
                        "fixture_namespace_absent": True},
        "evidence_sha256": evidence_hashes(root, fixture_root),
    }
    return validate_result(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--decoder", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    args = parser.parse_args()
    json.dump(audit(args.root, args.decoder, args.fixture_root), sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
