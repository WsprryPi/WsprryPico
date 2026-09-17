#!/usr/bin/env python3
"""Audit and sanitize the bounded-but-blocked Phase 11.5 Package 10 run."""

import argparse
import hashlib
import json
from pathlib import Path

from audit_phase11_5_package10 import validate_stopped_attempt
from phase11_5_inventory import require
from phase11_5_package10 import (AUTHORIZED_RF_DURATION_NS, BOOT, B_BOOT, B_DEVICE,
    B_SERIAL, DEVICE, IMAGE, PRIOR_ATTEMPT_PACKET_SHA256,
    PRIOR_ATTEMPT_RF_DURATION_NS, PRIOR_ATTEMPT_RF_JOBS, RF_DURATION_NS, RF_JOBS,
    SERIAL, SOURCE, WSPRRYPI_SOURCE, digest, validate)


B_REVISION = "8921a7008183"
ORIGINAL_ROLES = {"ap": "wlan0", "client": "wlan2",
                  "ap_mac": "2c:cf:67:62:76:66",
                  "client_mac": "e8:4e:06:ae:d7:09"}
SWAPPED_ROLES = {"ap": "wlan2", "client": "wlan0",
                 "ap_mac": "e8:4e:06:ae:d7:09",
                 "client_mac": "2c:cf:67:62:76:66"}
