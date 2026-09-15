"""Altered evidence must not turn the first completion failure into acceptance."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_completion_p1_failure import audit
from audit_phase11_5_completion_prearm import audit as audit_prearm

EVIDENCE = os.environ.get('PHASE115_COMPLETION_P1_FAILURE')
PREARM = os.environ.get('PHASE115_COMPLETION_PREARM')


@unittest.skipUnless(EVIDENCE, 'Private completed packet not supplied')
class Tests(unittest.TestCase):
    def test_preserved_failure(self):
        value = audit(Path(EVIDENCE))
        self.assertFalse(value['capacity_acceptance'])
        self.assertEqual(value['host_bytes_written'], 4096)

    def test_rejects_altered_write_console_and_completion(self):
        for mutation in ('write', 'console', 'completion'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)/'evidence'; shutil.copytree(EVIDENCE, root)
                path = root/'rf.jsonl'
                rows = [json.loads(line) for line in path.read_text().splitlines()]
                if mutation == 'write':
                    next(r for r in rows if r['kind']=='capacity_write')['value']['total_written']=65552
                elif mutation == 'console':
                    next(r for r in rows if r['kind']=='info')['value']['value']['status']['output_active']=True
                else:
                    value = json.loads((root/'rf-result.json').read_text())
                    value['status']='CAPTURED_REQUIRES_AUDIT'; rows[-1]['value']=value
                    (root/'rf-result.json').write_text(json.dumps(value))
                path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
                with self.assertRaises(ValueError):
                    audit(root)


@unittest.skipUnless(PREARM, 'Private pre-ARM packet not supplied')
class PrearmTests(unittest.TestCase):
    def test_failure_without_acceptance(self):
        result = audit_prearm(Path(PREARM))
        self.assertFalse(result['acceptance'])
        self.assertEqual(result['rf_jobs_charged'], 0)

    def test_rejects_missing_request_and_false_accounting(self):
        for mutation in ('request', 'accounting'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)/'evidence'; shutil.copytree(PREARM, root)
                path = root/'rf.jsonl'
                rows = [json.loads(line) for line in path.read_text().splitlines()]
                if mutation == 'request':
                    rows.remove(next(r for r in rows if r['kind'] == 'wtp_tx'))
                else:
                    result = json.loads((root/'rf-result.json').read_text())
                    result['rf_duration_ns_charged'] = 128_000_000_000
                    rows[-1]['value'] = result
                    (root/'rf-result.json').write_text(json.dumps(result))
                path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
                with self.assertRaises(ValueError):
                    audit_prearm(root)


if __name__ == '__main__':
    unittest.main()
