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
import sys
import time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from validate_wtp_contract import frame
from wtp_monitor import FrameDecoder

exe, credentials = sys.argv[1:]
credentials = pathlib.Path(credentials)
process = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    env={**os.environ,"WSPRRY_NETWORK_TEST_TIME_SCALE":"5"})

def control(command):
    process.stdin.write(command + '\n'); process.stdin.flush(); time.sleep(.02)

def context(identity='client', protocols=('http/1.1',), tls12=False):
    ctx = ssl.create_default_context(cafile=str(credentials / 'client-ca.crt'))
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2 if tls12 else ssl.TLSVersion.TLSv1_3
    ctx.maximum_version = ssl.TLSVersion.TLSv1_2 if tls12 else ssl.TLSVersion.TLSv1_3
    if identity:
        ctx.load_cert_chain(str(credentials / (identity + '.crt')), str(credentials / (identity + '.key')))
    if protocols:
        ctx.set_alpn_protocols(list(protocols))
    return ctx

def connect(ctx=None):
    return (ctx or context()).wrap_socket(socket.create_connection(('127.0.0.1', 18443), timeout=5), server_hostname='127.0.0.1')

def http(path='/api/v1/status', method='GET', body=None, headers=None, fragment=False, identity="client", padding=0):
    text = '' if body is None else json.dumps(body, separators=(',', ':'))
    text += ' ' * max(0, padding - len(text))
    fields = {'Host':'127.0.0.1:18443'}
    if body is not None:
        fields.update({'Content-Type':'application/json','Origin':'https://127.0.0.1:18443',
                       'X-WsprryPico-Request':'1','Content-Length':str(len(text))})
    fields.update(headers or {})
    wire = (f'{method} {path} HTTP/1.1\r\n' + ''.join(f'{k}: {v}\r\n' for k,v in fields.items()) + '\r\n' + text).encode()
    with connect(context(identity)) as stream:
        assert stream.version() == 'TLSv1.3' and stream.selected_alpn_protocol() == 'http/1.1'
        if fragment:
            for i in range(0, len(wire), 7): stream.sendall(wire[i:i+7])
        else: stream.sendall(wire)
        response = b''
        while chunk := stream.recv(4096): response += chunk
    head, payload = response.split(b'\r\n\r\n', 1)
    status = int(head.split()[1])
    response_headers = dict(line.decode().split(': ',1) for line in head.split(b'\r\n')[1:])
    assert int(response_headers['Content-Length']) == len(payload)
    return status, response_headers, payload

