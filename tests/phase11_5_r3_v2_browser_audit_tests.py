import json,os,shutil,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_v2_browser import audit,duration_text

class ExactDurationTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(duration_text(1000),'0.000001 s')
        self.assertEqual(duration_text(143250001000),'2 min 23.250001 s')
        self.assertEqual(duration_text(3600000000000),'60 min 0 s')

@unittest.skipUnless(os.environ.get('PHASE115_R3_V2_BROWSER_EVIDENCE'),'Private real Chromium evidence required')
class BrowserAuditTests(unittest.TestCase):
    def test_intact_and_mutations(self):
        source=Path(os.environ['PHASE115_R3_V2_BROWSER_EVIDENCE']);expected=audit(source)
        def edit(root,kind,change):
            file=root/'browser.jsonl';rows=[json.loads(s) for s in file.read_text().splitlines()]
            change(next(r for r in rows if r['kind']==kind));file.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        changes=[lambda r:(r/'job-30000.json').write_bytes((r/'job-30000.json').read_bytes()+b' '),
            lambda r:(r/'initial.png').write_bytes(b''),lambda r:(r/'final-a.stdout').write_text(''),
            lambda r:edit(r,'peer_certificate',lambda row:row['value'].update(sha256='0'*64)),
            lambda r:edit(r,'arm_charge',lambda row:row['value'].update(duration_ns='1')),
            lambda r:edit(r,'network_body',lambda row:row['value']['body'].update(body='{}',base64Encoded=False)),
            lambda r:edit(r,'request_guard',lambda row:row['value']['request'].update(url='https://other.invalid/')),
            lambda r:(r/'browser-binding.json').write_text('{}'),
            lambda r:(r/'observer-failed.json').write_text('{}'),
            lambda r:(r/'browser.jsonl').write_bytes((r/'browser.jsonl').read_bytes()[:-1])]
        for n,change in enumerate(changes):
            with self.subTest(mutation=n),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(source,root);change(root)
                with self.assertRaises((ValueError,KeyError,IndexError)):audit(root)
        self.assertEqual(audit(source),expected)

if __name__=='__main__':unittest.main()
