#!/usr/bin/env python3
"""Synthetic resource records exercise fail-closure, never device qualification."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase12_composition_audit_tests import fixture
from phase12_composition_capture_tests import info
import phase12_resource_capture_review as review


def records(plan,mutate=lambda index,value:None):
    result=[dict(kind='start',plan=plan,physical_acceptance=False)]
    for index in range(241):
        value=info(plan);value['status'].pop('owner_id');value['status'].pop('job_id')
        value['status'].update(storage_healthy=True,monotonic_now_ns=str((1000+index*30)*1_000_000_000))
        value.update(heap_allocated_bytes=1000,core0_stack_used_bytes=1000,fault_allocation_recorded=False,
                     softap_retained_sessions=0)
        mutate(index,value)
        raw=json.dumps(value).encode()
        result.append(dict(kind='INFO',transport_raw=True,elapsed_start_s=index*30,
            elapsed_end_s=index*30+.02,raw_info_hex=raw.hex(),raw_info_sha256=hashlib.sha256(raw).hexdigest(),
            info=value,decoded_info_sha256=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()))
    result.append(dict(kind='complete',status='CAPTURE_COMPLETE_REVIEW_REQUIRED',physical_acceptance=False))
    return result


class Tests(unittest.TestCase):
    def execute(self,mutate=lambda index,value:None,alter=lambda rows:None):
        plan,_=fixture();plan['heap_return_tolerance_bytes']=4096
        rows=records(plan,mutate);alter(rows)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'capture.jsonl'
            path.write_text('\n'.join(json.dumps(row) for row in rows)+'\n')
            return review.review(plan,path)
    def test_fresh_complete_soak_without_authority_or_pressure_claim(self):
        result=self.execute()
        self.assertEqual(result['samples'],241)
        self.assertTrue(result['target_freshness_brackets_verified'])
        for key in ('final_owner_verified','final_job_identity_verified','pressure_qualified',
                    'full_composition_qualified','physical_acceptance'):self.assertFalse(result[key])
    def test_stale_reboot_allocation_heap_and_pool_failures(self):
        def stale(index,v):
            if index==100:v['status']['monotonic_now_ns']=str((1000+99*30)*1_000_000_000)
        def reboot(index,v):
            if index==100:v['status']['boot_id']='f'*32
        def allocation(index,v):
            if index==100:v['allocator_failures']='1'
        def heap(index,v):
            if index==240:v['heap_allocated_bytes']=5097
        def pool(index,v):
            if index==240:v['network']['memory']['tcp_pcbs'].update(used=1,peak=1)
        def btstack(index,v):
            if index==240:v['btstack_pools']['hci_connections'].update(used=1,peak=1)
        for mutate in (stale,reboot,allocation,heap,pool,btstack):
            with self.subTest(mutation=mutate.__name__),self.assertRaises(ValueError):self.execute(mutate)
    def test_raw_binding_partial_capture_and_gaps(self):
        def digest(rows):rows[100]['raw_info_sha256']='0'*64
        def decoded(rows):rows[100]['decoded_info_sha256']='0'*64
        def partial(rows):rows.pop()
        def gap(rows):rows[100]['elapsed_start_s']+=20;rows[100]['elapsed_end_s']+=20
        for alter in (digest,decoded,partial,gap):
            with self.subTest(mutation=alter.__name__),self.assertRaises(ValueError):self.execute(alter=alter)
    def test_positive_target_progress_outside_bracket_is_stale(self):
        def mutate(index,v):
            if index>=100:v['status']['monotonic_now_ns']=str(int(v['status']['monotonic_now_ns'])-1_000_000_000)
        with self.assertRaises(ValueError):self.execute(mutate)


if __name__=='__main__':unittest.main()
