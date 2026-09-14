"""Adversarial checks for preserved setup failures and the authenticated trust probe."""
import json,os,shutil,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_v2_browser_setup import audit
class SetupAuditTests(unittest.TestCase):
    def check_case(self,kind):
        variable='PHASE115_R3_V2_BROWSER_'+kind.upper()+'_EVIDENCE';source=os.environ.get(variable)
        if not source:self.skipTest('Private '+kind+' evidence required')
        source=Path(source);expected=audit(source,kind)
        def edit(root,name,fn):
            p=root/name;x=json.loads(p.read_text());fn(x);p.write_text(json.dumps(x)+'\n')
        def trace(root,kind,fn):
            p=root/'browser.jsonl';rows=[json.loads(x) for x in p.read_text().splitlines()];fn(next(r for r in rows if r['kind']==kind)['value']);p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        changes=[lambda r:(r/'packet.json').write_text('{}'),lambda r:(r/'browser.jsonl').write_bytes((r/'browser.jsonl').read_bytes()[:-1]),
            lambda r:edit(r,'browser-result.json',lambda x:x.update(rf_jobs_charged=1)),
            lambda r:trace(r,'request_guard',lambda x:x['request'].update(method='POST')),
            lambda r:trace(r,'request_guard',lambda x:x['request'].update(url='https://other.invalid/'))]
        if kind=='b6':
            changes += [lambda r:trace(r,'network_body',lambda x:x['body'].update(body='{}',base64Encoded=False)),
                lambda r:(r/'final-a.stdout').write_text(''),lambda r:(r/'browser-observer.jsonl').write_text(''),
                lambda r:edit(r,'observer-failed.json',lambda x:x.update(faults=[]))]
        elif kind=='b2':changes+=[lambda r:(r/'recovery-final-a2.stdout').write_text('')]
        else:changes+=[lambda r:edit(r,'initial-dom.json',lambda x:x['job'].update(output_active=True))]
        for n,change in enumerate(changes):
            with self.subTest(kind=kind,mutation=n),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(source,root);change(root)
                with self.assertRaises((ValueError,KeyError,IndexError,AssertionError)):audit(root,kind)
        self.assertEqual(audit(source,kind),expected)
    def test_b2(self):self.check_case('b2')
    def test_p0(self):self.check_case('p0')
    def test_b6(self):self.check_case('b6')
if __name__=='__main__':unittest.main()
