#!/usr/bin/env python3
"""Focused authenticated GET status after the retained harness-only POST failure."""
import argparse
import json
import os
from pathlib import Path
import time

from phase11_5_inventory import require
from phase11_5_package5_http import digest, get_status, save
from phase11_5_package5_plan import BOOT, DEVICE, IMAGE, NAME, PEER, SOURCE


FAILED = "2039a76c119c23ebd7cdf36e8052252e58b9fc4b5a7d3283b51018690c829ccc"


def validate(packet):
    require(packet["schema"] == packet["scope"] == "phase11.5-package5-status-confirm-v1" and
            (packet["source_revision"], packet["image_sha256"], packet["boot_id"],
             packet["device_id"]) == (SOURCE, IMAGE, BOOT, DEVICE) and
            packet["retained_packet_sha256"] == FAILED and packet["runtime_seconds"] == 30 and
            packet["rf_jobs"] == packet["flashes"] == packet["configuration_writes"] ==
            packet["controlled_reboots"] == packet["wifi_cycles"] == 0,
            "Frozen Package 5 status confirmation")
    return packet


def run(root, packet):
    require(os.readlink("/proc/self/ns/net") == packet["client_netns"] and
            os.readlink("/proc/self/ns/mnt") == packet["client_mountns"],
            "Package 5 status confirmation namespace")
    log = (root / "status.jsonl").open("x")
    sequence = 0

    def emit(kind, value):
        nonlocal sequence
        log.write(json.dumps(dict(sequence=sequence, kind=kind, value=value,
                                  monotonic_ns=time.monotonic_ns(), utc_ns=time.time_ns())) + "\n")
        log.flush()
        os.fsync(log.fileno())
        sequence += 1

    result = dict(status="RUNNING")
    try:
        emit("start", dict(packet_sha256=digest(root / "packet.json")))
        value = get_status(root, packet, emit, name=NAME, peer_sha=PEER, device=DEVICE)
        job = value["job"]
        require(job["state"] == "empty" and job["output_active"] is False and
                job["owner_id"] is None and job["job_id"] is None,
                "Package 5 retained final authenticated authority")
        result.update(status="CAPTURED_REQUIRES_AUDIT", job=job)
    except BaseException as error:
        result.update(status="STOPPED_REQUIRES_DIAGNOSIS",
                      error=type(error).__name__ + ": " + str(error))
        emit("failure", result["error"])
    finally:
        emit("finish", result)
        log.close()
        save(root / "status-result.json", result)
    require(result["status"] == "CAPTURED_REQUIRES_AUDIT", "Package 5 status confirmation incomplete")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no network or device access.")
        return
    root = args.root.resolve(strict=True)
    require(os.geteuid() == 0 and digest(root / "packet.json") == args.packet_sha256,
            "Package 5 status root/packet")
    packet = validate(json.loads((root / "packet.json").read_text()))
    for name, sha in packet["stage_sha256"].items():
        require(digest(root / name) == sha, "Package 5 status helper changed")
    run(root, packet)


if __name__ == "__main__":
    main()
