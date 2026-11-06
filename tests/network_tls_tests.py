#!/usr/bin/env python3
"""Actual pinned TLS server on loopback; TCP/clock/RNG boundaries are host adapters."""
import json
import os
import concurrent.futures
import base64
import hashlib
import re
import pathlib
import socket
import ssl
import struct
import subprocess
from fixture_process import FixtureProcess, process_scope
from network_control import NetworkControl
from network_socket import connect_socket
from network_replies import ReplyCollector, StrictFrameDecoder
import sys
import time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from validate_wtp_contract import frame


# CTest has 90 seconds; reserve six-second teardown and four-second harness margin.
with process_scope(timeout=80):
    exe, credentials = sys.argv[1:]
    credentials = pathlib.Path(credentials)
    process = FixtureProcess([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={**os.environ,"WSPRRY_NETWORK_TEST_MANUAL_CLOCK":"1"})

    controls = NetworkControl(process)
    control = controls.send

    def state(deadline=None):
        control('STATE',deadline=deadline)
        parts = controls.line().strip().split()
        assert len(parts) == 11 and parts[0] == 'STATE', parts
        values = dict(zip(('active', 'pending', 'rx', 'tcp_pending', 'timeouts',
                           'admitted', 'closed', 'steps', 'now_us'), map(int, parts[1:10])))
        assert all(value >= 0 for value in values.values()) and values['steps'] in (0, 1), parts
        values['job'] = parts[10]
        return values

    def await_state(predicate, label):
        deadline = min(process.deadline, time.monotonic() + 3)
        last = None
        try:
            while time.monotonic() < deadline:
                last = state(deadline)
                if predicate(last):
                    assert time.monotonic() < deadline, ('late observed state', label, last)
                    return last
        except TimeoutError as error:
            raise TimeoutError(('state not observed', label, last)) from error
        raise AssertionError(('state not observed', label, last))

    def released(active=0):
        return await_state(lambda value: value['active'] == active and value['pending'] == 0,
                        'closed connections released')

    def advance(microseconds):
        before = state()['now_us']
        control('TIME ADVANCE ' + str(microseconds))
        assert controls.line().strip() == 'TIME ' + str(before + microseconds)
        assert state()['now_us'] == before + microseconds

    def context(identity='client', protocols=('http/1.1',), tls12=False):
        ctx = ssl.create_default_context(cafile=str(credentials / 'client-ca.crt'))
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2 if tls12 else ssl.TLSVersion.TLSv1_3
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2 if tls12 else ssl.TLSVersion.TLSv1_3
        if identity:
            ctx.load_cert_chain(str(credentials / (identity + '.crt')), str(credentials / (identity + '.key')))
        if protocols:
            ctx.set_alpn_protocols(list(protocols))
        return ctx

    HOSTNAME = "wsprrypico-" + "a" * 32 + ".local"

    def io_end():
        return min(process.deadline, time.monotonic() + 5)

    def io_budget(stream, end):
        remaining = end - time.monotonic()
        if remaining <= 0:raise TimeoutError('real socket operation watchdog expired')
        stream.settimeout(remaining)

    def receive_all(stream, end=None):
        end = io_end() if end is None else end
        response = bytearray()
        while True:
            io_budget(stream, end)
            chunk = stream.recv(4096)
            if time.monotonic() >= end:raise TimeoutError('late socket response cannot qualify')
            if not chunk:return bytes(response)
            response.extend(chunk)
            # Existing fixture safety bound, not an advertised product limit.
            # The current largest served document is below 500 KiB.
            assert len(response) <= FixtureProcess.limit, 'fixture response accumulation exceeded byte bound'

    def connect(ctx=None, hostname="127.0.0.1"):
        return connect_socket(('127.0.0.1',18443),deadline=process.deadline,
                              tls_context=ctx or context(),server_hostname=hostname)

    def control_document(body):
        return {'contract':'Wsprry-Control/1', **body}

    def config_update(config):
        return control_document({'schema':'config-update','target':target,'mode':'merge',
                                 'config':config})

    def http_on(stream, path='/api/control/v1/status', method='GET', body=None, headers=None, fragment=False, padding=0):
        text = '' if body is None else json.dumps(control_document(body), separators=(',', ':'))
        text += ' ' * max(0, padding - len(text))
        fields = {'Host':'127.0.0.1:18443'}
        if body is not None:
            fields.update({'Content-Type':'application/json','Origin':'https://127.0.0.1:18443',
                           'X-WsprryPico-Request':'1','Content-Length':str(len(text))})
        fields.update(headers or {})
        wire = (f'{method} {path} HTTP/1.1\r\n' + ''.join(f'{k}: {v}\r\n' for k,v in fields.items()) + '\r\n' + text).encode()
        assert stream.version() == 'TLSv1.3' and stream.selected_alpn_protocol() == 'http/1.1'
        end = io_end()
        if fragment:
            # Exercise the parser with the same seven-byte TLS writes, without
            # coupling the controlled absolute request deadline to the host's
            # sender-side TCP buffering. Production server deadlines are unchanged.
            stream.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            upload_started = time.monotonic()
            for i in range(0, len(wire), 7):
                io_budget(stream,end)
                stream.sendall(wire[i:i+7])
            if padding:
                print(f'Fragmented HTTP upload: {len(wire)} bytes, '
                      f'{time.monotonic() - upload_started:.3f}s, client TCP_NODELAY', flush=True)
        else:
            io_budget(stream,end)
            stream.sendall(wire)
        response = receive_all(stream,end)
        head, payload = response.split(b'\r\n\r\n', 1)
        status = int(head.split()[1])
        response_headers = dict(line.decode().split(': ',1) for line in head.split(b'\r\n')[1:])
        assert int(response_headers['Content-Length']) == len(payload)
        assert time.monotonic() < end, 'late parsed HTTP response cannot qualify'
        return status, response_headers, payload

    def http(path='/api/control/v1/status', method='GET', body=None, headers=None, fragment=False, identity="client", padding=0):
        with connect(context(identity)) as stream:
            return http_on(stream, path, method, body, headers, fragment, padding)

    try:
        ready = controls.line().strip()
        assert ready == 'READY 18443 PSA 1 PEAK 2', (ready, process.poll())
        # A multi-segment ClientHello must fit an already available receive slot
        # before the foreground poll; neither FIN nor reset may retain its bytes.
        # No TLS work/allocation is permitted from the raw TCP callback.
        for outcome in ('FIN', 'RESET'):
            control('PENDING BURST ' + outcome)
            assert controls.line().strip() == 'PENDING 1507 1 0 0 0 1'
            assert http()[0] == 200
        assert http()[0] == 200
        assert http('/api/v1/status')[0] == 404
        # A transient validator nests one PSA owner under the live server without
        # freeing global crypto state or disrupting the established TLS connection.
        for command, expected in [('VALIDATE GOOD', 1), ('VALIDATE BAD', 0)] * 3:
            with connect() as live:
                control(command)
                result = controls.line().strip().split()
                assert result[0] == 'VALIDATE' and int(result[1]) == expected, result
                assert (int(result[2]) == 0) == bool(expected), result
                assert result[3:] == ['1', '2'], result
                assert http_on(live)[0] == 200
            assert http()[0] == 200
        # Repeated last-owner release and first-owner reacquisition leave neither
        # PSA ownership nor TLS allocations retained between cycles.
        for _ in range(3):
            control('SERVER CYCLE')
            cycle = controls.line().strip().split()
            assert cycle[0:3] == ['CYCLE', '1', '1'], cycle
            assert int(cycle[3]) > 0, cycle
            assert http()[0] == 200
        control('PSA STATUS')
        assert controls.line().strip() == 'PSA 1 2'
        # Real DNS SAN verification over an explicit loopback destination; no NSS/mDNS claim.
        with connect(hostname=HOSTNAME) as named:
            named.sendall(f'GET /api/control/v1/status HTTP/1.1\r\nHost: {HOSTNAME}:18443\r\n\r\n'.encode())
            assert b' 200 ' in named.recv(4096)
        for mismatch in ('wrong.local', '127.0.0.2'):
            try:
                with connect(hostname=mismatch):
                    raise AssertionError('Mismatched TLS identity accepted')
            except ssl.SSLCertVerificationError:
                pass
            released()
        authority = HOSTNAME + ':18443'
        assert http(headers={'Host': authority, 'Origin': 'https://' + authority})[0] == 200
        assert http(headers={'Host': authority.upper(), 'Origin': 'https://' + authority})[0] == 200
        assert http(headers={'Host': authority, 'Origin': 'https://127.0.0.1:18443'})[0] == 403
        assert http(headers={'Host': '127.0.0.1:18443', 'Origin': 'https://' + authority})[0] == 403
        assert http(headers={'Origin': 'https://evil.local:18443'})[0] == 403
        caps = json.loads(http('/api/control/v1/capabilities')[2])
        assert caps['active_job_connections'] and caps['max_network_connections'] == 2
        assert caps['max_wtp_connections'] == 1
        for fragmented in (False, True):
            control('WRITE FRAGMENT' if fragmented else 'WRITE NORMAL')
            # Reach device-side certificate verification, not merely any TLS/TCP failure.
            for identity, reason in [(None, 'TLSV13_ALERT_CERTIFICATE_REQUIRED'),
                                     ('rogue', 'TLSV1_ALERT_UNKNOWN_CA'),
                                     ('expired', 'SSLV3_ALERT_CERTIFICATE_EXPIRED')]:
                try:
                    with connect(context(identity)) as stream:
                        stream.sendall(b'GET /api/control/v1/status HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n\r\n')
                        stream.recv(1024)
                    raise AssertionError(f'{identity}: expected a certificate alert')
                except ssl.SSLError as error:
                    # OpenSSL/Python versions use two names for the same expired-
                    # certificate alert. Preserve exact certificate-alert checking.
                    accepted = {reason}
                    if reason == 'SSLV3_ALERT_CERTIFICATE_EXPIRED':
                        accepted.add('TLS_ALERT_CERTIFICATE_EXPIRED')
                    assert error.reason in accepted, (identity, error.reason, reason)
                assert http()[0] == 200
        control('WRITE NORMAL')
        # An unacknowledged fatal alert cannot retain a rejected slot indefinitely.
        # The host adapter holds ACK callbacks, not TLS bytes delivered to OpenSSL.
        control('ACK HOLD NEXT')
        with connect(context(None)) as stream:
            try:
                stream.recv(1024)
                raise AssertionError('Expected missing-client fatal alert')
            except ssl.SSLError as error:
                assert error.reason == 'TLSV13_ALERT_CERTIFICATE_REQUIRED', error
            # Keep the rejected peer open; EOF cleanup must not fake the deadline.
            held = await_state(lambda value: value['active'] == 1 and value['tcp_pending'] > 0,
                            'rejected fatal alert retained pending ACK')
            advance(999000)
            assert state()['active'] == 1, 'fatal alert closed before its one-second deadline'
            advance(1000)
            released()
            assert http()[0] == 200, 'Rejected connection did not release its bounded slot'
        control('ACK RELEASE')
        for identity, protocols, tls12 in [(None, ('http/1.1',), False), ('server', ('http/1.1',), False),
                                          ('rogue', ('http/1.1',), False), ('expired', ('http/1.1',), False),
                                          ('client', (), False), ('client', ('bogus',), False),
                                          ('client', ('http/1.1',), True)]:
            try:
                with connect(context(identity, protocols, tls12)) as stream:
                    stream.sendall(b'GET /api/control/v1/status HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n\r\n')
                    assert not stream.recv(1024), 'Untrusted TLS client received application data'
            except (ssl.SSLError, ConnectionError):
                pass
            released()
            assert http()[0] == 200, 'Server failed to recover after rejected TLS connection'
        assert http(headers={'Host':'evil.test'})[0] == 403
        status, headers, body = http('/api/control/v1/config')
        assert status == 200 and json.loads(body)['config'] is None
        target = json.loads(http('/api/control/v1/management')[2])['target']
        config = {'enabled':False,'station':{'callsign':'AA0NT','locator':'EM18','power_dbm':37},
                  'wifi':{'ssid':'test','password':'never-echo-me','ntp_ipv4':'192.0.2.1'},'schedules':[{'period_s':120,'phase_s':0}]}
        assert http('/api/control/v1/config/update','POST',config_update(config),{'If-Match':headers['ETag'],'Origin':'https://evil.test'})[0] == 403
        status, saved, body = http('/api/control/v1/config/update','POST',config_update(config),{'If-Match':headers['ETag']},fragment=True)
        assert status == 200, body
        assert b'never-echo-me' not in body and json.loads(body)['config']['wifi']['password'] is None
        assert http('/api/control/v1/config/update','POST',config_update(config),{'If-Match':headers['ETag']})[0] == 412
        # A restart is dispatched only after its own complete response is acknowledged.
        assert caps['features']['restart']
        for expected, outcome in enumerate(('disconnect', 'apply', 'fin', 'reset')):
            revision = http('/api/control/v1/config')[1]['ETag']
            with connect() as management:
                control('ACK HOLD')
                payload = json.dumps(control_document({})).encode()
                management.sendall((f'POST /api/control/v1/restart HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n'
                    f'Origin: https://127.0.0.1:18443\r\nContent-Type: application/json\r\n'
                    f'X-WsprryPico-Request: 1\r\nIf-Match: {revision}\r\nContent-Length: {len(payload)}\r\n\r\n').encode() + payload)
                response = receive_all(management)
                assert response.startswith(b'HTTP/1.1 202'), response
                control('RESTART COUNT')
                assert controls.line().strip() == f'RESTARTS {max(0, expected - 1)}'
                if outcome == 'apply': control('ACK RELEASE')
                elif outcome == 'fin': control('ACK FIN')
                elif outcome == 'reset': control('ACK RESET')
            released()
            control('RESTART COUNT')
            assert controls.line().strip() == f'RESTARTS {expected}'
            assert http('/api/control/v1/restart', 'POST', {}, {'If-Match':revision})[0] == 412
        # The generated inline assets must match the browser-enforced CSP hashes.
        status, root_headers, document = http('/')
        for tag in ('style', 'script'):
            text = re.search(rb'<' + tag.encode() + rb'>(.*?)</' + tag.encode() + rb'>', document, re.S).group(1)
            digest = base64.b64encode(hashlib.sha256(text).digest()).decode()
            assert "'sha256-" + digest + "'" in root_headers['Content-Security-Policy']
        # A browser may start its next TLS connection before the previous response closes.
        with connect() as first:
            first.sendall(b'GET /api/control/v1/status HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n')
            with concurrent.futures.ThreadPoolExecutor() as pool:
                control('HTTP PAUSE')
                waiting = pool.submit(http)
                await_state(lambda value: value['active'] + value['pending'] == 2 and value['rx'] > 0 and value['steps'] == 0, 'second connection entered paused gate')
                first.sendall(b'\r\n')
                control('HTTP RESUME')
                receive_all(first)
                assert waiting.result(timeout=5)[0] == 200
        # A receiver which does not drain a large response cannot prevent another
        # authenticated status read. Closure is bounded by the total HTTP deadline.
        with connect() as no_reader:
            no_reader.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024)
            no_reader.sendall(b'GET / HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n\r\n')
            assert http(identity='other')[0] == 200
        # Absolute HTTP deadline also closes a slow, authenticated client.
        with connect() as stalled:
            stalled.sendall(b'GET /')
            assert http(identity='other')[0] == 200, 'independent authenticated progress while partial HTTP remains open'
            released(active=1)
            advance(14999000)
            assert state()['active'] == 1, 'HTTP closed before its fifteen-second deadline'
            advance(1000)
            released()
            try: assert not stalled.recv(4096)
            except ConnectionError: pass
        assert http()[0] == 200
        for path in ['/', '/app.js', '/style.css']:
            status, _, body = http(path)
            assert status == 200 and len(body) > 100
        # Unusable UTC cancels a pending handshake; coherent restoration admits TLS.
        with connect_socket(('127.0.0.1',18443),deadline=process.deadline,timeout=3):
            control('CLOCK OFF')
            control('VALIDATE GOOD')
            result = controls.line().strip().split()
            assert result[0] == 'VALIDATE' and result[1] == '0' and result[2] != '0', result
            assert result[3:] == ['1', '2'], result
            try:
                with connect() as stream:
                    assert not stream.recv(1024)
            except (ssl.SSLError, ConnectionError): pass
        control('CLOCK ON')
        assert http()[0] == 200
        # A plaintext client never reaches HTTP or WTP dispatch.
        admitted_before_plaintext = state()['admitted']
        with connect_socket(('127.0.0.1',18443),deadline=process.deadline,timeout=3) as raw:
            raw.sendall(b'GET / HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n\r\n')
            plaintext = await_state(lambda value: value['admitted'] > admitted_before_plaintext, 'plaintext peer reached actual TLS admission')
            if plaintext['active']:advance(10000000)
            try: assert b'HTTP/1.1' not in raw.recv(2048)
            except ConnectionError: pass
        released()
        assert http()[0] == 200
        # Bad HTTP is rejected after authenticated transport, then the next connection works.
        with connect() as stream:
            stream.sendall(b'GET / HTTP/1.1\r\nHost: 127.0.0.1:18443\r\nHost: evil\r\n\r\n')
            assert b'400' in stream.recv(4096)
        released()
        assert http()[0] == 200
        with connect(context(protocols=('wtp/1',))) as stream:
            assert stream.selected_alpn_protocol() == 'wtp/1'
            decoder = StrictFrameDecoder()
            def ask(operation, body=None, padded=False, deadline=None):
                # Unique IDs are supplied from the test's deterministic counter.
                ask.sequence += 1
                request_id = f'{ask.sequence:032x}'
                request = json.dumps({'type':'request','protocol':'WTP/1','session_id':'1'*32,
                    'request_id':request_id,'op':operation,'body':body or {}},separators=(',',':')).encode()
                if padded: request += b' ' * (65536 - len(request))
                if operation == 'HELLO':ask.collector=ReplyCollector('1'*32)
                end = min(io_end(), deadline if deadline is not None else float('inf'))
                io_budget(stream,end)
                stream.sendall(frame(request))
                while True:
                    io_budget(stream,end)
                    chunk = stream.recv(4096)
                    assert time.monotonic() < end, 'late WTP response cannot qualify'
                    assert chunk, 'WTP connection closed before its response'
                    response=ask.collector.accept(decoder.feed(chunk),request_id,operation)
                    if response is not None:
                        assert time.monotonic() < end, 'late parsed WTP response cannot qualify'
                        gap=ask.collector.gap;ask.collector.gap=False
                        if gap and operation!='STATUS':
                            assert ask('STATUS',deadline=end)['ok'], 'advisory gap requires authoritative STATUS'
                            print('Advisory gap observed: authoritative STATUS refreshed')
                        return response
            ask.sequence = 0
            assert ask('HELLO',{'versions':['WTP/1'],'client_name':'TLS test','client_version':'1'})['ok']
            # Deferring expensive handshake steps leaves the established WTP owner
            # responsive, and the paused handshake resumes without a reconnect.
            control('HANDSHAKE PAUSE')
            with concurrent.futures.ThreadPoolExecutor() as pool:
                waiting = pool.submit(http)
                await_state(lambda value: value['active'] == 2 and value['rx'] > 0 and value['steps'] == 0, 'paused handshake has actual queued TLS bytes')
                assert not waiting.done(), 'Handshake progressed while paused'
                assert ask('STATUS')['ok']
                control('HANDSHAKE RESUME')
                assert waiting.result(timeout=5)[0] == 200
            # The same bounded USB-reply grace also pauses an established HTTP
            # request/response, while the established WTP owner remains responsive.
            with connect(context('other')) as paused_http:
                paused_http.sendall(b'GET /api/control/v1/status HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n')
                control('HTTP PAUSE')
                paused_http.sendall(b'\r\n')
                await_state(lambda value: value['active'] == 2 and value['rx'] > 0 and value['steps'] == 0, 'HTTP request retained behind observed pause')
                assert ask('STATUS')['ok']
                assert state()['rx'] > 0, 'HTTP bytes consumed while paused and WTP made foreground progress'
                control('HTTP RESUME')
                paused_http.settimeout(5)
                response = receive_all(paused_http)
                assert response.startswith(b'HTTP/1.1 200'), response
            # Persistent WTP remains negotiated while independent certificates read HTTP.
            for _ in range(8):
                assert http(identity='other')[0] == 200
                assert ask('PING',{'token':'owner-retained'})['ok']
            with concurrent.futures.ThreadPoolExecutor() as pool:
                maximum = pool.submit(http, '/api/control/v1/jobs', 'POST', {}, None, True, 'other', 32768)
                assert ask('PING',{'token':'maximum-size-frame'},padded=True)['ok']
                assert maximum.result()[0] == 400
            # Independent stalled HTTP must not prevent the established owner from progressing.
            with connect(context('other')) as slow:
                slow.sendall(b'GET /api/control/v1/status HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n')
                with connect_socket(('127.0.0.1',18443),deadline=process.deadline,timeout=3) as pending:
                    await_state(lambda value: value['active'] == 2 and value['pending'] == 1, 'capacity pending slot entered')
                    with connect_socket(('127.0.0.1',18443),deadline=process.deadline,timeout=3) as extra:
                        try: assert not extra.recv(1), 'Capacity overflow was not rejected'
                        except ConnectionError: pass
                    assert ask('PING')['ok']
            released(active=1)
            # Idle admission does not authorize a config change completed after CLAIM.
            before_claim = http('/api/control/v1/config')
            revision = before_claim[1]['ETag']
            with connect(context('other')) as management:
                payload = json.dumps(config_update(config)).encode()
                header = (f'POST /api/control/v1/config/update HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n'
                          f'Origin: https://127.0.0.1:18443\r\nContent-Type: application/json\r\n'
                          f'X-WsprryPico-Request: 1\r\nIf-Match: {revision}\r\nContent-Length: {len(payload)}\r\n\r\n').encode()
                management.sendall(header + payload[:1])
                assert ask('CLAIM',{'owner_id':'1'*32,'lease_ms':60000})['ok']
                management.sendall(payload[1:])
                response = receive_all(management)
                assert response.startswith(b'HTTP/1.1 409'), response
            after_claim = http('/api/control/v1/config')
            assert after_claim[1]['ETag'] == revision, 'busy refusal must not append the persisted configuration journal'
            assert json.loads(after_claim[2])['config'] == json.loads(before_claim[2])['config'], 'busy refusal must preserve saved configuration'
            plan = {'job_id':'3'*32,'profile':'rf-events/1','mode':'tone','total_duration_ns':'10240000000',
                    'events':[{'offset_ns':str(i*20000000),'duration_ns':'20000000','rf_on':True,
                               'frequency_nhz':'1000000'} for i in range(512)]}
            assert ask('LOAD',plan)['ok']
            clock = ask('GET_CLOCK')['body']
            assert ask('ARM',{'job_id':'3'*32,'start_utc_ns':str(int(clock['utc_now_ns'])+2000000000),
                              'max_start_uncertainty_ns':'1000000'})['ok']
            assert json.loads(http(identity='other')[2])['job']['state'] == 'armed'
            # Same certificate/different session and foreign certificate cannot adopt ownership.
            sequence = 1000
            def browser(op, body, identity='other', session=None):
                global sequence
                sequence += 1
                session = session or ('4' if identity == 'client' else '6')*32
                return http('/api/control/v1/jobs','POST',{'session_id':session,'request_id':f'{sequence:032x}',
                            'operation':op,'body':body},identity=identity)
            for identity in ('client','other'):
                assert browser('HELLO',{'versions':['WTP/1'],'client_name':'observer','client_version':'1'},identity)[0] == 200
                assert browser('CLAIM',{'owner_id':'4'*32,'lease_ms':60000},identity)[0] == 409
                assert browser('ABORT',{'job_id':'3'*32},identity)[0] == 409
                assert browser('RELEASE',{},identity)[0] == 409
            advance(1999999)
            assert json.loads(http(identity='other')[2])['job']['state'] == 'armed'
            advance(1)
            running = json.loads(http(identity='other')[2])
            assert running['job']['state'] == 'running', running
            assert ask('PING')['ok']
        # No network input drives the job after ARM; query retained completion later.
        control('LINK OFF')
        advance(10239999)
        assert state()['job'] == 'running'
        advance(1)
        assert state()['job'] == 'complete'
        control('LINK ON')
        status, _, body = http()
        assert status == 200 and json.loads(body)['job']['state'] == 'complete', body
        # Owner lease survives controller disconnect. Use the original authenticated
        # session explicitly to release; no foreign browser recovery shortcut.
        assert browser('RELEASE',{},'client','1'*32)[0] == 200
        assert browser('CLAIM',{'owner_id':'4'*32,'lease_ms':60000})[0] == 200
        plan['job_id'] = '5'*32
        small = {'job_id':'5'*32,'profile':'rf-events/1','mode':'tone','total_duration_ns':'2000000000',
                 'events':[{'offset_ns':'0','duration_ns':'2000000000','rf_on':True,'frequency_nhz':'1000000'}]}
        assert browser('LOAD',small)[0] == 200
        # Obtain UTC through a temporary WTP observer, then close it before browser ARM.
        # The status includes the standalone clock's current UTC observation.
        observed = json.loads(http()[2])['standalone']
        start_utc = int(observed['utc_now_ns']) + 2000000000
        assert browser('ARM',{'job_id':'5'*32,'start_utc_ns':str(start_utc),'max_start_uncertainty_ns':'1000000'})[0] == 200
        assert json.loads(http()[2])['job']['state'] == 'armed'
        with connect() as slow:
            slow.sendall(b'GET /')
            assert browser('ABORT',{'job_id':'5'*32})[0] == 200
        assert browser('RELEASE',{})[0] == 200
        # Concurrent revisions admit exactly one distinct update.
        revision = http('/api/control/v1/config')[1]['ETag']
        # Establish both admitted TLS sessions before releasing concurrent requests.
        # This tests the config revision race itself without racing the deliberately
        # single pending-handshake slot in the host socket adapter.
        with connect(context()) as first, connect(context()) as second, concurrent.futures.ThreadPoolExecutor() as pool:
            configs = [{**config,'station':{**config['station'],'power_dbm':p}} for p in (20,30)]
            replies = list(pool.map(lambda pair:http_on(pair[0],'/api/control/v1/config/update','POST',config_update(pair[1]),{'If-Match':revision}),
                                    zip((first,second),configs)))
        assert sorted(r[0] for r in replies) == [200,412]
        # Delay the initiating PCB's ACK callback after its complete TLS response.
        # Unrelated closes cannot apply it; failure cancels; completion rechecks idle.
        for outcome in ('disconnect', 'claim', 'apply'):
            revision = http('/api/control/v1/network')[1]['ETag']
            with connect() as management:
                control('ACK HOLD')
                payload = json.dumps(control_document({'enabled':outcome == 'apply'})).encode()
                header = (f'PUT /api/control/v1/network HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n'
                          f'Origin: https://127.0.0.1:18443\r\nContent-Type: application/json\r\n'
                          f'X-WsprryPico-Request: 1\r\nIf-Match: {revision}\r\nContent-Length: {len(payload)}\r\n\r\n').encode()
                management.sendall(header + payload)
                response = receive_all(management)
                assert response.startswith(b'HTTP/1.1 200'), response
                pending = json.loads(http('/api/control/v1/network')[2])
                assert pending['enabled'] and pending['test_pending'] and pending['test_applied'] == 0
                if outcome == 'claim':
                    assert browser('CLAIM',{'owner_id':'6'*32,'lease_ms':60000})[0] == 200
                if outcome != 'disconnect':
                    control('ACK RELEASE')
            released()
            network_state = json.loads(http('/api/control/v1/network')[2])
            assert network_state['enabled'] and not network_state['test_pending'], network_state
            assert network_state['test_applied'] == (1 if outcome == 'apply' else 0), network_state
            if outcome == 'claim':
                assert browser('RELEASE',{})[0] == 200
        baseline = json.loads(http()[2])["transport"]["tls_allocated_bytes"]
        # Servicing each real reset must release its slot before one fresh request.
        # Synchronize the adapter boundary instead of racing its single pending
        # handshake slot with a new connect before it has observed the RST.
        for _ in range(20):
            raw = connect_socket(('127.0.0.1',18443),deadline=process.deadline,timeout=3)
            raw.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('ii',1,0)); raw.close()
            control('NETWORK DRAIN')
            assert controls.line().strip() == 'NETWORK 0 0 0'
            assert http()[0] == 200
        stats = json.loads(http()[2])['transport']
        assert stats['tls_allocated_bytes'] <= baseline + 1024, (baseline, stats)
        with connect(context(protocols=('wtp/1',))) as stream:
            decoder = StrictFrameDecoder()
            assert ask('HELLO',{'versions':['WTP/1'],'client_name':'close-metric','client_version':'1'})['ok']
            control('LINK OFF')
            control('CLOSE METRICS')
            assert controls.line().strip() == 'CLOSE 1 0'
        control('LINK ON')
        assert http()[0] == 200
        control('CLOSE METRICS')
        assert controls.line().strip() == 'CLOSE 1 0'  # HTTP cannot overwrite the WTP cause.
        print('Transport metrics:', stats)
        print('Actual TLS 1.3 mTLS/ALPN, HTTP framing, origin, revisions, assets and WTP tests passed')
    finally:
        process.finish()
        stderr = process.stderr_text()
        if stderr: print(stderr, file=sys.stderr)
