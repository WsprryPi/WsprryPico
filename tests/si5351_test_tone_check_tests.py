"""Acceptance-helper admission after finite execution and native lease expiry."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import si5351_test_tone_check as check


class IdleAdmissionTests(unittest.TestCase):
    def inspect(self, job, wspr=False, message=False):
        documents = {'status': {'job': job}, 'config': {'config': {'enabled': wspr}},
                     'message-schedule': {'saved': {'enabled': message}}}
        with patch.object(check, 'read', side_effect=lambda _, name: ({}, documents[name])):
            return check.idle(object())

    def test_unowned_inactive_terminal_is_ready_after_lease_expiry(self):
        for state in ('empty', 'complete', 'aborted', 'missed'):
            with self.subTest(state=state):
                self.assertEqual(self.inspect(dict(state=state, output_active=False, owner_id=None)),
                                 {'config': {'enabled': False}})

    def test_busy_owned_unknown_and_failed_states_refuse(self):
        for state in ('loaded', 'armed', 'running', 'failed', 'unknown'):
            with self.subTest(state=state), self.assertRaises(check.usb.Refusal):
                self.inspect(dict(state=state, output_active=False, owner_id=None))
        for change in ({'output_active': True}, {'output_active': 0}, {'owner_id': 'owner'}):
            with self.subTest(change=change), self.assertRaises(check.usb.Refusal):
                self.inspect(dict(state='complete', output_active=False, owner_id=None) | change)

    def test_completed_job_does_not_bypass_disabled_schedules(self):
        for wspr, message in ((True, False), (False, True)):
            with self.subTest(wspr=wspr, message=message), self.assertRaises(check.usb.Refusal):
                self.inspect(dict(state='complete', output_active=False, owner_id=None), wspr, message)


if __name__ == '__main__':
    unittest.main()
