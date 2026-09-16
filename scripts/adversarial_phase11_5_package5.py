#!/usr/bin/env python3
"""Adversarially validate the truthful partial Package 5 publication."""
import argparse
import copy
import json
from pathlib import Path

from phase11_5_inventory import require


SOURCE = "2b25ca05c270819466a04498f9bc4894a4c5bace"
IMAGE = "16698dd36ac4b919a93e56e948499462cbe41b1ca20c9b20007512339ff35a51"
BOOT = "80d558e5804547749eca849c53ba27e1"
LATE_PACKET = "0e959b66d071dc46eed76c0a8cfe9a5c95a3e2a72e06cc888671a807b2b0b79a"
RETAINED_PACKET = "2039a76c119c23ebd7cdf36e8052252e58b9fc4b5a7d3283b51018690c829ccc"
STATUS_PACKET = "df03ad86f412a0c6586c2a25075408b88d5439dc794ca119301a5e5ea6dd9e5b"
TERMINAL_PACKET = "ed7db2e3a386b47855b3bb5a06c19c3d65b3c8af1b0eee92a74cb769f5130149"
CYCLE_PACKETS = [
    "7878985c56b65df766e9fd717b59c44416ea96140b21002944981aa4e17736a8",
    "fc55afcf0efbdf236cb9472e5d6191b79ae700189c632f9111c22ce84969e730",
    "a536693b90e55cb9f3602d75ed42f6199178e1f0873bbad269071eb8f4ba3a6f",
]


def validate(value):
    require(value["schema"] == "phase11.5-package5-result-v1" and
            value["status"] == "PACKAGE5_OPEN" and
            (value["source_revision"], value["image_sha256"], value["boot_id"]) ==
            (SOURCE, IMAGE, BOOT), "Package 5 publication identity/status")
    require(value["assertions"] == {
        "R3.RETAINED.replay": "ACCEPTED",
        "R3.RETAINED.session": "ACCEPTED",
        "R3.RETAINED.terminal": "OPEN_EXPIRY_NOT_EXECUTED",
        "R3.RECLAIM": "OPEN_LIVE_MEMORY_COMPARISON_FAILED",
    }, "Package 5 assertion disposition")
    retained = value["replay_session"]
    require(retained["packet_sha256"] == RETAINED_PACKET and
            retained["status_confirmation_packet_sha256"] == STATUS_PACKET and
            retained["maximum_sessions"] == 16 and retained["overflow_sessions"] == 1 and
            retained["replay_entries_per_session"] == 8 and
            retained["initial_quiet_seconds"] == retained["expiry_quiet_seconds"] == 360 and
            retained["core_cases"] == 34,
            "Package 5 retained capacity/quiet evidence")
    terminal = value["terminal_capacity"]
    require(terminal["packet_sha256"] == TERMINAL_PACKET and
            terminal["status"] == "PACKAGE5_TERMINAL_CAPACITY_VERIFIED" and
            terminal["capacity"] == 8 and terminal["completed_jobs"] == 9 and
            terminal["rf_duration_ns"] == 9_000_000_000 and
            terminal["expiry_status"] == "NOT_RUN" and terminal["expiry_blocker"],
            "Package 5 terminal result/expiry boundary")
    reclaim = value["reclamation"]
    require(reclaim["required_post_tolerance_bytes"] == 1024 and
            reclaim["maximum_immediate_post_difference_bytes"] == 12384 and
            reclaim["post_live_bytes"] == [73008, 60624, 64480] and
            reclaim["post_live_growth_monotonic"] is False and
            reclaim["accepted"] is False and len(reclaim["functional_cycles"]) == 3,
            "Package 5 reclamation failure retained")
    require([cycle["packet_sha256"] for cycle in reclaim["functional_cycles"]] == CYCLE_PACKETS,
            "Package 5 functional cycle identities")
    require(all(cycle["audit_status"] == "P2_OVERLOAD_VERIFIED" and
                cycle["rf_duration_ns"] == 128_000_000_000 and
                cycle["resident_wtp_bytes"] >= 32768 and cycle["http_status"] == 503 and
                cycle["authenticated_recovery"] is True
                for cycle in reclaim["functional_cycles"]),
            "Package 5 functional cycle facts")
    failed = {item["packet_sha256"]: item for item in value["failed_attempts"]}
    require(len(failed) == 4 and LATE_PACKET in failed and
            failed[LATE_PACKET]["rf_duration_ns"] == 0 and
            failed[LATE_PACKET]["load_response_ns"] == 7_666_404_382 and
            failed[LATE_PACKET]["load_response_ns"] > 5_000_000_000,
            "Package 5 late response failure")
    require(value["repair"]["host_test_groups"] == 74 and
            value["repair"]["host_test_failures"] == 0 and
            value["repair"]["final_registered_ctest_groups"] == 68 and
            value["repair"]["final_registered_ctest_failures"] == 0 and
            value["deployment"]["flashes"] == 3 and
            value["deployment"]["accepted_status"] == "CORRECTIVE_RF_IMAGE_VERIFIED",
            "Package 5 repair/deployment result")
    charge = value["hardware_charge"]
    require(charge == dict(rf_jobs=13, rf_duration_ns=521_000_000_000,
                           wifi_cycles=1, flashes=3, configuration_writes=0,
                           controlled_reboots=0), "Package 5 hardware charge")
    restored = value["restoration"]
    require(restored["pico_a_state"] == restored["pico_b_state"] == "empty" and
            restored["pico_a_output_active"] is restored["pico_b_output_active"] is False and
            restored["pico_a_owner_id"] is restored["pico_b_owner_id"] is None and
            restored["reservation_state"] == "RELEASED" and
            restored["fixture_cleanup_failures"] == [] and
            restored["host_interfaces_and_routes_restored"] is True,
            "Package 5 restoration")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    original = json.loads(args.result.read_text())
    validate(original)
    mutations = {
        "source_identity": lambda v: v.update(source_revision="0" * 40),
        "replay_overclaim": lambda v: v["assertions"].update({"R3.RETAINED.replay": "OPEN"}),
        "terminal_expiry_overclaim": lambda v: v["assertions"].update(
            {"R3.RETAINED.terminal": "ACCEPTED"}),
        "reclamation_overclaim": lambda v: v["reclamation"].update(accepted=True),
        "reclamation_delta": lambda v: v["reclamation"].update(
            maximum_immediate_post_difference_bytes=1024),
        "late_response_hidden": lambda v: v["failed_attempts"].__setitem__(
            3, dict(v["failed_attempts"][3], load_response_ns=4_000_000_000)),
        "failed_packet_removed": lambda v: v["failed_attempts"].pop(),
        "hardware_charge_reduced": lambda v: v["hardware_charge"].update(rf_jobs=12),
        "reservation_not_released": lambda v: v["restoration"].update(
            reservation_state="HELD"),
        "fixture_failure_hidden": lambda v: v["restoration"].update(
            fixture_cleanup_failures=["hidden"]),
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
    print(json.dumps(dict(status="PACKAGE5_PARTIAL_ADVERSARIAL_VERIFIED",
                          result_status=original["status"], mutations=len(mutations),
                          rejected=rejected, package5_complete=False), indent=2))


if __name__ == "__main__":
    main()
