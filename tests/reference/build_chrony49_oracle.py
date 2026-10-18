#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Link a private reference harness to an already built external Chrony 4.9 tree.

Arguments: configured-and-built-chrony49-directory output-executable
No source download, package install, clock adjustment or firmware linkage occurs.
The resulting private oracle includes GPL code and is not an MIT firmware artifact.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

source = Path(sys.argv[1]).resolve(strict=True)
output = Path(sys.argv[2]).resolve()
kind = sys.argv[3] if len(sys.argv) == 4 else 'sourcestats'
if kind not in ('sourcestats', 'control', 'selection', 'loop', 'regression', 'combination'):
    raise SystemExit('Unknown reference harness')
harness = Path(__file__).with_name('chrony49_' + kind + '.c').resolve()
version = (source / 'version.txt').read_text()
if version.strip() != '4.9' or not (source / 'COPYING').is_file():
    raise SystemExit('An existing configured and built Chrony 4.9 tree is required')
objects = sorted(p for p in source.glob('*.o')
                 if p.name not in ('main.o', 'client.o', 'getdate.o', 'pktlength.o'))
if kind == 'combination':
    objects = [p for p in objects if p.name != 'reference.o']
if not objects or not (source / 'sourcestats.o').is_file():
    raise SystemExit('Build the external reference first; no dependency is installed here')
subprocess.run([os.environ.get('CC', 'cc'), '-O2', '-I' + str(source), str(harness),
                *(str(p) for p in objects), '-lresolv', '-lm', '-o', str(output)], check=True)
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
Path(str(output) + '.inputs.json').write_text(json.dumps({
    'scope': 'Private external GPL reference only; never linked to firmware',
    'harness_sha256': sha(harness), 'output_sha256': sha(output),
    'version_sha256': sha(source / 'version.txt'),
    'upstream_license_sha256': sha(source / 'COPYING'),
    'objects': {p.name: sha(p) for p in objects}}, indent=2, sort_keys=True) + '\n')
