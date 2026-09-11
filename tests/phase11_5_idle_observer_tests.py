#!/usr/bin/env python3
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase11_5_idle_observer import main, validate_info
from phase11_5_device_management_tests import baseline
from phase11_5_a2_family import resume_stages


class IdleObserverTests(unittest.TestCase):
    def test_resume_preserves_only_completed_stage_boundaries(self):
        old=dict(status='FAILED',current_interval='controller',intervals={'quiet-before':{}})
        self.assertEqual(resume_stages(old),('controller','nominal','quiet-after'))
        for change in [dict(status='RUNNING'),dict(current_interval='quiet-after'),
                       dict(intervals={}),dict(intervals={'quiet-before':{},'nominal':{}})]:
            with self.assertRaises(ValueError):resume_stages({**old,**change})
        self.assertEqual(resume_stages(dict(status='FAILED',current_interval='nominal',
            intervals={'quiet-before':{},'controller':{}})),('nominal','quiet-after'))

    def test_resource_and_current_info_faults_are_not_hidden_by_idle_baseline(self):
        old = baseline()
        old['info'].update(heap_capacity_bytes=218408, allocator_peak_bytes=42640,
                           allocator_failures='0', tls_allocation_failures=0)
        validate_info(old['info'], old)
        for field, value in [('allocator_peak_bytes',218408-32767),
                             ('allocator_failures','1'),('tls_allocation_failures',1),
                             ('core1_stack_fault_status',1)]:
            changed = copy.deepcopy(old['info']); changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_info(changed, old)
        for field,value in [('boot_id','b'*32),('state','running'),('output_active',True)]:
            changed = copy.deepcopy(old['info']); changed['status'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_info(changed, old)

    def test_no_run_never_reads_baseline_or_opens_endpoint(self):
        with patch.object(sys,'argv',['observer','--baseline','/absent','--output','/absent',
                '--session-id','a'*32,'--seconds','360']), \
             patch.object(Path,'read_text',side_effect=AssertionError('unexpected read')):
            main()


if __name__ == '__main__': unittest.main()
