#!/usr/bin/env python3
"""WsprryPico's shared USB installer. Python 3.10+, no third-party modules.

Network inputs are data. Programming uses only validated private transaction
copies and an explicitly selected USB serial. No mass erase or force-reset.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import select
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import termios
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

INSTALLER_VERSION = '0.1.0'
REPOSITORY = 'WsprryPi/WsprryPico'
API = 'https://api.github.com/repos/' + REPOSITORY + '/'
DOWNLOAD = 'https://github.com/' + REPOSITORY + '/releases/download/'
SCHEMA = Path(__file__).parent / 'ci/release-manifest-1.schema.json'
SCHEMA_BYTES = None  # A deployed adapter may supply its verified immutable bytes.
PERSISTENT_START = 0x3EE000  # Preserve the superset, including NTP learning.
FLASH_SIZE = 0x400000
PICOTOOL_REVISION = '6f6458d792b93685a11423b244a585eaa99eafcf'
MAX_DOWNLOAD = 16 * 1024 * 1024
HEX40 = r'[0-9a-f]{40}'
HEX64 = r'[0-9a-f]{64}'
SERIAL = r'[0-9A-F]{16}'
VERSION = r'0\.1\.0-ci\.([1-9][0-9]{0,19})\.([1-9][0-9]{0,5})'


class Refusal(ValueError):
    """An unsafe, unsupported, or incomplete operation; never a fallback."""


class HttpFailure(Refusal):
    def __init__(self, status):
        self.status = status
        super().__init__('Public download unavailable (HTTP %s); device unchanged' % status)


class GitHubRateLimit(Refusal):
    def __init__(self, status, headers):
        now = int(time.time())
        deadlines = []
        primary = headers.get('X-RateLimit-Remaining') == '0'
        if primary:
            reset = headers.get('X-RateLimit-Reset', '')
            if re.fullmatch(r'[0-9]{1,12}', reset) and now <= int(reset) <= now + 7 * 86400:
                deadlines.append(int(reset) + 1)
        retry = headers.get('Retry-After', '')
        if re.fullmatch(r'[0-9]{1,6}', retry):
            if int(retry) <= 7 * 86400:
                deadlines.append(now + int(retry) + 1)
        elif retry:
            try:
                date = parsedate_to_datetime(retry)
                if date.tzinfo is not None and now <= date.timestamp() <= now + 7 * 86400:
                    deadlines.append(int(date.timestamp()) + 1)
            except (TypeError, ValueError, OverflowError):
                pass
        # Without usable server guidance, GitHub requires at least one minute.
        deadline = max(deadlines) if deadlines else now + 60
        when = datetime.fromtimestamp(deadline, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        reason = "GitHub's anonymous API request limit is exhausted" if primary else 'GitHub temporarily rate-limited this API request'
        guidance = '' if deadlines else ' GitHub provided no usable retry time; wait at least one minute.'
        super().__init__(f'{reason} (HTTP {status}). Retry after {when}.{guidance}')
        self.details = {'error_code': 'github_rate_limited', 'retry_at': deadline}


class TransactionFailure(Refusal):
    def __init__(self, message, record, path, cause=None):
        super().__init__(message)
        self.result = dict(record, transaction=str(path))
        self.details = getattr(cause, 'details', {})


class MaintenanceDeclined(Refusal):
    """An explicit error response, with no ACK-authorized BOOTSEL request."""


def require(condition, message):
    if not condition:
        raise Refusal(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON member')
        result[key] = value
    return result


def decode(data):
    def invalid(_):
        raise Refusal('Nonfinite JSON')
    try:
        return json.loads(data, object_pairs_hook=unique, parse_constant=invalid)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as error:
        raise Refusal('Invalid JSON data') from error


def schema_check(value, schema):
    """Evaluate the keywords in the canonical v1 manifest (no second schema)."""
    supported = {'$schema', '$id', 'title', 'type', 'const', 'enum', 'required',
                 'properties', 'additionalProperties', 'minProperties', 'maxProperties',
                 'pattern', 'minLength', 'maxLength', 'minimum', 'maximum',
                 'items', 'minItems', 'maxItems', 'uniqueItems'}
    require(not set(schema) - supported, 'Unsupported canonical schema keyword')
    kinds = {'object': dict, 'array': list, 'string': str, 'integer': int,
             'boolean': bool, 'null': type(None)}
    if 'type' in schema:
        options = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
        require(any(type(value) is kinds[t] for t in options), 'Manifest field type mismatch')
    if 'const' in schema:
        require(type(value) is type(schema['const']) and value == schema['const'],
                'Manifest constant mismatch')
    if 'enum' in schema:
        require(value in schema['enum'], 'Manifest enumeration mismatch')
    if isinstance(value, dict):
        require(set(schema.get('required', [])) <= set(value), 'Missing manifest field')
        require(schema.get('minProperties', 0) <= len(value) <= schema.get('maxProperties', 100000),
                'Manifest property count')
        props = schema.get('properties', {})
        extra = schema.get('additionalProperties', True)
        for key, item in value.items():
            if key in props:
                schema_check(item, props[key])
            else:
                require(extra is not False, 'Unknown manifest field')
                if isinstance(extra, dict):
                    schema_check(item, extra)
    if isinstance(value, list):
        require(schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', 100000),
                'Manifest array size')
        if schema.get('uniqueItems'):
            require(len({json.dumps(x, sort_keys=True) for x in value}) == len(value),
                    'Duplicate manifest array member')
        for item in value:
            schema_check(item, schema.get('items', {}))
    if isinstance(value, str):
        require(schema.get('minLength', 0) <= len(value) <= schema.get('maxLength', 2000000),
                'Manifest string length')
        require('pattern' not in schema or re.search(schema['pattern'], value),
                'Manifest string pattern')
    if type(value) is int:
        require(schema.get('minimum', value) <= value <= schema.get('maximum', value),
                'Manifest integer bounds')


class Https:
    """Anonymous, bounded HTTPS. Never loads credentials from gh or the shell."""
    def get(self, url, limit=2 * 1024 * 1024):
        require(0 < limit <= MAX_DOWNLOAD and urllib.parse.urlsplit(url).scheme == 'https',
                'Invalid download URL/limit')
        started = time.monotonic()
        request = urllib.request.Request(url, headers={'User-Agent': 'WsprryPico-USB/' + INSTALLER_VERSION,
                                                       'Accept': 'application/vnd.github+json'})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                require(urllib.parse.urlsplit(response.url).scheme == 'https', 'Insecure redirect')
                content = bytearray()
                while True:
                    require(time.monotonic() - started < 90, 'Download deadline exceeded')
                    chunk = response.read(min(65536, limit + 1 - len(content)))
                    if not chunk:
                        break
                    content.extend(chunk)
                    require(len(content) <= limit, 'Download exceeds size limit')
                length = response.headers.get('Content-Length')
                require(length is None or int(length) == len(content), 'Partial download')
                return bytes(content)
        except urllib.error.HTTPError as error:
            with error:
                headers = error.headers or {}
                if urllib.parse.urlsplit(url).hostname == 'api.github.com' and error.code in (403, 429):
                    try:
                        body = decode(error.read(8192))
                    except (Refusal, OSError):
                        body = {}
                    message = body.get('message', '') if isinstance(body, dict) else ''
                    limited = (error.code == 429 or headers.get('X-RateLimit-Remaining') == '0' or
                               headers.get('Retry-After') is not None or
                               isinstance(message, str) and ('rate limit' in message.lower() or 'abuse detection' in message.lower()))
                    if limited:
                        raise GitHubRateLimit(error.code, headers) from error
                raise HttpFailure(error.code) from error
        except (OSError, urllib.error.URLError) as error:
            raise Refusal('HTTPS download failed; check connectivity or use a verified offline bundle') from error

    def api(self, path):
        return decode(self.get(API + path))


def index_identity(record, branch):
    require(record['schema'] == 'wsprrypico-ci-index/1' and
            record['repository'] == REPOSITORY and record['branch'] == branch and
            re.fullmatch(HEX40, record['source']) and
            type(record['run_id']) is int and record['run_id'] > 0 and
            type(record['attempt']) is int and record['attempt'] > 0 and
            record['version'] == f"0.1.0-ci.{record['run_id']}.{record['attempt']}" and
            record['tag'] == 'v' + record['version'] and
            record['uf2']['path'] == f"WsprryPico-{record['version']}-pico2_w.uf2" and
            re.fullmatch(HEX64, record['uf2']['sha256']) and
            type(record['uf2']['bytes']) is int and 0 < record['uf2']['bytes'] <= MAX_DOWNLOAD and
            re.fullmatch(HEX64, record['manifest_sha256']), 'Invalid branch download index')
    return record


def parse_index(body, branch):
    require(isinstance(body, str) and len(body) <= 16000, 'Invalid branch bookmark')
    matches = re.findall(r'<!-- wsprrypico-ci-index/1\n(.*?)\n-->', body, re.S)
    require(len(matches) == 1, 'Missing or ambiguous branch bookmark')
    return index_identity(decode(matches[0]), branch)


def uf2_blocks(data, application_end):
    """Exact RP2350 ARM-S blocks plus the pinned E10 absolute block only.

    The E10 address aliases the last page of a 4 MiB flash in the ROM UF2
    workflow. Pinned picotool's SUPPORT_RP2350_A2 reader recognizes and skips
    this exact absolute-family block. Programming uses that identified reader;
    all persistent sectors, including the final sector, must read back unchanged.
    """
    require(application_end in (0x103EE000, 0x103F0000), 'Unsupported application/storage layout')
    require(data and len(data) % 512 == 0 and len(data) <= MAX_DOWNLOAD, 'Invalid UF2 length')
    count = len(data) // 512
    blocks, workaround = {}, 0
    for index in range(count):
        block = data[index * 512:(index + 1) * 512]
        m0, m1, flags, address, size, number, total, family = struct.unpack_from('<8I', block)
        require((m0, m1, struct.unpack_from('<I', block, 508)[0]) ==
                (0x0A324655, 0x9E5D5157, 0x0AB16F30), 'Invalid UF2 magic')
        require(size == 256, 'UF2 payload size')
        if address == 0x10FFFF00:
            require(index == 0 and number == 0 and total == 2 and
                    flags == 0xA000 and family == 0xE48BFF57 and
                    block[32:288] == b'\xef' * 256 and
                    block[288:292] == bytes.fromhex('04e35799') and block[292:508] == bytes(216),
                    'Invalid RP2350 E10 workaround')
            workaround += 1
            continue
        require(number == index - 1 and total == count - 1 and
                flags == 0x2000 and family == 0xE48BFF59 and address % 256 == 0 and
                0x10000000 <= address < address + size <= application_end and
                address not in blocks and block[288:508] == bytes(220), 'Unsafe UF2 block/flash extent')
        blocks[address] = block[32:288]
    require(workaround == 1 and blocks and min(blocks) == 0x10000000, 'Missing application/E10 block')
    addresses = sorted(blocks)
    require(addresses == list(range(addresses[0], addresses[-1] + 256, 256)),
            'Sparse UF2 application is unsupported')
    # Page erasure is sector-rounded, including the padded tail of the image.
    require((addresses[-1] + 256 + 4095) // 4096 * 4096 <= 0x10000000 + PERSISTENT_START,
            'UF2 erase extent overlaps durable state')
    return b''.join(blocks[a] for a in addresses)


def verify_bundle(files, branch, schema_path=SCHEMA):
    require('release-manifest.json' in files and 'ci-publication.json' in files and
            'SHA256SUMS' in files, 'Incomplete verified bundle')
    manifest = decode(files['release-manifest.json'])
    schema_check(manifest, decode(SCHEMA_BYTES if schema_path == SCHEMA and SCHEMA_BYTES is not None
                                 else schema_path.read_bytes()))
    proof = decode(files['ci-publication.json'])
    source, workflow = manifest['source'], manifest['workflow']
    version = manifest['firmware_version']
    require(re.fullmatch(VERSION, version), 'Unsupported version/storage compatibility policy')
    require(manifest['deployment_candidate'] is True and source['clean'] is True and
            manifest['channel'] == 'ci-testing' and
            workflow['event'] in ('push', 'workflow_dispatch') and
            workflow['ref'] == 'refs/heads/' + branch and
            workflow['revision'] == source['revision'] and
            workflow['url'] == f"https://github.com/{REPOSITORY}/actions/runs/{workflow['run_id']}" and
            version == f"0.1.0-ci.{workflow['run_id']}.{workflow['attempt']}", 'Untrusted firmware provenance')
    checks = manifest['checks']
    require(checks['registered'] > 0 and checks['registered'] == checks['passed'] and
            checks['failed'] == checks['skipped'] == 0 and
            len(checks['test_names']) == len(set(checks['test_names'])) == checks['registered'],
            'Required CI checks did not all pass')
    require(proof['schema'] == 'wsprrypico-ci-publication/1' and proof['repository'] == REPOSITORY and
            proof['branch'] == branch and proof['source'] == source['revision'] and
            proof['version'] == version and proof['tag'] == manifest['intended_tag'] == 'v' + version and
            proof['run_id'] == workflow['run_id'] and proof['attempt'] == workflow['attempt'] and
            proof['url'] == workflow['url'] and
            proof['verified'] is True and proof['verification'] == 'accepted-verify-job-and-payload' and
            proof['verify_job']['status'] == 'completed' and proof['verify_job']['conclusion'] == 'success' and
            type(proof['verify_job']['id']) is int and proof['verify_job']['id'] > 0 and
            proof['manifest_sha256'] == sha(files['release-manifest.json']), 'Invalid preserved CI receipt')
    artifacts = proof['artifacts']
    require(len(artifacts) == 2 and {a['kind'] for a in artifacts} == {'deployment', 'audit'} and
            all(type(a['id']) is int and a['id'] > 0 and re.fullmatch(HEX64, a['archive_sha256'])
                for a in artifacts), 'Invalid original artifact identities')
    for artifact in artifacts:
        prefix = 'firmware' if artifact['kind'] == 'deployment' else 'audit'
        require(artifact['name'] == f"WsprryPico-{prefix}-{branch}-{workflow['run_id']}-{workflow['attempt']}-consumer",
                'Original artifact belongs to another branch/run/attempt')
    require(manifest['update']['ordinary_update_erases_settings'] is False and
            manifest['update']['whole_flash_erase_required'] is False and
            manifest['firmware']['credentials_in_image'] is False and
            manifest['firmware']['schedules_enabled_by_image'] is False,
            'Incompatible update behavior')
    assets = manifest['assets']
    names = [a['path'] for a in assets]
    uf2_name = f'WsprryPico-{version}-pico2_w.uf2'
    require(len(names) == len(set(names)) and set(names) ==
            {uf2_name, 'LICENSE.md', 'THIRD_PARTY_NOTICES.md', 'DEPENDENCY-LICENSES.txt'} and
            set(files) == set(names) | {'release-manifest.json', 'SHA256SUMS', 'ci-publication.json'},
            'Unexpected deployment asset inventory')
    for asset in assets:
        require(asset['bytes'] == len(files[asset['path']]) and sha(files[asset['path']]) == asset['sha256'],
                'Deployment size/SHA-256 mismatch')
    lines = files['SHA256SUMS'].decode('ascii').splitlines()
    expected = {**{a['path']: a['sha256'] for a in assets},
                'release-manifest.json': sha(files['release-manifest.json'])}
    checks = {}
    for line in lines:
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._-]*)', line)
        require(match and match[2] not in checks, 'Malformed/duplicate checksum inventory')
        checks[match[2]] = match[1]
    require(checks == expected and proof['uf2'] == next(a for a in assets if a['path'] == uf2_name),
            'Checksum/receipt payload inventory mismatch')
    image = uf2_blocks(files[uf2_name], int(manifest['update']['application_end'], 16))
    return manifest, image


def resolve(client, branch='main', version=None, stable=False):
    """Resolve once through the maintained source-ordered branch bookmark."""
    require(branch in ('main', 'devel'), 'Unsupported branch')
    if stable:
        require(not version, 'Choose either stable or an explicit version')
        release = client.api('releases/latest')
        require(release.get('draft') is False and release.get('prerelease') is False, 'No stable release is available')
        # Stable remains subject to the same canonical provenance/storage checks.
        # The current public v1 contract describes CI testing images only.
        raise Refusal('No compatible stable image is published under the supported CI manifest contract; use latest CI or --version explicitly')
    if version:
        require(re.fullmatch(VERSION, version), 'Unsupported explicit version')
        tag = 'v' + version
        index = None
    else:
        try:
            bookmark = client.api('releases/tags/ci-' + branch)
        except HttpFailure as error:
            if error.status != 404:
                raise
            raise Refusal(f'No verified {branch} CI download is available; its published branch bookmark is missing.') from error
        require(bookmark['tag_name'] == 'ci-' + branch and not bookmark['draft'], 'Invalid bookmark release')
        index = parse_index(bookmark['body'], branch)
        tag = index['tag']
    release = client.api('releases/tags/' + tag)
    require(release['tag_name'] == tag and release['prerelease'] is True and release['draft'] is False,
            'Release is not an eligible CI testing image')
    obj = client.api('git/ref/tags/' + tag)['object']
    for _ in range(4):
        if obj['type'] == 'commit':
            break
        require(obj['type'] == 'tag', 'Unsupported version tag object')
        obj = client.api('git/tags/' + obj['sha'])['object']
    require(obj['type'] == 'commit' and re.fullmatch(HEX40, obj['sha']), 'Invalid version tag')
    inventory = {a['name']: a for a in release['assets']}
    version = tag[1:]
    names = {'release-manifest.json', 'ci-publication.json', 'SHA256SUMS', 'LICENSE.md',
             'THIRD_PARTY_NOTICES.md', 'DEPENDENCY-LICENSES.txt', f'WsprryPico-{version}-pico2_w.uf2'}
    require(len(inventory) == len(release['assets']) and set(inventory) == names | {'deployment.zip', 'audit.zip'},
            'Incomplete or ambiguous public assets')
    files = {}
    for name in sorted(names):
        asset = inventory[name]
        require(asset['state'] == 'uploaded' and type(asset['size']) is int and
                0 < asset['size'] <= MAX_DOWNLOAD and re.fullmatch('sha256:' + HEX64, asset['digest']) and
                asset['browser_download_url'] == DOWNLOAD + tag + '/' + name, 'Invalid public asset')
        data = client.get(DOWNLOAD + tag + '/' + name, asset['size'])
        require(len(data) == asset['size'] and 'sha256:' + sha(data) == asset['digest'], 'Public asset mismatch')
        files[name] = data
    manifest, image = verify_bundle(files, branch)
    require(obj['sha'] == manifest['source']['revision'], 'Version tag/source mismatch')
    for artifact in decode(files['ci-publication.json'])['artifacts']:
        archive = inventory[artifact['kind'] + '.zip']
        require(archive['state'] == 'uploaded' and
                archive['digest'] == 'sha256:' + artifact['archive_sha256'],
                'Preserved CI archive/publication identity mismatch')
    if index:
        require(index['manifest_sha256'] == sha(files['release-manifest.json']) and
                index['source'] == manifest['source']['revision'] and
                index['uf2'] == decode(files['ci-publication.json'])['uf2'], 'Branch metadata swap')
    # A retained successful verification receipt remains usable after Actions
    # expiration. If live run metadata exists, require the whole run to pass.
    try:
        run = client.api(f"actions/runs/{manifest['workflow']['run_id']}/attempts/{manifest['workflow']['attempt']}")
    except HttpFailure as error:
        if error.status not in (404, 410):
            raise
    else:
        require(run['status'] == 'completed' and run['conclusion'] == 'success' and
                run['head_sha'] == manifest['source']['revision'] and run['head_branch'] == branch and
                run['path'] == '.github/workflows/software-build.yml' and
                run['head_repository']['full_name'] == REPOSITORY and
                run['event'] in ('push', 'workflow_dispatch') and
                run['run_attempt'] == manifest['workflow']['attempt'], 'CI run is not a canonical success')
        jobs = client.api(f"actions/runs/{manifest['workflow']['run_id']}/attempts/{manifest['workflow']['attempt']}/jobs?per_page=100")
        by_name = {job['name']: job for job in jobs['jobs']}
        require(jobs['total_count'] == len(jobs['jobs']) == len(by_name) and
                set(by_name) == {'verify', 'publish'} and
                all(j['status'] == 'completed' and j['conclusion'] == 'success' for j in by_name.values()) and
                by_name['verify']['id'] == decode(files['ci-publication.json'])['verify_job']['id'],
                'Required CI jobs or verification receipt disagree')
    return files, manifest, image


def command(arguments, timeout=30):
    """No shell, inherited stdin, credentials, or subprocess output in receipts."""
    result = subprocess.run([str(x) for x in arguments], stdin=subprocess.DEVNULL,
                            capture_output=True, timeout=timeout)
    require(result.returncode == 0, 'Command failed: ' + str(arguments[0]) +
            ' (check USB permissions, device connection, and picotool installation)')
    require(len(result.stdout) < 4 * 1024 * 1024, 'Oversized tool response')
    return result.stdout.decode('utf-8')


def recent_ci(client, branch, manifest):
    """Additional status only; never changes the pinned bookmark selection."""
    try:
        runs = client.api('actions/workflows/software-build.yml/runs?branch=' + branch + '&per_page=10')
        for run in runs['workflow_runs'][:10]:
            if (run.get('head_repository', {}).get('full_name') != REPOSITORY or
                    run.get('head_branch') != branch or run.get('event') not in ('push', 'workflow_dispatch') or
                    not re.fullmatch(HEX40, run.get('head_sha', ''))):
                continue
            if run['head_sha'] == manifest['source']['revision']:
                newer = (run['id'], run['run_attempt']) > (manifest['workflow']['run_id'], manifest['workflow']['attempt'])
            else:
                compare = client.api('compare/' + manifest['source']['revision'] + '...' + run['head_sha'])
                newer = compare['status'] == 'ahead' and compare['merge_base_commit']['sha'] == manifest['source']['revision']
            if newer:
                return {'available': True, 'newer_run': {'run_id': run['id'], 'attempt': run['run_attempt'],
                        'source': run['head_sha'], 'status': run['status'], 'conclusion': run['conclusion']},
                        'selection': 'Pinned published image remains selected; additional run is not substituted'}
        return {'available': True, 'newer_run': None}
    except GitHubRateLimit as error:
        return {'available': False, 'reason': str(error), **error.details}
    except (Refusal, KeyError, TypeError, ValueError):
        return {'available': False, 'reason': 'Additional CI run status is unavailable; selected public receipt was verified'}


def read_bundle(directory):
    files = {}
    require(directory.is_dir() and not directory.is_symlink(), 'Unsafe bundle directory')
    for member in directory.iterdir():
        require(member.is_file() and not member.is_symlink() and member.stat().st_size <= MAX_DOWNLOAD,
                'Unsafe bundle member')
        files[member.name] = member.read_bytes()
    return files


def candidate_asset(files, manifest):
    return (decode(files['local-build.json'])['uf2'] if 'local-build.json' in files else
            decode(files['ci-publication.json'])['uf2'])


def installed_local(root, serial, snapshot, flash=None):
    """A local version string alone is not an image identity."""
    matches = []
    reference = root / ('.local-reference-' + serial + '.json')
    if reference.exists():
        image_path = root / ('.local-image-' + serial + '.uf2')
        require(not reference.is_symlink() and not image_path.is_symlink() and
                reference.stat().st_size <= 65536 and image_path.stat().st_size <= MAX_DOWNLOAD,
                'Unsafe retained local image reference')
        identity = decode(reference.read_bytes())
        require(identity['schema'] == 'wsprrypico-local-reference/1' and identity['serial'] == serial,
                'Wrong-board local image reference')
        files = {'local-build.json': json.dumps(identity['manifest'], sort_keys=True).encode(),
                 'WsprryPico-0.0.0-devel-pico2_w.uf2': image_path.read_bytes()}
        manifest, image = verify_local(files)
        require(candidate_asset(files, manifest)['sha256'] == identity['uf2_sha256'] and
                manifest['source']['identity'] == snapshot['source_revision'] and
                (flash is None or flash[:len(image)] == image), 'Installed local image differs from its same-board reference')
        return files, manifest, image
    for directory in root.glob(serial + '-*'):
        if directory.is_symlink() or not (directory / 'local-build.json').is_file():
            continue
        try:
            for name in ('transaction.json', 'local-build.json', 'WsprryPico-0.0.0-devel-pico2_w.uf2'):
                member = directory / name
                require(member.is_file() and not member.is_symlink() and member.stat().st_size <= MAX_DOWNLOAD,
                        'Unsafe retained local candidate')
            record = decode((directory / 'transaction.json').read_bytes())
            require(record['serial'] == serial and record['stage'] == 'complete', 'Not an accepted local transaction')
            files = {name: (directory / name).read_bytes() for name in
                     ('local-build.json', 'WsprryPico-0.0.0-devel-pico2_w.uf2')}
            manifest, image = verify_local(files)
            if (manifest['source']['identity'] == snapshot['source_revision'] and
                    (flash is None or flash[:len(image)] == image) and candidate_asset(files, manifest)['sha256'] == record['uf2_sha256']):
                matches.append((files, manifest, image))
        except (OSError, Refusal, KeyError, ValueError):
            continue
    require(matches, 'Installed local image has no retained same-board verified transaction; deliberate recovery is required')
    require(len({candidate_asset(f, m)['sha256'] for f, m, _ in matches}) == 1, 'Ambiguous installed local image')
    return matches[0]


def remember_local(directory, record):
    """Retain generic image identity separately from expiring secret backups."""
    root, serial = directory.parent, record['serial']
    reference = root / ('.local-reference-' + serial + '.json')
    require(reference.exists() or len(list(root.glob('.local-reference-*.json'))) < 32,
            'Local image references are full; retire an unused board reference explicitly')
    files = {name: (directory / name).read_bytes() for name in
             ('local-build.json', 'WsprryPico-0.0.0-devel-pico2_w.uf2')}
    manifest, _ = verify_local(files)
    require(candidate_asset(files, manifest)['sha256'] == record['uf2_sha256'], 'Local reference image changed')
    image_path = root / ('.local-image-' + serial + '.uf2')
    require(not image_path.is_symlink() and not reference.is_symlink(), 'Unsafe local reference destination')
    save_bytes(image_path, files['WsprryPico-0.0.0-devel-pico2_w.uf2'])
    save_json(reference, {'schema': 'wsprrypico-local-reference/1', 'serial': serial,
                         'uf2_sha256': record['uf2_sha256'], 'manifest': decode(files['local-build.json'])})


def resolve_installed(client, version):
    """An installed image keeps its own original branch provenance."""
    require(re.fullmatch(VERSION, version), 'Unsupported installed firmware identity')
    release = client.api('releases/tags/v' + version)
    metadata = [a for a in release['assets'] if a['name'] == 'release-manifest.json']
    url = DOWNLOAD + 'v' + version + '/release-manifest.json'
    require(len(metadata) == 1 and metadata[0]['browser_download_url'] == url,
            'Installed image provenance is unavailable')
    manifest = decode(client.get(url, 2 * 1024 * 1024))
    ref = manifest['workflow']['ref']
    require(ref in ('refs/heads/main', 'refs/heads/devel'), 'Unsupported installed firmware branch')
    return resolve(client, ref.rsplit('/', 1)[1], version)


def verify_local(files):
    """Private developer metadata; never a public release or CI receipt."""
    meta = decode(files['local-build.json'])
    source, asset = meta['source'], meta['uf2']
    require(meta['schema'] == 'wsprrypico-local-build/1' and meta['board'] == 'pico2_w' and
            meta['variant'] == 'normal' and meta['version'] == '0.0.0-devel' and
            re.fullmatch(HEX40, source['revision']) and type(source['dirty']) is bool and
            re.fullmatch(HEX64, source['inputs_sha256']) and
            source['identity'] in (source['revision'][:12], source['revision'][:12] + '-dirty') and
            asset['path'] == 'WsprryPico-0.0.0-devel-pico2_w.uf2' and
            set(files) == {'local-build.json', asset['path']} and
            asset['bytes'] == len(files[asset['path']]) and asset['sha256'] == sha(files[asset['path']]),
            'Incompatible or changed developer bundle')
    require(meta['usb_update_contract'] == 1 and meta['application_end'] in ('103ee000', '103f0000'),
            'Developer image lacks the supported USB/storage contract')
    image = uf2_blocks(files[asset['path']], int(meta['application_end'], 16))
    require(b'WsprryPico USB maintenance 1 postboot verification 1' in image,
            'Developer image is missing its linked USB update declaration')
    manifest = {'firmware_version': meta['version'], 'source': source, 'workflow': None,
                'update': {'application_end': meta['application_end'], 'usb_maintenance': 1,
                           'postboot_verification': 1}}
    return manifest, image


def build_local(args):
    source = args.local_build.expanduser().resolve(strict=True)
    output = args.build_dir.expanduser().absolute()
    require(not output.exists() and not output.is_symlink(), 'Developer build directory must be new')
    revision = command(['git', '-C', source, 'rev-parse', 'HEAD']).strip()
    require(re.fullmatch(HEX40, revision) and
            (not args.source_revision or args.source_revision == revision), 'Local source revision mismatch')
    status = command(['git', '-C', source, 'status', '--porcelain', '--untracked-files=normal'])
    require(not status or args.allow_dirty, 'Dirty developer source needs explicit --allow-dirty')
    # Hash actual source inputs, including untracked source. Ignore generated and
    # ignored build outputs; refuse symlink inputs instead of following them.
    names = command(['git', '-C', source, 'ls-files', '-co', '--exclude-standard', '-z']).split('\0')
    inputs = hashlib.sha256()
    for name in sorted(set(names) - {''}):
        member = source / name
        require(not member.is_symlink(), 'Symlink developer source input is unsupported')
        if member.is_file():
            inputs.update(name.encode() + b'\0' + hashlib.sha256(member.read_bytes()).digest())
    before = inputs.hexdigest()
    require(shutil.disk_usage(output.parent).free >= 768 * 1024 * 1024,
            'Need at least 768 MiB free for a fresh developer build')
    # Existing helper checks exact SDK/submodule/compiler pins and performs the
    # linked engine/storage/USB checks. No package or SDK acquisition is offered.
    log = output.with_name(output.name + '.installer-build.log')
    with log.open('xb') as stream:
        result = subprocess.run(['bash', str(source / 'scripts/build_pico.sh'), 'WsprryPico', str(output)],
                                stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, timeout=900)
    require(result.returncode == 0, 'Developer compilation failed; inspect ' + str(log) + '; no alternate image was selected')
    require(command(['git', '-C', source, 'rev-parse', 'HEAD']).strip() == revision and
            command(['git', '-C', source, 'status', '--porcelain', '--untracked-files=normal']) == status,
            'Local source changed during compilation; do not use this build')
    after = hashlib.sha256()
    for name in sorted(set(names) - {''}):
        member = source / name
        require(not member.is_symlink(), 'Developer source changed during compilation')
        if member.is_file():
            after.update(name.encode() + b'\0' + hashlib.sha256(member.read_bytes()).digest())
    require(after.hexdigest() == before, 'Developer input bytes changed during compilation')
    cache = (output / 'CMakeCache.txt').read_text()
    require(re.search(r'^PICO_BOARD:STRING=pico2_w$', cache, re.M) and
            re.search(r'^WSPRRY_PICO_NETWORK_PORT:STRING=0$', cache, re.M) and
            re.search(r'^WSPRRY_PICO_NETWORK_CREDENTIAL_DIR:PATH=$', cache, re.M),
            'Developer build must use generic Pico 2 W defaults without credentials')
    identity = (output / 'firmware/generated/firmware_identity.hpp').read_text()
    match = re.search(r'kBuildRevision\[\]\s*=\s*"([0-9a-f]{12}(?:-dirty)?)"', identity)
    require(match and match[1].startswith(revision[:12]), 'Developer linked source identity unavailable')
    data = (output / 'firmware/WsprryPico.uf2').read_bytes()
    mapping = (output / 'firmware/WsprryPico.elf.map').read_text()
    end = re.search(r'^FLASH\s+0x10000000\s+0x003(ee000|f0000)\s+xr$', mapping, re.M)
    require(end, 'Developer linked storage boundary unavailable')
    meta = {'schema': 'wsprrypico-local-build/1', 'board': 'pico2_w', 'variant': 'normal',
            'version': '0.0.0-devel', 'source': {'revision': revision, 'dirty': bool(status),
                'identity': match[1], 'inputs_sha256': before}, 'usb_update_contract': 1,
            'application_end': '103' + end[1],
            'uf2': {'path': 'WsprryPico-0.0.0-devel-pico2_w.uf2', 'bytes': len(data), 'sha256': sha(data)}}
    files = {'local-build.json': json.dumps(meta, sort_keys=True).encode(), meta['uf2']['path']: data}
    manifest, image = verify_local(files)
    return files, manifest, image


def discover(system=None):
    """Metadata only. Interface identity comes from the USB parent, never tty order."""
    system = system or platform.system()
    devices = []
    if system == 'Darwin':
        raw = subprocess.run(['ioreg', '-a', '-r', '-c', 'IOUSBHostDevice', '-l'],
                             capture_output=True, check=True, timeout=10).stdout
        if not raw.strip():
            return []
        for parent in plistlib.loads(raw):
            vendor, product = parent.get('idVendor'), parent.get('idProduct')
            if (vendor, product) not in ((0x2E8A, 0x000F), (0xCAFE, 0x4012)):
                continue
            serial = parent.get('USB Serial Number', '')
            require(re.fullmatch(SERIAL, serial), 'USB serial unavailable/conflicting')
            ports = {}
            interfaces = {n['bInterfaceNumber']: n for n in parent.get('IORegistryEntryChildren', [])
                          if 'bInterfaceNumber' in n}
            def walk(node, role=None):
                if 'bInterfaceNumber' in node:
                    number = node['bInterfaceNumber']
                    # macOS attaches IOSerialBSDClient under the CDC DATA
                    # interface (1/3/5), paired with control interface 0/2/4.
                    control = interfaces.get(number - 1, {})
                    role = (number - 1 if number in (1, 3, 5) and
                            node.get('bInterfaceClass') == 10 and control.get('bInterfaceClass') == 2
                            else None)
                if 'IOCalloutDevice' in node and role in (0, 2, 4):
                    require(str(role) not in ports, 'Duplicate USB role')
                    ports[str(role)] = node['IOCalloutDevice']
                for child in node.get('IORegistryEntryChildren', []):
                    walk(child, role)
            walk(parent)
            devices.append({'serial': serial, 'mode': 'bootsel' if vendor == 0x2E8A else 'application',
                            'parent': str(parent['locationID']), 'ports': ports})
    elif system == 'Linux':
        for parent in Path('/sys/bus/usb/devices').iterdir():
            if not (parent / 'idVendor').is_file():
                continue
            vendor = int((parent / 'idVendor').read_text().strip(), 16)
            product = int((parent / 'idProduct').read_text().strip(), 16)
            if (vendor, product) not in ((0x2E8A, 0x000F), (0xCAFE, 0x4012)):
                continue
            serial = (parent / 'serial').read_text().strip()
            require(re.fullmatch(SERIAL, serial), 'Invalid USB serial')
            ports = {}
            for interface in parent.resolve().glob(parent.name + ':*'):
                if not (interface / 'bInterfaceNumber').is_file():
                    continue
                role = int((interface / 'bInterfaceNumber').read_text().strip(), 16)
                for tty in interface.rglob('ttyACM*'):
                    if tty.parent.name == 'tty' and role in (0, 2, 4):
                        require(str(role) not in ports, 'Duplicate USB role')
                        ports[str(role)] = '/dev/' + tty.name
            devices.append({'serial': serial, 'mode': 'bootsel' if vendor == 0x2E8A else 'application',
                            'parent': parent.name, 'ports': ports})
    else:
        raise Refusal('Supported hosts: macOS and Linux. Windows/WSL USB is not supported.')
    require(len({d['serial'] for d in devices}) == len(devices), 'Duplicate physical USB serial')
    return devices


def selected(serial, mode=None, parent=None):
    require(re.fullmatch(SERIAL, serial), 'Explicit 16-character uppercase USB serial required')
    matches = [d for d in discover() if d['serial'] == serial]
    require(len(matches) == 1, 'Selected Pico missing; connect that board using a USB data cable')
    device = matches[0]
    require(mode is None or device['mode'] == mode,
            'Hold BOOTSEL while reconnecting the selected Pico; automatic reset is not supported')
    require(parent is None or device['parent'] == parent, 'Physical USB port changed; re-plan the operation')
    return device


def device_id(serial):
    return sha(b'WsprryPico/1' + bytes.fromhex(serial))[:32]


class Management:
    """Bounded UMP1 session for reads and explicit USB maintenance only."""
    def __init__(self, device):
        self.device, self.fd, self.id, self.hello = device, None, 0, None
        self.etags = {}

    def __enter__(self):
        require('4' in self.device['ports'], 'USB management role is unavailable')
        selected(self.device['serial'], 'application', self.device['parent'])
        self.fd = os.open(self.device['ports']['4'], os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.ioctl(self.fd, termios.TIOCEXCL)
            attributes = termios.tcgetattr(self.fd)
            attributes[:4] = [0, 0, termios.CS8 | termios.CREAD | termios.CLOCAL, 0]
            attributes[4:6] = [termios.B115200, termios.B115200]
            attributes[6][termios.VMIN] = attributes[6][termios.VTIME] = 0
            termios.tcsetattr(self.fd, termios.TCSANOW, attributes)
            fcntl.ioctl(self.fd, termios.TIOCMBIC, struct.pack('I', termios.TIOCM_DTR))
            time.sleep(.1)
            termios.tcflush(self.fd, termios.TCIOFLUSH)
            fcntl.ioctl(self.fd, termios.TIOCMBIS, struct.pack('I', termios.TIOCM_DTR))
            self.hello = self.exchange({'operation': 'hello'})
            require(self.hello['status'] == 200 and self.hello['delivery_required'] is False and
                    self.hello['target']['device_id'] == device_id(self.device['serial']) and
                    re.fullmatch(r'[0-9a-f]{32}', self.hello['target']['boot_id']) and
                    re.fullmatch(r'[0-9a-f]{32}', self.hello['session']), 'USB application identity mismatch')
            body = decode(self.hello['body'])
            require(body['schema'] == 'usb-management-discovery/1' and body['product'] == 'WsprryPico',
                    'Unsupported USB management protocol')
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        if self.fd is not None:
            try:
                try:
                    fcntl.ioctl(self.fd, termios.TIOCMBIC, struct.pack('I', termios.TIOCM_DTR))
                    fcntl.ioctl(self.fd, termios.TIOCNXCL)
                except OSError as error:
                    if error.errno not in (errno.EIO, errno.ENXIO, errno.ENODEV):
                        raise
            finally:
                os.close(self.fd)
                self.fd = None

    def exchange(self, fields, repeat=False):
        if not repeat:
            self.id += 1
        request = dict(schema='usb-management/1', id=self.id, **fields)
        if self.hello:
            request.update(session=self.hello['session'], target=self.hello['target'])
        data = json.dumps(request, separators=(',', ':')).encode()
        outgoing = b'UMP1' + len(data).to_bytes(4, 'big') + data
        incoming = bytearray()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            readers, writers, _ = select.select([self.fd], [self.fd] if outgoing else [], [], .05)
            if writers:
                outgoing = outgoing[os.write(self.fd, outgoing):]
            if readers:
                part = os.read(self.fd, 65536)
                require(part, 'USB disconnected')
                incoming.extend(part)
                require(len(incoming) <= 65544, 'USB response overflow')
            if len(incoming) >= 8:
                size = int.from_bytes(incoming[4:8], 'big')
                require(incoming[:4] == b'UMP1' and 0 < size <= 65536, 'USB framing mismatch')
                if len(incoming) >= size + 8:
                    require(not outgoing and len(incoming) == size + 8, 'Ambiguous USB response')
                    response = decode(incoming[8:])
                    require(response['schema'] == 'usb-management/1' and response['id'] == self.id,
                            'USB response request mismatch')
                    if self.hello:
                        require(response['target'] == self.hello['target'] and
                                response['session'] == self.hello['session'], 'Stale USB boot/session')
                    return response
        raise Refusal('USB management deadline; delivery is unconfirmed and a requested maintenance change may have occurred')

    def get(self, path):
        response = self.exchange(dict(operation='request', method='GET', path=path, body='', if_match=''))
        require(response['delivery_required'] is True, 'Missing USB delivery acknowledgement')
        ack = self.exchange(dict(operation='ack'), repeat=True)
        require(ack['status'] == 200 and ack['delivery_required'] is False and
                decode(ack['body']) == {'acknowledged': True}, 'USB ACK failed')
        require(response['status'] == 200, 'Required USB resource unavailable: ' + path)
        self.etags[path] = response['etag']
        return decode(response['body'])

    def enter_bootsel(self, snapshot):
        require(self.hello['target'] == snapshot['target'], 'Application boot changed after preflight')
        body = dict(schema='transmitter-usb-maintenance/1', target=snapshot['target'], confirmed=True,
                    watermark_utc_ns=snapshot['status']['standalone']['watermark_utc_ns'])
        response = self.exchange(dict(operation='request', method='POST', path='/api/usb/v1/maintenance',
                                     body=json.dumps(body, separators=(',', ':')), if_match=snapshot['revision']))
        require(response['delivery_required'] is True, 'Maintenance response is not acknowledgeable')
        if response['status'] != 202:
            try:
                self.exchange(dict(operation='ack'), repeat=True)
            except (OSError, Refusal):
                pass  # Acknowledging an explicit error cannot authorize reset.
            raise MaintenanceDeclined('Firmware refused guarded USB maintenance. Leave jobs/settings unchanged; '
                          'this firmware may require manual recovery with a supported installer image.')
        require(decode(response['body']) == {'requested': True}, 'Invalid maintenance response')
        try:
            ack = self.exchange(dict(operation='ack'), repeat=True)
            require(ack['status'] == 200, 'Maintenance acknowledgement failed')
        except (OSError, Refusal):
            # The target may reset after receiving ACK but before the host sees
            # its reply. Only exact physical BOOTSEL re-identification settles it.
            pass

    def finish_verification(self, snapshot):
        require(self.hello['target'] == snapshot['target'], 'Application boot changed during final verification')
        phase = self.get('/api/usb/v1/maintenance')
        require(phase == {'schema': 'transmitter-usb-maintenance/1', 'phase': 'verification'},
                'Postboot maintenance was not established')
        body = dict(schema='transmitter-usb-maintenance/1', target=snapshot['target'], confirmed=True,
                    watermark_utc_ns=snapshot['status']['standalone']['watermark_utc_ns'])
        response = self.exchange(dict(operation='request', method='POST', path='/api/usb/v1/maintenance/finish',
                                     body=json.dumps(body, separators=(',', ':')), if_match=snapshot['revision']))
        require(response['status'] == 202 and response['delivery_required'] is True,
                'Target refused to finish verified maintenance')
        ack = self.exchange(dict(operation='ack'), repeat=True)
        require(ack['status'] == 200 and self.get('/api/usb/v1/maintenance') ==
                {'schema': 'transmitter-usb-maintenance/1', 'phase': 'idle'},
                'Maintenance release is unconfirmed; keep the Pi member paused')


def public_snapshot(device):
    with Management(device) as management:
        status = management.get('/api/v1/status')
        config = management.get('/api/v1/config/4')
        progress = management.get('/api/v1/progress/3')
        hostname = management.get('/api/v1/hostname')
        frequency = management.get('/api/v1/standalone-frequency')
        calibration = management.get('/api/v1/rf-calibration')
        observation = management.get('/api/v1/ntp-observations')
        return {'serial': device['serial'], 'parent': device['parent'],
                'target': management.hello['target'], 'firmware': decode(management.hello['body'])['firmware'],
                'status': status, 'config': config, 'progress': progress, 'hostname': hostname,
                'frequency': frequency, 'calibration': calibration,
                'source_revision': observation['source_revision'], 'captured_at': int(time.time()),
                'revision': management.etags['/api/v1/config/4']}


class Picotool:
    def __init__(self, path='picotool'):
        resolved = shutil.which(str(path))
        require(resolved, 'Install picotool 2.3.0 with USB support; see the USB installer guide')
        self.path = Path(resolved).resolve()
        report = command([self.path, 'version'])
        require(report.startswith('picotool v2.3.0 ') and 'without USB support' not in report,
                'USB-enabled picotool 2.3.0 is required (pinned source ' + PICOTOOL_REVISION + ')')
        self.identity = {'version': report.strip(), 'sha256': sha(self.path.read_bytes())}

    def run(self, serial, *args, timeout=60):
        selected(serial, 'bootsel')
        return command([self.path, *args, '--ser', serial], timeout)

    def read_flash(self, serial, path):
        self.run(serial, 'save', '-r', '0x10000000', '0x10400000', '-v', path, '-t', 'bin')
        require(path.is_file() and not path.is_symlink() and path.stat().st_size == FLASH_SIZE,
                'Incomplete private flash backup')
        data = path.read_bytes()
        # A second supported comparison verifies the same-board read, independently
        # of the save command's success/progress output.
        self.run(serial, 'verify', path, '-t', 'bin', '-o', '0x10000000')
        path.chmod(0o600)
        return data


@contextlib.contextmanager
def device_lock(serial):
    require(re.fullmatch(SERIAL, serial), 'Invalid USB serial')
    root = (Path('/run/lock/wsprrypico') if platform.system() == 'Linux' else
            Path.home() / 'Library/Caches/WsprryPico/locks')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(not root.is_symlink(), 'Unsafe lock directory')
    fd = os.open(root / (serial + '.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o660)
    if os.fstat(fd).st_uid == os.getuid():
        os.fchmod(fd, 0o660 if platform.system() == 'Linux' else 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), 'Unsafe device lock')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise Refusal('This Pico already has an installer or runtime owner') from error
        yield
    finally:
        os.close(fd)


def private_directory(path):
    path = Path(path).expanduser().absolute()
    require('..' not in path.parts, 'Parent traversal in private state path')
    # Backups contain credentials and bonds. A CLI override is not permission
    # to save them under a checkout, a served directory, or a redirected home.
    allowed = (Path.home() / '.local/state/wsprrypico-usb', Path('/var/lib/wsprrypi/pico-usb'))
    require(any(path == root or root in path.parents for root in allowed),
            'Backups must stay under ~/.local/state/wsprrypico-usb or /var/lib/wsprrypi/pico-usb')
    for ancestor in (path, *path.parents):
        require(not ancestor.is_symlink(), 'Symlink ancestor in private backup destination')
        require(not (ancestor / '.git').exists(), 'Flash backups cannot be stored inside a Git checkout')
    require(not any(part in ('public_html', 'htdocs', 'www', 'wwwroot', 'webroot') for part in path.parts),
            'Flash backups cannot be stored in a web root')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(path.resolve(strict=True) == path, 'Private state path is not a physical directory')
    require(path.stat().st_uid == os.getuid() and path.stat().st_mode & 0o077 == 0,
            'Private state directory must be owned by you with mode 0700')
    return path


def save_bytes(path, data):
    # Unique names permit retry after host loss without overwriting an unknown
    # temporary. In-process failures remove only this call's owned temporary.
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '-', suffix='.tmp', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def save_json(path, value):
    # Private atomic stage updates; never put flash contents or secret values here.
    save_bytes(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


def prune_transactions(root):
    """Bound completed/unchanged history for seven days; never erase recovery."""
    complete, unchanged, unresolved = [], [], []
    for directory in root.iterdir():
        require(not directory.is_symlink(), 'Symlink in private transaction inventory')
        if not directory.is_dir():
            continue
        record = directory / 'transaction.json'
        require(record.is_file() and not record.is_symlink() and record.stat().st_size <= 65536,
                'Unknown private transaction; inspect it before continuing')
        value = decode(record.read_bytes())
        require(value['schema'] == 'wsprrypico-usb-transaction/1' and
                directory.name.startswith(value['serial'] + '-') and re.fullmatch(SERIAL, value['serial']),
                'Unknown private transaction identity')
        if value['stage'] == 'complete' and value['recovery_required'] is False:
            complete.append(directory)
        elif value['recovery_required'] is False:
            # A refusal before mutation (including an explicit maintenance
            # decline) is diagnostic history, not an outstanding recovery.
            unchanged.append(directory)
        else:
            unresolved.append(directory)
    # Cap retained uncertain operations by refusing new ones, never discarding
    # the only old-image/settings recovery material to make room.
    require(len(unresolved) < 8, 'Eight unresolved transactions retained; reconcile recovery before another update')
    for history, limit in ((complete, 2), (unchanged, 8)):
        for index, directory in enumerate(sorted(history, key=lambda p: p.stat().st_mtime, reverse=True)):
            if index >= limit or time.time() - directory.stat().st_mtime > 7 * 86400:
                shutil.rmtree(directory)


def classify_flash(data):
    require(len(data) == FLASH_SIZE, 'Incomplete flash classification')
    boot = data[0x3FF000:]
    known_boot = boot == b'\xff' * 4096 or boot == b'\xff' * 3840 + b'\xef' * 256
    return {'application_erased': data[:PERSISTENT_START] == b'\xff' * PERSISTENT_START,
            'saved_state_erased': data[PERSISTENT_START:0x3FF000] == b'\xff' * (0x3FF000-PERSISTENT_START),
            'boot_sector_known': known_boot}


def transaction(args, files, manifest, image, client=None):
    serial = args.device
    if args.operation == 'upgrade':
        require(manifest['update'].get('usb_maintenance') == manifest['update'].get('postboot_verification') == 1,
                'Selected image lacks guarded upgrade/postboot verification; choose a compatible newer CI image')
    tool = Picotool(args.picotool)
    with device_lock(serial):
        board = selected(serial, 'bootsel' if args.operation == 'install' else 'application')
        require(args.board == 'pico2_w', 'Explicit --board pico2_w confirmation is required for BOOTSEL hardware')
        root = private_directory(args.state_dir)
        prune_transactions(root)
        if 'local-build.json' in files:
            require((root / ('.local-reference-' + serial + '.json')).exists() or
                    len(list(root.glob('.local-reference-*.json'))) < 32,
                    'Local image references are full; retire an unused board before installing another')
        require(shutil.disk_usage(root).free >= 128 * 1024 * 1024, 'Need at least 128 MiB for private backup/transaction')
        directory = Path(tempfile.mkdtemp(prefix=serial + '-', dir=root))
        root_fd = os.open(root, os.O_RDONLY)
        try:
            os.fsync(root_fd)
        finally:
            os.close(root_fd)
        record = {'schema': 'wsprrypico-usb-transaction/1', 'installer_version': INSTALLER_VERSION,
                  'serial': serial, 'parent': board['parent'], 'operation': args.operation,
                  'branch': args.branch, 'version': manifest['firmware_version'],
                  'source': manifest['source']['revision'], 'run': manifest['workflow'],
                  'uf2_sha256': candidate_asset(files, manifest)['sha256'],
                  'picotool': tool.identity, 'stage': 'validated', 'recovery_required': False}
        path = directory / 'transaction.json'
        save_json(path, record)
        try:
            for name, data in files.items():
                save_bytes(directory / name, data)
            candidate = directory / f"WsprryPico-{manifest['firmware_version']}-pico2_w.uf2"
            linked = command([tool.path, 'info', '-a', candidate])
            for field, expected in (('name', 'WsprryPico'), ('version', manifest['firmware_version']),
                                    ('description', 'Standalone PIO/DMA RF ' + manifest['source'].get('identity', manifest['source']['revision'][:12])),
                                    ('pico_board', 'pico2_w'), ('target chip', 'RP2350')):
                require(re.search(r'^ ' + re.escape(field) + r':\s+' + re.escape(expected) + r'$', linked, re.M),
                        'Embedded image identity mismatch: ' + field)
            snapshot = None
            if args.operation == 'upgrade':
                require(board['mode'] == 'application',
                        'An ordinary upgrade starts in the running application and requires guarded USB maintenance')
                snapshot = public_snapshot(board)
                admit_snapshot(snapshot)
                save_json(directory / 'preflight.json', snapshot)
                old_version = snapshot['firmware']
                require(client, 'Missing provenance resolver')
                if old_version == '0.0.0-devel':
                    old_files, old_manifest, old_image = installed_local(root, serial, snapshot)
                else:
                    require(re.fullmatch(VERSION, old_version), 'Unsupported installed firmware; retain backup and recover deliberately')
                    old_files, old_manifest, old_image = ((files, manifest, image) if old_version == manifest['firmware_version'] and
                                                        'local-build.json' not in files else resolve_installed(client, old_version))
                old_source, new_source = old_manifest['source']['revision'], manifest['source']['revision']
                if old_source != new_source:
                    compare = client.api('compare/' + old_source + '...' + new_source)
                    require(compare['status'] == 'ahead' and compare['merge_base_commit']['sha'] == old_source,
                            'Downgrade/diverged source is unsupported for saved storage')
                if old_manifest['update'].get('usb_maintenance') != 1:
                    # Legacy applications cannot hold their writers/scheduler.
                    # The operator performs the physical reset; no reset/STOP
                    # command or flash write is authorized by this preparation.
                    require(snapshot['config'].get('config') is None or
                            snapshot['config']['config'].get('enabled') is False,
                            'Disable the saved standalone schedule deliberately before BOOTSEL migration')
                    require(snapshot['source_revision'] == old_source[:12],
                            'Installed source does not match its verified CI image')
                    installed = directory / 'installed'
                    installed.mkdir(mode=0o700)
                    for name, data in old_files.items():
                        save_bytes(installed / name, data)
                    record.update(stage='awaiting_bootsel', recovery_required=True,
                                  manual_bootsel_required=True, installed_branch=old_manifest['workflow']['ref'].rsplit('/', 1)[-1],
                                  installed_source=old_source, installed_version=old_version,
                                  preflight_sha256=sha((directory / 'preflight.json').read_bytes()))
                    save_json(path, record)
                    return dict(record, transaction=str(path))
                # All network/provenance work completes before requesting reset.
                record.update(stage='entering_bootsel', recovery_required=True)
                save_json(path, record)
                with Management(board) as management:
                    try:
                        management.enter_bootsel(snapshot)
                    except MaintenanceDeclined:
                        record.update(stage='maintenance_refused', recovery_required=False)
                        save_json(path, record)
                        raise
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    matches = [d for d in discover() if d['serial'] == serial and d['mode'] == 'bootsel']
                    if matches:
                        require(len(matches) == 1 and matches[0]['parent'] == board['parent'], 'BOOTSEL device/port changed')
                        break
                    time.sleep(.1)
                else:
                    raise Refusal('Guarded BOOTSEL transition unconfirmed; no firmware was written')
            info = tool.run(serial, 'info', '-a')
            require(re.search(r'^ type:\s+RP2350$', info, re.M), 'Wrong processor')
            require(re.search(r'^ chipid:\s+0x' + serial.lower() + '$', info, re.M), 'BOOTSEL chip identity mismatch')
            before = tool.read_flash(serial, directory / 'before.bin')
            with (directory / 'before.bin').open('rb') as backup:
                os.fsync(backup.fileno())
            record.update(stage='backup_readback_verified', backup_sha256=sha(before),
                          persistent_sha256=sha(before[PERSISTENT_START:]))
            save_json(path, record)
            blank = before == b'\xff' * FLASH_SIZE
            if args.operation == 'install':
                classification = classify_flash(before)
                require(classification['saved_state_erased'] and classification['boot_sector_known'],
                        'Initial installation refused: existing saved state or unknown boot-sector data needs identified recovery')
                require(classification['application_erased'] or getattr(args, 'replace_unidentified_application', False),
                        'Initial installation refused: unidentified application bytes exist. Inspect the private backup; '
                        'explicit --replace-unidentified-application is required to replace them while retaining erased saved state.')
                record['initial_flash'] = classification
            else:
                require(not blank, 'Erased board requires explicit install operation')
                require(snapshot['serial'] == serial and snapshot['parent'] == board['parent'] and
                        snapshot['target']['device_id'] == device_id(serial), 'Preflight belongs to a different board')
                require(before[:len(old_image)] == old_image, 'Installed firmware does not match its verified identity')
                require(int(old_manifest['update']['application_end'], 16) <= int(manifest['update']['application_end'], 16) or
                        before[PERSISTENT_START:0x3F0000] == b'\xff' * 8192,
                        'Newly reserved storage is not erased; migration is unsupported')
            record.update(stage='backed_up', program_authorized=True, backup_sha256=sha(before),
                          persistent_sha256=sha(before[PERSISTENT_START:]))
            save_json(path, record)
            return program_verified(args, tool, record, path, manifest, image, before, snapshot)
        except BaseException as error:
            record['failure_stage'] = record['stage']
            record['stage'] = 'failed'
            record['failure_reason'] = str(error)
            try:
                save_json(path, record)
            except OSError:
                record['record_write_failed'] = True
            raise TransactionFailure('Interrupted; inspect the retained transaction and use manual BOOTSEL recovery.'
                                     if isinstance(error, KeyboardInterrupt) else str(error), record, path, error) from error


def program_verified(args, tool, record, path, manifest, image, before, snapshot):
    serial, directory = record['serial'], path.parent
    require(record.get('program_authorized') is True or record.get('preserved') is True,
            'Programming was not authorized by completed compatibility checks')
    selected(serial, 'bootsel', record['parent'])
    filename = directory / f"WsprryPico-{manifest['firmware_version']}-pico2_w.uf2"
    require(sha(filename.read_bytes()) == record['uf2_sha256'], 'Private programming image changed')
    record.update(stage='programming', recovery_required=True)
    save_json(path, record)  # Durable ambiguity begins before spawning the writer.
    tool.run(serial, 'load', '--ignore-partitions', '-v', filename, timeout=120)
    tool.run(serial, 'verify', filename, timeout=120)
    after = tool.read_flash(serial, directory / 'after.bin')
    require(after[:len(image)] == image and after[PERSISTENT_START:] == before[PERSISTENT_START:],
            'Program or reserved flash readback mismatch; leave board in BOOTSEL')
    record.update(stage='programmed_and_flash_verified', preserved=True)
    save_json(path, record)
    record.update(stage='launching_verification_boot')
    save_json(path, record)
    # Pinned -x selects REBOOT_TYPE_FLASH_UPDATE; -u skips the already
    # verified sectors. Supporting firmware holds scheduling on this boot
    # until the final identity/settings verification is acknowledged.
    tool.run(serial, 'load', '--ignore-partitions', '-u', '-v', '-x', filename, timeout=120)
    return verify_application(args, tool, record, path, manifest, snapshot)


def verify_application(args, tool, record, path, manifest, snapshot):
    serial = record['serial']
    deadline = time.monotonic() + 40
    observed = None
    while time.monotonic() < deadline:
        try:
            devices = [d for d in discover() if d['serial'] == serial and d['mode'] == 'application']
        except (OSError, plistlib.InvalidFileException):
            time.sleep(.25)
            continue
        if devices:
            require(len(devices) == 1 and devices[0]['parent'] == record['parent'], 'Reconnected device/port changed')
            try:
                observed = public_snapshot(devices[0])
                break
            except (OSError, Refusal):
                pass
        time.sleep(.25)
    require(observed and observed['firmware'] == manifest['firmware_version'] and
            observed['source_revision'] == manifest['source'].get('identity', manifest['source']['revision'][:12]),
            'Application identity/version verification failed; manual BOOTSEL recovery required')
    releasing = record.get('verification_release_boot') == observed['target']['boot_id']
    if not releasing:
        admit_snapshot(observed)
    if record['operation'] == 'upgrade' and not releasing:
        # Only stable saved representations are compared; boot/pending
        # observations are intentionally separate from durable settings.
        require(saved_semantics(snapshot) == saved_semantics(observed),
                'Saved semantic state differs after reboot; keep member in maintenance')
    if manifest['update'].get('postboot_verification') == 1:
        record.update(stage='application_verified_maintenance_held', target=observed['target'])
        save_json(path, record)
        with Management(selected(serial, 'application', record['parent'])) as management:
            phase = management.get('/api/usb/v1/maintenance')['phase']
            require(phase == 'verification' or (releasing and phase == 'idle'),
                    'Postboot verification hold is absent or the boot changed; deliberate recovery required')
            if phase == 'verification':
                record.update(stage='verification_release_requested', verification_release_boot=observed['target']['boot_id'])
                save_json(path, record)
                management.finish_verification(observed)
    else:
        require(record['operation'] == 'install' and observed['config'].get('config') is None,
                'Legacy image can only be initially installed with no saved standalone configuration')
    if 'local-build.json' in {p.name for p in path.parent.iterdir()}:
        remember_local(path.parent, record)
    record.update(stage='complete', recovery_required=False,
                  target=observed['target'], preserved=True)
    save_json(path, record)
    return dict(record, transaction=str(path))


def saved_semantics(snapshot):
    # Deliberately small and explicit: byte equality before boot covers all
    # banks. Public saved fields independently verify their loaded meaning.
    return {'config': snapshot['config'].get('config'),
            'progress_fields': snapshot['progress']['fields'],
            'draft_revision': snapshot['progress']['draft_revision'],
            'hostname': snapshot['hostname'].get('saved'),
            'frequency': snapshot['frequency']['frequency_hz'],
            'calibration': snapshot['calibration']['saved'],
            'watermark_utc_ns': snapshot['status']['standalone']['watermark_utc_ns'],
            'suspended': snapshot['status']['standalone']['suspended']}


def admit_snapshot(snapshot):
    job = snapshot['status']['job']
    require(job['state'] == 'empty' and job['output_active'] is False and job['owner_id'] is None,
            'Pico is busy, owned, stopped/faulted, or uncertain; leave its state unchanged')
    require(snapshot['status']['standalone']['suspended'] is False or snapshot['config'].get('config') is None,
            'STOP/suspension is active; resolve it deliberately before an update')


def recover_transaction(args):
    require(args.device and args.yes and args.transaction and args.board == 'pico2_w',
            'Recovery requires --device, --transaction, --board pico2_w and --yes')
    path = Path(args.transaction).expanduser().absolute()
    require(path.name == 'transaction.json' and path.parent.is_dir(), 'Select an existing private transaction.json')
    private_directory(path.parent)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 65536 and
            path.stat().st_uid == os.getuid() and path.stat().st_mode & 0o077 == 0,
            'Unsafe recovery transaction record')
    record = decode(path.read_bytes())
    require(record['schema'] == 'wsprrypico-usb-transaction/1' and record['serial'] == args.device and
            record['installer_version'] == INSTALLER_VERSION and
            (re.fullmatch(VERSION, record['version']) or record['version'] == '0.0.0-devel') and
            record['branch'] in ('main', 'devel') and re.fullmatch(HEX40, record['source']),
            'Incompatible or wrong-board recovery record')
    names = ({'local-build.json', f"WsprryPico-{record['version']}-pico2_w.uf2"} if (path.parent / 'local-build.json').exists() else
             {'release-manifest.json', 'SHA256SUMS', 'ci-publication.json', 'LICENSE.md',
             'THIRD_PARTY_NOTICES.md', 'DEPENDENCY-LICENSES.txt', f"WsprryPico-{record['version']}-pico2_w.uf2"})
    files = {}
    for name in names:
        member = path.parent / name
        require(member.is_file() and not member.is_symlink() and member.stat().st_size <= MAX_DOWNLOAD,
                'Recovery cache is incomplete or unsafe')
        files[name] = member.read_bytes()
    manifest, image = verify_local(files) if 'local-build.json' in files else verify_bundle(files, record['branch'])
    require(manifest['source']['revision'] == record['source'] and
            candidate_asset(files, manifest)['sha256'] == record['uf2_sha256'],
            'Recovery bundle differs from original transaction')
    pending_migration = (record.get('manual_bootsel_required') is True and
                         record.get('operation') == 'upgrade' and
                         record.get('failure_stage', record['stage']) == 'awaiting_bootsel' and
                         not record.get('program_authorized'))
    if pending_migration:
        return continue_migration(args, record, path, manifest, image)
    require(record.get('program_authorized') is True or record.get('preserved') is True,
            'No completed compatibility authorization; inspect the unchanged image and use deliberate recovery')
    backup = path.parent / 'before.bin'
    require(backup.is_file() and not backup.is_symlink() and backup.stat().st_size == FLASH_SIZE,
            'No verified backup was completed; firmware was not authorized for programming in this transaction')
    before = backup.read_bytes()
    require(sha(before) == record.get('backup_sha256') and
            sha(before[PERSISTENT_START:]) == record.get('persistent_sha256'), 'Recovery backup integrity mismatch')
    snapshot_path = path.parent / 'preflight.json'
    snapshot = decode(snapshot_path.read_bytes()) if record['operation'] == 'upgrade' else None
    tool = Picotool(args.picotool)
    with device_lock(args.device):
        board = selected(args.device, parent=record['parent'])
        original_stage = record.get('failure_stage', 'failed') if record['stage'] == 'failed' else record['stage']
        record['recovery_attempts'] = record.get('recovery_attempts', 0) + 1
        record['original_failure_stage'] = record.get('original_failure_stage', original_stage)
        try:
            if board['mode'] == 'application':
                require(original_stage in ('programmed_and_flash_verified', 'launching_verification_boot',
                                            'application_verified_maintenance_held', 'verification_release_requested', 'complete'),
                        'Programming was ambiguous. Deliberately reconnect this board in BOOTSEL for readback/recovery.')
                return verify_application(args, tool, record, path, manifest, snapshot)
            current = tool.read_flash(args.device, path.parent / 'recovery-readback.bin')
            require(current[PERSISTENT_START:] == before[PERSISTENT_START:],
                    'Reserved state differs from backup; do not overwrite it or restore it blindly')
            return program_verified(args, tool, record, path, manifest, image, before, snapshot)
        except BaseException as error:
            # Admission/read failures can happen before this attempt advances
            # hardware progress. Keep the last durable non-failure stage so
            # another same-boot application verification remains possible.
            if record['stage'] != 'failed':
                record['failure_stage'] = record['stage']
            record.update(stage='failed', recovery_required=True)
            record['failure_reason'] = str(error)
            try:
                save_json(path, record)
            except OSError:
                record['record_write_failed'] = True
            raise TransactionFailure(str(error), record, path, error) from error


def continue_migration(args, record, path, manifest, image):
    """Authorize a legacy migration only after physical same-board BOOTSEL."""
    try:
        require(manifest['update'].get('usb_maintenance') == manifest['update'].get('postboot_verification') == 1,
                'Migration target lacks guarded postboot verification')
        snapshot_path = path.parent / 'preflight.json'
        require(snapshot_path.is_file() and not snapshot_path.is_symlink() and
                snapshot_path.stat().st_size <= MAX_DOWNLOAD and
                sha(snapshot_path.read_bytes()) == record['preflight_sha256'], 'Migration snapshot integrity mismatch')
        snapshot = decode(snapshot_path.read_bytes())
        require(snapshot['serial'] == args.device and snapshot['parent'] == record['parent'] and
                snapshot['target']['device_id'] == device_id(args.device) and
                snapshot['firmware'] == record['installed_version'] and
                snapshot['source_revision'] == record['installed_source'][:12], 'Migration preflight identity mismatch')
        admit_snapshot(snapshot)
        require(snapshot['config'].get('config') is None or snapshot['config']['config'].get('enabled') is False,
                'Migration requires a disabled standalone schedule')
        old_manifest, old_image = verify_bundle(read_bundle(path.parent / 'installed'), record['installed_branch'])
        require(old_manifest['source']['revision'] == record['installed_source'] and
                old_manifest['firmware_version'] == snapshot['firmware'] and
                old_manifest['update'].get('usb_maintenance') != 1, 'Migration installed image identity mismatch')
        with device_lock(args.device):
            selected(args.device, 'bootsel', record['parent'])
            tool = Picotool(args.picotool)
            info = tool.run(args.device, 'info', '-a')
            require(re.search(r'^ type:\s+RP2350$', info, re.M) and
                    re.search(r'^ chipid:\s+0x' + args.device.lower() + '$', info, re.M), 'Migration BOOTSEL chip identity mismatch')
            require(shutil.disk_usage(path.parent).free >= 128 * 1024 * 1024,
                    'Need at least 128 MiB for private backup/transaction')
            before = tool.read_flash(args.device, path.parent / 'before.bin')
            with (path.parent / 'before.bin').open('rb') as backup:
                os.fsync(backup.fileno())
            require(before[:len(old_image)] == old_image, 'Installed firmware does not match its verified CI image')
            require(int(old_manifest['update']['application_end'], 16) <= int(manifest['update']['application_end'], 16) or
                    before[PERSISTENT_START:0x3F0000] == b'\xff' * 8192,
                    'Newly reserved storage is not erased; migration is unsupported')
            record.update(stage='backed_up', program_authorized=True, backup_sha256=sha(before),
                          persistent_sha256=sha(before[PERSISTENT_START:]), manual_bootsel_required=False)
            save_json(path, record)
            return program_verified(args, tool, record, path, manifest, image, before, snapshot)
    except BaseException as error:
        if record['stage'] != 'failed':
            record['failure_stage'] = record['stage']
        record.update(stage='failed', recovery_required=True)
        record['failure_reason'] = str(error)
        save_json(path, record)
        raise TransactionFailure(str(error), record, path, error) from error


def main(argv=None, schema_bytes=None):
    global SCHEMA_BYTES
    SCHEMA_BYTES = schema_bytes
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('discover', 'plan', 'snapshot', 'install', 'upgrade', 'recover'))
    parser.add_argument('--branch', choices=('main', 'devel'), default='main')
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument('--version', help='Explicit compatible CI version (never silently falls back)')
    choice.add_argument('--stable', action='store_true', help='Explicit stable selection; refuses when no compatible stable is published')
    choice.add_argument('--local-build', type=Path, help='Explicit developer source checkout to compile with existing pinned tools')
    choice.add_argument('--local-bundle', type=Path, help='Explicit previously built developer bundle')
    parser.add_argument('--build-dir', type=Path, help='New developer build directory; never reused')
    parser.add_argument('--source-revision', help='Require this exact full local source HEAD')
    parser.add_argument('--allow-dirty', action='store_true', help='Explicitly accept a labelled dirty developer build')
    parser.add_argument('--device', help='Physical USB serial; required for unattended operations')
    parser.add_argument('--board', choices=('pico2_w',), help='Confirm the actual BOOTSEL board is Pico 2 W')
    parser.add_argument('--yes', action='store_true', help='Explicit noninteractive install/upgrade request')
    parser.add_argument('--replace-unidentified-application', action='store_true',
                        help='Initial installation only: explicitly replace unknown application bytes, requiring erased saved state')
    parser.add_argument('--picotool', default='picotool')
    parser.add_argument('--output', type=Path, help='New private snapshot or verified offline bundle directory')
    parser.add_argument('--bundle', type=Path, help='Previously verified public bundle directory (offline planning/install)')
    parser.add_argument('--state-dir', type=Path, default=Path.home() / '.local/state/wsprrypico-usb')
    parser.add_argument('--transaction', type=Path, help='Exact private transaction.json for explicit same-board recovery')
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        require(not args.bundle or not (args.version or args.stable or args.local_build or args.local_bundle),
                '--bundle cannot be combined with another image selector')
        require(not args.replace_unidentified_application or args.operation == 'install',
                'Replacing unidentified application bytes is an explicit initial-install operation only')
        if args.operation == 'discover':
            result = {'devices': discover()}
        elif args.operation == 'recover':
            result = recover_transaction(args)
        elif args.operation == 'snapshot':
            require(args.device and args.output, 'snapshot requires --device and a new private --output file')
            device = selected(args.device, 'application')
            with device_lock(args.device):
                snapshot = public_snapshot(device)
                admit_snapshot(snapshot)
                require(not args.output.exists() and not args.output.is_symlink(), 'Snapshot output already exists')
                args.output.write_text(json.dumps(snapshot, indent=2) + '\n')
                args.output.chmod(0o600)
            result = {'stage': 'preflight', 'serial': args.device, 'snapshot': str(args.output),
                      'next': 'Diagnostic snapshot only. An upgrade takes a fresh snapshot and guarded maintenance itself.'}
        else:
            client = Https()
            if args.local_build:
                require(not args.bundle and args.build_dir, 'Local build needs a new --build-dir and no --bundle')
                files, manifest, image = build_local(args)
            elif args.local_bundle:
                require(not args.bundle, 'Choose only one bundle source')
                files = read_bundle(args.local_bundle)
                manifest, image = verify_local(files)
            elif args.bundle:
                files = {}
                for p in args.bundle.iterdir():
                    require(p.is_file() and not p.is_symlink() and p.stat().st_size <= MAX_DOWNLOAD,
                            'Unsafe offline bundle member')
                    files[p.name] = p.read_bytes()
                manifest, image = verify_bundle(files, args.branch)
            else:
                files, manifest, image = resolve(client, args.branch, args.version, args.stable)
            result = {'stage': 'planned', 'branch': args.branch, 'version': manifest['firmware_version'],
                      'source': manifest['source']['revision'], 'workflow': manifest['workflow'],
                      'uf2': candidate_asset(files, manifest),
                      'source_kind': 'local-development' if 'local-build.json' in files else 'canonical-ci',
                      'preserves': 'all reserved flash bytes; public saved state after boot',
                      'requires': 'Pico 2 W, manual BOOTSEL for initial install/recovery, USB-enabled picotool 2.3.0'}
            if not (args.bundle or args.local_build or args.local_bundle or args.stable):
                result['recent_ci'] = recent_ci(client, args.branch, manifest)
            if args.operation == 'plan' and args.output:
                args.output.mkdir(mode=0o700, exist_ok=False)
                for name, data in files.items():
                    (args.output / name).write_bytes(data)
                result['bundle'] = str(args.output)
            if args.operation in ('install', 'upgrade'):
                require(args.device and args.yes, 'Programming requires explicit --device, operation and --yes')
                result = transaction(args, files, manifest, image, client)
        print(json.dumps({**result, 'schema': 'wsprrypico-usb-result/1',
                          'installer_version': INSTALLER_VERSION, 'ok': True}, sort_keys=True))
        return 0
    except TransactionFailure as error:
        print(json.dumps({**error.result, 'schema': 'wsprrypico-usb-result/1',
                          'installer_version': INSTALLER_VERSION, 'ok': False,
                          'error': str(error), **error.details}, sort_keys=True))
        return 3 if error.result['recovery_required'] else 2
    except (Refusal, OSError, KeyError, TypeError, subprocess.SubprocessError, ValueError) as error:
        print(json.dumps({'schema': 'wsprrypico-usb-result/1', 'installer_version': INSTALLER_VERSION,
                          'ok': False, 'error': str(error), 'recovery_required': False,
                          **getattr(error, 'details', {})}, sort_keys=True))
        return 2
    except KeyboardInterrupt:
        print(json.dumps({'schema': 'wsprrypico-usb-result/1', 'ok': False,
                          'error': 'Cancelled; inspect the private transaction before retrying. BOOTSEL recovery may be required.'}))
        return 130


if __name__ == '__main__':
    sys.exit(main())
