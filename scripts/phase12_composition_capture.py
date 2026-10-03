#!/usr/bin/env python3
"""Explicit opt-in INFO-only two-hour observer; never controls jobs or networking.

A separately approved operator drives declared pressure/carrier cases. This
collector does not establish wire, principal, phone, pool or soak acceptance.
"""
import argparse
import datetime
import hashlib
import fcntl
import select
import json
import os
from pathlib import Path
import time
import termios

from phase12_composition_audit import require, strict_read, strict_load, validate_plan, counter


def pools(info):
    memory = info['network']['memory']
    require(memory['statistics_enabled'] is True, 'lwIP statistics disabled')
    result = {}
    for key in ('tcp_pcbs', 'tcp_listeners', 'udp_pcbs', 'timeouts', 'igmp_groups',
                'tcp_segments', 'packet_pool'):
        pool = memory[key]
        require(isinstance(pool, dict), 'required lwIP pool unmeasured: ' + key)
        for field in ('used', 'capacity', 'peak', 'errors'):
            require(type(pool[field]) is int and pool[field] >= 0, 'numeric lwIP pool')
        result[key] = pool
    return result


def acl_credits(p, info, previous=None, *, final=False, baseline=None):
    """Validate event-observed controller ACL credits on explicitly bound plans.

    Older captures and the consumer's disabled BLE controller do not establish
    this measurement. Credits describe the controller's public HCI ledger,
    never byte occupancy of its internal RAM.
    """
    if not p.get('controller_acl_credits_required', False):
        return None
    metric = info['btstack_acl_credits']
    require(info['btstack_controller_buffers_measured'] is True and
            metric['scope'] == 'controller_reported_hci_acl_credits' and
            metric['initialized'] is True and metric['measured'] is True,
            'controller ACL credit measurement unavailable')
    values = {k: counter(metric[k], 'ACL ' + k) for k in (
        'capacity', 'free', 'min_free', 'peak_outstanding', 'epoch',
        'send_events', 'completed_events', 'invalid_samples', 'transport_failures')}
    require(0 < values['capacity'] <= 65535 and values['epoch'] > 0 and
            0 <= values['min_free'] <= values['free'] <= values['capacity'] and
            values['peak_outstanding'] == values['capacity'] - values['min_free'],
            'controller ACL credit bounds')
    require(values['invalid_samples'] == values['transport_failures'] == 0 and
            values['min_free'] >= p['controller_acl_min_free_slots'],
            'controller ACL credit health/headroom')
    if previous is not None:
        require(values['capacity'] == previous['capacity'] and
                values['epoch'] == previous['epoch'], 'controller ACL epoch changed')
        require(values['min_free'] <= previous['min_free'] and
                values['peak_outstanding'] >= previous['peak_outstanding'] and
                all(values[k] >= previous[k] for k in ('send_events', 'completed_events')),
                'controller ACL event history regressed')
    if final:
        require(baseline is not None and baseline['capacity'] == values['capacity'] and
                baseline['epoch'] == values['epoch'], 'initial ACL capture baseline required')
        require(values['send_events'] > baseline['send_events'] and
                values['completed_events'] > baseline['completed_events'] and
                values['free'] == values['capacity'],
                'actual ACL pressure and complete credit return required')
    return values


