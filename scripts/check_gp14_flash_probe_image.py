#!/usr/bin/env python3
"""Check the temporary runtime flash probe's callback and reserved scratch."""
from pathlib import Path
import re
import subprocess
import sys
from check_standalone_image import validate_uf2


def validate(symbols, disassembly, map_text, uf2):
    entries = []
    for line in symbols.splitlines():
        match = re.fullmatch(r'([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+[A-Za-z]\s+(.+)', line)
        if match:
            entries.append((int(match[1],16),int(match[2],16),match[3]))
    def one(fragment):
        found = [e for e in entries if (e[2] == fragment if fragment.startswith('flash_range_')
                                       else fragment in e[2])]
        if len(found) != 1:
            raise ValueError('Expected one '+fragment)
        return found[0]
    for name in ('gp14_probe_flash_write', 'flash_range_erase', 'flash_range_program'):
        address, size, _ = one(name)
        if not 0x20000000 <= address < address+size <= 0x20082000:
            raise ValueError(name+' must be in SRAM')
    address = one('gp14_probe_flash_write')[0]
    match = re.search(rf'(?ms)^{address:08x} <[^\n]+>:\n(.*?)(?=^[0-9a-f]+ <|\Z)', disassembly)
    if not match:
        raise ValueError('Missing SRAM callback disassembly')
    body = match[1]
    allowed_calls = {one(name)[0] for name in ('flash_range_erase','flash_range_program')}
    calls = {int(dest,16) for dest in re.findall(r'\b(?:bl|b\.w)\s+([0-9a-f]+)\b',body)}
    if not allowed_calls.issubset(calls) or not calls.issubset(allowed_calls | {address}):
        raise ValueError('Unexpected callback dependency')
    if re.search(r'\bblx\b|\.word\s+0x10[0-3][0-9a-f]{5}\b',body):
        raise ValueError('Indirect call or XIP data in callback')
    if '.word\t0x003f2000' not in body:
        raise ValueError('Missing fixed scratch address')
    for fragment in ('WorkerEngine','PicoPioDma','sample_override','inject_dma_stop','inject_pio_stop'):
        if any(fragment in name for _,_,name in entries):
            raise ValueError('Forbidden RF/synthetic dependency: '+fragment)
    if not re.search(r'^FLASH\s+0x10000000\s+0x003f2000\s+xr$',map_text,re.M):
        raise ValueError('Missing scratch reservation')
    validate_uf2(uf2,application_end=0x103f2000)


if __name__ == '__main__':
    elf = Path(sys.argv[1])
    subprocess.run([sys.executable,str(Path(__file__).with_name('check_endpoint_image.py')),str(elf)],check=True)
    validate(subprocess.check_output(['arm-none-eabi-nm','-S','-C',str(elf)],text=True),
             subprocess.check_output(['arm-none-eabi-objdump','-d','-C',str(elf)],text=True),
             Path(str(elf)+'.map').read_text(),elf.with_suffix('.uf2').read_bytes())
    print('Runtime flash probe: SRAM callback, fixed reserved scratch, real input, no RF engine')