OUTCOMES = {
    2: "CLIENT_ASSOCIATION_FAILED",
    3: "CLIENT_ASSOCIATION_FAILED",
    4: "CLIENT_ASSOCIATION_FAILED",
    5: "CLIENT_ASSOCIATION_FAILED",
    6: "PICO_NETWORK_CLOCK_READINESS_TIMEOUT",
    7: "TLS_HANDSHAKE_STALL_INTERRUPTED",
    8: "MDNS_RESOLUTION_FAILED",
    9: "CLIENT_ASSOCIATION_FAILED",
    10: "WTP_READINESS_STALL_INTERRUPTED",
    11: "PICO_NETWORK_CLOCK_READINESS_TIMEOUT",
    12: "CLIENT_ASSOCIATION_FAILED",
    13: "SWAPPED_ROLE_CLIENT_ASSOCIATION_FAILED",
    14: "RESET_QUALIFIED_ROLE_CLIENT_ASSOCIATION_FAILED",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def finished(path):
    rows = jsonl(path)
    found = [row["value"] for row in rows if row.get("kind") == "finish"]
    require(len(found) == 1 and found[0].get("result") == "READ_ONLY_INVENTORY",
            "Final inventory incomplete")
    return found[0]


def role_from_source(root):
    source = (root / "scripts/phase11_5_network_fixture.py").read_text()
    if "AP_IF = 'wlan0'" in source and "CLIENT_IF = 'wlan2'" in source:
        return ORIGINAL_ROLES
    if "AP_IF = 'wlan2'" in source and "CLIENT_IF = 'wlan0'" in source:
        return SWAPPED_ROLES
    if ("'type', 'wifi', 'ifname', 'wlan0'" in source and
            "old.ROOT, old.CLIENT_IF = root, 'wlan2'" in source):
        return ORIGINAL_ROLES
    raise ValueError("Unknown fixture radio roles")


def audit_iteration(root, index):
    packet = json.loads((root / "packet.json").read_text())
    state = json.loads((root / "fixture-state.json").read_text())
    fixture = jsonl(root / "fixture.jsonl")
    cleanup = [row for row in fixture if row.get("kind") == "cleanup"]
    restored = [row for row in fixture if row.get("kind") == "host_restored"]
    require(state.get("restored") is True and cleanup and restored and
            cleanup[-1]["value"].get("failures") == [],
            "Corrected preflight was not restored")
    require(packet.get("source_revision") == SOURCE and
            packet.get("image_sha256") == IMAGE and packet.get("boot_id") == BOOT and
            packet.get("device_id") == DEVICE and
            packet.get("authorization") == "PACKAGE10-480-RF-SECONDS" and
            packet.get("configuration_writes") == 0 and
            packet.get("rf_jobs") == RF_JOBS and
            packet.get("rf_duration_ns") == RF_DURATION_NS,
            "Corrected preflight packet identity/budget")
    roles = role_from_source(root)
    if index >= 13:
        require(packet.get("network_fixture_roles") == roles,
                "Explicit final fixture roles")

    campaign_path = root / "campaign.jsonl"
    campaign = jsonl(campaign_path)
    kinds = [row.get("kind") for row in campaign]
    require(not set(kinds).intersection({"reservation_acquired", "capture_started",
            "normalizer_complete", "production_start", "normal_begin"}),
            "Corrected preflight reached RF-capable campaign work")
    ready = state.get("ready") is True
    log = (root / "client.log").read_text(errors="replace")
    outcome = OUTCOMES[index]
    if not ready:
        require(not (root / "client-ready").exists() and "AssertionError" in log and
                "CTRL-EVENT-CONNECTED" not in log and
                ("Trying to authenticate" in log or "Trying to associate" in log),
                "Association failure evidence")
    else:
        failures = [row for row in campaign if row.get("kind") == "failure"]
        require(len(failures) == 1 and failures[0] is campaign[-1],
                "Exact corrected readiness failure")
        failure = failures[0]["value"]
        if index in (6, 11):
            require(failure == {"type": "TimeoutError",
                    "error": "Normalizer network/clock readiness deadline"},
                    "Readiness timeout identity")
        elif index == 8:
            require(failure.get("type") == "gaierror" and
                    "Name or service not known" in failure.get("error", ""),
                    "mDNS failure identity")
        else:
            require(failure == {"type": "KeyboardInterrupt", "error": ""},
                    "Interrupted readiness identity")
            campaign_log = (root / "campaign.log").read_text(errors="replace")
            require((index == 7 and "do_handshake" in campaign_log) or
                    (index == 10 and "wait_for_normalizer_readiness" in campaign_log),
                    "Interrupted readiness stage")

    return {"iteration": index, "packet_sha256": sha(root / "packet.json"),
        "fixture_state_sha256": sha(root / "fixture-state.json"),
        "fixture_journal_sha256": sha(root / "fixture.jsonl"),
        "client_log_sha256": sha(root / "client.log"),
        "campaign_journal_sha256": sha(campaign_path) if campaign_path.exists() else None,
        "roles": roles, "fixture_ready": ready, "restored": True,
        "outcome": outcome}


def audit(root, history_parent, stopped_attempt_path, reservation_path):
    packet_path = root / "packet.json"
    packet_sha = sha(packet_path)
    packet = validate(json.loads(packet_path.read_text()))
    require(packet["network_fixture_roles"] == ORIGINAL_ROLES and
            packet_sha == "11c29234218383408394fcca61d3d9d21f5dc2e7f8c270e00d7c04a72606c75c" and
            not (root / "campaign.jsonl").exists() and
            not (root / "campaign-result.json").exists(),
            "Final corrected packet stopped before campaign")

    stopped = validate_stopped_attempt(json.loads(stopped_attempt_path.read_text()))
    history = [audit_iteration(history_parent /
        ("phase11-5-package10-v" + str(index) + "-20260917"), index)
        for index in range(2, 15)]
    require(sum(item["fixture_ready"] for item in history) == 5 and
            all(item["restored"] for item in history),
            "Corrected preflight history")

    final_a = finished(root / "final-blocked-a.jsonl")
    final_b = finished(root / "final-blocked-b.jsonl")
    a_status, b_status = final_a["wtp"]["STATUS"], final_b["wtp"]["STATUS"]
    require(final_a["info"]["device_id"] == DEVICE and
            final_a["info"]["revision"] == SOURCE[:12] and
            final_a["info"]["status"]["boot_id"] == BOOT and
            a_status["state"] == "empty" and a_status["owner_id"] is None and
            a_status["output_active"] is False and not a_status["terminal_records"],
            "Final blocked Pico A state")
    require(final_b["info"]["device_id"] == B_DEVICE and
            final_b["info"]["revision"] == B_REVISION and
            final_b["info"]["status"]["boot_id"] == B_BOOT and
            b_status["state"] == "empty" and b_status["owner_id"] is None and
            b_status["output_active"] is False and not b_status["terminal_records"],
            "Final blocked Pico B state")

    state = json.loads((root / "fixture-state.json").read_text())
    fixture = jsonl(root / "fixture.jsonl")
    cleanup = [row for row in fixture if row.get("kind") == "cleanup"]
    restored = [row for row in fixture if row.get("kind") == "host_restored"]
    require(state.get("restored") is True and state.get("ready") is not True and
            cleanup and cleanup[-1]["value"].get("failures") == [] and restored and
            str(restored[-1]["value"].get("installed_pid", "")).isdigit() and
            int(restored[-1]["value"]["installed_pid"]) > 0 and
            "10.77.15." not in restored[-1]["value"]["interfaces"] +
                restored[-1]["value"]["routes"],
            "Final fixture restoration")

    final_log = (root / "client.log").read_text(errors="replace")
    require("Trying to authenticate with 2c:cf:67:62:76:66" in final_log and
            "reason=CONN_FAILED" in final_log and "AssertionError" in final_log and
            "CTRL-EVENT-CONNECTED" not in final_log,
            "Final independent-client blocker")
    reservation = json.loads(reservation_path.read_text())
    require(reservation.get("state") == "RELEASED" and
            reservation.get("packet_sha256") == PRIOR_ATTEMPT_PACKET_SHA256 and
            reservation.get("boards", {}).get("a", {}).get("state") == "empty" and
            reservation.get("boards", {}).get("b", {}).get("state") == "empty",
            "Shared reservation remains released")

    return {"schema": "phase11.5-package10-failure-v1",
        "status": "PACKAGE10_OPEN_R6_FIXTURE_BLOCKED",
        "phase11_5_status": "OPEN_5_OF_6_FAMILIES", "acceptance_credit": 0,
        "candidate": {"source_revision": SOURCE, "image_sha256": IMAGE,
            "boot_id": BOOT, "device_id": DEVICE, "system_clock_hz": 138000000,
            "pio_divider": 1, "engine": "pio-dma-gp2", "renderer": "RAM",
            "wsprrypi_source_revision": WSPRRYPI_SOURCE},
        "diagnosis": {"package9_failure_preserved": True,
            "package9_resource_failure_retested": False,
            "intended_repair": "equivalent retained WTP replay-history classes",
            "firmware_memory_leak_found": False,
            "resource_limit_bytes": 1024,
            "reason_not_retested": "independent wireless client fixture never reached corrected RF admission"},
        "blocked_gate": {"stage": "independent_wireless_client_association",
            "final_error": "Independent client did not start",
            "final_packet_sha256": packet_sha,
            "final_roles": ORIGINAL_ROLES,
            "alternate_roles_tested": True,
            "alternate_roles": SWAPPED_ROLES,
            "alternate_role_packet_sha256": history[-2]["packet_sha256"],
            "identity_checked_radio_resets_tested": True,
            "fixed_acceptance_requirement": True},
        "execution": {"stopped_attempt_rf_jobs": stopped["charged_rf_jobs"],
            "stopped_attempt_rf_duration_ns": stopped["charged_rf_duration_ns"],
            "corrected_preflight_iterations": len(history),
            "corrected_fixture_ready_iterations": sum(item["fixture_ready"] for item in history),
            "corrected_campaign_launches": sum(item["campaign_journal_sha256"] is not None
                                               for item in history),
            "corrected_rf_jobs": 0, "corrected_rf_duration_ns": 0,
            "planned_corrected_rf_jobs": RF_JOBS,
            "planned_corrected_rf_duration_ns": RF_DURATION_NS,
            "full_workload_completed": False},
        "budget": {"authorized_rf_duration_ns": AUTHORIZED_RF_DURATION_NS,
            "charged_rf_jobs": PRIOR_ATTEMPT_RF_JOBS,
            "charged_rf_duration_ns": PRIOR_ATTEMPT_RF_DURATION_NS,
            "unused_authorized_rf_duration_ns":
                AUTHORIZED_RF_DURATION_NS - PRIOR_ATTEMPT_RF_DURATION_NS,
            "authorized_max_flashes": 2, "authorized_max_bootsel": 2,
            "flashes": 0, "bootsel": 0, "configuration_writes": 0,
            "controlled_reboots": 0, "wifi_cycles": 0, "allocation_probes": 0},
        "preflight_history": history,
        "final_inventory": {"pico_a": {"serial": SERIAL, "boot_id": BOOT,
                "source_revision": SOURCE[:12], "state": "empty",
                "owner_id": None, "output_active": False},
            "pico_b": {"serial": B_SERIAL, "boot_id": B_BOOT,
                "source_revision": B_REVISION, "state": "empty",
                "owner_id": None, "output_active": False}},
        "restoration": {"pico_a_empty_unowned_inactive": True,
            "pico_b_empty_unowned_inactive": True, "reservation_released": True,
            "host_fixture_restored": True, "installed_service_active": True,
            "recovery_timer_active": True},
        "evidence_sha256": {"stopped_attempt": sha(stopped_attempt_path),
            "final_packet": packet_sha,
            "final_fixture_state": sha(root / "fixture-state.json"),
            "final_fixture_journal": sha(root / "fixture.jsonl"),
            "final_client_log": sha(root / "client.log"),
            "final_a": sha(root / "final-blocked-a.jsonl"),
            "final_b": sha(root / "final-blocked-b.jsonl"),
            "reservation": sha(reservation_path),
            "alternate_role_packet": history[-2]["packet_sha256"],
            "alternate_role_fixture_state": history[-2]["fixture_state_sha256"]},
        "auditor_sha256": sha(Path(__file__))}


def valid_hash(value):
    return isinstance(value, str) and len(value) == 64 and value != "0" * 64 and \
        all(character in "0123456789abcdef" for character in value)


def validate_result(value):
    require(value.get("schema") == "phase11.5-package10-failure-v1" and
            value.get("status") == "PACKAGE10_OPEN_R6_FIXTURE_BLOCKED" and
            value.get("phase11_5_status") == "OPEN_5_OF_6_FAMILIES" and
            value.get("acceptance_credit") == 0,
            "Package 10 failure publication status")
    require(value.get("candidate") == {"source_revision": SOURCE,
            "image_sha256": IMAGE, "boot_id": BOOT, "device_id": DEVICE,
            "system_clock_hz": 138000000, "pio_divider": 1,
            "engine": "pio-dma-gp2", "renderer": "RAM",
            "wsprrypi_source_revision": WSPRRYPI_SOURCE},
            "Package 10 failure candidate")
    require(value.get("diagnosis") == {"package9_failure_preserved": True,
            "package9_resource_failure_retested": False,
            "intended_repair": "equivalent retained WTP replay-history classes",
            "firmware_memory_leak_found": False, "resource_limit_bytes": 1024,
            "reason_not_retested": "independent wireless client fixture never reached corrected RF admission"},
            "Package 10 failure diagnosis")
    blocked = value.get("blocked_gate", {})
    require(blocked == {"stage": "independent_wireless_client_association",
            "final_error": "Independent client did not start",
            "final_packet_sha256": value.get("evidence_sha256", {}).get("final_packet"),
            "final_roles": ORIGINAL_ROLES, "alternate_roles_tested": True,
            "alternate_roles": SWAPPED_ROLES,
            "alternate_role_packet_sha256":
                value.get("evidence_sha256", {}).get("alternate_role_packet"),
            "identity_checked_radio_resets_tested": True,
            "fixed_acceptance_requirement": True},
            "Package 10 blocked fixture gate")
    execution = value.get("execution", {})
    require(execution == {"stopped_attempt_rf_jobs": 4,
            "stopped_attempt_rf_duration_ns": 4_000_000_000,
            "corrected_preflight_iterations": 13,
            "corrected_fixture_ready_iterations": 5,
            "corrected_campaign_launches": 5,
            "corrected_rf_jobs": 0, "corrected_rf_duration_ns": 0,
            "planned_corrected_rf_jobs": RF_JOBS,
            "planned_corrected_rf_duration_ns": RF_DURATION_NS,
            "full_workload_completed": False}, "Package 10 blocked execution")
    require(value.get("budget") == {"authorized_rf_duration_ns": 480_000_000_000,
            "charged_rf_jobs": 4, "charged_rf_duration_ns": 4_000_000_000,
            "unused_authorized_rf_duration_ns": 476_000_000_000,
            "authorized_max_flashes": 2, "authorized_max_bootsel": 2,
            "flashes": 0, "bootsel": 0, "configuration_writes": 0,
            "controlled_reboots": 0, "wifi_cycles": 0, "allocation_probes": 0},
            "Package 10 actual budget")
    history = value.get("preflight_history", [])
    require(len(history) == 13 and
            [item.get("iteration") for item in history] == list(range(2, 15)) and
            [item.get("outcome") for item in history] ==
                [OUTCOMES[index] for index in range(2, 15)] and
            sum(item.get("fixture_ready") is True for item in history) == 5 and
            all(item.get("restored") is True and item.get("roles") ==
                (SWAPPED_ROLES if item["iteration"] == 13 else ORIGINAL_ROLES) and
                all(valid_hash(item[key]) for key in ("packet_sha256",
                    "fixture_state_sha256", "fixture_journal_sha256", "client_log_sha256")) and
                (item.get("campaign_journal_sha256") is None or
                 valid_hash(item["campaign_journal_sha256"])) for item in history),
            "Package 10 preflight history")
    require(value.get("final_inventory") == {"pico_a": {"serial": SERIAL,
                "boot_id": BOOT, "source_revision": SOURCE[:12], "state": "empty",
                "owner_id": None, "output_active": False},
            "pico_b": {"serial": B_SERIAL, "boot_id": B_BOOT,
                "source_revision": B_REVISION, "state": "empty",
                "owner_id": None, "output_active": False}},
            "Package 10 final inventories")
    require(value.get("restoration") == {"pico_a_empty_unowned_inactive": True,
            "pico_b_empty_unowned_inactive": True, "reservation_released": True,
            "host_fixture_restored": True, "installed_service_active": True,
            "recovery_timer_active": True}, "Package 10 restoration")
    evidence = value.get("evidence_sha256", {})
    require(set(evidence) == {"stopped_attempt", "final_packet", "final_fixture_state",
            "final_fixture_journal", "final_client_log", "final_a", "final_b",
            "reservation", "alternate_role_packet", "alternate_role_fixture_state"} and
            all(valid_hash(item) for item in evidence.values()) and
            valid_hash(value.get("auditor_sha256")), "Package 10 failure evidence")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--history-parent", type=Path, required=True)
    parser.add_argument("--stopped-attempt", type=Path, required=True)
    parser.add_argument("--reservation", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.root.resolve(strict=True), args.history_parent.resolve(strict=True),
        args.stopped_attempt.resolve(strict=True), args.reservation.resolve(strict=True))
    validate_result(result)
    raw = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(raw)
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
