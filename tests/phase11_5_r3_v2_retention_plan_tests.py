"""Real expiry and full/LRU semantics remain separate, with a finite RF budget."""
import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_retention_plan import cases,validate_plan,POLICY

class RetentionPlanTests(unittest.TestCase):
    def test_finite_scope_and_same_session_replay(self):
        owner='b'*32;rows=cases('a'*32,owner)
        p=dict(policy=POLICY,seed='a'*32,cases=rows,initial_quiet_seconds=360,
            expiry_quiet_seconds=360,maximum_connections=39,running_duration_ns='1020000000000')
        validate_plan(p,owner);by={r['label']:r for r in rows}
        self.assertEqual(len({r['request']['session_id'] for r in rows[:14]}),14)
        self.assertEqual(by['session-17-overflow']['error_code'],'BUSY')
        self.assertEqual(by['replay-fill-0']['wire_hex'],by['replay-touch-oldest']['wire_hex'])
        self.assertEqual(by['replay-conflict-1']['wire_hex'],by['replay-evicted-second']['wire_hex'])
        self.assertEqual(by['replay-conflict-1']['expected_status'],409)
        self.assertEqual(by['replay-evicted-second']['expected_status'],200)
        self.assertEqual(by['replay-touched-retained']['error_code'],'REQUEST_ID_REUSE')
        self.assertEqual(by['session-0-expired']['request']['operation'],'RENEW')
        self.assertEqual(by['session-0-expired']['error_code'],'HELLO_REQUIRED')
        self.assertEqual(by['replay-conflict-0']['wire_hex'],by['replay-expired-and-session-reused']['wire_hex'])
        for r in rows:
            raw=bytes.fromhex(r['wire_hex']);head,body=raw.split(b'\r\n\r\n',1)
            self.assertEqual(json.loads(body),r['request'])
            self.assertIn(('Content-Length: '+str(len(body))).encode(),head)
            self.assertIn(r['request']['operation'],['HELLO','RENEW'])
        for key,value in [('expiry_quiet_seconds',299),('maximum_connections',40),('running_duration_ns','100000000000')]:
            q=copy.deepcopy(p);q[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_plan(q,owner)
        q=copy.deepcopy(p);q['cases'][15]['expected_status']=409
        with self.assertRaises(ValueError):validate_plan(q,owner)

if __name__=='__main__':unittest.main()
