"""Private physical pressure evidence must reject altered authority and timing."""
import json,os,shutil,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_v2_pressure import audit
class PressureAuditTests(unittest.TestCase):
    def test_mutations(self):
        value=os.environ.get('PHASE115_R3_V2_PRESSURE_EVIDENCE')
        if not value:self.skipTest('Private pressure evidence required')
        source=Path(value);decoder=source/'pi/phase115_tls_observer_test.py';intact=audit(source,decoder)
        def edit(root,file,kind,fn):
            p=root/file;rows=[json.loads(l) for l in p.read_text().splitlines()];fn(next(r for r in rows if r['kind']==kind));p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        mutations=[lambda r:(r/'packet.json').write_text('{}'),lambda r:(r/'final-a.stdout').write_text(''),
            lambda r:(r/'production-tls.bin').write_bytes(b''),lambda r:(r/'pressure.pcap').write_bytes(b''),
            lambda r:(r/'pressure-job-0.json').write_text('{}'),lambda r:(r/'contention-result.json').write_text('{}'),
            lambda r:edit(r,'rf.jsonl','arm_acknowledged',lambda x:x['value'].update(start_utc_ns='0')),
            lambda r:edit(r,'rf.jsonl','info',lambda x:x['value']['value'].update(recovery_boot=True)),
            lambda r:edit(r,'contention.jsonl','https_status',lambda x:x['value'].update(peer_sha256='0'*64)),
            lambda r:(r/'pressure-capture.stderr').write_text('1 packets dropped by kernel\n')]
        for n,mutate in enumerate(mutations):
            with self.subTest(mutation=n),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(source,root);mutate(root)
                with self.assertRaises((ValueError,KeyError,IndexError,OSError)):audit(root,root/'pi/phase115_tls_observer_test.py')
        self.assertEqual(audit(source,decoder),intact)
if __name__=='__main__':unittest.main()
