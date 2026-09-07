#!/usr/bin/env python3
"""Independent sampled RF fixtures challenge operational false passes."""

import sys
import copy
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from campaign.plan import make_job
from campaign.analysis import keyed, spectrum


def synth(job, *, extra=False, wrong_shift=False, dropout=False):
    rate = 12000
    duration = int(job["total_duration_ns"]) / 1e9 + 4
    count = round(duration * rate)
    rng = np.random.default_rng(71)
    iq = 0.0001 * (rng.normal(size=count) + 1j * rng.normal(size=count))
    phase = 0.0
    for event in job["events"]:
        if not event["rf_on"]:
            continue
        a = round((2 + int(event["offset_ns"]) / 1e9) * rate)
        b = a + round(int(event["duration_ns"]) / 1e9 * rate)
        frequency = int(event["frequency_nhz"]) / 1e9 - 3570100
        if wrong_shift:
            frequency = 0
        angle = phase + 2 * np.pi * (2000 + frequency) * np.arange(b - a) / rate
        iq[a:b] += 0.2 * np.exp(1j * angle)
        phase = angle[-1] + 2 * np.pi * (2000 + frequency) / rate
    if extra:
        a = round(0.8 * rate)
        iq[a : a + 1200] += 0.2 * np.exp(2j * np.pi * 2000 * np.arange(1200) / rate)
    if dropout:
        a = round(3.2 * rate)
        iq[a : a + 100] = 0.0001
    return iq, rate


class AnalysisTests(unittest.TestCase):
    def test_keyed_modes_and_faults(self):
        for mode in ("QRSS", "FSKCW", "DFCW"):
            job = make_job(mode, 3570100)
            iq, rate = synth(job)
            good = keyed(iq, rate, 3568100, 3570100, job)
            self.assertTrue(good["passed"], (mode, good))
            for fault in ("extra", "dropout"):
                iq, rate = synth(job, **{fault: True})
                self.assertFalse(keyed(iq, rate, 3568100, 3570100, job)["passed"])
            if mode != "QRSS":
                iq, rate = synth(job, wrong_shift=True)
                self.assertFalse(keyed(iq, rate, 3568100, 3570100, job)["passed"])

    def test_keyed_transition_with_large_common_frequency_offset(self):
        job = make_job("FSKCW", 3570100)
        iq, rate = synth(job)
        iq *= np.exp(2j * np.pi * 45 * np.arange(len(iq)) / rate)
        report = keyed(iq, rate, 3568100, 3570100, job)
        self.assertTrue(report["passed"], report["issues"])

    def test_frequency_noise_is_not_reported_as_timing_failure(self):
        job = make_job("FSKCW", 3570100)
        iq, rate = synth(job)
        iq *= np.exp(1j * 0.03 * np.sin(2 * np.pi * 25 * np.arange(len(iq)) / rate))
        report = keyed(iq, rate, 3568100, 3570100, job)
        self.assertFalse(report["passed"])
        self.assertEqual(
            set(report["issues"]),
            {"keyed frequency transition fit residual exceeds 0.15 Hz"},
        )
        self.assertLess(max(abs(t["error_s"]) for t in report["transitions"]), 0.02)
        self.assertGreater(max(t["fit_rms_hz"] for t in report["transitions"]), 0.15)

    def test_spectrum_measures_known_spur(self):
        rate = 12000
        t = np.arange(12000) / rate
        iq = np.exp(2j * np.pi * 2000 * t) + 0.1 * np.exp(2j * np.pi * 3500 * t)
        report = spectrum(iq, rate, 0, [2000], [[0, 1]])
        self.assertTrue(report["available"])
        self.assertAlmostEqual(
            report["strongest_other_bin_hz"], 3500, delta=rate / report["fft_samples"]
        )
        self.assertAlmostEqual(report["strongest_other_bin_dbc"], -20, delta=1)
        self.assertFalse(spectrum(iq[:10], rate, 0, [2000], [[0, 0.001]])["available"])

    def test_fsk_timing_cannot_hide_in_continuous_carrier(self):
        expected = make_job("FSKCW", 3570100)
        changed = copy.deepcopy(expected)
        changed["events"][1]["duration_ns"] = str(
            int(changed["events"][1]["duration_ns"]) + 50000000
        )
        changed["events"][2]["offset_ns"] = str(
            int(changed["events"][2]["offset_ns"]) + 50000000
        )
        changed["events"][2]["duration_ns"] = str(
            int(changed["events"][2]["duration_ns"]) - 50000000
        )
        iq, rate = synth(changed)
        report = keyed(iq, rate, 3568100, 3570100, expected)
        self.assertFalse(report["passed"])
        self.assertIn("keyed frequency transition timing failed", report["issues"])


if __name__ == "__main__":
    unittest.main()
