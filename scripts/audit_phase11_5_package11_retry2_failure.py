#!/usr/bin/env python3
"""Validate the published Package 11 Retry 2 stopped-attempt result."""

import argparse
import json
from pathlib import Path

from phase11_5_inventory import require


PACKET_SHA256 = "6408d93a0d7b990c0cb40b5bafb8bc6bfd650b187bfb975984783572c898a1fb"
DEPENDENCIES = {
    "admission_result_sha256": "fe4d7a9b84ec97f256b09f187005399685d0aefd556b129648608ea2a4cb1214",
    "admission_adversarial_sha256": "2b9e18c73cc7f53572f086b44c2d1fef9835009b129cb4b30c8b0c5db6317935",
    "attempt1_result_sha256": "0bef1850d736535661e2c0ae1bc7519dbff2cfbf06ebacf1c64108b4831b6faf",
    "clock_poll_retest_result_sha256": "92838e20c1de3a998bda67084f75b8deb728049633598ab9e2b5b18b2606fa68",
    "retry1_result_sha256": "89a7a1f26b2aa084187d08b24749bde22bec95476a20cddfe397a62f25d9d1a7",
    "retry1_adversarial_sha256": "f9c83b32542f0843ca262fcd041c5a8e89b96fcff526917008d50757d61e28b8",
    "credential_retest_result_sha256": "eda622ce6aac1b0d0cf2628dac179233138910628179f16a64f7c41ca2069238",
}
EVIDENCE = {
    "packet.json": PACKET_SHA256,
    "campaign.jsonl": "5b82d393569a704feb85b23a8abac6cc03967d30489b229110ef4fcf1314bb56",
    "fixture-state.json": "f02f0bda4a7a60d9f6fe3816501d62ec2e04edf995319985f14a22a44b294df2",
    "fixture.jsonl": "7a1d5638b845edf7223ac03e9ec3ba73af6e63186048aa844923b5ba254fa2e2",
    "capture-client.pcap": "4040748d2eba20522f630d01e526cd74f335e44b427ba160751fc2004378dabf",
    "capture-client.log": "29453eb85a312158f5d58320ff1a21d5901867f7b2046b7d5badeec857d9cc0a",
    "reconcile-a.jsonl": "2ffa0b84ed1d5103a7c3c68bb172ce5c08957c1fcf6d2364ff699c68eca601ae",
    "reconcile-b.jsonl": "1b6a75074f05b1bd8ed517836df6e976c0b298bd2bcf9a967ffd61373a9f59ad",
    "reservation.json": "ff8be730d13f9487b99652f6774055fb8bb963d49f220c990fb41697a28b62dd",
    "remote-packet.json": "74b0d5f4690db9bf8e66b6eee6a44f9e29a747da5f8271d98891522065e247f4",
    "remote-ready.json": "63be508de7b7b0662062e1f6123976d5271bdcba0a15eacccffd93c9306ae0d2",
    "remote-state.json": "4cb86ed0a11da2106630cebc13f985a30f0dbb7cbb035d34cd827012788b1467",
    "remote.jsonl": "a197d4a8e0c7688bae254c6087d1b039c2ef6a0c95a8a2268009b42150aecc91",
    "remote-capture.pcap": "cf6aaeb7dd82c7aa22f5e0196cbe9383347af0c1c5f97c64bf79fc76dbc64134",
    "remote-capture.log": "ae76bcd6d1f7bd2b5bc411c6241fb846ca98543ba494fbfb1747906ac13475b3",
}


