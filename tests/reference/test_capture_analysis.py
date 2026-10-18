#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reject unsupported application authority and missing new accepted originals.

Uses a private, already validated phase-one capture. Originals remain untouched.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

if sys.flags.optimize:
    raise RuntimeError('Validation requires assertions; run without -O')

capture, engine = map(lambda p: Path(p).resolve(), sys.argv[1:])
analyzer = Path(__file__).with_name('analyze_microchrony_capture.py').resolve()


def rejected(root, reason):
    process = subprocess.run([sys.executable, str(analyzer), str(root), str(engine),
                              str(root/'analysis.json')], text=True,
                             capture_output=True, timeout=30)
    assert process.returncode and reason in process.stderr, process.stderr[-1500:]


def link_inputs(root, omitted=()):
    for path in capture.iterdir():
        if path.is_file() and path.name not in omitted:
            (root/path.name).symlink_to(path)


with tempfile.TemporaryDirectory(prefix='microchrony-authority-') as temporary:
    root = Path(temporary)
    link_inputs(root)
    path = next(p for p in sorted(root.glob('A-binding-*.json'))
                if json.loads(p.read_text())['bound'])
    value = json.loads(path.read_text())
    value['before']['body']['active_source'] = 'usb'
    path.unlink()  # Replace only the fixture link, never an original.
    path.write_text(json.dumps(value))
    rejected(root, 'stored authority verdict is unsupported')

pages = {}
originals = {}
for path in capture.glob('B-history-*.json'):
    value = json.loads(path.read_text())['response']
    if not value.get('ok'):
        continue
    keys = set()
    for record in value['records']:
        key = value['slot'], value['endpoint'], value['clock_epoch'], record['id']
        originals[key] = int(record['receive_raw_ns'])
        keys.add(key)
    pages[path.name] = keys
latest = max(originals, key=originals.get)
omitted = {name for name, records in pages.items() if latest in records}
assert omitted
with tempfile.TemporaryDirectory(prefix='microchrony-visibility-') as temporary:
    root = Path(temporary)
    link_inputs(root, omitted)
    rejected(root, 'missing newly accepted original')

print('Capture analysis rejects false application authority and a lost accepted original; private originals remain unchanged.')
