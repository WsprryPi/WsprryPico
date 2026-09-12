#!/usr/bin/env python3
"""One-shot restoration of the recorded R2 WSPR LOAD OOM; never resumes jobs."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys
import time

from phase11_5_device_fixture import DeviceFixture, ORIGINAL_CONFIG_SHA
from phase11_5_device_management import digest, save
from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_pilot_supervisor import (SERIAL, DEVICE, B_SERIAL, B_DEVICE,
    RESTORE_SHA, RESTORE_REVISION, finished, idle, configuration)
from phase11_5_network_fixture import HOST_BOOT

ROOT = Path('/home/pi/phase11-5-r2-modes-049cc92')
BOOT = '76e562d473a426c864d7cdb7bbee98f9'
PACKET = '3bb5b7f640477062a9fc9e51866aaddd9c5d055e84f17ca7eb122304304e2a62'
FAULT = (5, 3833354787, 0, 0)


def admission(current, baseline, comparator, original_b):
    info, status = current['info'], current['wtp']['STATUS']
    require(info['device_id'] == DEVICE and info['revision'] == '049cc929143b' and
            info['system_clock_hz'] == 138000000 and
            info['status']['engine'] == 'pio-dma-gp2', 'Preserved candidate changed')
    require(info['status']['boot_id'] == status['boot_id'] == BOOT and
            info['recovery_boot'] is True and
            tuple(info[k] for k in ('fault_stage','fault_hash','fault_pc','fault_status')) == FAULT,
            'Not the recorded WSPR LOAD OOM recovery boot')
    for observed in (info['status'], status):
        require(observed['state'] == 'empty' and observed['output_active'] is False,
                'Output is not authoritatively idle')
    require(status['owner_id'] is None and status['job_id'] is None and
            status['terminal_records'] == [] and info['status']['enabled'] is False and
            info['status']['last_error'] is None and info['status']['storage_healthy'] is True,
            'Recovery state changed')
    actual, expected = configuration(current), configuration(baseline)
    require(actual[0] == expected[0] and all(actual[1][key] == expected[1][key]
            for key in ('configured_hostname','control_configured')), 'Configuration changed')
    # Recovery deliberately skips CYW43 initialization, so its runtime MAC is
    # empty. Persisted hostname/control settings must still match the baseline.
    require(info['network']['initialized'] is False and
            info['network']['control_listening'] is False and
            info['network']['station_mac'] == '', 'Not the network-free recovery state')
    idle(comparator)
    require(comparator['info']['device_id'] == B_DEVICE and
            comparator['info']['revision'] == original_b['info']['revision'] and
            comparator['wtp']['STATUS']['boot_id'] == original_b['wtp']['STATUS']['boot_id'] and
            configuration(comparator) == configuration(original_b), 'Comparator changed')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', action='store_true')
    args = p.parse_args()
    if not args.run:
        print('Plan only: exactly one original CONFIG and original inhibited flash; no device access.')
        return
    require(sys.platform == 'linux' and os.geteuid() == 0, 'wspr5 root required')
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == HOST_BOOT,
            'Host rebooted')
    os.umask(0o077)
    with (ROOT/'device.lock').open('a') as lock, (ROOT/'management.lock').open('a') as mlock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(mlock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fixture = DeviceFixture(ROOT)
        fixture.verify_helpers()
        require(digest(ROOT/'packet.json') == PACKET and
                digest(ROOT/'original-config.json') == ORIGINAL_CONFIG_SHA and
                digest(ROOT/'original.uf2') == RESTORE_SHA, 'Frozen recovery input changed')
        state_path = ROOT/'management-state.json'
        management = json.loads(state_path.read_text())
        require(not management.get('pending') and not management.get('blocked') and
                management['counts'] == {'config':31,'wifi-off':0,'wifi-on':0,'heap-probe':6},
                'Unresolved write or changed budget')
        require(not fixture.state.get('pending') and not fixture.state.get('restored') and
                fixture.state['boot'] == '04aa04ade8232652055f5409d4e9d006',
                'Prior device transition changed')
        require(json.loads((ROOT/'fixture-state.json').read_text()).get('restored') is True,
                'Host fixture not restored')
        baseline = finished(ROOT/'candidate-physical-boot.stdout', 'READ_ONLY_INVENTORY')
        original = finished(ROOT/'before-a.stdout', 'READ_ONLY_INVENTORY')
        original_b = finished(ROOT/'before-b.stdout', 'READ_ONLY_INVENTORY')
        # The panic evidence and failed attempt remain intact. This distinct
        # one-shot record is created before any recovery mutation.
        with (ROOT/'oom-recovery-start.json').open('x') as stream:
            json.dump({'helper_sha256':digest(Path(__file__)), 'boot':BOOT,
                       'fault':FAULT, 'packet_sha256':PACKET,
                       'started_monotonic_ns':time.monotonic_ns()}, stream)
            stream.flush(); os.fsync(stream.fileno())
        current = fixture.inventory('oom-recovery-before-a')
        comparator = fixture.inventory('oom-recovery-before-b', B_SERIAL, B_DEVICE)
        admission(current, baseline, comparator, original_b)
        value = json.loads((ROOT/'original-config.json').read_text())
        require(value['enabled'] is False and value['expires_utc_s'] == 0,
                'Original autonomous scheduling not disabled')
        command = ('CONFIG '+json.dumps(value,separators=(',',':'),ensure_ascii=True)+'\n').encode()
        require(len(command) <= 1810, 'Original CONFIG size')
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as fd:
            fresh = exchange(fd,b'INFO\n',time.monotonic()+5,fixture.note,False)
            admission(dict(current,info=fresh),baseline,comparator,original_b)
            management['counts']['config'] += 1
            management['pending'] = {'action':'config','variant':'original','recovery_boot':BOOT}
            save(state_path,management)
            try:
                reply = exchange(fd,command,time.monotonic()+10,fixture.note,False)
                require(reply.get('ok') is True and reply['boot_id'] == BOOT and
                        reply['watermark_utc_ns'] == original['info']['status']['watermark_utc_ns'] and
                        all(reply[k] == value[k] for k in ('enabled','station','schedules','expires_utc_s')),
                        'Original CONFIG not acknowledged exactly')
                management['last_result'] = {'action':'config','reply':reply,'recovery':True}
                management['pending'] = None
                save(state_path,management)
            except BaseException:
                management['blocked'] = True
                save(state_path,management)
                raise
        # CONFIG does not change boot. Repeat both output authorities before
        # BOOTSEL, accepting only the same explicitly reconciled panic.
        configured = fixture.inventory('oom-recovery-configured-a')
        admission(configured,baseline,comparator,original_b)
        after = fixture.flash('original','recovered-original')
        require(after['info']['revision'] == RESTORE_REVISION and
                configuration(after) == configuration(original), 'Original restoration mismatch')
        after_b = fixture.inventory('oom-recovery-after-b',B_SERIAL,B_DEVICE)
        idle(after_b)
        require(after_b['wtp']['STATUS']['boot_id'] == original_b['wtp']['STATUS']['boot_id'] and
                after_b['info']['revision'] == original_b['info']['revision'] and
                configuration(after_b) == configuration(original_b), 'Comparator final mismatch')
        import subprocess
        timer = fixture.state['unit']+'.timer'
        description = subprocess.check_output(['systemctl','show',timer,'-p','Description','--value'],
                                              text=True,timeout=5).strip()
        require(description == fixture.state['token'], 'Restoration timer ownership changed')
        fixture.run('oom-recovery-stop-timer',['systemctl','stop',timer],15)
        fixture.remember(restored=True,recovery='WSPR LOAD OOM',recovery_boot=BOOT)
        fixture.management_baseline()
        save(ROOT/'oom-recovery-result.json', {'result':'RESTORED_INHIBITED',
             'original_uf2_sha256':RESTORE_SHA,'original_config_sha256':ORIGINAL_CONFIG_SHA,
             'a_boot':after['wtp']['STATUS']['boot_id'],'b_boot':after_b['wtp']['STATUS']['boot_id'],
             'counts':management['counts'],'output_active':False,'resumed_jobs':False})


if __name__ == '__main__':
    main()
