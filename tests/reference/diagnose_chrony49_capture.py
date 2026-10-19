#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Cold pooled replays of hash-bound admitted originals; no device operations.

The private evidence tree must include final-manifest.json and the specified
pulse-history segment. Missing pre-capture inputs remain missing. Zero initial
learned rate is common; RTC acquisition is explicit, not reconstructed live boot.
The external reference starts at the NTP sample API, after packet admission.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys

SECOND = 10**9
EPOCH = 1_800_000_000 * SECOND


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(binary, payload, mode='captured'):
    process = subprocess.run([str(binary.resolve()), '0', mode], input=payload,
                             text=True, capture_output=True, timeout=60, check=True,
                             env=dict(os.environ, MICROCHRONY_DIAGNOSTICS='1'))
    probes = []
    for line in process.stdout.splitlines():
        f = line.split()
        assert len(f) == 11, line
        row = [int(f[0]), int(f[1]), int(f[2]), *map(float, f[3:7]), *map(int, f[7:])]
        assert all(math.isfinite(v) for v in row)
        if row[1] == 0:
            probes.append(row)
    return probes, process.stderr


def qualified(row):
    return row[7] >= 0 and row[9] <= 500_000_000 and row[10] <= 90 * SECOND


def main():
    if sys.flags.optimize:
        raise RuntimeError('Validation requires assertions; run without -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('reference', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--segment', default='resume/pulse-history')
    parser.add_argument('--matched-rtc', action='store_true',
                        help='Both clocks start at the translated UTC origin, before any sample')
    args = parser.parse_args()
    root = args.evidence.resolve(strict=True)
    segment = (root / args.segment).resolve(strict=True)
    assert segment.is_relative_to(root)
    manifest = json.loads((root/'final-manifest.json').read_text())['files']
    hashes = {}

    def load(path):
        name = str(path.relative_to(root))
        assert name in manifest and sha(path) == manifest[name]['sha256'], name
        hashes[name] = sha(path)
        return path.read_text()

    baseline = json.loads(load(segment/'capture-baseline.json'))['boards']
    pulses = [json.loads(line) for line in load(segment/'pulses.jsonl').splitlines()]
    report = {'schema':'microchrony-captured-pool-diagnosis/1', 'script_sha256':sha(__file__),
              'manifest_sha256':sha(root/'final-manifest.json'), 'boards':{},
              'binaries_sha256':{n:sha(p) for n,p in [('before',args.before), ('after',args.after),
                                                    ('chrony49',args.reference)]},
              'limits':['Cold zero-frequency initialization; incomplete pre-capture boot history.',
                        'Admitted originals only; rejected packets and autonomous polling excluded.',
                        'Stable endpoint/epoch per slot required; no association reconstruction.',
                        'Pulse UTC path delay and reference allowance are not calibrated.',
                        'Replay output is not evidence of firmware application on a board.',
                        'No RF correction or independent absolute UTC qualification.'],
              'production_gates_changed':False}
    report['acquisition'] = ('Common synthetic initial RTC at the first-sample translated origin; '
                             'zero learned frequency. Conditional prior, not recovered boot state.'
                             if args.matched_rtc else
                             'Chrony RTC versus Pico first epoch assignment; zero learned frequency.')
    for board in 'AB':
        cohorts = {}
        identities = set()
        for path in sorted(segment.glob(board+'-history-*.json')):
            value = json.loads(load(path))['response']
            if not value.get('ok'):
                continue
            identities.add(tuple(value[k] for k in ('device_id','boot_id','firmware','revision')))
            key = value['boot_id'], value['slot'], value['endpoint'], value['clock_epoch']
            records = cohorts.setdefault(key, {})
            for record in value['records']:
                assert record['clock_epoch'] == key[3]
                if record['id'] in records:
                    assert records[record['id']] == record
                records[record['id']] = record
        assert len(cohorts) == 4 and {k[1] for k in cohorts} == set(range(4))
        assert len({k[0] for k in cohorts}) == 1
        frontier = json.loads(load(sorted(segment.glob(board+'-final-frontier-info-*.json'))[-1]))['response']
        assert {k[0] for k in cohorts} == {frontier['status']['boot_id']}
        identity = (frontier['device_id'],frontier['status']['boot_id'],
                    frontier['firmware'],frontier['revision'])
        assert identities == {identity}
        visibility = {}
        for key, records in sorted(cohorts.items()):
            slot = key[1]
            base = baseline[board][str(slot)]
            peer = next(p for p in frontier['network']['ntp_pool']['peers'] if p['slot'] == slot)
            assert peer['endpoint'] == key[2]
            accepted = peer['accepted']
            new_captured = len(records) - base['captured_originals']
            assert new_captured == accepted - base['accepted_packets'], (board,slot)
            visibility[str(slot)] = dict(new_captured=new_captured,
                                         missing_before_capture=base['unseen_before_capture'])
        records = sorted((int(r['receive_raw_ns']),key,r) for key,c in cohorts.items() for r in c.values())
        anchor = min(int(r['send_raw_ns']) for _,_,r in records) - SECOND
        first = records[0][2]
        utc_anchor = ((int(first['server_receive_ns']) + int(first['server_send_ns'])) // 2 -
                      ((int(first['send_raw_ns']) + int(first['receive_raw_ns'])) // 2 - anchor))
        events = []
        for _,key,r in records:
            fields = [EPOCH + int(r['server_send_ns']) - utc_anchor, r['stratum'],
                      EPOCH + int(r['server_receive_ns']) - utc_anchor,
                      EPOCH + int(r['server_reference_ns']) - utc_anchor,
                      r['root_delay_16_16'],r['root_dispersion_16_16'],r['precision'],r['leap']]
            events.extend([(int(r['send_raw_ns']),1,key[1],fields),
                           (int(r['receive_raw_ns']),2,key[1],fields)])
        points = [r for r in pulses if r['board'] == board]
        assert all(tuple(r['pico'][k] for k in ('device_id','boot_id','firmware','revision')) == identity
                   for r in points)
        raw_points = [(int(r['pico']['rise_raw_lower_ns']) + int(r['pico']['rise_raw_upper_ns'])) // 2
                      for r in points]
        assert raw_points == sorted(set(raw_points))
        assert raw_points[-1] < int(frontier['status']['monotonic_now_ns'])
        events += [(t,0,0,[0,1,0,0,0,0,-20,0]) for t in raw_points]
        events.sort()
        payload = ''.join(' '.join(map(str,[t-anchor,t-anchor,action,slot,*fields]))+'\n'
                          for t,action,slot,fields in events)
        outputs, diagnostics = {}, {}
        for name,binary in [('before',args.before),('after',args.after),('chrony49',args.reference)]:
            outputs[name], diagnostics[name] = run(binary,payload,
                'captured-rtc' if args.matched_rtc else 'captured')
            assert [r[0] for r in outputs[name]] == [t-anchor for t in raw_points]
        common = [i for i in range(len(points)) if all(qualified(r[i]) for r in outputs.values())]
        metrics = {}
        for name,rows in outputs.items():
            indicated = [rows[i][2] + utc_anchor - points[i]['events'][0]['timestamp_ns'] for i in common]
            metrics[name] = {
                'first_frequency_ppm':rows[0][3], 'final_frequency_ppm':rows[-1][3],
                'frequency_range_ppm':[min(r[3] for r in rows),max(r[3] for r in rows)],
                'stale_pulse_indices':[i for i,r in enumerate(rows) if r[10] > 90 * SECOND],
                'unqualified_pulse_indices':[i for i,r in enumerate(rows) if not qualified(r)],
                'rms_frequency_delta_from_chrony_ppm':math.sqrt(statistics.mean(
                    (r[3]-c[3])**2 for r,c in zip(rows,outputs['chrony49']))),
                'common_pulse_indicated_utc_rms_ms':math.sqrt(statistics.mean(v*v for v in indicated))/1e6,
                'common_pulse_indicated_utc_range_ms':[min(indicated)/1e6,max(indicated)/1e6],
            }
        report['boards'][board] = dict(originals=len(records), visibility=visibility,
                                       input_sha256=hashlib.sha256(payload.encode()).hexdigest(),
                                       pulse_count=len(points), common_qualified_pulses=len(common),
                                       metrics=metrics, rows=outputs, diagnostics=diagnostics)
        print(board,json.dumps(metrics),flush=True)
    report['inputs_sha256'] = hashes
    args.output.write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
