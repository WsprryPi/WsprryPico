#!/usr/bin/env python3
"""Reject known core-1 launch code in the BOOTSEL-capable image."""

import re
import subprocess
import sys


def validate(symbols):
    entries = []
    for line in symbols.splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]+)\s+([a-zA-Z])\s+(\S+)", line.strip())
        if match:
            entries.append((int(match[1], 16), match[2], match[3]))

    forbidden = ("multicore_launch_core1", "core1_wrapper", "bootsel_flash_reader")
    present = sorted(name for _, _, name in entries if any(item in name for item in forbidden))
    if present:
        raise ValueError(f"Core-1 launch/reader linked into BOOTSEL image: {present}")

    callback = [(address, kind) for address, kind, name in entries
                if "sample_chip_select" in name]
    if len(callback) != 1 or callback[0][1].lower() != "t" or not (
            0x20000000 <= callback[0][0] < 0x20082000):
        raise ValueError(f"BOOTSEL sample callback is not uniquely linked in SRAM: {callback}")

    if not any("sample_runtime_bootsel" in name for _, _, name in entries):
        raise ValueError("Runtime BOOTSEL sampler is absent")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_bootsel_topology.py image.elf")
    validate(subprocess.check_output(["arm-none-eabi-nm", sys.argv[1]], text=True))
    print("BOOTSEL topology: one SRAM callback; no linked core-1 launcher/reader")