def check_approval(p, approval, console):
    require(approval['schema'] == 'phase12-observer-approval/1' and
            approval['approved'] is True and approval['operation'] == 'composition-info-only',
            'separate explicit observer approval required')
    expected = hashlib.sha256(json.dumps(p, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    require(approval['plan_sha256'] == expected and approval['source_commit'] == p['source_commit']
            and approval['image_sha256'] == p['image_sha256'] and approval['console'] == console,
            'approval binding mismatch')
    expiry = datetime.datetime.fromisoformat(approval['expires_utc'].replace('Z', '+00:00'))
    require(expiry.tzinfo is not None and expiry >= datetime.datetime.now(datetime.timezone.utc) +
            datetime.timedelta(seconds=p['duration_s'] + p['max_gap_s']),
            'approval expired')


def check_info(p, info):
    status = info['status']
    require(info['ok'] is True and info['device_id'] == p['device_id'] and
            info['revision'] == p['source_commit'][:12] and
            info['firmware'] == p['firmware'] and status['boot_id'] == p['boot_id'],
            'exact device/boot/firmware mismatch')
    require(status['engine'] == p['engine'] and status['enabled'] is False and
            status['output_active'] is False, 'inhibited engine/output required')
    expected = 'plain' if p['mode'] == 'consumer' else 'engineering-tls'
    require(info['lan_wtp_mode'] == expected, 'wire mode mismatch; no fallback')
    require(counter(info['softap_session_inactivity_ms'], 'softap_session_inactivity_ms') == 900000 and
            counter(info['softap_session_absolute_ms'], 'softap_session_absolute_ms') == 43200000,
            'ordinary session limits')
    require(info['resource_schema'] == 1 and info['core0_stack_guard_valid'] == 1 and
            info['core0_stack_fault_status'] == 0, 'resource schema/guard')
    for field in ('fault_stage', 'fault_hash', 'fault_pc', 'fault_status',
                  'tls_allocation_failures', 'provisioning_fault'):
        require(info[field] == 0, 'target failure: ' + field)
    for field in ('allocator_failures', 'flash_read_failures',
                  'flash_erase_failures', 'flash_program_failures'):
        require(counter(info[field], field) == 0, 'target failure: ' + field)
    require(info['access_state'] in ('healthy', 'erased'), 'access journal health')
    require(info['deployment_identity_matches'] is True and
            info['radio_identity_valid'] is True, 'deployment/radio identity')
    require(info['provisioning_source'] != 'fault', 'profile health')
    require('phase12_fault_stage' not in info, 'ordinary candidate required')
    require(info['btstack_pool_occupancy_measured'] is True, 'BTstack pools unmeasured')
    for key in ('hci_connections', 'l2cap_channels', 'l2cap_services', 'sm_lookup', 'whitelist'):
        pool = info['btstack_pools'][key]
        for field in ('used', 'capacity', 'peak', 'failures', 'faults'):
            require(type(pool[field]) is int and pool[field] >= 0, 'numeric BTstack pool')
        require(pool['failures'] == 0 and pool['faults'] == 0, 'BTstack pool fault')
    for pool in pools(info).values():
        require(pool['errors'] == 0, 'lwIP pool error')
    acl_credits(p, info)
    return info


def capture(p, console, output, *, clock=time.monotonic, sleeper=time.sleep,
            observer=None):
    # Dependencies are injectable solely for deterministic host tests.
    if observer is None:
        from check_usb_target import port, write_all
        def observer():
            with port(console) as fd:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                termios.tcflush(fd, termios.TCIFLUSH)
                write_all(fd, b'INFO\n')
                deadline = time.monotonic() + 5
                data = bytearray()
                while time.monotonic() < deadline:
                    if select.select([fd], [], [], deadline-time.monotonic())[0]:
                        chunk = os.read(fd, 512)
                        require(bool(chunk), 'serial device closed')
                        data.extend(chunk)
                        require(len(data) <= 16384, 'bounded INFO response')
                        while b'\n' in data:
                            line, _, remainder = data.partition(b'\n')
                            data = bytearray(remainder)
                            if line.startswith(b'{'):
                                return strict_load(line), bytes(line)
                raise TimeoutError('INFO sample timeout')
    validate_plan(p)
    require(str(console).startswith('/dev/serial/by-id/usb-WsprryPi_WsprryPico_'),
            'explicit by-id Pico console required')
    start = clock()
    old_umask = os.umask(0o077)
    try:
        with Path(output).open('x') as log:
            def emit(value):
                log.write(json.dumps(value, sort_keys=True) + '\n')
                log.flush()
                os.fsync(log.fileno())
            emit({'kind': 'start', 'plan': p, 'physical_acceptance': False})
            try:
                previous_read = None
                previous_acl = None
                baseline_acl = None
                for index in range(241):
                    due = start + index * p['cadence_s']
                    sleeper(max(0, due - clock()))
                    require(clock() - start <= 7245, 'absolute observer deadline')
                    before = clock() - start
                    require(previous_read is None or before-previous_read <= p['max_gap_s'],
                            'sample cadence gap before USB access')
                    previous_read = before
                    observed = observer()
                    if isinstance(observed, tuple):
                        info, wire = observed
                        transport_raw = True
                    else:
                        info = observed
                        wire = json.dumps(info, sort_keys=True).encode()
                        transport_raw = False  # injected host-test observer only
                    after = clock() - start
                    require(after - before <= 10 and after <= 7245,
                            'observer sample deadline')
                    raw = json.dumps(info, sort_keys=True, separators=(',', ':')).encode()
                    emit({'kind': 'INFO', 'elapsed_start_s': before,
                          'elapsed_end_s': after, 'info': info,
                          'decoded_info_sha256': hashlib.sha256(raw).hexdigest(),
                          'transport_raw': transport_raw, 'raw_info_hex': wire.hex(),
                          'raw_info_sha256': hashlib.sha256(wire).hexdigest()})
                    check_info(p, info)
                    previous_acl = acl_credits(p, info, previous_acl, final=index == 240,
                                               baseline=baseline_acl)
                    if index == 0:
                        baseline_acl = previous_acl
                emit({'kind': 'complete', 'status': 'CAPTURE_COMPLETE_REVIEW_REQUIRED',
                      'physical_acceptance': False,
                      'pending': ['pressure', 'wire', 'principals', 'reclamation',
                                  'phone', '12h accelerated fixture']})
            except BaseException as error:
                emit({'kind': 'failed', 'error': type(error).__name__ + ': ' + str(error)})
                raise
    finally:
        os.umask(old_umask)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--console', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--approval-packet', type=Path, required=True)
    a = parser.parse_args()
    if not a.run:
        parser.error('explicit --run and separate hardware approval required')
    try:
        plan = validate_plan(strict_read(a.plan))
        check_approval(plan, strict_read(a.approval_packet), a.console)
        with Path(str(a.plan.resolve()) + '.campaign.lock').open('a') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            capture(plan, a.console, a.output)
    except (ValueError, KeyError, TypeError, OSError, TimeoutError) as error:
        parser.exit(1, 'STOPPED: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
