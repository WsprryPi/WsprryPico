#!/usr/bin/env python3
"""Correct one misselected Package 5 image while its RF reservation stays held."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time

from phase11_5_device_management import digest, save
from phase11_5_inventory import require
from phase11_5_load_reply_target import Journal, inventory, healthy
from phase11_5_pilot import DEVICE, SERIAL
from phase11_5_pilot_supervisor import PICOTOOL, PICOTOOL_SHA, configuration, finished
from phase11_5_r3_allocation_diagnostic import request_bootsel
from phase11_5_r3_v2_admission import candidate
from phase11_5_rf_reservation import BOARDS, PATH as RESERVATION_PATH, inactive

SCOPE = "phase115-package5-corrective-rf-deploy-v1"
WRONG_SOURCE = "f2b933ba407d"
WRONG_BOOT = "cadc0100a41f1cbbcfeadc702e2783a0"
ORIGINAL_PACKET = "050dfe6b51f6b08672ad6778c1aa4588bd0f2c00be048717c2e64d0f1acb8af3"


def validate(packet):
    require(packet["scope"] == SCOPE and packet["serial"] == SERIAL and
            packet["device_id"] == DEVICE and packet["prior_revision"] == WRONG_SOURCE and
            packet["prior_boot"] == WRONG_BOOT and
            packet["original_reservation_packet_sha256"] == ORIGINAL_PACKET and
            re.fullmatch(r"[0-9a-f]{40}", packet["source_revision"]) and
            re.fullmatch(r"[0-9a-f]{64}", packet["image_sha256"]),
            "Exact corrective deployment identity")
    require(packet["limits"] == {"flashes": 1, "bootsel": 1, "rf_jobs": 0,
            "loads": 0, "arm": 0, "reboots": 0, "wifi_cycles": 0,
            "configuration_writes": 0} and packet["runtime_seconds"] == 300 and
            packet["cleanup_seconds"] == 150, "Exact corrective budget")
    require(packet["work_deadline_monotonic_ns"] - packet["start_monotonic_ns"] ==
            300_000_000_000 and packet["cleanup_deadline_monotonic_ns"] -
            packet["work_deadline_monotonic_ns"] == 150_000_000_000,
            "Frozen corrective deadlines")
    return packet


def atomic_release(packet_sha, corrective_sha, values, transition):
    lock_path = Path(str(RESERVATION_PATH) + ".lock")
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous = json.loads(RESERVATION_PATH.read_text())
        require(previous["state"] == "HELD" and
                previous["packet_sha256"] == packet_sha and
                previous["host_boot"] == Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                "Exact unresolved original reservation")
        value = {
            "state": "RELEASED",
            "packet_sha256": packet_sha,
            "corrective_packet_sha256": corrective_sha,
            "boards": inactive(values),
            "host_boot": previous["host_boot"],
            "monotonic_ns": time.monotonic_ns(),
            "utc_ns": time.time_ns(),
            "transition": transition,
        }
        temporary = RESERVATION_PATH.with_suffix(".tmp")
        raw = (json.dumps(value, sort_keys=True) + "\n").encode()
        out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(out, "wb") as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, RESERVATION_PATH)
            directory = os.open(RESERVATION_PATH.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if temporary.exists():
                temporary.unlink()
        return value
    finally:
        os.close(fd)


def run(root, packet, packet_sha):
    require(os.geteuid() == 0 and str(root) == packet["root"] and
            Path("/proc/sys/kernel/random/boot_id").read_text().strip() == packet["host_boot_id"],
            "Host/root identity")
    for name, expected in packet["stage_sha256"].items():
        path = (root / name).resolve()
        require(path.is_relative_to(root) and digest(path) == expected, "Frozen helper: " + name)
    require(digest(PICOTOOL) == PICOTOOL_SHA and digest(root / "candidate.uf2") ==
            packet["image_sha256"], "Pinned flash tool and RF image")
    original = Path(packet["original_root"])
    prior_deployment = json.loads((original / "deployment.json").read_text())
    require(prior_deployment == {"bootsel_commands": 1, "flashes_started": 1,
            "status": "STOPPED_REQUIRES_RECONCILIATION",
            "error": "Extended candidate identity/capacity/resource"},
            "Exact preserved misdeployment failure")
    original_before = {
        board: finished(original / f"before-{board}.stdout", "READ_ONLY_INVENTORY")
        for board in BOARDS
    }
    end = packet["work_deadline_monotonic_ns"]
    def check():
        require(time.monotonic_ns() < end, "Corrective deployment deadline")
    emit = Journal(root / "deploy.jsonl")
    state = {"bootsel_commands": 0, "flashes_started": 0, "status": "STARTED"}
    save(root / "deployment.json", state)
    try:
        before = {b: inventory(root, packet, "before-" + b, b == "b") for b in BOARDS}
        inactive(before)
        info = before["a"]["info"]
        require(info["revision"] == WRONG_SOURCE and
                before["a"]["wtp"]["STATUS"]["boot_id"] == WRONG_BOOT and
                info["system_clock_hz"] == 150_000_000 and
                info["status"]["engine"] == "inhibited-standalone-simulator" and
                configuration(before["a"]) == configuration(original_before["a"]) and
                before["b"]["wtp"]["STATUS"] == original_before["b"]["wtp"]["STATUS"] and
                configuration(before["b"]) == configuration(original_before["b"]),
                "Exact inactive misselected image and unchanged comparator")
        held = json.loads(RESERVATION_PATH.read_text())
        require(held["state"] == "HELD" and held["packet_sha256"] == ORIGINAL_PACKET,
                "Original reservation remains held")
        check(); state["bootsel_commands"] = 1; save(root / "deployment.json", state)
        emit("bootsel_intent", state); request_bootsel(emit)
        until = time.monotonic() + 15; found = False
        while time.monotonic() < until:
            for serial in Path("/sys/bus/usb/devices").glob("*/serial"):
                try:
                    found |= (serial.read_text().strip().upper() == SERIAL and
                              (serial.parent / "idVendor").read_text().strip() == "2e8a" and
                              (serial.parent / "idProduct").read_text().strip() == "000f")
                except OSError:
                    pass
            if found:
                break
            time.sleep(.2)
        require(found, "Named A bootloader absent; no retry"); check()
        state["flashes_started"] = 1; save(root / "deployment.json", state)
        with (root / "flash.stdout").open("xb") as out, (root / "flash.stderr").open("xb") as err:
            result = subprocess.run([str(PICOTOOL), "load", "-v", "-x",
                str(root / "candidate.uf2"), "--ser", SERIAL], stdout=out, stderr=err, timeout=60)
        require(result.returncode == 0, "Corrective flash failed; no retry")
        until = time.monotonic() + 15
        serial_path = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")
        while not serial_path.exists() and time.monotonic() < until:
            time.sleep(.2)
        check()
        after = {b: inventory(root, packet, "final-" + b, b == "b") for b in BOARDS}
        boot = candidate(after["a"], packet)
        healthy(after["a"]["info"], boot, packet["source_revision"])
        require(boot != WRONG_BOOT and
                all(configuration(after[b]) == configuration(original_before[b]) for b in BOARDS) and
                after["b"]["wtp"]["STATUS"] == original_before["b"]["wtp"]["STATUS"],
                "Correct RF image, preserved configurations and comparator")
        transition = {"from_boot": WRONG_BOOT, "to_boot": boot,
                      "from_revision": WRONG_SOURCE,
                      "to_revision": packet["source_revision"][:12],
                      "from_image_sha256": packet["wrong_image_sha256"],
                      "to_image_sha256": packet["image_sha256"]}
        released = atomic_release(ORIGINAL_PACKET, packet_sha, after, transition)
        save(root / "reservation-released.json", released)
        state.update(status="CORRECTIVE_RF_IMAGE_VERIFIED", boot_id=boot)
        save(root / "deployment.json", state); emit("finish", state)
    except BaseException as error:
        state.update(status="STOPPED_REQUIRES_RECONCILIATION", error=str(error))
        save(root / "deployment.json", state); emit("failure", state)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no device access."); return
    root = args.root.resolve(strict=True)
    require(digest(root / "packet.json") == args.packet_sha256, "Exact corrective packet")
    run(root, validate(json.loads((root / "packet.json").read_text())), args.packet_sha256)


if __name__ == "__main__":
    main()
