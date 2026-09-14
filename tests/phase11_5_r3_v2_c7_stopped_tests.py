"""Raw-evidence mutations for the failed, zero-RF C7 attempt."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_v2_c7_stopped import audit


@unittest.skipUnless(os.environ.get('PHASE115_R3_V2_C7_EVIDENCE'), 'Private C7 evidence required')
class C7StoppedTests(unittest.TestCase):
    def test_raw_evidence_and_mutations(self):
        source=Path(os.environ['PHASE115_R3_V2_C7_EVIDENCE'])
        original=audit(source)
        self.assertFalse(original['acceptance_pass'])
        self.assertEqual(original['rf_jobs_charged'],0)
        def edit(root,fn):
            p=root/'rf.jsonl';rows=[json.loads(l) for l in p.read_text().splitlines()]
            fn(rows);p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        def first(rows,kind):return next(r for r in rows if r['kind']==kind)
        def result(root):
            p=root/'rf-result.json';v=json.loads(p.read_text());v['rf_duration_ns_charged']=128000000000
            p.write_text(json.dumps(v));edit(root,lambda rs:rs[-1].update(value=v))
        def no_raw(root):
            def change(rs):
                rs.remove(first(rs,'console_rx'))
                for n,r in enumerate(rs):r['sequence']=n
            edit(root,change)
        def bad_wire(root):
            def change(rs):
                r=first(rs,'wtp_tx');raw=bytearray.fromhex(r['value']['hex']);raw[-1]^=1;r['value']['hex']=raw.hex()
            edit(root,change)
        mutations=[
            lambda r:(r/'rf.jsonl').write_bytes((r/'rf.jsonl').read_bytes()[:-1]),
            lambda r:(r/'packet.json').write_text('{}'),result,no_raw,bad_wire,
            lambda r:edit(r,lambda rs:first(rs,'info')['value']['value'].update(allocator_failures='1')),
            lambda r:edit(r,lambda rs:first(rs,'info')['value']['value']['status'].update(output_active=True)),
            lambda r:edit(r,lambda rs:first(rs,'wtp_message')['value'].update(ok=False)),
            lambda r:edit(r,lambda rs:first(rs,'failure')['value'].update(error='STATUS response timeout')),
            lambda r:edit(r,lambda rs:first(rs,'wtp_tx')['value']['request'].update(op='ARM')),
            lambda r:edit(r,lambda rs:first(rs,'health').update(kind='arm_pending')),
            lambda r:(r/'final-a.stdout').write_bytes((r/'final-a.stdout').read_bytes()[:-100]),
        ]
        with tempfile.TemporaryDirectory() as d:
            for n,mutation in enumerate(mutations):
                root=Path(d)/str(n);shutil.copytree(source,root);mutation(root)
                with self.subTest(mutation=n),self.assertRaises((ValueError,KeyError,IndexError,UnicodeError)):
                    audit(root)
        self.assertEqual(audit(source),original)

if __name__=='__main__':unittest.main()
