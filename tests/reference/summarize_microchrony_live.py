#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Produce a derived engineering record from the completed finite A/B evidence."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from compare_chrony49_captured_loop import metrics

if sys.flags.optimize:
    raise RuntimeError('Validation requires assertions; run without -O')
evidence, analysis, output = map(Path, sys.argv[1:])


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ct(wall_ns):
    return datetime.fromtimestamp(wall_ns/1e9, ZoneInfo('America/Chicago')).isoformat(timespec='seconds')


start = load(evidence/'observer-start.json')
finish = load(evidence/'observer-complete.json')
guard = load(evidence/'guard-complete.json')
restored = load(evidence/'post-run-verification.json')
verified = load(analysis/'evidence-verification.json')
assert finish['success'] and guard['observer_exited'] and not guard['terminated_observer']
assert finish['elapsed_seconds'] <= start['duration_seconds']
assert all(sum(phases.values()) <= start['query_budget_per_board'] for phases in finish['queries'].values())
assert verified['all_remote_hashes_match'] and verified['bytes'] <= start['evidence_cap_bytes']
assert finish['saved_settings_restored'] and finish['manual_ppm_preserved']

report = {
    'schema': 'microchrony-live-comparison/1',
    'summary_script_sha256': sha(__file__),
    'experiment': {'start_ct': start['start_ct'],
                   'crossover_ct': load(evidence/'crossover-complete.json')['ct'],
                   'finish_ct': finish['ct'], 'hard_finish_ct': start['finish_no_later_than_ct'],
                   'elapsed_seconds': finish['elapsed_seconds'],
                   'query_budget_per_board': start['query_budget_per_board'],
                   'queries_by_boot_and_phase': finish['queries'],
                   'evidence_cap_bytes': start['evidence_cap_bytes'],
                   'guard_reason': guard['reason'], 'no_RF_jobs': True},
    'firmware': {'version': start['firmware'], 'source_revision': start['revision'],
                 'normal_uf2_sha256': start['image_sha256'],
                 'engine': 'pio-dma-gp2', 'nominal_system_clock_hz': 138000000},
    'evidence': verified,
    'restored': restored,
    'independent_UTC_or_RF_truth': False,
    'conditions': {},
}
for phase in ['phase1', 'phase2']:
    original = load(analysis/(phase+'-final-analysis.json'))
    replay = load(analysis/(phase+'-final-chrony49-loop.json'))
    phase_receipt = load(evidence/(phase+'-complete.json'))
    assert phase_receipt['accepted_originals_since_baseline_complete']
    for board in ['A', 'B']:
        board_analysis = original['boards'][board]
        visibility = board_analysis['accepted_original_visibility']
        binding = board_analysis['verified_application_clock']
        assert visibility['complete_since_baseline']
        assert binding['source_and_application_binding'] and binding['within_3us']
        wrappers = [load(p) for p in sorted((evidence/phase).glob(board+'-observe-*.json'))]
        wrappers.sort(key=lambda p: p['host_monotonic_ns'])
        infos = [p['response'] for p in wrappers]
        for info in infos:
            assert info['firmware'] == start['firmware'] and info['revision'] == start['revision']
            assert info['system_clock_hz'] == 138000000 and info['status']['engine'] == 'pio-dma-gp2'
            assert info['device_id'] == restored['boards'][board]['device_id']
            assert info['status']['owner_id'] is None and not info['status']['output_active']
            assert not info['status']['enabled'] and info['status']['job_id'] is None
        last = infos[-1]
        learning = last['network']['ntp_learning']
        records = []
        qualified = []
        exceptions = []
        for wrapper, info in zip(wrappers, infos):
            status = info['status']
            model = info['network']['ntp_learning']
            ready = (status['clock_state'] == 'synchronized' and
                     int(status['sync_age_ns']) <= 90*10**9 and
                     int(status['uncertainty_ns']) <= 500_000_000)
            elapsed = (wrapper['host_monotonic_ns']/1e9-start['start_monotonic'])/60
            is_qualified = model['rf_candidate']['qualified']
            records.append({'elapsed_minutes': elapsed,
                            'frequency_ppm': model['utc_frequency_ppb']/1000 if model['synchronized'] else None,
                            'skew_ppm': model['skew_ppb']/1000,
                            'launch_timing_ready': ready,
                            'statistical_candidate': is_qualified})
            if is_qualified:
                qualified.append({'ct': ct(wrapper['host_wall_ns']), 'elapsed_minutes': elapsed})
            if not ready:
                exceptions.append({'ct': ct(wrapper['host_wall_ns']), 'clock_state': status['clock_state'],
                                   'age_ns': status['sync_age_ns'], 'clock_error_ns': status['uncertainty_ns'],
                                   'peer_reasons': [p['reason'] for p in info['network']['ntp_pool']['peers']]})
            for value in info['network'].get('memory', {}).values():
                if isinstance(value, dict):
                    assert not int(value.get('errors', 0)), 'network allocator fault'
        bindings = {k: v for k, v in binding.items() if k != 'pairs'}
        comparison = replay['boards'][board]
        assert all(not message for cohort in comparison['cohorts'] for message in cohort['stderr'].values())
        report['conditions'][phase+'_'+board] = {
            'board': board, 'phase': phase, 'source': last['network']['ntp_server'],
            'boot_id': last['status']['boot_id'],
            'capture_first_ct': ct(wrappers[0]['host_wall_ns']),
            'capture_last_ct': ct(wrappers[-1]['host_wall_ns']),
            'info_reads': len(infos), 'launch_timing_ready_reads': sum(r['launch_timing_ready'] for r in records),
            'timing_exceptions': exceptions,
            'first_observed_statistical_candidate': qualified[0] if qualified else None,
            'statistical_candidate_reads': len(qualified),
            'final_frequency_ppm': learning['utc_frequency_ppb']/1000,
            'final_skew_ppm': learning['skew_ppb']/1000,
            'final_clock_error_ms': int(last['status']['uncertainty_ns'])/1e6,
            'final_phase_settled': learning['phase_settled'], 'final_rate_settled': learning['rate_settled'],
            'whole_boot_queries': phase_receipt['whole_boot_query_totals'][board],
            'visibility': visibility, 'application_clock': bindings,
            'cohort_replay': {'common_probe_gates': replay['common_probe_gates'],
                              'metrics': comparison['metrics'],
                              'windows': {f'{lo}-{hi}min': {
                                  model: metrics(p['errors_ns'][model] for p in comparison['points']
                                                 if lo*60 <= p['elapsed_seconds'] < hi*60)
                                  for model in comparison['metrics']}
                                  for lo, hi in ((0,15), (15,30), (30,60))},
                              'cohorts': [{k: c[k] for k in ('slot','epoch','originals','input_sha256','common_probes')}
                                          for c in comparison['cohorts']]},
            'resource': {'core0_stack_max_bytes': max(i['core0_stack_used_bytes'] for i in infos),
                         'core1_stack_max_bytes': max(i['core1_stack_used_bytes'] for i in infos),
                         'heap_min_bytes': min(i['heap_available_bytes'] for i in infos),
                         'ntp_processing_max_us': max(p['max_process_us'] for i in infos for p in i['network']['ntp_pool']['peers'])},
            'analysis_sha256': sha(analysis/(phase+'-final-analysis.json')),
            'replay_sha256': sha(analysis/(phase+'-final-chrony49-loop.json')),
            'reference_binary_sha256': replay['reference_sha256'],
            'microchrony_binary_sha256': replay['microchrony_sha256'],
            'curve': records,
        }
output.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({name: {k: v for k, v in data.items() if k not in ('curve','timing_exceptions')}
                  for name, data in report['conditions'].items()}, indent=2))
