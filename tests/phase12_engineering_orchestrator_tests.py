#!/usr/bin/env python3
import ast
import json
from pathlib import Path
import sys
import tempfile
import signal
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_engineering_orchestrator as run
class Backend:
    last=None;fail='';reset_consumed=True
    def __init__(self,*args):
        Backend.last=self;self.remote='/private';self.roles={};self.restores=[];self.submits=0;self.cleaned=False;self.deployed=None
    def setup(self):return {}
    def snapshot(self,name):
        if name=='baseline.bin':return dict(path=name,sha256='a'*64,inspection={})
        if name=='reset-before.bin':return dict(path=name,sha256='b'*64,inspection=dict(effective_station={'callsign':'K1ABC'},profile_sequence=5,epoch=1))
        return dict(path=name,sha256='c'*64,inspection=dict(profile_source=2,profile_payload='',profile_sequence=1,epoch=2,bond_count=0,default_password=True,effective_station={'callsign':'K1ABC'}))
    def restore(self,b,name):
        self.restores.append(name);return dict(readback=name)
    def stable_restore(self,*a):return dict(samples=5)
    def deploy(self,role,*a):
        self.deployed=role
        if Backend.fail=='deploy':raise TimeoutError()
        return dict(info={'status':{'boot_id':'before'}})
    def prepare(self,*a):return dict(sha256='d'*64)
    def submit(self,*a):self.submits+=1;raise TimeoutError('uncertain')
    def cleanup(self):self.cleaned=True
