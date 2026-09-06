#!/usr/bin/env python3
"""Locate a bench burst in hash-verified Harness CF32; no qualification claim."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from wsprrypi_qualification.carrier import CarrierParameters, analyze_carrier


def analyze(iq_path, metadata_path, output, tone=0):
    metadata = json.loads(metadata_path.read_text())
    expected = metadata['output']
    with iq_path.open('rb') as capture:
        digest = hashlib.file_digest(capture, 'sha256').hexdigest()
    if (metadata['primary_outcome'] != 'success' or metadata['cleanup']['outcome'] != 'verified' or
            iq_path.stat().st_size != expected['size_bytes'] or digest != expected['sha256'] or
            metadata['wire_format'] != dict(sample_format='CF32', component_type='IEEE754_binary32',
                                             interleave='real_imaginary', byte_order='little_endian',
                                             bytes_per_complex_sample=8) or
            expected['size_bytes'] != metadata['retained_sample_count'] * 8 or
            expected.get('complete') is not True):
        raise ValueError('Capture identity or cleanup mismatch')
    settings = metadata['actual_settings']
    rate, center = settings['sample_rate_hz'], settings['center_frequency_hz']
    requested = 3570100.0 + tone * 1.46484375
    iq = np.memmap(iq_path, dtype='<c8', mode='r')
    if not np.isfinite(rate) or rate <= 0 or not np.isfinite(center) or not np.isfinite(iq).all():
        raise ValueError('Non-finite samples or invalid settings')
    width = 4096
    bins = np.fft.fftfreq(width, 1 / rate) + center
    target = np.abs(bins - requested) <= 1000
    if not np.any(target) or len(iq) < 4 * width:
        raise ValueError('Insufficient capture span or length')
    window = np.hanning(width)
    scores = np.array([np.sum(np.abs(np.fft.fft(iq[i:i+width] * window)[target]) ** 2)
                       for i in range(0, len(iq) - width + 1, width)])
    background = float(np.median(scores))
    active = np.flatnonzero(scores > max(background * 10, np.finfo(float).tiny))
    result = dict(capture_sha256=digest, capture_metadata=str(metadata_path),
                  sample_rate_hz=rate, center_hz=center, requested_hz=requested,
                  detector_window_samples=width, detector_contrast_db=10,
                  peak_contrast_db=float(10 * np.log10(max(float(scores.max()), 1e-300) /
                                                       max(background, 1e-300))),
                  detected=bool(len(active)), qualification=False,
                  limitations=['Burst selection is diagnostic and can include unrelated signals.',
                               'Frequency and power are uncalibrated.',
                               'Capture-relative edges do not establish absolute GPIO timing.'])
    output.mkdir(parents=True, exist_ok=False)
    if len(active):
        groups = np.split(active, np.flatnonzero(np.diff(active) > 1) + 1)
        result['intervals_s'] = [[int(g[0]) * width / rate, (int(g[-1]) + 1) * width / rate]
                                 for g in groups]
        selected = max(groups, key=lambda g: float(scores[g].sum()))
        start, stop = int(selected[0]) * width, (int(selected[-1]) + 1) * width
        result['selected_samples'] = [start, stop]
        # The crop includes whole detector windows; no edge trimming hides failures.
        on = output / 'selected-on.cf32'
        off = output / 'selected-off.cf32'
        np.asarray(iq[start:stop]).tofile(on)
        quiet_end = min(start, int(rate))
        if quiet_end < width:
            raise ValueError('No independent leading quiet interval')
        np.asarray(iq[:quiet_end]).tofile(off)
        result['off_samples'] = [0, quiet_end]
        result['carrier'] = analyze_carrier(
            off, on, CarrierParameters(int(rate), center, requested, fft_size=width),
            output / 'harness-carrier.json')
    (output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'carrier'}, indent=2))
    if 'carrier' in result:
        print(json.dumps(result['carrier']['metrics'], indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('iq', type=Path)
    parser.add_argument('metadata', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--tone', type=int, choices=range(4), default=0)
    args = parser.parse_args()
    analyze(args.iq, args.metadata, args.output, args.tone)
