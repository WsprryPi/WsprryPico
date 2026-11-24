"""Test Tone through the production TLS server, RF worker, and native coordinator."""
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
from fixture_process import FixtureProcess, process_scope
from network_control import NetworkControl
from network_socket import connect_socket

with process_scope(timeout=45):
    executable, credentials = sys.argv[1:]
    credentials = Path(credentials)
    process = FixtureProcess([executable], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, env={**os.environ,
        'WSPRRY_NETWORK_TEST_MANUAL_CLOCK': '1', 'WSPRRY_NETWORK_TEST_TONE': '1'})
    control = NetworkControl(process)
    assert control.line().strip() == 'READY 18443 PSA 1 PEAK 2'
    context = ssl.create_default_context(cafile=str(credentials / 'client-ca.crt'))
    context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.load_cert_chain(str(credentials / 'client.crt'), str(credentials / 'client.key'))
    context.set_alpn_protocols(['http/1.1'])
    def http(path, body=None, revision=None):
        method = 'POST' if body is not None else 'GET'
        text = '' if body is None else json.dumps({'contract': 'Wsprry-Control/1', **body}, separators=(',', ':'))
        headers = {'Host': '127.0.0.1:18443'}
        if body is not None:
            headers.update({'Origin': 'https://127.0.0.1:18443', 'Content-Type': 'application/json',
                'X-WsprryPico-Request': '1', 'Content-Length': str(len(text))})
        if revision is not None: headers['If-Match'] = revision
        with connect_socket(('127.0.0.1', 18443), deadline=process.deadline,
                tls_context=context, server_hostname='127.0.0.1') as stream:
            stream.settimeout(5)
            stream.sendall((f'{method} {path} HTTP/1.1\r\n' + ''.join(f'{k}: {v}\r\n' for k,v in headers.items()) + '\r\n' + text).encode())
            data = b''
            while True:
                part = stream.recv(4096)
                if not part: break
                data += part
                assert len(data) < 32768
        head, raw = data.split(b'\r\n\r\n', 1)
        fields = dict(line.decode().split(': ', 1) for line in head.split(b'\r\n')[1:])
        assert int(fields['Content-Length']) == len(raw)
        return int(head.split()[1]), fields, json.loads(raw)
    prefix = '/api/control/v1/test-tone/'
    _, _, caps = http('/api/control/v1/capabilities')
    assert caps['test_tone']['available'] and caps['test_tone']['maximum_duration_ms'] == 120000
    _, _, observations = http('/api/control/v1/ntp-observations')
    target = observations['target']
    status, headers, review = http(prefix+'review', {'schema':'test-tone-review', 'target':target,
        'tone':{'carrier_hz':5366200, 'duration_ms':120000, 'proposed_drive_ma':12}})
    assert status == 200 and review['admission'] == 'ready'
    assert review['realization']['requested_nhz'] == '5366200000000000'
    request = {'schema':'test-tone-start', 'target':target, 'request_id':'1'*32,
        'tone':{'carrier_hz':5366200, 'duration_ms':120000, 'expected_drive_ma':12}}
    original_revision = review['assessment_revision']
    status, _, accepted = http(prefix+'start', request, original_revision)
    assert status == 202 and accepted['job']['phase'] == 'accepted'
    job = accepted['job']
    assert job['pad_readback']['drive_ma'] == 12 and job['pad_readback']['stage'] == 'verified'
    selector = prefix+'status?device_id='+target['device_id']+'&boot_id='+target['boot_id']+'&request_id='+'1'*32
    # Every HTTP call is a fresh real mTLS connection: no session owns the tone.
    status, _, reconciled = http(selector)
    assert status == 200 and reconciled['job']['job_id'] == job['job_id']
    status, _, replay = http(prefix+'start', request, original_revision)
    assert status == 202 and replay['job']['job_id'] == job['job_id']
    control.send('STATE')
    current_us = int(control.line().strip().split()[9])
    launch_us = int(job['scheduled_monotonic_ns']) // 1000
    control.send('TIME ADVANCE ' + str(max(0, launch_us - current_us) + 1))
    assert control.line().startswith('TIME ')
    control.send('TIME ADVANCE 90000000')
    assert control.line().startswith('TIME ')
    status, _, running = http(selector)
    assert status == 200 and running['job']['phase'] == 'running'
    control.send('TIME ADVANCE 35000000')
    assert control.line().startswith('TIME ')
    status, _, completed = http(selector)
    assert status == 200 and completed['job']['outcome'] == 'completed'
    assert completed['job']['output_inactive_confirmed']
    status, _, stopped = http(prefix+'stop', {'schema':'test-tone-stop', 'target':target,
        'job_id':job['job_id']}, job['control_revision'])
    assert status == 200 and stopped['job']['outcome'] == 'completed'
    process.finish()
print('PASS Test Tone production TLS/worker: review, finite expiry, reconnect, replay, exact Stop')
