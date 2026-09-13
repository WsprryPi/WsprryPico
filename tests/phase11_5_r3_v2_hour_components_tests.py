"""A failed observation assertion must remain failed while independent evidence stays valid."""
import json,os,shutil,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_v2_hour import audit

@unittest.skipUnless(os.environ.get('PHASE115_R3_V2_H0_COMPONENT_EVIDENCE'),'Private H0 component evidence required')
class HourComponentTests(unittest.TestCase):
    def test_strict_failure_and_independent_components(self):
        source=Path(os.environ['PHASE115_R3_V2_H0_COMPONENT_EVIDENCE'])
        def run(root,report=False):return audit(root,root/'pi/phase115_tls_observer_test.py',report_cadence_findings=report)
        with self.assertRaisesRegex(ValueError,'https full-hour'):run(source)
        expected=run(source,True)
        self.assertTrue(expected['physical_hour_verified']);self.assertFalse(expected['all_contention_cadence_passed'])
        self.assertEqual({k:v['status'] for k,v in expected['contention_coverage'].items()},
            {'native_wire':'PASS','native_http':'PASS','https':'FAILED'})
        self.assertEqual([v['family'] for v in expected['cadence_findings']],['https'])
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'evidence';shutil.copytree(source,root)
            file=root/'contention.jsonl';rows=[json.loads(s) for s in file.read_text().splitlines()]
            sample=next(r for r in rows if r['kind']=='https_status');sample['value']['peer_sha256']='0'*64
            file.write_text(''.join(json.dumps(r)+'\n' for r in rows))
            # Reporting cadence findings cannot excuse false authentication evidence.
            with self.assertRaisesRegex(ValueError,'HTTPS request/authentication'):run(root,True)
        self.assertEqual(run(source,True),expected)

if __name__=='__main__':unittest.main()
