#!/usr/bin/env python3
"""Canonical firmware bundle creation and independent post-download verification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_application_image import validate as validate_engine
from check_standalone_image import validate_uf2
from firmware_payload import verify_payload
from usb_installer import MAX_VERSION, SEMVER, firmware_channel, version_kind

PROFILES = {
    'consumer': {'target': 'WsprryPico', 'engine': 'pio-dma', 'role': 'uninhibited'},
    'inhibited-regression': {'target': 'WsprryPico-Inhibited', 'engine': 'simulator', 'role': 'inhibited'},
}
APPLICATION_END = 0x103ee000
SUPPORTED_APPLICATION_ENDS = {APPLICATION_END, 0x103f0000}
MAX_FILE = 64 * 1024 * 1024
SCHEMA = Path(__file__).with_name('release-manifest-1.schema.json')
CONSUMER_OVERLAYS = {'cyw43-tx-overlay/cyw43_ll.c',
                     'mbedtls-alert-overlay/ssl_msg.c', 'mbedtls-alert-overlay/ssl_tls13_generic.c',
                     'mbedtls-alert-overlay/ssl_tls.c'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def is_testing_version(version):
    return isinstance(version, str) and re.fullmatch(r'0\.1\.0-testing\.[1-9][0-9]{0,5}', version) is not None


def testing_metadata(source):
    """Release-only metadata; ordinary CI bundles retain their installer contract."""
    base = 'https://github.com/WsprryPi/WsprryPico/blob/' + source + '/'
    return {
        'prerelease': True, 'installer_default_eligible': False,
        'gpio_drive_ma': {'choices': [2, 4, 8, 12], 'default': 4},
        'protocols': ['WTP/1', 'USB-Management/1', 'Consumer-Radio/1', 'Field-GATT/1'],
        'api': ['transmitter-application/3', 'transmitter-hardware/2',
                'transmitter-progress/2', 'transmitter-gpio-drive/1'],
        'storage': {'configuration': 1, 'saved_progress_read': [1, 2, 3],
                    'layout': '72 KiB reserved; application ends at 0x103ee000; E10 is SDK workaround only',
                    'policy': 'Preserving update; no whole-flash erase. Downgrade preservation unqualified.'},
        'companion': {'software_tested_revision': read_json(ROOT / 'scripts/ci/inputs.json')['companion'],
                      'historical_drive_acceptance_pico': 'd6de1f3cf14dc49266c4401c3bca91b8ce9da688',
                      'historical_drive_acceptance_pi': 'fe701cf4c2b05e46cb84927188984084503d1cea',
                      'physical_release_pair_tested': False},
        'recipe': ['Confirm remote devel equals source.revision; dispatch that frozen source with: '
                   'gh workflow run software-build.yml --repo WsprryPi/WsprryPico --ref devel '
                   '-f profile=consumer -f testing_version=<firmware_version>',
                   'The following commands run inside that GitHub workflow, which supplies GITHUB_* '
                   'run/source/event context, CI_WORKFLOW_SHA, CI_EVENT_SHA, CI_STREAM=devel, '
                   'CI_PROFILE=consumer and CI_TESTING_VERSION=<firmware_version>. '
                   'DEPENDENCIES and OUTPUT denote fresh private task directories; '
                   'consumer.log retains the resolved CMake configure/build commands.',
                   'python -m pip install --require-hashes --only-binary=:all: -r scripts/ci/requirements.txt',
                   'python scripts/ci/setup.py "$DEPENDENCIES"',
                   'python scripts/ci/run.py build --dependencies "$DEPENDENCIES" --output "$OUTPUT"',
                   'Ninja; Release; WSPRRY_PICO_BUILD_FIRMWARE=ON; WSPRRY_PICO_BUILD_TESTS=OFF; '
                   'PICO_BOARD=pico2_w; WSPRRY_PICO_FIRMWARE_VERSION=<firmware_version>; '
                   'PICOTOOL_NO_LIBUSB=1; PICOTOOL_GIT_REPOSITORY_URL=<verified dependencies>/picotool; '
                   'PICO_SDK_PATH=<verified dependencies>/sdk; four build jobs'],
        'references': [base + path for path in (
            'engineering/development/gpio-drive.md', 'engineering/protocol/USB-Management.md',
            'src/standalone/pico/flash_layout.hpp', 'src/standalone/progress.cpp',
            'engineering/development/short-wspr-type23-decode-results.md',
            'engineering/development/band-support.md', 'LICENSE.md', 'THIRD_PARTY_NOTICES.md')],
    }


def build_stream(event, ref):
    if event in ('push', 'workflow_dispatch') and ref in ('refs/heads/devel', 'refs/heads/main'):
        return ref.removeprefix('refs/heads/')
    if event == 'pull_request' and isinstance(ref, str) and re.fullmatch(r'refs/pull/[1-9][0-9]*/merge', ref):
        return 'pull-request'
    if event in ('push', 'workflow_dispatch') and isinstance(ref, str) and ref.startswith('refs/tags/v'):
        require(version_kind(ref.removeprefix('refs/tags/v')) in ('prerelease', 'stable'),
                'CI/testing versions require their original branch workflow')
        return 'release'
    raise ValueError('Unsupported CI event or branch')


def artifact_name(kind, stream, run, attempt):
    require(kind in ('firmware', 'audit') and stream in ('devel', 'main', 'pull-request', 'release'),
            'Unsupported artifact stream')
    return f'WsprryPico-{kind}-{stream}-{run}-{attempt}-consumer'


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'Duplicate JSON member')
        value[key] = item
    return value


def read_json(path, limit=2 * 1024 * 1024):
    require(not path.is_symlink() and path.stat().st_size <= limit, 'Unsafe or oversized JSON')
    return json.loads(path.read_text(), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def descriptor(path, root):
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= MAX_FILE,
            'Invalid artifact file')
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def safe_file(root, record):
    name = record['path']
    require(isinstance(name, str) and len(name) <= 200 and
            re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/+-]*', name) and
            not any(part in ('', '.', '..') for part in name.split('/')), 'Unsafe asset path')
    path = root / name
    require(path.resolve().is_relative_to(root.resolve()), 'Asset escapes bundle')
    for parent in (path, *path.parents):
        if parent == root:
            break
        require(not parent.is_symlink(), 'Symlink asset')
    require(path.is_file() and type(record['bytes']) is int and
            0 < record['bytes'] <= MAX_FILE and path.stat().st_size == record['bytes'], 'Asset size mismatch')
    require(re.fullmatch(r'[0-9a-f]{64}', record['sha256']) and sha(path) == record['sha256'], 'Asset SHA-256 mismatch')
    return path


def inventory(root, records, extra=()):
    names = [record['path'] for record in records]
    require(len(set(names)) == len(names), 'Duplicate asset')
    actual = set()
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'Symlink in bundle')
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    require(actual == set(names) | set(extra), 'Missing or extra bundle files')
    return {record['path']: safe_file(root, record) for record in records}


def capture(*args):
    return subprocess.check_output(list(map(str, args)), text=True).strip()


def required_tests(source=None):
    source = source or capture('git', '-C', ROOT, 'rev-parse', 'HEAD')
    require(re.fullmatch('[0-9a-f]{40}', source), 'Full frozen source revision required')
    paths = capture('git', '-C', ROOT, 'ls-tree', '-r', '--name-only', source, 'cmake').splitlines()
    files = ['CMakeLists.txt', *(path for path in paths if path.endswith('host_tests.cmake')),
             'cmake/host_client_interop.cmake', 'cmake/network_client_interop.cmake']
    expected = set()
    for path in files:
        text = capture('git', '-C', ROOT, 'show', source + ':' + path)
        expected.update(re.findall(r'add_test\(\s*NAME\s+([a-zA-Z0-9_]+)\s', text))
    loop = re.search(r'foreach\(phase12_python_test IN ITEMS(.*?)\)',
                     capture('git', '-C', ROOT, 'show', source + ':CMakeLists.txt'), re.S)
    if loop:  # Frozen earlier artifacts used a generated campaign-test registration.
        expected.update(name + '_tests' for name in loop[1].split())
    return expected


def binary_identity(report):
    fields = {}
    section = ''
    for line in report.splitlines():
        if line and not line[0].isspace():
            section = line
        if section not in ('Program Information', 'Build Information'):
            continue
        match = re.fullmatch(r'\s+(name|version|description|target chip|image type|sdk version|pico_board|build attributes):\s+(.+?)\s*', line)
        if match:
            require(match[1] not in fields, 'Duplicate picotool identity field')
            fields[match[1]] = match[2]
    return fields


def source_application_end(source):
    require(re.fullmatch('[0-9a-f]{40}', source), 'Full frozen source revision required')
    text = capture('git', '-C', ROOT, 'show', source + ':cmake/standalone_link/memory_flash.incl')
    match = re.search(r'FLASH\(rx\)\s*:\s*ORIGIN\s*=\s*0x10000000,\s*LENGTH\s*=\s*(0x[0-9a-fA-F]+)', text)
    require(match, 'Frozen source flash reservation missing')
    end = 0x10000000 + int(match[1], 16)
    require(end in SUPPORTED_APPLICATION_ENDS, 'Unsupported source flash reservation')
    return end


def inspect_payload(directory, identifier, application_end=APPLICATION_END):
    require(application_end in SUPPORTED_APPLICATION_ENDS, 'Unsupported flash reservation')
    target = PROFILES[identifier]['target']
    elf, uf2 = directory / (target + '.elf'), directory / (target + '.uf2')
    require(elf.stat().st_size <= MAX_FILE and uf2.stat().st_size <= 9 * 1024 * 1024,
            'Oversized image')
    elf_bytes, uf2_bytes = elf.read_bytes(), uf2.read_bytes()
    validate_uf2(uf2_bytes, application_end=application_end)
    verify_payload(elf_bytes, uf2_bytes, application_end=application_end)
    for offset in range(0, len(uf2_bytes), 512):
        if struct.unpack_from('<I', uf2_bytes, offset + 12)[0] == 0x10ffff00:
            expected_e10 = (struct.pack('<8I', 0x0a324655, 0x9e5d5157, 0xa000,
                                        0x10ffff00, 256, 0, 2, 0xe48bff57) +
                            bytes([0xef]) * 256 + struct.pack('<I', 0x9957e304) +
                            bytes(216) + struct.pack('<I', 0x0ab16f30))
            require(uf2_bytes[offset:offset + 512] == expected_e10, 'Unexpected E10 block metadata')


def inspect_profile(directory, identifier, version, source, picotool='picotool', application_end=None):
    profile = PROFILES[identifier]
    target = profile['target']
    require(re.match(r'^picotool v2\.3\.0(?: |$)', capture(picotool, 'version')),
            'picotool v2.3.0 is required for linked identity inspection')
    elf, uf2 = directory / (target + '.elf'), directory / (target + '.uf2')
    require(elf.stat().st_size <= MAX_FILE and uf2.stat().st_size <= 9 * 1024 * 1024,
            'Oversized image')
    elf_bytes, uf2_bytes = elf.read_bytes(), uf2.read_bytes()
    expected_binary_identity = {
        'name': target, 'version': version,
        'description': ('Standalone PIO/DMA RF ' if identifier == 'consumer' else
                        'Standalone RF-inhibited ') + source[:12],
        'target chip': 'RP2350', 'image type': 'ARM Secure',
        'sdk version': '2.3.1', 'pico_board': 'pico2_w', 'build attributes': 'Release'}
    actual_identity = binary_identity(capture(picotool, 'info', '-a', elf))
    require(actual_identity == expected_binary_identity, 'Linked picotool program identity mismatch')
    require(binary_identity((directory / 'picotool-info.txt').read_text()) == actual_identity,
            'Retained picotool report differs from linked image')
    application_end = source_application_end(source) if application_end is None else application_end
    require(application_end in SUPPORTED_APPLICATION_ENDS, 'Unsupported flash reservation')
    inspect_payload(directory, identifier, application_end)
    header = (directory / 'firmware_identity.hpp').read_text()
    expected = {'kProduct': 'WsprryPico', 'kFirmwareVersion': version,
                'kBuildRevision': source[:12], 'kBoard': 'pico2_w', 'kProcessor': 'RP2350',
                'kPicoSdkVersion': '2.3.1',
                'kPicoSdkCommit': '079c6f39023649b154152db30f1d781e884879bc',
                'kArmToolchainVersion': '15.3.1'}
    for key, value in expected.items():
        require(f'char {key}[] = "{value}";' in header, 'Generated identity mismatch: ' + key)
    for value in ('WsprryPico', version, source[:12], 'pico2_w'):
        require((value + '\0').encode() in elf_bytes, 'Identity missing from linked ELF')
    require(not re.search(rb'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----\r?\n[A-Za-z0-9+/=\r\n]{64,}', elf_bytes) and b'/Users/' not in elf_bytes,
            'Private build data in image')
    symbols = capture('arm-none-eabi-nm', '-C', elf)
    validate_engine(symbols, 'rf' if identifier == 'consumer' else 'inhibited')
    map_text = (directory / (target + '.elf.map')).read_text()
    require(re.search(rf'^FLASH\s+0x10000000\s+0x{application_end-0x10000000:08x}\s+xr$', map_text, re.M), 'Wrong current flash reservation')
    commands = read_json(directory / 'compile_commands.json', limit=MAX_FILE)
    selected = [item for item in commands if f'CMakeFiles/{target}.dir/' in item.get('command', '')]
    require(selected, 'Target compile evidence absent')
    for item in commands:
        command = item.get('command', '')
        require('WSPRRY_PICO_STANDALONE_WSPR_BASE_FREQUENCY_HZ' not in command,
                'Band-specific build input is forbidden')
        linked_owned = item in selected or re.search(r'CMakeFiles/wsprrypico_(?:core|rf|pico_rf)\.dir/', command)
        if linked_owned:
            require(not re.search(r'-DWSPRRY_PICO_\w*(?:FIXTURE|FAULT|RF_BENCH|RF_WTP|ACCEPTANCE|DIAGNOSTIC|PROVISIONED)\w*(?:=1|\s)', command),
                    'Fixture or provisioned compile input')
    for item in selected:
        flags = set(shlex.split(item['command']))
        require('-DWSPRRY_PICO_RF_SAMPLE_RATE_HZ=138000000' in flags, 'Wrong application clock')
        require('-DWSPRRY_PICO_CONSUMER_LAN_MODE=1' in flags, 'Wrong consumer LAN profile')
        require('-DCYW43_ENABLE_BLUETOOTH=1' in flags, 'Wrong linked CYW43 firmware selection')
        if identifier == 'consumer':
            require('-DWSPRRY_PICO_STANDALONE_RF=1' in flags and
                    '-DWSPRRY_PICO_RF_OUTPUT_DISABLED=1' not in flags, 'Wrong application role')
        else:
            require('-DWSPRRY_PICO_RF_OUTPUT_DISABLED=1' in flags, 'Wrong diagnostic role')
    cache = (directory / 'CMakeCache.txt').read_text()
    require(not re.search(r'^WSPRRY_PICO_.*(?:CREDENTIAL|PROVISIONED).*=[^\n]+$', cache, re.M),
            'Credential build input')
    require('WSPRRY_PICO_STANDALONE_WSPR_BASE_FREQUENCY_HZ:' not in cache, 'Removed build override present')
    for checker, args in (
            ('check_standalone_image.py', []), ('check_btstack_pool_hooks.py', []),
            ('check_heap_hooks.py', []),
            ('check_stack_guards.py', ['--physical'] if identifier == 'consumer' else []),
            ('check_gp14_rf_image.py', []) if identifier == 'consumer' else ('check_bootsel_topology.py', [])):
        subprocess.run([sys.executable, str(ROOT / 'scripts' / checker), str(elf), *args], check=True)
    if identifier == 'consumer':
        subprocess.run([sys.executable, str(ROOT / 'scripts/check_rf_renderer.py'), str(elf), '--expect', 'ram'], check=True)
    return {'identity': expected, 'engine': profile['engine'], 'clock_hz': 138000000,
            'frequency_selected_by_image': None}


def create(deployment, audit, source, version, selected, checks, build_inputs):
    require(selected == ['consumer'], 'Only the generic consumer image may be deployed')
    basename = f'WsprryPico-{version}-pico2_w.uf2'
    shutil.copyfile(audit / 'consumer/WsprryPico.uf2', deployment / basename)
    (audit / 'build-inputs.json').write_text(json.dumps(build_inputs, indent=2) + '\n')
    source_inventory = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', source])
    event, ref = os.environ['GITHUB_EVENT_NAME'], os.environ['GITHUB_REF']
    stream = build_stream(event, ref)
    workflow = {'path': '.github/workflows/software-build.yml',
                'revision': os.environ['CI_WORKFLOW_SHA'], 'event': event, 'ref': ref,
                'run_id': int(os.environ['GITHUB_RUN_ID']), 'attempt': int(os.environ['GITHUB_RUN_ATTEMPT']),
                'url': f'https://github.com/WsprryPi/WsprryPico/actions/runs/{os.environ["GITHUB_RUN_ID"]}'}
    actual_stream, channel, eligible = firmware_channel(version, workflow)
    require(stream == actual_stream, 'Version/workflow stream mismatch')
    manifest = {
        'schema_version': 1, 'product': 'WsprryPico', 'firmware_version': version,
        'intended_tag': 'v' + version, 'channel': channel,
        'repository': 'https://github.com/WsprryPi/WsprryPico',
        'source': {'revision': source, 'tree': capture('git', '-C', ROOT, 'rev-parse', source + '^{tree}'),
                   'clean': True, 'input_digest_sha256': hashlib.sha256(source_inventory).hexdigest()},
        'workflow': workflow,
        'deployment_candidate': eligible,
        'firmware': {'profile': 'consumer', 'target': 'WsprryPico', 'board': 'pico2_w',
                     'processor': 'RP2350', 'family_id': 'e48bff59', 'role': 'uninhibited',
                     'engine': 'pio-dma', 'clock_hz': 138000000,
                     'frequency_selected_by_image': None, 'station_selected_by_image': False,
                     'credentials_in_image': False, 'schedules_enabled_by_image': False},
        'checks': checks, 'build_inputs': build_inputs,
        'assets': [descriptor(path, deployment) for path in sorted(deployment.iterdir())],
        'audit_assets': [descriptor(path, audit) for path in sorted(audit.rglob('*')) if path.is_file()],
        'update': {'application_end': f'{APPLICATION_END:x}', 'ordinary_update_erases_settings': False,
                   'usb_maintenance': 1, 'postboot_verification': 1,
                   'whole_flash_erase_required': False,
                   'unset_frequency_transmits': False, 'first_frequency_save_enables_schedule': False,
                   'rollback': 'Older firmware may reject extended saved configuration; downgrade preservation is unqualified.'},
        'qualification': {'software_build_only': True, 'physical_boot_usb_rf_timing': 'not assessed by this run'},
        'licenses': ['LICENSE.md', 'THIRD_PARTY_NOTICES.md', 'DEPENDENCY-LICENSES.txt'],
    }
    if is_testing_version(version):
        require(event == 'workflow_dispatch' and ref == 'refs/heads/devel',
                'Testing candidate must come from a manual devel dispatch')
        manifest['testing_release'] = testing_metadata(source)
    path = deployment / 'release-manifest.json'
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    (deployment / 'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(deployment.iterdir())))


def verify(deployment, audit, source, version, inspect=True):
    from jsonschema import Draft202012Validator
    deployment, audit = deployment.resolve(), audit.resolve()
    manifest = read_json(deployment / 'release-manifest.json')
    schema = read_json(SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest)
    require(re.fullmatch(r'[0-9a-f]{40}', source) and manifest['source']['revision'] == source,
            'Source identity mismatch')
    application_end = int(manifest['update']['application_end'], 16)
    require(application_end == source_application_end(source), 'Flash reservation differs from frozen source')
    require(manifest['firmware_version'] == version and manifest['intended_tag'] == 'v' + version,
            'Version identity mismatch')
    require(manifest['source']['tree'] == capture('git', '-C', ROOT, 'rev-parse', source + '^{tree}') and
            manifest['source']['input_digest_sha256'] == hashlib.sha256(subprocess.check_output(
                ['git', '-C', str(ROOT), 'ls-tree', '-r', source])).hexdigest(), 'Source tree/input digest mismatch')
    require(manifest['workflow']['revision'] == source, 'Workflow revision differs from artifact source')
    stream = build_stream(manifest['workflow']['event'], manifest['workflow']['ref'])
    actual_stream, channel, eligible = firmware_channel(version, manifest['workflow'])
    require(actual_stream == stream and manifest['channel'] == channel, 'Version/channel/ref mismatch')
    testing = is_testing_version(version)
    require(manifest['deployment_candidate'] == eligible,
            'Untrusted deployment channel')
    if testing:
        require(manifest['workflow']['event'] == 'workflow_dispatch' and stream == 'devel' and
                manifest.get('testing_release') == testing_metadata(source), 'Testing release metadata mismatch')
    else:
        require('testing_release' not in manifest, 'Unexpected testing release metadata')
    checks = manifest['checks']
    require(checks['registered'] == checks['passed'] == len(checks['test_names']) and
            len(set(checks['test_names'])) == len(checks['test_names']), 'Incomplete test inventory')
    for name in ('wtp_contract', 'browser_npm', 'packaging_failure_tests', 'consumer_ui',
                 'compatibility_rf', 'inhibited_regression'):
        require(checks[name] == 'passed', 'Required check did not pass: ' + name)
    require(checks['failed'] == checks['skipped'] == 0 and checks['reproducibility'] == 'identical',
            'Failed, skipped or nonreproducible build')
    pins = read_json(Path(__file__).with_name('inputs.json'))
    require(manifest['build_inputs']['pins'] == pins and
            manifest['build_inputs']['toolchain_archive_sha256'] == pins['toolchain_sha256'],
            'Dependency pin mismatch')
    assets = inventory(deployment, manifest['assets'], extra=('release-manifest.json', 'SHA256SUMS'))
    basename = f'WsprryPico-{version}-pico2_w.uf2'
    require(set(assets) == {basename, 'LICENSE.md', 'THIRD_PARTY_NOTICES.md', 'DEPENDENCY-LICENSES.txt'},
            'Wrong consumer asset allowlist')
    inventory(audit, manifest['audit_assets'])
    registered = read_json(audit / 'registered-tests.json')
    names = [item['name'] for item in registered['tests']]
    cases = ET.parse(audit / 'host-tests.xml').getroot().findall('testcase')
    actual = [case.attrib['name'] for case in cases]
    require(set(names) == set(actual) == set(checks['test_names']) and
            len(names) == len(set(names)) == len(cases) and required_tests(source) <= set(names),
            'Test reports differ from declared or required inventory')
    require(all(case.find('failure') is None and case.find('error') is None and
                case.find('skipped') is None and case.attrib.get('status', 'run') in ('run', 'passed')
                for case in cases), 'Audit report contains failed or skipped required tests')
    require(read_json(audit / 'evidence-skips.json') == checks['historical_evidence_skips'],
            'Historical skip inventory differs')
    allowed_skips = read_json(Path(__file__).with_name('legacy-test-skip-reasons.json'))
    require(all(item['reason'] in allowed_skips for item in checks['historical_evidence_skips']),
            'Unapproved test prerequisite skip')
    require(sha(assets[basename]) == sha(audit / 'consumer/WsprryPico.uf2'), 'Audit UF2 differs from deployment')
    expected = ''.join(f'{sha(deployment / name)}  {name}\n'
                       for name in sorted([*assets, 'release-manifest.json']))
    require((deployment / 'SHA256SUMS').read_text() == expected, 'SHA256SUMS mismatch')
    # Bind every declared report to the exact audit artifact as well as the manifest.
    require(read_json(audit / 'build-inputs.json') == manifest['build_inputs'], 'Build provenance differs')
    for name, repository in (('sdk', 'https://github.com/raspberrypi/pico-sdk.git'),
                             ('picotool', 'https://github.com/raspberrypi/picotool.git'),
                             ('companion', 'https://github.com/WsprryPi/WsprryPi.git'),
                             ('harness', 'https://github.com/WsprryPi/WsprryPi-Qualification-Harness.git')):
        dependency = manifest['build_inputs'][name]
        require(dependency['revision'] == pins[name] and dependency['repository'] == repository,
                'Wrong dependency source: ' + name)
    actual_submodules = {line.strip().split()[1]: line.strip().split()[0]
                         for line in manifest['build_inputs']['sdk']['submodules']}
    require(all(actual_submodules.get(path) == revision for path, revision in pins['sdk_submodules'].items()),
            'Wrong linked SDK submodule provenance')
    require(manifest['build_inputs']['linked_resources'] == pins['linked_resource_sha256'],
            'Wrong linked firmware resource provenance')
    require(set(manifest['build_inputs']['overlays'].get('consumer', {})) == CONSUMER_OVERLAYS,
            'Required consumer overlay inventory missing')
    for profile, overlays in manifest['build_inputs']['overlays'].items():
        require(profile in PROFILES, 'Unknown overlay profile')
        for path, digest in overlays.items():
            require(re.fullmatch(r'(cyw43-tx-overlay|mbedtls-alert-overlay)/[A-Za-z0-9_.-]+', path) and
                    sha(audit / profile / 'overlays' / path) == digest, 'Generated overlay digest mismatch')
    if inspect:
        inspect_profile(audit / 'consumer', 'consumer', version, source, application_end=application_end)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('deployment', type=Path)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    manifest = verify(args.deployment, args.audit, args.source, args.version)
    print(json.dumps({'verified': True, 'source': args.source, 'version': args.version,
                      'uf2_sha256': next(asset['sha256'] for asset in manifest['assets'] if asset['path'].endswith('.uf2'))}))


if __name__ == '__main__':
    main()
