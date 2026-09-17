#!/usr/bin/env python3
"""Adversarially assess the sanitized Phase 11.5 Package 8 result."""

import argparse
import copy
import json
from pathlib import Path

from audit_phase11_5_package8 import validate_result


def assess(result):
    validate_result(result)
    mutations = {
        "schema": lambda value: value.update(schema="phase11.5-package8-v0"),
        "status": lambda value: value.update(status="PACKAGE8_INCOMPLETE"),
        "phase-count": lambda value: value.update(phase11_5_status="OPEN_4_OF_6_FAMILIES"),
        "accepted-configuration": lambda value: value.update(accepted_configuration={}),
        "family": lambda value: value["family_status"].update(R5="OPEN"),
        "row": lambda value: value["accepted_rows"].pop(),
        "row-order": lambda value: value["accepted_rows"].reverse(),
        "source": lambda value: value["candidate"].update(source_revision="0" * 40),
        "image": lambda value: value["candidate"].update(image_sha256="0" * 64),
        "device": lambda value: value["candidate"].update(device_id="0" * 32),
        "boot": lambda value: value["candidate"].update(final_boot_id="0" * 32),
        "clock": lambda value: value["candidate"].update(system_clock_hz=132_000_000),
        "engine": lambda value: value["candidate"].update(engine="stub"),
        "base-frequency": lambda value: value["candidate"].update(
            schedule_base_frequency_nhz="3570100000000000"),
        "network-job": lambda value: value["network"].update(job_id="0" * 32),
        "network-samples": lambda value: value["network"].update(running_usb_samples=1046),
        "network-address": lambda value: value["network"]["address_change"].pop(),
        "network-link": lambda value: value["network"].update(external_link_loss_seconds=14),
        "network-sntp": lambda value: value["network"].update(sntp_rejected=1),
        "network-terminal": lambda value: value["network"].update(terminal="aborted"),
        "storage-job": lambda value: value["storage_and_autonomy"].update(job_id="0" * 32),
        "storage-owner": lambda value: value["storage_and_autonomy"].update(owner_id="0" * 32),
        "storage-samples": lambda value: value["storage_and_autonomy"]["usb_samples"].update(
            running=461),
        "clock-gate": lambda value: value["storage_and_autonomy"]["clock_gate"].reverse(),
        "journal": lambda value: value["storage_and_autonomy"]["journal_sequences"].pop(),
        "busy-write": lambda value: value["storage_and_autonomy"].update(
            running_config="accepted"),
        "storage-network": lambda value: value["storage_and_autonomy"][
            "network_states"].pop(),
        "watermark": lambda value: value["storage_and_autonomy"].update(
            watermark_utc_ns="0"),
        "restored-suspend": lambda value: value["storage_and_autonomy"].update(
            restored_suspended=True),
        "rf-budget": lambda value: value["budget"].update(rf_jobs=4),
        "duration-budget": lambda value: value["budget"].update(
            planned_rf_duration_ns=590_592_000_001),
        "write-budget": lambda value: value["budget"].update(configuration_writes=3),
        "reboot-budget": lambda value: value["budget"].update(controlled_reboots=3),
        "storage-load": lambda value: value["budget"].update(direct_loads_in_storage=1),
        "deployment": lambda value: value["budget"]["deployments"][1].update(
            source_revision="0" * 40),
        "failed-preclaim": lambda value: value["failed_attempts"].update(
            pre_claim_harness_packet_sha256="0" * 64),
        "failed-network-log": lambda value: value["failed_attempts"].update(
            address_recovery_log_sha256="0" * 64),
        "failed-storage-rf": lambda value: value["failed_attempts"].update(
            storage_observer_rf_jobs=1),
        "impact-files": lambda value: value["source_impact"]["changed_files"].pop(),
        "impact-diff": lambda value: value["source_impact"].update(diff_sha256="0" * 64),
        "impact-decision": lambda value: value["source_impact"].update(
            decision="R1-R4 remain applicable"),
        "later-drift": lambda value: value["source_impact"].update(
            later_pico_runtime_source_changes=1),
        "restoration": lambda value: value["restoration"].update(
            host_fixture_restored=False),
        "capture-drops": lambda value: value["restoration"].update(capture_drops=1),
        "archive": lambda value: value.update(raw_evidence_archive_sha256="0" * 64),
        "evidence": lambda value: value["evidence_sha256"].update({
            "phase11-5-package8-repair-20260916/storage-result.json": "0" * 64}),
    }
    rejected = []
    for name, mutate in mutations.items():
        candidate = copy.deepcopy(result)
        mutate(candidate)
        try:
            validate_result(candidate)
        except (AssertionError, KeyError, TypeError, ValueError):
            rejected.append(name)
        else:
            raise AssertionError("Mutation survived: " + name)
    validate_result(result)
    return {"schema": "phase11.5-package8-adversarial-v1", "status": "PASS",
            "intact_result_before": "PASS", "mutations": len(mutations),
            "rejected": rejected, "intact_result_after": "PASS",
            "r5_closed": True, "phase11_5_status": "OPEN_5_OF_6"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(assess(json.loads(args.result.read_text())), indent=2))


if __name__ == "__main__":
    main()
