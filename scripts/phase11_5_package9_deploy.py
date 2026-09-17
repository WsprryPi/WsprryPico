#!/usr/bin/env python3
"""One-flash Package 9 repair deployment with held RF reconciliation."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_rf_reservation import Reservation


SERIAL = "0BF4B4AEC9FFB344"
DEVICE = "fd6127d11d6aca42a9905fa3fb1bf1d5"
B_SERIAL = "CDDBF8767C506C07"
B_DEVICE = "29f20b7342051ef947aa56cb9d4fab42"
PICOTOOL = Path("/home/pi/phase11-4-e1/picotool-build/picotool")
PICOTOOL_SHA256 = "4a68cfd7fc36002e80857802c8192c9f24c751357c6cb26ad13ad7f38c227921"
HOST_BOOT = "220e53ca-ca95-4206-9581-dbe28aa1eeb8"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def finished(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines()]
    row = next((row for row in reversed(rows) if row.get("kind") == "finish"), None)
    require(row is not None and row["value"]["result"] == "READ_ONLY_INVENTORY",
            "Inventory did not finish")
    return row["value"]


def run_inventory(root, name, serial, device):
    output = root / f"{name}.jsonl"
    error = root / f"{name}.stderr"
    with output.open("xb") as stdout, error.open("xb") as stderr:
        result = subprocess.run([
            sys.executable, str(root / "scripts/phase11_5_inventory.py"),
            "--serial", serial, "--device-id", device,
            "--session-id", uuid.uuid4().hex, "--run"],
            stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, timeout=90)
        stdout.flush()
        os.fsync(stdout.fileno())
        stderr.flush()
        os.fsync(stderr.fileno())
    require(result.returncode == 0, name + " failed")
    return finished(output)


def inactive(value):
    info, status = value["info"], value["wtp"]["STATUS"]
    require(status["state"] in ("empty", "complete", "aborted", "missed") and
            status["output_active"] is False and status["owner_id"] is None and
            info["status"]["enabled"] is False and
            info["status"]["output_active"] is False,
            "Deployment requires inactive, unowned and schedule-disabled state")


def configuration(value):
    status = value["info"]["status"]
    return {key: status[key] for key in (
        "station", "schedules", "schedule_base_frequency_nhz", "storage_healthy",
        "watermark_utc_ns")}


def enter_bootsel():
    path = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")
    with exclusive_port(path) as fd:
        response = exchange(fd, b"BOOTSEL\n", time.monotonic() + 10,
                            lambda _kind, _value: None, False)
    require(response.get("ok") is True and response.get("rebooting") is True,
            "BOOTSEL was not acknowledged")
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        for serial in Path("/sys/bus/usb/devices").glob("*/serial"):
            try:
                if (serial.read_text().strip().upper() == SERIAL and
                        (serial.parent / "idVendor").read_text().strip() == "2e8a" and
                        (serial.parent / "idProduct").read_text().strip() == "000f"):
                    return
            except OSError:
                pass
        time.sleep(.2)
    raise ValueError("Serial-specific BOOTSEL enumeration missing")


def picotool(root, label, *arguments):
    with (root / f"{label}.stdout").open("xb") as stdout, \
            (root / f"{label}.stderr").open("xb") as stderr:
        result = subprocess.run([str(PICOTOOL), *map(str, arguments)],
                                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                timeout=180)
        stdout.flush()
        os.fsync(stdout.fileno())
        stderr.flush()
        os.fsync(stderr.fileno())
    require(result.returncode == 0, label + " failed")


def wait_application():
    path = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not path.exists():
        time.sleep(.2)
    require(path.exists(), "Application USB did not enumerate")
    time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        parser.error("--run requires explicit deployment authorization")
    require(sys.platform.startswith("linux") and os.geteuid() == 0,
            "Run as root on the bound host")
    root = args.root.resolve()
    packet_path = root / "packet.json"
    packet = json.loads(packet_path.read_text())
    require(digest(packet_path) == args.packet_sha256 and
            packet["schema"] == "phase11.5-package9-repair-deployment-v5" and
            packet["source_revision"] == "91933c00970939e366d1bfcf3c1956b59be8f6c5" and
            packet["source_revision"][:12] == "91933c009709" and
            packet["image_sha256"] == digest(root / "candidate.uf2") and
            packet["image_sha256"] ==
            "5da240aacf20e27db79126a7bff2be18e4ece849a608fa439f4e0c577659f446" and
            packet["flashes"] == packet["bootsel"] == 1 and packet["rf_jobs"] == 0 and
            packet["repair_attempt"] == packet["cumulative_flashes"] == 5,
            "Frozen deployment packet")
    require(Path("/proc/sys/kernel/random/boot_id").read_text().strip() == HOST_BOOT and
            digest(PICOTOOL) == PICOTOOL_SHA256, "Bound host or picotool changed")

    before = {
        "a": run_inventory(root, "before-a", SERIAL, DEVICE),
        "b": run_inventory(root, "before-b", B_SERIAL, B_DEVICE),
    }
    for value in before.values():
        inactive(value)
    require(before["a"]["info"]["revision"] == "91933c009709" and
            before["a"]["wtp"]["STATUS"]["boot_id"] ==
                "62db69d84d44022100c311ab8e5acd46" and
            before["b"]["info"]["revision"] == "8921a7008183",
            "Unexpected predeployment revision")
    old_boot = before["a"]["wtp"]["STATUS"]["boot_id"]
    b_boot = before["b"]["wtp"]["STATUS"]["boot_id"]
    accepted_configuration = {
        "station": {"callsign": "AA0NT", "locator": "EM18", "power_dbm": 20},
        "schedules": [{"period_s": 120, "phase_s": 0}],
        "schedule_base_frequency_nhz": "135500000000000",
        "storage_healthy": True,
        "watermark_utc_ns": "1789607761000000000",
    }

    reservation = Reservation(args.packet_sha256)
    reservation.acquire(before)
    save(root / "reservation-acquired.json", json.loads(reservation.path.read_text()))
    reservation.close()

    enter_bootsel()
    picotool(root, "before-flash-save", "save", "-a", "-v", root / "before-flash.bin",
             "-t", "bin", "--ser", SERIAL)
    picotool(root, "candidate-load", "load", "-v", "-x", root / "candidate.uf2",
             "--ser", SERIAL)
    wait_application()

    after = {
        "a": run_inventory(root, "after-a", SERIAL, DEVICE),
        "b": run_inventory(root, "after-b", B_SERIAL, B_DEVICE),
    }
    for value in after.values():
        inactive(value)
    new_boot = after["a"]["wtp"]["STATUS"]["boot_id"]
    require(new_boot != old_boot and after["a"]["info"]["revision"] == "91933c009709" and
            after["a"]["info"]["system_clock_hz"] == 138000000 and
            after["a"]["info"]["status"]["engine"] == "pio-dma-gp2" and
            after["a"]["info"]["rf_render_in_ram"] is True and
            configuration(after["a"]) == accepted_configuration and
            after["a"]["info"]["network"]["control_configured"] is True and
            after["a"]["info"]["network"]["control_listening"] is True and
            after["a"]["info"]["network"]["configured_hostname"] ==
                "wsprrypico-0a60df.local",
            "Candidate identity, engine or retained configuration")
    require(after["b"]["wtp"]["STATUS"]["boot_id"] == b_boot and
            after["b"]["info"]["revision"] == before["b"]["info"]["revision"],
            "Comparator changed")

    reservation = Reservation(args.packet_sha256,
        reconciliation=(after, time.monotonic_ns()),
        authorized_boot_changes={"a": (old_boot, new_boot)})
    reservation.release(after)
    save(root / "reservation-released.json", json.loads(reservation.path.read_text()))
    reservation.close()
    # Preserve v36's local count exactly. It omitted the separately named first
    # static-page deployment; audit_phase11_5_package9_attempts.py reports the
    # corrected six-flash aggregate without rewriting the frozen packet.
    save(root / "deployment.json", {
        "result": "PASS", "source_revision": packet["source_revision"],
        "image_sha256": packet["image_sha256"], "packet_sha256": args.packet_sha256,
        "before_boot_id": old_boot, "after_boot_id": new_boot,
        "comparator_boot_id": b_boot, "before_flash_sha256": digest(root / "before-flash.bin"),
        "accepted_configuration_restored": True, "network_identity_configured": True,
        "reservation_released": True, "repair_attempt": 5,
        "cumulative_flashes": 5, "flashes": 1, "bootsel": 1, "rf_jobs": 0})


if __name__ == "__main__":
    main()
