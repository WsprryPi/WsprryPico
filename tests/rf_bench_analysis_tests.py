#!/usr/bin/env python3
"""Optional offline checks; run with the existing Harness Python environment."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from analyze_rf_bench import analyze


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.iq = self.root / 'capture.cf32'
        self.meta = self.root / 'capture.json'
        rng = np.random.default_rng(17)
        self.samples = (rng.normal(size=250000) + 1j * rng.normal(size=250000)) * 0.0001

    def write(self):
        self.samples.astype('<c8').tofile(self.iq)
        self.metadata = dict(primary_outcome='success', cleanup=dict(outcome='verified'),
            output=dict(complete=True, size_bytes=self.iq.stat().st_size,
                        sha256=hashlib.sha256(self.iq.read_bytes()).hexdigest()),
            retained_sample_count=len(self.samples),
            wire_format=dict(sample_format='CF32', component_type='IEEE754_binary32',
                             interleave='real_imaginary', byte_order='little_endian',
                             bytes_per_complex_sample=8),
            actual_settings=dict(sample_rate_hz=250000, center_frequency_hz=3550000))
        self.meta.write_text(json.dumps(self.metadata))

    def run_analysis(self):
        with contextlib.redirect_stdout(io.StringIO()):
            analyze(self.iq, self.meta, self.root / 'analysis')
        return json.loads((self.root / 'analysis/summary.json').read_text())

    def test_burst_preserves_edges_and_is_not_qualification(self):
        t = np.arange(50000) / 250000
        self.samples[75000:125000] += 0.1 * np.exp(2j * np.pi * 20100 * t)
        self.write()
        result = self.run_analysis()
        self.assertTrue(result['detected'])
        self.assertFalse(result['qualification'])
        begin, end = result['selected_samples']
        self.assertLessEqual(begin, 75000)
        self.assertGreaterEqual(end, 125000)
        self.assertEqual(result['off_samples'], [0, begin])
        self.assertEqual(result['carrier']['metrics']['noise_guard']['outcome'], 'inconclusive')

    def test_noise_does_not_create_burst(self):
        self.write()
        self.assertFalse(self.run_analysis()['detected'])

    def test_tampered_capture_rejected(self):
        self.write()
        with self.iq.open('r+b') as output:
            output.write(b'bad!')
        with self.assertRaises(ValueError):
            self.run_analysis()

    def test_nonfinite_samples_rejected_even_with_matching_hash(self):
        self.samples[100] = complex(float('nan'), 0)
        self.write()
        with self.assertRaises(ValueError):
            self.run_analysis()

    def test_wrong_wire_format_rejected(self):
        self.write()
        self.metadata['wire_format']['interleave'] = 'imaginary_real'
        self.meta.write_text(json.dumps(self.metadata))
        with self.assertRaises(ValueError):
            self.run_analysis()


if __name__ == '__main__':
    unittest.main()
