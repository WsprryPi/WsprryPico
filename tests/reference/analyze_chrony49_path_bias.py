#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Indicated source/path bias against retained GPIO timestamps; offline only.

Interpolation assumes a locally linear raw clock between adjacent measured
edges. It neither calibrates the GPIO path nor separates server error from
one-way network asymmetry. No pulse is used to steer either replay controller.
"""
import argparse
from bisect import bisect_right
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import statistics
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(root, cohort_path, histories_path):
    cohort = json.loads(cohort_path.read_text())
    histories = json.loads(histories_path.read_text())
    assert histories['cohort_sha256'] == sha(cohort_path)
    for name, digest in cohort['inputs_sha256'].items():
        assert sha(root/name) == digest, name
    pulses = [json.loads(line) for line in (root/'pulse-history/pulses.jsonl').read_text().splitlines()]
    report = {'schema': 'captured-source-path-bias/1', 'cohort_sha256': sha(cohort_path),
              'histories_sha256': sha(histories_path), 'script_sha256': sha(Path(__file__)),
              'absolute_path_calibrated': False,
              'interpolation': 'Locally linear raw clock between physical pulse edges; no extrapolation.',
              'inference_limit': 'Server clock bias and one-way network asymmetry remain inseparable.',
              'boards': {}}
    for board in 'AB':
        points = [r for r in pulses if r['board'] == board]
        raw = [(int(r['pico']['rise_raw_lower_ns'])+int(r['pico']['rise_raw_upper_ns']))//2 for r in points]
        host = [r['events'][0]['timestamp_ns'] for r in points]
        sources = {}
        for slot in range(4):
            originals = {}
            identities = set()
            for name in cohort['inputs_sha256']:
                if not Path(name).name.startswith(board+'-history-'):
                    continue
                page = json.loads((root/name).read_text())['response']
                if page.get('ok') and page['slot'] == slot:
                    identities.add(tuple(page[k] for k in ('boot_id', 'endpoint', 'clock_epoch')))
                    for r in page['records']:
                        if r['id'] in originals:
                            assert originals[r['id']] == r, 'Original changed'
                        originals[r['id']] = r
            assert len(identities) == 1, 'Source cohort changed'
            records = sorted(originals.values(), key=lambda r: int(r['receive_raw_ns']))
            before = max(i for i, r in enumerate(records) if int(r['receive_raw_ns']) <= raw[0])
            fit = histories['sources'][board+str(slot)]
            assert len(records) == fit['points'] == len(fit['reference_rows'])
            indicated = []
            delays = []
            values = []
            for r in records:
                midpoint = (int(r['send_raw_ns'])+int(r['receive_raw_ns']))//2
                i = bisect_right(raw, midpoint)-1
                if not 0 <= i < len(raw)-1:
                    continue
                assert 0 < raw[i+1]-raw[i] < 12*10**9
                gps = F(host[i]) + F(midpoint-raw[i], raw[i+1]-raw[i])*(host[i+1]-host[i])
                server = F(int(r['server_receive_ns'])+int(r['server_send_ns']), 2)
                error = float(server-gps)
                delay = int(r['receive_raw_ns'])-int(r['send_raw_ns'])-int(r['server_send_ns'])+int(r['server_receive_ns'])
                indicated.append(error);delays.append(delay)
                values.append({'id': r['id'], 'raw_midpoint_ns': midpoint,
                               'indicated_source_bias_ns': error, 'peer_delay_ns': delay})
            assert len(indicated) >= 20
            mx, my = statistics.mean(delays), statistics.mean(indicated)
            xx = sum((v-mx)**2 for v in delays)
            yy = sum((v-my)**2 for v in indicated)
            xy = sum((x-mx)*(y-my) for x, y in zip(delays, indicated))
            sources[str(slot)] = {
                'first_capture_raw_coordinate_rate_ppm': -fit['reference_rows'][before][3]*1e6,
                'first_capture_conditional_skew_ppm': fit['reference_rows'][before][5]*1e6,
                'final_raw_coordinate_rate_ppm': -fit['reference_rows'][-1][3]*1e6,
                'independently_bracketed_observations': len(indicated),
                'indicated_source_bias_ms_range': [min(indicated)/1e6, max(indicated)/1e6],
                'indicated_source_bias_median_ms': statistics.median(indicated)/1e6,
                'peer_delay_ms_range': [min(delays)/1e6, max(delays)/1e6],
                'delay_error_correlation': xy/(xx*yy)**.5 if xx and yy else 0,
                'delay_error_regression_coefficient': xy/xx if xx else 0,
                'points': values}
        report['boards'][board] = sources
    return report


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Validation requires assertions; run without -O')
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('evidence', 'cohort', 'histories', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    report = analyze(args.evidence, args.cohort, args.histories)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({b: {s: {k: v for k, v in values.items() if k != 'points'}
                         for s, values in sources.items()}
                     for b, sources in report['boards'].items()}, indent=2))
