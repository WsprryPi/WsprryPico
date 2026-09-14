"""Prospective INFO policy failure bounds and recorded B7 latency regression."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_observer_policy import validate_intervals,next_offer

class ObserverPolicyTests(unittest.TestCase):
    def test_nominal_hz(self):
        self.assertEqual(next_offer(1.0,1.1),2.0)
        self.assertEqual(validate_intervals([0,10**9,2*10**9],[10**8,11*10**8,21*10**8],0,3*10**9)['samples'],3)

    def test_measured_b7_latency_is_not_idle_host_delay(self):
        # Prospective scheduler test only: B7 remains FAILED and is never regraded.
        reply=2177624184;next_start=reply+10_000_000
        self.assertEqual(next_offer(0,reply/1e9),reply/1e9)
        r=validate_intervals([0,next_start],[reply,next_start+100_000_000],0,next_start+1_000_000_000)
        self.assertEqual(r['max_roundtrip_ns'],reply)

    def test_late_idle_offer_rejected(self):
        with self.assertRaisesRegex(ValueError,'offer'):
            validate_intervals([0,2_000_000_001],[100_000_000,2_100_000_001],0,3_000_000_001)

    def test_late_offer_after_slow_reply_rejected(self):
        with self.assertRaisesRegex(ValueError,'offer'):
            validate_intervals([0,4_000_000_001],[3_000_000_000,4_100_000_001],0,5_000_000_001)

    def test_six_second_read_rejected(self):
        with self.assertRaisesRegex(ValueError,'five-second'):
            validate_intervals([0],[5_000_000_001],0,6_000_000_000)

    def test_overlapping_request_rejected(self):
        with self.assertRaisesRegex(ValueError,'overlap'):
            validate_intervals([0,1_000_000_000],[2_000_000_000,2_100_000_000],0,3_000_000_000)

    def test_missing_tail_initial_and_rows_rejected(self):
        for args in [([],[],0,0),([0],[100_000_000],0,2_000_000_001),
                     ([2_000_000_001],[2_100_000_001],0,3_000_000_000)]:
            with self.subTest(args=args),self.assertRaises(ValueError):validate_intervals(*args)

if __name__=='__main__':unittest.main()
