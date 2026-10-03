#!/usr/bin/env python3
import tempfile
import errno
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_engineering_network_dispatch as run
class Socket:
    def __init__(self,body=None,error=None):
        value=json.dumps(body or dict(device_id=run.DEVICE,boot_id='2'*32,pending=False)).encode()
        self.raw=b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(value)).encode()+b'\r\nConnection: close\r\n\r\n'+value
        self.error=error;self.options=[];self.bound=None;self.closed=False;self.sent=None
    def settimeout(self,*a):pass
    def setsockopt(self,*a):self.options.append(a)
    def bind(self,address):self.bound=address
    def connect(self,address):
        if self.error:raise self.error
    def sendall(self,value):self.sent=value
    def recv(self,size):value=self.raw[:size];self.raw=self.raw[size:];return value
    def close(self):self.closed=True
class Tests(unittest.TestCase):
    def test_interface_bound_readonly_full_identity(self):
        stream=Socket()
        with patch.object(run.socket,'socket',return_value=stream):
            raw,device,outcome=run.http_identity('2'*32)
        self.assertEqual(outcome,'reply');self.assertEqual(device,run.DEVICE)
        self.assertEqual(stream.bound,('192.168.4.3',0));self.assertIn((socket.SOL_SOCKET,socket.SO_BINDTODEVICE,b'wlan0\0'),stream.options)
        self.assertIn(b'GET /api/recovery/v1/status ',stream.sent);self.assertNotIn(b'Cookie',stream.sent)
        self.assertTrue(stream.closed);self.assertTrue(raw.startswith(b'HTTP/1.1'))
    def test_wrong_boot_pending_and_timeout_not_pass(self):
        for body in (dict(device_id=run.DEVICE,boot_id='3'*32,pending=False),dict(device_id=run.DEVICE,boot_id='2'*32,pending=True)):
            stream=Socket(body)
            with patch.object(run.socket,'socket',return_value=stream):
                with self.assertRaises(ValueError):run.http_identity('2'*32)
            self.assertTrue(stream.closed)
        stream=Socket(error=socket.timeout())
        with patch.object(run.socket,'socket',return_value=stream):self.assertEqual(run.http_identity('2'*32)[2],'timeout')
    def test_observed_socket_failure_classification(self):
        for code,outcome in ((errno.ECONNREFUSED,'refused'),(errno.EHOSTUNREACH,'network_unreachable'),(errno.EADDRNOTAVAIL,'association_lost')):
            with patch.object(run.socket,'socket',return_value=Socket(error=OSError(code,'fixture'))):self.assertEqual(run.http_identity('2'*32)[2],outcome)
    def test_fresh_iw_bssid_and_association_parse(self):
        scan=b'BSS aa:bb:cc:dd:ee:ff(on wlan0)\n\tSSID: WsprryPico-0a9d89\n'
        link=b'Connected to aa:bb:cc:dd:ee:ff (on wlan0)\n\tSSID: WsprryPico-0a9d89\n'
        with patch.object(run,'command',side_effect=[scan,link]) as command:
            value=run.scan_link()
        self.assertEqual(value[3],['aa:bb:cc:dd:ee:ff']);self.assertEqual(value[4],'aa:bb:cc:dd:ee:ff')
        self.assertIn('scan',command.call_args_list[0].args[0])
    def test_cleanup_deletes_only_exact_owned_name(self):
        root='/home/pi/phase12-recovery-'+'a'*32;name='p12-observer-'+'a'*32
        with patch.object(run,'command',side_effect=[(name+'\nmanagement\n').encode(),b'']) as command:run.cleanup_action(root)
        self.assertEqual(command.call_args_list[-1].args[0],['sudo','-n','nmcli','connection','delete',name])
class RadioComparisonTests(unittest.TestCase):
 def setUp(self):run.HOST_AP='wlan2';run.OBSERVER_INTERFACE='wlan0'
 def tearDown(self):run.HOST_AP='wlan2';run.OBSERVER_INTERFACE='wlan0'
 def test_swapped_mapping_hash_required_before_actions(self):
   with tempfile.TemporaryDirectory() as d:
    from phase12_fixture_roles import role_map
    roles=role_map('swapped');Path(d,'fixture-roles.json').write_text(json.dumps(roles))
    for request in ({},{'roles_sha256':'wrong'}):
     with self.assertRaises(ValueError):run.bind_radio_roles(d,request)
    self.assertEqual(run.bind_radio_roles(d,{'roles_sha256':roles['sha256']}),roles)
    self.assertEqual((run.HOST_AP,run.OBSERVER_INTERFACE),('wlan0','wlan2'))
 def test_swapped_original_socket_binding_and_one_readonly_request(self):
   import socket

   stream=Socket();run.OBSERVER_INTERFACE='wlan2'
   with patch.object(run.socket,'socket',return_value=stream):
    _,device,outcome=run.http_identity('2'*32)
   self.assertEqual(outcome,'reply');self.assertEqual(device,run.DEVICE)
   self.assertIn((socket.SOL_SOCKET,socket.SO_BINDTODEVICE,b'wlan2\0'),stream.options)
   self.assertEqual(stream.bound,('192.168.4.3',0));self.assertIn(b'GET /api/recovery/v1/status ',stream.sent)
 def test_actual_profile_security_and_one_activation(self):
   import time
   from types import SimpleNamespace
   class Evidence:
    def record(self,*args,**kwargs):pass
   adds=[];ups=[];original=run.observe_then_activate
   def observed(name,evidence,end):
    return original(name,evidence,end,beacon=lambda *a:None)
   def activate(argv,**kwargs):ups.append((argv,kwargs));return SimpleNamespace(returncode=0,stdout=b'',stderr=b'')
   with patch.object(run,'command',side_effect=lambda argv:adds.append(argv)),patch.object(run,'observe_then_activate',side_effect=observed),patch.object(run.subprocess,'run',side_effect=activate):
    run.create_owned_observer('p12-observer-'+'a'*32,dict(interface='wlan0',ssid='synthetic',password='synthetic',deadline=time.monotonic()+60),Evidence())
   self.assertEqual(len(adds),1);self.assertEqual(len(ups),1);self.assertEqual(ups[0][1]['timeout'],20)
   for field,value in [('wifi-sec.proto','rsn'),('wifi-sec.pairwise','ccmp'),('wifi-sec.group','ccmp')]:
    self.assertEqual(adds[0][adds[0].index(field)+1],value)
   with patch.object(run,'command',side_effect=AssertionError('host mutation')):
    with self.assertRaises(ValueError):run.create_owned_observer('p12-observer-'+'a'*32,dict(interface='wlan1'),Evidence())

if __name__=='__main__':unittest.main()
