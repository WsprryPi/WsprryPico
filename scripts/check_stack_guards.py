#!/usr/bin/env python3
"""Check linked MSP guard installation routes, not target execution or WCET."""
import argparse
import json
from pathlib import Path
import re
import subprocess


def validate(disassembly, physical):
    functions = {}
    current = None
    for line in disassembly.splitlines():
        label = re.fullmatch(r'[0-9a-f]+ <([^>]+)>:', line)
        if label:
            current = label[1]
            functions[current] = []
        elif current:
            functions[current].append(line)
    installer = 'runtime_init_per_core_install_stack_guard'
    snapshot = 'wsprry_stack_guard_snapshot'
    callers = set()
    writes = []
    for name, lines in functions.items():
        for line in lines:
            if re.search(r'\bmsr\s+MSPLIM,', line, re.IGNORECASE):
                writes.append(name)
            if re.search(r'\b(?:bl|b\.w)\s+[0-9a-f]+ <' + installer + r'>', line):
                callers.add(name)
    expected = {'runtime_init'} | ({'core1_wrapper'} if physical else set())
    if callers != expected:
        raise ValueError('Stack guard startup routes differ: ' + repr(sorted(callers)))
    if writes != [installer]:
        raise ValueError('Unexpected or missing MSPLIM writer: ' + repr(writes))
    body = '\n'.join(functions.get(snapshot, ()))
    for register in ('MSPLIM', 'MSP', 'CONTROL'):
        if not re.search(r'\bmrs\s+\w+,\s*' + register + r'\b', body, re.IGNORECASE):
            raise ValueError('Missing stack register readback: ' + register)
    if not re.search(r'\bisb\b', '\n'.join(functions.get(installer, ()))):
        raise ValueError('Missing post-install synchronization')
    return {'startup_callers': sorted(callers), 'msplim_writers': writes,
            'scope': 'Linked startup/readback routes only; inspect constants and target evidence separately'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf', type=Path)
    parser.add_argument('--physical', action='store_true')
    args = parser.parse_args()
    result = validate(subprocess.check_output(['arm-none-eabi-objdump', '-d', str(args.elf)],
                                             text=True), args.physical)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
