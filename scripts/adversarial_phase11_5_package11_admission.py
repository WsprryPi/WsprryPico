#!/usr/bin/env python3
"""Mutation assessment for the Package 11 zero-RF admission result."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from phase11_5_inventory import require
from audit_phase11_5_package11_admission import validate_result


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mutations(value):
    changes = []

    def add(name, edit):
        candidate = copy.deepcopy(value)
        edit(candidate)
        changes.append((name, candidate))

    add("status", lambda v: v.__setitem__("status", "OPEN"))
    add("source", lambda v: v["candidate"].__setitem__("source_revision", "0" * 40))
    add("boot", lambda v: v["candidate"].__setitem__("boot_id", "0" * 32))
    add("ap-host", lambda v: v["fixture"].__setitem__("ap_host", "wspr5"))
    add("ap-mac", lambda v: v["fixture"].__setitem__("ap_mac", "00:00:00:00:00:00"))
    add("client-mac", lambda v: v["fixture"].__setitem__("client_mac", "00:00:00:00:00:00"))
    add("bssid", lambda v: v["fixture"].__setitem__("association_bssid", "00:00:00:00:00:00"))
    add("channel", lambda v: v["fixture"].__setitem__("channel", 6))
    add("netns", lambda v: v["fixture"].__setitem__("client_network_namespace", False))
    add("mountns", lambda v: v["fixture"].__setitem__("client_mount_namespace", False))
    add("duration", lambda v: v["readiness"].__setitem__("observation_seconds", 179))
    add("wtp-samples", lambda v: v["readiness"].__setitem__("wtp_status_samples", 5))
    add("https-samples", lambda v: v["readiness"].__setitem__("https_status_samples", 5))
    add("mdns-ntp", lambda v: v["readiness"].__setitem__("mdns_ntp_probes", 1))
    add("same-boot", lambda v: v["readiness"].__setitem__("same_boot", False))
    add("terminal-drift", lambda v: v["readiness"].__setitem__("terminal_set_unchanged", False))
    add("reservation", lambda v: v["zero_rf"].__setitem__("reservation_acquired", True))
    add("mutation", lambda v: v["zero_rf"].__setitem__("mutating_wtp_requests", 1))
    add("launch", lambda v: v["zero_rf"].__setitem__("launch_epoch_delta", 1))
    add("tail", lambda v: v["zero_rf"].__setitem__("tail_irq_delta", 1))
    add("rf", lambda v: v["zero_rf"].__setitem__("rf_jobs", 1))
    add("wspr4-restore", lambda v: v["restoration"].__setitem__("wspr4_restored", False))
    add("wspr5-restore", lambda v: v["restoration"].__setitem__("wspr5_restored", False))
    add("pico-active", lambda v: v["restoration"].__setitem__("pico_a_inactive_unowned", False))
    add("capture-drop", lambda v: v["restoration"].__setitem__("capture_drops", 1))
    add("evidence-hash", lambda v: v["evidence_sha256"].__setitem__(
        next(iter(v["evidence_sha256"])), "0" * 63))
    return changes


def assess(value):
    validate_result(value)
    outcomes = []
    for name, candidate in mutations(value):
        try:
            validate_result(candidate)
        except Exception as error:
            outcomes.append({"name": name, "rejected": True,
                             "error_type": type(error).__name__})
        else:
            outcomes.append({"name": name, "rejected": False})
    require(all(item["rejected"] for item in outcomes), "Admission mutation accepted")
    validate_result(value)
    return {"schema": "phase11.5-package11-admission-adversarial-v1",
        "status": "PASS", "mutation_count": len(outcomes),
        "all_mutations_rejected": True, "mutations": outcomes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = json.loads(args.result.read_text())
    result = assess(value)
    result["admission_result_sha256"] = digest(args.result)
    result["adversarial_script_sha256"] = digest(Path(__file__))
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
