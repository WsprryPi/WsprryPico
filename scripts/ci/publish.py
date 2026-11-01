#!/usr/bin/env python3
"""Preserve verified CI bytes and maintain independent permanent branch indexes."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import sys
from types import SimpleNamespace

import bundle
import download
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_control_policy import check_files as check_control_policy

REPOSITORY = download.REPOSITORY
BASE = 'https://github.com/' + REPOSITORY
MARKER = 'wsprrypico-ci-index/1'
TAG_VISIBILITY_DELAYS = (1, 2, 4, 8, 16)


def api(path, method='GET', data=None, missing=False):
    endpoint = 'graphql' if path == 'graphql' else f'repos/{REPOSITORY}/{path}'
    command = ['gh', 'api', '--method', method, endpoint]
    if data is not None:
        command += ['--input', '-']
    result = subprocess.run(command, input=json.dumps(data) if data is not None else None,
                            text=True, capture_output=True)
    if result.returncode:
        if missing and '(HTTP 404)' in result.stderr:
            return None
        raise RuntimeError('GitHub API failed: ' + result.stderr.strip())
    return json.loads(result.stdout, object_pairs_hook=bundle.unique)


def tag_commit(tag):
    ref = api('git/ref/tags/' + tag, missing=True)
    if ref is None:
        return None
    obj = ref['object']
    for _ in range(4):
        if obj['type'] == 'commit':
            return obj['sha']
        bundle.require(obj['type'] == 'tag', 'Unsupported release tag object')
        obj = api('git/tags/' + obj['sha'])['object']
    raise ValueError('Excessively nested release tag')


def ensure_tag(tag, source):
    current = tag_commit(tag)
    if current is None:
        api('git/refs', 'POST', {'ref': 'refs/tags/' + tag, 'sha': source})
        current = tag_commit(tag)
        # A successful creation can precede visibility through the read API.
        # Retry only missing reads; never recreate or move an existing tag.
        for delay in TAG_VISIBILITY_DELAYS:
            if current is not None:
                break
            time.sleep(delay)
            current = tag_commit(tag)
        bundle.require(current is not None,
                       'Created version tag is still not visible after bounded retries: ' + tag)
    bundle.require(current == source,
                   f'Existing version tag points to different source: {tag} (expected {source}, found {current})')


def release_url(tag):
    return BASE + '/releases/tag/' + tag


def asset_url(tag, name):
    return bundle.release_asset_url(tag, name)


def asset_inventory(release):
    assets = release['assets']
    names = [item['name'] for item in assets]
    bundle.require(len(names) == len(set(names)) <= 20, 'Ambiguous release asset inventory')
    return dict(zip(names, assets))


def check_asset(asset, path):
    bundle.require(asset['state'] == 'uploaded' and asset['size'] == path.stat().st_size and
                   asset.get('digest') == 'sha256:' + bundle.sha(path),
                   'Published asset size/SHA-256 mismatch: ' + path.name)


def find_version_release(tag):
    # The REST tag endpoint excludes drafts. GraphQL resolves the pending tag
    # directly, independent of how many permanent versions have accumulated.
    published = api('releases/tags/' + tag, missing=True)
    if published is not None:
        return published
    owner, name = REPOSITORY.split('/')
    result = api('graphql', 'POST', {
        'query': 'query($owner:String!,$name:String!,$tag:String!){repository(owner:$owner,name:$name){release(tagName:$tag){databaseId isDraft}}}',
        'variables': {'owner':owner, 'name':name, 'tag':tag}})
    bundle.require(not result.get('errors'), 'Draft release lookup failed')
    draft = result['data']['repository']['release']
    if draft is None:
        return None
    bundle.require(draft['isDraft'], 'Release changed during discovery')
    return api('releases/' + str(draft['databaseId']))


def version_body(receipt):
    tag = 'v' + receipt['version']
    label = 'Release' if receipt['branch'] == 'release' else receipt['branch'] + ' CI'
    return (f"{label} firmware for Pico 2 W.\n\n"
            f"Version `{receipt['version']}`; source `{receipt['source']}`.\n\n"
            f"[Build and checks]({receipt['url']}) · "
            f"[UF2]({asset_url(tag, receipt['uf2']['path'])}) · "
            f"[Manifest]({asset_url(tag, 'release-manifest.json')}) · "
            f"[Checksums]({asset_url(tag, 'SHA256SUMS')})\n\n"
            "Generic uninhibited application: configure frequency, station and schedules at runtime. "
            "Software/build checks do not establish physical RF or timing acceptance. "
            "The original deployment and linked-image audit archives are preserved unchanged.\n")


def preserve(receipt, destination):
    """Draft until complete; retries may only add missing draft assets."""
    kind = bundle.version_kind(receipt['version'])
    bundle.require(kind != 'testing' and receipt['branch'] in ('main', 'devel', 'release'),
                   'Unsupported publication stream')
    bundle.require((receipt['branch'] == 'release') == (kind in ('stable', 'prerelease')),
                   'Version/publication stream mismatch')
    prerelease = kind != 'stable'
    make_latest = receipt.get('make_latest', False)
    bundle.require(type(make_latest) is bool and (not make_latest or kind == 'stable'),
                   'Only an explicitly selected final release can become latest stable')
    tag = 'v' + receipt['version']
    body = version_body(receipt)
    name = f"WsprryPico {receipt['branch']} {receipt['version']}"
    proof = dict(receipt, schema='wsprrypico-ci-publication/1', repository=REPOSITORY,
                 tag=tag, manifest_sha256=bundle.sha(destination / 'deployment/release-manifest.json'))
    proof_path = destination / 'ci-publication.json'
    proof_path.write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    files = {path.name:path for path in (destination / 'deployment').iterdir()}
    files.update({path.name:path for path in
                  (destination / 'deployment.zip', destination / 'audit.zip', proof_path)})
    bundle.require(len(files) == 9 and all(p.is_file() and not p.is_symlink() for p in files.values()),
                   'Incomplete publication inventory')
    if receipt['branch'] == 'release':
        bundle.require(tag_commit(tag) == receipt['source'], 'Release tag/source mismatch')
    else:
        ensure_tag(tag, receipt['source'])
    release = find_version_release(tag)
    if release is None:
        release = api('releases', 'POST', {'tag_name': tag, 'target_commitish': receipt['source'],
                      'name': name, 'body': body, 'draft': True, 'prerelease': prerelease, 'make_latest': 'false'})
    bundle.require(release['tag_name'] == tag and release['prerelease'] is prerelease and
                   release['name'] == name and release['body'] == body,
                   'Existing version release has different identity')
    existing = asset_inventory(release)
    bundle.require(set(existing) <= set(files), 'Unexpected version release assets')
    for filename, asset in existing.items():
        check_asset(asset, files[filename])
    missing = sorted(set(files) - set(existing))
    bundle.require(not missing or release['draft'], 'Published version release is incomplete')
    for filename in missing:
        subprocess.run(['gh', 'release', 'upload', tag, str(files[filename]), '--repo', REPOSITORY], check=True)
    release = api('releases/' + str(release['id']))
    existing = asset_inventory(release)
    bundle.require(set(existing) == set(files), 'Publication assets are incomplete')
    for filename, path in files.items():
        check_asset(existing[filename], path)
    bundle.require(release['tag_name'] == tag and release['prerelease'] is prerelease and
                   release['name'] == name and release['body'] == body,
                   'Release metadata changed before publication')
    bundle.require(tag_commit(tag) == receipt['source'], 'Version tag changed before publication')
    if release['draft']:
        release = api('releases/' + str(release['id']), 'PATCH',
                      {'draft': False, 'prerelease': prerelease, 'make_latest': 'true' if make_latest else 'false'})
    bundle.require(not release['draft'] and release['prerelease'] is prerelease and
                   tag_commit(tag) == receipt['source'], 'Version release is not eligible')
    return tag


def index_record(receipt):
    tag = 'v' + receipt['version']
    return dict(schema=MARKER, repository=REPOSITORY, branch=receipt['branch'], tag=tag,
                source=receipt['source'], version=receipt['version'], run_id=receipt['run_id'],
                attempt=receipt['attempt'], uf2=receipt['uf2'],
                manifest_sha256=receipt['manifest_sha256'])


def validate_index(record, branch):
    bundle.require(record['schema'] == MARKER and record['repository'] == REPOSITORY and
                   record['branch'] == branch and branch in ('devel', 'main') and
                   re.fullmatch('[0-9a-f]{40}', record['source']) and
                   type(record['run_id']) is int and record['run_id'] > 0 and
                   type(record['attempt']) is int and record['attempt'] > 0 and
                   record['version'] == f"0.1.0-ci.{record['run_id']}.{record['attempt']}" and
                   record['tag'] == 'v' + record['version'] and
                   record['uf2']['path'] == f"WsprryPico-{record['version']}-pico2_w.uf2" and
                   re.fullmatch('[0-9a-f]{64}', record['uf2']['sha256']) and
                   type(record['uf2']['bytes']) is int and 0 < record['uf2']['bytes'] < bundle.MAX_FILE and
                   re.fullmatch('[0-9a-f]{64}', record['manifest_sha256']), 'Invalid branch index identity')
    return record


def parse_index(body, branch):
    matches = re.findall(r'<!-- ' + re.escape(MARKER) + r'\n(.*?)\n-->', body, re.S)
    bundle.require(len(matches) == 1 and len(body) <= 16000, 'Missing or ambiguous branch index')
    return validate_index(json.loads(matches[0], object_pairs_hook=bundle.unique), branch)


def index_body(record):
    tag = record['tag']
    return (f"Latest successful **{record['branch']}** firmware for Pico 2 W.\n\n"
            f"[Download UF2]({asset_url(tag, record['uf2']['path'])}) · "
            f"[Manifest]({asset_url(tag, 'release-manifest.json')}) · "
            f"[Checksums]({asset_url(tag, 'SHA256SUMS')}) · "
            f"[All files and audit]({release_url(tag)})\n\n"
            f"Version `{record['version']}`; source `{record['source']}`.\n\n"
            "This page is a download bookmark. Its tag stays at its original commit; "
            "the linked version release and manifest identify the current firmware. "
            "Configure frequency, station and schedules at runtime.\n\n"
            f"<!-- {MARKER}\n{json.dumps(record, sort_keys=True)}\n-->\n")


def ancestor(older, newer):
    result = subprocess.run(['git', '-C', str(bundle.ROOT), 'merge-base', '--is-ancestor', older, newer])
    bundle.require(result.returncode in (0, 1), 'Cannot establish branch source ordering')
    return result.returncode == 0


def advance(previous, candidate):
    bundle.require(previous['branch'] == candidate['branch'], 'Cross-branch index update')
    if previous['source'] == candidate['source']:
        return (candidate['run_id'], candidate['attempt']) > (previous['run_id'], previous['attempt'])
    if ancestor(previous['source'], candidate['source']):
        return True
    bundle.require(ancestor(candidate['source'], previous['source']), 'Diverged branch index sources')
    return False


def update_index(receipt):
    record = validate_index(index_record(receipt), receipt['branch'])
    tag = 'ci-' + receipt['branch']
    release = api('releases/tags/' + tag, missing=True)
    if release is None:
        # These two bookmark tags are created once. Their bodies, never tags or
        # firmware bytes, advance to a new fully published version.
        current = tag_commit(tag)
        if current is None:
            ensure_tag(tag, receipt['source'])
        else:
            bundle.require(ancestor(current, receipt['source']), 'Unrelated existing branch bookmark tag')
        release = api('releases', 'POST', {'tag_name': tag, 'target_commitish': receipt['source'],
                      'name': 'Latest ' + receipt['branch'] + ' firmware', 'body': index_body(record),
                      'draft': False, 'prerelease': True, 'make_latest': 'false'})
    else:
        bundle.require(not release['draft'] and release['prerelease'] and not release['assets'] and
                       release['tag_name'] == tag, 'Invalid existing branch index release')
        previous = parse_index(release['body'], receipt['branch'])
        if advance(previous, record):
            release = api('releases/' + str(release['id']), 'PATCH', {'body': index_body(record)})
    current = parse_index(release['body'], receipt['branch'])
    return {'branch': receipt['branch'], 'index': release_url(tag), 'selected': current,
            'published': release_url('v' + receipt['version'])}


def resolve(branch):
    bundle.require(branch in ('devel', 'main'), 'Unsupported branch')
    release = api('releases/tags/ci-' + branch)
    bundle.require(not release['draft'] and release['prerelease'] and not release['assets'],
                   'Branch index is not public')
    return parse_index(release['body'], branch)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--resolve', choices=('devel', 'main'), help='Read a public download bookmark only')
    args = parser.parse_args()
    if args.resolve:
        print(json.dumps(resolve(args.resolve), indent=2))
        return
    bundle.require(args.destination is not None, 'Publication destination is required')
    require_authorization()
    branch = bundle.build_stream(os.environ.get('GITHUB_EVENT_NAME'), os.environ.get('GITHUB_REF'))
    run, attempt = int(os.environ['GITHUB_RUN_ID']), int(os.environ['GITHUB_RUN_ATTEMPT'])
    request = SimpleNamespace(branch=branch, run=run, attempt=attempt, source=os.environ['GITHUB_SHA'],
                              version=(os.environ['GITHUB_REF'].removeprefix('refs/tags/v') if branch == 'release'
                                       else f'0.1.0-ci.{run}.{attempt}'), destination=args.destination)
    check_control_policy(stable_release=bundle.version_kind(request.version) == 'stable')
    make_latest = os.environ.get('CI_MAKE_LATEST', 'false')
    bundle.require(make_latest in ('true', 'false') and
                   (make_latest == 'false' or bundle.version_kind(request.version) == 'stable'),
                   'Latest selection requires an explicit final release')
    receipt = download.retrieve(request, for_publication=True)
    if branch == 'release':
        receipt['make_latest'] = make_latest == 'true'
    preserve(receipt, args.destination)
    receipt['manifest_sha256'] = bundle.sha(args.destination / 'deployment/release-manifest.json')
    print(json.dumps(receipt if branch == 'release' else update_index(receipt), indent=2))


def require_authorization():
    bundle.require(os.environ.get('CI_PUBLISH') == 'true' and
                   os.environ.get('GITHUB_ACTIONS') == 'true' and
                   os.environ.get('GITHUB_JOB') == 'publish' and
                   os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch' and
                   os.environ.get('GITHUB_REPOSITORY') == REPOSITORY,
                   'Publication requires explicit manual publish=true in the trusted publisher job')


if __name__ == '__main__':
    main()
