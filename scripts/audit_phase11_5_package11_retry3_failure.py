#!/usr/bin/env python3
"""Validate the published Package 11 Retry 3 stopped-attempt result."""

import argparse
import json
from pathlib import Path

from phase11_5_inventory import require


PACKET_SHA256 = "f2f0e684b658310038dd6b3a36b8b58ef285c1db6bd6fcbf05a9c4111b153dbd"
DEPENDENCIES = {
    "admission_result_sha256": "fe4d7a9b84ec97f256b09f187005399685d0aefd556b129648608ea2a4cb1214",
    "admission_adversarial_sha256": "2b9e18c73cc7f53572f086b44c2d1fef9835009b129cb4b30c8b0c5db6317935",
    "attempt1_result_sha256": "0bef1850d736535661e2c0ae1bc7519dbff2cfbf06ebacf1c64108b4831b6faf",
    "clock_poll_retest_result_sha256": "92838e20c1de3a998bda67084f75b8deb728049633598ab9e2b5b18b2606fa68",
    "retry1_result_sha256": "89a7a1f26b2aa084187d08b24749bde22bec95476a20cddfe397a62f25d9d1a7",
    "retry1_adversarial_sha256": "f9c83b32542f0843ca262fcd041c5a8e89b96fcff526917008d50757d61e28b8",
    "credential_retest_result_sha256": "b12474628bac9c07e93f86652f92f4c8dae47cb8464f00c06e93245e34aff59b",
    "retry2_result_sha256": "4f4eaf27cd1ad84a84d72b7669e4f72822c25402768d5acc20eb33cc7412c7e1",
    "retry2_adversarial_sha256": "717a3aea894f10ae28881a98bc67b4cb12208a972bb30e1515593fc69a7330c5",
}
EVIDENCE = {
    "packet.json": PACKET_SHA256,
    "campaign.jsonl": "e67f3d0e17b25425352f01070710a52a2be277e0e143f964991f01a4da587c76",
    "campaign.log": "160ed356f86e9ef69930f4be811cf1335200862fb0f5321770e70c5b7adc9f81",
    "campaign.pcap": "7a8d0cad87daba0bb588633e19c7cb9583dc0241666590f836d9ba60df8ded2f",
    "campaign-capture.log": "c355a1b249833faf1e516202cf2683cd877b539eb5d7d553a7d52f3daadc1af7",
    "fixture-state.json": "6c37ce1c0415f75a3f0cf32b250ad7a24db1d11cf8b753642428ff35eaffc258",
    "fixture.jsonl": "914ea2526b88cd7f8768b0634ed1144619a1b4862d179e42a4132c96456a4bf0",
    "capture-client.pcap": "b0334060c6362ad821eb4c23e40bdb9c905ea9dfda46e7cd02cc381df1dfc5b4",
    "capture-client.log": "6a9864d4262e153aa209732c710c30b96b99da90236bb1cf37ba8e49fcb3a9d9",
    "reconcile-a.jsonl": "83b5f8fadbf32400932c999ecb29b1cd0d203271ff91514833edfdc30cd801ce",
    "reconcile-b.jsonl": "5df8a1e50861834205b52068e4aac9c25f20fdd3d991f00299e92720e03cfedd",
    "reservation-reconciled-release.json":
        "fa1acadc148b31fa7b770ee7658edc0905b8aa0451952152a733e7fcebc59a50",
    "restored-a.jsonl": "3c567cbf92541c085b430ab6f0c59c65b1a94b643f5a42ecf3872f365b6d4505",
    "restored-b.jsonl": "65031e2040be08e9423de1cdfea1844ce114b37f1c8832222211f560f2015cd7",
    "production-1.ini": "6f4d1bd66c8ac6a0f6a38d5ec5ad291313e1d0cee150c31aadc6fe6753a52e97",
    "production-1.log": "3c096c47d74c0654334deac593729bf90ea42955e6cbfda0e47c9d3e7d02aac3",
    "production-1-tls.bin": "9378fff1851fe7608cbf1cb460de0e64605a2e5a39c1762210b67808bbd2afcb",
    "remote-ready.json": "6b31f27e035e07b181def1629886d41c7db60c15a865e45e625bb4e3a8a4897a",
    "remote-packet.json": "6fc9fe6f1a8b65676d79098e7cbe1325b329fa6e57fe91c934f09b4aff67b480",
    "remote-state.json": "6ebeecc634657d8735fbd86c15667200115fd4affad952aded70ce3411e018ca",
    "remote.jsonl": "01119410bbb8193b2a6babffc5b3ffa842d79e30cdabfe6c5b94c2f6b30766ca",
    "remote-capture.pcap": "22c5fe9c44f82076066ec8f886255a160065d124d9277cc6efc9c6e6cb8d4ed4",
    "remote-capture.log": "b36fe189c03e368c4be0aeec2144919df5e5303631e8b19e6532d6d2a43bc8ed",
}


