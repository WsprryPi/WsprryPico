#!/usr/bin/env python3
"""Execute the frozen Phase 11.5 Package 10 matched replay-state packet."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import threading
import time

import phase11_5_package9 as package9
from phase11_5_inventory import require
from phase11_5_rf_reservation import Reservation


SOURCE = package9.SOURCE
IMAGE = package9.IMAGE
BOOT = package9.BOOT
SERIAL = package9.SERIAL
DEVICE = package9.DEVICE
B_SERIAL = package9.B_SERIAL
B_DEVICE = package9.B_DEVICE
B_BOOT = package9.B_BOOT
HOST_BOOT = package9.HOST_BOOT
WSPRRYPI_SOURCE = package9.WSPRRYPI_SOURCE
ADDRESS = package9.ADDRESS
HOSTNAME = package9.HOSTNAME
PEER_SHA = package9.PEER_SHA
PRODUCTION_DURATION_NS = package9.PRODUCTION_DURATION_NS
NORMALIZER_DURATION_NS = package9.NORMALIZER_DURATION_NS
NORMAL_SECONDS = package9.NORMAL_SECONDS
FINAL_QUIET_SECONDS = package9.FINAL_QUIET_SECONDS
INTERLEAVED_QUIET_SECONDS = package9.INTERLEAVED_QUIET_SECONDS
CRITICAL_PATH_NS = package9.CRITICAL_PATH_NS
WARMUP_PRODUCTION_JOBS = 3
WARMUP_MAXIMUM_JOBS = 5
REFRESH_JOBS = 5
RF_JOBS = WARMUP_PRODUCTION_JOBS + WARMUP_MAXIMUM_JOBS + 3 + REFRESH_JOBS
RF_DURATION_NS = ((WARMUP_PRODUCTION_JOBS + WARMUP_MAXIMUM_JOBS + REFRESH_JOBS) *
                  NORMALIZER_DURATION_NS + 3 * PRODUCTION_DURATION_NS)
AUTHORIZED_RF_DURATION_NS = 480_000_000_000
PRIOR_ATTEMPT_RF_JOBS = 4
PRIOR_ATTEMPT_RF_DURATION_NS = 4_000_000_000
CUMULATIVE_RF_JOBS = PRIOR_ATTEMPT_RF_JOBS + RF_JOBS
CUMULATIVE_RF_DURATION_NS = PRIOR_ATTEMPT_RF_DURATION_NS + RF_DURATION_NS
PRIOR_ATTEMPT_PACKET_SHA256 = "def689a1e498bb0ba0206198b9a6637b4496f275d498cf15011390ece9540c90"
PRIOR_ATTEMPT_RESULT_SHA256 = "d73515feb8a35c6bb559fbb346213f73f0649bf06e26fb5dc2d5848aa2759f79"
EXPECTED_PRODUCTION_EVENTS = 383
NETWORK_ROUTE_SECONDS = 600
NETWORK_SETTLE_SECONDS = 180
NETWORK_READINESS_SECONDS = 300
NORMALIZER_CONNECT_TIMEOUT_SECONDS = 15
NORMALIZER_RETRY_SECONDS = 30
TLS_KEY_EXCHANGE_GROUP = "X25519"
FIXTURE_AP_IF = "wlan0"
FIXTURE_CLIENT_IF = "wlan2"
EXPECTED_MAXIMUM_EVENTS = 512


def digest(path):
    return package9.digest(path)


def identity(value, label):
    return package9.identity(value, label)


def browser_actions():
    return package9.browser_actions()


def production_frequencies():
    """Return the exact FSKCW frequency sequence for 32 question marks."""
    # WsprryPi FSKCW treats Base Frequency as the space frequency and adds
    # Shift Hz for the mark. Retained Package 9 TLS evidence independently
    # binds this exact 135.505/135.500 MHz sequence.
    mark = 135_505_000_000_000
    space = 135_500_000_000_000
    values = []
    for character in range(32):
        for element in range(6):
            values.append(mark)
            if element != 5:
                values.append(space)
        if character != 31:
            values.append(space)
    require(len(values) == EXPECTED_PRODUCTION_EVENTS, "Production frequency sequence")
    return values


def production_class_job(seed, index):
    base, remainder = divmod(NORMALIZER_DURATION_NS, EXPECTED_PRODUCTION_EVENTS)
    offset = 0
    events = []
    for event_index, frequency in enumerate(production_frequencies()):
        duration = base + (1 if event_index < remainder else 0)
        events.append({"offset_ns": str(offset), "duration_ns": str(duration),
                       "rf_on": True, "frequency_nhz": str(frequency)})
        offset += duration
    require(offset == NORMALIZER_DURATION_NS, "Production normalizer duration")
    return {"job_id": hashlib.sha256(
                f"{seed}:production-class:{index}".encode()).hexdigest()[:32],
            "profile": "rf-events/1", "mode": "fskcw",
            "total_duration_ns": str(NORMALIZER_DURATION_NS),
            "allow_frequency_adjustment": True, "events": events}


def maximum_class_job(seed, phase, index):
    event_ns = 1_953_125
    events = [{"offset_ns": str(event_index * event_ns),
               "duration_ns": str(event_ns), "rf_on": True,
               "frequency_nhz": str(135_500_000_000_000 if event_index % 2 == 0
                                     else 135_495_000_000_000)}
              for event_index in range(EXPECTED_MAXIMUM_EVENTS)]
    return {"job_id": hashlib.sha256(
                f"{seed}:{phase}:{index}".encode()).hexdigest()[:32],
            "profile": "rf-events/1", "mode": "fskcw",
            "total_duration_ns": str(NORMALIZER_DURATION_NS),
            "allow_frequency_adjustment": True, "events": events}


def warmup_jobs(seed):
    return ([production_class_job(seed, index)
             for index in range(WARMUP_PRODUCTION_JOBS)] +
            [maximum_class_job(seed, "warmup-maximum", index)
             for index in range(WARMUP_MAXIMUM_JOBS)])


def refresh_jobs(seed):
    return [maximum_class_job(seed, "refresh-maximum", index)
            for index in range(REFRESH_JOBS)]


def canonical_adjustments(adjustments):
    normalized = []
    for value in adjustments:
        normalized.append({"event_index": int(value["event_index"]),
            "requested_frequency_nhz": int(value["requested_frequency_nhz"]),
            "realized_frequency_nhz": int(value["realized_frequency_nhz"])})
    return normalized


def adjustment_hash(adjustments):
    raw = json.dumps(canonical_adjustments(adjustments), separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def wait_for_network_settle(packet, journal):
    """Wait for the retained route and clock runway without opening TCP."""
    deadline = time.monotonic() + packet["network_route_seconds"]
    attempt = 0
    while True:
        attempt += 1
        try:
            addresses = sorted({row[4][0] for row in socket.getaddrinfo(
                HOSTNAME, 18443, socket.AF_INET, socket.SOCK_STREAM)})
        except socket.gaierror:
            addresses = []
        ready = addresses == [ADDRESS]
        journal.emit("network_route_readiness", {"attempt": attempt,
            "ready": ready, "addresses": addresses})
        if ready:
            break
        require(time.monotonic() < deadline, "Network route readiness deadline")
        time.sleep(min(5, max(0, deadline - time.monotonic())))
    settle_deadline = time.monotonic() + packet["network_settle_seconds"]
    sample = 0
    while True:
        remaining = settle_deadline - time.monotonic()
        if remaining <= 0:
            break
        sample += 1
        journal.emit("network_clock_settle", {"sample": sample,
            "remaining_seconds": int(remaining), "observed_address": ADDRESS})
        time.sleep(min(15, remaining))
    journal.emit("network_clock_settle_complete", {
        "seconds": packet["network_settle_seconds"], "address": ADDRESS})


def validate(packet):
    require(packet["schema"] == "phase11.5-package10-fixture-v2" and
            packet["family"] == "R6" and
            packet["authorization"] == "PACKAGE10-480-RF-SECONDS" and
            packet["source_revision"] == SOURCE and packet["image_sha256"] == IMAGE and
            packet["boot_id"] == BOOT and packet["serial"] == SERIAL and
            packet["device_id"] == DEVICE and packet["b_serial"] == B_SERIAL and
            packet["b_device_id"] == B_DEVICE and packet["b_boot_id"] == B_BOOT and
            packet["host_boot_id"] == HOST_BOOT and
            packet["wsprrypi_source_revision"] == WSPRRYPI_SOURCE and
            packet["address"] == ADDRESS and packet["hostname"] == HOSTNAME and
            packet["peer_sha256"] == PEER_SHA, "Exact Package 10 identity")
    require(packet["network_runtime_seconds"] == 5400 and
            packet["network_restoration_seconds"] == 900 and
            packet["configuration_writes"] == packet["controlled_reboots"] ==
            packet["flashes"] == packet["bootsel"] == packet["wifi_cycles"] ==
            packet["allocation_probes"] == 0 and
            packet["authorized_max_flashes"] == packet["authorized_max_bootsel"] == 2 and
            packet["authorized_rf_duration_ns"] == AUTHORIZED_RF_DURATION_NS and
            packet["rf_jobs"] == RF_JOBS and packet["rf_duration_ns"] == RF_DURATION_NS and
            packet["cumulative_rf_jobs"] == CUMULATIVE_RF_JOBS and
            packet["cumulative_rf_duration_ns"] == CUMULATIVE_RF_DURATION_NS and
            CUMULATIVE_RF_DURATION_NS <= AUTHORIZED_RF_DURATION_NS,
            "Finite Package 10 budget")
    require(packet["network_fixture_roles"] == {"ap": FIXTURE_AP_IF,
            "client": FIXTURE_CLIENT_IF, "ap_mac": "2c:cf:67:62:76:66",
            "client_mac": "e8:4e:06:ae:d7:09"},
            "Frozen Package 10 network fixture roles")
    require(packet["prior_attempt"] == {
        "packet_sha256": PRIOR_ATTEMPT_PACKET_SHA256,
        "result_sha256": PRIOR_ATTEMPT_RESULT_SHA256,
        "status": "STOPPED_PRE_GATE_SEQUENCE_MISMATCH",
        "charged_rf_jobs": PRIOR_ATTEMPT_RF_JOBS,
        "charged_rf_duration_ns": PRIOR_ATTEMPT_RF_DURATION_NS,
        "reservation_released": True, "fixture_restored": True,
    }, "Preserved Package 10 stopped attempt")
    require(packet["memory_preflight"] == {
        "timeout_seconds": package9.MEMORY_PREFLIGHT_SECONDS,
        "sample_seconds": package9.MEMORY_PREFLIGHT_SAMPLE_SECONDS,
        "minimum_heap_available_bytes": package9.MINIMUM_PREFLIGHT_HEAP_AVAILABLE_BYTES,
        "minimum_inventory_heap_available_bytes":
            package9.MINIMUM_INVENTORY_HEAP_AVAILABLE_BYTES,
        "minimum_connected_heap_available_bytes":
            package9.MINIMUM_CONNECTED_HEAP_AVAILABLE_BYTES,
        "reason": "expire prior WTP state before installing matched replay classes",
    }, "Frozen Package 10 memory preflight")
    require(packet["normal_load"] == {
        "cycles": 3, "seconds_per_cycle": package9.NORMAL_SECONDS,
        "browser_intervals_per_cycle": 2, "browser_actions": browser_actions(),
        "production": {"mode": "FSKCW", "message": "?" * 32,
            "base_frequency_hz": 135500, "shift_hz": 5,
            "dot_seconds": 0.2, "event_count": EXPECTED_PRODUCTION_EVENTS,
            "duration_ns": PRODUCTION_DURATION_NS, "start_offset_seconds": 90}},
        "Frozen Package 10 normal workload")
    require(packet["quiet"] == {"baseline_seconds": package9.BASELINE_QUIET_SECONDS,
            "interleaved_seconds": [package9.INTERLEAVED_QUIET_SECONDS] * 3,
            "final_seconds": package9.FINAL_QUIET_SECONDS,
            "minimum_measured_seconds": 3438}, "Frozen Package 10 quiet schedule")
    require(packet["warmup_jobs"] == warmup_jobs(packet["normalizer_seed"]) and
            packet["refresh_jobs"] == refresh_jobs(packet["normalizer_seed"]) and
            packet["network_route_seconds"] == NETWORK_ROUTE_SECONDS and
            packet["network_settle_seconds"] == NETWORK_SETTLE_SECONDS and
            packet["network_readiness_seconds"] == NETWORK_READINESS_SECONDS and
            packet["normalizer_connect_timeout_seconds"] ==
                NORMALIZER_CONNECT_TIMEOUT_SECONDS and
            packet["normalizer_retry_seconds"] == NORMALIZER_RETRY_SECONDS and
            packet["tls_key_exchange_group"] == TLS_KEY_EXCHANGE_GROUP and
            packet["production_openssl"] == "production-openssl.cnf" and
            digest(Path(packet["root"]) / packet["production_openssl"]) ==
                packet["production_openssl_sha256"] and
            packet["normalizer_request_timeout_seconds"] ==
                package9.NORMALIZER_REQUEST_TIMEOUT_SECONDS,
            "Frozen matched normalizers")
    require(packet["terminal_history"] == {
        "capacity": 8, "warmup_production_class": 3, "warmup_maximum_class": 5,
        "production_jobs": 3, "refresh_maximum_class": 5,
        "final_production_class": 3, "final_maximum_class": 5,
        "resource_return_limit_bytes": 1024,
    }, "Frozen terminal-history equivalence")
    require(packet["credentials"] == {
        "controller": {"ca": "credentials/controller/client-ca.crt",
                       "cert": "credentials/controller/client.crt",
                       "key": "credentials/controller/client.key"},
        "browser": {"ca": "credentials/browser/client-ca.crt",
                    "cert": "credentials/browser/client.crt",
                    "key": "credentials/browser/client.key"}}, "Frozen credentials")
    names = ["normalizer_seed", "warmup_session", "warmup_owner", "refresh_session",
             "refresh_owner", "before_a_session", "before_b_session", "final_a_session",
             "final_b_session"] + [f"usb_observer_session_{index}" for index in range(1, 4)]
    values = [identity(packet[name], name) for name in names]
    require(isinstance(packet["readiness_sessions"], list) and
            len(packet["readiness_sessions"]) == 4, "Package 10 readiness sessions")
    values.extend(identity(value, "readiness_session")
                  for value in packet["readiness_sessions"])
    require(len(values) == len(set(values)), "Distinct Package 10 identities")
    for name, expected in (("binary", packet["wsprrypi_binary_sha256"]),
                           ("observer", packet["tls_observer_sha256"])):
        path = Path(packet[name])
        require(path.is_file() and digest(path) == expected, "Frozen " + name)
    for name, expected in packet["stage_sha256"].items():
        path = (Path(packet["root"]) / name).resolve()
        require(path.is_relative_to(Path(packet["root"]).resolve()) and
                digest(path) == expected, "Changed staged input")
    return packet


def run_job_batch(root, packet, journal, phase, jobs, session, owner, expected_count):
    peer = package9.NetworkPeer(root, packet, journal, session).connect()
    try:
        initial = peer.ask("STATUS")
        require(initial["boot_id"] == BOOT and initial["output_active"] is False and
                initial["owner_id"] is None, phase + " initial authority")
        if phase == "warmup":
            connected = package9.console_info_once(journal, "normalizer-connected")
            require(connected["heap_available_bytes"] >=
                    packet["memory_preflight"]["minimum_connected_heap_available_bytes"],
                    "Connected normalizer LOAD headroom")
        completed, hashes = [], []
        for index, job in enumerate(jobs):
            event_start = len(peer.events)
            package9.wait_for_fresh_clock(peer, journal, f"{phase}-{index}")
            peer.ask("CLAIM", {"owner_id": owner, "lease_ms": 60000})
            loaded = peer.ask("LOAD", job)
            require(loaded["job_id"] == job["job_id"] and
                    len(loaded["adjustments"]) == expected_count[index],
                    phase + " LOAD")
            digest_value = adjustment_hash(loaded["adjustments"])
            clock = peer.ask("GET_CLOCK")
            require(package9.arm_clock_usable(clock), phase + " clock")
            target = ((int(clock["utc_now_ns"]) + package9.NORMALIZER_ARM_LEAD_NS +
                       999_999_999) // 1_000_000_000) * 1_000_000_000
            peer.ask("ARM", {"job_id": job["job_id"], "start_utc_ns": str(target),
                     "max_start_uncertainty_ns": "500000000"})
            states, final = set(), None
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                status = peer.ask("STATUS")
                states.add(status["state"])
                if status["state"] == "complete":
                    final = status
                    break
                time.sleep(1)
            states.update(event["body"]["state"] for event in peer.events[event_start:]
                          if event["event"] == "JOB_STATE" and
                          event["body"].get("job_id") == job["job_id"])
            require(final is not None and
                    {"loaded", "armed", "running"}.issubset(states) and
                    final["output_active"] is False and final["job_id"] == job["job_id"],
                    phase + " lifecycle")
            peer.ask("RELEASE")
            released = peer.ask("STATUS")
            require(released["owner_id"] is None and released["output_active"] is False,
                    phase + " release")
            completed.append(job["job_id"])
            hashes.append(digest_value)
            journal.emit("normalizer_complete", {"phase": phase, "index": index,
                "job_id": job["job_id"], "event_count": expected_count[index],
                "adjustment_sha256": digest_value, "states": sorted(states),
                "terminal_records": released["terminal_records"]})
        require(len(released["terminal_records"]) == 8 and
                all(record["state"] == "complete" and not record["output_active"]
                    for record in released["terminal_records"]),
                phase + " terminal cardinality")
        return {"status": released, "jobs": completed, "adjustment_hashes": hashes}
    finally:
        peer.close()


def run_warmup(root, packet, journal):
    expected = ([EXPECTED_PRODUCTION_EVENTS] * WARMUP_PRODUCTION_JOBS +
                [EXPECTED_MAXIMUM_EVENTS] * WARMUP_MAXIMUM_JOBS)
    result = run_job_batch(root, packet, journal, "warmup", packet["warmup_jobs"],
                           packet["warmup_session"], packet["warmup_owner"], expected)
    production = result["adjustment_hashes"][:WARMUP_PRODUCTION_JOBS]
    maximum = result["adjustment_hashes"][WARMUP_PRODUCTION_JOBS:]
    require(len(set(production)) == len(set(maximum)) == 1 and
            production[0] != maximum[0], "Warm-up adjustment classes")
    require({record["job_id"] for record in result["status"]["terminal_records"]} ==
            set(result["jobs"]), "Warm-up terminal set")
    result["production_hash"] = production[0]
    result["maximum_hash"] = maximum[0]
    return result


def run_refresh(root, packet, journal, cycles, warmup):
    result = run_job_batch(root, packet, journal, "refresh", packet["refresh_jobs"],
                           packet["refresh_session"], packet["refresh_owner"],
                           [EXPECTED_MAXIMUM_EVENTS] * REFRESH_JOBS)
    require(set(result["adjustment_hashes"]) == {warmup["maximum_hash"]},
            "Refresh adjustment class")
    expected_jobs = {cycle["job_id"] for cycle in cycles} | set(result["jobs"])
    terminal = result["status"]["terminal_records"]
    require({record["job_id"] for record in terminal} == expected_jobs,
            "Refreshed equivalent terminal set")
    result["expected_terminal_jobs"] = sorted(expected_jobs)
    return result


def _run_with_service_paused(root, packet, journal, pre_memory=None):
    if pre_memory is not None:
        pre_memory(root, packet, journal)
    package9.wait_for_memory_headroom(packet, journal)
    wait_for_network_settle(packet, journal)
    package9.wait_for_normalizer_readiness(root, packet, journal,
        packet["readiness_sessions"][0], seconds=packet["network_readiness_seconds"])
    package9.wait_for_readiness_session_release(packet, journal)
    before_a = package9.inventory(root, packet, "before-a", SERIAL, DEVICE,
                                  packet["before_a_session"])
    before_b = package9.inventory(root, packet, "before-b", B_SERIAL, B_DEVICE,
                                  packet["before_b_session"])
    require(before_a["info"]["revision"] == SOURCE[:12] and
            before_a["wtp"]["STATUS"]["boot_id"] == BOOT and
            before_b["wtp"]["STATUS"]["boot_id"] == B_BOOT and
            before_a["info"]["heap_available_bytes"] >=
                packet["memory_preflight"]["minimum_inventory_heap_available_bytes"],
            "Preflight identity/headroom")
    reservation = Reservation(digest(root / "packet.json"))
    reservation.acquire({"a": before_a, "b": before_b})
    journal.emit("reservation_acquired", json.loads(reservation.path.read_text()))
    observer_stop = threading.Event()
    console = package9.ConsoleObserver(journal, observer_stop)
    host = package9.HostObserver(journal, observer_stop)
    cycles, windows = [], []
    final_values = None
    capture = capture_output = None
    try:
        capture_output = (root / "campaign-capture.log").open("xb")
        capture = subprocess.Popen(["tcpdump", "--immediate-mode", "-i", FIXTURE_CLIENT_IF, "-U",
            "-s", "0", "-w", str(root / "campaign.pcap"),
            "tcp port 18443 or arp or udp port 123 or udp port 5353"],
            stdout=capture_output, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 5
        while not (root / "campaign.pcap").exists() and time.monotonic() < deadline:
            time.sleep(.05)
        require((root / "campaign.pcap").exists() and capture.poll() is None,
                "Campaign capture did not start")
        journal.emit("capture_started", {"pid": capture.pid})
        warmup = run_warmup(root, packet, journal)
        console.start()
        host.start()
        windows.append(package9.quiet(journal, console, "post-warmup-baseline",
                                      package9.BASELINE_QUIET_SECONDS))
        for cycle in range(1, 4):
            cycles.append(package9.run_normal_cycle(root, packet, journal, cycle,
                                                    observer_stop))
            windows.append(package9.quiet(journal, console, f"post-n{cycle}",
                                          package9.INTERLEAVED_QUIET_SECONDS))
        refresh = run_refresh(root, packet, journal, cycles, warmup)
        journal.emit("terminal_equivalence", {
            "stage": "before-final-q", "production_class_records": 3,
            "maximum_class_records": 5,
            "terminal_jobs": refresh["expected_terminal_jobs"],
            "production_adjustment_sha256": warmup["production_hash"],
            "maximum_adjustment_sha256": warmup["maximum_hash"]})
        windows.append(package9.quiet(journal, console, "final-q",
                                      package9.FINAL_QUIET_SECONDS))
        observer_stop.set()
        console.join(10)
        host.join(10)
        require(not console.is_alive() and not host.is_alive() and
                console.failure is None and host.failure is None, "Long observers")
        final_a = package9.inventory(root, packet, "final-a", SERIAL, DEVICE,
                                     packet["final_a_session"])
        final_b = package9.inventory(root, packet, "final-b", B_SERIAL, B_DEVICE,
                                     packet["final_b_session"])
        final_values = {"a": final_a, "b": final_b}
        final_status = final_a["wtp"]["STATUS"]
        require(final_status["boot_id"] == BOOT and final_status["owner_id"] is None and
                final_status["output_active"] is False and
                {record["job_id"] for record in final_status["terminal_records"]} ==
                    set(refresh["expected_terminal_jobs"]) and
                all(record["state"] == "complete" and not record["output_active"]
                    for record in final_status["terminal_records"]),
                "Final equivalent terminal/authority state")
        baseline = windows[0]["heap_allocated_bytes"]
        posts = [window["heap_allocated_bytes"] for window in windows[1:4]]
        final_live = windows[4]["heap_allocated_bytes"]
        require(all(abs(value - baseline) <= 1024 for value in posts + [final_live]) and
                max(posts) - min(posts) <= 1024 and
                not (posts[0] < posts[1] < posts[2]), "R6 matched resource return")
        final_info = final_a["info"]
        require(int(final_info["rf_max_service_gap_ns"]) <= package9.CRITICAL_PATH_NS and
                int(final_info["max_refill_irq_to_ready_ns"]) <=
                    package9.CRITICAL_PATH_NS and
                final_info["refill_full_predecessor"]["measured"] and
                final_info["refill_short_predecessor"]["measured"] and
                final_info["refill_full_predecessor"]["remaining_words"] * 4 >=
                    final_info["refill_full_predecessor"]["total_words"] and
                final_info["refill_short_predecessor"]["remaining_words"] * 4 >=
                    final_info["refill_short_predecessor"]["total_words"] and
                final_info["tail_irqs"] >= 16 and
                int(final_info["launch_epoch"]) >= int(before_a["info"]["launch_epoch"]) + 16,
                "Final RF timing/path gate")
        result = {"status": "CAPTURED_REQUIRES_AUDIT",
            "packet_sha256": digest(root / "packet.json"), "normal_seconds": 1800,
            "rf_jobs": RF_JOBS, "rf_duration_ns": RF_DURATION_NS,
            "warmup_jobs": warmup["jobs"], "refresh_jobs": refresh["jobs"],
            "production_adjustment_sha256": warmup["production_hash"],
            "maximum_adjustment_sha256": warmup["maximum_hash"],
            "cycles": cycles, "windows": windows,
            "final_terminal_jobs": refresh["expected_terminal_jobs"],
            "console_samples": len(console.starts), "host_samples": len(host.starts),
            "final_metrics": {key: final_info[key] for key in (
                "allocator_peak_bytes", "heap_capacity_bytes", "core0_stack_used_bytes",
                "core1_stack_used_bytes", "rf_max_service_gap_ns",
                "max_refill_irq_to_ready_ns", "min_data_successor_ready_words",
                "min_tail_successor_ready_words", "dma_errors", "tail_irqs", "launch_epoch")}}
        (root / "campaign-result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        observer_stop.set()
        if console.is_alive():
            console.join(10)
        if host.is_alive():
            host.join(10)
        if capture is not None and capture.poll() is None:
            capture.send_signal(signal.SIGINT)
            try:
                capture.wait(timeout=15)
            except subprocess.TimeoutExpired:
                capture.terminate()
                capture.wait(timeout=5)
        if capture_output is not None:
            capture_output.close()
        if capture is not None:
            journal.emit("capture_stopped", {"exit": capture.returncode,
                "pcap_bytes": (root / "campaign.pcap").stat().st_size
                    if (root / "campaign.pcap").exists() else 0})
        if reservation.held and final_values is not None:
            reservation.release(final_values)
            journal.emit("reservation_released", json.loads(reservation.path.read_text()))
        reservation.close()


def run(root, packet, journal, pre_memory=None):
    service_was_active = subprocess.run([*package9.HOST_SYSTEMCTL, "is-active", "--quiet",
        "wsprrypi.service"]).returncode == 0
    require(service_was_active, "Installed WsprryPi service baseline")
    subprocess.run([*package9.HOST_SYSTEMCTL, "stop", "wsprrypi.service"],
                   check=True, timeout=15)
    journal.emit("installed_service_paused", {"was_active": True,
        "before_memory_readiness": True})
    try:
        return _run_with_service_paused(root, packet, journal, pre_memory)
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
        print("Plan only; no host, network, USB or RF access.")
        return
    require(os.geteuid() == 0 and os.name == "posix", "Linux root required")
    root = args.root.resolve(strict=True)
    require(root.stat().st_mode & 0o077 == 0 and
            digest(root / "packet.json") == args.packet_sha256, "Private root/packet")
    packet = validate(json.loads((root / "packet.json").read_text()))
    require(packet["root"] == str(root) and
            Path("/proc/sys/kernel/random/boot_id").read_text().strip() == HOST_BOOT,
            "Package 10 root/host")
    require(os.readlink("/proc/self/ns/net") != os.readlink("/proc/1/ns/net") and
            os.readlink("/proc/self/ns/mnt") != os.readlink("/proc/1/ns/mnt"),
            "Package 10 requires independent client namespaces")
    os.umask(0o077)
    journal = package9.Journal(root / "campaign.jsonl")
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
