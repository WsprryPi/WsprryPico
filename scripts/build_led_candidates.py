#!/usr/bin/env python3
"""Pinned retained-dependency LED candidate matrix; no download, flash or RF."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from led_closeout.candidates import build
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--prepare', action='store_true', help='Check worktree candidates; final live manifest still requires a clean commit')
p.add_argument('--build-dir', type=Path, default=ROOT/'build/phase13-1-pico')
p.add_argument('--output', type=Path, default=ROOT/'build/phase13-led-candidates')
a = p.parse_args()
manifest = build(ROOT, a.build_dir, a.output, prepare=a.prepare)
print('Checked', len(manifest['images']), 'images; clean =', manifest['clean'])
