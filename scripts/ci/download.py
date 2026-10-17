#!/usr/bin/env python3
"""Retrieve one successful canonical CI run's immutable artifact pair and verify it."""
import argparse
import json
from pathlib import Path
import re
import shutil
import stat
import subprocess
import zipfile

import bundle

REPOSITORY = 'WsprryPi/WsprryPico'


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', f'repos/{REPOSITORY}/{path}']))


def extract(archive, destination):
    destination.mkdir()
    with zipfile.ZipFile(archive) as source:
        members = source.infolist()
        names = [item.filename for item in members]
        bundle.require(len(names) == len(set(names)) and len(names) <= 2000 and
                       sum(item.file_size for item in members) <= 512 * 1024 * 1024,
                       'Invalid or oversized archive inventory')
        for item in members:
            name = item.filename.rstrip('/')
            bundle.require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]*', name) and
                           not any(part in ('', '.', '..') for part in name.split('/')) and
                           not stat.S_ISLNK(item.external_attr >> 16) and
                           item.file_size <= bundle.MAX_FILE, 'Unsafe archive member')
            target = destination / name
            bundle.require(target.resolve().is_relative_to(destination.resolve()), 'Archive escapes destination')
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(item) as data, target.open('xb') as output:
                    while chunk := data.read(1024 * 1024):
                        output.write(chunk)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=int, required=True)
    parser.add_argument('--attempt', type=int, required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    bundle.require(args.run > 0 and args.attempt > 0 and re.fullmatch('[0-9a-f]{40}', args.source),
                   'Invalid run/attempt/source')
    run = api(f'actions/runs/{args.run}/attempts/{args.attempt}')
    bundle.require(run['status'] == 'completed' and run['conclusion'] == 'success' and
                   run['run_attempt'] == args.attempt and run['head_sha'] == args.source and
                   run['head_branch'] == 'devel' and run['event'] in ('push', 'workflow_dispatch') and
                   run['path'] == '.github/workflows/software-build.yml' and
                   run['head_repository']['full_name'] == REPOSITORY,
                   'Run is not a complete successful canonical devel build')
    workflow = api('actions/workflows/software-build.yml')
    bundle.require(workflow['id'] == run['workflow_id'] and workflow['path'] == run['path'],
                   'Wrong canonical workflow')
    jobs = api(f'actions/runs/{args.run}/attempts/{args.attempt}/jobs')
    bundle.require(jobs['total_count'] == 1 and jobs['jobs'][0]['name'] == 'verify' and
                   jobs['jobs'][0]['conclusion'] == 'success', 'Required CI job did not pass')
    inventory = api(f'actions/runs/{args.run}/artifacts?per_page=100')
    bundle.require(inventory['total_count'] <= 100, 'Ambiguous oversized run artifact inventory')
    destination = args.destination.resolve()
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    receipts = []
    for kind, prefix in (('deployment', 'firmware'), ('audit', 'audit')):
        expected = f'WsprryPico-{prefix}-{args.run}-{args.attempt}-consumer'
        selected = [item for item in inventory['artifacts'] if item['name'] == expected]
        bundle.require(len(selected) == 1 and not selected[0]['expired'], 'Missing or expired immutable artifact')
        artifact = selected[0]
        digest = artifact.get('digest', '')
        bundle.require(re.fullmatch(r'sha256:[0-9a-f]{64}', digest), 'Artifact archive digest unavailable')
        archive = destination / (kind + '.zip')
        with archive.open('xb') as output:
            subprocess.run(['gh', 'api', f'repos/{REPOSITORY}/actions/artifacts/{artifact["id"]}/zip'],
                           stdout=output, check=True)
        bundle.require(bundle.sha(archive) == digest.removeprefix('sha256:'), 'Downloaded archive SHA-256 mismatch')
        extract(archive, destination / kind)
        receipts.append({'kind': kind, 'id': artifact['id'], 'name': artifact['name'],
                         'archive_sha256': bundle.sha(archive), 'expires_at': artifact['expires_at']})
    manifest = bundle.verify(destination / 'deployment', destination / 'audit', args.source, args.version)
    identity = manifest['workflow']
    bundle.require(identity['run_id'] == args.run and identity['attempt'] == args.attempt and
                   identity['event'] == run['event'] and identity['ref'] == 'refs/heads/devel' and
                   identity['url'] == f'https://github.com/{REPOSITORY}/actions/runs/{args.run}' and
                   identity['path'] == run['path'] and args.version == f'0.1.0-ci.{args.run}.{args.attempt}',
                   'Manifest belongs to a different CI run/attempt')
    receipt = {'run_id': args.run, 'attempt': args.attempt, 'source': args.source,
               'version': args.version, 'url': run['html_url'], 'artifacts': receipts,
               'uf2': next(item for item in manifest['assets'] if item['path'].endswith('.uf2')),
               'inspection_tool': {'path': shutil.which('picotool'),
                                   'sha256': bundle.sha(shutil.which('picotool')),
                                   'version': bundle.capture('picotool', 'version')},
               'verified': True}
    (destination / 'verified-download.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
