#!/usr/bin/env python3
import copy
import json
import socket
import ssl
import tempfile
import threading
import struct
from types import SimpleNamespace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_engineering_composition as run
from wsprrypico_ble import ClientError
from validate_wtp_contract import frame

class State:
    def __init__(self):self.owner=None;self.job=None;self.state='empty';self.claims=0
    def status(self):return {'boot_id':'2'*32,'output_active':False,'owner_id':self.owner,
                            'job_id':self.job,'state':self.state}
class Owner:
    def __init__(self,state):self.state=state;self.ops=[];self.bodies=[];self.fail=False;self.fail_mutation=None;self.apply_before_failure=False
    def request(self,op,body,**kw):
        self.ops.append(op);self.bodies.append((op,body));s=self.state
        if op=='STATUS':return s.status()
        if op=='CAPS':return {'engine':'inhibited-standalone-simulator','modes':['tone'],'profiles':['rf-events/1'],'max_events':1,'max_job_duration_ns':'60000000000','minimum_arm_lead_ns':'1000000','maximum_arm_ahead_ns':'60000000000','maximum_arm_uncertainty_ns':'500000000','minimum_lease_ms':1000,'maximum_lease_ms':60000,'frequency_ranges':[{'minimum_nhz':'1','maximum_nhz':'999999999999999999'}]}
        if op=='CLAIM':s.owner=body['owner_id'];s.claims+=1;return {'owner_id':s.owner}
        if op=='LOAD':
            if self.fail:raise TimeoutError('unknown')
            s.job=body['job_id'];s.state='loaded';return {}
        if op=='GET_CLOCK':return {'state':'synchronized','leap':'normal','uncertainty_ns':'300000000','utc_now_ns':'1800000000000000000'}
        if op=='ARM':s.state='running' if s.claims==3 else 'armed';return {}
        if op in ('ABORT','RELEASE'):
            if self.fail_mutation==op and not self.apply_before_failure:raise TimeoutError('unknown mutation')
            if op=='ABORT':s.state='aborted'
            else:s.state='empty';s.owner=s.job=None
            if self.fail_mutation==op:raise TimeoutError('unknown mutation')
            return {}
    def close(self):pass
class Foreign:
    def __init__(self,state):self.state=state;self.ops=[];self.accept=False
    def request(self,op,body,expected_error=None):
        self.ops.append(op)
        if op=='STATUS':return self.state.status()
        if self.accept:return {}
        if expected_error:return {'code':'NOT_OWNER'}
        raise RuntimeError({'code':'NOT_OWNER'})
    def open(self):self.ops.append('open')
    def close(self):self.ops.append('close')
class Ble(Foreign):
    def wtp_exchange(self,op,body):
        if op=='STATUS':return self.state.status()
        if self.accept:return {}
        raise ClientError('NOT_OWNER')
