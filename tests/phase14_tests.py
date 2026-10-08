"""Matrix boundaries and adversarial identity/capture checks; no hardware."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.plan import matrix,job,accepted_events,validate_capture,validate_physical

class Tests(unittest.TestCase):
    def test_clock_boundaries_and_full_jobs(self):
        rows=matrix();self.assertEqual(len(rows),225)
        self.assertEqual(sum(r['disposition']=='UNSUPPORTED_CONFIGURATION' for r in rows),25)
        for clock in (132000000,138000000,150000000):
            with self.assertRaises(ValueError):job('TONE','2m',clock,'test')
        with self.assertRaises(ValueError):job('WSPR','4m',138000000,'test')
        self.assertEqual(len(job('WSPR','4m',150000000,'test')['events']),162)
        for mode in ('WSPR','QRSS','FSKCW','DFCW'):
            value=job(mode,'80m',138000000,'test')
            self.assertEqual(sum(int(e['duration_ns']) for e in value['events']),int(value['total_duration_ns']))
        self.assertEqual(job('TONE','80m',138000000,'test',3600)['total_duration_ns'],'3600000000000')
        for value in (0,3601,True):
            with self.assertRaises(ValueError):job('TONE','80m',138000000,'test',value)
    def test_adjustments_cannot_bind_foreign_event(self):
        value=job('TONE','80m',138000000,'test')
        a=dict(event_index=0,requested_frequency_nhz=value['events'][0]['frequency_nhz'],realized_frequency_nhz='3570099990000000')
        self.assertEqual(accepted_events(value,[a])['events'][0]['frequency_nhz'],a['realized_frequency_nhz'])
        self.assertNotEqual(value['events'][0]['frequency_nhz'],a['realized_frequency_nhz'])
        for changes in ({'event_index':1},{'event_index':True},{'requested_frequency_nhz':'1'}):
            with self.assertRaises(ValueError):accepted_events(value,[dict(a,**changes)])
        with self.assertRaises(ValueError):accepted_events(value,[a,a])
    def test_corrupt_receiver_evidence_never_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'iq';path.write_bytes(b'\0'*80)
            settings=dict(format='CF32',sample_rate_hz=250000)
            metadata=dict(resolved_device=dict(driver='sdrplay',serial='2404058C60'),actual_settings=settings,
                          overflow_count=0,clipping=dict(sample_count=0),primary_outcome='success',
                          cleanup=dict(outcome='verified'),retained_sample_count=10,
                          output=dict(complete=True,size_bytes=80,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            validate_capture(metadata,path,settings)
            for key,value in [('resolved_device',dict(driver='sdrplay',serial='foreign')),('overflow_count',1),
                              ('clipping',dict(sample_count=1)),('primary_outcome','failure'),
                              ('cleanup',dict(outcome='unknown')),('retained_sample_count',11),
                              ('output',dict(complete=True,size_bytes=80,sha256='0'*64))]:
                invalid=copy.deepcopy(metadata);invalid[key]=value
                with self.assertRaises(ValueError):validate_capture(invalid,path,settings)
            path.write_bytes(b'\1'*80)
            with self.assertRaises(ValueError):validate_capture(metadata,path,settings)
    def test_lifecycle_and_source_substitutions_are_rejected(self):
        value=job('TONE','80m',138000000,'test')
        idle=dict(device_id='fd6127d11d6aca42a9905fa3fb1bf1d5',revision='144e8e83e598',
                  system_clock_hz=138000000,status=dict(boot_id='a'*32,engine='pio-dma-gp2',
                  owner_id=None,output_active=False,enabled=False,state='empty'))
        running=dict(boot_id='a'*32,job_id=value['job_id'],state='running',output_active=True)
        terminal=dict(running,state='complete',output_active=False)
        physical=dict(schema='phase14-physical/1',board='A',serial='0BF4B4AEC9FFB344',
                      device_id=idle['device_id'],source_revision=idle['revision'],
                      clock_hz=138000000,band='80m',mode='TONE',divider=1,rf_gp=2,engine='pio-dma-gp2',
                      result='CONTROL_COMPLETE',firmware_sha256='b'*64,boot_id='a'*32,job=value,
                      accepted_job=copy.deepcopy(value),load=dict(job_id=value['job_id'],adjustments=[]),
                      arm=dict(job_id=value['job_id']),action='complete',
                      status=[dict(status=running),dict(status=terminal)],terminal=terminal,before=idle,after=idle)
        validate_physical(physical)
        mutations=[lambda v:v.update(board='B'),lambda v:v.update(boot_id='c'*32),
                   lambda v:v.update(firmware_sha256='bad'),
                   lambda v:v['accepted_job']['events'][0].update(duration_ns='1'),
                   lambda v:v['arm'].update(job_id='d'*32),
                   lambda v:v['status'][0]['status'].update(boot_id='d'*32),
                   lambda v:v['terminal'].update(output_active=True),
                   lambda v:v['after']['status'].update(enabled=True),
                   lambda v:v['after'].update(revision='0123456789ab')]
        for mutation in mutations:
            invalid=copy.deepcopy(physical);mutation(invalid)
            with self.assertRaises(ValueError):validate_physical(invalid)
if __name__=='__main__':unittest.main()
