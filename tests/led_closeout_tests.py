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
from led_closeout.device import Device, Peer, validate_manifest, validate_setup
from led_closeout.capture import Captures
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
                state = 'failed' if self.fail_on else 'running'
            if state == 'running' and self.t >= self.started+int(self.job['total_duration_ns'])/1e9:
                state = 'completed'
            if self.fault == 'premature' and state == 'running' and self.t >= self.started+.2:
                state = 'completed'
            self.states[board] = state
        if self.owner and self.t >= self.lease_end and self.owner != 'e'*32:
            self.owner = None
        image = self.images[board]
        if self.fault == 'transient_stop' and self.started is not None and self.job and self.t >= self.started+int(self.job['total_duration_ns'])/1e9 and self.t < self.started+int(self.job['total_duration_ns'])/1e9+.3:
            state='running';self.states[board]=state
        active = state == 'running' and image['engine'] == 'pio-dma-gp2'
        if self.fault == 'transient_stop' and self.started is not None and self.job and self.t >= self.started+int(self.job['total_duration_ns'])/1e9:
            active=False
        if self.fault == 'active_terminal' and state == 'completed': active = True
        boot = self.boots[board] if self.fault != 'boot' or state != 'running' else 'rebooted'
        return dict(ok=True, system_clock_hz=138000000, device_id=BOARDS[board]['device_id'], revision=image['revision'],
            led_boot_pins=image['pins'], led_acceptance=image['acceptance'], led_selection=image['selection'],
            access_state='healthy', rf_safety_inhibited=self.gp14, led_rejected_writes=int(self.fail_on),
            indicator_output_known=True, indicator_output_on=active and image["selection"] != 3,
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
    def request(self, op, body):
        if op == 'CLAIM': self.owner=body['owner_id'];self.lease_end=self.t+10
        if op == 'RENEW':
            if self.fault == 'lease' and self.started is not None: raise TimeoutError('lost renewal')
            self.renewals += 1;self.lease_end=self.t+10
        if op == 'LOAD':
            self.job=body;self.states[self.dut]='loaded'
            return dict(job_id=body['job_id'])
        if op == 'GET_CLOCK': return dict(state='unsynchronized' if self.fault == 'clock' else 'synchronized', leap='normal', uncertainty_ns='1000', utc_now_ns=str(int(self.t*1e9)))
        if op == 'ARM':
            assert self.e.state['jobs'] > self.admissions
            self.admissions += 1
            self.started=int(body['start_utc_ns'])/1e9
            self.states[self.dut]='armed'
            if self.fault == 'arm': raise TimeoutError('ambiguous ARM')
            if self.fault == 'premature_never_ran': self.states[self.dut]='completed'
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
            provisioning_source='consumer_preclock',lan_wtp_mode='plain',lan_wtp_port=31417,
            network=dict(ipv4='192.168.1.47'))
        with patch('led_closeout.device.socket.create_connection',return_value=connection) as connect,              patch('led_closeout.device.exclusive_port') as usb,              patch('led_closeout.device.Peer') as peer:
            peer.return_value.request.return_value=dict(device_id=BOARDS['A']['device_id'])
            obj.peer('A')
            connect.assert_called_once_with(('192.168.1.47',31417),timeout=3)
            usb.assert_not_called()
            obj.close_peer('A')
            connection.close.assert_called_once()

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

    def test_usb_real_peer_rejects_invalid_schema_and_no_arm_retry(self):
        e,_,_=self.exercise()
        peer=Peer(0,e,ROOT)
        with patch('led_closeout.device.exchange',return_value=dict(ok=True,protocol='WTP/1',body={})):
            with self.assertRaises(ValueError):peer.request('ARM',{})


class CaptureAndFlashTests(unittest.TestCase):
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
