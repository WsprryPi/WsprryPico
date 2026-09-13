"""Observer publication and failure isolation, without hardware."""
import sys
import threading
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase11_5_r3_v2_rf import fresh_sample, guarded_action

class ObserverRaceTests(unittest.TestCase):
    def test_publication_is_read_after_writer_releases_lock(self):
        # The writer has journaled a fresh INFO but is still flushing it. The
        # stale previous tuple must not escape before the publication completes.
        actual = threading.Lock()
        entered = threading.Event()
        class Lock:
            def __enter__(self):
                entered.set()
                actual.acquire()
            def __exit__(self, *args): actual.release()
        samples = {'info': (0, 'old')}
        values = []
        with actual:
            reader = threading.Thread(target=lambda: values.append(
                fresh_sample(samples, Lock(), 'info', 2, lambda: 10)))
            reader.start()
            self.assertTrue(entered.wait(2))
            samples['info'] = (9, 'fresh')
        reader.join(2)
        self.assertFalse(reader.is_alive())
        self.assertEqual(values, ['fresh'])

    def test_freshness_bound_is_unchanged(self):
        lock = threading.Lock()
        self.assertEqual(fresh_sample({'info': (8, 'ok')}, lock, 'info', 2, lambda: 10), 'ok')
        for stamp in [7, 11]:
            with self.subTest(stamp=stamp), self.assertRaisesRegex(ValueError, 'age_ns='):
                fresh_sample({'info': (stamp, 'bad')}, lock, 'info', 2, lambda: 10)

    def test_failed_action_does_not_kill_reader_or_allow_later_mutation(self):
        faults, records, read, acted = [], [], [], []
        def action(value):
            acted.append(value)
            raise ValueError('injected guard failure')
        for value in range(3):
            read.append(value)
            guarded_action(action, value, faults, lambda k, v: records.append((k, v)))
        self.assertEqual(read, [0, 1, 2])
        self.assertEqual(acted, [0])
        self.assertEqual(len(faults), 1)
        self.assertEqual(records, [('failure', {'worker': 'wtp action', 'error': 'injected guard failure', 'type': 'ValueError'})])

    def test_successful_actions_continue(self):
        values, faults = [], []
        for value in range(3): guarded_action(values.append, value, faults, self.fail)
        self.assertEqual(values, [0, 1, 2])
        self.assertEqual(faults, [])

if __name__ == '__main__': unittest.main()
