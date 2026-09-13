"""Hardware-free retained-baseline credential and terminal-cleanup admission."""
import copy
import contextlib
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase11_5_network_fixture import fixture_wifi
from phase11_5_r3_retained import terminal_admission, BOOT, PRIOR_JOB


class RetainedTests(unittest.TestCase):
    def test_packet_cannot_expand_rf_or_recovery_scope(self):
        import phase11_5_r3_retained as m
        from phase11_5_r3_tls_plan import jobs, CASES
        p = dict(schema=m.SCHEMA_RETAINED, family='R3', r3_scope=m.SCHEMA, source_revision=m.SOURCE,
                 initial_a_boot_id=m.BOOT, host_boot_id=m.HOST_BOOT, serial=m.SERIAL, device_id=m.DEVICE,
                 configuration_writes=0, flashes=0, heap_probes=0, network_runtime_seconds=1800,
                 network_restoration_seconds=600, maximum_renewals=12, maximum_tcp_connections=12,
                 nominal_seconds=300, observation_seconds=360, time_server_mdns=True, time_server_dns=False,
                 retained_wifi_sha256='fc42b65f177e62afc6664ffc1f13bc14e7711d7cd51c9d191c2e0c580d620764',
                 nonce='1'*32, owner_id='2'*32, inventory_session_id='3'*32,
                 b_inventory_session_id='4'*32, cleanup_owner_id='5'*32,
                 finite_job_templates=jobs('1'*32), pressure_cases=[list(c) for c in CASES])
        self.assertEqual(m.validate(p), p)
        for change in [dict(flashes=1), dict(configuration_writes=1), dict(heap_probes=1),
                       dict(network_runtime_seconds=1801), dict(maximum_tcp_connections=13),
                       dict(observation_seconds=359), dict(initial_a_boot_id='6'*32),
                       dict(cleanup_owner_id=p['owner_id']), dict(inventory_session_id='0'*32),
                       dict(wifi_recovery={'maximum_off':2}), dict(finite_job_templates=jobs('7'*32))]:
            with self.assertRaises(ValueError): m.validate(p | change)

    def test_wifi_cycle_preserves_idle_state_and_never_retries_uncertain_command(self):
        import phase11_5_r3_retained as module
        original = json.loads((Path(__file__).parent/'fixtures/phase11_5_r3_terminal_baseline.json').read_text())['inventory']
        on = copy.deepcopy(original)
        on['wtp']['STATUS'].update(state='empty', job_id=None)
        on['info']['status']['state'] = 'empty'
        on['info']['network'].update(enabled=True, link_status=-3, ipv4='', withdrawal_pending=False, requested_enabled=None)
        off = copy.deepcopy(on); off['info']['network']['enabled'] = False
        for failed in (False, True):
            with tempfile.TemporaryDirectory() as temp:
                dut = object.__new__(module.RetainedDUT)
                dut.root, dut.baseline, dut.packet = Path(temp), on, {'wifi_recovery': {'scope': 'test'}}
                dut.check_current = Mock(side_effect=[on, on, off, off, on])
                replies = [on['info'], TimeoutError('lost ACK')] if failed else [on['info'], {'ok': True}, off['info'], {'ok': True}]
                with patch.object(module, 'exclusive_port', return_value=contextlib.nullcontext(123)), \
                     patch.object(module, 'exchange', side_effect=replies) as exchange:
                    if failed:
                        with self.assertRaises(TimeoutError): dut.recover_wifi()
                    else:
                        dut.recover_wifi()
                    commands = [call.args[1] for call in exchange.call_args_list]
                self.assertEqual(commands, [b'INFO\n', b'WIFI OFF\n'] if failed else
                                 [b'INFO\n', b'WIFI OFF\n', b'INFO\n', b'WIFI ON\n'])
                state = json.loads((dut.root/'wifi-recovery.json').read_text())
                self.assertEqual(state['off'], 1)
                self.assertEqual(state['on'], 0 if failed else 1)
                self.assertEqual(state.get('pending'), 'off' if failed else None)

    def test_retained_wifi_requires_exact_input_without_generating_password(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value = dict(ssid='WsprryPico-Phase115', password='a'*32, ntp_ipv4='time.local')
            raw = json.dumps(value).encode(); (root/'retained-wifi.json').write_bytes(raw)
            p = dict(schema='phase11.5-r3-retained-fixture-v1', family='R3', configuration_writes=0,
                     retained_wifi_sha256=hashlib.sha256(raw).hexdigest())
            with patch('phase11_5_network_fixture.secrets.token_hex', side_effect=AssertionError('Generated password')):
                self.assertEqual(fixture_wifi(root, p, True, False), value)
                for change in (dict(configuration_writes=1),dict(schema='old'),dict(family='R2'),
                               dict(retained_wifi_sha256='f'*64)):
                    with self.assertRaises(ValueError):fixture_wifi(root, p|change, True, False)
                (root/'retained-wifi.json').write_text(json.dumps(value|dict(password='changed')))
                with self.assertRaises(ValueError):fixture_wifi(root,p,True,False)

    def test_terminal_cleanup_admission_from_recorded_a1b_inventory(self):
        path = Path(__file__).parent/'fixtures/phase11_5_r3_terminal_baseline.json'
        data = json.loads(path.read_text()); value = data['inventory']
        self.assertTrue(terminal_admission(value, value, {PRIOR_JOB}))
        for field, replacement in [('state','running'),('output_active',True),('owner_id','f'*32),
                                   ('job_id','f'*32),('boot_id','f'*32),('terminal_records',[])]:
            bad=copy.deepcopy(value);bad['wtp']['STATUS'][field]=replacement
            with self.assertRaises(ValueError):terminal_admission(bad,value,{PRIOR_JOB})
        empty=copy.deepcopy(value);empty['wtp']['STATUS'].update(state='empty',job_id=None)
        empty['info']['status']['state']='empty'
        self.assertFalse(terminal_admission(empty,value,{PRIOR_JOB}))

    def test_retained_no_run_has_no_file_or_hardware_access(self):
        import phase11_5_r3_retained as module
        with patch.object(sys,'argv',['retained','--root','/absent','--packet-sha256','absent']), \
                patch.object(module.Path,'resolve',side_effect=AssertionError('File access')):
            module.main()


if __name__ == '__main__':unittest.main()
