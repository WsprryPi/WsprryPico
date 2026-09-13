#!/usr/bin/env python3
"""Opt-in B1 transport pressure. USB observer retains sole RF authority."""
from contextlib import contextmanager
import hashlib
import os
import select
import socket
import ssl
import subprocess
import time

from phase11_5_device_management import save
from phase11_5_inventory import require
from phase11_5_r3_tls_pressure import Pressure, NAME, PEER, main
from phase11_5_r3_transport_plan import CASES, SCHEMA, SCHEMA_B2


def partial_request(label):
    prefix = f'POST /api/v1/jobs HTTP/1.1\r\nHost: {NAME}:18443\r\n'.encode()
    if label == 'partial-header':
        return prefix + b'Content-Length: 20\r\nX-Incomplete: '
    require(label == 'partial-body', 'Unknown partial request')
    return prefix + b'Content-Length: 20\r\nContent-Type: application/json\r\n\r\n{'


def check_transport(previous, current, label):
    if previous is None:
        return
    timeout = label in ('recover-header', 'recover-body', 'recover-pending', 'recover-reader')
    require(current['admitted'] - previous['admitted'] == (1 if label == 'positive' else 2)
            and current['rejected'] == previous['rejected']
            and current['timeouts'] - previous['timeouts'] == int(timeout)
            and current['tls_allocation_failures'] == previous['tls_allocation_failures'],
            'B1 target admission/rejection/timeout/allocation counters')


def ack_rules(table, port):
    require(table.startswith('r3b1_') and table[5:].isalnum()
            and type(port) is int and 1 <= port <= 65535, 'ACK filter identity')
    # Installed only after the TCP three-way handshake. A trace must additionally
    # prove no client payload was lost and the fatal alert was not acknowledged.
    return (f'create table ip {table}\n'
            f'add chain ip {table} output {{ type filter hook output priority 0; policy accept; }}\n'
            f'add rule ip {table} output ip saddr 10.77.15.2 ip daddr 10.77.15.10 '
            f'tcp sport {port} tcp dport 18443 tcp flags & (syn | fin | rst | psh | ack) == ack '
            'counter drop\n')


