#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Isolate adaptive history and source combination using public reference APIs.

Upstream SST/SRC objects remain unmodified and outside firmware. Combination
uses the exact same source estimates at the REF boundary in both calculators.
"""
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys

if sys.flags.optimize:
    raise RuntimeError('Validation requires assertions; run without -O')


def run(binary, payload, *args):
    return subprocess.run([str(binary), *args], input=payload, text=True,
                          capture_output=True, check=True, timeout=60).stdout


def compare(stats, combination, tests, engine, output):
    report = {'schema': 'microchrony-chrony49-adaptation/1', 'histories': {},
              'combinations': {}, 'binaries_sha256': {
                  str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in [stats, combination, tests, engine]}}
    # Fresh seeds and disturbances exercise the horizon beyond its 64-point
    # active capacity; no future row chooses an earlier model/window.
    for seed in [314159, 271828, 918273]:
        for mode in ['stationary', 'ramp']:
            rng = random.Random(seed)
            rows = []
            for i in range(256):
                t = (i+1)*64
                offset = t*35e-6 + (0.5*18e-6*t*t/3600 if mode == 'ramp' else 0)
                offset += rng.uniform(-1, 1) * (.0001 if mode == 'ramp' else .005)
                rows.append(f'{1800000000+t} {offset:.12f} .02 .000002\n')
            payload = ''.join(rows)
            ref = [list(map(float, l.split())) for l in run(stats, payload).splitlines()]
            mu = [list(map(float, l.split())) for l in run(tests, payload, 'stats').splitlines()]
            assert len(ref) == len(mu) == 256
            count_mismatches = [i+1 for i, (a,b) in enumerate(zip(ref,mu)) if a[1] != b[1]]
            assert not count_mismatches, (mode, seed, count_mismatches)
            frequency_delta = max(abs(a[3]-b[3]) for a,b in zip(ref[2:],mu[2:]))
            assert frequency_delta < 5e-9, (mode,seed,frequency_delta)
            report['histories'][f'{mode}_{seed}'] = {
                'input_sha256': hashlib.sha256(payload.encode()).hexdigest(),
                'points': 256, 'count_mismatches': count_mismatches,
                'max_frequency_delta_ppb': frequency_delta*1e9,
                'reference_rows': ref, 'microchrony_rows': mu}
    for seed in [1701, 2802, 3903]:
        rng = random.Random(seed)
        payload = ''.join(
            f'{slot} {1800000000+i*64+slot*.2:.9f} '
            f'{i*64*35e-6+slot*.00003+rng.uniform(-.005,.005):.12f} '
            f'{.02+slot*.003:.9f} .000002 1 0 1\n'
            for i in range(1,97) for slot in range(4))
        reference = run(combination,payload)
        inputs, expected = [], []
        for line in reference.splitlines():
            if not line.startswith('C '):
                continue
            values = list(map(float,line.split()[1:]))
            event,count,selected,epoch,offset,sd,rate,rate_sd,skew,delay,dispersion = values[:11]
            if count != 4:
                continue
            sources = [values[j:j+10] for j in range(11,len(values),10)]
            selected_fit = sources[int(selected)-1]
            origin = selected_fit[1] + selected_fit[3]*(epoch-selected_fit[0])
            inputs.append('4\n')
            for t,o,s,f,fs,k,d,p,distance,variance in sources:
                inputs.append(f'{o+f*(epoch-t)-origin:.15g} {s} {f} {fs} {k} '
                              f'{distance} {epoch-t}\n')
            expected.append([offset-origin,sd,rate,rate_sd,skew])
        actual = [list(map(float,l.split())) for l in run(engine,''.join(inputs),'combination').splitlines()]
        assert len(actual) == len(expected) >= 80
        deltas = [max(abs(a[j]-b[j]) for a,b in zip(actual,expected)) for j in range(5)]
        assert deltas[0] < 1e-9 and deltas[1] < 1e-9, deltas
        assert all(d < 1e-12 for d in deltas[2:]), deltas
        # The public bound still covers every admitted source's frequency
        # interval; the controller's combined statistical error cannot replace it.
        for row in actual:
            assert row[5] >= row[4]
        report['combinations'][str(seed)] = {
            'input_sha256': hashlib.sha256(payload.encode()).hexdigest(),
            'reference_output_sha256': hashlib.sha256(reference.encode()).hexdigest(),
            'same_estimates_input_sha256': hashlib.sha256(''.join(inputs).encode()).hexdigest(),
            'points':len(actual), 'max_deltas':deltas,
            'reference_rows':expected,'microchrony_rows':actual}
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(len(report['histories']), '256-point adaptive histories matched;',
          sum(r['points'] for r in report['combinations'].values()),
          'same-estimate combinations matched')


if __name__ == '__main__':
    compare(*map(Path, sys.argv[1:]))
