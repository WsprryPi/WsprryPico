#!/usr/bin/env python3
"""Hardware-free admission checks for the single recorded OOM recovery."""
import copy
import subprocess
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r2_oom_recovery import admission, BOOT, FAULT, DEVICE, B_DEVICE

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        status=dict(state='empty',output_active=False,owner_id=None,job_id=None,
                    terminal_records=[],enabled=False,last_error=None,storage_healthy=True,
                    boot_id=BOOT,engine='pio-dma-gp2',configured=True,
                    station={},schedules=[],watermark_utc_ns='1')
        info=dict(device_id=DEVICE,revision='049cc929143b',system_clock_hz=138000000,
                  recovery_boot=True,status=copy.deepcopy(status),
                  network=dict(station_mac='',initialized=False,control_listening=False,configured_hostname='h',control_configured=True))
        info.update(zip(('fault_stage','fault_hash','fault_pc','fault_status'),FAULT))
        self.current=dict(info=info,wtp={'STATUS':status})
        self.baseline=copy.deepcopy(self.current)
        self.b=copy.deepcopy(self.current)
        self.b['info'].update(device_id=B_DEVICE,revision='dbf1d86f0885-dirty',recovery_boot=False)
        self.original_b=copy.deepcopy(self.b)
    def test_exact_and_mutated_admission(self):
        admission(self.current,self.baseline,self.b,self.original_b)
        for path,value in [(('info','fault_hash'),0),(('info','recovery_boot'),False),
                           (('info','revision'),'different'),(('info','system_clock_hz'),150000000),
                           (('wtp','STATUS','output_active'),True),(('wtp','STATUS','owner_id'),'f'*32),
                           (('wtp','STATUS','boot_id'),'b'*32),(('wtp','STATUS','job_id'),'a'*32),
                           (('info','status','enabled'),True),(('info','status','storage_healthy'),False),
                           (('info','status','watermark_utc_ns'),'2')]:
            with self.subTest(path=path):
                mutated=copy.deepcopy(self.current); at=mutated
                for key in path[:-1]: at=at[key]
                at[path[-1]]=value
                with self.assertRaises(ValueError): admission(mutated,self.baseline,self.b,self.original_b)
        changed=copy.deepcopy(self.b); changed['wtp']['STATUS']['boot_id']='new'
        with self.assertRaises(ValueError): admission(self.current,self.baseline,changed,self.original_b)
    def test_dry_run(self):
        result=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/phase11_5_r2_oom_recovery.py')],capture_output=True,text=True,check=True)
        self.assertIn('no device access',result.stdout)

if __name__=='__main__': unittest.main()
