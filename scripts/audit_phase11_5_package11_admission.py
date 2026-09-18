#!/usr/bin/env python3
"""Independently audit Package 11's private zero-RF admission evidence."""

import argparse
import hashlib
import json
from pathlib import Path
import re

from phase11_5_inventory import require
import phase11_5_package10 as package10
import phase11_5_package11 as package11
import phase11_5_package11_admission as admission
from phase11_5_time_local import validate_admission


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    values = [json.loads(line) for line in Path(path).read_text().splitlines()]
    require(values and [row["sequence"] for row in values] == list(range(len(values))) and
            all(values[index]["monotonic_ns"] <= values[index + 1]["monotonic_ns"]
                for index in range(len(values) - 1)), "Admission journal ordering")
    return values


def events(records, kind):
    return [row for row in records if row["kind"] == kind]


def single(records, kind):
    found = events(records, kind)
    require(len(found) == 1, "Expected one " + kind)
    return found[0]


def finished(path):
    records = [json.loads(line) for line in Path(path).read_text().splitlines()]
    found = [row["value"] for row in records if row["kind"] == "finish"]
    require(len(found) == 1 and found[0]["result"] == "READ_ONLY_INVENTORY",
            "Admission inventory")
    return found[0]


def fixture_rows(path):
    records = [json.loads(line) for line in Path(path).read_text().splitlines()]
    require(records and all(records[index]["monotonic_ns"] <=
            records[index + 1]["monotonic_ns"] for index in range(len(records) - 1)),
            "Fixture journal ordering")
    return records


