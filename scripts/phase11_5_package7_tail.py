#!/usr/bin/env python3
"""Corrective Package 7 packet for the lost-ABORT tail only."""

import argparse
import contextlib
import json
import os
from pathlib import Path
import time

from phase11_5_inventory import exclusive_port, require
from phase11_5_package7_direct import (Journal, NetworkPeer, console_info, lost,
                                       make_job, status)
from phase11_5_package7_plan import BOOT, DEVICE, SERIAL, validate
from rf_wtp import WtpPeer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no device, network or RF accessed.")
        return
    require(os.geteuid() == 0, "Package 7 tail requires root")
    root = args.root.resolve(strict=True)
    packet = validate(json.loads((root / "packet.json").read_text()))
    require(packet.get("corrective_amendment") is not None, "Corrective amendment absent")
    journal = Journal(root / "tail.jsonl")
    base = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}")
    info = console_info(Path(str(base) + "-if00"), journal)
    require(info["status"]["state"] == "empty" and not info["status"]["output_active"] and
            not info["status"]["enabled"] and info["status"]["clock_state"] == "synchronized",
            "Corrective tail admission")
    owner, job = packet["tail_owner_id"], packet["tail_job_id"]
    peer = NetworkPeer(root, packet, journal)
    peer.session = packet["tail_network_session"]
    try:
        with exclusive_port(Path(str(base) + "-if02")) as fd, \
                (root / "tail-usb-frames.jsonl").open("x") as wire:
            usb = WtpPeer(fd)
            with contextlib.redirect_stdout(wire):
                hello = usb.request("HELLO", {"versions": ["WTP/1"],
                                    "client_name": "phase11-5-package7-tail",
                                    "client_version": "1"})
                require(hello["device_id"] == DEVICE and hello["boot_id"] == BOOT,
                        "Corrective USB identity")
                peer.connect()
                peer.ask("CLAIM", {"owner_id": owner, "lease_ms": 60000})
                peer.ask("LOAD", make_job(job, 12_000_000_000))
                clock = peer.ask("GET_CLOCK")
                require(clock["state"] == "synchronized", "Corrective arm clock")
                peer.ask("ARM", {"job_id": job,
                         "start_utc_ns": str(int(clock["utc_now_ns"]) + 5_000_000_000),
                         "max_start_uncertainty_ns": "500000000"})
                deadline = time.monotonic() + 8
                while True:
                    current = usb.request("STATUS", {})
                    if current["state"] == "running" and current["output_active"] is True:
                        break
                    require(current["state"] == "armed" and time.monotonic() < deadline,
                            "Corrective Running transition")
                    time.sleep(.05)
                running = console_info(Path(str(base) + "-if00"), journal)
                require(running["status"]["state"] == "running" and
                        running["status"]["output_active"] is True,
                        "Corrective Running authority")
                # Consume queued network events before the socket-local receive
                # drop is attached; recv() must measure only the ABORT reply.
                status(peer, "running", job, owner, True)
                peer.ask("PING")
                require(not peer.decoder.buffer, "Corrective network decoder not drained")
                lost(root, peer, usb, journal, "ABORT", {"job_id": job},
                     "aborted", job, owner)
                terminal = status(peer, "aborted", job, owner, False)
                matches = [r for r in terminal["terminal_records"] if r["job_id"] == job]
                require(len(matches) == 1 and matches[0]["state"] == "aborted",
                        "Corrective single aborted terminal")
                peer.ask("RELEASE")
                final = peer.ask("STATUS")
                require(final["state"] == "empty" and final["owner_id"] is None and
                        final["job_id"] is None and final["output_active"] is False,
                        "Corrective tail final idle")
                journal.emit("tail_pass", {"job_id": job, "planned_duration_ns": 12_000_000_000,
                             "terminal": matches[0], "final": final})
    finally:
        try:
            if peer.stream is not None:
                current = peer.ask("STATUS")
                if current.get("owner_id") == owner:
                    if (current.get("job_id") and current["state"] not in
                            ("complete", "aborted", "failed", "missed")):
                        peer.ask("ABORT", {"job_id": current["job_id"]})
                    peer.ask("RELEASE")
        finally:
            peer.close()
            journal.emit("tail_cleanup", console_info(Path(str(base) + "-if00"), journal))
            journal.close()


if __name__ == "__main__":
    main()
