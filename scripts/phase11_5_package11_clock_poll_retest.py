#!/usr/bin/env python3
"""Prove the repaired Package 11 clock poll catches one fresh SNTP window."""

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
import phase11_5_package11_admission as admission


MINIMUM_INITIAL_AGE_NS = 20_000_000_000
PROBE_SECONDS = 90
ROUTE_SECONDS = 120
READ_ONLY_OPERATIONS = frozenset(("HELLO", "CAPS", "STATUS", "GET_CLOCK"))


class Journal:
    def __init__(self, path):
        self.inner = package9.Journal(path)
        self.rows = []

    def emit(self, kind, value):
        self.rows.append((kind, value))
        self.inner.emit(kind, value)

    def close(self):
        self.inner.close()


def wait_until_stale(root, packet, journal):
    peer = None
    route_deadline = time.monotonic() + ROUTE_SECONDS
    while peer is None:
        try:
            peer = package9.NetworkPeer(root, packet, journal,
                                        packet["readiness_sessions"][0]).connect()
        except (OSError, TimeoutError) as error:
            journal.emit("clock_poll_route_wait", {"error_type": type(error).__name__})
            require(time.monotonic() < route_deadline,
                    "Clock-poll route/listener readiness deadline")
            time.sleep(2)
    deadline = time.monotonic() + PROBE_SECONDS
    try:
        while time.monotonic() < deadline:
            status = peer.ask("STATUS")
            clock = peer.ask("GET_CLOCK")
            require(status["boot_id"] == package10.BOOT and
                    status["owner_id"] is None and status["output_active"] is False and
                    clock["state"] == "synchronized" and clock["leap"] == "normal",
                    "Clock-poll retest inactive synchronized baseline")
            age = int(clock["sync_age_ns"])
            journal.emit("clock_poll_precondition", {"sync_age_ns": age,
                "uncertainty_ns": int(clock["uncertainty_ns"]),
                "minimum_age_ns": MINIMUM_INITIAL_AGE_NS})
            if age >= MINIMUM_INITIAL_AGE_NS:
                return clock
            time.sleep(2)
    finally:
        peer.close()
    raise TimeoutError("Clock-poll stale precondition deadline")


def accepted_clock_poll(initial, readiness, requests, reservation_unchanged):
    """Accept a stale-to-fresh observation made with read-only WTP requests."""
    return (int(initial["sync_age_ns"]) >= MINIMUM_INITIAL_AGE_NS and
            bool(readiness) and readiness[-1]["usable"] is True and
            int(readiness[-1]["clock_sync_age_ns"]) <= package9.FRESH_CLOCK_AGE_NS and
            bool(requests) and set(requests) <= READ_ONLY_OPERATIONS and
            "STATUS" in requests and "GET_CLOCK" in requests and
            reservation_unchanged)


def run(root, packet, journal):
    reservation = Path("/home/pi/phase11-5-shared-rf-reservation.json")
    before = reservation.read_bytes()
    require(json.loads(before)["state"] == "RELEASED", "Clock-poll reservation baseline")
    initial = wait_until_stale(root, packet, journal)
    began = time.monotonic_ns()
    package9.wait_for_normalizer_readiness(root, packet, journal,
        packet["readiness_sessions"][1], "clock-poll-retest", PROBE_SECONDS)
    ended = time.monotonic_ns()
    readiness = [value for kind, value in journal.rows
                 if kind == "normalizer_network_readiness" and
                 value["label"] == "clock-poll-retest"]
    requests = [value["request"]["op"] for kind, value in journal.rows
                if kind == "normalizer_tx"]
    require(accepted_clock_poll(initial, readiness, requests,
                                reservation.read_bytes() == before),
            "Clock-poll read-only fresh-window result")
    result = {"schema": "phase11.5-package11-clock-poll-retest-v1",
        "status": "PASS_ZERO_RF", "packet_sha256": package10.digest(root / "packet.json"),
        "initial_sync_age_ns": int(initial["sync_age_ns"]),
        "fresh_sync_age_ns": int(readiness[-1]["clock_sync_age_ns"]),
        "elapsed_ns": ended - began, "readiness_attempts": len(readiness),
        "request_ops": requests, "rf_jobs": 0, "rf_duration_ns": 0,
        "reservation_unchanged_sha256": package10.digest(reservation)}
    (root / "clock-poll-retest-result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


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
            package10.digest(root / "packet.json") == args.packet_sha256 and
            os.readlink("/proc/self/ns/net") != os.readlink("/proc/1/ns/net") and
            os.readlink("/proc/self/ns/mnt") != os.readlink("/proc/1/ns/mnt"),
            "Private clock-poll root/namespaces")
    packet = admission.validate(json.loads((root / "packet.json").read_text()))
    require(packet["root"] == str(root), "Clock-poll packet root")
    journal = Journal(root / "clock-poll-retest.jsonl")
    service_active = subprocess.run([*package9.HOST_SYSTEMCTL, "is-active", "--quiet",
        "wsprrypi.service"]).returncode == 0
    require(service_active, "Clock-poll installed service baseline")
    subprocess.run([*package9.HOST_SYSTEMCTL, "stop", "wsprrypi.service"],
                   check=True, timeout=15)
    try:
        journal.emit("start", {"packet_sha256": args.packet_sha256})
        result = run(root, packet, journal)
        journal.emit("finish", result)
        print(json.dumps(result, indent=2))
    except BaseException as error:
        journal.emit("failure", {"type": type(error).__name__, "error": str(error)})
        raise
    finally:
        subprocess.run([*package9.HOST_SYSTEMCTL, "start", "wsprrypi.service"],
                       check=False, timeout=15)
        journal.close()


if __name__ == "__main__":
    main()
