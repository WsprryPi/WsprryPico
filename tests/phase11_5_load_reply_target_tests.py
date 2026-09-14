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
from audit_phase11_5_load_reply_target import wire_decode
from validate_wtp_contract import frame
import phase11_5_load_reply_target as target

class LoadTargetTests(unittest.TestCase):
    def packet(self):
        return dict(b_session='1'*32,inventory_session='2'*32,owner_id='3'*32,fresh_request_id='4'*32,tls_session='5'*32,scope='R3-G2-LOAD-TARGET-v1',source_revision=SOURCE,serial=SERIAL,device_id=DEVICE,primary=primary(),limits=dict(flashes=1,bootsel=1,primary_loads=1,replays=2,rf_jobs=0,configuration_writes=0,wifi_cycles=0,https_requests=4,network_seconds=90),start_utc_ns=0,work_deadline_utc_ns=2700000000000,cleanup_deadline_utc_ns=3600000000000)
    def test_exact_frozen_request(self):
        raw=raw_request(primary());self.assertEqual(len(raw),52105);self.assertEqual(hashlib.sha256(raw).hexdigest(),WIRE_SHA);validate_packet(self.packet())
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
                target.run(root,dict(owner_id='1'*32,cleanup_deadline_utc_ns=10**30),lambda k,v:log.append((k,v)),lambda:None)
            self.assertEqual(calls,['final-a','final-b'])
            fixture.return_value.cleanup.assert_called_once()
            result=json.loads((root/'run-result.json').read_text())
            self.assertEqual(result['status'],'FAILED')
            self.assertTrue(result['final_b_authority_verified'])
            self.assertIn('final_a_authority_error',result)
            self.assertEqual(log[-1],('finish',result))

if __name__=='__main__':unittest.main()
