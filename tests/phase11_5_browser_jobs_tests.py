#!/usr/bin/env python3
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_browser_jobs import checked_reply,finite_start,admit_snapshot,main
from audit_phase11_5_a3 import dma_coverage
from phase11_5_pilot_tests import packet
import phase11_5_a3 as coordinator


class BrowserJobsTests(unittest.TestCase):
    def test_prerequisite_names_do_not_replace_the_new_case(self):
        class ReachedAdmission(Exception):pass
        for family in ('A3','F1'):
            with self.subTest(family=family),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);(root/'packet.json').write_text('{}')
                manifest=dict(family=family,case=family.lower()+'-physical-reviewed',
                    lifecycle_packet_sha256=coordinator.sha(root/'packet.json'),helper_sha256={},a2_result_sha256={})
                for kind in ('inhibited','physical'):
                    name='a2-'+kind+'-browser-priority'
                    result=dict(status='CAPTURED_REQUIRES_FINAL_REVIEW',intervals={
                        'quiet-before':{},'controller':{},'nominal':{},'quiet-after':dict(boot='a'*32)})
                    p=root/(name+'-family-result.json');p.write_text(json.dumps(result))
                    manifest['a2_result_sha256'][kind]=coordinator.sha(p)
                    (root/(name+'-packet.json')).write_text(json.dumps(dict(
                        source='8fb3894253ef45adc3aad28f25a684168487490f',
                        clock_hz=138000000 if kind=='physical' else 150000000)))
                if family=='F1':
                    prior=root/'a3-physical';prior.mkdir();(prior/'jobs.json').write_text('{}')
                    (prior/'audit.json').write_text(json.dumps(dict(status='CAPTURED_REQUIRES_FINAL_REVIEW',
                        packet_sha256=coordinator.sha(prior/'jobs.json'),usb=dict(boot='a'*32,terminal_records=[]))))
                    manifest['a3_result_sha256']=coordinator.sha(prior/'audit.json')
                p=root/'manifest.json';p.write_text(json.dumps(manifest));labels=[]
                def current(label):labels.append(label);raise ReachedAdmission()
                device=SimpleNamespace(state=dict(kind='physical',pending=None,boot='a'*32,
                    deadline_monotonic_ns=10**30),verify_helpers=lambda:None,check_current=current)
                with patch.object(coordinator,'DeviceFixture',return_value=device), \
                     patch.object(coordinator,'Fixture',return_value=SimpleNamespace(verify=lambda:None)), \
                     patch.object(sys,'platform','linux'),patch.object(coordinator.os,'geteuid',return_value=0), \
                     patch.object(coordinator.os,'umask'),patch.object(sys,'argv',['coordinator','--root',str(root),
                         '--manifest',str(p),'--family',family,'--attempt','reviewed','--run']):
                    with self.assertRaises(ReachedAdmission):coordinator.main()
                self.assertEqual(labels,[family.lower()+'-physical-reviewed-admission'])

    def test_inflight_read_is_not_a_stale_completed_snapshot(self):
        old=dict(packet_sha256='a'*64,pid=42,pid_start_ticks='123',monotonic_ns=112630589628633)
        pending={**old,'monotonic_ns':112631498791352,'value':{'hex':b'INFO\n'.hex()}}
        now=112632597786459
        admit_snapshot(old,now,2_000_000_000,'a'*64,pending)
        # ARM still requires a fresh completed INFO, with no in-flight exception.
        with self.assertRaises(ValueError):admit_snapshot(old,now,2_000_000_000,'a'*64)
        for changed in ({**pending,'pid':43},{**pending,'monotonic_ns':old['monotonic_ns']},
                        {**pending,'value':{'hex':b'BOOTSEL\n'.hex()}}):
            with self.assertRaises(ValueError):admit_snapshot(old,now,2_000_000_000,'a'*64,changed)
        with self.assertRaises(ValueError):
            admit_snapshot(old,pending['monotonic_ns']+5_000_000_001,2_000_000_000,'a'*64,pending)

    def test_late_arm_stops_before_emission_and_preserves_release_allowance(self):
        clock=dict(clock_state='synchronized',uncertainty_ns='500000000',utc_now_ns='100000000001')
        self.assertEqual(finite_start(clock,145_000_000_000,180_000_000_000,10_000_000_000),
                         110_000_001_000)
        for now,clock_value in [(145_000_000_001,clock),
                (0,{**clock,'clock_state':'holdover'}),(0,{**clock,'uncertainty_ns':'500000001'})]:
            with self.subTest(now=now,clock=clock_value),self.assertRaises(ValueError):
                finite_start(clock_value,now,180_000_000_000,10_000_000_000)

    def test_completed_labels_do_not_replace_full_job_hardware_coverage(self):
        before=dict(dma_irqs=20,tail_irqs=2,alarm_irqs=2,running_successor_links=14)
        # 1,380,000,000 samples require 2,633 data blocks per ten-second job.
        delta=dict(dma_irqs=7902,tail_irqs=3,alarm_irqs=3,running_successor_links=7896)
        after={key:before[key]+value for key,value in delta.items()}
        self.assertEqual(dma_coverage(packet(),before,after),delta)
        for key in after:
            for missed in (-1,1):
                with self.subTest(key=key,missed=missed),self.assertRaises(ValueError):
                    dma_coverage(packet(),before,{**after,key:after[key]+missed})

    def test_claim_response_requires_matching_owner_and_request(self):
        request=dict(session_id='a'*32,request_id='b'*32,operation='CLAIM',body=dict(owner_id='c'*32,lease_ms=60000))
        reply=dict(ok=True,request_id='b'*32,result=dict(owner_id='c'*32,
                   granted_lease_ms=60000,expires_monotonic_ns='123456789'))
        checked_reply(request,200,json.dumps(reply).encode())
        checked_reply({**request,'operation':'RENEW'},200,json.dumps(reply).encode())
        for field,value in [('request_id','d'*32),('ok',False),('extra',True)]:
            bad=dict(reply,**{field:value})
            with self.subTest(field=field),self.assertRaises(ValueError):
                checked_reply(request,200,json.dumps(bad).encode())
        bad=copy.deepcopy(reply);bad['result']['owner_id']='d'*32
        with self.assertRaises(ValueError):checked_reply(request,200,json.dumps(bad).encode())
        with self.assertRaises(ValueError):
            checked_reply({**request,'operation':'RENEW'},200,json.dumps(bad).encode())
        bad=copy.deepcopy(reply);bad['result']['granted_lease_ms']=5000
        with self.assertRaises(ValueError):checked_reply(request,200,json.dumps(bad).encode())
        with self.assertRaises(ValueError):checked_reply(request,409,json.dumps(reply).encode())

    def test_no_run_has_no_device_or_file_access(self):
        with patch.object(sys,'argv',['actor','--root','/absent']), \
             patch.object(Path,'resolve',side_effect=AssertionError('file accessed')):
            main()


if __name__=='__main__':unittest.main()