def audit(root, packet_sha256, local_fixture, remote_fixture, reservation_path):
    require(digest(root / "packet.json") == packet_sha256, "Admission packet hash")
    packet = admission.validate(json.loads((root / "packet.json").read_text()))
    records = rows(root / "admission.jsonl")
    require(not events(records, "failure") and not events(records, "worker_failure") and
            not events(records, "observer_failure"), "Admission failure record")
    captured = json.loads((root / "admission-result.json").read_text())
    finish = single(records, "finish")["value"]
    require(captured == finish and captured["status"] == "CAPTURED_ZERO_RF_REQUIRES_AUDIT" and
            captured["packet_sha256"] == packet_sha256 and
            captured["rf_jobs"] == captured["rf_duration_ns"] == 0 and
            captured["observation_seconds"] == admission.OBSERVATION_SECONDS and
            len(captured["samples"]) == admission.SAMPLES,
            "Admission captured result")
    samples = events(records, "admission_sample")
    require([row["value"] for row in samples] == captured["samples"] and
            [row["value"]["index"] for row in samples] == list(range(admission.SAMPLES)) and
            samples[-1]["value"]["elapsed_seconds"] >=
                (admission.SAMPLES - 1) * admission.INTERVAL_SECONDS and
            all(row["value"]["state"] in ("empty", "complete") for row in samples) and
            len({row["value"]["launch_epoch"] for row in samples}) == 1 and
            len({row["value"]["tail_irqs"] for row in samples}) == 1 and
            all(row["value"]["terminal_records"] == samples[0]["value"]["terminal_records"]
                for row in samples), "Admission stable samples")
    requests = [row["value"]["request"] for row in events(records, "normalizer_tx")]
    require(len(requests) == admission.SAMPLES * 3 and
            [request["op"] for request in requests] ==
                [op for _ in range(admission.SAMPLES) for op in ("HELLO", "CAPS", "STATUS")] and
            not any(request["op"] in ("CLAIM", "LOAD", "ARM", "ABORT", "RELEASE")
                    for request in requests), "Admission WTP is read-only")
    browser = events(records, "browser_get")
    require(len(browser) == admission.SAMPLES and
            all(row["value"]["path"] == "/api/v1/status" and
                row["value"]["status"] == 200 for row in browser),
            "Admission HTTPS samples")
    console = [row for row in events(records, "preflight_console_info")
               if re.fullmatch(r"admission-[0-9]+", row["value"]["label"])]
    require(len(console) == admission.SAMPLES and
            [row["value"]["label"] for row in console] ==
                ["admission-" + str(index) for index in range(admission.SAMPLES)],
            "Admission Console samples")
    time_readiness = events(records, "admission_pico_time_readiness")
    require(time_readiness and time_readiness[-1]["value"] == {
                "attempt": len(time_readiness), "ready": True,
                "ntp_address": package11.TIME_ADDRESS, "ntp_resolution": "resolved",
                "clock_state": "synchronized"} and
            all(row["value"]["attempt"] == index + 1
                for index, row in enumerate(time_readiness)),
            "Admission Pico time readiness")
    for name in ("first", "final"):
        value = json.loads((root / ("time-probe-" + name + ".json")).read_text())
        validate_admission(value, package11.TIME_ADDRESS)
    before_a, before_b = finished(root / "before-a.jsonl"), finished(root / "before-b.jsonl")
    final_a, final_b = finished(root / "final-a.jsonl"), finished(root / "final-b.jsonl")
    before_status, final_status = before_a["wtp"]["STATUS"], final_a["wtp"]["STATUS"]
    require(before_status["boot_id"] == final_status["boot_id"] == package10.BOOT and
            before_status["terminal_records"] == final_status["terminal_records"] and
            final_status["owner_id"] is None and final_status["output_active"] is False and
            int(before_a["info"]["launch_epoch"]) == int(final_a["info"]["launch_epoch"]) ==
                captured["before_launch_epoch"] == captured["final_launch_epoch"] and
            int(before_a["info"]["tail_irqs"]) == int(final_a["info"]["tail_irqs"]) ==
                captured["before_tail_irqs"] == captured["final_tail_irqs"] and
            before_b["wtp"]["STATUS"]["boot_id"] ==
                final_b["wtp"]["STATUS"]["boot_id"] == package10.B_BOOT and
            final_b["wtp"]["STATUS"]["owner_id"] is None and
            final_b["wtp"]["STATUS"]["output_active"] is False,
            "Admission zero-RF inventories")
    reservation = json.loads(Path(reservation_path).read_text())
    require(reservation["state"] == "RELEASED" and
            digest(reservation_path) == captured["reservation_unchanged_sha256"],
            "Admission reservation unchanged/released")
    local_state = json.loads((local_fixture / "fixture-state.json").read_text())
    remote_state = json.loads((remote_fixture / "remote-state.json").read_text())
    require(local_state.get("restored") is True and remote_state.get("restored") is True,
            "Admission two-host restoration")
    local_rows = fixture_rows(local_fixture / "fixture.jsonl")
    remote_rows = fixture_rows(remote_fixture / "remote.jsonl")
    local_cleanup = events(local_rows, "cleanup")
    remote_cleanup = events(remote_rows, "cleanup")
    local_restored = events(local_rows, "host_restored")
    remote_restored = events(remote_rows, "host_restored")
    # Cleanup is deliberately idempotent.  A management-network interruption may
    # leave a failed attempt in the append-only log; acceptance still requires a
    # later, clean attempt and a final state record proving full restoration.
    require(local_cleanup and remote_cleanup and local_restored and remote_restored and
            local_cleanup[-1]["value"]["failures"] == [] and
            remote_cleanup[-1]["value"]["failures"] == [] and
            int(local_restored[-1]["value"]["installed_pid"]) > 0 and
            "192.168.1.68/24" in remote_restored[-1]["value"]["interfaces"],
            "Admission host restoration evidence")
    client_log = (local_fixture / "capture-client.log").read_text()
    remote_log = (remote_fixture / "capture.log").read_text().splitlines()
    remote_capture = [json.loads(line) for line in remote_log if line.startswith("{") and
                      "kernel_drops" in line]
    require(re.search(r"[1-9][0-9]* packets captured", client_log) and
            "0 packets dropped by kernel" in client_log and
            len(remote_capture) == 1 and remote_capture[0]["captured"] > 0 and
            remote_capture[0]["kernel_drops"] == 0 and
            (local_fixture / "capture-client.pcap").stat().st_size > 24 and
            (remote_fixture / "capture.pcap").stat().st_size > 24,
            "Admission capture completeness")
    evidence = {}
    for name in ("packet.json", "admission.jsonl", "admission-result.json",
                 "before-a.jsonl", "before-b.jsonl", "final-a.jsonl", "final-b.jsonl",
                 "time-probe-first.json", "time-probe-final.json"):
        evidence[name] = digest(root / name)
    for prefix, base, names in (("local", local_fixture,
        ("fixture-state.json", "fixture.jsonl", "capture-client.pcap")),
        ("remote", remote_fixture,
        ("remote-state.json", "remote.jsonl", "capture.pcap", "remote-ready.json"))):
        for name in names:
            evidence[prefix + "/" + name] = digest(base / name)
    return {"schema": "phase11.5-package11-admission-result-v1",
        "status": "PASS_ZERO_RF", "packet_sha256": packet_sha256,
        "candidate": {"source_revision": package10.SOURCE,
            "image_sha256": package10.IMAGE, "boot_id": package10.BOOT,
            "device_id": package10.DEVICE},
        "fixture": {"ap_host": "wspr4", "ap_mac": "e8:4e:06:ac:f3:87",
            "client_host": "wspr5", "client_mac": "e8:4e:06:ae:d7:09",
            "association_bssid": "e8:4e:06:ac:f3:87", "channel": 11,
            "client_network_namespace": True, "client_mount_namespace": True},
        "readiness": {"observation_seconds": admission.OBSERVATION_SECONDS,
            "wtp_status_samples": admission.SAMPLES,
            "https_status_samples": admission.SAMPLES, "mdns_ntp_probes": 2,
            "same_boot": True, "terminal_set_unchanged": True},
        "zero_rf": {"reservation_acquired": False, "mutating_wtp_requests": 0,
            "launch_epoch_delta": 0, "tail_irq_delta": 0,
            "rf_jobs": 0, "rf_duration_ns": 0},
        "restoration": {"pico_a_inactive_unowned": True,
            "pico_b_inactive_unowned": True, "reservation_released_unchanged": True,
            "wspr5_restored": True, "wspr4_restored": True,
            "installed_service_active": True, "capture_drops": 0},
        "auditor_sha256": digest(Path(__file__)), "evidence_sha256": evidence}


