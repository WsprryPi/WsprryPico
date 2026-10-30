#!/usr/bin/env python3
"""TLS flight must reach the client while its first TCP record ACK is withheld."""
import os
import pathlib
import re
import socket
import ssl
import subprocess
import sys

exe, directory = sys.argv[1:]
credentials = pathlib.Path(directory)
process = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, env=os.environ.copy())
try:
    assert process.stdout.readline().strip() == 'READY 18443 PSA 1 PEAK 2'
    process.stdin.write('NAGLE HOLD\n')
    process.stdin.flush()
    assert process.stdout.readline().strip() == 'NAGLE HOLD READY'
    context = ssl.create_default_context(cafile=str(credentials / 'client-ca.crt'))
    context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.set_alpn_protocols(['http/1.1'])
    context.load_cert_chain(credentials / 'client.crt', credentials / 'client.key')
    with socket.create_connection(('127.0.0.1', 18443), timeout=4) as raw:
        with context.wrap_socket(raw, server_hostname='127.0.0.1') as stream:
            assert stream.version() == 'TLSv1.3'
            assert stream.selected_alpn_protocol() == 'http/1.1'
            stream.sendall(b'GET /api/control/v1/status HTTP/1.1\r\nHost: 127.0.0.1:18443\r\nConnection: close\r\n\r\n')
            response = bytearray()
            while block := stream.recv(4096):
                response.extend(block)
    header, body = bytes(response).split(b'\r\n\r\n', 1)
    assert int(header.splitlines()[0].split()[1]) == 200
    fields = dict(line.split(b': ', 1) for line in header.splitlines()[1:])
    assert int(fields[b'Content-Length']) == len(body)
    print('Withheld first-flight ACK: authenticated TLS 1.3 and complete HTTP 200 passed')
finally:
    process.terminate()
    out, err = process.communicate(timeout=5)
    assert process.returncode == 0, (out, err)
    assert re.search(r'TLS peak=\d+ retained=0 allocation_failures=\d+ psa_owners=0', err), (out, err)
