#!/usr/bin/env python3
"""Hardware-free adversarial checks for R1 identity, normal actions and comparisons."""
import copy
import sys
import tempfile
import struct
import json
from unittest.mock import patch
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_load import audit_normal_browser, normal_response
from phase11_5_device_fixture import candidate_images, IMAGES, reconciled_boots
from phase11_5_device_management import SOURCE, R1_SOURCE
from phase11_5_r1 import matched_quiet, resources, validate_fixture_dns, main, R1_HELPERS


def normal_rows():
    rows=[]
    def add(kind,value,stamp):rows.append(dict(kind=kind,value=value,monotonic_ns=stamp))
    page=['/','/api/v1/capabilities','/api/v1/status','/api/v1/config']
    actions=sorted([(0,'initialize',page),(150,'reload',page)]+
                   [(n,'refresh',['/api/v1/status']) for n in (30,70,110,190,230,270)])
    for index,(offset,action,paths) in enumerate(actions):
        stamp=offset*10**9
        add('browser_action_start',dict(index=index,action=action,paths=paths,scheduled_monotonic_ns=stamp),stamp)
        for path in paths:
            add('browser_get',dict(path=path,began_monotonic_ns=stamp),stamp+10**8);stamp+=10**8
        add('browser_action_finish',dict(index=index,action=action),stamp)
    return rows


