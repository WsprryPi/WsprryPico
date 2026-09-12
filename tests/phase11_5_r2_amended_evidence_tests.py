"""Opt-in offline mutations of the private amended campaign; no hardware access."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r1 import audit as audit_r1
from audit_phase11_5_r2 import audit as audit_r2

ROOT=os.environ.get('PHASE115_AMENDED_EVIDENCE')


@unittest.skipUnless(ROOT,'Private amended campaign evidence not supplied')
class Evidence(unittest.TestCase):
    def test_intact_and_mutated_completed_evidence(self):
        source=Path(ROOT).resolve()
        def audit(root):
            self.assertEqual(audit_r1(root)['target_assertions'],'PASS')
            result=audit_r2(root/'r2-tone',root/'pi/phase115_tls_observer_test.py')
            self.assertEqual(result['completed_jobs'],3)
            self.assertFalse(result['family_closed'])
        audit(source)
        mutations=[
            ('packet.json',lambda v:v.update(source_revision='f'*40)),
            ('r1-result.json',lambda v:v.update(quiet_delta_bytes=99999)),
            ('r1-result.json',lambda v:v['intervals'].pop('r1-normal')),
            ('device-state.json',lambda v:v.update(restored=False)),
            ('management-state.json',lambda v:v['counts'].update(config=31)),
            ('host-fixture-state.json',lambda v:v.update(restored=False)),
            ('r2-tone/jobs.json',lambda v:v.update(uf2_sha256='f'*64)),
            ('r2-tone/jobs.json',lambda v:v['jobs'][0].update(total_duration_ns='10000000001')),
            ('r2-tone/actor-result.json',lambda v:v.update(exit=1)),
        ]
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'evidence'
            shutil.copytree(source,target,ignore=shutil.ignore_patterns(
                'credentials','*.uf2','*.ini','original-config.json','before-flash.bin'))
            # Demonstrate that the copy itself passes before mutating any file.
            audit(target)
            for name,mutate in mutations:
                path=target/name;original=path.read_bytes()
                value=json.loads(original);mutate(value)
                path.write_text(json.dumps(value)+'\n')
                try:
                    with self.subTest(file=name),self.assertRaises((ValueError,KeyError)):
                        audit(target)
                finally:path.write_bytes(original)
            audit(target)
        audit(source)


if __name__=='__main__':unittest.main()
