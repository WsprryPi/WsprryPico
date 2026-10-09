"""Finite authenticated HTTPS activity against the existing engineering browser API."""
import hashlib
import json
from pathlib import Path
import socket
import ssl
import time


def activity(browser,path):
    """Retain request-start cadence independently of HTTPS completion latency."""
    started=time.monotonic_ns()
    response=browser.get(path)
    return dict(utc_ns=time.time_ns(),started_monotonic_ns=started,
                completed_monotonic_ns=time.monotonic_ns(),response=response)


class Browser:
    def __init__(self,credentials,info):
        root=Path(credentials);manifest=json.loads((root/'server/deployment.json').read_text())
        if manifest['device_id']!=info['device_id']:
            raise ValueError('browser certificate device binding')
        self.hostname=manifest['hostname'];self.address=info['network']['ipv4']
        self.fingerprint=manifest['certificate_sha256']
        self.context=ssl.create_default_context(cafile=str(root/'server/client-ca.crt'))
        self.context.minimum_version=self.context.maximum_version=ssl.TLSVersion.TLSv1_3
        self.context.set_alpn_protocols(['http/1.1'])
        self.context.load_cert_chain(root/'client/client.crt',root/'client/client.key')

    def get(self,path):
        if path not in ('/','/api/v1/status','/api/v1/capabilities','/api/v1/jobs'):
            raise ValueError('read-only browser workload path')
        with socket.create_connection((self.address,443),timeout=4) as raw:
            with self.context.wrap_socket(raw,server_hostname=self.hostname) as connection:
                if (connection.selected_alpn_protocol()!='http/1.1' or
                    hashlib.sha256(connection.getpeercert(binary_form=True)).hexdigest()!=self.fingerprint):
                    raise ValueError('selected HTTPS server fingerprint/ALPN')
                connection.sendall(('GET '+path+' HTTP/1.1\r\nHost: '+self.hostname+'\r\nConnection: close\r\n\r\n').encode())
                response=bytearray()
                while True:
                    block=connection.recv(8192)
                    if not block:break
                    response.extend(block)
                    if len(response)>131072:raise ValueError('bounded browser response exceeded')
        header,body=bytes(response).split(b'\r\n\r\n',1)
        lines=header.decode().split('\r\n');status=int(lines[0].split()[1])
        headers={k.lower():v.strip() for k,v in (line.split(':',1) for line in lines[1:])}
        if status!=200 or int(headers['content-length'])!=len(body):
            raise ValueError('complete successful browser response required')
        value=None if path=='/' else json.loads(body)
        return dict(path=path,status=status,bytes=len(body),body_sha256=hashlib.sha256(body).hexdigest(),
                    server_sha256=self.fingerprint,value=value)
