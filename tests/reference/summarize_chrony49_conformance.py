#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Extract bounded, sanitized results from the private conformance suite.

No captures, packet prefixes, IP addresses, credentials or row-level histories
are published. Original private artifacts remain hash-bound for local audit.
This summarizer does not confer test success or physical qualification.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def summarize(root):
    hashes = {}
    repo = Path(__file__).resolve().parents[2]

    def load(name):
        data = (root/name).read_bytes()
        hashes[name] = hashlib.sha256(data).hexdigest()
        return json.loads(data)

    loop = load('loop.json')
    packets = load('packets-final.json')
    histories = load('histories-final.json')
    adaptation = load('adaptation.json')
    frequency = load('frequency.json')
    ablations = load('ablations-final/results.json')
    benefit = load('rate-benefit.json')
    cold = load('pooled-cold-final.json')
    rtc = load('pooled-rtc-final.json')
    validation = load('loop-validation.json')
    for kind, expected in [('packet', packets['reference_sha256']),
                           ('loop', loop['reference_sha256']),
                           ('stats', histories['reference_sha256'])]:
        binary = root/('chrony49-'+kind)
        binding = load('chrony49-'+kind+'.inputs.json')
        actual = hashlib.sha256(binary.read_bytes()).hexdigest()
        if actual != expected or actual != binding['output_sha256']:
            raise ValueError('Reference binary binding changed: '+kind)
        driver = repo/'tests/reference'/('chrony49_'+('sourcestats' if kind == 'stats' else kind)+'.c')
        if hashlib.sha256(driver.read_bytes()).hexdigest() != binding['harness_sha256']:
            raise ValueError('Reference adapter changed after its build: '+kind)
    engine = root/'host/microchrony_loop'
    if hashlib.sha256(engine.read_bytes()).hexdigest() != loop['microchrony_sha256']:
        raise ValueError('Engine executable changed after the comparison')
    if not (packets['engine_sha256'] == histories['engine_sha256'] ==
            benefit['binaries_sha256']['microchrony'] == loop['microchrony_sha256']):
        raise ValueError('Results do not share the same engine executable')
    curves = {}
    for name in ['internet_weak_queue', 'internet_forward_queue', 'internet_reverse_queue']:
        case = loop['cases'][name]
        first = max(v['first_sync_s'] for v in case['summary'].values())
        bins = {}
        for who, key in [('microchrony', 'microchrony_rows'), ('chrony49', 'reference_rows')]:
            for row in case[key]:
                t = row[0]/1e9
                if row[1] != 0 or t < first or t > 14400:
                    continue
                block = min(47, int(t//300))
                bins.setdefault(block, {}).setdefault(who, []).append((row[2]-row[0])/1e6)
        curves[name] = [{'end_minute': (block+1)*5,
            **{who: {'samples': len(errors),
                     'utc_rms_ms': math.sqrt(sum(x*x for x in errors)/len(errors))}
               for who, errors in values.items()}}
            for block, values in sorted(bins.items())]
    return {
        'schema': 'microchrony-conformance-summary/1',
        'upstream': {'version': '4.9', 'license': 'GPL-2.0-only',
                     'firmware_linkage': False,
                     'official_archive': 'https://chrony-project.org/releases/chrony-4.9.tar.gz',
                     'archive_sha256': '4924c6f530105bcd5b9e9e33c48a2ae1bfd889222c8480bc41601110efc864d0'},
        'complete_daemon_equivalence_demonstrated': False,
        'quality_thresholds_relaxed': False,
        'source_sha256': {name: hashlib.sha256((repo/name).read_bytes()).hexdigest()
            for name in ['src/microchrony/microchrony.cpp', 'src/microchrony/microchrony.hpp',
                'src/time/ntp_client.cpp', 'src/time/ntp_client.hpp',
                'tests/reference/microchrony_loop.cpp', 'tests/reference/chrony49_loop.c',
                'tests/reference/chrony49_sourcestats.c', 'tests/reference/chrony49_packet.c']},
        'packet_admission': {
            'scope': packets['scope'],
            'reference_sha256': packets['reference_sha256'],
            'engine_sha256': packets['engine_sha256'],
            'deliberate_stricter_profile_differences': packets['deliberate_stricter_profile_differences'],
            'cases': {n: {k: v[k] for k in ['input_sha256', 'offered_wire_sha256',
                'offered', 'chrony_accepted', 'microchrony_accepted', 'differences']}
                      for n, v in packets['cases'].items()}},
        'fixed_coordinate_histories': {
            'scope': 'Instantaneous common raw midpoint, peer delay and dispersion; no control loop or packet admission.',
            'sources': {n: {k: value for k, value in v.items()
                           if k not in ['reference_rows', 'microchrony_rows']}
                        for n, v in histories['sources'].items()}},
        'known_truth_loops': {
            'scope': loop['scope'], 'reference_sha256': loop['reference_sha256'],
            'engine_sha256': loop['microchrony_sha256'],
            'cases': {n: {k: v[k] for k in ['plant', 'input_sha256', 'summary']}
                      for n, v in loop['cases'].items()},
            'five_minute_rms': curves,
            'validation': validation},
        'rate_benefit': {
            'scope': 'Zero initial learned frequency; same physical inputs; phase-only control suppresses learning in offline adapters only. Positive RMS gain means learned frequency helps.',
            'cases': {n: {'plant': v['plant'], 'input_sha256': v['input_sha256'],
                'controllers': {who: {k: x for k, x in d.items()
                    if k not in ['full_rows', 'phase_only_rows']}
                    for who, d in v['controllers'].items()}}
                for n, v in benefit['cases'].items()}},
        'ablations': {'baseline_revision': ablations['baseline_revision'],
            'variants': {n: {'source_sha256': v['source_sha256'],
                'binary_sha256': v['binary_sha256'],
                'cases': {case: {k: x for k, x in d.items() if k != 'rows'}
                          for case, d in v['cases'].items()}}
                for n, v in ablations['variants'].items()}},
        'captured_subset': {
            'limits': cold['limits'],
            'cold_acquisition': cold['acquisition'],
            'matched_rtc_acquisition': rtc['acquisition'],
            'boards': {b: {'originals': v['originals'], 'visibility': v['visibility'],
                'input_sha256': v['input_sha256'], 'common_qualified_pulses': v['common_qualified_pulses'],
                'cold_metrics': v['metrics'], 'matched_rtc_metrics': rtc['boards'][b]['metrics']}
                for b, v in cold['boards'].items()}},
        'additional_checks': {
            'adaptive_histories': len(adaptation['histories']),
            'frequency_cases': len(frequency['cases']),
            'max_frequency_difference_ppm': frequency['max_rate_difference_ppm'],
            'max_skew_difference_ppm': frequency['max_skew_difference_ppm']},
        'private_artifact_sha256': hashes,
        'summarizer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('private_results', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    args.output.write_text(json.dumps(summarize(args.private_results), indent=2)+'\n')
