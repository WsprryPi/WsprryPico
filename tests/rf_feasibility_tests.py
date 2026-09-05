#!/usr/bin/env python3
"""Independent arithmetic and spectral checks for the feasibility study."""

import cmath
from fractions import Fraction as F
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_rf_feasibility as rf


class FeasibilityTests(unittest.TestCase):
    def test_report_is_current(self):
        self.assertEqual((ROOT / "docs/rf-calculations.md").read_text(), rf.report())

    def test_static_dividers_cannot_resolve_four_tones(self):
        for base in rf.BASES:
            pio = [rf.divider(F(base) + n * rf.SPACING, 256, 2)[0] for n in range(4)]
            self.assertEqual(len(set(pio)), 1)
        for scale, toggles in ((256, 2), (65536, 1)):
            for base in rf.BASES:
                f = F(base)
                word, actual = rf.divider(f, scale, toggles)
                for neighbor in (word - 1, word + 1):
                    self.assertLessEqual(abs(actual - f), abs(F(rf.FS * scale, toggles * neighbor) - f))
        with self.assertRaises(ValueError):
            rf.divider(F(rf.FS), 256, 2)

    def test_tone_errors_and_multisynth_register_round_trip(self):
        for base in rf.BASES:
            represented = []
            for tone in range(4):
                target = F(base) + tone * rf.SPACING
                word, actual = rf.nco(target)
                self.assertLessEqual(abs(actual - target), F(rf.FS, 2 ** 33))
                represented.append(actual)
                ratio, actual = rf.multisynth(target)
                a, b = divmod(ratio.numerator, ratio.denominator)
                c = ratio.denominator
                # AN619 encoded parameters, reconstructed independently.
                q = (128 * b) // c
                p1 = 128 * a + q - 512
                p2 = 128 * b - c * q
                self.assertTrue(0 <= p1 < 2 ** 18)
                self.assertTrue(0 <= p2 < 2 ** 20)
                self.assertTrue(1 <= c < 2 ** 20)
                reconstructed = F(p1 + 512, 128) + F(p2, 128 * c)
                self.assertEqual(reconstructed, ratio)
                self.assertLess(abs(actual - target), F(2, 1_000_000))
            self.assertEqual(len(set(represented)), 4)
            for left, right in zip(represented, represented[1:]):
                self.assertLess(abs(right - left - rf.SPACING), F(4, 100))

    def test_absolute_deadlines_do_not_accumulate_rounding(self):
        deadlines = [rf.nearest(n * rf.SYMBOL * 1_000_000) for n in range(163)]
        self.assertEqual(deadlines[-1], 110_592_000)
        self.assertEqual(set(b - a for a, b in zip(deadlines, deadlines[1:])), {682666, 682667})
        for n, deadline in enumerate(deadlines):
            self.assertLessEqual(abs(deadline - n * rf.SYMBOL * 1_000_000), F(1, 2))
        self.assertEqual(rf.FS * rf.SYMBOL, 102_400_000)
        self.assertEqual(rf.nearest(rf.SYMBOL * 1_000_000) * 162 - deadlines[-1], 54)

    def test_bounded_measurement_budget(self):
        transition_ns = rf.nearest(16 * rf.SYMBOL * 1_000_000_000)
        frame_ns = rf.nearest(162 * rf.SYMBOL * 1_000_000_000)
        expected = 2_000_000_000 + 3 * 2_000_000_000 + 2 * (4 * 5_000_000_000 + transition_ns + frame_ns)
        self.assertEqual(rf.MEASUREMENT_RF_ON_NS, expected)
        self.assertIn(str(float(F(expected, 1_000_000_000))),
                      (ROOT / "docs/development/rf-measurement-plan.md").read_text())

    def test_edge_error_bounds(self):
        for base in rf.BASES:
            errors = rf.edge_errors(rf.nco(F(base))[1])
            self.assertTrue(all(0 <= error < 1 for error in errors))
        self.assertEqual(set(rf.edge_errors(F(rf.FS, 4))), {F(0)})

    def test_spectral_coefficients_against_direct_dft(self):
        # Small exact period permits an independent full DFT without an FFT library.
        period, step = 128, 13
        word = step * ((1 << 32) // period)
        samples = [1 if ((n * step) % period) < period // 2 else -1 for n in range(period)]

        def amplitude(bin_index):
            coeff = sum(value * cmath.exp(-2j * math.pi * bin_index * n / period)
                        for n, value in enumerate(samples))
            x = math.pi * bin_index / period
            return abs(coeff) * math.sin(x) / x

        for order, frequency, db in rf.aliases(word):
            index = int(frequency * period / rf.FS)
            expected = 20 * math.log10(amplitude(index) / amplitude(step))
            self.assertAlmostEqual(db, expected, places=9)


if __name__ == "__main__":
    unittest.main()
