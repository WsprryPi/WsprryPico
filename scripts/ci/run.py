#!/usr/bin/env python3
"""Hardware-free CI recipe; all firmware comes from a clean committed checkout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/ci'))
import bundle


def capture(*args):
    return subprocess.check_output(list(map(str, args)), cwd=ROOT, text=True).strip()


def execute(log, *args, cwd=ROOT):
    print('+', ' '.join(map(str, args)), flush=True)
    with log.open('a') as output:
        output.write('+ ' + ' '.join(map(str, args)) + '\n')
        output.flush()
        result = subprocess.run(list(map(str, args)), cwd=cwd, stdout=output,
                                stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        print(log.read_text()[-24000:], flush=True)
        raise RuntimeError(f'Command failed ({result.returncode}); see {log.name}')


def inputs():
    profile = os.environ.get('CI_PROFILE', 'consumer')
    if profile != 'consumer':
        raise ValueError('Unsupported profile')
    stream = bundle.build_stream(os.environ.get('GITHUB_EVENT_NAME'), os.environ.get('GITHUB_REF'))
    if os.environ.get('CI_STREAM') != stream:
        raise ValueError('Artifact stream differs from the actual event/branch')
    run_id, attempt = os.environ.get('GITHUB_RUN_ID', ''), os.environ.get('GITHUB_RUN_ATTEMPT', '')
    if not re.fullmatch(r'[1-9][0-9]{0,19}', run_id) or not re.fullmatch(r'[1-9][0-9]{0,5}', attempt):
        raise ValueError('A real GitHub run/attempt is required')
    if os.environ.get('CI_VERSION'):
        raise ValueError('Firmware identity is generated uniquely per run/attempt; overrides are unsupported')
    tagged = stream == 'release'
    version = (os.environ['GITHUB_REF'].removeprefix('refs/tags/v') if tagged else
               os.environ.get('CI_TESTING_VERSION', '') or f'0.1.0-ci.{run_id}.{attempt}')
    if os.environ.get('CI_TESTING_VERSION'):
        bundle.require(bundle.is_testing_version(version) and
                       os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch' and
                       os.environ.get('GITHUB_REF') == 'refs/heads/devel',
                       'Testing versions require a manual devel dispatch and 0.1.0-testing.N')
    bundle.firmware_channel(version, dict(event=os.environ['GITHUB_EVENT_NAME'],
                            ref=os.environ['GITHUB_REF'], run_id=int(run_id), attempt=int(attempt)))
    publish = os.environ.get('CI_PUBLISH', 'false')
    latest = os.environ.get('CI_MAKE_LATEST', 'false')
    bundle.require(publish in ('true', 'false') and latest in ('true', 'false') and
                   (publish == 'false' or os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch') and
                   (latest == 'false' or publish == 'true' and bundle.version_kind(version) == 'stable'),
                   'Publication/latest selection requires explicit manual authorization and a final version for latest')
    source = capture('git', 'rev-parse', 'HEAD')
    if source != os.environ.get('CI_EVENT_SHA'):
        raise ValueError('Actual checkout differs from workflow event SHA')
    if tagged:
        bundle.require(capture('git', 'rev-parse', os.environ['GITHUB_REF'] + '^{commit}') == source,
                       'Release tag/source mismatch')
        maintained = False
        for branch in ('main', 'devel'):
            ref = 'refs/remotes/origin/' + branch
            if subprocess.run(['git', 'show-ref', '--verify', '--quiet', ref], cwd=ROOT).returncode == 0:
                result = subprocess.run(['git', 'merge-base', '--is-ancestor', source, ref], cwd=ROOT)
                bundle.require(result.returncode in (0, 1), 'Cannot verify release source ancestry')
                maintained |= result.returncode == 0
        bundle.require(maintained, 'Release source must belong to maintained main/devel history')
    if capture('git', 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('Clean tracked and untracked CI input required')
    for name in ('CMakeUserPresets.json', 'pico_config.local.h', 'config/local'):
        if (ROOT / name).exists():
            raise ValueError('Local override or credential input: ' + name)
    if os.environ.get('GITHUB_REPOSITORY') != 'WsprryPi/WsprryPico':
        raise ValueError('Unexpected repository')
    selected = ['consumer']
    return source, version, selected


def expected_tests():
    return bundle.required_tests()


def host_checks(deps, audit):
    harness_source = str(deps / 'harness/src')
    sys.path.insert(0, harness_source)
    os.environ['PYTHONPATH'] = harness_source
    import cryptography
    import jsonschema
    import numpy
    import serial
    import ssl
    from wsprrypi_qualification import carrier, cw_defaults, wtp_control
    # Import before configure: missing modules must never silently shrink coverage.
    assert all((cryptography, jsonschema, numpy, serial, ssl, carrier, cw_defaults, wtp_control))
    log = audit / 'host.log'
    web = ROOT / 'src/network/bootstrap_web'
    execute(log, 'npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund', cwd=web)
    host = ROOT / 'build/host-debug'
    if host.exists():
        raise ValueError('Fresh host directory required')
    options = {
        'CMAKE_BUILD_TYPE': 'Debug', 'WSPRRY_PICO_BUILD_TESTS': 'ON',
        'WSPRRY_PICO_BUILD_FIRMWARE': 'OFF',
        'WSPRRY_PICO_TEST_MBEDTLS_PATH': deps / 'sdk/lib/mbedtls',
        'WSPRRY_PICO_TEST_LWIP_PATH': deps / 'sdk/lib/lwip',
        'WSPRRY_PICO_TEST_CYW43_PATH': deps / 'sdk/lib/cyw43-driver',
        'WSPRRY_PICO_TEST_TINYUSB_PATH': deps / 'sdk/lib/tinyusb',
        'WSPRRY_PICO_BTSTACK_TEST_ROOT': deps / 'sdk/lib/btstack',
        'WSPRRY_PICO_WSPRRYPI_SOURCE': deps / 'companion',
        'WSPRRY_PICO_NETWORK_CLIENT_SOURCE': deps / 'companion',
        'WSPRRY_PICO_HARNESS_PYTHON': sys.executable,
    }
    execute(log, 'cmake', '-S', ROOT, '-B', host, '-G', 'Ninja',
            *(f'-D{k}={v}' for k, v in options.items()))
    registered = json.loads(capture('ctest', '--test-dir', host, '--show-only=json-v1'))
    names = {test['name'] for test in registered['tests']}
    missing = expected_tests() - names
    if missing:
        raise ValueError('Required tests not registered: ' + ', '.join(sorted(missing)))
    (audit / 'registered-tests.json').write_text(json.dumps(registered, indent=2) + '\n')
    execute(log, 'cmake', '--build', host, '--parallel', '4')
    execute(log, 'ctest', '--test-dir', host, '--output-on-failure', '--timeout', '240',
            '--output-junit', audit / 'host-tests.xml')
    suite = ET.parse(audit / 'host-tests.xml').getroot()
    cases = suite.findall('testcase')
    if (len(cases) != len(names) or any(case.find('skipped') is not None or
            case.find('failure') is not None or case.find('error') is not None for case in cases)):
        raise ValueError('Incomplete, skipped or failed required CTest suite')
    # CTest does not expose unittest's internal skips as skipped CTest cases.
    internal_skips = [case.attrib['name'] for case in cases
                      if re.search(r'\bskipped=\d+', ''.join(case.itertext()))]
    if internal_skips:
        raise ValueError('Internally skipped required suite: ' + ', '.join(internal_skips))
    (audit / 'evidence-skips.json').write_text('[]\n')
    execute(log, sys.executable, ROOT / 'scripts/validate_wtp_contract.py')
    execute(log, 'npm', 'test', cwd=web)
    execute(log, sys.executable, ROOT / 'tests/ci_bundle_tests.py')
    execute(log, 'node', '--test', ROOT / 'tests/ui_process_cleanup.test.mjs')
    chrome = shutil.which('google-chrome')
    if not chrome:
        raise ValueError('Runner Chrome is required for the consumer frequency UI check')
    os.environ['CHROME_BIN'] = chrome
    execute(log, 'node', ROOT / 'tests/standalone_frequency_ui_integration.mjs',
            host / 'consumer_bootstrap_driver', audit / 'consumer-ui')
    return {'registered': len(names), 'passed': len(cases), 'failed': 0, 'skipped': 0,
            'test_names': sorted(names), 'wtp_contract': 'passed', 'browser_npm': 'passed',
            'packaging_failure_tests': 'passed', 'consumer_ui': 'passed',
            'historical_evidence_skips': json.loads((audit / 'evidence-skips.json').read_text())}


def firmware(deps, audit, identifier, version):
    profile = bundle.PROFILES[identifier]
    target = profile['target']
    build = ROOT / ('build/ci-' + identifier)
    if build.exists():
        raise ValueError('Fresh firmware build directory required')
    log = audit / (identifier + '.log')
    execute(log, 'cmake', '-S', ROOT, '-B', build, '-G', 'Ninja',
            '-DCMAKE_BUILD_TYPE=Release', '-DWSPRRY_PICO_BUILD_FIRMWARE=ON',
            '-DWSPRRY_PICO_BUILD_TESTS=OFF', '-DPICO_BOARD=pico2_w',
            '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', '-DPICOTOOL_NO_LIBUSB=1',
            f'-DPICOTOOL_GIT_REPOSITORY_URL={deps / "picotool"}',
            f'-DWSPRRY_PICO_FIRMWARE_VERSION={version}')
    execute(log, 'cmake', '--build', build, '--target', target, '--parallel', '4')
    directory = audit / identifier
    directory.mkdir()
    for suffix in ('.elf', '.elf.map', '.uf2'):
        shutil.copyfile(build / 'firmware' / (target + suffix), directory / (target + suffix))
    shutil.copyfile(build / 'firmware/generated/firmware_identity.hpp', directory / 'firmware_identity.hpp')
    shutil.copyfile(build / 'compile_commands.json', directory / 'compile_commands.json')
    shutil.copyfile(build / 'CMakeCache.txt', directory / 'CMakeCache.txt')
    overlays = {}
    for subdir in ('cyw43-tx-overlay', 'mbedtls-alert-overlay', 'btstack-pool-overlay'):
        path = build / subdir
        if path.exists():
            for item in sorted(path.rglob('*')):
                if item.is_file():
                    overlays[str(item.relative_to(build))] = bundle.sha(item)
                    retained = directory / 'overlays' / item.relative_to(build)
                    retained.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(item, retained)
    if identifier == 'consumer' and set(overlays) != bundle.CONSUMER_OVERLAYS:
        raise ValueError('Required consumer overlays missing from fresh build')
    picotool = list(build.glob('_deps/picotool-build/picotool'))
    if len(picotool) != 1:
        raise ValueError('Pinned built picotool missing')
    identity = capture(picotool[0], 'info', '-a', directory / (target + '.elf'))
    (directory / 'picotool-info.txt').write_text(identity + '\n')
    os.environ['PATH'] = str(picotool[0].parent) + os.pathsep + os.environ['PATH']
    bundle.inspect_profile(directory, identifier, version, capture('git', 'rev-parse', 'HEAD'), picotool[0])
    return directory, overlays


def licenses(deps, destination):
    sources = [(ROOT, [ROOT / 'LICENSE.md', ROOT / 'THIRD_PARTY_NOTICES.md',
                      ROOT / 'src/encoding/WsprryPi-LICENSE.md', *(ROOT / 'engineering/licenses').glob('*.txt')])]
    for name in ('sdk', 'arm-gnu-toolchain-15.3.rel1-x86_64-arm-none-eabi'):
        base = deps / name
        paths = [p for p in base.rglob('*') if p.is_file() and '.git' not in p.parts
                 and re.match(r'(?i)^(LICENSE|COPYING|NOTICE)([._-].*|\d*)?$', p.name)]
        sources.append((base, paths))
    sections = []
    for base, paths in sources:
        for path in sorted(paths):
            if path.stat().st_size > 1024 * 1024:
                raise ValueError('Unexpected license material size')
            label = ('project' if base == ROOT else base.name) + '/' + str(path.relative_to(base))
            sections.append(f'===== {label} (SHA-256 {bundle.sha(path)}) =====\n' +
                            path.read_text(errors='strict') + '\n')
    for relative, count in (
            ('lib/btstack/3rd-party/rijndael/rijndael.c', 4),
            ('lib/btstack/3rd-party/rijndael/rijndael.h', 4),
            ('lib/cyw43-driver/firmware/wifi_nvram_43439.h', 3),
            ('src/rp2_common/pico_rand/rand.c', 25)):
        path = deps / 'sdk' / relative
        sections.append(f'===== sdk/{relative} attribution header (source SHA-256 {bundle.sha(path)}) =====\n' +
                        '\n'.join(path.read_text().splitlines()[:count]) + '\n')
    if len(sections) < 15:
        raise ValueError('Dependency license inventory incomplete')
    destination.write_text('\n'.join(sections))


def build(deps, output):
    source, version, selected = inputs()
    deps = deps.resolve(strict=True)
    output.mkdir(parents=True, exist_ok=False)
    audit, deployment = output / 'audit', output / 'deployment'
    audit.mkdir()
    deployment.mkdir()
    os.environ['PICO_SDK_PATH'] = str(deps / 'sdk')
    os.environ['PATH'] = str(deps / 'arm-gnu-toolchain-15.3.rel1-x86_64-arm-none-eabi/bin') + os.pathsep + os.environ['PATH']
    checks = host_checks(deps, audit)
    images, overlays = {}, {}
    for identifier in selected:
        images[identifier], overlays[identifier] = firmware(deps, audit, identifier, version)
    # Compatibility shares application wiring, but is never a deployment asset.
    _, overlays['inhibited-regression'] = firmware(deps, audit, 'inhibited-regression', version)
    (audit / 'inhibited-regression/WsprryPico-Inhibited.uf2').unlink()
    checks['inhibited_regression'] = 'passed'
    if 'consumer' in selected:
        execute(audit / 'compatibility.log', 'cmake', '--build', ROOT / 'build/ci-consumer',
                '--target', 'WsprryPico-StandaloneRF', '--parallel', '4')
        checks['compatibility_rf'] = 'passed'
        # Independent fresh directory with identical declared inputs and identity.
        original = ROOT / 'build/ci-consumer'
        fresh = ROOT / 'build/ci-reproducibility'
        execute(audit / 'reproducibility.log', 'cmake', '-S', ROOT, '-B', fresh, '-G', 'Ninja',
                '-DCMAKE_BUILD_TYPE=Release', '-DWSPRRY_PICO_BUILD_FIRMWARE=ON',
                '-DWSPRRY_PICO_BUILD_TESTS=OFF', '-DPICO_BOARD=pico2_w', '-DPICOTOOL_NO_LIBUSB=1',
                f'-DPICOTOOL_GIT_REPOSITORY_URL={deps / "picotool"}',
                f'-DWSPRRY_PICO_FIRMWARE_VERSION={version}')
        execute(audit / 'reproducibility.log', 'cmake', '--build', fresh,
                '--target', 'WsprryPico', '--parallel', '4')
        checks['reproducibility'] = 'identical' if bundle.sha(original / 'firmware/WsprryPico.uf2') == bundle.sha(fresh / 'firmware/WsprryPico.uf2') else 'different'
        if checks['reproducibility'] != 'identical':
            raise ValueError('Two fresh consumer builds differ; investigate before distribution')
    else:
        checks.update(compatibility_rf='not-selected', reproducibility='not-selected')
    licenses(deps, deployment / 'DEPENDENCY-LICENSES.txt')
    for name in ('LICENSE.md', 'THIRD_PARTY_NOTICES.md'):
        shutil.copyfile(ROOT / name, deployment / name)
    environment = {name: os.environ.get(name, '') for name in
                   ('ImageOS', 'ImageVersion', 'RUNNER_OS', 'RUNNER_ARCH')}
    environment['versions'] = {tool: capture(*args) for tool, args in {
        'cmake': ('cmake', '--version'), 'ninja': ('ninja', '--version'),
        'host_cxx': ('c++', '--version'), 'python': (sys.executable, '--version'),
        'node': ('node', '--version'), 'openssl': ('openssl', 'version'),
        'pip': (sys.executable, '-m', 'pip', 'freeze'),
        'system_packages': ('dpkg-query', '-W', 'libssl-dev', 'gcc', 'g++'),
        'chrome': (os.environ['CHROME_BIN'], '--version')}.items()}
    build_inputs = json.loads((deps / 'verified-inputs.json').read_text())
    build_inputs.update(environment=environment, overlays=overlays,
                        python_lock_sha256=bundle.sha(ROOT / 'scripts/ci/requirements.txt'),
                        npm_lock_sha256=bundle.sha(ROOT / 'src/network/bootstrap_web/package-lock.json'))
    build_inputs['linked_resources'] = {
        name: bundle.sha(deps / 'sdk/lib/cyw43-driver/firmware' / name)
        for name in ('wb43439A0_7_95_49_00_combined.h', 'wifi_nvram_43439.h', 'cyw43_btfw_43439.h')}
    bundle.create(deployment, audit, source, version, selected, checks, build_inputs)
    bundle.verify(deployment, audit, source, version)
    print(json.dumps({'source': source, 'version': version, 'profiles': selected,
                      'deployment': str(deployment), 'checks': checks}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inputs', 'build'))
    parser.add_argument('--dependencies', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.action == 'inputs':
        print(inputs())
    elif args.dependencies and args.output:
        build(args.dependencies, args.output)
    else:
        parser.error('build requires --dependencies and --output')


if __name__ == '__main__':
    main()
