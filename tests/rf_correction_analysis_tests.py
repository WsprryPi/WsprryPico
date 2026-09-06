import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from analyze_rf_drift import fit_drift
from compare_rf_clocks import compare
from predict_rf_spurs import alias, corrected_increment, simulate

class Tests(unittest.TestCase):
    def test_clock_comparison(self):
        rows = compare()['clocks']
        for row in rows:
            rate = row['sample_rate_hz']
            self.assertEqual(12000000*row['feedback'], rate*np.prod(row['postdiv']))
            self.assertEqual(row['symbol_samples']*12000, rate*8192)
        old = next(r for r in rows if r['sample_rate_hz'] == 150000000)
        new = next(r for r in rows if r['sample_rate_hz'] == 138000000)
        self.assertLess(new['nearest_strong_aliases'][0]['ideal_coefficient_dbc'],
                        old['nearest_strong_aliases'][0]['ideal_coefficient_dbc']-30)
        model = simulate(2222, sample_rate=138000000, harmonics=(1, 2125, 2127))
        for feature in model['features']:
            self.assertLess(abs(feature['predicted_hz']-feature['simulated_peak_hz']), 10)
        self.assertLess(model['features'][1]['simulated_peak_dbc'], -60)
        with self.assertRaises(ValueError):
            corrected_increment(0, 0)

    def test_spur_movement(self):
        raw, corrected = corrected_increment(0), corrected_increment(2222)
        self.assertAlmostEqual(alias(corrected,43)-alias(raw,43),
                               43*(alias(corrected,1)-alias(raw,1)), places=6)
        for ppb in (0,2222):
            result = simulate(ppb)
            for feature in result['features']:
                self.assertLess(abs(feature['predicted_hz']-feature['simulated_peak_hz']), 10)
            self.assertLess(result['features'][2]['simulated_peak_dbc'], -30)
            self.assertGreater(result['features'][2]['simulated_peak_dbc'], -36)
    def test_transient_fit_on_held_out_symbols(self):
        time = np.arange(162)*8192/12000
        tones = np.arange(162)%4
        frequency = 3570100+tones*375/256+.35*np.exp(-time/19)
        result = fit_drift(time,tones,frequency)
        self.assertLess(result['held_out_max_residual_hz'], .001)
        self.assertAlmostEqual(result['fitted_tau_s'], 19, delta=.1)
    def test_fit_does_not_hide_irregular_error(self):
        rng = np.random.default_rng(6)
        time = np.arange(162)*8192/12000
        result = fit_drift(time,np.arange(162)%4,3570100+rng.normal(0,.2,162))
        self.assertGreater(result['held_out_max_residual_hz'], .1)
    def test_bad_input(self):
        with self.assertRaises(ValueError):
            fit_drift([1]*30,[0]*30,[0]*30)
        with self.assertRaises(ValueError):
            fit_drift(np.arange(30),np.zeros(30),np.arange(30))
        with self.assertRaises(ValueError):
            corrected_increment(100001)

if __name__ == '__main__':
    unittest.main()
