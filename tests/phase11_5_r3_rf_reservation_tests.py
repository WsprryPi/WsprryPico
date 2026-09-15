"""Offline reservation tests: uncertainty must survive loss of the process lock."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase11_5_rf_reservation import BOARDS, Reservation, inactive


def snapshots():
    return {name: dict(info=dict(device_id=device, revision='test', status=dict(
                boot_id=name * 32, state='empty', output_active=False, enabled=False)),
                wtp=dict(HELLO=dict(device_id=device, boot_id=name * 32), STATUS=dict(
                    boot_id=name * 32, state='empty', output_active=False, owner_id=None)))
            for name, (_, device) in BOARDS.items()}


class Tests(unittest.TestCase):
    def test_authority_and_identity_fail_closed(self):
        original = snapshots()
        inactive(original)
        for board in BOARDS:
            mutations = [
                lambda v: v['info'].update(device_id='f' * 32),
                lambda v: v['wtp']['HELLO'].update(boot_id='f' * 32),
                lambda v: v['info']['status'].update(enabled=True),
                lambda v: v['info']['status'].update(enabled=0),
                lambda v: v['wtp']['STATUS'].update(output_active=0),
                lambda v: v['wtp']['STATUS'].update(output_active=True),
                lambda v: v['wtp']['STATUS'].update(state='armed'),
                lambda v: v['wtp']['STATUS'].update(owner_id='e' * 32),
            ]
            for mutate in mutations:
                value = copy.deepcopy(original)
                mutate(value[board])
                with self.assertRaises(ValueError):
                    inactive(value)
        with self.assertRaises(ValueError):
            inactive({'a': original['a']})

    def test_crash_or_expiry_cannot_transfer_reservation(self):
        original_read = Path.read_text

        def read(path, *args, **kwargs):
            if str(path) == '/proc/sys/kernel/random/boot_id':
                return 'test-host-boot'
            return original_read(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as directory, patch.object(Path, 'read_text', read):
            path = Path(directory) / 'reservation.json'
            first = Reservation('a' * 64, path)
            first.acquire(snapshots())
            with self.assertRaises(BlockingIOError):
                Reservation('b' * 64, path)
            first.close()
            self.assertEqual(json.loads(path.read_text())['state'], 'HELD')
            with self.assertRaises(ValueError):
                Reservation('b' * 64, path)

    def test_release_requires_both_boards_and_allows_next_packet(self):
        original_read = Path.read_text

        def read(path, *args, **kwargs):
            if str(path) == '/proc/sys/kernel/random/boot_id':
                return 'test-host-boot'
            return original_read(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as directory, patch.object(Path, 'read_text', read):
            path = Path(directory) / 'reservation.json'
            first = Reservation('a' * 64, path)
            first.acquire(snapshots())
            with self.assertRaises(ValueError):
                first.release({'a': snapshots()['a']})
            self.assertEqual(json.loads(path.read_text())['state'], 'HELD')
            first.release(snapshots())
            first.close()
            second = Reservation('b' * 64, path)
            second.acquire(snapshots())
            second.release(snapshots())
            second.close()
            self.assertEqual(json.loads(path.read_text())['packet_sha256'], 'b' * 64)

    def test_candidate_cannot_run_without_new_policy_and_shared_reservation(self):
        from phase11_5_r3_v2_rf import validate, COMPLETION_POLICY, COMPLETION_SOURCE, COMPLETION_IMAGE
        from phase11_5_r3_capacity_plan import http_capacity_cases
        from phase11_5_r3_v2_rf_tests import FiniteRfPacketTests
        packet = FiniteRfPacketTests().packet()
        packet.update(runtime_seconds=300, observer_policy='single-flight-info-v1',
            b_role='unchanged-comparator',
            wtp_capacity=dict(maximum_request_id='a'*32, oversized_request_id='b'*32, recovery_request_id='c'*32),
            http_capacity=dict(seed='d'*32, cases=http_capacity_cases('d'*32)),
            contention=dict(policy='native-wtp-and-https-status-20s-v1',maximum_https_requests=16))
        packet['jobs'][0].update(mode='fskcw',total_duration_ns='128000000000',events=[
            dict(offset_ns=str(n*250000000),duration_ns='250000000',rf_on=True,
                frequency_nhz=str(135500000000000 if n%2==0 else 135495000000000)) for n in range(512)])
        packet.update(source_revision=COMPLETION_SOURCE, image_sha256=COMPLETION_IMAGE,
                      closure_policy=COMPLETION_POLICY, shared_rf_reservation='durable-both-picos-v1',
                      maximum_initial_terminal_records=1, not_before_host_monotonic_ns=1)
        validate(packet)
        for key, value in [('shared_rf_reservation', None), ('closure_policy', None),
                           ('b_role', 'independent-zero-rf'), ('image_sha256', '0' * 64),
                           ('runtime_seconds', 301), ('maximum_initial_terminal_records', 2), ('not_before_host_monotonic_ns', None)]:
            altered = copy.deepcopy(packet)
            altered[key] = value
            with self.assertRaises(ValueError):
                validate(altered)


if __name__ == '__main__':
    unittest.main()
