#!/usr/bin/env python3
import copy
import ast
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
import phase12_engineering_dispatch as dispatch
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
    def test_profile_upload_precedes_running_finish_and_cancel_never_repeats(self):
        calls=[];events=[];state=['loaded'];now=[0]
        class Client:
            generation=7
            def _field(self,op,**value):
                calls.append((op,state[0],value))
                if op=='profile_step_up':return dict(confirmation_required=True,ready=False)
                return {}
            def exchange(self,message,**kwargs):
                calls.append(('apply',state[0],message));raise ClientError('busy')
        prepared=run.prepare_busy_profile(Client(),b'x'*300,'private',7,
            lambda:self.assertEqual(state[0],'loaded'),lambda k,v:events.append(k),clock=lambda:now[0])
        self.assertEqual(calls[0][0],'open');self.assertGreater(len(calls),2)
        self.assertTrue(all(op=='write' for op,_,_ in calls[1:]))
        state[0]='running'
        prepared.finish(lambda:self.assertEqual(state[0],'running'),deadline=18)
        prepared.cancel()
        self.assertTrue(all(s=='loaded' for op,s,_ in calls if op in ('open','write')))
        self.assertTrue(all(s=='running' for op,s,_ in calls if op in ('profile_step_up','apply','cancel')))
        self.assertEqual(sum(op=='cancel' for op,_,_ in calls),1)
        with self.assertRaises(ValueError):prepared.finish(lambda:None,deadline=18)
        self.assertEqual(sum(op=='apply' for op,_,_ in calls),1)
    def setUp(self):
        self.s=State();self.owner=Owner(self.s);self.contender=Foreign(self.s);self.usb=Foreign(self.s);self.ble=Ble(self.s)
        self.p={'source_commit':'1'*40,'boot_id':'2'*32,'profile_generation':7}
        self.events=[];self.reads=0;self.pressures=0
        self.profile_pressures=[]
        self.ble.phase12_profile_pressure=lambda state,owner,job,**kw:self.profile_pressures.append((state,owner,job))
        self.profile_prepares=[];self.profile_cancels=[]
        def prepare(owner,job):
            self.profile_prepares.append((self.s.state,owner,job))
            return SimpleNamespace(finish=lambda *a,**kw:None,cancel=lambda:self.profile_cancels.append(job))
        self.ble.phase12_profile_prepare=prepare
        self.application_pressures=[]
        self.ble.phase12_application_pressure=lambda state,owner,job,**kw:self.application_pressures.append((state,owner,job))
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
        self.assertEqual([v[0] for v in self.application_pressures],['loaded','armed','running'])
        self.assertEqual([v[0] for v in self.profile_prepares],['loaded'])
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
    def test_combined_running_pressure_has_one_deadline_and_no_timer_extension(self):
        now=[0];deadlines=[]
        def application(state,owner,job,*,deadline=None):
            if state=='running':deadlines.append(deadline);now[0]=13
        def profile(state,owner,job,*,deadline=None,prepared=None):
            if state=='running':
                deadlines.append(deadline);self.assertIsNotNone(prepared);now[0]=19
        self.ble.phase12_application_pressure=application;self.ble.phase12_profile_pressure=profile
        with patch.object(run,'resource_health'):
            with self.assertRaisesRegex(ValueError,'combined running pressure deadline'):
                run.directed_wave(self.p,self.owner,self.contender,self.usb,self.ble,
                    lambda:self.s.status(),self.info,self.pressure,clock=lambda:now[0])
        self.assertEqual(deadlines,[18,18]);self.assertEqual(self.owner.ops.count('LOAD'),3)
        self.assertEqual(self.owner.ops.count('ARM'),2);self.assertEqual(len(self.profile_cancels),1)
        self.assertEqual(self.s.state,'empty')
    def test_uncertain_running_arm_cancels_prepared_profile_and_does_not_retry(self):
        original=self.owner.request
        def request(op,body,**kwargs):
            value=original(op,body,**kwargs)
            if op=='ARM' and self.s.claims==3:raise TimeoutError('ARM reply lost')
            return value
        self.owner.request=request
        with self.assertRaises(TimeoutError):self.invoke()
        self.assertEqual(self.owner.ops.count('ARM'),2);self.assertEqual(len(self.profile_cancels),1)
        self.assertEqual(self.s.state,'empty')
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


