"""Actual unattended runner success and adverse cleanup with deterministic hardware adapters."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from led_closeout.plan import BOARDS, IMAGES, make_plan, validate_plan
from led_closeout.candidates import pins
from led_closeout.runner import Evidence, Runner, admit, quiescent, save_json
from led_closeout.device import Device, Peer, inventory, validate_manifest, validate_setup
from led_closeout.capture import Captures, storage_reserve
from validate_wtp_contract import loads_strict, SchemaValidator


def manifest():
    return dict(images={name: dict(engine='pio-dma-gp2' if rf else 'inhibited-standalone-simulator',
        acceptance=a, selection=s, gp14=g, pins=pins(s), revision='candidate')
        for name, (rf,a,s,g) in IMAGES.items()})


class Fake:
    def __init__(self, e, fault=None):
        self.e, self.fault, self.t = e, fault, 0
        self.images, self.boots, self.states = {}, {}, {}
        self.engaged, self.restored, self.aborted, self.commands = [], [], [], []
        self.owner, self.job, self.started, self.lease_end = None, None, None, 0
        self.capture_active, self.admissions, self.renewals = False, 0, 0
        self.fail_on, self.gp14, self.loaded_at = False, False, 0
        self.setup = {}
        self.clock_reads = 0

    def now(self): return self.t
    def sleep(self, seconds): self.t += seconds
    def preflight(self, m, board, fixture):
        if self.fault == 'preflight': raise ValueError('occupied entry')
        self.dut, self.fixture = board, fixture
        self.engaged = list(filter(None, (board, fixture)))
    def deploy(self, board, image):
        self.images[board] = image
        self.boots[board] = str(self.t)+str(len(self.commands))+'boot'
        self.states[board] = 'empty'
        self.owner, self.job, self.started = None, None, None
        self.fail_on = self.gp14 = False
    def info(self, board):
        state = self.states[board]
        if self.started is not None:
            if state == 'armed' and self.t >= self.started:
                state = ('missed' if self.fault == 'launch_missed' else 'failed') if self.fail_on else 'running'
            if state == 'running' and self.t >= self.started+int(self.job['total_duration_ns'])/1e9:
                state = 'complete'
            if self.fault == 'premature' and state == 'running' and self.t >= self.started+.2:
                state = 'complete'
            self.states[board] = state
        if self.owner and self.t >= self.lease_end and self.owner != 'e'*32:
            self.owner = None
        image = self.images[board]
        if self.fault == 'transient_stop' and self.started is not None and self.job and self.t >= self.started+int(self.job['total_duration_ns'])/1e9 and self.t < self.started+int(self.job['total_duration_ns'])/1e9+.3:
            state='running';self.states[board]=state
        active = state == 'running' and image['engine'] == 'pio-dma-gp2'
        if self.fault == 'transient_stop' and self.started is not None and self.job and self.t >= self.started+int(self.job['total_duration_ns'])/1e9:
            active=False
        if self.fault == 'active_terminal' and state == 'complete': active = True
        boot = self.boots[board] if self.fault != 'boot' or state != 'running' else 'rebooted'
        return dict(ok=True, system_clock_hz=138000000, device_id=BOARDS[board]['device_id'], revision=image['revision'],
            led_boot_pins=image['pins'], led_acceptance=image['acceptance'], led_selection=image['selection'],
            access_state='healthy', rf_safety_inhibited=self.gp14, led_rejected_writes=int(self.fail_on),
            indicator_output_known=True, indicator_output_on=active and image["selection"] != 3,
            indicator_pin_readback_known=self.fault != 'gpio_unknown' and image['selection'] != 3,
            indicator_pin_readback_error=-1 if self.fault == 'gpio_unknown' or image['selection'] == 3 else 0,
            indicator_pin_readback_on=None if self.fault == 'gpio_unknown' or image['selection'] == 3 else
                (active and self.fault != 'gpio_mismatch'),
            indicator_onboard_readback_known=True, indicator_onboard_readback_error=0,
            indicator_onboard_readback_on=active and image['selection'] != 3,
            tx_indicator_ready=active and image["selection"] != 3,
            tx_indicator_requested=active and image["selection"] != 3, status=dict(boot_id=boot, output_active=active,
            enabled=False, storage_healthy=True, state=state, engine=image['engine'],
            owner_id=self.owner, job_id=self.job['job_id'] if self.job else None))
    def hello(self): return dict(boot_id=self.boots[self.dut])
    def command(self, board, command):
        self.commands.append((board, command))
        if command == 'FAIL': self.fail_on=True
        if command == 'SCHEDULE':
            assert self.e.state['jobs'] > self.admissions
            self.admissions += 1
            case=next(c for c in make_plan()['cases'] if c['action']=='standalone')
            self.job, self.owner = case['job'], 'e'*32
            self.started = self.t+10
            self.states[board]='armed'
        if command == 'STOP':
            self.states[board]='empty';self.owner=None;self.job=None
        if command == 'HOLD':
            if self.fault == 'fixture': raise TimeoutError('fixture timeout')
            self.states[self.dut]='aborted';self.gp14=True;self.owner=None
            if self.fault == 'slow_fixture':self.t+=3
    def request(self, op, body):
        clock_snapshot=int(self.t*1e9)
        if op == 'GET_CLOCK':
            self.clock_reads += 1
            if self.fault == 'boot_clock_listener' and self.clock_reads <= 2:
                raise ValueError(('consumer Plain LAN WTP unavailable: listener/time not ready',
                                  'consumer station address unavailable')[self.clock_reads-1])
            if self.fault == 'clock_identity':raise ValueError('WTP device identity')
        if self.fault == 'slow_transport':
            if self.owner and clock_snapshot/1e9 >= self.lease_end:self.owner=None
            self.t+=2.5
        if op == 'CLAIM': self.owner=body['owner_id'];self.lease_end=clock_snapshot/1e9+body['lease_ms']/1000
        if op == 'RENEW':
            if self.owner is None:raise ValueError('owner already cleared')
            if self.fault == 'lease' and self.started is not None: raise TimeoutError('lost renewal')
            self.renewals += 1;self.lease_end=clock_snapshot/1e9+body['lease_ms']/1000
        if op == 'LOAD':
            self.job=body;self.states[self.dut]='loaded'
            return dict(job_id=body['job_id'])
        if op == 'GET_CLOCK': return dict(state='unsynchronized' if self.fault == 'clock' else 'synchronized', leap='normal', uncertainty_ns='1000', utc_now_ns=str(clock_snapshot))
        if op == 'ARM':
            assert self.e.state['jobs'] > self.admissions
            self.admissions += 1
            self.started=int(body['start_utc_ns'])/1e9
            if self.fault == 'slow_transport' and self.started <= self.t:raise ValueError('start already passed')
            self.states[self.dut]='armed'
            if self.fault == 'arm': raise TimeoutError('ambiguous ARM')
            if self.fault == 'premature_never_ran': self.states[self.dut]='complete'
        if op == 'ABORT': self.states[self.dut]='aborted'
        if op == 'RELEASE': self.owner=None;self.job=None;self.states[self.dut]='empty'
        return {}
    def start_captures(self, root, duration):
        self.capture_active=True
        if self.fault == 'capture_start': raise ValueError('camera readiness')
    def captures_healthy(self):
        if self.fault == 'capture_mid' and self.started is not None and self.t >= self.started:
            raise ValueError('camera exit')
    def finish_captures(self):
        if self.fault == 'capture_final': raise ValueError('receiver hash')
    def stop_captures(self): self.capture_active=False
    def abort(self, board):
        if board in self.engaged:
            self.aborted.append(board);self.owner=None
            self.states[board]='aborted'
    def restore(self, board, image):
        if board in self.engaged:
            self.restored.append(board)
            if self.fault == 'restore' and board == self.dut: raise ValueError('journal mismatch')
            return 'VERIFIED_INHIBITED'
        return 'UNCHANGED'


class RunnerTests(unittest.TestCase):
    def test_controlled_launch_miss_is_a_non_rf_failure(self):
        e,fake,_=self.exercise('launch_missed')
        Runner(make_plan(),manifest(),'A',fake,e,cases=['led_write_launch_failure']).run()
        self.assertEqual(e.state['jobs'],1)
        self.assertEqual(e.state['cleanup'],'VERIFIED_INHIBITED')
        self.assertEqual(e.state['attempts'][0]['result'],'AUTOMATION_PASS_PHYSICAL_REVIEW_PENDING')

    def test_budget_continuation_requires_definite_terminal_and_keeps_spent_charge(self):
        from led_closeout.runner import carry_budget
        old,fake,_=self.exercise();case=make_plan()['cases'][0];boot='1'*32
        old.charge(case,boot);old.state.update(result='STOP',cleanup='VERIFIED_INHIBITED');old.save()
        old.event('stale_wtp_message',dict(event='JOB_STATE',boot_id=boot,
                 body=dict(job_id=case['job']['job_id'],state='running',output_active=True)))
        new=Evidence(old.root.parent/'continuation',make_plan(),'A',None)
        with self.assertRaisesRegex(ValueError,'ambiguous'):carry_budget(new,old.root)
        self.assertEqual(new.state['jobs'],0)
        old.event('stale_wtp_message',dict(event='JOB_STATE',boot_id=boot,
                 body=dict(job_id=case['job']['job_id'],state='complete',output_active=False)))
        carry_budget(new,old.root)
        backend=Fake(new)
        Runner(make_plan(),manifest(),'A',backend,new,cases=['warmup']).run()
        self.assertEqual(new.state['jobs'],2)
        self.assertEqual(new.state['rf_ns'],2*case['charge_ns'])
        self.assertEqual(new.state['prior_budget']['jobs'],1)

    def test_clock_listener_readiness_retries_but_identity_error_stops_before_admission(self):
        e,fake,_=self.exercise('boot_clock_listener')
        Runner(make_plan(),manifest(),'A',fake,e,cases=['warmup']).run()
        self.assertEqual(e.state['jobs'],1)
        self.assertEqual(fake.admissions,1)
        e,fake,_=self.exercise('clock_identity')
        with self.assertRaisesRegex(ValueError,'unexpected clock readiness'):
            Runner(make_plan(),manifest(),'A',fake,e,cases=['warmup']).run()
        self.assertEqual(e.state['jobs'],0)
        self.assertEqual(fake.admissions,0)
        self.assertEqual(e.state['cleanup'],'VERIFIED_INHIBITED')

    def test_reboot_endpoint_absence_is_retryable_but_occupied_endpoint_is_not(self):
        obj=Device.__new__(Device)
        message='Endpoint occupied or ownership check unavailable'
        with patch('led_closeout.device.Path.exists',return_value=False), patch('led_closeout.device.exclusive_port') as port:
            with self.assertRaises(FileNotFoundError):obj.console('B','INFO')
            port.assert_not_called()
        with patch('led_closeout.device.Path.exists',return_value=True), patch('led_closeout.device.exclusive_port',side_effect=ValueError(message)):
            with self.assertRaisesRegex(ValueError,'Endpoint occupied'):obj.console('B','INFO')
        with patch('led_closeout.device.Path.exists',side_effect=[True,False]), patch('led_closeout.device.exclusive_port',side_effect=ValueError(message)):
            with self.assertRaises(FileNotFoundError):obj.console('B','INFO')

    def test_onboard_gpio_subset_has_no_external_or_stop_fixture_dependency(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        plan=make_plan();e=Evidence(Path(directory.name)/'run',plan,'B',None)
        fake=Fake(e);fake.setup={'evidence_mode':'gpio-readback'}
        chosen=[c['id'] for c in plan['cases'] if c['id'] not in ('external_high','external_low','gp14_cutoff')]
        result=Runner(plan,manifest(),'B',fake,e,cases=chosen).run()
        self.assertEqual(result['jobs'],13)
        self.assertEqual(result['result'],'PASS_GPIO_FUNCTIONAL_RF_REVIEW_PENDING')
        self.assertEqual(fake.restored,['B'])
        self.assertTrue(all(a['result']=='PASS_GPIO_FUNCTIONAL' for a in result['attempts']))

    def test_gpio_mismatch_and_unknown_stop_without_false_pass(self):
        for failure in ('gpio_mismatch','gpio_unknown'):
            e,fake,_=self.exercise(failure,steps=(3,))
            fake.setup={'evidence_mode':'gpio-readback'}
            runner=Runner(make_plan(),manifest(),'A',fake,e,cases=['warmup'])
            with self.assertRaisesRegex(ValueError,'GPIO readback'):
                runner.run()
            self.assertEqual(e.state['result'],'STOP')
            self.assertEqual(fake.restored,['A'])
            self.assertNotEqual(e.state['attempts'][-1]['result'] if e.state['attempts'] else None,
                                'PASS_GPIO_FUNCTIONAL')

    def test_case_selection_rejects_unknown_duplicates_empty_and_missing_image(self):
        e,fake,_=self.exercise()
        for cases in ([],['bad'],['warmup','warmup'],['gp14_cutoff']):
            with self.assertRaises(ValueError):Runner(make_plan(),manifest(),'A',fake,e,cases=cases)
        m=manifest();del m['images']['onboard']
        with self.assertRaises(ValueError):Runner(make_plan(),m,'A',fake,e,cases=['warmup'])
        self.assertEqual(fake.engaged,[])

    def exercise(self, fault=None, steps=(3,4,5)):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        plan=make_plan();e=Evidence(Path(directory.name)/'run',plan,'A','B')
        fake=Fake(e,fault)
        runner=Runner(plan,manifest(),'A',fake,e,fixture='B',steps=steps)
        return e,fake,runner

    def test_full_matrix_runs_once_and_restores_both(self):
        e,fake,runner=self.exercise()
        result=runner.run()
        self.assertEqual(result['jobs'],16)
        self.assertEqual(len(fake.restored),2)
        self.assertEqual(fake.admissions,16)
        self.assertGreater(fake.renewals,0)
        self.assertEqual(result['cleanup'],'VERIFIED_INHIBITED')
        self.assertEqual(result['physical_acceptance'],'NOT_ASSESSED')
        self.assertFalse(fake.capture_active)
        self.assertIn(('B','HOLD'),fake.commands)

    def test_hardware_completion_before_foreground_status_reconciles(self):
        e,fake,runner=self.exercise('transient_stop',steps=(3,))
        runner.run()
        self.assertEqual(e.state['result'],'AUTOMATION_PASS_PHYSICAL_REVIEW_PENDING')

    def test_slow_fixture_reply_does_not_renew_cleared_owner(self):
        e,fake,runner=self.exercise('slow_fixture',steps=(5,))
        runner.run()
        self.assertEqual(e.state['result'],'AUTOMATION_PASS_PHYSICAL_REVIEW_PENDING')

    def test_bounded_transport_delay_preserves_lease_and_future_start(self):
        e,fake,runner=self.exercise('slow_transport')
        runner.run()
        self.assertEqual(e.state['result'],'AUTOMATION_PASS_PHYSICAL_REVIEW_PENDING')

    def test_adversarial_faults_stop_and_restore(self):
        for fault in ('clock','capture_start','capture_mid','capture_final','boot','arm','lease','fixture',
                      'active_terminal','premature','premature_never_ran','restore'):
            with self.subTest(fault=fault):
                e,fake,runner=self.exercise(fault)
                with self.assertRaises((ValueError,TimeoutError)): runner.run()
                self.assertEqual(e.state['result'],'STOP')
                self.assertEqual(fake.restored,['A','B'])
                self.assertFalse(fake.capture_active)
                self.assertLessEqual(fake.admissions,16)
                if fault=='arm': self.assertEqual(fake.admissions,1)
                if fault=='restore': self.assertEqual(e.state['cleanup'],'STOP_UNCERTAIN')

    def test_preflight_refusal_preserves_entry(self):
        e,fake,runner=self.exercise('preflight')
        with self.assertRaises(ValueError):runner.run()
        self.assertFalse(fake.engaged)
        self.assertEqual(e.state['cleanup'],'UNCHANGED_NO_MUTATIONS')

    def test_packet_and_accounting_reject_mutations(self):
        p=make_plan()
        changed=copy.deepcopy(p);changed['cases'][0]['job']['events'][0]['rf_on']=1
        with self.assertRaises(ValueError):validate_plan(changed)
        for key,value in (('receiver_serial','wrong'),('operator_step',1)):
            changed=copy.deepcopy(p);changed[key]=value
            with self.assertRaises(ValueError):validate_plan(changed)
        e,fake,runner=self.exercise()
        case=p['cases'][0]
        e.charge(case,'boot')
        with self.assertRaises(ValueError):e.charge(case,'boot')
        e.state['jobs']=18
        with self.assertRaises(ValueError):e.charge(p['cases'][1],'boot')
        e.state['jobs']=0;e.state['rf_ns']=600000000000
        with self.assertRaises(ValueError):e.charge(p['cases'][1],'boot')
        self.assertEqual(json.loads((e.root/'state.json').read_text())['jobs'],1)

    def test_all_jobs_obey_normative_schema(self):
        schema=loads_strict((ROOT/'docs/protocol/wtp-1.schema.json').read_text())
        v=SchemaValidator(schema)
        for case in make_plan()['cases']:
            request=dict(protocol='WTP/1',type='request',session_id='1'*32,request_id='2'*32,
                         op='LOAD',body=case['job'])
            self.assertEqual(v.errors(request,schema),[],case['id'])

    def test_identity_engine_pin_and_active_refusal(self):
        e,fake,r=self.exercise();fake.preflight(None,'A','B');image=manifest()['images']['onboard'];fake.deploy('A',image)
        info=fake.info('A')
        for key,value in (('device_id','wrong'),('revision','wrong'),('led_boot_pins',pins(1))):
            wrong=copy.deepcopy(info);wrong[key]=value
            with self.assertRaises(ValueError):admit(wrong,BOARDS['A'],image)
        for key,value in (('output_active',True),('owner_id','other'),('enabled',True)):
            wrong=copy.deepcopy(info);wrong['status'][key]=value
            with self.assertRaises(ValueError):quiescent(wrong,BOARDS['A'],image)
        with self.assertRaises(ValueError):admit(info,BOARDS['A'],image,'stale')

    def test_cli_defaults_to_offline_packet(self):
        import subprocess
        result=subprocess.run([sys.executable,str(ROOT/'scripts/led_closeout.py')],
                              capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(result.stdout),make_plan())

    def test_readback_config_rejects_torn_records_and_occupied_pins(self):
        from led_closeout.device import snapshot_config, FLASH_SIZE
        import struct,zlib
        data=bytearray(b'\xff'*FLASH_SIZE)
        def append(config):
            record=bytearray(b'\xff'*2048)
            body=json.dumps(config).encode()
            struct.pack_into('<QQI',record,0,0x32524f5453505757,1,len(body))
            record[32:32+len(body)]=body
            struct.pack_into('<I',record,2044,zlib.crc32(record[:-4]))
            data[0x3fb000:0x3fb800]=record
        config=dict(version=1,enabled=False,pins=pins(0))
        append(config)
        self.assertEqual(snapshot_config(data),config)
        data[0x3fb020]^=1
        with self.assertRaises(ValueError):snapshot_config(data)
        config['pins']=pins(1);append(config)
        with self.assertRaises(ValueError):snapshot_config(data)
        config['pins']=pins(0);config['enabled']=True;append(config)
        with self.assertRaises(ValueError):snapshot_config(data)

    def test_console_authority_makes_cleanup_independent_of_lan(self):
        obj=Device.__new__(Device)
        value=dict(status=dict(state='empty',output_active=False,boot_id='boot',owner_id=None,job_id=None))
        obj.console=lambda *a:value
        obj.peer=unittest.mock.Mock(side_effect=OSError('LAN unavailable'))
        self.assertIs(obj.info('A'),value)
        obj.peer.assert_not_called()

    def test_authority_transition_is_resampled(self):
        obj=Device.__new__(Device)
        from types import SimpleNamespace
        info=dict(status=dict(state='armed',output_active=False,boot_id='boot'))
        settled=dict(status=dict(state='running',output_active=True,boot_id='boot'))
        peer=SimpleNamespace(request=lambda *a:dict(state='running',output_active=True,
            boot_id='boot',owner_id='owner',job_id='job'))
        obj.peer=lambda b:peer
        obj.console=unittest.mock.Mock(side_effect=[info,settled])
        obj.e=SimpleNamespace(event=lambda *a:None)
        self.assertEqual(obj.info('A')['status']['owner_id'],'owner')
        self.assertEqual(obj.console.call_count,2)

    def test_consumer_transport_uses_normal_plain_lan(self):
        from types import SimpleNamespace
        e,_,_=self.exercise()
        obj=Device({},e,ROOT)
        connection=unittest.mock.Mock()
        connection.fileno.return_value=42
        obj.console=lambda *a:dict(device_id=BOARDS['A']['device_id'],
            provisioning_source='consumer_preclock',lan_wtp_mode='plain',lan_wtp_port=31417,lan_wtp_ready=True,
            network=dict(ipv4='192.168.1.47'))
        with patch('led_closeout.device.socket.create_connection',return_value=connection) as connect,              patch('led_closeout.device.exclusive_port') as usb,              patch('led_closeout.device.Peer') as peer:
            peer.return_value.request.return_value=dict(device_id=BOARDS['A']['device_id'])
            obj.peer('A')
            connect.assert_called_once_with(('192.168.1.47',31417),timeout=3)
            usb.assert_not_called()
            obj.close_peer('A')
            connection.close.assert_called_once()

    def test_unready_inventory_records_both_boards_without_inventing_authority(self):
        e,_,_=self.exercise()
        obj=Device({},e,ROOT)
        obj.lock_boards=unittest.mock.Mock()
        def console(board,command):
            self.assertEqual(command,'INFO')
            return dict(ok=True,device_id=BOARDS[board]['device_id'],revision='installed',
                provisioning_source='consumer_preclock',lan_wtp_mode='plain',lan_wtp_port=31417,
                lan_wtp_ready=False,network=dict(ipv4='192.168.1.47'),
                status=dict(boot_id=board,state='empty',output_active=False,clock_state='unsynchronized'))
        obj.console=console
        with patch('led_closeout.device.socket.create_connection') as connect, patch('led_closeout.device.exclusive_port') as usb:
            self.assertFalse(inventory(obj,e,'A','B'))
            connect.assert_not_called();usb.assert_not_called()
        stored=json.loads((e.root/'state.json').read_text())
        self.assertEqual(stored['result'],'READ_ONLY_INVENTORY_PARTIAL')
        self.assertEqual(stored['transport_cleanup'],'CLOSED')
        self.assertEqual(stored['cleanup'],'UNCHANGED')
        self.assertEqual([s['board'] for s in stored['inventory']],['A','B'])
        for summary in stored['inventory']:
            self.assertIn('listener/time not ready',summary['error']['message'])
            self.assertNotIn('owner_id',summary['status'])
            self.assertNotIn('responses',summary)
        self.assertEqual((stored['jobs'],stored['rf_ns']),(0,0))

    def test_inventory_binds_boot_and_engine_and_continues_after_mismatch(self):
        from types import SimpleNamespace
        e,_,_=self.exercise()
        calls=[]
        def info(board,command):
            self.assertEqual(command,'INFO')
            return dict(ok=True,device_id=BOARDS[board]['device_id'],revision='installed',
                        status=dict(boot_id=board,engine='inhibited',output_active=False))
        def peer(board):
            def request(op,body):
                calls.append((board,op))
                return {'HELLO':dict(device_id=BOARDS[board]['device_id'],boot_id=board),
                        'CAPS':dict(engine='inhibited'), 'GET_CLOCK':dict(state='unsynchronized'),
                        'STATUS':dict(boot_id='other' if board=='A' else board,output_active=False),
                        'PING':{}}[op]
            return SimpleNamespace(request=request)
        obj=SimpleNamespace(console=info,peer=peer,lock_boards=lambda *a:None,close=unittest.mock.Mock())
        self.assertFalse(inventory(obj,e,'A','B'))
        self.assertEqual([s['result'] for s in e.state['inventory']],['UNAVAILABLE','COMPLETE'])
        self.assertIn('Boot mismatch',e.state['inventory'][0]['error']['message'])
        self.assertEqual({op for _,op in calls},{'HELLO','CAPS','GET_CLOCK','STATUS','PING'})
        self.assertEqual(len(calls),10)
        obj.close.assert_called_once()
        calls.clear()
        self.assertTrue(inventory(obj,e,'B'))
        self.assertEqual(e.state['result'],'READ_ONLY_INVENTORY')

    def test_inventory_lock_and_cleanup_failures_remain_partial(self):
        from types import SimpleNamespace
        e,_,_=self.exercise()
        obj=SimpleNamespace(lock_boards=unittest.mock.Mock(side_effect=OSError('occupied')),
            console=unittest.mock.Mock(),peer=unittest.mock.Mock(),
            close=unittest.mock.Mock(side_effect=OSError('close failed')))
        self.assertFalse(inventory(obj,e,'A','B'))
        obj.console.assert_not_called();obj.peer.assert_not_called()
        self.assertEqual(e.state['transport_cleanup'],'FAILED')
        self.assertEqual([v['stage'] for v in e.state['errors']],['inventory','transport_cleanup'])
        self.assertEqual(e.state['inventory'],[])

    def test_failed_hello_closes_transport_and_does_not_cache_peer(self):
        e,_,_=self.exercise()
        obj=Device({},e,ROOT)
        connection=unittest.mock.Mock()
        connection.fileno.return_value=42
        obj.console=lambda *a:dict(device_id=BOARDS['A']['device_id'],
            provisioning_source='consumer_preclock',lan_wtp_mode='plain',lan_wtp_port=31417,
            lan_wtp_ready=True,network=dict(ipv4='192.168.1.47'))
        with patch('led_closeout.device.socket.create_connection',return_value=connection), patch('led_closeout.device.Peer') as peer:
            peer.return_value.request.side_effect=ConnectionResetError('reset')
            with self.assertRaises(ConnectionResetError):obj.peer('A')
        connection.close.assert_called_once()
        self.assertEqual(obj.peers,{})
        self.assertEqual(obj.peer_contexts,{})

    def test_inventory_interruption_is_not_a_complete_result(self):
        from types import SimpleNamespace
        e,_,_=self.exercise()
        obj=SimpleNamespace(lock_boards=lambda *a:None,
            console=unittest.mock.Mock(side_effect=KeyboardInterrupt()),close=unittest.mock.Mock())
        with self.assertRaises(KeyboardInterrupt):inventory(obj,e,'A','B')
        stored=json.loads((e.root/'state.json').read_text())
        self.assertEqual(stored['result'],'READ_ONLY_INVENTORY_PARTIAL')
        self.assertEqual(stored['errors'][0]['type'],'KeyboardInterrupt')
        obj.close.assert_called_once()

    def test_transport_event_failure_closes_open_connection(self):
        e,_,_=self.exercise()
        obj=Device({},e,ROOT)
        connection=unittest.mock.Mock()
        connection.fileno.return_value=42
        obj.console=lambda *a:dict(device_id=BOARDS['A']['device_id'],
            provisioning_source='consumer_preclock',lan_wtp_mode='plain',lan_wtp_port=31417,
            lan_wtp_ready=True,network=dict(ipv4='192.168.1.47'))
        with patch('led_closeout.device.socket.create_connection',return_value=connection), patch.object(e,'event',side_effect=OSError('evidence unavailable')):
            with self.assertRaisesRegex(OSError,'evidence unavailable'):obj.peer('A')
        connection.close.assert_called_once()
        self.assertEqual(obj.peer_contexts,{})

    def test_failed_peer_cleanup_retains_primary_error_and_retries_close(self):
        e,_,_=self.exercise()
        obj=Device({},e,ROOT)
        connection=unittest.mock.Mock()
        connection.fileno.return_value=42
        connection.close.side_effect=[OSError('close uncertain'),None]
        obj.console=lambda *a:dict(device_id=BOARDS['A']['device_id'],
            provisioning_source='consumer_preclock',lan_wtp_mode='plain',lan_wtp_port=31417,
            lan_wtp_ready=True,network=dict(ipv4='192.168.1.47'))
        with patch('led_closeout.device.socket.create_connection',return_value=connection), patch('led_closeout.device.Peer') as peer:
            peer.return_value.request.side_effect=ConnectionResetError('reset')
            with self.assertRaisesRegex(ConnectionResetError,'reset') as caught:obj.peer('A')
        self.assertIn('close uncertain',caught.exception.__notes__[0])
        self.assertIn('A',obj.peer_contexts)
        obj.close()
        self.assertEqual(connection.close.call_count,2)
        self.assertEqual(obj.peer_contexts,{})

    def test_manifest_rejects_wrong_hash_role_and_dirty_source(self):
        from led_closeout.runner import sha256
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'artifact';file.write_bytes(b'reviewed bytes')
            value=manifest();commit='a'*40
            value.update(schema='phase13.1-led-candidates/2',source_commit=commit,clean=True,
                         board='pico2_w',sample_rate_hz=138000000,
                         sdk_commit='079c6f39023649b154152db30f1d781e884879bc',
                         picotool_commit='6f6458d792b93685a11423b244a585eaa99eafcf')
            for image in value['images'].values():
                image.update(revision=commit[:12],uf2=str(file),elf=str(file),
                             uf2_sha256=sha256(file),elf_sha256=sha256(file))
            with patch('led_closeout.device.tool',side_effect=lambda argv:commit if argv[-1]=='HEAD' else ''),                  patch('led_closeout.device.validate_uf2'):
                validate_manifest(value,ROOT)
                for field,wrong in (('uf2_sha256','wrong'),('pins',pins(1)),('engine','wrong')):
                    changed=copy.deepcopy(value);changed['images']['onboard'][field]=wrong
                    with self.assertRaises(ValueError):validate_manifest(changed,ROOT)
                value['clean']=False
                with self.assertRaises(ValueError):validate_manifest(value,ROOT)
                value['clean']=True;value['runner_commit']='b'*40
                def current(argv):
                    if argv[-1]=='HEAD':return value['runner_commit']
                    if '--verify' in argv:return commit
                    if 'diff' in argv:return 'src/led_closeout/device.py\ndocs/development/phase13-1-runner.md'
                    return ''
                with patch('led_closeout.device.tool',side_effect=current):validate_manifest(value,ROOT)
                def changed_input(argv):
                    return 'src/rf/pio_dma_sink.cpp' if 'diff' in argv else current(argv)
                with patch('led_closeout.device.tool',side_effect=changed_input):
                    with self.assertRaisesRegex(ValueError,'firmware inputs changed'):validate_manifest(value,ROOT)

    def test_real_peer_coalesced_and_fragmented_events_keep_response_identity(self):
        import socket,threading,struct
        from validate_wtp_contract import frame
        a,b=socket.socketpair();a.setblocking(False);b.settimeout(3)
        self.addCleanup(a.close);self.addCleanup(b.close)
        e,_,_=self.exercise();peer=Peer(a.fileno(),e,ROOT);peer.boot='1'*32
        errors=[]
        def responder():
            try:
                for index in range(2):
                    raw=bytearray()
                    while len(raw)<16 or len(raw)<16+struct.unpack('>I',raw[8:12])[0]:
                        raw.extend(b.recv(4096))
                    req=json.loads(raw[16:]);response=dict(req,type='response',ok=True,body={'token':str(index)})
                    event=dict(type='event',protocol='WTP/1',session_id=req['session_id'],boot_id='1'*32,
                               event_id=str(index+2),event='JOB_STATE',body=dict(job_id=None,state='empty',output_active=False))
                    event_bytes=frame(json.dumps(event).encode())
                    if index==0:
                        b.sendall(frame(json.dumps(response).encode())+event_bytes[:23])
                        tail=event_bytes[23:]
                    else:b.sendall(tail+event_bytes+frame(json.dumps(response).encode()))
            except BaseException as error:errors.append(error)
        thread=threading.Thread(target=responder);thread.start()
        self.assertEqual(peer.request('PING',{})['token'],'0')
        self.assertEqual(peer.request('PING',{})['token'],'1')
        thread.join(3);self.assertFalse(thread.is_alive());self.assertFalse(errors)
        self.assertEqual(len(peer.received),0)
        event=dict(type='event',protocol='WTP/1',session_id=peer.session,boot_id='2'*32,
                   event_id='3',event='JOB_STATE',body=dict(job_id=None,state='empty',output_active=False))
        with self.assertRaisesRegex(ValueError,'boot changed'):peer.emit('stale_wtp_message',event)
        event['boot_id']=peer.boot;event['session_id']='4'*32
        with self.assertRaisesRegex(ValueError,'schema/session'):peer.emit('stale_wtp_message',event)

    def test_usb_real_peer_rejects_invalid_schema_and_no_arm_retry(self):
        e,_,_=self.exercise()
        peer=Peer(0,e,ROOT)
        with patch('led_closeout.device.exchange',return_value=dict(ok=True,protocol='WTP/1',body={})):
            with self.assertRaises(ValueError):peer.request('ARM',{})


class SetupTests(unittest.TestCase):
    def setUp(self):
        from led_closeout.runner import sha256
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        tool=Path(self.directory.name)/'tool';tool.write_bytes(b'fixture tool bytes')
        self.setup=dict(schema='phase13.1-led-setup/1',receiver_serial='2404058C60',
            camera=dict(device='/dev/video0',fps=30,width=640,height=480,
                rois=dict(onboard=[0,0,20,20],external_high=[20,0,20,20],external_low=[40,0,20,20])),
            fixtures=dict(external_high_gp=15,external_low_gp=16,stimulus_gp=15,dut_stop_gp=14,open_drain=True),
            rf_path='operator-confirmed test path')
        for name in ('picotool','capture_helper','ffmpeg'):
            self.setup[name]=dict(path=str(tool),sha256=sha256(tool))

    def test_led_regions_are_distinct_and_adjacent_regions_are_allowed(self):
        # Inject only device-node existence, retaining actual file hash checks.
        with patch('led_closeout.device.Path.exists',return_value=True):
            validate_setup(self.setup)
            for region in ([0,0,20,20],[19,0,20,20],[True,0,20,20],[630,0,20,20],[20,0,0,20]):
                changed=copy.deepcopy(self.setup)
                changed['camera']['rois']['external_high']=region
                with self.assertRaises(ValueError):validate_setup(changed)

    def test_gpio_setup_needs_no_camera_or_external_fixture_for_onboard_cases(self):
        value=copy.deepcopy(self.setup)
        value.update(evidence_mode='gpio-readback',camera=None,fixtures={},retained_snapshots={})
        del value['ffmpeg']
        cases=[c for c in make_plan()['cases'] if c['id'] not in ('external_high','external_low','gp14_cutoff')]
        validate_setup(value,cases=cases)
        with self.assertRaisesRegex(ValueError,'fixture roles'):validate_setup(value)
        value['evidence_mode']='invalid'
        with self.assertRaisesRegex(ValueError,'evidence mode'):validate_setup(value,cases=cases)

    def test_reused_snapshot_preflight_never_enters_rom_or_saves_flash(self):
        from types import SimpleNamespace
        from led_closeout.device import retained_settings, FLASH_SIZE
        from led_closeout.runner import sha256
        import struct,zlib
        folder=Path(self.directory.name)
        data=bytearray(b'\xff'*FLASH_SIZE);record=bytearray(b'\xff'*2048)
        config=json.dumps(dict(version=1,enabled=False,pins=pins(0))).encode()
        struct.pack_into('<QQI',record,0,0x32524f5453505757,1,len(config))
        record[32:32+len(config)]=config
        struct.pack_into('<I',record,2044,zlib.crc32(record[:-4]))
        data[0x3fb000:0x3fb800]=record
        retained=folder/'retained.bin';retained.write_bytes(data)
        info=dict(ok=True,device_id=BOARDS['B']['device_id'],revision='entry',access_state='healthy',
                  access_generation=1,access_default_password=True,provisioning_generation=1,
                  provisioning_source='consumer_preclock',
                  status=dict(output_active=False,enabled=False,state='empty',storage_healthy=True,
                              owner_id=None,job_id=None,configured=True,expires_utc_s=None,
                              schedule_base_frequency_nhz=3570100000000000,schedules=[],station={},
                              watermark_utc_ns='0',last_job=None))
        value=copy.deepcopy(self.setup)
        value.update(evidence_mode='gpio-readback',camera=None,fixtures={},retained_snapshots={
            'B':dict(path=str(retained),serial=BOARDS['B']['serial'],sha256=sha256(retained),
                     settings=retained_settings(info))})
        e=Evidence(folder/'reuse-run',make_plan(),'B',None);obj=Device(value,e,ROOT)
        obj.select_cases([make_plan()['cases'][0]])
        obj.info=lambda b:copy.deepcopy(info);obj.lock_boards=unittest.mock.Mock()
        obj.rom=unittest.mock.Mock();obj.pt=unittest.mock.Mock()
        with patch('led_closeout.device.validate_manifest'), patch('led_closeout.device.shutil.disk_usage',return_value=SimpleNamespace(free=10**12)):
            obj.preflight({},'B',None)
        obj.rom.assert_not_called();obj.pt.assert_not_called()
        self.assertEqual(obj.snapshots['B']['state'],'REUSED')
        self.assertEqual(obj.snapshots['B']['path'],str(retained))
        uf2=folder/'candidate.uf2';uf2.write_bytes(b'checked-image')
        image=dict(uf2=str(uf2),uf2_sha256=sha256(uf2))
        booted=copy.deepcopy(info);booted['status']['boot_id']='new-boot'
        obj.wait_info=lambda b:booted
        with patch('led_closeout.device.quiescent'):
            obj.deploy('B',image)
        commands=[c.args[1] for c in obj.pt.call_args_list]
        self.assertEqual([c[0] for c in commands],['load','load','verify','reboot'])
        self.assertEqual(commands[2],['verify',str(retained),'-t','bin','-r','0x103f3000','0x10400000'])
        booted['provisioning_generation']=2
        with patch('led_closeout.device.quiescent'):
            with self.assertRaisesRegex(ValueError,'settings drift'):obj.deploy('B',image)
        obj.close()
        e=Evidence(folder/'stale-run',make_plan(),'B',None);obj=Device(value,e,ROOT)
        obj.select_cases([make_plan()['cases'][0]]);info['provisioning_generation']=2
        obj.info=lambda b:copy.deepcopy(info);obj.lock_boards=unittest.mock.Mock();obj.rom=unittest.mock.Mock()
        with patch('led_closeout.device.validate_manifest'), patch('led_closeout.device.shutil.disk_usage',return_value=SimpleNamespace(free=10**12)):
            with self.assertRaisesRegex(ValueError,'settings changed'):obj.preflight({},'B',None)
        obj.rom.assert_not_called();self.assertEqual(obj.snapshots,{})
        obj.close()

    def test_fixture_boolean_and_tool_hashes_cannot_be_substituted(self):
        with patch('led_closeout.device.Path.exists',return_value=True):
            changed=copy.deepcopy(self.setup);changed['fixtures']['open_drain']=1
            with self.assertRaisesRegex(ValueError,'fixture roles'):validate_setup(changed)
            changed=copy.deepcopy(self.setup);changed['capture_helper']['sha256']='wrong'
            with self.assertRaisesRegex(ValueError,'executable hash'):validate_setup(changed)

    def test_preparation_draft_is_not_a_runnable_setup_and_recovery_ignores_camera(self):
        changed=copy.deepcopy(self.setup)
        changed.update(schema='phase13.1-led-step2-preparation/1',camera=None,ready=False)
        with self.assertRaisesRegex(ValueError,'setup/receiver identity'):validate_setup(changed)
        changed=copy.deepcopy(self.setup);changed['camera']=None
        validate_setup(changed,recovery=True)

    def test_insufficient_matrix_storage_refuses_before_device_mutation(self):
        from types import SimpleNamespace
        reserve=storage_reserve(self.setup)
        self.assertGreater(reserve,3912000000)
        faster=copy.deepcopy(self.setup);faster['camera']['fps']=60
        self.assertGreater(storage_reserve(faster),reserve)
        e=Evidence(Path(self.directory.name)/'run',make_plan(),'B','A')
        obj=Device(self.setup,e,ROOT)
        obj.lock_boards=unittest.mock.Mock();obj.info=unittest.mock.Mock();obj.rom=unittest.mock.Mock()
        with patch('led_closeout.device.Path.exists',return_value=True), patch('led_closeout.device.validate_manifest'), patch('led_closeout.device.shutil.disk_usage',return_value=SimpleNamespace(free=2*1024**3)):
            with self.assertRaisesRegex(ValueError,'storage reserve'):obj.preflight({},'B','A')
        obj.lock_boards.assert_not_called();obj.info.assert_not_called();obj.rom.assert_not_called()
        self.assertEqual(obj.snapshots,{})


class CaptureAndFlashTests(unittest.TestCase):
    def test_gpio_capture_starts_only_receiver_and_marks_optics_unselected(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            cfg=dict(evidence_mode='gpio-readback',capture_helper={'path':'sdr'},receiver_serial='2404058C60')
            def start(*a,**k):
                (root/'capture.cf32.incomplete').write_bytes(b'x'*65536)
                return SimpleNamespace(pid=123,poll=lambda:None)
            c=Captures(cfg,SimpleNamespace(event=lambda *a:None))
            with patch('led_closeout.capture.subprocess.Popen',side_effect=start) as launch:
                c.start(root,10)
            self.assertEqual(launch.call_count,1)
            self.assertEqual(len(c.processes),1)
            for f in c.logs:f.close()
            binding=json.loads((root/'capture-binding.json').read_text())
            self.assertIsNone(binding['camera'])
            self.assertEqual(binding['optical_assessment'],'NOT_SELECTED')
            self.assertIsNone(binding['optical_pixel_format'])
    def test_capture_start_failure_terminates_previous_process(self):
        class Process:
            pid=123
            running=True
            def poll(self):return None if self.running else 0
            def wait(self,timeout):self.running=False;return 0
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);process=Process()
            cfg=dict(capture_helper={'path':'sdr'},receiver_serial='2404058C60',ffmpeg={'path':'ffmpeg'},
                camera=dict(fps=30,width=640,height=480,device='/dev/video0'))
            c=Captures(cfg,None)
            with patch('led_closeout.capture.subprocess.Popen',side_effect=[process,OSError('camera')]), \
                 patch('led_closeout.capture.os.killpg') as kill:
                with self.assertRaises(OSError):c.start(root,10)
                kill.assert_called_once()
                self.assertFalse(c.processes)
                self.assertFalse(process.running)
            binding=json.loads((root/'capture-binding.json').read_text())
            self.assertEqual(binding['receiver'][5],str(10*250000))
            self.assertEqual(binding['optical_pixel_format'],'bgr0')
            self.assertEqual(binding['camera'][binding['camera'].index('-pix_fmt')+1],'bgr0')

    def test_live_process_with_stalled_media_stops(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            now=[0]
            c=Captures({},None,now=lambda:now[0])
            c.root=Path(d);c.deadline=30
            c.processes=[SimpleNamespace(poll=lambda:None),SimpleNamespace(poll=lambda:None)]
            (c.root/'capture.cf32.incomplete').write_bytes(b'x'*65536)
            (c.root/'video.progress').write_text('frame=1\n')
            c.healthy()
            now[0]=6
            with self.assertRaises(ValueError):c.healthy()

    def test_restore_verification_checks_entire_reserved_region(self):
        from led_closeout.device import FLASH_SIZE, RESERVED
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);backup=root/'entry.bin';backup.write_bytes(b'\xff'*FLASH_SIZE)
            from led_closeout.runner import sha256
            readback=root/'readback.bin';readback.write_bytes(backup.read_bytes())
            uf2=root/'image.uf2';uf2.write_bytes(b'')
            obj=Device.__new__(Device)
            with patch('led_closeout.device.validate_uf2'):
                obj.verify('A',dict(uf2=str(uf2)),readback,dict(path=str(backup),sha256=sha256(backup)))
                data=bytearray(readback.read_bytes());data[RESERVED]=0;readback.write_bytes(data)
                with self.assertRaises(ValueError):obj.verify('A',dict(uf2=str(uf2)),readback,dict(path=str(backup),sha256=sha256(backup)))


if __name__=='__main__':unittest.main()
