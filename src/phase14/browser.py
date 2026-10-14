"""Finite authenticated HTTPS activity against the existing engineering browser API."""
import hashlib
import json
from pathlib import Path
import socket
import ssl
import time
from threading import Thread


REQUEST_BUDGET_SECONDS = 30


class BrowserDeadline(TimeoutError):
    """A harness network deadline, with the stage preserved for diagnosis."""

    def __init__(self, stage, elapsed, budget):
        self.stage = stage
        self.elapsed_seconds = elapsed
        self.budget_seconds = budget
        super().__init__(f'HTTPS harness deadline at {stage}: {elapsed:.3f}s/{budget}s')


class BrowserWorkload:
    """One in-flight read; network waits never hold up RF/control observations."""

    def __init__(self, browser):
        self.browser = browser
        self.thread = None
        self.sample = self.error = None
        self.started_monotonic_ns = None

    @property
    def pending(self):
        return self.thread is not None

    def start(self, path):
        if self.pending:
            raise RuntimeError('one browser request already in flight')
        self.sample = self.error = None
        self.started_monotonic_ns = time.monotonic_ns()
        def run():
            try:
                self.sample = activity(self.browser, path)
            except BaseException as error:
                self.error = error
        self.thread = Thread(target=run, name='phase14-browser-read')
        self.thread.start()

    def poll(self):
        if self.thread is None or self.thread.is_alive():
            return None
        self.thread.join()
        self.thread = None
        if self.error is not None:
            raise self.error
        return self.sample

    def close(self):
        if self.thread is not None:
            self.thread.join(self.browser.request_budget_seconds + 1)
            if self.thread.is_alive():
                raise RuntimeError('browser worker exceeded its absolute request deadline')
        return self.poll()


def activity(browser,path):
    """Retain request-start cadence independently of HTTPS completion latency."""
    started=time.monotonic_ns()
    response=browser.get(path)
    return dict(utc_ns=time.time_ns(),started_monotonic_ns=started,
                completed_monotonic_ns=time.monotonic_ns(),response=response)


class Browser:
    def __init__(self,credentials,info,*,request_budget_seconds=REQUEST_BUDGET_SECONDS):
        if type(request_budget_seconds) not in (int,float) or not 0<request_budget_seconds<=60:
            raise ValueError('finite HTTPS request budget required')
        self.request_budget_seconds=request_budget_seconds
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
        started=time.monotonic();deadline=started+self.request_budget_seconds
        stage='TCP connect';stages=[]
        def remaining():
            left=deadline-time.monotonic()
            if left<=0:
                raise BrowserDeadline(stage,time.monotonic()-started,self.request_budget_seconds)
            return left
        def completed(name):
            stages.append(dict(stage=name,elapsed_seconds=time.monotonic()-started))
        try:
          with socket.create_connection((self.address,443),timeout=remaining()) as raw:
            completed(stage);stage='TLS handshake';raw.settimeout(remaining())
            with self.context.wrap_socket(raw,server_hostname=self.hostname,do_handshake_on_connect=False) as connection:
                connection.settimeout(remaining());connection.do_handshake();completed(stage)
                if (connection.selected_alpn_protocol()!='http/1.1' or
                    hashlib.sha256(connection.getpeercert(binary_form=True)).hexdigest()!=self.fingerprint):
                    raise ValueError('selected HTTPS server fingerprint/ALPN')
                stage='HTTP request';connection.settimeout(remaining())
                connection.sendall(('GET '+path+' HTTP/1.1\r\nHost: '+self.hostname+'\r\nConnection: close\r\n\r\n').encode())
                completed(stage);stage='HTTP response'
                response=bytearray()
                while True:
                    connection.settimeout(remaining())
                    block=connection.recv(8192)
                    if not block:break
                    response.extend(block)
                    if len(response)>131072:raise ValueError('bounded browser response exceeded')
                completed(stage)
        except TimeoutError as error:
            if isinstance(error,BrowserDeadline):raise
            raise BrowserDeadline(stage,time.monotonic()-started,self.request_budget_seconds) from error
        header,body=bytes(response).split(b'\r\n\r\n',1)
        lines=header.decode().split('\r\n');status=int(lines[0].split()[1])
        headers={k.lower():v.strip() for k,v in (line.split(':',1) for line in lines[1:])}
        if status!=200 or int(headers['content-length'])!=len(body):
            raise ValueError('complete successful browser response required')
        value=None if path=='/' else json.loads(body)
        return dict(path=path,status=status,bytes=len(body),body_sha256=hashlib.sha256(body).hexdigest(),
                    server_sha256=self.fingerprint,value=value,
                    transport=dict(request_budget_seconds=self.request_budget_seconds,
                                   elapsed_seconds=time.monotonic()-started,stages=stages))
