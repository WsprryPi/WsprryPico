#!/usr/bin/env python3
"""Audit and publish the complete Package 11 corrected R6 campaign."""

import argparse
import hashlib
import json
from pathlib import Path

from phase11_5_inventory import require
import audit_phase11_5_package10 as package10_audit
import phase11_5_package10 as package10
import phase11_5_package11 as package11
from audit_phase11_5_package11_retry1_failure import validate_result as validate_retry1
from audit_phase11_5_package11_retry2_failure import validate_result as validate_retry2


FAMILY_STATUS = dict(package10_audit.FAMILY_STATUS)
FAMILY_STATUS["R6"] = "CLOSED with Package 11 two-host sustained mixed-operation evidence"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(root, packet_sha256, decoder, local_fixture, remote_fixture, reservation):
    packet = package11.validate(json.loads((root / "packet.json").read_text()))
    require(digest(root / "packet.json") == packet_sha256, "Package 11 packet hash")
    # The campaign and its gates are intentionally unchanged from Package 10.
    # Inject only the Package 11 packet validator, then independently extend the
    # result with the two-host and prior-admission evidence below.
    original = package10_audit.validate
    try:
        package10_audit.validate = package11.validate
        result = package10_audit.audit(root, packet_sha256, decoder, local_fixture,
                                       reservation)
    finally:
        package10_audit.validate = original
    local_state = json.loads((local_fixture / "fixture-state.json").read_text())
    local_rows = [json.loads(line) for line in
                  (local_fixture / "fixture.jsonl").read_text().splitlines()]
    verified = [row["value"] for row in local_rows if row["kind"] == "verified"]
    require(verified and all(
            "Connected to " + package11.REMOTE_AP_MAC in item["peer"]["link"]
            for item in verified) and
            local_state.get("restored") is True, "Package 11 remote client binding")
    remote_state = json.loads((remote_fixture / "remote-state.json").read_text())
    remote_rows = [json.loads(line) for line in
                   (remote_fixture / "remote.jsonl").read_text().splitlines()]
    remote_ready = json.loads((remote_fixture / "remote-ready.json").read_text())
    cleanup = [row for row in remote_rows if row["kind"] == "cleanup"]
    restored = [row for row in remote_rows if row["kind"] == "host_restored"]
    capture_rows = [json.loads(line) for line in
                    (remote_fixture / "capture.log").read_text().splitlines()
                    if line.startswith("{") and "kernel_drops" in line]
    require(remote_state.get("restored") is True and len(cleanup) == len(restored) == 1 and
            cleanup[0]["value"]["failures"] == [] and
            "192.168.1.68/24" in restored[0]["value"]["interfaces"] and
            remote_ready == packet["remote_ready"] and len(capture_rows) == 1 and
            capture_rows[0]["captured"] > 0 and capture_rows[0]["kernel_drops"] == 0,
            "Package 11 remote AP restoration/capture")
    admission_result = root / "admission-result.json"
    admission_adversarial = root / "admission-adversarial.json"
    prior_attempt = root / "prior-attempt-result.json"
    clock_poll_retest = root / "clock-poll-retest-result.json"
    retry1_result = root / "retry1-result.json"
    retry1_adversarial = root / "retry1-adversarial.json"
    credential_retest = root / "credential-retest-result.json"
    retry2_result = root / "retry2-result.json"
    retry2_adversarial = root / "retry2-adversarial.json"
    require(digest(admission_result) == packet["admission_result_sha256"] and
            digest(admission_adversarial) == packet["admission_adversarial_sha256"] and
            json.loads(admission_result.read_text())["status"] == "PASS_ZERO_RF" and
            json.loads(admission_adversarial.read_text())["status"] == "PASS",
            "Package 11 admission binding")
    prior_value = json.loads(prior_attempt.read_text())
    clock_value = json.loads(clock_poll_retest.read_text())
    retry1_value = json.loads(retry1_result.read_text())
    retry1_adversarial_value = json.loads(retry1_adversarial.read_text())
    credential_retest_value = json.loads(credential_retest.read_text())
    retry2_value = json.loads(retry2_result.read_text())
    retry2_adversarial_value = json.loads(retry2_adversarial.read_text())
    require(digest(prior_attempt) == packet["prior_attempt_result_sha256"] and
            prior_value["status"] == "STOPPED_PRE_CYCLE_CLOCK_POLL_ALIAS" and
            prior_value["actual_budget"]["charged_rf_jobs"] ==
                package11.ATTEMPT1_RF_JOBS and
            prior_value["actual_budget"]["charged_rf_duration_ns"] ==
                package11.ATTEMPT1_RF_DURATION_NS and
            prior_value["restoration"][
                "reservation_released_after_fresh_reconciliation"] is True,
            "Package 11 prior-attempt binding")
    require(digest(clock_poll_retest) == packet["clock_poll_retest_result_sha256"] and
            clock_value["status"] == "PASS_ZERO_RF" and
            clock_value["budget"]["rf_jobs"] == 0 and
            clock_value["budget"]["rf_duration_ns"] == 0 and
            clock_value["finding"]["fresh_pico_clock_window_observed"] is True and
            clock_value["restoration"]["reservation_released_unchanged"] is True,
            "Package 11 clock-poll repair binding")
    validate_retry1(retry1_value)
    require(digest(retry1_result) == packet["retry1_attempt_result_sha256"] and
            digest(retry1_adversarial) == packet["retry1_adversarial_sha256"] and
            retry1_adversarial_value["status"] == "PASS" and
            retry1_adversarial_value["all_mutations_rejected"] is True and
            retry1_adversarial_value["result_sha256"] == digest(retry1_result),
            "Package 11 Retry 1 stopped-attempt binding")
    require(digest(credential_retest) == packet["credential_retest_result_sha256"] and
            credential_retest_value["status"] == "PASS_ZERO_RF_HOST_ONLY" and
            credential_retest_value["files"] == 6 and
            credential_retest_value["content_hashes_unchanged"] is True and
            credential_retest_value["rf_jobs"] == 0 and
            credential_retest_value["pico_access"] is False,
            "Package 11 credential-repair retest binding")
    validate_retry2(retry2_value)
    require(digest(retry2_result) == packet["retry2_attempt_result_sha256"] and
            digest(retry2_adversarial) == packet["retry2_adversarial_sha256"] and
            retry2_adversarial_value["status"] == "PASS" and
            retry2_adversarial_value["all_mutations_rejected"] is True and
            retry2_adversarial_value["result_sha256"] == digest(retry2_result),
            "Package 11 Retry 2 stopped-attempt binding")
    campaign_rows = [json.loads(line) for line in
                     (root / "campaign.jsonl").read_text().splitlines()]
    retention_rows = [row["value"] for row in campaign_rows
                      if row["kind"] == "terminal_retention_preflight"]
    require(retention_rows and retention_rows[-1]["terminal_records"] == 0 and
            all(row["all_complete_output_inactive"] is True and
                0 <= row["terminal_records"] <= 8 for row in retention_rows),
            "Package 11 terminal-retention preflight evidence")
    result["schema"] = "phase11.5-package11-raw-audit-v1"
    result["package"] = 11
    result["two_host_fixture"] = {"ap_host": "wspr4", "ap_mac": package11.REMOTE_AP_MAC,
        "client_host": "wspr5", "client_mac": package11.CLIENT_MAC,
        "association_bssid": package11.REMOTE_AP_MAC, "channel": 11,
        "local_restored": True, "remote_restored": True}
    result["admission"] = {"result_sha256": digest(admission_result),
        "adversarial_sha256": digest(admission_adversarial), "status": "PASS_ZERO_RF"}
    result["prior_attempt"] = {"result_sha256": digest(prior_attempt),
        "status": prior_value["status"],
        "charged_rf_jobs": package11.ATTEMPT1_RF_JOBS,
        "charged_rf_duration_ns": package11.ATTEMPT1_RF_DURATION_NS,
        "resource_result_accepted": False}
    result["clock_poll_retest"] = {"result_sha256": digest(clock_poll_retest),
        "status": "PASS_ZERO_RF", "rf_jobs": 0, "rf_duration_ns": 0}
    result["retry1_attempt"] = {"result_sha256": digest(retry1_result),
        "adversarial_sha256": digest(retry1_adversarial),
        "status": retry1_value["status"],
        "charged_rf_jobs": package11.RETRY1_RF_JOBS,
        "charged_rf_duration_ns": package11.RETRY1_RF_DURATION_NS,
        "production_jobs_armed": 0, "resource_result_accepted": False}
    result["credential_retest"] = {"result_sha256": digest(credential_retest),
        "status": "PASS_ZERO_RF_HOST_ONLY", "files": 6, "rf_jobs": 0,
        "rf_duration_ns": 0}
    result["retry2_attempt"] = {"result_sha256": digest(retry2_result),
        "adversarial_sha256": digest(retry2_adversarial),
        "status": retry2_value["status"],
        "charged_rf_jobs": package11.RETRY2_RF_JOBS,
        "charged_rf_duration_ns": package11.RETRY2_RF_DURATION_NS,
        "reservation_acquired": False, "resource_result_accepted": False}
    result["terminal_retention_preflight"] = {"attempts": len(retention_rows),
        "initial_terminal_records": retention_rows[0]["terminal_records"],
        "final_terminal_records": retention_rows[-1]["terminal_records"],
        "threshold_unchanged_bytes": package10.package9.MINIMUM_PREFLIGHT_HEAP_AVAILABLE_BYTES}
    result["budget"] = {"authorized_rf_duration_ns": package11.AUTHORIZED_RF_DURATION_NS,
        "charged_rf_jobs": package10.RF_JOBS,
        "charged_rf_duration_ns": package10.RF_DURATION_NS,
        "unused_authorized_rf_duration_ns":
            package11.AUTHORIZED_RF_DURATION_NS - package10.RF_DURATION_NS,
        "prior_attempt_charged_rf_jobs": package11.ATTEMPT1_RF_JOBS,
        "prior_attempt_charged_rf_duration_ns": package11.ATTEMPT1_RF_DURATION_NS,
        "retry1_charged_rf_jobs": package11.RETRY1_RF_JOBS,
        "retry1_charged_rf_duration_ns": package11.RETRY1_RF_DURATION_NS,
        "retry2_charged_rf_jobs": package11.RETRY2_RF_JOBS,
        "retry2_charged_rf_duration_ns": package11.RETRY2_RF_DURATION_NS,
        "cumulative_package11_rf_jobs": package11.CUMULATIVE_RF_JOBS,
        "cumulative_package11_rf_duration_ns": package11.CUMULATIVE_RF_DURATION_NS,
        "flashes": 0, "bootsel": 0, "configuration_writes": 0,
        "controlled_reboots": 0, "wifi_cycles": 0, "allocation_probes": 0}
    result["evidence_sha256"]["remote/remote-state.json"] = digest(
        remote_fixture / "remote-state.json")
    result["evidence_sha256"]["remote/remote.jsonl"] = digest(
        remote_fixture / "remote.jsonl")
    result["evidence_sha256"]["remote/capture.pcap"] = digest(
        remote_fixture / "capture.pcap")
    result["evidence_sha256"]["remote/remote-ready.json"] = digest(
        remote_fixture / "remote-ready.json")
    result["evidence_sha256"]["prior-attempt-result.json"] = digest(prior_attempt)
    result["evidence_sha256"]["clock-poll-retest-result.json"] = digest(
        clock_poll_retest)
    result["evidence_sha256"]["retry1-result.json"] = digest(retry1_result)
    result["evidence_sha256"]["retry1-adversarial.json"] = digest(retry1_adversarial)
    result["evidence_sha256"]["credential-retest-result.json"] = digest(
        credential_retest)
    result["evidence_sha256"]["retry2-result.json"] = digest(retry2_result)
    result["evidence_sha256"]["retry2-adversarial.json"] = digest(
        retry2_adversarial)
    result["auditor_sha256"] = digest(Path(__file__))
    return result


