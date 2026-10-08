#!/usr/bin/env python3
"""Build ordinary Phase 14 RF candidates from retained pinned inputs; no devices."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SDK_SHA = '079c6f39023649b154152db30f1d781e884879bc'
PT_SHA = '6f6458d792b93685a11423b244a585eaa99eafcf'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def output(args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def build(destination, clocks, *, independent=False):
    destination = destination.resolve()
    if not destination.is_relative_to((ROOT/'build').resolve()):
        raise ValueError('artifacts must remain in ignored build/')
    commit = output(['git', 'rev-parse', 'HEAD'])
    if output(['git', 'diff', '--name-only', 'HEAD', '--']):
        raise ValueError('commit reviewed tracked changes before candidate binding')
    sdk, pt = ROOT/'build/local-sdk-079c6f3', ROOT/'build/pico2-w/_deps/picotool-src'
    for path, expected in ((sdk, SDK_SHA), (pt, PT_SHA)):
        if output(['git', '-C', str(path), 'rev-parse', 'HEAD']) != expected:
            raise ValueError('retained dependency identity')
        if output(['git', '-C', str(path), 'status', '--porcelain', '--untracked-files=no']):
            raise ValueError('dirty retained dependency')
    destination.mkdir(parents=True, exist_ok=False)
    manifest = dict(schema='phase14-candidates/1', source_commit=commit,
        firmware_version='0.0.0-phase14-candidate', sdk_commit=SDK_SHA,
        picotool_commit=PT_SHA, toolchain=output(['arm-none-eabi-gcc', '--version']).splitlines()[0],
        board='pico2_w', engine='pio-dma-gp2', divider=1, rf_gp=2,
        gp14_enabled=False, fixtures_enabled=False, release_qualified=False,
        runtime_inputs={}, images={})
    tracked = output(['git','ls-files','src','firmware','cmake','CMakeLists.txt','CMakePresets.json',
                      'scripts/generate_web_assets.py']).splitlines()
    manifest['runtime_inputs'] = {p:sha(ROOT/p) for p in tracked}
    for clock in clocks:
        directory = destination/('independent-' if independent else 'build-')/str(clock)
        args = ['cmake','-S',str(ROOT),'-B',str(directory),'-G','Ninja',
            '-DCMAKE_BUILD_TYPE=Release','-DWSPRRY_PICO_BUILD_FIRMWARE=ON',
            '-DWSPRRY_PICO_BUILD_TESTS=OFF','-DPICO_BOARD=pico2_w',
            '-DPICO_SDK_PATH='+str(sdk),'-DPICOTOOL_FETCH_FROM_GIT_PATH='+str(pt.parent),
            '-DWSPRRY_PICO_CONSUMER_LAN_MODE=plain',
            '-DWSPRRY_PICO_RF_SAMPLE_RATE_HZ='+str(clock),
            '-DWSPRRY_PICO_STANDALONE_WSPR_BASE_FREQUENCY_HZ=3570100',
            '-DWSPRRY_PICO_FIRMWARE_VERSION='+manifest['firmware_version'],
            '-DWSPRRY_PICO_GP14_RUNTIME_BUTTON=OFF','-DWSPRRY_PICO_LED_ACCEPTANCE=OFF']
        subprocess.run(args,cwd=ROOT,check=True)
        subprocess.run(['cmake','--build',str(directory),'--target','WsprryPico-StandaloneRF','-j4'],check=True)
        image = dict(clock_hz=clock, configure=args)
        for ext in ('uf2','elf','elf.map'):
            original = directory/'firmware'/('WsprryPico-StandaloneRF.'+ext)
            target = destination/('WsprryPico-phase14-'+str(clock)+'.'+ext)
            shutil.copyfile(original,target)
            image[ext] = dict(path=str(target),sha256=sha(target),bytes=target.stat().st_size)
        manifest['images'][str(clock)] = image
        (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if commit != output(['git','rev-parse','HEAD']) or output(['git','diff','--name-only','HEAD','--']):
        raise ValueError('source changed during build')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--clocks',type=int,nargs='+',choices=(132000000,138000000,150000000),
                        default=[132000000,138000000,150000000])
    parser.add_argument('--independent',action='store_true')
    args=parser.parse_args()
    manifest=build(args.output,args.clocks,independent=args.independent)
    print(json.dumps({k:v['uf2']['sha256'] for k,v in manifest['images'].items()}))


if __name__=='__main__':
    main()
