#!/usr/bin/env python3
"""Explicitly authorized B-only deployment. No LOAD, ARM, or A endpoint access."""
import argparse
import errno
import json
import os
from pathlib import Path
import re
import subprocess
import time

from phase11_5_inventory import require, exclusive_port, exchange
from phase11_5_pilot_supervisor import B_SERIAL, B_DEVICE, PICOTOOL, PICOTOOL_SHA, finished
from phase11_5_r3_allocation_diagnostic import inactive, saved_configuration
from phase11_5_device_management import digest, save

SCHEMA = 'phase11.5-r3-v2-parallel-b-deploy-v1'
SOURCE = 'c5f00b6109cc1c692b3f6bf258c1a77dadef6639'
IMAGE = 'b36f8d524cb0659107e82a41a3f8d15973fda80b843ef6909fe1a448b6ff3c6b'
AUTHORIZATION = '37ae5f5658ffc7c4436547061e4a81e577ea9102a086ec1e74d09031699caaab'
DURATION = 3600_000_000_000


def validate(packet):
    require(packet['schema'] == packet['r3_scope'] == SCHEMA and packet['serial'] == B_SERIAL and
            packet['device_id'] == B_DEVICE and packet['source_revision'] == SOURCE and
            packet['authorization_sha256'] == AUTHORIZATION, 'B-only authorized identity')
    for key, expected in dict(runtime_seconds=300, cleanup_seconds=150, flashes=1,
            bootsel_commands=1, rf_jobs=0, arm_commands=0, loads=0,
            configuration_writes=0, wifi_cycles=0).items():
        require(type(packet[key]) is int and packet[key] == expected, 'Exact B budget: '+key)
    require(packet['prior_revision'] == 'dbf1d86f0885-dirty' and
            packet['prior_boot'] == 'feffcd075ab6cb0b74e7e0c2fde6c87f', 'B initial image')
    require(packet['image_sha256'] == IMAGE and
            re.fullmatch('[0-9a-f]{32}', packet['inventory_session']) and
            packet['inventory_session'] != '0'*32, 'Image/session identity')
    require(packet['image_file'] == 'candidate.uf2' and
            packet['root'].startswith('/home/pi/phase11-5-r3-v2-parallel-b-deploy-') and
            '..' not in Path(packet['root']).parts and str(Path(packet['root'])) == packet['root'],
            'Private fresh B root')
    require(len(packet['predecessors']) == 2 and
            {p['name'] for p in packet['predecessors']} == {'H2b','E1'}, 'Both unchanged-B gates required')
    return packet


def validate_stage(root, packet):
    required = {'scripts/phase11_5_r3_v2_parallel_b_deploy.py',
                'scripts/phase11_5_inventory.py', 'docs/protocol/wtp-1.schema.json'}
    require(required <= packet['stage_sha256'].keys(), 'Missing dependency manifest')
    for name, expected in packet['stage_sha256'].items():
        path = root/name
        require(path.resolve().is_relative_to(root) and path.is_file() and digest(path) == expected,
                'Missing or changed stage dependency: '+name)
    json.loads((root/'docs/protocol/wtp-1.schema.json').read_text())


def predecessors_complete(packet):
    for gate in packet['predecessors']:
        path = Path(gate['audit_file'])
        require(path.is_absolute() and digest(path) == gate['audit_sha256'], 'Prior audit missing/changed')
        # The launcher freezes independently audited artifacts only after original
        # finite supervisors finish. Recheck both units and original final B boot.
        state = subprocess.check_output(['systemctl','show',gate['unit'],
            '-p','ActiveState','-p','MainPID'],text=True,timeout=5)
        require('MainPID=0' in state.splitlines() and 'ActiveState=inactive' in state.splitlines(),
                'Unchanged-B predecessor still active')
        final = finished(Path(gate['final_b_file']), 'READ_ONLY_INVENTORY')
        inactive(final)
        require(final['wtp']['STATUS']['boot_id'] == packet['prior_boot'] and
                final['info']['revision'] == packet['prior_revision'], 'Prior B gate identity')


