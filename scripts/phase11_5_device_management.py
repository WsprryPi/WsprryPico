#!/usr/bin/env python3
"""Guarded, opt-in idle management for the Phase 11.5 candidate.

This helper does not flash, reboot, submit RF jobs, create a network fixture or
infer a boot. The supervising campaign supplies a previously recorded admission
inventory and independently bounded restoration. Each invocation owns Console
and WTP exclusively, verifies identity and inactivity through both, records a
write-ahead intent, and refuses further writes after an ambiguous result.
Private configuration and USB wire evidence remain outside Git.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from phase11_5_inventory import exclusive_port, exchange, require, inventory_session
from phase11_5_pilot import DEVICE, SERIAL
from phase11_5_pilot_supervisor import finished, idle

SOURCE = '4058d3a4a95110326006a7db6e37eb4b562a500c'
R1_SOURCE = 'e20ae8bea2d5237af017dbd5f73bfe9332ce144e'
CANDIDATES = (SOURCE, R1_SOURCE)
MAX_WRITES = 32
MAX_PROBES = 64


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def admit(current, baseline, source=SOURCE):
    require(source in CANDIDATES, 'Unreviewed candidate')
    idle(current)
    idle(baseline)
    info, old = current['info'], baseline['info']
    require(info['device_id'] == old['device_id'] == DEVICE, 'DUT identity')
    require(info['revision'] == old['revision'] == source[:12], 'Candidate revision')
    require(info['status']['boot_id'] == old['status']['boot_id'], 'Boot changed')
    require(info['system_clock_hz'] == old['system_clock_hz'], 'Clock changed')
    physical = info['status']['engine'] == 'pio-dma-gp2'
    require(info['status']['engine'] == old['status']['engine'] and
            info['system_clock_hz'] == (138000000 if physical else 150000000),
            'Engine/clock admission')
    require(info['status']['engine'] in ('pio-dma-gp2', 'inhibited-standalone-simulator'),
            'Unknown engine')
    require(all(info[key] == 0 for key in ('fault_stage','fault_hash','fault_pc','fault_status')),
            'Preserved firmware fault')
    if physical:
        require(info['rf_render_in_ram'] is True and not info['engine_diagnostic'] and
                all(info[key] == 0 for key in ('dma_errors','refill_invalid_reserves',
                    'exhausted_successor_links','refill_irq_unpaired')), 'Preserved RF fault')
    for core in range(2 if physical else 1):
        prefix = f'core{core}_stack_'
        require(type(info[prefix + 'guard_valid']) is int and
                info[prefix + 'guard_valid'] == 1 and
                info[prefix + 'guard_bottom'] == old[prefix + 'guard_bottom'] and
                info[prefix + 'guard_limit'] == old[prefix + 'guard_limit'] ==
                info[prefix + 'guard_bottom'] + 4096 and
                info[prefix + 'fault_status'] == 0, 'Stack guard/fault admission')
    require(info['status']['watermark_utc_ns'] == old['status']['watermark_utc_ns'],
            'Saved watermark changed')
    return physical


def configuration(original, test_wifi, variant, time_server='clock.phase115.test'):
    require(type(original) is dict and original.get('enabled') is False and
            original.get('expires_utc_s') == 0, 'Original schedules must remain disabled')
    require(set(test_wifi) == {'ssid', 'password', 'ntp_ipv4'} and
            test_wifi['ssid'] == 'WsprryPico-Phase115' and
            time_server in ('clock.phase115.test', 'time.local') and
            test_wifi['ntp_ipv4'] == time_server and
            type(test_wifi['password']) is str and 8 <= len(test_wifi['password']) <= 63,
            'Unexpected isolated network configuration')
    value = json.loads(json.dumps(original))
    if variant != 'original':
        value['wifi'] = test_wifi
    if variant == 'schedule-variant':
        require(value['schedules'] == [{'period_s': 120, 'phase_s': 0}],
                'Original schedule differs from frozen variant')
        value['schedules'][0]['phase_s'] = 1
    require(variant in ('original', 'test', 'schedule-variant'), 'Configuration variant')
    text = json.dumps(value, separators=(',', ':'), ensure_ascii=True)
    require(len(text) <= 1800, 'Configuration bound')
    return value, ('CONFIG ' + text + '\n').encode('ascii')


def authorize(state, action, argument):
    require(state.get('pending') is None and not state.get('blocked'),
            'Previous management outcome needs independent reconciliation')
    now = time.monotonic_ns()
    deadline = (state.get('restoration_deadline_monotonic_ns', state['deadline_monotonic_ns'])
                if action == 'config' and argument == 'original' else state['deadline_monotonic_ns'])
    require(type(deadline) is int and now < deadline <= now + 21600_000_000_000,
            'Management deadline')
    counts = state['counts']
    require(set(counts) == {'config', 'wifi-off', 'wifi-on', 'heap-probe'} and
            all(type(v) is int and v >= 0 for v in counts.values()), 'Invalid operation counters')
    if action == 'config':
        # Always retain one successful-write allowance for original restoration.
        require(counts['config'] < (MAX_WRITES if argument == 'original' else MAX_WRITES - 1),
                'Configuration write budget exhausted')
    elif action in ('wifi-off', 'wifi-on'):
        require(counts[action] < 3, 'Wi-Fi cycle budget exhausted')
    elif action == 'heap-probe':
        require(counts[action] < MAX_PROBES, 'Heap probe budget exhausted')
    else:
        raise ValueError('Unsupported management action')


def save(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('config', 'wifi-off', 'wifi-on', 'heap-probe'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--variant', choices=('original', 'test', 'schedule-variant'))
    parser.add_argument('--bytes', type=int)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        print('Plan only; no files, USB devices or network settings accessed.')
        return
    require(sys.platform == 'linux' and os.geteuid() == 0, 'wspr5 root required')
    os.umask(0o077)
    root = args.root.resolve(strict=True)
    require(root.is_dir() and root.stat().st_mode & 0o077 == 0, 'Private root required')
    require(args.baseline.resolve(strict=True).is_relative_to(root), 'Baseline outside evidence root')
    require(Path(__file__).resolve() == root/'scripts/phase11_5_device_management.py',
            'Run only the staged helper')
    packet = json.loads((root/'packet.json').read_text())
    require('scripts/phase11_5_device_management.py' in packet['helper_sha256'], 'Missing helper identity')
    for relative, expected in packet['helper_sha256'].items():
        path = root/relative
        require(path.resolve().is_relative_to(root) and digest(path) == expected,
                'Staged helper changed')
    # The surrounding supervisor creates and freezes this state only after its
    # restoration unit, absolute deadline and both board inventories are recorded.
    state_path = root / 'management-state.json'
    with (root / 'management.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = json.loads(state_path.read_text())
        require(state['host_boot'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'Host boot changed')
        unit = state['restoration_unit']
        require(unit.startswith('phase115-device-') and unit.endswith('.timer'),
                'Unexpected restoration unit')
        result = subprocess.run(['systemctl', 'show', unit, '-p', 'ActiveState',
                                 '-p', 'Description'], capture_output=True, text=True,
                                timeout=5, check=True)
        require('ActiveState=active\n' in result.stdout and
                'Description=' + state['restoration_token'] + '\n' in result.stdout,
                'Independent restoration is not armed with matching ownership')
        authorize(state, args.action, args.variant)
        if packet.get('time_server_mdns') and packet.get('family') == 'R1' and args.action == 'heap-probe':
            require(packet['max_idle_heap_probes'] == 3 and state['counts']['heap-probe'] < 3,
                    'R1 permits exactly three bounded idle probes')
        require(digest(args.baseline) == state['baseline_sha256'], 'Baseline file changed')
        baseline = finished(args.baseline, 'READ_ONLY_INVENTORY')
        require(type(state['inventory_session_id']) is str, 'Missing persistent administration session')
        session = inventory_session(state['inventory_session_id'])
        sequence = sum(state['counts'].values())
        inventory = root / f'management-{sequence:03d}-before.jsonl'
        with inventory.open('xb') as stream:
            subprocess.run([sys.executable, Path(__file__).with_name('phase11_5_inventory.py'),
                            '--serial', SERIAL, '--device-id', DEVICE, '--session-id', session,
                            '--run'], stdout=stream,
                           stderr=subprocess.PIPE, timeout=65, check=True)
            stream.flush()
            os.fsync(stream.fileno())
        current = finished(inventory, 'READ_ONLY_INVENTORY')
        admit(current, baseline, packet['source_revision'])
        if args.action == 'config':
            require(args.variant is not None, 'Missing configuration variant')
            original_path, wifi_path = root / 'original-config.json', root / 'test-wifi.json'
            require(digest(original_path) == state['original_config_sha256'] and
                    digest(wifi_path) == state['test_wifi_sha256'], 'Private input changed')
            value, command = configuration(json.loads(original_path.read_text()),
                                            json.loads(wifi_path.read_text()), args.variant,
                                            'time.local' if packet.get('time_server_mdns') else 'clock.phase115.test')
        elif args.action == 'heap-probe':
            require(type(args.bytes) is int and 1 <= args.bytes <=
                    current['info']['heap_capacity_bytes'] + 1, 'Heap probe bound')
            command = f'HEAP PROBE {args.bytes}\n'.encode('ascii')
        else:
            command = ('WIFI ' + ('OFF' if args.action == 'wifi-off' else 'ON') + '\n').encode()
        evidence = root / f'management-{sequence:03d}-exchange.jsonl'
        with evidence.open('x') as stream:
            def emit(kind, value):
                stream.write(json.dumps(dict(kind=kind, value=value,
                    monotonic_ns=time.monotonic_ns(), utc_ns=time.time_ns())) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            # Recheck Console after acquiring its exclusive handle. The WTP
            # inventory precedes it; another owner can arrive meanwhile, so the
            # firmware's idle gate remains authoritative for the actual command.
            with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as fd:
                info = exchange(fd, b'INFO\n', time.monotonic() + 5, emit, False)
                fresh = dict(current, info=info)
                admit(fresh, baseline, packet['source_revision'])
                state['pending'] = {'action': args.action, 'variant': args.variant,
                                    'bytes': args.bytes, 'evidence': evidence.name,
                                    'command_sha256': hashlib.sha256(command).hexdigest()}
                state['counts'][args.action] += 1
                save(state_path, state)
                try:
                    reply = exchange(fd, command, time.monotonic() + 10, emit, False)
                    require(reply.get('ok') is True, 'Management command rejected')
                    if args.action == 'config':
                        require(all(reply[key] == value[key] for key in
                                    ('enabled', 'station', 'schedules', 'expires_utc_s')) and
                                reply['watermark_utc_ns'] ==
                                baseline['info']['status']['watermark_utc_ns'],
                                'Configuration readback differs')
                    elif args.action == 'heap-probe':
                        require(type(reply.get('allocated')) is bool, 'Missing allocation outcome')
                    state['last_result'] = {'action': args.action, 'reply': reply,
                                            'evidence_sha256': digest(evidence)}
                    state['pending'] = None
                    save(state_path, state)
                except BaseException:
                    state['blocked'] = True
                    save(state_path, state)
                    raise
        print('Recorded management result; no reboot or RF action performed.')


if __name__ == '__main__':
    main()
