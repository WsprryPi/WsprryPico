import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from rf_analysis.carrier_repeatability import compare_carriers
from analyze_rf_drift import fit_drift
from compare_rf_clocks import compare
from predict_rf_spurs import alias, corrected_increment, simulate

class Tests(unittest.TestCase):
    def reference_iq(self, error=0, sample_ppm=0, *, finite=True, reference=True,
                     dropout=False, ambiguity=False):
        rate = 10000
        time = np.arange(18*rate)/rate
        physical = time/(1+sample_ppm/1e6)
        common_phase = 2*np.pi*(35*time+.25*time*time)
        active = ((time >= 2) & (time < 14)) if finite else np.ones(len(time))
        if dropout:
            active = active & ~((time > 8) & (time < 8.2))
        signal = .2*active*np.exp(1j*(2*np.pi*(2000+error)*physical+common_phase))
        if reference:
            signal += .12*np.exp(1j*(2*np.pi*2500*physical+common_phase))
        if ambiguity:
            signal += .2*active*np.exp(1j*(2*np.pi*2030*physical+common_phase))
        random = np.random.default_rng(21)
        signal += .0001*(random.normal(size=len(time))+1j*random.normal(size=len(time)))
        return signal.astype(np.complex64)

    def reference_result(self, iq):
        return compare_carriers(iq, 10000, 28124100, 28126100, 28126600)

    def test_simultaneous_reference_known_errors(self):
        for error in (-3., 0., 2.5):
            for sample_ppm in (-100, 0, 100):
                with self.subTest(error=error, sample_ppm=sample_ppm):
                    result = self.reference_result(self.reference_iq(error, sample_ppm))
                    expected = 500+(error-500)/(1+sample_ppm/1e6)
                    self.assertAlmostEqual(result['measured_error_hz'], expected, delta=.002)
                    self.assertLessEqual(abs(result['measured_error_hz']-error),
                                         result['total_allowance_hz'])
                    self.assertEqual(len(result['one_second_errors_hz']), 8)

    def test_simultaneous_reference_invalid_input(self):
        iq = self.reference_iq()
        for bad in (iq[:1000], np.full_like(iq, complex(float('nan'), 0)),
                    np.full_like(iq, complex(1, 0)), self.reference_iq(reference=False)):
            with self.assertRaises(ValueError):
                self.reference_result(bad)
        with self.assertRaises(ValueError):
            compare_carriers(iq, 10000, 28124100, 28126100, 28126100)

    def test_simultaneous_reference_ambiguity(self):
        with self.assertRaises(ValueError):
            self.reference_result(self.reference_iq(ambiguity=True))

    def test_simultaneous_reference_dropout(self):
        with self.assertRaises(ValueError):
            self.reference_result(self.reference_iq(dropout=True))

    def test_simultaneous_reference_requires_quiet(self):
        with self.assertRaises(ValueError):
            self.reference_result(self.reference_iq(finite=False))

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
