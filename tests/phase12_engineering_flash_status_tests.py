#!/usr/bin/env python3
import copy
import json
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_engineering_flash_status as m
from validate_wtp_contract import frame


def wire(value):
    return frame(json.dumps(value,separators=(',',':')).encode())


class Fixture:
    def __init__(self):
        self.plan={'boot_id':'boot','source_commit':'a'*40}
        self.config={'version':1,'enabled':False,'station':{'callsign':'AB1CD','locator':'FN20','power_dbm':30},
                     'wifi':{'ssid':'private','password':'private','ntp_ipv4':'1.2.3.4'},
                     'schedules':[{'period_s':120,'phase_s':0}],'expires_utc_s':'42'}
        self.count=0; self.lock=threading.Lock(); self.commands=[]; self.config_attempts=0
        self.records=[]; self.uncertain=False; self.badcrc=False; self.overflow=False
        tick=10
        def span(kind):
            nonlocal tick
            sid=len(self.records)+1
            for phase,outcome in [('begin','pending'),('end','complete')]:
                self.records.append({'seq':str(len(self.records)+1),'span':str(sid),
                                     'monotonic_ns':str(tick),'kind':kind,'phase':phase,'outcome':outcome});tick+=10
        for _ in range(3):span('status')
        span('standalone_erase')
        for _ in range(8):span('standalone_program')
        for _ in range(57):span('status')
    def observe(self):return {},b'{}'
    def console(self,command,deadline):
        self.commands.append(command)
        base={'ok':True,'schema':'wsprrypico-activity-trace/1','device_id':m.DEVICE,
              'boot_id':'boot','revision':'a'*12,'capture_epoch':'1'}
        if command.startswith('CONFIG '):
            self.config_attempts+=1;time.sleep(.03)
            if self.uncertain:raise TimeoutError('uncertain save')
            base={'ok':True,'enabled':False}
        elif ' READ ' in command:
            cursor=int(command.rsplit(' ',1)[1]); selected=self.records[cursor:cursor+54]
            base.update(enabled=False,overflow=self.overflow,clock_regressed=False,dropped_spans='0',
                        open_spans='0',record_count=str(len(self.records)),records=selected,
                        next_cursor=str(cursor+len(selected)),more=cursor+len(selected)<len(self.records))
        else:base['enabled']=' BEGIN ' in command
        return base,json.dumps(base).encode()
    def exchange(self,carrier,op,body,deadline):
        if op=='STATUS':time.sleep(.002)
        with self.lock:self.count+=1;rid=f'{self.count:032x}'
        request={'protocol':'WTP/1','type':'request','session_id':carrier,'request_id':rid,'op':op,'body':{}}
        result={'boot_id':'boot','state':'empty','owner_id':None,'job_id':None,'output_active':False} if op=='STATUS' else {'monotonic_now_ns':'0' if self.count<4 else '10000'}
        response={**request,'type':'response','ok':True,'body':result}
        raw=wire(response)
        if self.badcrc:raw=raw[:-1]+bytes([raw[-1]^1])
        return wire(request),raw
    def run(self):
        with patch.object(m,'guard'):
            return m.run(self.plan,self.config,self.observe,self.console,
                         {c:lambda op,b,d,c=c:self.exchange(c,op,b,d) for c in m.CARRIERS})


