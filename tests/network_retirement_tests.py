"""Actual TLS admission and absent former plaintext listener; no RF hardware."""
import json
import pathlib
import socket
import ssl
import subprocess
import sys
from fixture_process import FixtureProcess, process_scope
from network_control import NetworkControl
from network_socket import connect_socket

exe, directory=sys.argv[1:]
credentials=pathlib.Path(directory)
for flag in ('--plain-wtp','--plain-with-tls','--local-wtp'):
    rejected=subprocess.run([exe,'0','a',flag],capture_output=True,text=True,timeout=5)
    assert rejected.returncode==2 and rejected.stdout=='' and 'Retired WTP carrier' in rejected.stderr

with process_scope(timeout=20):
    process=FixtureProcess([exe],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    controls=NetworkControl(process)
    try:
        assert controls.line().strip()=='READY 18443 PSA 1 PEAK 2'
        # The native server owns no former plaintext execution socket.
        try:
            with socket.create_connection(('127.0.0.1',18444),timeout=1):
                raise AssertionError('Former plaintext listener exists')
        except ConnectionRefusedError:
            pass
        def context(protocol,certificate=True):
            value=ssl.create_default_context(cafile=str(credentials/'client-ca.crt'))
            value.minimum_version=value.maximum_version=ssl.TLSVersion.TLSv1_3
            value.set_alpn_protocols([protocol])
            if certificate:value.load_cert_chain(credentials/'client.crt',credentials/'client.key')
            return value
        for certificate in (False,True):
            try:
                with connect_socket(('127.0.0.1',18443),deadline=process.deadline,timeout=3,tls_context=context('wtp/1',certificate),server_hostname='127.0.0.1'):
                    raise AssertionError('Retired WTP ALPN admitted')
            except ssl.SSLError:
                pass
        with connect_socket(('127.0.0.1',18443),deadline=process.deadline,timeout=3,tls_context=context('http/1.1'),server_hostname='127.0.0.1') as stream:
            stream.sendall(b'GET /api/control/v1/status HTTP/1.1\r\nHost: 127.0.0.1:18443\r\n\r\n')
            response=bytearray()
            while data:=stream.recv(4096):response.extend(data)
            header,body=bytes(response).split(b'\r\n\r\n',1)
            assert header.startswith(b'HTTP/1.1 200')
            status=json.loads(body)['job']
            assert status['state']=='empty' and status['owner_id'] is None and status['output_active'] is False
        print('PASS retired profile flags before allocation, absent plaintext listener, WTP ALPN refusal with/without certificate, and retained actual HTTPS status')
    finally:
        process.finish()
        assert process.returncode==0,process.stderr_text()