def request_b_bootsel(emit):
    acknowledged = False
    try:
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{B_SERIAL}-if00')) as fd:
            reply = exchange(fd, b'BOOTSEL\n', time.monotonic()+5, emit, False)
            require(reply.get('ok') is True and reply.get('rebooting') is True, 'B BOOTSEL ACK')
            emit('bootsel_acknowledged', reply)
            acknowledged = True
    except OSError as error:
        if not acknowledged or error.errno not in (errno.EIO, errno.ENODEV):
            raise
        emit('bootsel_disconnect_cleanup', dict(errno=error.errno))


def candidate(value, packet, *, boot=None):
    inactive(value)
    info = value['info']; status = value['wtp']['STATUS']; caps = value['wtp']['CAPS']
    require(info['device_id'] == B_DEVICE and info['revision'] == packet['source_revision'][:12] and
            info['status']['boot_id'] == status['boot_id'] and (boot is None or status['boot_id'] == boot) and
            info['recovery_boot'] is False and info['fault_allocation_recorded'] is False and
            info['fault_allocation_returned_null'] is None and info['system_clock_hz'] == 138000000 and
            info['status']['engine'] == 'pio-dma-gp2' and info['rf_render_in_ram'] is True and
            all(info[k] == 0 for k in ('fault_stage','fault_hash','fault_pc','fault_status')) and
            int(info['allocator_failures']) == 0 and
            info['heap_capacity_bytes'] - info['allocator_peak_bytes'] >= 32768 and
            caps['max_events'] == 512 and int(caps['max_job_duration_ns']) == DURATION and
            caps['max_payload_bytes'] == 65536, 'Extended candidate identity/capacity/resource')
    for core in (0,1):
        require(type(info[f'core{core}_stack_guard_valid']) is int and
                info[f'core{core}_stack_guard_valid'] == 1 and info[f'core{core}_stack_fault_status'] == 0 and
                info[f'core{core}_stack_guard_limit'] - info[f'core{core}_stack_guard_bottom'] == 4096,
                'Extended candidate stack guards')
    require(all(int(info[k]) == 0 for k in ('launch_epoch','dma_irqs','alarm_irqs','tail_irqs')),
            'Idle packet unexpectedly executed RF')
    return status['boot_id']


