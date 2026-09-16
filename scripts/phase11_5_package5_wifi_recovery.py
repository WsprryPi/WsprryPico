#!/usr/bin/env python3
"""One guarded inactive Wi-Fi OFF/ON after Package 5 fixture no-route failure."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_package5_http import digest, save
from phase11_5_package5_plan import (RETAINED_BOOT as BOOT, DEVICE,
    RETAINED_IMAGE as IMAGE, RETAINED_SOURCE as SOURCE)


SERIAL = "0BF4B4AEC9FFB344"


def validate(packet):
    require(packet["schema"] == packet["scope"] == "phase11.5-package5-wifi-recovery-v1" and
            (packet["source_revision"], packet["image_sha256"], packet["boot_id"],
             packet["device_id"], packet["serial"]) ==
            (SOURCE, IMAGE, BOOT, DEVICE, SERIAL) and
            packet["hypothesis"] == "After 360 seconds with the retained isolated AP active, Pico A remained addressless at terminal link -3; one inactive OFF/ON restarts acquisition" and
            packet["failed_packet_sha256"] ==
            "713248760e3bdf9c5cfbcb871f315055ef610cd60e328cfaf0e317d3f6e5f92e" and
            packet["runtime_seconds"] == 300 and packet["restoration_seconds"] == 150 and
            packet["maximum_wifi_cycles"] == 1 and packet["rf_jobs"] == packet["flashes"] ==
            packet["configuration_writes"] == packet["controlled_reboots"] == 0,
            "Frozen Package 5 Wi-Fi recovery")
    return packet


def run(root, packet):
    end = time.monotonic() + packet["runtime_seconds"]
    log = (root / "wifi.jsonl").open("x")
    sequence = 0
    result = dict(status="RUNNING", off=0, on=0)

    def emit(kind, value):
        nonlocal sequence
        log.write(json.dumps(dict(sequence=sequence, kind=kind, value=value,
                                  monotonic_ns=time.monotonic_ns(), utc_ns=time.time_ns())) + "\n")
        log.flush()
        os.fsync(log.fileno())
        sequence += 1

    def info(fd, label):
        value = exchange(fd, b"INFO\n", min(end, time.monotonic() + 5), emit, False)
        status = value["status"]
        require(value["device_id"] == DEVICE and value["revision"] == SOURCE[:12] and
                status["boot_id"] == BOOT and status["state"] == "empty" and
                status["output_active"] is False and status["enabled"] is False and
                int(value["allocator_failures"]) == 0 and int(value["tls_allocation_failures"]) == 0,
                "Package 5 Wi-Fi recovery inactive identity")
        emit("info", dict(label=label, value=value))
        return value

    try:
        emit("start", dict(packet_sha256=digest(root / "packet.json")))
        with exclusive_port(Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")) as fd:
            before = info(fd, "before")
            require(before["network"]["enabled"] is True and before["network"]["link_status"] == -3 and
                    before["network"]["ipv4"] == "", "Exact Package 5 no-route prerequisite")
            result["off"] = 1
            save(root / "wifi-result.json", result)
            require(exchange(fd, b"WIFI OFF\n", min(end, time.monotonic() + 5), emit, False) ==
                    dict(ok=True), "Package 5 WIFI OFF rejected")
            for n in range(20):
                value = info(fd, f"off-{n}")
                if value["network"]["enabled"] is False and not value["network"]["withdrawal_pending"]:
                    break
                require(n < 19, "Package 5 WIFI OFF did not settle")
                time.sleep(.5)
            result["on"] = 1
            save(root / "wifi-result.json", result)
            require(exchange(fd, b"WIFI ON\n", min(end, time.monotonic() + 5), emit, False) ==
                    dict(ok=True), "Package 5 WIFI ON rejected")
            final = None
            for n in range(100):
                value = info(fd, f"on-{n}")
                network = value["network"]
                if (network["enabled"] is True and network["link_status"] == 3 and
                        network["ipv4"] == "10.77.15.10" and
                        value["status"]["clock_state"] == "synchronized"):
                    final = value
                    break
                require(n < 99 and time.monotonic() + 2 < end, "Package 5 Wi-Fi recovery deadline")
                time.sleep(2)
            require(final is not None, "Package 5 Wi-Fi recovery missing readiness")
            require(before["status"]["watermark_utc_ns"] == final["status"]["watermark_utc_ns"] and
                    before["status"]["schedules"] == final["status"]["schedules"],
                    "Package 5 Wi-Fi recovery changed saved authority configuration")
        result.update(status="RECOVERED_REQUIRES_AUDIT", final=final)
    except BaseException as error:
        result.update(status="STOPPED_REQUIRES_RECONCILIATION",
                      error=type(error).__name__ + ": " + str(error))
        emit("failure", result["error"])
    finally:
        emit("finish", result)
        log.close()
        save(root / "wifi-result.json", result)
    require(result["status"] == "RECOVERED_REQUIRES_AUDIT", "Package 5 Wi-Fi recovery incomplete")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no host or device access.")
        return
    require(os.geteuid() == 0, "Package 5 Wi-Fi recovery runs as root on wspr5")
    root = args.root.resolve(strict=True)
    require(digest(root / "packet.json") == args.packet_sha256, "Package 5 recovery packet changed")
    packet = validate(json.loads((root / "packet.json").read_text()))
    require(packet["root"] == str(root) and
            time.monotonic_ns() + 450_000_000_000 < packet["fixture_deadline_monotonic_ns"],
            "Package 5 recovery fixture reserve")
    for name, sha in packet["stage_sha256"].items():
        require(digest(root / name) == sha, "Package 5 recovery helper changed")
    run(root, packet)


if __name__ == "__main__":
    main()
