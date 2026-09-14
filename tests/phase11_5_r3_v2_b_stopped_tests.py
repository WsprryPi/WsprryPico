"""Private stopped B evidence: independent component and fault-classification checks."""
import json,os,shutil,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_v2_b_stopped import audit,PACKETS

class StoppedBTests(unittest.TestCase):
    def test_bf3_connection_failure(self):
        value=os.environ.get('PHASE115_R3_V2_B_STOPPED_BUILD')
        if not value:self.skipTest('Private stopped B archives required')
        source=Path(value)/'phase11-5-r3-v2-parallel-b-functional-bf3/evidence'
        sha='482ddb19074aff4190ffd5b2e432109d3926a2cd1c6829e29631e82f46b9983c';intact=audit(source,sha)
        for name in ['packet.json','before-b.stdout','final-b.stdout','functional-result.json','functional.jsonl']:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(source,root);(root/name).write_text('{}')
                with self.assertRaises((ValueError,KeyError,IndexError,OSError)):audit(root,sha)
        self.assertEqual(audit(source,sha),intact)

    def test_stopped_components_and_failure_mutations(self):
        value=os.environ.get('PHASE115_R3_V2_B_STOPPED_BUILD')
        if not value:self.skipTest('Private stopped B archives required')
        for label,sha in zip(('bf0','bf1','bf2'),PACKETS):
            source=Path(value)/('phase11-5-r3-v2-parallel-b-functional-'+label)/'evidence'
            intact=audit(source,sha)
            def edit(root,kind,fn):
                p=root/'functional.jsonl';rows=[json.loads(l) for l in p.read_text().splitlines()]
                fn(next(r for r in rows if r['kind']==kind));p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            mutations=[lambda r:(r/'packet.json').write_text('{}'),
                lambda r:(r/'before-b.stdout').write_text(''),
                lambda r:edit(r,'http_write_complete',lambda x:x['value'].update(bytes=1)),
                lambda r:edit(r,'http_response',lambda x:x['value'].update(status=503)),
                lambda r:edit(r,'http_response',lambda x:x['value'].update(peer_sha256='0'*64)),
                lambda r:edit(r,'http_response',lambda x:x['value'].update(body_hex=b'{}'.hex())),
                lambda r:edit(r,'http_response',lambda x:x.update(monotonic_ns=x['monotonic_ns']+20_000_000_000)),
                lambda r:edit(r,'failure',lambda x:x.update(kind='ARM_UNDECLARED'))]
            if label=='bf0':mutations.append(lambda r:(r/'final-b.stdout').write_text(''))
            else:
                mutations += [lambda r:(r/'diagnostic-b.stdout').write_text(''),
                    lambda r:edit(r,'usb_tx',lambda x:x['value'].update(wire_hex='00'))]
            for number,mutate in enumerate(mutations):
                with self.subTest(label=label,mutation=number),tempfile.TemporaryDirectory() as directory:
                    root=Path(directory)/'evidence';shutil.copytree(source,root);mutate(root)
                    with self.assertRaises((ValueError,KeyError,IndexError,OSError)):audit(root,sha)
            self.assertEqual(audit(source,sha),intact)

if __name__=='__main__':unittest.main()