def validate_result(value):
    require(value.get("schema") == "phase11.5-package11-admission-result-v1" and
            value.get("status") == "PASS_ZERO_RF" and
            value.get("candidate") == {"source_revision": package10.SOURCE,
                "image_sha256": package10.IMAGE, "boot_id": package10.BOOT,
                "device_id": package10.DEVICE}, "Admission publication identity")
    require(value.get("fixture") == {"ap_host": "wspr4",
            "ap_mac": "e8:4e:06:ac:f3:87", "client_host": "wspr5",
            "client_mac": "e8:4e:06:ae:d7:09",
            "association_bssid": "e8:4e:06:ac:f3:87", "channel": 11,
            "client_network_namespace": True, "client_mount_namespace": True},
            "Admission publication fixture")
    require(value.get("readiness") == {"observation_seconds": admission.OBSERVATION_SECONDS,
            "wtp_status_samples": admission.SAMPLES,
            "https_status_samples": admission.SAMPLES, "mdns_ntp_probes": 2,
            "same_boot": True, "terminal_set_unchanged": True},
            "Admission publication readiness")
    require(value.get("zero_rf") == {"reservation_acquired": False,
            "mutating_wtp_requests": 0, "launch_epoch_delta": 0,
            "tail_irq_delta": 0, "rf_jobs": 0, "rf_duration_ns": 0},
            "Admission publication zero RF")
    require(value.get("restoration") == {"pico_a_inactive_unowned": True,
            "pico_b_inactive_unowned": True, "reservation_released_unchanged": True,
            "wspr5_restored": True, "wspr4_restored": True,
            "installed_service_active": True, "capture_drops": 0},
            "Admission publication restoration")
    require(isinstance(value.get("packet_sha256"), str) and
            len(value["packet_sha256"]) == 64 and
            isinstance(value.get("auditor_sha256"), str) and
            len(value["auditor_sha256"]) == 64 and value.get("evidence_sha256") and
            all(isinstance(item, str) and len(item) == 64
                for item in value["evidence_sha256"].values()),
            "Admission publication hashes")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--local-fixture", type=Path, required=True)
    parser.add_argument("--remote-fixture", type=Path, required=True)
    parser.add_argument("--reservation", type=Path,
                        default=Path("/home/pi/phase11-5-shared-rf-reservation.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root.resolve(strict=True), args.packet_sha256,
                   args.local_fixture.resolve(strict=True),
                   args.remote_fixture.resolve(strict=True),
                   args.reservation.resolve(strict=True))
    validate_result(result)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