class Tests(unittest.TestCase):
    def test_failed_fixture_captures_original_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter=run.RemoteAdapters(Path(directory));adapter.backend=SimpleNamespace(remote='/private/remote')
            original=TimeoutError('uncertain fixture invocation')
            adapter.invoke=MagicMock(side_effect=original);adapter.collect=MagicMock()
            with self.assertRaises(TimeoutError) as caught:adapter.fixture('start_ap',{})
            self.assertIs(caught.exception,original)
            adapter.collect.assert_called_once_with(('fixture-action-failure.json',))
    def test_fixture_capture_failure_preserves_original_invocation(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter=run.RemoteAdapters(Path(directory));adapter.backend=SimpleNamespace(remote='/private/remote')
            original=TimeoutError('uncertain fixture invocation')
            adapter.invoke=MagicMock(side_effect=original);adapter.collect=MagicMock(side_effect=OSError('capture unavailable'))
            with self.assertRaises(TimeoutError) as caught:adapter.fixture('start_ap',{})
            self.assertIs(caught.exception,original)
    def provision_adapter(self,root,invoke,collect):
        from types import SimpleNamespace
        adapter=run.RemoteAdapters(root);adapter.backend=SimpleNamespace(remote='/private/remote')
        adapter.invoke=invoke;adapter.collect=collect
        profile=root/'input-profile.json';profile.write_bytes(b'{}')
        password=root/'input-password.txt';password.write_bytes(b'fixture-only')
        clearance=root/'input-clearance.json';clearance.write_bytes(b'{}')
        with patch.object(run,'transfer'):
            return adapter.provision(dict(profile=str(profile),password_file=str(password),private_wire_log=str(root/'setup-wire.jsonl'),target_bond_clearance_file=str(clearance)))

    def test_failed_setup_collects_original_wire_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);original=TimeoutError('unknown setup result')
            invoke=MagicMock(side_effect=original)
            def collect(names):
                self.assertEqual(names,('setup-wire.jsonl',));(root/names[0]).write_bytes(b'{"status":"STOPPED"}\n')
            collected=MagicMock(side_effect=collect)
            with self.assertRaises(TimeoutError) as caught:self.provision_adapter(root,invoke,collected)
            self.assertIs(caught.exception,original);self.assertEqual(invoke.call_count,1);collected.assert_called_once()
            self.assertTrue((root/'setup-wire.jsonl').is_file())

    def test_failed_setup_preserves_original_error_if_collection_also_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);original=TimeoutError('unknown setup result');invoke=MagicMock(side_effect=original)
            collect=MagicMock(side_effect=OSError('capture unavailable'))
            with self.assertRaises(TimeoutError) as caught:self.provision_adapter(root,invoke,collect)
            self.assertIs(caught.exception,original);self.assertEqual(invoke.call_count,1);collect.assert_called_once()
            self.assertEqual(json.loads((root/'setup-capture-error.json').read_text())['error_type'],'OSError')

    def test_original_setup_error_survives_unwritable_error_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);original=TimeoutError('unknown setup result');write=run.private_write
            def private_write(path,value):
                if Path(path).name=='setup-capture-error.json':raise OSError('receipt unavailable')
                return write(path,value)
            with patch.object(run,'private_write',side_effect=private_write),self.assertRaises(TimeoutError) as caught:
                self.provision_adapter(root,MagicMock(side_effect=original),MagicMock(side_effect=OSError('capture unavailable')))
            self.assertIs(caught.exception,original)

    def test_acknowledged_setup_requires_regular_nonempty_original_capture(self):
        for invalid in ('missing','empty','symlink'):
            with self.subTest(invalid=invalid),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);invoke=MagicMock(return_value={'status':'ACKNOWLEDGED'})
                def collect(names):
                    target=root/names[0]
                    if invalid=='empty':target.write_bytes(b'')
                    if invalid=='symlink':
                        other=root/'other';other.write_bytes(b'not-original');target.symlink_to(other)
                with self.assertRaisesRegex(ValueError,'original setup capture'):
                    self.provision_adapter(root,invoke,MagicMock(side_effect=collect))
                self.assertEqual(invoke.call_count,1)

    def test_acknowledged_setup_returns_after_original_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);result={'status':'ACKNOWLEDGED'};invoke=MagicMock(return_value=result)
            def collect(names):(root/names[0]).write_bytes(b'{"status":"ACKNOWLEDGED"}\n')
            self.assertEqual(self.provision_adapter(root,invoke,MagicMock(side_effect=collect)),result)
            self.assertEqual(invoke.call_count,1)

    def test_real_bond_reset_attempt_once_and_restore_original_manifest_binding(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'before.bin').write_bytes(bytes(4194304));(root/'after.bin').write_bytes(bytes(4194304))
            original={'source_commit':'a'*40};old_role={'role':'fault_1','revision':'a'*12}
            selected={'role':'fault_1','fault_stage':1,'revision':'b'*12,'uf2':{'path':'fault.uf2'}}
            preparation={'source_commit':'b'*40,'candidates':[selected]}
            backend=MagicMock();backend.manifest=original;backend.roles={'fault_1':old_role}
            info=dict(device_id=run.DEVICE,revision='b'*12,provisioning_source='unprovisioned',
                phase12_fault_consumed=True,status=dict(boot_id='2'*32,state='empty',enabled=False,output_active=False))
            backend.info.return_value=info
            backend.snapshot.side_effect=[dict(path='before.bin',inspection=dict(bond_count=1,profile_source=1,
                profile_healthy=True,operational_healthy=True,access_state=2,config={'enabled':False},effective_station={})),
                dict(path='after.bin',inspection=dict(profile_source=2,bond_count=0,profile_sequence=1))]
            backend.deploy.side_effect=[dict(info=dict(info,status=dict(info['status'],boot_id='1'*32))),dict(info=info)]
            backend.prepare.return_value={'request_sha256':'d'*64};backend.submit.side_effect=TimeoutError('unknown reply')
            context=dict(backend=backend,root=root,preparation=preparation,preparation_artifacts=root,info=info)
            with patch.object(run,'safe_info',side_effect=lambda value,*args:value),patch.object(run,'transfer'),                  patch.object(run,'bonded_security_keys',return_value={1:b'oldER',2:b'oldIR'}),patch.object(run,'local_security_keys',return_value={1:b'newER',2:b'newIR'}),patch.object(run,'assess') as assess:
                result=run.revoke_single_bond(context)
            self.assertEqual(backend.submit.call_count,1);self.assertEqual(backend.prepare.call_count,1)
            self.assertIs(backend.manifest,original);self.assertIs(backend.roles['fault_1'],old_role)
            self.assertFalse(result['cryptographic_peer_refusal_observed']);self.assertEqual(result['old_peer_attempts'],0)
            self.assertEqual(backend.deploy.call_args.args[0],'engineering');assess.assert_called_once()
            self.assertTrue((root/'single-bond-submit-unknown.json').exists())

    def test_bonded_root_parser_accepts_actual_peer_and_deleted_history(self):
        import struct
        def bank(epoch=0,peer_tag=0x42544400,peer_size=60,unknown=None):
            records=struct.pack('>II',0,16)+b'x'*16
            records+=struct.pack('>II',0x534d4552,16)+b'e'*16
            records+=struct.pack('>II',0x534d4952,16)+b'i'*16
            records+=struct.pack('>II',peer_tag,peer_size)+b'p'*peer_size
            if unknown is not None:records+=struct.pack('>II',unknown,16)+b'u'*16
            return b'BTstack'+bytes([epoch])+records+b'\xff'*(4088-len(records))
        parsed=run.bonded_security_keys(bank()+b'\xff'*4096)
        self.assertEqual(parsed,{0x534d4552:b'e'*16,0x534d4952:b'i'*16})
        self.assertEqual(run.bonded_security_keys(bank(0)+bank(1)),parsed)
        for value in (bank(peer_tag=0x42544404),bank(peer_size=59),bank(unknown=0x12345678)):
            with self.assertRaises(ValueError):run.bonded_security_keys(value+b'\xff'*4096)
        with self.assertRaises(ValueError):run.bonded_security_keys(bank()+bank())
    def test_att_metadata_preserves_opaque_peer_and_rejects_invalid_records(self):
        import struct
        def bank(extra=(), peer=b'p'*60):
            records=[(0x534d4552,b'e'*16),(0x534d4952,b'i'*16),
                     (0x42544403,peer),(0x42544442,b'h'*16)] + list(extra)
            raw=b''.join(struct.pack('>II',tag,len(value))+value for tag,value in records)
            return b'BTstack\0'+raw+b'\xff'*(4088-len(raw))+b'\xff'*4096
        ccc=struct.pack('<IHBB',1,16,2,3)
        expected={0x534d4552:b'e'*16,0x534d4952:b'i'*16}
        self.assertEqual(run.bonded_security_keys(bank([(0x42544313,ccc)])),expected)
        self.assertEqual(run.bonded_security_keys(bank([(0x42544300,ccc)],b'\x90'*60)),expected)
        bad=[[(0x42544314,ccc)],[(0x12345678,ccc)],[(0x42544313,b'x'*7)],
             [(0x42544442,b'h'*16)],[(0x42544313,ccc),(0x42544313,ccc)]]
        bad += [[(0x42544313,struct.pack('<IHBB',seq,handle,value,device))]
                for seq,handle,value,device in [(0,16,2,3),(1,0,2,3),(1,16,0,3),
                    (1,16,4,3),(1,16,2,4),(1,16,2,2)]]
        for records in bad:
            with self.subTest(records=records):
                with self.assertRaises(ValueError):run.bonded_security_keys(bank(records))
        torn=bytearray(bank());struct.pack_into('>I',torn,12,4090)
        with self.assertRaises(ValueError):run.bonded_security_keys(bytes(torn))
    def setUp(self):Backend.fail=''
    def test_whole_tranche_interrupts_blocking_operation_and_restores_timer(self):
        previous = signal.getsignal(signal.SIGALRM)
        with self.assertRaisesRegex(TimeoutError, 'whole ordinary serialization'):
            with run.tranche_deadline(.03):
                time.sleep(1)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))
        self.assertIs(signal.getsignal(signal.SIGALRM), previous)

    def test_tranche_preserves_existing_alarm_before_work(self):
        signal.setitimer(signal.ITIMER_REAL, 5)
        try:
            with self.assertRaisesRegex(ValueError, 'existing process timer'):
                with run.tranche_deadline():
                    self.fail('work must not begin')
            self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0], 0)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)

    def invoke(self,root,**kw):
        recovery=dict(source_commit='1'*40);prep=dict(source_commit='2'*40)
        with patch.object(run,'safe_info'),patch.object(run,'sha',return_value='a'*64):
            return run.execute(recovery,prep,root,root/'campaign','inspector',{},backend_factory=Backend,
                fixture=lambda *a:None,provision=lambda *a:None,cases=lambda *a:None,**kw)
    def test_uncertain_reset_submit_once_then_restore(self):
        with tempfile.TemporaryDirectory() as t:
            result=self.invoke(Path(t));b=Backend.last
            self.assertEqual(b.submits,1);self.assertEqual(result['status'],'STOPPED')
            self.assertEqual(b.restores,['restoration-preflight.bin','final-restoration.bin'])
            self.assertTrue(b.cleaned)
            rows=[json.loads(l) for l in (Path(t)/'campaign/ledger.jsonl').read_text().splitlines()]
            self.assertEqual(sum(r['kind']=='mutation_attempt' for r in rows),1)
    def test_deployment_failure_restores_without_submit(self):
        Backend.fail='deploy'
        with tempfile.TemporaryDirectory() as t:
            result=self.invoke(Path(t));b=Backend.last
            self.assertEqual(b.submits,0);self.assertEqual(b.restores[-1],'final-restoration.bin')
            self.assertTrue(b.cleaned);self.assertEqual(result['status'],'STOPPED')
    def test_case_failure_after_provision_stops_fixture_and_restores(self):
        class Success(Backend):
            calls=0
            def __init__(self,*args):
                super().__init__(*args);self.campaign=Path(args[3])
            def submit(self,*a):self.submits+=1
            def info(self):
                Success.calls+=1
                if Success.calls==1:return dict(device_id=run.DEVICE,revision='1'*12,phase12_fault_consumed=True,status={'boot_id':'after'})
                return dict(device_id=run.DEVICE,revision='2'*12,provisioning_source='provisioned',provisioning_generation='2',status={'boot_id':'new'})
            def deploy(self,role,*a):
                if role=='fault_1':return dict(info={'status':{'boot_id':'before'}})
                return dict(info=dict(device_id=run.DEVICE,revision='2'*12,provisioning_source='unprovisioned',provisioning_generation='1',local_suffix='0a9d89',status={'boot_id':'engineering'}))
            def snapshot(self,name):
                (self.campaign/name).write_bytes(('mock snapshot '+name).encode())
                if name=='engineering-profile-readback.bin':return dict(path=name,sha256='e'*64,inspection=dict(profile_source=1,profile_sequence=2,profile_payload='{}',bond_count=1,access_state=2,profile_healthy=True))
                return super().snapshot(name)
        actions=[];provisions=[]
        def fixture(action,args):
            actions.append(action)
            return dict(address='AA:BB:CC:DD:EE:FF',matching_names=1)
        def cases(context):raise TimeoutError('case uncertain')
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with patch.object(run,'safe_info'),patch.object(run,'sha',return_value='a'*64),patch.object(run,'transfer'),patch.object(run,'canonical_profile',return_value=bytearray(b'{}')),patch.object(run,'assess') as assessor:
                result=run.execute(dict(source_commit='1'*40),dict(source_commit='2'*40,candidates=[dict(role='engineering',uf2=dict(path='image'))]),root,root/'campaign','inspector',dict(tls={},console='console'),backend_factory=Success,fixture=fixture,provision=provisions.append,cases=cases,sleeper=lambda seconds:None)
            self.assertEqual(actions,['start_ap','discover_ble','stop'])
            self.assertEqual(len(provisions),1);self.assertEqual(provisions[0]['generation'],1)
            assessor.assert_called_once()
            self.assertEqual(assessor.call_args.args[3:5],(b'mock snapshot reset-before.bin',b'mock snapshot reset-after.bin'))
            self.assertEqual(Backend.last.submits,1)
            self.assertEqual(Backend.last.restores[-1],'final-restoration.bin')
            self.assertEqual(result['status'],'STOPPED');self.assertTrue(Backend.last.cleaned)
    def test_journal_failure_stops_fixture_and_restores(self):
        class Success(Backend):
            calls=0
            def __init__(self,*args):
                super().__init__(*args);self.campaign=Path(args[3])
            def submit(self,*a):self.submits+=1
            def info(self):
                Success.calls+=1
                if Success.calls==1:return dict(device_id=run.DEVICE,revision='1'*12,phase12_fault_consumed=True,status={'boot_id':'after'})
                return dict(device_id=run.DEVICE,revision='2'*12,provisioning_source='provisioned',provisioning_generation='2',status={'boot_id':'new'})
            def deploy(self,role,*a):
                if role=='fault_1':return dict(info={'status':{'boot_id':'before'}})
                return dict(info=dict(device_id=run.DEVICE,revision='2'*12,provisioning_source='unprovisioned',provisioning_generation='1',local_suffix='0a9d89',status={'boot_id':'engineering'}))
            def snapshot(self,name):
                (self.campaign/name).write_bytes(('mock snapshot '+name).encode())
                if name=='engineering-profile-readback.bin':return dict(path=name,sha256='e'*64,inspection=dict(profile_source=1,profile_sequence=2,profile_payload='{}',bond_count=1,access_state=2,profile_healthy=True))
                return super().snapshot(name)
        actions=[];provisions=[]
        def fixture(action,args):
            actions.append(action)
            return dict(address='AA:BB:CC:DD:EE:FF',matching_names=1)
        def cases(context):pass
        def journal(context):raise TimeoutError('one journal apply uncertain')
        accelerated=[]
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with patch.object(run,'safe_info'),patch.object(run,'sha',return_value='a'*64),patch.object(run,'transfer'),patch.object(run,'canonical_profile',return_value=bytearray(b'{}')),patch.object(run,'assess') as assessor:
                result=run.execute(dict(source_commit='1'*40),dict(source_commit='2'*40,candidates=[dict(role='engineering',uf2=dict(path='image'))]),root,root/'campaign','inspector',dict(tls={},console='console'),backend_factory=Success,fixture=fixture,provision=provisions.append,cases=cases,journal=journal,accelerated=accelerated.append,sleeper=lambda seconds:None)
            self.assertEqual(accelerated,[],'session teardown cannot precede station-dependent journal work')
            self.assertEqual(actions,['start_ap','discover_ble','stop'])
            self.assertEqual(len(provisions),1);self.assertEqual(provisions[0]['generation'],1)
            assessor.assert_called_once()
            self.assertEqual(assessor.call_args.args[3:5],(b'mock snapshot reset-before.bin',b'mock snapshot reset-after.bin'))
            self.assertEqual(Backend.last.submits,1)
            self.assertEqual(Backend.last.restores[-1],'final-restoration.bin')
            self.assertEqual(result['status'],'STOPPED');self.assertTrue(Backend.last.cleaned)
    def test_flash_status_failure_stops_later_cases_and_restores(self):
        class Success(Backend):
            calls=0
            def __init__(self,*args):
                super().__init__(*args);self.campaign=Path(args[3])
            def submit(self,*a):self.submits+=1
            def info(self):
                Success.calls+=1
                if Success.calls==1:return dict(device_id=run.DEVICE,revision='1'*12,phase12_fault_consumed=True,status={'boot_id':'after'})
                return dict(device_id=run.DEVICE,revision='2'*12,provisioning_source='provisioned',provisioning_generation='2',status={'boot_id':'new'})
            def deploy(self,role,*a):
                if role=='fault_1':return dict(info={'status':{'boot_id':'before'}})
                return dict(info=dict(device_id=run.DEVICE,revision='2'*12,provisioning_source='unprovisioned',provisioning_generation='1',local_suffix='0a9d89',status={'boot_id':'engineering'}))
            def snapshot(self,name):
                (self.campaign/name).write_bytes(('mock snapshot '+name).encode())
                if name=='engineering-profile-readback.bin':return dict(path=name,sha256='e'*64,inspection=dict(profile_source=1,profile_sequence=2,profile_payload='{}',bond_count=1,access_state=2,profile_healthy=True))
                return super().snapshot(name)
        actions=[];provisions=[]
        def fixture(action,args):
            actions.append(action)
            return dict(address='AA:BB:CC:DD:EE:FF',matching_names=1)
        def cases(context):pass
        def flash_status(context):raise TimeoutError('ordinary save outcome uncertain')
        later=[]
        def later_case(context):later.append(context)
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with patch.object(run,'safe_info'),patch.object(run,'sha',return_value='a'*64),patch.object(run,'transfer'),patch.object(run,'canonical_profile',return_value=bytearray(b'{}')),patch.object(run,'assess') as assessor:
                result=run.execute(dict(source_commit='1'*40),dict(source_commit='2'*40,candidates=[dict(role='engineering',uf2=dict(path='image'))]),root,root/'campaign','inspector',dict(tls={},console='console'),backend_factory=Success,fixture=fixture,provision=provisions.append,cases=cases,flash_status=flash_status,accelerated=later_case,journal=later_case,sleeper=lambda seconds:None)
            self.assertEqual(actions,['start_ap','discover_ble','stop'])
            self.assertEqual(later,[])
            self.assertEqual(len(provisions),1);self.assertEqual(provisions[0]['generation'],1)
            assessor.assert_called_once()
            self.assertEqual(assessor.call_args.args[3:5],(b'mock snapshot reset-before.bin',b'mock snapshot reset-after.bin'))
            self.assertEqual(Backend.last.submits,1)
            self.assertEqual(Backend.last.restores[-1],'final-restoration.bin')
            self.assertEqual(result['status'],'STOPPED');self.assertTrue(Backend.last.cleaned)
    def test_stage_preserves_exact_private_snapshot_and_hash(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'input.py';source.write_bytes(b'exact input')
            adapter=run.RemoteAdapters(root);adapter.backend=SimpleNamespace(remote='/remote')
            with patch.object(run,'transfer') as transfer,patch.object(run.subprocess,'run') as command:
                digest=adapter.stage(source,'input.py')
            self.assertEqual(digest,run.sha(source))
            self.assertEqual((root/'observer-input.py').read_bytes(),source.read_bytes())
            self.assertEqual((root/'observer-input.py').stat().st_mode&0o777,0o600)
            transfer.assert_called_once_with(adapter.backend,source,'input.py')
            self.assertEqual(command.call_args.args[0],['ssh','wspr5','chmod','600','/remote/input.py'])
    def test_accelerator_retains_profile_snapshot_before_image(self):
        class Accelerator(Backend):
            def snapshot(self,name):return dict(path=name,sha256='e'*64,inspection=dict(profile_source=1,profile_healthy=True))
            def deploy(self,role,saved,name):
                self.deployed=(role,saved['path'],name);return dict(info={'boot':'new'})
        b=Accelerator();role=dict(role='session_deadline',uf2=dict(path='fixture.uf2'))
        with patch.object(run,'transfer') as transfer:
            result=run.deploy_accelerated(dict(backend=b,preparation=dict(candidates=[role]),preparation_artifacts='/artifacts'))
        self.assertEqual(b.deployed,('session_deadline','before-session-fixture.bin','session-fixture-deployment.bin'))
        self.assertEqual(result['candidate'],role)
        transfer.assert_called_once_with(b,Path('/artifacts/fixture.uf2'),'session_deadline.uf2')
    def test_existing_campaign_cannot_resume_mutations(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'campaign').mkdir()
            with self.assertRaises(ValueError):self.invoke(root)

    def test_journal_return_requires_original_profile_and_restores_checkpoint(self):
        for retained in ('original A','unexpected C'):
            with tempfile.TemporaryDirectory() as t:
                root=Path(t);checkpoint=root/'journal-a-before.bin';checkpoint.write_bytes(b'exact prior flash')
                profile=root/'engineering-profile.json';profile.write_text('original A')
                backend=MagicMock();backend.inspect.return_value=dict(profile_source=1,profile_healthy=True,
                    profile_payload=retained,bond_count=1)
                context=dict(root=root,backend=backend,profile_path=profile)
                if retained=='unexpected C':
                    with self.assertRaisesRegex(ValueError,'exact pre-journal A'):run.return_journal_checkpoint(context)
                    backend.deploy.assert_not_called()
                else:
                    run.return_journal_checkpoint(context)
                    args=backend.deploy.call_args
                    self.assertEqual(args.args[0],'engineering');self.assertTrue(args.kwargs['restore'])
                    self.assertEqual(args.args[1]['path'],checkpoint.name)
                    self.assertEqual(args.args[1]['sha256'],run.sha(checkpoint))
                    self.assertEqual(args.args[2],'journal-a-return.bin')
                    helper=ast.parse((Path(__file__).resolve().parents[1]/'scripts/phase12_recovery_device.py').read_text())
                    main=next(n for n in helper.body if isinstance(n,ast.FunctionDef) and n.name=='main')
                    guard=next(n for n in main.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='name')
                    import re
                    exec(compile(ast.fix_missing_locations(ast.Module(body=[guard],type_ignores=[])),'actual-artifact-guard','exec'),dict(request=dict(image='engineering.uf2',backup=args.args[1]['path'],readback=args.args[2]),root=root,re=re,require=run.require))
class SessionSelectionTests(unittest.TestCase):
 def test_default_payload_unchanged_and_explicit_running(self):
  self.assertIsNone(run.session_selection('all'))
  self.assertEqual(run.session_payload({'bound':1},None),{'bound':1})
  choice=run.session_selection('sessions','running',True)
  self.assertEqual(run.session_payload({'bound':1},choice),dict(bound=1,cookie_grace_stages=['running'],cookie_grace_only=True))
 def test_actual_dispatch_capacity_branch_skips_only_explicitly(self):
  tree=ast.parse(Path(run.__file__).with_name('phase12_engineering_session_dispatch.py').read_text())
  branch=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=='not cookie_only')
  for cookie_only in (False,True):
   calls=[]
   ns=dict(cookie_only=cookie_only,run_device=lambda *args:calls.append(args),candidate={},manifest={},boot='boot',profile={'tls':{'hostname':'bound'}},root=Path('/private'),password='private',info=None,status=None,ap=None)
   exec(compile(ast.fix_missing_locations(ast.Module(body=[branch],type_ignores=[])),'actual-capacity-branch','exec'),ns)
   self.assertEqual(len(calls),0 if cookie_only else 1)
 def test_invalid_cli_before_manifest_or_backend(self):
  argv=['program']
  for name in ('manifest','artifact-root','preparation-manifest','preparation-artifact-root','campaign','inspector','credential-root'):argv+=['--'+name,'/not/read']
  for scope in ('all','composition','flash-status','time-jobs','network','journal','bond-revocation'):
   with patch.object(sys,'argv',argv+['--scope',scope,'--cookie-grace-stages','running']),patch.object(run,'read_json',side_effect=AssertionError('file access')):
    with self.assertRaises(ValueError):run.main()
 def test_actual_parent_durable_selection_before_setup_and_cleanup(self):
  choice=run.session_selection('sessions','running',True)
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'fresh'
   class Backend:
    remote='/private';roles={}
    def __init__(self,*args):pass
    def setup(self):
     self.selection=json.loads((root/'campaign-config.json').read_text())['session_selection']
     self.assertion=self.selection==choice
     if not self.assertion:raise AssertionError('metadata absent')
     raise TimeoutError('no mutation')
    def cleanup(self):pass
   result=run.execute({'source_commit':'a'*40},{'source_commit':'a'*40},Path(d),root,Path('none'),{},backend_factory=Backend,fixture=lambda *a:None,provision=lambda *a:None,cases=lambda *a:None,scope='sessions',session_choice=choice)
   self.assertEqual(result['session_selection'],choice)
   ledger=[json.loads(l) for l in (root/'ledger.jsonl').read_text().splitlines()]
   self.assertEqual(ledger[0]['payload']['session_selection'],choice)
   self.assertEqual(result['status'],'STOPPED')

class RadioComparisonTests(unittest.TestCase):
 def test_cli_wrong_scope_before_input_access(self):
   argv=['program']
   for name in ('manifest','artifact-root','preparation-manifest','preparation-artifact-root','campaign','inspector','credential-root'):argv+=['--'+name,'/not/read']
   with patch.object(sys,'argv',argv+['--scope','sessions','--fixture-roles','swapped']),patch.object(run,'read_json',side_effect=AssertionError('input')):
    with self.assertRaises(ValueError):run.main()

if __name__=='__main__':unittest.main()
