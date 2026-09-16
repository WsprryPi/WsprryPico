#!/usr/bin/env python3
"""Adversarially validate the complete Package 5 publication."""
import argparse
import copy
import json
from pathlib import Path

from phase11_5_inventory import require


SOURCE = "2b25ca05c270819466a04498f9bc4894a4c5bace"
IMAGE = "16698dd36ac4b919a93e56e948499462cbe41b1ca20c9b20007512339ff35a51"
BOOT = "80d558e5804547749eca849c53ba27e1"
NORMALIZER_PACKET = "78b7a9f3ffd412a405f2f4eac0811dc676d5168cbf7263a35331facb520fab23"
RECLAIM_PACKET = "b0829059d55f4e35890bfff6750202cddf357abed0bdcde3709160bf37415274"
EXPIRY_PACKET = "ffb41161d63745bee2f88fb6675d78e552a49f41edbd756bbcc6dd620bfb19f4"
LATE_PACKET = "0e959b66d071dc46eed76c0a8cfe9a5c95a3e2a72e06cc888671a807b2b0b79a"
CYCLE_PACKETS = [
    "05573ec4e23f1760d295a04b5c85eff67beb7d98bac79b4d2461ea5693c9ceae",
    "417ddd20bc663015e4b917c329cdb11eac300d761c49a6e8d5b30d7c19cc5b74",
    "e1e8428715bb03a4732499eb244a2629872647db23672ba2936073b07a7167cd",
]
NORMALIZER_ORDER = [
    "ba582b6091c432f0f3dab33cfc19d8a8",
    "5a529502c6dad01e28225663579a4346",
    "64f812a54255928f5b48261b2ca9913d",
    "1029f1aa4bfbf704e0a1e0cef4a9ef0e",
    "366e8f92cd6406e4743af30a6f46c76c",
    "7ad35b6dceec21d654e750b19b04be7a",
    "eab7b171aa091bea99214a2021057070",
    "c993678761becba86455e23b4c2bcf46",
]


