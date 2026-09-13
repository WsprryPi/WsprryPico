"""Opt-in raw replay of the consumed A1b failure, never a physical pass."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_phase11_5_r3_a1b_failure import audit

ROOT = os.environ.get('PHASE115_R3_A1B_EVIDENCE')


@unittest.skipUnless(ROOT, 'Private A1b evidence not supplied')
class A1bFailureTests(unittest.TestCase):
    def test_raw_failure_and_adversarial_mutations(self):
        source = Path(ROOT).resolve()
        original = audit(source)
        self.assertEqual(original['completed_jobs'], 1)
        self.assertEqual(original['accepted_assertions'], 0)
        self.assertFalse(original['http_response_bytes_retained'])
        mutations = [
            ('r3-result.json', '"status": "FAILED"', '"status": "PASS"'),
            ('tls-a1/pressure.jsonl', 'R3 HTTP status', 'Other failure'),
            ('tls-a1/usb-health.jsonl', 'Unexpected job/owner', 'Other failure'),
            ('tls-a1/usb-health.jsonl', '"launch_epoch": "1"', '"launch_epoch": "2"'),
            ('tls-a1/usb-health.jsonl', '"op": "ARM"', '"op": "ABORT"'),
            ('tls-a1/usb-health.jsonl', '"kind": "health"', '"kind": "injected"'),
            ('restore-admission-a.stdout', '"output_active": false', '"output_active": true'),
            ('management-state.json', '"config": 37', '"config": 38'),
            ('fixture-state.json', '"restored": true', '"restored": false'),
            ('fixture.jsonl', '"failures": []', '"failures": ["injected"]'),
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'evidence'; shutil.copytree(source, root)
            for name, before, after in mutations:
                path = root / name; raw = path.read_text(); self.assertIn(before, raw)
                path.write_text(raw.replace(before, after))
                with self.assertRaises((ValueError, KeyError)):
                    audit(root)
                path.write_text(raw)
            self.assertEqual(audit(root), original)


if __name__ == '__main__':
    unittest.main()
