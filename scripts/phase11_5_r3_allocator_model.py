#!/usr/bin/env python3
"""Hardware-free execution of the exact ELF's newlib allocator (optional Unicorn).

Only serialized malloc lock/unlock calls are stubbed; malloc, free, trim,
page size, sbrk, heap bounds and initialized allocator data come from the ELF.
This synthetic history proves a mechanism, not C0's unrecorded exact allocation.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def model(path):
    from elftools.elf.elffile import ELFFile
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        symbols = {s.name: s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols()}
        cpu = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        cpu.mem_map(0x10000000, 0x400000)
        cpu.mem_map(0x20000000, 0x82000)
        for segment in elf.iter_segments():
            if segment['p_type'] == 'PT_LOAD' and segment['p_filesz']:
                cpu.mem_write(segment['p_vaddr'], segment.data())
    extensions = []
    locks = {symbols[n] & ~1 for n in ('__malloc_lock', '__malloc_unlock')}
    def hook(cpu, address, size, data):
        if address in locks:
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
        if address == symbols['_sbrk'] & ~1:
            extensions.append(struct.unpack('<i', struct.pack('<I', cpu.reg_read(UC_ARM_REG_R0)))[0])
        if address == 0x20080000:
            cpu.emu_stop()
    cpu.hook_add(UC_HOOK_CODE, hook)
    def call(name, *args):
        cpu.reg_write(UC_ARM_REG_SP, 0x2007fff0)
        cpu.reg_write(UC_ARM_REG_LR, 0x20080001)
        for reg, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), args):
            cpu.reg_write(reg, value)
        cpu.emu_start(symbols[name] | 1, 0, count=2_000_000)
        if cpu.reg_read(UC_ARM_REG_PC) != 0x20080000:
            raise ValueError('Instruction bound or unexpected allocator return: ' + name)
        return cpu.reg_read(UC_ARM_REG_R0)
    def word(address):
        return struct.unpack('<I', cpu.mem_read(address, 4))[0]
    def heap():
        top = word(symbols['__malloc_av_'] + 8)
        end = word(symbols['heap_end.0'])
        return dict(top_bytes=word(top + 4) & ~3,
                    arena_bytes=end - symbols['__end__'],
                    unextended_bytes=symbols['__StackLimit'] - end)
    context = 0x2007c100
    blocks, pins = [], []
    for _ in range(4):
        blocks.append(call('_malloc_r', context, 30000))
        pins.append(call('_malloc_r', context, 64))
    tail = call('_malloc_r', context, 40000)
    assert all(blocks + pins + [tail]), 'History must allocate completely'
    for pointer in blocks + [tail]:
        call('_free_r', context, pointer)
    before = heap()
    attempts = len(extensions)
    rejected = call('_malloc_r', context, 65552)
    failure_extensions = extensions[attempts:]
    assert rejected == 0 and before == heap()
    assert before['top_bytes'] + before['unextended_bytes'] > 65552
    assert failure_extensions == [69632] and before['unextended_bytes'] < 69632
    assert call('_malloc_trim_r', context, 0) == 1
    trimmed = heap()
    accepted = call('_malloc_r', context, 65552)
    assert accepted and accepted + 65552 <= symbols['__StackLimit']
    cpu.mem_write(accepted, b'Z' * 65552)
    assert bytes(cpu.mem_read(accepted, 65552)) == b'Z' * 65552
    call('_free_r', context, accepted)
    for pointer in pins:
        call('_free_r', context, pointer)
    return dict(status='MECHANISM_REPRODUCED_TRIM_REPAIR_MODEL_PASSED',
                elf_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                requested_bytes=65552, before=before,
                rejected_extension_bytes=failure_extensions, after_trim=trimmed,
                accepted_pointer=accepted, extensions=extensions,
                historical_c0_exact_allocation_proven=False,
                physical_remediation_verified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf', type=Path)
    args = parser.parse_args()
    print(json.dumps(model(args.elf), indent=2))
