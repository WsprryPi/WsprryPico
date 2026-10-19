#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finite, explicit Linux GPIO/USB clock-probe check; never submits time or RF jobs."""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import time

from usb_inventory import exclusive_port, loads_console


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def identify_usb_parent(parent, serial):
    """Bind the nearest USB device, excluding serial-bearing ancestor hubs."""
    identities = [p for p in [parent, *parent.parents]
                  if (p/'idVendor').is_file() and (p/'idProduct').is_file()]
    require(bool(identities), 'USB physical identity missing')
    device = identities[0]
    require((device/'serial').is_file() and
            (device/'serial').read_text().strip().upper() == serial and
            (device/'idVendor').read_text().strip() == 'cafe' and
            (device/'idProduct').read_text().strip() == '4012', 'USB physical identity')
    return {'path': str(device), 'serial': serial, 'vendor': 'cafe', 'product': '4012'}


def validate_edges(record, events, line, previous_sequence):
    """Reject miswiring, duplicates, lost events and nonphysical time order."""
    require(record.get('ok') is True and record.get('schema') == 'pico-clock-probe/1',
            'Pico pulse failed')
    require(record.get('gpio') == 22 and record.get('pin_restored') is True and
            record.get('high_readback') is True and record.get('low_readback') is True,
            'Pico pulse/readback/restoration failed')
    require(len(events) == 2 and all(e['line'] == line for e in events),
            'Expected exactly one pulse on the selected Pi input and none on the other')
    require([e['edge'] for e in events] == ['RISING_EDGE', 'FALLING_EDGE'], 'Wrong pulse edges')
    require([e['sequence'] for e in events] == [previous_sequence + 1, previous_sequence + 2],
            'GPIO event loss or unexpected intervening edge')
    width = events[1]['timestamp_ns'] - events[0]['timestamp_ns']
    require(500_000 <= width <= 10_000_000, 'Observed pulse width outside 0.5–10 ms')
    before, after = record['rise_before'], record['rise_after']
    a, b = int(record['rise_raw_lower_ns']), int(record['rise_raw_upper_ns'])
    require(record.get('raw_resolution_ns') == 1000 and
            a == int(before['monotonic_now_ns']) and
            b == int(after['monotonic_now_ns'])+1000, 'Missing physical edge quantization bounds')
    require(0 <= b - a <= 50_000, 'Pico edge bracket exceeds 50 us')
    require(b <= int(record['fall_before_ns']) <= int(record['fall_after_ns']),
            'Pico edge timestamps regressed')
    return {'rising_utc_ns': events[0]['timestamp_ns'], 'pulse_width_ns': width,
            'pico_edge_bracket_ns': b-a, 'clock_valid': record.get('clock_valid') is True,
            'absolute_timestamp_delay_qualified': False}


@contextlib.contextmanager
def lock(path):
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o660)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), 'Unsafe lock file')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


class Console:
    def __init__(self, fd):
        self.fd, self.wire = fd, []

    def request(self, command):
        require(len(command) <= 240 and '\n' not in command, 'Console command bound')
        sent = (command+'\n').encode()
        self.wire.append({'sent': command, 'utc_ns': time.time_ns()})
        require(os.write(self.fd, sent) == len(sent), 'Partial USB command; do not replay')
        pending = bytearray()
        until = time.monotonic()+5
        while time.monotonic() < until:
            if select.select([self.fd], [], [], .1)[0]:
                data = os.read(self.fd, 4096)
                require(bool(data), 'Console disconnected')
                pending.extend(data)
                require(len(pending) <= 131072, 'Console response bound')
                if b'\n' in pending:
                    line, _, tail = pending.partition(b'\n')
                    require(not tail.strip(), 'Unexpected extra Console reply')
                    value = loads_console(line.decode('utf8'))
                    self.wire.append({'received': value, 'utc_ns': time.time_ns()})
                    return value
        raise TimeoutError('Console reply missing; retrieve STATUS before any new pulse')


