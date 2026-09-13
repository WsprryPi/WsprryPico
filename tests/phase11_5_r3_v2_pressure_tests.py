import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_pressure_plan import validate
from phase11_5_r3_tls_pressure import Pressure
from phase11_5_r3_transport_pressure import TransportPressure

class PressureScopeTests(unittest.TestCase):
    def test_frozen_scope_and_refusals(self):
        base=Path(__file__).resolve().parents[1]/'build'
        for label,cls in [('t0',Pressure),('t1a',TransportPressure)]:
            file=base/f'phase11-5-r3-v2-pressure-{label}/stage/packet.json'
            if not file.exists():self.skipTest('Prospective local v2 pressure packet required')
            packet=json.loads(file.read_text());self.assertEqual(validate(packet),packet)
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);(root/'jobs.json').write_text(json.dumps(packet));(root/'load.json').write_text('{}')
                value=cls(root,lambda *_:None);self.assertEqual(value.packet,packet)
            for key,value in [('runtime_seconds',331),('maximum_tcp_connections',99),('pressure_family','unknown'),
                    ('observer_bracket_policy',None),('maximum_renewals',13),('configuration_writes',1),('ack_filter_policy','unsafe')]:
                altered=copy.deepcopy(packet);altered[key]=value
                with self.subTest(label=label,key=key),self.assertRaises(ValueError):validate(altered)
            altered=copy.deepcopy(packet);altered['pressure_cases'][0].pop()
            with self.assertRaises(ValueError):validate(altered)
            altered=copy.deepcopy(packet);altered['jobs'][0]['events'][0]['frequency_nhz']='135600000000000'
            with self.assertRaises(ValueError):validate(altered)

if __name__=='__main__':unittest.main()
