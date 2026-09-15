"""Hardware-free scope and response-evidence checks for the bounded LOAD test."""
import copy
import contextlib
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_load_reply_target import primary,raw_request,request,validate_packet,response_ok,SOURCE,SERIAL,DEVICE,WIRE_SHA
from audit_phase11_5_load_reply_target import wire_decode,pressure_brackets
from validate_wtp_contract import frame
import phase11_5_load_reply_target as target

class LoadTargetTests(unittest.TestCase):
    def packet(self):
        return dict(b_session='1'*32,inventory_session='2'*32,owner_id='3'*32,fresh_request_id='4'*32,tls_session='5'*32,scope='R3-G2-LOAD-TARGET-v1',source_revision=SOURCE,serial=SERIAL,device_id=DEVICE,primary=primary(),limits=dict(flashes=1,bootsel=1,primary_loads=1,replays=2,rf_jobs=0,configuration_writes=0,wifi_cycles=0,https_requests=4,network_seconds=90),start_utc_ns=0,work_deadline_utc_ns=2700000000000,cleanup_deadline_utc_ns=3600000000000)
    def test_exact_frozen_request(self):
        raw=raw_request(primary());self.assertEqual(len(raw),52105);self.assertEqual(hashlib.sha256(raw).hexdigest(),WIRE_SHA);validate_packet(self.packet())
    def test_repaired_candidate_scope_is_exact_and_bounded(self):
        p=self.packet();p.update(scope=target.REPLAY_SCOPE,source_revision=target.REPLAY_SOURCE);validate_packet(p)
        for key in p['limits']:
            bad=copy.deepcopy(p);bad['limits'][key]+=1
            with self.subTest(key=key),self.assertRaises(ValueError):validate_packet(bad)
        for source in [SOURCE,'f'*40]:
            bad=copy.deepcopy(p);bad['source_revision']=source
            with self.assertRaises(ValueError):validate_packet(bad)

    def test_tls_comparability_covers_each_complete_exchange(self):
        tx={k:dict(start=i*3*10**9,elapsed_ns=2*10**9,response=True) for i,k in enumerate(['primary','identical-replay','fresh-id-replay'])}
        infos=[dict(monotonic_ns=i*10**9,value=dict(value=dict(tls_allocated_bytes=31384))) for i in range(-1,10)]
        self.assertTrue(all(x['comparable'] for x in pressure_brackets(tx,infos).values()))
        infos[-2]['value']['value']['tls_allocated_bytes']=1000
        brackets=pressure_brackets(tx,infos)
        self.assertTrue(brackets['primary']['comparable']);self.assertFalse(brackets['fresh-id-replay']['comparable'])
        self.assertFalse(pressure_brackets(tx,infos[:1])['fresh-id-replay']['bracketed'])

    def test_scope_changes_rejected(self):
        for key in self.packet()['limits']:
            p=self.packet();p['limits'][key]+=1
            with self.subTest(key=key),self.assertRaises(ValueError):validate_packet(p)
        p=self.packet();p['b_session']='1'*33
        with self.assertRaises(ValueError):validate_packet(p)
        for op in ['ARM','RENEW','CONFIG','REBOOT','WIFI']:
            with self.assertRaises(ValueError):request(op,{},'1'*32)
        p=self.packet();p['primary']['body']['events'][0]['duration_ns']='1'
        with self.assertRaises(ValueError):validate_packet(p)
    def test_retained_continuation_has_no_deployment_allowance(self):
        p=self.packet();p.update(scope=target.CONTINUATION,prior_packet_sha256=target.PRIOR_PACKET_SHA,expected_boot=target.RETAINED_BOOT)
        p['limits'].update(flashes=0,bootsel=0);validate_packet(p)
        for field in ['flashes','bootsel']:
            bad=copy.deepcopy(p);bad['limits'][field]=1
            with self.assertRaises(ValueError):validate_packet(bad)
        with self.assertRaisesRegex(ValueError,'no flash authority'):target.deploy(None,p,None,lambda:None)

    def test_network_waits_for_two_confirmed_addresses(self):
        waiting=dict(network=dict(initialized=True,enabled=True,link_status=-2,ipv4='',control_listening=True))
        ready=dict(network=dict(initialized=True,enabled=True,link_status=3,ipv4='10.77.15.10',control_listening=True))
        log=[]
        with patch.object(target,'Journal',return_value=lambda k,v:log.append((k,v))),patch.object(target,'exclusive_port',return_value=contextlib.nullcontext(7)),patch.object(target,'exchange',side_effect=[waiting,ready,waiting,ready,ready]) as exchange,patch.object(target,'healthy'),patch.object(target.time,'sleep'):
            target.wait_network(Path('/unused'),'a'*32,lambda:None)
        self.assertEqual(exchange.call_count,5)
        self.assertEqual(log[-1],('finish',dict(status='PICO_NETWORK_READY')))

    def test_network_wait_clamps_sleep_to_remaining_deadline(self):
        waiting=dict(network=dict(initialized=True,enabled=True,link_status=-3,ipv4='',control_listening=True))
        with patch.object(target,'Journal',return_value=lambda k,v:None),patch.object(target,'exclusive_port',return_value=contextlib.nullcontext(7)),patch.object(target,'exchange',return_value=waiting),patch.object(target,'healthy'),patch.object(target.time,'monotonic',side_effect=[0,89,89,89.5,90]),patch.object(target.time,'sleep') as sleep:
            with self.assertRaisesRegex(TimeoutError,'readiness deadline'):target.wait_network(Path('/unused'),'a'*32,lambda:None)
        sleep.assert_called_once_with(.5)

    def test_recovery_scope_allows_one_cycle_and_no_flash(self):
        p=self.packet();p.update(scope=target.RECOVERY,prepare_retained=True,prior_packet_sha256=target.PRIOR_PACKET_SHA,expected_boot=target.RETAINED_BOOT);p['limits'].update(flashes=0,bootsel=0,wifi_cycles=1);validate_packet(p)
        for key,value in [('wifi_cycles',2),('flashes',1),('bootsel',1),('rf_jobs',1)]:
            bad=copy.deepcopy(p);bad['limits'][key]=value
            with self.assertRaises(ValueError):validate_packet(bad)
        with self.assertRaisesRegex(ValueError,'no flash authority'):target.deploy(None,p,None,lambda:None)

    def test_wifi_on_attempted_once_after_lost_off_ack(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);commands=[]
            def exchange(fd,command,*args):
                commands.append(command)
                if command==b'INFO\n':return dict(ok=True,status=dict(state='empty'))
                if command==b'WIFI OFF\n':raise TimeoutError('lost OFF ack')
                return dict(ok=True)
            with patch.object(target,'exclusive_port',return_value=contextlib.nullcontext(7)),patch.object(target,'healthy'),patch.object(target,'exchange',side_effect=exchange):
                with self.assertRaisesRegex(TimeoutError,'lost OFF ack'):target.wifi_cycle(root,'a'*32,lambda:None,10**30)
            self.assertEqual(commands,[b'INFO\n',b'WIFI OFF\n',b'WIFI ON\n'])
            state=json.loads((root/'wifi-state.json').read_text());self.assertEqual(state['off_started'],1);self.assertEqual(state['on_started'],1)

    def test_complete_reply_and_corrupted_frame(self):
        reply=dict(type='response',protocol='WTP/1',session_id=primary()['session_id'],request_id=primary()['request_id'],op='LOAD',ok=True,body=dict(job_id=primary()['body']['job_id'],state='loaded',adjustments=[dict(event_index=i,requested_frequency_nhz=str(135500000000000 if i%2==0 else 135495000000000),realized_frequency_nhz=str(135500002652407 if i%2==0 else 135494990274310)) for i in range(512)]))
        response_ok(reply);raw=frame(json.dumps(reply,separators=(',',':')).encode());buf=bytearray();got=[]
        for i in range(0,len(raw),17):buf.extend(raw[i:i+17]);got.extend(wire_decode(buf))
        self.assertFalse(buf);self.assertEqual(got[0][0],reply);self.assertEqual(len(got[0][1]),54916)
        for offset in [0,8,12,len(raw)-1]:
            bad=bytearray(raw);bad[offset]^=1
            with self.assertRaises(ValueError):wire_decode(bad)
        for modify in [lambda v:v['body']['adjustments'].pop(),lambda v:v['body']['adjustments'][3].update(event_index=4),lambda v:v['body'].update(job_id='f'*32)]:
            bad=copy.deepcopy(reply);modify(bad)
            with self.assertRaises(ValueError):response_ok(bad)
    def test_actual_partial_write_counts_and_raw_reply(self):
        q=request('STATUS',{},'1'*32)
        reply=dict(type='response',protocol='WTP/1',session_id=q['session_id'],request_id=q['request_id'],op='STATUS',ok=True,body=dict(boot_id='2'*32,state='empty',output_active=False,owner_id=None,job_id=None,terminal_records=[]))
        expected=raw_request(q);wire=bytearray(frame(json.dumps(reply,separators=(',',':')).encode()));written=bytearray();log=[]
        def write(fd,data):
            n=min(7,len(data));written.extend(data[:n]);return n
        def ready(reads,writes,errors,timeout):return ([7] if len(written)==len(expected) and wire else [],writes,[])
        def read(fd,count):
            out=bytes(wire[:11]);del wire[:11];return out
        peer=target.USB(7,'2'*32,lambda kind,value:log.append((kind,value)),lambda:None)
        with patch.object(target.os,'write',write),patch.object(target.os,'read',read),patch.object(target.select,'select',ready):
            self.assertEqual(peer.ask(q,'test'),reply)
        self.assertEqual(bytes(written),expected)
        writes=[v for k,v in log if k=='usb_write'];self.assertEqual(sum(v['bytes'] for v in writes),len(expected));self.assertEqual(writes[-1]['total_written'],len(expected))
        self.assertEqual(len([v for k,v in log if k=='usb_tx']),1)

    def test_failure_reply_is_not_retried(self):
        q=request('STATUS',{},'1'*32)
        reply=dict(type='response',protocol='WTP/1',session_id=q['session_id'],request_id=q['request_id'],op='STATUS',ok=False,error=dict(code='INTERNAL_ERROR',message='INTERNAL_ERROR',retryable=False))
        raw=frame(json.dumps(reply,separators=(',',':')).encode());log=[]
        peer=target.USB(7,'2'*32,lambda k,v:log.append((k,v)),lambda:None)
        with patch.object(target.os,'write',side_effect=lambda fd,data:len(data)),patch.object(target.os,'read',return_value=raw),patch.object(target.select,'select',return_value=([7],[7],[])):
            with self.assertRaises(ValueError):peer.ask(q,'test')
        self.assertEqual(len([v for k,v in log if k=='usb_tx']),1)

    def test_console_uint64_zero_and_nonzero_health_counters(self):
        info=dict(device_id=DEVICE,revision=SOURCE[:12],status=dict(boot_id='a'*32,output_active=False,enabled=False),recovery_boot=False,
            allocator_failures='0',launch_epoch='0',tls_allocation_failures=0,
            heap_capacity_bytes=219712,allocator_peak_bytes=112920)
        for k in ['fault_stage','fault_hash','fault_pc','fault_status','dma_irqs','alarm_irqs','tail_irqs']:info[k]=0
        for core in (0,1):
            info.update({f'core{core}_stack_guard_valid':1,f'core{core}_stack_fault_status':0,f'core{core}_stack_used_bytes':8700})
        target.healthy(info,'a'*32)
        for key,value in [('launch_epoch','1'),('allocator_failures','1'),('tls_allocation_failures',1),('fault_pc',1),('dma_irqs',1),('core0_stack_guard_valid',0),('core1_stack_used_bytes',12289),('allocator_peak_bytes',219712-32767),('launch_epoch',0)]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):target.healthy(dict(info,**{key:value}),'a'*32)

    def test_failed_a_inventory_still_checks_b_and_restores_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'deployment.json').write_text(json.dumps(dict(boot_id='a'*32)))
            calls=[];log=[]
            b=dict(wtp=dict(STATUS=dict(boot_id='b'*32)))
            def inventory(root,packet,label,b_board=False):
                calls.append(label)
                if label=='final-a':raise ValueError('A health unavailable')
                return b
            with patch.object(target,'exclusive_port',side_effect=lambda p:contextlib.nullcontext(7)),patch.object(target.USB,'ask',side_effect=ValueError('test stopped')),patch.object(target,'exchange',side_effect=[dict(device_id=DEVICE,status=dict(boot_id='a'*32)),dict(ok=True)]),patch.object(target,'Fixture') as fixture,patch.object(target,'inventory',side_effect=inventory),patch.object(target,'finished',return_value=b),patch.object(target,'configuration',return_value={}),patch.object(target,'inactive'):
                target.run(root,dict(scope='R3-G2-LOAD-TARGET-v1',owner_id='1'*32,cleanup_deadline_utc_ns=10**30),lambda k,v:log.append((k,v)),lambda:None)
            self.assertEqual(calls,['final-a','final-b'])
            fixture.return_value.cleanup.assert_called_once()
            result=json.loads((root/'run-result.json').read_text())
            self.assertEqual(result['status'],'FAILED')
            self.assertTrue(result['final_b_authority_verified'])
            self.assertIn('final_a_authority_error',result)
            self.assertEqual(log[-1],('finish',result))

if __name__=='__main__':unittest.main()
