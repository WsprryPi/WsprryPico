#!/usr/bin/env python3
"""Hardware-free failure-path tests for the finite physical campaign runner."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase15_15_hardware as hardware


class BudgetTests(unittest.TestCase):
    def test_reopen_discards_queues_only_during_dtr_low_interval(self):
        events = []
        with patch('fcntl.ioctl', side_effect=lambda fd, op, value: events.append(op)), \
                patch('termios.tcflush', side_effect=lambda fd, mode: events.append('discard')), \
                patch('time.sleep', side_effect=lambda seconds: events.append(('quiet', seconds))):
            hardware.reset_cdc(10)
        self.assertEqual(events, [hardware.termios.TIOCMBIC, 'discard', ('quiet', .1),
                                  'discard', hardware.termios.TIOCMBIS])

    def test_failed_backup_reboots_unchanged_board_without_restore_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            helper = root / 'helper'
            helper.write_bytes(b'fixture')
            campaign = object.__new__(hardware.Campaign)
            campaign.args = types.SimpleNamespace(candidate=helper, baseline=helper)
            campaign.rig = types.SimpleNamespace(e=types.SimpleNamespace(root=root), close=lambda: None)
            campaign.original, campaign.in_rom, campaign.managed = {}, set(), None
            campaign.armed = campaign.rf_budget = campaign.captures = 0
            campaign.preparations, campaign.restarts = [], []
            campaign.original_service = campaign.stopped_service = False
            campaign.claim = None
            operations = []
            campaign.pt = lambda *args: operations.append(args)
            campaign.wait = lambda *args: None

            def failed_snapshot(board):
                campaign.in_rom.add(board)
                raise OSError('backup storage unavailable; flash never written')

            campaign.snapshot = failed_snapshot
            with patch.object(hardware, 'PIC', str(helper)), patch.object(hardware, 'CLIENT', str(helper)), \
                    patch.object(hardware, 'CAPTURE', str(helper)), \
                    patch('subprocess.run', return_value=types.SimpleNamespace(returncode=1)), \
                    patch('phase14_reference.gps', return_value=dict(out1=False, out2=False)), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(campaign.execute())
            self.assertEqual(operations, [('A', 'reboot')])
            self.assertFalse(campaign.in_rom)

    def test_pad_probe_arms_inactive_before_readback_then_cancels(self):
        with tempfile.TemporaryDirectory() as directory:
            campaign = object.__new__(hardware.Campaign)
            campaign.managed = None
            campaign.armed = campaign.rf_budget = 0
            campaign.preparations = []
            campaign.claim = None
            campaign.rig = types.SimpleNamespace(e=types.SimpleNamespace(root=Path(directory)))
            campaign.idle = lambda board: {'status': {'clock_state': 'synchronized', 'uncertainty_ns': '1'}}
            state = {'value': 'empty'}
            order = []

            class Api:
                def api(self, resource):
                    order.append('read-' + state['value'])
                    return {'etag': 'revision', 'body': {'pad_readback': 4 if state['value'] == 'armed' else None,
                            'rf_gp': 2, 'boot_active': 4, 'application_error': None,
                            'target': {'boot_id': 'b' * 32}}}

                def command(self, value):
                    return {'status': 409}

                def close(self):
                    pass

            def connect(board):
                campaign.managed = Api()
                return campaign.managed

            class Peer:
                boot = 'b' * 32

                def request(self, operation, body, **kwargs):
                    order.append(operation)
                    if operation == 'GET_CLOCK':
                        return {'utc_now_ns': '1000000000'}
                    if operation in ('LOAD', 'ARM', 'ABORT'):
                        state['value'] = {'LOAD': 'loaded', 'ARM': 'armed', 'ABORT': 'aborted'}[operation]
                    return {'state': state['value'], 'output_active': False}

            @contextlib.contextmanager
            def peer(board):
                yield Peer()

            campaign.connect, campaign.peer = connect, peer
            campaign.prepare('A', 4)
            self.assertLess(order.index('ARM'), order.index('read-armed'))
            self.assertLess(order.index('read-armed'), order.index('ABORT'))
            self.assertEqual(len(campaign.preparations), 1)
            self.assertEqual(campaign.armed, 1)
            self.assertEqual(campaign.rf_budget, 1)
            self.assertIsNone(campaign.claim)

    def test_unknown_arm_consumes_budget_without_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            helper = root / 'helper'
            helper.write_bytes(b'identity-only fixture; never executed')
            campaign = object.__new__(hardware.Campaign)
            campaign.managed = None
            campaign.armed = campaign.rf_budget = campaign.captures = 0
            campaign.claim = None
            campaign.records = []
            campaign.current_image = {'A': 'a' * 64}
            campaign.rig = types.SimpleNamespace(e=types.SimpleNamespace(root=root, event=lambda *args: None))
            campaign.idle = lambda board: {'status': {'clock_state': 'synchronized', 'uncertainty_ns': '1'}}
            arms = []

            class Peer:
                def request(self, operation, body, **kwargs):
                    if operation == 'GET_CLOCK':
                        return {'state': 'synchronized', 'uncertainty_ns': '1', 'utc_now_ns': '1000000000'}
                    if operation == 'ARM':
                        arms.append(body)
                        raise TimeoutError('response lost after possible delivery')
                    return {}

            @contextlib.contextmanager
            def peer(board):
                yield Peer()

            campaign.peer = peer
            with patch.object(hardware, 'CAPTURE', str(helper)):
                with self.assertRaises(TimeoutError):
                    campaign.run_job('A', 4, 14097100, 'uncertain-arm', capture=False)
            self.assertEqual(len(arms), 1)
            self.assertEqual(campaign.armed, 1)
            self.assertEqual(campaign.rf_budget, 5)
            self.assertIsNotNone(campaign.claim)
            self.assertTrue((root / 'uncertain-arm' / 'physical.json').exists())

    def test_exhausted_budget_refuses_before_any_device_access(self):
        campaign = object.__new__(hardware.Campaign)
        campaign.armed, campaign.rf_budget, campaign.captures = 36, 0, 0
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            campaign.run_job('A', 4, 14097100, 'no-window', capture=False)


if __name__ == '__main__':
    unittest.main()
