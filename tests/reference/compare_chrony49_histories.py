#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare fixed raw-coordinate SST histories from a verified captured cohort.

The companion pooled report supplies identity, baseline visibility and hashes.
This normalizes each measurement to an instantaneous server midpoint and peer
RTT, with common precision/dispersion. No clock discipline or packet admission
is exercised here. Missing pre-capture history remains missing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SECOND = 10**9
EPOCH = 1_800_000_000 * SECOND


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(root, cohort, reference, engine):
    manifest = root / 'final-manifest.json'
    verified = json.loads(cohort.read_text())
    assert sha(manifest) == verified['manifest_sha256']
    for name, digest in verified['inputs_sha256'].items():
        path = (root / name).resolve(strict=True)
        assert path.is_relative_to(root.resolve()) and sha(path) == digest
    result = {'schema': 'microchrony-fixed-coordinate-histories/1',
              'cohort_sha256': sha(cohort), 'manifest_sha256': sha(manifest),
              'reference_sha256': sha(reference), 'engine_sha256': sha(engine),
              'script_sha256': sha(Path(__file__)), 'sources': {}}
    for board in 'AB':
        for slot in range(4):
            records = {}
            for name in verified['inputs_sha256']:
                if not Path(name).name.startswith(board + '-history-'):
                    continue
                response = json.loads((root / name).read_text())['response']
                if response.get('ok') and response['slot'] == slot:
                    for r in response['records']:
                        if r['id'] in records:
                            assert records[r['id']] == r
                        records[r['id']] = r
            records = sorted(records.values(), key=lambda r: int(r['receive_raw_ns']))
            assert records
            anchor = int(records[0]['send_raw_ns']) - SECOND
            epoch = (int(records[0]['server_receive_ns']) + int(records[0]['server_send_ns'])) // 2
            epoch -= (int(records[0]['send_raw_ns']) + int(records[0]['receive_raw_ns'])) // 2 - anchor
            rows = []
            for r in records:
                midpoint = (int(r['send_raw_ns']) + int(r['receive_raw_ns'])) // 2 - anchor
                delay = (int(r['receive_raw_ns']) - int(r['send_raw_ns']) -
                         int(r['server_send_ns']) + int(r['server_receive_ns']))
                utc = EPOCH + (int(r['server_receive_ns']) + int(r['server_send_ns'])) // 2 - epoch
                assert delay > 0
                rows.append(f'{midpoint-delay//2} {midpoint+(delay-delay//2)} {utc}\n')
            payload = ''.join(rows)
            outputs = {}
            for name, binary in [('chrony49', reference), ('microchrony', engine)]:
                run = subprocess.run([str(binary.resolve()), 'raw'], input=payload,
                                     text=True, capture_output=True, timeout=30, check=True)
                outputs[name] = [list(map(float, l.split())) for l in run.stdout.splitlines()]
                assert len(outputs[name]) == len(records)
            ref, mu = outputs['chrony49'], outputs['microchrony']
            different_counts = [i+1 for i, (a,b) in enumerate(zip(ref,mu)) if a[1] != b[1]]
            different_coefficients = [i+1 for i,(a,b) in enumerate(zip(ref,mu))
                                      if abs(a[10]+b[8]) > 1e-4]
            frequency_delta = max(abs(a[3]-b[3])*1e9 for a,b in zip(ref[2:],mu[2:]))
            assert not different_counts, (board, slot, different_counts)
            assert not different_coefficients, (board, slot, different_coefficients)
            assert frequency_delta < .001, (board, slot, frequency_delta)
            result['sources'][board+str(slot)] = dict(points=len(records),
                input_sha256=hashlib.sha256(payload.encode()).hexdigest(),
                count_divergences=different_counts, coefficient_divergences=different_coefficients,
                max_frequency_difference_ppb=frequency_delta,
                final_reference_samples=ref[-1][1], final_microchrony_samples=mu[-1][1],
                final_reference_rate_ppm=-ref[-1][3]*1e6,
                final_microchrony_rate_ppm=-mu[-1][3]*1e6,
                reference_rows=ref, microchrony_rows=mu)
            print(board, slot, 'count differences', different_counts,
                  'coefficient differences', different_coefficients,
                  'max slope difference ppb', frequency_delta, flush=True)
    return result


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O')
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('evidence', 'cohort', 'reference', 'engine', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(compare(args.evidence, args.cohort, args.reference,
                                              args.engine), indent=2)+'\n')
