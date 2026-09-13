"""B1 fault-injection discrimination; no target, network or fixture access."""
import copy
import contextlib
import errno
import hashlib
import json
import os
from pathlib import Path
import struct
import ssl
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase11_5_r3_tls_tests import packet
from phase11_5_r3_transport_plan import SCHEMA, SCHEMA_B2, ACK_POLICY_B2, CASES, validate
from phase11_5_r3_tls_pressure import Pressure
from phase11_5_r3_transport_pressure import TransportPressure, partial_request, ack_rules, check_transport
from audit_phase11_5_r3_transport import tcp_packets, audit_case_flow


def tcp(t, server=False, flags=16, seq=1, ack=1, size=0, window=1024):
    a, b = ('10.77.15.10', '10.77.15.2') if server else ('10.77.15.2', '10.77.15.10')
    return dict(realtime_ns=int(t * 1e9), source=a, destination=b, sport=18443 if server else 45000,
                dport=45000 if server else 18443, flags=flags, seq=seq, ack=ack, size=size, window=window,
                payload_hex='00' * size)


def group(label):
    return [dict(kind='tcp_open', monotonic_ns=10100000000, value=dict(
                    local=['10.77.15.2', 45000], began_ns=10000000000)),
            dict(kind='tls', monotonic_ns=11000000000, value={})]


