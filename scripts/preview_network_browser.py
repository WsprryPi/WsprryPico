#!/usr/bin/env python3
"""Local visual-test proxy to the hardware-free TLS driver. Never connects to a Pico."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import http.client
from pathlib import Path
import ssl
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build', type=Path, required=True)
args = parser.parse_args()
build = args.build.resolve()
credentials = build / 'network-test-credentials-v3'
context = ssl.create_default_context(cafile=str(credentials / 'client-ca.crt'))
context.load_cert_chain(str(credentials / 'client.crt'), str(credentials / 'client.key'))
context.minimum_version = ssl.TLSVersion.TLSv1_3
context.set_alpn_protocols(['http/1.1'])

class Handler(BaseHTTPRequestHandler):
    def forward(self):
        body = self.rfile.read(int(self.headers.get('Content-Length','0')))
        headers = {k:v for k,v in self.headers.items() if k.lower() not in ('host','origin','connection')}
        headers['Host'] = '127.0.0.1:18443'
        if 'Origin' in self.headers:
            headers['Origin'] = 'https://127.0.0.1:18443'
        connection = http.client.HTTPSConnection('127.0.0.1',18443,context=context,timeout=5)
        try:
            connection.request(self.command,self.path,body=body or None,headers=headers)
            response = connection.getresponse()
            payload = response.read()
            self.send_response(response.status)
            for key,value in response.getheaders(): self.send_header(key,value)
            self.end_headers()
            self.wfile.write(payload)
        finally:
            connection.close()
    do_GET = do_POST = do_PUT = forward

process = subprocess.Popen([str(build/'network_tls_driver')],stdout=subprocess.PIPE,text=True)
try:
    if not process.stdout.readline().startswith('READY'): raise RuntimeError('TLS driver failed')
    print('Host simulation preview: http://127.0.0.1:18300 (no hardware)',flush=True)
    HTTPServer(('127.0.0.1',18300),Handler).serve_forever()
finally:
    process.terminate()
    process.wait(timeout=5)