try:
    assert process.stdout.readline().startswith('READY'), process.stderr.read()
    assert http()[0] == 200
    caps = json.loads(http('/api/v1/capabilities')[2])
    assert caps['active_job_connections'] and caps['max_network_connections'] == 2
    assert caps['max_wtp_connections'] == 1
    for identity, protocols, tls12 in [(None, ('http/1.1',), False), ('server', ('http/1.1',), False),
                                      ('rogue', ('http/1.1',), False), ('expired', ('http/1.1',), False),
                                      ('client', (), False), ('client', ('bogus',), False),
                                      ('client', ('http/1.1',), True)]:
        try:
            with connect(context(identity, protocols, tls12)) as stream:
                stream.sendall(b'GET /api/v1/status HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n\r\n')
                assert not stream.recv(1024), 'Untrusted TLS client received application data'
        except (ssl.SSLError, ConnectionError):
            pass
        time.sleep(.03)
        assert http()[0] == 200, 'Server failed to recover after rejected TLS connection'
    assert http(headers={'Host':'evil.test'})[0] == 403
    status, headers, body = http('/api/v1/config')
    assert status == 200 and json.loads(body)['config'] is None
    config = {'version':1,'enabled':False,'station':{'callsign':'AA0NT','locator':'EM18','power_dbm':37},
              'wifi':{'ssid':'test','password':'never-echo-me','ntp_ipv4':'192.0.2.1'},'schedules':[{'period_s':120,'phase_s':0}]}
    assert http('/api/v1/config','PUT',config,{'If-Match':headers['ETag'],'Origin':'https://evil.test'})[0] == 403
    status, saved, body = http('/api/v1/config','PUT',config,{'If-Match':headers['ETag']},fragment=True)
    assert status == 200, body
    assert b'never-echo-me' not in body and json.loads(body)['config']['wifi']['password'] is None
    assert http('/api/v1/config','PUT',config,{'If-Match':headers['ETag']})[0] == 412
    # The generated inline assets must match the browser-enforced CSP hashes.
    status, root_headers, document = http('/')
    for tag in ('style', 'script'):
        text = re.search(rb'<' + tag.encode() + rb'>(.*?)</' + tag.encode() + rb'>', document, re.S).group(1)
        digest = base64.b64encode(hashlib.sha256(text).digest()).decode()
        assert "'sha256-" + digest + "'" in root_headers['Content-Security-Policy']
    # A browser may start its next TLS connection before the previous response closes.
    with connect() as first:
        first.sendall(b'GET /api/v1/status HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n')
        with concurrent.futures.ThreadPoolExecutor() as pool:
            waiting = pool.submit(http)
            time.sleep(.05)
            first.sendall(b'\r\n')
            while first.recv(4096): pass
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
        try: assert not stalled.recv(4096)
        except ConnectionError: pass
    assert http()[0] == 200
    for path in ['/', '/app.js', '/style.css']:
        status, _, body = http(path)
        assert status == 200 and len(body) > 100
    # Unusable UTC cancels a pending handshake; coherent restoration admits TLS.
    with socket.create_connection(('127.0.0.1',18443),timeout=3):
        control('CLOCK OFF')
        try:
            with connect() as stream:
                assert not stream.recv(1024)
        except (ssl.SSLError, ConnectionError): pass
    control('CLOCK ON')
    assert http()[0] == 200
    # A plaintext client never reaches HTTP or WTP dispatch.
    with socket.create_connection(('127.0.0.1',18443), timeout=3) as raw:
        raw.sendall(b'GET / HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n\r\n')
        try: assert b'HTTP/1.1' not in raw.recv(2048)
        except ConnectionError: pass
    time.sleep(.05)
    assert http()[0] == 200
    # Bad HTTP is rejected after authenticated transport, then the next connection works.
    with connect() as stream:
        stream.sendall(b'GET / HTTP/1.1\r\nHost: 127.0.0.1:18443\r\nHost: evil\r\n\r\n')
        assert b'400' in stream.recv(4096)
    time.sleep(.03)
    assert http()[0] == 200
    with connect(context(protocols=('wtp/1',))) as stream:
        assert stream.selected_alpn_protocol() == 'wtp/1'
        decoder = FrameDecoder()
        def ask(operation, body=None, padded=False):
            # Unique IDs are supplied from the test's deterministic counter.
            ask.sequence += 1
            request_id = f'{ask.sequence:032x}'
            request = json.dumps({'type':'request','protocol':'WTP/1','session_id':'1'*32,
                'request_id':request_id,'op':operation,'body':body or {}},separators=(',',':')).encode()
            if padded: request += b' ' * (65536 - len(request))
            stream.sendall(frame(request))
            while True:
                chunk = stream.recv(4096)
                assert chunk, 'WTP connection closed before its response'
                for payload in decoder.feed(chunk):
                    response = json.loads(payload)
                    if response.get('request_id') == request_id: return response
        ask.sequence = 0
        assert ask('HELLO',{'versions':['WTP/1'],'client_name':'TLS test','client_version':'1'})['ok']
        # Persistent WTP remains negotiated while independent certificates read HTTP.
        for _ in range(8):
            assert http(identity='other')[0] == 200
            assert ask('PING',{'token':'owner-retained'})['ok']
        with concurrent.futures.ThreadPoolExecutor() as pool:
            maximum = pool.submit(http, '/api/v1/jobs', 'POST', {}, None, True, 'other', 32768)
            assert ask('PING',{'token':'maximum-size-frame'},padded=True)['ok']
            assert maximum.result()[0] == 400
        # Independent stalled HTTP must not prevent the established owner from progressing.
        with connect(context('other')) as slow:
            slow.sendall(b'GET /api/v1/status HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n')
            with socket.create_connection(('127.0.0.1',18443),timeout=3) as pending:
                time.sleep(.03)
                with socket.create_connection(('127.0.0.1',18443),timeout=3) as extra:
                    try: assert not extra.recv(1), 'Capacity overflow was not rejected'
                    except ConnectionError: pass
                assert ask('PING')['ok']
        time.sleep(.03)
        # Idle admission does not authorize a config change completed after CLAIM.
        revision = http('/api/v1/config')[1]['ETag']
        with connect(context('other')) as management:
            payload = json.dumps(config).encode()
            header = (f'PUT /api/v1/config HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n'
                      f'Origin: https://127.0.0.1:18443\r\nContent-Type: application/json\r\n'
                      f'X-WsprryPico-Request: 1\r\nIf-Match: {revision}\r\nContent-Length: {len(payload)}\r\n\r\n').encode()
            management.sendall(header + payload[:1])
            assert ask('CLAIM',{'owner_id':'1'*32,'lease_ms':60000})['ok']
            management.sendall(payload[1:])
            response = b''
            while chunk := management.recv(4096): response += chunk
            assert response.startswith(b'HTTP/1.1 409'), response
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
            return http('/api/v1/jobs','POST',{'session_id':session,'request_id':f'{sequence:032x}',
                        'operation':op,'body':body},identity=identity)
        for identity in ('client','other'):
            assert browser('HELLO',{'versions':['WTP/1'],'client_name':'observer','client_version':'1'},identity)[0] == 200
            assert browser('CLAIM',{'owner_id':'4'*32,'lease_ms':60000},identity)[0] == 409
            assert browser('ABORT',{'job_id':'3'*32},identity)[0] == 409
            assert browser('RELEASE',{},identity)[0] == 409
        time.sleep(.40)
        running = json.loads(http(identity='other')[2])
        assert running['job']['state'] == 'running', running
        assert ask('PING')['ok']
    # No network input drives the job after ARM; query retained completion later.
    control('LINK OFF')
    time.sleep(2.2)
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
    start_utc = int(time.time()*1e9) + 3000000000  # host clock differs under accelerated fixture
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
    revision = http('/api/v1/config')[1]['ETag']
    with concurrent.futures.ThreadPoolExecutor() as pool:
        configs = [{**config,'station':{**config['station'],'power_dbm':p}} for p in (20,30)]
        replies = list(pool.map(lambda c:http('/api/v1/config','PUT',c,{'If-Match':revision}),configs))
    assert sorted(r[0] for r in replies) == [200,412]
    # Delay the initiating PCB's ACK callback after its complete TLS response.
    # Unrelated closes cannot apply it; failure cancels; completion rechecks idle.
    for outcome in ('disconnect', 'claim', 'apply'):
        revision = http('/api/v1/network')[1]['ETag']
        with connect() as management:
            control('ACK HOLD')
            payload = json.dumps({'enabled':outcome == 'apply'}).encode()
            header = (f'PUT /api/v1/network HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n'
                      f'Origin: https://127.0.0.1:18443\r\nContent-Type: application/json\r\n'
                      f'X-WsprryPico-Request: 1\r\nIf-Match: {revision}\r\nContent-Length: {len(payload)}\r\n\r\n').encode()
            management.sendall(header + payload)
            response = b''
            while chunk := management.recv(4096): response += chunk
            assert response.startswith(b'HTTP/1.1 200'), response
            pending = json.loads(http('/api/v1/network')[2])
            assert pending['enabled'] and pending['test_pending'] and pending['test_applied'] == 0
            if outcome == 'claim':
                assert browser('CLAIM',{'owner_id':'6'*32,'lease_ms':60000})[0] == 200
            if outcome != 'disconnect':
                control('ACK RELEASE')
        time.sleep(.03)
        state = json.loads(http('/api/v1/network')[2])
        assert state['enabled'] and not state['test_pending'], state
        assert state['test_applied'] == (1 if outcome == 'apply' else 0), state
        if outcome == 'claim':
            assert browser('RELEASE',{})[0] == 200
    baseline = json.loads(http()[2])["transport"]["tls_allocated_bytes"]
    # Repeated reset/reconnect cycles must leave the remaining slot usable.
    for _ in range(20):
        raw = socket.create_connection(('127.0.0.1',18443),timeout=3)
        raw.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('ii',1,0)); raw.close()
        assert http()[0] == 200
    stats = json.loads(http()[2])['transport']
    assert stats['tls_allocated_bytes'] <= baseline + 1024, (baseline, stats)
    print('Transport metrics:', stats)
    print('Actual TLS 1.3 mTLS/ALPN, HTTP framing, origin, revisions, assets and WTP tests passed')
finally:
    process.terminate()
    try: process.wait(timeout=3)
    except subprocess.TimeoutExpired: process.kill(); process.wait()
    stderr = process.stderr.read()
    if stderr: print(stderr, file=sys.stderr)
