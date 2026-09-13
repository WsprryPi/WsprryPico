"""Adversarial reconstruction of the real B1 capture; never rescored as PASS."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_phase11_5_r3_b1_failure import audit


@unittest.skipUnless(os.environ.get('PHASE115_R3_B1_EVIDENCE'), 'Private B1 archive not provided')
class B1FailureTests(unittest.TestCase):
    def test_classifies_raw_failure_and_preserves_both_actual_completions(self):
        value = audit(Path(os.environ['PHASE115_R3_B1_EVIDENCE']))
        self.assertEqual(value['classification'], 'HARNESS_ACK_SUPPRESSION_BEFORE_SERVER_FLIGHT')
        self.assertEqual((value['accepted_assertions'], value['completed_jobs'], len(value['preliminary_cases'])), (0, 2, 12))
        self.assertEqual(value['samples'], dict(info=360, status=72, health=72))

    def test_raw_summary_causality_and_cleanup_mutations_are_rejected(self):
        original = Path(os.environ['PHASE115_R3_B1_EVIDENCE'])
        for mutation in ('failure-reason', 'server-flight', 'reported-counter', 'missing-capture-byte',
                         'raw-load-disagreement', 'info-disagreement', 'cleanup-claim', 'filter-removal'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / 'evidence'
                shutil.copytree(original, root)
                case = root / 'tls-a1'
                if mutation in ('failure-reason', 'server-flight', 'reported-counter'):
                    path = case / 'pressure.jsonl'
                    rows = [json.loads(s) for s in path.read_text().splitlines()]
                    if mutation == 'failure-reason': rows[-1]['value']['error'] = 'firmware failure'
                    elif mutation == 'server-flight': rows[75]['value']['hex'] = '00' * 127
                    else: rows[5]['value']['transport']['timeouts'] += 1
                    path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
                elif mutation == 'missing-capture-byte':
                    path = case / 'transport.pcap'; path.write_bytes(path.read_bytes()[:-1])
                elif mutation in ('raw-load-disagreement', 'info-disagreement'):
                    path = case / 'usb-health.jsonl'
                    rows = [json.loads(s) for s in path.read_text().splitlines()]
                    if mutation == 'raw-load-disagreement':
                        row = next(r for r in rows if r['kind'] == 'wtp_tx' and r['value']['request']['op'] == 'LOAD')
                        row['value']['request']['body']['total_duration_ns'] = '1'
                    else:
                        row = next(r for r in rows if r['kind'] == 'info')
                        row['value']['value']['heap_allocated_bytes'] += 1
                    path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
                else:
                    path = root / 'retained-result.json' if mutation == 'cleanup-claim' else case / 'ack-filter.json'
                    value = json.loads(path.read_text())
                    if mutation == 'cleanup-claim': value['host_restored'] = False
                    else: value['status'] = 'INSTALLED'
                    path.write_text(json.dumps(value))
                with self.assertRaises((ValueError, KeyError, StopIteration)):
                    audit(root)


if __name__ == '__main__':
    unittest.main()
