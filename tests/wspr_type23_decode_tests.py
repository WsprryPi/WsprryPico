#!/usr/bin/env python3
"""Failure-path checks for captured-pair acceptance, without RF or decoder fixtures."""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
spec = importlib.util.spec_from_file_location('pair', Path(__file__).resolve().parents[1] / 'scripts/decode_wspr_type23_pair.py')
pair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pair)


class DecodeTests(unittest.TestCase):
    def setUp(self):
        self.type2 = '1400 -10 0.1 3.570100 0 PJ4/AA0NT 20\n<DecodeFinished>\n'
        self.type3 = '1402 -11 0.1 3.570100 0 <PJ4/AA0NT> EM18IG 20\n'

    def test_exact_formats_and_wrong_identity(self):
        self.assertTrue(pair.matches(self.type2, 2, 'PJ4/AA0NT', 'EM18IG', 20))
        self.assertTrue(pair.matches(self.type3, 3, 'PJ4/AA0NT', 'EM18IG', 20))
        for call, grid, power in [('PJ4/AA0NTX', 'EM18IG', 20), ('PJ4/AA0NT', 'AA00AA', 20), ('PJ4/AA0NT', 'EM18IG', 23)]:
            self.assertFalse(pair.matches(self.type3, 3, call, grid, power))
        self.assertFalse(pair.matches(self.type2, 3, 'PJ4/AA0NT', 'EM18IG', 20))
        self.assertFalse(pair.matches(self.type3.replace('<PJ4/AA0NT>', '<...>'), 3, 'PJ4/AA0NT', 'EM18IG', 20))
        self.assertFalse(pair.matches(self.type3.replace('3.570100', 'nan'), 3, 'PJ4/AA0NT', 'EM18IG', 20))

    def test_missing_truncated_wrong_order(self):
        rate = 1000
        intervals = [[2000, 112592], [122000, 232592]]
        pair.validate_windows(intervals, rate, 245000)
        for bad in [intervals[:1], intervals[::-1], [[2000, 110000], intervals[1]], [[2000, 112592], [123000, 233592]]]:
            with self.assertRaises(ValueError):
                pair.validate_windows(bad, rate, 245000)
        slots = [1792266841, 1792266961]
        ids = ['eeeeeeeeeeeeeeee' + format(s * 10**9, '016x') for s in slots]
        value = dict(slots_utc_s=slots, job_ids=ids, actual_rf_starts=2, status='CAPTURED', errors=[],
                     restoration={'verified': True}, ready={'status': {'boot_id': 'boot'}},
                     samples=[{'info': {'status': dict(state='running', job_id=i, boot_id='boot')}} for i in ids])
        terminal = dict(state='empty', job_id=None, boot_id='boot', owner_id=None, output_active=False,
                        wspr_pair_pending=False, last_job=ids[1], wspr_frame=2, wspr_frames=2,
                        last_error=None, enabled=True, suspended=False)
        value['samples'].append(dict(host_utc_ns=1, info=dict(status=terminal, dma_errors=0,
                                                            fault_stage=0, engine_diagnostic='')))
        pair.validate_order(value)
        for bad in [dict(value, samples=value['samples'][:1]), dict(value, samples=value['samples'][::-1]), dict(value, actual_rf_starts=1), dict(value, restoration={})]:
            with self.assertRaises(ValueError):
                pair.validate_order(bad)
        corrected = dict(value, status='FAILED', errors=["ValueError('receiver ended before complete pair')"])
        self.assertTrue(pair.validate_order(corrected)['controller_termination_corrected'])
        for bad in [dict(corrected, samples=value['samples'][:-1]),
                    dict(corrected, errors=['actual engine failure'])]:
            with self.assertRaises(ValueError):
                pair.validate_order(bad)
        self.assertFalse(pair.native_pair_terminal(dict(status=dict(terminal, suspended=True), dma_errors=0,
                                                        fault_stage=0, engine_diagnostic=''), ids[1]))
        self.assertFalse(pair.native_pair_terminal(dict(status=terminal, dma_errors=1,
                                                        fault_stage=0, engine_diagnostic=''), ids[1]))

    def test_frequency_mapping(self):
        self.assertEqual(pair.frequency_mapping(3568600), 3570100)
        self.assertEqual(pair.frequency_mapping(14095600), 14097100)
        for bad in (0, True, '14095600', 14095600.0, float('nan'), 2**64):
            with self.assertRaises(ValueError):
                pair.frequency_mapping(bad)
        physical = {'ready': {'status': {'schedule_dial_frequency_nhz': '14095600000000000'}}}
        self.assertEqual(pair.validate_dial(physical, 14095600), 14097100)
        for bad in ('14097100000000000', '14097097802734375', '0'):
            physical['ready']['status']['schedule_dial_frequency_nhz'] = bad
            with self.assertRaises(ValueError):
                pair.validate_dial(physical, 14095600)
        with self.assertRaises(ValueError):
            pair.validate_dial({'ready': {'status': {'schedule_base_frequency_nhz':'14095600000000000'}}}, 14095600)

    def test_decoder_rejects_nonfinite_dial_before_execution(self):
        for dial in (float('nan'), float('inf'), 0, -1):
            with self.assertRaises(ValueError):
                pair.run_decoder(Path('/missing'), Path('/missing.wav'), Path('/missing'), dial)

    def test_sample_job_time_association(self):
        origin = 1792266800
        slots = [origin + 10, origin + 130]
        intervals = [[10000, 120592], [130000, 240592]]
        metadata = {'timestamps': {'retained_capture_start_utc': datetime.fromtimestamp(origin, timezone.utc).isoformat()}}
        samples = [dict(host_utc_ns=(s + 1) * 10**9, host_monotonic_ns=(s - origin + 1) * 10**9,
                        info={'status': dict(state='running', job_id=j)}) for s, j in zip(slots, ['a', 'b'])]
        physical = dict(slots_utc_s=slots, job_ids=['a', 'b'], samples=samples)
        self.assertEqual(len(pair.associate(intervals, 1000, metadata, physical)), 2)
        with self.assertRaises(ValueError):
            pair.associate([[n + 120000 for n in v] for v in intervals], 1000, metadata, physical)

    def test_conversion_preserves_received_offset_and_rejects_silence(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest('Existing NumPy analysis environment required')
        rate, center, base = 10000, 3569100, 3570100
        t = np.arange(2 * rate) / rate
        iq = np.exp(2j * np.pi * (base - center + 2) * t)
        audio, parameters = pair.convert_audio(iq, rate, center, base)
        segment = audio[1200:13200]
        frequency = np.fft.rfftfreq(len(segment), 1 / 12000)[np.argmax(np.abs(np.fft.rfft(segment)))]
        self.assertAlmostEqual(frequency, 1502, delta=1)
        self.assertEqual(parameters['trailing_zero_samples'], 118 * 12000)
        self.assertEqual(parameters['fitted_frequency_correction_hz'], 0)
        with self.assertRaises(ValueError):
            pair.convert_audio(np.zeros_like(iq), rate, center, base)
        with self.assertRaises(ValueError):
            pair.convert_audio(iq, rate, center, base + 100000)

    def test_stale_state_and_decoder_failure_timeout(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / 'data'
            pair.fresh_directory(directory)
            (directory / 'hashtable.txt').write_text('stale expected identity\n')
            with self.assertRaises(FileExistsError):
                pair.fresh_directory(directory)
            # Executed subprocesses exercise real return-code and timeout handling.
            executable = Path(root) / 'decoder'
            executable.write_text('#!/bin/sh\nexit 7\n')
            executable.chmod(0o700)
            result = pair.run_decoder(executable, Path(root) / 'none.wav', directory, 3.568600)
            self.assertEqual(result['returncode'], 7)
            self.assertTrue(result['before']['exists'])
            executable.write_text('#!/bin/sh\nprintf "partial output\\n"\nexec sleep 2\n')
            result = pair.run_decoder(executable, Path(root) / 'none.wav', directory, 3.568600, timeout=.01)
            self.assertEqual(result['error'], 'TimeoutExpired')
            self.assertIsNone(result['returncode'])
            self.assertIn('partial output', result['stdout'])


if __name__ == '__main__':
    unittest.main()
