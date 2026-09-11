#!/usr/bin/env python3
"""Check pinned Arm linked renderer placement; no hardware access.

This deliberately rejects calls, computed jumps, literal pools and constructed
addresses in the SRAM renderer. It does not prove timing or pointer provenance.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess


def validate(symbols, disassembly, sections, expect):
    matches = re.findall(r"^([0-9a-f]+) ([0-9a-f]+) [Tt] (wsprrypico::rf::Waveform::render\(.*)$",
                         symbols, re.M)
    if len(matches) != 1:
        raise ValueError("expected exactly one renderer")
    address, size = (int(value, 16) for value in matches[0][:2])
    if not size:
        raise ValueError("empty renderer")
    if expect == "flash":
        if not 0x10000000 <= address < address + size <= 0x103FB000:
            raise ValueError("renderer is not in application flash")
        return dict(placement=expect, address=hex(address), bytes=size)
    data = re.search(r"^\s*\d+ \.data\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)", sections, re.M)
    if not data:
        raise ValueError("missing initialized data section")
    length, vma, lma = (int(value, 16) for value in data.groups())
    if not (0x20000000 <= vma <= address < address + size <= vma + length <= 0x2007C000
            and 0x10000000 <= lma < lma + length <= 0x103FB000):
        raise ValueError("renderer outside SRAM initialization image")
    # The engine contains its immutable plan, tables and double buffers by value.
    engine = re.findall(r"^([0-9a-f]+) ([0-9a-f]+) [Bb] wsprrypico::rf::start_worker\(.*::engine$",
                        symbols, re.M)
    if len(engine) != 1:
        raise ValueError("missing standalone worker engine")
    base, extent = (int(value, 16) for value in engine[0])
    if not 0x20000000 <= base < base + extent <= 0x2007C000:
        raise ValueError("worker engine outside SRAM")
    lines = []
    cursor = address
    for line in disassembly.splitlines():
        location = re.match(r"^\s*([0-9a-f]+):", line)
        if not location or not address <= int(location[1], 16) < address + size:
            continue
        match = re.match(r"^\s*([0-9a-f]+):\s+([0-9a-f ]+)\t\s*([.a-z][.a-z0-9]*)\s*(.*)$", line)
        if not match or int(match[1], 16) != cursor:
            raise ValueError("incomplete renderer disassembly")
        width = len(match[2].replace(" ", "")) // 2
        if width not in (2, 4):
            raise ValueError("unexpected instruction width")
        cursor += width
        lines.append(match)
    if not lines or cursor != address + size:
        raise ValueError("missing renderer disassembly")
    # Fail closed if a new compiler introduces an instruction outside this
    # reviewed integer/load/store subset. Raw bytes also bind full symbol coverage.
    ordinary = re.compile(r"^(?:adc|add|and|asr|bic|cmp|cmn|eor|it|itt|ite|lsl|lsr|mla|mov|mvn|mul|nop|orr|rsb|sbc|sub|tst|uxtah|uxth|uxtb|ldr|ldrb|ldrh|ldrd|str|strb|strh|strd)(?:s|eq|ne|cs|cc|hi|ls|ge|lt|gt|le|mi|pl|vs|vc)?$")
    for match in lines:
        instruction, operands = match[3].split('.')[0], match[4].split('@')[0].strip()
        if instruction in {"b", "beq", "bne", "bcs", "bcc", "bhi", "bls", "bge", "blt", "bgt", "ble", "bmi", "bpl", "bvs", "bvc", "cbz", "cbnz"}:
            target = re.search(r"(?:^|,\s*)([0-9a-f]+)\s+<", operands)
            if not target or not address <= int(target[1], 16) < address + size:
                raise ValueError("branch leaves renderer")
        elif instruction in {"push", "pop", "stmdb", "ldmia"}:
            if instruction in {"stmdb", "ldmia"} and not operands.startswith("sp!"):
                raise ValueError("non-stack multiple-register transfer")
            if "pc" in operands and instruction not in {"pop", "ldmia"}:
                raise ValueError("unexpected program counter use")
        elif not ordinary.fullmatch(instruction) or re.search(r"\bpc\b", operands):
            raise ValueError("unreviewed instruction or flash dependency: " + match[0].strip())
    return dict(placement=expect, address=hex(address), bytes=size,
                initialized_data_bytes=length, worker_address=hex(base), worker_bytes=extent,
                checked_instructions=len(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    parser.add_argument("--expect", choices=("ram", "flash"), required=True)
    args = parser.parse_args()
    def run(*command):
        return subprocess.check_output([*command, str(args.elf)], text=True)
    result = validate(run("arm-none-eabi-nm", "-S", "-C"),
                      run("arm-none-eabi-objdump", "-d", "-C"),
                      run("arm-none-eabi-objdump", "-h"), args.expect)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
