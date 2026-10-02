#!/usr/bin/env python3
"""Check linked BTstack fixed-pool get/free routing; hardware-free.

Direct branch routing proves the pinned callers are observed. It does not
measure controller buffers, RF behavior or target resource sufficiency.
"""
import argparse
import json
import re
import subprocess

POOLS = ('hci_connection', 'l2cap_channel', 'l2cap_service', 'sm_lookup_entry', 'whitelist_entry')


def validate(disassembly):
    edges = {}
    symbols = set()
    caller = None
    for line in disassembly.splitlines():
        label = re.fullmatch(r'[0-9a-f]+ <([^>]+)>:', line)
        if label:
            caller = label[1]
            symbols.add(caller)
            continue
        instruction = re.match(r'\s*[0-9a-f]+:\s+[0-9a-f ]+\t\s*(\S+)\s+(.*)', line)
        if not instruction or not caller:
            continue
        op, operands = instruction.groups()
        if not re.fullmatch(r'(?:blx?|b(?:eq|ne|cs|cc|mi|pl|vs|vc|hi|ls|ge|lt|gt|le)?)(?:\.[nw])?', op):
            continue
        target = re.search(r'<([^>]+)>', operands)
        if target:
            callee = target[1].split('+0x')[0]
            if caller != callee:
                edges.setdefault(callee, set()).add(caller)
    result = {}
    for pool in POOLS:
        for operation in ('get', 'free'):
            real = f'btstack_memory_{pool}_{operation}'
            wrapper = '__wrap_' + real
            if real not in symbols or wrapper not in symbols:
                raise ValueError('missing pool/wrapper: ' + real)
            if edges.get(real) != {wrapper}:
                raise ValueError('pool bypass or missing delegation: ' + real)
            callers = edges.get(wrapper, set())
            if pool == 'hci_connection' and not callers:
                raise ValueError('unused required HCI pool wrapper: ' + wrapper)
            # Other configured peripheral pools have no acquisition path in the
            # pinned image. Retained hooks prove routing capability, not activity.
            result[wrapper] = sorted(callers)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf')
    args = parser.parse_args()
    disassembly = subprocess.check_output(['arm-none-eabi-objdump', '-d', args.elf], text=True)
    print(json.dumps(validate(disassembly), sort_keys=True))


if __name__ == '__main__':
    main()