def reference():
    text = subprocess.check_output(['chronyc', 'tracking'], text=True, timeout=5)
    fields = dict((k.strip(), v.strip()) for k, v in
                  (line.split(':', 1) for line in text.splitlines() if ':' in line))
    require('(PPS)' in fields['Reference ID'] and fields['Stratum'] == '1' and
            fields['Leap status'] == 'Normal', 'Host GPS PPS is not selected')
    source = Path('/dev/pps-gps').resolve().name
    assertion = (Path('/sys/class/pps')/source/'assert').read_text().strip()
    stamp = assertion.split('#')[0]
    seconds, fraction = stamp.split('.')
    age = time.time_ns() - (int(seconds)*10**9 + int(fraction.ljust(9, '0')))
    require(-1_000_000 <= age <= 2_000_000_000, 'Stale GPS PPS assertion')
    return {'tracking': text, 'pps_device': source, 'pps_assertion': assertion,
            'absolute_timestamp_delay_qualified': False}


def input_state(line):
    text = subprocess.check_output(['pinctrl', 'get', str(line)], text=True, timeout=3)
    found = re.fullmatch(r'\s*\d+: (no|ip)\s+(p[udn]) \| .*\n', text)
    require(found is not None, 'Measurement GPIO is already configured for another function')
    return text, found.groups()


def restore_inputs(saved):
    import gpiod
    with gpiod.Chip('/dev/gpiochip0') as chip:
        require(all(not chip.get_line_info(n).used for n in saved),
                'GPIO acquired by another process; restoration paused')
    for line, (original, options) in saved.items():
        current, _ = input_state(line)
        require(re.search(r': ip\s+pd \|', current), 'Foreign GPIO change; restoration paused')
        subprocess.run(['pinctrl', 'set', str(line), *options], check=True, timeout=3)
        require(input_state(line)[0] == original, 'GPIO input state restoration failed')


