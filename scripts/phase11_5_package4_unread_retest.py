#!/usr/bin/env python3
"""One-job physical retest of Phase 11.5 assertion 2.3e."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import threading
import time

from phase11_5_device_management import digest, save
from phase11_5_inventory import exchange, exclusive_port, require
from phase11_5_package4_usb import (BOOT, B_BOOT, DEVICE, IMAGE, NetworkPeer,
                                    SERIAL, SOURCE, Journal, inventory,
                                    unread_pressure, usb_peer)
from phase11_5_pilot_supervisor import B_DEVICE, B_SERIAL, configuration
from phase11_5_r3_v2_rf import validate_info


SCHEMA = "phase11.5-package4-unread-retest-v1"
CASE = "usb-unread-output"
PRIOR_PACKET = "6de855e36977a824498d920fce9eeff9c4bfd9b087c8964966d93f7daa68522f"
PRIOR_RESULT = "afd16acff0e041d53119b5e2f788f5fd808feb502974f3f4525d0c9fb36d5621"


def identity(value):
    require(isinstance(value, str) and len(value) == 32 and value != "0" * 32 and
            all(c in "0123456789abcdef" for c in value), "Unread retest identity")
    return value


def validate(packet):
    require(packet["schema"] == packet["scope"] == SCHEMA and
            packet["standing_authority"] == "R3-COMPLETE-20260913-v2" and
            packet["source_revision"] == SOURCE and packet["image_sha256"] == IMAGE and
            packet["boot_id"] == BOOT and packet["b_boot_id"] == B_BOOT and
            packet["serial"] == SERIAL and packet["device_id"] == DEVICE and
            packet["b_serial"] == B_SERIAL and packet["b_device_id"] == B_DEVICE and
            packet["case"] == CASE, "Exact unread retest target/scope")
    attempt = packet.get("retest_attempt", 1)
    require(attempt in (1, 2), "Exact unread retest attempt")
    if attempt == 1:
        require(packet["authorization"] == "USER-REQUESTED-PHYSICAL-RETEST-20260916" and
                packet["fixture_root"] ==
                "/home/pi/phase11-5-package4-unread-fixture-20260916" and
                packet["fixture_packet_sha256"] ==
                "0084f965781aaf591f55c6d2a7b6252876d29c8dd455a0ae48d33c9803b828ea" and
                "previous_retest" not in packet, "Exact first unread retest authority")
    else:
        require(packet["authorization"] ==
                "USER-REQUESTED-PHYSICAL-RETEST-RETRY-20260916" and
                packet["fixture_root"] ==
                "/home/pi/phase11-5-package4-unread-fixture2-20260916" and
                packet["fixture_packet_sha256"] ==
                "f4d1dade80f5df59375af02faccfd347158cffe295955b74aa360bf4a30b9e86" and
                packet["previous_retest"] == {
                    "packet_sha256":
                        "10fe965e5ac0e15d58226aaab598ca9671ed0d5009149e5f737b26f6499607ba",
                    "result_sha256":
                        "a0071448cbdb22026bfbef8dda4cc947f5d0ef1b532f2c7817d22dce3436e519",
                    "status": "OPEN_NO_UNREAD_PRESSURE_EXECUTED",
                    "rf_jobs_charged": 1,
                    "rf_duration_ns_charged": 100_000_000_000,
                }, "Exact second unread retest authority/history")
    require(packet["prior_package4_packet_sha256"] == PRIOR_PACKET and
            packet["prior_package4_result_sha256"] == PRIOR_RESULT and
            packet["prior_assertion"] ==
            {"2.3d": "ACCEPTED", "2.3e": "OPEN_MISSING_SAME_SESSION_SILENCE_AND_DTR_RECOVERY"},
            "Exact prior Package 4 boundary")
    require(packet["runtime_seconds"] == 240 and packet["restoration_seconds"] == 150 and
            packet["rf_jobs"] == 1 and packet["rf_duration_ns"] == 100_000_000_000 and
            packet["flashes"] == packet["wifi_cycles"] == packet["configuration_writes"] ==
            packet["controlled_reboots"] == 0 and packet["maximum_renewals"] == 4,
            "Finite unread retest budget")
    require(packet["client_netns"] == f"/proc/{packet['client_pid']}/ns/net" and
            packet["client_mountns"] == f"/proc/{packet['client_pid']}/ns/mnt" and
            packet["address"] == "10.77.15.10" and packet["port"] == 18443 and
            packet["shared_rf_reservation"] == "durable-both-picos-v1",
            "Frozen unread retest fixture")
    ids = ["inventory_session", "b_session", "network_session", "owner_id",
           "unread_session", "unread_probe", "unread_recovery_session"]
    require(len({identity(packet[key]) for key in ids}) == len(ids),
            "Distinct unread retest identities")
    require(packet["usb"] == {"maximum_payload_bytes": 65536,
            "maximum_wire_bytes": 65552, "parser_write_bytes": 512,
            "parser_write_pause_ms": 15, "unread_max_requests": 1024,
            "unread_write_seconds": 3, "unread_hold_seconds": 12,
            "unread_capture_bytes": 1048576, "silence_seconds": 2},
            "Exact unread retest pressure")
    job = packet["job"]
    identity(job["job_id"])
    require(job == {"case": CASE, "job_id": job["job_id"], "profile": "rf-events/1",
            "mode": "tone", "total_duration_ns": "100000000000",
            "allow_frequency_adjustment": True, "events": [{"offset_ns": "0",
                "duration_ns": "100000000000", "rf_on": True,
                "frequency_nhz": "135500000000000"}]}, "Exact one-job Tone")
    require(packet["credentials"] == {"controller": {
        "ca": "credentials/controller/client-ca.crt",
        "cert": "credentials/controller/client.crt",
        "key": "credentials/controller/client.key"}}, "Frozen controller credentials")
    return packet


def wait_console_running(latest, latest_lock, stop, timeout_seconds=2):
    """Wait for the Console observer to catch up with network Running."""
    deadline = time.monotonic() + timeout_seconds
    last_state = None
    while time.monotonic() < deadline and not stop.is_set():
        with latest_lock:
            sample = latest["info"]
        if sample is not None:
            age = time.monotonic_ns() - sample[0]
            status = sample[1]["status"]
            last_state = status["state"]
            require(status["boot_id"] == BOOT, "Console boot authority")
            if 0 <= age <= 2_000_000_000:
                if status["state"] == "running":
                    require(status["output_active"] is True, "Console Running authority")
                    return
                require(status["state"] in ("empty", "loaded", "armed") and
                        status["output_active"] is False,
                        "Console pre-Running authority")
        stop.wait(.02)
    raise ValueError("Console Running authority; last state: " + str(last_state))


def settle_and_release(root, packet, journal):
    """Bounded cleanup after an armed job outlives a failed observer."""
    path = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02")
    session = hashlib.sha256((packet["network_session"] + ":cleanup-session").encode()
                             ).hexdigest()[:32]
    owner = hashlib.sha256((packet["owner_id"] + ":cleanup-owner").encode()
                           ).hexdigest()[:32]
    reserved = {packet[key] for key in ("inventory_session", "b_session", "network_session",
                "owner_id", "unread_session", "unread_probe", "unread_recovery_session")}
    reserved.add(packet["job"]["job_id"])
    require(session not in reserved and owner not in reserved and session != owner,
            "Distinct deterministic cleanup identities")
    deadline = time.monotonic() + packet["rf_duration_ns"] / 1_000_000_000 + 30
    job_id = packet["job"]["job_id"]
    with exclusive_port(path) as fd:
        peer = usb_peer(fd, packet, journal, session, "unread-retest-cleanup")
        while time.monotonic() < deadline:
            status = peer.request("STATUS")
            journal.emit("cleanup_status", status)
            require(status["boot_id"] == BOOT and status["state"] in
                    ("empty", "loaded", "armed", "running", "complete", "aborted", "missed"),
                    "Unread retest cleanup authority")
            if status["state"] == "empty":
                require(status["output_active"] is False and status["owner_id"] is None and
                        status["job_id"] is None, "Unread retest cleanup Empty authority")
                return status
            require(status["job_id"] == job_id, "Unread retest cleanup job changed")
            if status["state"] in ("loaded", "armed"):
                require(status["output_active"] is False,
                        "Unread retest cleanup inactive pre-launch authority")
            elif status["state"] == "running":
                require(status["output_active"] is True,
                        "Unread retest cleanup Running authority")
            else:
                require(status["output_active"] is False and status["owner_id"] is None and
                        any(record["job_id"] == job_id and record["state"] == status["state"] and
                            record["output_active"] is False
                            for record in status["terminal_records"]),
                        "Unread retest cleanup terminal authority")
                lease = peer.request("CLAIM", {"owner_id": owner, "lease_ms": 60000})
                require(lease["owner_id"] == owner, "Unread retest cleanup CLAIM")
                peer.request("RELEASE")
                final = peer.request("STATUS")
                require(final["state"] == "empty" and final["output_active"] is False and
                        final["owner_id"] is None and final["job_id"] is None,
                        "Unread retest cleanup RELEASE")
                journal.emit("cleanup_released", final)
                return final
            time.sleep(.25)
    raise TimeoutError("Unread retest cleanup did not reach an inactive terminal state")


def run(root, packet):
    os.umask(0o077)
    started = time.monotonic()
    journal = Journal(root / "unread-retest.jsonl")
    stop = threading.Event()
    console_ready = threading.Event()
    running_ready = threading.Event()
    case_done = threading.Event()
    network_done = threading.Event()
    latest_lock = threading.Lock()
    latest = {"info": None}
    faults = []
    result = {"status": "RUNNING", "case": None, "armed_jobs": [],
              "completed_jobs": [], "rf_jobs_charged": 0,
              "rf_duration_ns_charged": 0, "renewals": 0}
    save(root / "unread-retest-result.json", result)
    before = before_b = None
    reservation = None
    final_values = {}

    def record_fault(worker, error, stop_workers=False):
        fault = worker + ": " + type(error).__name__ + ": " + str(error)
        if fault not in faults:
            faults.append(fault)
            journal.emit("failure", {"worker": worker, "type": type(error).__name__,
                                      "error": str(error)})
        if stop_workers:
            stop.set()

    def console_worker():
        try:
            path = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")
            with exclusive_port(path) as fd:
                while not stop.is_set():
                    began = time.monotonic_ns()
                    value = exchange(fd, b"INFO\n", time.monotonic() + 5,
                        lambda kind, body: journal.emit("console_" + kind, {"value": body}), False)
                    validate_info(value, before, packet)
                    with latest_lock:
                        latest["info"] = (time.monotonic_ns(), value)
                    journal.emit("info", {"began_monotonic_ns": began, "value": value})
                    console_ready.set()
                    stop.wait(.25)
        except BaseException as error:
            record_fault("console", error, True)
            running_ready.set()

    def network_worker():
        try:
            require(console_ready.wait(10), "Initial Console observer")
            with NetworkPeer(root, packet, journal) as peer:
                hello = peer.ask("hello", "HELLO", {"versions": ["WTP/1"],
                    "client_name": "Package 4 unread retest", "client_version": "1"})
                require(hello["device_id"] == DEVICE and hello["boot_id"] == BOOT,
                        "Unread retest network identity")
                status = peer.ask("initial", "STATUS")
                require(status["state"] == "empty" and status["owner_id"] is None and
                        status["job_id"] is None and status["output_active"] is False,
                        "Unread retest initial Empty authority")
                lease = peer.ask("claim", "CLAIM",
                    {"owner_id": packet["owner_id"], "lease_ms": 60000})
                require(lease["owner_id"] == packet["owner_id"], "Unread retest CLAIM")
                payload = {key: value for key, value in packet["job"].items() if key != "case"}
                loaded = peer.ask("load", "LOAD", payload)
                require(loaded["job_id"] == packet["job"]["job_id"], "Unread retest LOAD")
                clock = peer.ask("clock", "GET_CLOCK")
                require(clock["state"] == "synchronized" and clock["leap"] == "normal" and
                        int(clock["uncertainty_ns"]) <= 500_000_000,
                        "Unread retest synchronized ARM clock")
                target = ((int(clock["utc_now_ns"]) + 10_000_000_000 + 999) // 1000) * 1000
                result["armed_jobs"].append(packet["job"]["job_id"])
                result["rf_jobs_charged"] = 1
                result["rf_duration_ns_charged"] = 100_000_000_000
                save(root / "unread-retest-result.json", result)
                arm = peer.ask("arm", "ARM", {"job_id": packet["job"]["job_id"],
                    "start_utc_ns": str(target), "max_start_uncertainty_ns": "500000000"})
                require(arm["start_utc_ns"] == str(target), "Unread retest ARM changed start")
                journal.emit("job_armed", {"job": packet["job"],
                                             "start_utc_ns": str(target), "arm": arm})
                last_renew = time.monotonic()
                while not stop.is_set():
                    status = peer.ask("status", "STATUS")
                    journal.emit("network_status", {"case": CASE, "value": status})
                    require(status["boot_id"] == BOOT and
                            status["job_id"] == packet["job"]["job_id"] and
                            status["owner_id"] == packet["owner_id"] and status["state"] in
                            ("armed", "running", "complete"), "Unread retest RF authority")
                    if status["state"] == "running":
                        require(status["output_active"] is True, "Unread retest Running output")
                        wait_console_running(latest, latest_lock, stop)
                        running_ready.set()
                    else:
                        require(status["output_active"] is False, "Unread retest inactive state")
                    if status["state"] == "complete":
                        require(case_done.is_set(), "RF completed before unread action finished")
                        result["completed_jobs"].append(packet["job"]["job_id"])
                        peer.ask("release", "RELEASE")
                        released = peer.ask("released-status", "STATUS")
                        require(released["state"] == "empty" and released["owner_id"] is None and
                                released["job_id"] is None and released["output_active"] is False,
                                "Unread retest RELEASE")
                        journal.emit("job_complete", {"job_id": packet["job"]["job_id"],
                                                      "status": status})
                        save(root / "unread-retest-result.json", result)
                        return
                    if time.monotonic() - last_renew >= 30:
                        require(result["renewals"] < packet["maximum_renewals"],
                                "Unread retest renewal bound")
                        lease = peer.ask("renew", "RENEW",
                            {"owner_id": packet["owner_id"], "lease_ms": 60000})
                        require(lease["owner_id"] == packet["owner_id"], "Unread retest RENEW")
                        result["renewals"] += 1
                        last_renew = time.monotonic()
                    time.sleep(.35)
        except BaseException as error:
            record_fault("network", error, True)
            running_ready.set()
        finally:
            network_done.set()

    try:
        before_b = inventory(root, packet, "before-b", True)
        before = inventory(root, packet, "before-a")
        validate_info(before["info"], before, packet)
        require(before["wtp"]["CAPS"]["max_payload_bytes"] == 65536,
                "Unread retest maximum payload")
        from phase11_5_rf_reservation import Reservation
        reservation = Reservation(digest(root / "packet.json"))
        reservation.acquire({"a": before, "b": before_b})
        save(root / "rf-reservation-acquired.json", json.loads(reservation.path.read_text()))
        journal.emit("start", {"packet_sha256": digest(root / "packet.json"),
            "before_a_sha256": digest(root / "before-a.stdout"),
            "before_b_sha256": digest(root / "before-b.stdout")})
        console_thread = threading.Thread(target=console_worker, name="unread-retest-console")
        network_thread = threading.Thread(target=network_worker, name="unread-retest-network")
        console_thread.start()
        network_thread.start()
        try:
            require(running_ready.wait(45) and not faults, "Unread retest Running gate")
            result["case"] = unread_pressure(packet, journal)
            save(root / "unread-retest-result.json", result)
        except BaseException as error:
            record_fault("supervisor", error)
        finally:
            case_done.set()
        require(network_done.wait(155), "Unread retest finite job completion")
        require(not any(fault.startswith(("network:", "console:")) for fault in faults),
                "Unread retest observer/authority failure")
        if faults:
            result["status"] = "STOPPED_REQUIRES_DIAGNOSIS"
        else:
            require(result["completed_jobs"] == [packet["job"]["job_id"]],
                    "Unread retest local completion")
            result["status"] = "CAPTURED_REQUIRES_AUDIT"
    except BaseException as error:
        record_fault("runner", error, True)
        result["status"] = "STOPPED_REQUIRES_DIAGNOSIS"
        case_done.set()
    finally:
        stop.set()
        for name in ("network_thread", "console_thread"):
            thread = locals().get(name)
            if thread is not None:
                thread.join(10)
        if result["armed_jobs"] and not result["completed_jobs"]:
            try:
                result["cleanup_status"] = settle_and_release(root, packet, journal)
            except BaseException as error:
                record_fault("cleanup", error)
                result["status"] = "STOPPED_FINAL_STATE_UNVERIFIED"
        for label, b in (("final-a", False), ("final-b", True)):
            try:
                value = inventory(root, packet, label, b)
                final_values["b" if b else "a"] = value
                baseline = before_b if b else before
                require(baseline is not None and configuration(value) == configuration(baseline),
                        "Unread retest configuration changed")
                if b:
                    require(value["info"]["revision"] == baseline["info"]["revision"],
                            "Unread retest B changed")
                else:
                    validate_info(value["info"], before, packet)
                result[label] = value["wtp"]["STATUS"]
            except BaseException as error:
                record_fault("final-" + ("b" if b else "a"), error)
                result["status"] = "STOPPED_FINAL_STATE_UNVERIFIED"
        if reservation is not None:
            try:
                if reservation.held and set(final_values) == {"a", "b"}:
                    reservation.release(final_values)
                    save(root / "rf-reservation-released.json",
                         json.loads(reservation.path.read_text()))
            except BaseException as error:
                record_fault("reservation", error)
                result["status"] = "STOPPED_FINAL_STATE_UNVERIFIED"
            finally:
                reservation.close()
        result["faults"] = faults
        result["elapsed_seconds"] = time.monotonic() - started
        journal.emit("finishing", {"elapsed_seconds": result["elapsed_seconds"]})
        save(root / "unread-retest-result.json", result)
        journal.emit("finish", result)
        journal.close()
    require(result["status"] == "CAPTURED_REQUIRES_AUDIT", result["status"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no sockets, USB endpoints, jobs or fixture changes.")
        return
    require(os.geteuid() == 0, "Unread retest runs as root on wspr5")
    root = args.root.resolve(strict=True)
    require(digest(root / "packet.json") == args.packet_sha256, "Frozen unread retest packet")
    packet = validate(json.loads((root / "packet.json").read_text()))
    require(packet["root"] == str(root) and
            Path("/proc/sys/kernel/random/boot_id").read_text().strip() == packet["host_boot_id"] and
            os.readlink("/proc/self/ns/net") == os.readlink(packet["client_netns"]) and
            os.readlink("/proc/self/ns/mnt") == os.readlink(packet["client_mountns"]),
            "Unread retest host/namespaces")
    require(time.monotonic_ns() + (packet["runtime_seconds"] + packet["restoration_seconds"]) *
            1_000_000_000 < packet["fixture_deadline_monotonic_ns"],
            "Unread retest fixture restoration reserve")
    for name, sha in packet["stage_sha256"].items():
        require((root / name).resolve().is_relative_to(root) and digest(root / name) == sha,
                "Unread retest staged input changed")
    for name, spec in packet["remote_copy_inputs"].items():
        require(digest(root / name) == spec["sha256"], "Unread retest private input changed")
    run(root, packet)


if __name__ == "__main__":
    main()
