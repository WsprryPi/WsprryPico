#!/usr/bin/env python3
"""Opt-in idle USB capacity admission. No RF job, Wi-Fi, CONFIG or flash path."""
import argparse
import json
import os
from pathlib import Path
import select
import subprocess
import time

from phase11_5_inventory import require, exclusive_port
from phase11_5_pilot import Peer, SERIAL, DEVICE
from phase11_5_pilot_supervisor import finished, idle, configuration, B_SERIAL, B_DEVICE
from phase11_5_network_fixture import HOST_BOOT
from phase11_5_r3_retained import BOOT
from phase11_5_r3_tls_plan import SOURCE
from phase11_5_device_management import digest, admit, save
from phase11_5_rf_observer import validate_info
from phase11_5_r3_capacity_plan import identity, wtp_capacity_frame
from validate_wtp_contract import frame

SCHEMA = 'phase11.5-r3-capacity-probe-v1'


def validate(packet):
    require(packet['schema'] == packet['r3_scope'] == SCHEMA and packet['source_revision'] == SOURCE
            and packet['boot_id'] == BOOT and packet['host_boot_id'] == HOST_BOOT
            and packet['serial'] == SERIAL and packet['device_id'] == DEVICE
            and packet['b_boot_id'] == 'feffcd075ab6cb0b74e7e0c2fde6c87f'
            and packet['runtime_seconds'] == 300 and packet['maximum_payload_bytes'] == 65536
            and packet['oversized_payload_bytes'] == 65537 and packet['rf_jobs'] == 0
            and packet['configuration_writes'] == packet['wifi_cycles'] == packet['flashes'] == 0,
            'C0 exact idle scope')
    keys = ('inventory_session_id', 'b_inventory_session_id', 'peer_session_id',
            'maximum_request_id', 'oversized_request_id', 'recovery_request_id')
    require(len({identity(packet[k]) for k in keys}) == len(keys), 'C0 distinct principals/request identities')
    return packet


def exchange_capacity(peer, raw, request, emit, *, invalid_frames=0):
    """One duplex write/read, preserving the deliberate invalid-frame advisory."""
    require(request['op'] in ('STATUS', 'PING') and invalid_frames in (0, 1), 'C0 read-only operation')
    peer.checkpoint()
    emit('capacity_tx', dict(request=request, hex=raw.hex(), expected_invalid_frames=invalid_frames))
    pending = raw
    deadline = time.monotonic() + 5
    response, invalid = None, 0
    while time.monotonic() < deadline:
        peer.checkpoint()
        read, write, _ = select.select([peer.fd], [peer.fd] if pending else [], [], .025)
        if write:
            try:
                size = os.write(peer.fd, pending[:4096])
                require(size > 0, 'C0 write made no progress')
                pending = pending[size:]
                emit('capacity_write', dict(bytes=size, total_written=len(raw)-len(pending)))
            except BlockingIOError:
                pass
        if not read:
            continue
        try:
            data = os.read(peer.fd, 4096)
        except BlockingIOError:
            continue
        require(data, 'C0 USB closed before expected recovery response')
        emit('capacity_rx', dict(hex=data.hex()))
        for value in peer.decoder.feed(data):
            require(not peer.validator.errors(value, peer.schema) and value['session_id'] == peer.session,
                    'C0 invalid/foreign response')
            emit('capacity_message', value)
            if value['type'] == 'event':
                require(value['boot_id'] == peer.boot and value['event'] == 'INVALID_FRAME',
                        'C0 unexpected target event')
                invalid += 1
                require(invalid <= invalid_frames, 'C0 extra parser rejection')
            else:
                require(response is None and not pending and value['request_id'] == request['request_id']
                        and value['op'] == request['op'] and value['ok'] is True, 'C0 expected operation rejected')
                response = value['body']
        if response is not None:
            require(invalid == invalid_frames, 'C0 missing oversized-frame rejection')
            return response
    raise TimeoutError('C0 five-second capacity operation deadline; no retry or RF action')