class ApplicationResourceTests(unittest.TestCase):
    def setUp(self):
        self.plan=dict(boot_id='2'*32);self.events=[];self.calls=[];self.generation=7
        self.pending=False;self.busy=False;self.wrong_error=False;self.corrupt=False
        self.target=dict(scope='member',device_id=run.DEVICE,boot_id=self.plan['boot_id'])
        self.station=dict(callsign='AA0NT',locator='EM18',power_dbm=37)
        self.pins=dict(engine='direct',rf_gp=2,i2c_pair=None,button_gp=14,amplifier_gp=None,
            lpf_gps=[],indicator='onboard_led',indicator_gp=None,indicator_active_high=True)
        self.saved=copy.deepcopy(self.pins)
        self.config=dict(config=dict(version=1,enabled=False,station=copy.deepcopy(self.station),
            wifi=dict(ssid='preserved',password=None,ntp_ipv4='pool.ntp.org'),schedules=[]))
        self.initial_config=copy.deepcopy(self.config)
        self.principal=[];test=self
        class Peer:
            def request(self,op,body,expected_error=None):
                test.principal.append((op,expected_error))
                if op=='STATUS':return dict(boot_id='2'*32,state='empty',owner_id=None,job_id=None,output_active=False)
                if op=='CLAIM' and test.pending:return dict(code='BUSY')
                raise AssertionError('unexpected or admitted request')
        self.peer=Peer()
    def etag(self):return '"'+format(self.generation,'064x')+'"'
    def app(self):
        return dict(schema='transmitter-application/1',target=copy.deepcopy(self.target),
            station=dict(schema='transmitter-station/1',target=copy.deepcopy(self.target),
                station=copy.deepcopy(self.station),saved_generation=str(self.generation),storage_healthy=True),
            hardware=dict(schema='transmitter-hardware/1',target=copy.deepcopy(self.target),
                saved=copy.deepcopy(self.saved),active=copy.deepcopy(self.pins),active_revision='3'*64,
                saved_generation=str(self.generation),storage_healthy=True,pending_restart=self.pending,
                application_error=None,execution_engine='inhibited-standalone-simulator'),
            recurrence=dict(authority='member',enabled=False,suspended=True,schedules=[]),
            capabilities=dict(hardware_write=True),reboot_required=self.pending)
    def http(self,method,path,body=None,revision=None,*,deadline=None):
        self.calls.append((method,path,copy.deepcopy(body),revision))
        if method=='GET':return 200,self.app() if path=='/api/v1/application' else copy.deepcopy(self.config),self.etag()
        if revision is None:return 428,dict(error=dict(code='revision_required')),None
        if revision!=self.etag():return 412,dict(error=dict(code='revision_conflict')),None
        if self.busy:
            if self.corrupt:self.generation+=1
            return 409,dict(error=dict(code='authentication_required' if self.wrong_error else 'busy')),None
        if body['target']!=self.target:return 409,dict(error=dict(code='target_mismatch')),None
        self.generation+=1
        if path=='/api/v1/station':
            self.station=copy.deepcopy(body['station']);self.config['config']['station']=copy.deepcopy(self.station)
        else:
            self.saved=copy.deepcopy(body['pins']);self.pending|=self.saved!=self.pins
            if self.saved==self.pins:self.config['config'].pop('pins',None)
            else:self.config['config']['pins']=copy.deepcopy(self.saved)
        return 200,{},self.etag()
    def emit(self,k,v):self.events.append((k,v))
    def baseline(self):return run.application_readback(self.http,self.plan)
    def test_busy_uses_exact_targets_revisions_and_retains_every_field(self):
        baseline=self.baseline();self.busy=True
        run.busy_application_resources(self.http,baseline,self.plan,lambda:None,self.emit,clock=lambda:0)
        puts=[call for call in self.calls if call[0]=='PUT']
        self.assertEqual([call[1] for call in puts],['/api/v1/station','/api/v1/hardware'])
        self.assertTrue(all(call[2]['target']==self.target and call[3]==baseline['revision'] for call in puts))
        self.assertNotEqual(puts[1][2]['pins']['rf_gp'],self.pins['rf_gp'])
        self.assertEqual(self.generation,7);self.assertEqual(self.config,self.initial_config)
        self.assertEqual([k for k,_ in self.events],['application_busy_refusal']*2+['application_busy_unchanged'])
    def test_wrong_error_or_changed_generation_cannot_count_as_busy_pass(self):
        for field in ('wrong_error','corrupt'):
            with self.subTest(field=field):
                self.setUp();baseline=self.baseline();self.busy=True;setattr(self,field,True)
                with self.assertRaises(ValueError):run.busy_application_resources(self.http,baseline,self.plan,lambda:None,self.emit,clock=lambda:0)
                self.assertFalse(any(k=='application_busy_unchanged' for k,_ in self.events))
    def test_wrong_target_and_cross_route_revision_cannot_qualify_readback(self):
        baseline=self.http
        for fault in ('target','revision'):
            def http(*a,**kw):
                code,value,etag=baseline(*a,**kw)
                if a[1]=='/api/v1/application' and fault=='target':value['target']['boot_id']='0'*32
                if a[1]=='/api/v1/config' and fault=='revision':etag='"'+'f'*64+'"'
                return code,value,etag
            with self.subTest(fault=fault),self.assertRaises(ValueError):run.application_readback(http,self.plan)
    def test_idle_four_saves_restore_metadata_and_pins_but_keep_admission_latch(self):
        result=run.idle_application_resources(self.http,self.peer,self.plan,lambda:None,self.emit,clock=lambda:0)
        self.assertEqual(result['saves'],4);self.assertEqual(result['simulated_jobs'],0)
        self.assertEqual(self.generation,11);self.assertEqual(self.config,self.initial_config)
        self.assertEqual(self.saved,self.pins);self.assertTrue(self.pending)
        self.assertEqual([v for op,v in self.principal if op=='CLAIM'],['BUSY','BUSY'])
        self.assertEqual(sum(k=='application_idle_negative' for k,_ in self.events),4)
    def test_uncertain_idle_save_never_repeated_or_reported_complete(self):
        original=self.http
        def uncertain(*a,**kw):
            result=original(*a,**kw)
            if a[0]=='PUT' and result[0]==200:raise TimeoutError('save applied response lost')
            return result
        with self.assertRaises(TimeoutError):run.idle_application_resources(uncertain,self.peer,self.plan,lambda:None,self.emit,clock=lambda:0)
        self.assertEqual(self.generation,8)
        self.assertEqual(sum(k=='application_idle_complete' for k,_ in self.events),0)
    def test_late_busy_reply_fails_without_extended_deadline(self):
        baseline=self.baseline();self.busy=True;now=[0];original=self.http
        def late(*a,**kw):now[0]=13;return original(*a,**kw)
        with self.assertRaises(ValueError):run.busy_application_resources(late,baseline,self.plan,lambda:None,self.emit,clock=lambda:now[0])
        self.assertEqual(sum(k=='application_busy_unchanged' for k,_ in self.events),0)
