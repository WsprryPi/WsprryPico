#!/usr/bin/env python3
"""Opt-in bounded A2 observer. Read-only USB and host health; no RF or management."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

from phase11_5_device_management import admit
from phase11_5_inventory import exclusive_port, exchange, require, inventory_session
from phase11_5_network_fixture import HOST_BOOT
from phase11_5_pilot import DEVICE, SERIAL, Peer, check_status
from phase11_5_pilot_supervisor import finished


def validate_info(info, baseline):
    # Retain independently sampled WTP baseline only for admission of unchanged
    # identity and guards. Current WTP authority is checked by its own worker.
    admit(dict(info=info, wtp=baseline['wtp']), baseline)
    require(info['status']['state'] == 'empty' and not info['status']['output_active'],
            'A2 is idle only')
    require(info['heap_capacity_bytes'] - info['allocator_peak_bytes'] >= 32768,
            'Recovery heap reserve lost')
    require(info['allocator_failures'] == baseline['info']['allocator_failures'] and
            info['tls_allocation_failures'] == baseline['info']['tls_allocation_failures'],
            'Nominal allocation failure')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--seconds', type=int, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    require(1 <= args.seconds <= 1800, 'Bounded interval required')
    session = inventory_session(args.session_id)
    if not args.run:
        print('Plan only; no host or device accessed.')
        return
    require(os.geteuid() == 0 and Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            == HOST_BOOT, 'Expected wspr5 root and boot required')
    os.umask(0o077)
    baseline = finished(args.baseline, 'READ_ONLY_INVENTORY')
    validate_info(baseline['info'], baseline)
    boot = baseline['info']['status']['boot_id']
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

        def checkpoint():
            require(not faults, 'Independent observer failed')

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
                    value = peer.request('STATUS'); check_status(value, boot, {'empty'})
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
            helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
        threads = [threading.Thread(target=worker,args=(name,fn))
                   for name,fn in [('console',console),('wtp',wtp),('health',health)]]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        emit('finish', dict(result='FAILED' if faults else 'CAPTURED_REQUIRES_AUDIT', faults=faults))
        require(not faults, 'Idle observer failed; stop dependent campaign actions')


if __name__ == '__main__': main()
