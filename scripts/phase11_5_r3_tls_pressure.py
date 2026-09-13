#!/usr/bin/env python3
"""Opt-in R3 A1 client pressure; never owns USB, submits jobs or changes a fixture."""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import select
import socket
import ssl
import time

from phase11_5_inventory import require
from phase11_5_device_management import digest, save
from phase11_5_browser_jobs import NAME, PEER, admit_snapshot
from phase11_5_r3_tls_plan import CASES, validate


def running_epoch(info, status, packet, job):
    """Join distinct Console and WTP shapes without inventing Console owner/job fields."""
    console = info['status']
    require(console['boot_id'] == status['boot_id'] == packet['boot_id'], 'Pressure boot changed')
    if console['state'] != 'running' or status['state'] != 'running':
        return None
    require(console['output_active'] is True and status['output_active'] is True,
            'Running observation lacks active output')
    if status['job_id'] != job['job_id']:
        require(status['job_id'] in {j['job_id'] for j in packet['jobs']}
                and status['owner_id'] == packet['owner_id'], 'Foreign Running job')
        return None  # A previous finite job may still be finishing during the next wait.
    require(status['owner_id'] == packet['owner_id'], 'Pressure owner changed')
    epoch = int(info['launch_epoch'])
    require(epoch > 0, 'Running INFO has no launch epoch')
    return epoch


def check_transport(previous, current, label):
    expected = {'recover-certificate': ((2, 2), 0, 0),
                'recover-handshake': ((2, 2), 0, 1),
                'recover-slots': ((2, 3), 1, 0),
                'recover-wtp': ((2, 2), 0, 0), 'positive': ((1, 1), 0, 0)}
    if previous is not None:
        admission, rejected, timeouts = expected[label]
        require(admission[0] <= current['admitted'] - previous['admitted'] <= admission[1]
                and current['rejected'] - previous['rejected'] == rejected
                and current['timeouts'] - previous['timeouts'] == timeouts,
                'Target counters do not establish intended trigger/recovery')
        require(current['tls_allocation_failures'] == previous['tls_allocation_failures'],
                'Unexpected TLS allocation failure')


def response(raw, packet, job):
    """Decode the actual response bytes; reject truncated or ambiguous framing."""
    headers, body = raw.split(b'\r\n\r\n', 1)
    lines = headers.split(b'\r\n')
    require(re.fullmatch(rb'HTTP/1\.1 200 [\t\x20-\x7e\x80-\xff]*', lines[0]) is not None,
            'R3 HTTP status')
    fields = {}
    for line in lines[1:]:
        key, value = line.split(b':', 1)
        key = key.strip().lower()
        require(key not in fields, 'Duplicate HTTP header')
        fields[key] = value.strip()
    require(b'transfer-encoding' not in fields and int(fields[b'content-length']) == len(body)
            and len(raw) <= 32768, 'R3 HTTP framing/size')
    value = json.loads(body)
    status = value['job']
    require(status['boot_id'] == packet['boot_id'] and status['job_id'] == job['job_id']
            and status['owner_id'] == packet['owner_id'] and status['state'] == 'running'
            and status['output_active'] is True, 'HTTPS did not overlap owned Running RF')
    transport = value['transport']
    require(transport['active'] == 2 and transport['pending'] == 0,
            'Positive control requires one production WTP plus this HTTPS connection')
    return value


