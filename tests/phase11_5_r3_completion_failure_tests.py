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

EVIDENCE = os.environ.get('PHASE115_COMPLETION_P1_FAILURE')


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


if __name__ == '__main__':
    unittest.main()
