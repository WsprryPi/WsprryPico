"""Matrix boundaries and adversarial identity/capture checks; no hardware."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.plan import matrix,job,accepted_events,validate_capture,validate_physical

class Tests(unittest.TestCase):
    def test_clock_boundaries_and_full_jobs(self):
        rows=matrix();self.assertEqual(len(rows),225)
        self.assertEqual(sum(r['disposition']=='UNSUPPORTED_CONFIGURATION' for r in rows),25)
        for clock in (132000000,138000000,150000000):
            with self.assertRaises(ValueError):job('TONE','2m',clock,'test')
        with self.assertRaises(ValueError):job('WSPR','4m',138000000,'test')
        self.assertEqual(len(job('WSPR','4m',150000000,'test')['events']),162)
        for mode in ('WSPR','QRSS','FSKCW','DFCW'):
            value=job(mode,'80m',138000000,'test')
            self.assertEqual(sum(int(e['duration_ns']) for e in value['events']),int(value['total_duration_ns']))
        maximum=job('FSKCW','80m',138000000,'test',3600,'max-events')
        self.assertEqual(len(maximum['events']),512)
        self.assertEqual(sum(int(e['duration_ns']) for e in maximum['events']),3600000000000)
        for mode in ('TONE','WSPR','QRSS','DFCW'):
            with self.assertRaises(ValueError):job(mode,'80m',138000000,'test',3600,'max-events')
        self.assertEqual(job('TONE','80m',138000000,'test',3600)['total_duration_ns'],'3600000000000')
        for value in (0,3601,True):
            with self.assertRaises(ValueError):job('TONE','80m',138000000,'test',value)
    def test_adjustments_cannot_bind_foreign_event(self):
        value=job('TONE','80m',138000000,'test')
        a=dict(event_index=0,requested_frequency_nhz=value['events'][0]['frequency_nhz'],realized_frequency_nhz='3570099990000000')
        self.assertEqual(accepted_events(value,[a])['events'][0]['frequency_nhz'],a['realized_frequency_nhz'])
        self.assertNotEqual(value['events'][0]['frequency_nhz'],a['realized_frequency_nhz'])
        for changes in ({'event_index':1},{'event_index':True},{'requested_frequency_nhz':'1'}):
            with self.assertRaises(ValueError):accepted_events(value,[dict(a,**changes)])
        with self.assertRaises(ValueError):accepted_events(value,[a,a])
    def test_corrupt_receiver_evidence_never_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'iq';path.write_bytes(b'\0'*80)
            settings=dict(format='CF32',sample_rate_hz=250000)
            metadata=dict(resolved_device=dict(driver='sdrplay',serial='2404058C60'),actual_settings=settings,
                          overflow_count=0,clipping=dict(sample_count=0),primary_outcome='success',
                          cleanup=dict(outcome='verified'),retained_sample_count=10,
                          output=dict(complete=True,size_bytes=80,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            validate_capture(metadata,path,settings)
            for key,value in [('resolved_device',dict(driver='sdrplay',serial='foreign')),('overflow_count',1),
                              ('clipping',dict(sample_count=1)),('primary_outcome','failure'),
                              ('cleanup',dict(outcome='unknown')),('retained_sample_count',11),
                              ('output',dict(complete=True,size_bytes=80,sha256='0'*64))]:
                invalid=copy.deepcopy(metadata);invalid[key]=value
                with self.assertRaises(ValueError):validate_capture(invalid,path,settings)
            path.write_bytes(b'\1'*80)
            with self.assertRaises(ValueError):validate_capture(metadata,path,settings)
    def test_lifecycle_and_source_substitutions_are_rejected(self):
        value=job('TONE','80m',138000000,'test')
        idle=dict(device_id='fd6127d11d6aca42a9905fa3fb1bf1d5',revision='144e8e83e598',
                  system_clock_hz=138000000,status=dict(boot_id='a'*32,engine='pio-dma-gp2',
                  owner_id=None,output_active=False,enabled=False,state='empty'))
        running=dict(boot_id='a'*32,job_id=value['job_id'],state='running',output_active=True)
        terminal=dict(running,state='complete',output_active=False)
        physical=dict(schema='phase14-physical/1',board='A',serial='0BF4B4AEC9FFB344',
                      device_id=idle['device_id'],source_revision=idle['revision'],
                      clock_hz=138000000,band='80m',mode='TONE',divider=1,rf_gp=2,engine='pio-dma-gp2',
                      result='CONTROL_COMPLETE',firmware_sha256='b'*64,boot_id='a'*32,job=value,
                      accepted_job=copy.deepcopy(value),load=dict(job_id=value['job_id'],adjustments=[]),
                      arm=dict(job_id=value['job_id']),action='complete',
                      status=[dict(status=running),dict(status=terminal)],terminal=terminal,before=idle,after=idle)
        validate_physical(physical)
        mutations=[lambda v:v.update(board='B'),lambda v:v.update(boot_id='c'*32),
                   lambda v:v.update(firmware_sha256='bad'),
                   lambda v:v['accepted_job']['events'][0].update(duration_ns='1'),
                   lambda v:v['arm'].update(job_id='d'*32),
                   lambda v:v['status'][0]['status'].update(boot_id='d'*32),
                   lambda v:v['terminal'].update(output_active=True),
                   lambda v:v['after']['status'].update(enabled=True),
                   lambda v:v['after'].update(revision='0123456789ab')]
        for mutation in mutations:
            invalid=copy.deepcopy(physical);mutation(invalid)
            with self.assertRaises(ValueError):validate_physical(invalid)
    def test_settings_journal_corruption_never_rolls_back(self):
        from phase14.profiles import engineering_record,profile
        value=dict(device_id='b'*32,version=1,wifi=dict(ssid='test',password='private'),tls={})
        raw=engineering_record(7,value)
        self.assertEqual(profile(raw),(7,1,value))
        for at in (0,8,16,24,252,260,7936,7944,7952,8188):
            broken=bytearray(raw);broken[at]^=1
            with self.assertRaises(ValueError):profile(broken)
        for sequence in (0,True,2**64):
            with self.assertRaises(ValueError):engineering_record(sequence,value)
        # A valid older slot must not hide a torn newer slot.
        broken=bytearray(engineering_record(8,value)[:8192]+raw[:8192]);broken[260]^=1
        with self.assertRaises(ValueError):profile(broken)
    def test_refill_faults_and_growth_samples(self):
        from phase14.plan import resources
        fields=('allocator_failures','tls_allocation_failures','dma_errors','exhausted_successor_links',
                'refill_invalid_reserves','refill_irq_unpaired','core0_stack_fault_status','core1_stack_fault_status',
                'flash_read_failures','flash_erase_failures','flash_program_failures')
        info=dict.fromkeys(fields,0);info.update(system_clock_hz=138000000,status=dict(boot_id='a'*32),
            heap_available_bytes=100000,heap_allocated_bytes=30000,core0_stack_guard_valid=1,
            core1_stack_guard_valid=1,max_refill_irq_to_ready_ns=1500000)
        self.assertTrue(resources([info,copy.deepcopy(info)],138000000)['passed'])
        wire=copy.deepcopy(info);wire['max_refill_irq_to_ready_ns']='1500000'
        self.assertTrue(resources([info,wire],138000000)['passed'])
        for invalid in (True,'-1','01','NaN','18446744073709551616'):
            with self.assertRaises(ValueError):resources([dict(info,max_refill_irq_to_ready_ns=invalid)],138000000)
        for changes in ({'heap_available_bytes':32767},{'exhausted_successor_links':1},
                        {'max_refill_irq_to_ready_ns':4000000},{'core1_stack_guard_valid':0}):
            self.assertFalse(resources([info,dict(info,**changes)],138000000)['passed'])
        with self.assertRaises(ValueError):resources([info,dict(info,system_clock_hz=132000000)],138000000)
    def test_clock_loss_cannot_target_a_foreign_ntp_peer(self):
        from phase14.clock_loss import NtpBlock
        value=dict(provisioning_source='provisioned',network=dict(ntp_address='192.168.1.54',ipv4='192.168.1.53'))
        NtpBlock(value,None)
        for change in ('public','foreign','consumer'):
            invalid=copy.deepcopy(value)
            if change=='public':invalid['network']['ntp_address']='1.1.1.1'
            elif change=='foreign':invalid['network']['ipv4']='192.168.2.53'
            else:invalid['provisioning_source']='consumer_preclock'
            with self.assertRaises(ValueError):NtpBlock(invalid,None)
    def test_clock_loss_observation_failure_still_removes_owned_rule(self):
        from phase14.clock_loss import NtpBlock
        from unittest.mock import Mock,patch
        import subprocess
        block=NtpBlock(dict(provisioning_source='provisioned',network=dict(ntp_address='192.168.1.54',ipv4='192.168.1.53')),Mock())
        block.active=True
        with patch('phase14.clock_loss.subprocess.check_output',side_effect=subprocess.TimeoutExpired('nft',5)),patch('phase14.clock_loss.subprocess.run',return_value=Mock(returncode=1)) as run:
            with self.assertRaises(subprocess.TimeoutExpired):block.close()
            self.assertEqual(run.call_args_list[0].args[0][1:4],['delete','table','inet'])
            self.assertFalse(block.active)
    def test_candidate_hash_and_reserved_region_substitutions_are_rejected(self):
        from phase14.candidate import candidate
        from standalone_image_tests import block
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);artifacts=root/'artifacts';artifacts.mkdir()
            path=artifacts/'candidate.uf2';path.write_bytes(block(0x10000000)+block(0x10FFFF00,True))
            manifest=dict(schema='phase14-candidates/1',source_commit='a'*40,board='pico2_w',engine='pio-dma-gp2',divider=1,rf_gp=2,
                gp14_enabled=False,fixtures_enabled=False,release_qualified=False,
                sdk_commit='079c6f39023649b154152db30f1d781e884879bc',picotool_commit='6f6458d792b93685a11423b244a585eaa99eafcf',
                images={'138000000':{'uf2':dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())}})
            def publish():(artifacts/'manifest.json').write_text(json.dumps(manifest))
            publish();self.assertEqual(candidate(root)[2],path)
            manifest['fixtures_enabled']=True;publish()
            with self.assertRaises(ValueError):candidate(root)
            manifest['fixtures_enabled']=False;publish();path.write_bytes(b'wrong firmware')
            with self.assertRaises(ValueError):candidate(root)
            path.write_bytes(block(0x103F8000))
            manifest['images']['138000000']['uf2']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();publish()
            with self.assertRaises(ValueError):candidate(root)
    def test_clock_probe_unexpected_admission_still_aborts_its_job(self):
        from phase14.clock_loss import reject_aged_arm
        from unittest.mock import Mock,patch
        value=job('TONE','80m',138000000,'clock-probe',5)
        for admitted in (False,True):
            peer=Mock(fd=1,session='a'*32,received=bytearray(),schema={})
            peer.validator.errors.return_value=[]
            owner=[None];operations=[]
            def request(op,body,**kwargs):
                operations.append(op)
                if op=='CLAIM':owner[0]=body['owner_id'];return dict(owner_id=owner[0])
                if op=='GET_CLOCK':return dict(state='unsynchronized',utc_now_ns='1000000000')
                if op=='STATUS':return dict(job_id=value['job_id'],owner_id=owner[0],output_active=False,state='armed' if admitted else 'loaded')
                return {}
            peer.request.side_effect=request
            response=dict(ok=admitted,error=dict(code='CLOCK_UNSYNCHRONIZED'))
            with patch('phase11_5_inventory.exchange',return_value=response):
                if admitted:
                    with self.assertRaises(ValueError):reject_aged_arm(peer,Mock(),value)
                else:reject_aged_arm(peer,Mock(),value)
            self.assertEqual(operations[-3:],['ABORT','STATUS','RELEASE'])
    def test_controller_relay_rejects_truncated_and_corrupt_frames(self):
        from phase14.relay import messages
        from validate_wtp_contract import frame
        schema=json.loads((ROOT/'docs/protocol/wtp-1.schema.json').read_text())
        value=dict(type='request',protocol='WTP/1',session_id='a'*32,request_id='b'*32,op='PING',body={})
        raw=frame(json.dumps(value,separators=(',',':')).encode())
        self.assertEqual(messages(raw,schema),[value])
        broken=bytearray(raw);broken[-1]^=1
        for invalid in (raw[:-1],raw[:8],bytes(broken),raw+b'extra'):
            with self.assertRaises(ValueError):messages(invalid,schema)
    def test_controller_relay_drains_fragmented_bytes_at_half_close(self):
        from phase14.relay import Relay
        import socket,threading
        source=b'complete local job'*8192;answer=b'complete response'*4096
        received=[]
        with tempfile.TemporaryDirectory() as directory,socket.socket() as server:
            server.bind(('127.0.0.1',0));server.listen(1)
            def endpoint():
                with server.accept()[0] as connection:
                    connection.settimeout(5);parts=[]
                    while data:=connection.recv(4096):parts.append(data)
                    received.append(b''.join(parts));connection.sendall(answer)
            worker=threading.Thread(target=endpoint);worker.start()
            relay=Relay(directory,'127.0.0.1',server.getsockname()[1],listen_port=0)
            try:
                with socket.create_connection(('127.0.0.1',relay.listen_port),timeout=5) as client:
                    for at in range(0,len(source),137):client.sendall(source[at:at+137])
                    client.shutdown(socket.SHUT_WR);parts=[]
                    while data:=client.recv(4096):parts.append(data)
                    self.assertEqual(b''.join(parts),answer)
            finally:relay.close();worker.join(timeout=5)
            self.assertFalse(worker.is_alive());self.assertEqual(received,[source])
            self.assertEqual((Path(directory)/'client-to-device.bin').read_bytes(),source)
            self.assertEqual((Path(directory)/'device-to-client.bin').read_bytes(),answer)
    def test_sampling_axis_correction_preserves_reference_anchor_and_original(self):
        from phase14.calibration import quantities
        reference=dict(schema='phase14-reference/1',scale_nominal_to_true_time=1.000002,repeatability_bound_ppm=.2,
            reference_accuracy_assumption_ppb=1,traceable_calibration=False)
        measurement=dict(reference_hz=3530100,observed_duration_s=110.592,tone_spacing_hz=1.46484375,
            measurements=[dict(index=0,reference_compared_hz=3570100.08)])
        original=copy.deepcopy(measurement);result=quantities(measurement,reference)
        self.assertEqual(measurement,original)
        self.assertAlmostEqual(result['reference_subtracted_frequencies'][0]['frequency_hz_true_axis'],3570100,places=6)
        self.assertGreater(result['observed_duration_s_true_axis'],measurement['observed_duration_s'])
        self.assertEqual(result['transmitter_frequency_correction_ppb'],0)
        for invalid in (True,0,float('nan'),1.1):
            with self.assertRaises(ValueError):quantities(measurement,dict(reference,scale_nominal_to_true_time=invalid))
    def test_usb_deauthorization_refuses_changed_port_identity(self):
        from phase14.usb import UsbUnavailable
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);device=root/'3-1.2';device.mkdir()
            (device/'serial').write_text('CDDBF8767C506C07');(device/'authorized').write_text('1')
            change=UsbUnavailable('B',Mock(),sysroot=root);change.start()
            self.assertEqual((device/'authorized').read_text().strip(),'0')
            (device/'serial').write_text('foreign')
            with self.assertRaises(ValueError):change.close()
            self.assertEqual((device/'authorized').read_text().strip(),'0')
            (device/'serial').write_text('CDDBF8767C506C07');change.close()
            self.assertEqual((device/'authorized').read_text().strip(),'1')
    def test_requested_compensation_changes_frequency_without_changing_time(self):
        from phase14.calibration import request_compensated
        value=job('WSPR','80m',138000000,'compensation')
        self.assertEqual(request_compensated(value,0),value)
        positive=request_compensated(value,1500);negative=request_compensated(value,-1500)
        self.assertLess(int(positive['events'][0]['frequency_nhz']),int(value['events'][0]['frequency_nhz']))
        self.assertGreater(int(negative['events'][0]['frequency_nhz']),int(value['events'][0]['frequency_nhz']))
        self.assertNotEqual(positive['job_id'],negative['job_id'])
        self.assertEqual(positive['total_duration_ns'],value['total_duration_ns'])
        self.assertEqual([(e['offset_ns'],e['duration_ns']) for e in positive['events']],[(e['offset_ns'],e['duration_ns']) for e in value['events']])
        for invalid in (True,100001,-100001,1.5):
            with self.assertRaises(ValueError):request_compensated(value,invalid)
if __name__=='__main__':unittest.main()
