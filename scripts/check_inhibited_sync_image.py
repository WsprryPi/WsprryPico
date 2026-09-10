#!/usr/bin/env python3
"""Check the pinned RP2350 semaphore's emitted SDK 2.3.1 event-drain ordering."""
import argparse
from pathlib import Path
import re
import subprocess


def check(disassembly):
    if '<sem_acquire_block_until>:' not in disassembly:
        raise ValueError('missing semaphore implementation')
    instructions = re.findall(r'^[ \t]*[0-9a-f]+:[ \t]+(?:[0-9a-f]{4}[ \t]+)+([a-z][a-z0-9.]*)[ \t]*(.*)$',
                              disassembly, re.MULTILINE)
    if not instructions:
        raise ValueError('missing semaphore instructions')
    waits = [i for i, (op, _) in enumerate(instructions) if op in ('wfe', 'wfi')]
    if len(waits) != 1 or instructions[waits[0]][0] != 'wfe':
        raise ValueError('expected exactly one SDK event-draining WFE')
    index = waits[0]
    # This is a narrow emitted-pattern check for the pinned SDK/toolchain,
    # not a general ARM control-flow or synchronization proof.
    if index == 0 or index + 1 >= len(instructions):
        raise ValueError('missing event-drain critical section')
    if instructions[index - 1][0] != 'stlb':
        raise ValueError('event drain must immediately follow the unlock store')
    if not (instructions[index + 1][0] == 'msr' and
            instructions[index + 1][1].lower().startswith('primask,')):
        raise ValueError('event drain must precede IRQ restoration')
    irq_state = None
    for op, args in instructions[:index]:
        if op == 'cpsid' and args.strip() == 'i':
            irq_state = 'masked'
        elif op == 'cpsie' or (op == 'msr' and args.lower().startswith('primask,')):
            irq_state = 'restored'
    if irq_state != 'masked':
        raise ValueError('event drain occurs after IRQ restoration')
    if not any(op.startswith('bl') and 'best_effort_wfe_or_timeout' in args
               for op, args in instructions[index + 2:]):
        raise ValueError('missing timeout-aware wait helper after event drain')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf', type=Path)
    args = parser.parse_args()
    result = subprocess.run(['arm-none-eabi-objdump', '-d',
                             '--disassemble=sem_acquire_block_until', str(args.elf)],
                            capture_output=True, text=True, check=True)
    check(result.stdout)
    print('Linked semaphore drains its unlock event before restoring IRQs and calls the timeout-aware helper')


if __name__ == '__main__':
    main()