class Tests(unittest.TestCase):
    def test_real_pairs_and_exact_scope(self):
        f=Fixture();old=copy.deepcopy(f.config);result=f.run()
        self.assertEqual(result['status_samples'],60);self.assertEqual(f.config_attempts,1)
        expected=copy.deepcopy(old);expected['station']['power_dbm']=27
        self.assertEqual(result['config'],expected);self.assertEqual(f.config,old)
        self.assertEqual(sum(e.get('operation')=='STATUS' for e in result['exchanges']),60)
        self.assertTrue(result['review_required'])
    def test_uncertain_never_retry_and_ends_trace(self):
        f=Fixture();f.uncertain=True
        with self.assertRaises(TimeoutError):f.run()
        self.assertEqual(f.config_attempts,1)
        self.assertEqual(f.commands[-1],'ACTIVITYTRACE END '+m.DEVICE)
    def test_worker_failure_joins_peers_before_trace_end(self):
        f=Fixture();exchange=f.exchange;console=f.console;active=[0];lock=threading.Lock();ended=[]
        def worker_exchange(carrier,op,body,deadline):
            if threading.current_thread() is threading.main_thread():
                return exchange(carrier,op,body,deadline)
            with lock:active[0]+=1
            try:
                if carrier=='usb':raise RuntimeError('independent worker failure')
                time.sleep(.04)
                return exchange(carrier,op,body,deadline)
            finally:
                with lock:active[0]-=1
        def observed_console(command,deadline):
            if ' END ' in command:ended.append(active[0])
            return console(command,deadline)
        f.exchange=worker_exchange;f.console=observed_console
        with self.assertRaises(RuntimeError):f.run()
        self.assertEqual(ended,[0]);self.assertEqual(active,[0])
    def test_wrong_program_count_rejected(self):
        # Directly remove a complete last program pair.
        f=Fixture();del f.records[22:24]
        mapping={}
        for i,r in enumerate(f.records):
            old=r['span'];r['seq']=str(i+1)
            if r['phase']=='begin':mapping[old]=r['seq']
            r['span']=mapping[old]
        with self.assertRaises(Exception):m.assess(f.records,0,10000)
    def test_crc_corruption_rejected_before_save(self):
        f=Fixture();f.badcrc=True
        with self.assertRaises(Exception):f.run()
        self.assertEqual(f.config_attempts,0)
    def test_overflow_rejected(self):
        f=Fixture();f.overflow=True
        with self.assertRaises(Exception):f.run()
    def test_no_actual_erase_rejected(self):
        f=Fixture();f.records=[r for r in f.records if r['kind']!='standalone_erase']
        mapping={}
        for i,r in enumerate(f.records):
            r['seq']=str(i+1)
            if r['phase']=='begin':mapping[r['span']]=r['seq']
            r['span']=mapping.get(r['span'],r['span'])
        with self.assertRaises(Exception):m.assess(f.records,0,10000)
    def test_missing_pair_rejected(self):
        f=Fixture();f.records.pop()
        with self.assertRaises(Exception):m.assess(f.records,0,10000)
    def test_status_inside_flash_rejected(self):
        f=Fixture();f.records[6]['monotonic_ns']='5';f.records[7]['monotonic_ns']='25'
        f.records.sort(key=lambda r:int(r['monotonic_ns']))
        mapping={}
        for i,r in enumerate(f.records):
            r['seq']=str(i+1)
            if r['phase']=='begin':mapping[r['span']]=r['seq']
            r['span']=mapping.get(r['span'],r['span'])
        with self.assertRaises(Exception):m.assess(f.records,0,10000)
    def test_nested_identical_clock_stamps_rejected_by_sequence(self):
        f=Fixture()
        for r in f.records:r['monotonic_ns']='100'
        # Erase begins before STATUS and finishes after it; all clocks quantized equal.
        erase_begin=f.records.pop(6);erase_end=f.records.pop(6)
        f.records.insert(0,erase_begin);f.records.insert(3,erase_end)
        mapping={}
        for i,r in enumerate(f.records):
            r['seq']=str(i+1)
            if r['phase']=='begin':mapping[r['span']]=r['seq']
            r['span']=mapping.get(r['span'],r['span'])
        with self.assertRaises(Exception):m.assess(f.records,0,10000)
    def test_canonical_config_retains_all_fields(self):
        f=Fixture();canonical=m.canonical_config(f.config)
        self.assertEqual(list(canonical),['version','enabled','station','wifi','schedules','expires_utc_s'])
        self.assertEqual(canonical,f.config)
        f.config['unexpected']=True
        with self.assertRaises(Exception):m.canonical_config(f.config)
    def test_bookend_mismatch_rejected(self):
        with self.assertRaises(Exception):m.assess(Fixture().records,20,10000)
    def test_decoded_only_dispatch_rejected(self):
        with self.assertRaises(Exception):m.dispatch({}, {}, {c:object() for c in m.CARRIERS},None,None)

