import copy,json
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_browser_observer import validate

class BrowserScopeTests(unittest.TestCase):
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
