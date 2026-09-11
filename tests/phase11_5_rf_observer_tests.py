#!/usr/bin/env python3
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_device_management_tests import baseline
from phase11_5_rf_observer import validate_info,validate_status,validate_event


class RFObserverTests(unittest.TestCase):
    def test_foreign_job_and_fault_events_are_rejected(self):
        packet=dict(owner_id='b'*32,jobs=[dict(job_id='c'*32)])
        value=dict(boot_id='a'*32,event='JOB_STATE',body=dict(job_id='c'*32,state='complete',output_active=False))
        validate_event(value,'a'*32,packet)
        for body in (dict(value['body'],job_id='d'*32),dict(value['body'],state='failed'),
                     dict(value['body'],output_active=True),dict(value['body'],error={})):
            with self.assertRaises(ValueError):validate_event(dict(value,body=body),'a'*32,packet)
        with self.assertRaises(ValueError):validate_event(dict(value,event='DEVICE_FAULT'),'a'*32,packet)
    def fixture(self):
        value=baseline();value['info'].update(ok=True,heap_capacity_bytes=218408,
            allocator_peak_bytes=42640,allocator_failures='0',tls_allocation_failures=0,
            refill_full_predecessor=dict(total_words=16384,remaining_words=4096,observations=1),
            refill_short_predecessor=None,running_successor_links=1,refill_irq_pairs=1,
            rf_max_service_gap_ns='2849391')
        return value
    def test_exact_deadline_and_reserve_boundaries(self):
        old=self.fixture();validate_info(old['info'],old)
        for key,bad in [('rf_max_service_gap_ns','2849392'),('system_clock_hz',150000000),
                        ('core1_stack_fault_status',1),('allocator_peak_bytes',185641),
                        ('refill_irq_pairs',0)]:
            value=copy.deepcopy(old['info']);value[key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError):validate_info(value,old)
        value=copy.deepcopy(old['info']);value['refill_full_predecessor']['remaining_words']=4095
        with self.assertRaises(ValueError):validate_info(value,old)
    def test_owned_states_are_bound_to_declared_job(self):
        packet=dict(owner_id='b'*32,jobs=[dict(job_id='c'*32)])
        value=dict(boot_id='a'*32,state='running',output_active=True,owner_id='b'*32,job_id='c'*32)
        validate_status(value,'a'*32,packet)
        for key,bad in [('owner_id','d'*32),('job_id','d'*32),('boot_id','d'*32),
                        ('state','failed'),('output_active',1)]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate_status(dict(value,**{key:bad}),'a'*32,packet)


if __name__=='__main__':unittest.main()
