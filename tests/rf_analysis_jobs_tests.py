"""Independent timing-oracle and input checks for reusable RF sample jobs."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from rf_analysis.jobs import CLOCKS, MODES, make_job
from wsprrypi_qualification.cw_defaults import hardware_free_keyed_protocol
from wsprrypi_qualification.cw_reference import generate_expected_events


class SampleJobTests(unittest.TestCase):
    def test_keyed_jobs_match_independent_protocol_reference(self):
        for mode in ('QRSS', 'FSKCW', 'DFCW'):
            expected = generate_expected_events(dict(
                mode=mode.lower(),
                capture_contract=dict(sample_count=3000000, sample_rate_hz=250000),
                protocol=hardware_free_keyed_protocol(
                    mode.lower(), primary_frequency_hz=3570100,
                    pre_quiet_seconds=1, post_quiet_seconds=1)))
            actual = make_job(mode, 3570100)['events']
            self.assertEqual(len(expected), len(actual))
            for observed, reference in zip(actual, expected):
                self.assertEqual(int(observed['offset_ns']), round(reference['start_s'] * 1e9))
                self.assertEqual(int(observed['duration_ns']),
                                 round((reference['end_s'] - reference['start_s']) * 1e9))
                self.assertEqual(observed['rf_on'], reference['rf_state'] != 'off')
                if observed['rf_on']:
                    self.assertEqual(int(observed['frequency_nhz']),
                                     round(reference['frequency_hz'] * 1e9))

    def test_qrss3_ratios_and_complete_job_timelines(self):
        for mode in ('QRSS', 'FSKCW', 'DFCW'):
            durations = [int(e['duration_ns'])
                         for e in make_job(mode, 3570100, keyed_dot_ns=3000000000)['events']]
            seconds = [1, 3, 3, 3, 3, 3, 1] if mode == 'DFCW' else [1, 3, 9, 9, 9, 3, 1]
            self.assertEqual(durations, [value * 1000000000 for value in seconds])
        for clock in CLOCKS:
            for mode in MODES:
                value = make_job(mode, 3570100, sample_rate_hz=clock)
                offset = 0
                for event in value['events']:
                    self.assertEqual(int(event['offset_ns']), offset)
                    self.assertGreater(int(event['duration_ns']), 0)
                    self.assertEqual('frequency_nhz' in event, event['rf_on'])
                    offset += int(event['duration_ns'])
                self.assertEqual(offset, int(value['total_duration_ns']))
                if mode == 'WSPR':
                    self.assertEqual((len(value['events']), offset), (162, 110592000000))

    def test_unsupported_clocks_modes_and_timing_inputs_are_rejected(self):
        for clock in (12000000, True, 138000000.0, 0):
            with self.subTest(clock=clock), self.assertRaises(ValueError):
                make_job('TONE', 3570100, sample_rate_hz=clock)
        for duration in (True, 0, 1, 700000000.0):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                make_job('QRSS', 3570100, keyed_dot_ns=duration)
        for mode, frequency in (('UNKNOWN', 3570100), ('TONE', True), ('TONE', 0),
                                ('TONE', 144490500), ('TONE', 3570100.0)):
            with self.subTest(mode=mode, frequency=frequency), self.assertRaises(ValueError):
                make_job(mode, frequency)


if __name__ == '__main__':
    unittest.main()
