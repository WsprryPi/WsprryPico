"""No hardware: distinguish AP authentication, device readiness and record expiry."""
import copy,json,os,shutil,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_terminal_history import retained_prior
from audit_phase11_5_r3_a1g_failure import audit

class ExpiryTests(unittest.TestCase):
    def test_expiry_uses_target_age_inclusive_boundary_without_refresh(self):
        r=dict(job_id='a'*32,state='complete',ended_monotonic_ns='10',output_active=False)
        c=dict(terminal_record_entries=8,terminal_record_ttl_seconds=3600);expiry=3600*10**9+10
        self.assertEqual(retained_prior([r],c,expiry-2,expiry-1),([r],[]))
        self.assertEqual(retained_prior([r],c,expiry,expiry+2),([],[r]))
        with self.assertRaisesRegex(ValueError,'inside the observation clock bracket'):
            retained_prior([r],c,expiry-1,expiry)
        for lower,upper in ((20,10),(-1,0),(0,1)):
            with self.assertRaises(ValueError):retained_prior([r],c,lower,upper)
        for bad in (c|dict(terminal_record_ttl_seconds=1),c|dict(terminal_record_entries=9)):
            with self.assertRaises(ValueError):retained_prior([r],bad,expiry,expiry+1)
        for changed in (r|dict(state='failed'),r|dict(output_active=True)):
            with self.assertRaises(ValueError):retained_prior([changed],c,expiry,expiry+1)

    def test_remaining_records_preserve_exact_contents_and_order(self):
        records=[dict(job_id=str(i)*32,state='complete',ended_monotonic_ns=str(i*10**12),output_active=False) for i in (3,2,1)]
        original=copy.deepcopy(records);c=dict(terminal_record_entries=8,terminal_record_ttl_seconds=3600)
        kept,expired=retained_prior(records,c,4_700_000_000_000,4_700_100_000_000)
        self.assertEqual(kept,records[:2]);self.assertEqual(expired,records[2:]);self.assertEqual(records,original)
        with self.assertRaises(ValueError):retained_prior(records+[records[0]],c,4_700_000_000_000,4_700_100_000_000)

@unittest.skipUnless(os.environ.get('PHASE115_R3_A1G_EVIDENCE'),'Private A1g evidence required')
class A1gTests(unittest.TestCase):
    def test_reconstructs_disagreement_and_rejects_changed_raw_evidence(self):
        source=Path(os.environ['PHASE115_R3_A1G_EVIDENCE']).resolve();original=audit(source)
        self.assertEqual(original['inventories'],29);self.assertEqual(original['completed_jobs'],0)
        self.assertFalse(original['firmware_defect_confirmed']);self.assertEqual(original['accepted_assertions'],0)
        self.assertEqual(original['expired_terminal_jobs'],['d27689688f2f3e519a3836b775b3092b'])
        edits=[
            ('retained-result.json','"status": "FAILED"','"status": "PASS"'),
            ('retained-ap-identity.json','true','false'),
            ('network-ready-24.stdout','"link_status": -3','"link_status": 3'),
            ('network-ready-24.stdout','"output_active": false','"output_active": true'),
            ('network-ready-1.stdout','"launch_epoch": "4"','"launch_epoch": "5"'),
            ('final-terminal-before.stdout','5461175002000','9461175002000'),
            ('final-terminal-before.stdout','"terminal_record_ttl_seconds": 3600','"terminal_record_ttl_seconds": 10'),
            ('supplicant-journal.json','EAPOL-4WAY-HS-COMPLETED','AP-STA-POSSIBLE-PSK-MISMATCH'),
            ('supplicant-journal.json','88:a2:9e:0a:60:df','88:a2:9e:00:00:00'),
            ('after-b.stdout','feffcd075ab6cb0b74e7e0c2fde6c87f','1'*32),
            ('fixture-state.json','"restored": true','"restored": false'),
        ]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'evidence';shutil.copytree(source,root)
            for name,before,after in edits:
                with self.subTest(file=name):
                    path=root/name;raw=path.read_text();self.assertIn(before,raw);path.write_text(raw.replace(before,after))
                    with self.assertRaises((ValueError,KeyError)):audit(root)
                    path.write_text(raw);self.assertEqual(audit(root),original)
            (root/'tls-a1').mkdir()
            with self.assertRaises(ValueError):audit(root)
            (root/'tls-a1').rmdir()
            path=root/'network-ready-0.stdout';raw=path.read_text();path.write_text(raw.rstrip('\n'))
            with self.assertRaises(ValueError):audit(root)
            path.write_text(raw);self.assertEqual(audit(root),original)

if __name__=='__main__':unittest.main()
