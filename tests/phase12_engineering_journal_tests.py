#!/usr/bin/env python3
import copy
import hashlib
import json
from pathlib import Path
import ast
import re
import sys
import tempfile
import ssl
import shutil
import subprocess
import unittest
from contextlib import contextmanager,ExitStack
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_engineering_journal as runner
import phase12_engineering_journal_dispatch as dispatch
from wsprrypico_ble import canonical_profile,ClientError

class Evidence:
    def __init__(self):self.rows=[]
    def record(self,kind,*args,**kwargs):self.rows.append((kind,args,kwargs))
class Client:
    def __init__(self):self.actions=[];self.fail=False;self.gen=7;self.timeout=8.0
    def connect(self,*args,**kw):self.actions.append('connect');return dict(generation=self.gen)
    def authorize(self,p):self.actions.append('authorize')
    def synchronize_time(self):self.actions.append('time')
    def _field(self,op,**values):self.actions.append(op);return dict(ready=op=='profile_step_up_status')
    def _step_up_ready(self,result):return True,result['ready']
    def exchange(self,value):
        self.actions.append('apply')
        if self.fail:raise ClientError('timeout')
        return dict(generation=8)
    def close(self):self.actions.append('close')

class Tests(unittest.TestCase):
    def setUp(self):
        pem='-----BEGIN CERTIFICATE-----\nAA==\n-----END CERTIFICATE-----\n'
        value=dict(version=1,device_id=runner.DEVICE,wifi=dict(ssid='fixture',password='secret-password',time_server='192.168.84.1'),
            tls=dict(hostname='wsprrypico-0a9d89.local',port=443,server_certificate=pem,
                server_private_key='-----BEGIN PRIVATE KEY-----\nAA==\n-----END PRIVATE KEY-----\n',client_ca=pem))
        self.payload=canonical_profile(value);self.context=dict(stage=0,generation=7,source_commit='a'*40,
            boot_id='b'*32,ble_address='AA:BB:CC:DD:EE:FF',profile_sha256=hashlib.sha256(self.payload).hexdigest())
        from phase12_engineering_journal_stimuli_tests import info as serial_info
        # Use the real USB Scheduler::status schema, including no owner/job keys.
        projection=serial_info()
        self.info=dict(ok=True,device_id=runner.DEVICE,revision='a'*12,phase12_fault_stage=0,phase12_fault_consumed=False,
            status=projection['status'],access_state='healthy',ble_running=True,ble_active_connections=0,
            lan_wtp_ready=False,lan_wtp_port=0,
            provisioning_source='provisioned',provisioning_generation='7',lan_wtp_mode='engineering-tls',access_default_password=True,local_suffix='0a9d89')
        self.client=Client();self.commands=[];self.evidence=Evidence()
    def observe(self):return copy.deepcopy(self.info),json.dumps(self.info).encode()
    def test_supported_cli_creates_two_strict_distinct_cold_profiles(self):
        from network_certificates import validate_bundle
        repo=Path(__file__).resolve().parents[1]
        private=repo/'config/local';private.mkdir(parents=True,exist_ok=True)
        directory=Path(tempfile.mkdtemp(prefix='phase12-journal-test-',dir=private))
        def create(args):
            result=subprocess.run([sys.executable,str(repo/'scripts/network_certificates.py'),*args],
                                  capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr.decode())
        try:
            principals=runner.prepare(directory,bytes(self.payload),create)
            self.assertEqual(set(principals),{'B','C'})
            self.assertNotEqual(principals['B']['server_sha256'],principals['C']['server_sha256'])
            for principal in principals.values():
                payload=Path(principal['profile_path']).read_bytes()
                self.assertEqual(bytes(canonical_profile(json.loads(payload))),payload)
                validate_bundle(Path(principal['key']).parents[1]/'server')
                result=subprocess.run(['openssl','verify','-x509_strict','-purpose','sslclient',
                    '-CAfile',principal['ca'],principal['cert']],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr.decode())
            with self.assertRaises(ValueError):runner.prepare(directory,bytes(self.payload),create)
        finally:shutil.rmtree(directory)
    def command(self,text):self.commands.append(text);return dict(ok=True)
    def run_case(self):
        with patch('phase12_recovery_orchestrator.resource_health'):
            return runner.apply_once(self.context,self.payload,'wspr-0a9d89',self.client,self.observe,self.command,self.evidence,
                                     clock=lambda:0,sleeper=lambda _:None)
    def test_one_apply_and_confirm_scrub(self):
        result=self.run_case();self.assertEqual(result['applies'],1);self.assertEqual(result['confirmations'],1)
        self.assertEqual(self.commands,['ACCESS CONFIRM PROFILE '+runner.DEVICE]);self.assertEqual(self.client.actions.count('apply'),1)
        self.assertTrue(all(v==0 for v in self.payload))
    def test_uncertain_apply_no_cancel_or_retry(self):
        self.context['stage']=8;self.info['phase12_fault_stage']=8;self.client.fail=True
        result=self.run_case();self.assertEqual(result['status'],'APPLY_UNCERTAIN_READBACK_REQUIRED')
        self.assertEqual(self.client.actions.count('apply'),1);self.assertNotIn('cancel',self.client.actions)
    def test_generation_mismatch_before_authorize(self):
        self.client.gen=8
        with self.assertRaises(ValueError):self.run_case()
        self.assertNotIn('authorize',self.client.actions);self.assertFalse(self.commands)
    def test_active_authority_no_hardware_mutation(self):
        self.info['status']['owner_id']='c'*32
        with self.assertRaises(ValueError):self.run_case()
        self.assertEqual(self.client.actions,['close']);self.assertFalse(self.commands)
    def test_checkpoint_ack_is_not_success(self):
        self.context['stage']=10;self.info['phase12_fault_stage']=10
        with self.assertRaises(ValueError):self.run_case()
    def test_consumer_compiled_plain_is_not_engineering(self):
        self.info['provisioning_source']='consumer_preclock';self.info['lan_wtp_mode']='consumer-plain'
        with self.assertRaises(ValueError):self.run_case()
        self.assertFalse(self.commands)
    def test_consumed_fixture_prevents_apply(self):
        self.info['phase12_fault_consumed']=True
        with self.assertRaises(ValueError):self.run_case()
        self.assertFalse(self.commands)
    def test_selection_requires_exact_readback_and_three_principals(self):
        payload=bytes(self.payload);self.info['status']['boot_id']='d'*32;self.info['provisioning_generation']='8'
        probes={r:dict(outcome='tls_auth_refused',reason='TLSV1_ALERT_UNKNOWN_CA',server_sha256='e'*64,address='192.168.84.2',hostname='pico.local') for r in 'ABC'}
        probes['B']=dict(outcome='accepted',device_id=runner.DEVICE,boot_id='d'*32,server_sha256='e'*64,address='192.168.84.2',hostname='pico.local')
        regions=dict(standalone='1'*64,e10='2'*64)
        with patch('phase12_recovery_orchestrator.resource_health'):
            result=runner.verify_selection(self.context,self.info,json.dumps(self.info).encode(),payload,payload,regions,regions,probes,self.evidence)
            self.assertEqual(result['selected'],'B')
            probes['A']['reason']='TIMEOUT'
            with self.assertRaises(ValueError):runner.verify_selection(self.context,self.info,json.dumps(self.info).encode(),payload,payload,regions,regions,probes,self.evidence)
    def test_tls_timeout_not_refusal(self):
        with patch.object(runner.network,'Peer') as cls:
            cls.return_value.open.side_effect=TimeoutError()
            with self.assertRaises(TimeoutError):runner.tls_probe(dict(address='192.168.84.2',device_id=runner.DEVICE,port=443,server_sha256='e'*64,boot_id='d'*32,hostname='pico.local',ca='selected-ca'),dict(ca='a',cert='b',key='c'),self.evidence)

    def test_selected_server_CA_is_used_with_old_client_identity(self):
        plan=dict(address='192.168.84.2',device_id=runner.DEVICE,port=443,
                  server_sha256='e'*64,boot_id='d'*32,hostname='pico.local',ca='current-B-ca')
        principal=dict(ca='retired-A-ca',cert='old-A-client-cert',key='old-A-client-key')
        with patch.object(runner.network,'Peer') as cls:
            cls.return_value.open.side_effect=TimeoutError()
            with self.assertRaises(TimeoutError):runner.tls_probe(plan,principal,self.evidence)
            actual=cls.call_args.args[0]
            self.assertEqual(actual.ca,'current-B-ca');self.assertEqual(actual.cert,'old-A-client-cert')
    def test_local_certificate_verify_failure_cannot_prove_client_revocation(self):
        plan=dict(address='192.168.84.2',device_id=runner.DEVICE,port=443,
                  server_sha256='e'*64,boot_id='d'*32,hostname='pico.local',ca='current-B-ca')
        error=ssl.SSLError('local server certificate failure');error.reason='CERTIFICATE_VERIFY_FAILED'
        with patch.object(runner.network,'Peer') as cls:
            cls.return_value.open.side_effect=error
            with self.assertRaises(ValueError):runner.tls_probe(plan,dict(cert='old',key='old'),self.evidence)
    def test_server_unknown_CA_alert_requires_actual_server_pin(self):
        plan=dict(address='192.168.84.2',device_id=runner.DEVICE,port=443,
                  server_sha256='e'*64,boot_id='d'*32,hostname='pico.local',ca='current-B-ca')
        for pinned in (False,True):
            error=ssl.SSLError('server rejects old client issuer');error.reason='TLSV1_ALERT_UNKNOWN_CA'
            with patch.object(runner.network,'Peer') as cls:
                def handshake():
                    if pinned:
                        cls.call_args.args[1].record('tls',dict(destination=plan['address'],identity=plan['hostname'],fingerprint=plan['server_sha256']))
                    raise error
                cls.return_value.open.side_effect=handshake
                if pinned:
                    result=runner.tls_probe(plan,dict(ca='retired',cert='old',key='old'),self.evidence)
                    self.assertEqual(result['outcome'],'tls_auth_refused')
                else:
                    with self.assertRaises(ValueError):runner.tls_probe(plan,dict(cert='old',key='old'),self.evidence)

    def timed_case(self,clock,*,observe=None,sleeper=None):
        with patch('phase12_recovery_orchestrator.resource_health'):
            return runner.apply_once(self.context,self.payload,'wspr-0a9d89',self.client,
                self.observe if observe is None else observe,self.command,self.evidence,
                clock=lambda:clock[0],sleeper=(lambda delay:clock.__setitem__(0,clock[0]+delay))
                    if sleeper is None else sleeper)

    def test_timely_confirmation_applies_once_without_timeout_renewal(self):
        clock=[0.0];timeouts=[]
        class TimedClient(Client):
            def _field(self,op,**values):
                value=super()._field(op,**values)
                if op=='profile_step_up_status':
                    timeouts.append(self.timeout);clock[0]=24.999
                return value
        self.client=TimedClient()
        result=self.timed_case(clock)
        self.assertEqual(result['applies'],1);self.assertEqual(result['confirmations'],1)
        self.assertEqual(self.client.actions.count('apply'),1)
        self.assertEqual(timeouts,[8.0]);self.assertEqual(self.client.timeout,8.0)

    def test_exact_and_late_confirmation_cannot_apply_or_retry(self):
        for response_s in (25.0,25.001):
            with self.subTest(response_s=response_s):
                case=Tests();case.setUp();clock=[0.0]
                class TimedClient(Client):
                    def _field(self,op,**values):
                        value=super()._field(op,**values)
                        if op=='profile_step_up_status':clock[0]=response_s
                        return value
                case.client=TimedClient()
                with self.assertRaisesRegex(ValueError,'confirmation deadline'):case.timed_case(clock)
                self.assertEqual(case.client.actions.count('profile_step_up_status'),1)
                self.assertNotIn('apply',case.client.actions);self.assertNotIn('cancel',case.client.actions)
                self.assertEqual(case.client.actions.count('close'),1);self.assertEqual(len(case.commands),1)
                self.assertEqual(case.client.timeout,8.0);self.assertFalse(any(case.payload))

    def test_exact_and_late_initial_info_cannot_authorize(self):
        for response_s in (300.0,300.001):
            with self.subTest(response_s=response_s):
                case=Tests();case.setUp();clock=[0.0]
                def observe():
                    value=case.observe();clock[0]=response_s;return value
                with self.assertRaisesRegex(ValueError,'whole journal stage deadline'):
                    case.timed_case(clock,observe=observe)
                self.assertEqual(case.client.actions,['close']);self.assertFalse(case.commands)
                self.assertEqual([row[0] for row in case.evidence.rows],['journal_info'])

    def test_late_connect_authorize_or_time_cannot_admit_next_action(self):
        for operation,next_action in (('connect','authorize'),('authorize','time'),('time','open')):
            with self.subTest(operation=operation):
                case=Tests();case.setUp();clock=[0.0]
                class TimedClient(Client):
                    def connect(self,*args,**values):
                        result=super().connect(*args,**values)
                        if operation=='connect':clock[0]=300.0
                        return result
                    def authorize(self,password):
                        super().authorize(password)
                        if operation=='authorize':clock[0]=300.0
                    def synchronize_time(self):
                        super().synchronize_time()
                        if operation=='time':clock[0]=300.0
                case.client=TimedClient()
                with self.assertRaisesRegex(ValueError,'whole journal stage deadline'):case.timed_case(clock)
                self.assertNotIn(next_action,case.client.actions);self.assertNotIn('apply',case.client.actions)
                self.assertFalse(case.commands);self.assertEqual(case.client.timeout,8.0)

    def test_late_field_result_stops_before_follow_on_mutation(self):
        for operation,next_action in (('open','write'),('write','profile_step_up'),
                                      ('profile_step_up','profile_step_up_status')):
            with self.subTest(operation=operation):
                case=Tests();case.setUp();clock=[0.0]
                class TimedClient(Client):
                    def _field(self,op,**values):
                        result=super()._field(op,**values)
                        if op==operation:clock[0]=300.0
                        return result
                case.client=TimedClient()
                with self.assertRaisesRegex(ValueError,'whole journal stage deadline'):case.timed_case(clock)
                self.assertNotIn(next_action,case.client.actions);self.assertNotIn('apply',case.client.actions)
                self.assertFalse(case.commands);self.assertEqual(case.client.timeout,8.0)

    def test_late_pre_confirmation_or_pre_apply_info_cannot_mutate(self):
        for observation,forbidden in ((3,'confirmation'),(4,'apply')):
            with self.subTest(observation=observation):
                case=Tests();case.setUp();clock=[0.0];observations=[]
                def observe():
                    observations.append(True);value=case.observe()
                    if len(observations)==observation:clock[0]=300.0
                    return value
                with self.assertRaisesRegex(ValueError,'whole journal stage deadline'):
                    case.timed_case(clock,observe=observe)
                self.assertNotIn('apply',case.client.actions)
                self.assertEqual(len(case.commands),0 if forbidden=='confirmation' else 1)

    def test_late_confirmation_command_cannot_poll_or_apply(self):
        clock=[0.0]
        def command(text):
            self.commands.append(text);clock[0]=300.0;return dict(ok=True)
        self.command=command
        with self.assertRaisesRegex(ValueError,'whole journal stage deadline'):self.timed_case(clock)
        self.assertEqual(len(self.commands),1);self.assertNotIn('profile_step_up_status',self.client.actions)
        self.assertNotIn('apply',self.client.actions)

    def test_confirmation_sleep_and_response_timeout_share_original_end(self):
        clock=[0.0];sleeps=[];timeouts=[]
        class TimedClient(Client):
            def _field(self,op,**values):
                result=super()._field(op,**values)
                if op=='profile_step_up_status':
                    timeouts.append(self.timeout);clock[0]=max(clock[0],24.95);result['ready']=False
                return result
        self.client=TimedClient()
        def sleeper(delay):sleeps.append(delay);clock[0]+=delay
        with self.assertRaisesRegex(ValueError,'confirmation deadline'):
            self.timed_case(clock,sleeper=sleeper)
        self.assertEqual(len(timeouts),1);self.assertEqual(sleeps[0],.1)
        self.assertAlmostEqual(sleeps[1],.05);self.assertEqual(clock[0],25.0)
        self.assertNotIn('apply',self.client.actions);self.assertEqual(self.client.timeout,8.0)
        # A smaller stage budget also bounds the confirmation response wait.
        case=Tests();case.setUp();case.context['remaining_s']=5;clock[0]=0.0;timeouts.clear()
        class ShortClient(Client):
            def _field(self,op,**values):
                result=super()._field(op,**values)
                if op=='profile_step_up_status':timeouts.append(self.timeout);clock[0]=5.0
                return result
        case.client=ShortClient()
        with self.assertRaisesRegex(ValueError,'confirmation deadline'):case.timed_case(clock)
        self.assertEqual(timeouts,[4.9]);self.assertNotIn('apply',case.client.actions)

    def test_exact_and_late_apply_ack_cannot_publish_success_or_replay(self):
        for response_s in (300.0,300.001):
            with self.subTest(response_s=response_s):
                case=Tests();case.setUp();clock=[0.0]
                class TimedClient(Client):
                    def exchange(self,value):
                        result=super().exchange(value);clock[0]=response_s;return result
                case.client=TimedClient()
                with self.assertRaisesRegex(ValueError,'whole journal stage deadline'):case.timed_case(clock)
                self.assertEqual(case.client.actions.count('apply'),1)
                self.assertNotIn('cancel',case.client.actions);self.assertEqual(len(case.commands),1)
                self.assertEqual(case.client.actions.count('close'),1);self.assertEqual(case.client.timeout,8.0)

