#!/usr/bin/env python3
import copy
from pathlib import Path
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase11_5_device_management import SOURCE, DEVICE, admit, authorize, configuration
from phase11_5_inventory import inventory_session


def baseline(physical=True):
    status = dict(state='empty', output_active=False, owner_id=None, job_id=None,
                  enabled=False, last_error=None, storage_healthy=True,
                  boot_id='a'*32, watermark_utc_ns='0',
                  engine='pio-dma-gp2' if physical else 'inhibited-standalone-simulator')
    info = dict(device_id=DEVICE, revision=SOURCE[:12], status=status.copy(),
                system_clock_hz=138000000 if physical else 150000000, recovery_boot=False,
                fault_stage=0,fault_hash=0,fault_pc=0,fault_status=0,rf_render_in_ram=True,
                engine_diagnostic='',dma_errors=0,refill_invalid_reserves=0,
                exhausted_successor_links=0,refill_irq_unpaired=0)
    for core, bottom in enumerate((0x2007c000, 0x20003488)):
        for suffix, value in (('guard_bottom', bottom), ('guard_limit', bottom+4096),
                              ('guard_valid', 1), ('fault_status', 0)):
            info[f'core{core}_stack_{suffix}'] = value
    return dict(info=info, wtp={'STATUS': status})


class ManagementTests(unittest.TestCase):
    def test_inventory_session_reuse_is_explicit_and_validated(self):
        value=inventory_session(None)
        self.assertEqual(len(value),32)
        self.assertEqual({inventory_session(value) for _ in range(64)},{value})
        for invalid in ('','0'*32,'A'*32,'a'*31,'a'*33):
            with self.assertRaises(ValueError):inventory_session(invalid)
    def test_both_exact_engines(self):
        for physical in (True, False):
            value = baseline(physical)
            self.assertEqual(admit(value, value), physical)

    def test_reject_authority_and_identity_changes(self):
        old = baseline()
        for section, key, value in (
            ('info', 'revision', SOURCE[:12]+'-dirty'),
            ('info', 'device_id', 'b'*32), ('info', 'system_clock_hz', 150000000),
            ('info', 'recovery_boot', True), ('status', 'boot_id', 'b'*32),
            ('info', 'fault_stage', 1), ('info', 'dma_errors', 1),
            ('info', 'engine_diagnostic', 'fault'), ('info', 'rf_render_in_ram', False),
            ('status', 'watermark_utc_ns', '1'), ('status', 'enabled', True),
            ('status', 'state', 'failed'), ('status', 'storage_healthy', False),
            ('status', 'last_error', 'DEVICE_FAULT'),
            ('wtp', 'owner_id', 'b'*32), ('wtp', 'output_active', True),
            ('wtp', 'job_id', 'b'*32), ('wtp', 'state', 'running')):
            changed = copy.deepcopy(old)
            target = changed['info'] if section == 'info' else (
                changed['info']['status'] if section == 'status' else changed['wtp']['STATUS'])
            target[key] = value
            with self.subTest(section=section, key=key), self.assertRaises(ValueError):
                admit(changed, old)

    def test_guard_disabling_relocation_and_faults(self):
        old = baseline()
        for core in (0, 1):
            for suffix, bad in (('guard_valid', 0), ('guard_valid', True),
                                 ('guard_bottom', 0x20002000), ('guard_limit', 0),
                                 ('fault_status', 0x100000)):
                changed = copy.deepcopy(old)
                changed['info'][f'core{core}_stack_{suffix}'] = bad
                with self.subTest(core=core, suffix=suffix), self.assertRaises(ValueError):
                    admit(changed, old)

    def test_variants_never_enable_schedules_or_change_station(self):
        original = dict(version=1, enabled=False, expires_utc_s=0,
                        station={'callsign':'AA0NT', 'locator':'EM18', 'power_dbm':20},
                        schedules=[{'period_s':120, 'phase_s':0}], wifi={'ssid':'original'})
        wifi = dict(ssid='WsprryPico-Phase115', password='test-only-password', ntp_ipv4='clock.phase115.test')
        for variant in ('original', 'test', 'schedule-variant'):
            value, wire = configuration(original, wifi, variant)
            self.assertFalse(value['enabled'])
            self.assertEqual(value['station'], original['station'])
            self.assertEqual(value['wifi'], original['wifi'] if variant == 'original' else wifi)
            self.assertEqual(value['schedules'][0]['phase_s'], 1 if variant == 'schedule-variant' else 0)
            self.assertTrue(wire.startswith(b'CONFIG ') and wire.endswith(b'\n'))
        self.assertEqual(original['schedules'][0]['phase_s'], 0)
        for change in ({'enabled':True}, {'expires_utc_s':1}):
            with self.assertRaises(ValueError): configuration(dict(original, **change), wifi, 'test')

    def test_wrong_network_rejected(self):
        original = dict(enabled=False, expires_utc_s=0, schedules=[{'period_s':120,'phase_s':0}])
        wifi = dict(ssid='WsprryPico-Phase115', password='test-only-password', ntp_ipv4='clock.phase115.test')
        for key, bad in (('ssid','ordinary-LAN'), ('ntp_ipv4','8.8.8.8'), ('password','short')):
            with self.assertRaises(ValueError):
                configuration(original, dict(wifi, **{key:bad}), 'test')

    def state(self):
        return dict(deadline_monotonic_ns=time.monotonic_ns()+600_000_000_000,
                    pending=None, blocked=False,
                    counts={'config':0,'wifi-off':0,'wifi-on':0,'heap-probe':0})

    def test_reserve_final_write_and_bound_cycles(self):
        state = self.state(); state['counts']['config'] = 31
        authorize(state, 'config', 'original')
        with self.assertRaises(ValueError): authorize(state, 'config', 'test')
        state['counts']['config'] = 32
        with self.assertRaises(ValueError): authorize(state, 'config', 'original')
        for action, limit in (('wifi-off',3), ('wifi-on',3), ('heap-probe',64)):
            state = self.state(); state['counts'][action] = limit-1
            authorize(state, action, None)
            state['counts'][action] = limit
            with self.assertRaises(ValueError): authorize(state, action, None)

    def test_unresolved_deadline_and_counter_mutations(self):
        for key, value in (('pending',{'action':'config'}), ('blocked',True),
                           ('deadline_monotonic_ns',0), ('deadline_monotonic_ns',2**63)):
            state = self.state();state[key]=value
            with self.assertRaises(ValueError): authorize(state,'config','test')
        for count in (-1,True,1.5):
            state = self.state();state['counts']['config']=count
            with self.assertRaises(ValueError): authorize(state,'config','test')


if __name__ == '__main__': unittest.main()
