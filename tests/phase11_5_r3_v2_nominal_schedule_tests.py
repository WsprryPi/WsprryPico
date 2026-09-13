"""Finite HTTPS scheduling failures; virtual time does not qualify target cadence."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_nominal_load import periodic_https

class ScheduleTests(unittest.TestCase):
    def run_clock(self,delays,deadline=81,lateness=0,stop_at=None,done_at=None):
        now=[7.5];starts=[];waits=[]
        class Stop:
            def wait(self,seconds):
                waits.append(seconds)
                now[0]+=seconds+lateness
                return stop_at is not None and now[0]>=stop_at
        def observe():
            starts.append(now[0]);now[0]+=delays[len(starts)-1]
        periodic_https(0,deadline,Stop(),observe,lambda:done_at is not None and now[0]>=done_at,lambda:now[0])
        return starts,waits
    def test_response_time_does_not_shift_starts(self):
        self.assertEqual(self.run_clock([15,1,12,2])[0],[20,40,60,80])
    def test_no_request_after_deadline(self):
        self.assertEqual(self.run_clock([15],40)[0],[20])
    def test_stop_during_wait(self):
        self.assertEqual(self.run_clock([],stop_at=20)[0],[])
    def test_completed_rf_during_wait(self):
        self.assertEqual(self.run_clock([],done_at=20)[0],[])
    def test_missed_start_is_failure_without_request(self):
        with self.assertRaises(ValueError):self.run_clock([],lateness=1.01)
    def test_boundary_jitter_does_not_accumulate(self):
        self.assertEqual(self.run_clock([15,1,12,2],deadline=82,lateness=1)[0],[21,41,61,81])
    def test_late_wakeup_cannot_start_at_deadline(self):
        self.assertEqual(self.run_clock([],deadline=21,lateness=1)[0],[])

if __name__=='__main__':unittest.main()
