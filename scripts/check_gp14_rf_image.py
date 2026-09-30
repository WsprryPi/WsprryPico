#!/usr/bin/env python3
"""Read-only check that finite RF acceptance controls match the selected image."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('elf', type=Path)
parser.add_argument('--acceptance', action='store_true')
args = parser.parse_args()
data = args.elf.read_bytes()
markers = (b'GP14 RF BUSY ', b'rf_busy_refused', b'gp14_rf_acceptance',
           b'gp14_prior_rf_decision_after_launch_us')
assert all((marker in data) == args.acceptance for marker in markers), 'RF acceptance control mismatch'
symbols = subprocess.check_output(['arm-none-eabi-nm', '-C', str(args.elf)], text=True)
assert 'wsprrypico::rf::WorkerEngine::check_safety()' in symbols
assert 'wsprrypico::provisioning::PicoGp14Capture::start()' in symbols
print('GP14 RF safety linked; finite busy control ' + ('present' if args.acceptance else 'absent'))