def validate_result(value):
    require(value.get("schema") == "phase11.5-package11-retry2-failure-v1" and
            value.get("status") == "STOPPED_PRE_RESERVATION_MEMORY_RETENTION_WINDOW" and
            value.get("phase11_5_status") == "OPEN_5_OF_6_FAMILIES" and
            value.get("packet_sha256") == PACKET_SHA256 and
            value.get("authorization") == "PACKAGE11-TWO-HOST-R6-RETRY2",
            "Retry 2 failure identity")
    require(value.get("dependencies") == DEPENDENCIES, "Retry 2 dependency hashes")
    completed = value.get("completed_scope", {})
    require(completed == {"credential_repair_observed": True,
            "credential_files_verified": 6, "fixture_ready": True,
            "memory_preflight_attempts": 25, "reservation_acquired": False,
            "warmup_jobs": 0, "production_jobs": 0, "normal_cycles": 0,
            "post_n_windows": 0, "r6_credit": False},
            "Retry 2 completed scope")
    memory = value.get("memory_preflight", {})
    require(memory.get("timeout_seconds") == 360 and memory.get("sample_seconds") == 15 and
            memory.get("elapsed_ns") == 360_001_652_399 and
            memory.get("required_heap_available_bytes") == 165_000 and
            memory.get("minimum_observed_bytes") == 162_400 and
            memory.get("maximum_observed_bytes") == 164_800 and
            memory.get("final_observed_bytes") == 164_776 and
            memory.get("final_shortfall_bytes") == 224 and
            memory.get("allocator_failures") == 0 and
            memory.get("network_wtp_close_reasons") == [2] and
            memory.get("runner_type") == "ValueError" and
            memory.get("runner_message") == "Memory headroom readiness deadline",
            "Retry 2 memory preflight")
    retained = value.get("retained_state", {})
    require(retained.get("terminal_record_ttl_seconds") == 3600 and
            retained.get("retry1_reconciliation_terminal_records") == 8 and
            retained.get("retry2_reconciliation_terminal_records") == 4 and
            retained.get("retry2_reconciliation_monotonic_now_ns") == 44_520_235_518_000 and
            retained.get("latest_retained_terminal_ended_monotonic_ns") ==
                41_137_685_933_000 and
            retained.get("latest_retained_terminal_remaining_ns") == 217_450_415_000 and
            retained.get("all_observed_records_complete_and_output_inactive") is True and
            retained.get("classification") == "HOST_FIXTURE_PREFLIGHT_SEQUENCING_DEFECT" and
            retained.get("product_failure") is False and
            retained.get("resource_result_accepted") is False,
            "Retry 2 retained-state diagnosis")
    budget = value.get("actual_budget", {})
    require(budget.get("authorized_rf_jobs") == 16 and
            budget.get("authorized_rf_duration_ns") == 480_000_000_000 and
            budget.get("planned_rf_duration_ns") == 356_800_000_000 and
            budget.get("charged_rf_jobs") == budget.get("charged_rf_duration_ns") == 0 and
            all(budget.get(name) == 0 for name in ("flashes", "bootsel",
                "configuration_writes", "controlled_reboots", "wifi_cycles",
                "allocation_probes")) and budget.get("automatic_retry_authorized") is False,
            "Retry 2 finite accounting")
    require(value.get("cumulative_package11_budget") == {
            "attempt1_charged_rf_jobs": 8,
            "attempt1_charged_rf_duration_ns": 8_000_000_000,
            "retry1_charged_rf_jobs": 8,
            "retry1_charged_rf_duration_ns": 8_000_000_000,
            "retry2_charged_rf_jobs": 0, "retry2_charged_rf_duration_ns": 0,
            "charged_rf_jobs": 16, "charged_rf_duration_ns": 16_000_000_000},
            "Retry 2 cumulative accounting")
    require(value.get("capture") == {"campaign_capture_started": False,
            "campaign_kernel_drops": None, "client_kernel_drops": 0,
            "remote_ap_kernel_drops": 0}, "Retry 2 capture integrity")
    restoration = value.get("restoration", {})
    require(all(restoration.get(name) is True for name in (
                "pico_a_empty_unowned_inactive", "pico_a_boot_unchanged",
                "pico_b_empty_unowned_inactive", "pico_b_boot_unchanged",
                "reservation_remained_released", "wspr5_fixture_restored",
                "wspr4_fixture_restored", "installed_service_active",
                "recovery_timers_active")) and restoration.get("cleanup_failures") == 0,
            "Retry 2 authoritative restoration")
    require(value.get("evidence_sha256") == EVIDENCE, "Retry 2 evidence hashes")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    validate_result(json.loads(args.result.read_text()))
    print("PASS")


if __name__ == "__main__":
    main()
