#!/usr/bin/env python3
"""Describe frame drift without changing the original diagnostic result."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def fit_drift(time, tones, frequency):
    time, tones, frequency = [np.asarray(x, dtype=float) for x in (time, tones, frequency)]
    if len(time) < 24 or len(tones) != len(time) or len(frequency) != len(time):
        raise ValueError('At least 24 aligned measurements are required')
    if not all(np.isfinite(x).all() for x in (time, tones, frequency)) or np.any(np.diff(time) <= 0):
        raise ValueError('Invalid measurement coordinates')
    if len(np.unique(tones)) < 2:
        raise ValueError('Multiple tones are required to estimate spacing')
    time = time - time[0]
    base = float(frequency.mean())
    values = frequency - base
    train = np.arange(len(time)) % 3 == 0
    best = None
    for tau in np.geomspace(1, 300, 1000):
        design = np.column_stack([np.ones(len(time)), tones, np.exp(-time/tau)])
        if np.linalg.matrix_rank(design[train]) < 3:
            raise ValueError('Training measurements cannot identify model coefficients')
        coefficients = np.linalg.lstsq(design[train], values[train], rcond=None)[0]
        residual = values - design @ coefficients
        score = float(np.mean(residual[train]**2))
        if best is None or score < best[0]:
            best = score, tau, coefficients, residual
    _, tau, coefficients, residual = best
    return dict(model='offset + tone*spacing + amplitude*exp(-time/tau)',
                fitted_asymptotic_base_hz=float(base+coefficients[0]),
                fitted_spacing_hz=float(coefficients[1]),
                transient_amplitude_hz=float(coefficients[2]), fitted_tau_s=float(tau),
                held_out_max_residual_hz=float(np.max(np.abs(residual[~train]))),
                held_out_rms_hz=float(np.sqrt(np.mean(residual[~train]**2))),
                observed_duration_s=float(time[-1]),
                limitation='Descriptive fit, not proof of temperature causation or a runtime compensation law',
                qualification=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('measurement', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    document = json.loads(args.measurement.read_text())
    rows = document['measurements']
    field = 'reference_compared_hz' if 'reference_hz' in document else 'indicated_hz'
    result = fit_drift([sum(r['interval_s'])/2 for r in rows], [r['tone'] for r in rows],
                       [r[field] for r in rows])
    result['measurement_sha256'] = hashlib.sha256(args.measurement.read_bytes()).hexdigest()
    result['frequency_basis'] = field
    with args.output.open('x') as output:
        output.write(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2))
