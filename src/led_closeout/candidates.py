"""Build retained dependencies and bind checked candidates to an exact source tree."""
import json
from pathlib import Path
import shutil
import subprocess

from led_closeout.plan import IMAGES
from led_closeout.runner import require, save_json, sha256


def pins(selection):
    return dict(engine='direct', rf_gp=2, i2c_pair=None, button_gp=14, amplifier_gp=None,
                lpf_gps=[], indicator=('onboard_led', 'external', 'external', 'disabled')[selection],
                indicator_gp=15 if selection == 1 else 16 if selection == 2 else None,
                indicator_active_high=selection != 2)


def build(root, build_dir, destination, *, prepare=False):
    root, build_dir, destination = map(lambda p: Path(p).resolve(), (root, build_dir, destination))
    def output(argv):
        return subprocess.check_output(argv, cwd=root, text=True).strip()
    commit = output(['git', 'rev-parse', 'HEAD'])
    clean = not output(['git', 'status', '--porcelain', '--untracked-files=normal'])
    require(clean or prepare, 'commit reviewed sources before final candidate binding')
    require(build_dir.is_relative_to(root/'build') and destination.is_relative_to(root/'build'),
            'candidates must stay under ignored build/')
    destination.mkdir(parents=True, exist_ok=True)
    sdk = root/'build/local-sdk-079c6f3'
    picotool = root/'build/pico2-w/_deps/picotool-src'
    sdk_commit = output(['git', '-C', str(sdk), 'rev-parse', 'HEAD'])
    pt_commit = output(['git', '-C', str(picotool), 'rev-parse', 'HEAD'])
    require(sdk_commit == '079c6f39023649b154152db30f1d781e884879bc' and
            pt_commit == '6f6458d792b93685a11423b244a585eaa99eafcf', 'retained dependency revision')
    manifest = dict(schema='phase13.1-led-candidates/2', source_commit=commit, clean=clean,
                    sdk_commit=sdk_commit, picotool_commit=pt_commit, board='pico2_w',
                    sample_rate_hz=138000000, physical_acceptance='NOT_RUN', images={})
    groups = [('restore', 'onboard'), ('cue', 'stimulus'), ('high',), ('low',), ('disabled',), ('gp14',)]
    for keys in groups:
        rf, acceptance, selection, gp14 = IMAGES[keys[0]]
        args = ['cmake', '-S', str(root), '-B', str(build_dir), '-G', 'Ninja',
                '-DCMAKE_BUILD_TYPE=Release', '-DWSPRRY_PICO_BUILD_FIRMWARE=ON',
                '-DWSPRRY_PICO_BUILD_TESTS=OFF', '-DPICO_BOARD=pico2_w',
                '-DPICO_SDK_PATH='+str(sdk), '-DPICOTOOL_FETCH_FROM_GIT_PATH='+str(picotool.parent),
                '-DWSPRRY_PICO_CONSUMER_LAN_MODE=plain', '-DWSPRRY_PICO_RF_SAMPLE_RATE_HZ=138000000',
                '-DWSPRRY_PICO_STANDALONE_WSPR_BASE_FREQUENCY_HZ=3570100',
                '-DWSPRRY_PICO_FIRMWARE_VERSION=0.0.0-devel',
                '-DWSPRRY_PICO_PHASE12_SESSION_DEADLINE_FIXTURE=OFF',
                '-DWSPRRY_PICO_PHASE12_PHYSICAL_CUT_FIXTURE=OFF',
                '-DWSPRRY_PICO_GP14_BUTTON_DIAGNOSTIC=OFF',
                '-DWSPRRY_PICO_GP14_DIAG_INJECT_WATCHDOG=OFF',
                '-DWSPRRY_PICO_GP14_ROBUSTNESS=OFF',
                '-DWSPRRY_PICO_LED_ACCEPTANCE='+('ON' if acceptance else 'OFF'),
                '-DWSPRRY_PICO_LED_SELECTION='+str(selection),
                '-DWSPRRY_PICO_GP14_RUNTIME_BUTTON='+('ON' if gp14 else 'OFF'),
                '-DWSPRRY_PICO_GP14_RF_ACCEPTANCE=OFF', '-DWSPRRY_PICO_GP14_FLASH_PROBE=OFF',
                '-DWSPRRY_PICO_PHASE12_INDICATOR_FAULT_FIXTURE=OFF',
                '-DWSPRRY_PICO_PHASE12_FAULT_STAGE=0', '-DWSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC=OFF']
        subprocess.run(args, cwd=root, check=True)
        targets = ['WsprryPico-StandaloneRF' if IMAGES[k][0] else 'WsprryPico' for k in keys]
        subprocess.run(['cmake', '--build', str(build_dir), '--target']+targets+['-j4'], check=True)
        for key, target in zip(keys, targets):
            image = dict(engine='pio-dma-gp2' if IMAGES[key][0] else 'inhibited-standalone-simulator',
                acceptance=acceptance, selection=selection, gp14=gp14, pins=pins(selection),
                revision=commit[:12]+('' if clean else '-dirty'))
            for extension in ('elf', 'uf2'):
                source = build_dir/'firmware'/(target+'.'+extension)
                copied = destination/(key+'.'+extension)
                shutil.copyfile(source, copied)
                image[extension] = str(copied)
                image[extension+'_sha256'] = sha256(copied)
            # Both the ordinary and fixture images pass the real linked-image checks.
            subprocess.run(['python3', str(root/'scripts/check_standalone_image.py'), str(build_dir/'firmware'/(target+'.elf'))], check=True)
            symbols = output(['arm-none-eabi-nm', image['elf']])
            require(('led_acceptance' in symbols) == acceptance, 'fixture symbol isolation')
            manifest['images'][key] = image
            save_json(destination/'manifest.json', manifest)
    # Build the ordinary Pico platform link-check with all acceptance options off.
    subprocess.run(['cmake', '-S', str(root), '-B', str(build_dir),
                    '-DWSPRRY_PICO_LED_ACCEPTANCE=OFF', '-DWSPRRY_PICO_LED_SELECTION=0',
                    '-DWSPRRY_PICO_GP14_RUNTIME_BUTTON=OFF'], check=True)
    subprocess.run(['cmake', '--build', str(build_dir), '--target', 'field_access_pico_linkcheck', '-j4'], check=True)
    require(commit == output(['git', 'rev-parse', 'HEAD']) and
            (prepare or not output(['git', 'status', '--porcelain', '--untracked-files=normal'])),
            'source changed during candidate build')
    save_json(destination/'manifest.json', manifest)
    return manifest
