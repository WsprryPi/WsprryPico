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
process = subprocess.Popen([exe], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    env={**os.environ,"WSPRRY_NETWORK_TEST_TIME_SCALE":"5"})

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

def http(path='/api/v1/status', method='GET', body=None, headers=None, fragment=False):
    text = '' if body is None else json.dumps(body, separators=(',', ':'))
    fields = {'Host':'127.0.0.1:18443'}
    if body is not None:
        fields.update({'Content-Type':'application/json','Origin':'https://127.0.0.1:18443',
                       'X-WsprryPico-Request':'1','Content-Length':str(len(text))})
    fields.update(headers or {})
    wire = (f'{method} {path} HTTP/1.1\r\n' + ''.join(f'{k}: {v}\r\n' for k,v in fields.items()) + '\r\n' + text).encode()
    with connect() as stream:
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
    assert http('/api/v1/capabilities')[0] == 200
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
    # Absolute HTTP deadline also closes a slow, authenticated client.
    with connect() as stalled:
        stalled.sendall(b'GET /')
        try: assert not stalled.recv(4096)
        except ConnectionError: pass
    assert http()[0] == 200
    for path in ['/', '/app.js', '/style.css']:
        status, _, body = http(path)
        assert status == 200 and len(body) > 100
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
        assert ask('PING',{'token':'maximum-size-frame'},padded=True)['ok']
        assert ask('CLAIM',{'owner_id':'1'*32,'lease_ms':60000})['ok']
        plan = {'job_id':'3'*32,'profile':'rf-events/1','mode':'tone','total_duration_ns':'512000000',
                'events':[{'offset_ns':str(i*1000000),'duration_ns':'1000000','rf_on':True,
                           'frequency_nhz':'1000000'} for i in range(512)]}
        assert ask('LOAD',plan)['ok']
        clock = ask('GET_CLOCK')['body']
        assert ask('ARM',{'job_id':'3'*32,'start_utc_ns':str(int(clock['utc_now_ns'])+2000000000),
                          'max_start_uncertainty_ns':'1000000'})['ok']
    # No network input drives the job after ARM; query retained completion later.
    time.sleep(.65)
    status, _, body = http()
    assert status == 200 and json.loads(body)['job']['state'] == 'complete', body
    print('Actual TLS 1.3 mTLS/ALPN, HTTP framing, origin, revisions, assets and WTP tests passed')
finally:
    process.terminate()
    try: process.wait(timeout=3)
    except subprocess.TimeoutExpired: process.kill(); process.wait()
    stderr = process.stderr.read()
    if stderr: print(stderr, file=sys.stderr)