class TrancheTests(unittest.TestCase):
    def test_independent_faults_restore_B_once_no_apply_retries(self):
        setup=Tests();setup.setUp()
        base=bytes(setup.payload);cv=json.loads(base);cv['tls']['client_ca']=cv['tls']['client_ca'].replace('AA==','AQ==');cp=bytes(canonical_profile(cv))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);principals={}
            for role,payload in [('A',base),('B',base),('C',cp)]:
                path=root/(role+'.json');path.write_bytes(payload)
                principals[role]=dict(profile_path=str(path),profile_sha256=hashlib.sha256(payload).hexdigest(),server_sha256=role.lower()*64)
            candidates=[dict(role='engineering',target='WsprryPico',uf2=dict(sha256='e'*64))]+[dict(role='fault_'+str(n),target='WsprryPico',uf2=dict(sha256='f'*64)) for n in (8,9,10)]
            helper_tree=ast.parse((Path(__file__).resolve().parents[1]/'scripts/phase12_recovery_device.py').read_text())
            helper_main=next(n for n in helper_tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
            artifact_guard=next(n for n in helper_main.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='name')
            guard_code=compile(ast.fix_missing_locations(ast.Module(body=[artifact_guard],type_ignores=[])),'actual-device-artifact-guard','exec')
            primitive_paths=[]
            def guard(request):
                exec(guard_code,dict(request=request,root=root,re=re,require=runner.require))
                primitive_paths.extend(request.values())
            with self.assertRaises(ValueError):guard(dict(name='journal-A-before.bin'))
            class Backend:
                remote='/home/pi/phase12-recovery-'+('1'*32)
                def __init__(self):self.gen=7;self.payload=base;self.boot=0;self.stage=0;self.consumed=False;self.calls=[];self.torn=False
                def info(self):
                    value=copy.deepcopy(setup.info);value.update(provisioning_generation=str(self.gen),phase12_fault_stage=self.stage,phase12_fault_consumed=self.consumed)
                    value['status']['boot_id']=f'{self.boot:032x}';return value
                def snapshot(self,name):
                    guard(dict(name=name))
                    (root/name).write_bytes(bytes(4194304));return dict(path=name,inspection=dict(profile_source=1,bond_count=1,default_password=True,profile_healthy=True,profile_payload=self.payload.decode(),profile_sequence=self.gen))
                def deploy(self,role,backup,name,restore=False):
                    guard(dict(image=role+'.uf2',backup=backup['path'],readback=name))
                    self.calls.append((role,name,restore))
                    if name.startswith('journal-b-restore-'):
                        if not restore:raise ValueError('torn C residue not restored')
                        self.gen=backup['inspection']['profile_sequence'];self.payload=backup['inspection']['profile_payload'].encode();self.torn=False
                    self.stage=0 if role=='engineering' else int(role.rsplit('_',1)[1]);self.consumed=False;self.boot+=1
                    return dict(info=self.info())
            backend=Backend();applies=[]
            def apply(request):
                if request.get('action')=='observe_checkpoint':
                    info=backend.info();return dict(info=info,wire_hex=json.dumps(info).encode().hex())
                applies.append(request['stage']);backend.boot+=1;backend.consumed=bool(request['stage'])
                if request['stage'] in (0,10):backend.gen+=1;backend.payload=base if request['stage']==0 else cp
                else:backend.torn=True
                return dict(applies=1,confirmations=1,rf_jobs=0)
            def tls(request):
                selected=request['selected'];probes={r:dict(outcome='tls_auth_refused',reason='TLSV1_ALERT_UNKNOWN_CA',server_sha256=request['server_sha256'],address='192.168.84.2',hostname=request['hostname']) for r in 'ABC'}
                probes[selected].update(outcome='accepted',device_id=runner.DEVICE,boot_id=request['boot_id'])
                return dict(probes=probes)
            context=dict(backend=backend,root=root,preparation=dict(source_commit='a'*40,candidates=candidates),principals=principals,principal_hashes={r:{k:'a'*64 for k in ('ca','cert','key')} for r in 'ABC'},authority='authorized',manifest_sha256='1'*64,ble_address='AA:BB:CC:DD:EE:FF',hostname='pico.local')
            with patch('phase12_recovery_orchestrator.resource_health'):
                result=runner.tranche(context,lambda *args:None,apply,tls,lambda path,value:path.write_text(json.dumps(value)),clock=lambda:0)
            self.assertEqual(applies,[0,8,9,10]);self.assertEqual([row['selected'] for row in result['stages']],['B','B','B','C'])
            restores=[c for c in backend.calls if c[1].startswith('journal-b-restore-')]
            self.assertEqual(len(restores),3);self.assertTrue(all(c[2] for c in restores))
            self.assertTrue(primitive_paths);self.assertTrue(all(re.fullmatch('[a-z0-9_.-]+',name) for name in primitive_paths))

class DispatchTests(unittest.TestCase):
    @contextmanager
    def deadline_case(self,action,observe=None,probe=None,fixture=None,remaining=90):
        setup=Tests();setup.setUp();clock=[0.0];observations=[];probes=[];fixtures=[];sleeps=[]
        evidence=Evidence();evidence.closed=False
        evidence.saved=[]
        evidence.close=lambda:setattr(evidence,'closed',True)
        with tempfile.TemporaryDirectory() as directory:
            actual=Path(directory);remote='/home/pi/phase12-recovery-'+('1'*32)
            class Root:
                def __str__(self):return remote
                def is_dir(self):return True
                def is_symlink(self):return False
                def __truediv__(self,name):return actual/name
            root=Root();image=b'bounded dispatcher admission fixture'
            manifest=dict(source_commit='a'*40,candidates=[dict(role='engineering',target='WsprryPico',
                fault_stage=0,lan_mode='tls',uf2=dict(sha256=hashlib.sha256(image).hexdigest()))])
            manifest_raw=json.dumps(manifest).encode();payload=bytes(setup.payload)
            files={'preparation-manifest.json':manifest_raw,'engineering.uf2':image,'engineering-profile-B.json':payload}
            principal_hashes={}
            for role in 'ABC':
                principal_hashes[role]={}
                for key in ('ca','cert','key'):
                    data=json.loads(payload)['tls']['client_ca'].encode() if (role,key)==('B','ca') else ('fixture-'+role+'-'+key).encode()
                    files['journal-'+role+'-'+key+('.key' if key=='key' else '.crt')]=data
                    principal_hashes[role][key]=hashlib.sha256(data).hexdigest()
            for name,data in files.items():
                path=actual/name;path.write_bytes(data);path.chmod(0o600)
            info=copy.deepcopy(setup.info);info['status'].update(boot_id='c'*32,clock_state='synchronized')
            info['network']=dict(enabled=True,link_status=3,ipv4='192.168.84.2',ntp_server='192.168.84.1',
                ntp_address='192.168.84.1',accepted=1)
            request=dict(root=remote,authority=dispatch.AUTHORITY,stage=0,candidate_role='engineering',
                source_commit='a'*40,manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
                image_name='engineering.uf2',image_sha256=hashlib.sha256(image).hexdigest(),action=action,
                boot_id=('b' if action=='observe_checkpoint' else 'c')*32,remaining_s=remaining,
                journal_stage=0,selected='B',profile_generation=7,hostname=json.loads(payload)['tls']['hostname'],
                selected_profile_sha256=hashlib.sha256(payload).hexdigest(),server_sha256='d'*64,
                principal_hashes=principal_hashes)
            def observer():
                observations.append(clock[0]);value=copy.deepcopy(info)
                if observe is not None:observe(clock,value,len(observations))
                return value,json.dumps(value).encode()
            def tls(plan,principal,sink):
                probes.append(principal)
                if probe is not None:probe(clock,len(probes))
                return dict(outcome='fixture-deadline-result')
            def call_fixture(value):
                fixtures.append(value['action'])
                if fixture is not None:return fixture(clock,value['action'])
            def sleep(seconds):sleeps.append(seconds);clock[0]+=seconds
            with ExitStack() as stack:
                stack.enter_context(patch.object(dispatch,'Path',side_effect=lambda value:root if str(value)==remote else Path(value)))
                stack.enter_context(patch.object(dispatch,'validate_uf2'))
                stack.enter_context(patch.object(dispatch,'Observer',return_value=observer))
                stack.enter_context(patch.object(dispatch,'Evidence',return_value=evidence))
                stack.enter_context(patch.object(dispatch,'tls_probe',side_effect=tls))
                stack.enter_context(patch.object(dispatch,'fixture',side_effect=call_fixture))
                stack.enter_context(patch.object(dispatch,'save',side_effect=lambda path,value:evidence.saved.append((path,value))))
                stack.enter_context(patch.object(dispatch.time,'monotonic',side_effect=lambda:clock[0]))
                stack.enter_context(patch.object(dispatch.time,'sleep',side_effect=sleep))
                stack.enter_context(patch('phase12_recovery_orchestrator.resource_health'))
                yield request,clock,observations,probes,fixtures,sleeps,evidence

    def test_checkpoint_success_before_short_remaining_deadline(self):
        def slow(clock,value,count):clock[0]=44.999
        with self.deadline_case('observe_checkpoint',observe=slow,remaining=45) as case:
            request,clock,observations,probes,fixtures,sleeps,evidence=case
            result=dispatch.run(request)
            self.assertEqual(result['info']['status']['boot_id'],'c'*32)
            self.assertEqual(len(observations),1);self.assertFalse(probes+fixtures+sleeps)

    def test_checkpoint_pending_boot_sleep_uses_same_remaining_deadline(self):
        def old_boot(clock,value,count):
            clock[0]=89.8;value['status']['boot_id']='b'*32
        with self.deadline_case('observe_checkpoint',observe=old_boot) as case:
            request,clock,observations,probes,fixtures,sleeps,evidence=case
            with self.assertRaisesRegex(ValueError,'checkpoint observation deadline'):
                dispatch.run(request)
            self.assertEqual(len(observations),1);self.assertFalse(probes+fixtures)
            self.assertEqual(len(sleeps),1);self.assertAlmostEqual(sleeps[0],.2)
            self.assertEqual(clock[0],90)

    def test_checkpoint_exact_or_late_success_cannot_escape_deadline(self):
        for finish in (90,90.001):
            with self.subTest(finish=finish):
                def slow(clock,value,count):clock[0]=finish
                with self.deadline_case('observe_checkpoint',observe=slow) as case:
                    request,clock,observations,probes,fixtures,sleeps,evidence=case
                    with self.assertRaisesRegex(ValueError,'checkpoint observation deadline'):
                        dispatch.run(request)
                    self.assertEqual(len(observations),1);self.assertFalse(probes+fixtures+sleeps)

    def test_timely_tls_readiness_and_all_three_probes_share_deadline(self):
        with self.deadline_case('tls') as case:
            request,clock,observations,probes,fixtures,sleeps,evidence=case
            result=dispatch.run(request)
            self.assertEqual(set(result['probes']),set('ABC'));self.assertEqual(len(probes),3)
            self.assertEqual(fixtures,['bind_peer','sntp_on']);self.assertEqual(len(observations),7)
            self.assertTrue(evidence.closed)

    def test_exact_or_late_sntp_readiness_admits_no_fixture_or_probe(self):
        for finish in (90,90.001):
            with self.subTest(finish=finish):
                def slow(clock,value,count):clock[0]=finish
                with self.deadline_case('tls',observe=slow) as case:
                    request,clock,observations,probes,fixtures,sleeps,evidence=case
                    with self.assertRaisesRegex(ValueError,'fresh SNTP TLS readiness'):
                        dispatch.run(request)
                    self.assertEqual(len(observations),1);self.assertFalse(probes+fixtures+sleeps)
                    self.assertTrue(evidence.closed)
                    self.assertEqual([row[0] for row in evidence.rows],['tls_usb_info'])
                    self.assertFalse(evidence.saved)

    def test_late_fixture_bind_cannot_enable_sntp_or_probe(self):
        def late(clock,action):clock[0]=90
        with self.deadline_case('tls',fixture=late) as case:
            request,clock,observations,probes,fixtures,sleeps,evidence=case
            with self.assertRaisesRegex(ValueError,'fresh SNTP TLS readiness'):
                dispatch.run(request)
            self.assertEqual(fixtures,['bind_peer']);self.assertFalse(probes)
            self.assertTrue(evidence.closed)

    def test_exact_or_late_tls_probe_cannot_publish_success_or_continue(self):
        for finish in (90,90.001):
            with self.subTest(finish=finish):
                def late(clock,count):clock[0]=finish
                with self.deadline_case('tls',probe=late) as case:
                    request,clock,observations,probes,fixtures,sleeps,evidence=case
                    with self.assertRaisesRegex(ValueError,'fresh SNTP TLS readiness'):
                        dispatch.run(request)
                    self.assertEqual(len(probes),1);self.assertEqual(len(observations),2)
                    self.assertTrue(evidence.closed)
                    self.assertFalse(evidence.saved)

    def test_late_preprobe_observer_prevents_first_tls_attempt(self):
        def late(clock,value,count):
            if count==2:clock[0]=90
        with self.deadline_case('tls',observe=late) as case:
            request,clock,observations,probes,fixtures,sleeps,evidence=case
            with self.assertRaisesRegex(ValueError,'fresh SNTP TLS readiness'):
                dispatch.run(request)
            self.assertEqual(len(observations),2);self.assertFalse(probes)
            self.assertTrue(evidence.closed)

    def test_readiness_sleep_shrinks_to_remaining_absolute_deadline(self):
        def not_ready(clock,value,count):
            clock[0]=89.8;value['network']['link_status']=1
        with self.deadline_case('tls',observe=not_ready) as case:
            request,clock,observations,probes,fixtures,sleeps,evidence=case
            with self.assertRaisesRegex(ValueError,'fresh SNTP TLS readiness'):
                dispatch.run(request)
            self.assertEqual(len(observations),1);self.assertFalse(probes+fixtures)
            self.assertEqual(len(sleeps),1);self.assertAlmostEqual(sleeps[0],.2)
            self.assertEqual(clock[0],90);self.assertTrue(evidence.closed)

    def test_actual_dispatch_accepts_exact_stage_UF2_basenames(self):
        setup=Tests();setup.setUp()
        with tempfile.TemporaryDirectory() as directory:
            actual=Path(directory)
            class Root:
                def __str__(self):return '/home/pi/phase12-recovery-'+('1'*32)
                def is_dir(self):return True
                def is_symlink(self):return False
                def __truediv__(self,name):return actual/name
            for stage in (0,8,9,10):
                role='engineering' if stage==0 else 'fault_'+str(stage);image=b'bounded dummy image'
                candidate=dict(role=role,target='WsprryPico',fault_stage=stage,lan_mode='tls' if stage==0 else 'plain',uf2=dict(sha256=hashlib.sha256(image).hexdigest()))
                manifest=dict(source_commit='a'*40,candidates=[candidate]);manifest_raw=json.dumps(manifest).encode()
                for name,data in [('preparation-manifest.json',manifest_raw),(role+'.uf2',image)]:
                    path=actual/name;path.write_bytes(data);path.chmod(0o600)
                info=copy.deepcopy(setup.info);info.update(phase12_fault_stage=stage,phase12_fault_consumed=bool(stage));info['status']['boot_id']='c'*32
                request=dict(root=str(Root()),authority=dispatch.AUTHORITY,stage=stage,candidate_role=role,
                    source_commit='a'*40,manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),image_name=role+'.uf2',image_sha256=hashlib.sha256(image).hexdigest(),action='observe_checkpoint',boot_id='b'*32,remaining_s=90)
                with patch.object(dispatch,'Path',return_value=Root()),patch.object(dispatch,'validate_uf2'),patch.object(dispatch,'Observer',return_value=lambda:(info,json.dumps(info).encode())),patch('phase12_recovery_orchestrator.resource_health'):
                    result=dispatch.run(request)
                    self.assertEqual(result['info']['phase12_fault_stage'],stage)
                    wrong=dict(request,image_name='fault_7.uf2')
                    with self.assertRaises(ValueError):dispatch.run(wrong)