def run(args, output, report):
    import gpiod
    from gpiod.line import Direction, Edge, Clock, Bias
    report.update({'schema': 'pico-clock-probe-capture/1', 'start_utc_ns': time.time_ns(),
              'serial': args.serial, 'device_id': args.device_id, 'line': args.line,
              'other_line': 23 if args.line == 22 else 22, 'records': [],
              'rf_jobs': False, 'time_submissions': False, 'absolute_utc_qualified': False})
    directory = Path('/run/lock/wsprrypico')
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(not directory.is_symlink(), 'Unsafe device lock directory')
    with contextlib.ExitStack() as stack:
        for path in [directory/(args.serial+'.lock'),
                     Path('/tmp/wsprrypico-led-'+args.serial+'.lock'),
                     Path('/tmp/wsprrypico-clock-probe-inputs.lock')]:
            stack.enter_context(lock(path))
        # Bind the selected tty's real USB parent, not its mutable ttyACM name.
        tty = Path(args.console).resolve().name
        parent = (Path('/sys/class/tty')/tty/'device').resolve()
        report['usb_identity'] = identify_usb_parent(parent, args.serial)
        fd = stack.enter_context(exclusive_port(Path(args.console)))
        console = Console(fd)
        report['wire'] = console.wire
        initial = console.request('INFO'); report['initial_info'] = initial
        require(initial.get('ok') is True and initial['device_id'] == args.device_id and
                initial['revision'] == args.revision, 'Firmware/device identity')
        boot = initial['status']['boot_id']; report['boot_id'] = boot
        require(initial['network']['ntp_server'] == 'pool.ntp.org', 'Internet pool setting changed')
        require(initial['status']['owner_id'] is None and not initial['status']['output_active'] and
                not initial['status']['enabled'], 'Board is active, owned or schedule-enabled')
        prefix = f'CLOCKPROBE {args.device_id} {boot} '
        status = console.request(prefix+'STATUS'); report['initial_status'] = status
        require(status.get('ok') is True, 'Clock instrumentation unavailable')
        sequence = int(status['last_sequence'])
        report['reference_before'] = reference()
        saved = {n: input_state(n) for n in [22, 23]}
        report['original_gpio'] = saved
        request = None
        try:
            def settings(up=False):
                return {n: gpiod.LineSettings(direction=Direction.INPUT, edge_detection=Edge.BOTH,
                        event_clock=Clock.REALTIME,
                        bias=Bias.PULL_UP if up and n == args.line else Bias.PULL_DOWN)
                        for n in [22, 23]}
            request = gpiod.request_lines('/dev/gpiochip0', consumer='wsprrypico-clock-probe',
                                           config=settings())
            def drain(wait=.05):
                events = []
                while request.wait_edge_events(timeout=wait):
                    events.extend({'line': e.line_offset, 'timestamp_ns': e.timestamp_ns,
                                   'edge': e.event_type.name, 'sequence': e.global_seqno,
                                   'line_sequence': e.line_seqno} for e in request.read_edge_events())
                    require(len(events) <= 64, 'Unexpected active measurement wiring')
                    wait = .02
                return events
            report['continuity'] = []
            report['continuity_mode'] = 'pulse_output' if args.pulse_only else 'weak_input_bias'
            if args.pulse_only:
                # Explicit input-only preparation clears a possible A2 pad
                # leakage state before the measurement interval begins.
                prepared = console.request(prefix+'READ')
                report['input_preparation'] = prepared
                require(prepared.get('ok') is True and prepared.get('level') is False and
                        prepared.get('output_enabled') is False and
                        prepared.get('pad_settling', 0x40) & 0x40 == 0,
                        'Pico input did not settle low before output measurement')
            for high in ([] if args.pulse_only else [False, True, False, True, False]):
                request.reconfigure_lines(settings(high)); time.sleep(.02)
                before = [x.name for x in request.get_values([22, 23])]
                value = console.request(prefix+'READ')
                report['continuity'].append({'pi_pull_up': high, 'pi_before': before,
                        'pico': value, 'pi_after': [x.name for x in request.get_values([22, 23])]})
                if value.get('ok') is not True or value.get('level') is not high:
                    report['continuity_failure_edges'] = drain()
                require(value.get('ok') is True, 'Pico passive pin read failed')
                require(value.get('level') is high, 'Pico GP22 does not follow the selected Pi input bias')
            discarded = drain(); report['continuity_edges'] = discarded
            previous = discarded[-1]['sequence'] if discarded else 0
            for _ in range(args.count):
                time.sleep(.6)
                unexpected = drain(wait=0)
                if unexpected:
                    report['uncommanded_edges'] = unexpected
                    raise ValueError('Uncommanded edge before pulse')
                sequence += 1
                record = console.request(prefix+f'PULSE {sequence}')
                report['records'].append({'pico': record})
                require(record.get('device_id') == args.device_id and record.get('boot_id') == boot and
                        int(record.get('sequence', 0)) == sequence, 'Pulse identity/sequence')
                events = drain(); report['records'][-1]['events'] = events
                result = validate_edges(record, events, args.line, previous)
                report['records'][-1]['measurement'] = result
                previous = events[-1]['sequence']
                duplicate = console.request(prefix+f'PULSE {sequence}')
                extra = drain()
                report['records'][-1]['duplicate_events'] = extra
                require(duplicate == record and not extra,
                        'Duplicate request changed record or emitted another pulse')
            report['wiring_verified'] = True
        finally:
            if request is not None:
                try:
                    request.reconfigure_lines(settings())
                finally:
                    request.release()
                restore_inputs(saved)
                report['gpio_restored'] = True
            output.write_text(json.dumps(report, indent=2)+'\n')
        final = console.request('INFO'); report['final_info'] = final
        require(final['status']['boot_id'] == boot and final['revision'] == args.revision and
                final['network']['ntp_server'] == 'pool.ntp.org' and
                final['status']['owner_id'] is None and not final['status']['output_active'] and
                not final['status']['enabled'], 'Final identity/state changed')
        report['reference_after'] = reference()
        report['finish_utc_ns'] = time.time_ns()
        output.write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--console', required=True)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--device-id', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--line', type=int, choices=[22, 23], required=True)
    parser.add_argument('--count', type=int, choices=range(1, 17), default=3)
    parser.add_argument('--pulse-only', action='store_true',
                        help='Verify commanded Pico output edges without the optional weak input-bias check')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(re.fullmatch('[0-9A-F]{16}', args.serial) is not None, 'USB serial syntax')
    require(re.fullmatch('[0-9a-f]{32}', args.device_id) is not None, 'Device ID syntax')
    os.umask(0o077)
    with args.output.open('x'):
        pass
    args.output.chmod(0o600)
    def timeout(_s, _f):
        raise TimeoutError('Finite 60 second clock-probe deadline')
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(60)
    report = {}
    try:
        result = run(args, args.output, report)
    except BaseException as error:
        report['failure'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'wiring_verified': result['wiring_verified'],
                      'gpio_restored': result['gpio_restored'], 'pulses': len(result['records'])}))


if __name__ == '__main__':
    main()
