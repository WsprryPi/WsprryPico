#!/usr/bin/env python3
"""Obtain verified CI inputs in a new private directory; never install globally."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def run(*args):
    return subprocess.check_output(list(map(str, args)), text=True).strip()


def checkout(destination, repository, revision):
    run('git', 'clone', '--no-checkout', repository, destination)
    run('git', '-C', destination, 'checkout', '--detach', revision)
    run('git', '-C', destination, 'submodule', 'update', '--init', '--recursive')
    if run('git', '-C', destination, 'rev-parse', 'HEAD') != revision:
        raise ValueError('Dependency revision mismatch')
    if run('git', '-C', destination, 'status', '--porcelain'):
        raise ValueError('Dirty dependency')
    submodules = run('git', '-C', destination, 'submodule', 'status', '--recursive')
    if any(line[0] in '-+U' for line in submodules.splitlines()):
        raise ValueError('Unverified submodule')
    return {'repository': repository, 'revision': revision,
            'submodules': submodules.splitlines()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise SystemExit('CI dependency setup requires Linux x86_64; no tools were downloaded')
    pins = json.loads((ROOT / 'scripts/ci/inputs.json').read_text())
    destination = args.destination.resolve()
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    archive = destination / 'arm-toolchain.tar.xz'
    with urllib.request.urlopen(pins['toolchain_url'], timeout=120) as response:
        with archive.open('xb') as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
    digest = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
    if digest != pins['toolchain_sha256']:
        raise ValueError('Official Arm archive digest mismatch')
    with tarfile.open(archive) as source:
        source.extractall(destination, filter='data')
    toolchain = destination / 'arm-gnu-toolchain-15.3.rel1-x86_64-arm-none-eabi'
    if run(toolchain / 'bin/arm-none-eabi-gcc', '-dumpfullversion') != pins['arm_gcc']:
        raise ValueError('Wrong Arm compiler')
    inputs = {'pins': pins, 'toolchain_archive_sha256': digest}
    for name, repository in (
            ('sdk', 'https://github.com/raspberrypi/pico-sdk.git'),
            ('picotool', 'https://github.com/raspberrypi/picotool.git'),
            ('companion', 'https://github.com/WsprryPi/WsprryPi.git'),
            ('harness', 'https://github.com/WsprryPi/WsprryPi-Qualification-Harness.git')):
        inputs[name] = checkout(destination / name, repository, pins[name])
    actual_submodules = {line.strip().split()[1]: line.strip().split()[0]
                         for line in inputs['sdk']['submodules']}
    if any(actual_submodules.get(path) != revision for path, revision in pins['sdk_submodules'].items()):
        raise ValueError('SDK linked submodule differs from recorded pin')
    for name, expected in pins['linked_resource_sha256'].items():
        with (destination / 'sdk/lib/cyw43-driver/firmware' / name).open('rb') as source:
            if hashlib.file_digest(source, 'sha256').hexdigest() != expected:
                raise ValueError('SDK linked firmware resource digest mismatch')
    (destination / 'verified-inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
    print(json.dumps({'dependency_directory': str(destination), 'toolchain_sha256': digest}))


if __name__ == '__main__':
    main()