class StimuliDispatchTests(unittest.TestCase):
    deadline_case=DispatchTests.deadline_case
    def test_fresh_A_original_is_bound_then_held_before_parent_apply(self):
        def observe(clock,value,count):
            value['network']['rejected']=0;value['network']['accepted']=int(count>1)
            value['status']['clock_state']='synchronized' if count>1 else 'unsynchronized'
        def fixture(clock,action):return dict(status='STIMULUS_HOLD')
        with self.deadline_case('stale_prepare',observe=observe,fixture=fixture) as case:
            request,clock,observations,probes,fixtures,sleeps,evidence=case;request['journal_selection']='stimuli'
            result=dispatch.run(request)
            self.assertEqual(result['status'],'STIMULUS_HOLD')
            self.assertEqual(fixtures,['bind_peer','journal_stale_old_bind','sntp_on','journal_stale_hold'])
            self.assertEqual(len(observations),2);self.assertFalse(probes);self.assertTrue(evidence.closed)
    def test_late_A_success_or_late_bind_cannot_hold_or_allow_onward_apply(self):
        for kind in ('observer','bind'):
            def observe(clock,value,count):
                value['network'].update(accepted=0,rejected=0);value['status']['clock_state']='unsynchronized'
                if kind=='observer':clock[0]=90
            def fixture(clock,action):clock[0]=90
            with self.subTest(kind=kind),self.deadline_case('stale_prepare',observe=observe,fixture=fixture) as case:
                request,clock,observations,probes,fixtures,sleeps,evidence=case;request['journal_selection']='stimuli'
                with self.assertRaisesRegex(ValueError,'journal stimulus observation deadline'):dispatch.run(request)
                self.assertEqual(fixtures,[] if kind=='observer' else ['bind_peer']);self.assertFalse(probes)
                self.assertTrue(evidence.closed)
    def test_fresh_B_rejection_before_success_and_late_observer_never_releases(self):
        for finish,passes in [(89.999,True),(90,False),(90.001,False)]:
            def observe(clock,value,count):
                value['provisioning_generation']='8';value['network'].update(accepted=0,rejected=int(count>1))
                value['status']['clock_state']='unsynchronized'
                if count>1:clock[0]=finish
            with self.subTest(finish=finish),self.deadline_case('observe_checkpoint',observe=observe) as case:
                request,clock,observations,probes,fixtures,sleeps,evidence=case;request['journal_selection']='stimuli'
                if passes:
                    result=dispatch.run(request);self.assertTrue(result['stale_time_not_adopted']);self.assertEqual(result['stale_datagrams'],1)
                    self.assertEqual(fixtures,['bind_peer','journal_stale_new_bind','journal_stale_release'])
                else:
                    with self.assertRaisesRegex(ValueError,'checkpoint observation deadline'):dispatch.run(request)
                    self.assertEqual(fixtures,['bind_peer','journal_stale_new_bind'])
                self.assertFalse(probes);self.assertTrue(evidence.closed)
    def test_premature_clock_acceptance_cannot_release_stale_hold(self):
        def observe(clock,value,count):
            value['provisioning_generation']='8';value['network']['rejected']=0
        with self.deadline_case('observe_checkpoint',observe=observe) as case:
            request,clock,observations,probes,fixtures,sleeps,evidence=case;request['journal_selection']='stimuli'
            with self.assertRaisesRegex(ValueError,'no premature B time'):dispatch.run(request)
            self.assertTrue(evidence.closed);self.assertFalse(probes+fixtures)
    def test_five_actual_fault_INFO_samples_before_review_required_publication(self):
        def observe(clock,value,count):
            value.update(provisioning_source='fault',provisioning_generation='0',provisioning_fault=1,lan_wtp_ready=False,
                         ble_running=False,ble_active_connections=0)
            value['status']['clock_state']='unsynchronized'
            value['network'].update(enabled=False,ipv4='',link_status=0,accepted=0,rejected=0)
        with self.deadline_case('observe_fault',observe=observe,remaining=300) as case:
            request,clock,observations,probes,fixtures,sleeps,evidence=case
            request.update(journal_selection='stimuli',boot_id='b'*32)
            result=dispatch.run(request);self.assertEqual(result['fault_samples'],5)
            self.assertEqual(observations,[0,2,4,6,8]);self.assertEqual(len(evidence.rows),5)
            self.assertFalse(probes+fixtures);self.assertEqual(len(evidence.saved),1);self.assertTrue(evidence.closed)
    def test_exact300s_fault_success_or_wrong_fault_source_cannot_publish(self):
        for wrong in (False,True):
            def observe(clock,value,count):
                value.update(provisioning_source='provisioned' if wrong else 'fault',provisioning_generation='0',provisioning_fault=1,lan_wtp_ready=False,
                             ble_running=False,ble_active_connections=0)
                value['status']['clock_state']='unsynchronized'
                value['network'].update(enabled=False,ipv4='',link_status=0,accepted=0,rejected=0)
                if count==5:clock[0]=300
            with self.subTest(wrong=wrong),self.deadline_case('observe_fault',observe=observe,remaining=300) as case:
                request,clock,observations,probes,fixtures,sleeps,evidence=case;request.update(journal_selection='stimuli',boot_id='b'*32)
                with self.assertRaises(ValueError):dispatch.run(request)
                self.assertFalse(evidence.saved+probes+fixtures);self.assertTrue(evidence.closed)
    def test_stimuli_actions_require_explicit_selection_before_observer_or_fixture(self):
        for action in ('stale_suspend','stale_a_ready','stale_arm','stale_prepare','observe_fault'):
            with self.subTest(action=action),self.deadline_case(action) as case:
                request,clock,observations,probes,fixtures,sleeps,evidence=case
                with self.assertRaisesRegex(ValueError,'explicit ordinary journal stimuli'):dispatch.run(request)
                self.assertFalse(observations+fixtures+probes)

