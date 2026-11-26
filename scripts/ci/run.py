#!/usr/bin/env python3
"""Hardware-free CI recipe; all firmware comes from a clean committed checkout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/ci'))
import bundle
import execution
sys.path.insert(0, str(ROOT / 'scripts'))
from check_control_policy import check_files as check_control_policy


def capture(*args):
    return subprocess.check_output(list(map(str, args)), cwd=ROOT, text=True).strip()


def execute(log, *args, cwd=ROOT, context=None, expected=None):
    command = list(map(str, args))
    print('+', ' '.join(command), flush=True)
    try:
        execution.execute(log, command, cwd, capture('git', 'rev-parse', 'HEAD'), context, expected=expected)
    except BaseException as primary:
        try:
            print(log.read_text()[-24000:], flush=True)
        except OSError as diagnostic:
            raise BaseExceptionGroup('command and diagnostic read failed', [primary, diagnostic]) from None
        raise


def producer_execution_policy():
    policy = bundle.validate_execution_policy(bundle.read_json(ROOT / "scripts/ci/execution-policy.json"))
    bundle.require(policy["schema"] == "ci-execution-policy/2", "Current producer requires current completion policy")
    bundle.require(set(policy['contexts']) == set(execution.HOST_CONTEXTS), 'Incomplete producer execution contexts')
    return policy


DIRECT_COMPILER_OPTIONS = tuple(f'-DCMAKE_{language}_COMPILER_LAUNCHER='
                                for language in ('C', 'CXX'))


def fresh_directory(path):
    if path.exists() or path.is_symlink():
        raise ValueError('Fresh build directory required: ' + str(path))
    return path


def direct_compiler_environment():
    for key in ('CC', 'CXX', 'ASM', 'CMAKE_C_COMPILER_LAUNCHER',
                'CMAKE_CXX_COMPILER_LAUNCHER', 'CMAKE_ASM_COMPILER_LAUNCHER'):
        if os.environ.get(key):
            raise ValueError('Canonical builds require direct configured compilers; override: ' + key)


def direct_firmware_compilers(build, deps):
    values = {}
    for line in (build / 'CMakeCache.txt').read_text().splitlines():
        if line and not line.startswith(('#', '//')) and '=' in line and ':' in line.split('=', 1)[0]:
            key, value = line.split('=', 1)
            values[key.split(':', 1)[0]] = value
    directory = deps / 'arm-gnu-toolchain-15.3.rel1-x86_64-arm-none-eabi/bin'
    for language, binary in (('C', 'gcc'), ('CXX', 'g++'), ('ASM', 'gcc')):
        compiler = values.get(f'CMAKE_{language}_COMPILER', '')
        bundle.require(compiler and Path(compiler).resolve() ==
                       (directory / ('arm-none-eabi-' + binary)).resolve(),
                       'Firmware compiler differs from verified archive: ' + language)
        if language != 'ASM':
            bundle.require(values.get(f'CMAKE_{language}_COMPILER_LAUNCHER') == '',
                           'Compiler cache/launcher forbidden in fresh builds: ' + language)
        else:
            bundle.require(values.get('CMAKE_ASM_COMPILER_LAUNCHER', '') == '', 'Unsupported ASM launcher override')
    # Target properties can override cache defaults. Inspect the actual declared
    # commands as well; CMake has no ASM_COMPILER_LAUNCHER property.
    commands = bundle.read_json(build / 'compile_commands.json', limit=bundle.MAX_FILE)
    bundle.require(isinstance(commands, list) and bool(commands), 'Missing direct compiler command inventory')
    trusted = {(directory / ('arm-none-eabi-' + binary)).resolve() for binary in ('gcc', 'g++')}
    resolved = {}
    for entry in commands:
        bundle.require(isinstance(entry, dict) and ('arguments' in entry) != ('command' in entry),
                       'Ambiguous compiler command inventory')
        if 'arguments' in entry:
            args = entry['arguments']
        else:
            bundle.require(isinstance(entry['command'], str), 'Invalid compiler command')
            lexer = shlex.shlex(entry['command'], posix=True)
            lexer.whitespace_split = True
            lexer.commenters = ''
            args = [next(lexer, None)]
        bundle.require(isinstance(args, list) and bool(args) and all(isinstance(arg, str) and arg for arg in args),
                       'Invalid compiler command arguments')
        if args[0] not in resolved:
            resolved[args[0]] = Path(args[0]).resolve()
        bundle.require(resolved[args[0]] in trusted, 'Compiler command is wrapped or outside the verified archive')


def inputs():
    execution.require_unoptimized_python()
    producer_execution_policy()
    direct_compiler_environment()
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
        raise ValueError('The historical 0.1.0-testing.N producer is unsupported for Control/1; use a CI build or a semantic beta/stable release')
    bundle.firmware_channel(version, dict(event=os.environ['GITHUB_EVENT_NAME'],
                            ref=os.environ['GITHUB_REF'], run_id=int(run_id), attempt=int(attempt)))
    check_control_policy(stable_release=bundle.version_kind(version) == 'stable')
    publish = os.environ.get('CI_PUBLISH', 'false')
    latest = os.environ.get('CI_MAKE_LATEST', 'false')
    bundle.require(publish in ('true', 'false') and latest in ('true', 'false') and
                   (publish == 'false' or os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch') and
                   (latest == 'false' or publish == 'true' and bundle.version_kind(version) == 'stable'),
                   'Publication/latest selection requires explicit manual authorization and a final version for latest')
    bundle.require(stream != 'validation' or publish == latest == 'false',
                   'Feature validation cannot publish or select latest')
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
    for name in ('host-debug', 'ci-consumer', 'ci-reproducibility'):
        fresh_directory(ROOT / 'build' / name)
    selected = ['consumer']
    return source, version, selected


def expected_tests():
    return bundle.required_tests()


def host_checks(deps, audit):
    completion = execution.completion_policy(bundle.read_json(ROOT / "scripts/ci/ctest-completion-policy.json"))
    chrome = shutil.which('google-chrome')
    if not chrome:
        raise ValueError('Runner Chrome is required for the native browser checks')
    os.environ['CHROME_BIN'] = chrome
    harness_source = str(deps / 'harness/src')
    sys.path.insert(0, harness_source)
    os.environ['PYTHONPATH'] = harness_source
    import cryptography
    import jsonschema
    import numpy
    import serial
    import ssl
    from wsprrypi_qualification import carrier, cw_defaults
    # Import before configure: missing modules must never silently shrink coverage.
    assert all((cryptography, jsonschema, numpy, serial, ssl, carrier, cw_defaults))
    log = audit / 'host.log'
    web = ROOT / 'src/network/bootstrap_web'
    execute(log, 'npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund', cwd=web)
    host = fresh_directory(ROOT / 'build/host-debug')
    options = {
        'CMAKE_BUILD_TYPE': 'Debug', 'WSPRRY_PICO_BUILD_TESTS': 'ON',
        'WSPRRY_PICO_BUILD_FIRMWARE': 'OFF',
        'WSPRRY_PICO_DOCUMENTATION_VERSION': documentation_version(),
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
            *DIRECT_COMPILER_OPTIONS,
            *(f'-D{k}={v}' for k, v in options.items()))
    registered = json.loads(capture('ctest', '--test-dir', host, '--show-only=json-v1'))
    execution.completion_registration(registered, completion, source_root=ROOT)
    names = {test['name'] for test in registered['tests']}
    missing = expected_tests() - names
    if missing:
        raise ValueError('Required tests not registered: ' + ', '.join(sorted(missing)))
    (audit / 'ctest-completion-policy.json').write_text(json.dumps(completion, indent=2) + '\n')
    (audit / 'registered-tests.json').write_text(json.dumps(registered, indent=2) + '\n')
    execute(log, 'cmake', '--build', host, '--parallel', '4')
    execute(log, 'ctest', '--test-dir', host, '--parallel', '2', '--output-on-failure', '--timeout', '240',
            '--test-output-size-passed', '1048576', '--test-output-size-failed', '1048576',
            '--output-junit', audit / 'host-tests.xml', context='ctest')
    suite = ET.parse(audit / 'host-tests.xml').getroot()
    cases = suite.findall('testcase')
    execution.ctest_result(suite, names, completion, registered, command_root=ROOT)
    (audit / 'evidence-skips.json').write_text('[]\n')
    execute(log, sys.executable, ROOT / 'scripts/check_control_policy.py', context='control-policy')
    execute(log, 'npm', 'test', cwd=web, context='npm', expected=completion['contexts']['npm'])
    execute(log, sys.executable, ROOT / 'tests/ci_bundle_tests.py', context='packaging', expected=completion['contexts']['packaging'])
    execute(log, 'node', '--test', ROOT / 'tests/ui_process_cleanup.test.mjs',
            ROOT / 'tests/chrome_startup.test.mjs', ROOT / 'tests/contextual_help_cleanup.test.mjs', context='browser-lifecycle', expected=completion['contexts']['browser-lifecycle'])
    execute(log, 'node', ROOT / 'tests/standalone_frequency_ui_integration.mjs',
            host / 'consumer_bootstrap_driver', audit / 'consumer-ui', context='frequency')
    execute(log, 'node', ROOT / 'tests/standalone_frequency_ui_integration.mjs',
            host / 'consumer_bootstrap_driver', audit / 'first-wspr-ui', 'first-use:network', 'transmission', context='first-use')
    execute(log, 'node', ROOT / 'tests/session_timeout_browser.mjs',
            host / 'consumer_bootstrap_driver', audit / 'session-timeout-ui', context='session-timeout')
    execute(log, 'env', 'PROGRESS_BROWSER_NO_CAPTURE=1', 'node', ROOT / 'tests/progress_browser_integration.mjs',
            host / 'consumer_bootstrap_driver', audit / 'progress-ui', context='progress')
    execute(log, 'node', ROOT / 'tests/consumer_recovery_browser.mjs', host / 'consumer_bootstrap_driver', context='recovery')
    execute(log, 'env', 'UI_REVIEW_NO_CAPTURE=1', 'node', ROOT / 'tests/submission_ui_browser.mjs',
            host / 'consumer_bootstrap_driver', audit / 'submission-ui', context='submission')
    for suite in ('hostname_browser_integration', 'organization_browser_integration',
                  'wspr_browser_integration', 'message_frequency_ui_integration'):
        execute(log, 'env', 'PICO_BROWSER_NO_CAPTURE=1', 'node', ROOT / f'tests/{suite}.mjs',
                host / 'consumer_bootstrap_driver', audit / suite,
                context={'hostname_browser_integration': 'hostname', 'organization_browser_integration': 'organization',
                         'wspr_browser_integration': 'wspr', 'message_frequency_ui_integration': 'message-frequency'}[suite])
    execute(log, 'node', ROOT / 'tests/operator_cleanup_browser.mjs', host / 'consumer_session_driver', context='operator')
    for carrier in ('consumer', 'engineering'):
        execute(log, 'env', 'UI_REVIEW_NO_CAPTURE=1', 'node', ROOT / 'tests/ui_sections_browser.mjs',
                host / 'consumer_bootstrap_driver', audit / f'sections-{carrier}', carrier, context=f'sections-{carrier}')
    return {'registered': len(names), 'passed': len(cases), 'failed': 0, 'skipped': 0,
            'test_names': sorted(names), 'control_policy': 'passed', 'browser_npm': 'passed',
            'packaging_failure_tests': 'passed', 'consumer_ui': 'passed',
            'historical_evidence_skips': json.loads((audit / 'evidence-skips.json').read_text())}


def documentation_version():
    bundle.build_stream(os.environ.get('GITHUB_EVENT_NAME'), os.environ.get('GITHUB_REF'))
    return 'devel'


def firmware(deps, audit, identifier, version, reuse_build=None):
    profile = bundle.PROFILES[identifier]
    target = profile['target']
    log = audit / (identifier + '.log')
    if reuse_build is None:
        build = fresh_directory(ROOT / ('build/ci-' + identifier))
        execute(log, 'cmake', '-S', ROOT, '-B', build, '-G', 'Ninja',
                *DIRECT_COMPILER_OPTIONS,
                '-DCMAKE_BUILD_TYPE=Release', '-DWSPRRY_PICO_BUILD_FIRMWARE=ON',
                '-DWSPRRY_PICO_BUILD_TESTS=OFF', '-DPICO_BOARD=pico2_w',
                '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', '-DPICOTOOL_NO_LIBUSB=1',
                f'-DPICOTOOL_GIT_REPOSITORY_URL={deps / "picotool"}',
                f'-DWSPRRY_PICO_FIRMWARE_VERSION={version}',
                f'-DWSPRRY_PICO_DOCUMENTATION_VERSION={documentation_version()}')
    else:
        # Both targets are declared by the same configuration with their own
        # definitions, sources, metadata, and post-link checks. Only common
        # CMake library objects are shared; no per-image objects are substituted.
        build = reuse_build
        bundle.require(identifier == 'inhibited-regression' and build == ROOT / 'build/ci-consumer' and
                       (build / 'firmware/WsprryPico.uf2').is_file(), 'Invalid shared image build context')
    direct_firmware_compilers(build, deps)
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
    return overlays


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


def runner_environment(browser=False):
    environment = {name: os.environ.get(name, '') for name in
                   ('ImageOS', 'ImageVersion', 'RUNNER_OS', 'RUNNER_ARCH')}
    tools = {
        'cmake': ('cmake', '--version'), 'ninja': ('ninja', '--version'),
        'host_cxx': ('c++', '--version'), 'python': (sys.executable, '--version'),
        'openssl': ('openssl', 'version'), 'pip': (sys.executable, '-m', 'pip', 'freeze'),
        'system_packages': ('dpkg-query', '-W', 'libssl-dev', 'gcc', 'g++'),
    }
    if browser:
        tools.update(node=('node', '--version'), chrome=(os.environ['CHROME_BIN'], '--version'))
    environment['versions'] = {tool: capture(*args) for tool, args in tools.items()}
    return environment


def firmware_checks(deps, audit, deployment, version):
    os.environ['PATH'] = str(deps / 'arm-gnu-toolchain-15.3.rel1-x86_64-arm-none-eabi/bin') + os.pathsep + os.environ['PATH']
    consumer_overlays = firmware(deps, audit, 'consumer', version)
    normal = ROOT / 'build/ci-consumer/firmware/WsprryPico'
    suffixes = ('.elf', '.elf.map', '.uf2')
    retained = {suffix: bundle.sha(Path(str(normal) + suffix)) for suffix in suffixes}
    inhibited_overlays = firmware(deps, audit, 'inhibited-regression', version,
                                  reuse_build=normal.parent.parent)
    bundle.require(all(bundle.sha(Path(str(normal) + suffix)) == retained[suffix] for suffix in suffixes),
                   'Inhibited build changed the accepted normal image')
    (audit / 'inhibited-regression/WsprryPico-Inhibited.uf2').unlink()
    execute(audit / 'compatibility.log', 'cmake', '--build', ROOT / 'build/ci-consumer',
            '--target', 'WsprryPico-StandaloneRF', '--parallel', '4')

    fresh = fresh_directory(ROOT / 'build/ci-reproducibility')
    execute(audit / 'reproducibility.log', 'cmake', '-S', ROOT, '-B', fresh, '-G', 'Ninja',
            *DIRECT_COMPILER_OPTIONS,
            '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
            '-DCMAKE_BUILD_TYPE=Release', '-DWSPRRY_PICO_BUILD_FIRMWARE=ON',
            '-DWSPRRY_PICO_BUILD_TESTS=OFF', '-DPICO_BOARD=pico2_w', '-DPICOTOOL_NO_LIBUSB=1',
            f'-DPICOTOOL_GIT_REPOSITORY_URL={deps / "picotool"}',
            f'-DWSPRRY_PICO_FIRMWARE_VERSION={version}',
            f'-DWSPRRY_PICO_DOCUMENTATION_VERSION={documentation_version()}')
    direct_firmware_compilers(fresh, deps)
    execute(audit / 'reproducibility.log', 'cmake', '--build', fresh,
            '--target', 'WsprryPico', '--parallel', '4')
    reproduced = bundle.sha(fresh / 'firmware/WsprryPico.uf2')
    bundle.require(reproduced == retained['.uf2'] == bundle.sha(audit / 'consumer/WsprryPico.uf2'),
                   'Two fresh consumer builds differ; investigate before distribution')

    licenses(deps, deployment / 'DEPENDENCY-LICENSES.txt')
    for name in ('LICENSE.md', 'THIRD_PARTY_NOTICES.md'):
        shutil.copyfile(ROOT / name, deployment / name)
    return {
        'checks': {'inhibited_regression': 'passed', 'compatibility_rf': 'passed', 'reproducibility': 'identical'},
        'reproduced_uf2_sha256': reproduced,
        'overlays': {'consumer': consumer_overlays, 'inhibited-regression': inhibited_overlays},
        'linked_resources': {name: bundle.sha(deps / 'sdk/lib/cyw43-driver/firmware' / name)
                             for name in bundle.read_json(ROOT / 'scripts/ci/inputs.json')['linked_resource_sha256']},
    }


def stage_identity(source, version):
    return {'source': source, 'tree': capture('git', 'rev-parse', source + '^{tree}'),
            'version': version, 'workflow': os.environ['CI_WORKFLOW_SHA'],
            'event': os.environ['GITHUB_EVENT_NAME'], 'ref': os.environ['GITHUB_REF'],
            'run_id': os.environ['GITHUB_RUN_ID'], 'attempt': os.environ['GITHUB_RUN_ATTEMPT']}


def stage_paths(output):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    audit = output / 'audit'
    audit.mkdir()
    return audit


STAGE_INPUT_KEYS = {
    'host': ('pins', 'sdk', 'companion', 'harness'),
    'firmware': ('pins', 'sdk', 'picotool', 'toolchain_archive_sha256'),
}


def build_stage(role, deps, output, identity):
    deps = deps.resolve(strict=True)
    os.environ['PICO_SDK_PATH'] = str(deps / 'sdk')
    audit = stage_paths(output)
    if role == 'host':
        data = {'checks': host_checks(deps, audit)}
    else:
        deployment = output / 'deployment'
        deployment.mkdir()
        data = firmware_checks(deps, audit, deployment, identity['version'])
        (audit / 'execution.json').rename(audit / execution.FIRMWARE_EXECUTION)
    data['environment'] = runner_environment(browser=role == 'host')
    inputs = bundle.read_json(deps / 'verified-inputs.json')
    data['inputs'] = {key: inputs[key] for key in STAGE_INPUT_KEYS[role]}
    bundle.require(capture('git', 'rev-parse', 'HEAD') == identity['source'] and
                   not capture('git', 'status', '--porcelain', '--untracked-files=all'),
                   'Source changed during ' + role + ' stage')
    files = [bundle.descriptor(path, output) for path in sorted(output.rglob('*')) if path.is_file()]
    manifest = {'schema': 'ci-stage/1', 'role': role, 'identity': identity, 'data': data, 'files': files}
    (output / 'stage.json').write_text(json.dumps(manifest, indent=2) + '\n')


def read_stage(root, role, identity):
    bundle.require(root.is_dir() and not root.is_symlink(), 'Missing or unsafe ' + role + ' stage')
    bundle.require((root / 'stage.json').is_file(), 'Missing ' + role + ' stage receipt')
    manifest = bundle.read_json(root / 'stage.json')
    bundle.require(isinstance(manifest, dict) and set(manifest) == {'schema', 'role', 'identity', 'data', 'files'}
                   and manifest['schema'] == 'ci-stage/1' and manifest['role'] == role
                   and manifest['identity'] == identity, role + ' stage belongs to another source or run attempt')
    data_keys = {'checks', 'environment', 'inputs'}
    if role == 'firmware':
        data_keys.update({'reproduced_uf2_sha256', 'overlays', 'linked_resources'})
    data = manifest['data']
    bundle.require(isinstance(data, dict) and data.keys() == data_keys and
                   all(isinstance(data[key], dict) for key in data_keys - {'reproduced_uf2_sha256'}),
                   'Malformed ' + role + ' stage data')
    bundle.require(data['inputs'].keys() == set(STAGE_INPUT_KEYS[role]) and
                   isinstance(data['environment'].get('versions'), dict), 'Wrong stage input or tool evidence')
    records = manifest['files']
    bundle.require(isinstance(records, list) and 0 < len(records) <= 2000 and
                   all(isinstance(record, dict) and record.keys() == {'path', 'bytes', 'sha256'} and
                       isinstance(record['path'], str) and isinstance(record['sha256'], str) for record in records),
                   'Malformed ' + role + ' stage file inventory')
    for record in records:
        name = record['path']
        firmware_owned = (name.startswith(('audit/consumer/', 'audit/inhibited-regression/', 'deployment/')) or
                          name.startswith('audit/') and name.removeprefix('audit/') in (
                              *execution.FIRMWARE_COMMAND_LOGS, execution.FIRMWARE_EXECUTION))
        bundle.require((firmware_owned if role == 'firmware' else name.startswith('audit/') and
                        not firmware_owned) and name not in {'audit/build-inputs.json', 'audit/ci-stages.json'},
                       'Wrong stage file owner: ' + name)
    files = bundle.inventory(root, records, extra=('stage.json',))
    return manifest, files


def assemble(host, firmware_output, output, identity, selected):
    host_stage, host_files = read_stage(host, 'host', identity)
    firmware_stage, firmware_files = read_stage(firmware_output, 'firmware', identity)
    bundle.require(not host_files.keys() & firmware_files.keys(), 'Stage file ownership overlaps')
    host_data, firmware_data = host_stage['data'], firmware_stage['data']
    host_inputs, firmware_inputs = host_data['inputs'], firmware_data['inputs']
    pins = bundle.read_json(ROOT / 'scripts/ci/inputs.json')
    bundle.require(host_inputs.get('pins') == firmware_inputs.get('pins') == pins and
                   isinstance(host_inputs.get('sdk'), dict) and host_inputs['sdk'] == firmware_inputs.get('sdk'),
                   'Stage dependency pins or SDK provenance differ')
    host_checks = host_data['checks']
    firmware_checks = firmware_data['checks']
    bundle.require(set(host_checks) == {'registered', 'passed', 'failed', 'skipped', 'test_names', 'control_policy',
                                       'browser_npm', 'packaging_failure_tests', 'consumer_ui', 'historical_evidence_skips'} and
                   firmware_checks == {'inhibited_regression': 'passed', 'compatibility_rf': 'passed',
                                       'reproducibility': 'identical'},
                   'Incomplete stage check evidence')
    uf2 = firmware_files.get('audit/consumer/WsprryPico.uf2')
    bundle.require(uf2 is not None and bundle.sha(uf2) == firmware_data['reproduced_uf2_sha256'],
                   'Reproducibility evidence does not match the staged image')
    bundle.inspect_payload(uf2.parent, 'consumer', bundle.source_application_end(identity['source']))

    build_inputs = dict(firmware_inputs)
    build_inputs.update({key: host_inputs[key] for key in ('companion', 'harness')})
    environment = firmware_data['environment']
    environment = {**environment, 'versions': {**environment['versions'],
                   **{key: host_data['environment']['versions'][key] for key in ('node', 'chrome')}}}
    build_inputs.update(environment=environment, overlays=firmware_data['overlays'],
                        linked_resources=firmware_data['linked_resources'],
                        python_lock_sha256=bundle.sha(ROOT / 'scripts/ci/requirements.txt'),
                        npm_lock_sha256=bundle.sha(ROOT / 'src/network/bootstrap_web/package-lock.json'))
    source, version = identity['source'], identity['version']
    checks = host_checks | firmware_checks
    bundle.require(not output.exists() and not output.is_symlink(), 'Fresh bundle output required')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.wsprrypico-verify-', dir=output.parent) as temporary:
        staged_bundle = Path(temporary) / 'bundle'
        audit = stage_paths(staged_bundle)
        deployment = staged_bundle / 'deployment'
        for name, path in (host_files | firmware_files).items():
            target = staged_bundle / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        bundle.inventory(staged_bundle, host_stage['files'] + firmware_stage['files'])
        (audit / 'ci-stages.json').write_text(json.dumps([host_stage, firmware_stage], indent=2) + '\n')
        bundle.create(deployment, audit, source, version, selected, checks, build_inputs)
        # The firmware job inspected the linked image using pinned tools.
        # Check transported bytes and host evidence without running staged binaries.
        bundle.verify(deployment, audit, source, version, inspect=False)
        staged_bundle.rename(output)
    print(json.dumps({'source': source, 'version': version, 'profiles': selected,
                      'deployment': str(output / 'deployment'), 'checks': checks}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inputs', 'build', 'host', 'firmware', 'assemble'))
    parser.add_argument('--dependencies', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--host', type=Path)
    parser.add_argument('--firmware', type=Path)
    args = parser.parse_args()
    source, version, selected = inputs()
    if args.action == 'inputs':
        print((source, version, selected))
    elif args.action == 'assemble' and args.host and args.firmware and args.output:
        assemble(args.host, args.firmware, args.output, stage_identity(source, version), selected)
    elif args.action in ('host', 'firmware', 'build') and args.dependencies and args.output:
        identity = stage_identity(source, version)
        if args.action == 'build':
            with tempfile.TemporaryDirectory(prefix='wsprrypico-stages-') as temporary:
                host, firmware_output = Path(temporary) / 'host', Path(temporary) / 'firmware'
                build_stage('host', args.dependencies, host, identity)
                build_stage('firmware', args.dependencies, firmware_output, identity)
                assemble(host, firmware_output, args.output, identity, selected)
        else:
            build_stage(args.action, args.dependencies, args.output, identity)
    else:
        parser.error('Provide --output with --dependencies for stages/build or --host and --firmware for assemble')


if __name__ == '__main__':
    main()
