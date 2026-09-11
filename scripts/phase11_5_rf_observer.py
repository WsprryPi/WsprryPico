#!/usr/bin/env python3
"""Opt-in physical observer; read-only USB and health for frozen A3 or F1 jobs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

from phase11_5_pilot import check_rf_observation
from phase11_5_f1_plan import validate_rf_packet as validate_packet,SCHEMA as F1_SCHEMA,NOMINAL_SECONDS
from phase11_5_inventory import exclusive_port, exchange, require, inventory_session
from phase11_5_network_fixture import HOST_BOOT
from phase11_5_pilot import DEVICE, SERIAL, Peer, check_status
from phase11_5_pilot_supervisor import finished
from phase11_5_device_management import save


def validate_info(info, baseline):
    old=baseline['info']
    require(info['ok'] is True and info['device_id']==old['device_id']==DEVICE and
            info['revision']==old['revision']=='8fb3894253ef' and
            info['system_clock_hz']==138000000 and
            info['status']['boot_id']==old['status']['boot_id'] and
            info['status']['engine']=='pio-dma-gp2' and info['rf_render_in_ram'] is True,
            'Physical identity changed')
    require(not info['recovery_boot'] and not info['engine_diagnostic'] and
            all(info[k]==0 for k in ('fault_stage','fault_hash','fault_pc','fault_status')) and
            info['status']['storage_healthy'] is True and info['status']['enabled'] is False and
            info['status']['last_error'] is None and
            info['status']['watermark_utc_ns']==old['status']['watermark_utc_ns'],
            'Firmware fault/configuration change')
    for core in (0,1):
        p=f'core{core}_stack_'
        require(type(info[p+'guard_valid']) is int and info[p+'guard_valid']==1 and
                info[p+'fault_status']==0 and info[p+'guard_bottom']==old[p+'guard_bottom'] and
                info[p+'guard_limit']==old[p+'guard_limit']==info[p+'guard_bottom']+4096,
                'Stack reserve or fault')
    require(type(info['status']['output_active']) is bool and
            info['status']['state'] in ('empty','loaded','armed','running','complete') and
            (info['status']['state']=='running' or info['status']['output_active'] is False),
            'Unexpected job/output state')
    require(info['heap_capacity_bytes']-info['allocator_peak_bytes']>=32768 and
            info['allocator_failures']==old['allocator_failures'] and
            info['tls_allocation_failures']==old['tls_allocation_failures'],
            'Nominal allocation failure or lost heap reserve')
    check_rf_observation(info)


def validate_status(value, boot, packet):
    require(value['boot_id']==boot and type(value['output_active']) is bool and
            value['state'] in ('empty','loaded','armed','running','complete'), 'WTP boot/state')
    require(value['state']=='running' or not value['output_active'],'WTP output/state')
    if value['state']=='empty':
        require(value['job_id'] is None and value['owner_id'] in (None,packet['owner_id']),
                'Unexpected empty ownership')
    else:
        require(value['job_id'] in {j['job_id'] for j in packet['jobs']} and
                value['owner_id']==packet['owner_id'],'Unexpected job/owner')


def validate_event(value,boot,packet):
    require(value['boot_id']==boot and value['event'] in ('JOB_STATE','OWNER_RELEASED'),
            'Unexpected device event or fault')
    body=value['body']
    if value['event']=='OWNER_RELEASED':
        require(body['owner_id']==packet['owner_id'] and body['output_active'] is False,
                'Foreign owner release or active output')
    else:
        require('error' not in body and body['state'] in ('empty','loaded','armed','running','complete') and
                (body['job_id'] is None if body['state']=='empty' else
                 body['job_id'] in {j['job_id'] for j in packet['jobs']}) and
                (body['state']=='running' or body['output_active'] is False),'Unexpected job event')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--seconds', type=int, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    require(1 <= args.seconds <= NOMINAL_SECONDS+60, 'Bounded interval required')
    session = inventory_session(args.session_id)
    if not args.run:
        print('Plan only; no host or device accessed.')
        return
    require(os.geteuid() == 0 and Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            == HOST_BOOT, 'Expected wspr5 root and boot required')
    os.umask(0o077)
    packet=json.loads(args.packet.read_text());validate_packet(packet)
    require(args.seconds==(NOMINAL_SECONDS+60 if packet['schema']==F1_SCHEMA else 240),'Frozen RF observation interval')
    packet_sha=hashlib.sha256(args.packet.read_bytes()).hexdigest()
    pid_start=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]
    require(packet['revision']=='8fb3894253ef' and inventory_session(packet['owner_id'])==packet['owner_id'],
            'Frozen RF packet identity')
    baseline = finished(args.baseline, 'READ_ONLY_INVENTORY')
    validate_info(baseline['info'], baseline)
    boot = baseline['info']['status']['boot_id']
    require(packet['boot_id']==boot,'Packet boot changed')
    stop = threading.Event()
    lock = threading.Lock()
    faults = []
    sequence = 0
    end = time.monotonic() + args.seconds
    with args.output.open('x') as log:
        def emit(kind, value):
            nonlocal sequence
            with lock:
                log.write(json.dumps(dict(sequence=sequence, kind=kind, value=value,
                    monotonic_ns=time.monotonic_ns(), utc_ns=time.time_ns())) + '\n')
                log.flush(); os.fsync(log.fileno()); sequence += 1
                if kind in ('info','status','failure','finish'):
                    save(args.output.parent/('observer-'+kind+'.json'),dict(
                        value=value,monotonic_ns=time.monotonic_ns(),pid=os.getpid(),
                        pid_start_ticks=pid_start,packet_sha256=packet_sha))

        def checkpoint():
            require(not faults, 'Independent observer failed')
            require(hashlib.sha256(args.packet.read_bytes()).hexdigest()==packet_sha,'RF packet changed')

        def interrupted(signum, frame):
            faults.append('signal ' + str(signum)); stop.set()
        signal.signal(signal.SIGTERM, interrupted)
        signal.signal(signal.SIGINT, interrupted)

        def periodic(name, interval, read):
            count = 0
            next_at = time.monotonic()
            last = None
            while time.monotonic() < end and not stop.is_set():
                began = time.monotonic()
                require(began - next_at <= 1, name + ' sampling fell behind')
                require(last is None or began - last <= interval + 1, name + ' gap')
                value = read()
                emit(name, dict(began_monotonic_ns=int(began * 1e9), value=value))
                last = began; count += 1; next_at += interval
                stop.wait(max(0, min(next_at, end) - time.monotonic()))
            emit(name + '_finish', dict(samples=count, completed=not stop.is_set()))

        def console():
            with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as fd:
                def read():
                    value = exchange(fd, b'INFO\n', time.monotonic()+5,
                                     lambda k,v: emit('console_'+k,v), False)
                    validate_info(value, baseline)
                    return value
                periodic('info', 1, read)

        def wtp():
            with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02')) as fd:
                peer = Peer(fd, emit, checkpoint, boot); peer.session = session
                hello = peer.request('HELLO', dict(versions=['WTP/1'],
                    client_name='phase11-5-idle-observer', client_version='1'))
                require(hello['device_id'] == DEVICE and hello['boot_id'] == boot, 'HELLO identity')
                def read():
                    value = peer.request('STATUS'); validate_status(value, boot, packet)
                    return value
                periodic('status', 5, read)

        def health():
            def read():
                require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == HOST_BOOT,
                        'Host boot changed')
                result = subprocess.run(['vcgencmd','get_throttled'], capture_output=True,
                                        text=True, timeout=2, check=True)
                require(result.stdout.strip() == 'throttled=0x0', 'Host throttling')
                return dict(boot=HOST_BOOT, throttled=result.stdout.strip(),
                    loadavg=Path('/proc/loadavg').read_text().strip(),
                    meminfo=Path('/proc/meminfo').read_text(),
                    temperature=Path('/sys/class/thermal/thermal_zone0/temp').read_text().strip())
            periodic('health', 5, read)

        def worker(name, fn):
            try: fn()
            except BaseException as error:
                faults.append(name + ': ' + str(error))
                emit('failure', dict(worker=name, type=type(error).__name__, error=str(error)))
                stop.set()

        emit('start', dict(seconds=args.seconds, boot=boot, session_id=session,
            baseline_sha256=hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
            helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            packet_sha256=hashlib.sha256(args.packet.read_bytes()).hexdigest()))
        threads = [threading.Thread(target=worker,args=(name,fn))
                   for name,fn in [('console',console),('wtp',wtp),('health',health)]]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        emit('finish', dict(result='FAILED' if faults else 'CAPTURED_REQUIRES_AUDIT', faults=faults))
        require(not faults, 'Idle observer failed; stop dependent campaign actions')


if __name__ == '__main__': main()
