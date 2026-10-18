#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Causal clock-loop replay of admitted Pico originals, with no independent UTC truth.

Both adapters receive identical raw send/receive ticks, server timestamps and
wire quality fields. Each probe precedes admission of its own NTP reply. The
external reference enters at Chrony's sample API, not its packet-admission path.
"""
import argparse
import hashlib
import json
import math
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


def metrics(values):
    values = list(values)
    ordered = sorted(abs(v) for v in values)
    return {'count': len(values),
            'median_abs_ms': statistics.median(ordered)/1e6 if ordered else None,
            'rms_ms': math.sqrt(statistics.mean(v*v for v in values))/1e6 if values else None,
            'p95_abs_ms': ordered[min(len(ordered)-1, int(.95*len(ordered)))]/1e6 if ordered else None}


def run(executable, payload, phase_only):
    process = subprocess.run([str(executable), '0', 'captured-phase' if phase_only else 'captured'],
                             input=payload, text=True, capture_output=True, timeout=30, check=True)
    rows = []
    for line in process.stdout.splitlines():
        row = line.split()
        assert len(row) == 11, line
        values = [int(row[0]), int(row[1]), int(row[2]),
                  *map(float, row[3:7]), *map(int, row[7:11])]
        assert all(math.isfinite(x) for x in values)
        if phase_only:
            assert abs(values[3]) < .000001, 'phase-only counterfactual applied frequency'
        if values[1] == 0:
            rows.append(values)
    return rows, process.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('microchrony', type=Path)
    parser.add_argument('reference', type=Path)
    parser.add_argument('validated', type=Path, help='analyze_microchrony_capture.py output')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    validated = json.loads(args.validated.read_text())
    for name, digest in validated['inputs_sha256'].items():
        assert sha(args.capture/name) == digest, name
    baseline_path = args.capture/'capture-baseline.json'
    baseline = json.loads(baseline_path.read_text())['boards']
    report = {
        'schema': 'microchrony-chrony49-captured-clock-loop/1',
        'reference_sha256': sha(args.reference), 'microchrony_sha256': sha(args.microchrony),
        'script_sha256': sha(__file__), 'validated_manifest_sha256': sha(args.validated),
        'capture_baseline_sha256': sha(baseline_path),
        'baseline_frontiers_sha256': {},
        'independent_utc_or_rf_truth': False,
        'common_probe_gates': {'synchronized': True, 'maximum_age_ns': 90*SECOND,
                               'maximum_reported_clock_error_ns': 500_000_000},
        'scope': 'Separate cold source-to-clock replays; identical captured raw ticks and wire fields; next-original NTP-proxy scoring before admission.',
        'utc_origin': 'First server midpoint selects a common coordinate origin; the reference RTC initially shares it, while Engine assigns UTC from a usable fit. RTC/boot acquisition is not compared.',
        'offset_control': 'Last admitted raw/UTC midpoint, no learned frequency; 100 ppm supported-drift error envelope plus measured path/root uncertainty.',
        'limits': ['No live combined-clock reconstruction, persisted seed or rejected-packet reconstruction.',
                   'External Chrony NTP sample API; UDP admission, autonomous polls and DNS are excluded.',
                   'Raw ticks define the replay plant; no independent oscillator or UTC truth is available.',
                   'NTP timestamp re-encoding introduces at most nanosecond-scale quantization.',
                   'Phase-only counterfactual tightens max-update-skew; production gates are unchanged.'],
        'boards': {},
    }
    for board in ['A', 'B']:
        paths = sorted(args.capture.glob(board+'-observe-*.json'))
        infos = [json.loads(p.read_text())['response'] for p in paths]
        assert infos
        begin = int(infos[0]['status']['monotonic_now_ns'])
        end = int(infos[-1]['status']['monotonic_now_ns'])
        cohorts = {}
        pages = []
        for path in sorted(args.capture.glob(board+'-history-*.json')):
            wrapper = json.loads(path.read_text())
            value = wrapper['response']
            if not value.get('ok'):
                continue
            pages.append(wrapper)
            key = value['boot_id'], value['slot'], value['endpoint'], value['clock_epoch']
            cohort = cohorts.setdefault(key, {})
            for record in value['records']:
                if record['id'] in cohort:
                    assert cohort[record['id']] == record
                cohort[record['id']] = record
        frontiers = sorted(args.capture.glob(board+'-baseline-frontier-*.json'))
        assert frontiers
        frontier = json.loads(frontiers[-1].read_text())
        report['baseline_frontiers_sha256'][frontiers[-1].name] = sha(frontiers[-1])
        assert (frontier['response']['device_id'], frontier['response']['status']['boot_id'],
                frontier['response']['firmware'], frontier['response']['revision']) == (
                    infos[0]['device_id'], infos[0]['status']['boot_id'],
                    infos[0]['firmware'], infos[0]['revision'])
        initial_records = set()
        for wrapper in pages:
            if wrapper['host_wall_ns'] >= frontier['host_wall_start_ns']:
                continue
            value = wrapper['response']
            for record in value['records']:
                initial_records.add((value['slot'], value['endpoint'], value['clock_epoch'], record['id']))
        visibility = {}
        for peer in infos[-1]['network']['ntp_pool']['peers']:
            slot = peer['slot']
            initial = next(p for p in frontier['response']['network']['ntp_pool']['peers'] if p['slot'] == slot)
            base = baseline[board][str(slot)]
            initial_count = sum(key[0] == slot for key in initial_records)
            assert initial['accepted'] == base['accepted_packets']
            assert initial_count == base['captured_originals']
            count = sum(len(records) for key, records in cohorts.items() if key[1] == slot)
            assert count-initial_count == peer['accepted']-initial['accepted'], 'lost accepted input'
            visibility[str(slot)] = {'new_accepted': peer['accepted']-initial['accepted'],
                                     'new_captured': count-initial_count,
                                     'pre_capture_missing': base['unseen_before_capture']}
        board_report = {'source': infos[-1]['network']['ntp_server'],
                        'visibility': visibility, 'cohorts': [], 'points': []}
        for key, by_id in sorted(cohorts.items()):
            if not by_id:
                continue
            records = sorted(by_id.values(), key=lambda r: int(r['receive_raw_ns']))
            assert len({r['id'] for r in records}) == len(records)
            first = records[0]
            raw_anchor = max(0, int(first['send_raw_ns'])-SECOND)
            first_midpoint = (int(first['send_raw_ns'])+int(first['receive_raw_ns']))//2
            utc_anchor = (int(first['server_receive_ns'])+int(first['server_send_ns']))//2 - (first_midpoint-raw_anchor)
            def translated(value):
                return EPOCH+int(value)-utc_anchor
            events = []
            probes = {}
            for record_index, record in enumerate(records):
                send, receive = int(record['send_raw_ns']), int(record['receive_raw_ns'])
                midpoint = (send+receive)//2
                assert send < midpoint < receive
                t = midpoint-raw_anchor
                probes[t] = {'id': record['id'], 'raw_ns': midpoint,
                             'previous': records[record_index-1] if record_index else None,
                             'server_utc_ns': (translated(record['server_receive_ns'])+
                                               translated(record['server_send_ns']))//2-EPOCH}
                empty = (0, 0, 1, 0, 0, 0, 0, -20, 0)
                events.append((send-raw_anchor, 1, *empty))
                events.append((t, 0, *empty))
                events.append((receive-raw_anchor, 2, 0, translated(record['server_send_ns']),
                               record['stratum'], translated(record['server_receive_ns']),
                               translated(record['server_reference_ns']), record['root_delay_16_16'],
                               record['root_dispersion_16_16'], record['precision'], record['leap']))
            assert all(len(event) == 11 for event in events)
            events.sort()
            payload = ''.join(f'{t} {t} {action} '+ ' '.join(map(str, fields))+'\n'
                              for t, action, *fields in events)
            outputs = {}
            errors = {}
            for name, executable, phase_only in [
                ('microchrony_phase', args.microchrony, True),
                ('microchrony_rate', args.microchrony, False),
                ('chrony49_rate', args.reference, False),
            ]:
                rows, stderr = run(executable.resolve(), payload, phase_only)
                assert [r[0] for r in rows] == sorted(probes)
                outputs[name] = rows
                errors[name] = stderr
            names = list(outputs)
            points = []
            for index, t in enumerate(sorted(probes)):
                probe = probes[t]
                if not begin <= probe['raw_ns'] <= end:
                    continue
                previous = probe['previous']
                if previous is None:
                    continue
                previous_raw = (int(previous['send_raw_ns'])+int(previous['receive_raw_ns']))//2
                previous_utc = (translated(previous['server_receive_ns'])+
                                translated(previous['server_send_ns']))//2-EPOCH
                age = probe['raw_ns']-previous_raw
                assert int(previous['receive_raw_ns']) < probe['raw_ns']
                path = max(1, int(previous['receive_raw_ns'])-int(previous['send_raw_ns'])-
                           (int(previous['server_send_ns'])-int(previous['server_receive_ns'])))
                wire = previous['root_delay_16_16']
                wire = wire if wire < 2**31 else wire-2**32
                baseline_error = (path/2 + max(0, wire)*SECOND/131072 +
                                  previous['root_dispersion_16_16']*SECOND/65536 + 2000 + age*.0001)
                if age > 90*SECOND or baseline_error > 500_000_000:
                    continue
                if not all(outputs[name][index][7] >= 0 and
                           outputs[name][index][9] <= 500_000_000 and
                           outputs[name][index][10] <= 90*SECOND for name in names):
                    continue
                point_errors = {name: outputs[name][index][2]-probe['server_utc_ns'] for name in names}
                point_errors['offset_only'] = previous_utc+age-probe['server_utc_ns']
                points.append({'id': probe['id'], 'slot': key[1], 'endpoint': key[2],
                               'epoch': key[3], 'raw_ns': probe['raw_ns'],
                               'elapsed_seconds': (probe['raw_ns']-begin)/SECOND,
                               'errors_ns': point_errors,
                               'pure_rates_ppm': {name: outputs[name][index][3] for name in names}})
            board_report['cohorts'].append({'slot': key[1], 'endpoint': key[2], 'epoch': key[3],
                                           'originals': len(records),
                                           'input_sha256': hashlib.sha256(payload.encode()).hexdigest(),
                                           'common_probes': len(points), 'stderr': errors})
            board_report['points'].extend(points)
        points = board_report['points']
        assert points, 'No common probes pass the unchanged timing gates'
        board_report['metrics'] = {name: metrics(p['errors_ns'][name] for p in points)
                                   for name in ['offset_only', *names]}
        report['boards'][board] = board_report
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({b: {k: v for k, v in data.items() if k != 'points'}
                      for b, data in report['boards'].items()}, indent=2))


if __name__ == '__main__':
    main()
