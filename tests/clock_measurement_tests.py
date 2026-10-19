"""Known physical-error and uncertainty cases for independent clock measurements."""
import sys
import unittest
import copy
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from rf_analysis.clock_measurement import (
    independent_improvement, paired_utc_improvement, paired_rate_improvement,
    residual_rate, rf_error,
    utc_bracket_error, verdict, project_clock, pulse_holdout,
    paired_utc_interval_improvement,
)


class Tests(unittest.TestCase):
    def test_fully_asymmetric_usb_capture_is_inside_bound(self):
        # Capture can occur at either end; midpoint is not known true time.
        before, after, error = 1_000_000_000, 1_006_000_000, 20_000
        for truth in (before - error, before, after, after + error):
            pico = truth + 120_000
            low, high = utc_bracket_error(pico, before, after, 10, 6_000_010, error, 1000)
            self.assertLessEqual(low, 120_000)
            self.assertGreaterEqual(high, 120_000)

    def test_clock_step_and_bad_bounds_refuse(self):
        for values in [(100, 100, 200, 100, 110, 1, 5),
                       (100, 100, 90, 100, 110, 1, 5),
                       (100, 100, 110, 100, 110, -1, 5)]:
            with self.assertRaises(ValueError):
                utc_bracket_error(*values)

    def test_shared_reference_can_resolve_small_rate_benefit(self):
        # A 128 us improvement is resolvable despite +/-1 ms reference range
        # when both predictions are certainly on the same side of true UTC.
        gain = paired_utc_improvement(10_000_000, 9_872_000, (-1_000_000, 1_000_000))
        self.assertEqual(gain, (128_000, 128_000))
        self.assertEqual(verdict(gain), 'improved')

    def test_crossing_reference_leaves_benefit_unresolved(self):
        gain = paired_utc_improvement(128_000, 0, (-1_000_000, 1_000_000))
        self.assertEqual(gain, (-128_000, 128_000))
        self.assertEqual(verdict(gain), 'unresolved')

    def test_interval_predictions_include_interior_true_time(self):
        self.assertEqual(paired_utc_interval_improvement((-1, 1), (10, 10), (0, 0)),
                         (-10, -9))
        self.assertEqual(paired_utc_interval_improvement((10, 10), (-1, 1), (0, 0)),
                         (9, 10))

    def test_interval_gain_covers_dense_independent_reference_grid(self):
        result = paired_utc_interval_improvement((-2, 3), (-4, 1), (-1, 2))
        values = [abs(Fraction(c, 4)-Fraction(r, 4))-
                  abs(Fraction(q, 4)-Fraction(r, 4))
                  for c in range(-8, 13) for q in range(-16, 5)
                  for r in range(-4, 9)]
        self.assertEqual(result, (min(values), max(values)))

    def test_two_rf_references_remove_offset_and_sample_scale(self):
        # Known receiver plant: indicated = 100 + actual * 1.0002.
        # A single offset subtraction leaves a 2 Hz scale bias at 10 kHz spacing.
        indicate = lambda f: Fraction(100) + Fraction(5001, 5000) * f
        actual, requested = Fraction(3_570_100_125, 1000), 3_570_100
        refs = (3_560_000, 3_580_000)
        result = rf_error((indicate(actual),) * 2,
                          [(indicate(f),) * 2 for f in refs],
                          [(f, f) for f in refs], requested)
        self.assertEqual(result['error_hz'], (Fraction(1, 8),) * 2)
        self.assertEqual(result['receiver_scale'], (Fraction(5000, 5001),) * 2)

    def test_rf_uncertainty_covers_known_plant(self):
        target, refs = Fraction(3_570_100_125, 1000), (3_560_000, 3_580_000)
        result = rf_error((target - Fraction(1, 100), target + Fraction(1, 100)),
                          [(f - Fraction(1, 100), f + Fraction(1, 100)) for f in refs],
                          [(f - Fraction(1, 1000), f + Fraction(1, 1000)) for f in refs],
                          3_570_100)
        self.assertLessEqual(result['error_hz'][0], Fraction(1, 8))
        self.assertGreaterEqual(result['error_hz'][1], Fraction(1, 8))
        with self.assertRaises(ValueError):
            rf_error((1, 2), [(1, 2)], [(1, 2)], 1)
        with self.assertRaises(ValueError):
            rf_error((1, 2), [(1, 2), (1, 2)], [(1, 2), (3, 4)], 1)

    def test_independent_treatments_do_not_reuse_shared_error(self):
        self.assertEqual(verdict(independent_improvement((9, 11), (-2, 2))), 'improved')
        self.assertEqual(verdict(independent_improvement((-2, 2), (9, 11))), 'worsened')
        self.assertEqual(verdict(independent_improvement((-2, 2), (-2, 2))), 'unresolved')

    def test_physical_rate_overcorrection_is_distinct_from_uncertainty(self):
        raw = (Fraction('-0.992'), Fraction('-0.903'))
        corrected = residual_rate(raw, 20748)
        self.assertGreater(corrected[0], 19)
        self.assertEqual(verdict(paired_rate_improvement(raw, 20748)), 'worsened')
        self.assertEqual(verdict(paired_rate_improvement(raw, 950)), 'improved')
        # An uncertainty interval crossing the optimum cannot certify benefit.
        self.assertEqual(verdict(paired_rate_improvement((Fraction('.854'), Fraction('.942')),
                                                        -1858)), 'unresolved')
        with self.assertRaises(ValueError):
            residual_rate((0, 1), -1_000_000_000)

    def test_phase_slew_and_frequency_benefit_are_separate(self):
        raw = (Fraction('.85'), Fraction('.95'))
        # Phase slew is deliberately speeding the clock to remove an offset.
        # The learned negative frequency component reduces that instantaneous
        # rate error, even though the total mapping still runs too fast.
        total, phase_only = 2929, 4148
        self.assertGreater(residual_rate(raw, total)[0], 3)
        gain = paired_rate_improvement(raw, total, phase_only)
        self.assertGreater(gain[0], Fraction('1.218'))
        self.assertEqual(verdict(gain), 'improved')

    def holdout_records(self, frequency=-1000, phase=2000, offset=5_000_000):
        # Known plant: raw oscillator is 1 ppm fast. A -1000 ppb frequency
        # estimate cancels it; phase slew is intentionally speeding up UTC.
        start, elapsed, epoch = 10**9, 64*10**9, 10**12
        anchor = dict(monotonic_now_ns=str(start), utc_now_ns=str(epoch+offset),
                      rate_ppb=frequency+phase, subsequent_rate_ppb=frequency,
                      rate_until_monotonic_ns=str(2**64-1), model_generation='7')
        a = dict(clock_valid=True, source_sntp=True, source_disagreement=False,
                 device_id='device', boot_id='boot', revision='source', source_epoch='2',
                 ntp_generation='9',
                 rise_before=anchor, rise_raw_lower_ns=str(start),
                 rise_raw_upper_ns=str(start+5000), frequency_ppb=frequency)
        b = copy.deepcopy(a)
        low, high = start+elapsed, start+elapsed+5000
        b.update(rise_raw_lower_ns=str(low), rise_raw_upper_ns=str(high),
                 rise_utc_lower_ns=str(project_clock(anchor, low)),
                 rise_utc_upper_ns=str(project_clock(anchor, high)))
        b['rise_before'].update(monotonic_now_ns=str(low),
                               utc_now_ns=b['rise_utc_lower_ns'])
        host = epoch+elapsed*10**6//1_000_001
        return ({'pico': a}, {'pico': b, 'events': [{'timestamp_ns': host}]})

    def test_causal_pulse_holdout_resolves_known_rate_benefit(self):
        first, last = self.holdout_records()
        result = pulse_holdout(first, last, 1_000_000)
        self.assertEqual(result['verdict'], 'improved')
        self.assertGreater(result['absolute_improvement_ns'][0], 50_000)
        # Frozen starting frequency removes the incremental treatment entirely.
        held = pulse_holdout(first, last, 1_000_000, control_frequency_ppb=-1000)
        self.assertEqual(held['verdict'], 'unresolved')

    def test_pulse_holdout_detects_physical_overcorrection(self):
        first, last = self.holdout_records(frequency=20_000, phase=0)
        self.assertEqual(pulse_holdout(first, last, 1_000_000)['verdict'], 'worsened')

    def test_pulse_holdout_keeps_reference_uncertainty(self):
        first, last = self.holdout_records(phase=0, offset=0)
        self.assertEqual(pulse_holdout(first, last, 1_000_000)['verdict'], 'unresolved')

    def test_admitted_mapping_difference_cannot_create_a_small_benefit(self):
        first, last = self.holdout_records(frequency=-100, phase=0)
        for name in ['rise_utc_lower_ns', 'rise_utc_upper_ns']:
            last['pico'][name] = str(int(last['pico'][name])+1900)
        result = pulse_holdout(first, last, 1_000_000)
        self.assertEqual(result['verdict'], 'unresolved')
        self.assertEqual(result['applied_utc_ns'][0],
                         int(last['pico']['rise_utc_lower_ns']))

    def test_pulse_holdout_refuses_changed_model_or_unseen_phase_jump(self):
        first, last = self.holdout_records()
        for key in ['boot_id', 'source_epoch', 'revision', 'ntp_generation']:
            bad = copy.deepcopy(last)
            bad['pico'][key] = 'changed'
            with self.assertRaises(ValueError):
                pulse_holdout(first, bad, 1_000_000)
        bad = copy.deepcopy(last)
        bad['pico']['rise_before']['model_generation'] = '8'
        with self.assertRaises(ValueError):
            pulse_holdout(first, bad, 1_000_000)
        bad = copy.deepcopy(last)
        bad['pico']['rise_utc_lower_ns'] = str(int(bad['pico']['rise_utc_lower_ns'])+3000)
        with self.assertRaises(ValueError):
            pulse_holdout(first, bad, 1_000_000)

    def test_projection_preserves_finite_slew_end_and_rounding(self):
        anchor = dict(monotonic_now_ns='1000', utc_now_ns='1000000000000',
                      rate_ppb=100_000_000, subsequent_rate_ppb=-1000,
                      rate_until_monotonic_ns='2000')
        self.assertEqual(project_clock(anchor, 3000), 1_000_000_002_099)
        self.assertEqual(project_clock(anchor, 3000, 1000), 1_000_000_002_100)
        with self.assertRaises(ValueError):
            project_clock(anchor, 999)


if __name__ == '__main__':
    unittest.main()
