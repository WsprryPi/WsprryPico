#!/usr/bin/env python3
"""Reject false conducted comparisons and verify measured amplitude semantics."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / part) for part in ('src', 'scripts')]
from rf_analysis.drive_comparison import comparison, reduce_tone


class RelativeRfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rate = 250000
        cls.time = np.arange(12 * cls.rate) / cls.rate
        cls.gate = (cls.time >= 2) & (cls.time < 7)
        rng = np.random.default_rng(1515)
        cls.noise = (rng.normal(size=len(cls.time)) + 1j * rng.normal(size=len(cls.time))) * 1e-5

    def tone(self, amplitude=.05, spur=False):
        data = self.noise + self.gate * amplitude * np.exp(2j * np.pi * 25000 * self.time)
        if spur:
            data = data + self.gate * .002 * np.exp(2j * np.pi * 26000 * self.time)
        return reduce_tone(data.astype('<c8'), self.rate, 975000, 1000000, 5)

    def test_doubling_voltage_is_six_db_without_calibrated_watts(self):
        reference, _ = self.tone()
        doubled, _ = self.tone(.1)
        self.assertAlmostEqual(doubled['power_db_relative'] - reference['power_db_relative'], 6.0206, places=2)

    def test_added_resolved_spur_fails_spectral_screen(self):
        reference, old = self.tone()
        changed, new = self.tone(spur=True)
        result = comparison(reference, changed, old, new, 0)
        self.assertFalse(result['spectrum_screen_passed'])
        self.assertGreater(result['new_resolved_feature_count'], 0)

    def test_noise_and_continuous_unbracketed_signal_rejected(self):
        with self.assertRaises(ValueError):
            reduce_tone(self.noise.astype('<c8'), self.rate, 975000, 1000000, 5)
        constant = (.05 * np.exp(2j * np.pi * 25000 * self.time)).astype('<c8')
        with self.assertRaises(ValueError):
            reduce_tone(constant, self.rate, 975000, 1000000, 5)

    def test_same_capture_passes_but_three_db_gain_change_fails(self):
        reference, old = self.tone()
        same = comparison(reference, reference, old, old, 0)
        self.assertTrue(same['carrier_screen_passed'] and same['spectrum_screen_passed'])
        changed, new = self.tone(.05 * np.sqrt(2))
        self.assertFalse(comparison(reference, changed, old, new, .05)['carrier_screen_passed'])

    def test_single_quiet_bin_null_is_not_a_new_resolved_feature(self):
        quiet = np.ones(101)
        quiet[50] = .001
        previous = dict(on=np.ones(101) * 2, quiet=np.ones(101), eligible=np.ones(101, dtype=bool))
        current = dict(added=np.ones(101) * 5, quiet=quiet, eligible=np.ones(101, dtype=bool))
        value = dict(power_db_relative=0)
        self.assertTrue(comparison(value, value, previous, current, 0)['spectrum_screen_passed'])


if __name__ == '__main__':
    unittest.main()
