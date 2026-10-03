#!/usr/bin/env python3
"""Backup barriers and failure restoration for the unattended parent."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import phase12_independent_orchestrator as r

class Backend:
    def __init__(self,*args):self.root=Path(args[3]);self.remote='/home/pi/phase12-recovery-'+'1'*32;self.restores=0;self.cleaned=False
    def setup(self):return {'revision':'a'*12}
    def snapshot(self,name):
        (self.root/name).write_bytes(b'backup')
        return {'sha256':r.sha(self.root/name)}
    def restore(self,baseline,name):
        self.restores+=1
        if self.restores==1:raise OSError('preflight failed before campaign')
        return {'readback':{'path':name,'sha256':'b'*64}}
    def stable_restore(self,*args):return {'samples':5}
    def cleanup(self):self.cleaned=True

class Tests(unittest.TestCase):
    def candidate(self,source):
        return dict(role='restore',fault_stage=0,session_deadline_fixture=False,target='WsprryPico',
            lan_mode='plain',gp14=False,revision=source[:12],uf2=dict(path='ordinary.uf2',sha256='c'*64),map=dict(path='ordinary.map'))
    def test_exercise_full_manifest_validation_and_source_binding(self):
        base=dict(source_commit='a'*40,candidates=[self.candidate('a'*40)])
        selected=dict(source_commit='b'*40,candidates=[self.candidate('b'*40)])
        with patch.object(r,'verify') as verify:
            actual=r.exercise_selection(base,'base',selected,'new')
            verify.assert_called_once_with(selected,'new');self.assertEqual(actual[0]['source_commit'],'b'*40)
            self.assertEqual(actual[3],'exercise.uf2')
            selected['candidates'][0]['revision']='a'*12
            with self.assertRaises(ValueError):r.exercise_selection(base,'base',selected,'new')
        with self.assertRaises(ValueError):r.exercise_selection(base,'base',selected,None)
    def test_exercise_deploy_failure_restores_original_standard(self):
        objects=[];transfers=[]
        class Standard(Backend):
            def __init__(self,*args):super().__init__(*args);self.manifest=args[1];self.roles={};objects.append(self)
            def restore(self,baseline,name):
                self.restores+=1;self.asserted_source=self.manifest['source_commit'];return {'readback':{'path':name,'sha256':'b'*64}}
            def info(self):return {}
            def deploy(self,role,baseline,name):
                self.exercise_role=role;raise OSError('exercise failed after backup')
        manifest=dict(source_commit='a'*40,candidates=[self.candidate('a'*40)])
        exercise=dict(source_commit='b'*40,candidates=[self.candidate('b'*40)])
        with tempfile.TemporaryDirectory() as d,patch.object(r,'Backend',Standard),patch.object(r,'verify'),patch.object(r.time,'sleep'),patch.object(r,'transfer',side_effect=lambda b,p,n:transfers.append(n)):
            result=r.execute(manifest,d,Path(d)/'campaign','unused',exercise_manifest=exercise,exercise_artifact_root=d)
            retained=json.loads((Path(d)/'campaign/campaign-config.json').read_text())
        self.assertEqual(result['status'],'STOPPED');self.assertEqual(objects[0].restores,2)
        self.assertEqual(objects[0].asserted_source,'a'*40);self.assertEqual(retained['source_commit'],'a'*40)
        self.assertEqual(objects[0].exercise_role,'exercise');self.assertEqual(transfers,['exercise.uf2'])
    def test_wait_new_source_actual_consumer_readiness(self):
        observed=dict(revision='b'*12,provisioning_source='consumer_preclock',provisioning_generation=5,access_generation=2,
            saved_consumer_profile={'station':{'callsign':'K1ABC'}},status={'boot_id':'new','clock_state':'unsynchronized'},
            network={'link_status':3,'ipv4':'192.168.1.53'},lan_wtp_mode='plain')
        class Current:
            calls=0
            def info(self):
                self.calls+=1
                value=json.loads(json.dumps(observed))
                if self.calls>1:value['status']['clock_state']='synchronized'
                return value
        now=[0];backend=Current()
        with patch.object(r,'safe_info',lambda info,revision,*args:info if info['revision']==revision else (_ for _ in ()).throw(ValueError('source mismatch'))):
            value=r.wait_exercise_ready(backend,{'inspection':dict(profile_sequence=5,access_sequence=2,effective_station={'callsign':'K1ABC'})},'b'*40,
                clock=lambda:now[0],sleeper=lambda duration:now.__setitem__(0,now[0]+duration))
        self.assertEqual(backend.calls,6);self.assertEqual(value['revision'],'b'*12)
    def test_child_close_error_does_not_skip_wait(self):
        child=Mock();child.stdin.close.side_effect=BrokenPipeError('closed pipe')
        errors=r.shutdown_child(child)
        self.assertEqual(errors[0]['type'],'BrokenPipeError');child.wait.assert_called_once_with(timeout=10)
    def test_child_second_timeout_is_guarded_and_killed(self):
        child=Mock();child.wait.side_effect=[r.subprocess.TimeoutExpired('ssh',10),
            r.subprocess.TimeoutExpired('ssh',10),0]
        errors=r.shutdown_child(child)
        self.assertEqual(len(errors),2);child.terminate.assert_called_once();child.kill.assert_called_once()
    def test_failed_child_shutdown_still_restores_and_records_result(self):
        with patch.object(r,'shutdown_child',return_value=[dict(type='TimeoutExpired',message='shutdown failed')]):
            value,rows=self.run_case(Backend)
        self.assertEqual(value['status'],'STOPPED')
        self.assertEqual(value['restoration']['stability']['samples'],5)
        self.assertTrue(any(x['kind']=='child_shutdown_failed' for x in rows))
        self.assertTrue(any(x['kind']=='final_restoration_pass' for x in rows))
    def run_case(self,factory):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(r,'Backend',factory),patch.object(r.time,'sleep'):
                value=r.execute({'source_commit':'a'*40},d,Path(d)/'campaign','unused')
                rows=[json.loads(x) for x in (Path(d)/'campaign/ledger.jsonl').read_text().splitlines()]
                return value,rows
    def test_backup_failure_prevents_all_restore_writes(self):
        objects=[]
        def factory(*args):
            b=Backend(*args);objects.append(b)
            def fail(_):raise OSError('backup lost')
            b.snapshot=fail;return b
        value,rows=self.run_case(factory)
        self.assertEqual(value['status'],'STOPPED');self.assertIsNone(value['restoration'])
        self.assertEqual(objects[0].restores,0);self.assertTrue(objects[0].cleaned)
        self.assertFalse(any(x['kind']=='consumer_capture_started' for x in rows))
    def test_preflight_failure_still_restores_verified_backup(self):
        objects=[]
        def factory(*args):b=Backend(*args);objects.append(b);return b
        value,rows=self.run_case(factory)
        self.assertEqual(value['status'],'STOPPED');self.assertEqual(objects[0].restores,2)
        self.assertEqual(value['restoration']['stability']['samples'],5)
        self.assertEqual(sum(x['kind']=='final_restoration_pass' for x in rows),1)
        self.assertTrue(objects[0].cleaned)
    def test_failed_restoration_cannot_report_completion(self):
        def factory(*args):
            b=Backend(*args)
            def fail(*args):raise OSError('restoration unavailable')
            b.restore=fail;return b
        value,rows=self.run_case(factory)
        self.assertEqual(value['status'],'STOPPED');self.assertIn('error',value['restoration'])
        self.assertFalse(value['physical_acceptance'])
    def test_recovery_refuses_changed_backup_before_device_access(self):
        import hashlib
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);manifest={'source_commit':'a'*40}
            binding=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            r.private_write(root/'campaign-config.json',dict(campaign_id='1'*32,source_commit='a'*40,manifest_sha256=binding))
            r.private_write(root/'baseline-receipt.json',dict(sha256='f'*64,manifest_sha256=binding))
            (root/'baseline.bin').write_bytes(b'bad')
            with patch.object(r,'Backend') as adapter:
                with self.assertRaisesRegex(ValueError,'backup'):r.recover_only(manifest,d,root,'unused')
                adapter.assert_not_called()

    def test_wrong_initial_revision_prevents_rom_and_flash(self):
        objects=[]
        def factory(*args):
            b=Backend(*args);objects.append(b);b.setup=lambda:{'revision':'f'*12};return b
        value,rows=self.run_case(factory)
        self.assertEqual(value['status'],'STOPPED');self.assertEqual(objects[0].restores,0)

if __name__=='__main__':unittest.main()