def validate_result(value):
    require(value.get("schema") == "phase11.5-package11-retry3-failure-v1" and
            value.get("status") == "STOPPED_AFTER_CYCLE1_USB_EVENT_REDUCTION" and
            value.get("phase11_5_status") == "OPEN_5_OF_6_FAMILIES" and
            value.get("packet_sha256") == PACKET_SHA256 and
            value.get("authorization") == "PACKAGE11-TWO-HOST-R6-RETRY3" and
            value.get("dependencies") == DEPENDENCIES,
            "Retry 3 failure identity")
    require(value.get("completed_scope") == {
            "credential_files_verified": 6, "fixture_ready": True,
            "terminal_retention_attempts": 1, "terminal_retention_records": 0,
            "memory_preflight_attempts": 1, "memory_available_bytes": 193736,
            "memory_required_bytes": 165000, "reservation_acquired": True,
            "warmup_jobs": 8, "baseline_windows": 1, "baseline_seconds": 360,
            "production_jobs": 1, "normal_cycles": 1, "normal_seconds": 600,
            "post_n_windows": 0, "refresh_jobs": 0, "r6_credit": False},
            "Retry 3 completed scope")
    failure = value.get("failure", {})
    require(failure.get("sequence") == 38624 and
            failure.get("runner_type") == "ValueError" and
            failure.get("runner_message") == "USB lifecycle/cadence" and
            failure.get("usb_status_samples") == 120 and
            failure.get("usb_status_state_counts") ==
                {"empty": 95, "armed": 2, "running": 23} and
            failure.get("usb_event_count") == 6 and
            failure.get("usb_job_state_event_count") == 5 and
            failure.get("usb_event_states") ==
                ["armed", "complete", "empty", "loaded", "running"] and
            failure.get("minimum_status_gap_ns") == 4_999_961_309 and
            failure.get("maximum_status_gap_ns") == 5_000_065_331 and
            failure.get("maximum_status_response_ns") == 954_628_630 and
            failure.get("observer_failures") == failure.get("worker_failures") == 0 and
            failure.get("matching_terminal_complete_output_inactive") is True and
            failure.get("cycle1_native_report_complete") is True and
            failure.get("classification") == "HOST_HARNESS_EVENT_REDUCTION_DEFECT" and
            failure.get("product_failure") is False and
            failure.get("resource_result_accepted") is False,
            "Retry 3 failure diagnosis")
    repair = value.get("repair", {})
    require(repair.get("decision") ==
            "Preserve USB lifecycle events for transient states and require periodic STATUS plus its retained complete output-inactive terminal record for authority." and
            repair.get("host_only_retest_status") == "PASS_ZERO_RF_HOST_ONLY" and
            repair.get("host_only_retest_result_sha256") ==
                "9016f26d0f6d87c8743202cd2ffd4cba2be9473f6320c0e6f1064afe520f823b" and
            repair.get("host_only_retest_adversarial_sha256") ==
                "e88f8ab10c8ad16e6fe80ed77990e299be7b7be67cdf56534ace86af2c252868" and
            repair.get("adversarial_mutations_rejected") == 22 and
            repair.get("phase11_5_package9_source_sha256") ==
                "5d9b268b65f9dcc01c962217d620603c0a55363639dc03a14fbb2d55c3ca7a3c" and
            repair.get("fresh_rf_retest_required") is True,
            "Retry 3 repair evidence")
    require(value.get("actual_budget") == {
            "authorized_rf_jobs": 16, "authorized_rf_duration_ns": 480000000000,
            "planned_rf_duration_ns": 356800000000, "charged_rf_jobs": 9,
            "charged_rf_duration_ns": 122600000000,
            "unspent_authorized_rf_duration_ns": 357400000000,
            "flashes": 0, "bootsel": 0, "configuration_writes": 0,
            "controlled_reboots": 0, "wifi_cycles": 0, "allocation_probes": 0,
            "automatic_retry_authorized": False}, "Retry 3 finite accounting")
    require(value.get("cumulative_package11_budget") == {
            "attempt1_charged_rf_jobs": 8,
            "attempt1_charged_rf_duration_ns": 8000000000,
            "retry1_charged_rf_jobs": 8,
            "retry1_charged_rf_duration_ns": 8000000000,
            "retry2_charged_rf_jobs": 0, "retry2_charged_rf_duration_ns": 0,
            "retry3_charged_rf_jobs": 9,
            "retry3_charged_rf_duration_ns": 122600000000,
            "charged_rf_jobs": 25, "charged_rf_duration_ns": 138600000000},
            "Retry 3 cumulative accounting")
    require(value.get("capture") == {
            "campaign_capture_started": True, "campaign_captured": 9613,
            "campaign_received_by_filter": 9613, "campaign_kernel_drops": 0,
            "client_captured": 9740, "client_received_by_filter": 9740,
            "client_kernel_drops": 0, "remote_ap_captured": 9969,
            "remote_ap_kernel_packets": 9969, "remote_ap_kernel_drops": 0},
            "Retry 3 capture integrity")
    require(value.get("restoration") == {
            "pico_a_empty_unowned_inactive": True, "pico_a_boot_unchanged": True,
            "pico_a_terminal_records": 8,
            "pico_b_empty_unowned_inactive": True, "pico_b_boot_unchanged": True,
            "pico_b_terminal_records": 0, "reservation_reconciled_released": True,
            "wspr5_fixture_restored": True, "wspr4_fixture_restored": True,
            "installed_service_active": True, "recovery_timers_active": True,
            "cleanup_failures": 0}, "Retry 3 authoritative restoration")
    require(value.get("evidence_sha256") == EVIDENCE, "Retry 3 evidence hashes")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    validate_result(json.loads(args.result.read_text()))
    print("PASS")


if __name__ == "__main__":
    main()
