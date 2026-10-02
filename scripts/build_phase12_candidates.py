#!/usr/bin/env python3
"""Build private, clean Phase12 candidates with retained dependencies; no device I/O."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from phase12_candidate_manifest import verify


def run(argv, **kwargs):
    return subprocess.run(argv, check=True, text=True, **kwargs)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--artifact-root', type=Path, required=True)
    p.add_argument('--sdk', type=Path, required=True)
    p.add_argument('--picotool-import', type=Path, required=True)
    a = p.parse_args()
    source, root, sdk = (x.resolve() for x in (a.source, a.artifact_root, a.sdk))
    revision = run(['git', '-C', str(source), 'rev-parse', 'HEAD'], capture_output=True).stdout.strip()
    if run(['git', '-C', str(source), 'status', '--porcelain'], capture_output=True).stdout:
        p.error('source must be a clean committed checkout, including untracked files')
    sdk_revision = run(['git', '-C', str(sdk), 'rev-parse', 'HEAD'], capture_output=True).stdout.strip()
    if run(['git', '-C', str(sdk), 'status', '--porcelain', '--ignore-submodules=none'], capture_output=True).stdout:
        p.error('retained SDK and submodules must be clean')
    if sdk_revision != '079c6f39023649b154152db30f1d781e884879bc':
        p.error('retained SDK revision mismatch')
    if root.exists() or root.is_relative_to(source) or source.is_relative_to(root):
        p.error('artifact root must be new and separate from clean source')
    if not a.picotool_import.is_file():
        p.error('retained picotool import missing')
    root.mkdir(mode=0o700, parents=True)
    candidates = []
    roles = ['restore', 'consumer', 'engineering', 'rf_ap', 'session_deadline'] + [f'fault_{n}' for n in range(1, 11)]
    for role in roles:
        stage = int(role[6:]) if role.startswith('fault_') else 0
        gp14 = role in ('consumer', 'rf_ap')
        target = 'WsprryPico-StandaloneRF' if role == 'rf_ap' else 'WsprryPico'
        mode = 'tls' if role == 'engineering' else 'plain'
        # Stage-only recompilation retains the exact source-specific macro, with
        # each role exported before the next configure replaces its build files.
        build = root / '_build' / ('fault' if stage else role)
        folder = root / role
        folder.mkdir(mode=0o700)
        args = ['cmake', '-S', str(source), '-B', str(build), '-G', 'Ninja',
                '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
                '-DPICO_BOARD=pico2_w', '-DPICO_SDK_PATH=' + str(sdk),
                '-DCMAKE_PROJECT_INCLUDE=' + str(a.picotool_import.resolve()),
                '-DWSPRRY_PICO_BUILD_FIRMWARE=ON', '-DWSPRRY_PICO_BUILD_TESTS=OFF',
                '-DWSPRRY_PICO_GP14_RUNTIME_BUTTON=' + ('ON' if gp14 else 'OFF'),
                '-DWSPRRY_PICO_CONSUMER_LAN_MODE=' + mode,
                '-DWSPRRY_PICO_PHASE12_FAULT_STAGE=' + str(stage),
                '-DWSPRRY_PICO_PHASE12_SESSION_DEADLINE_FIXTURE=' + ('ON' if role == 'session_deadline' else 'OFF'),
                '-DWSPRRY_PICO_GP14_RF_ACCEPTANCE=' + ('ON' if role == 'rf_ap' else 'OFF')]
        with (folder / 'build.log').open('w') as log:
            run(args, stdout=log, stderr=subprocess.STDOUT)
            run(['cmake', '--build', str(build), '--target', target, '-j', '8'], stdout=log, stderr=subprocess.STDOUT)
        record = dict(role=role, firmware='0.0.0-devel', revision=revision[:12], target=target,
                      gp14=gp14, lan_mode=mode, fault_stage=stage, session_deadline_fixture=role == 'session_deadline')
        paths = {'elf': build / 'firmware' / (target + '.elf'),
                 'uf2': build / 'firmware' / (target + '.uf2'),
                 'map': build / 'firmware' / (target + '.elf.map'),
                 'build_identity': build / 'firmware/generated/firmware_identity.hpp',
                 'compile_commands': build / 'compile_commands.json'}
        for kind, path in paths.items():
            out = folder / path.name
            shutil.copyfile(path, out)
            os.chmod(out, 0o600)
            record[kind] = dict(path=str(out.relative_to(root)), bytes=out.stat().st_size,
                                sha256=hashlib.sha256(out.read_bytes()).hexdigest())
        symbols = folder / 'symbols.txt'
        with symbols.open('w') as output:
            run(['arm-none-eabi-nm', '-C', str(root / record['elf']['path'])], stdout=output)
        record['symbols'] = dict(path=str(symbols.relative_to(root)), bytes=symbols.stat().st_size,
                                  sha256=hashlib.sha256(symbols.read_bytes()).hexdigest())
        candidates.append(record)
        print('Built and retained ' + role, flush=True)
    if run(['git', '-C', str(source), 'status', '--porcelain'], capture_output=True).stdout:
        p.error('source changed during build')
    if run(['git', '-C', str(source), 'rev-parse', 'HEAD'], capture_output=True).stdout.strip() != revision:
        p.error('source HEAD changed during build')
    if run(['git', '-C', str(sdk), 'rev-parse', 'HEAD'], capture_output=True).stdout.strip() != sdk_revision or run(['git', '-C', str(sdk), 'status', '--porcelain', '--ignore-submodules=none'], capture_output=True).stdout:
        p.error('SDK or submodules changed during build')
    manifest = dict(schema='phase12-candidates/1', source_commit=revision, sdk_commit=sdk_revision,
                    toolchain='GNU Arm 15.3.1', authority='NONE_PREPARATION_ONLY', candidates=candidates)
    result = verify(manifest, root)
    (root / 'candidates.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