def validate(value):
    require(value["schema"] == "phase11.5-package5-result-v2" and
            value["status"] == "PACKAGE5_COMPLETE" and
            (value["source_revision"], value["image_sha256"], value["boot_id"]) ==
            (SOURCE, IMAGE, BOOT), "Package 5 publication identity/status")
    require(value["assertions"] == {
        "R3.RETAINED.replay": "ACCEPTED",
        "R3.RETAINED.session": "ACCEPTED",
        "R3.RETAINED.terminal": "ACCEPTED",
        "R3.RECLAIM": "ACCEPTED",
    }, "Package 5 assertion disposition")

    retained = value["replay_session"]
    require(retained["maximum_sessions"] == 16 and retained["overflow_sessions"] == 1 and
            retained["replay_entries_per_session"] == 8 and
            retained["initial_quiet_seconds"] == retained["expiry_quiet_seconds"] == 360 and
            retained["core_cases"] == 34, "Retained replay/session result")

    terminal = value["terminal_capacity"]
    normalizer = terminal["normalizer"]
    require(normalizer["packet_sha256"] == NORMALIZER_PACKET and
            normalizer["status"] == "PACKAGE5_NORMALIZER_VERIFIED" and
            normalizer["jobs"] == 8 and normalizer["events_per_job"] == 512 and
            normalizer["duration_ns_per_job"] == 1_000_000_000 and
            normalizer["event_duration_ns"] == 1_953_125 and
            normalizer["frequencies_nhz"] == [135500000000000, 135495000000000] and
            normalizer["terminal_record_job_ids"] == NORMALIZER_ORDER and
            normalizer["terminal_record_state"] == "complete" and
            normalizer["quiet_seconds"] == 360 and normalizer["quiet_samples"] >= 13 and
            normalizer["allowed_quiet_operations"] == ["console-info", "host-health"] and
            normalizer["application_quiet_operations"] == 0 and
            normalizer["allocator_failures"] == normalizer["tls_allocation_failures"] == 0,
            "Normalizer workload/order/quiet result")

    expiry = terminal["expiry"]
    require(expiry["packet_sha256"] == EXPIRY_PACKET and
            expiry["status"] == "PACKAGE5_TERMINAL_EXPIRY_VERIFIED" and
            expiry["initial_records"] == expiry["expired_records"] == 8 and
            expiry["initial_record_state"] == "complete" and
            expiry["source_ttl_seconds"] == 3600 and expiry["quiet_seconds"] == 3660 and
            expiry["quiet_http_operations"] == expiry["quiet_status_operations"] == 0 and
            expiry["console_samples"] >= 120 and expiry["final_records"] == 0 and
            expiry["authenticated_recovery_deadline_ns"] == 15_000_000_000 and
            0 < expiry["authenticated_recovery_ns"] <=
            expiry["authenticated_recovery_deadline_ns"] and
            expiry["host_boot_id"] == "220e53ca-ca95-4206-9581-dbe28aa1eeb8" and
            expiry["host_throttled"] == "throttled=0x0",
            "Terminal expiry/traffic/recovery result")

    reclaim = value["reclamation"]
    require(reclaim["aggregate_packet_sha256"] == RECLAIM_PACKET and
            reclaim["status"] == "PACKAGE5_THREE_CYCLE_RECLAMATION_VERIFIED" and
            reclaim["selected_workload"] == "bounded-overload" and
            reclaim["load_response_deadline_ns"] == 5_000_000_000 and
            reclaim["post_quiet_seconds"] == 360 and
            reclaim["required_post_tolerance_bytes"] == 1024 and
            reclaim["normalized_live_bytes"] == 36840 and
            reclaim["post_live_bytes"] == [37088, 37080, 37088] and
            reclaim["maximum_post_difference_bytes"] == 8 and
            reclaim["maximum_post_difference_bytes"] <=
            reclaim["required_post_tolerance_bytes"] and
            reclaim["post_live_growth_monotonic"] is False and
            reclaim["observed_reserve_bytes"] >= reclaim["minimum_reserve_bytes"] == 32768 and
            reclaim["terminal_records_per_cycle"] == 8 and
            reclaim["terminal_record_state"] == "complete" and
            reclaim["terminal_order_bound"] is True and reclaim["stack_guards_valid"] is True and
            reclaim["allocator_failures"] == reclaim["tls_allocation_failures"] == 0 and
            reclaim["accepted"] is True, "Reclamation comparison/resource result")
    cycles = reclaim["cycles"]
    require(len(cycles) == 3 and [cycle["packet_sha256"] for cycle in cycles] == CYCLE_PACKETS and
            all(cycle["number"] == n and cycle["rf_duration_ns"] == 128_000_000_000 and
                0 < cycle["load_response_ns"] <= reclaim["load_response_deadline_ns"] and
                cycle["resident_wtp_bytes"] >= 32768 and cycle["http_status"] == 503 and
                cycle["http_error"] == "resource_exhausted" and
                cycle["authenticated_recovery"] is True and
                cycle["post_live_bytes"] == reclaim["post_live_bytes"][n - 1]
                for n, cycle in enumerate(cycles, 1)),
            "Three exact reclamation cycles")

    failures = {item["packet_sha256"]: item for item in value["failed_attempts"]}
    require(len(failures) == 4 and failures[LATE_PACKET]["load_response_ns"] == 7_666_404_382 and
            failures[LATE_PACKET]["load_response_ns"] > reclaim["load_response_deadline_ns"],
            "Historical failures retained")
    repair = value["repair"]
    require(repair["host_test_groups"] == 74 and repair["host_test_failures"] == 0 and
            repair["final_registered_ctest_groups"] == 75 and
            repair["final_registered_ctest_failures"] == 0,
            "Package 5 deterministic validation")
    charge = value["hardware_charge"]
    require(charge["continuation"] == dict(rf_jobs=11, rf_duration_ns=392_000_000_000,
            wifi_cycles=1, flashes=0, configuration_writes=0, controlled_reboots=0) and
            charge["total"] == dict(rf_jobs=24, rf_duration_ns=913_000_000_000,
            wifi_cycles=2, flashes=3, configuration_writes=0, controlled_reboots=0),
            "Package 5 hardware charge")
    restored = value["restoration"]
    require(restored["pico_a_last_authoritative_state"] == restored["pico_b_state"] == "empty" and
            restored["pico_a_last_authoritative_output_active"] is
            restored["pico_b_output_active"] is False and
            restored["pico_a_last_authoritative_owner_id"] is restored["pico_b_owner_id"] is None and
            restored["pico_a_final_terminal_records"] == 0 and
            restored["reservation_state"] == "RELEASED" and
            restored["fixture_cleanup_failures"] == [] and
            restored["host_interfaces_and_routes_restored"] is True and
            restored["temporary_namespace_present"] is False and
            restored["temporary_units_active"] == 0 and
            restored["wifi_recovery_timer_active"] is True and
            restored["installed_wsprrypi_pid"] == 1957,
            "Package 5 authority/reservation/restoration")
    require(value["remaining"] == ["Execute Package 6 assertion-level R3 closeout.",
            "Keep R3 and Phase 11.5 open until Package 6 passes."],
            "Package 5 completion boundary")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    original = json.loads(args.result.read_text())
    validate(original)
    mutations = {
        "identity": lambda v: v.update(source_revision="0" * 40),
        "normalizer-event-count": lambda v: v["terminal_capacity"]["normalizer"].update(
            events_per_job=511),
        "normalizer-duration": lambda v: v["terminal_capacity"]["normalizer"].update(
            duration_ns_per_job=999_999_999),
        "load-deadline": lambda v: v["reclamation"].update(load_response_deadline_ns=6_000_000_000),
        "quiet-duration": lambda v: v["reclamation"].update(post_quiet_seconds=359),
        "quiet-traffic": lambda v: v["terminal_capacity"]["expiry"].update(
            quiet_status_operations=1),
        "terminal-type": lambda v: v["terminal_capacity"]["normalizer"].update(
            terminal_record_state="aborted"),
        "terminal-order": lambda v: v["terminal_capacity"]["normalizer"]
            ["terminal_record_job_ids"].reverse(),
        "resident-wtp": lambda v: v["reclamation"]["cycles"][0].update(
            resident_wtp_bytes=32767),
        "http-outcome": lambda v: v["reclamation"]["cycles"][0].update(http_status=200),
        "recovery": lambda v: v["reclamation"]["cycles"][0].update(
            authenticated_recovery=False),
        "memory-comparison": lambda v: v["reclamation"].update(
            maximum_post_difference_bytes=1025),
        "expiry": lambda v: v["terminal_capacity"]["expiry"].update(final_records=1),
        "authority": lambda v: v["restoration"].update(pico_a_last_authoritative_state="running"),
        "reservation": lambda v: v["restoration"].update(reservation_state="HELD"),
        "restoration": lambda v: v["restoration"].update(
            host_interfaces_and_routes_restored=False),
        "hardware-charge": lambda v: v["hardware_charge"]["continuation"].update(rf_jobs=10),
        "failed-attempt": lambda v: v["failed_attempts"].pop(),
    }
    rejected = []
    for name, mutate in mutations.items():
        candidate = copy.deepcopy(original)
        mutate(candidate)
        try:
            validate(candidate)
        except (AssertionError, KeyError, TypeError, ValueError):
            rejected.append(name)
        else:
            raise AssertionError("Mutation survived: " + name)
    require(rejected == list(mutations), "Complete Package 5 mutation coverage")
    print(json.dumps(dict(schema="phase11.5-package5-adversarial-v2", status="PASS",
                          result_status=original["status"], mutations=len(mutations),
                          rejected=rejected, package5_complete=True), indent=2))


if __name__ == "__main__":
    main()
