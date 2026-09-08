#!/usr/bin/env python3
"""Opt-in bounded administration of an identified standalone Pico image."""
import argparse
import json
from pathlib import Path
import time

from check_usb_target import port, write_all
from rf_wtp import read_line

ACTIONS = {"info": "INFO", "status": "STATUS", "stop": "STOP", "abort": "ABORT", "reboot": "REBOOT",
           "bootsel": "BOOTSEL", "wifi-off": "WIFI OFF", "wifi-on": "WIFI ON"}


def configuration(path, enable_schedule, now):
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict) or type(value.get("enabled")) is not bool:
            raise ValueError()
        if value["enabled"]:
            expiry = value.get("expires_utc_s")
            if (not enable_schedule or type(expiry) is not int or
                    not now < expiry <= now + 3600):
                raise ValueError()
        text = json.dumps(value, separators=(",", ":"), ensure_ascii=True)
        if len(text) > 1800:
            raise ValueError()
        return "CONFIG " + text
    except (OSError, ValueError, TypeError):
        # Never include the input document or a parser excerpt in diagnostics.
        raise ValueError("Invalid private configuration; enabled tests require explicit opt-in and expiry within one hour") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=[*ACTIONS, "config"])
    parser.add_argument("--port", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--revision")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--enable-schedule", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        parser.error("--run is required for device I/O")
    if args.action == "config":
        if not args.config or not args.revision:
            parser.error("configuration requires --config and --revision")
        try:
            command = configuration(args.config, args.enable_schedule, time.time())
        except ValueError as error:
            parser.error(str(error))
    else:
        command = ACTIONS[args.action]
    with port(args.port) as fd:
        write_all(fd, b"INFO\n")
        identity = read_line(fd, time.monotonic() + 5)
        if (not identity.get("ok") or identity.get("device_id") != args.device_id or
                (args.revision and identity.get("revision") != args.revision)):
            raise RuntimeError("Firmware/device identity mismatch")
        if args.action == "info":
            result = identity
        else:
            write_all(fd, (command + "\n").encode("ascii"))
            result = read_line(fd, time.monotonic() + 10)
        if not result.get("ok"):
            raise RuntimeError("Device rejected command: " + str(result.get("error", "unknown")))
        print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
