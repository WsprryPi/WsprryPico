#!/usr/bin/env python3
"""Validate the published Package 11 Retry 1 stopped-attempt result."""

import argparse
import json
from pathlib import Path

from phase11_5_inventory import require


PACKET_SHA256 = "cc3bf2c66075112bccc93557173f256541c6fcecea9637972ada6e55312cec0a"
DEPENDENCIES = {
    "admission_result_sha256": "fe4d7a9b84ec97f256b09f187005399685d0aefd556b129648608ea2a4cb1214",
    "admission_adversarial_sha256": "2b9e18c73cc7f53572f086b44c2d1fef9835009b129cb4b30c8b0c5db6317935",
    "attempt1_result_sha256": "0bef1850d736535661e2c0ae1bc7519dbff2cfbf06ebacf1c64108b4831b6faf",
    "clock_poll_retest_result_sha256": "92838e20c1de3a998bda67084f75b8deb728049633598ab9e2b5b18b2606fa68",
}
EVIDENCE = {
    "packet.json": PACKET_SHA256,
    "campaign.jsonl": "a7b2303dffa97dbdd06b3fb2a5907c806d91afa02cc659ab6d74dd7165e100ef",
    "campaign.pcap": "1829039dd6f0098bc8aa8d754c984a50b1cff946b340e4b0322ab216b5455f36",
    "production-1.log": "f87f2a02c5c6deefc3451d36c96ba52b14320a7ce7e1488ceb9a7ba72100ad24",
    "production-1.ini": "a60b01a3a6450564365b5ffb95538cc69befd5fbc5e360d207814154691f9e02",
    "production-1-tls.bin": "f8525d4e0d65032c0a1c9170d0fa6f0edb8ad94a8b8d1c660f521f0a6cc7ce42",
    "reconcile-a.jsonl": "7a263b949a5f2bfb1f385ca58f34c2569df7bb401effc0d4315b29794afac1cd",
    "reconcile-b.jsonl": "2aaf32cd186cb50ccab7e612924b31999f66707a653a02152e9c0796472811b6",
    "reconciliation-result.json": "6ce1329b7d89e062ecce2b9182366dd06d350758d362bbd142e82ed780c77eca",
    "fixture-state.json": "d96b27f1e1ddd3cd19308e9c1dd295e462ba93955f5ce530b858cd89810d3704",
    "fixture.jsonl": "da6c4edfd1b37e97bb646e302cd7991fb8243a499bd8c38e709ff866737056b2",
    "capture-client.pcap": "94da77b880c53e6a037191c325546de02eec3bf3d9a22c3d3b60209679b1d9db",
    "remote-packet.json": "d93a0c99f3c657f7a51d132ce83f9836c9d2a3d5c1b990b5d067aa64778d3869",
    "remote-ready.json": "6cfda5b97877f39095c7f7ed80056c3b0cf40ff936b8cf15bb74a264a6a5361a",
    "remote-state.json": "b2031c99bd260146d35c43200b0f1cfa1c04b402c169cf356582305e739ce20f",
    "remote.jsonl": "2982859b6d91dc942fd578c83b10987ff01bf210054c8192ad97963c5b9c9ec9",
    "remote-capture.pcap": "88ab294b9e76a84ac60c2935c24c8161b6e55ab454aede5423556cbd3e1a2a6e",
}


def sha256(value):
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value)