class ApplicationHTTPTests(unittest.TestCase):
    def exchange(self,raw,*,late=False,port=443,chunks=None,times=None,log_error=None,close_error=None,no_eof=False):
        events=[];sent=[];now=[0];raw_chunks=list(chunks if chunks is not None else [raw])
        class Stream:
            closed=False;reads=0
            def settimeout(self,value):pass
            def sendall(self,value):sent.append(value)
            def recv(self,size):
                if late:now[0]=4
                if times:now[0]=times[min(self.reads,len(times)-1)]
                self.reads+=1
                if raw_chunks:
                    value=raw_chunks.pop(0)
                    if isinstance(value,BaseException):raise value
                    return value
                if no_eof:raise TimeoutError('EOF has not arrived')
                return b''
            def close(self):
                self.closed=True
                if close_error:raise close_error
        stream=Stream()
        def record(kind,value):
            events.append((kind,value))
            if log_error and kind=='private_application_https_finish':raise log_error
        evidence=SimpleNamespace(record=record)
        args=SimpleNamespace(hostname='wsprrypico.test',port=port)
        def invoke():
            with patch.object(run,'connect',return_value=stream) as connect,patch.object(run,'context'),patch.object(run.time,'monotonic',side_effect=lambda:now[0]):
                try:return run.resource_http(args,evidence,'PUT','/api/v1/station',{'target':'known'},'"'+'a'*64+'"')
                finally:self.assertEqual(connect.call_count,1)
        return invoke,stream,sent,events
    def test_original_request_response_retained_and_exact_etag_returned(self):
        raw=b'HTTP/1.1 409 Conflict\r\nContent-Length: 25\r\nETag: "'+b'a'*64+b'"\r\n\r\n{"error":{"code":"busy"}}'
        # The actual JSON body is 25 bytes; private evidence keeps all wire bytes.
        invoke,stream,sent,events=self.exchange(raw)
        self.assertEqual(invoke(),(409,{'error':{'code':'busy'}},'"'+'a'*64+'"'))
        self.assertTrue(stream.closed);self.assertEqual(len(sent),1)
        self.assertIn(b'If-Match: "'+b'a'*64+b'"\r\n',sent[0])
        self.assertEqual(bytes.fromhex(next(v for k,v in events if k=='private_application_https_tx')['hex']),sent[0])
        self.assertEqual(bytes.fromhex(next(v for k,v in events if k=='private_application_https_rx')['hex']),raw)
    def test_incomplete_extra_or_chunked_response_never_qualifies(self):
        for headers,body in ((b'Content-Length: 3',b'{}'),(b'Content-Length: 2',b'{}x'),
                (b'Content-Length: 2\r\nContent-Length: 3',b'{}'),
                (b'Content-Length: 2\r\nContent-Length: 2',b'{}'),
                (b'Content-Length: 02',b'{}'),
                (b'Content-Length: 2\r\nTransfer-Encoding: identity',b'{}'),
                (b'Transfer-Encoding: chunked',b'2\r\n{}\r\n0\r\n\r\n')):
            with self.subTest(headers=headers,body=body):
                invoke,stream,sent,events=self.exchange(b'HTTP/1.1 200 OK\r\n'+headers+b'\r\n\r\n'+body)
                with self.assertRaises(ValueError):invoke()
                self.assertTrue(stream.closed);self.assertEqual(len(sent),1)
                self.assertEqual(sum(k=='private_application_https_tx' for k,_ in events),1)
                self.assertEqual(sum(k=='private_application_https_finish' for k,_ in events),1)
    def test_duplicate_json_or_expired_transport_never_retries(self):
        body=b'{"x":1,"x":2}'
        raw=b'HTTP/1.1 200 OK\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body
        for late in (False,True):
            with self.subTest(late=late):
                invoke,stream,sent,events=self.exchange(raw,late=late)
                with self.assertRaises(ValueError):invoke()
                self.assertTrue(stream.closed);self.assertEqual(len(sent),1)
    def test_complete_content_length_does_not_wait_for_eof(self):
        raw=b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}'
        invoke,stream,sent,events=self.exchange(raw,no_eof=True)
        self.assertEqual(invoke(),(200,{},None));self.assertEqual(stream.reads,1)
        self.assertTrue(stream.closed);self.assertEqual(len(sent),1)
        self.assertEqual(next(v for k,v in events if k=='private_application_https_finish')['phase'],'complete')
    def test_default_and_nondefault_ports_send_canonical_authority(self):
        raw=b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}'
        for port,authority in ((443,'wsprrypico.test'),(8443,'wsprrypico.test:8443')):
            with self.subTest(port=port):
                invoke,stream,sent,events=self.exchange(raw,port=port)
                invoke();self.assertIn(('Host: '+authority+'\r\n').encode(),sent[0])
                self.assertIn(('Origin: https://'+authority+'\r\n').encode(),sent[0])
                self.assertEqual(len(sent),1);self.assertTrue(stream.closed)
    def test_actual_capacity_pressure_request_uses_canonical_authority(self):
        # Execute the actual nested pressure callback without opening carriers.
        import capacity_pending
        tree=ast.parse(Path(run.__file__).read_text())
        wave=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_device')
        pressure=next(n for n in ast.walk(wave) if isinstance(n,ast.FunctionDef) and n.name=='pressure')
        for port,authority in ((443,'wsprrypico.test'),(8443,'wsprrypico.test:8443')):
            with self.subTest(port=port):
                held=SimpleNamespace(sendall=lambda value:sent.append(value),close=lambda:closed.append(True))
                sent=[];closed=[]
                owner=SimpleNamespace(session='session',padded_status=lambda:None,request=lambda op,body:{'max_payload_bytes':65536},
                    stream=SimpleNamespace(sendall=lambda _:None),close=lambda:None,open=lambda:None)
                namespace=dict(vars(run),args=SimpleNamespace(hostname='wsprrypico.test',port=port),
                    other=object(),e=SimpleNamespace(record=lambda *a:None),owner=owner,wave_end=240,
                    observe_original_info=None,observe_info=lambda:{},plan={'boot_id':'2'*32})
                exec(compile(ast.fix_missing_locations(ast.Module(body=[pressure],type_ignores=[])),'actual-pressure','exec'),namespace)
                with patch.object(run,'connect',return_value=held),patch.object(run,'context'),patch.object(run,'check_status'),\
                        patch.object(run,'invalid_disconnect'),patch.object(capacity_pending,'run',return_value={}):
                    # Function globals were copied above; install only the fake I/O hooks.
                    for name in ('connect','context','check_status','invalid_disconnect'):namespace[name]=getattr(run,name)
                    namespace['pressure']()
                self.assertEqual(sent,[('GET /api/v1/status HTTP/1.1\r\nHost: '+authority+'\r\n').encode()])
                self.assertEqual(closed,[True])
    def test_fragmented_complete_body_has_exact_original_and_no_eof_read(self):
        raw=b'HTTP/1.1 200 OK\r\nContent-Length: 11\r\n\r\n{"ok":true}'
        chunks=[raw[:9],raw[9:-3],raw[-3:]]
        invoke,stream,sent,events=self.exchange(raw,chunks=chunks,no_eof=True)
        self.assertEqual(invoke(),(200,{'ok':True},None));self.assertEqual(stream.reads,3)
        self.assertEqual(bytes.fromhex(next(v for k,v in events if k=='private_application_https_rx')['hex']),raw)
    def test_partial_reply_preserves_first_error_through_logger_and_close(self):
        raw=b'HTTP/1.1 200 OK\r\nContent-Length: 11\r\n\r\n{"ok"'
        original=TimeoutError('original partial receive timeout')
        invoke,stream,sent,events=self.exchange(raw,chunks=[raw,original],
            log_error=OSError('evidence write failed'),close_error=RuntimeError('close failed'))
        with self.assertRaises(TimeoutError) as caught:invoke()
        self.assertIs(caught.exception,original);self.assertTrue(stream.closed);self.assertEqual(len(sent),1)
        final=next(v for k,v in events if k=='private_application_https_finish')
        self.assertEqual(bytes.fromhex(final['hex']),raw);self.assertEqual(final['phase'],'receive')
        self.assertEqual(final['error_type'],'TimeoutError')
    def test_complete_response_at_original_deadline_cannot_qualify(self):
        raw=b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}'
        for at in (2.999,3,3.001):
            with self.subTest(at=at):
                invoke,stream,sent,events=self.exchange(raw,times=[at])
                if at<3:self.assertEqual(invoke(),(200,{},None))
                else:
                    with self.assertRaises(ValueError):invoke()
                self.assertTrue(stream.closed);self.assertEqual(len(sent),1)
                final=next(v for k,v in events if k=='private_application_https_finish')
                self.assertEqual(final['deadline_s'],3);self.assertEqual(final['bytes'],len(raw))

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