class TransportTests(unittest.TestCase):
    def test_new_scope_dispatch_preserves_old_budget(self):
        from phase11_5_f1_plan import validate_rf_packet
        p = packet() | dict(schema=SCHEMA, pressure_cases=[list(c) for c in CASES],
                            maximum_tcp_connections=15, observer_bracket_policy='request-cadence-and-roundtrip-v1')
        validate(p)
        validate_rf_packet(p)
        for change in ({'maximum_tcp_connections': 16}, {'observer_bracket_policy': None},
                       {'pressure_cases': [['positive']]}, {'nominal_seconds': 301}):
            with self.assertRaises(ValueError):
                validate(p | change)
        obj = object.__new__(Pressure)
        obj.packet = packet() | {'maximum_tcp_connections': 999}
        obj.connections = 12
        obj.checkpoint = Mock()
        with patch('phase11_5_r3_tls_pressure.socket.create_connection', side_effect=AssertionError('socket')):
            with self.assertRaisesRegex(ValueError, 'connection budget'):
                obj.tcp('positive')

    def test_incomplete_requests_are_distinct_and_cannot_dispatch(self):
        header = partial_request('partial-header')
        body = partial_request('partial-body')
        self.assertNotIn(b'\r\n\r\n', header)
        self.assertIn(b'Content-Length: 20\r\n', body)
        self.assertEqual(body.split(b'\r\n\r\n')[1], b'{')
        with self.assertRaises(ValueError):
            partial_request('other')

    def test_filter_scope_is_one_ipv4_tuple_and_ack_only(self):
        text = ack_rules('r3b1_1234', 45000)
        self.assertIn('create table ip r3b1_1234', text)
        self.assertIn('tcp sport 45000 tcp dport 18443', text)
        self.assertIn('(syn | fin | rst | psh | ack) == ack', text)
        self.assertEqual(text.count('counter drop'), 1)
        for table, port in [('r3b1_x;delete ruleset', 1234), ('foreign', 1234), ('r3b1_x', 65536), ('r3b1_x', True)]:
            with self.assertRaises(ValueError):
                ack_rules(table, port)

    def test_filter_cleanup_runs_even_when_counter_capture_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            pressure = object.__new__(TransportPressure)
            pressure.root, pressure.packet, pressure.sha = Path(temp), {'nonce': '1' * 32, 'schema': SCHEMA}, '2' * 64
            pressure.checkpoint, pressure.emit = Mock(), Mock()
            stream = Mock()
            stream.getsockname.return_value = ('10.77.15.2', 45000)
            with patch('phase11_5_r3_transport_pressure.os.readlink', return_value='net:[123]'), \
                 patch('phase11_5_r3_transport_pressure.subprocess.run',
                       side_effect=[Mock(), Mock(), RuntimeError('counter capture failed'), Mock()]) as command:
                with self.assertRaisesRegex(RuntimeError, 'counter capture'):
                    with pressure.ack_filter(stream):
                        pass
            self.assertEqual(command.call_args_list[-1].args[0][:4], ['/usr/sbin/nft', 'delete', 'table', 'ip'])
            self.assertEqual(json.loads((Path(temp) / 'ack-filter.json').read_text())['status'], 'REMOVED')

    def test_new_load_envelope_reuses_actual_a1h2_producer_bytes(self):
        if not os.environ.get('PHASE115_R3_A1H2_EVIDENCE'):
            self.skipTest('Private A1h2 archive not provided')
        from audit_phase11_5_load import audit
        original = Path(os.environ['PHASE115_R3_A1H2_EVIDENCE']).resolve()
        p = json.loads((original / 'tls-a1/jobs.json').read_text()) | {'schema': SCHEMA}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for path in (original / 'tls-a1').iterdir():
                if path.name != 'result.json':
                    (root / path.name).symlink_to(path)
            result = json.loads((original / 'tls-a1/result.json').read_text()) | {'capture_exit': 0}
            (root / 'result.json').write_text(json.dumps(result))
            audit(root, original / 'pi/phase115_tls_observer_test.py', p, cadence_policy='single-flight-admin-v1')
            result['capture_exit'] = 1
            (root / 'result.json').write_text(json.dumps(result))
            with self.assertRaisesRegex(ValueError, 'Coordinator'):
                audit(root, original / 'pi/phase115_tls_observer_test.py', p, cadence_policy='single-flight-admin-v1')

    def test_b2_policy_cannot_change_b1_scoring(self):
        p = packet() | dict(schema=SCHEMA_B2, pressure_cases=[list(c) for c in CASES],
                            maximum_tcp_connections=15, observer_bracket_policy='request-cadence-and-roundtrip-v1',
                            ack_filter_policy=ACK_POLICY_B2)
        validate(p)
        for change in ({'schema': SCHEMA}, {'ack_filter_policy': None}):
            with self.assertRaisesRegex(ValueError, 'filter policy'):
                validate(p | change)

    def test_real_openssl_client_defers_final_flight_until_filter_is_ready(self):
        from phase11_5_r3_tls_pressure import NAME
        with tempfile.TemporaryDirectory() as temp:
            cert, key = Path(temp) / 'cert.pem', Path(temp) / 'key.pem'
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                            '-subj', '/CN=' + NAME, '-keyout', str(key), '-out', str(cert)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15)
            server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            server_context.minimum_version = server_context.maximum_version = ssl.TLSVersion.TLSv1_3
            server_context.load_cert_chain(cert, key)
            server_context.load_verify_locations(cert)
            server_context.verify_mode = ssl.CERT_REQUIRED
            server_context.set_alpn_protocols(['http/1.1'])
            client = ssl.create_default_context(cafile=str(cert))
            client.minimum_version = client.maximum_version = ssl.TLSVersion.TLSv1_3
            client.set_alpn_protocols(['http/1.1'])
            incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
            server = server_context.wrap_bio(incoming, outgoing, server_side=True)
            state = dict(failed=False, filter=False)
            sends = []

            class Stream:
                def send(self, data):
                    sends.append(dict(filtered=state['filter'], data=data))
                    incoming.write(data)
                    try:
                        server.do_handshake()
                    except ssl.SSLWantReadError:
                        pass
                    except ssl.SSLError as error:
                        if error.reason != 'PEER_DID_NOT_RETURN_A_CERTIFICATE':
                            raise
                        state['failed'] = True
                    return len(data)

                def recv(self, size):
                    if outgoing.pending:
                        return outgoing.read(size)
                    if state['failed']:
                        raise ConnectionResetError(errno.ECONNRESET, 'server closed after fatal alert')
                    raise AssertionError('Client waited without driving its outgoing TLS flight')

            stream = Stream()
            pressure = object.__new__(TransportPressure)
            pressure.packet = {'schema': SCHEMA_B2}
            pressure.checkpoint = Mock()
            pressure.emit = Mock()
            pressure.tcp = Mock(return_value=contextlib.nullcontext(stream))
            pressure.invoke = lambda s, method, deadline, *args: method(*args)

            @contextlib.contextmanager
            def filtering(s):
                self.assertIs(s, stream)
                self.assertFalse(state['failed'])
                self.assertTrue(sends)
                self.assertFalse(any(v['filtered'] for v in sends))
                state['filter'] = True
                yield
                state['filter'] = False

            pressure.ack_filter = filtering
            peer = hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert.read_text())).hexdigest()
            with patch('phase11_5_r3_transport_pressure.PEER', peer):
                self.assertEqual(pressure.alert('failed-alert-wait', client, True), dict(alert=116, close='reset'))
            self.assertTrue(state['failed'])
            self.assertEqual(sum(v['filtered'] for v in sends), 1)
            self.assertTrue(any(call.args[0] == 'server_flight_complete' for call in pressure.emit.call_args_list))

    def test_expected_counters_separate_pending_from_silent_activation(self):
        before = dict(admitted=20, rejected=3, timeouts=7, tls_allocation_failures=0)
        after = before | dict(admitted=22, timeouts=8)
        check_transport(before, after, 'recover-pending')
        for wrong in ({'admitted': 23}, {'timeouts': 9}, {'timeouts': 7}, {'tls_allocation_failures': 1}):
            with self.assertRaises(ValueError):
                check_transport(before, after | wrong, 'recover-pending')

    def test_http_timeout_rejects_client_close_and_early_target_close(self):
        flow = [tcp(10, flags=2), tcp(10.01, True, flags=18), tcp(25.02, True, flags=4)]
        audit_case_flow('partial-header', group('partial-header'), flow, 0)
        for changed in (flow[:-1] + [tcp(12, True, flags=4)],
                        flow[:-1] + [tcp(24, flags=1), flow[-1]], flow[:-1]):
            with self.assertRaises(ValueError):
                audit_case_flow('partial-header', group('partial-header'), changed, 0)

    def test_stalled_reader_needs_actual_zero_window(self):
        flow = [tcp(10, flags=2), tcp(10.01, True, flags=18), tcp(11.5, window=0), tcp(25.02, True, flags=4)]
        g = group('stalled-http-reader') + [dict(kind='case_finish', monotonic_ns=28000000000)]
        audit_case_flow('stalled-http-reader', g, flow, 0)
        flow[2]['window'] = 1024
        with self.assertRaisesRegex(ValueError, 'backpressure'):
            audit_case_flow('stalled-http-reader', g, flow, 0)

    def test_alert_acknowledgement_and_retransmission_are_not_interchangeable(self):
        label = 'failed-alert-ack'
        g = group(label) + [dict(kind='ciphertext_tx', monotonic_ns=10100000000, value=dict(hex='00' * 3)),
                           dict(kind='ciphertext_rx', monotonic_ns=11000000000, value=dict(hex='00' * 30)),
                           dict(kind='fatal_alert', value=dict(label=label, alert=116,
                              reason='TLSV13_ALERT_CERTIFICATE_REQUIRED'))]
        flow = [tcp(10, flags=2), tcp(10.01, True, flags=18, seq=0xfffffff0),
                tcp(10.1, seq=2, size=3),
                tcp(11, True, seq=0xfffffff1, size=30), tcp(11.01, ack=15), tcp(11.02, True, flags=4)]
        audit_case_flow(label, g, flow, 0)
        with self.assertRaisesRegex(ValueError, 'Acknowledged-alert'):
            audit_case_flow(label, g, flow[:4] + flow[5:], 0)
        label = 'failed-alert-wait'
        g[-1]['value']['label'] = label
        table = 'r3b1_1234'
        g += [dict(kind='ack_filter_installed', monotonic_ns=10050000000,
                   value=dict(table=table, rules=ack_rules(table, 45000))),
              dict(kind='ack_filter_counters', value=dict(table=table, raw_json=json.dumps(
                   {'nftables': [{'rule': {'expr': [{'counter': {'packets': 2}}]}}]}))),
              dict(kind='ack_filter_removed', monotonic_ns=12010000000, value=dict(table=table))]
        retransmitted = flow[:4] + [tcp(11.5, True, seq=0xfffffff1, size=30), tcp(12, True, flags=4)]
        audit_case_flow(label, g, retransmitted, 0)
        with self.assertRaisesRegex(ValueError, 'Unacknowledged-alert'):
            audit_case_flow(label, g, retransmitted[:-1] + [tcp(11.9, ack=15), retransmitted[-1]], 0)

    def test_tcp_decoder_preserves_flags_window_and_rejects_fragment_truncation(self):
        ip = bytearray(40)
        ip[0], ip[9] = 0x45, 6
        struct.pack_into('!H', ip, 2, 40)
        ip[12:20] = bytes([10, 77, 15, 2, 10, 77, 15, 10])
        struct.pack_into('!HHII', ip, 20, 45000, 18443, 1, 2)
        ip[32], ip[33] = 0x50, 0x10
        wire = bytes(12) + b'\x08\x00' + ip
        header = struct.pack('<IHHIIII', 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)
        raw = header + struct.pack('<IIII', 10, 123, len(wire), len(wire)) + wire
        value, = tcp_packets(raw)
        self.assertEqual((value['realtime_ns'], value['window'], value['size'], value['flags']),
                         (10000123000, 0, 0, 16))
        for malformed in (raw[:-1], raw + b'x', raw[:60] + b'\x20' + raw[61:]):
            with self.assertRaises(ValueError):
                tcp_packets(malformed)


if __name__ == '__main__':
    unittest.main()
