#!/usr/bin/env python3
"""Read-only ELF memory-layout check for the pinned RP2350 endpoint build."""
import subprocess
import sys

result = subprocess.run(["arm-none-eabi-nm", "-n", sys.argv[1]], check=True, capture_output=True, text=True)
symbols = {}
for line in result.stdout.splitlines():
    parts = line.split()
    if len(parts) == 3:
        symbols[parts[2]] = int(parts[0], 16)
assert symbols["__StackTop"] - symbols["__StackBottom"] == 16384
assert symbols["__HeapLimit"] <= symbols["__StackBottom"]
assert symbols["__bss_end__"] < symbols["__HeapLimit"]
assert 0x20000000 <= symbols["__StackBottom"] < symbols["__StackTop"] <= 0x20080000
assert symbols["__StackTop"] <= symbols["__StackOneBottom"]
worker = next((address for name, address in symbols.items() if "worker_stack" in name), None)
if worker is not None:
    assert symbols["__bss_start__"] <= worker < worker + 16384 <= symbols["__bss_end__"]
    assert worker % 8 == 0
    print("RF worker: dedicated aligned 16 KiB BSS stack below the heap")
print("RP2350: 16 KiB primary stack; heap and core-1 stack do not overlap it")
