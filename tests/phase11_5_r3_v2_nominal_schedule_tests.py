"""Finite HTTPS scheduling failures; virtual time does not qualify target cadence."""
import sys,unittest,json,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_nominal_load import periodic_https,await_capacity_phase

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
    def test_missing_capacity_completion_cannot_admit_http(self):
        with tempfile.TemporaryDirectory() as directory:
            now=[1]
            class Stop:
                def wait(self, seconds):now[0]+=1;return False
            with self.assertRaisesRegex(ValueError,'no HTTP capacity traffic'):
                await_capacity_phase(Path(directory),'a','b',3,Stop(),lambda:False,lambda:now[0])
    def test_capacity_completion_requires_identity_and_full_sequence(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);good=dict(packet_sha256='a',job_id='b',completed_exchanges=2,monotonic_ns=1)
            for bad in [dict(packet_sha256='c'),dict(job_id='c'),dict(completed_exchanges=1),
                        dict(completed_exchanges=True),dict(monotonic_ns=3_000_000_000)]:
                (root/'wtp-capacity-complete.json').write_text(json.dumps(good|bad))
                with self.assertRaises(ValueError):
                    await_capacity_phase(root,'a','b',3,None,lambda:False,lambda:2)
            (root/'wtp-capacity-complete.json').write_text(json.dumps(good))
            self.assertEqual(await_capacity_phase(root,'a','b',3,None,lambda:False,lambda:2),good)

class NativePublicationTests(unittest.TestCase):
    def test_cached_identity_does_not_prove_connected_authority(self):
        from phase11_5_r3_v2_nominal_load import native_status_live
        packet=dict(boot_id='b'*32)
        remote=dict(boot_id=packet['boot_id'],state='running',output_active=True)
        host=dict(ready=True,session_phase='ready',remote=remote,now_ms='10000',status_observed_ms='9900')
        self.assertTrue(native_status_live(dict(host=host,job=remote),packet))
        for changed in (dict(ready=False),dict(session_phase='disconnected'),dict(remote=None),
                        dict(status_observed_ms=None),dict(status_observed_ms='0')):
            self.assertFalse(native_status_live(dict(host=dict(host,**changed),job=remote),packet))

    def test_candidate_policy_publishes_the_consumed_running_authority(self):
        from phase11_5_r3_v2_nominal_load import publish_native
        from phase11_5_r3_v2_rf import TERMINAL_POLICY, native_running
        import json
        import tempfile
        import time
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet = dict(closure_policy=TERMINAL_POLICY, boot_id='b'*32,
                          owner_id='c'*32, jobs=[dict(job_id='d'*32)])
            value = dict(job=dict(boot_id=packet['boot_id'],owner_id=packet['owner_id'],
                         job_id=packet['jobs'][0]['job_id'],state='running',output_active=True))
            publish_native(root,packet,'a'*64,value)
            record = json.loads((root/'native-observation.json').read_text())
            self.assertTrue(native_running(record,packet,'a'*64,time.monotonic_ns()))


if __name__=='__main__':unittest.main()
