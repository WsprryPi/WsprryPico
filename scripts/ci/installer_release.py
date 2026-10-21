#!/usr/bin/env python3
"""Publish the independently tested USB installer contract, without firmware."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import publish

ROOT = Path(__file__).resolve().parents[2]
MARKER = 'wsprrypico-usb-installer/1'
WORKFLOW = '.github/workflows/usb-installer.yml'
FILES = {'usb_installer.py': 'scripts/usb_installer.py',
         'release-manifest-1.schema.json': 'scripts/ci/release-manifest-1.schema.json'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build(root, source, channel, run, attempt, job):
    publish.bundle.require(channel in ('main', 'devel') and re.fullmatch('[0-9a-f]{40}', source) and
                           type(run) is int and run > 0 and type(attempt) is int and attempt > 0 and
                           job['name'] == 'verify' and job['status'] == 'completed' and
                           job['conclusion'] == 'success' and type(job['id']) is int and job['id'] > 0,
                           'Installer source or verification identity is invalid')
    files = {name: (root / relative).read_bytes() for name, relative in FILES.items()}
    tree = ast.parse(files['usb_installer.py'])
    versions = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'INSTALLER_VERSION' for target in node.targets)]
    publish.bundle.require(len(versions) == 1 and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', versions[0]),
                           'Installer must declare one semantic version')
    manifest = {'schema': MARKER, 'repository': publish.REPOSITORY, 'contract': 1,
                'result_schema': 'wsprrypico-usb-result/1', 'transaction_schema': 'wsprrypico-usb-transaction/1',
                'firmware_manifest_schema': 1, 'python_min': [3, 10], 'installer_version': versions[0],
                'channel': channel, 'source': source, 'run_id': run, 'attempt': attempt,
                'workflow': WORKFLOW, 'verify_job': {key: job[key] for key in ('id', 'name', 'status', 'conclusion')},
                'tag': f'usb-installer-v1-{channel}-{run}.{attempt}',
                'files': {name: {'sha256': digest(data), 'bytes': len(data)} for name, data in files.items()}}
    files['usb-installer.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    return manifest, files


def index(manifest, files):
    return {key: manifest[key] for key in ('schema', 'repository', 'contract', 'channel', 'source', 'run_id', 'attempt', 'tag')} | {
        'manifest_sha256': digest(files['usb-installer.json'])}


def body(record):
    return ('Latest tested compatible USB installer. Firmware image selection is independent.\n\n'
            f"<!-- {MARKER}\n{json.dumps(record, sort_keys=True)}\n-->\n")


def publish_bundle(manifest, files, destination):
    tag = manifest['tag']
    publish.ensure_tag(tag, manifest['source'])
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        (destination / name).write_bytes(data)
    expected_body = body(index(manifest, files))
    release = publish.find_version_release(tag)
    if release is None:
        release = publish.api('releases', 'POST', {'tag_name': tag, 'target_commitish': manifest['source'],
            'name': tag, 'body': expected_body, 'draft': True, 'prerelease': True, 'make_latest': 'false'})
    publish.bundle.require(release['body'] == expected_body and release['tag_name'] == tag and release['prerelease'],
                           'Existing installer release has another identity')
    assets = publish.asset_inventory(release)
    publish.bundle.require(set(assets) <= set(files), 'Unexpected installer release assets')
    for name, asset in assets.items():
        publish.check_asset(asset, destination / name)
    missing = set(files) - set(assets)
    publish.bundle.require(not missing or release['draft'], 'Published installer is incomplete')
    for name in sorted(missing):
        subprocess.run(['gh', 'release', 'upload', tag, str(destination / name), '--repo', publish.REPOSITORY], check=True)
    release = publish.api('releases/' + str(release['id']))
    assets = publish.asset_inventory(release)
    publish.bundle.require(set(assets) == set(files), 'Incomplete installer asset inventory')
    for name, asset in assets.items():
        publish.check_asset(asset, destination / name)
    if release['draft']:
        publish.api('releases/' + str(release['id']), 'PATCH', {'draft': False, 'prerelease': True, 'make_latest': 'false'})
    channel_tag = f"usb-installer-v1-{manifest['channel']}"
    channel = publish.api('releases/tags/' + channel_tag, missing=True)
    if channel is None:
        publish.ensure_tag(channel_tag, manifest['source'])
        publish.api('releases', 'POST', {'tag_name': channel_tag, 'target_commitish': manifest['source'],
            'name': 'Latest ' + manifest['channel'] + ' USB installer (contract 1)', 'body': expected_body,
            'draft': False, 'prerelease': True, 'make_latest': 'false'})
    else:
        publish.bundle.require(not channel['draft'] and channel['prerelease'] and not channel['assets'],
                               'Invalid installer channel release')
        matches = re.findall(r'<!-- ' + re.escape(MARKER) + r'\n(.*?)\n-->', channel['body'], re.S)
        publish.bundle.require(len(matches) == 1, 'Ambiguous installer channel')
        previous = json.loads(matches[0], object_pairs_hook=publish.bundle.unique)
        candidate = index(manifest, files)
        publish.bundle.require(previous['schema'] == MARKER and previous['repository'] == publish.REPOSITORY and
                               previous['contract'] == 1 and previous['channel'] == manifest['channel'],
                               'Installer channel contract changed')
        if publish.advance({'branch': previous['channel'], **previous}, {'branch': manifest['channel'], **candidate}):
            publish.api('releases/' + str(channel['id']), 'PATCH', {'body': expected_body})


def main():
    publish.require_authorization()
    channel = publish.bundle.build_stream(os.environ['GITHUB_EVENT_NAME'], os.environ['GITHUB_REF'])
    run, attempt = int(os.environ['GITHUB_RUN_ID']), int(os.environ['GITHUB_RUN_ATTEMPT'])
    source = os.environ['GITHUB_SHA']
    observed = publish.api(f'actions/runs/{run}/attempts/{attempt}')
    publish.bundle.require(observed['head_sha'] == source and observed['head_branch'] == channel and
                           observed['path'] == WORKFLOW and observed['event'] in ('push', 'workflow_dispatch'),
                           'Installer publication workflow mismatch')
    jobs = publish.api(f'actions/runs/{run}/attempts/{attempt}/jobs?per_page=100')
    verified = [job for job in jobs['jobs'] if job['name'] == 'verify']
    publish.bundle.require(jobs['total_count'] <= 100 and len(verified) == 1, 'Ambiguous installer verification job')
    manifest, files = build(ROOT, source, channel, run, attempt, verified[0])
    publish_bundle(manifest, files, Path(os.environ['RUNNER_TEMP']) / 'usb-installer-publication')
    print(json.dumps(index(manifest, files), indent=2))


if __name__ == '__main__':
    main()
