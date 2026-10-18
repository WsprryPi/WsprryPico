#!/usr/bin/env python3
"""Retrieve one successful canonical CI run's immutable artifact pair and verify it."""
import argparse
import json
import os
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


def fetch_archive(artifact, archive):
    with archive.open('xb') as output:
        subprocess.run(['gh', 'api', f'repos/{REPOSITORY}/actions/artifacts/{artifact["id"]}/zip'],
                       stdout=output, check=True)


def select_artifact(inventory, kind, branch, run, attempt):
    names = {bundle.artifact_name(kind, branch, run, attempt)}
    # Retain access to the accepted original devel bundles without relabelling them.
    if branch == 'devel':
        names.add(f'WsprryPico-{kind}-{run}-{attempt}-consumer')
    selected = [item for item in inventory['artifacts'] if item['name'] in names]
    bundle.require(len(selected) == 1 and not selected[0]['expired'],
                   'Missing, ambiguous or expired immutable artifact for ' + branch)
    return selected[0]


def required_jobs(source):
    import yaml
    workflow = yaml.load(bundle.capture('git', '-C', bundle.ROOT, 'show',
                          source + ':.github/workflows/software-build.yml'), Loader=yaml.BaseLoader)
    return set(workflow['jobs'])


def inspection_tool():
    path = shutil.which('picotool')
    return {'path': path, 'sha256': bundle.sha(path), 'version': bundle.capture('picotool', 'version')}


