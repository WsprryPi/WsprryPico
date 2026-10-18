#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline captured-metadata adapter checks; requires an existing private oracle."""
import subprocess
import sys

from compare_chrony49_loop import events

if sys.flags.optimize:
    raise RuntimeError('Validation requires assertions; run without -O')

microchrony, reference = sys.argv[1:]
payload = events({'ppm': 20, 'duration_s': 7200}, 1)


def captured(processing=0, dispersion=0):
    result = []
    for line in payload.splitlines():
        truth, raw, action, slot, server, stratum = map(int, line.split())
        receive = server
        previous = server-10**9 if server else 0
        if action == 2:
            receive -= processing//2
            server += processing//2
        result.append(f'{truth} {raw} {action} {slot} {server} {stratum} '
                      f'{receive} {previous} 0 {dispersion} -20 0')
    return '\n'.join(result)+'\n'


def run(executable, mode, data):
    result = subprocess.run([executable, '0', *mode], input=data, text=True,
                            capture_output=True, timeout=45, check=True)
    return result.stdout, [line.split() for line in result.stdout.splitlines()]


for executable in (microchrony, reference):
    original, _ = run(executable, [], payload)
    _, equivalent = run(executable, ['captured'], captured())
    base_columns = ''.join(' '.join(row[:9])+'\n' for row in equivalent)
    assert original == base_columns, 'metadata defaults changed the existing loop'
    _, phase = run(executable, ['captured-phase'], captured())
    assert all(abs(float(row[3])) < .000001 for row in phase), 'phase baseline applied rate'
    _, processing = run(executable, ['captured'], captured(processing=200000))
    assert all(len(row) == 11 for row in processing), 'missing quality fields'
    later = [row for row in processing if row[1] == '0' and int(row[0]) >= 3600*10**9]
    assert later and all(int(row[7]) >= 0 for row in later)
    assert all(int(row[9]) <= 500000000 and int(row[10]) <= 90*10**9 for row in later)
    assert max(abs(int(row[2])-int(row[0])) for row in later) < 50000, 'server midpoint biased UTC'
    _, rejected = run(executable, ['captured'], captured(dispersion=4*65536))
    assert all(int(row[7]) < 0 for row in rejected), 'root-distance gate was weakened'
print('Both adapters preserve default rows, disable rate in phase controls, remove server processing, and retain the root-distance gate.')
