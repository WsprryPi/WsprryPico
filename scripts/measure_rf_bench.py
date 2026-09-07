#!/usr/bin/env python3
"""Offline relative frequency/frame measurements from verified bench IQ."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from analyze_rf_bench import load_capture

BASE = 3570100.0
SPACING = 375 / 256
SYMBOL = 8192 / 12000


def baseband(iq, rate, center, carrier=BASE):
    """Hann-weighted integrate/decimate; preserve global oscillator phase."""
    factor = max(1, int(rate / 1000))
    weights = np.hanning(factor) if factor > 2 else np.ones(factor)
    weights /= weights.sum()
    count = len(iq) // factor
    result = np.empty(count, dtype=np.complex128)
    for block in range(0, count, 4096):
        first, last = block * factor, min(count, block + 4096) * factor
        indices = np.arange(first, last)
        mixed = iq[first:last] * np.exp(-2j * np.pi * (carrier - center) * indices / rate)
        result[block:last // factor] = mixed.reshape(-1, factor) @ weights
    return result, rate / factor


def phase_fit(samples, rate, carrier=BASE):
    if len(samples) < 8 or not np.isfinite(samples).all() or np.median(np.abs(samples)) <= np.finfo(float).tiny:
        raise ValueError('Insufficient finite nonzero samples for phase fit')
    time = np.arange(len(samples)) / rate
    time -= time.mean()
    phase = np.unwrap(np.angle(samples))
    slope, intercept = np.polyfit(time, phase, 1)
    residual = phase - (slope * time + intercept)
    return dict(indicated_hz=float(carrier + slope / (2 * np.pi)),
                phase_residual_rms_rad=float(np.sqrt(np.mean(residual ** 2))),
                amplitude_min_ratio=float(np.min(np.abs(samples)) / np.median(np.abs(samples))))


def local_contrast(iq, rate, center, frequency):
    n = min(len(iq), 262144)
    power = np.abs(np.fft.fft(iq[:n] * np.hanning(n))) ** 2
    bins = center + np.fft.fftfreq(n, 1 / rate)
    distance = np.abs(bins - frequency)
    signal = power[distance < 100]
    background = power[(distance > 500) & (distance < 1500)]
    if not len(signal) or not len(background):
        raise ValueError('Insufficient reference spectral span')
    return float(10 * np.log10(max(float(signal.max()), 1e-300) /
                              max(float(np.median(background)), 1e-300)))


def measure(iq, rate, center, *, frame=False, tone=0, duration_s=10, reference_hz=None, base_hz=BASE, symbols=None):
    if symbols is not None:
        if not frame or len(symbols) != 162 or any(type(x) is not int or x not in range(4) for x in symbols):
            raise ValueError('Expected 162 WSPR tone indexes with frame=True')
    tones = list(symbols) if symbols is not None else [i % 4 for i in range(162)]
    if not np.isfinite(base_hz):
        raise ValueError('Expected carrier must be finite')
    if rate < 10000 or abs(base_hz - center) > rate / 2 - 2000:
        raise ValueError('Requested signal is outside usable capture span')
    bb, brate = baseband(iq, rate, center, base_hz)
    if len(bb) < brate:
        raise ValueError('Capture needs leading and trailing baseline')
    ref = None
    if reference_hz is not None:
        if (not np.isfinite(reference_hz) or abs(reference_hz - base_hz) < 2000 or
                abs(reference_hz - center) > rate / 2 - 2000):
            raise ValueError('Reference is outside usable capture span')
        ref, _ = baseband(iq, rate, center, reference_hz)
    power = np.abs(bb) ** 2
    noise = float(np.median(power[:int(brate / 2)]))
    threshold = max(noise * 100, float(np.max(power)) * .05, np.finfo(float).tiny)
    active = np.flatnonzero(power > threshold)
    groups = np.split(active, np.flatnonzero(np.diff(active) > 1) + 1) if len(active) else []
    groups = [g for g in groups if len(g) >= 10]
    intervals = [[float(g[0] / brate), float((g[-1] + 1) / brate)] for g in groups]
    expected = 162 * SYMBOL if frame else duration_s
    report = dict(version=1, qualification=False, calibration_applied=False,
                  workload=('encoded-162' if symbols is not None else 'cycle4-162') if frame else 'tone', intervals_s=intervals,
                  expected_duration_s=expected, expected_base_hz=base_hz, issues=[], measurements=[],
                  method='Hann integrate/decimate then per-interval linear unwrapped phase fit',
                  limitations=['Receiver clock and frequency axis are uncalibrated.',
                               'Decimator is diagnostic; adjacent interference can bias phase.',
                               'No absolute GPIO timing or out-of-band harmonic claim.'])
    if len(groups) != 1:
        report['issues'].append('Expected one uninterrupted burst')
    if not groups:
        report['relative_checks_passed'] = False
        return report
    group = max(groups, key=len)
    start, end = group[0] / brate, (group[-1] + 1) / brate
    report['observed_duration_s'] = float(end - start)
    if start < .5 or len(bb) / brate - end < .5:
        report['issues'].append('Missing independent leading/trailing quiet interval')
    if abs(end - start - expected) > .02:
        report['issues'].append('Burst duration differs by more than 20 ms')
    segments = 162 if frame else max(1, int(np.ceil((expected - .16) / .5)))
    for index in range(segments):
        left = start + index * SYMBOL + .08 if frame else start + .08 + index * (expected - .16) / segments
        right = start + (index + 1) * SYMBOL - .08 if frame else start + .08 + (index + 1) * (expected - .16) / segments
        if right > end or right <= left:
            report['issues'].append(f'Missing segment {index}')
            break
        data = bb[int(round(left * brate)):int(round(right * brate))]
        result = phase_fit(data, brate, base_hz)
        if ref is not None:
            reference = phase_fit(ref[int(round(left * brate)):int(round(right * brate))],
                                  brate, reference_hz)
            reference['local_contrast_db'] = local_contrast(
                iq[round(left * rate):round(right * rate)], rate, center, reference_hz)
            result['reference'] = reference
            result['reference_compared_hz'] = result['indicated_hz'] - (reference['indicated_hz'] - reference_hz)
            if (reference['local_contrast_db'] < 20 or reference['phase_residual_rms_rad'] > .15 or reference['amplitude_min_ratio'] < .5 or
                    abs(reference['indicated_hz'] - reference_hz) > 100):
                report['issues'].append(f'Invalid reference in segment {index}')
        result.update(index=index, tone=tones[index] if frame else tone, interval_s=[left, right])
        report['measurements'].append(result)
        if (result['phase_residual_rms_rad'] > .15 or result['amplitude_min_ratio'] < .5 or
                abs(result['indicated_hz'] - base_hz) > 100):
            report['issues'].append(f'Incoherent, interrupted or out-of-range segment {index}')
    if frame and len(report['measurements']) == 162:
        field = 'reference_compared_hz' if ref is not None else 'indicated_hz'
        values = np.array([m[field] for m in report['measurements']])
        # Fit offset + tone spacing + linear drift; retain every segment residual.
        design = np.column_stack([np.ones(162), tones, np.arange(162) * SYMBOL])
        offset, spacing, drift = np.linalg.lstsq(design, values, rcond=None)[0]
        residuals = values - design @ np.array([offset, spacing, drift])
        report.update(frequency_basis=field, fitted_base_hz=float(offset), tone_spacing_hz=float(spacing),
                      linear_drift_hz_per_s=float(drift),
                      max_symbol_residual_hz=float(np.max(np.abs(residuals))))
        # Symmetric 20 ms phase difference locates each physical tone transition.
        lag = max(1, round(brate * .01))
        phase = np.unwrap(np.angle(bb))
        instantaneous = base_hz + (phase[2*lag:] - phase[:-2*lag]) * brate / (4*np.pi*lag)
        boundaries = []
        for index in range(1, 162):
            if tones[index-1] == tones[index]:
                continue  # No physical transition exists between equal symbols.
            expected_time = start + index * SYMBOL
            before = report['measurements'][index-1]['indicated_hz']
            after = report['measurements'][index]['indicated_hz']
            lo = max(0, round((expected_time - .05) * brate) - lag)
            hi = min(len(instantaneous), round((expected_time + .05) * brate) - lag)
            times = (np.arange(lo, hi) + lag) / brate
            candidates = expected_time + np.linspace(-.04, .04, 801)
            # Fit the ramp induced by the symmetric phase-difference window;
            # a single noisy midpoint crossing must not choose the boundary.
            ramps = np.clip((times[None, :] - candidates[:, None] + lag/brate) /
                            (2*lag/brate), 0, 1)
            predicted = before + (after - before) * ramps
            mse = np.mean((predicted - instantaneous[None, lo:hi]) ** 2, axis=1)
            best = int(np.argmin(mse))
            observed = candidates[best]
            rms = float(np.sqrt(mse[best]))
            if best in (0, 800):
                report['issues'].append(f'Transition boundary unresolved at symbol {index}')
            if rms > .15:
                report['issues'].append(f'Transition fit residual exceeds 0.15 Hz at symbol {index}')
            boundaries.append(dict(index=index, observed_s=float(observed),
                                   error_s=float(observed - expected_time), fit_rms_hz=rms))
        report['transitions'] = boundaries
        if boundaries:
            report['max_transition_error_s'] = max(abs(b['error_s']) for b in boundaries)
            if report['max_transition_error_s'] > .01:
                report['issues'].append('Transition timing differs by more than 10 ms')
        if abs(spacing - SPACING) > .05 or np.max(np.abs(residuals)) > .1:
            report['issues'].append('Tone spacing/order residual exceeds diagnostic limits')
    if ref is not None:
        report['reference_hz'] = reference_hz
        report['reference_comparison'] = 'Subtract simultaneous indicated reference error; sample-rate scale not independently calibrated'
    if not frame and report['measurements']:
        left = report['measurements'][0]['interval_s'][0]
        right = report['measurements'][-1]['interval_s'][1]
        frequencies = [m.get('reference_compared_hz', m['indicated_hz']) for m in report['measurements']]
        report['tone_frequency_summary'] = dict(mean_hz=float(np.mean(frequencies)),
            peak_to_peak_hz=float(np.ptp(frequencies)),
            nominal_offset_hz=float(np.mean(frequencies) - (base_hz + tone * SPACING)),
            basis='reference_compared_hz' if ref is not None else 'indicated_hz')
        data = np.asarray(iq[round(left * rate):round(right * rate)])
        n = min(len(data), 2097152)
        spectrum = np.abs(np.fft.fft(data[:n] * np.hanning(n))) ** 2
        bins = center + np.fft.fftfreq(n, 1 / rate)
        carrier = report['measurements'][0]['indicated_hz']
        main = np.abs(bins - carrier) < 5
        eligible = (np.abs(bins - center) < min(90000, rate * .4)) & ~main
        if ref is not None:
            eligible &= np.abs(bins - report['measurements'][0]['reference']['indicated_hz']) > 5
        indexes = np.flatnonzero(eligible)
        strongest = indexes[np.argmax(spectrum[indexes])]
        report['in_band_spectrum'] = dict(fft_samples=n, bin_width_hz=rate/n,
            strongest_other_bin_hz=float(bins[strongest]),
            strongest_other_bin_dbc=float(10*np.log10(max(spectrum[strongest], 1e-300)/max(float(spectrum[main].max()), 1e-300))),
            limitation='Windowed peak-bin ratio in retained receiver band, excluding +/-5 Hz around source/reference; not harmonic or power qualification')
    report['relative_checks_passed'] = not report['issues']
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('iq', type=Path)
    p.add_argument('metadata', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--base-hz', type=float, default=BASE, help='Expected carrier for an intentional frequency-translation experiment')
    p.add_argument('--reference-hz', type=float, help='Known simultaneously present reference frequency')
    p.add_argument('--symbols', help='162 encoded tone digits; implies frame')
    p.add_argument('--frame', action='store_true')
    p.add_argument('--tone', type=int, choices=range(4), default=0)
    p.add_argument('--duration-s', type=float, default=10)
    args = p.parse_args()
    if not np.isfinite(args.duration_s) or args.duration_s <= .2:
        p.error('Tone duration must be finite and greater than 0.2 seconds')
    iq, meta, digest = load_capture(args.iq, args.metadata)
    settings = meta['actual_settings']
    result = measure(iq, settings['sample_rate_hz'], settings['center_frequency_hz'],
                     frame=args.frame or args.symbols is not None, symbols=None if args.symbols is None else [int(c) for c in args.symbols], tone=args.tone, duration_s=args.duration_s, reference_hz=args.reference_hz, base_hz=args.base_hz)
    if meta.get('overflow_count') != 0 or meta.get('clipping', {}).get('sample_count') != 0:
        result['issues'].append('Receiver overflow/clipping evidence is absent or nonzero')
        result['relative_checks_passed'] = False
    result.update(capture_sha256=digest, metadata_sha256=hashlib.sha256(args.metadata.read_bytes()).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        output.write(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('measurements', 'transitions')}, indent=2))
    return 0 if result['relative_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
