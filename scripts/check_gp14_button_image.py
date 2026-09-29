#!/usr/bin/env python3
"""Refuse a GP14 diagnostic link with RF, flash writers, or missing flash work."""

import re
import subprocess
import sys


def validate(symbols, disassembly):
    entries = []
    for line in symbols.splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([A-Za-z])\s+(.+)", line)
        if match:
            entries.append((int(match[1], 16), int(match[2], 16), match[3], match[4]))

    def unique(fragment):
        matches = [entry for entry in entries if fragment in entry[3]]
        if len(matches) != 1:
            raise ValueError(f"Expected one {fragment}, found {matches}")
        return matches[0]

    for fragment in ("flash_probe_step", "flash_probe_words", "core1_main"):
        address, size, _, _ = unique(fragment)
        if not (0x10000000 <= address < address + size <= 0x103f3000):
            raise ValueError(f"{fragment} must execute/read from external flash")
    main = [entry for entry in entries if entry[3] == "main"]
    if len(main) != 1 or not (0x10000000 <= main[0][0] < main[0][0] + main[0][1] <= 0x103f3000):
        raise ValueError("main must execute from external flash")
    if unique("flash_probe_words")[1] < 32768:
        raise ValueError("Flash probe data must exceed the 16 KiB XIP cache")

    def body_for(address, symbol):
        body = re.search(rf"(?ms)^{address:08x} <[^\n]*{symbol}[^\n]*>:\n"
                         r"(.*?)(?=^[0-9a-f]+ <|\Z)", disassembly)
        if not body:
            raise ValueError(f"Missing disassembly for {symbol}")
        return body[1]

    probe_address = unique("flash_probe_step")[0]
    for symbol, address in (("core1_main", unique("core1_main")[0]), ("main", main[0][0])):
        if not re.search(rf"\bbl\b\s+{probe_address:08x}\s+<[^\n]*flash_probe_step",
                         body_for(address, symbol)):
            raise ValueError(f"{symbol} must call the XIP flash probe")

    address, _, _, _ = unique("button_hardfault")
    if not 0x20000000 <= address < 0x20082000:
        raise ValueError("HardFault handler must be in SRAM")
    if re.search(r"\bblx?\b", body_for(address, "button_hardfault")):
        raise ValueError("HardFault handler calls out of SRAM")

    required = ("multicore_launch_core1_with_stack", "watchdog_enable", "watchdog_update")
    for fragment in required:
        if not any(fragment in name for _, _, _, name in entries):
            raise ValueError(f"Missing {fragment}")
    forbidden = ("flash_range_erase", "flash_range_program", "flash_safe_execute",
                 "cyw43_", "pio_sm_", "pio_gpio_init", "PicoPioDma", "WorkerEngine",
                 "capture_chip_select_gesture", "sample_runtime_bootsel")
    for fragment in forbidden:
        if any(fragment in name for _, _, _, name in entries):
            raise ValueError(f"Forbidden link in GP14 diagnostic: {fragment}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_gp14_button_image.py image.elf")
    elf = sys.argv[1]
    validate(subprocess.check_output(["arm-none-eabi-nm", "-S", "-C", elf], text=True),
             subprocess.check_output(["arm-none-eabi-objdump", "-d", "-C", elf], text=True))
    print("GP14 diagnostic: both-core XIP workload, SRAM fault handler, no RF or flash writer")
