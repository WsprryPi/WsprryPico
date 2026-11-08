import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from rf_analysis.carrier_repeatability import compare_carriers
from rf_analysis.pps_windows import analyze_windows, compare_production
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

    def bracketed_pulses(self, error_ppb=0, timer_ppb=0):
        from fractions import Fraction
        rows = []
        for i in range(301):
            raw = 1_000_000 + int(Fraction(i*1_000_000*(1_000_000_000+timer_ppb), 1_000_000_000))
            count = 100 + int(Fraction(i*1_000_000*(1_000_000_000+error_ppb), 1_000_000_000))
            rows.append((i, raw, raw+1, count, count+1))
        return rows

    def test_pps_known_reference_and_independent_timer(self):
        for error in (-337, -75, 0, 45, 20000):
            for timer in (-20000, 0, 20000):
                result = analyze_windows(self.bracketed_pulses(error, timer))
                self.assertEqual([r['windows'] for r in result['summaries']], [30,10,5,1])
                for row in result['windows']:
                    self.assertLessEqual(row['reference_offset_ppb'][0], error)
                    self.assertGreaterEqual(row['reference_offset_ppb'][1], error)
                    self.assertLessEqual(row['raw_timer_error_ppb'][0], timer)
                    self.assertGreaterEqual(row['raw_timer_error_ppb'][1], timer)

    def test_pps_shared_clock_exact_ratio(self):
        result = analyze_windows(self.bracketed_pulses(), pps_endpoint_us=0)
        for row in result['windows']:
            self.assertEqual(row['reference_midpoint_ppb'], 0)
            self.assertLess(row['reference_offset_ppb'][0], 0)
            self.assertGreater(row['reference_offset_ppb'][1], 0)
        bounds = [r['maximum_half_interval_ppb'] for r in result['summaries']]
        self.assertGreater(bounds[0], bounds[1])
        self.assertGreater(bounds[1], bounds[2])
        self.assertGreater(bounds[2], bounds[3])

    def test_pps_short_window_quantization(self):
        result = analyze_windows(self.bracketed_pulses(45), pps_endpoint_us=0)
        short, _, long, _ = result['summaries']
        self.assertGreater(short['peak_to_peak_ppb'], long['peak_to_peak_ppb'])
        self.assertAlmostEqual(long['mean_ppb'], 45, delta=4)

    def test_pps_missing_and_duplicate_edges_refused(self):
        rows = self.bracketed_pulses()
        for bad in (rows[:-1], rows[:50]+rows[51:], rows[:50]+[rows[49]]+rows[51:]):
            with self.assertRaises(ValueError):
                analyze_windows(bad)

    def test_pps_invalid_brackets_refused(self):
        rows = self.bracketed_pulses()
        for row in ((20,0,101,0,1), (20,1,0,1,2), (20,1,2,3,2), (20,1,2,3,104),
                    (20,True,2,3,4)):
            bad = rows.copy(); bad[20] = row
            with self.assertRaises(ValueError):
                analyze_windows(bad)

    def test_pps_invalid_assumptions_refused(self):
        rows = self.bracketed_pulses()
        for allowance in (-1,101,float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):
                analyze_windows(rows, pps_endpoint_us=allowance)
        for nominal in (0,-1,True,1.0):
            with self.assertRaises(ValueError):
                analyze_windows(rows, nominal_hz=nominal)

    def production_observations(self, pulses, *, timestamp_error=False):
        result = []
        for i, low, high, count_low, count_high in pulses:
            raw = (low+high)*500
            error = ((i % 7)-3)*5000 if timestamp_error else 0
            result.append(dict(seq=i+1,raw_ns=raw+error,
                               utc_ns=(1_800_000_000+i)*1_000_000_000,
                               uncertainty_ns=200000,coherent=1,edges=count_low+50,
                               count_raw_ns=raw+50000,count_bound_ns=100000,
                               plan=1,capture=1))
        return result

    def test_same_edge_comparison_cancels_real_clock_error(self):
        for error in (-337,0,45):
            pulses = self.bracketed_pulses(error)
            result = compare_production(pulses,self.production_observations(pulses))
            self.assertEqual(result['observations'],301)
            self.assertTrue(all(r['consistent_with_independent_brackets'] for r in result['windows']))
            self.assertTrue(all(r['loaded'] is not None for r in result['windows']))
            shifted = compare_production(pulses,self.production_observations(pulses)[1:])
            self.assertTrue(any(r['loaded'] is None for r in shifted['windows']))

    def test_same_edge_comparison_detects_capture_error(self):
        pulses = self.bracketed_pulses()
        result = compare_production(pulses,self.production_observations(pulses,timestamp_error=True))
        self.assertTrue(any(not r['consistent_with_independent_brackets'] for r in result['windows']))
        self.assertGreater(max(abs(r['acquisition_difference_midpoint_ppb']) for r in result['windows']),500)

    def test_same_edge_comparison_refuses_missing_or_unbound_records(self):
        pulses = self.bracketed_pulses()
        rows = self.production_observations(pulses)
        bad = rows[:100]+rows[101:]
        with self.assertRaises(ValueError):
            compare_production(pulses,bad)
        for field,value in (('coherent',0),('plan',0),('capture',0),('count_bound_ns',1)):
            bad = [dict(r) for r in rows];bad[50][field] = value
            with self.assertRaises(ValueError):
                compare_production(pulses,bad)

    def test_production_transcript_completion_and_privacy(self):
        import importlib.util
        import json
        path = Path(__file__).parent/'hardware/si5351-reference-truth/analyze_production.py'
        spec = importlib.util.spec_from_file_location('production_analysis',path)
        module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        pulses = self.bracketed_pulses()
        observations = self.production_observations(pulses)
        lines = ['INFO serial=1545B6EFBF78028C clock_hz=138000000 ram_only=1 pps_gp=3 input_gp=7 seconds=300 source=si5351 production=1']
        lines += ['LOAD x']*10800
        lines += ['BEGIN_PRODUCTION first_loaded=0 pattern=alternating_60pps']
        lines += ['PULSE i=%d raw_low=%d raw_high=%d count_low=%d count_high=%d'%p for p in pulses]
        lines += ['PROD '+' '.join('%s=%s'%(k,v) for k,v in r.items()) for r in observations]
        health = dict(uart_errors=0,dropped=0,capture_rejections=0,
                      maximum_irq_latency_ns='5000',capture_error_bound_ns='6000',
                      position=dict(latitude_e7=123,longitude_e7=456))
        lines += ['GPS_STATUS '+json.dumps(health), 'END_PRODUCTION pulses=301 observations=301 coherent=1 max_gap_us=1 restored=1 first_loaded=0 load_writes=10800']
        text = '\n'.join(lines)+'\n'
        result = module.analyze(text)
        self.assertNotIn('latitude',json.dumps(result))
        self.assertNotIn('longitude',json.dumps(result))
        for bad in (text.replace('restored=1','restored=0'), text.replace('input_gp=7','input_gp=9'),
                    text.replace('coherent=1','coherent=0',1), text.replace('LOAD x\n','',1),
                    text.replace('observations=301','observations=300')):
            with self.assertRaises(ValueError):
                module.analyze(bad)

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
