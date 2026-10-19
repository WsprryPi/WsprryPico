#!/usr/bin/env python3
"""Closed update schemas and vectors versus actual Pico handler responses."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

try:
    from jsonschema import Draft202012Validator
except ImportError:
    print('SKIP: requires existing jsonschema; this test never installs packages')
    sys.exit(77)

ROOT = Path(__file__).resolve().parents[1]
DRIVER = sys.argv.pop(1)
SCHEMA = json.loads((ROOT / 'engineering/protocol/transmitter-config-update-1.schema.json').read_text())
VECTORS = json.loads((ROOT / 'engineering/protocol/transmitter-config-update-1-vectors.json').read_text())


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


class ConfigUpdateSchemaTests(unittest.TestCase):
    def test_closed_vectors_against_actual_handler(self):
        Draft202012Validator.check_schema(SCHEMA)
        validator = Draft202012Validator(SCHEMA)
        for vector in VECTORS['vectors']:
            with self.subTest(vector=vector['name']):
                try:
                    value = json.loads(vector['raw'], object_pairs_hook=unique)
                    structural = validator.is_valid(value) and len(vector['raw'].encode()) <= 2048
                except ValueError:
                    structural = False
                self.assertEqual(structural, vector['structural_valid'])
                # Preserve all raw bytes, including duplicates, into the actual handler.
                result = subprocess.run([DRIVER, '--raw-update'], input=vector['raw'], text=True,
                                        capture_output=True, check=True)
                response = json.loads(result.stdout)
                self.assertEqual(response['status'], vector['http_status'])
                self.assertLessEqual(len(json.dumps(response['body']).encode()), 4096)


if __name__ == '__main__':
    unittest.main()
