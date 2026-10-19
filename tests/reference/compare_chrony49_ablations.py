#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build private original-code ablations and score known-truth physical events.

Only owned MIT implementation is transformed. No reference source is read or
incorporated. The weighting-only variant retains the old asymmetry/horizon rules;
the asymmetry-only variant retains the old root-distance weights. Covariance and
horizon changes belong to the asymmetry factor. Generated sources/binaries stay
in the specified ignored output directory; no firmware or device is involved.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from compare_chrony49_loop import events, internet_queue_cases, run, summarize


def replace(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new)


def main():
    if sys.flags.optimize:
        raise RuntimeError('Run without -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', help='Owned Git revision before weighting/asymmetry changes')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    args.output.mkdir(parents=True, exist_ok=True)
    current = (root/'src/microchrony/microchrony.cpp').read_text()
    baseline = subprocess.check_output(['git','show',args.baseline+':src/microchrony/microchrony.cpp'],
                                       cwd=root, text=True)
    driver = root/'tests/reference/microchrony_loop.cpp'
    header = root/'src/microchrony/microchrony.hpp'
    # Replace only the weighting factor in each owned source. The complete
    # generated variants and hashes remain inspectable alongside the results.
    def weight(source):
        start = source.index('    auto weight = ')
        return source[start:source.index('    };',start)+6]
    original_weight, path_weight = weight(baseline), weight(current)
    weighting = replace(baseline, original_weight, path_weight)
    helpers = current[current.index('double peer_distance('):current.index('// Centered weighted')]
    weighting = replace(weighting, '// Centered weighted', helpers+'// Centered weighted')
    weighting = replace(weighting,
        '             std::span<const Measurement> runs_samples,',
        '             NoiseScale noise, std::span<const Measurement> runs_samples,')
    weighting = replace(weighting, '    while (source.count - source.fit_start >= 3) {',
        '    const auto noise = noise_scale(std::span{source.samples.data()+source.fit_start, '
        'source.count-source.fit_start}, config_.precision);\n'
        '    while (source.count - source.fit_start >= 3) {')
    weighting = replace(weighting, 'regress(points, config_.precision, 0, runs_points, extra,',
                        'regress(points, config_.precision, 0, noise, runs_points, extra,')
    asymmetry = replace(current, path_weight, original_weight)
    variants = {'baseline':baseline, 'weighting_only':weighting,
                'asymmetry_only':asymmetry, 'combined':current}
    report = {'schema':'microchrony-clock-ablations/1', 'baseline_revision':args.baseline,
              'driver_sha256':hashlib.sha256(driver.read_bytes()).hexdigest(),
              'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(), 'variants':{}}
    for name,source in variants.items():
        path = args.output/(name+'.cpp'); path.write_text(source)
        executable = args.output/name
        command = [os.environ.get('CXX','c++'),'-std=c++20','-O2','-I'+str(header.parent),
                   str(path),str(driver),'-o',str(executable)]
        subprocess.run(command, check=True)
        cases = {}
        for case_name,case in internet_queue_cases().items():
            payload = events(case,1)
            rows = run(str(executable.resolve()),0,payload)
            cases[case_name] = dict(input_sha256=hashlib.sha256(payload.encode()).hexdigest(),
                                   summary=summarize(rows,case), rows=rows)
        report['variants'][name] = dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),
            binary_sha256=hashlib.sha256(executable.read_bytes()).hexdigest(), cases=cases,
            compile_command=command)
        print(name,{k:round(v['summary']['last_hour_utc_rms_ms'],6) for k,v in cases.items()},flush=True)
    (args.output/'results.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
