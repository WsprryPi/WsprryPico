#!/usr/bin/env python3
"""Run the separate zero-RF admission packet for Package 11."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from phase11_5_inventory import require
import phase11_5_package9 as package9
import phase11_5_package10 as package10
import phase11_5_package11 as package11


SCHEMA = "phase11.5-package11-admission-v1"
SAMPLES = 6
INTERVAL_SECONDS = 36
OBSERVATION_SECONDS = SAMPLES * INTERVAL_SECONDS
STATUS_READINESS_SECONDS = 30
PICO_TIME_READINESS_SECONDS = 120


def validate(packet):
    require(packet.get("schema") == SCHEMA and packet.get("family") == "R6" and
            packet.get("authorization") == package11.AUTHORIZATION and
            packet.get("admission_only") is True and
            packet.get("time_authority_address") == package11.TIME_ADDRESS and
            packet.get("rf_jobs") == packet.get("rf_duration_ns") == 0 and
            packet.get("configuration_writes") == packet.get("controlled_reboots") ==
                packet.get("flashes") == packet.get("bootsel") ==
                packet.get("wifi_cycles") == packet.get("allocation_probes") == 0 and
            packet.get("observation_seconds") == OBSERVATION_SECONDS and
            packet.get("sample_count") == SAMPLES and
            packet.get("sample_interval_seconds") == INTERVAL_SECONDS and
            packet.get("status_readiness_seconds") == STATUS_READINESS_SECONDS and
            packet.get("pico_time_readiness_seconds") == PICO_TIME_READINESS_SECONDS,
            "Package 11 admission scope")
    for key, expected in (("source_revision", package10.SOURCE),
                          ("image_sha256", package10.IMAGE),
                          ("boot_id", package10.BOOT),
                          ("serial", package10.SERIAL),
                          ("device_id", package10.DEVICE),
                          ("b_serial", package10.B_SERIAL),
                          ("b_device_id", package10.B_DEVICE),
                          ("b_boot_id", package10.B_BOOT),
                          ("host_boot_id", package10.HOST_BOOT),
                          ("address", package10.ADDRESS),
                          ("hostname", package10.HOSTNAME),
                          ("peer_sha256", package10.PEER_SHA)):
        require(packet.get(key) == expected, "Admission identity: " + key)
    require(packet.get("network_fixture_roles") == {
        "ap_host": "wspr4", "ap": "wlan1", "ap_mac": package11.REMOTE_AP_MAC,
        "client_host": "wspr5", "client": package11.CLIENT_IF,
        "client_mac": package11.CLIENT_MAC}, "Admission fixture roles")
    require(packet.get("remote_ready", {}).get("wifi_sha256") ==
            packet.get("retained_wifi_canonical_sha256"), "Admission Wi-Fi binding")
    for name, expected in packet["stage_sha256"].items():
        path = (Path(packet["root"]) / name).resolve()
        require(path.is_relative_to(Path(packet["root"]).resolve()) and
                package10.digest(path) == expected, "Changed admission input")
    return packet


def time_probe(root, label):
    output = root / (label + ".json")
    error = root / (label + ".stderr")
    with output.open("xb") as stdout, error.open("xb") as stderr:
        environment = dict(os.environ, PHASE115_TIME_ADDRESS=package11.TIME_ADDRESS)
        result = subprocess.run(["python3", str(root / "scripts/phase11_5_time_local.py"),
            "probe", "--run"], stdout=stdout, stderr=stderr, env=environment, timeout=20)
    require(result.returncode == 0, "Admission native mDNS/NTP probe")
    value = json.loads(output.read_text())
    require(value["status"] == "PASS", "Admission native mDNS/NTP result")
    return value


def status_with_retry(root, packet, journal, session, label):
    """Read STATUS after bounded transport retries; never issue a mutating op."""
    deadline = time.monotonic() + packet["status_readiness_seconds"]
    attempt = 0
    request_number = 0
    while time.monotonic() < deadline:
        attempt += 1
        peer = package9.NetworkPeer(root, packet, journal, session)
        peer.number = request_number
        try:
            peer.connect()
            status = peer.ask("STATUS")
            journal.emit("admission_status_ready", {"label": label, "attempt": attempt})
            return status
        except (OSError, TimeoutError) as error:
            request_number = peer.number
            journal.emit("admission_status_wait", {"label": label, "attempt": attempt,
                         "error_type": type(error).__name__})
        finally:
            peer.close()
        time.sleep(packet.get("normalizer_retry_seconds", 2))
    raise TimeoutError("Admission WTP STATUS readiness deadline")


def wait_for_pico_time(journal, seconds):
    """Wait read-only for the Pico to resolve the fixture NTP host and synchronize."""
    deadline = time.monotonic() + seconds
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        info = package9.console_info_once(journal, "admission-time-" + str(attempt))
        network, status = info["network"], info["status"]
        ready = (network["ntp_address"] == package11.TIME_ADDRESS and
                 network["ntp_resolution"] == "resolved" and
                 status["clock_state"] == "synchronized" and
                 status["output_active"] is False)
        journal.emit("admission_pico_time_readiness", {"attempt": attempt,
            "ready": ready, "ntp_address": network["ntp_address"],
            "ntp_resolution": network["ntp_resolution"],
            "clock_state": status["clock_state"]})
        if ready:
            return info
        time.sleep(2)
    raise TimeoutError("Admission Pico time readiness deadline")


def console_ready(info):
    """Apply the admission readiness gate to the firmware's current INFO schema."""
    network, status = info["network"], info["status"]
    return (network["ipv4"] == package10.ADDRESS and
            network["mdns_state"] == "active" and
            status["clock_state"] == "synchronized" and
            status["output_active"] is False and
            status["reboot_required"] is False and
            status["last_error"] is None and
            info["engine_diagnostic"] == "")


