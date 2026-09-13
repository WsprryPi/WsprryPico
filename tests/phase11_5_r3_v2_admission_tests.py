import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_admission import SCHEMA, SERIAL, DEVICE, maximum_job, validate, DURATION, IdlePeer
from validate_wtp_contract import SchemaValidator


class AdmissionTests(unittest.TestCase):
    def packet(self):
        p=dict(schema=SCHEMA,r3_scope=SCHEMA,serial=SERIAL,device_id=DEVICE,runtime_seconds=600,
               flashes=1,bootsel_commands=1,rf_jobs=0,wifi_cycles=0,configuration_writes=0,heap_probes=0,
               source_revision='1'*40,prior_revision='2'*40,image_sha256='3'*64,installed_sha256='4'*64,
               image_file='candidate.uf2',installed_pid=123,root='/home/pi/phase11-5-r3-v2-unit')
        for i,k in enumerate(('prior_boot','b_boot','a_session','b_session','peer_session','owner_id',
                             'maximum_job_id','oversized_job_id','overduration_job_id'),1):p[k]=f'{i:032x}'
        p['maximum_job']=maximum_job(p['maximum_job_id'])
        return p
    def test_packet(self):
        p=self.packet();self.assertEqual(validate(p),p)
        for key,value in [('rf_jobs',1),('flashes',2),('runtime_seconds',601),('flashes',True),
                          ('wifi_cycles',1),('configuration_writes',1),('heap_probes',1),
                          ('source_revision','1'*12),('image_file','other.uf2'),
                          ('root','/home/pi/phase11-5-r3-v2-test/../escape')]:
            q=copy.deepcopy(p);q[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(q)
        q=copy.deepcopy(p);q['maximum_job']['events'][0]['frequency_nhz']='140000000000000'
        with self.assertRaises(ValueError):validate(q)
    def test_exact_job_boundaries(self):
        job=maximum_job('1'*32)
        self.assertEqual(len(job['events']),512)
        self.assertEqual(sum(int(e['duration_ns']) for e in job['events']),DURATION)
        self.assertEqual(int(job['events'][-1]['offset_ns'])+int(job['events'][-1]['duration_ns']),DURATION)
        self.assertTrue(all(e['rf_on'] and 135490000000000<=int(e['frequency_nhz'])<=135510000000000
                            for e in job['events']))
        self.assertLess(len(json.dumps(job,separators=(',',':')))+256,65536)
        self.assertEqual(len(maximum_job('2'*32,513)['events']),513)
        self.assertEqual(maximum_job('3'*32,1,DURATION+1)['total_duration_ns'],str(DURATION+1))
    def test_no_arm_path(self):
        peer=object.__new__(IdlePeer)
        for op in ['ARM','CONFIG','RESTART','RENEW']:
            with self.subTest(op=op),self.assertRaises(ValueError):peer.operation(op,{})


class RawAdmissionAuditTests(unittest.TestCase):
    def test_intact_and_adversarial_evidence(self):
        import os
        import shutil
        import tempfile
        from audit_phase11_5_r3_v2_admission import audit
        value=os.environ.get('PHASE115_R3_V2_E0A_EVIDENCE')
        if not value:self.skipTest('Private E0a evidence required')
        source=Path(value);original=audit(source)
        def trace_change(root,fn):
            path=root/'admission.jsonl';rows=[json.loads(s) for s in path.read_text().splitlines()]
            fn(rows);path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        def record(rows,kind):return next(r for r in rows if r['kind']==kind)
        mutations=[
            lambda r:trace_change(r,lambda a:record(a,'idle_write')['value'].update(bytes=1)),
            lambda r:trace_change(r,lambda a:record(a,'capacity_write')['value'].update(total_written=4095)),
            lambda r:trace_change(r,lambda a:record(a,'idle_message')['value']['body'].update(device_id='f'*32)),
            lambda r:trace_change(r,lambda a:record(a,'flash_pending')['value'].update(sha256='0'*64)),
            lambda r:trace_change(r,lambda a:a.pop(20)),
            lambda r:(r/'flash.stdout').write_text('No verification\n'),
            lambda r:(r/'final-b.stdout').write_text(''),
            lambda r:(r/'final-a.stdout').write_text((r/'final-a.stdout').read_text().replace('7d183978d08d','deadbeefdead')),
            lambda r:(r/'packet.json').write_text('{}\n'),
            lambda r:trace_change(r,lambda a:record(a,'capacity_rx')['value'].update(hex='00')),
        ]
        for i,mutate in enumerate(mutations):
            with self.subTest(mutation=i),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(source,root);mutate(root)
                with self.assertRaises((ValueError,KeyError,IndexError)):audit(root)
        self.assertEqual(audit(source),original)

if __name__=='__main__':unittest.main()
