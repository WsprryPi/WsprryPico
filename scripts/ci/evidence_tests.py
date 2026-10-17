#!/usr/bin/env python3
"""Inventory deliberately unavailable private historical evidence, without hiding dependencies."""
import json
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[2]
suite = unittest.defaultTestLoader.discover(str(root / 'tests'), pattern='phase11_5_r3*tests.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
skips = [{'test': test.id(), 'reason': reason} for test, reason in result.skipped]
permitted = json.loads((root / 'scripts/ci/allowed-evidence-skips.json').read_text())
unexpected = [item for item in skips if item['reason'] not in permitted]
Path(sys.argv[1]).write_text(json.dumps(skips, indent=2) + '\n')
if unexpected or not result.wasSuccessful():
    raise SystemExit('Unexpected missing test prerequisite or failed evidence suite: ' + str(unexpected))