class Pressure:
    def __init__(self, root, emit):
        self.root, self.emit = root, emit
        self.packet_path = root / 'jobs.json'
        self.packet = validate(json.loads(self.packet_path.read_text()))
        self.sha = digest(self.packet_path)
        self.plan = json.loads((root / 'load.json').read_text())
        self.observer = None
        self.job = None
        self.launch_epoch = None
        self.connections = 0
        self.last_transport = None
        self.recover_until = None
        self.deadline = time.monotonic() + 310

    def checkpoint(self):
        require(time.monotonic() < self.deadline and digest(self.packet_path) == self.sha,
                'R3 pressure deadline/packet')
        require(not any((self.root / name).exists() for name in
                        ('load-failed.json', 'observer-failure.json', 'observer-finish.json')),
                'Dependent pressure stopped by observer/load')
        snapshots = []
        for kind, budget in (('info', 2_000_000_000), ('status', 6_000_000_000)):
            item = json.loads((self.root / f'observer-{kind}.json').read_text())
            pending_path = self.root / ('observer-' + ('console_tx' if kind == 'info' else 'wtp_tx') + '.json')
            pending = json.loads(pending_path.read_text()) if pending_path.exists() else None
            admit_snapshot(item, time.monotonic_ns(), budget, self.sha, pending,
                           'INFO' if kind == 'info' else 'STATUS')
            identity = (item['pid'], item['pid_start_ticks'])
            if self.observer is None:
                self.observer = identity
            require(identity == self.observer, 'Observer process changed')
            stat = Path(f'/proc/{identity[0]}/stat').read_text().rsplit(')', 1)[1].split()[19]
            require(stat == identity[1], 'Observer exited or PID reused')
            value = item['value']['value']
            status = value['status'] if kind == 'info' else value
            require(status['boot_id'] == self.packet['boot_id'], 'Pressure boot changed')
            snapshots.append(item)
        if self.job is not None:
            epoch = running_epoch(snapshots[0]['value']['value'], snapshots[1]['value']['value'],
                                  self.packet, self.job)
            require(epoch is not None and epoch == self.launch_epoch,
                    'Pressure requires fresh Running RF in the bound launch epoch')
        return snapshots

    def pause(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.checkpoint()
            time.sleep(min(.05, max(0, end - time.monotonic())))

    def tcp(self, label):
        self.checkpoint()
        self.connections += 1
        require(self.connections <= 12, 'R3 connection budget')
        began = time.monotonic_ns()
        stream = socket.create_connection(('10.77.15.10', 18443), timeout=2)
        stream.setblocking(False)
        self.emit('tcp_open', dict(label=label, began_ns=began, local=list(stream.getsockname()),
                                   peer=list(stream.getpeername())))
        return stream

    def invoke(self, stream, method, deadline, *args):
        while True:
            self.checkpoint()
            require(time.monotonic() < deadline, 'R3 socket operation deadline')
            try:
                return method(*args)
            except (ssl.SSLWantReadError, ssl.SSLWantWriteError, BlockingIOError) as error:
                writing = isinstance(error, ssl.SSLWantWriteError)
                select.select([] if writing else [stream], [stream] if writing else [], [], .05)

    def tls(self, label, context, alpn, deadline):
        raw = self.tcp(label)
        try:
            stream = context.wrap_socket(raw, server_hostname=NAME, do_handshake_on_connect=False,
                                         suppress_ragged_eofs=False)
        except BaseException:
            raw.close()
            raise
        try:
            self.invoke(stream, stream.do_handshake, deadline)
            peer = hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest()
            require(peer == PEER and stream.version() == 'TLSv1.3'
                    and stream.selected_alpn_protocol() == alpn, 'R3 verified TLS identity/protocol')
            self.emit('tls', dict(label=label, peer_sha256=peer, version=stream.version(), alpn=alpn))
            return stream
        except BaseException:
            stream.close()
            raise

    def positive(self, label, context):
        end = time.monotonic() + 15
        if label.startswith('recover-'):
            require(self.recover_until is not None, 'Recovery has no preceding trigger')
            end = min(end, self.recover_until)
        with self.tls(label, context, 'http/1.1', end) as stream:
            request = f'GET /api/v1/status HTTP/1.1\r\nHost: {NAME}:18443\r\nConnection: close\r\n\r\n'.encode()
            remaining = request
            while remaining:
                sent = self.invoke(stream, stream.send, end, remaining)
                require(sent > 0, 'HTTPS write made no progress')
                remaining = remaining[sent:]
            raw = b''
            while True:
                chunk = self.invoke(stream, stream.recv, end, 4096)
                if not chunk:
                    break
                raw += chunk
                require(len(raw) <= 32768, 'HTTPS response size')
                # The embedded server closes TCP without TLS close_notify. Stop
                # at a complete Content-Length message, never accept a short read.
                if b'\r\n\r\n' in raw:
                    head, body = raw.split(b'\r\n\r\n', 1)
                    lengths = [line.split(b':', 1)[1].strip() for line in head.split(b'\r\n')
                               if line.lower().startswith(b'content-length:')]
                    if len(lengths) == 1 and len(body) >= int(lengths[0]):
                        break
            self.emit('http', dict(label=label, request_hex=request.hex(), response_hex=raw.hex()))
            value = response(raw, self.packet, self.job)
        return value['transport']

    def closed(self, stream, deadline):
        try:
            data = self.invoke(stream, stream.recv, deadline, 1)
            require(data == b'', 'Unexpected data before rejection/timeout')
            return 'eof'
        except ConnectionResetError as error:
            require(error.errno == errno.ECONNRESET, 'Unexpected reset error')
            return 'reset'
        except ssl.SSLEOFError:
            # Only used after a verified duplicate-WTP handshake. This is a
            # transport close, never evidence of certificate validation failure.
            return 'tls-eof'

    def run_case(self, label, context, missing, wtp):
        began = time.monotonic_ns()
        self.emit('case_begin', dict(label=label, job_id=self.job['job_id'], launch_epoch=self.launch_epoch))
        if label == 'positive' or label.startswith('recover-'):
            transport = self.positive(label, context)
            check_transport(self.last_transport, transport, label)
            self.last_transport = transport
            result = dict(transport=transport)
        elif label == 'missing-certificate':
            end = time.monotonic() + 5
            try:
                with self.tls(label, missing, 'http/1.1', end) as stream:
                    self.invoke(stream, stream.recv, end, 1)
            except ssl.SSLError as error:
                require(error.reason == 'TLSV13_ALERT_CERTIFICATE_REQUIRED',
                        'Missing-certificate case requires target fatal alert 116, not EOF or client validation')
                result = dict(alert=116, reason=error.reason, library=error.library)
            else:
                raise ValueError('Target did not emit missing-certificate fatal alert')
        elif label == 'silent-handshake':
            with self.tcp(label) as stream:
                result = dict(close=self.closed(stream, time.monotonic() + 12))
            # Includes client TCP setup. Target accept/activation timestamps are
            # unavailable, so this is a client-observed 12 s bound plus a target
            # timeout-counter delta, not precise target-deadline metrology.
        elif label == 'slot-excess':
            with self.tcp('slot-active') as first:
                self.pause(.5)
                with self.tcp('slot-pending') as second:
                    self.pause(.5)
                    with self.tcp('slot-excess') as excess:
                        result = dict(close=self.closed(excess, time.monotonic() + 2))
                    # Ensure the supposed supported/pending sockets were not
                    # already rejected. No bytes are sent; closure is not timeout evidence.
                    for stream in (first, second):
                        readable = select.select([stream], [], [], 0)[0]
                        require(not readable, 'Supported/pending slot closed prematurely')
            result['client_closed_supported_slots'] = True
        elif label == 'duplicate-wtp':
            with self.tls(label, wtp, 'wtp/1', time.monotonic() + 5) as stream:
                result = dict(close=self.closed(stream, time.monotonic() + 2))
        else:
            raise ValueError('Unknown pressure case')
        self.checkpoint()
        if label not in ('positive',) and not label.startswith('recover-'):
            self.recover_until = time.monotonic() + 15
        self.emit('case_finish', dict(label=label, job_id=self.job['job_id'], launch_epoch=self.launch_epoch,
                                     began_ns=began, **result))
        self.pause(.5)  # Bounded server cleanup before the next fresh connection.

    def run(self):
        p = self.plan
        require(p['boot_id'] == self.packet['boot_id'] and p['device_id'] == self.packet['device_id']
                and p['seconds'] == 300 and p['browser'] is False and p['address'] == '10.77.15.10'
                and os.readlink('/proc/self/ns/net') == p['netns']
                and os.readlink('/proc/self/ns/mnt') == p['mountns'], 'R3 isolated RF-off controller load')
        contexts = []
        for role, alpn in (('browser', 'http/1.1'), (None, 'http/1.1'), ('controller', 'wtp/1')):
            ctx = ssl.create_default_context(cafile=p['ca'])
            ctx.minimum_version = ctx.maximum_version = ssl.TLSVersion.TLSv1_3
            ctx.set_alpn_protocols([alpn])
            if role:
                ctx.load_cert_chain(p[role + '_cert'], p[role + '_key'])
            contexts.append(ctx)
        initial = self.checkpoint()
        previous_epoch = int(initial[0]['value']['value']['launch_epoch'])
        save(self.root / 'pressure-ready.json', dict(packet_sha256=self.sha))
        for index, job in enumerate(self.packet['jobs']):
            limit = time.monotonic() + 160
            while True:
                values = self.checkpoint()
                epoch = running_epoch(values[0]['value']['value'], values[1]['value']['value'],
                                      self.packet, job)
                if epoch is not None:
                    require(epoch > previous_epoch, 'RF job did not advance launch epoch')
                    break
                require(time.monotonic() < limit, 'RF job did not reach observed Running')
                time.sleep(.05)
            self.job = job
            self.launch_epoch = previous_epoch = epoch
            for label in CASES[index]:
                self.run_case(label, *contexts)
            save(self.root / f'pressure-job-{index}.json', dict(status='PASS', packet_sha256=self.sha,
                                                              job_id=job['job_id']))
            self.job = None
            self.launch_epoch = None
        self.emit('finish', dict(status='CAPTURED_REQUIRES_AUDIT', connections=self.connections))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        print('Plan only; no files, sockets or devices accessed.')
        return
    root = args.root.resolve(strict=True)
    require(root.stat().st_mode & 0o077 == 0, 'Private R3 case directory')
    os.umask(0o077)
    with (root / 'pressure.jsonl').open('x') as log:
        sequence = 0

        def emit(kind, value):
            nonlocal sequence
            log.write(json.dumps(dict(sequence=sequence, kind=kind, value=value,
                                      monotonic_ns=time.monotonic_ns())) + '\n')
            log.flush()
            os.fsync(log.fileno())
            sequence += 1

        try:
            pressure = Pressure(root, emit)
            emit('start', dict(packet_sha256=pressure.sha, load_sha256=digest(root / 'load.json')))
            pressure.run()
        except BaseException as error:
            emit('failure', dict(type=type(error).__name__, error=str(error)))
            save(root / 'load-failed.json', dict(source='R3 pressure', error=str(error)))
            raise


if __name__ == '__main__':
    main()
