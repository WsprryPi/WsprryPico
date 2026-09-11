#!/usr/bin/env python3
"""Opt-in restoration of the specific preserved P1b fault; never resumes RF."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_pilot_supervisor import (B_DEVICE, B_SERIAL, DEVICE, SERIAL, PICOTOOL,
                                      PICOTOOL_SHA, RESTORE_SHA, RESTORE_REVISION,
                                      configuration, finished, idle)

BOOT = "dd156859a9a87dc6d0fcd161bb30518d"
JOB = "ec30945b745c408d950b46d48f0cbd38"
HOST_BOOT = "220e53ca-ca95-4206-9581-dbe28aa1eeb8"
HERE = Path(__file__).resolve().parent


def admission(current, original, comparator, original_comparator):
    status, info = current["wtp"]["STATUS"], current["info"]
    require(info["device_id"] == DEVICE and info["revision"] == "ce1c339a976e" and
            info["system_clock_hz"] == 138000000 and info["status"]["engine"] == "pio-dma-gp2",
            "faulted candidate identity changed")
    require(status["boot_id"] == BOOT == info["status"]["boot_id"] and
            status["state"] == info["status"]["state"] == "failed" and
            status["output_active"] is False and info["status"]["output_active"] is False and
            status["owner_id"] is None and status["job_id"] == JOB and
            not info["recovery_boot"] and info["status"]["storage_healthy"] is True and
            info["status"]["enabled"] is False, "not the preserved inactive unowned fault")
    require(len(status["terminal_records"]) == 1 and
            status["terminal_records"][0]["job_id"] == JOB and
            status["terminal_records"][0]["state"] == "failed" and
            status["terminal_records"][0]["output_active"] is False and
            status["terminal_records"][0]["error"]["code"] == "DEVICE_FAULT", "terminal changed")
    idle(comparator)
    require(comparator["wtp"]["STATUS"]["boot_id"] == original_comparator["wtp"]["STATUS"]["boot_id"]
            and comparator["info"]["revision"] == original_comparator["info"]["revision"],
            "comparator changed")
    require(configuration(current) == configuration(original) and
            configuration(comparator) == configuration(original_comparator), "configuration changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restoration", type=Path, required=True)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    require(hashlib.sha256(args.restoration.read_bytes()).hexdigest() == RESTORE_SHA, "restore image changed")
    original = finished(args.prior / "before-a.stdout", "READ_ONLY_INVENTORY")
    original_b = finished(args.prior / "before-b.stdout", "READ_ONLY_INVENTORY")
    if not args.run:
        print("Restoration image and preserved baseline valid; no hardware accessed")
        return
    require(sys.platform.startswith("linux") and os.geteuid() == 0, "wspr5 root required")
    require(Path("/proc/sys/kernel/random/boot_id").read_text().strip() == HOST_BOOT, "host boot changed")
    require(hashlib.sha256(PICOTOOL.read_bytes()).hexdigest() == PICOTOOL_SHA, "flash tool changed")
    os.umask(0o077)
    args.evidence.mkdir(mode=0o700, exist_ok=False)
    with (args.evidence / "events.jsonl").open("x") as log:
        sequence = 0
        def emit(kind, value):
            nonlocal sequence
            log.write(json.dumps(dict(sequence=sequence, kind=kind, utc_ns=time.time_ns(),
                                      monotonic_ns=time.monotonic_ns(), value=value)) + "\n")
            log.flush(); os.fsync(log.fileno()); sequence += 1
        def run(label, argv, timeout):
            emit("command_start", dict(label=label, argv=[str(x) for x in argv]))
            with (args.evidence / (label + ".stdout")).open("xb") as out, (args.evidence / (label + ".stderr")).open("xb") as err:
                r = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=timeout)
                out.flush(); err.flush(); os.fsync(out.fileno()); os.fsync(err.fileno())
            emit("command_exit", dict(label=label, returncode=r.returncode))
            require(r.returncode == 0, "command failed; no retry")
        def inventory(label, serial=SERIAL, device=DEVICE):
            run(label, [sys.executable, HERE / "phase11_5_inventory.py", "--serial", serial,
                        "--device-id", device, "--run"], 65)
            return finished(args.evidence / (label + ".stdout"), "READ_ONLY_INVENTORY")
        emit("start", dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                           restoration_sha256=RESTORE_SHA, boot=BOOT, job=JOB))
        try:
            current = inventory("before-a")
            comparator = inventory("before-b", B_SERIAL, B_DEVICE)
            admission(current, original, comparator, original_b)
            with exclusive_port(Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")) as fd:
                reply = exchange(fd, b"BOOTSEL\n", time.monotonic() + 5, emit, False)
                require(reply.get("ok") is True and reply.get("rebooting") is True, "BOOTSEL not acknowledged")
            end = time.monotonic() + 15
            matched = False
            while not matched and time.monotonic() < end:
                for path in Path("/sys/bus/usb/devices").glob("*/serial"):
                    try:
                        matched |= (path.read_text().strip().upper() == SERIAL and
                                    (path.parent / "idVendor").read_text().strip() == "2e8a" and
                                    (path.parent / "idProduct").read_text().strip() == "000f")
                    except OSError:
                        continue
                if not matched: time.sleep(.2)
            require(matched, "serial-specific BOOTSEL missing")
            run("restore", [PICOTOOL, "load", "-v", "-x", args.restoration, "--ser", SERIAL], 60)
            end = time.monotonic() + 15
            path = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")
            while not path.exists() and time.monotonic() < end: time.sleep(.2)
            require(path.exists(), "application USB missing")
            after = inventory("after-a")
            after_b = inventory("after-b", B_SERIAL, B_DEVICE)
            idle(after); idle(after_b)
            require(after["info"]["revision"] == RESTORE_REVISION and
                    after["info"]["status"]["engine"] == "inhibited-standalone-simulator" and
                    configuration(after) == configuration(original), "restoration mismatch")
            require(after_b["wtp"]["STATUS"]["boot_id"] == original_b["wtp"]["STATUS"]["boot_id"] and
                    after_b["info"]["revision"] == original_b["info"]["revision"] and
                    configuration(after_b) == configuration(original_b), "comparator mismatch")
            emit("finish", dict(result="RESTORED_INHIBITED", output_active=False))
        except BaseException as error:
            emit("failure", dict(error=str(error), action="STOP; no retry or fault clearing"))
            raise


if __name__ == "__main__":
    main()
