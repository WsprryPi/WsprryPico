#!/usr/bin/env python3
"""One bounded native Mac DNS + authenticated HTTPS observation; no mutations."""
import argparse
import hashlib
import http.client
import io
import json
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import time

from phase11_4_loop_common import NAME, ADDRESS, SERVER_SHA, validate_https


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--credentials', type=Path, required=True)
    p.add_argument('--boot', required=True)
    p.add_argument('--run', action='store_true')
    a = p.parse_args()
    if not a.run:
        p.error('--run requires authorization for network reads')
    started = time.time_ns()
    result = {'started_ns': started}
    try:
        code = 'import json,socket;print(json.dumps(socket.getaddrinfo(sys.argv[1],18443,socket.AF_INET,socket.SOCK_STREAM)))'
        r = subprocess.run([sys.executable, '-c', 'import sys;' + code, NAME],
                           capture_output=True, text=True, timeout=6)
        result['dns'] = {'exit': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}
        result['dns_ok'] = r.returncode == 0 and {v[4][0] for v in json.loads(r.stdout)} == {ADDRESS}
    except Exception as e:
        result['dns_ok'] = False
        result['dns_error'] = str(e)
    # Explicit address preserves DNS-vs-TCP isolation; certified hostname is mandatory.
    try:
        cx = ssl.create_default_context(cafile=str(a.credentials / 'client-ca.crt'))
        cx.minimum_version = cx.maximum_version = ssl.TLSVersion.TLSv1_3
        cx.load_cert_chain(str(a.credentials / 'operator-browser/client.crt'),
                           str(a.credentials / 'operator-browser/client.key'))
        cx.set_alpn_protocols(['http/1.1'])
        result['https_started_ns'] = time.time_ns()
        with socket.create_connection((ADDRESS, 18443), timeout=3) as raw:
            with cx.wrap_socket(raw, server_hostname=NAME) as stream:
                fingerprint = hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest()
                if fingerprint != SERVER_SHA or stream.selected_alpn_protocol() != 'http/1.1':
                    raise ValueError('wrong certificate or ALPN')
                stream.sendall(f'GET /api/v1/status HTTP/1.1\r\nHost: {NAME}:18443\r\nConnection: close\r\n\r\n'.encode())
                data = b''
                deadline = time.monotonic() + 5
                while True:
                    stream.settimeout(max(.001, deadline - time.monotonic()))
                    part = stream.recv(4096)
                    if not part:
                        break
                    data += part
                    if len(data) > 65536 or time.monotonic() >= deadline:
                        raise TimeoutError('bounded HTTPS response')
        class Buffered:
            def makefile(self, mode):
                return io.BytesIO(data)
        response = http.client.HTTPResponse(Buffered())
        response.begin()
        value = {'http': response.status, 'server_sha256': fingerprint,
                 'body': json.loads(response.read())}
        validate_https(value, a.boot)
        result.update(https_ok=True, https=value)
    except Exception as e:
        result.update(https_ok=False, https_error=type(e).__name__ + ': ' + str(e))
    result['ended_ns'] = time.time_ns()
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
