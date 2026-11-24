#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finite, explicitly selected Si5351 Test Tone acceptance through production USB.

No instrument access. --configure saves the supported profile and restarts this
board; it never enables schedules. Evidence stays in a new private directory.
"""
import argparse
import json
import time
import uuid
from pathlib import Path

import usb_installer as usb

PREFIX = '/api/control/v1/'


def request(management, method, resource, body=None, revision=''):
    if body is not None:
        body = {'contract': 'Wsprry-Control/1', **body}
    result = management.exchange(dict(operation='request', method=method,
        path=PREFIX + resource, body='' if body is None else json.dumps(body, separators=(',', ':')),
        if_match=revision))
    usb.require(result['delivery_required'] is True, 'Missing delivery acknowledgement')
    ack = management.exchange({'operation': 'ack'}, repeat=True)
    usb.require(ack['status'] == 200, 'Delivery acknowledgement failed; reconcile, never replay')
    return result, usb.decode(result['body'])


def read(management, resource):
    response, value = request(management, 'GET', resource)
    usb.require(response['status'] == 200, 'Read failed: ' + resource)
    return response, value


def configured_settings(drive):
    return dict(reference_hz=25000000, reference_source='external_xa', crystal_load_pf=None,
        address=96, drive_ma=drive, transmit_output=0, loopback_output=None, loopback_input_gp=None,
        rf_gate_gp=None, rf_gate_active_high=True, reference_use='measurement_only',
        trusted_uncertainty_ppb=None, manual_correction_ppb=0, automatic_calibration=False)


def idle(management):
    _, status = read(management, 'status')
    job = status['job']
    usb.require(job['output_active'] is False and job['owner_id'] is None and
                job['state'] in ('empty', 'complete', 'aborted', 'missed'),
                'Output is busy, owned, faulted, or uncertain')
    _, config = read(management, 'config')
    usb.require(config['config'] is None or config['config']['enabled'] is False,
                'Disable the saved WSPR schedule explicitly before testing')
    _, messages = read(management, 'message-schedule')
    usb.require(messages['saved'] is None or messages['saved']['enabled'] is False,
                'Disable the saved message schedule explicitly before testing')
    return config


def configure(args, emit):
    board = usb.selected(args.device, 'application')
    with usb.Management(board) as management:
        config = idle(management)
        _, capabilities = read(management, 'capabilities')
        usb.require(capabilities.get('test_tone', {}).get('engines', {}).get('si5351', {}).get('drive_ma') == [2, 4, 6, 8],
                    'Install firmware with the current four-drive Test Tone contract before configuration')
        emit('original_config', config)
        usb.require(config['config'] is not None, 'Configure the RF allocation through normal setup first')
        settings = config['config'].get('si5351')
        if settings is None:
            settings = configured_settings(args.drive)
        else:
            settings = dict(settings, drive_ma=args.drive)
            usb.require(settings['reference_hz'] == 25000000 and
                        settings['reference_source'] == 'external_xa' and settings['address'] == 96 and
                        settings['transmit_output'] == 0 and settings['rf_gate_gp'] is None,
                        'Existing Si5351 settings do not match the supported profile; use normal setup')
        pins = dict(config['config']['pins'], engine='i2c', rf_gp=None, i2c_pair=1)
        target = management.hello['target']
        revision = read(management, 'config')[0]['etag']
        body = dict(schema='config-update', target=target, mode='merge',
                    config=dict(pins=pins, si5351=settings))
        emit('configuration_request', body)
        response, saved = request(management, 'POST', 'config/update', body, revision)
        emit('configuration_response', dict(status=response['status'], body=saved))
        usb.require(response['status'] in (200, 202), 'Configuration was refused; leave settings unchanged')
        _, authoritative = read(management, 'si5351')
        usb.require(authoritative['saved'] == settings, 'Saved settings mismatch')
        revision = read(management, 'config')[0]['etag']
        emit('restart_requested', dict(target=target))
        # A lost reset ACK is settled by a new same-board boot, never a second POST.
        response, value = request(management, 'POST', 'restart', {}, revision)
        emit('restart_response', dict(status=response['status'], body=value))
        usb.require(response['status'] == 202, 'Restart was refused')
    deadline = time.monotonic() + 40
    last_error = None
    while time.monotonic() < deadline:
        try:
            board = usb.selected(args.device, 'application', board['parent'])
            with usb.Management(board) as management:
                usb.require(management.hello['target']['boot_id'] != target['boot_id'], 'Still on original boot')
                _, current = read(management, 'si5351')
                usb.require(current['boot_active'] == settings and
                            current['pending_restart'] is False and current['execution_engine'] == 'si5351',
                            'Boot configuration is not applied')
                emit('configured_boot', current)
                return
        except (OSError, ValueError, usb.Refusal) as error:
            last_error = str(error)
            time.sleep(.5)
    raise usb.Refusal('Restart/readback unresolved: ' + str(last_error))


def exercise(args, emit):
    board = usb.selected(args.device, 'application')
    request_id = uuid.uuid4().hex
    accepted = None
    with usb.Management(board) as management:
        idle(management)
        _, caps = read(management, 'capabilities')
        tone_cap = caps.get('test_tone', {})
        usb.require(tone_cap.get('available') is True and tone_cap.get('active_engine') == 'si5351',
                    'Si5351 Test Tone is not available on this boot')
        usb.require(tone_cap['engines']['si5351']['drive_ma'] == [2, 4, 6, 8], 'Unsupported drive descriptor')
        target = management.hello['target']
        proposal = dict(engine='si5351', carrier_hz=args.carrier_hz, duration_ms=args.duration_ms,
                        proposed_drive_ma=args.drive)
        emit('review_request', proposal)
        response, review = request(management, 'POST', 'test-tone/review',
                                  dict(schema='test-tone-review', target=target, tone=proposal))
        emit('review', dict(status=response['status'], body=review))
        usb.require(response['status'] == 200 and review.get('admission') == 'ready', 'Review refused')
        body = dict(schema='test-tone-start', target=target, request_id=request_id,
                    tone=dict(engine='si5351', carrier_hz=args.carrier_hz,
                              duration_ms=args.duration_ms, expected_drive_ma=args.drive))
        emit('start_request', body)
        selector = ('test-tone/status?device_id=' + target['device_id'] + '&boot_id=' + target['boot_id'] +
                    '&request_id=' + request_id)
        try:
            response, accepted = request(management, 'POST', 'test-tone/start', body, review['assessment_revision'])
            emit('accepted', dict(status=response['status'], body=accepted))
            usb.require(response['status'] == 202 and accepted.get('job'), 'Start was refused')
            job = accepted['job']
            evidence = job['synthesis_readback']
            usb.require(evidence['stage'] == 'verified' and evidence['drive_ma'] == args.drive and
                        evidence['transmit_output'] == 0 and job['engine'] == 'si5351',
                        'Fresh job-bound drive verification failed')
            deadline = time.monotonic() + args.duration_ms / 1000 + 15
            running_at = None
            stop_sent = False
            while time.monotonic() < deadline:
                _, status = read(management, selector)
                current = status.get('job')
                usb.require(current and current['job_id'] == job['job_id'], 'Receipt unavailable or wrong job')
                if current['phase'] == 'running' and running_at is None:
                    running_at = time.monotonic()
                    emit('running', status)
                if current['phase'] == 'terminal':
                    emit('terminal', status)
                    usb.require(current['output_inactive_confirmed'] is True and
                                current['recovery_required'] is False and
                                current['outcome'] == ('stopped' if stop_sent else 'completed'),
                                'Terminal shutdown was not confirmed')
                    return
                if args.stop_after_ms is not None and running_at is not None and not stop_sent and \
                        (time.monotonic() - running_at) * 1000 >= args.stop_after_ms:
                    stop_sent = True  # Never replay an uncertain mutation.
                    response, stopped = request(management, 'POST', 'test-tone/stop',
                        dict(schema='test-tone-stop', target=target, job_id=job['job_id']), job['control_revision'])
                    emit('stop', dict(status=response['status'], body=stopped))
                    usb.require(response['status'] == 200, 'Identified Stop failed')
                time.sleep(.05)
            raise usb.Refusal('Finite test deadline expired')
        except BaseException:
            # Reconcile an uncertain Start using the exact request, never replay it.
            try:
                _, observed = read(management, selector)
                emit('failure_reconciliation', observed)
                record = observed.get('job')
                if record and record['phase'] != 'terminal':
                    response, stopped = request(management, 'POST', 'test-tone/stop',
                        dict(schema='test-tone-stop', target=target, job_id=record['job_id']), record['control_revision'])
                    emit('failure_stop', dict(status=response['status'], body=stopped))
            except BaseException as error:
                emit('cleanup_unresolved', dict(error=str(error)))
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', required=True)
    parser.add_argument('--drive', type=int, choices=(2, 4, 6, 8), required=True)
    parser.add_argument('--configure', action='store_true')
    parser.add_argument('--carrier-hz', type=int, default=14097100)
    parser.add_argument('--duration-ms', type=int, default=3000)
    parser.add_argument('--stop-after-ms', type=int)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    usb.require(10 <= args.duration_ms <= 120000 and 8000 <= args.carrier_hz <= 160000000, 'Invalid finite tone')
    usb.require(args.stop_after_ms is None or 0 < args.stop_after_ms < args.duration_ms, 'Invalid Stop interval')
    if args.dry_run:
        print(json.dumps(dict(schema='si5351-test-tone-plan/1', device=args.device, drive_ma=args.drive,
            configure_and_restart=args.configure, carrier_hz=args.carrier_hz, duration_ms=args.duration_ms,
            stop_after_ms=args.stop_after_ms, instruments=False)))
        return
    args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    with (args.output / 'events.jsonl').open('x') as stream:
        def emit(event, body):
            stream.write(json.dumps(dict(event=event, host_monotonic_ns=time.monotonic_ns(), body=body)) + '\n')
            stream.flush()
        with usb.device_lock(args.device):
            if args.configure: configure(args, emit)
            exercise(args, emit)
        emit('success', dict(scope='production USB and native/register shutdown; no measured RF claim'))
    print(json.dumps(dict(ok=True, drive_ma=args.drive, evidence=str(args.output))))


if __name__ == '__main__':
    main()