class DurableFlashPreservation(unittest.TestCase):
    @staticmethod
    def record(tag,payload):
        import struct
        return struct.pack('>II',tag,len(payload))+payload
    def fixture(self):
        import struct
        rec=self.record
        base=[rec(0x534d4552,b'e'*16),rec(0x534d4952,b'i'*16),rec(0x42544442,b'd'*16),rec(0x42544403,b'p'*60)]
        ccc=struct.pack('<IHBB',1,42,1,3)
        def image(records):
            bank=b'BTstack\0'+b''.join(records)
            return b'\xff'*0x3f5000+bank+b'\xff'*(0x400000-0x3f5000-len(bank))
        return base,ccc,image
    def test_canonical_deleted_and_appended_ccc(self):
        from phase12_flash_preservation import preserve
        base,ccc,image=self.fixture()
        preserve(image(base+[self.record(0x42544313,ccc)]),image(base+[self.record(0,ccc),self.record(0,ccc)]))
    def test_reject_root_peer_unknown_torn_and_other_regions(self):
        from phase12_flash_preservation import preserve
        import struct
        base,ccc,image=self.fixture();rec=self.record
        before=image(base+[rec(0x42544313,ccc)])
        bad=[image([rec(0x534d4552,b'x'*16)]+base[1:]),image(base[:-1]+[rec(0x42544403,b'x'*60)]),
             image(base+[rec(0,ccc),rec(0,b'p'*60)]),image(base+[rec(0,ccc),rec(123,ccc)]),
             image(base+[rec(0,ccc),rec(0,struct.pack('<IHBB',1,42,1,2))]),image(base+[rec(0,ccc),rec(0,b'\0'*8)]),
             image(base+[rec(0x42544402,b'q'*60)]),image(base),image(base+[rec(0,struct.pack('<IHBB',2,42,1,3))])]
        for offset in (0x3f3000,0x3f7000,0x3fd000,0x3ff000):
            changed=bytearray(before);changed[offset]^=1;bad.append(bytes(changed))
        torn=bytearray(before);torn[0x3f5000+12]=0xff;bad.append(bytes(torn))
        for after in bad:
            with self.subTest(after_hash=__import__('hashlib').sha256(after).hexdigest()):
                with self.assertRaises(ValueError):preserve(before,after)
    def test_actual_parent_durable_guard_uses_semantics_and_exact_operational_fields(self):
        import ast
        from phase12_flash_preservation import preserve
        # Execute the real callback's readback guard, not a duplicate predicate.
        tree=ast.parse((Path(__file__).resolve().parents[1]/'scripts/phase12_engineering_orchestrator.py').read_text())
        callback=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='flash_status')
        start=next(i for i,n in enumerate(callback.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and getattr(n.value.func,'id',None)=='preserve_flash_reserved')
        code=compile(ast.fix_missing_locations(ast.Module(body=callback.body[start:start+2],type_ignores=[])),'actual-durable-guard','exec')
        base,ccc,image=self.fixture();before=image(base+[self.record(0x42544313,ccc)]);after=image(base+[self.record(0,ccc),self.record(0,ccc)])
        prepared=dict(config_sequence=3,watermark=11,cursor_sequence=9)
        selected=dict(config={'power_dbm':27},config_sequence=4,watermark=11,cursor_sequence=9)
        calls=[]
        def checked(a,b):calls.append((a,b));preserve(a,b)
        def require(ok,message):
            if not ok:raise ValueError(message)
        ns=dict(seed=before,actual=after,selected=selected,prepared=prepared,result={'config':selected['config']},require=require,preserve_flash_reserved=checked)
        exec(code,ns);self.assertEqual(len(calls),1)
        for key,value in [('config',{'power_dbm':20}),('config_sequence',5),('watermark',12),('cursor_sequence',10)]:
            ns['selected']={**selected,key:value}
            with self.subTest(key=key):
                with self.assertRaises(ValueError):exec(code,ns)

if __name__=='__main__':unittest.main()