def validate_result(value):
    require(value.get("schema") == "phase11.5-package11-retry1-failure-v1" and
            value.get("status") == "STOPPED_PRE_ARM_WSPRRYPI_TLS_CREDENTIAL_OWNER" and
            value.get("phase11_5_status") == "OPEN_5_OF_6_FAMILIES" and
            value.get("packet_sha256") == PACKET_SHA256 and
            value.get("authorization") == "PACKAGE11-TWO-HOST-R6-RETRY1",
            "Retry 1 failure identity")
    dependencies = value.get("dependencies", {})
    require(dependencies == DEPENDENCIES,
            "Retry 1 dependency hashes")
    completed = value.get("completed_scope", {})
    require(completed.get("clock_poll_repair_observed") is True and
            completed.get("warmup_jobs") == 8 and
            completed.get("warmup_rf_duration_ns") == 8_000_000_000 and
            completed.get("production_class_records") == 3 and
            completed.get("maximum_class_records") == 5 and
            completed.get("production_adjustment_sha256") ==
                "9376f7feb101e33b690f2086ae165b4a7cbfc084fd7bc0a82c88afa81b845776" and
            completed.get("maximum_adjustment_sha256") ==
                "d2c61a738d93e6bb1f16dd4129dd9b48b61e72a5d9c8d0a5fea2b89ab828e130" and
            completed.get("matched_baseline_seconds") == 360 and
            completed.get("matched_baseline_bytes") == 56_216 and
            completed.get("cycle_1_readiness_passed") is True and
            completed.get("cycle_1_normal_begin_observed") is True and
            completed.get("production_process_started") is True and
            completed.get("production_readiness_passed") is False and
            completed.get("production_arm_accepted") is False and
            completed.get("normal_cycles") == completed.get("post_n_windows") == 0 and
            completed.get("r6_credit") is False, "Retry 1 completed scope")
    timing = value.get("baseline_timing", {})
    require(timing.get("rf_max_service_gap_ns") == 2_166_000 and
            timing.get("max_refill_irq_to_ready_ns") == 2_157_000 and
            timing.get("acceptance_limit_ns") == 2_849_391 and
            timing.get("timing_gate_passed_at_baseline") is True and
            timing.get("resource_gate_accepted") is False,
            "Retry 1 baseline timing scope")
    failure = value.get("failure", {})
    require(failure.get("runner_message") == "Production exited before readiness" and
            failure.get("production_message") ==
                "TLS credentials require regular protected files; private key requires owner-only permissions" and
            failure.get("classification") == "HOST_FIXTURE_TOOLING_DEFECT" and
            failure.get("product_failure") is False and
            failure.get("resource_result_accepted") is False and
            failure.get("timing_result_accepted_for_r6") is False,
            "Retry 1 failure classification")
    budget = value.get("actual_budget", {})
    require(budget.get("authorized_rf_jobs") == 16 and
            budget.get("authorized_rf_duration_ns") == 480_000_000_000 and
            budget.get("planned_rf_duration_ns") == 356_800_000_000 and
            budget.get("charged_rf_jobs") == 8 and
            budget.get("charged_rf_duration_ns") == 8_000_000_000 and
            budget.get("production_jobs_armed") == 0 and
            all(budget.get(name) == 0 for name in ("flashes", "bootsel",
                "configuration_writes", "controlled_reboots", "wifi_cycles",
                "allocation_probes")) and
            budget.get("automatic_retry_authorized") is False,
            "Retry 1 finite accounting")
    cumulative = value.get("cumulative_package11_budget", {})
    require(cumulative == {"attempt1_charged_rf_jobs": 8,
            "attempt1_charged_rf_duration_ns": 8_000_000_000,
            "retry1_charged_rf_jobs": 8,
            "retry1_charged_rf_duration_ns": 8_000_000_000,
            "charged_rf_jobs": 16, "charged_rf_duration_ns": 16_000_000_000},
            "Retry 1 cumulative accounting")
    external = value.get("external_events", {})
    require(external.get("bohica_management_flaps_observed") is True and
            external.get("classification") == "EXTERNAL_TO_PICO_AND_RF_TEST" and
            external.get("used_as_product_evidence") is False and
            external.get("used_as_failure_cause") is False,
            "Retry 1 external-event boundary")
    require(value.get("capture") == {"campaign_kernel_drops": 0,
            "client_kernel_drops": 0, "remote_ap_kernel_drops": 0},
            "Retry 1 capture integrity")
    restoration = value.get("restoration", {})
    require(all(restoration.get(name) is True for name in (
                "pico_a_empty_unowned_inactive", "pico_a_boot_unchanged",
                "pico_b_empty_unowned_inactive", "pico_b_boot_unchanged",
                "reservation_released_after_fresh_reconciliation",
                "wspr5_fixture_restored", "wspr4_fixture_restored",
                "installed_service_active", "recovery_timers_active")) and
            restoration.get("cleanup_failures") == 0,
            "Retry 1 authoritative restoration")
    evidence = value.get("evidence_sha256", {})
    require(evidence == EVIDENCE,
            "Retry 1 evidence hashes")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    validate_result(json.loads(args.result.read_text()))
    print("PASS")


if __name__ == "__main__":
    main()
