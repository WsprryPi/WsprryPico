"""Recovery evidence is necessary even when the producer's summary failed."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_v2_reconcile import audit

class RecoveryAuditTests(unittest.TestCase):
    def test_intact_and_missing_evidence(self):
        name=os.environ.get('PHASE115_R3_V2_RECONCILE_EVIDENCE') or os.environ.get('PHASE115_R3_V2_R0A_EVIDENCE')
        if not name:self.skipTest('Private R0a evidence required')
        root=Path(name);expected=audit(root)
        current=expected['original_runner_status']=='RECONCILED_INACTIVE_UNOWNED'
        self.assertEqual(expected['b_unchanged'],None if current else True)
        if not current:self.assertEqual(expected['original_runner_status'],'FAILED')
        files=['before-a.stdout','after-a.stdout','reconcile.jsonl','packet.json']
        if not current:files+=['before-b.stdout','after-b.stdout']
        for name in files:
            with self.subTest(removed=name),tempfile.TemporaryDirectory() as directory:
                altered=Path(directory)/'evidence';shutil.copytree(root,altered);(altered/name).write_text('')
                with self.assertRaises((ValueError,KeyError,IndexError)):audit(altered)
        self.assertEqual(audit(root),expected)

if __name__=='__main__':unittest.main()
