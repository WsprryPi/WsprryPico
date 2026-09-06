import sys
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from rf_bench import execute, decode_response

class Fake:
    def __init__(self, fail=False, cleanup='stopped', identity='abc'):
        self.commands = []
        self.fail, self.cleanup, self.identity = fail, cleanup, identity
    def exchange(self, command, timeout=5):
        self.commands.append(command)
        if command == 'INFO':
            return dict(ok=True, product='WsprryPico-RFBench', serial=self.identity,
                        utc_synchronized=False, revision='test')
        if command == 'CAPS':
            return dict(ok=True, interface='pico-rf-bench/1', engine='pio-dma-gp2', wspr='type1', frame='cycle4-162', correction_ppb_range=[-100000,100000])
        if command.startswith('CORRECTION '):
            return dict(ok=True, correction_ppb=int(command.split()[1]), output_active=False)
        if command == 'STOP':
            return dict(ok=True, state=self.cleanup, output_active=False)
        if command.startswith(('RUN ', 'FRAME ', 'WSPR ')):
            if self.fail:
                raise TimeoutError('lost response')
            return dict(ok=True, state='complete', output_active=False)
        return dict(ok=True, state='idle', output_active=False)

class Tests(unittest.TestCase):
    def test_numeric_response(self):
        self.assertEqual(decode_response(b'{"spacing":1.46484375,"time":12345678901234}')["time"],
                         12345678901234)
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}'):
            with self.assertRaises(ValueError):
                decode_response(raw)
    def test_success(self):
        fake = Fake()
        self.assertTrue(execute(fake, 'RUN 0 1 100', 2, 'abc', 'test')['completed'])
        self.assertEqual(fake.commands[-1], 'STOP')
    def test_correction_verified_before_run(self):
        fake = Fake()
        self.assertTrue(execute(fake, 'RUN 0 1 100', 2, 'abc', 'test', correction_ppb=2222)['completed'])
        self.assertLess(fake.commands.index('CORRECTION 2222'), fake.commands.index('RUN 0 1 100'))
    def test_stale_stop_prevents_correction(self):
        fake = Fake(cleanup='armed')
        with self.assertRaises(RuntimeError):
            execute(fake, 'RUN 0 1 100', 2, 'abc', 'test', correction_ppb=2222)
        self.assertNotIn('CORRECTION 2222', fake.commands)
        self.assertNotIn('RUN 0 1 100', fake.commands)

    def test_bad_correction_never_runs(self):
        fake = Fake()
        with self.assertRaises(ValueError):
            execute(fake, 'RUN 0 1 100', 2, 'abc', 'test', correction_ppb=100001)
        self.assertNotIn('RUN 0 1 100', fake.commands)
    def test_encoded_success_and_timeout_cleanup(self):
        fake = Fake()
        self.assertTrue(execute(fake, 'WSPR AA0NT EM18 20 100', 120, 'abc', 'test')['completed'])
        self.assertEqual(fake.commands[-1], 'STOP')
        fake = Fake(fail=True)
        with self.assertRaises(TimeoutError):
            execute(fake, 'WSPR AA0NT EM18 20 100', 120, 'abc', 'test')
        self.assertEqual(fake.commands[-1], 'STOP')

    def test_frame_success(self):
        fake = Fake()
        self.assertTrue(execute(fake, 'FRAME 100', 120, 'abc', 'test')['completed'])
        self.assertEqual(fake.commands[-1], 'STOP')
    def test_abort_then_rearm(self):
        class Running(Fake):
            def exchange(self, command, timeout=5):
                result = super().exchange(command, timeout)
                if command.startswith('FRAME ') or command == 'STATUS':
                    return dict(ok=True, state='running', output_active=True)
                return result
        fake = Running()
        with patch('rf_bench.time.sleep'):
            result = execute(fake, 'FRAME 100', 2, 'abc', 'test', abort_after_s=0)
        self.assertTrue(result['intentional_abort'] and result['completed'])
        self.assertTrue(execute(fake, 'RUN 0 1 100', 2, 'abc', 'test')['completed'])
    def test_not_exercised_abort_is_failure(self):
        fake = Fake()
        with self.assertRaises(RuntimeError):
            execute(fake, 'FRAME 100', 2, 'abc', 'test', abort_after_s=.1)
        self.assertEqual(fake.commands[-1], 'STOP')
    def test_timeout_stops(self):
        fake = Fake(fail=True)
        with self.assertRaises(TimeoutError):
            execute(fake, 'RUN 0 1 100', 2, 'abc', 'test')
        self.assertEqual(fake.commands[-1], 'STOP')
    def test_wrong_board_never_runs(self):
        fake = Fake(identity='other')
        with self.assertRaises(ValueError):
            execute(fake, 'RUN 0 1 100', 2, 'abc', 'test')
        self.assertEqual(fake.commands, ['INFO'])
    def test_stale_response_is_not_stop_confirmation(self):
        fake = Fake(cleanup='armed')
        with self.assertRaises(RuntimeError):
            execute(fake, 'RUN 0 1 100', 2, 'abc', 'test')
    def test_status_does_not_send_stop(self):
        fake = Fake()
        self.assertTrue(execute(fake, 'STATUS', 2, 'abc', 'test')['completed'])
        self.assertNotIn('STOP', fake.commands)

if __name__ == '__main__':
    unittest.main()