class R1Tests(unittest.TestCase):
    def test_dns_failure_stops_before_device_subprocess(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            packet=dict(family='R1',source_revision=R1_SOURCE,rf_jobs=[],runtime_seconds=2400,
                network_runtime_seconds=4200,network_root=str(root),
                case_helper_sha256={name:'packet' for name in R1_HELPERS})
            (root/'packet.json').write_text(json.dumps(packet))
            with patch.object(sys,'argv',['r1','--root',str(root),'--packet-sha256','packet','--run']), \
                 patch('phase11_5_r1.sys.platform','linux'),patch('phase11_5_r1.os.geteuid',return_value=0), \
                 patch('phase11_5_r1.digest',return_value='packet'),patch('phase11_5_r1.Fixture'), \
                 patch('phase11_5_r1.fixture_dns',side_effect=ValueError('DNS absent')), \
                 patch('phase11_5_r1.subprocess.run') as process:
                with self.assertRaisesRegex(ValueError,'R1 incomplete'):main()
                process.assert_not_called()
            result=json.loads((root/'r1-result.json').read_text())
            self.assertEqual(result['status'],'FAILED');self.assertEqual(result['intervals'],{})
            self.assertIn('DNS absent',result['error'])

    def test_dns_admission_rejects_wrong_id_address_error_and_deadline(self):
        question=b'\x05clock\x08phase115\x04test\x00\x00\x01\x00\x01'
        query=struct.pack('!HHHHHH',1234,256,1,0,0,0)+question
        reply=struct.pack('!HHHHHH',1234,0x8580,1,1,0,0)+question+b'\xc0\x0c\x00\x01\x00\x01'+struct.pack('!IH',30,4)+bytes((10,77,15,1))
        value=dict(query_hex=query.hex(),reply_hex=reply.hex(),peer=['10.77.15.1',53],local_address='10.77.15.2',elapsed_ns=100)
        validate_fixture_dns(value)
        for mutate in (lambda v:v.update(reply_hex=(b'xx'+reply[2:]).hex()),
            lambda v:v.update(reply_hex=(reply[:-1]+b'\x02').hex()),
            lambda v:v.update(reply_hex=(reply[:3]+b'\x83'+reply[4:]).hex()),
            lambda v:v.update(reply_hex=reply[:-1].hex()),
            lambda v:v.update(local_address='127.0.0.1'),
            lambda v:v.update(elapsed_ns=3_000_000_001)):
            bad=copy.deepcopy(value);mutate(bad)
            with self.assertRaises(ValueError):validate_fixture_dns(bad)

    def test_reconciled_reboots_still_require_original_idle_state(self):
        def inventory(revision,boot):
            return dict(info=dict(revision=revision,recovery_boot=False,
                fault_stage=0,fault_hash=0,fault_pc=0,fault_status=0,
                status=dict(state='empty',output_active=False,enabled=False,last_error=None,
                    storage_healthy=True,engine='inhibited-standalone-simulator',configured=True,
                    station={},schedules=[],watermark_utc_ns='0'),
                network=dict(station_mac='mac',configured_hostname='name',control_configured=True)),
                wtp=dict(STATUS=dict(boot_id=boot,state='empty',output_active=False,owner_id=None,job_id=None)))
        a=inventory('802c91a7b86e-dirty','a');b=inventory('dbf1d86f0885-dirty','b')
        packet=dict(initial_a_boot_id='a',initial_b_boot_id='b',prior_boot_reconciliation=dict(
            reason='User confirmed rebooting both Picos between campaigns',
            a_inventory='/a',a_sha256='hash',b_inventory='/b',b_sha256='hash'))
        def exercise(current_a):
            with patch('phase11_5_device_fixture.digest',return_value='hash'), \
                 patch('phase11_5_device_fixture.finished',side_effect=[current_a,a,b,b]):
                reconciled_boots(packet,Path('/prior'))
        exercise(a)
        for mutate in (lambda v:v['info'].update(fault_status=1),
            lambda v:v['wtp']['STATUS'].update(owner_id='foreign'),
            lambda v:v['info']['status'].update(enabled=True),
            lambda v:v['info']['status'].update(station={'changed':True}),
            lambda v:v['wtp']['STATUS'].update(boot_id='different')):
            bad=copy.deepcopy(a);mutate(bad)
            with self.assertRaises(ValueError):exercise(bad)
        with self.assertRaises(ValueError):reconciled_boots({},Path('/prior'))

    def test_resource_history_is_independent_wtp_not_console(self):
        # Console INFO intentionally has no terminal_records member.
        info=dict(status=dict(engine='inhibited-standalone-simulator',boot_id='boot'),
            heap_sample_observed_us='1000000',allocator_sample_time_us='1',system_clock_hz=150000000,
            heap_capacity_bytes=100000,allocator_peak_bytes=100,allocator_largest_successful_request_bytes=20,
            allocator_max_sample_us=1,allocator_max_entry_us=2,core0_stack_used_bytes=100,
            core0_stack_scan_us=1,heap_sample_cost_us=1,heap_allocated_bytes=100,heap_arena_bytes=200,
            heap_arena_free_bytes=100,heap_free_chunks=1,heap_top_releasable_bytes=100,
            allocator_failures='0',tls_allocation_failures=0,network={})
        later=dict(info,heap_sample_observed_us='2000000',allocator_sample_time_us='11')
        rows=[dict(kind='info',monotonic_ns=100,value=dict(began_monotonic_ns=0,value=info)),
              dict(kind='info',monotonic_ns=200,value=dict(began_monotonic_ns=100,value=later)),
              dict(kind='status',value=dict(value=dict(terminal_records=[])))]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'rows'
            path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            self.assertEqual(resources(path)['terminal_records'],[])
            rows[-1]['value']['value']['terminal_records']=[{}]
            path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            with self.assertRaises(ValueError):resources(path)

    def test_candidate_registry_is_closed_and_preserves_legacy(self):
        self.assertEqual(candidate_images(SOURCE),IMAGES)
        self.assertEqual(candidate_images(R1_SOURCE)['original'],IMAGES['original'])
        self.assertNotEqual(candidate_images(R1_SOURCE)['physical'],IMAGES['physical'])
        for value in ('e20ae8bea2d5',R1_SOURCE+'-dirty','arbitrary'):
            with self.assertRaises(ValueError):candidate_images(value)

    def test_normal_initialization_rejects_error_and_incomplete_resources(self):
        normal_response('/',b'<style>css</style><script>js</script>','boot')
        normal_response('/api/v1/capabilities',json.dumps(dict(api_version=1,wtp={},features={},active_job_connections=True)).encode(),'boot')
        normal_response('/api/v1/config',json.dumps(dict(config=dict(enabled=False,station={},schedules=[],wifi=dict(password=None)))).encode(),'boot')
        for path,body in (('/',b'<html>error</html>'),('/api/v1/capabilities',b'{"ok":false}'),
                          ('/api/v1/capabilities',b'{}'),('/api/v1/config',b'{"config":null}')):
            with self.assertRaises(ValueError):normal_response(path,body,'boot')

    def test_complete_normal_actions_and_whole_latency(self):
        value=audit_normal_browser(normal_rows(),300,0)
        self.assertEqual(value['actions'],8);self.assertEqual(value['refresh_actions'],6)
        self.assertAlmostEqual(max(value['action_latencies_seconds']),.4)

    def test_missing_extra_wrong_order_and_late_actions_fail(self):
        original=normal_rows()
        for index in range(len(original)):
            rows=copy.deepcopy(original);rows.pop(index)
            with self.assertRaises((ValueError,KeyError)):audit_normal_browser(rows,300,0)
        for mutate in (
            lambda r:r.append(r[-2]),
            lambda r:r[1]['value'].update(path='/style.css'),
            lambda r:r[0]['value'].update(scheduled_monotonic_ns=1_000_001),
            lambda r:r[0].update(monotonic_ns=15_000_000_001),
            lambda r:r[-1].update(monotonic_ns=301_000_000_000)):
            rows=copy.deepcopy(original);mutate(rows)
            with self.assertRaises(ValueError):audit_normal_browser(rows,300,0)

    def test_quiet_rejects_boot_history_network_failures_and_growth(self):
        before=dict(boot='a',clock_hz=138000000,terminal_records=[],
            network=dict(ipv4='10.77.15.10',ntp_address='10.77.15.1',stable_hostname='name',
                         mdns_state='active',control_listening=True),
            last=dict(heap_allocated_bytes=20000,allocator_failures='1',tls_allocation_failures=0))
        self.assertEqual(matched_quiet(before,copy.deepcopy(before)),0)
        for mutate in (lambda v:v.update(boot='b'),lambda v:v.update(terminal_records=[{}]),
            lambda v:v['network'].update(ipv4='10.77.15.20'),
            lambda v:v['last'].update(allocator_failures='2'),
            lambda v:v['last'].update(heap_allocated_bytes=21025)):
            value=copy.deepcopy(before);mutate(value)
            with self.assertRaises(ValueError):matched_quiet(before,value)


if __name__=='__main__':unittest.main()
