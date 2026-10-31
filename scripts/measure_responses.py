#!/usr/bin/env python3
"""Compare response allocation/host-time metrics from identical baseline/candidate probes.

Build both core libraries first. The probe sources from the candidate deliberately
compile against either source tree; __has_include selects that tree's actual API.
No hardware is accessed. Raw runs, digests, medians and deltas remain inspectable.
"""
import argparse
import json
import hashlib
import platform
from pathlib import Path
import statistics
import subprocess


def run(command):
    return subprocess.check_output([str(arg) for arg in command], text=True)


def parse(text):
    rows = {}
    label = None
    for line in text.splitlines():
        if line.startswith('digest='):
            rows[label]['digest'] = int(line.split('=')[1])
        else:
            label, *fields = line.split()
            rows[label] = {key: int(value) for key, value in (field.split('=') for field in fields)}
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-source', type=Path, required=True)
    parser.add_argument('--baseline-revision', required=True)
    parser.add_argument('--baseline-build', type=Path, required=True)
    parser.add_argument('--candidate-build', type=Path, required=True)
    parser.add_argument('--mbedtls-source', type=Path, required=True)
    parser.add_argument('--compiler', default='c++')
    parser.add_argument('--runs', type=int, default=21)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.runs < 3:
        parser.error('--runs must be at least 3')
    samples = {}
    for name, source, build in [('before', args.baseline_source, args.baseline_build),
                                ('after', root, args.candidate_build)]:
        core = [build / 'libwsprrypico_core.a', build / 'src/microchrony/libmicrochrony.a']
        common = [args.compiler, '-std=c++20', '-g', '-DWSPRRY_PICO_RF_SAMPLE_RATE_HZ=138000000',
                  '-I', source / 'tests', '-I', source / 'src', '-I', source / 'src/microchrony',
                  '-I', root / 'tests']
        plain = build / 'response_metrics_comparison'
        run(common + [root / 'tests/response_metrics.cpp', *core, '-o', plain])
        crypto = build / 'response_crypto_metrics_comparison'
        run(common + ['-DWSPRRY_PICO_CONSUMER_RADIO_CRYPTO_TEST=1',
                      '-DMBEDTLS_CONFIG_FILE="' + str(source / 'src/network/pico/mbedtls_config.h') + '"',
                      '-I', args.mbedtls_source / 'include', root / 'tests/response_crypto_metrics.cpp',
                      source / 'src/network/pico/consumer_radio_crypto.cpp',
                      source / 'src/network/pico/psa_lifetime.cpp', *core,
                      args.candidate_build / 'mbedtls/libmbedcrypto.a', '-o', crypto])
        # Warm process/library paths once; retain every subsequent complete run.
        vector = root / 'engineering/protocol/Consumer-Radio-v1-vectors.json'
        run([plain]); run([crypto, vector])
        samples[name] = [parse(run([plain]) + run([crypto, vector])) for _ in range(args.runs)]
    summary = {}
    for label in samples['before'][0]:
        summary[label] = {}
        for side in ('before', 'after'):
            rows = [sample[label] for sample in samples[side]]
            summary[label][side] = {key: statistics.median(row[key] for row in rows)
                                    for key in rows[0]}
            for key in ('bytes', 'digest'):
                if key in rows[0]:
                    assert len({row[key] for row in rows}) == 1, (label, side, key)
        before, after = summary[label]['before'], summary[label]['after']
        assert before['bytes'] == after['bytes'], (label, 'wire length changed')
        if 'digest' in before:
            assert before['digest'] == after['digest'], (label, 'wire bytes changed')
        summary[label]['delta'] = {key: after[key] - before[key]
                                    for key in before if key not in ('digest', 'bytes')}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    inputs = sorted(set(run(['git', '-C', root, 'ls-files', '--cached', '--others',
                              '--exclude-standard', 'src', 'tests', 'cmake', 'scripts',
                              'engineering/protocol', 'CMakeLists.txt']).splitlines()))
    digest = hashlib.sha256()
    for relative in inputs:
        path = root / relative
        if path.is_file():
            digest.update(relative.encode() + b'\0' + path.read_bytes() + b'\0')
    provenance = {'baseline_revision': args.baseline_revision,
                  'candidate_base_revision': run(['git', '-C', root, 'rev-parse', 'HEAD']).strip(),
                  'candidate_inputs_sha256': digest.hexdigest(),
                  'compiler': run([args.compiler, '--version']).splitlines()[0],
                  'platform': platform.platform(),
                  'mbedtls_revision': run(['git', '-C', args.mbedtls_source, 'rev-parse', 'HEAD']).strip()}
    args.output.write_text(json.dumps({'runs': args.runs, 'provenance': provenance,
        'scope': 'Host requested allocation bytes; allocator overhead, networking and target latency excluded',
        'samples': samples, 'summary': summary}, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
