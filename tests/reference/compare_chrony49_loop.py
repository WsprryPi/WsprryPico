#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Closed-loop comparison on identical deterministic physical timestamp events.

No host clock, network, board or service is used. Truth is used by the plant and
scorer only, never supplied as a frequency/phase correction to either controller.
The reference exercises SST -> SRC -> REF -> LCL -> SYS_Generic -> plant; muChrony
exercises request -> receive -> selection -> discipline -> virtual UTC -> scorer.
Reference packet admission/poll scheduling is outside this clock-control test.
"""
import argparse
import hashlib
import json
import math
import random
from pathlib import Path
import statistics
import subprocess
import sys

if sys.flags.optimize:
    raise RuntimeError('Validation requires assertions; run without -O')

SECOND = 10**9
EPOCH = 1_800_000_000 * SECOND


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plant(t, case):
    """Uncorrected hardware ticks; includes a continuous frequency step."""
    if 'ramp_ppm_per_hour' in case:
        return round(t + t*case['ppm']/1e6 +
                     .5*case['ramp_ppm_per_hour']*(t/SECOND/3600)*t/1e6)
    switch = case.get('switch_s', 3600) * SECOND
    first, second = case['ppm'], case.get('after_ppm', case['ppm'])
    return round(t + (min(t, switch) * first + max(0, t-switch) * second) / 1e6)


def events(case, tick_s):
    duration = case.get('duration_s', 14400)
    rows = [(t, 0, 0, 0, 1) for t in range(0, (duration+1)*SECOND, round(tick_s*SECOND))]
    poll_times = [1, 3, 5, 7] + list(range(71, duration, 64))
    count = case.get('sources', 1)
    noise_generator = random.Random(case.get('noise_seed', 20261018))
    for i, poll in enumerate(poll_times):
        for slot in range(count):
            send = (poll * SECOND) + slot * 200_000_000
            # A fixed path plus deterministic, symmetric measurement noise.
            noise = round(case.get('noise_s', 0) * SECOND * noise_generator.uniform(-1, 1))
            forward = case.get('forward_ns', 1_000_000) + noise
            backward = case.get('backward_ns', 1_000_000) - noise
            if forward <= 0 or backward <= 0:
                raise ValueError('A physical path delay must be positive')
            if 'queue_s' in case:
                forward += round(case['queue_s'] * SECOND * ((i*7)%11)/10)
            receive = send + forward + backward
            bias = round(case.get('bias_s', 0) * SECOND)
            if 'phase_step_s' in case and send >= case['switch_s'] * SECOND:
                bias += round(case['phase_step_s'] * SECOND)
            if count > 1:
                bias += 100_000_000 if case.get('falseticker') and slot == count-1 else slot*30_000
            server = EPOCH + send + forward + bias
            lost = case.get('loss_start_s', math.inf)*SECOND <= send < case.get('loss_end_s', -1)*SECOND
            rows.append((send, 1, slot, 0, 1))
            rows.append((receive, 3 if lost else 2, slot, server, 1))
    rows.sort()
    return ''.join(f'{t} {plant(t,case)} {action} {slot} {server} {stratum}\n'
                   for t,action,slot,server,stratum in rows)


def run(executable, seed, payload):
    p = subprocess.run([str(executable), str(seed)], input=payload, text=True,
                       capture_output=True, timeout=90)
    if p.returncode:
        raise RuntimeError(f'{executable}: exit {p.returncode}: {p.stderr[-2000:]}')
    result = []
    for line in p.stdout.splitlines():
        row = line.split()
        if len(row) != 9:
            raise RuntimeError(f'Bad output: {line}')
        result.append([int(row[0]), int(row[1]), int(row[2]),
                       *map(float, row[3:7]), int(row[7]), int(row[8])])
        if not all(math.isfinite(v) for v in result[-1]):
            raise RuntimeError(f'Nonfinite output: {line}')
    return result


def summarize(rows, case):
    synced = [r for r in rows if r[1] == 0 and r[7] >= 0 and r[2] > -10**18]
    # Holdover is scored even when synchronization has been withdrawn.
    probes = [r for r in rows if r[1] == 0 and r[0] >= synced[0][0] and r[2] > -10**18]
    if not probes:
        raise RuntimeError('No synchronized clock observations')
    scored = []
    for r in probes:
        t = r[0] / SECOND
        osc = case.get('after_ppm', case['ppm']) if t >= case.get('switch_s', math.inf) else case['ppm']
        osc += case.get('ramp_ppm_per_hour', 0) * t/3600
        freq_error = ((1+osc/1e6)*(1+r[3]/1e6)-1)*1e6
        scored.append((t, (r[2]-r[0])/1e6, freq_error))
    last_hour = [r for r in scored if r[0] >= case.get('duration_s',14400)-3600]
    def settling(threshold, column, start):
        # Earliest probe after which every subsequent available probe meets it.
        eligible = [r for r in scored if r[0] >= start]
        bad = [i for i,r in enumerate(eligible) if abs(r[column]) > threshold]
        index = bad[-1]+1 if bad else 0
        return eligible[index][0]-start if index < len(eligible) else None
    start = case.get('switch_s', 0) if any(k in case for k in ('after_ppm','phase_step_s')) else 0
    return {'first_sync_s': synced[0][0]/SECOND,
            'final_utc_error_ms': scored[-1][1], 'final_frequency_error_ppm': scored[-1][2],
            'last_hour_utc_rms_ms': math.sqrt(statistics.mean(r[1]**2 for r in last_hour)),
            'last_hour_utc_max_abs_ms': max(abs(r[1]) for r in last_hour),
            'last_hour_frequency_max_abs_ppm': max(abs(r[2]) for r in last_hour),
            'settling_start_s': start,
            'utc_settles_1ms_s': settling(1, 1, start),
            'frequency_settles_1ppm_s': settling(1, 2, start),
            'synchronized_probe_count': len(synced), 'valid_probe_count': len(probes)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference', type=Path)
    p.add_argument('microchrony', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--tick-s', type=float, default=1)
    p.add_argument('--cases', nargs='+')
    p.add_argument('--validation-seeds', action='store_true',
                   help='Include fresh pool, ramp and majority noise seeds')
    args = p.parse_args()
    cases = {
        'fast_20ppm': {'ppm': 20},
        'slow_20ppm': {'ppm': -20},
        'zero': {'ppm': 0},
        'wrong_restart_seed': {'ppm': 20, 'seed_ppm': -60},
        'jitter_500us': {'ppm': 20, 'noise_s': .0005},
        'frequency_step': {'ppm': -20, 'after_ppm': 20, 'switch_s': 3600},
        'noisy_frequency_step': {'ppm': -20, 'after_ppm': 20, 'switch_s': 3600, 'noise_s': .0005},
        'server_step_50ms': {'ppm': 20, 'phase_step_s': .05, 'switch_s': 3600},
        'outage': {'ppm': 20, 'noise_s': .0001, 'loss_start_s': 3600, 'loss_end_s': 4800},
        'majority': {'ppm': 20, 'sources': 3, 'noise_s': .0001, 'falseticker': True},
        'heldout_fast_80ppm': {'ppm':80, 'noise_s':.0005, 'noise_seed':17},
        'heldout_slow_80ppm': {'ppm':-80, 'noise_s':.0005, 'noise_seed':42},
        'heldout_ramp': {'ppm':-30, 'ramp_ppm_per_hour':18, 'noise_s':.0001, 'noise_seed':99},
        'heldout_queue': {'ppm':35, 'queue_s':.0005, 'noise_s':.0001, 'noise_seed':2718},
        'heldout_bias': {'ppm':20, 'forward_ns':5_000_000, 'backward_ns':1_000_000},
        'heldout_pool': {'ppm':35, 'sources':4, 'forward_ns':10_000_000,
                         'backward_ns':10_000_000, 'noise_s':.005, 'noise_seed':314159},
    }
    if args.validation_seeds:
        for seed in [271828, 918273, 161803]:
            for base in ['heldout_pool', 'heldout_ramp', 'majority']:
                cases[f'verification_{base}_{seed}'] = dict(cases[base], noise_seed=seed)
    report = {'schema': 'microchrony-chrony49-clock-loop/1',
              'scope': 'Complete source-statistics/selection/clock-feedback loops; common physical timestamp events; external Chrony packet admission and automatic polling excluded',
              'reference_sha256': sha(args.reference), 'microchrony_sha256': sha(args.microchrony),
              'tick_s': args.tick_s, 'cases': {}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for name, case in cases.items():
        if args.cases and name not in args.cases:
            continue
        payload = events(case, args.tick_s)
        seed = case.get('seed_ppm', 0)
        ref = run(args.reference, seed, payload)
        mu = run(args.microchrony, -seed/(1+seed/1e6), payload)
        assert [(r[0],r[1]) for r in ref] == [(r[0],r[1]) for r in mu]
        summary = {'chrony49': summarize(ref,case), 'microchrony': summarize(mu,case)}
        report['cases'][name] = {'plant':case, 'input_sha256':hashlib.sha256(payload.encode()).hexdigest(),
                                 'summary':summary, 'reference_rows':ref, 'microchrony_rows':mu}
        print(name, json.dumps(summary), flush=True)
    args.output.write_text(json.dumps(report,separators=(',',':'))+'\n')


if __name__ == '__main__':
    main()
