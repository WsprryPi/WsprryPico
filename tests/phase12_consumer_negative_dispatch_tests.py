#!/usr/bin/env python3
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_consumer_negative_dispatch as run
class Socket:
    def __init__(self,raw):self.raw=raw;self.sent=None;self.closed=False;self.options=[];self.bound=None
    def __enter__(self):return self
    def __exit__(self,*a):self.close()
    def settimeout(self,*a):pass
    def setsockopt(self,*a):self.options.append(a)
    def bind(self,a):self.bound=a
    def connect(self,a):self.destination=a
    def sendall(self,v):self.sent=v
    def recv(self,n):value=self.raw[:n];self.raw=self.raw[n:];return value
    def close(self):self.closed=True
    def shutdown(self,*a):pass
class Tests(unittest.TestCase):
    def test_owned_disconnect_rescan_single_join_and_private_stderr(self):
        evidence=MagicMock();name='p12-recovery-'+'a'*32
        responses=[run.subprocess.CompletedProcess([],0,(name+'\n').encode(),b'owned'),
                   run.subprocess.CompletedProcess([],0,b'down',b''),
                   run.subprocess.CompletedProcess([],4,b'join stdout',b'private failure')]
        with patch.object(run.subprocess,'run',side_effect=responses) as execute,patch.object(run,'wait_visible_ap',return_value='aa:bb:cc:dd:ee:ff'):
            run.disconnect_owned(evidence,name,run.time.monotonic()+20)
            with self.assertRaisesRegex(ValueError,'owned nmcli operation failed'):
                run.rejoin_owned(evidence,name,'WsprryPico-0a9d89',run.time.monotonic()+20,lambda:None)
        self.assertEqual(execute.call_count,3)
        self.assertEqual(sum('up' in call.args[0] for call in execute.call_args_list),1)
        self.assertTrue(all(call.kwargs['timeout']<=7 for call in execute.call_args_list))
        self.assertEqual(evidence.record.call_args.kwargs['stderr_hex'],b'private failure'.hex())
        with patch.object(run,'private_nmcli',return_value='unrelated') as nmcli:
            with self.assertRaisesRegex(ValueError,'campaign-owned'):
                run.disconnect_owned(evidence,name,run.time.monotonic()+5)
            self.assertEqual(nmcli.call_count,1)

    def test_complete_active_scan_gates_single_join_and_rechecks_current_boot(self):
        evidence=MagicMock();guard=MagicMock();now=[0]
        scans=[run.subprocess.CompletedProcess([],0,b'BSS aa:aa:aa:aa:aa:aa(on wlan2)\n\tSSID: Other\n',b''),
               run.subprocess.CompletedProcess([],0,b'BSS bb:bb:bb:bb:bb:bb(on wlan2)\n\tSSID: WsprryPico-0a9d89\n',b'actual scan')]
        with patch.object(run.subprocess,'run',side_effect=scans) as execute:
            actual=run.wait_visible_ap(evidence,'WsprryPico-0a9d89',60,guard,
                clock=lambda:now[0],sleeper=lambda delay:now.__setitem__(0,now[0]+delay))
        self.assertEqual(actual,'bb:bb:bb:bb:bb:bb');self.assertEqual(execute.call_count,2)
        self.assertEqual(guard.call_count,3)
        self.assertEqual(execute.call_args.args[0],['sudo','-n','/usr/sbin/iw','dev','wlan2','scan'])
        with patch.object(run.subprocess,'run') as execute:
            with self.assertRaisesRegex(ValueError,'wrong fresh boot'):
                run.wait_visible_ap(evidence,'WsprryPico-0a9d89',run.time.monotonic()+60,
                                    MagicMock(side_effect=ValueError('wrong fresh boot')))
            execute.assert_not_called()

    def test_authority_precedes_private_inputs(self):
        with patch.object(run,'private_bytes',side_effect=AssertionError('input accessed')):
            with self.assertRaises(ValueError):run.run(dict(authority='wrong'))
    def test_all_four_actual_routes_and_no_extras(self):
        http=run.HTTP()
        for method,path,body in [('GET','/api/owner/v1/public-status',None),('GET','/api/owner/v1/claim/status',None),('POST','/api/owner/v1/claim/start',{'version':1}),('POST','/api/owner/v1/claim/submit',{'version':1})]:
            self.assertTrue(http.wire(method,path,body).startswith((method+' '+path+' HTTP/1.1\r\n').encode()))
        for method,path,body in [('POST','/api/owner/v1/reset/intent',{}),('GET','/api/owner/v1/claim/start',None),('POST','/api/owner/v1/claim/submit',None),('GET','/api/owner/v1/public-status',{})]:
            with self.assertRaises(ValueError):http.wire(method,path,body)
    def test_actual_http_exchange_interface_bound_length_and_body(self):
        raw=b'HTTP/1.1 409 Conflict\r\nContent-Length: 16\r\n\r\n{"error":"busy"}'
        stream=Socket(raw);http=run.HTTP()
        with patch.object(run.socket,'socket',return_value=stream):
            code,value,wire,response=http('POST','/api/owner/v1/claim/submit',{'version':1},run.time.monotonic()+5)
        self.assertEqual(code,409);self.assertEqual(value,{'error':'busy'});self.assertEqual(response,raw)
        self.assertEqual(stream.bound,('192.168.4.2',0));self.assertIn((socket.SOL_SOCKET,socket.SO_BINDTODEVICE,b'wlan2\0'),stream.options)
        self.assertIn(b'Origin: http://192.168.4.1',wire);self.assertIn(b'Content-Length: 13',wire);self.assertTrue(stream.closed)
    def test_deadline_before_socket_and_header_injection(self):
        http=run.HTTP()
        with patch.object(run.socket,'socket',side_effect=AssertionError('socket opened')):
            with self.assertRaises(ValueError):http('GET','/api/owner/v1/public-status',None,0)
        for method,path in [('GET\r\nInjected','/api/owner/v1/public-status'),('GET','/api/owner/v1/status\r\nInjected')]:
            with self.assertRaises(ValueError):http.wire(method,path,None)
    def test_wrong_length_duplicate_headers_and_oversized_reply_fail(self):
        for raw in (b'HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\n{}',b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nContent-Length: 2\r\n\r\n{}',b'x'*32769):
            stream=Socket(raw)
            with patch.object(run.socket,'socket',return_value=stream):
                with self.assertRaises(ValueError):run.HTTP()('GET','/api/owner/v1/public-status',None,run.time.monotonic()+5)
            self.assertTrue(stream.closed)
    def dispatch(self,wrong=None,wait=False,listener_wait=False):
        manifest=dict(source_commit='1'*40,candidates=[dict(role='fault_8',fault_stage=8,uf2=dict(sha256=run.hashlib.sha256(b'image').hexdigest()))])
        raw=json.dumps(manifest).encode()
        request=dict(authority='USER_AUTHORIZED_UNATTENDED_PHASE12',root='/home/pi/phase12-recovery-'+'a'*32,
                     manifest_sha256=run.hashlib.sha256(raw).hexdigest(),source_commit='1'*40,boot_id='2'*32,profile_generation=7,station={},case='CANCELLED')
        info=dict(device_id=run.DEVICE,revision='1'*12,provisioning_generation='7',provisioning_source='consumer_preclock',
                  phase12_fault_stage='8',phase12_fault_consumed=False,phase12_boot_ap_window_ms=120000,
                  lan_wtp_mode='plain',lan_wtp_port=31417,lan_wtp_ready=True,
                  status=dict(boot_id='2'*32,state='empty',enabled=False,output_active=False,monotonic_now_ns='20000000000'),network=dict(link_status=3,ipv4='192.168.84.2'))
        if wrong=='device':info['device_id']='wrong'
        if wrong=='boot':info['status']['boot_id']='3'*32
        if wrong=='consumed':info['phase12_fault_consumed']=True
        reads=[0]
        def observe():
            reads[0]+=1
            info['lan_wtp_ready']=not listener_wait
            return info,json.dumps(info).encode()
        observer=MagicMock(side_effect=observe);evidence=MagicMock();peer=MagicMock()
        now=[100.]
        def negative(*args,**kwargs):
            self.assertIsNone(args[3], 'Never fabricate WTP authority from INFO')
            if wait:
                kwargs['sleeper'](62);raise TimeoutError('stop after actual expiry wait')
            return kwargs['cancel_boundary']()
        def sleep(seconds):now[0]+=seconds
        with patch.object(Path,'is_dir',return_value=True),patch.object(Path,'is_symlink',return_value=False),patch.object(run,'private_bytes',side_effect=[raw,b'image']),patch.object(run,'validate_uf2'),patch.object(run,'Evidence',return_value=evidence),patch.object(run,'Observer',return_value=observer),patch.object(run,'command') as command,patch.object(run,'management',return_value={'host':'unchanged'}),patch.object(run,'disconnect_owned'),patch.object(run,'negative',side_effect=negative) as cases,patch.object(run,'console',side_effect=TimeoutError('uncertain reboot')) as console,patch.object(run.time,'monotonic',side_effect=lambda:now[0]),patch.object(run.time,'sleep',side_effect=sleep):
            with self.assertRaises((ValueError,TimeoutError)):run.run(request)
        return command,console,evidence,cases,observer
    def test_wrong_device_boot_or_consumed_fixture_prevents_host_change(self):
        for wrong in ('device','boot','consumed'):
            command,console,evidence,cases,observer=self.dispatch(wrong=wrong)
            command.assert_not_called();console.assert_not_called();evidence.close.assert_called_once();cases.assert_not_called()
    def test_uncertain_reboot_is_one_attempt_and_closes_evidence(self):
        command,console,evidence,cases,observer=self.dispatch()
        console.assert_called_once_with('REBOOT');command.assert_called_once();evidence.close.assert_called_once()
    def test_expiry_wait_retains_actual_info_without_claiming_wtp_authority(self):
        command,console,evidence,cases,observer=self.dispatch(wait=True)
        console.assert_not_called();command.assert_called_once()
        self.assertGreaterEqual(observer.call_count,31)
        evidence.close.assert_called_once()
    def test_ap_only_cases_do_not_require_or_fabricate_lan_readiness(self):
        command,console,evidence,cases,observer=self.dispatch(listener_wait=True)
        command.assert_called_once();console.assert_called_once_with('REBOOT')
    def test_interrupted_start_sends_once_and_retains_request(self):
        stream=Socket(b'');http=run.HTTP()
        with patch.object(run.socket,'socket',return_value=stream):wire=http.interrupted('/api/owner/v1/claim/start',{'version':1},run.time.monotonic()+5)
        self.assertEqual(http.attempts,1);self.assertEqual(wire,stream.sent);self.assertTrue(stream.closed)
if __name__=='__main__':unittest.main()
