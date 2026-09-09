#!/usr/bin/env python3
"""Hardware-free trace evidence refusal tests."""
import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_4_trace_audit import trace_events, fingerprint
from phase11_4_loop_common import DEVICE

class TraceTests(unittest.TestCase):
    def fixture(self):
        return [{'kind':'NETTRACE','value':{'ok':True,'device_id':DEVICE,'boot_id':'boot',
            'revision':'candidate','trace':{'oldest':1,'latest':2,'overwritten':0,
             'intact':True,'install_errors':0,'events':[
              {'seq':i,'us':10+i,'end_us':10+i,'kind':3,'generation':1,'header':''}
              for i in (1,2)]}}}]
    def test_complete_and_fingerprint(self):
        self.assertEqual(len(trace_events(self.fixture(),'boot','candidate')),2)
        self.assertEqual(fingerprint(b'hello'),0x4f9f2cab)
    def test_corruption_refused(self):
        variants=[]
        for field,value in [('device_id','wrong'),('boot_id','wrong'),('revision','wrong'),('ok',False)]:
            r=self.fixture();r[0]['value'][field]=value;variants.append(r)
        for field,value in [('intact',False),('install_errors',1),('oldest',2),('latest',3),('overwritten',1)]:
            r=self.fixture();r[0]['value']['trace'][field]=value;variants.append(r)
        r=self.fixture();r[0]['value']['trace']['events'][1]['seq']=4;variants.append(r)
        r=self.fixture();r[0]['value']['trace']['events'][1]['end_us']=0;variants.append(r)
        r=self.fixture();r[0]['value']['trace']['events'].pop();variants.append(r)
        for r in variants:
            with self.subTest(r=r), self.assertRaises(ValueError):trace_events(r,'boot','candidate')
    def test_cross_page_gap_refused(self):
        rows=self.fixture();second=copy.deepcopy(rows[0]);second['value']['trace'].update(latest=4)
        second['value']['trace']['events']=[dict(rows[0]['value']['trace']['events'][0],seq=4)]
        with self.assertRaises(ValueError):trace_events(rows+[second],'boot','candidate')
if __name__=='__main__':unittest.main()
