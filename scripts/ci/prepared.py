#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare a verified firmware publication packet and publish it in a later job.

Preparation and validation write private local files only. Publication uses the
original canonical run's immutable archives and never invokes a firmware build.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bundle
import download
import publish
from check_control_policy import check_files as check_control_policy

SCHEMA = 'wsprrypico-prepared-publication/1'
WORKFLOW = 'WsprryPi/WsprryPico/.github/workflows/publish-prepared.yml@refs/heads/devel'
MAX_PLAN = 32768


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def public_files(destination):
    paths = list((destination / 'deployment').iterdir())
    paths += [destination / name for name in ('deployment.zip', 'audit.zip', 'ci-publication.json')]
    bundle.require(len(paths) == 9 and len({p.name for p in paths}) == 9 and
                   all(p.is_file() and not p.is_symlink() for p in paths),
                   'Incomplete prepared public inventory')
    return {p.name: p for p in paths}


def inventory(destination):
    return {name: {'bytes': p.stat().st_size, 'sha256': bundle.sha(p)}
            for name, p in sorted(public_files(destination).items())}


def write_proof(receipt, destination):
    value = dict(receipt, schema='wsprrypico-ci-publication/1', repository=download.REPOSITORY,
                 tag='v' + receipt['version'],
                 manifest_sha256=bundle.sha(destination / 'deployment/release-manifest.json'))
    path = destination / 'ci-publication.json'
    data = encode(value)
    bundle.require(not path.exists() or (not path.is_symlink() and path.read_bytes() == data),
                   'Existing preparation proof differs')
    if not path.exists():
        path.write_bytes(data)


def validate_plan(plan):
    bundle.require(isinstance(plan, dict) and set(plan) == {
        'schema', 'receipt', 'files', 'packet_sha256', 'plan_sha256'}, 'Invalid prepared plan shape')
    bundle.require(plan['schema'] == SCHEMA and
                   plan['plan_sha256'] == digest({k: v for k, v in plan.items() if k != 'plan_sha256'}),
                   'Prepared plan changed')
    receipt = plan['receipt']
    bundle.require(isinstance(receipt, dict) and receipt.get('verified') is True and
                   receipt.get('verification') == 'accepted-verify-job-and-payload',
                   'Canonical verification receipt required')
    bundle.require(receipt.get('branch') in ('devel', 'main', 'release') and
                   type(receipt.get('run_id')) is int and receipt['run_id'] > 0 and
                   type(receipt.get('attempt')) is int and receipt['attempt'] > 0 and
                   isinstance(receipt.get('source'), str) and
                   re.fullmatch('[0-9a-f]{40}', receipt['source']) and
                   bundle.version_kind(receipt.get('version', '')) in ('ci', 'prerelease', 'stable'),
                   'Invalid prepared source/version/run')
    records = plan['files']
    bundle.require(isinstance(records, dict) and len(records) == 9 and
                   plan['packet_sha256'] == digest(records), 'Prepared packet identity differs')
    for name, value in records.items():
        bundle.require(isinstance(name, str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9._+-]*', name) and
                       isinstance(value, dict) and set(value) == {'bytes', 'sha256'} and
                       type(value['bytes']) is int and 0 < value['bytes'] <= 512 * 1024 * 1024 and
                       isinstance(value['sha256'], str) and re.fullmatch('[0-9a-f]{64}', value['sha256']),
                       'Invalid prepared artifact record')
    return plan


def prepare(args):
    bundle.require(bundle.version_kind(args.version) in ('ci', 'prerelease', 'stable'),
                   'Only canonical publishable versions can be prepared')
    receipt = download.retrieve(args, prepared=True)
    if args.branch == 'release':
        receipt['make_latest'] = False
    write_proof(receipt, args.destination)
    records = inventory(args.destination)
    plan = {'schema': SCHEMA, 'receipt': receipt, 'files': records,
            'packet_sha256': digest(records)}
    plan['plan_sha256'] = digest(plan)
    validate_plan(plan)
    (args.destination / 'prepared-publication.json').write_bytes(encode(plan))
    return plan


def verify(plan, destination):
    validate_plan(plan)
    r = plan['receipt']
    args = SimpleNamespace(branch=r['branch'], run=r['run_id'], attempt=r['attempt'],
                           source=r['source'], version=r['version'], destination=destination)
    current = download.retrieve(args, prepared=True)
    if r['branch'] == 'release':
        current['make_latest'] = False
    bundle.require(current == r, 'Canonical preparation inputs changed; return to preparation')
    write_proof(r, destination)
    bundle.require(inventory(destination) == plan['files'],
                   'Retained and canonical artifact bytes differ; return to preparation')
    return {'status': 'PASS', 'schema': SCHEMA, 'packet_sha256': plan['packet_sha256'],
            'source': r['source'], 'version': r['version'], 'publication_performed': False}


