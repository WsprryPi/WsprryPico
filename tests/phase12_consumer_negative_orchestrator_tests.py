#!/usr/bin/env python3
import json
from pathlib import Path
import sys
import tempfile
import shutil
import subprocess
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_consumer_negative_orchestrator as run
class Backend:
    last=None;mutate=False
    def __init__(self,*a):Backend.last=self;self.root=Path(a[3]);self.remote='/remote';self.restores=[];self.deployments=[];self.cleaned=False
    def setup(self):return {}
    def snapshot(self,name):
        data=bytearray(4194304)
        if self.mutate and name.endswith('-after.bin'):data[-1]=1
        (self.root/name).write_bytes(data)
        return dict(path=name,sha256='a'*64,inspection={'effective_station':{}})
    def restore(self,baseline,name):self.restores.append(name);return dict(readback=name)
    def deploy(self,*a):self.deployments.append(a);return dict(info=self.info())
    def stable_restore(self,*a):return {'samples':5}
    def info(self):return dict(provisioning_source='consumer_preclock',provisioning_generation='7',status={'boot_id':'2'*32})
    def cleanup(self):self.cleaned=True
class Remote:
    retrieval_failure=False;fail=True;last=None
    def __init__(self,*a):Remote.last=self;self.calls=0;self.collected=False
    def stage(self,*a):return 'a'*64
    def invoke(self,*a,**kw):
        self.calls+=1
        if self.fail:raise TimeoutError('uncertain child')
        return dict(status='NEGATIVES_REVIEW_REQUIRED',cases=1,wtp_owner_verified=False,wtp_job_identity_verified=False)
    def collect(self,*a):
        self.collected=True
        if self.retrieval_failure:raise TimeoutError('partial retrieval')
class Tests(unittest.TestCase):
    def test_ordered_subset_validation(self):
        self.assertEqual(run.selected_cases(),tuple(run.CASES))
        self.assertEqual(run.selected_cases('CANCELLED,INTERRUPTED'),('CANCELLED','INTERRUPTED'))
        for value in ('', 'CANCELLED,CANCELLED', 'INTERRUPTED,CANCELLED', 'FOREIGN', 'CANCELLED, INTERRUPTED'):
            with self.assertRaises(ValueError):run.selected_cases(value)

    def setUp(self):Remote.fail=True;Remote.retrieval_failure=False;Backend.mutate=False
    def test_complete_staged_helpers_import_without_repository_fallback(self):
        scripts=Path(__file__).resolve().parents[1]/'scripts'
        with tempfile.TemporaryDirectory() as t:
            for name in run.STAGED_HELPERS:shutil.copyfile(scripts/name,Path(t)/name)
            result=subprocess.run([sys.executable,'-I','-c',
                'import sys; sys.path.insert(0,sys.argv[1]); import phase12_consumer_negative_dispatch',t],
                capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr.decode())
    def test_failure_or_partial_retrieval_always_restores_exact_backup(self):
        for failed_retrieval in (False,True):
            with self.subTest(retrieval=failed_retrieval),tempfile.TemporaryDirectory() as t:
                Remote.retrieval_failure=failed_retrieval
                with patch.object(run,'safe_info',side_effect=lambda info,*args:info):
                    result=run.execute(dict(source_commit='1'*40),t,Path(t)/'campaign','inspector',backend_factory=Backend,remote_factory=Remote)
                self.assertEqual(Remote.last.calls,1);self.assertTrue(Remote.last.collected)
                self.assertEqual(Backend.last.restores,['restoration-preflight.bin','final-restoration.bin']);self.assertTrue(Backend.last.cleaned)
                self.assertEqual(result['status'],'STOPPED');self.assertEqual(result['error']['type'],'TimeoutError')
                receipt=json.loads((Path(t)/'campaign/baseline-receipt.json').read_text());self.assertEqual(receipt['sha256'],'a'*64)
    def test_seven_separate_fresh_fixtures_and_reserved_failure_stops_next_case(self):
        for corrupt in (False,True):
            with self.subTest(corrupt=corrupt),tempfile.TemporaryDirectory() as t:
                Backend.mutate=corrupt;Remote.fail=False
                with patch.object(run,'safe_info',side_effect=lambda info,*args:info):
                    result=run.execute(dict(source_commit='1'*40),t,Path(t)/'campaign','inspector',backend_factory=Backend,remote_factory=Remote)
                self.assertEqual(Remote.last.calls,1 if corrupt else 7)
                self.assertEqual(len(Backend.last.deployments),Remote.last.calls)
                self.assertTrue(all(args[0]=='fault_8' for args in Backend.last.deployments))
                self.assertEqual(result['status'],'STOPPED' if corrupt else 'NEGATIVES_COMPLETE_REVIEW_REQUIRED')
                self.assertEqual(Backend.last.restores[-1],'final-restoration.bin');self.assertTrue(Backend.last.cleaned)
    def test_existing_campaign_refuses_repeated_run(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):run.execute({},t,t,'inspector')
    def test_late_child_result_cannot_qualify_but_still_restores(self):
        now=[0.];Remote.fail=False
        original=Remote.invoke
        def late(*args,**kwargs):
            result=original(*args,**kwargs);now[0]=1801.;return result
        with tempfile.TemporaryDirectory() as t,patch.object(run,'safe_info',side_effect=lambda info,*args:info),patch.object(run.time,'monotonic',side_effect=lambda:now[0]),patch.object(Remote,'invoke',late):
            result=run.execute(dict(source_commit='1'*40),t,Path(t)/'campaign','inspector',backend_factory=Backend,remote_factory=Remote)
            self.assertEqual(result['status'],'STOPPED');self.assertIn('deadline',result['error']['message'])
            self.assertEqual(Backend.last.restores[-1],'final-restoration.bin');self.assertTrue(Backend.last.cleaned)
if __name__=='__main__':unittest.main()
