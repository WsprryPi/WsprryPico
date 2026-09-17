#!/usr/bin/env python3
"""Audit raw Phase 11.5 Package 8 evidence and its sanitized closure result."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


SOURCE = "7c5296471250cc06416c79a73c9627aed0eb3624"
IMAGE = "c73e0714572cb0edd7f3ba4c6c0c9e3b3a8ac500aca7a7edea23fc4b32cb9e87"
DEVICE = "fd6127d11d6aca42a9905fa3fb1bf1d5"
B_DEVICE = "29f20b7342051ef947aa56cb9d4fab42"
B_BOOT = "6684b4b197d80cfa0ce83b3aaf205cb0"
DEPLOYED_BOOT = "61130461c14d4fb9297684539d4ebd45"
FAILED_STORAGE_BOOT = "8af7e0f0f4cef61bcbf8d5f7173d4c78"
FINAL_BOOT = "f93fe05254d1523e50b16b0ad248a44a"
HOST_BOOT = "220e53ca-ca95-4206-9581-dbe28aa1eeb8"
PARENT_PACKET = "37d7405bdec781fd3dce9e854b2cdd8548b356f5c51e86d14e537646b12dfb01"
RETRY_PACKET = "de2a51816f1ae0e1588a0eccbdb8c3dc6076361ac251c40327bcd6c66efdfdf3"
BASE_NHZ = "135500000000000"
LOCAL_OWNER = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
ROWS = ["R5.link-loss", "R5.address", "R5.wifi", "R5.dns-sntp",
        "R5.persistence", "R5.rotation", "R5.time-admission", "R5.schedule"]
PRODUCTION_CHANGES = ["CMakeLists.txt", "src/standalone/pico/adapters.cpp",
                      "src/standalone/pico/adapters.hpp", "src/standalone/scheduler.cpp",
                      "src/standalone/storage.hpp"]
SOURCE_DIFF_SHA256 = "6e724bf7ddfdb072008439fe2240eeba28e0c16d56b83b484a671b9b4aab79a6"
ARCHIVE_SHA256 = "cfe88bd9cb8852640a4044fcd67b8baf240aaa8b546dd248bb5644df7adfd82b"
EVIDENCE_SHA256 = {
    "phase11-5-package8-20260916/network-attempt1-packet.json":
        "44918000c592b5348179fbafb5d96432efd2a577f6c1f5b3b9d7fcf8e853724d",
    "phase11-5-package8-20260916/packet.json":
        "7248629e1c08d45571598f101da4f3687ea062680a4ed86e9e2ea2e6c9a6a5e3",
    "phase11-5-package8-20260916/network-run.jsonl":
        "c57e1546ce8b177c3240887fad5d10baa386bf637f9665b01aabd75a815ca6d9",
    "phase11-5-package8-20260916/network-run-attempt2.jsonl":
        "2edfc16623899402c2e552494ed233767e1d465ef2e92193d1cf9983cf6fcc68",
    "phase11-5-package8-deploy2-20260916/packet.json":
        "27b87b496585bb80371dee8302851bd813db2228e71b4bbdc9b9781fac7c5160",
    "phase11-5-package8-deploy2-20260916/deployment.json":
        "ef29468ec493f67ad28f38794d43b13ae4312473479c31cdadfab7f16f0f3655",
    "phase11-5-package8-repair-deploy-20260916/packet.json":
        "45cdcb5c276498b5720a8745b0c8b76af255ad967ebb63445919f1b4d2c28324",
    "phase11-5-package8-repair-deploy-20260916/deployment.json":
        "057297ba46e0ff55be5f32deb644a9a3a3f23e85ca73c6bfebf92a52668128a2",
    "phase11-5-package8-repair-20260916/packet.json":
        "37d7405bdec781fd3dce9e854b2cdd8548b356f5c51e86d14e537646b12dfb01",
    "phase11-5-package8-repair-20260916/network-run.jsonl":
        "e388615ae05a9347e30127e2beb7960d50458c454b6a0a4c72278a23f355be86",
    "phase11-5-package8-repair-20260916/network-finalize.jsonl":
        "18d596555f7448f70a4703d18359b102b3bc06e57a141cad5366d213640d8292",
    "phase11-5-package8-repair-20260916/network-result.json":
        "9cf0cdf4e11ae8b01993804b57e8e804f7ea2adb926cc5634eb66413c371cd3c",
    "phase11-5-package8-repair-20260916/storage-run.jsonl":
        "1766ba75586a637d38fe4979fb0646ff9321535e43381b6233f71bc27113943c",
    "phase11-5-package8-repair-20260916/storage-retry-packet.json":
        "de2a51816f1ae0e1588a0eccbdb8c3dc6076361ac251c40327bcd6c66efdfdf3",
    "phase11-5-package8-repair-20260916/storage-retry.jsonl":
        "e10fa25abe9cec5bfff52c77ea26d4c70700ff9c4889cde49f8bf1fa45132239",
    "phase11-5-package8-repair-20260916/storage-result.json":
        "7f1fb8fbcca668a50e7168a75f4928956391defae3894cebbf2d0398086c57ed",
    "phase11-5-package8-repair-20260916/storage-retry-reservation-released.json":
        "277285d3b6327dc88d0ae8c09552dbd11fcaf120dd2497bffec60476a037ff23",
    "phase11-5-package8-repair-20260916/storage-retry-final-a.stdout":
        "0f38c9fbbdaf0ab8a64ff4a63db6921c1bec73f115ab30c2d7eb0e84967ba4d2",
    "phase11-5-package8-repair-20260916/storage-retry-final-b.stdout":
        "0f83af1c6f97bc2770a7425598b2cb653cfd2556902b17abfbcc5e9157de5248",
    "phase11-5-package8-repair-20260916/fixture-state.json":
        "824951352495e4d07ae8a7c5497ce3703e09b395baa3593a09fc70f0fe9dbdac",
    "phase11-5-package8-repair-20260916/fixture.jsonl":
        "0c4481f678648395e7bec2faf6a8a137a253c3f89f3a29d020984a4883ff86f2",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def values(records, kind):
    return [row["value"] for row in records if row["kind"] == kind]


def console_exchanges(records):
    exchanges, current = [], None
    for row in records:
        if row["kind"] == "console_tx":
            if current is not None:
                exchanges.append(current)
            current = {"command": bytes.fromhex(row["value"]["hex"]).decode().strip(),
                       "response": bytearray()}
        elif row["kind"] == "console_rx" and current is not None:
            current["response"].extend(bytes.fromhex(row["value"]["hex"]))
    if current is not None:
        exchanges.append(current)
    complete = []
    for item in exchanges:
        raw = bytes(item["response"])
        if not raw:
            require(item["command"] == "INFO", "Mutation command lacked a response")
            continue
        require(raw.endswith(b"\n") and raw.count(b"\n") == 1,
                "Console response framing")
        item["response"] = json.loads(raw)
        complete.append(item)
    return complete


def inventory(path):
    records = rows(path)
    finished = values(records, "finish")
    require(len(finished) == 1 and finished[0]["result"] == "READ_ONLY_INVENTORY",
            "Final inventory completion")
    value = finished[0]
    info, hello, status = value["info"], value["wtp"]["HELLO"], value["wtp"]["STATUS"]
    require(info["device_id"] == hello["device_id"] and
            info["status"]["boot_id"] == hello["boot_id"] == status["boot_id"] and
            info["status"]["state"] == status["state"] and
            info["status"]["output_active"] is status["output_active"] is False and
            status["owner_id"] is None and info["status"]["enabled"] is False,
            "Final inventory identity and authority")
    return {"device_id": info["device_id"], "revision": info["revision"],
            "boot_id": status["boot_id"], "state": status["state"],
            "output_active": False, "enabled": False}


def exact_source_impact(repo):
    completed = subprocess.run(
        ["git", "diff", "--name-only",
         "2b25ca05c270819466a04498f9bc4894a4c5bace.." + SOURCE,
         "--", "src", "include", "firmware", "cmake", "CMakeLists.txt"],
        cwd=repo, check=True, text=True, stdout=subprocess.PIPE)
    names = completed.stdout.splitlines()
    require(names == PRODUCTION_CHANGES, "Package 8 source-impact file set")
    diff = subprocess.run(
        ["git", "diff", "2b25ca05c270819466a04498f9bc4894a4c5bace.." + SOURCE,
         "--", "src", "include", "firmware", "cmake", "CMakeLists.txt"],
        cwd=repo, check=True, stdout=subprocess.PIPE).stdout
    require(hashlib.sha256(diff).hexdigest() == SOURCE_DIFF_SHA256,
            "Package 8 source-impact diff")
    later = subprocess.run(
        ["git", "diff", "--name-only", SOURCE + "..HEAD", "--",
         "src", "include", "firmware", "cmake"], cwd=repo, check=True,
        text=True, stdout=subprocess.PIPE).stdout
    require(not later, "Later production source drift after Package 8 candidate")


def audit_raw(evidence, archive, repo):
    require(digest(archive) == ARCHIVE_SHA256, "Package 8 evidence archive identity")
    old = evidence / "phase11-5-package8-20260916"
    first_deploy = evidence / "phase11-5-package8-deploy2-20260916"
    repair_deploy = evidence / "phase11-5-package8-repair-deploy-20260916"
    current = evidence / "phase11-5-package8-repair-20260916"
    require(all(path.is_dir() for path in (old, first_deploy, repair_deploy, current)),
            "Complete Package 8 evidence roots")
    exact_source_impact(repo)

    # Both deployed candidates are explicit one-flash/one-BOOTSEL packets.  The
    # first one is retained because its external-link recovery failed.
    deployments = []
    for root, source, image, boot in (
            (first_deploy, "71d8f5b174d227ec4ecbbfbda594b5edc19a7313",
             "9ec4b084822dc5d6bf54bac3798ea178051162d5aea45b83255503eee681cbd7",
             "3609966a45a282631fb9e38884724d25"),
            (repair_deploy, SOURCE, IMAGE, DEPLOYED_BOOT)):
        packet, state, released = load(root / "packet.json"), load(root / "deployment.json"), \
            load(root / "reservation-released.json")
        require(packet["source_revision"] == source and packet["image_sha256"] == image and
                packet["limits"] == {"flashes": 1, "bootsel": 1, "rf_jobs": 0,
                    "loads": 0, "arm": 0, "reboots": 0, "wifi_cycles": 0,
                    "configuration_writes": 0} and
                state == {"bootsel_commands": 1, "flashes_started": 1,
                          "status": "CANDIDATE_VERIFIED", "boot_id": boot} and
                released["state"] == "RELEASED" and
                released["boards"]["a"]["boot_id"] == boot and
                released["boards"]["b"]["boot_id"] == B_BOOT,
                "Package 8 deployment identity/budget")
        deployments.append({"packet_sha256": digest(root / "packet.json"),
                            "source_revision": source, "image_sha256": image,
                            "boot_id": boot, "flashes": 1, "bootsel": 1})

    # Preserve the no-RF harness failure and the real one-job reconnect failure.
    preclaim = rows(old / "network-run.jsonl")
    require(digest(old / "network-attempt1-packet.json") ==
            "44918000c592b5348179fbafb5d96432efd2a577f6c1f5b3b9d7fcf8e853724d" and
            not values(preclaim, "usb_status") and
            [item["request"]["op"] for item in values(preclaim, "network_tx")] ==
                ["HELLO", "CAPS", "CAPS"],
            "Preserved pre-CLAIM harness failure")
    failed_network = rows(old / "network-run-attempt2.jsonl")
    failed_usb = values(failed_network, "usb_status")
    failed_final = values(failed_network, "info_observation")[-1]
    require(digest(old / "packet.json") ==
            "7248629e1c08d45571598f101da4f3687ea062680a4ed86e9e2ea2e6c9a6a5e3" and
            any(item["state"] == "running" and item["output_active"] for item in failed_usb) and
            sum(item["state"] == "complete" for item in failed_usb) == 1 and
            failed_final["network"]["link_status"] == -3 and
            failed_final["network"]["ipv4"] == "" and
            failed_final["status"]["output_active"] is False,
            "Preserved address-recovery failure")

    parent = load(current / "packet.json")
    require(digest(current / "packet.json") == PARENT_PACKET and
            parent["source_revision"] == SOURCE and parent["image_sha256"] == IMAGE and
            parent["boot_id"] == DEPLOYED_BOOT and parent["b_boot_id"] == B_BOOT and
            parent["schedule_base_frequency_nhz"] == BASE_NHZ,
            "Repaired Package 8 parent packet")

    network = load(current / "network-result.json")
    network_rows = rows(current / "network-run.jsonl")
    network_usb = values(network_rows, "usb_status")
    fixture_rows = rows(current / "fixture.jsonl")
    kinds = [row["kind"] for row in fixture_rows]
    require(network["status"] == "accepted" and network["boot_id"] == DEPLOYED_BOOT and
            network["planned_duration_ns"] == 240_000_000_000 and
            network["running_usb_samples"] == 1047 and
            sum(item["state"] == "running" and item["output_active"]
                for item in network_usb) == 1047 and
            sum(item["state"] == "complete" for item in network_usb) == 1 and
            network["terminal"]["state"] == "complete" and
            network["terminal"]["output_active"] is False and
            network["recovered_ipv4"] == "10.77.15.20" and
            network["native_resolutions"] == [["10.77.15.20"], ["10.77.15.20"]] and
            network["sntp_accepted"] == 8 and network["sntp_rejected"] == 0 and
            network["https_status"] == 200 and
            [item["request"]["op"] for item in values(network_rows, "network_tx")] ==
                ["HELLO", "CAPS", "CAPS", "CLAIM", "LOAD", "RENEW", "GET_CLOCK",
                 "ARM", "HELLO", "CAPS", "STATUS"] and
            kinds.count("dhcp_binding_changed") == kinds.count("external_link_down") ==
                kinds.count("external_link_restored") == 1,
            "Package 8 network lifecycle")

    # The first storage attempt reached Armed only; it never asserted output.
    # Its STOP/config cleanup and exact log hash are prerequisites for the retry.
    failed_storage = rows(current / "storage-run.jsonl")
    failed_states = values(failed_storage, "schedule_usb_status")
    require(digest(current / "storage-run.jsonl") ==
            "1766ba75586a637d38fe4979fb0646ff9321535e43381b6233f71bc27113943c" and
            sum(item["state"] == "armed" for item in failed_states) == 1 and
            not any(item["state"] == "running" or item["output_active"]
                    for item in failed_states) and
            len(values(failed_storage, "cleanup_stop")) ==
                len(values(failed_storage, "cleanup_restore")) == 1 and
            values(failed_storage, "cleanup_restore")[0]["enabled"] is False,
            "Preserved zero-RF storage observer failure")

    retry_packet = load(current / "storage-retry-packet.json")
    require(digest(current / "storage-retry-packet.json") == RETRY_PACKET and
            retry_packet["prior_attempt"]["rf_jobs"] == 0 and
            retry_packet["limits"] == {"rf_jobs": 1,
                "rf_duration_ns": 110_592_000_000, "loads": 0, "arm": 0,
                "time_commands": 0, "configuration_writes": 2,
                "controlled_reboots": 1, "flashes": 0, "bootsel": 0,
                "wifi_cycles": 0},
            "Bounded Package 8 storage retry packet")
    retry_rows = rows(current / "storage-retry.jsonl")
    retry_states = values(retry_rows, "retry_usb_status")
    counts = {state: sum(item["state"] == state for item in retry_states)
              for state in ("empty", "armed", "running", "complete")}
    result = load(current / "storage-result.json")
    http = values(retry_rows, "http")
    network_sessions = values(retry_rows, "network_connect")
    network_messages = values(retry_rows, "network_message")
    exchanges = console_exchanges(retry_rows)
    busy = [item for item in exchanges if item["command"].startswith("CONFIG ")]
    storage_reads = [item["response"]["config"] for item in exchanges
                     if item["command"] == "STORAGE"]
    require(counts == {"empty": 1547, "armed": 21, "running": 462, "complete": 1} and
            all(item["output_active"] for item in retry_states if item["state"] == "running") and
            not any(item["output_active"] for item in retry_states
                    if item["state"] != "running") and
            [(item["method"], item["path"], item["status"]) for item in http] == [
                ("GET", "/api/v1/config", 200), ("PUT", "/api/v1/config", 200),
                ("POST", "/api/v1/restart", 202), ("GET", "/api/v1/status", 200),
                ("GET", "/api/v1/status", 200), ("GET", "/api/v1/config", 200),
                ("PUT", "/api/v1/config", 200)] and
            [item["session"] for item in network_sessions] ==
                [retry_packet["armed_network_session"], retry_packet["running_network_session"]] and
            [(item.get("op"), item.get("body", {}).get("state"))
             for item in network_messages if item.get("op") == "STATUS"] ==
                [("STATUS", "armed"), ("STATUS", "running")] and
            len(busy) == 1 and busy[0]["response"] == {"ok": False, "error": "busy"} and
            storage_reads == [{"sequence": "70", "latest_offset": 2048,
                               "record_size": 2048},
                              {"sequence": "71", "latest_offset": 4096,
                               "record_size": 2048},
                              {"sequence": "71", "latest_offset": 4096,
                               "record_size": 2048},
                              {"sequence": "71", "latest_offset": 4096,
                               "record_size": 2048},
                              {"sequence": "72", "latest_offset": 6144,
                               "record_size": 2048}],
            "Package 8 autonomous cross-transport observations")
    require(result["status"] == "accepted" and result["prior_boot_id"] == FAILED_STORAGE_BOOT and
            result["boot_id"] == FINAL_BOOT and result["owner_id"] == LOCAL_OWNER and
            result["planned_duration_ns"] == 110_592_000_000 and
            result["unsynchronized_observation"]["clock_state"] == "unsynchronized" and
            result["unsynchronized_observation"]["state"] == "empty" and
            result["synchronized_observation"]["clock_state"] == "synchronized" and
            result["storage_before"] == {"sequence": "70", "latest_offset": 2048,
                                          "record_size": 2048} and
            result["storage_rotated"] == {"sequence": "71", "latest_offset": 4096,
                                           "record_size": 2048} and
            result["storage_restored"] == {"sequence": "72", "latest_offset": 6144,
                                            "record_size": 2048} and
            result["terminal"] == {"job_id": result["job_id"], "state": "complete",
                "ended_monotonic_ns": result["terminal"]["ended_monotonic_ns"],
                "output_active": False} and
            result["final_status"]["enabled"] is False and
            result["final_status"]["suspended"] is False and
            result["final_status"]["output_active"] is False and
            result["final_status"]["watermark_utc_ns"] == result["occurrence_utc_ns"] and
            result["final_status"]["schedule_base_frequency_nhz"] == BASE_NHZ,
            "Package 8 autonomous result and restoration")

    parent_release = load(current / "storage-retry-parent-reservation-released.json")
    acquired = load(current / "storage-retry-reservation-acquired.json")
    released = load(current / "storage-retry-reservation-released.json")
    require(parent_release["state"] == "RELEASED" and
            parent_release["packet_sha256"] == PARENT_PACKET and
            parent_release["boards"]["a"]["boot_id"] == FAILED_STORAGE_BOOT and
            acquired["state"] == "HELD" and acquired["packet_sha256"] == RETRY_PACKET and
            released["state"] == "RELEASED" and released["packet_sha256"] == RETRY_PACKET and
            released["boards"]["a"]["boot_id"] == FINAL_BOOT and
            released["boards"]["b"]["boot_id"] == B_BOOT,
            "Package 8 reservation chain")

    final_a = inventory(current / "storage-retry-final-a.stdout")
    final_b = inventory(current / "storage-retry-final-b.stdout")
    require(final_a == {"device_id": DEVICE, "revision": SOURCE[:12], "boot_id": FINAL_BOOT,
                        "state": "complete", "output_active": False, "enabled": False} and
            final_b == {"device_id": B_DEVICE, "revision": "8921a7008183", "boot_id": B_BOOT,
                        "state": "empty", "output_active": False, "enabled": False},
            "Package 8 final A/B inventories")
    fixture = load(current / "fixture-state.json")
    cleanup = values(fixture_rows, "cleanup")
    before = fixture["before"]
    restored = values(fixture_rows, "host_restored")
    require(fixture["restored"] is True and len(cleanup) == 1 and cleanup[0]["failures"] == [] and
            len(restored) == 1 and restored[0] == before and
            "0 packets dropped by kernel" in (current / "capture-ap.log").read_text() and
            "0 packets dropped by kernel" in (current / "capture-client.log").read_text(),
            "Package 8 host/fixture restoration")

    hashes = {name: digest(evidence / name) for name in EVIDENCE_SHA256}
    require(hashes == EVIDENCE_SHA256, "Package 8 exact raw evidence hashes")
    return {
        "schema": "phase11.5-package8-result-v1",
        "status": "PACKAGE8_COMPLETE_R5_CLOSED",
        "phase11_5_status": "OPEN_5_OF_6_FAMILIES",
        "accepted_configuration": None,
        "family_status": {"R1": "CLOSED", "R2": "CLOSED", "R3": "CLOSED",
                          "R4": "CLOSED", "R5": "CLOSED", "R6": "OPEN"},
        "accepted_rows": ROWS,
        "candidate": {"source_revision": SOURCE, "image_sha256": IMAGE,
                      "device_id": DEVICE, "initial_boot_id": DEPLOYED_BOOT,
                      "final_boot_id": FINAL_BOOT, "system_clock_hz": 138_000_000,
                      "engine": "pio-dma-gp2", "renderer": "ram",
                      "schedule_base_frequency_nhz": BASE_NHZ},
        "network": {"job_id": network["job_id"], "owner_id": network["owner_id"],
                    "running_usb_samples": 1047, "planned_duration_ns": 240_000_000_000,
                    "address_change": ["10.77.15.10", "10.77.15.20"],
                    "external_link_loss_seconds": 15, "native_resolutions": 2,
                    "sntp_accepted": 8, "sntp_rejected": 0,
                    "https_status": 200, "terminal": "complete"},
        "storage_and_autonomy": {"job_id": result["job_id"],
                    "owner_id": LOCAL_OWNER, "planned_duration_ns": 110_592_000_000,
                    "usb_samples": counts, "clock_gate": ["unsynchronized", "synchronized"],
                    "journal_sequences": ["70", "71", "72"],
                    "running_config": "busy/no-write", "network_states": ["armed", "running"],
                    "terminal": "complete", "watermark_utc_ns": result["occurrence_utc_ns"],
                    "restored_enabled": False, "restored_suspended": False},
        "budget": {"rf_jobs": 3, "planned_rf_duration_ns": 590_592_000_000,
                   "configuration_writes": 4, "controlled_reboots": 2,
                   "flashes": 2, "bootsel": 2, "direct_loads_in_storage": 0,
                   "direct_arms_in_storage": 0, "time_commands": 0,
                   "wifi_cycles": 0, "deployments": deployments},
        "failed_attempts": {
            "pre_claim_harness_packet_sha256": digest(old / "network-attempt1-packet.json"),
            "address_recovery_packet_sha256": digest(old / "packet.json"),
            "address_recovery_log_sha256": digest(old / "network-run-attempt2.jsonl"),
            "storage_observer_log_sha256": digest(current / "storage-run.jsonl"),
            "storage_observer_rf_jobs": 0},
        "source_impact": {"prior_candidate":
                "2b25ca05c270819466a04498f9bc4894a4c5bace",
                "changed_files": PRODUCTION_CHANGES, "diff_sha256": SOURCE_DIFF_SHA256,
                "decision": "R1-R4 remain applicable; Package 8 directly covers the new "
                            "scheduler/storage diagnostics and network reconnect state. RF "
                            "renderer, WTP authority, protocol limits and timing are unchanged.",
                "later_pico_runtime_source_changes": 0},
        "restoration": {"pico_a_inactive": True, "pico_a_schedule_disabled": True,
                        "pico_b_unchanged_inactive": True, "reservation_released": True,
                        "host_fixture_restored": True, "capture_drops": 0},
        "raw_evidence_archive_sha256": ARCHIVE_SHA256,
        "evidence_sha256": hashes,
    }


def validate_result(value):
    require(value.get("schema") == "phase11.5-package8-result-v1" and
            value.get("status") == "PACKAGE8_COMPLETE_R5_CLOSED" and
            value.get("phase11_5_status") == "OPEN_5_OF_6_FAMILIES" and
            value.get("accepted_configuration") is None,
            "Package 8 closure status")
    require(value.get("family_status") == {"R1": "CLOSED", "R2": "CLOSED",
            "R3": "CLOSED", "R4": "CLOSED", "R5": "CLOSED", "R6": "OPEN"} and
            value.get("accepted_rows") == ROWS and len(set(value["accepted_rows"])) == 8,
            "Package 8 family/row closure")
    require(value.get("candidate") == {"source_revision": SOURCE, "image_sha256": IMAGE,
            "device_id": DEVICE, "initial_boot_id": DEPLOYED_BOOT,
            "final_boot_id": FINAL_BOOT, "system_clock_hz": 138_000_000,
            "engine": "pio-dma-gp2", "renderer": "ram",
            "schedule_base_frequency_nhz": BASE_NHZ}, "Package 8 candidate identity")
    require(value.get("network") == {
            "job_id": "f0c02c551ced8fe0b300e3e0b0289d08",
            "owner_id": "8c098429aa70df60f52d0f56ba3ea4eb",
            "running_usb_samples": 1047, "planned_duration_ns": 240_000_000_000,
            "address_change": ["10.77.15.10", "10.77.15.20"],
            "external_link_loss_seconds": 15, "native_resolutions": 2,
            "sntp_accepted": 8, "sntp_rejected": 0,
            "https_status": 200, "terminal": "complete"},
            "Package 8 network result")
    storage = value.get("storage_and_autonomy", {})
    require(storage.get("job_id") == "eeeeeeeeeeeeeeee18d5f6c6e1afea00" and
            storage.get("owner_id") == LOCAL_OWNER and
            storage.get("planned_duration_ns") == 110_592_000_000 and
            storage.get("usb_samples") == {"empty": 1547, "armed": 21,
                                            "running": 462, "complete": 1} and
            storage.get("clock_gate") == ["unsynchronized", "synchronized"] and
            storage.get("journal_sequences") == ["70", "71", "72"] and
            storage.get("running_config") == "busy/no-write" and
            storage.get("network_states") == ["armed", "running"] and
            storage.get("terminal") == "complete" and
            storage.get("watermark_utc_ns") == "1789607761000000000" and
            storage.get("restored_enabled") is storage.get("restored_suspended") is False,
            "Package 8 storage/autonomy result")
    budget = value.get("budget", {})
    require({key: budget.get(key) for key in ("rf_jobs", "planned_rf_duration_ns",
            "configuration_writes", "controlled_reboots", "flashes", "bootsel",
            "direct_loads_in_storage", "direct_arms_in_storage", "time_commands",
            "wifi_cycles")} == {"rf_jobs": 3, "planned_rf_duration_ns": 590_592_000_000,
            "configuration_writes": 4, "controlled_reboots": 2, "flashes": 2,
            "bootsel": 2, "direct_loads_in_storage": 0, "direct_arms_in_storage": 0,
            "time_commands": 0, "wifi_cycles": 0} and
            budget.get("deployments") == [{
                "packet_sha256":
                    "27b87b496585bb80371dee8302851bd813db2228e71b4bbdc9b9781fac7c5160",
                "source_revision": "71d8f5b174d227ec4ecbbfbda594b5edc19a7313",
                "image_sha256":
                    "9ec4b084822dc5d6bf54bac3798ea178051162d5aea45b83255503eee681cbd7",
                "boot_id": "3609966a45a282631fb9e38884724d25",
                "flashes": 1, "bootsel": 1}, {
                "packet_sha256":
                    "45cdcb5c276498b5720a8745b0c8b76af255ad967ebb63445919f1b4d2c28324",
                "source_revision": SOURCE, "image_sha256": IMAGE,
                "boot_id": DEPLOYED_BOOT, "flashes": 1, "bootsel": 1}],
            "Package 8 aggregate budget")
    failures = value.get("failed_attempts", {})
    require(failures == {
            "pre_claim_harness_packet_sha256":
                "44918000c592b5348179fbafb5d96432efd2a577f6c1f5b3b9d7fcf8e853724d",
            "address_recovery_packet_sha256":
                "7248629e1c08d45571598f101da4f3687ea062680a4ed86e9e2ea2e6c9a6a5e3",
            "address_recovery_log_sha256":
                "2edfc16623899402c2e552494ed233767e1d465ef2e92193d1cf9983cf6fcc68",
            "storage_observer_log_sha256":
                "1766ba75586a637d38fe4979fb0646ff9321535e43381b6233f71bc27113943c",
            "storage_observer_rf_jobs": 0},
            "Package 8 failure preservation")
    impact = value.get("source_impact", {})
    require(impact == {"prior_candidate":
                "2b25ca05c270819466a04498f9bc4894a4c5bace",
                "changed_files": PRODUCTION_CHANGES, "diff_sha256": SOURCE_DIFF_SHA256,
                "decision": "R1-R4 remain applicable; Package 8 directly covers the new "
                            "scheduler/storage diagnostics and network reconnect state. RF "
                            "renderer, WTP authority, protocol limits and timing are unchanged.",
                "later_pico_runtime_source_changes": 0},
            "Package 8 source-impact decision")
    require(value.get("restoration") == {"pico_a_inactive": True,
            "pico_a_schedule_disabled": True, "pico_b_unchanged_inactive": True,
            "reservation_released": True, "host_fixture_restored": True,
            "capture_drops": 0} and
            value.get("raw_evidence_archive_sha256") == ARCHIVE_SHA256 and
            value.get("evidence_sha256") == EVIDENCE_SHA256,
            "Package 8 restoration/evidence identity")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if args.result:
        print(json.dumps(validate_result(load(args.result)), indent=2))
        return
    require(args.evidence is not None and args.archive is not None,
            "Raw audit requires --evidence and --archive")
    print(json.dumps(audit_raw(args.evidence, args.archive, args.repo), indent=2))


if __name__ == "__main__":
    main()