def require_publisher(expected_source):
    bundle.require(re.fullmatch('[0-9a-f]{40}', expected_source or '') and
                   re.fullmatch('[1-9][0-9]*', os.environ.get('GITHUB_RUN_ID', '')) and
                   re.fullmatch('[1-9][0-9]*', os.environ.get('GITHUB_RUN_ATTEMPT', '')) and
                   os.environ.get('CI_PUBLISH') == 'true' and
                   os.environ.get('GITHUB_ACTIONS') == 'true' and
                   os.environ.get('GITHUB_JOB') == 'publish' and
                   os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch' and
                   os.environ.get('GITHUB_REPOSITORY') == download.REPOSITORY and
                   os.environ.get('GITHUB_REF') == 'refs/heads/devel' and
                   os.environ.get('GITHUB_WORKFLOW_REF') == WORKFLOW and
                   os.environ.get('GITHUB_SHA') == expected_source and
                   bundle.capture('git', '-C', bundle.ROOT, 'rev-parse', 'HEAD') == expected_source,
                   'Prepared publication requires the explicit trusted devel publisher job')


def publish_prepared(plan, destination, confirmed, expected_publisher_source):
    validate_plan(plan)
    bundle.require(confirmed == plan['packet_sha256'], 'Prepared publication digest not confirmed')
    require_publisher(expected_publisher_source)
    # Every remote verification finishes before the first tag, draft, asset or index effect.
    result = verify(plan, destination)
    receipt = plan['receipt']
    check_control_policy(stable_release=bundle.version_kind(receipt['version']) == 'stable')
    record = {'packet_sha256': plan['packet_sha256'], 'source': receipt['source'],
              'build_run': receipt['run_id'], 'build_attempt': receipt['attempt'],
              'tag': 'v' + receipt['version'], 'publishers': [{
                  'run_id': int(os.environ['GITHUB_RUN_ID']),
                  'attempt': int(os.environ['GITHUB_RUN_ATTEMPT']),
                  'source': expected_publisher_source}]}
    from usb_installer import prepared_body_record, PREPARED_MARKER
    prepared_body_record('<!-- ' + PREPARED_MARKER + '\n' + json.dumps(record) + '\n-->')
    tag = publish.preserve(receipt, destination, publication_record=record)
    index = None if receipt['branch'] == 'release' else publish.update_index(
        dict(receipt, manifest_sha256=bundle.sha(destination / 'deployment/release-manifest.json')))
    return dict(result, publication_performed=True, release_tag=tag, index=index)


def read_plan(path):
    bundle.require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_PLAN,
                   'Missing or oversized prepared plan')
    return validate_plan(json.loads(path.read_text(), object_pairs_hook=bundle.unique))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    build = sub.add_parser('prepare', help='retain a successful canonical run without publication')
    build.add_argument('--branch', choices=('devel', 'main', 'release'), required=True)
    build.add_argument('--run', type=int, required=True)
    build.add_argument('--attempt', type=int, required=True)
    build.add_argument('--source', required=True)
    build.add_argument('--version', required=True)
    build.add_argument('--destination', type=Path, required=True)
    check = sub.add_parser('verify', help='revalidate canonical archives; no public effects')
    check.add_argument('plan', type=Path)
    check.add_argument('--destination', type=Path, required=True)
    job = sub.add_parser('workflow', help='trusted workflow continuation or read-only validation')
    job.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    if args.operation == 'prepare':
        result = prepare(args)
    elif args.operation == 'verify':
        result = verify(read_plan(args.plan), args.destination)
    else:
        raw = os.environ.get('CI_PREPARED_PLAN', '')
        bundle.require(len(raw.encode()) <= MAX_PLAN, 'Oversized workflow plan')
        plan = validate_plan(json.loads(raw, object_pairs_hook=bundle.unique))
        expected = os.environ.get('CI_EXPECTED_PUBLISHER_SOURCE', '')
        bundle.require(re.fullmatch('[0-9a-f]{40}', expected) and
                       os.environ.get('GITHUB_ACTIONS') == 'true' and
                       os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch' and
                       os.environ.get('GITHUB_REPOSITORY') == download.REPOSITORY and
                       os.environ.get('GITHUB_SHA') == expected and
                       bundle.capture('git', '-C', bundle.ROOT, 'rev-parse', 'HEAD') == expected,
                       'Workflow checkout differs from the selected publisher source')
        confirmed = os.environ.get('CI_PREPARED_PACKET_SHA256', '')
        bundle.require(confirmed == plan['packet_sha256'], 'Workflow packet digest differs')
        selected = os.environ.get('CI_PUBLISH', 'false')
        bundle.require(selected in ('true', 'false'), 'Invalid publication selection')
        if selected == 'true':
            result = publish_prepared(plan, args.destination, confirmed,
                                      os.environ.get('CI_EXPECTED_PUBLISHER_SOURCE', ''))
        else:
            result = verify(plan, args.destination)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