class ApplicationDispatchTests(unittest.TestCase):
    def info(self,boot='2'*32):
        return dict(device_id=run.DEVICE,revision='1'*12,firmware='0.0.0-devel',
            provisioning_source='provisioned',provisioning_generation='7',access_generation='3',
            access_state='healthy',access_default_password=True,saved_consumer_profile=None,
            lan_wtp_mode='engineering-tls',softap_session_inactivity_ms='900000',softap_session_absolute_ms='43200000',
            network=dict(link_status=3,ipv4='192.168.84.2',accepted='1',ntp_server='192.168.84.1'),
            status=dict(boot_id=boot,engine='inhibited-standalone-simulator',output_active=False,
                enabled=False,storage_healthy=True,state='empty',clock_state='synchronized'))
    def plan(self):return dict(source_commit='1'*40,boot_id='2'*32,profile_generation=7)
    def observer(self,value):return lambda:(copy.deepcopy(value),json.dumps(value).encode())
    def test_fresh_warm_records_prerequisite_without_time_acceptance(self):
        actions=[];observations=[self.info(),self.info()];observations[-1]['network']['accepted']='2'
        def observer():
            value=observations.pop(0);return value,json.dumps(value).encode()
        with tempfile.TemporaryDirectory() as path,patch.object(run,'resource_health'):
            result=dispatch.warm_accepted_time(self.plan(),observer,
                lambda action,**kw:actions.append((action,kw)),Path(path),clock=lambda:0,sleeper=lambda s:None)
            self.assertEqual(result['cases'],[]);self.assertEqual(result['max_seconds'],180)
            self.assertEqual([a for a,_ in actions],['bind_peer','sntp_on'])
            self.assertEqual(len(list(Path(path).glob('continuation-warm-info-*'))),2)
    def test_warm_late_or_wrong_boot_cannot_enable_fixture(self):
        for fault in ('late','boot'):
            info=self.info('3'*32 if fault=='boot' else '2'*32);now=[0];actions=[]
            def observer():
                now[0]=181 if fault=='late' else 0
                return info,json.dumps(info).encode()
            with tempfile.TemporaryDirectory() as path,patch.object(run,'resource_health'):
                with self.assertRaises(ValueError):dispatch.warm_accepted_time(self.plan(),observer,
                    lambda *a,**kw:actions.append(a),Path(path),clock=lambda:now[0])
            self.assertEqual(actions,[])
    def test_action_lock_precedes_one_normal_reboot_and_unknown_reply_not_retried(self):
        for uncertain in (False,True):
            calls=[]
            def request(op):
                calls.append(op)
                if op=='INFO':return self.info()
                if uncertain:raise TimeoutError('reboot ack lost')
                return dict(ok=True,rebooting=True)
            with patch.object(run,'resource_health'),patch.object(dispatch.os,'open',return_value=99),patch.object(dispatch.os,'close') as close,patch.object(dispatch.fcntl,'flock',side_effect=lambda *a:calls.append('action_flock')):
                if uncertain:
                    with self.assertRaises(TimeoutError):dispatch.normal_reboot(self.plan(),request=request)
                else:self.assertEqual(dispatch.normal_reboot(self.plan(),request=request)['attempts'],1)
                self.assertEqual(calls,['action_flock','INFO','REBOOT']);close.assert_called_once_with(99)
    def test_idle_unknown_reboot_stops_before_cold_proof_without_new_jobs(self):
        stage=dict(saves=4,simulated_jobs=0,rf_jobs=0)
        with tempfile.TemporaryDirectory() as path,patch.object(run,'resource_health'),patch.object(dispatch,'run_idle_device',return_value=stage) as idle,patch.object(dispatch,'normal_reboot',side_effect=TimeoutError('unknown')) as reboot,patch.object(dispatch,'cold_application') as cold:
            with self.assertRaises(TimeoutError):dispatch.application_stage(self.plan(),self.observer(self.info()),Path(path),lambda *a,**kw:None)
            self.assertEqual(idle.call_count,1);self.assertEqual(reboot.call_count,1);cold.assert_not_called()
    def cold_fixture(self,fault=None):
        fixture=ApplicationResourceTests();fixture.setUp()
        baseline=fixture.baseline();app=copy.deepcopy(baseline['application']);target=dict(fixture.target,boot_id='3'*32)
        for resource in (app,app['station'],app['hardware']):resource['target']=copy.deepcopy(target)
        for name in ('station','hardware'):app[name]['saved_generation']='11'
        app['recurrence']['suspended']=False
        active=':'.join((run.DEVICE,'3'*32,'hardware',json.dumps(app['hardware']['saved'],separators=(',',':'))))
        app['hardware']['active_revision']=run.hashlib.sha256(active.encode()).hexdigest()
        info=self.info('3'*32)
        if fault=='pins':app['hardware']['active']['rf_gp']=28
        if fault=='pending':app['hardware']['pending_restart']=True
        if fault=='generation':app['hardware']['saved_generation']='12'
        if fault=='settings':info['access_generation']='4'
        if fault=='time':info['network']['ntp_server']='foreign'
        readback=dict(application=app,config=copy.deepcopy(baseline['config']),revision='"'+'c'*64+'"')
        if fault=='revision':readback['revision']=baseline['revision']
        if fault=='config':readback['config']['config']['wifi']['ssid']='foreign'
        stage=dict(baseline=baseline,before_info=self.info(),saved_generation='11',
            initial_revision=baseline['revision'],final_revision='"'+'b'*64+'"')
        return info,readback,stage
    def test_cold_new_boot_has_exact_saved_active_original_settings_and_shared_authority(self):
        info,readback,stage=self.cold_fixture();actions=[];calls=[]
        class Peer:
            def __init__(self,*a):self.owner=None
            def open(self):calls.append('HELLO/CAPS')
            def request(self,op,body):
                calls.append(op)
                if op=='CLAIM':self.owner=body['owner_id'];return dict(owner_id=self.owner)
                if op=='RELEASE':self.owner=None;return {}
                return dict(boot_id='3'*32,state='empty',output_active=False,owner_id=self.owner,job_id=None)
            def close(self):calls.append('close')
        with tempfile.TemporaryDirectory() as path,patch.object(run,'resource_health'),patch.object(dispatch,'validate_device_plan',return_value=(SimpleNamespace(),None,'')),patch.object(dispatch,'application_readback',return_value=readback),patch.object(dispatch,'RecordedPeer',Peer):
            result=dispatch.cold_application(self.plan(),stage,self.observer(info),Path(path),
                lambda action,**kw:actions.append(action),clock=lambda:0)
            self.assertEqual(result['status'],'PASS_IDLE_APPLICATION_COLD_PROOF')
            self.assertEqual((result['saves'],result['normal_reboots'],result['simulated_jobs']),(4,1,0))
            self.assertEqual(calls,['HELLO/CAPS','STATUS','CLAIM','STATUS','RELEASE','STATUS','close'])
            self.assertEqual((result['claims'],result['releases']),(1,1));self.assertEqual(actions,['bind_peer'])
    def admission(self,*,fault=None,applied=False,record_failure=False):
        calls=[];events=[];test=self;original=TimeoutError('mutation reply unavailable')
        class Peer:
            owner=None
            def request(self,op,body):
                calls.append(op)
                if op=='STATUS':return dict(boot_id='3'*32,state='empty',output_active=False,owner_id=self.owner,job_id=None)
                if op=='CLAIM':
                    if fault=='busy':raise RuntimeError({'code':'BUSY'})
                    if fault!='CLAIM' or applied:self.owner=body['owner_id']
                    if fault=='CLAIM':raise original
                    return dict(owner_id=self.owner)
                if op=='RELEASE':
                    if fault!='RELEASE' or applied:self.owner=None
                    if fault=='RELEASE':raise original
                    return {}
                test.fail('unexpected job operation')
        def record(kind,**value):
            if record_failure:raise OSError('observer unavailable')
            events.append(kind)
        return lambda:dispatch.cold_admission(Peer(),'3'*32,SimpleNamespace(record=record),180,clock=lambda:0),calls,events,original
    def test_healthy_empty_status_with_busy_claim_cannot_qualify_recovered_admission(self):
        invoke,calls,events,_=self.admission(fault='busy')
        with self.assertRaises(RuntimeError):invoke()
        self.assertEqual(calls.count('CLAIM'),1);self.assertNotIn('RELEASE',calls)
        self.assertNotIn('cold_shared_admission_recovered',events)
    def test_unknown_cold_claim_or_release_never_repeated_and_original_failure_preserved(self):
        for fault in ('CLAIM','RELEASE'):
            for applied in (False,True):
                for record_failure in (False,True):
                    with self.subTest(fault=fault,applied=applied,record_failure=record_failure):
                        invoke,calls,events,original=self.admission(fault=fault,applied=applied,record_failure=record_failure)
                        with self.assertRaises(TimeoutError) as caught:invoke()
                        self.assertIs(caught.exception,original);self.assertEqual(calls.count('CLAIM'),1)
                        self.assertLessEqual(calls.count('RELEASE'),1);self.assertNotIn('LOAD',calls)
                        self.assertNotIn('cold_shared_admission_recovered',events)
    def test_cold_pin_pending_config_generation_time_or_revision_mismatch_never_qualifies(self):
        for fault in ('pins','pending','config','generation','settings','time','revision'):
            with self.subTest(fault=fault):
                info,readback,stage=self.cold_fixture(fault)
                with tempfile.TemporaryDirectory() as path,patch.object(run,'resource_health'),patch.object(dispatch,'validate_device_plan',return_value=(SimpleNamespace(),None,'')),patch.object(dispatch,'application_readback',return_value=readback),patch.object(dispatch,'RecordedPeer') as peer:
                    with self.assertRaises(ValueError):dispatch.cold_application(self.plan(),stage,self.observer(info),Path(path),lambda *a,**kw:None,clock=lambda:0)
                    peer.assert_not_called();self.assertFalse((Path(path)/'application-cold-result.json').exists())
    def test_cold_same_boot_deadline_is_bounded_without_second_reboot(self):
        info,readback,stage=self.cold_fixture();now=[0]
        with tempfile.TemporaryDirectory() as path,patch.object(dispatch,'validate_device_plan',return_value=(SimpleNamespace(),None,'')):
            with self.assertRaisesRegex(ValueError,'cold observer cannot fit deadline'):dispatch.cold_application(self.plan(),stage,self.observer(self.info()),Path(path),lambda *a,**kw:None,
                clock=lambda:now[0],sleeper=lambda s:now.__setitem__(0,now[0]+s))
            self.assertLessEqual(now[0],180)

if __name__=='__main__':unittest.main()
