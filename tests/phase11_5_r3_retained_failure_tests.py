"""Adversarial raw replay of A1c; successful audit still awards zero acceptance."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_retained_failure import audit

ROOT = os.environ.get('PHASE115_R3_A1C_EVIDENCE')


@unittest.skipUnless(ROOT, 'Private A1c evidence not supplied')
class RetainedFailureTests(unittest.TestCase):
    def test_raw_reconstruction_rejects_mutations_and_recovers_after_each(self):
        source = Path(ROOT).resolve()
        original = audit(source)
        self.assertEqual(original['accepted_assertions'], 0)
        self.assertEqual(original['submitted_jobs'], 0)
        self.assertEqual(original['inventories'], 30)
        mutations = [
            ('retained-result.json', '"status": "FAILED"', '"status": "PASS"'),
            ('retained-result.json', '"configuration_writes": 0', '"configuration_writes": 1'),
            ('retained-result.json', '"host_restored": true', '"host_restored": false'),
            ('network-ready-24.stdout', '"link_status": -3', '"link_status": 3'),
            ('network-ready-24.stdout', '"output_active": false', '"output_active": true'),
            ('network-ready-13.stdout', '"launch_epoch": "1"', '"launch_epoch": "2"'),
            ('initial-terminal-release.jsonl', '"op": "RELEASE"', '"op": "ABORT"'),
            ('initial-terminal-release.jsonl', '"lease_ms": 60000', '"lease_ms": 5000'),
            ('initial-terminal-release.jsonl', '"state": "empty"', '"state": "running"'),
            ('initial-terminal-before.stdout', '"state": "complete"', '"state": "failed"'),
            ('after-b.stdout', 'feffcd075ab6cb0b74e7e0c2fde6c87f', '1'*32),
            ('fixture-state.json', '"restored": true', '"restored": false'),
            ('fixture.jsonl', '"failures": []', '"failures": ["injected"]'),
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'evidence'; shutil.copytree(source, root)
            for name, before, after in mutations:
                path = root/name; raw = path.read_text(); self.assertIn(before, raw)
                path.write_text(raw.replace(before, after))
                with self.assertRaises((ValueError, KeyError)): audit(root)
                path.write_text(raw)
                self.assertEqual(audit(root), original)
            path = root/'network-ready-1.stdout'; raw = path.read_text()
            path.write_text(raw.rstrip('\n'))
            with self.assertRaises(ValueError): audit(root)
            path.write_text(raw)
            (root/'tls-a1').mkdir()
            with self.assertRaises(ValueError): audit(root)
            (root/'tls-a1').rmdir()
            path = root/'network-ready-2.stdout'; raw = path.read_text()
            path.write_text((root/'network-ready-1.stdout').read_text())
            with self.assertRaises(ValueError): audit(root)
            path.write_text(raw)
            path = root/'initial-terminal-release.jsonl'; raw = path.read_text()
            trace = [json.loads(line) for line in raw.splitlines()]
            tx = next(r for r in trace if r['kind'] == 'wtp_tx')
            data = bytearray.fromhex(tx['value']['hex']); data[-2] ^= 1
            tx['value']['hex'] = data.hex()
            path.write_text(''.join(json.dumps(r)+'\n' for r in trace))
            with self.assertRaises(ValueError): audit(root)
            path.write_text(raw)
            self.assertEqual(audit(root), original)


if __name__ == '__main__': unittest.main()
