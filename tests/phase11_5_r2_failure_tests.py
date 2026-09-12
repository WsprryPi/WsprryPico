"""Opt-in offline raw-evidence mutations; requires the private captured attempt."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r2_failure import audit

ROOT=os.environ.get('PHASE115_R2_EVIDENCE')

@unittest.skipUnless(ROOT,'Private R2 evidence not supplied; no hardware access')
class PreservedFailure(unittest.TestCase):
    def test_intact_and_mutations(self):
        source=Path(ROOT).resolve()
        self.assertEqual(audit(source)['classification'],'VERIFIED_MISSED_START_NOT_ACCEPTED')
        mutations=[
            ('packet.json',lambda s:s.replace('138000000','150000000')),
            ('r2-tone/browser-jobs.jsonl',lambda s:s.replace('"operation": "ARM"','"operation": "ABORT"')),
            ('r2-tone/browser-jobs.jsonl',lambda s:s.replace('"http_status": 200','"http_status": 500')),
            ('missed-reconciliation-a.stdout',lambda s:s.replace('"state": "missed"','"state": "complete"')),
            ('missed-reconciliation-a.stdout',lambda s:s.replace('"launch_epoch": "0"','"launch_epoch": "1"')),
            ('missed-release.jsonl',lambda s:s.replace('"hex": "57545046','"hex": "57545047',1)),
            ('restored-original-boot.stdout',lambda s:s.replace('802c91a7b86e-dirty','wrong-revision')),
            ('after-b.stdout',lambda s:s.replace('feffcd075ab6cb0b74e7e0c2fde6c87f','0'*32)),
            ('final-restoration.json',lambda s:s.replace('"config": 28','"config": 27')),
            ('final-restoration.json',lambda s:s.replace('"configurations_match": true','"configurations_match": false')),
            ('fixture-state.json',lambda s:s.replace('"restored": true','"restored": false')),
            ('fixture.jsonl',lambda s:s.replace('"failures": []','"failures": ["injected"]')),
        ]
        for name, mutate in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                # Link immutable evidence; replace only one file with mutated bytes.
                for p in source.iterdir():
                    if p.name=='r2-tone':
                        (root/p.name).mkdir()
                        for q in p.iterdir():(root/p.name/q.name).symlink_to(q)
                    else:(root/p.name).symlink_to(p)
                path=root/name;before=path.read_text();changed=mutate(before)
                self.assertNotEqual(before,changed)
                path.unlink();path.write_text(changed)
                with self.assertRaises(ValueError):audit(root)
        self.assertEqual(audit(source)['completed_jobs'],0)

if __name__=='__main__':unittest.main()
