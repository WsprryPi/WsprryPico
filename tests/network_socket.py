"""Real sockets constrained by their enclosing fixture's monotonic watchdog."""
import math
import socket
import time


class BoundedSocket:
    def __init__(self, stream, deadline):
        self.stream=stream
        self.deadline=deadline
        self.timeout=stream.gettimeout()
        if not math.isfinite(deadline) or self.timeout is None or not math.isfinite(self.timeout) or self.timeout<=0:
            raise ValueError('Finite enclosing deadline and socket watchdog required')

    def __getattr__(self,name):return getattr(self.stream,name)
    def settimeout(self,value):
        if value is None or not math.isfinite(value) or value<=0:
            raise ValueError('Finite positive socket watchdog required')
        self.timeout=value
    def _call(self,operation,*args):
        remaining=self.deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('enclosing network fixture deadline expired')
        self.stream.settimeout(min(self.timeout,remaining))
        value=operation(*args)
        if time.monotonic()>=self.deadline:raise TimeoutError('late socket result cannot qualify')
        return value
    def sendall(self,value):return self._call(self.stream.sendall,value)
    def recv(self,count):return self._call(self.stream.recv,count)
    def close(self):return self.stream.close()
    def __enter__(self):return self
    def __exit__(self,kind,primary,trace):
        try:self.close()
        except BaseException as cleanup:
            if primary is not None:raise BaseExceptionGroup('socket operation and cleanup failed',[primary,cleanup])
            raise
        return False


def connect_socket(address,*,deadline,timeout=5,tls_context=None,server_hostname=None):
    if not math.isfinite(deadline) or not math.isfinite(timeout) or timeout<=0:
        raise ValueError('Finite enclosing deadline and positive socket watchdog required')
    end=min(deadline,time.monotonic()+timeout)
    remaining=end-time.monotonic()
    if remaining<=0:raise TimeoutError('enclosing network fixture deadline expired before connect')
    raw=socket.create_connection(address,timeout=remaining)
    stream=None
    try:
        remaining=end-time.monotonic()
        if remaining<=0:raise TimeoutError('late TCP connection cannot qualify')
        raw.settimeout(remaining)
        stream=tls_context.wrap_socket(raw,server_hostname=server_hostname) if tls_context else raw
        result=BoundedSocket(stream,deadline)
        if time.monotonic()>=end:raise TimeoutError('late TLS connection cannot qualify')
        return result
    except BaseException as primary:
        failures=[]
        for owned in ([stream,raw] if stream is not raw else [raw]):
            if owned is not None:
                try:owned.close()
                except BaseException as error:failures.append(error)
        if failures:raise BaseExceptionGroup('socket acquisition and cleanup failed',[primary,*failures])
        raise
