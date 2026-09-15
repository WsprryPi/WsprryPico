#!/usr/bin/env python3
"""One reviewed Pico A repair flash; no RF, configuration or network mutation."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time

from phase11_5_device_management import digest, save
from phase11_5_inventory import require
from phase11_5_load_reply_target import Journal, inventory, healthy
from phase11_5_pilot import SERIAL, DEVICE
from phase11_5_pilot_supervisor import PICOTOOL, PICOTOOL_SHA, configuration
from phase11_5_r3_allocation_diagnostic import request_bootsel, saved_configuration
from phase11_5_r3_v2_admission import candidate
from phase11_5_rf_reservation import Reservation, inactive

HTTP_PAGES = 'phase115-completion-http-pages-deploy-v1'
RECOVERY_FAULT = dict(recovery_boot=True,fault_stage=14,fault_hash=3833354787,
    fault_pc=0,fault_status=0,fault_allocation_recorded=True,
    fault_allocation_request_bytes=32769,fault_allocation_returned_null=True)

CANDIDATES = {
    'phase115-memory-pressure-deploy-v1': (
        '8dd6f0812292e9264c2a72745078a95ee606c191', '150fe016bb61',
        'c3ea3e2ad15dafe5db2acec253e35c99'),
    'phase115-completion-retained-sharing-deploy-v1': (
        '150fe016bb61518fb259adcedf86d3ac9779d373', '6b7a1b848e2b',
        '1739cc4f28304080ec97e2b228ab2683'),
    HTTP_PAGES: ('6b7a1b848e2b5192acaa0fa08fb778613457ad8b', 'e64ebb9b0373',
                 'cb429dd3964439e66e03bb0d93a9863b'),
    'phase115-completion-read-workspace-deploy-v1': (
        'e64ebb9b03739b61e33987ec267f7adf1f9732c6', 'b0254c5e64ab',
        '4dad3b38c27aad73da01cefc9e857cdb'),
    'phase115-completion-info-lifetime-deploy-v1': (
        'b0254c5e64abf858255ca6d426e864080f003891', '0001a3625832',
        '6213cc6b8d7694082fb804fdf5b121fc'),
    'phase115-completion-active-replay-deploy-v1': (
        '0001a3625832b16ad89236cd98cce9679353aba8', 'd674dc6cbf8e',
        'd76d4e540ddafff6622513596125c58c'),
    'phase115-completion-streamed-reply-deploy-v1': (
        'd674dc6cbf8efd142527c1c54f283d6037bb1acf', 'a9d5610d76f6',
        '8d747e80fa4e2762ba2509b5bb5ecfae'),
    'phase115-completion-terminal-storage-deploy-v1': (
        'bd16bb1c736720fbf901589d41d2a25897987b8b', '98f5797d77fb',
        'b1c0af7bef6ef0bef8f5e44130182149'),
    'phase115-completion-deferred-decode-deploy-v1': (
        'a9d5610d76f6cb349249b8def6eba65f21e7bfa9', 'bd16bb1c7367',
        '3dbf851d7107a714504e5f3dd52df4d9'),
}


def validate(p):
    require(p['serial'] == SERIAL and p['device_id'] == DEVICE and
            CANDIDATES.get(p['scope']) == (p['source_revision'], p['prior_revision'],
                                        p['prior_boot']), 'Exact A repair candidate')
    require(p['limits'] == dict(flashes=1, bootsel=1, rf_jobs=0, loads=0, arm=0,
            reboots=0, wifi_cycles=0, configuration_writes=0), 'Single idle flash budget')
    require(p['runtime_seconds'] == 300 and p['cleanup_seconds'] == 150 and
            p['cleanup_deadline_monotonic_ns'] - p['work_deadline_monotonic_ns'] == 150_000_000_000 and
            p['work_deadline_monotonic_ns'] - p['start_monotonic_ns'] == 300_000_000_000,
            'Frozen deployment deadlines')
    require(p['image_file'] == 'candidate.uf2' and re.fullmatch('[0-9a-f]{64}', p['image_sha256']),
            'Reviewed image identity')
    require(all(re.fullmatch('[0-9a-f]{32}',p[k]) for k in ('inventory_session','b_session')) and
            p['inventory_session'] != p['b_session'], 'Separate board sessions')
    return p


def admit_prior(before, p):
    inactive(before)
    require(before['a']['info']['revision'] == p['prior_revision'] and
            before['a']['wtp']['STATUS']['boot_id'] == p['prior_boot'] and
            before['b']['wtp']['STATUS']['boot_id'] == p['b_boot_id'], 'Prior A/B boots')
    if p['scope'] == HTTP_PAGES:
        require(all(before['a']['info'][key] == value for key,value in RECOVERY_FAULT.items()),
                'Exact previously audited recovery fault')


def config_snapshot(value, p):
    # Recovery intentionally has no live station MAC. Retained configuration,
    # including station identity and schedules, remains available read-only.
    return saved_configuration(value) if p['scope'] == HTTP_PAGES else configuration(value)


def run(root, p, sha):
    require(os.geteuid() == 0 and str(root) == p['root'] and
            Path('/proc/sys/kernel/random/boot_id').read_text().strip() == p['host_boot_id'], 'Host/root identity')
    for name, expected in p['stage_sha256'].items():
        require((root/name).resolve().is_relative_to(root) and digest(root/name) == expected,
                'Frozen helper: '+name)
    require(digest(PICOTOOL) == PICOTOOL_SHA and digest(root/'candidate.uf2') == p['image_sha256'],
            'Pinned flash tool and image')
    def check():
        require(p['start_monotonic_ns'] <= time.monotonic_ns() < p['work_deadline_monotonic_ns'],
                'Deployment execution deadline')
    check()
    require(not (root/'deployment.json').exists(), 'Consumed deployment packet')
    emit = Journal(root/'deploy.jsonl'); emit('start', dict(packet_sha256=sha))
    reservation = Reservation(sha)
    state = dict(bootsel_commands=0, flashes_started=0, status='STARTED')
    try:
        before = {b: inventory(root,p,'before-'+b,b=='b') for b in ('a','b')}
        admit_prior(before, p)
        reservation.acquire(before)
        save(root/'reservation-acquired.json', json.loads(reservation.path.read_text()))
        check(); state['bootsel_commands'] = 1; save(root/'deployment.json',state)
        emit('bootsel_intent',state); request_bootsel(emit)
        end = time.monotonic()+15; found = False
        while time.monotonic() < end:
            for serial in Path('/sys/bus/usb/devices').glob('*/serial'):
                try:
                    found |= serial.read_text().strip().upper() == SERIAL and (serial.parent/'idVendor').read_text().strip() == '2e8a' and (serial.parent/'idProduct').read_text().strip() == '000f'
                except OSError:
                    pass
            if found:
                break
            time.sleep(.2)
        require(found, 'Named A bootloader absent; no retry'); check()
        state['flashes_started'] = 1; save(root/'deployment.json',state)
        with (root/'flash.stdout').open('xb') as out, (root/'flash.stderr').open('xb') as err:
            result = subprocess.run([str(PICOTOOL),'load','-v','-x',str(root/'candidate.uf2'),'--ser',SERIAL],
                                    stdout=out,stderr=err,timeout=60)
        require(result.returncode == 0, 'Flash failed; no retry')
        end = time.monotonic()+15
        while not Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00').exists() and time.monotonic()<end:
            time.sleep(.2)
        check()
        after = {b: inventory(root,p,'final-'+b,b=='b') for b in ('a','b')}
        boot = candidate(after['a'],p)
        healthy(after['a']['info'],boot,p['source_revision'])
        require(boot != p['prior_boot'] and all(config_snapshot(after[b], p) == config_snapshot(before[b], p) for b in before)
                and after['b']['wtp']['STATUS'] == before['b']['wtp']['STATUS']
                and configuration(after['b']) == configuration(before['b']), 'Preserved configurations and B')
        reservation.release(after)
        save(root/'reservation-released.json', json.loads(reservation.path.read_text()))
        state.update(status='CANDIDATE_VERIFIED',boot_id=boot)
        save(root/'deployment.json',state); emit('finish',state)
    except BaseException as error:
        state.update(status='STOPPED_REQUIRES_RECONCILIATION',error=str(error))
        save(root/'deployment.json',state); emit('failure',state)
        raise
    finally:
        reservation.close()  # An uncertain flash keeps the reservation HELD.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--packet-sha256',required=True)
    parser.add_argument('--run',action='store_true')
    args = parser.parse_args()
    if not args.run:
        print('Plan only; no device access.'); return
    root = args.root.resolve(strict=True)
    require(digest(root/'packet.json') == args.packet_sha256, 'Exact frozen deployment packet')
    run(root,validate(json.loads((root/'packet.json').read_text())),args.packet_sha256)


if __name__ == '__main__':
    main()
