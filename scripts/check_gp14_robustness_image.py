#!/usr/bin/env python3
"""Check the opt-in diagnostic's linked topology, SRAM callbacks and flash limits."""
from pathlib import Path
import re
import subprocess
import sys
from check_standalone_image import validate_uf2


def validate(symbols, disassembly, map_text, uf2):
    entries = []
    for line in symbols.splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([A-Za-z])\s+(.+)", line)
        if match:
            entries.append((int(match[1], 16), int(match[2], 16), match[4]))

    def one(fragment):
        found = [entry for entry in entries if fragment in entry[2]]
        if len(found) != 1:
            raise ValueError(f"Expected one {fragment}, found {found}")
        return found[0]

    def body(address):
        found = re.search(rf"(?ms)^{address:08x} <[^\n]+>:\n(.*?)(?=^[0-9a-f]+ <|\Z)", disassembly)
        if not found:
            raise ValueError(f"Missing disassembly at {address:x}")
        return found[1]

    for fragment in ('robustness_flash_probe', 'robustness_flash_words', 'robustness_core1'):
        address, size, _ = one(fragment)
        if not 0x10000000 <= address < address + size <= 0x103F2000:
            raise ValueError(f"{fragment} must use XIP")
    if one('robustness_flash_words')[1] < 32768:
        raise ValueError("Probe must exceed the XIP cache")
    probe = one('robustness_flash_probe')[0]
    for fragment in ('robustness_core1', ' main'):
        entry = one(fragment) if fragment != ' main' else next(e for e in entries if e[2] == 'main')
        if not re.search(rf"\bbl\b\s+{probe:08x}\b", body(entry[0])):
            raise ValueError(f"{fragment} must call the XIP probe")
    for fragment in ('robustness_flash_write', 'robustness_hardfault',
                     'flash_range_erase', 'flash_range_program', 'multicore_lockout_handler'):
        address, size, _ = one(fragment)
        if not 0x20000000 <= address < address + size <= 0x20082000:
            raise ValueError(f"{fragment} is outside SRAM")
    for fragment in ('robustness_flash_write', 'robustness_hardfault'):
        code = body(one(fragment)[0])
        for destination in re.findall(r"\b(?:bl|b\.w)\s+([0-9a-f]+)\b", code):
            if not 0x20000000 <= int(destination, 16) < 0x20082000:
                raise ValueError(f"{fragment} branches outside SRAM")
        if re.search(r"\bblx\b|\.word\s+0x10[0-3][0-9a-f]{5}\b", code):
            raise ValueError(f"{fragment} has indirect calls or XIP literal")
    if '.word\t0x003f2000' not in body(one('robustness_flash_write')[0]):
        raise ValueError('Missing fixed diagnostic scratch address in flash callback')
    for fragment in ('PicoPioDma', 'WorkerEngine', 'cyw43_', 'sample_runtime_bootsel',
                     'capture_chip_select_gesture', 'PicoAccessStorage', 'PicoProfileStorage'):
        if any(fragment in name for _, _, name in entries):
            raise ValueError(f"Forbidden diagnostic dependency: {fragment}")
    if not re.search(r'^FLASH\s+0x10000000\s+0x003f2000\s+xr$', map_text, re.M):
        raise ValueError('Diagnostic scratch/settings reservation absent')
    validate_uf2(uf2, application_end=0x103F2000)


if __name__ == '__main__':
    elf = Path(sys.argv[1])
    validate(subprocess.check_output(['arm-none-eabi-nm', '-S', '-C', str(elf)], text=True),
             subprocess.check_output(['arm-none-eabi-objdump', '-d', '-C', str(elf)], text=True),
             Path(str(elf) + '.map').read_text(), elf.with_suffix('.uf2').read_bytes())
    print('GP14 robustness: both-core XIP, SRAM flash/fault/lockout, reserved scratch, no RF/network')
