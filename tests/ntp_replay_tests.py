#!/usr/bin/env python3
"""Exact integer oracle and identical deterministic, held-out time traces."""
import json
import random
import statistics
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

NS = 10**9
EPOCH = 1_800_000_000 * NS
DRIVER = sys.argv[1]
if sys.flags.optimize:
    raise RuntimeError('Validation requires assertions; run without -O')


def ceil(value):
    return -(-value.numerator // value.denominator)


def oracle():
    rng = random.Random(5905)
    cases = [(0, EPOCH, r, EPOCH + delta) for r in (-100000, -10000, 0, 10000, 100000)
             for delta in (0, 1, 999, 1000, NS - 1, NS, 604800 * NS)]
    cases += [(rng.randrange(10**15), EPOCH + rng.randrange(10**15), rng.randint(-100000, 100000),
               EPOCH + rng.randrange(10**15)) for _ in range(200)]
    for raw, utc, rate, target in cases:
        exact = raw + ceil(Fraction((target - utc) * NS, NS + rate))
        output = subprocess.check_output([DRIVER, 'map', str(raw), str(utc), str(rate), str(target)], text=True).strip()
        if not 0 <= exact <= 2**64 - 1:
            assert output == 'invalid', (raw, utc, rate, target, output)
            continue
        actual_raw, actual_utc = map(int, output.split())
        assert actual_raw == exact
        projected = utc + ((exact - raw) * (NS + rate)) // NS
        assert actual_utc == projected >= target
        if exact:
            assert utc + ((exact - raw - 1) * (NS + rate)) // NS < target
    return len(cases)


def trace(name):
    raw, truth = 10 * NS, EPOCH
    result = []
    for i in range(100):
        step = (2 if name == 'retry_burst' and i < 8 else 64) * NS
        if name == 'outage' and i == 45:
            step = 256 * NS
        slope = -20000 if name != 'negative_rate' else 20000
        if name == 'drift_change' and i >= 50:
            slope = 20000
        if name == 'zero_rate':
            slope = 0
        raw += step
        truth += step * (NS + slope) // NS
        uncertainty, error, rtt = 2_000_000, 0, 1_000_000
        if name in ('queues', 'processing', 'spikes') or name == 'retry_burst' and i < 8:
            queue = (i * 17 % 11) * 3_000_000
            if name == 'spikes' and i % 9 == 0:
                queue += 240_000_000
            error = (-queue if name == 'processing' else queue) // 2
            rtt += queue
            uncertainty += queue
        if name == 'rising_delay':
            rtt += i * 4_000_000
            error = i * 2_000_000
            uncertainty += i * 4_000_000
        if name == 'asymmetric_bias':
            error, uncertainty = 20_000_000, 100_000_000
        if name == 'phase_step' and i >= 45:
            error += 2 * NS  # incompatible server phase, not a truth change
        endpoint = 2 if name == 'source_change' and i >= 50 else 1
        accepted = not (name == 'loss' and 40 <= i <= 45 or name == 'outage' and 45 <= i <= 50)
        result.append((i + 1, endpoint, raw, truth + error, uncertainty, rtt,
                       raw + 32 * NS, truth + 32 * (NS + slope), int(accepted)))
        if name == 'duplicates' and i % 7 == 0:
            result.append(result[-1])
    return result


def replay():
    report = {}
    for name in ('constant_delay', 'queues', 'processing', 'spikes', 'rising_delay',
                 'loss', 'duplicates', 'outage', 'phase_step', 'drift_change',
                 'source_change', 'asymmetric_bias', 'negative_rate', 'zero_rate', 'retry_burst'):
        inputs = trace(name)
        payload = '\n'.join(' '.join(map(str, row)) for row in inputs) + '\n'
        output = subprocess.check_output([DRIVER, 'replay'], input=payload, text=True)
        modes = [[], [], []]
        for row in output.splitlines():
            mode, sample, error, uncertainty, age, usable, rate = map(int, row.split())
            modes[mode].append((sample, error, uncertainty, age, usable, rate))
        report[name] = {}
        for label, rows in zip(('offset_only', 'filter_only', 'filter_rate'), modes):
            admitted = [r for r in rows if r[4]]
            errors = [r[1] for r in admitted]
            jitter = [abs(b - a) for a, b in zip(errors, errors[1:])]
            report[name][label] = {
                'probes': len(rows), 'launch_available': len(admitted),
                'coverage': sum(abs(r[1]) <= r[2] for r in admitted),
                'max_abs_error_ns': max(map(abs, errors), default=None),
                'median_abs_error_ns': statistics.median(map(abs, errors)) if errors else None,
                'max_error_change_ns': max(jitter, default=None),
                'nonzero_rate_probes': sum(r[5] != 0 for r in rows),
                'max_admitted_age_ns': max((r[3] for r in admitted), default=None),
            }
            # The server step intentionally lies outside its declared uncertainty.
            # Existing two-observation reacquisition can accept a consistently wrong server.
            # This is an explicit absolute-accuracy limitation, not covered truth.
            if name != 'phase_step':
                assert report[name][label]['coverage'] == len(admitted), (name, label)
            assert all(r[3] <= 90 * NS for r in admitted)
        assert report[name]['filter_rate']['launch_available'] == report[name]['offset_only']['launch_available']
        if name in ('constant_delay', 'negative_rate'):
            rates = report[name]['filter_rate']
            assert rates['nonzero_rate_probes'] > 50
            assert rates['median_abs_error_ns'] < report[name]['filter_only']['median_abs_error_ns']
        if name == 'asymmetric_bias':
            assert report[name]['filter_rate']['nonzero_rate_probes'] == 0
            assert report[name]['filter_rate']['median_abs_error_ns'] >= 20_000_000
    return report


result = {'schema': 'ntp-work-replay/1', 'oracle_cases': oracle(), 'traces': replay(),
          'physical_utc_or_rf_qualification': False}
if len(sys.argv) == 3:
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
else:
    print(json.dumps(result, sort_keys=True))