class TransportPressure(Pressure):
    cases = CASES

    def __init__(self, root, emit):
        super().__init__(root, emit)
        require(self.packet['schema'] in (SCHEMA, SCHEMA_B2), 'Transport runner requires B1/B2 packet')
        self.stalled_stream = None

    def run(self):
        try:
            super().run()
        finally:
            if self.stalled_stream is not None:
                self.stalled_stream.close()

    def write(self, stream, data, end):
        remaining = data
        while remaining:
            size = self.invoke(stream, stream.send, end, remaining)
            require(size > 0, 'B1 write made no progress')
            remaining = remaining[size:]

    def tcp(self, label):
        if label != 'stalled-http-reader':
            return super().tcp(label)
        self.checkpoint()
        self.connections += 1
        require(self.connections <= 15, 'B1 connection budget')
        began = time.monotonic_ns()
        stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            stream.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024)
            stream.setsockopt(socket.IPPROTO_TCP, socket.TCP_WINDOW_CLAMP, 1024)
            stream.settimeout(2)
            stream.connect(('10.77.15.10', 18443))
            stream.setblocking(False)
            self.emit('tcp_open', dict(label=label, began_ns=began, local=list(stream.getsockname()),
                                       peer=list(stream.getpeername())))
            return stream
        except BaseException:
            stream.close()
            raise

    @contextmanager
    def ack_filter(self, stream):
        self.checkpoint()
        b2 = self.packet['schema'] == SCHEMA_B2
        table = ('r3b2_' if b2 else 'r3b1_') + self.packet['nonce'][:16]
        port = stream.getsockname()[1]
        if b2:
            from phase11_5_r3_ack_filter import rules as payload_free_rules
            rules = payload_free_rules(table, port)
        else:
            rules = ack_rules(table, port)
        state = dict(status='INSTALL_PENDING', table=table, port=port, rules=rules,
                     packet_sha256=self.sha, netns=os.readlink('/proc/self/ns/net'))
        save(self.root / 'ack-filter.json', state)
        # A fresh namespace belongs to this packet; never replace a table.
        subprocess.run(['/usr/sbin/nft', '-c', '-f', '-'], input=rules, text=True,
                       check=True, timeout=2, capture_output=True)
        installed = False
        try:
            subprocess.run(['/usr/sbin/nft', '-f', '-'], input=rules, text=True,
                           check=True, timeout=2, capture_output=True)
            installed = True
            self.emit('ack_filter_installed', state)
            yield
        finally:
            if installed:
                try:
                    result = subprocess.run(['/usr/sbin/nft', '-j', 'list', 'table', 'ip', table],
                                            text=True, check=True, timeout=2, capture_output=True)
                    self.emit('ack_filter_counters', dict(table=table, raw_json=result.stdout))
                finally:
                    subprocess.run(['/usr/sbin/nft', 'delete', 'table', 'ip', table],
                                   check=True, timeout=2, capture_output=True)
                    self.emit('ack_filter_removed', dict(table=table))
                    save(self.root / 'ack-filter.json', dict(state, status='REMOVED'))

    def alert(self, label, context, suppress):
        # MemoryBIO keeps the TCP socket open after OpenSSL reports its fatal
        # alert. An SSLSocket context exit would otherwise manufacture closure.
        with self.tcp(label) as stream:
            incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
            tls = context.wrap_bio(incoming, outgoing, server_hostname=NAME)
            end = time.monotonic() + 7

            def flush():
                while outgoing.pending:
                    data = outgoing.read()
                    self.write(stream, data, end)
                    self.emit('ciphertext_tx', dict(label=label, hex=data.hex()))

            def step(method, defer_final_flush=False):
                while True:
                    self.checkpoint()
                    require(time.monotonic() < end, 'Fatal alert deadline')
                    try:
                        value = method()
                        if not defer_final_flush:
                            flush()
                        return value
                    except ssl.SSLWantReadError:
                        flush()
                        data = self.invoke(stream, stream.recv, end, 16384)
                        require(data, 'TCP closed before target fatal alert')
                        self.emit('ciphertext_rx', dict(label=label, hex=data.hex()))
                        incoming.write(data)
                    except ssl.SSLWantWriteError:
                        flush()

            def identity():
                require(hashlib.sha256(tls.getpeercert(binary_form=True)).hexdigest() == PEER
                        and tls.version() == 'TLSv1.3'
                        and tls.selected_alpn_protocol() == 'http/1.1', 'Fatal-alert peer identity')
                self.emit('tls', dict(label=label, peer_sha256=PEER, version='TLSv1.3', alpn='http/1.1'))

            def exercise(handshake_done=False):
                try:
                    if not handshake_done:
                        step(tls.do_handshake)
                        identity()
                    else:
                        flush()
                    step(lambda: tls.read(1))
                except ssl.SSLError as error:
                    require(error.reason == 'TLSV13_ALERT_CERTIFICATE_REQUIRED', 'Expected target alert 116')
                    self.emit('fatal_alert', dict(label=label, alert=116, reason=error.reason))
                    return dict(alert=116, close=self.closed(stream, end))
                raise ValueError('Missing target fatal alert')

            if suppress and self.packet['schema'] == SCHEMA_B2:
                step(tls.do_handshake, defer_final_flush=True)
                identity()
                require(outgoing.pending > 0, 'Missing deferred client final flight')
                self.emit('server_flight_complete', dict(label=label, deferred_client_bytes=outgoing.pending))
                with self.ack_filter(stream):
                    return exercise(handshake_done=True)
            if suppress:
                with self.ack_filter(stream):
                    return exercise()
            return exercise()

    def stalled_reader(self, label, context):
        # lwIP may queue FIN behind unacknowledged response bytes. Keep this
        # socket unread through fresh recovery; slot admission + timeout counters
        # establish logical reclamation without pretending EOF measures it.
        stream = self.tls(label, context, 'http/1.1', time.monotonic() + 5)
        self.stalled_stream = stream
        request = f'GET /app.js HTTP/1.1\r\nHost: {NAME}:18443\r\nConnection: close\r\n\r\n'.encode()
        self.write(stream, request, time.monotonic() + 2)
        self.emit('request', dict(label=label, request_hex=request.hex(),
                                 receive_buffer=stream.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)))
        self.pause(16)
        return dict(client_read_response=False, socket_held_for_recovery=True)

    def run_case(self, label, context, missing, wtp):
        began = time.monotonic_ns()
        self.emit('case_begin', dict(label=label, job_id=self.job['job_id'], launch_epoch=self.launch_epoch))
        if label == 'positive' or label.startswith('recover-'):
            transport = self.positive(label, context)
            check_transport(self.last_transport, transport, label)
            self.last_transport = transport
            result = dict(transport=transport)
            if label == 'recover-reader':
                require(self.stalled_stream is not None, 'Missing held stalled reader')
                self.emit('stalled_client_close', dict(after_authenticated_recovery=True))
                self.stalled_stream.close()
                self.stalled_stream = None
        elif label.startswith('partial-'):
            with self.tls(label, context, 'http/1.1', time.monotonic() + 5) as stream:
                request = partial_request(label)
                self.write(stream, request, time.monotonic() + 2)
                self.emit('request', dict(label=label, request_hex=request.hex()))
                result = dict(close=self.closed(stream, time.monotonic() + 17))
        elif label == 'pending-expiry':
            with self.tls('pending-holder', context, 'http/1.1', time.monotonic() + 5) as held:
                with self.tcp(label) as pending:
                    result = dict(close=self.closed(pending, time.monotonic() + 12))
                    try:
                        held.recv(1)
                    except (ssl.SSLWantReadError, ssl.SSLWantWriteError, BlockingIOError):
                        pass  # Includes processing non-application TLS session tickets.
                    else:
                        raise ValueError('HTTP holder ended or returned application data before pending expiry')
                result['holder_open_at_expiry'] = True
        elif label == 'stalled-http-reader':
            result = self.stalled_reader(label, context)
        elif label in ('failed-alert-ack', 'failed-alert-wait'):
            result = self.alert(label, missing, label == 'failed-alert-wait')
        else:
            raise ValueError('Unknown B1 pressure case')
        self.checkpoint()
        if label != 'positive' and not label.startswith('recover-'):
            self.recover_until = time.monotonic() + 15
        self.emit('case_finish', dict(label=label, job_id=self.job['job_id'], launch_epoch=self.launch_epoch,
                                     began_ns=began, **result))
        self.pause(.5)


if __name__ == '__main__':
    main(TransportPressure)
