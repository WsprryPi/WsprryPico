#!/usr/bin/env python3
"""Separately authorized candidate lifecycle; no RF jobs or fault recovery.

Start backs up A, verifies its original application/configuration, arms a local
restoration timer, then installs the inhibited candidate and isolated settings.
Switch requires the inhibited baseline to be authoritatively idle. Restore
requires the last recorded boot to remain safe and inactive, restores original
settings and the original inhibited image, and verifies comparator B unchanged.
Unknown writes, boots, firmware faults or output block device restoration.
Host-only N0 cleanup remains independent and does not reset the device.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import struct
import subprocess
import sys
import time
import zlib

from phase11_5_inventory import exclusive_port, exchange, require, inventory_session
from phase11_5_pilot import SERIAL, DEVICE
from phase11_5_pilot_supervisor import (B_SERIAL, B_DEVICE, PICOTOOL, PICOTOOL_SHA,
    RESTORE_SHA, RESTORE_REVISION, finished, idle, configuration, verify_application_backup)
from phase11_5_device_management import SOURCE, admit, digest, save
from phase11_5_network_fixture import Fixture, HOST_BOOT, PREFIX as HOST_PREFIX, RUN_SECONDS

IMAGES = {
    'inhibited': ('inhibited.uf2', '0a7d54673e7171ee10275272701de5fbb3cecdc91c097a18eeae496c0922c7b9'),
    'physical': ('physical.uf2', 'cb91912f7915db7828c5f58ea2a35c714c22728ee71f9ce04c7d034d22598154'),
    'original': ('original.uf2', RESTORE_SHA),
}
ORIGINAL_CONFIG_SHA = '2978a00337f174286085251ec12ea15d0e524652738e009af3eb64e3be4ca0bf'
SECONDS = 18000
HELPERS = {'scripts/'+name+'.py' for name in (
    'phase11_5_device_fixture', 'phase11_5_device_management', 'phase11_5_inventory',
    'phase11_5_pilot', 'phase11_5_pilot_supervisor', 'phase11_5_network_fixture',
    'phase11_4_hotspot', 'phase11_5_network_fault', 'validate_wtp_contract',
    'wtp_monitor')} | {'docs/protocol/wtp-1.schema.json'}


def journal_config(backup):
    candidates = []
    for start in range(0x3fb000, 0x3fd000, 2048):
        record = backup[start:start+2048]
        require(len(record) == 2048, 'Incomplete configuration journal backup')
        if record == b'\xff'*2048: continue
        require(struct.unpack_from('<Q', record, 0)[0] == 0x32524f5453505757 and
                zlib.crc32(record[:-4]) == struct.unpack_from('<I', record, 2044)[0],
                'Invalid journal record; do not resurrect an older configuration')
        length = struct.unpack_from('<I', record, 16)[0]
        sequence = struct.unpack_from('<Q', record, 8)[0]
        require(0 < length <= 1984 and sequence > 0 and
                all(previous[0] != sequence for previous in candidates),
                'Configuration journal length/sequence')
        candidates.append((sequence,
                           json.loads(record[32:32+length])))
    require(bool(candidates), 'No CRC-valid saved configuration')
    return max(candidates, key=lambda item: item[0])


class DeviceFixture:
    def __init__(self, root):
        self.root = root
        self.path = root / 'device-state.json'
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {}

    def note(self, kind, value):
        with (self.root / 'device-fixture.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(kind=kind, value=value,
                utc_ns=time.time_ns(), monotonic_ns=time.monotonic_ns()))+'\n')
            stream.flush(); os.fsync(stream.fileno())

    def remember(self, **changes):
        self.state.update(changes)
        save(self.path, self.state)

    def run(self, label, argv, timeout=65):
        self.note('command_start', {'label':label, 'program':str(argv[0])})
        with (self.root/(label+'.stdout')).open('xb') as out, \
             (self.root/(label+'.stderr')).open('xb') as err:
            result = subprocess.run([str(arg) for arg in argv], stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=err, timeout=timeout)
            out.flush(); os.fsync(out.fileno()); err.flush(); os.fsync(err.fileno())
        self.note('command_exit', {'label':label, 'exit':result.returncode})
        require(result.returncode == 0, label+' failed; no automatic retry')

    def inventory(self, label, serial=SERIAL, device=DEVICE):
        session = self.state.get('inventory_session_id') if serial == SERIAL else None
        if self.state and serial == SERIAL:
            require(type(session) is str, 'Missing persistent administration session')
            session = inventory_session(session)
        self.run(label, [sys.executable, Path(__file__).with_name('phase11_5_inventory.py'),
                        '--serial',serial,'--device-id',device,
                        *(['--session-id',session] if session else []),'--run'])
        return finished(self.root/(label+'.stdout'), 'READ_ONLY_INVENTORY')

    def console(self, command):
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as fd:
            reply = exchange(fd, (command+'\n').encode(), time.monotonic()+10, self.note, False)
            require(reply.get('ok') is True, 'Console command rejected')
            return reply

    def flash(self, kind, label):
        filename, expected = IMAGES[kind]
        require(digest(self.root/filename) == expected, 'Firmware artifact changed')
        self.remember(pending='BOOTSEL for '+kind)
        reply = self.console('BOOTSEL')
        require(reply.get('rebooting') is True, 'BOOTSEL not acknowledged')
        end = time.monotonic()+15
        while time.monotonic() < end:
            found = False
            for serial in Path('/sys/bus/usb/devices').glob('*/serial'):
                try:
                    found |= (serial.read_text().strip().upper() == SERIAL and
                              (serial.parent/'idVendor').read_text().strip() == '2e8a' and
                              (serial.parent/'idProduct').read_text().strip() == '000f')
                except OSError:
                    continue
            if found: break
            time.sleep(.2)
        require(found, 'Serial-specific BOOTSEL enumeration missing')
        if kind == 'inhibited':
            self.run('original-backup', [PICOTOOL,'save','-a','-v',self.root/'before-flash.bin',
                                        '-t','bin','--ser',SERIAL])
            backup = (self.root/'before-flash.bin').read_bytes()
            blocks = verify_application_backup((self.root/'original.uf2').read_bytes(), backup)
            sequence, config = journal_config(backup)
            require(config == json.loads((self.root/'original-config.json').read_text()),
                    'Current saved configuration differs from frozen original')
            self.note('backup_verified', {'blocks':blocks, 'configuration_sequence':sequence,
                                         'sha256':digest(self.root/'before-flash.bin')})
        self.remember(pending='load '+kind)
        self.run(label+'-load', [PICOTOOL,'load','-v','-x',self.root/filename,'--ser',SERIAL])
        self.wait_application()
        current = self.inventory(label+'-boot')
        idle(current)
        expected_revision = RESTORE_REVISION if kind == 'original' else SOURCE[:12]
        require(current['info']['revision'] == expected_revision and
                current['info']['status']['engine'] == ('pio-dma-gp2' if kind == 'physical'
                    else 'inhibited-standalone-simulator'), 'Flashed image admission')
        require(current['info']['status']['boot_id'] != self.state.get('boot'), 'Boot did not change')
        if kind != 'original': admit(current, current)
        self.remember(pending=None, kind=kind, baseline=label+'-boot.stdout',
                      boot=current['info']['status']['boot_id'])
        return current

    def wait_application(self):
        end = time.monotonic()+15
        path = Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')
        while not path.exists() and time.monotonic() < end: time.sleep(.2)
        require(path.exists(), 'Application USB did not enumerate')

    def management_baseline(self):
        path = self.root/'management-state.json'
        state = json.loads(path.read_text())
        state['baseline_sha256'] = digest(self.root/self.state['baseline'])
        save(path, state)

    def manage(self, variant, label):
        self.management_baseline()
        self.run(label, [sys.executable, Path(__file__).with_name('phase11_5_device_management.py'),
                        'config','--root',self.root,'--baseline',self.root/self.state['baseline'],
                        '--variant',variant,'--run'], 90)

    def check_current(self, label):
        require(not self.state.get('pending'), 'Pending device transition; reconciliation required')
        old = finished(self.root/self.state['baseline'], 'READ_ONLY_INVENTORY')
        current = self.inventory(label)
        admit(current, old)
        return current

    def verify_helpers(self):
        require(Path(__file__).resolve() == self.root/'scripts/phase11_5_device_fixture.py',
                'Run only the staged lifecycle helper')
        packet = json.loads((self.root/'packet.json').read_text())
        require(packet['source_revision'] == SOURCE and type(packet['runtime_seconds']) is int and
                0 < packet['runtime_seconds'] <= SECONDS and
                packet['serial'] == SERIAL and packet['device_id'] == DEVICE and
                packet['root'] == packet['network_root'] == str(self.root), 'Lifecycle packet')
        require(packet['host_boot_id'] == HOST_BOOT ==
                Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'Host boot changed')
        require(set(packet['helper_sha256']) == HELPERS, 'Incomplete helper identity set')
        for relative, expected in packet['helper_sha256'].items():
            path = self.root/relative
            require(path.resolve().is_relative_to(self.root) and digest(path) == expected,
                    'Helper identity changed')
        for filename, expected in IMAGES.values():
            require(digest(self.root/filename) == expected, 'Firmware identity changed')
        require(digest(PICOTOOL) == PICOTOOL_SHA and
                digest(self.root/'original-config.json') == ORIGINAL_CONFIG_SHA,
                'Restoration input identity changed')
        return packet

    def start(self):
        require(not self.state, 'Fresh lifecycle required')
        packet = self.verify_helpers()
        seconds = packet['runtime_seconds']
        counts = {'config':0,'wifi-off':0,'wifi-on':0,'heap-probe':0}
        prior = packet.get('prior_restored_attempt')
        if prior:
            old_root = Path(prior['root'])
            old_device = old_root/'device-state.json'
            old_management = old_root/'management-state.json'
            require(digest(old_device) == prior['device_state_sha256'] and
                    digest(old_management) == prior['management_state_sha256'], 'Prior evidence changed')
            previous = json.loads(old_device.read_text())
            management = json.loads(old_management.read_text())
            require(previous.get('restored') is True and not previous.get('pending') and
                    not management.get('pending') and not management.get('blocked') and
                    previous['boot'] == packet['initial_a_boot_id'] and
                    previous['host_boot'] == HOST_BOOT, 'Prior attempt not reconciled/restored')
            counts = management['counts']
            require(set(counts) == {'config','wifi-off','wifi-on','heap-probe'} and
                    all(type(n) is int and n >= 0 for n in counts.values()) and
                    counts['config'] <= 30 and counts['wifi-off'] <= 3 and
                    counts['wifi-on'] <= 3 and counts['heap-probe'] <= 64,
                    'Prior operation budgets do not admit continuation/restoration')
        host = Fixture(Path(packet['network_root']))
        host.verify()
        # Require the host fixture to outlive device restoration by ten minutes.
        stamp = subprocess.check_output(['systemctl','show',HOST_PREFIX+'-cleanup.timer',
            '-p','ActiveEnterTimestampMonotonic','--value'], text=True, timeout=5).strip()
        host_deadline = int(stamp)*1000 + host.state.get('runtime_seconds', RUN_SECONDS)*1_000_000_000
        now = time.monotonic_ns()
        require(host_deadline >= now+(seconds+1200)*1_000_000_000,
                'Insufficient remaining host-fixture time; do not touch device')
        space = os.statvfs(self.root)
        require(space.f_bavail*space.f_frsize >= 2 << 30, 'Less than two GiB evidence space')
        before_a, before_b = self.inventory('before-a'), self.inventory('before-b',B_SERIAL,B_DEVICE)
        idle(before_a); idle(before_b)
        require(before_a['info']['revision'] == RESTORE_REVISION and
                before_a['info']['status']['engine'] == 'inhibited-standalone-simulator',
                'Original A baseline changed')
        require(before_a['wtp']['STATUS']['boot_id'] == packet['initial_a_boot_id'] and
                before_b['wtp']['STATUS']['boot_id'] == packet['initial_b_boot_id'] and
                before_b['info']['revision'] == 'dbf1d86f0885-dirty' and
                before_b['info']['status']['engine'] == 'inhibited-standalone-simulator',
                'Frozen initial boot/comparator identity changed')
        unit = 'phase115-device-'+packet['attempt']
        require(packet['attempt'].isalnum() and len(packet['attempt']) <= 16, 'Attempt name')
        for suffix in ('.timer','.service'):
            load = subprocess.check_output(['systemctl','show',unit+suffix,'-p','LoadState',
                                            '--value'], text=True, timeout=5).strip()
            require(load == 'not-found', 'Restoration unit already exists')
        token = 'Phase115 device '+secrets.token_hex(16)
        self.remember(host_boot=HOST_BOOT, token=token, unit=unit,
                      deadline_monotonic_ns=now+seconds*1_000_000_000, pending=None,
                      cleanup_intent=True, inventory_session_id=secrets.token_hex(16))
        shutil.copyfile(Path(packet['network_root'])/'pico-wifi.json', self.root/'test-wifi.json')
        save(self.root/'management-state.json', dict(host_boot=HOST_BOOT,
            deadline_monotonic_ns=now+seconds*1_000_000_000,
            restoration_deadline_monotonic_ns=now+(seconds+600)*1_000_000_000,
            restoration_unit=unit+'.timer', restoration_token=token,
            inventory_session_id=self.state['inventory_session_id'],
            original_config_sha256=ORIGINAL_CONFIG_SHA,
            test_wifi_sha256=digest(self.root/'test-wifi.json'),
            pending=None, blocked=False, counts=counts))
        self.run('arm-restoration', ['systemd-run','--quiet','--unit='+unit,
            '--description='+token,'--on-active='+str(seconds)+'s','--property=UMask=0077',
            '--property=RuntimeMaxSec=600','--property=TimeoutStartSec=600',
            '--property=StandardOutput=append:'+str(self.root/'automatic-restoration.log'),
            '--property=StandardError=append:'+str(self.root/'automatic-restoration.log'),
            '/usr/bin/python3',Path(__file__).resolve(),'restore','--root',self.root,'--run'])
        self.flash('inhibited','candidate-inhibited')
        self.manage('test','configure-test')
        self.check_current('before-network-reboot')
        self.remember(pending='intentional configuration reboot')
        require(self.console('REBOOT').get('rebooting') is True, 'Reboot not acknowledged')
        # Require disappearance, not an old device node seen before reset.
        end = time.monotonic()+10
        path = Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')
        while path.exists() and time.monotonic() < end: time.sleep(.05)
        require(not path.exists(), 'Reboot disappearance not observed')
        self.wait_application()
        current = self.inventory('inhibited-network-boot')
        idle(current); admit(current,current)
        require(current['info']['status']['boot_id'] != self.state['boot'], 'Reboot did not change boot')
        self.remember(pending=None, baseline='inhibited-network-boot.stdout',
                      boot=current['info']['status']['boot_id'])
        self.management_baseline()
        self.note('ready_for_inhibited_baseline', {'boot':self.state['boot'],
                                                'network_reachability':'must be measured'})

    def switch(self):
        self.verify_helpers()
        require(self.state['kind'] == 'inhibited' and time.monotonic_ns() <
                self.state['deadline_monotonic_ns'], 'Physical switch admission')
        self.check_current('before-physical-switch')
        management = json.loads((self.root/'management-state.json').read_text())
        require(not management.get('pending') and not management.get('blocked'), 'Management unresolved')
        self.flash('physical','candidate-physical')
        self.management_baseline()
        self.note('ready_for_physical_baseline', {'boot':self.state['boot']})

    def restore(self):
        self.verify_helpers()
        require(self.state and not self.state.get('restored'), 'Lifecycle is absent or restored')
        current = self.check_current('restore-admission-a')
        before_b = finished(self.root/'before-b.stdout','READ_ONLY_INVENTORY')
        current_b = self.inventory('restore-admission-b',B_SERIAL,B_DEVICE)
        idle(current_b)
        require(current_b['wtp']['STATUS']['boot_id'] == before_b['wtp']['STATUS']['boot_id'] and
                current_b['info']['revision'] == before_b['info']['revision'] and
                configuration(current_b) == configuration(before_b), 'Comparator changed')
        self.manage('original','restore-config')
        self.check_current('after-restore-config')
        after_a = self.flash('original','restored-original')
        before_a = finished(self.root/'before-a.stdout','READ_ONLY_INVENTORY')
        require(configuration(after_a) == configuration(before_a), 'Original configuration differs')
        after_b = self.inventory('after-b',B_SERIAL,B_DEVICE); idle(after_b)
        require(after_b['wtp']['STATUS']['boot_id'] == before_b['wtp']['STATUS']['boot_id'] and
                configuration(after_b) == configuration(before_b), 'Comparator final state changed')
        timer = self.state['unit']+'.timer'
        description = subprocess.check_output(['systemctl','show',timer,'-p','Description','--value'],
                                              text=True, timeout=5).strip()
        require(description == self.state['token'], 'Restoration timer ownership changed')
        self.run('stop-restoration-timer', ['systemctl','stop',timer], 15)
        self.remember(restored=True)
        self.note('restored_inhibited', {'boot':after_a['info']['status']['boot_id'],
                                       'output_active':False, 'original_uf2_sha256':RESTORE_SHA})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('start','switch','restore'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        print('Plan only; no host or device accessed. Separate lifecycle authorization required.')
        return
    require(sys.platform == 'linux' and os.geteuid() == 0, 'wspr5 root required')
    os.umask(0o077)
    root = args.root.resolve(strict=True)
    require(root.is_dir() and root.stat().st_mode & 0o077 == 0, 'Private root required')
    with (root/'device.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fixture = DeviceFixture(root)
        try: getattr(fixture,args.stage)()
        except BaseException as error:
            fixture.note('failure', {'stage':args.stage,'type':type(error).__name__,
                                    'action':'STOP; no automatic device retry or fault clearing'})
            raise


if __name__ == '__main__': main()
