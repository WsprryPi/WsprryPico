#!/usr/bin/env python3
"""Deterministic regressions for native STATUS start-cadence auditing."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_phase11_5_load import audit, status_cadence
from validate_wtp_contract import frame


def request(identity, started, finished=None):
    return dict(request_id=str(identity), started_ns=started,
                write_completed_ns=started if finished is None else finished)


class CadenceTests(unittest.TestCase):
    def test_delayed_write_return_cannot_hide_late_next_start(self):
        # Completion gap is only 1.5 s; actual request starts are 2.5 s apart.
        rows = [request(1, 0, 1_000_000_000), request(2, 2_500_000_000)]
        with self.assertRaisesRegex(ValueError, '2500000000'):
            status_cadence(rows, 0, 4)

    def test_return_delay_does_not_create_false_start_gap_failure(self):
        rows = [request(1, 0), request(2, 1_000_000_000, 2_500_000_000)]
        result = status_cadence(rows, 0, 4)
        self.assertEqual(result['nominal_max_status_start_gap_ns'], 1_000_000_000)

    def test_start_controls_nominal_window_membership(self):
        rows = [request(0, 0, 1_000_000_000), request(1, 1_000_000_001),
                request(2, 2_000_000_000), request(3, 3_000_000_000),
                request(4, 4_000_000_000), request(5, 5_000_000_000, 6_000_000_000)]
        self.assertEqual(status_cadence(rows, 1_000_000_000, 4)['nominal_status_count'], 5)

    def test_exact_bound_passes_one_nanosecond_over_fails(self):
        rows = [request(1, 0), request(2, 2_000_000_000)]
        self.assertEqual(status_cadence(rows, 0, 4)['nominal_max_status_start_gap_ns'], 2_000_000_000)
        rows[-1]['started_ns'] += 1
        with self.assertRaisesRegex(ValueError, '2000000001'):
            status_cadence(rows, 0, 4)

    def test_missing_requests_cannot_pass_small_gap(self):
        with self.assertRaisesRegex(ValueError, 'absent/reduced'):
            status_cadence([request(1, 0), request(2, 1_000_000_000)], 0, 180)

    def test_bad_order_and_empty_interval_fail(self):
        with self.assertRaisesRegex(ValueError, 'out of order'):
            status_cadence([request(1, 2), request(2, 1)], 0, 4)
        with self.assertRaisesRegex(ValueError, 'absent/reduced'):
            status_cadence([], 0, 180)

    def audit_writes(self, writes, version='P115TLS2'):
        """Exercise framing, schema and cadence together with synthetic TLS rows."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = dict(seconds=4, browser=False, boot_id='b' * 32)
            (root / 'load.json').write_text(json.dumps(plan))
            (root / 'result.json').write_text(json.dumps(dict(
                result='CAPTURED_REQUIRES_AUDIT', observer_exit=0, load_exit=0)))
            values = [('start', plan, 0), ('nominal_begin', {}, 0),
                      ('nominal_finish', {}, 4_000_000_000),
                      ('finish', dict(result='CAPTURED_REQUIRES_INDEPENDENT_AUDIT',
                                      failures=[], exit=0), 4_000_000_001)]
            (root / 'load-events.jsonl').write_text(''.join(json.dumps(dict(
                sequence=n, kind=k, value=v, monotonic_ns=t)) + '\n'
                for n, (k, v, t) in enumerate(values)))
            rows = []
            def row(kind, stamp, payload=b''):
                rows.append(dict(kind=kind, connection_id=1, monotonic_ns=stamp,
                                 version=version, payload=payload.hex()))
            row(2, 0, bytes.fromhex(
                '06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016'))
            for n, (start, finished) in enumerate(writes):
                common = dict(protocol='WTP/1', session_id='a' * 32,
                              request_id=f'{n:032x}', op='STATUS')
                request_bytes = frame(json.dumps(dict(common, type='request', body={})).encode())
                if version == 'P115TLS2':
                    row(7, start, request_bytes)
                row(3, finished, request_bytes)
                body = dict(boot_id=plan['boot_id'], state='empty', output_active=False,
                            owner_id=None, job_id=None, terminal_records=[])
                row(4, finished + 1, frame(json.dumps(dict(
                    common, type='response', ok=True, body=body)).encode()))
            # The real observer decoder has its own corruption/lifecycle tests.
            # This adapter supplies synthetic rows while audit() validates wire data.
            decoder = root / 'decoder.py'
            decoder.write_text('import json\ndef decode(data):\n'
                               ' return [dict(r, payload=bytes.fromhex(r["payload"])) '
                               'for r in json.loads(data)]\n')
            (root / 'production-tls.bin').write_text(json.dumps(rows))
            return audit(root, decoder)

    def test_full_audit_rejects_start_gap_hidden_by_write_completion(self):
        with self.assertRaisesRegex(ValueError, '2500000000'):
            self.audit_writes([(0, 1_000_000_000), (2_500_000_000, 2_500_000_000)])

    def test_full_audit_uses_entry_for_gap_and_request_latency(self):
        result = self.audit_writes([(0, 1), (1_000_000_000, 2_500_000_000)])
        self.assertEqual(result['nominal_max_status_start_gap_ns'], 1_000_000_000)
        self.assertEqual(result['max_observed_write_to_response_seconds'], 1.500000001)

    def test_legacy_return_only_observer_cannot_prove_start_cadence(self):
        with self.assertRaisesRegex(ValueError, 'requires native TLS write-entry timestamps'):
            self.audit_writes([(0, 1), (1_000_000_000, 1_000_000_001)], 'P115TLS1')


if __name__ == '__main__':
    unittest.main()
