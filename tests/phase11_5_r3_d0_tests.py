import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_phase11_5_r3_d0 import audit


class D0AuditTests(unittest.TestCase):
    def test_raw_success_and_adversarial_mutations(self):
        source = os.environ.get('PHASE115_R3_D0_EVIDENCE')
        if not source:
            self.skipTest('Private D0 evidence not supplied')
        baseline = audit(Path(source))
        def mutate_rows(root, change):
            path = root / 'diagnostic.jsonl'
            rows = [json.loads(s) for s in path.read_text().splitlines()]
            change(rows)
            path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        def change_kind(rows, kind, key, value):
            next(r for r in rows if r['kind'] == kind)['value'][key] = value
        mutations = [
            lambda p: mutate_rows(p, lambda r: r.pop(12)),
            lambda p: mutate_rows(p, lambda r: change_kind(r,'capacity_write','bytes',4095)),
            lambda p: mutate_rows(p, lambda r: change_kind(r,'flash_pending','sha256','0'*64)),
            lambda p: mutate_rows(p, lambda r: change_kind(r,'maximum_response','output_active',True)),
            lambda p: mutate_rows(p, lambda r: change_kind(r,'maximum_response','boot_id','f'*32)),
            lambda p: (p/'flash.stdout').write_text('Failed verification\n'),
            lambda p: (p/'final-b.stdout').write_text(''),
            lambda p: (p/'final-a.stdout').write_text((p/'final-a.stdout').read_text().replace('481da3c3ff17','badbadbadbad')),
            lambda p: (p/'final-a.stdout').write_text((p/'final-a.stdout').read_text().replace('"fault_allocation_recorded": false','"fault_allocation_recorded": true')),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutations.index(mutation)), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)/'evidence'
                shutil.copytree(source, root)
                mutation(root)
                with self.assertRaises((ValueError, IndexError, KeyError)):
                    audit(root)
        self.assertEqual(audit(Path(source)), baseline)
