"""Offline reservation tests: uncertainty must survive loss of the process lock."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import time
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
    def test_rejected_preflight_never_claims_aborts_or_releases(self):
        from phase11_5_completion_native_idle import run
        from unittest.mock import Mock
        original_read = Path.read_text
        def read(path, *args, **kwargs):
            return 'host' if str(path) == '/proc/sys/kernel/random/boot_id' else original_read(path, *args, **kwargs)
        for foreign_active in (False, True):
            values = snapshots()
            if foreign_active:
                values['a']['info']['status'].update(state='running', output_active=True)
                values['a']['wtp']['STATUS'].update(state='running', output_active=True, owner_id='foreign')
            with self.subTest(foreign_active=foreign_active), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); now = time.monotonic_ns()
                packet = dict(root=str(root), boot_id='a'*32, source_revision='test', host_boot_id='host',
                              stage_sha256={}, start_monotonic_ns=now-1_000_000_000,
                              work_deadline_monotonic_ns=now+10_000_000_000,
                              cleanup_deadline_monotonic_ns=now+20_000_000_000)
                reservation = Mock()
                with patch.object(Path, 'read_text', read), patch('os.geteuid', return_value=0), \
                     patch('phase11_5_completion_native_idle.Reservation', return_value=reservation), \
                     patch('phase11_5_completion_native_idle.inventory', side_effect=lambda root,p,label,b: values['b' if b else 'a']) as inventory, \
                     patch('phase11_5_completion_native_idle.candidate', side_effect=ValueError('rejected candidate')), \
                     patch('phase11_5_completion_native_idle.configuration', return_value={}), \
                     patch('phase11_5_completion_native_idle.exclusive_port') as port:
                    run(root, packet, 'packet')
                port.assert_not_called()
                reservation.acquire.assert_not_called()
                reservation.release.assert_not_called()
                reservation.close.assert_called_once()
                self.assertEqual(inventory.call_count, 4)
                result = json.loads((root/'run-result.json').read_text())
                self.assertEqual(result['status'], 'FAILED')
                self.assertTrue(result['preflight_rejected'])
                self.assertEqual(result['loads'], 0)
                self.assertNotIn('cleanup_error', result)
                self.assertFalse((root/'reservation-released.json').exists())
                if foreign_active:
                    self.assertIn('reconciliation_error', result)
                else:
                    self.assertEqual(result['error'], 'rejected candidate')
                    self.assertNotIn('reconciliation_error', result)

    def test_loaded_dwell_requires_observed_state_not_just_elapsed_time(self):
        from phase11_5_completion_native_idle import LoadedObservationGate
        state=dict(boot_id='boot',state='loaded',job_id='job',owner_id='owner',output_active=False)
        gate=LoadedObservationGate('packet','boot','owner','job',9_000_000_000)
        def value(stamp,job):return dict(packet_sha256='packet',observed_monotonic_ns=stamp,job=job)
        self.assertFalse(gate.observe(value(8_000_000_000,state),9_000_000_000))
        for stamp in (9_132_000_000,10_153_000_000,11_177_000_000,12_190_000_000):
            self.assertFalse(gate.observe(value(stamp,None),stamp))
        self.assertFalse(gate.observe(value(13_203_000_000,state),13_203_000_000))
        self.assertFalse(gate.observe(value(13_203_000_000,state),13_250_000_000))
        self.assertTrue(gate.observe(value(14_219_000_000,state),14_219_000_000))
        for changed in (state|dict(job_id='other'),state|dict(owner_id='other'),state|dict(output_active=True)):
            fresh=LoadedObservationGate('packet','boot','owner','job',0)
            self.assertFalse(fresh.observe(value(1,changed),1))
        with self.assertRaises(ValueError):gate.observe(value(1,state),7_000_000_002)
        with self.assertRaises(ValueError):gate.observe(value(14_219_000_000,state)|dict(packet_sha256='other'),14_219_000_000)

    def test_recovery_deployment_requires_exact_fault_and_inactive_peer(self):
        from phase11_5_completion_deploy import admit_prior, HTTP_PAGES, RECOVERY_FAULT
        before=snapshots();before['a']['info'].update(RECOVERY_FAULT)
        packet=dict(scope=HTTP_PAGES,prior_revision='test',prior_boot='a'*32,b_boot_id='b'*32)
        admit_prior(before,packet)
        for change in ('fault','boot','peer','active','schedule'):
            altered=copy.deepcopy(before)
            if change=='fault':altered['a']['info']['fault_allocation_request_bytes']=32768
            elif change=='boot':altered['a']['wtp']['STATUS']['boot_id']='c'*32
            elif change=='peer':altered['b']['wtp']['STATUS']['boot_id']='c'*32
            elif change=='active':altered['a']['wtp']['STATUS']['output_active']=True
            else:altered['b']['info']['status']['enabled']=True
            with self.subTest(change=change),self.assertRaises(ValueError):admit_prior(altered,packet)

    def test_recovery_config_excludes_only_uninitialized_runtime_mac(self):
        from phase11_5_completion_deploy import config_snapshot, HTTP_PAGES
        info=dict(status=dict(configured=True,enabled=False,station=dict(call='TEST'),schedules=[],watermark_utc_ns='0'),
                  network=dict(station_mac='',configured_hostname='pico.local',control_configured=True))
        before=dict(info=info);after=copy.deepcopy(before)
        after['info']['network']['station_mac']='88:a2:9e:0a:60:df'
        packet=dict(scope=HTTP_PAGES)
        self.assertEqual(config_snapshot(before,packet),config_snapshot(after,packet))
        self.assertNotEqual(config_snapshot(before,dict(scope='old')),config_snapshot(after,dict(scope='old')))
        for change in ('station','schedule','hostname'):
            altered=copy.deepcopy(after)
            if change=='station':altered['info']['status']['station']['call']='CHANGED'
            elif change=='schedule':altered['info']['status']['enabled']=True
            else:altered['info']['network']['configured_hostname']='other.local'
            self.assertNotEqual(config_snapshot(before,packet),config_snapshot(altered,packet))

    def test_failed_resource_gate_does_not_block_identified_cleanup(self):
        from phase11_5_completion_native_idle import cleanup_identity
        info = snapshots()['a']['info']
        info['allocator_peak_bytes'] = 200000
        cleanup_identity(info, 'a'*32, 'test')
        for change in (dict(device_id='wrong'), dict(revision='wrong'),
                       dict(status=dict(boot_id='changed',enabled=False)),
                       dict(status=dict(boot_id='a'*32,enabled=True))):
            with self.assertRaises(ValueError):cleanup_identity(info|change, 'a'*32, 'test')

    def test_final_authority_release_is_independent_of_failed_resource_acceptance(self):
        from phase11_5_completion_native_idle import reconcile_authority
        from unittest.mock import Mock
        before = snapshots(); final = copy.deepcopy(before)
        final['a']['info']['allocator_peak_bytes'] = 200000
        reservation = Mock()
        with patch('phase11_5_completion_native_idle.configuration', return_value={}):
            reconcile_authority(reservation, before, final, 'a'*32, 'test')
            reservation.release.assert_called_once_with(final)
            for mutation in ('boot', 'active', 'schedule'):
                changed = copy.deepcopy(final)
                if mutation == 'boot': changed['a']['info']['status']['boot_id'] = 'wrong'
                elif mutation == 'active': changed['a']['wtp']['STATUS']['output_active'] = True
                else: changed['a']['info']['status']['enabled'] = True
                rejected = Mock()
                with self.assertRaises(ValueError):reconcile_authority(rejected, before, changed, 'a'*32, 'test')
                rejected.release.assert_not_called()

    def test_reconciliation_cannot_transfer_or_use_stale_authority(self):
        original_read=Path.read_text
        def read(path,*args,**kwargs):
            return 'test-host-boot' if str(path)=='/proc/sys/kernel/random/boot_id' else original_read(path,*args,**kwargs)
        with tempfile.TemporaryDirectory() as directory, patch.object(Path,'read_text',read):
            path=Path(directory)/'reservation.json';values=snapshots()
            owner=Reservation('a'*64,path);owner.acquire(values);owner.close()
            changed=copy.deepcopy(values);changed['a']['info']['revision']='other'
            for sha,v,stamp in [('b'*64,values,time.monotonic_ns()),('a'*64,changed,time.monotonic_ns()),
                                ('a'*64,values,time.monotonic_ns()-6_000_000_000)]:
                with self.assertRaises(ValueError):Reservation(sha,path,reconciliation=(v,stamp))
                self.assertEqual(json.loads(path.read_text())['state'],'HELD')
            owner=Reservation('a'*64,path,reconciliation=(values,time.monotonic_ns()))
            owner.release(values);owner.close()
            self.assertEqual(json.loads(path.read_text())['state'],'RELEASED')

    def test_reconciliation_allows_only_exact_authorized_boot_transition(self):
        original_read=Path.read_text
        def read(path,*args,**kwargs):
            return 'test-host-boot' if str(path)=='/proc/sys/kernel/random/boot_id' else original_read(path,*args,**kwargs)
        with tempfile.TemporaryDirectory() as directory, patch.object(Path,'read_text',read):
            path=Path(directory)/'reservation.json';before=snapshots()
            owner=Reservation('a'*64,path);owner.acquire(before);owner.close()
            after=copy.deepcopy(before)
            after['a']['info']['status']['boot_id']='c'*32
            after['a']['wtp']['HELLO']['boot_id']='c'*32
            after['a']['wtp']['STATUS']['boot_id']='c'*32
            transition={'a':('a'*32,'c'*32)}
            for allowed in (None, {'a':('a'*32,'d'*32)}, {'b':('b'*32,'c'*32)},
                            {'a':('a'*32,'c'*32), 'b':('b'*32,'d'*32)}):
                with self.subTest(allowed=allowed),self.assertRaises(ValueError):
                    Reservation('a'*64,path,reconciliation=(after,time.monotonic_ns()),
                                authorized_boot_changes=allowed)
                self.assertEqual(json.loads(path.read_text())['state'],'HELD')
            owner=Reservation('a'*64,path,reconciliation=(after,time.monotonic_ns()),
                              authorized_boot_changes=transition)
            owner.release(after);owner.close()
            self.assertEqual(json.loads(path.read_text())['state'],'RELEASED')

    def test_declared_complete_predecessor_only_before_load(self):
        from phase11_5_r3_v2_rf import observed_status, SERIAL_CAPACITY
        packet=dict(boot_id='boot',owner_id='owner',jobs=[dict(job_id='new')],
                    capacity_schedule_policy=SERIAL_CAPACITY,initial_a_job_id='old')
        status=dict(boot_id='boot',owner_id=None,job_id='old',state='complete',output_active=False)
        self.assertEqual(observed_status(status,packet,initial=True),status)
        with self.assertRaises(ValueError):observed_status(status,packet)
        for change in [dict(state='armed'),dict(state='running',output_active=True),dict(owner_id='foreign'),
                       dict(owner_id='owner'),dict(job_id='undeclared'),dict(boot_id='other')]:
            with self.assertRaises(ValueError):observed_status(status|change,packet,initial=True)
        self.assertEqual(observed_status(status|dict(job_id='new',state='loaded',owner_id='owner'),packet)['job_id'],'new')
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
        sequential = dict(packet, capacity_schedule_policy='wtp-then-http-capacity-v1',
                          initial_a_state='complete', initial_a_job_id='b88c7a3082eb4208a7e1f403bc13c9f8')
        validate(sequential)
        for key in ('initial_a_state', 'initial_a_job_id'):
            with self.assertRaises(ValueError):
                validate(dict(sequential, **{key: None}))
        for key, value in [('shared_rf_reservation', None), ('closure_policy', None),
                           ('b_role', 'independent-zero-rf'), ('image_sha256', '0' * 64),
                           ('runtime_seconds', 301), ('maximum_initial_terminal_records', 2), ('not_before_host_monotonic_ns', None)]:
            altered = copy.deepcopy(packet)
            altered[key] = value
            with self.assertRaises(ValueError):
                validate(altered)


if __name__ == '__main__':
    unittest.main()
