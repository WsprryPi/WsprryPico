"""Opt-in raw B archives: intact evidence must pass and altered evidence must fail."""
import json,os,shutil,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_v2_parallel_b import deployment,functional

class ParallelBAuditTests(unittest.TestCase):
    def run_archive(self,kind,audit):
        value=os.environ.get('PHASE115_R3_V2_B_'+kind+'_EVIDENCE')
        if not value:self.skipTest('Private B '+kind+' evidence required')
        source=Path(value);sha=os.environ['PHASE115_R3_V2_B_'+kind+'_PACKET']
        intact=audit(source,sha)
        revision=json.loads((source/'packet.json').read_text())['source_revision'][:12]
        logname='deployment.jsonl' if kind=='DEPLOY' else 'functional.jsonl'
        def edit(root,fn):
            path=root/logname;rows=[json.loads(l) for l in path.read_text().splitlines()]
            fn(rows);path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        def first(rows,kind):return next(r for r in rows if r['kind']==kind)
        def undeclared(rows):
            rows.insert(-1,dict(rows[-1],kind='ARM_UNDECLARED',value={}))
            for i,r in enumerate(rows):r['sequence']=i
        mutations=[lambda r:(r/'final-b.stdout').write_text(''),
            lambda r:(r/'packet.json').write_text('{}'),
            lambda r:edit(r,lambda rows:rows.pop(2)),
            lambda r:edit(r,undeclared),
            lambda r:(r/'final-b.stdout').write_text((r/'final-b.stdout').read_text().replace(revision,'deadbeefdead'))]
        if kind=='DEPLOY':
            mutations += [lambda r:(r/'flash.stdout').write_text('Not verified'),
                lambda r:edit(r,lambda rows:first(rows,'flash_pending')['value'].update(sha256='0'*64)),
                lambda r:edit(r,lambda rows:first(rows,'tx')['value'].update(hex=b'ARM\n'.hex()))]
        else:
            mutations += [lambda r:edit(r,lambda rows:first(rows,'usb_write')['value'].update(bytes=1)),
                lambda r:edit(r,lambda rows:first(rows,'usb_rx')['value'].update(hex='00')),
                lambda r:edit(r,lambda rows:first(rows,'http_write_complete')['value'].update(bytes=1)),
                lambda r:edit(r,lambda rows:first(rows,'http_response')['value'].update(peer_sha256='0'*64)),
                lambda r:edit(r,lambda rows:first(rows,'http_response')['value'].update(body_hex=b'{}'.hex()))]
        for i,mutate in enumerate(mutations):
            with self.subTest(kind=kind,mutation=i),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(source,root);mutate(root)
                with self.assertRaises((ValueError,KeyError,IndexError,OSError)):audit(root,sha)
        self.assertEqual(audit(source,sha),intact)
    def test_deployment(self):self.run_archive('DEPLOY',deployment)
    def test_functional(self):self.run_archive('FUNCTIONAL',functional)

if __name__=='__main__':unittest.main()
