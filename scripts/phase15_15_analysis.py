#!/usr/bin/env python3
"""Offline P15.15 relative RF comparison; no device access or calibrated watts."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from measure_rf_bench import measure
from phase14.plan import validate_capture
from led_closeout.runner import require, sha256
from phase14.live import save


def db(value):
    return 10 * np.log10(np.maximum(value, 1e-300))


def spectrum(samples, n=131072, blocks=3):
    count = min(blocks, len(samples) // n)
    require(count >= 1 and np.isfinite(samples).all(), 'finite complete spectral windows required')
    window = np.hanning(n)
    return np.mean([np.abs(np.fft.fftshift(np.fft.fft(samples[i*n:(i+1)*n] * window)))**2 /
                    (np.sum(window)**2) for i in range(count)], axis=0)


def reduce_tone(samples, rate, center, expected, seconds):
    observation = measure(samples, rate, center, base_hz=expected, duration_s=seconds)
    require(observation['relative_checks_passed'], 'finite continuous Tone: ' + str(observation['issues']))
    start, end = observation['intervals_s'][0]
    require(start >= .8 and len(samples) / rate - end >= .8, 'quiet bracketing required')
    on = samples[round((start + .5) * rate):round((end - .5) * rate)]
    quiet = np.concatenate([samples[:round((start - .2) * rate)],
                            samples[round((end + .2) * rate):]])
    n = 131072
    enabled, disabled = spectrum(on, n), spectrum(quiet, n)
    bins = center + np.fft.fftshift(np.fft.fftfreq(n, 1 / rate))
    eligible = np.abs(bins - expected) < 500
    peak_index = np.flatnonzero(eligible)[np.argmax(enabled[eligible] - disabled[eligible])]
    peak = float(bins[peak_index])
    main = np.abs(bins - peak) <= 25
    power = float(np.sum(enabled[main] - disabled[main]))
    noise = float(np.sum(disabled[main]))
    require(power > 0 and float(db(power / max(noise, 1e-300))) >= 10, 'RF contrast below 10 dB')
    added = np.maximum(enabled - disabled, 0)
    span = (np.abs(bins - center) <= 90000) & (np.abs(bins - peak) >= 100) & (np.abs(bins - center) >= 100)
    indexes = np.flatnonzero(span)
    strongest = indexes[np.argmax(added[indexes])]
    close = (np.abs(bins - peak) >= 8) & (np.abs(bins - peak) <= 100)
    value = dict(power_db_relative=float(db(power)), contrast_db=float(db(power / max(noise, 1e-300))),
                 peak_hz=peak, observation=observation, fft_samples=n, bin_width_hz=rate/n,
                 close_8_to_100_hz_dbc=float(db(np.sum(added[close]) / power)),
                 strongest_added_hz=float(bins[strongest]),
                 strongest_added_dbc=float(db(added[strongest] / power)),
                 subtraction='Mean linear on power minus mean linear quiet power, identical Hann/FFT bins')
    return value, dict(bins=bins, on=enabled, quiet=disabled, added=added, eligible=span)


def comparison(reference, candidate, reference_psd, candidate_psd, repeat_spread):
    delta = candidate['power_db_relative'] - reference['power_db_relative']
    # Compare resolution elements in absolute receiver frequency; exclude the
    # carrier and tuner DC in both records. Resolved features need local quiet
    # contrast in the candidate AND exceed the baseline signal/noise envelope.
    eligible = reference_psd['eligible'] & candidate_psd['eligible']
    old = np.maximum(reference_psd['on'], reference_psd['quiet'])
    # Resolve a baseline feature over +/-3 bins (5.72 Hz), rather than treating
    # ordinary sub-bin receiver/source drift as a new spectral line.
    old = np.max(np.lib.stride_tricks.sliding_window_view(np.pad(old, 3, mode='edge'), 7), axis=1)
    added = candidate_psd['added']
    quiet = candidate_psd['quiet']
    # A stochastic quiet-bin null is not a physical local noise floor.
    local_noise = np.median(np.lib.stride_tricks.sliding_window_view(np.pad(quiet, 15, mode='edge'), 31), axis=1)
    floor = np.maximum(quiet, local_noise)
    new = eligible & (added > floor * 10) & (added > old * 10**(.3))
    return dict(carrier_delta_db=delta, observed_repeat_spread_db=repeat_spread,
                carrier_screen_passed=abs(delta) <= 1 + repeat_spread,
                new_resolved_feature_count=int(np.count_nonzero(new)),
                spectrum_screen_passed=not bool(np.any(new)))


def analyze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    records = json.loads((root / 'records.json').read_text())
    acquisition = json.loads((root / 'result.json').read_text())
    require(acquisition['status'] == 'ACQUISITION_COMPLETE' and not acquisition['errors'], 'acquisition/restoration incomplete')
    values, psds, source_records = {}, {}, {}
    for record in records:
        if not record.get('capture_sha256'):
            continue
        label = record['label']
        directory = root / label
        physical = json.loads((directory / 'physical.json').read_text())
        require(physical == {k: v for k, v in record.items() if k != 'label'}, 'physical record substitution')
        metadata = json.loads((directory / 'capture.json').read_text())
        validate_capture(metadata, directory / 'capture.cf32', physical['receiver_settings'])
        require(sha256(directory / 'capture.cf32') == physical['capture_sha256'] and
                sha256(directory / 'capture.json') == physical['metadata_sha256'], 'capture identity changed')
        data = np.memmap(directory / 'capture.cf32', dtype='<c8', mode='r')
        value, psd = reduce_tone(data, 250000, record['frequency_hz'] - 25000,
                                 record['frequency_hz'], record['requested_duration_s'])
        value.update(board=record['board'], ma=record['ma'], frequency_hz=record['frequency_hz'],
                     image_sha256=record['image_sha256'], capture_sha256=record['capture_sha256'],
                     metadata_sha256=record['metadata_sha256'], physical_sha256=sha256(directory / 'physical.json'))
        values[label], psds[label], source_records[label] = value, psd, record
        save(output / (label + '.json'), value)
    require(len(values) == 18, 'complete frozen 18-capture matrix required')
    comparisons = {}
    for board, frequencies in [('A', (137600, 14097100)), ('B', (14097100,))]:
        for frequency in frequencies:
            baseline = 'baseline-' + board + '-' + str(frequency)
            first = 'candidate-' + board + '-4-' + str(frequency)
            last = 'bracket-' + board + '-' + str(frequency)
            spread = abs(values[last]['power_db_relative'] - values[first]['power_db_relative'])
            for label in (first, last):
                comparisons[label] = comparison(values[baseline], values[label], psds[baseline], psds[label], spread)
            for ma in (2, 4, 8, 12):
                label = 'candidate-' + board + '-' + str(ma) + '-' + str(frequency)
                values[label]['relative_to_baseline_4ma_db'] = values[label]['power_db_relative'] - values[baseline]['power_db_relative']
    result = dict(schema='phase15-15-relative-rf/1', values=values, comparisons=comparisons,
                  pad_acceptance_evaluated=False,
                  all_screens_passed=all(x['carrier_screen_passed'] and x['spectrum_screen_passed'] for x in comparisons.values()),
                  limitations=['Relative conducted amplitude, same receiver settings and path; no calibrated watts.',
                               'Two frequencies on A and one on B; no all-band/mode or out-of-span harmonic qualification.',
                               'Nominal receiver sample/frequency axis; no calibrated absolute timing/frequency.',
                               'New-feature screen excludes 100 Hz around carrier/tuner DC and receiver span beyond 90 kHz.'])
    save(output / 'summary.json', result)
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        figure, axes = plt.subplots(3, 1, figsize=(11, 11), constrained_layout=True)
        for axis, (board, frequency) in zip(axes, [('A',137600), ('A',14097100), ('B',14097100)]):
            baseline = 'baseline-' + board + '-' + str(frequency)
            for ma in (2,4,8,12):
                label = 'candidate-' + board + '-' + str(ma) + '-' + str(frequency)
                psd = psds[label]
                axis.plot(psd['bins'] - frequency, db(psd['added']) - values[baseline]['power_db_relative'],
                          linewidth=.7, label=str(ma)+' mA')
            axis.set(xlim=(-1000,1000), ylim=(-100,10), xlabel='Offset from requested RF (Hz)',
                     ylabel='dB relative to baseline carrier', title=f'Pico {board}, {frequency} Hz; conducted, nominal receiver axis')
            axis.grid(alpha=.25)
            axis.legend(ncol=4)
        figure.savefig(output / 'conducted-comparison.png', dpi=160)
        plt.close(figure)
    except ImportError:
        result['plot_unavailable'] = 'Existing matplotlib unavailable; numeric results retained.'
        save(output / 'summary.json', result)
    print(json.dumps(dict(captures=len(values), screens_passed=result['all_screens_passed'], comparisons=comparisons), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    analyze(args.root, args.output)
