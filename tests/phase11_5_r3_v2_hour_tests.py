"""Adversarial H0 evidence checks; no device or timing simulation qualifies the hour."""
import json,os,shutil,struct,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_v2_hour import audit

@unittest.skipUnless(os.environ.get('PHASE115_R3_V2_H0_EVIDENCE'),'Private completed H0 evidence required')
class PhysicalHourAuditTests(unittest.TestCase):
    def test_intact_and_mutations(self):
        source=Path(os.environ['PHASE115_R3_V2_H0_EVIDENCE'])
        def run(root):return audit(root,root/'pi/phase115_tls_observer_test.py')
        expected=run(source)
        def change_load(root,fn):
            file=root/'contention.jsonl';rows=[json.loads(s) for s in file.read_text().splitlines()];fn(rows)
            file.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        def https_change(root,key,value):
            def edit(rows):
                row=next(r for r in rows if r['kind']=='https_status');body=json.loads(bytes.fromhex(row['value']['body_hex']))
                body['transport'][key]=value;row['value']['body_hex']=json.dumps(body,separators=(',',':')).encode().hex()
                row['value']['headers']=[[k,str(len(bytes.fromhex(row['value']['body_hex']))) if k.lower()=='content-length' else v]
                    for k,v in row['value']['headers']]
            change_load(root,edit)
        def missing_https(root):
            def edit(rows):
                selected=[n for n,r in enumerate(rows) if r['kind']=='https_status'];rows.pop(selected[len(selected)//2])
                for n,r in enumerate(rows):r['sequence']=n
                rows[-1]['value']['https_requests']-=1
                result=root/'contention-result.json';result.write_text(json.dumps(rows[-1]['value']))
            change_load(root,edit)
        def false_native_terminal(root):
            def edit(rows):
                selected=[r for r in rows if r['kind']=='native_status'];r=selected[len(selected)//2]
                body=json.loads(bytes.fromhex(r['value']['body_hex']));body['job'].update(state='complete',output_active=False)
                r['value']['body_hex']=json.dumps(body).encode().hex();r['value']['value']=body
            change_load(root,edit)
        def wrong_peer(root):
            file=root/'production-tls.bin';data=bytearray(file.read_bytes());offset=0
            while offset<len(data):
                fields=struct.unpack('>8s7Q',data[offset:offset+64])
                if fields[2]==2:data[offset+64]^=1;break
                offset+=64+fields[-1]
            file.write_bytes(data)
        mutations=[lambda r:(r/'production-tls.bin').write_bytes((r/'production-tls.bin').read_bytes()[:-1]),
            wrong_peer,missing_https,false_native_terminal,lambda r:https_change(r,'active',1),
            lambda r:https_change(r,'pending',1),lambda r:(r/'contention-failed.json').write_text('{}'),
            lambda r:(r/'pi/phase115_tls_observer_test.py').write_text(''),
            lambda r:change_load(r,lambda rows:rows[-1]['value'].update(native_exit=1)),
            lambda r:(r/'final-a.stdout').write_text('')]
        for n,mutation in enumerate(mutations):
            with self.subTest(mutation=n),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(source,root);mutation(root)
                with self.assertRaises((ValueError,KeyError,IndexError)):run(root)
        self.assertEqual(run(source),expected)

if __name__=='__main__':unittest.main()