def retrieve(args, for_publication=False):
    bundle.require(args.run > 0 and args.attempt > 0 and re.fullmatch('[0-9a-f]{40}', args.source),
                   'Invalid run/attempt/source')
    bundle.require(args.branch in ('devel', 'main'), 'Unsupported download branch')
    if for_publication:
        expected = {'GITHUB_ACTIONS':'true', 'GITHUB_JOB':'publish', 'GITHUB_RUN_ID':str(args.run),
                    'GITHUB_RUN_ATTEMPT':str(args.attempt), 'GITHUB_SHA':args.source,
                    'GITHUB_REF':'refs/heads/' + args.branch, 'GITHUB_REPOSITORY':REPOSITORY}
        bundle.require(all(os.environ.get(k) == v for k,v in expected.items()),
                       'Publication collection is restricted to its current trusted publisher job')
    run = api(f'actions/runs/{args.run}/attempts/{args.attempt}')
    complete = run['status'] == 'completed' and run['conclusion'] == 'success'
    publishing = for_publication and run['status'] == 'in_progress' and run['conclusion'] is None
    bundle.require((complete or publishing) and
                   run['run_attempt'] == args.attempt and run['head_sha'] == args.source and
                   run['head_branch'] == args.branch and run['event'] in ('push', 'workflow_dispatch') and
                   run['path'] == '.github/workflows/software-build.yml' and
                   run['head_repository']['full_name'] == REPOSITORY,
                   'Run is not a complete successful canonical ' + args.branch + ' build')
    workflow = api('actions/workflows/software-build.yml')
    bundle.require(workflow['id'] == run['workflow_id'] and workflow['path'] == run['path'],
                   'Wrong canonical workflow')
    jobs = api(f'actions/runs/{args.run}/attempts/{args.attempt}/jobs')
    expected_jobs = required_jobs(args.source)
    by_name = {job['name']:job for job in jobs['jobs']}
    bundle.require(jobs['total_count'] == len(jobs['jobs']) == len(by_name) and
                   set(by_name) == expected_jobs and by_name['verify']['status'] == 'completed' and
                   by_name['verify']['conclusion'] == 'success',
                   'Required CI job did not pass')
    if 'publish' in expected_jobs:
        publisher = by_name['publish']
        bundle.require((for_publication and publisher['status'] == 'in_progress' and
                        publisher['conclusion'] is None) or publisher['conclusion'] == 'success',
                       'Required publication job did not pass')
    bundle.require(not for_publication or 'publish' in expected_jobs, 'Publisher absent from frozen source')
    inventory = api(f'actions/runs/{args.run}/artifacts?per_page=100')
    bundle.require(inventory['total_count'] <= 100, 'Ambiguous oversized run artifact inventory')
    destination = args.destination.resolve()
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    receipts = []
    for kind, prefix in (('deployment', 'firmware'), ('audit', 'audit')):
        artifact = select_artifact(inventory, prefix, args.branch, args.run, args.attempt)
        digest = artifact.get('digest', '')
        bundle.require(re.fullmatch(r'sha256:[0-9a-f]{64}', digest), 'Artifact archive digest unavailable')
        archive = destination / (kind + '.zip')
        fetch_archive(artifact, archive)
        bundle.require(bundle.sha(archive) == digest.removeprefix('sha256:'), 'Downloaded archive SHA-256 mismatch')
        extract(archive, destination / kind)
        receipts.append({'kind': kind, 'id': artifact['id'], 'name': artifact['name'],
                         'archive_sha256': bundle.sha(archive), 'expires_at': artifact['expires_at']})
    manifest = bundle.verify(destination / 'deployment', destination / 'audit', args.source, args.version,
                             inspect=not for_publication)
    if for_publication:
        # The completed read-only verify job ran all linked-image tools. Bind its
        # exact immutable archives and recheck the payload before copying bytes.
        bundle.inspect_payload(destination / 'audit/consumer', 'consumer')
    identity = manifest['workflow']
    bundle.require(identity['run_id'] == args.run and identity['attempt'] == args.attempt and
                   identity['event'] == run['event'] and identity['ref'] == 'refs/heads/' + args.branch and
                   identity['url'] == f'https://github.com/{REPOSITORY}/actions/runs/{args.run}' and
                   identity['path'] == run['path'] and args.version == f'0.1.0-ci.{args.run}.{args.attempt}',
                   'Manifest belongs to a different CI run/attempt')
    receipt = {'branch': args.branch, 'run_id': args.run, 'attempt': args.attempt, 'source': args.source,
               'version': args.version, 'url': run['html_url'], 'artifacts': receipts,
               'verify_job': {key:by_name['verify'][key] for key in ('id', 'status', 'conclusion')},
               'uf2': next(item for item in manifest['assets'] if item['path'].endswith('.uf2')),
               'verified': True, 'verification': 'accepted-verify-job-and-payload' if for_publication else 'independent-linked-image'}
    if not for_publication:
        receipt['inspection_tool'] = inspection_tool()
    (destination / 'verified-download.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def retrieve_published(args):
    """Validate preserved archives even after Actions storage expires."""
    import publish
    bundle.require(args.branch in ('devel', 'main') and args.run > 0 and args.attempt > 0 and
                   re.fullmatch('[0-9a-f]{40}', args.source) and
                   args.version == f'0.1.0-ci.{args.run}.{args.attempt}', 'Invalid published identity')
    tag = 'v' + args.version
    release = publish.api('releases/tags/' + tag)
    bundle.require(not release['draft'] and release['prerelease'] and release['tag_name'] == tag and
                   publish.tag_commit(tag) == args.source, 'Ineligible published version')
    assets = publish.asset_inventory(release)
    names = {f'WsprryPico-{args.version}-pico2_w.uf2', 'release-manifest.json', 'SHA256SUMS',
             'LICENSE.md', 'THIRD_PARTY_NOTICES.md', 'DEPENDENCY-LICENSES.txt',
             'deployment.zip', 'audit.zip', 'ci-publication.json'}
    bundle.require(set(assets) == names, 'Incomplete preserved release')
    destination = args.destination.resolve()
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    for filename in ('ci-publication.json', 'deployment.zip', 'audit.zip'):
        asset = assets[filename]
        bundle.require(0 < asset['size'] <= 512 * 1024 * 1024, 'Oversized preserved asset')
        path = destination / filename
        with path.open('xb') as output:
            subprocess.run(['gh', 'api', '-H', 'Accept: application/octet-stream',
                            f'repos/{REPOSITORY}/releases/assets/{asset["id"]}'], stdout=output, check=True)
        publish.check_asset(asset, path)
    receipt = bundle.read_json(destination / 'ci-publication.json')
    bundle.require(receipt['schema'] == 'wsprrypico-ci-publication/1' and
                   receipt['repository'] == REPOSITORY and receipt['tag'] == tag and
                   receipt['branch'] == args.branch and receipt['source'] == args.source and
                   receipt['version'] == args.version and receipt['run_id'] == args.run and
                   receipt['attempt'] == args.attempt and receipt['verified'] is True and
                   receipt['verification'] == 'accepted-verify-job-and-payload' and
                   type(receipt['verify_job']['id']) is int and receipt['verify_job']['id'] > 0 and
                   receipt['verify_job']['status'] == 'completed' and
                   receipt['verify_job']['conclusion'] == 'success' and
                   receipt['url'] == f'https://github.com/{REPOSITORY}/actions/runs/{args.run}',
                   'Preserved CI receipt belongs to another build')
    bundle.require(len(receipt['artifacts']) == 2, 'Invalid preserved artifact pair')
    bundle.require(release['body'] == publish.version_body(receipt), 'Published release identity mismatch')
    for kind in ('deployment', 'audit'):
        records = [a for a in receipt['artifacts'] if a['kind'] == kind]
        bundle.require(len(records) == 1 and records[0]['id'] > 0 and
                       records[0]['name'] == bundle.artifact_name('firmware' if kind == 'deployment' else kind,
                                                               args.branch, args.run, args.attempt) and
                       bundle.sha(destination / (kind + '.zip')) == records[0]['archive_sha256'],
                       'Preserved original archive identity mismatch')
        extract(destination / (kind + '.zip'), destination / kind)
    manifest = bundle.verify(destination / 'deployment', destination / 'audit', args.source, args.version)
    bundle.require(bundle.sha(destination / 'deployment/release-manifest.json') == receipt['manifest_sha256'] and
                   manifest['workflow']['ref'] == 'refs/heads/' + args.branch and
                   manifest['workflow']['run_id'] == args.run and manifest['workflow']['attempt'] == args.attempt and
                   manifest['workflow']['url'] == receipt['url'] and
                   receipt['uf2'] == next(a for a in manifest['assets'] if a['path'].endswith('.uf2')),
                   'Preserved manifest/source/run identity mismatch')
    for path in (destination / 'deployment').iterdir():
        publish.check_asset(assets[path.name], path)
    receipt['verification'] = 'independent-linked-image-from-preserved-release'
    receipt['inspection_tool'] = inspection_tool()
    (destination / 'verified-download.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--branch', choices=('devel', 'main'), default='devel')
    parser.add_argument('--run', type=int, required=True)
    parser.add_argument('--attempt', type=int, required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--published', action='store_true', help='Use permanent release archives, independent of Actions expiry')
    args = parser.parse_args()
    receipt = retrieve_published(args) if args.published else retrieve(args)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
