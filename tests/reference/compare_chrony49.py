#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare original muChrony with a separately built, unmodified Chrony 4.9 SST oracle.

Arguments: external-sst-oracle microchrony_tests output.json
This is a differential characterization, not a full Chrony conformance certificate.
No networking, host clock control, source download or upstream code import occurs.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def series(name):
    values = []
    offset = 0
    for i in range(1, 65):
        rate = 20e-6 if name == 'positive_rate' else -20e-6
        if name == 'zero_rate':
            rate = 0
        if name == 'drift_change' and i > 32:
            rate = 20e-6
        offset += rate * 64
        delay = .002
        noise = .0005 * (-1 if i % 2 else 1) if name == 'alternating' else 0
        if name in ('queues', 'reverse_queues'):
            queue = (i * 17 % 11) * .003
            delay += queue
            noise = queue * (.5 if name == 'queues' else -.5)
        if name == 'correlated_delay':
            delay = .01 + .00015 * i + (.0005 if i % 2 else -.0005)
            noise = .4 * delay + ((i * 7) % 5 - 2) * .00004
        values.append((1800000000 + i * 64, offset + noise, delay, 0))
    return '\n'.join(' '.join(f'{x:.12f}' for x in row) for row in values) + '\n'


def run(executable, payload, *args):
    result = subprocess.run([executable, *args], input=payload, text=True,
                            capture_output=True, check=True)
    return [[float(x) for x in line.split()] for line in result.stdout.splitlines()]


if sys.flags.optimize:
    raise RuntimeError('Validation requires assertions; run without -O')
oracle, engine, output = sys.argv[1:]
report = {'schema': 'microchrony-chrony49-differential/1',
          'oracle_sha256': sha(oracle), 'engine_sha256': sha(engine),
          'reference_scope': 'Chrony 4.9 source statistics API; delay admission disabled in both drivers',
          'full_equivalence_demonstrated': False, 'adaptive_acceptance': 'bounded causal recovery and covariance coverage, not identical floating-point pruning', 'cases': {}}
for name in ('negative_rate', 'positive_rate', 'zero_rate', 'alternating',
             'queues', 'reverse_queues', 'drift_change', 'correlated_delay'):
    payload = series(name)
    expected, actual = run(oracle, payload), run(engine, payload, 'stats')
    assert len(expected) == len(actual) == 64
    pairs = [(a, b) for a, b in zip(expected, actual) if a[0] >= 3]
    delta = max(abs(a[3] - b[3]) * 1e9 for a, b in pairs)
    skew_delta = max(abs(a[5] - b[5]) * 1e9 for a, b in pairs)
    # Exact noiseless drift and ordinary stationary noise have a narrow
    # independent numerical tolerance; adaptation cases remain explicitly measured.
    if name in ('negative_rate', 'positive_rate', 'zero_rate', 'alternating'):
        assert delta < 1, (name, delta)
        assert skew_delta < 2, (name, skew_delta)
    if name in ('queues', 'reverse_queues'):
        assert delta < 5, (name, delta)
    if name == 'correlated_delay':
        # The original full joint covariance remains conservative; matching
        # a smaller reference skew is not an acceptance criterion.
        assert delta < 1000, (name, delta)
        for row in actual[12:]:
            assert abs(row[3] - 20e-6) <= max(row[5], 1e-12), (name, row)
    if name == 'drift_change':
        # Both implementations must discard obsolete history and recover from
        # the injected 40 ppm change within eight admitted observations.
        for label, rows in [('reference', expected), ('microchrony', actual)]:
            assert rows[39][1] <= 16, (name, label, rows[39])
            assert abs(rows[39][3] + 20e-6) < 5e-9, (name, label, rows[39])
            assert abs(rows[-1][3] + 20e-6) < 5e-9, (name, label, rows[-1])
    report['cases'][name] = {
        'input_sha256': hashlib.sha256(payload.encode()).hexdigest(),
        'points': 64, 'max_frequency_difference_ppb': delta,
        'max_skew_difference_ppb': skew_delta,
        'final_reference_frequency_ppb': expected[-1][3] * 1e9,
        'final_microchrony_frequency_ppb': actual[-1][3] * 1e9,
        'final_reference_samples': expected[-1][1],
        'final_microchrony_samples': actual[-1][1],
        'reference_rows': expected, 'microchrony_rows': actual}
Path(output).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps({key: {k: v for k, v in value.items() if not k.endswith('_rows')}
                  for key, value in report['cases'].items()}, indent=2))
