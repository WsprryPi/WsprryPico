import copy,json
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_browser_observer import validate

class BrowserScopeTests(unittest.TestCase):
    def test_remaining_cases_require_preserved_results_and_real_quiet(self):
        file=Path(__file__).resolve().parents[1]/'build/phase11-5-r3-v2-browser-b5/stage/packet.json'
        if not file.exists():self.skipTest('Prospective local continuation packet required')
        packet=json.loads(file.read_text());self.assertEqual(validate(packet),packet)
        for key,value in [('case_indices',[3,2]),('case_indices',[3]),('maximum_jobs',3),
                ('between_case_quiet_seconds',299),('between_case_quiet_seconds',361),
                ('reused_completed_fskcw_audit_sha256','0'*64),('reused_browser_audit_sha256','0'*64)]:
            changed=copy.deepcopy(packet);changed[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):validate(changed)

    def test_bounded_actual_producer(self):
        file=Path(__file__).resolve().parents[1]/'build/phase11-5-r3-v2-browser-b1/stage/packet.json'
        if not file.exists():self.skipTest('Prospective local browser packet required')
        packet=json.loads(file.read_text());self.assertEqual(validate(packet),packet)
        for key,value in [('runtime_seconds',901),('maximum_jobs',5),('maximum_request_count',251),
                ('configuration_writes',1),('running_abort_after_ns',110000000000),('source_revision','0'*40)]:
            changed=copy.deepcopy(packet);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(changed)
        for mutate in [lambda p:p['cases'].pop(),lambda p:p['cases'][1]['message'].update(message='?'*33),
            lambda p:p['cases'][1]['message'].update(frequency_nhz='140000000000000'),
            lambda p:p['cases'][3]['message']['timing'].update(dot_ns='350000001')]:
            changed=copy.deepcopy(packet);mutate(changed)
            with self.assertRaises(ValueError):validate(changed)

if __name__=='__main__':unittest.main()
