#!/usr/bin/env python3
"""Retain derived GPSDO sampling-axis quantities beside immutable original analysis."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.calibration import quantities
from led_closeout.runner import sha256
from phase14.live import save


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('analysis',type=Path);p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('immutable derived comparison already exists')
    original=json.loads(a.analysis.read_text());reference=json.loads(a.reference.read_text())
    report=quantities(original.get('measurement',original),reference)
    report.update(original_analysis_sha256=sha256(a.analysis),reference_comparison_sha256=sha256(a.reference),
        source_revision=original['source_revision'],firmware_sha256=original['firmware_sha256'],job_id=original['job_id'],
        script_sha256=sha256(__file__))
    save(a.output,report);print(json.dumps(dict(output=str(a.output),original_screen_unchanged=True)))
