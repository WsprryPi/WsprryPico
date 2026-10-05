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
class StagingPreflightTests(unittest.TestCase):
    def inputs(self,root,scope='all'):
        repository=root/'source';module=repository/'scripts/phase12_engineering_orchestrator.py'
        module.parent.mkdir(parents=True);module.write_bytes(b'# private test source\n')
        manifest=root/'preparation.json';manifest.write_text(json.dumps({'source_commit':'a'*40}))
        recovery=root/'recovery.json';recovery.write_text(json.dumps({'source_commit':'a'*40}))
        credentials=root/'credentials'
        with patch.object(run,'__file__',str(module)):
            for source in run.staging_inputs(scope,manifest,credentials):
                source.parent.mkdir(parents=True,exist_ok=True)
                if not source.exists():source.write_bytes(b'private test input\n')
        (credentials/'ca/server/deployment.json').write_text(json.dumps({'certificate_sha256':run.hashlib.sha256(b'der').hexdigest()}))
        native=root/'native';native.write_bytes(b'private test executable')
        argv=['program','--run','--scope',scope,'--native',str(native)]
        values=dict(manifest=recovery,artifact_root=root,preparation_manifest=manifest,
            preparation_artifact_root=root,campaign=root/'campaign',inspector=root/'inspector',credential_root=credentials)
        for name,value in values.items():argv+=['--'+name.replace('_','-'),str(value)]
        return module,manifest,credentials,argv

    def assert_refused_before_board(self,root,scope,relative,invalid='missing'):
        module,manifest,credentials,argv=self.inputs(root,scope)
        source=(credentials/relative[12:]) if relative.startswith('credentials/') else module.parents[1]/relative
        source.unlink()
        if invalid=='empty':source.write_bytes(b'')
        if invalid=='directory':source.mkdir()
        if invalid=='symlink':
            original=root/'original';original.write_bytes(b'private original');source.symlink_to(original)
        with patch.object(run,'__file__',str(module)),patch.object(sys,'argv',argv),patch.object(run,'verify'), \
             patch.object(run,'Backend') as backend,patch.object(run,'RemoteAdapters') as remote, \
             patch.object(run,'execute') as execute,patch.object(run,'credential_config') as config, \
             patch.object(run.subprocess,'run') as process,patch.object(run.subprocess,'Popen') as child:
            with self.assertRaisesRegex(ValueError,'scope staging input'):run.main()
            backend.assert_not_called();remote.assert_not_called();execute.assert_not_called()
            config.assert_not_called();process.assert_not_called();child.assert_not_called()
        self.assertFalse((root/'campaign').exists())

    def test_actual_time_jobs_schema_omission_stops_before_backend_or_provision(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assert_refused_before_board(Path(directory),'time-jobs','docs/protocol/wtp-1.schema.json')

    def test_missing_inputs_for_every_real_stage_precede_board_actions(self):
        cases=(('composition','docs/development/phase12-composition-engineering-plan-template.json'),
            ('application','credentials/contender/client.key'),
            ('time-jobs','scripts/phase12_engineering_time_jobs.py'),
            ('network','scripts/phase12_engineering_network_dispatch.py'),
            ('sessions','scripts/phase12_engineering_cookie_grace.py'),
            ('flash-status','scripts/phase12_engineering_flash_status_dispatch.py'),
            ('journal','scripts/phase12_engineering_journal_dispatch.py'),
            ('journal','scripts/network_certificates.py'),
            ('journal-stimuli','scripts/phase12_engineering_journal_stimuli.py'),
            ('journal-stimuli','docs/protocol/wtp-1.schema.json'),
            ('bond-revocation','scripts/phase12_engineering_bond_refusal_dispatch.py'),
            ('all','scripts/phase12_engineering_fixture.py'),
            ('all','scripts/phase12_engineering_setup.py'),
            ('all','scripts/capacity_pending.py'),
            ('all','credentials/owner/client.crt'))
        for scope,source in cases:
            with self.subTest(scope=scope,source=source),tempfile.TemporaryDirectory() as directory:
                self.assert_refused_before_board(Path(directory),scope,source)

    def test_empty_directory_and_symlink_are_not_staging_inputs(self):
        for invalid in ('empty','directory','symlink'):
            with self.subTest(invalid=invalid),tempfile.TemporaryDirectory() as directory:
                self.assert_refused_before_board(Path(directory),'time-jobs','docs/protocol/wtp-1.schema.json',invalid)

    def test_common_callback_consumes_the_preflight_checked_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);module,manifest,credentials,argv=self.inputs(root,'bond-revocation')
            admitted=[];staged=[];adapter=MagicMock();adapter.backend=SimpleNamespace(remote='/private/no-access')
            def stage(source,name):
                source=Path(source);self.assertIn(source,admitted);staged.append((source,name));return run.sha(source)
            adapter.stage.side_effect=stage
            def execute(*args,**kwargs):
                admitted.extend(run.staging_inputs('bond-revocation',manifest,credentials))
                campaign=root/'campaign';campaign.mkdir()
                result=kwargs['cases']({'root':campaign})
                self.assertEqual(result['status'],'COMMON_INPUTS_STAGED')
                return dict(status='PASS',restoration={'samples':5})
            with patch.object(run,'__file__',str(module)),patch.object(sys,'argv',argv),patch.object(run,'verify'), \
                 patch.object(run,'credential_config',return_value={'tls':{}}),patch.object(run,'canonical_profile'), \
                 patch.object(run.subprocess,'check_output',return_value=b'der'),patch.object(run.signal,'signal'), \
                 patch.object(run,'RemoteAdapters',return_value=adapter),patch.object(run,'execute',side_effect=execute), \
                 patch.object(run.subprocess,'run') as process,patch('builtins.print'):
                run.main()
            self.assertIn((module.parents[1]/'docs/protocol/wtp-1.schema.json','docs/protocol/wtp-1.schema.json'),staged)
            self.assertIn((credentials/'owner/client.key','owner-client.key'),staged)
            inputs=json.loads((root/'campaign/dispatch-inputs.json').read_text())
            self.assertEqual(inputs['schema'],run.sha(module.parents[1]/'docs/protocol/wtp-1.schema.json'))
            self.assertEqual(set(inputs),{name for _,name in staged}-{'docs/protocol/wtp-1.schema.json'}|{'schema'})
            process.assert_called_once()
            self.assertEqual(process.call_args.args[0][0],'ssh') # Only a mocked schema-directory command.

    def test_journal_stimuli_actual_callback_creates_private_credentials_in_fresh_source(self):
        import phase12_engineering_journal as journal
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);module,manifest,credentials,argv=self.inputs(root,'journal-stimuli')
            repository=module.parents[1]
            self.assertFalse((repository/'config').exists())
            with patch.object(run,'__file__',str(module)):
                admitted=set(run.staging_inputs('journal-stimuli',manifest,credentials))
            generated=set();staged=[];adapter=MagicMock()
            backend=SimpleNamespace(remote='/private/no-access',roles={},setup=MagicMock(return_value={}))
            adapter.backend=backend
            def stage(source,name):
                source=Path(source);self.assertIn(source,admitted|generated)
                self.assertTrue(source.is_file());staged.append((source,name));return run.sha(source)
            adapter.stage.side_effect=stage
            def prepare(private_root,baseline,create):
                self.assertEqual(baseline,b'private retained A profile')
                self.assertTrue(private_root.is_dir())
                self.assertEqual(private_root.stat().st_mode&0o777,0o700)
                self.assertEqual(private_root.parent,repository/'config/local')
                self.assertEqual(private_root.parent.stat().st_mode&0o777,0o700)
                principals={}
                for role in ('B','C'):
                    principal={}
                    for key in ('profile_path','ca','cert','key'):
                        path=private_root/(role+'-'+key);path.write_bytes(b'private generated test input')
                        generated.add(path);principal[key]=str(path)
                    principals[role]=principal
                return principals
            def tranche(context,stage_image,apply,probe,write,**options):
                self.assertEqual(options['selection'],'stimuli')
                self.assertIs(options['stage_seed'],adapter.stage)
                self.assertEqual(set(context['principal_hashes']),{'A','B','C'})
                self.assertEqual(context['hostname'],'private.test')
                self.assertIn((module.with_name('phase12_engineering_journal_stimuli.py'),
                               'phase12_engineering_journal_stimuli.py'),staged)
                return dict(status='ENGINEERING_JOURNAL_STIMULI_REVIEW_REQUIRED')
            def execute(*args,**kwargs):
                self.assertEqual(kwargs['scope'],'journal-stimuli')
                for key in ('accelerated','flash_status','bond_revocation'):self.assertIsNone(kwargs[key])
                campaign=root/'campaign';campaign.mkdir()
                profile=campaign/'engineering-profile.json';profile.write_bytes(b'private retained A profile')
                kwargs['backend_factory']().setup()
                kwargs['journal'](dict(root=campaign,backend=backend,profile_path=profile))
                return dict(status='PREPARED_CASES_REVIEW_REQUIRED',restoration={'samples':5})
            with patch.object(run,'__file__',str(module)),patch.object(sys,'argv',argv),patch.object(run,'verify'), \
                 patch.object(run,'credential_config',return_value={'tls':{'hostname':'private.test'}}), \
                 patch.object(run,'canonical_profile'),patch.object(run.subprocess,'check_output',return_value=b'der'), \
                 patch.object(run.signal,'signal'),patch.object(run,'Backend',return_value=backend), \
                 patch.object(run,'RemoteAdapters',return_value=adapter),patch.object(run,'execute',side_effect=execute), \
                 patch.object(journal,'prepare',side_effect=prepare),patch.object(journal,'tranche',side_effect=tranche), \
                 patch.object(run,'return_journal_checkpoint') as checkpoint, \
                 patch.object(run.subprocess,'run') as process,patch.object(run.subprocess,'Popen') as child,patch('builtins.print'):
                run.main()
            self.assertEqual(checkpoint.call_count,1)
            self.assertEqual(json.loads((root/'campaign/journal-result.json').read_text())['status'],
                             'ENGINEERING_JOURNAL_STIMULI_REVIEW_REQUIRED')
            self.assertEqual(sum(name=='phase12_engineering_journal_stimuli.py' for _,name in staged),2)
            self.assertEqual(set(name for _,name in staged if name.startswith('journal-')),
                             {'journal-'+role+'-'+key+('.key' if key=='key' else '.crt')
                              for role in ('A','B','C') for key in ('ca','cert','key')})
            process.assert_not_called();child.assert_not_called()

    def test_all_scope_checks_union_without_requiring_other_scopes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);module,manifest,credentials,_=self.inputs(root,'composition')
            with patch.object(run,'__file__',str(module)):
                run.preflight_staging('composition',manifest,credentials)
                with self.assertRaisesRegex(ValueError,'phase12_engineering_time_jobs'):run.preflight_staging('time-jobs',manifest,credentials)
                with self.assertRaisesRegex(ValueError,'phase12_engineering_time_jobs'):run.preflight_staging('all',manifest,credentials)

    def test_recovery_only_does_not_require_missing_case_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);module,_,_,argv=self.inputs(root,'time-jobs')
            (module.parents[1]/'docs/protocol/wtp-1.schema.json').unlink()
            campaign=root/'campaign';campaign.mkdir();(campaign/'campaign-config.json').write_text(json.dumps({'campaign_id':'b'*32}))
            adapter=MagicMock()
            with patch.object(run,'__file__',str(module)),patch.object(sys,'argv',argv+['--recover-only']), \
                 patch.object(run,'verify'),patch.object(run,'RemoteAdapters',return_value=adapter), \
                 patch.object(run,'recover_only',return_value={'status':'RESTORED'}) as recover, \
                 patch.object(run,'preflight_staging',side_effect=AssertionError('must allow restoration')),patch('builtins.print'):
                run.main()
            recover.assert_called_once();adapter.fixture.assert_called_once_with('stop',{})

