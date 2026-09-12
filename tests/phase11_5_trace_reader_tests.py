import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase11_5_trace_reader import TraceReader


class TraceTests(unittest.TestCase):
    def reader(self, cost=0.001, latest=40):
        self.now, self.requests, self.rows = 0.0, [], []
        def transfer(fd, command, deadline, emit, framed):
            self.assertFalse(framed)
            self.assertEqual(fd, 7)
            self.assertAlmostEqual(deadline, self.now+5)
            self.requests.append(command)
            cursor = int(command.decode().split()[1])
            self.now += cost
            return dict(ok=True, device_id='device', boot_id='boot', revision='revision',
                        trace=dict(intact=True, install_errors=0, oldest=max(1, latest-255),
                                   latest=latest, events=[dict(seq=i) for i in
                                   range(cursor+1, min(cursor+8, latest)+1)]))
        return TraceReader('device', 'boot', 'revision', lambda *r: self.rows.append(r),
                           clock=lambda: self.now, transfer=transfer)

    def test_slow_page_returns_to_info_instead_of_draining_backlog(self):
        reader = self.reader(cost=0.65)
        reader.drain(7)
        self.assertEqual(self.requests, [b'NETTRACE 0\n'])
        self.assertEqual(reader.cursor, 8)
        reader.drain(7)
        self.assertEqual(self.requests[-1], b'NETTRACE 8\n')
        self.assertEqual(reader.cursor, 16)

    def test_fast_pages_drain_to_latest(self):
        reader = self.reader()
        reader.drain(7)
        self.assertEqual(reader.cursor, 40)
        self.assertEqual(len(self.requests), 5)

    def test_time_budget_also_bounds_repeated_small_pages(self):
        reader = self.reader(cost=0.011, latest=80)
        reader.drain(7)
        self.assertEqual(len(self.requests), 5)
        self.assertEqual(reader.cursor, 40)

    def test_nonadvancing_clock_still_limits_page_count(self):
        reader = self.reader(cost=0, latest=256)
        reader.drain(7)
        self.assertEqual(len(self.requests), 16)
        self.assertEqual(reader.cursor, 128)

    def test_identity_hooks_gaps_and_empty_backlog_fail_without_cursor_advance(self):
        for mutate in (lambda r: r.update(boot_id='wrong'),
                       lambda r: r['trace'].update(intact=False),
                       lambda r: r['trace'].update(install_errors=1),
                       lambda r: r['trace']['events'][0].update(seq=2),
                       lambda r: r['trace']['events'][1].update(seq=99),
                       lambda r: r['trace'].update(events=[])):
            reader = self.reader()
            original = reader.transfer
            def transfer(*args):
                reply = copy.deepcopy(original(*args)); mutate(reply); return reply
            reader.transfer = transfer
            with self.assertRaises(ValueError):
                reader.drain(7)
            self.assertEqual(reader.cursor, 0)

    def test_empty_current_ring_completes(self):
        reader = self.reader(latest=0)
        reader.drain(7)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(reader.cursor, 0)

    def test_exchange_failure_is_not_retried_or_marked_consumed(self):
        reader = self.reader()
        def failed(*args):
            self.requests.append(args[1])
            raise TimeoutError('partial Console reply')
        reader.transfer = failed
        with self.assertRaises(TimeoutError):
            reader.drain(7)
        self.assertEqual(self.requests, [b'NETTRACE 0\n'])
        self.assertEqual(reader.cursor, 0)


if __name__ == '__main__':
    unittest.main()
