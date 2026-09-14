"""Deterministic framed native-wire fixtures and adversarial scope failures."""
import copy,hashlib,json,struct,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_phase11_5_r3_v2_native import native_wire
from validate_wtp_contract import frame
from phase11_5_pilot_supervisor import finished
DECODER=ROOT/'build/phase11-5-r3-v2-hour-h0/stage/pi/phase115_tls_observer_test.py'
BASE=ROOT/'build/phase11-5-r3-v2-browser-b9/evidence/before-a.stdout'

@unittest.skipUnless(BASE.exists() and DECODER.exists(),'Identified private template/decoder inputs required')
class NativeWireTests(unittest.TestCase):
    def fixture(self,mode,loss=False,mutation=None):
        baseline=finished(BASE,'READ_ONLY_INVENTORY')['wtp']
        template=json.loads((ROOT/f'build/phase11-5-r3-v2-native-preparation/final-templates/{mode}-load-template.json').read_text())['body']
        binding=dict(session_id='1'*32,owner_id='2'*32,job_id='3'*32,start_utc_ns='1800000000000000000')
        p=dict(native=dict(job_template=template,mode=mode,transport_loss=loss),peer_sha256='ab'*32,
            stage_sha256={'pi/phase115_tls_observer_test.py':hashlib.sha256(DECODER.read_bytes()).hexdigest()},
            boot_id=baseline['HELLO']['boot_id'],device_id=baseline['HELLO']['device_id'])
        events=[(0,0,b''),(1,1,b''),(2,1,bytes.fromhex(p['peer_sha256']))];number=0
        def exchange(op,body,response,cid=1,answer=True):
            nonlocal number
            number+=1;q=dict(type='request',protocol='WTP/1',session_id=binding['session_id'],request_id=f'{number:032x}',op=op,body=body)
            r=dict(q,type='response',ok=True,body=response)
            if mutation:mutation(q,r,number)
            wire=frame(json.dumps(q,separators=(',',':')).encode());events.extend([(7,cid,wire),(3,cid,wire)])
            if answer:events.append((4,cid,frame(json.dumps(r,separators=(',',':')).encode())))
        hello=dict(versions=['WTP/1'],client_name='native-test',client_version='1')
        exchange('HELLO',hello,baseline['HELLO']);exchange('STATUS',{},baseline['STATUS']);exchange('CAPS',{},baseline['CAPS']);exchange('GET_CLOCK',{},baseline['GET_CLOCK'])
        lease=dict(owner_id=binding['owner_id'],granted_lease_ms=60000,expires_monotonic_ns='100000000000')
        exchange('CLAIM',dict(owner_id=binding['owner_id'],lease_ms=60000),lease)
        job=dict(template,job_id=binding['job_id'])
        adjustments=[dict(event_index=n,requested_frequency_nhz=e['frequency_nhz'],realized_frequency_nhz=e['frequency_nhz'])
            for n,e in enumerate(job['events']) if e['rf_on']]
        exchange('LOAD',job,dict(job_id=binding['job_id'],state='loaded',adjustments=adjustments))
        exchange('RENEW',dict(owner_id=binding['owner_id'],lease_ms=60000),lease)
        exchange('ARM',dict(job_id=binding['job_id'],start_utc_ns=binding['start_utc_ns'],max_start_uncertainty_ns='500000000'),
            dict(job_id=binding['job_id'],state='armed',start_utc_ns=binding['start_utc_ns'],start_monotonic_ns='100000000000',clock=baseline['GET_CLOCK']))
        record=dict(job_id=binding['job_id'],state='complete',ended_monotonic_ns='255750000000',output_active=False)
        status=dict(boot_id=p['boot_id'],state='complete',output_active=False,owner_id=None if loss else binding['owner_id'],job_id=binding['job_id'],terminal_records=[record])
        cid=1
        if loss:
            exchange('STATUS',{},status,answer=False);events.extend([(5,1,b''),(1,2,b''),(2,2,bytes.fromhex(p['peer_sha256']))]);cid=2
            exchange('HELLO',hello,baseline['HELLO'],cid);exchange('STATUS',{},status,cid);exchange('CAPS',{},baseline['CAPS'],cid)
        exchange('STATUS',{},status,cid)
        if not loss:
            exchange('RELEASE',{}, {});exchange('STATUS',{},dict(status,state='empty',owner_id=None,job_id=None))
        events.extend([(5,cid,b''),(6,0,b'')])
        raw=b''.join(struct.pack('>8s7Q',b'P115TLS2',n,k,c,n+1,1800000000000000000+n,42,len(v))+v for n,(k,c,v) in enumerate(events))
        return raw,p,binding
    def check(self,mode,loss=False,mutation=None):
        raw,p,b=self.fixture(mode,loss,mutation)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'production-tls.bin').write_bytes(raw)
            return native_wire(root,p,b,DECODER)
    def test_source_distinct_modes_and_loss(self):
        for mode in ['qrss','fskcw','dfcw']:
            with self.subTest(mode=mode):self.assertEqual(self.check(mode)['job']['mode'],mode)
        self.assertEqual(len(self.check('dfcw',True)['lost_pending']),1)
    def test_wrong_load_arm_session_and_false_completion(self):
        def field(op,side,key,value):
            def mutate(q,r,n):
                if q['op']==op:(q if side=='request' else r)['body'][key]=value
            return mutate
        changes=[field('RENEW','request','owner_id','6'*32),field('LOAD','request','total_duration_ns','1'),field('ARM','response','job_id','4'*32),
            field('ARM','request','start_utc_ns','1800000000000000001'),field('STATUS','response','state','aborted'),
            field('STATUS','response','output_active',True)]
        for mutation in changes:
            with self.assertRaises(ValueError):self.check('qrss',mutation=mutation)
        def wrong_session(q,r,n):r['session_id']='5'*32
        with self.assertRaises(ValueError):self.check('qrss',mutation=wrong_session)
