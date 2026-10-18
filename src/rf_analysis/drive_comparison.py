"""Relative GPIO-drive RF comparisons; no calibrated power or emissions claim."""
import numpy as np
from measure_rf_bench import measure

def require(condition, message):
    if not condition:
        raise ValueError(message)

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
