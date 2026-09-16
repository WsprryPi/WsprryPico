#!/usr/bin/env python3
"""Run the single authorized inactive Wi-Fi recovery for Package 5 continuation."""
import argparse
import json
import os
from pathlib import Path
import time

from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_package5_http import digest, save
from phase11_5_package5_plan import BOOT, DEVICE, IMAGE, SOURCE


SERIAL = "0BF4B4AEC9FFB344"
POLICY = "phase11.5-package5-continuation-wifi-recovery-v1"
BLOCKED_FIXTURE_PACKET = "8b63bd2b0a2f337559d034907e181eeeff2fc92740cddcbb2ed140e3a5af882d"
ACTIVE_FIXTURE_PACKET = "a8aaf885a1112489a680593b12e4d60d8bcfb5552a15378e7561914d6b409dbd"
HYPOTHESIS = (
    "After a 300-second passive wait with the replacement isolated AP active, "
    "Pico A remained enabled, link -3, addressless, and unsynchronized; one "
    "inactive OFF/ON cycle restarts acquisition"
)


def validate(packet):
    require(packet["schema"] == packet["scope"] == POLICY and
            (packet["source_revision"], packet["image_sha256"], packet["boot_id"],
             packet["device_id"], packet["serial"]) ==
            (SOURCE, IMAGE, BOOT, DEVICE, SERIAL) and
            packet["hypothesis"] == HYPOTHESIS and
            packet["blocked_fixture_packet_sha256"] == BLOCKED_FIXTURE_PACKET and
            packet["active_fixture_packet_sha256"] == ACTIVE_FIXTURE_PACKET and
            packet["runtime_seconds"] == 300 and packet["restoration_seconds"] == 150 and
            packet["maximum_wifi_cycles"] == packet["wifi_cycles"] == 1 and
            packet["rf_jobs"] == packet["flashes"] == packet["configuration_writes"] ==
            packet["controlled_reboots"] == 0,
            "Frozen Package 5 continuation Wi-Fi recovery")
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
                int(value["allocator_failures"]) == 0 and
                int(value["tls_allocation_failures"]) == 0,
                "Package 5 continuation Wi-Fi recovery inactive identity")
        emit("info", dict(label=label, value=value))
        return value

    try:
        emit("start", dict(packet_sha256=digest(root / "packet.json")))
        with exclusive_port(Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")) as fd:
            before = info(fd, "before")
            require(before["network"]["enabled"] is True and
                    before["network"]["link_status"] == -3 and
                    before["network"]["ipv4"] == "" and
                    before["status"]["clock_state"] == "unsynchronized",
                    "Exact Package 5 continuation no-route prerequisite")
            result["off"] = 1
            save(root / "wifi-result.json", result)
            require(exchange(fd, b"WIFI OFF\n", min(end, time.monotonic() + 5), emit, False) ==
                    dict(ok=True), "Package 5 continuation WIFI OFF rejected")
            for n in range(20):
                value = info(fd, f"off-{n}")
                if value["network"]["enabled"] is False and not value["network"]["withdrawal_pending"]:
                    break
                require(n < 19, "Package 5 continuation WIFI OFF did not settle")
                time.sleep(.5)
            result["on"] = 1
            save(root / "wifi-result.json", result)
            require(exchange(fd, b"WIFI ON\n", min(end, time.monotonic() + 5), emit, False) ==
                    dict(ok=True), "Package 5 continuation WIFI ON rejected")
            final = None
            for n in range(100):
                value = info(fd, f"on-{n}")
                network = value["network"]
                if (network["enabled"] is True and network["link_status"] == 3 and
                        network["ipv4"] == "10.77.15.10" and
                        value["status"]["clock_state"] == "synchronized"):
                    final = value
                    break
                require(n < 99 and time.monotonic() + 2 < end,
                        "Package 5 continuation Wi-Fi recovery deadline")
                time.sleep(2)
            require(final is not None, "Package 5 continuation Wi-Fi recovery missing readiness")
            require(before["status"]["watermark_utc_ns"] == final["status"]["watermark_utc_ns"] and
                    before["status"]["schedules"] == final["status"]["schedules"],
                    "Package 5 continuation Wi-Fi recovery changed saved authority configuration")
        result.update(status="RECOVERED_REQUIRES_AUDIT", final=final)
    except BaseException as error:
        result.update(status="STOPPED_REQUIRES_RECONCILIATION",
                      error=type(error).__name__ + ": " + str(error))
        emit("failure", result["error"])
    finally:
        emit("finish", result)
        log.close()
        save(root / "wifi-result.json", result)
    require(result["status"] == "RECOVERED_REQUIRES_AUDIT",
            "Package 5 continuation Wi-Fi recovery incomplete")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no host or device access.")
        return
    require(os.geteuid() == 0, "Package 5 continuation Wi-Fi recovery runs as root on wspr5")
    root = args.root.resolve(strict=True)
    require(digest(root / "packet.json") == args.packet_sha256,
            "Package 5 continuation recovery packet changed")
    packet = validate(json.loads((root / "packet.json").read_text()))
    require(packet["root"] == str(root) and
            time.monotonic_ns() + 450_000_000_000 < packet["fixture_deadline_monotonic_ns"],
            "Package 5 continuation recovery fixture reserve")
    for name, sha in packet["stage_sha256"].items():
        path = (root / name).resolve()
        require(path.is_relative_to(root) and digest(path) == sha,
                "Package 5 continuation recovery helper changed")
    run(root, packet)


if __name__ == "__main__":
    main()
