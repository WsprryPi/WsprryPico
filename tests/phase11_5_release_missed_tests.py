import copy
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_release_missed import admit,main,BOOT,JOB,SOURCE,DEVICE

class RetirementTests(unittest.TestCase):
    def test_plan_only_no_access(self):
        with patch.object(sys,'argv',['release','--root','/absent','--baseline','/absent','--baseline-sha256','none']),patch('pathlib.Path.read_bytes',side_effect=AssertionError('access')):
            main()
    def test_exact_missed_only(self):
        status=dict(boot_id=BOOT,state='missed',output_active=False,owner_id=None,job_id=JOB,
            terminal_records=[dict(job_id=JOB,state='missed',output_active=False,error=dict(code='MISSED_START',message='MISSED_START',retryable=False))])
        info=dict(revision=SOURCE[:12],device_id=DEVICE,system_clock_hz=138000000,rf_render_in_ram=True,
            status=dict(boot_id=BOOT,state='missed',output_active=False,enabled=False,storage_healthy=True,last_error=None),
            recovery_boot=False,engine_diagnostic=False,launch_epoch='0',launch_observed_ns='0',alarm_irqs=1)
        info.update({k:0 for k in ('fault_stage','fault_status','fault_pc','fault_hash','dma_errors','dma_irqs','tail_irqs','refill_irq_unpaired','refill_invalid_reserves','exhausted_successor_links','core0_stack_fault_status','core1_stack_fault_status')})
        info.update(core0_stack_guard_valid=1,core1_stack_guard_valid=1)
        current=dict(info=info,wtp=dict(STATUS=status));admit(current,status)
        for field,value in [('state','failed'),('output_active',True),('owner_id','foreign'),('boot_id','wrong'),('job_id','wrong')]:
            bad=copy.deepcopy(current);bad['wtp']['STATUS'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):admit(bad,bad['wtp']['STATUS'])
        for field,value in [('dma_irqs',1),('launch_epoch','1'),('fault_status',1),('system_clock_hz',150000000)]:
            bad=copy.deepcopy(current);bad['info'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):admit(bad,status)
if __name__=='__main__':unittest.main()
