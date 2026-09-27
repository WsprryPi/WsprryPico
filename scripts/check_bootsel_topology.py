#!/usr/bin/env python3
"""Reject known core-1 launch code in the BOOTSEL-capable image."""

import re
import subprocess
import sys


def validate(symbols, disassembly, expect_core1=False):
    entries = []
    for line in symbols.splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]+)\s+([a-zA-Z])\s+(\S+)", line.strip())
        if match:
            entries.append((int(match[1], 16), match[2], match[3]))

    core1_symbols = ("multicore_launch_core1", "core1_wrapper", "bootsel_flash_reader")
    present = {symbol: any(symbol in name for _, _, name in entries)
               for symbol in core1_symbols}
    if expect_core1:
        if not all(present.values()):
            raise ValueError(f"Core-1 diagnostic is incomplete: {present}")
    elif any(present.values()):
        raise ValueError(f"Core-1 launch/reader linked into production image: {present}")

    for symbol, required in (("sample_chip_select", True),
                             ("capture_chip_select_gesture", expect_core1)):
        callback = [(address, kind) for address, kind, name in entries if symbol in name]
        wrong_count = len(callback) != 1 if required else len(callback) > 1
        wrong_address = any(kind.lower() != "t" or not 0x20000000 <= address < 0x20082000
                            for address, kind in callback)
        if wrong_count or wrong_address:
            raise ValueError(f"BOOTSEL callback is not uniquely linked in SRAM: {symbol}: {callback}")
        if callback:
            address = callback[0][0]
            body = re.search(rf"(?ms)^{address:08x} <[^\n]*{symbol}[^\n]*>:\n"
                             r"(.*?)(?=^[0-9a-f]+ <|\Z)", disassembly)
            if not body or re.search(r"\bblx?\b", body[1]) or re.search(
                    r"\.word\s+0x10[0-3][0-9a-f]{5}\b", body[1]):
                raise ValueError(f"BOOTSEL callback calls out or reads XIP: {symbol}")

    if not any("sample_runtime_bootsel" in name for _, _, name in entries):
        raise ValueError("Runtime BOOTSEL sampler is absent")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != "--expect-core1"):
        raise SystemExit("usage: check_bootsel_topology.py image.elf [--expect-core1]")
    expect_core1 = len(sys.argv) == 3
    symbols = subprocess.check_output(["arm-none-eabi-nm", sys.argv[1]], text=True)
    disassembly = subprocess.check_output(["arm-none-eabi-objdump", "-d", sys.argv[1]], text=True)
    validate(symbols, disassembly, expect_core1)
    print("BOOTSEL topology: SRAM callback(s); " +
          ("diagnostic core-1 flash reader linked" if expect_core1
           else "no linked core-1 launcher/reader"))
