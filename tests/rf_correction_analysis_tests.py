import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from rf_analysis.carrier_repeatability import compare_carriers
from rf_analysis.pps_windows import analyze_windows, compare_production, _reconstruction_bounds
from rf_analysis.wiring import analyze_wiring
from rf_analysis.pairing import diagnose_pairing
from analyze_rf_drift import fit_drift
from compare_rf_clocks import compare
from predict_rf_spurs import alias, corrected_increment, simulate

class Tests(unittest.TestCase):
    def pairing_text(self):
        rows=['BEGIN_PAIRING_TRACE samples=41 valid=1 period_ns=100000000 max_work_us=250']
        for i in range(41):
            observations = 0 if i<10 else 1 if i<40 else 2
            error = 'unpaired_utc' if 20<=i<30 else 'pairing_acquisition' if 30<=i<40 else 'none'
            rows.append('PAIRING i=%d raw_ns=%d candidate_utc_ns=%d candidate_raw_ns=%d candidate_pps_ns=%d observation_raw_ns=%d observations=%d rejected=0 uart_errors=0 dropped=0 capture_rejections=0 flags=15 error=%s'%(i,10**9+i*100000000,1800000000000000000,10**9+i//10*1000000000,10**9+i//10*1000000000,10**9,observations,error))
        return '\n'.join(rows+['END_PAIRING_TRACE'])+'\n'
    def test_pairing_trace_explains_stall_without_accepting_capture(self):
        import json
        result=diagnose_pairing(self.pairing_text())
        self.assertEqual(result['qualification'],'not_evaluated')
        self.assertEqual(result['samples'],41)
        self.assertEqual(result['maximum_sample_gap_ns'],100000000)
        self.assertEqual(len(result['observation_stalls']),1)
        self.assertIn('unpaired_utc',result['observation_stalls'][0]['errors'])
        self.assertIn('pairing_acquisition',result['observation_stalls'][0]['errors'])
        self.assertNotIn('latitude',json.dumps(result))
        self.assertIsNone(diagnose_pairing('old capture without trace'))
        self.assertFalse(diagnose_pairing(self.pairing_text().replace('valid=1','valid=0'))['valid'])
        aux=['BEGIN_AUX_PPS gp=3 pulses=5 valid=1']
        primary=[]
        for i in range(5):
            raw=1000000*(i+1)
            aux.append('AUX_PPS i=%d raw_low_us=%d raw_high_us=%d'%(i,raw,raw+1))
            primary.append('PULSE i=%d raw_low=%d raw_high=%d count_low=0 count_high=1'%(i,raw+50000,raw+50001))
        combined='\n'.join(aux+['END_AUX_PPS']+primary)+'\n'+self.pairing_text()
        phase=diagnose_pairing(combined)
        self.assertEqual(phase['auxiliary_pps_pulses'],5)
        self.assertEqual(phase['qlg3_minus_primary_phase_ns'],[-50001000,-49999000])
        with self.assertRaises(ValueError):diagnose_pairing(combined.replace('pulses=5','pulses=6'))
    def test_pairing_trace_refuses_missing_malformed_and_reversed_records(self):
        text=self.pairing_text()
        for bad in (text.replace('samples=41','samples=40'),text.replace('END_PAIRING_TRACE',''),text.replace('flags=15','flags=16',1),text.replace('error=none','error=unknown',1),text.replace('uart_errors=0','uart_errors=true',1),text.replace('i=1 raw_ns=1100000000','i=1 raw_ns=900000000'),text.replace('observations=2','observations=0'),text.replace('dropped=0','dropped=4294967296',1)):
            with self.assertRaises(ValueError):diagnose_pairing(bad)
    def wiring_text(self, phase):
        rows=['CHECK duration_us=2200000 clock_edges=%d max_gap_us=9 coherent=1 input_only=1' % (2200000 if phase=='clock' else 0)]
        for gp in range(8,14):
            n=123456 if phase=='clock' and gp==9 else 2 if phase=='pps' and gp==11 else 0
            rows.append('CHECK_PIN gp=%d rises=%d falls=%d' % (gp,n,n))
        return '\n'.join(rows+['END_CHECK'])
    def test_wiring_valid_isolated_outputs(self):
        for phase in ('off','clock','pps'):
            self.assertEqual(analyze_wiring(self.wiring_text(phase),phase)['phase'],phase)
    def test_wiring_refuses_swapped_or_neighbouring_signal(self):
        for gp in (8,9,10,12,13):
            text=self.wiring_text('pps').replace('gp=11 rises=2 falls=2','gp=11 rises=0 falls=0').replace('gp=%d rises=0 falls=0'%gp,'gp=%d rises=2 falls=2'%gp)
            with self.assertRaises(ValueError):analyze_wiring(text,'pps')
        with self.assertRaises(ValueError):analyze_wiring(self.wiring_text('clock'),'off')
    def test_wiring_refuses_missing_wrong_rate_or_stuck_pps(self):
        for phase,text in [('clock',self.wiring_text('clock').replace('clock_edges=2200000','clock_edges=22000000')),('pps',self.wiring_text('off')),('pps',self.wiring_text('pps').replace('rises=2 falls=2','rises=1 falls=0'))]:
            with self.assertRaises(ValueError):analyze_wiring(text,phase)
    def test_wiring_refuses_incomplete_and_invalid_health(self):
        base=self.wiring_text('off')
        for text in (base.replace('coherent=1','coherent=0'),base.replace('input_only=1','input_only=0'),base.replace('max_gap_us=9','max_gap_us=400'),base.replace('duration_us=2200000','duration_us=1'),base+'\nEND_CHECK',base.replace('gp=10','gp=9')):
            with self.assertRaises(ValueError):analyze_wiring(text,'off')
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
            self.assertTrue(any(r['loaded'] is None for r in result['windows']))
            self.assertTrue(any(r['loaded'] is False for r in result['windows']))
            self.assertTrue(any(r['loaded'] is True for r in result['windows']))
            shifted = compare_production(pulses,self.production_observations(pulses)[1:])
            self.assertTrue(any(r['loaded'] is None for r in shifted['windows']))

    def test_same_edge_comparison_detects_capture_error(self):
        pulses = self.bracketed_pulses()
        result = compare_production(pulses,self.production_observations(pulses,timestamp_error=True))
        self.assertTrue(any(not r['consistent_with_independent_brackets'] for r in result['windows']))
        self.assertGreater(max(abs(r['acquisition_difference_midpoint_ppb']) for r in result['windows']),500)

    def test_reconstruction_encloses_retained_discrepancy_without_hiding_midpoint(self):
        from fractions import Fraction
        # Retained quiet-first PPS100..110: 10M counts, 2355ns normalization
        # difference. Independent count delta is 9,999,987..10,000,002.
        a=dict(edges=100975524,raw_ns=110634365145,count_raw_ns=110634373500,
               uncertainty_ns=200000,count_bound_ns=9855)
        b=dict(edges=110975524,raw_ns=120634378500,count_raw_ns=120634384500,
               uncertainty_ns=200000,count_bound_ns=7500)
        pa=(100,110634365,110634373,100975517,100975524)
        pb=(110,120634371,120634379,110975512,110975518)
        result=_reconstruction_bounds(a,b,pa,pb,Fraction(100),10000000)
        full=result['declared_production']['acquisition_difference_bounds_ppb']
        self.assertLess(full[0],-41800)
        self.assertGreater(full[1],43400)
        self.assertTrue(result['declared_production']['overlaps_independent_brackets'])
        self.assertTrue(result['observed_raw_pps']['overlaps_independent_brackets'])
        # This remains a midpoint discrepancy: adding full intervals does not
        # change the original arithmetic or its comparison result.
        midpoint=Fraction(10000000*10000013355,10000011000)
        self.assertAlmostEqual(float((midpoint-10000002)*100),35.49974095028495)
        with self.assertRaises(ValueError):
            _reconstruction_bounds(a,dict(b,count_raw_ns=a['count_raw_ns']+1),
                                   pa,pb,Fraction(100),10000000)

    def test_reconstruction_bounds_do_not_accept_unexplained_count_bias(self):
        pulses=self.bracketed_pulses()
        rows=self.production_observations(pulses)
        for row in rows:
            row.update(count_raw_ns=row['raw_ns'],count_bound_ns=1000,
                       uncertainty_ns=1000,edges=row['edges']-50)
        rows[10]['edges']+=100 # 10ppm count error, exceeding endpoint bounds.
        first=compare_production(pulses,rows)['windows'][0]
        self.assertFalse(first['consistent_with_independent_brackets'])
        self.assertFalse(first['reconstruction_bounds']['declared_production']['overlaps_independent_brackets'])
        self.assertFalse(first['reconstruction_bounds']['observed_raw_pps']['overlaps_independent_brackets'])

    def test_same_edge_comparison_refuses_missing_or_unbound_records(self):
        pulses = self.bracketed_pulses()
        rows = self.production_observations(pulses)
        bad = rows[:100]+rows[101:]
        with self.assertRaises(ValueError):
            compare_production(pulses,bad)
        refused = [dict(r) for r in rows];refused[50]['coherent'] = 0
        analyzed = compare_production(pulses,refused)
        self.assertEqual(analyzed['incoherent_sequences'],[51])
        self.assertTrue(any(not r['available'] for r in analyzed['windows']))
        for field,value in (('coherent',2),('plan',0),('capture',0),('count_bound_ns',1)):
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
        lines = ['INFO serial=1545B6EFBF78028C clock_hz=138000000 ram_only=1 pps_gp=3 input_gp=7 seconds=300 source=si5351 production=1 input_only=1']
        lines += ['LOAD x']*10800
        lines += ['BEGIN_PRODUCTION first_loaded=0 pattern=alternating_60pps']
        lines += ['PULSE i=%d raw_low=%d raw_high=%d count_low=%d count_high=%d'%p for p in pulses]
        lines += ['PROD '+' '.join('%s=%s'%(k,v) for k,v in r.items()) for r in observations]
        health = dict(uart_errors=0,dropped=0,capture_rejections=0,
                      maximum_irq_latency_ns='5000',capture_error_bound_ns='6000',
                      position=dict(latitude_e7=123,longitude_e7=456))
        lines += ['GPS_BASELINE_STATUS '+json.dumps(health),'GPS_STATUS '+json.dumps(health), 'END_PRODUCTION pulses=301 observations=301 coherent=1 max_gap_us=1 restored=1 first_loaded=0 load_writes=10800']
        text = '\n'.join(lines)+'\n'
        result = module.analyze(text)
        self.assertNotIn('latitude',json.dumps(result))
        self.assertNotIn('longitude',json.dumps(result))
        known = text.replace('pps_gp=3 input_gp=7','pps_gp=11 input_gp=9').replace('source=si5351','source=known_ratio')
        self.assertEqual(module.analyze(known)['independent']['pps_endpoint_allowance_us'],10)
        startup = text.replace('"uart_errors": 0','"uart_errors": 90')
        self.assertEqual(module.analyze(startup)['health_deltas']['uart_errors'],0)
        during_capture = startup.replace('GPS_STATUS {"uart_errors": 90','GPS_STATUS {"uart_errors": 91')
        with self.assertRaises(ValueError):
            module.analyze(during_capture)
        for bad in (text.replace('restored=1','restored=0'), text.replace('input_gp=7','input_gp=9'),
                    text.replace('coherent=1','coherent=2',1), text.replace('LOAD x\n','',1),
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
