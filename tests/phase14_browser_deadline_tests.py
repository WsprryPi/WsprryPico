"""Realistic network delays and bounded asynchronous harness reads; no hardware."""
import hashlib
from pathlib import Path
import sys
from threading import Event
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from phase14.browser import Browser,BrowserDeadline,BrowserWorkload

class Clock:
    now=0.
    def monotonic(self):return self.now

class Socket:
    def __init__(self,clock,blocks):self.clock=clock;self.blocks=list(blocks);self.timeout=None;self.certificate=b'bound certificate'
    def __enter__(self):return self
    def __exit__(self,*_):pass
    def settimeout(self,value):self.timeout=value
    def do_handshake(self):
        if self.timeout<6:raise TimeoutError('TLS delayed packet')
        self.clock.now+=6
    def selected_alpn_protocol(self):return 'http/1.1'
    def getpeercert(self,**_):return self.certificate
    def sendall(self,data):self.request=data
    def recv(self,_):
        seconds,block=self.blocks.pop(0)
        if seconds>self.timeout:raise TimeoutError('response delay')
        self.clock.now+=seconds;return block

class Context:
    def __init__(self,connection):self.connection=connection
    def wrap_socket(self,raw,**kwargs):
        assert kwargs==dict(server_hostname='named-device.local',do_handshake_on_connect=False)
        return self.connection

class BrowserDeadlineTests(unittest.TestCase):
    def browser(self,clock,blocks):
        connection=Socket(clock,blocks);browser=object.__new__(Browser)
        browser.request_budget_seconds=30;browser.address='192.168.1.53';browser.hostname='named-device.local'
        browser.fingerprint=hashlib.sha256(connection.certificate).hexdigest();browser.context=Context(connection)
        return browser,connection
    def connect(self,clock,connection):
        def create(address,timeout):
            self.assertEqual(address,('192.168.1.53',443))
            if timeout<6:raise TimeoutError('TCP delayed packet')
            clock.now+=6;return connection
        return create
    def test_delayed_connect_handshake_and_body_share_one_budget(self):
        clock=Clock();body=b'{"ok":true}'
        browser,connection=self.browser(clock,[(2,b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body),(0,b'')])
        with patch('phase14.browser.time.monotonic',clock.monotonic),patch('phase14.browser.socket.create_connection',self.connect(clock,connection)):
            response=browser.get('/api/v1/status')
        self.assertEqual(response['value'],{'ok':True});self.assertEqual(response['transport']['elapsed_seconds'],14)
        self.assertEqual([x['stage'] for x in response['transport']['stages']],['TCP connect','TLS handshake','HTTP request','HTTP response'])
        self.assertEqual(connection.timeout,16)
        self.assertNotIn(b'POST ',connection.request)
    def test_old_four_second_budget_reproduces_connect_timeout(self):
        clock=Clock();browser,connection=self.browser(clock,[]);browser.request_budget_seconds=4
        with patch('phase14.browser.time.monotonic',clock.monotonic),patch('phase14.browser.socket.create_connection',self.connect(clock,connection)):
            with self.assertRaises(BrowserDeadline) as caught:browser.get('/')
        self.assertEqual(caught.exception.stage,'TCP connect')
    def test_stream_progress_does_not_restart_absolute_deadline(self):
        clock=Clock();browser,connection=self.browser(clock,[(9,b'HTTP/1.1 200 OK\r\nContent-Length: 30\r\n\r\nx'),(9,b'x'),(9,b'x')])
        with patch('phase14.browser.time.monotonic',clock.monotonic),patch('phase14.browser.socket.create_connection',self.connect(clock,connection)):
            with self.assertRaises(BrowserDeadline) as caught:browser.get('/')
        self.assertEqual(caught.exception.stage,'HTTP response');self.assertEqual(connection.timeout,9)
        self.assertEqual(clock.now,30)
    def test_security_failure_is_not_retried_or_promoted(self):
        clock=Clock();browser,connection=self.browser(clock,[]);browser.fingerprint='0'*64
        with patch('phase14.browser.time.monotonic',clock.monotonic),patch('phase14.browser.socket.create_connection',self.connect(clock,connection)) as create:
            with self.assertRaisesRegex(ValueError,'fingerprint/ALPN'):browser.get('/')
        self.assertEqual(clock.now,12);self.assertEqual(connection.blocks,[])
    def test_invalid_path_never_opens_socket(self):
        browser,_=self.browser(Clock(),[])
        with patch('phase14.browser.socket.create_connection') as create:
            with self.assertRaises(ValueError):browser.get('/api/v1/config')
            create.assert_not_called()
    def test_blocked_browser_does_not_block_control_polling_or_duplicate(self):
        entered=Event();release=Event()
        class Delayed:
            request_budget_seconds=30
            calls=0
            def get(self,path):
                self.calls+=1;entered.set()
                if not release.wait(1):raise AssertionError('test did not release worker')
                return {'path':path,'status':200}
        browser=Delayed();work=BrowserWorkload(browser)
        try:
            work.start('/');self.assertTrue(entered.wait(1))
            controls=[]
            for index in range(20):
                self.assertIsNone(work.poll());controls.append(index)
            self.assertEqual(len(controls),20);self.assertTrue(work.pending)
            with self.assertRaisesRegex(RuntimeError,'already in flight'):work.start('/')
            release.set();sample=work.close()
            self.assertEqual(sample['response']['status'],200);self.assertFalse(work.pending);self.assertEqual(browser.calls,1)
            self.assertIsNone(work.poll())
        finally:release.set();work.close()
    def test_worker_failure_is_published_and_worker_closes(self):
        class Failed:
            request_budget_seconds=30
            def get(self,path):raise BrowserDeadline('TLS handshake',30,30)
        work=BrowserWorkload(Failed());work.start('/')
        with self.assertRaises(BrowserDeadline) as caught:work.close()
        self.assertFalse(work.pending);self.assertEqual(caught.exception.stage,'TLS handshake')
        self.assertIsNone(work.close())

if __name__=='__main__':unittest.main()