class Tests(unittest.TestCase):
    def profile_probe(self,outcome='busy',ready=False,slow=False):
        calls=[];time=[0];events=[]
        class Client:
            generation=7
            def _field(self,op,**value):
                calls.append((op,value))
                if slow and op=='write':time[0]+=21
                if op=='profile_step_up':return dict(confirmation_required=True,ready=ready)
                return {}
            def exchange(self,message,**kwargs):
                calls.append(('apply',message))
                if outcome!='accepted':raise ClientError(outcome)
                return {}
        def invoke():return run.busy_profile_apply(Client(),b'{"device_id":"'+run.DEVICE.encode()+b'"}',
            'private',7,lambda:None,lambda k,v:events.append((k,v)),clock=lambda:time[0])
        return calls,events,invoke
    def test_busy_profile_apply_exact_response_then_cancel(self):
        calls,events,invoke=self.profile_probe();invoke()
        self.assertEqual([op for op,_ in calls].count('apply'),1)
        self.assertEqual(calls[-1][0],'cancel')
        self.assertTrue(any(kind=='profile_apply_busy' for kind,_ in events))
        step=next(value for op,value in calls if op=='profile_step_up')
        apply=next(value for op,value in calls if op=='apply')
        self.assertEqual(step['apply_request_id'],apply['request_id'])
        self.assertEqual(step['profile_session_id'],apply['session_id'])
    def test_profile_auth_error_or_acceptance_never_count_as_busy(self):
        for outcome in ('authentication_required','accepted','timeout'):
            calls,events,invoke=self.profile_probe(outcome)
            with self.assertRaises(ValueError):invoke()
            self.assertEqual(calls[-1][0],'cancel')
            self.assertFalse(any(kind=='profile_apply_busy' for kind,_ in events))
    def test_profile_ready_or_late_staging_cannot_attempt_apply(self):
        for options in ({'ready':True},{'slow':True}):
            calls,events,invoke=self.profile_probe(**options)
            with self.assertRaises(ValueError):invoke()
            self.assertNotIn('apply',[op for op,_ in calls])
            self.assertEqual(calls[-1][0],'cancel')
    def setUp(self):
        self.s=State();self.owner=Owner(self.s);self.contender=Foreign(self.s);self.usb=Foreign(self.s);self.ble=Ble(self.s)
        self.p={'source_commit':'1'*40,'boot_id':'2'*32,'profile_generation':7}
        self.events=[];self.reads=0;self.pressures=0
        self.profile_pressures=[]
        self.ble.phase12_profile_pressure=lambda state,owner,job:self.profile_pressures.append((state,owner,job))
    def info(self):
        self.reads+=1
        return {'device_id':run.DEVICE,'revision':'1'*12,'firmware':'0.0.0-devel',
                'provisioning_source':'provisioned','provisioning_generation':'7','lan_wtp_mode':'engineering-tls',
                'network_active_connections':1,'network_pending_connections':0,
                'access_state':'healthy','softap_session_inactivity_ms':'900000','softap_session_absolute_ms':'43200000',
                'status':{'boot_id':'2'*32,'state':self.s.state,'output_active':False,
                          'engine':'inhibited-standalone-simulator','enabled':False,'storage_healthy':True}}
    def pressure(self):self.pressures+=1
    def invoke(self):
        with patch('phase12_engineering_composition.resource_health'):
            return run.directed_wave(self.p,self.owner,self.contender,self.usb,self.ble,
                lambda:self.s.status(),self.info,self.pressure,clock=lambda:0,
                emit=lambda k,v:self.events.append((k,v)))
    def test_three_bounded_jobs_shared_observations_cleanup(self):
        result=self.invoke()
        self.assertEqual(result['simulated_jobs'],3)
        self.assertEqual(self.owner.ops.count('LOAD'),3)
        self.assertEqual(self.owner.ops.count('ARM'),2)
        self.assertEqual(self.owner.ops.count('RELEASE'),3)
        self.assertEqual(self.pressures,1)
        self.assertNotIn('open',self.contender.ops)
        rows=[v for k,v in self.events if k=='shared_status']
        self.assertEqual(len(rows),24)
        self.assertEqual([v[0] for v in self.profile_pressures],['loaded','armed','running'])
        self.assertEqual({v['state'] for v in rows},{'loaded','armed','running'})
        self.assertEqual(self.s.state,'empty');self.assertIsNone(self.s.owner)
        self.assertIn('maximum 65536-byte valid STATUS framing',result['covered'])
    def test_unsafe_baseline_no_mutation(self):
        original=self.info
        def unsafe():
            v=original();v['status']['output_active']=True;return v
        self.info=unsafe
        with self.assertRaises(ValueError):self.invoke()
        self.assertEqual(self.owner.ops,[]);self.assertEqual(self.pressures,0)
    def test_foreign_mutation_success_stops_and_cleans(self):
        self.usb.accept=True
        with self.assertRaises(ValueError):self.invoke()
        self.assertEqual(self.owner.ops.count('LOAD'),1)
        self.assertEqual(self.s.state,'empty')
        self.assertTrue(any(k=='cleanup_confirmed' for k,v in self.events))
    def test_uncertain_load_never_repeated(self):
        self.owner.fail=True
        with self.assertRaises(TimeoutError):self.invoke()
        self.assertEqual(self.owner.ops.count('LOAD'),1)
        self.assertEqual(self.owner.ops.count('CLAIM'),1)
        self.assertEqual(self.s.state,'empty')
    def test_uncertain_mutations_never_repeat(self):
        for op in ('ABORT','RELEASE'):
            for applied in (False,True):
                with self.subTest(op=op,applied=applied):
                    self.setUp();self.owner.fail_mutation=op;self.owner.apply_before_failure=applied
                    with self.assertRaises(TimeoutError):self.invoke()
                    self.assertEqual(self.owner.ops.count(op),1)
                    expected='cleanup_confirmed' if applied else 'cleanup_unconfirmed'
                    self.assertTrue(any(k==expected for k,v in self.events))
    def test_capacity_timeout_is_inconclusive(self):
        def connect():raise socket.timeout('timeout')
        with self.assertRaises(socket.timeout):run.capacity_probe(connect,lambda k,v:self.events.append((k,v)))
        self.assertEqual(self.events,[])
    def test_capacity_observed_refusal_or_reset(self):
        for error in (ConnectionRefusedError('refused'),ConnectionResetError('reset'),ssl.SSLEOFError('EOF')):
            def connect():raise error
            run.capacity_probe(connect,lambda k,v:self.events.append((k,v)))
        self.assertEqual(len(self.events),3)
    def test_capacity_exact_unexpected_eof_specimen(self):
        error=ssl.SSLEOFError(8,'[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol')
        def connect():raise error
        run.capacity_probe(connect,lambda k,v:self.events.append((k,v)))
        self.assertEqual(self.events,[('excess_connection_refused',{'observed':'SSLEOFError'})])
    def test_capacity_unexpected_tls_error_fails(self):
        def connect():raise ssl.SSLError('unrelated TLS failure')
        with self.assertRaises(ValueError):run.capacity_probe(connect,lambda k,v:self.events.append((k,v)))
        self.assertEqual(self.events,[])
    def test_capacity_admitted_stream_closed_and_fails(self):
        class Socket:
            closed=False
            def close(self):self.closed=True
        stream=Socket()
        with self.assertRaises(ValueError):run.capacity_probe(lambda:stream,lambda k,v:None)
        self.assertTrue(stream.closed)
    def test_running_completion_during_https_fails_without_extension(self):
        def http():
            if self.s.state=='running':self.s.state='completed'
            return self.s.status()
        with patch('phase12_engineering_composition.resource_health'):
            with self.assertRaises((ValueError,RuntimeError)):
                run.directed_wave(self.p,self.owner,self.contender,self.usb,self.ble,http,
                    self.info,self.pressure,clock=lambda:0,emit=lambda k,v:self.events.append((k,v)))
        self.assertEqual(self.owner.ops.count('LOAD'),3)
        self.assertEqual(self.owner.ops.count('ARM'),2)
        self.assertEqual(self.owner.ops.count('ABORT'),2)
        self.assertEqual(self.owner.ops.count('RELEASE'),3)
        self.assertEqual(self.s.state,'empty')
        self.assertFalse(any(k=='case_pass' and v['state']=='running' for k,v in self.events))
    def test_wtp_owner_preflight_requires_explicit_unowned(self):
        self.s.owner='foreign-owner'
        with self.assertRaises((ValueError,RuntimeError)):self.invoke()
        self.assertEqual(self.owner.ops,['STATUS'])
        self.assertEqual(self.pressures,0)
    def test_info_has_no_owner_or_job_identity(self):
        value=self.info()
        self.assertNotIn('owner_id',value['status']);self.assertNotIn('job_id',value['status'])
        with patch('phase12_engineering_composition.resource_health'):
            run.guard(value,self.p,empty=True)
    def test_worker_api_no_signal_or_process_lock_and_private_evidence(self):
        errors=[];peers=[]
        class Peer:
            def __init__(self,*a):self.closed=False;peers.append(self)
            def close(self):self.closed=True
            def open(self):raise AssertionError('unsafe baseline must precede network')
        def worker(path):
            try:run.run_device(self.p,path,lambda:dict(self.info(),device_id='wrong'))
            except BaseException as error:errors.append(error)
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'wire.jsonl'
            with patch.object(run,'validate_device_plan',return_value=(None,None,'password')),patch.object(run,'RecordedPeer',Peer),patch.object(run,'resource_health'),patch.object(run.signal,'signal',side_effect=AssertionError('signal in worker')),patch.object(run.signal,'alarm',side_effect=AssertionError('alarm in worker')),patch.object(run.fcntl,'flock',side_effect=AssertionError('global lock')):
                thread=threading.Thread(target=worker,args=(path,));thread.start();thread.join(2)
                self.assertFalse(thread.is_alive())
            self.assertEqual(len(errors),1);self.assertIsInstance(errors[0],ValueError)
            self.assertEqual(path.stat().st_mode&0o777,0o600)
            self.assertTrue(all(p.closed for p in peers))
    def test_https_contender_uses_exact_foreign_hello_abort_release_helper(self):
        args=object();evidence=object();peer=run.HTTPSContender(args,evidence)
        with patch.object(run,'foreign_checks') as checks:
            self.assertEqual(peer.request('ABORT',{'job_id':'job'},expected_error='NOT_OWNER'),{'code':'NOT_OWNER'})
            checks.assert_called_once_with(args,evidence,'job')
        with self.assertRaises(ValueError):peer.request('CLAIM',{})
    def test_predeclared_duration_and_leads(self):
        self.invoke()
        jobs=[body for op,body in self.owner.bodies if op=='LOAD']
        self.assertEqual([j['total_duration_ns'] for j in jobs],['30000000000']*3)
        self.assertTrue(all(j['events'][0]['duration_ns']=='30000000000' for j in jobs))
        starts=[int(body['start_utc_ns']) for op,body in self.owner.bodies if op=='ARM']
        self.assertEqual(starts,[1800000045000000000,1800000010000000000])
    def test_insufficient_arm_caps_rejected_before_claim_load(self):
        original=self.owner.request
        def request(op,body,**kw):
            value=original(op,body,**kw)
            if op=='CAPS':value['maximum_arm_ahead_ns']='44000000000'
            return value
        self.owner.request=request
        with self.assertRaises(ValueError):self.invoke()
        self.assertNotIn('CLAIM',self.owner.ops);self.assertNotIn('LOAD',self.owner.ops)
        self.assertEqual(self.pressures,0)
    def test_maximum_valid_status_exact_frame_and_rejection_paths(self):
        class Evidence:
            def record(self,*a):pass
        for failure in (None,'crc','request','session','owned'):
            with self.subTest(failure=failure):
                peer=run.RecordedPeer(SimpleNamespace(boot_id='2'*32),Evidence())
                class Socket:
                    def __init__(self):self.pending=b'';self.wire=None
                    def settimeout(self,value):pass
                    def sendall(self,wire):
                        self.wire=wire
                        header=struct.unpack('>4sBBHII',wire[:16])
                        self_payload=wire[16:]
                        self_test.assertEqual(header[4],65536);self_test.assertEqual(len(self_payload),65536)
                        self_test.assertEqual(run.crc32c(self_payload),header[5])
                        request=json.loads(self_payload)
                        self_test.assertEqual(request['op'],'STATUS')
                        value=dict(type='response',protocol='WTP/1',session_id=peer.session,
                            request_id=request['request_id'],op='STATUS',ok=True,
                            body=dict(boot_id='2'*32,state='empty',output_active=False,owner_id=None,job_id=None,terminal_records=[]))
                        if failure=='request':value['request_id']='0'*32
                        if failure=='session':value['session_id']='0'*32
                        if failure=='owned':value['body']['owner_id']='a'*32
                        self.pending=frame(json.dumps(value).encode())
                        if failure=='crc':self.pending=self.pending[:15]+bytes([self.pending[15]^1])+self.pending[16:]
                    def recv(self,size):
                        result=self.pending[:size];self.pending=self.pending[size:];return result
                self_test=self;peer.stream=Socket()
                if failure:
                    with self.assertRaises((ValueError,RuntimeError)):peer.padded_status()
                else:self.assertIsNone(peer.padded_status()['owner_id'])
    def test_guard_rejects_wrong_boot_profile_and_policy_types(self):
        for key,value in [('revision','3'*12),('provisioning_generation',True),
                          ('softap_session_inactivity_ms','0900000'),('lan_wtp_mode','plain')]:
            value_info=self.info();value_info[key]=value
            with patch('phase12_engineering_composition.resource_health'):
                with self.assertRaises(ValueError):run.guard(value_info,self.p,empty=True)
    def test_three_actual_framing_events_then_disconnect(self):
        values=[]
        for i in range(3):
            values.append(frame(json.dumps({'type':'event','protocol':'WTP/1','session_id':'s',
                'boot_id':'2'*32,'event':'INVALID_FRAME','body':{'error':{'code':'INVALID_FRAME'}}}).encode()))
        class Socket:
            def settimeout(self,value):pass
            def recv(self,size):return values.pop(0) if values else b''
        run.invalid_disconnect(Socket(),'s','2'*32)
    def test_disconnect_without_error_events_not_framing_pass(self):
        class Socket:
            def settimeout(self,value):pass
            def recv(self,size):return b''
        with self.assertRaises(ValueError):run.invalid_disconnect(Socket(),'s','2'*32)
    def test_wrong_rejection_layer_fails(self):
        def call(op,body):raise ClientError('authentication_required')
        with self.assertRaises(ValueError):run.reject_foreign(call,'job')
