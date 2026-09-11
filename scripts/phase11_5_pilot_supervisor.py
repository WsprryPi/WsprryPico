#!/usr/bin/env python3
"""Bounded start/ExecStopPost stages for the separately authorized RF pilot.

Invoke restore as a separately armed systemd ExecStopPost. It refuses flashing
after an incomplete/failed pilot, changed boot, owner, configuration or output.
Nothing runs without --run. Images, backups and logs remain private.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import struct
import sys
import time

from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_pilot import DEVICE, SERIAL, validate_packet
from validate_wtp_contract import loads_strict, unique_object, reject_float, reject_constant

B_SERIAL = "CDDBF8767C506C07"
B_DEVICE = "29f20b7342051ef947aa56cb9d4fab42"
PICOTOOL = Path("/home/pi/phase11-4-e1/picotool-build/picotool")
PICOTOOL_SHA = "4a68cfd7fc36002e80857802c8192c9f24c751357c6cb26ad13ad7f38c227921"
RESTORE_SHA = "25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10"
RESTORE_REVISION = "802c91a7b86e-dirty"
HERE = Path(__file__).resolve().parent
HELPERS = {"scripts/phase11_5_pilot.py", "scripts/phase11_5_pilot_supervisor.py",
           "scripts/phase11_5_inventory.py", "scripts/validate_wtp_contract.py",
           "scripts/wtp_monitor.py", "docs/protocol/wtp-1.schema.json"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_application_backup(uf2, backup):
    require(uf2 and len(uf2) % 512 == 0, "invalid restoration UF2")
    checked = 0
    for offset in range(0, len(uf2), 512):
        magic0, magic1, flags, address, size = struct.unpack_from("<5I", uf2, offset)
        require((magic0, magic1) == (0x0A324655, 0x9E5D5157) and
                struct.unpack_from("<I", uf2, offset + 508)[0] == 0x0AB16F30 and
                0 < size <= 476, "invalid restoration block")
        if address == 0x10FFFF00 or flags & 1:
            continue  # Special RP2350-E10 boot block is not application payload.
        start = address - 0x10000000
        require(0 <= start < start + size <= min(len(backup), 0x3FB000), "backup range")
        require(backup[start:start + size] == uf2[offset + 32:offset + 32 + size],
                "existing application differs from the restoration image")
        checked += 1
    require(checked > 0, "missing application payload")
    return checked


def finished(path, result):
    # Host evidence envelopes contain 64-bit nanosecond timestamps. WTP's
    # signed-32-bit JSON integer rule applies to wire messages, not these logs.
    source = path.read_text()
    require(source.endswith("\n"), "truncated evidence record")
    rows = [json.loads(line, object_pairs_hook=unique_object, parse_float=reject_float,
                       parse_constant=reject_constant) for line in source.splitlines()]
    require(rows and rows[0]["kind"] == "start", "missing evidence start")
    for row in rows:
        require(type(row["sequence"]) is int and all(type(row[key]) is int and
                0 <= row[key] < 1 << 64 for key in ("utc_ns", "monotonic_ns")),
                "invalid host evidence envelope")
    require(all(a["monotonic_ns"] <= b["monotonic_ns"] for a, b in zip(rows, rows[1:])),
            "host evidence time reversed")
    require(rows and rows[-1]["kind"] == "finish" and rows[-1]["value"]["result"] == result,
            "missing successful finish marker")
    require([row["sequence"] for row in rows] == list(range(len(rows))), "incomplete log sequence")
    return rows[-1]["value"]


def idle(value):
    status, info = value["wtp"]["STATUS"], value["info"]
    require(status["state"] == "empty" and status["output_active"] is False and
            status["owner_id"] is None and status["job_id"] is None, "not authoritatively idle")
    require(info["status"]["state"] == "empty" and info["status"]["output_active"] is False and
            info["status"]["enabled"] is False and info["status"]["last_error"] is None and
            info["status"]["storage_healthy"] is True and not info["recovery_boot"], "unsafe INFO")


def configuration(value):
    info = value["info"]
    status = info["status"]
    return {key: status[key] for key in ("configured", "enabled", "station", "schedules",
                                       "watermark_utc_ns")}, {
        key: info["network"][key] for key in ("station_mac", "configured_hostname",
                                             "control_configured")}


def restoration_admitted(before_a, before_b, candidate, completion, current_a, current_b, revision):
    idle(current_a)
    idle(current_b)
    require(current_a["info"]["revision"] == revision and
            current_a["info"]["status"]["engine"] == "pio-dma-gp2" and
            current_a["info"]["system_clock_hz"] == candidate["info"]["system_clock_hz"],
            "candidate changed")
    boot = candidate["wtp"]["STATUS"]["boot_id"]
    require(completion["boot_id"] == boot == current_a["wtp"]["STATUS"]["boot_id"] and
            completion["result"] == "DIAGNOSTIC_COMPLETED_NOT_ACCEPTANCE" and
            completion["output_active"] is False, "pilot boot/finish changed")
    require(current_b["wtp"]["STATUS"]["boot_id"] == before_b["wtp"]["STATUS"]["boot_id"] and
            current_b["info"]["revision"] == before_b["info"]["revision"], "comparator changed")
    require(configuration(current_a) == configuration(before_a) and
            configuration(current_b) == configuration(before_b), "configuration changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("start", "restore"))
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--restoration", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    packet = loads_strict(args.packet.read_text())
    validate_packet(packet)
    require(digest(args.candidate) == packet["uf2_sha256"] and
            digest(args.restoration) == RESTORE_SHA, "image identity")
    if not args.run:
        print("Packet and images valid; no hardware accessed")
        return
    require(sys.platform.startswith("linux") and os.geteuid() == 0, "wspr5 root supervisor required")
    require(Path("/proc/sys/kernel/random/boot_id").read_text().strip() == packet["host_boot_id"],
            "host boot changed")
    require(digest(PICOTOOL) == PICOTOOL_SHA, "flash tool changed")
    require(set(packet["helper_sha256"]) == HELPERS, "incomplete helper identity")
    for relative, expected in packet["helper_sha256"].items():
        path = HERE.parent / relative
        require(path.resolve().is_relative_to(HERE.parent) and digest(path) == expected,
                "helper/schema changed")
    os.umask(0o077)
    if args.stage == "start":
        args.evidence.mkdir(mode=0o700, parents=False, exist_ok=False)
    require(args.evidence.is_dir(), "missing evidence directory")
    space = os.statvfs(args.evidence)
    require(space.f_bavail * space.f_frsize >= 1 << 30, "less than 1 GiB free evidence space")
    with (args.evidence / f"{args.stage}.jsonl").open("x") as log:
        sequence = 0

        def emit(kind, value):
            nonlocal sequence
            log.write(json.dumps(dict(sequence=sequence, kind=kind, utc_ns=time.time_ns(),
                                      monotonic_ns=time.monotonic_ns(), value=value)) + "\n")
            log.flush()
            os.fsync(log.fileno())
            sequence += 1

        def run(label, command, timeout):
            emit("command_start", dict(label=label, argv=[str(x) for x in command]))
            with (args.evidence / f"{label}.stdout").open("xb") as out, \
                    (args.evidence / f"{label}.stderr").open("xb") as err:
                result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                        timeout=timeout, check=False)
                out.flush()
                err.flush()
                os.fsync(out.fileno())
                os.fsync(err.fileno())
            emit("command_exit", dict(label=label, returncode=result.returncode,
                                      stdout_sha256=digest(args.evidence / f"{label}.stdout"),
                                      stderr_sha256=digest(args.evidence / f"{label}.stderr")))
            require(result.returncode == 0, f"{label} failed; no automatic retry")

        def inventory(label, serial=SERIAL, device=DEVICE):
            run(label, [sys.executable, HERE / "phase11_5_inventory.py", "--serial", serial,
                        "--device-id", device, "--run"], 65)
            return finished(args.evidence / f"{label}.stdout", "READ_ONLY_INVENTORY")

        def bootsel():
            with exclusive_port(Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")) as fd:
                reply = exchange(fd, b"BOOTSEL\n", time.monotonic() + 5, emit, False)
                require(reply.get("ok") is True and reply.get("rebooting") is True, "BOOTSEL not acknowledged")
            end = time.monotonic() + 15
            while time.monotonic() < end:
                for path in Path("/sys/bus/usb/devices").glob("*/serial"):
                    try:
                        if (path.read_text().strip().upper() == SERIAL and
                                (path.parent / "idVendor").read_text().strip() == "2e8a" and
                                (path.parent / "idProduct").read_text().strip() == "000f"):
                            emit("bootsel_enumerated", dict(serial=SERIAL, path=str(path.parent)))
                            return
                    except OSError:
                        continue
                time.sleep(.2)
            raise TimeoutError("selected BOOTSEL serial did not enumerate")

        def wait_application():
            path = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")
            end = time.monotonic() + 15
            while not path.exists() and time.monotonic() < end:
                time.sleep(.2)
            require(path.exists(), "application USB did not enumerate")

        emit("start", dict(stage=args.stage, packet_sha256=digest(args.packet), packet=packet))
        try:
            if args.stage == "start":
                before_a = inventory("before-a")
                before_b = inventory("before-b", B_SERIAL, B_DEVICE)
                idle(before_a)
                idle(before_b)
                require(before_a["info"]["revision"] == RESTORE_REVISION and
                        before_a["info"]["status"]["engine"] == "inhibited-standalone-simulator",
                        "starting baseline changed")
                bootsel()
                run("backup", [PICOTOOL, "save", "-a", "-v", args.evidence / "before-flash.bin",
                               "-t", "bin", "--ser", SERIAL], 60)
                backup = args.evidence / "before-flash.bin"
                blocks = verify_application_backup(args.restoration.read_bytes(), backup.read_bytes())
                emit("backup_verified", dict(sha256=digest(backup), bytes=backup.stat().st_size,
                                             application_blocks=blocks))
                run("candidate-load", [PICOTOOL, "load", "-v", "-x", args.candidate,
                                       "--ser", SERIAL], 60)
                wait_application()
                candidate = inventory("candidate")
                idle(candidate)
                require(candidate["info"]["revision"] == packet["revision"] and
                        candidate["info"]["system_clock_hz"] == packet["system_clock_hz"] and
                        candidate["info"]["status"]["engine"] == "pio-dma-gp2" and
                        configuration(candidate) == configuration(before_a), "candidate admission")
                run("pilot", [sys.executable, HERE / "phase11_5_pilot.py", args.packet,
                              "--uf2", args.candidate, "--evidence", args.evidence / "pilot",
                              "--run"], 190)
                finished(args.evidence / "pilot/events.jsonl", "DIAGNOSTIC_COMPLETED_NOT_ACCEPTANCE")
                emit("finish", dict(result="PILOT_FINISHED_RESTORATION_REQUIRED"))
            else:
                # A missing start/finish is never interpreted as an inactive output.
                finished(args.evidence / "start.jsonl", "PILOT_FINISHED_RESTORATION_REQUIRED")
                before_a = finished(args.evidence / "before-a.stdout", "READ_ONLY_INVENTORY")
                before_b = finished(args.evidence / "before-b.stdout", "READ_ONLY_INVENTORY")
                candidate = finished(args.evidence / "candidate.stdout", "READ_ONLY_INVENTORY")
                completion = finished(args.evidence / "pilot/events.jsonl", "DIAGNOSTIC_COMPLETED_NOT_ACCEPTANCE")
                current_a = inventory("restore-admission-a")
                current_b = inventory("restore-admission-b", B_SERIAL, B_DEVICE)
                restoration_admitted(before_a, before_b, candidate, completion, current_a,
                                     current_b, packet["revision"])
                bootsel()
                run("restoration-load", [PICOTOOL, "load", "-v", "-x", args.restoration,
                                         "--ser", SERIAL], 60)
                wait_application()
                after_a = inventory("after-a")
                after_b = inventory("after-b", B_SERIAL, B_DEVICE)
                idle(after_a)
                idle(after_b)
                require(after_a["info"]["revision"] == RESTORE_REVISION and
                        after_a["info"]["status"]["engine"] == "inhibited-standalone-simulator" and
                        configuration(after_a) == configuration(before_a), "restoration mismatch")
                require(after_b["wtp"]["STATUS"]["boot_id"] == before_b["wtp"]["STATUS"]["boot_id"] and
                        after_b["info"]["revision"] == before_b["info"]["revision"] and
                        configuration(after_b) == configuration(before_b), "comparator mismatch")
                emit("finish", dict(result="RESTORED_INHIBITED", output_active=False,
                                    restoration_sha256=RESTORE_SHA))
        except BaseException as error:
            emit("failure", dict(error=str(error), action="STOP; independent authoritative reconciliation required"))
            raise


if __name__ == "__main__":
    main()