class ActualNativeAuditTests(unittest.TestCase):
    def test_actual_capture_and_mutations(self):
        import os,shutil
        from audit_phase11_5_r3_v2_native import audit
        name=os.environ.get('PHASE115_R3_V2_NATIVE_EVIDENCE')
        if not name:self.skipTest('Actual native capture required')
        source=Path(name);packet_sha=hashlib.sha256((source/'packet.json').read_bytes()).hexdigest();expected=audit(source,packet_sha)
        for file in ['native.jsonl','native-result.json','native-binding.json','production-tls.bin','production-job.ini',
            'before-a.stdout','final-a.stdout','native-observer.jsonl','native-observer-result.json']:
            with self.subTest(file=file),tempfile.TemporaryDirectory() as directory:
                altered=Path(directory)/'evidence';shutil.copytree(source,altered);(altered/file).write_bytes(b'')
                with self.assertRaises((ValueError,KeyError,IndexError)):audit(altered,packet_sha)
        if expected['status'] in ['ACTUAL_NATIVE_SUBMISSION_VERIFIED',
            'N4_NATIVE_LOSS_RECONCILIATION_WITH_EXIT_EXPECTATION_FAILURE_VERIFIED'] and json.loads((source/'packet.json').read_text())['native'].get('transport_loss'):
            def change_ack(row):row['value']['ack_monotonic_ns']+=1
            def change_pid(row):row['value']['identity']['pid']+=1
            def change_session(row):row['value']['session_id']='0'*32
            def change_order(row):row['monotonic_ns']=1
            def change_peer(row):row['value']['peer'][0]='192.168.1.53'
            def change_recovery(row):
                row['value']['value']['status']['recovery_required']=True
                row['value']['body_hex']=json.dumps(row['value']['value']).encode().hex()
            def change_exit(row):row['value']['returncode']=0
            for kind,change in [('arm_ack_before_loss',change_ack),('transport_loss_result',change_pid),
                ('reconciliation_pending',change_session),('reconciliation_pending',change_order),
                ('transport_loss_result',change_peer),('reconciliation_response',change_recovery),
                ('process_exit',change_exit)]:
                with self.subTest(loss=kind),tempfile.TemporaryDirectory() as directory:
                    altered=Path(directory)/'evidence';shutil.copytree(source,altered)
                    rows=[json.loads(x) for x in (altered/'native.jsonl').read_text().splitlines()]
                    change(next(r for r in rows if r['kind']==kind))
                    (altered/'native.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
                    with self.assertRaises(ValueError):audit(altered,packet_sha)
        self.assertEqual(audit(source,packet_sha),expected)

if __name__=='__main__':unittest.main()