class FramingWitnessTests(unittest.TestCase):
    def test_partial_advisory_requires_fresh_endpoint_close_and_actual_peer_close(self):
        headers=struct.pack('>4sBBHII',b'WTPF',1,1,0,65537,0)*3
        # Original LIVE8 receive specimen: a complete header with missing body.
        partial=bytes.fromhex('5754504601010000000000fd75e34fa7')
        for fault in (None,'stale','reason','tls','active','pending','timeout','headers','late'):
            with self.subTest(fault=fault):
                sent=[];chunks=[partial];now=[0];events=[]
                infos=[dict(network_wtp_close_reason=4 if fault=='stale' else 0),
                    dict(network_wtp_close_reason=5 if fault=='reason' else 4,
                         network_wtp_tls_result=-1 if fault=='tls' else 0,
                         network_active_connections=1 if fault=='active' else 0,
                         network_pending_connections=1 if fault=='pending' else 0)]
                class Socket:
                    def settimeout(self,value):pass
                    def sendall(self,value):sent.append(value)
                    def recv(self,size):
                        if chunks:return chunks.pop(0)
                        if fault=='timeout':raise TimeoutError('inconclusive')
                        raise ConnectionResetError('observed peer reset')
                def observe():
                    if len(infos)==1 and fault=='late':now[0]=6
                    return infos.pop(0)
                with patch.object(run.time,'monotonic',side_effect=lambda:now[0]):
                    def call():return run.invalid_disconnect(Socket(),'s','2'*32,
                        observe_close=observe,headers=headers[:-1] if fault=='headers' else headers,
                        emit=lambda *v:events.append(v))
                    if fault is None:
                        result=call();self.assertEqual(result['peer_outcome'],'reset')
                        self.assertEqual(result['advisory_events_received'],0)
                        self.assertEqual(sent,[headers]);self.assertEqual(events[-1][0],'framing_endpoint_close_observed')
                    else:
                        with self.assertRaises((ValueError,TimeoutError)):call()
                        self.assertFalse(any(v[0]=='framing_endpoint_close_observed' for v in events))
                        self.assertEqual(len(sent),0 if fault in ('stale','headers') else 1)
    def test_complete_foreign_advisory_fails_even_with_endpoint_witness(self):
        payload=json.dumps(dict(type='event',protocol='WTP/1',session_id='foreign',
            boot_id='2'*32,event='INVALID_FRAME',body={'error':{'code':'INVALID_FRAME'}})).encode()
        values=[frame(payload)];infos=[dict(network_wtp_close_reason=0)]
        class Socket:
            def settimeout(self,value):pass
            def sendall(self,value):pass
            def recv(self,size):return values.pop(0)
        with self.assertRaises(ValueError):run.invalid_disconnect(Socket(),'s','2'*32,
            observe_close=lambda:infos.pop(0),headers=struct.pack('>4sBBHII',b'WTPF',1,1,0,65537,0)*3)

if __name__=='__main__':unittest.main()