class StimuliTrancheTests(unittest.TestCase):
    @contextmanager
    def case(self,late=None,bad_native=False):
        from phase12_engineering_journal_stimuli_tests import bank,info as stimulus_info
        from phase12_engineering_journal_stimuli import BASE,SLOT
        setup=Tests();setup.setUp();now=[0.0]
        base=json.loads(setup.payload);profiles={}
        for role,encoded in [('A','AA=='),('B','AQ=='),('C','Ag==')]:
            value=copy.deepcopy(base);value['tls']['client_ca']=value['tls']['client_ca'].replace('AA==',encoded)
            profiles[role]=bytes(canonical_profile(value))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);principals={}
            for role,payload in profiles.items():
                path=root/(role+'.json');path.write_bytes(payload)
                principals[role]=dict(profile_path=str(path),profile_sha256=hashlib.sha256(payload).hexdigest(),server_sha256=role.lower()*64)
            candidates=[dict(role='engineering',target='WsprryPico',uf2=dict(sha256='e'*64))]+[
                dict(role='fault_'+str(stage),target='WsprryPico',uf2=dict(sha256='f'*64)) for stage in (8,9,10)]
            calls=[];applies=[];events=[];saved=[]
            class Backend:
                remote='/home/pi/phase12-recovery-'+('1'*32)
                def __init__(self):self.generation=7;self.boot=1;self.stage=0;self.fault=False;self.consumed=False
                def info(self):
                    value=stimulus_info(self.generation,f'{self.boot:032x}')
                    value.update(phase12_fault_stage=self.stage,phase12_fault_consumed=self.consumed,
                                 access_default_password=True,local_suffix='0a9d89')
                    if self.fault:
                        value.update(provisioning_source='fault',provisioning_generation='0',provisioning_fault=1,lan_wtp_ready=False,
                                     ble_running=False,ble_active_connections=0)
                        value['network'].update(enabled=False,ipv4='',link_status=0)
                    return value
                def inspection(self):
                    role={7:'A',8:'B',9:'C'}[self.generation]
                    return dict(profile_source=1,bond_count=1,default_password=True,profile_healthy=True,
                        profile_payload=profiles[role].decode(),profile_sequence=self.generation,
                        access_loaded=True,access_state=2,access_sequence=1,epoch=1,reset_level=0,reset_phase=0,
                        operational_healthy=True,config_sequence=0,cursor_sequence=0,watermark=0,config=None,effective_station=None)
                def snapshot(self,name):
                    raw=bytearray(b'\xff'*4194304)
                    previous={7:'A',8:'A',9:'B'}[self.generation];selected={7:'A',8:'B',9:'C'}[self.generation]
                    raw[BASE:BASE+SLOT]=bank(self.generation-1,profiles[previous])
                    raw[BASE+SLOT:BASE+2*SLOT]=bank(self.generation,profiles[selected])
                    (root/name).write_bytes(raw)
                    return dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),inspection=self.inspection())
                def inspect(self,path):
                    from phase12_engineering_journal_stimuli import committed_bank
                    events.append('native_fault_inspection')
                    raw=path.read_bytes();self.assert_corruption=committed_bank(raw,0)['payload']==profiles['B']
                    try:committed_bank(raw,1)
                    except ValueError:pass
                    else:raise AssertionError('newest digest must actually fail')
                    value=self.inspection();value.update(profile_healthy=bad_native,profile_source=0,profile_sequence=0,profile_payload='')
                    return value
                def deploy(self,role,backup,name,restore=False):
                    calls.append((role,name,restore));events.append(name)
                    self.fault=backup['inspection'].get('profile_healthy') is False
                    self.generation=backup['inspection']['profile_sequence'] if not self.fault else 0
                    self.stage=0 if role=='engineering' else int(role.rsplit('_',1)[1]);self.consumed=False;self.boot+=1
                    if late==name:now[0]+=300
                    return dict(info=self.info())
            backend=Backend()
            def remote(request):
                action=request.get('action');events.append(action or 'apply')
                if late is not None and late==action:now[0]+=request['remaining_s']
                if action=='stale_suspend':return dict(status='OWNED_SNTP_SUSPENDED_ONCE')
                if action=='stale_a_ready':
                    value=backend.info();return dict(status='FRESH_A_NO_SNTP_READY',info=value,wire_hex=json.dumps(value).encode().hex())
                if action=='stale_arm':return dict(status='STIMULUS_ARMED')
                if action=='stale_prepare':return dict(status='STIMULUS_HOLD')
                if action=='observe_checkpoint':
                    value=backend.info();result=dict(info=value,wire_hex=json.dumps(value).encode().hex())
                    if request.get('journal_selection')=='stimuli':result.update(stale_datagrams=1,stale_time_not_adopted=True)
                    return result
                if action=='observe_fault':
                    value=backend.info();return dict(info=value,wire_hex=json.dumps(value).encode().hex(),fault_samples=5,rf_jobs=0)
                applies.append(request['stage']);backend.boot+=1;backend.consumed=bool(request['stage'])
                if request['stage'] in (0,10):backend.generation+=1
                return dict(applies=1,confirmations=1,rf_jobs=0)
            def tls(request):
                probes={role:dict(outcome='tls_auth_refused',reason='TLSV1_ALERT_UNKNOWN_CA',server_sha256=request['server_sha256'],
                    address='192.168.84.2',hostname=request['hostname']) for role in 'ABC'}
                probes[request['selected']].update(outcome='accepted',device_id=runner.DEVICE,boot_id=request['boot_id'])
                return dict(probes=probes)
            def stage_seed(path,name):
                events.append('stage_seed');self.assertEqual(path.name,name);self.assertEqual(path.stat().st_size,4194304)
            def save(path,value):saved.append(path.name);path.write_text(json.dumps(value))
            context=dict(backend=backend,root=root,preparation=dict(source_commit='a'*40,candidates=candidates),principals=principals,
                principal_hashes={role:{key:'a'*64 for key in ('ca','cert','key')} for role in 'ABC'},authority='authorized',
                manifest_sha256='1'*64,ble_address='AA:BB:CC:DD:EE:FF',hostname='pico.local')
            def run(selection='stimuli'):
                with patch('phase12_recovery_orchestrator.resource_health'):
                    return runner.tranche(context,lambda *args:None,remote,tls,save,clock=lambda:now[0],selection=selection,stage_seed=stage_seed)
            yield run,backend,calls,applies,events,saved

    def test_explicit_stimuli_four_existing_applies_and_one_guarded_fault_seed(self):
        with self.case() as (run,backend,calls,applies,events,saved):
            result=run();self.assertEqual(applies,[0,8,9,10]);self.assertEqual(result['stale_datagrams'],1)
            self.assertEqual(result['status'],'ENGINEERING_JOURNAL_STIMULI_REVIEW_REQUIRED')
            self.assertEqual(result['corrupted_newest']['fault_samples'],5)
            self.assertTrue(backend.assert_corruption)
            self.assertLess(events.index('native_fault_inspection'),events.index('stage_seed'))
            self.assertLess(events.index('stage_seed'),events.index('journal-corrupt-deploy.bin'))
            self.assertEqual(len([call for call in calls if call[1]=='journal-corrupt-deploy.bin']),1)
            self.assertTrue(next(call for call in calls if call[1]=='journal-corrupt-deploy.bin')[2])
            self.assertEqual(len([call for call in calls if call[1].startswith('journal-b-restore-')]),3)
    def test_default_standard_never_arms_stimulus_or_constructs_fault_seed(self):
        with self.case() as (run,backend,calls,applies,events,saved):
            result=run('standard');self.assertEqual(applies,[0,8,9,10]);self.assertEqual(result['stale_datagrams'],0)
            self.assertFalse(set(events)&{'stale_suspend','stale_a_ready','stale_arm','stale_prepare','observe_fault','native_fault_inspection','stage_seed'})
    def test_original90s_expiry_at_arm_prepare_or_checkpoint_stops_without_followon(self):
        for action,expected in [('stale_arm',[]),('stale_prepare',[]),('observe_checkpoint',[0])]:
            with self.subTest(action=action),self.case(late=action) as (run,backend,calls,applies,events,saved):
                with self.assertRaisesRegex(ValueError,'original stale interval'):run()
                self.assertEqual(applies,expected);self.assertNotIn('native_fault_inspection',events)
                self.assertFalse(any(call[1].startswith('journal-b-restore-') for call in calls))
    def test_cold_prefix300s_expiry_or_A_readiness_expiry_never_starts90_or_applies(self):
        for late in ('journal-deploy-0.bin','stale_a_ready'):
            with self.subTest(late=late),self.case(late=late) as (run,backend,calls,applies,events,saved):
                with self.assertRaisesRegex(ValueError,'stage budget'):run()
                self.assertEqual(applies,[]);self.assertNotIn('stale_arm',events)
    def test_one_suspension_cold_deploy_readiness_then_first90s_arm_order(self):
        with self.case() as (run,backend,calls,applies,events,saved):
            run()
            sequence=['stale_suspend','journal-deploy-0.bin','stale_a_ready','stale_arm','stale_prepare','apply','observe_checkpoint']
            self.assertEqual([events.index(name) for name in sequence],sorted(events.index(name) for name in sequence))
            self.assertEqual(events.count('stale_suspend'),1);self.assertEqual(events.count('stale_arm'),1)
    def test_native_loader_must_fault_before_seed_transfer_or_deployment(self):
        with self.case(bad_native=True) as (run,backend,calls,applies,events,saved):
            with self.assertRaisesRegex(ValueError,'production native loader faults'):run()
            self.assertEqual(applies,[0,8,9,10]);self.assertNotIn('stage_seed',events)
            self.assertNotIn('journal-corrupt-deploy.bin',events)
    def test_original300s_fault_deploy_expiry_admits_no_usb_success_observation(self):
        with self.case(late='journal-corrupt-deploy.bin') as (run,backend,calls,applies,events,saved):
            with self.assertRaisesRegex(ValueError,'corrupted journal case deadline'):run()
            self.assertEqual(applies,[0,8,9,10]);self.assertNotIn('observe_fault',events)
            self.assertNotIn('journal-corrupt-review-required.json',saved)

if __name__=='__main__':unittest.main()