def run(root, packet, journal):
    reservation_path = Path("/home/pi/phase11-5-shared-rf-reservation.json")
    reservation_before = reservation_path.read_bytes()
    reservation = json.loads(reservation_before)
    require(reservation.get("state") == "RELEASED", "Admission reservation baseline")
    service_active = subprocess.run([*package9.HOST_SYSTEMCTL, "is-active", "--quiet",
        "wsprrypi.service"]).returncode == 0
    require(service_active, "Admission installed service baseline")
    subprocess.run([*package9.HOST_SYSTEMCTL, "stop", "wsprrypi.service"],
                   check=True, timeout=15)
    journal.emit("installed_service_paused", {"was_active": True, "zero_rf": True})
    try:
        before_a = package9.inventory(root, packet, "before-a", package10.SERIAL,
                                      package10.DEVICE, packet["before_a_session"])
        before_b = package9.inventory(root, packet, "before-b", package10.B_SERIAL,
                                      package10.B_DEVICE, packet["before_b_session"])
        before_status = before_a["wtp"]["STATUS"]
        require(before_status["owner_id"] is None and before_status["output_active"] is False and
                before_status["boot_id"] == package10.BOOT and
                before_b["wtp"]["STATUS"]["boot_id"] == package10.B_BOOT and
                before_b["wtp"]["STATUS"]["output_active"] is False,
                "Admission before authority")
        first_time = time_probe(root, "time-probe-first")
        wait_for_pico_time(journal, packet["pico_time_readiness_seconds"])
        began = time.monotonic()
        samples = []
        for index in range(SAMPLES):
            due = began + index * INTERVAL_SECONDS
            while time.monotonic() < due:
                time.sleep(min(.2, due - time.monotonic()))
            session = packet["readiness_sessions"][index]
            status = status_with_retry(root, packet, journal, session,
                                       "sample-" + str(index))
            require(status["boot_id"] == package10.BOOT and status["owner_id"] is None and
                    status["output_active"] is False and status["state"] in ("empty", "complete"),
                    "Admission WTP STATUS")
            package9.browser_get(root, packet, journal, 0, "/api/v1/status")
            info = package9.console_info_once(journal, "admission-" + str(index))
            require(console_ready(info), "Admission Pico readiness")
            sample = {"index": index, "elapsed_seconds": time.monotonic() - began,
                      "state": status["state"], "terminal_records": status["terminal_records"],
                      "launch_epoch": int(info["launch_epoch"]),
                      "tail_irqs": int(info["tail_irqs"]),
                      "heap_allocated_bytes": int(info["heap_allocated_bytes"])}
            samples.append(sample)
            journal.emit("admission_sample", sample)
        remaining = began + OBSERVATION_SECONDS - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
        second_time = time_probe(root, "time-probe-final")
        after_a = package9.inventory(root, packet, "final-a", package10.SERIAL,
                                     package10.DEVICE, packet["final_a_session"])
        after_b = package9.inventory(root, packet, "final-b", package10.B_SERIAL,
                                     package10.B_DEVICE, packet["final_b_session"])
        final_status = after_a["wtp"]["STATUS"]
        require(final_status["owner_id"] is None and final_status["output_active"] is False and
                final_status["boot_id"] == package10.BOOT and
                final_status["terminal_records"] == before_status["terminal_records"] and
                int(after_a["info"]["launch_epoch"]) == int(before_a["info"]["launch_epoch"]) and
                int(after_a["info"]["tail_irqs"]) == int(before_a["info"]["tail_irqs"]) and
                after_b["wtp"]["STATUS"]["boot_id"] == package10.B_BOOT and
                after_b["wtp"]["STATUS"]["output_active"] is False and
                reservation_path.read_bytes() == reservation_before,
                "Admission zero-RF/final authority")
        result = {"status": "CAPTURED_ZERO_RF_REQUIRES_AUDIT",
            "packet_sha256": package10.digest(root / "packet.json"),
            "observation_seconds": OBSERVATION_SECONDS, "samples": samples,
            "first_time_probe": first_time, "final_time_probe": second_time,
            "before_launch_epoch": int(before_a["info"]["launch_epoch"]),
            "final_launch_epoch": int(after_a["info"]["launch_epoch"]),
            "before_tail_irqs": int(before_a["info"]["tail_irqs"]),
            "final_tail_irqs": int(after_a["info"]["tail_irqs"]),
            "terminal_records": final_status["terminal_records"],
            "rf_jobs": 0, "rf_duration_ns": 0,
            "reservation_unchanged_sha256": package10.digest(reservation_path)}
        (root / "admission-result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        subprocess.run([*package9.HOST_SYSTEMCTL, "start", "wsprrypi.service"],
                       check=False, timeout=15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no host, network or USB access.")
        return
    require(os.geteuid() == 0 and os.name == "posix", "Linux root required")
    root = args.root.resolve(strict=True)
    require(package10.digest(root / "packet.json") == args.packet_sha256 and
            root.stat().st_mode & 0o077 == 0, "Private admission root/packet")
    packet = validate(json.loads((root / "packet.json").read_text()))
    require(packet["root"] == str(root) and
            os.readlink("/proc/self/ns/net") != os.readlink("/proc/1/ns/net") and
            os.readlink("/proc/self/ns/mnt") != os.readlink("/proc/1/ns/mnt"),
            "Admission client namespaces")
    journal = package9.Journal(root / "admission.jsonl")
    try:
        journal.emit("start", {"packet_sha256": args.packet_sha256})
        result = run(root, packet, journal)
        journal.emit("finish", result)
    except BaseException as error:
        journal.emit("failure", {"type": type(error).__name__, "error": str(error)})
        raise
    finally:
        journal.close()


if __name__ == "__main__":
    main()