def run(root, packet):
    stop = time.monotonic() + packet['runtime_seconds']

    def checkpoint():
        require(time.monotonic() < stop, 'C0 overall deadline')

    def inventory(label, b=False):
        checkpoint()
        with (root / (label + '.stdout')).open('xb') as out, (root / (label + '.stderr')).open('xb') as err:
            code = subprocess.run(['python3', str(root / 'scripts/phase11_5_inventory.py'), '--serial',
                B_SERIAL if b else SERIAL, '--device-id', B_DEVICE if b else DEVICE, '--session-id',
                packet['b_inventory_session_id'] if b else packet['inventory_session_id'], '--run'],
                stdout=out, stderr=err, timeout=65).returncode
        require(code == 0, 'C0 inventory failed: ' + label)
        value = finished(root / (label + '.stdout'), 'READ_ONLY_INVENTORY')
        idle(value)
        require(value['wtp']['STATUS']['boot_id'] == (packet['b_boot_id'] if b else BOOT), 'C0 boot changed')
        return value

    result = dict(status='FAILED', rf_jobs=0, configuration_writes=0, wifi_cycles=0, flashes=0)
    before = before_b = None
    try:
        before_b = inventory('before-b', True)
        before = inventory('before-a')
        admit(before, before, SOURCE); validate_info(before['info'], before)
        require(before['wtp']['CAPS']['max_payload_bytes'] == 65536, 'C0 advertised payload changed')
        with (root / 'capacity.jsonl').open('x') as log:
            sequence = 0

            def emit(kind, value):
                nonlocal sequence
                log.write(json.dumps(dict(sequence=sequence, monotonic_ns=time.monotonic_ns(), kind=kind, value=value)) + '\n')
                log.flush(); os.fsync(log.fileno()); sequence += 1

            emit('start', dict(packet_sha256=digest(root / 'packet.json')))
            with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02')) as fd:
                peer = Peer(fd, emit, checkpoint, BOOT)
                peer.session = packet['peer_session_id']
                hello = peer.request('HELLO', dict(versions=['WTP/1'], client_name='R3-idle-capacity', client_version='1'))
                require(hello['device_id'] == DEVICE and hello['boot_id'] == BOOT, 'C0 HELLO identity')
                raw = wtp_capacity_frame(peer.session, packet['maximum_request_id'])
                status = exchange_capacity(peer, raw, json.loads(raw[16:]), emit)
                require(status['boot_id'] == BOOT and status['state'] == 'empty'
                        and status['owner_id'] is None and status['output_active'] is False, 'C0 maximum response is not idle')
                emit('maximum_admitted', status)
                oversized = wtp_capacity_frame(peer.session, packet['oversized_request_id'], True)
                recovery = dict(type='request', protocol='WTP/1', session_id=peer.session,
                                request_id=packet['recovery_request_id'], op='PING', body={'token': 'C0-after-oversize'})
                wire = oversized + frame(json.dumps(recovery, separators=(',', ':')).encode())
                pong = exchange_capacity(peer, wire, recovery, emit, invalid_frames=1)
                require(pong == {'token': 'C0-after-oversize'}, 'C0 recovery response changed')
                final = peer.request('STATUS')
                require(final['boot_id'] == BOOT and final['state'] == 'empty'
                        and final['owner_id'] is None and final['output_active'] is False, 'C0 final USB authority')
                emit('finish', dict(status='CAPTURED_REQUIRES_AUDIT', final_status=final))
        result['status'] = 'CAPTURED_REQUIRES_AUDIT'
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        after = after_b = None
        inventory_errors = []
        for name, b in (('after-a', False), ('after-b', True)):
            try:
                value = inventory(name, b)
                if b:
                    after_b = value
                else:
                    after = value
            except BaseException as error:
                inventory_errors.append(name + ': ' + type(error).__name__ + ': ' + str(error))
        try:
            require(not inventory_errors, '; '.join(inventory_errors))
            require(before is not None and before_b is not None, 'C0 missing initial inventory')
            admit(after, before, SOURCE); validate_info(after['info'], before)
            require(configuration(after) == configuration(before) and configuration(after_b) == configuration(before_b),
                    'C0 configuration changed')
            for key in ('launch_epoch', 'dma_irqs', 'alarm_irqs', 'tail_irqs'):
                require(after['info'][key] == before['info'][key], 'Unexpected C0 RF work')
            if result['status'] == 'CAPTURED_REQUIRES_AUDIT':
                require(after['info']['allocator_largest_successful_request_bytes'] == 65552,
                        'Maximum payload did not establish the required allocation')
            result.update(device_inactive_unowned=True, b_unchanged=True, final_status=after['wtp']['STATUS'],
                          largest_successful_request_bytes=after['info']['allocator_largest_successful_request_bytes'])
        except BaseException as error:
            result['status'] = 'FAILED'
            result['final_inventory_error'] = type(error).__name__ + ': ' + str(error)
        save(root / 'capacity-result.json', result)
    require(result['status'] == 'CAPTURED_REQUIRES_AUDIT', 'C0 capacity admission failed; preserve evidence')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--packet-sha256', required=True)
    p.add_argument('--run', action='store_true')
    args = p.parse_args()
    if not args.run:
        print('Plan only; no files, sockets or devices accessed.')
        return
    require(os.geteuid() == 0 and Path('/proc/sys/kernel/random/boot_id').read_text().strip() == HOST_BOOT, 'C0 host identity')
    os.umask(0o077)
    root = args.root.resolve(strict=True)
    require(digest(root / 'packet.json') == args.packet_sha256, 'C0 packet bytes changed')
    packet = validate(json.loads((root / 'packet.json').read_text()))
    require(packet['root'] == str(root), 'C0 root mismatch')
    for name, sha in packet['stage_sha256'].items():
        require((root / name).resolve().is_relative_to(root) and digest(root / name) == sha, 'C0 helper changed')
    with (root / 'capacity-result.json').open('x') as f:
        json.dump({'status': 'RUNNING'}, f)
    run(root, packet)


if __name__ == '__main__':
    main()
