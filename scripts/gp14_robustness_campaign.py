#!/usr/bin/env python3
"""Bounded opt-in campaign; default only prints the plan and never opens USB."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time

ACTIONS = ('SHORT', 'MIDDLE', 'LONG', 'STUCK', 'FLASH', 'DMA_STOP', 'PIO_STOP',
           'OVERRUN', 'RESET', 'WATCHDOG', 'FAULT', 'BOOT_HELD', 'RELOAD')
RESET_ACTIONS = ('RESET', 'WATCHDOG', 'FAULT', 'BOOT_HELD')
FAULT_CODES = {'DMA_STOP': 7, 'PIO_STOP': 9, 'OVERRUN': 6}
BUDGET = {'STUCK': 640, 'RELOAD': 90, 'OVERRUN': 30, 'BOOT_HELD': 35}
INTEGER_FIELDS = ('synthetic', 'rf_output', 'active', 'sequence', 'prior_action',
                  'prior_sequence', 'prior_watchdog', 'boot_id', 'prior_fault',
                  'uptime_us', 'clock_hz', 'started', 'capture_fault', 'fault_code',
                  'held', 'samples', 'blocks', 'backlog', 'stops', 'aps',
                  'would_reset', 'releases', 'duration_us', 'low_at_us',
                  'high_at_us', 'reads0', 'reads1', 'flash_ok', 'settings_before',
                  'settings_now')


def decode_record(raw, serial, revision):
    """Reject incomplete telemetry even when lost bytes leave valid JSON."""
    row = json.loads(raw)
    if not isinstance(row, dict):
        raise ValueError('Diagnostic status is not an object')
    for key in ('image', 'serial', 'revision', 'result', 'action'):
        if not isinstance(row.get(key), str):
            raise ValueError(f'Missing or invalid diagnostic field: {key}')
    for key in INTEGER_FIELDS:
        if type(row.get(key)) is not int or row[key] < 0:
            raise ValueError(f'Missing or invalid diagnostic field: {key}')
    identity(row, serial, revision)
    return row


def identity(row, serial, revision):
    if (row.get('image') != 'gp14-robustness' or row.get('serial', '').upper() != serial.upper()
            or row.get('revision') != revision or row.get('clock_hz') != 150_000_000
            or row.get('started') != 1 or row.get('synthetic') != 1 or row.get('rf_output') != 0):
        raise ValueError('Diagnostic identity/clock/startup mismatch')


def continuity(before, after):
    if (after['settings_now'] != before['settings_now'] or
            after['settings_before'] != before['settings_now']):
        raise ValueError('Reserved settings checksum changed')
    if after['boot_id'] == before['boot_id']:
        if after['samples'] <= before['samples']:
            raise ValueError('Capture made no progress')
        for field in ('reads0', 'reads1'):
            if not 0 < (after[field] - before[field]) % (1 << 32) < (1 << 31):
                raise ValueError(f'{field} made no bounded progress')


def outcome(action, before, after):
    if after['active']:
        raise ValueError('Action did not finish')
    if action in RESET_ACTIONS:
        if (before['boot_id'] == after['boot_id'] or
                after['prior_action'] != ACTIONS.index(action) + 1 or
                after['prior_sequence'] != before['sequence'] + 1):
            raise ValueError('Reset breadcrumb/boot mismatch')
        if bool(after['prior_watchdog']) != (action in ('WATCHDOG', 'FAULT')):
            raise ValueError('Unexpected reset cause')
        if bool(after['prior_fault']) != (action == 'FAULT'):
            raise ValueError('Unexpected fault breadcrumb')
    elif (before['boot_id'] != after['boot_id'] or after['action'] != action or
          after['sequence'] != before['sequence'] + 1):
        raise ValueError('Unexpected reboot/action/sequence')
    expected_fault = FAULT_CODES.get(action, 0)
    if after['fault_code'] != expected_fault or bool(after['capture_fault']) != bool(expected_fault):
        raise ValueError('Wrong capture fault result')
    if action in ('SHORT', 'MIDDLE', 'LONG', 'STUCK', 'FLASH'):
        if after['releases'] != 1 or after['held']:
            raise ValueError('Missing release or stuck synthetic input')
        if action == 'FLASH':
            if not after['flash_ok'] or after['duration_us'] < 139_000:
                raise ValueError('Scratch write/restore or blackout capture failed')
            expected = (int(after['duration_us'] >= 400_000),
                        int(after['duration_us'] >= 9_000_000),
                        int(after['duration_us'] < 400_000))
        else:
            low, high, expected = {
                'SHORT': (180_000, 350_000, (0, 0, 1)),
                'MIDDLE': (550_000, 850_000, (1, 0, 0)),
                'LONG': (10_900_000, 11_200_000, (1, 1, 0)),
                'STUCK': (609_900_000, 610_200_000, (1, 1, 0)),
            }[action]
            if not low <= after['duration_us'] <= high:
                raise ValueError('Gesture timing outside bounded range')
        if tuple(after[key] for key in ('stops', 'aps', 'would_reset')) != expected:
            raise ValueError('Wrong release/threshold classification')
    elif any(after[key] for key in ('stops', 'aps', 'would_reset', 'releases')):
        raise ValueError('Unexpected gesture')
    if action == 'RELOAD' and after['blocks'] - before['blocks'] < 2:
        raise ValueError('Fewer than two DMA reloads observed')
    if action == 'BOOT_HELD' and after['held']:
        raise ValueError('Boot-held input not released')


class Connection:
    def __init__(self, args, log):
        import serial
        from serial.tools import list_ports
        self.module, self.ports = serial, list_ports
        self.args, self.log, self.port = args, log, None

    def close(self):
        if self.port:
            self.port.close()
            self.port = None

    def query(self, command):
        if self.port is None:
            matches = [p for p in self.ports.comports()
                       if (p.serial_number or '').upper() == self.args.serial.upper()]
            if len(matches) != 1:
                raise OSError('Exact serial not uniquely enumerated')
            self.port = self.module.Serial(matches[0].device, 115200, timeout=0.5, write_timeout=1,
                                           exclusive=True)
        self.log.write(json.dumps({'host_time': time.time(), 'command': command}) + '\n')
        self.log.flush()
        self.port.write((command + '\n').encode('ascii'))
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            raw = self.port.read_until(b'\n', 4096)
            if not raw:
                continue
            self.log.write(json.dumps({'host_time': time.time(), 'raw': raw.decode('utf-8', 'replace')}) + '\n')
            self.log.flush()
            row = decode_record(raw, self.args.serial, self.args.revision)
            # Completion notifications may precede a requested STATUS reply.
            if row['result'] == 'done':
                continue
            return row
        raise OSError('Diagnostic reply timeout')

    def status(self, deadline):
        while time.monotonic() < deadline:
            try:
                return self.query('STATUS')
            except (OSError, self.module.SerialException) as error:
                self.log.write(json.dumps({'host_time': time.time(), 'transport_error': str(error)}) + '\n')
                self.log.flush()
                self.close()
                time.sleep(0.5)
        raise TimeoutError('Device did not return by deadline')

    def run_case(self, action, before):
        if self.query(f'ARM {self.args.serial.upper()} {self.args.revision}')['result'] != 'armed':
            raise ValueError('ARM refused')
        accepted = self.query('RUN ' + action)
        if accepted['result'] != 'accepted' or accepted['sequence'] != before['sequence'] + 1:
            raise ValueError('Action refused or wrong sequence')
        deadline = time.monotonic() + BUDGET.get(action, 25)
        last = before
        saw_stop_held = saw_ap_held = False
        while True:
            time.sleep(0.25)
            after = self.status(deadline)
            if action in RESET_ACTIONS and after['boot_id'] == before['boot_id']:
                continue
            if after['boot_id'] == last['boot_id'] and action not in FAULT_CODES:
                continuity(last, after)
            if after['held']:
                saw_stop_held |= after['stops'] == 1
                saw_ap_held |= after['aps'] == 1
            last = after
            if not after['active']:
                break
        outcome(action, before, after)
        if action in ('LONG', 'STUCK') and not (saw_stop_held and saw_ap_held):
            raise ValueError('Stop/AP thresholds were not observed while held')
        if (after['settings_now'] != before['settings_now'] or
                after['settings_before'] != before['settings_now']):
            raise ValueError('Settings changed during action/reset')
        return after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actions', nargs='+', choices=ACTIONS, default=list(ACTIONS))
    parser.add_argument('--run', action='store_true', help='Execute only after exact-device/image/action authorization')
    parser.add_argument('--serial')
    parser.add_argument('--revision')
    parser.add_argument('--image', type=Path)
    parser.add_argument('--sha256')
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    if not args.run:
        print(json.dumps({'actions': args.actions, 'fault_case_cleanup': 'RESET', 'device_io': False,
                          'note': 'STUCK takes 610 seconds; no live Wi-Fi or RF in this image'}))
        return
    if (not args.serial or not re.fullmatch(r'[0-9a-fA-F]{16}', args.serial) or
            not args.revision or not re.fullmatch(r'[0-9a-f]{12}', args.revision) or
            not args.image or not args.sha256 or not args.evidence):
        parser.error('--run requires serial, clean revision, image, sha256 and a new evidence directory')
    if hashlib.sha256(args.image.read_bytes()).hexdigest() != args.sha256:
        parser.error('Local image hash mismatch')
    os.umask(0o077)
    args.evidence.mkdir(parents=True, exist_ok=False, mode=0o700)
    (args.evidence / 'manifest.json').write_text(json.dumps({**vars(args), 'image': str(args.image),
        'evidence': str(args.evidence)}, indent=2) + '\n')
    with (args.evidence / 'raw.jsonl').open('x') as log:
        connection = Connection(args, log)
        try:
            initial = connection.status(time.monotonic() + 15)
            if initial['active'] or initial['capture_fault'] or initial['held']:
                raise ValueError('Diagnostic not clean and idle at campaign start')
            before = initial
            for action in args.actions:
                after = connection.run_case(action, before)
                if action in FAULT_CODES:
                    after = connection.run_case('RESET', after)
                # A fresh STATUS after two seconds proves both cores and capture
                # resumed; no reliance on the action-completion reply alone.
                time.sleep(2)
                follow = connection.status(time.monotonic() + 5)
                if follow['boot_id'] != after['boot_id'] or follow['capture_fault']:
                    raise ValueError('Post-action recovery fault/reboot')
                continuity(after, follow)
                for field in ('stops', 'aps', 'would_reset', 'releases'):
                    if follow[field] != after[field]:
                        raise ValueError('Unexpected post-release action')
                if follow['settings_now'] != initial['settings_now']:
                    raise ValueError('Campaign changed settings')
                before = follow
                print(action + ': passed bounded diagnostic assertions', flush=True)
            (args.evidence / 'result.json').write_text(json.dumps({'passed': args.actions,
                'scope': 'Synthetic PIO capture, XIP/flash/fault continuity; no physical pad, live AP or RF acceptance'}, indent=2) + '\n')
        except Exception as error:
            (args.evidence / 'failure.json').write_text(json.dumps({
                'error': str(error), 'type': type(error).__name__,
                'scope': 'Campaign stopped; inspect raw evidence before any retry'}, indent=2) + '\n')
            raise
        finally:
            connection.close()


if __name__ == '__main__':
    main()