class JournalSelectionTests(unittest.TestCase):
 def test_optional_stimuli_dependency_and_exact_output_names(self):
  new=Path(run.__file__).with_name('phase12_engineering_journal_stimuli.py')
  for scope in ('all','journal','journal-stimuli'):
   paths=run.staging_inputs(scope,'/private/manifest','/private/credentials')
   self.assertEqual(new in paths,scope=='journal-stimuli')
  self.assertEqual(run.journal_outputs(dict(stage=0,action='stale_arm')),())
  self.assertEqual(run.journal_outputs(dict(stage=0,action='stale_suspend')),())
  self.assertEqual(run.journal_outputs(dict(stage=0,action='stale_a_ready')),('journal-stale_a_ready-wire.jsonl',))
  self.assertEqual(run.journal_outputs(dict(stage=0,action='stale_prepare')),('journal-stale_prepare-wire.jsonl',))
  self.assertEqual(run.journal_outputs(dict(stage=0,action='observe_checkpoint',journal_selection='stimuli')),('journal-stale-new-wire.jsonl',))
  self.assertEqual(run.journal_outputs(dict(stage=8,action='observe_checkpoint',journal_selection='stimuli')),())
  self.assertEqual(run.journal_outputs(dict(stage=10)),('journal-apply-10-wire.jsonl','journal-apply-10-result.json'))
  self.assertEqual(run.journal_outputs(dict(stage=0,journal_stage=10,action='tls')),('journal-tls-10-wire.jsonl','journal-tls-10-result.json'))
  self.assertEqual(run.journal_outputs(dict(stage=0,action='observe_fault')),('journal-observe_fault-wire.jsonl','journal-corrupt-result.json'))
  with self.assertRaises(ValueError):run.journal_outputs(dict(stage=0,action='replay'))

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
 def test_skip_accepted_time_cases_wrong_scope_before_input_access(self):
   argv=['program']
   for name in ('manifest','artifact-root','preparation-manifest','preparation-artifact-root','campaign','inspector','credential-root'):argv+=['--'+name,'/not/read']
   for scope in ('time-jobs','network','journal','flash-status','sessions','bond-revocation'):
    with self.subTest(scope=scope),patch.object(sys,'argv',argv+['--scope',scope,'--skip-accepted-time-cases']),patch.object(run,'read_json',side_effect=AssertionError('input')):
     with self.assertRaises(ValueError):run.main()
 def test_cli_wrong_scope_before_input_access(self):
   argv=['program']
   for name in ('manifest','artifact-root','preparation-manifest','preparation-artifact-root','campaign','inspector','credential-root'):argv+=['--'+name,'/not/read']
   with patch.object(sys,'argv',argv+['--scope','sessions','--fixture-roles','swapped']),patch.object(run,'read_json',side_effect=AssertionError('input')):
    with self.assertRaises(ValueError):run.main()

