"""The reclamation design cannot substitute short retention, reboot, or fewer cycles."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_admission import maximum_job
from phase11_5_r3_v2_reclamation_policy import validate,POLICY,terminal_expired
from phase11_5_r3_v2_retention_plan import cases,POLICY as HTTP_POLICY

class ReclamationPolicyTests(unittest.TestCase):
    def packet(self):
        jobs=[dict(job_id=f'{n+1:032x}',profile='rf-events/1',mode='tone',
            total_duration_ns='10000000000',allow_frequency_adjustment=True,
            events=[dict(offset_ns='0',duration_ns='10000000000',rf_on=True,frequency_nhz='135500000000000')])
            for n in range(8)]
        jobs.append(maximum_job('9'*32,512,1020_000_000_000))
        return dict(source_revision='c5f00b6109cc1c692b3f6bf258c1a77dadef6639',
            image_sha256='5f681b10d2c076309116cb9c20df1653d21e522ad19b6b33c1ee57efb3f54756',
            b_role='independent-zero-rf',cycle_number=1,runtime_seconds=6000,restoration_seconds=150,
            contention=dict(policy=POLICY,maximum_https_requests=301),owner_id='b'*32,jobs=jobs,
            reclamation=dict(initial_quiet_seconds=360,terminal_ttl_ns=3600_000_000_000,
                post_cache_seconds=60,resource_return_tolerance_bytes=1024,
                idle_groups=['terminal-lru-touch','post-expiry-max-reuse']),
            retention_http=dict(policy=HTTP_POLICY,seed='a'*32,cases=cases('a'*32,'b'*32),
                initial_quiet_seconds=360,expiry_quiet_seconds=360,maximum_connections=39,
                running_duration_ns='1020000000000'))
    def test_exact_equivalent_workload(self):
        p=self.packet();validate(p)
        for number in (1,2,3):p['cycle_number']=number;validate(p)
        for key,value in [('cycle_number',4),('runtime_seconds',4000),('source_revision','0'*40),
                          ('b_role','unchanged-comparator')]:
            q=copy.deepcopy(p);q[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(q)
        for key,value in [('terminal_ttl_ns',300_000_000_000),('resource_return_tolerance_bytes',4096),
                          ('initial_quiet_seconds',300)]:
            q=copy.deepcopy(p);q['reclamation'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(q)
        q=copy.deepcopy(p);q['jobs'].pop()
        with self.assertRaises(ValueError):validate(q)
    def test_absence_is_not_inferred_from_active_or_foreign_state(self):
        jobs=self.packet()['jobs'];s=dict(state='empty',output_active=False,owner_id=None,terminal_records=[])
        info=dict(status=dict(output_active=False))
        self.assertTrue(terminal_expired(s,info,jobs))
        s['terminal_records']=[dict(job_id=jobs[0]['job_id'])]
        self.assertFalse(terminal_expired(s,info,jobs))
        s['terminal_records']=[dict(job_id='f'*32)]
        with self.assertRaises(ValueError):terminal_expired(s,info,jobs)
        s.update(terminal_records=[],output_active=True)
        with self.assertRaises(ValueError):terminal_expired(s,info,jobs)

if __name__=='__main__':unittest.main()
