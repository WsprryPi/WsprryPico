#!/usr/bin/env python3
"""Offline adversarial checks for relative tone/frame interpretation."""
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from measure_rf_bench import BASE, SPACING, SYMBOL, measure, phase_fit

RATE = 10000
CENTER = BASE - 2000

def capture(frame=False, gap=False, wrong=False, duration=2, delayed_boundary=False):
    length = 162 * SYMBOL if frame else duration
    n = round(length * RATE)
    rng = np.random.default_rng(9)
    iq = (rng.normal(size=n + 2 * RATE) + 1j * rng.normal(size=n + 2 * RATE)) * 1e-5
    tones = (np.floor(np.arange(n) / RATE / SYMBOL).astype(int) % 4) if frame else np.zeros(n)
    if delayed_boundary:
        tones[round(SYMBOL*RATE):round((SYMBOL+.02)*RATE)] = 0
    if wrong:
        tones = 3 - tones
    frequency = BASE - CENTER + 7.25 + tones * SPACING
    iq[RATE:RATE+n] += .1 * np.exp(2j * np.pi * np.cumsum(frequency) / RATE)
    if gap:
        iq[RATE + n//2:RATE + n//2 + RATE//20] = 1e-5
    return iq

class Tests(unittest.TestCase):
    def test_tone_frequency(self):
        result = measure(capture(), RATE, CENTER, duration_s=2)
        self.assertTrue(result['relative_checks_passed'], result['issues'])
        self.assertAlmostEqual(result['measurements'][0]['indicated_hz'], BASE + 7.25, places=3)
        self.assertFalse(result['qualification'])
    def test_frame(self):
        result = measure(capture(frame=True), RATE, CENTER, frame=True)
        self.assertTrue(result['relative_checks_passed'], result['issues'])
        self.assertEqual(len(result['measurements']), 162)
        self.assertAlmostEqual(result['tone_spacing_hz'], SPACING, places=3)
    def test_delayed_symbol_boundary(self):
        result = measure(capture(frame=True, delayed_boundary=True), RATE, CENTER, frame=True)
        self.assertFalse(result['relative_checks_passed'])
        self.assertGreater(result['max_transition_error_s'], .015)
    def test_gap(self):
        result = measure(capture(gap=True), RATE, CENTER, duration_s=2)
        self.assertFalse(result['relative_checks_passed'])
    def test_wrong_duration(self):
        self.assertFalse(measure(capture(), RATE, CENTER, duration_s=3)['relative_checks_passed'])
    def test_reversed_frame(self):
        self.assertFalse(measure(capture(frame=True, wrong=True), RATE, CENTER, frame=True)['relative_checks_passed'])
    def test_simultaneous_reference(self):
        iq = capture()
        reference = BASE - 4000
        # Both sources have the same +7.25 Hz receiver error.
        iq += .07 * np.exp(2j * np.pi * (reference - CENTER + 7.25) * np.arange(len(iq)) / RATE)
        result = measure(iq, RATE, CENTER, duration_s=2, reference_hz=reference)
        self.assertTrue(result['relative_checks_passed'], result['issues'])
        self.assertAlmostEqual(result['tone_frequency_summary']['mean_hz'], BASE, places=3)
    def test_absent_reference_rejected(self):
        with self.assertRaises(ValueError):
            phase_fit(np.zeros(100, dtype=complex), 1000)
        result = measure(capture(), RATE, CENTER, duration_s=2, reference_hz=BASE-4000)
        self.assertFalse(result['relative_checks_passed'])
    def test_self_reference_rejected(self):
        with self.assertRaises(ValueError):
            measure(capture(), RATE, CENTER, duration_s=2, reference_hz=BASE)
    def test_noise(self):
        rng = np.random.default_rng(7)
        iq = rng.normal(size=40000) + 1j*rng.normal(size=40000)
        self.assertFalse(measure(iq, RATE, CENTER, duration_s=2)['relative_checks_passed'])

if __name__ == '__main__':
    unittest.main()
