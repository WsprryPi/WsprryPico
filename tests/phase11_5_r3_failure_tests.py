"""Opt-in replay of the retained first R3 failure; no hardware or acceptance credit."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_phase11_5_r3_failure import audit
from audit_phase11_5_idle import audit as audit_idle

ROOT = os.environ.get('PHASE115_R3_FAILURE_EVIDENCE')


@unittest.skipUnless(ROOT, 'Private R3 failed evidence not supplied')
class FailureTests(unittest.TestCase):
    def test_retained_failure_raw_wire_restoration_and_mutations(self):
        source = Path(ROOT).resolve()
        self.assertEqual(audit(source)['classification'], 'FAILED_PREJOB_NO_RF_RESTORED')
        with self.assertRaises(ValueError):
            audit_idle(source / 'tls-a1/usb-health.jsonl', source / 'r3-a1-admission.stdout')
        mutations = [
            ('r3-result.json', '"status": "FAILED"', '"status": "PASS"'),
            ('device-state.json', '"restored": true', '"restored": false'),
            ('management-state.json', '"config": 36', '"config": 35'),
            ('tls-a1/pressure.jsonl', '"KeyError"', '"OtherError"'),
            ('tls-a1/usb-health.jsonl', '"launch_epoch": "0"', '"launch_epoch": "1"'),
            ('tls-a1/usb-health.jsonl', '"output_active": false', '"output_active": true'),
            ('tls-a1/usb-health.jsonl', 'Remaining USB jobs did not finish', 'Different fault'),
            ('restored-original-boot.stdout', '802c91a7b86e-dirty', 'unreviewed-firmware'),
            ('after-b.stdout', 'feffcd075ab6cb0b74e7e0c2fde6c87f', '0' * 32),
            ('fixture-state.json', '"restored": true', '"restored": false'),
            ('fixture.jsonl', '"failures": []', '"failures": ["injected"]'),
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'evidence'
            shutil.copytree(source, root)
            for name, before, after in mutations:
                path = root / name
                original = path.read_text()
                self.assertIn(before, original)
                path.write_text(original.replace(before, after))
                with self.assertRaises((ValueError, KeyError)):
                    audit(root)
                path.write_text(original)
            self.assertEqual(audit(root)['submitted_jobs'], 0)


if __name__ == '__main__':
    unittest.main()
