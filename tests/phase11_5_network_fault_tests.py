#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_network_fault import Fault, admit_fault


class FaultTests(unittest.TestCase):
    def test_one_attempt_only_and_pending_blocks_both(self):
        for action in ('lease','link'):
            admit_fault({},action)
            with self.assertRaises(ValueError):admit_fault({'attempted':[action]},action)
            with self.assertRaises(ValueError):admit_fault({'pending':'unknown'},action)
        with self.assertRaises(ValueError):admit_fault({},'ordinary-lan')

    def test_failed_host_admission_performs_no_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            fault=Fault(Path(directory))
            with patch.object(fault.host,'verify',side_effect=ValueError('host changed')), \
                 patch.object(fault.host,'cmd') as cmd,patch.object(fault,'persist') as persist:
                with self.assertRaises(ValueError):fault.run('link')
                cmd.assert_not_called();persist.assert_not_called()

    def test_return_rechecks_durable_completion_under_its_own_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            fault=Fault(Path(directory))
            fault.path.write_text('{"link_restored":true}')
            with patch.object(fault,'_restore_link') as restore:
                fault.restore_link()
                restore.assert_not_called()

    def test_return_refuses_changed_host_before_any_command(self):
        with tempfile.TemporaryDirectory() as directory:
            fault=Fault(Path(directory));fault.host.state={'host_boot':'original'}
            with patch.object(Path,'read_text',return_value='new-boot'), \
                 patch.object(fault.host,'cmd') as cmd:
                with self.assertRaises(ValueError):fault._restore_link()
                cmd.assert_not_called()


if __name__=='__main__':unittest.main()
