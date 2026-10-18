"""An aborted waveform must leave the entire remaining capture quiet."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from rf_analysis.abort import envelope


class AbortEnvelopeTests(unittest.TestCase):
    def test_rejects_full_duration_extra_bursts_and_brief_leading_or_tail_rf(self):
        power = np.zeros(12000)
        power[2000:4874] = 1
        self.assertTrue(envelope(power, 1000, 10)['passed'])
        for case in ('complete', 'extra', 'tail', 'leading', 'missing'):
            invalid = power.copy()
            if case == 'complete':
                invalid[2000:] = 1
            elif case == 'extra':
                invalid[7000:7500] = 1
            elif case == 'tail':
                invalid[8000:8002] = .2
            elif case == 'leading':
                invalid[:3] = .2
            else:
                invalid[:] = 0
            with self.subTest(case=case):
                self.assertFalse(envelope(invalid, 1000, 10)['passed'])

    def test_nonfinite_or_negative_power_and_invalid_axes_are_rejected(self):
        power = np.zeros(12000)
        power[2000:4874] = 1
        for value in (float('nan'), float('inf'), -.1):
            invalid = power.copy()
            invalid[100] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                envelope(invalid, 1000, 10)
        for rate, duration in ((0, 10), (float('nan'), 10), (1000, 1),
                               (1000, float('inf'))):
            with self.subTest(rate=rate, duration=duration), self.assertRaises(ValueError):
                envelope(power, rate, duration)


if __name__ == '__main__':
    unittest.main()
