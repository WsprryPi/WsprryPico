#!/usr/bin/env python3
"""Check the selected application engine in the actual linked ELF, without hardware."""
import argparse
from pathlib import Path
import subprocess


def validate(symbols, expected):
    physical = expected == 'rf'
    for marker in ('wsprrypico::rf::start_worker(',
                   'wsprrypico::rf::WorkerEngine::',
                   'wsprrypico::rf::PicoPioDma',
                   'wsprrypico::rf::Waveform::render('):
        if (marker in symbols) != physical:
            raise ValueError('Application RF linkage mismatch: ' + marker)
    if ('wsprrypico::standalone::DryRunEngine::' in symbols) == physical:
        raise ValueError('Application simulator linkage mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf', type=Path)
    parser.add_argument('--expect', choices=('rf', 'inhibited'), required=True)
    args = parser.parse_args()
    symbols = subprocess.check_output(['arm-none-eabi-nm', '-C', str(args.elf)], text=True)
    validate(symbols, args.expect)
    print('Linked application engine: ' + args.expect)


if __name__ == '__main__':
    main()