def run(root, packet):
    deadline = time.monotonic()+packet['runtime_seconds']
    cleanup_deadline = deadline+packet['cleanup_seconds']
    result = dict(status='RUNNING', bootsel_commands=0, flashes_started=0,
                  rf_jobs=0, arm_commands=0, loads=0, configuration_writes=0, wifi_cycles=0)
    log = (root/'deployment.jsonl').open('x'); sequence = 0
    def emit(kind, value):
        nonlocal sequence
        log.write(json.dumps(dict(sequence=sequence,kind=kind,value=value,
            monotonic_ns=time.monotonic_ns(),utc_ns=time.time_ns()))+'\n')
        log.flush(); os.fsync(log.fileno()); sequence += 1
    def inventory(label, cleanup=False):
        require(time.monotonic()+65 < (cleanup_deadline if cleanup else deadline), 'B inventory budget')
        with (root/(label+'.stdout')).open('xb') as out, (root/(label+'.stderr')).open('xb') as err:
            code = subprocess.run(['python3',str(root/'scripts/phase11_5_inventory.py'),
                '--serial',B_SERIAL,'--device-id',B_DEVICE,'--session-id',packet['inventory_session'],
                '--run'],stdout=out,stderr=err,timeout=65).returncode
        require(code == 0, 'B inventory failed: '+label)
        return finished(root/(label+'.stdout'),'READ_ONLY_INVENTORY')
    before = after = None
    try:
        emit('start', dict(packet_sha256=digest(root/'packet.json')))
        before = inventory('before-b'); inactive(before)
        require(before['info']['device_id'] == B_DEVICE and
                before['wtp']['STATUS']['boot_id'] == packet['prior_boot'] and
                before['info']['revision'] == packet['prior_revision'], 'Fresh B identity')
        require(digest(PICOTOOL) == PICOTOOL_SHA and
                digest(root/packet['image_file']) == packet['image_sha256'], 'Image/tool changed')
        result['bootsel_commands'] = 1; save(root/'deployment-result.json',result)
        emit('bootsel_pending', dict(serial=B_SERIAL)); request_b_bootsel(emit)
        end = min(deadline, time.monotonic()+15); found = False
        while time.monotonic() < end and not found:
            for path in Path('/sys/bus/usb/devices').glob('*/serial'):
                try:
                    found |= (path.read_text().strip().upper() == B_SERIAL and
                        (path.parent/'idVendor').read_text().strip() == '2e8a' and
                        (path.parent/'idProduct').read_text().strip() == '000f')
                except OSError: pass
            if not found: time.sleep(.2)
        require(found and time.monotonic()+125 < deadline, 'B bootloader or flash budget missing')
        result['flashes_started'] = 1; save(root/'deployment-result.json',result)
        command = [str(PICOTOOL),'load','-v','-x',str(root/packet['image_file']),'--ser',B_SERIAL]
        emit('flash_pending',dict(argv=command,sha256=packet['image_sha256']))
        with (root/'flash.stdout').open('xb') as out, (root/'flash.stderr').open('xb') as err:
            code = subprocess.run(command,stdout=out,stderr=err,timeout=60).returncode
        emit('flash_exit',dict(exit=code)); require(code == 0, 'B flash failed; no retry')
        end = min(deadline, time.monotonic()+15)
        port = Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{B_SERIAL}-if00')
        while not port.exists() and time.monotonic() < end: time.sleep(.2)
        require(port.exists(),'B application enumeration missing')
        after = inventory('after-flash-b'); boot = candidate(after,packet)
        require(boot != packet['prior_boot'] and saved_configuration(after) == saved_configuration(before),
                'B configuration retention/new boot')
        result.update(status='OBSERVED_REQUIRES_INDEPENDENT_AUDIT', boot_id=boot)
    except BaseException as error:
        result.update(status='STOPPED_REQUIRES_DIAGNOSIS',error=type(error).__name__+': '+str(error))
        emit('failure',result['error'])
    finally:
        try:
            final = inventory('final-b',cleanup=True); inactive(final)
            require(before is not None and saved_configuration(final) == saved_configuration(before),
                    'Saved B configuration changed')
            if after is not None: candidate(final,packet,boot=after['wtp']['STATUS']['boot_id'])
            else:
                require(result['flashes_started'] == 0 and
                        final['wtp']['STATUS']['boot_id'] == packet['prior_boot'], 'B image/output unresolved')
            result['final_b'] = final['wtp']['STATUS']
        except BaseException as error:
            result.update(status='STOPPED_FINAL_STATE_UNVERIFIED',final_b_error=str(error))
        emit('finish',result); save(root/'deployment-result.json',result); log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--packet-sha256',required=True)
    parser.add_argument('--run',action='store_true'); args=parser.parse_args()
    if not args.run:
        print('Plan only; no device or filesystem changes.'); return
    require(os.geteuid() == 0, 'wspr5 root required'); os.umask(0o077)
    root=args.root.resolve(strict=True)
    require(digest(root/'packet.json') == args.packet_sha256, 'Packet changed')
    packet=validate(json.loads((root/'packet.json').read_text()))
    require(packet['root'] == str(root), 'Root changed'); validate_stage(root,packet)
    predecessors_complete(packet)
    with (root/'deployment-result.json').open('x') as stream:
        json.dump(dict(status='STARTING'),stream)
    run(root,packet)


if __name__ == '__main__': main()
