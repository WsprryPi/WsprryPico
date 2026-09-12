#!/usr/bin/env python3
"""Hardware-free adversarial admission and timing evidence tests for R2."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r2_plan import SCHEMA,SOURCE,IMAGE,jobs,validate
from phase11_5_r2 import main
from audit_phase11_5_r2 import timing


def packet():
    return dict(schema=SCHEMA,source_revision=SOURCE,revision=SOURCE[:12],uf2_sha256=IMAGE,
        system_clock_hz=138000000,rf_render_in_ram=True,pio_divider=1,listener_enabled=True,
        serial='0BF4B4AEC9FFB344',device_id='fd6127d11d6aca42a9905fa3fb1bf1d5',
        nonce='1'*32,boot_id='2'*32,owner_id='3'*32,browser_session_id='4'*32,
        nominal_seconds=300,browser_profile='N',submission_path='browser',prior_terminal_records=[],jobs=jobs('1'*32))


class R2Tests(unittest.TestCase):
    def test_plan_only_has_no_access(self):
        with patch.object(sys,'argv',['r2','--root','/absent','--packet-sha256','absent']), \
             patch('phase11_5_r2.Path.resolve',side_effect=AssertionError('accessed')), \
             patch('phase11_5_r2.subprocess.run',side_effect=AssertionError('executed')):
            main()

    def test_exact_packet(self):
        validate(packet())
        for key,value in [('source_revision','f'*40),('revision','f'*12),('uf2_sha256','f'*64),
            ('system_clock_hz',150000000),('rf_render_in_ram',False),('listener_enabled',False),
            ('pio_divider',2),('serial','B'),('boot_id','0'*32),('nominal_seconds',180),
            ('browser_profile','S'),('submission_path','production'),('prior_terminal_records',[{}])]:
            bad=packet();bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(bad)

    def test_finite_jobs_cannot_expand_or_change(self):
        for mutate in (lambda j:j.append(copy.deepcopy(j[0])), lambda j:j.pop(),
            lambda j:j[0].update(total_duration_ns='20000000000'),
            lambda j:j[0]['events'][0].update(frequency_nhz='14097100000000000'),
            lambda j:j[0]['events'][0].update(rf_on=1),
            lambda j:j[1].update(job_id=j[0]['job_id'])):
            bad=packet();mutate(bad['jobs'])
            with self.assertRaises(ValueError):validate(bad)

    def test_missing_raw_job_observations_cannot_pass(self):
        with self.assertRaises(ValueError):timing(packet(),[],[])
        actor=[]
        for j in packet()['jobs']:
            actor.extend([dict(kind='armed_job',monotonic_ns=1,value=dict(job=j)),
                dict(kind='request_intent',monotonic_ns=2,value=dict(request=dict(operation='RELEASE')))])
        with self.assertRaises(ValueError):timing(packet(),actor,[])


    def test_per_job_timing_accepts_intact_and_rejects_mutations(self):
        p=packet();actor=[];rows=[]
        base=dict(allocator_largest_successful_request_bytes=18364,dma_irqs=0,alarm_irqs=0,tail_irqs=0,running_successor_links=0,
            refill_irq_pairs=0,running_tail_links=0,refill_short_predecessor=None)
        blocks=(1380000000+524287)//524288
        for index,job in enumerate(p['jobs']):
            begin=(index+1)*100000000000;target=begin
            rows.append(dict(kind='info',monotonic_ns=begin-1,value=dict(value=copy.deepcopy(base))))
            actor.extend([dict(kind='armed_job',monotonic_ns=begin,value=dict(start_utc_ns=str(target))),
                dict(kind='request_intent',monotonic_ns=begin+3,value=dict(request=dict(operation='RELEASE')))])
            info=copy.deepcopy(base)
            for key,delta in dict(dma_irqs=blocks+1,alarm_irqs=1,tail_irqs=1,
                running_successor_links=blocks-1,refill_irq_pairs=blocks-1,running_tail_links=1).items():
                info[key]+=delta
            info.update(launch_epoch=str(index+1),launch_target_ns=str(target),launch_observed_ns=str(target+1000),
                max_refill_irq_to_ready_ns='2000000',max_dma_irq_ns=1000,max_alarm_irq_ns='200000',
                refill_full_predecessor=dict(total_words=16384,remaining_words=8192),
                refill_short_predecessor=dict(total_words=((1380000000%524288)+31)//32,
                    remaining_words=((1380000000%524288)+31)//32,observations=index+1),
                status=dict(state='running',utc_now_ns=str(target),monotonic_now_ns=str(target),uncertainty_ns='1000'))
            rows.append(dict(kind='info',monotonic_ns=begin+1,value=dict(value=copy.deepcopy(info))))
            info['status']['state']='complete'
            rows.append(dict(kind='info',monotonic_ns=begin+2,value=dict(value=copy.deepcopy(info))))
            base=info
        self.assertEqual(len(timing(p,actor,rows)),3)
        diagnostic=copy.deepcopy(rows)
        diagnostic[-1]['value']['value']['max_alarm_irq_ns']='293000'
        self.assertEqual(timing(p,actor,diagnostic)[-1]['max_alarm_callback_ns'],293000)
        for key,value in [('launch_epoch','1'),('launch_observed_ns','1'),('launch_observed_ns','301000000000'),('tail_irqs',0),
                          ('refill_irq_pairs',0),('allocator_largest_successful_request_bytes',18365),
                          ('max_refill_irq_to_ready_ns','2849392')]:
            bad=copy.deepcopy(rows);bad[-1]['value']['value'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):timing(p,actor,bad)
        bad=copy.deepcopy(rows);bad[-1]['value']['value']['refill_short_predecessor']['remaining_words']=0
        with self.assertRaises(ValueError):timing(p,actor,bad)

if __name__=='__main__':unittest.main()