def publication(raw, packet):
    return {"schema": "phase11.5-package11-result-v1",
        "status": "PACKAGE11_COMPLETE_R6_CLOSED",
        "phase11_5_status": "CLOSED_6_OF_6_FAMILIES",
        "family_status": FAMILY_STATUS,
        "accepted_configuration": {
            "board": "Pico A 0BF4B4AEC9FFB344", "device_id": package10.DEVICE,
            "source_revision": package10.SOURCE, "image_sha256": package10.IMAGE,
            "boot_id": package10.BOOT, "system_clock_hz": 138000000,
            "pio_divider": 1, "engine": "pio-dma-gp2", "renderer": "RAM",
            "rf_pin": "GP2", "schedule_base_frequency_nhz": "135500000000000",
            "network_listener": "configured"},
        "campaign": {"packet_sha256": raw["packet_sha256"],
            "normal_load_seconds": raw["normal_load_seconds"],
            "rf_jobs": raw["rf_jobs"], "planned_rf_duration_ns": raw["rf_duration_ns"],
            "warmup_jobs": raw["warmup_jobs"], "refresh_jobs": raw["refresh_jobs"],
            "production_jobs": len(raw["production_jobs"]),
            "browser_actions": raw["browser_actions"], "browser_gets": raw["browser_gets"],
            "resource_windows": len(raw["resource_windows"]),
            "matched_baseline_bytes": raw["matched_baseline_bytes"],
            "post_n_bytes": raw["post_n_bytes"], "final_q_bytes": raw["final_q_bytes"],
            "maximum_post_span_bytes": raw["maximum_post_span_bytes"],
            "monotonic_retained_growth": raw["monotonic_retained_growth"],
            "final_terminal_records": raw["final_terminal_records"],
            "terminal_class_cardinality": {"production": 3, "maximum": 5},
            "production_adjustment_sha256": raw["production_adjustment_sha256"],
            "maximum_adjustment_sha256": raw["maximum_adjustment_sha256"]},
        "diagnosis": {"package9_failure_preserved": True,
            "package10_fixture_blocker_preserved": True,
            "package11_attempt1_failure_preserved": True,
            "package11_retry1_failure_preserved": True,
            "package11_retry2_failure_preserved": True,
            "credential_owner_repair_zero_rf_verified": True,
            "clock_poll_repair_zero_rf_verified": True,
            "terminal_retention_preflight_verified": True,
            "cause": "inequivalent retained WTP replay-history classes",
            "firmware_memory_leak_found": False, "resource_limit_bytes": 1024,
            "protocol_retention_preserved": True},
        "fixture": {"zero_rf_admission": "PASS", "ap_host": "wspr4",
            "ap_mac": package11.REMOTE_AP_MAC, "client_host": "wspr5",
            "client_mac": package11.CLIENT_MAC, "channel": 11,
            "wspr4_restored": True, "wspr5_restored": True},
        "source_impact": {"deployed_candidate": package10.SOURCE,
            "repository_baseline_revision": "e22c86c83ceb161080c218748baf5d3eaa892652",
            "runtime_source_changes": 0,
            "decision": "measurement-only replay-history normalization",
            "wsprrypi_source_revision": package10.WSPRRYPI_SOURCE},
        "budget": raw["budget"],
        "restoration": {"pico_a_inactive": True, "pico_a_empty_unowned": True,
            "pico_b_unchanged_inactive": True, "reservation_released": True,
            "wspr5_fixture_restored": True, "wspr4_fixture_restored": True,
            "installed_service_active": True, "capture_drops": 0},
        "admission_result_sha256": packet["admission_result_sha256"],
        "admission_adversarial_sha256": packet["admission_adversarial_sha256"],
        "prior_attempt_result_sha256": packet["prior_attempt_result_sha256"],
        "clock_poll_retest_result_sha256": packet["clock_poll_retest_result_sha256"],
        "retry1_attempt_result_sha256": packet["retry1_attempt_result_sha256"],
        "retry1_adversarial_sha256": packet["retry1_adversarial_sha256"],
        "credential_retest_result_sha256": packet["credential_retest_result_sha256"],
        "retry2_attempt_result_sha256": packet["retry2_attempt_result_sha256"],
        "retry2_adversarial_sha256": packet["retry2_adversarial_sha256"],
        "raw_audit_sha256": hashlib.sha256(
            (json.dumps(raw, indent=2) + "\n").encode()).hexdigest(),
        "evidence_sha256": raw["evidence_sha256"]}


