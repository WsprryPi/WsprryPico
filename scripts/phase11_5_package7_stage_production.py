#!/usr/bin/env python3
"""Freeze one Package 7 production case without starting a process or job."""

import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import time

from phase11_5_inventory import require
from phase11_5_package7_plan import BOOT, DEVICE, validate


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=("armed", "running"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--client-pid", type=int, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--observer", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    packet = validate(json.loads((root / "packet.json").read_text()))
    binary, observer = args.binary.resolve(strict=True), args.observer.resolve(strict=True)
    require(binary.is_file() and observer.is_file(), "Production executable/observer")
    case = root / args.case
    case.mkdir(mode=0o700)
    config = configparser.ConfigParser(interpolation=None, strict=True)
    config.optionxform = str
    base = root / "production-base.ini"
    require(config.read(base) == [str(base)], "Production base INI")
    config.set("Operation", "Mode", "QRSS")
    config.set("Operation", "Transmit", "true")
    config.set("Operation", "Transmit Backend", "wtp")
    config.set("Operation", "Enable on Boot", "Follow")
    config.set("Operation", "Use LED", "false")
    config.set("Operation", "Use Amp", "false")
    config.set("Operation", "Use Shutdown", "false")
    config.set("Operation", "Web Port", "31425")
    config.set("Operation", "Socket Port", "31426")
    config.set("Experimental", "Allow Unqualified Frequency", "true")
    config.set("Experimental", "Allow Non-Amateur Frequency", "true")
    config.set("CW", "Message", "ETE")
    config.set("CW", "Base Frequency", "135500")
    config.set("CW", "Dot Seconds", "3")
    config.set("CW", "Intra Element Gap", "1")
    config.set("CW", "Inter Character Gap", "3")
    config.set("CW", "Fade Shape", "none")
    config.set("CW", "Repeat Minutes", "60")
    start_ns = ((time.time_ns() + 90_000_000_000 + 999_999_999) // 1_000_000_000) * 1_000_000_000
    start = time.gmtime(start_ns // 1_000_000_000)
    config.set("CW", "Start Minute", str(start.tm_min))
    config.set("CW", "Start Second", str(start.tm_sec))
    controller = root / "credentials/controller"
    config.set("WTP", "Transport", "network")
    config.set("WTP", "Hostname", packet["hostname"])
    config.set("WTP", "TCP Port", str(packet["port"]))
    config.set("WTP", "TLS Server Identity", packet["hostname"])
    config.set("WTP", "TLS CA File", str(controller / "client-ca.crt"))
    config.set("WTP", "TLS Client Certificate", str(controller / "client.crt"))
    config.set("WTP", "TLS Client Key", str(controller / "client.key"))
    config.set("WTP", "Device ID", DEVICE)
    config.set("WTP", "Start Uncertainty ns", "500000000")
    config.set("WTP", "Allow Frequency Adjustment", "true")
    config.set("WTP", "Endpoint", "")
    ini = case / "production.ini"
    with ini.open("x") as stream:
        config.write(stream, space_around_delimiters=True)
        stream.flush()
        os.fsync(stream.fileno())
    plan = {"case": args.case, "request_id": packet[f"production_{args.case}_request"],
            "boot_id": BOOT, "device_id": DEVICE, "planned_duration_ns": 33_000_000_000,
            "start_utc_ns": start_ns, "netns": os.readlink(f"/proc/{args.client_pid}/ns/net"),
            "mountns": os.readlink(f"/proc/{args.client_pid}/ns/mnt"),
            "binary": str(binary), "binary_sha256": digest(binary), "ini": str(ini),
            "ini_sha256": digest(ini), "observer": str(observer),
            "observer_sha256": digest(observer)}
    temporary = case / "case.tmp"
    temporary.write_text(json.dumps(plan, indent=2) + "\n")
    temporary.replace(case / "case.json")
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
