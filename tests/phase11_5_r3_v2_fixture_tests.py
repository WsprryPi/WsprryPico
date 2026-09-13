import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_network_fixture import runtime_budget
from phase11_5_join_diagnostics import selected

class ExtendedFixtureTests(unittest.TestCase):
    def test_legacy_ceiling_preserved(self):
        self.assertEqual(runtime_budget({}),(21000,600))
        with self.assertRaises(ValueError):runtime_budget(dict(network_runtime_seconds=21001))
    def test_v2_limits(self):
        p=dict(schema='phase11.5-r3-v2-fixture-v1',standing_authority='R3-COMPLETE-20260913-v2',
            family='R3',configuration_writes=0,network_runtime_seconds=28800,network_restoration_seconds=900,
            network_join_diagnostics='ap-auth-dhcp-v1')
        self.assertEqual(runtime_budget(p),(28800,900));self.assertTrue(selected(p))
        for key,value in [('network_runtime_seconds',28801),('network_restoration_seconds',901),
                          ('network_runtime_seconds',True),('configuration_writes',1),
                          ('standing_authority','other'),('family','R4')]:
            q=copy.deepcopy(p);q[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):runtime_budget(q)

if __name__=='__main__':unittest.main()