def validate_result(value):
    require(value.get("schema") == "phase11.5-package11-result-v1" and
            value.get("status") == "PACKAGE11_COMPLETE_R6_CLOSED" and
            value.get("phase11_5_status") == "CLOSED_6_OF_6_FAMILIES" and
            value.get("family_status") == FAMILY_STATUS,
            "Package 11 closure status")
    require(value.get("accepted_configuration") == {
        "board": "Pico A 0BF4B4AEC9FFB344", "device_id": package10.DEVICE,
        "source_revision": package10.SOURCE, "image_sha256": package10.IMAGE,
        "boot_id": package10.BOOT, "system_clock_hz": 138000000, "pio_divider": 1,
        "engine": "pio-dma-gp2", "renderer": "RAM", "rf_pin": "GP2",
        "schedule_base_frequency_nhz": "135500000000000",
        "network_listener": "configured"}, "Package 11 accepted configuration")
    campaign = value.get("campaign", {})
    require(isinstance(campaign.get("packet_sha256"), str) and
            len(campaign["packet_sha256"]) == 64 and
            campaign.get("normal_load_seconds") == 1800 and
            campaign.get("rf_jobs") == package10.RF_JOBS and
            campaign.get("planned_rf_duration_ns") == package10.RF_DURATION_NS and
            campaign.get("warmup_jobs") == 8 and campaign.get("refresh_jobs") == 5 and
            campaign.get("production_jobs") == 3 and
            campaign.get("browser_actions") == 48 and campaign.get("browser_gets") == 84 and
            campaign.get("resource_windows") == 5 and
            campaign.get("final_terminal_records") == 8 and
            campaign.get("terminal_class_cardinality") == {"production": 3, "maximum": 5} and
            isinstance(campaign.get("matched_baseline_bytes"), int) and
            isinstance(campaign.get("post_n_bytes"), list) and
            len(campaign["post_n_bytes"]) == 3 and
            isinstance(campaign.get("final_q_bytes"), int) and
            0 <= campaign.get("maximum_post_span_bytes", -1) <= 1024 and
            campaign.get("monotonic_retained_growth") is False and
            campaign.get("production_adjustment_sha256") !=
                campaign.get("maximum_adjustment_sha256"), "Package 11 campaign summary")
    baseline = campaign["matched_baseline_bytes"]
    require(all(abs(value_ - baseline) <= 1024 for value_ in
                campaign["post_n_bytes"] + [campaign["final_q_bytes"]]) and
            max(campaign["post_n_bytes"]) - min(campaign["post_n_bytes"]) ==
                campaign["maximum_post_span_bytes"] and
            not (campaign["post_n_bytes"][0] < campaign["post_n_bytes"][1] <
                 campaign["post_n_bytes"][2]), "Package 11 resource return")
    require(value.get("diagnosis") == {"package9_failure_preserved": True,
            "package10_fixture_blocker_preserved": True,
            "package11_attempt1_failure_preserved": True,
            "package11_retry1_failure_preserved": True,
            "package11_retry2_failure_preserved": True,
            "credential_owner_repair_zero_rf_verified": True,
            "clock_poll_repair_zero_rf_verified": True,
            "terminal_retention_preflight_verified": True,
            "cause": "inequivalent retained WTP replay-history classes",
            "firmware_memory_leak_found": False, "resource_limit_bytes": 1024,
            "protocol_retention_preserved": True}, "Package 11 diagnosis")
    require(value.get("fixture") == {"zero_rf_admission": "PASS", "ap_host": "wspr4",
            "ap_mac": package11.REMOTE_AP_MAC, "client_host": "wspr5",
            "client_mac": package11.CLIENT_MAC, "channel": 11,
            "wspr4_restored": True, "wspr5_restored": True},
            "Package 11 fixture")
    require(value.get("source_impact") == {"deployed_candidate": package10.SOURCE,
            "repository_baseline_revision": "e22c86c83ceb161080c218748baf5d3eaa892652",
            "runtime_source_changes": 0,
            "decision": "measurement-only replay-history normalization",
            "wsprrypi_source_revision": package10.WSPRRYPI_SOURCE},
            "Package 11 source impact")
    require(value.get("budget") == {"authorized_rf_duration_ns":
                package11.AUTHORIZED_RF_DURATION_NS,
            "charged_rf_jobs": package10.RF_JOBS,
            "charged_rf_duration_ns": package10.RF_DURATION_NS,
            "unused_authorized_rf_duration_ns":
                package11.AUTHORIZED_RF_DURATION_NS - package10.RF_DURATION_NS,
            "prior_attempt_charged_rf_jobs": package11.ATTEMPT1_RF_JOBS,
            "prior_attempt_charged_rf_duration_ns": package11.ATTEMPT1_RF_DURATION_NS,
            "retry1_charged_rf_jobs": package11.RETRY1_RF_JOBS,
            "retry1_charged_rf_duration_ns": package11.RETRY1_RF_DURATION_NS,
            "retry2_charged_rf_jobs": package11.RETRY2_RF_JOBS,
            "retry2_charged_rf_duration_ns": package11.RETRY2_RF_DURATION_NS,
            "cumulative_package11_rf_jobs": package11.CUMULATIVE_RF_JOBS,
            "cumulative_package11_rf_duration_ns": package11.CUMULATIVE_RF_DURATION_NS,
            "flashes": 0, "bootsel": 0, "configuration_writes": 0,
            "controlled_reboots": 0, "wifi_cycles": 0, "allocation_probes": 0},
            "Package 11 budget")
    require(value.get("restoration") == {"pico_a_inactive": True,
            "pico_a_empty_unowned": True, "pico_b_unchanged_inactive": True,
            "reservation_released": True, "wspr5_fixture_restored": True,
            "wspr4_fixture_restored": True, "installed_service_active": True,
            "capture_drops": 0}, "Package 11 restoration")
    require(value.get("admission_result_sha256") == package11.ADMISSION_RESULT_SHA256 and
            value.get("admission_adversarial_sha256") ==
                package11.ADMISSION_ADVERSARIAL_SHA256 and
            value.get("prior_attempt_result_sha256") ==
                package11.ATTEMPT1_RESULT_SHA256 and
            value.get("clock_poll_retest_result_sha256") ==
                package11.CLOCK_POLL_RETEST_RESULT_SHA256 and
            value.get("retry1_attempt_result_sha256") ==
                package11.RETRY1_RESULT_SHA256 and
            value.get("retry1_adversarial_sha256") ==
                package11.RETRY1_ADVERSARIAL_SHA256 and
            value.get("credential_retest_result_sha256") ==
                package11.CREDENTIAL_RETEST_RESULT_SHA256 and
            value.get("retry2_attempt_result_sha256") ==
                package11.RETRY2_RESULT_SHA256 and
            value.get("retry2_adversarial_sha256") ==
                package11.RETRY2_ADVERSARIAL_SHA256,
            "Package 11 exact dependency hashes")
    require(isinstance(value.get("raw_audit_sha256"), str) and
            len(value["raw_audit_sha256"]) == 64, "Package 11 raw audit hash")
    require(value.get("evidence_sha256") and all(isinstance(item, str) and len(item) == 64
            for item in value["evidence_sha256"].values()), "Package 11 evidence hashes")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--decoder", type=Path, required=True)
    parser.add_argument("--local-fixture", type=Path, required=True)
    parser.add_argument("--remote-fixture", type=Path, required=True)
    parser.add_argument("--reservation", type=Path,
                        default=Path("/home/pi/phase11-5-shared-rf-reservation.json"))
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--published-output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    raw = audit(root, args.packet_sha256, args.decoder.resolve(strict=True),
                args.local_fixture.resolve(strict=True),
                args.remote_fixture.resolve(strict=True),
                args.reservation.resolve(strict=True))
    raw_bytes = (json.dumps(raw, indent=2) + "\n").encode()
    args.raw_output.write_bytes(raw_bytes)
    packet = json.loads((root / "packet.json").read_text())
    published = publication(raw, packet)
    require(published["raw_audit_sha256"] == hashlib.sha256(raw_bytes).hexdigest(),
            "Package 11 raw publication binding")
    validate_result(published)
    args.published_output.write_text(json.dumps(published, indent=2) + "\n")
    print(json.dumps(published, indent=2))


if __name__ == "__main__":
    main()
