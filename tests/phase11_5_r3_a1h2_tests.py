"""Adversarial replay of the physical A1h2 subset; no hardware access."""
import json,os,shutil,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_a1h2 import audit

@unittest.skipUnless(os.environ.get('PHASE115_R3_A1H2_EVIDENCE'),'Private A1h2 evidence required')
class A1h2Tests(unittest.TestCase):
    def test_pass_requires_raw_pressure_rf_authority_and_restoration(self):
        source=Path(os.environ['PHASE115_R3_A1H2_EVIDENCE']);original=audit(source)
        self.assertEqual(original['accepted_a1_pressure_cases'],10)
        self.assertFalse(original['family_closed']);self.assertEqual(original['completed_jobs'],2)
        edits=[('retained-result.json','"host_restored": true','"host_restored": false'),
            ('wifi-recovery.json','"off": 1','"off": 2'),
            ('retained-ap-identity.json','true','false'),
            ('network-ready-1.stdout','"state": "synchronized"','"state": "unsynchronized"'),
            ('after-b.stdout','feffcd075ab6cb0b74e7e0c2fde6c87f','1'*32),
            ('tls-a1/pressure.jsonl','"alert": 116','"alert": 117'),
            ('tls-a1/pressure.jsonl','"version": "TLSv1.3"','"version": "TLSv1.2"'),
            ('tls-a1/result.json','"pressure_exit": 0','"pressure_exit": 1'),
            ('fixture-state.json','"restored": true','"restored": false'),
            ('ap-before-host-cleanup.json','88:a2:9e:0a:60:df','88:a2:9e:00:00:00')]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'evidence';shutil.copytree(source,root)
            for name,before,after in edits:
                with self.subTest(name=name):
                    p=root/name;raw=p.read_text();self.assertIn(before,raw);p.write_text(raw.replace(before,after))
                    with self.assertRaises((ValueError,KeyError)):audit(root)
                    p.write_text(raw)
            p=root/'tls-a1/pressure.jsonl';raw=p.read_text();items=[json.loads(s) for s in raw.splitlines()]
            end=next(r for r in items if r['kind']=='case_finish');end['monotonic_ns']+=20_000_000_000
            p.write_text(''.join(json.dumps(r)+'\n' for r in items))
            with self.assertRaises(ValueError):audit(root)
            p.write_text(raw)
            p=root/'tls-a1/usb-health.jsonl';raw=p.read_bytes();p.write_bytes(raw[:-1])
            with self.assertRaises(ValueError):audit(root)
            p.write_bytes(raw)
            self.assertEqual(audit(root),original)

if __name__=='__main__':unittest.main()
