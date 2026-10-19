#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Identical captured packet cohorts at the external NCR/Engine boundary.

The common UTC origin and correlation nonce are translated by original test
adapters. Both implementations receive the resulting identical wire bytes.
This is a cold, fixed-clock admission comparison, not restored live boot state.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from rf_analysis.ntp_packets import PacketHistory
from compare_chrony49_packets import EPOCH, SECOND, stamp


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode(value):
    n = int.from_bytes(value, 'big')
    return ((n >> 32)-2208988800)*SECOND + (n & 0xffffffff)*SECOND//2**32


def compare(root, manifest_name, expected_hash, reference, before, after):
    root = root.resolve(strict=True)
    manifest_path = (root/manifest_name).resolve(strict=True)
    assert manifest_path.is_relative_to(root) and sha(manifest_path) == expected_hash
    manifest = json.loads(manifest_path.read_text())['files']
    hashes = {}

    def load(name):
        path = root/name
        assert sha(path) == manifest[name]['sha256'], name
        hashes[name] = sha(path)
        return path.read_text()

    identity = json.loads(load('expected.json'))
    states = {}
    for board in 'AB':
        info = identity[board]['info']
        states[board] = PacketHistory(info['device_id'], info['status']['boot_id'],
                                     info['firmware'], info['revision'])
    cohorts = {}
    for line in load('packet-pages.jsonl').splitlines():
        row = json.loads(line)
        state = states[row['board']]
        offered = state.ingest(row['receipt']['response'], allow_initial_gap=not state.pages)
        for record in offered:
            key = row['board'], record['slot'], record['endpoint'], record['clock_epoch']
            cohorts.setdefault(key, []).append(record)
    result = {'schema': 'chrony49-captured-packet-comparison/1',
              'manifest_file': manifest_name, 'manifest_sha256': expected_hash,
              'script_sha256': sha(Path(__file__)), 'inputs_sha256': hashes,
              'binaries_sha256': {name: sha(path) for name, path in
                                 [('chrony49', reference), ('before', before), ('after', after)]},
              'limits': ['Cold cohort starts omit earlier boot/admission history.',
                         'Server/reference epochs share a translated origin; correlation nonce is regenerated.',
                         'Original body quality fields, raw request/reply intervals and correlation failures are retained.',
                         'Clock output is fixed; autonomous polling and live combined control are excluded.'],
              'cohorts': {}}
    for key, records in sorted(cohorts.items()):
        # This report's compact board/slot key requires one immutable cohort.
        # Never silently replace a prior endpoint or clock epoch.
        cohort_name = key[0]+str(key[1])
        assert cohort_name not in result['cohorts'], 'Multiple source cohorts for '+cohort_name
        assert all(r['length'] == 48 and not r['truncated'] for r in records)
        first = next(r for r in records if r['accepted'])
        raw_anchor = min(int(r['request_raw_ns']) for r in records)-SECOND
        packet = bytes.fromhex(first['prefix_hex'])
        raw_mid = (int(first['request_raw_ns'])+int(first['receive_raw_ns']))//2
        utc_anchor = (decode(packet[32:40])+decode(packet[40:48]))//2-(raw_mid-raw_anchor)
        rows = []
        for record in records:
            packet = bytearray.fromhex(record['prefix_hex'])
            mask = int.from_bytes(packet[24:32], 'big') ^ int(record['request_token'])
            for offset in (16, 32, 40):
                if any(packet[offset:offset+8]):
                    packet[offset:offset+8] = stamp(EPOCH+decode(packet[offset:offset+8])-utc_anchor).to_bytes(8, 'big')
            rows.append(f"{int(record['request_raw_ns'])-raw_anchor} {int(record['receive_raw_ns'])-raw_anchor} {mask:x} {packet.hex()}\n")
        payload = ''.join(rows)
        ref = subprocess.run([str(reference.resolve())], input=payload, text=True,
                             capture_output=True, timeout=30, check=True)
        repeated = subprocess.run([str(reference.resolve())], input=payload, text=True,
                                  capture_output=True, timeout=30, check=True)
        assert ref.stdout == repeated.stdout
        expected = [line.split() for line in ref.stdout.splitlines()]
        assert len(expected) == len(records)
        outputs = {}
        for name, binary in [('before', before), ('after', after)]:
            mu = subprocess.run([str(binary.resolve()), 'packet'], input=ref.stdout,
                                text=True, capture_output=True, timeout=30, check=True)
            actual = [line.split() for line in mu.stdout.splitlines()]
            assert len(actual) == len(expected)
            outputs[name] = {'accepted': sum(int(r[1]) for r in actual),
                             'rows': actual,
                             'differences_from_reference': [records[i]['id'] for i, (r, m) in
                                  enumerate(zip(expected, actual)) if int(r[7]) != int(m[1])],
                             'differences_from_live': [records[i]['id'] for i, m in
                                  enumerate(actual) if bool(int(m[1])) != records[i]['accepted']]}
        result['cohorts'][cohort_name] = {
            'endpoint': key[2], 'epoch': key[3], 'offered': len(records),
            'live_accepted': sum(r['accepted'] for r in records),
            'chrony49_accepted': sum(int(r[7]) for r in expected),
            'input_sha256': hashlib.sha256(payload.encode()).hexdigest(),
            'offered_wire_sha256': hashlib.sha256(ref.stdout.encode()).hexdigest(),
            'reference_rows': expected, **outputs}
    assert len(result['cohorts']) == len(cohorts)
    assert sum(c['offered'] for c in result['cohorts'].values()) == sum(map(len, cohorts.values()))
    return result


if __name__ == '__main__':
    if sys.flags.optimize:
        raise RuntimeError('Run without -O')
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('evidence', 'reference', 'before', 'after', 'output'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--manifest', default='retrieval-manifest.json')
    parser.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    result = compare(args.evidence, args.manifest, args.manifest_sha256,
                     args.reference, args.before, args.after)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({name: {k: v for k, v in data.items() if k not in
                            ('reference_rows', 'before', 'after')} |
                     {'before_differences': data['before']['differences_from_reference'],
                      'after_differences': data['after']['differences_from_reference']}
                     for name, data in result['cohorts'].items()}, indent=2))
