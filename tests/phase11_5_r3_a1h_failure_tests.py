"""No hardware: distinguish AP authentication, device readiness and record expiry."""
import copy,json,os,shutil,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_terminal_history import retained_prior
from audit_phase11_5_r3_a1h_failure import audit

@unittest.skipUnless(os.environ.get('PHASE115_R3_A1H_EVIDENCE'),'Private A1h evidence required')
class A1hTests(unittest.TestCase):
    def test_reconstructs_disagreement_and_rejects_changed_raw_evidence(self):
        source=Path(os.environ['PHASE115_R3_A1H_EVIDENCE']).resolve();original=audit(source)
        self.assertEqual(original['inventories'],12);self.assertEqual(original['completed_jobs'],0)
        self.assertFalse(original['firmware_defect_confirmed']);self.assertEqual(original['accepted_assertions'],0)
        self.assertTrue(original['assistant_tooling_defect_confirmed'])
        edits=[
            ('retained-result.json','"status": "FAILED"','"status": "PASS"'),
            ('retained-ap-identity.json','true','false'),
            ('wifi-recovery-admission.stdout','"link_status": 1','"link_status": 3'),
            ('wifi-recovery-admission.stdout','"output_active": false','"output_active": true'),
            ('diagnostic-ready-1.stdout','"launch_epoch": "4"','"launch_epoch": "5"'),
            ('final-terminal-before.stdout','"terminal_record_ttl_seconds": 3600','"terminal_record_ttl_seconds": 10'),
            ('ap-before-recovery.json','EAPOL-4WAY-HS-COMPLETED','AP-STA-POSSIBLE-PSK-MISMATCH'),
            ('ap-before-recovery.json','88:a2:9e:0a:60:df','88:a2:9e:00:00:00'),
            ('ap-before-host-cleanup.json','associated:\\tyes','associated:\\tno'),
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
            path=root/'diagnostic-ready-0.stdout';raw=path.read_text();path.write_text(raw.rstrip('\n'))
            with self.assertRaises(ValueError):audit(root)
            path.write_text(raw);self.assertEqual(audit(root),original)

if __name__=='__main__':unittest.main()