class BoundParentTests(unittest.TestCase):
    def test_actual_fresh_USB_bookends_bracket_discovery_and_refuse_drift(self):
        import inspect,textwrap
        source=inspect.getsource(run.execute);begin=source.index("        generation=counter(info['provisioning_generation']");end=source.index('        clearance_path=',begin)
        block=compile(textwrap.dedent(source[begin:end]),'<actual execute discovery block>','exec')
        info=dict(device_id=run.DEVICE,provisioning_source='unprovisioned',provisioning_generation=1,status=dict(boot_id='2'*32))
        for drift in (False,True):
            actions=[];fresh=dict(info,status=dict(boot_id='3'*32 if drift else '2'*32))
            def read():actions.append('INFO');return fresh
            def fixture(action,args):actions.append(action);self.assertEqual(args['expected_address'],'88:A2:9E:0A:9D:8A');return dict(address=args['expected_address'],matching_bound_addresses=1,selection_mode='bound_public_address',fresh_advertisement_proven=False)
            namespace=dict(info=info,backend=SimpleNamespace(info=read),bound_ble_address='88:A2:9E:0A:9D:8A',root=Path('/inert'),counter=run.counter,private_write=MagicMock(),safe_info=MagicMock(),preparation=dict(source_commit='1'*40),require=run.require,DEVICE=run.DEVICE,fixture=fixture)
            if drift:
                with self.assertRaisesRegex(ValueError,'before discovery'):exec(block,namespace)
                self.assertEqual(actions,['INFO'])
            else:
                exec(block,namespace);self.assertEqual(actions,['INFO','discover_ble','INFO']);self.assertEqual(namespace['private_write'].call_count,3)
    def test_other_board_bound_address_refuses_before_any_backend_or_campaign(self):
        with tempfile.TemporaryDirectory() as d,patch.object(run,'Backend',side_effect=AssertionError('no backend')):
            target=Path(d)/'unstarted'
            with self.assertRaisesRegex(ValueError,'explicit verified B address only'):
                run.execute({}, {},Path(d),target,Path(d)/'native',{},fixture=lambda *a:None,provision=lambda *a:None,cases=lambda *a:None,bound_ble_address='88:A2:9E:0A:60:E0')
            self.assertFalse(target.exists())

if __name__=='__main__':unittest.main()
