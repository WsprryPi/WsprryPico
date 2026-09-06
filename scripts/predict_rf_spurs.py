#!/usr/bin/env python3
"""Offline NCO square-wave model; predicts aliases, not analog output compliance."""
import argparse
import json
from pathlib import Path
import numpy as np

RATE = 150000000
INCREMENT = 102223085


def corrected_increment(ppb):
    if not -100000 <= ppb <= 100000:
        raise ValueError('Correction outside supported range')
    divisor = 1000000000 + ppb
    return (INCREMENT * 1000000000 + divisor // 2) // divisor


def alias(increment, harmonic, rate=RATE):
    phase = (increment * harmonic) % (1 << 32)
    return min(phase, (1 << 32) - phase) * rate / (1 << 32)


def simulate(ppb, duration=.1, center=3550000):
    increment = corrected_increment(ppb)
    factor = 500
    count = round(duration * RATE / factor)
    iq = np.empty(count, dtype=complex)
    weights = np.hanning(factor)
    weights /= weights.sum()
    for block in range(0, count, 2000):
        first, last = block*factor, min(count, block+2000)*factor
        indexes = np.arange(first, last, dtype=np.uint64)
        # Independent per-sample oracle, as used to test the C++ packed generator.
        bits = ((indexes * np.uint64(increment)) & np.uint64(0xffffffff)) >> np.uint64(31)
        wave = 2*bits.astype(float)-1
        mixed = wave * np.exp(-2j*np.pi*center*indexes.astype(float)/RATE)
        iq[block:last//factor] = mixed.reshape(-1, factor) @ weights
    rate = RATE/factor
    power = np.abs(np.fft.fft(iq*np.hanning(count)))**2
    bins = center + np.fft.fftfreq(count, 1/rate)
    main = alias(increment, 1)
    fundamental = float(power[np.abs(bins-main)<30].max())
    result = dict(correction_ppb=ppb, increment=increment, nominal_sample_rate_hz=RATE,
                  duration_s=duration, bin_width_hz=rate/count, qualification=False,
                  model='MSB of 32-bit phase accumulator, plus Hann integrate/decimate', features=[])
    for harmonic in (1, 41, 43):
        frequency = alias(increment, harmonic)
        candidates = np.flatnonzero(np.abs(bins-frequency)<30)
        best = candidates[np.argmax(power[candidates])]
        result['features'].append(dict(harmonic=harmonic, predicted_hz=frequency,
            simulated_peak_hz=float(bins[best]), simulated_peak_dbc=float(10*np.log10(power[best]/fundamental))))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    p.add_argument('--correction-ppb', type=int, default=0)
    args = p.parse_args()
    result = simulate(args.correction_ppb)
    with args.output.open('x') as output:
        output.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
