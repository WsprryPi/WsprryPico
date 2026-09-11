#!/usr/bin/env python3
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase11_5_f1_plan as plan
from validate_wtp_contract import SchemaValidator
from audit_phase11_5_a3 import dma_coverage


class F1PlanTests(unittest.TestCase):
    def packet(self):
        packet=dict(schema=plan.SCHEMA,source_revision=plan.SOURCE,revision=plan.SOURCE[:12],
            uf2_sha256=plan.IMAGE,system_clock_hz=138000000,rf_render_in_ram=True,
            serial='0BF4B4AEC9FFB344',device_id='fd6127d11d6aca42a9905fa3fb1bf1d5',
            host_boot_id=plan.HOST_BOOT,maximum_renewals=60,nominal_seconds=1500,boot_id='a'*32,owner_id='b'*32,
            browser_session_id='c'*32,nonce='d'*32)
        packet['jobs']=plan.jobs(packet['nonce']);packet['totals']=plan.totals(packet['jobs'])
        return packet

    def test_finite_modes_fit_independent_wtp_schema_and_declared_budget(self):
        packet=self.packet();plan.validate(packet)
        schema=json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text())
        validator=SchemaValidator(schema)
        self.assertEqual(len({j['job_id'] for j in packet['jobs']}),15)
        for job in packet['jobs']:
            envelope=dict(type='request',protocol='WTP/1',session_id='e'*32,
                          request_id=job['job_id'],op='LOAD',body=job)
            self.assertEqual(validator.errors(envelope,schema),[])
            self.assertLessEqual(len(job['events']),162)
            self.assertLessEqual(int(job['total_duration_ns']),110592000000)
        self.assertEqual(packet['totals'],dict(jobs=15,duration_ns=622776000000,rf_on_ns=532776000000))

    def test_altered_emissions_or_identity_cannot_reuse_plan(self):
        original=self.packet()
        changes=[lambda p:p.update(host_boot_id='0'*36),
                 lambda p:p.update(system_clock_hz=150000000),
                 lambda p:p.update(owner_id='0'*32),
                 lambda p:p['jobs'].pop(),
                 lambda p:p['jobs'][0]['events'][0].update(frequency_nhz='14097000000000000'),
                 lambda p:p['jobs'][0]['events'][0].update(duration_ns='20000000000'),
                 lambda p:p['jobs'][3]['events'][0].update(rf_on=True,frequency_nhz='135500000000000')]
        for change in changes:
            packet=copy.deepcopy(original);change(packet)
            packet['totals']=plan.totals(packet['jobs'])
            with self.subTest(change=change),self.assertRaises(ValueError):plan.validate(packet)

    def test_hardware_coverage_includes_all_fifteen_complete_jobs(self):
        packet=self.packet()
        expected=dict(dma_irqs=163947,tail_irqs=15,alarm_irqs=15,running_successor_links=163917)
        before={key:100 for key in expected}
        final={key:before[key]+value for key,value in expected.items()}
        self.assertEqual(dma_coverage(packet,before,final),expected)
        for key in expected:
            for change in (-1,1):
                with self.subTest(key=key,change=change),self.assertRaises(ValueError):
                    dma_coverage(packet,before,{**final,key:final[key]+change})

    def test_actual_caps_can_refuse_a_prepared_job(self):
        packet=self.packet()
        caps=dict(modes=['tone','qrss','fskcw','dfcw','wspr'],profiles=['rf-events/1'],
                  max_events=162,max_job_duration_ns='110592000000',frequency_ranges=[
                      dict(minimum_nhz='100000000000000',maximum_nhz='68999999000000000')])
        plan.admit_caps(packet,caps)
        for change in (dict(modes=['tone']),dict(max_events=161),dict(max_job_duration_ns='10000000000'),
                       dict(frequency_ranges=[dict(minimum_nhz='140000000000000',maximum_nhz='150000000000000')])):
            with self.subTest(change=change),self.assertRaises(ValueError):plan.admit_caps(packet,{**caps,**change})


if __name__=='__main__':unittest.main()
