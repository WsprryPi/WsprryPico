"""Counterexamples for real owned Python control pipes and teardown."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest
from unittest.mock import patch

from fixture_process import FixtureProcess, process_scope

PRELUDE = "import os,sys,signal,json;signal.signal(signal.SIGTERM,lambda *args:sys.exit(0))\n"


class ProcessTests(unittest.TestCase):
    def child(self, code, **kwargs):
        return FixtureProcess([sys.executable, '-u', '-c', PRELUDE + code], **kwargs)

    def test_spawn_requires_prior_ownership_and_spawn_failure_propagates(self):
        with self.assertRaisesRegex(RuntimeError, 'ownership before spawn'):
            FixtureProcess([sys.executable, '-c', 'pass'])
        with self.assertRaises(FileNotFoundError), process_scope():
            FixtureProcess(['/no/such/owned-fixture'])

    def test_failed_signal_registration_restores_prior_handler_and_owner(self):
        before = signal.getsignal(signal.SIGINT)
        actual = signal.signal
        def install(number, handler):
            if number == signal.SIGTERM and getattr(handler, '__name__', '') == 'interrupted':
                raise PermissionError('signal registration denied')
            return actual(number, handler)
        with patch.object(signal, 'signal', side_effect=install):
            with self.assertRaises(PermissionError), process_scope():
                self.fail('acquisition must fail before the body')
        self.assertIs(signal.getsignal(signal.SIGINT), before)
        with self.assertRaisesRegex(RuntimeError, 'ownership before spawn'):
            self.child('pass')

    def test_invalid_watchdogs_and_stdio_refuse_before_spawning(self):
        for value in (0, -1, True, float('inf'), float('nan')):
            with self.subTest(value=value), self.assertRaises(ValueError), process_scope(value):
                self.fail('invalid enclosing watchdog')
            with process_scope():
                with self.assertRaises(ValueError):
                    self.child('pass', cleanup_timeout=value)
        with process_scope(), self.assertRaises(ValueError):
            self.child('pass', stdout=subprocess.DEVNULL)

    def test_fragmented_utf8_and_queued_lines_preserve_framing(self):
        with process_scope():
            p = self.child("sys.stdin.readline();os.write(1,b'{\"x\":\"\\xce');sys.stdin.readline();os.write(1,b'\\xbb\"}\\n{\"next\":2}\\n');sys.stdin.read()")
            p.send_line('BEGIN')
            while not p.pending:
                p._pump(p._end())
            self.assertEqual(p.pending, b'{"x":"\xce')  # Observed partial UTF-8 before release.
            p.send_line('RELEASE')
            self.assertEqual(json.loads(p.line()), {'x': 'λ'})
            self.assertEqual(json.loads(p.line()), {'next': 2})
            p.finish(mode='eof')
            p.finish()
            self.assertEqual(p.returncode, 0)
            self.assertFalse(p.open_pipes)

    def test_observed_partial_line_has_a_finite_read_watchdog(self):
        with process_scope():
            p = self.child("sys.stdin.readline();os.write(1,b'partial');sys.stdin.read()")
            p.send_line('HOLD')
            while not p.pending:
                p._pump(p._end())
            with self.assertRaises(TimeoutError):
                p.line(timeout=.02)  # Finite fault watchdog after observed held bytes.
            with self.assertRaisesRegex(RuntimeError, 'refused after failed operation'):
                p.exchange('NEXT')  # A cancelled/late reply cannot satisfy a later request.
            p.finish(mode='eof')

    def test_parent_deadline_rejects_late_queued_success(self):
        with process_scope():
            p = self.child("print('READY',flush=True);sys.stdin.read()")
            while b'\n' not in p.pending:
                p._pump(p._end())
            with self.assertRaises(TimeoutError):
                p.line(deadline=0)
            p.finish(mode='eof')

    def test_invalid_utf8_is_refused_without_disclosing_payload(self):
        with process_scope():
            p = self.child("sys.stdin.readline();os.write(1,b'\\xff\\n');sys.stdin.read()")
            p.send_line('INVALID')
            with self.assertRaises(UnicodeDecodeError):
                p.line()
            p.finish(mode='eof')

    def test_oversized_line_fails_and_owned_child_is_reaped(self):
        p = None
        with self.assertRaises(ValueError) as result:
            with process_scope():
                p = self.child("sys.stdin.readline();os.write(1,b'x'*(1024*1024+1));sys.stdin.read()")
                p.exchange('OVERSIZE')
        self.assertIn('byte bound', str(result.exception))
        self.assertIsNotNone(p.returncode)

    def test_unsolicited_buffered_reply_cannot_qualify_a_later_exchange(self):
        with process_scope():
            p = self.child("sys.stdin.readline();print('{}\\n{\"unsolicited\":1}',flush=True);sys.stdin.read()")
            self.assertEqual(json.loads(p.exchange('FIRST')), {})
            while not p.pending:
                p._pump(p._end())
            with self.assertRaisesRegex(RuntimeError, 'unsolicited buffered reply'):
                p.exchange('NEXT')
            p.finish(mode='eof')

    def test_response_during_orderly_shutdown_cannot_hide_after_last_reply(self):
        with self.assertRaises(BaseExceptionGroup):
            with process_scope():
                p = self.child("sys.stdin.readline();print('{}',flush=True);sys.stdin.read();print('UNEXPECTED',flush=True)")
                self.assertEqual(json.loads(p.exchange('LAST')), {})
                p.finish(mode='eof')

    def test_eof_before_complete_line_refuses(self):
        with self.assertRaises((EOFError, BaseExceptionGroup)) as result:
            with process_scope():
                p = self.child("sys.stdin.readline();os.write(1,b'partial');sys.exit(0)")
                p.exchange('EOF')
        self.assertIsInstance(result.exception.exceptions[0] if isinstance(result.exception, BaseExceptionGroup) else result.exception, EOFError)

    def test_last_reply_then_exit_cannot_pass_and_other_finalizers_run(self):
        other = None
        with self.assertRaises(BaseExceptionGroup):
            with process_scope():
                p = self.child("sys.stdin.readline();print('{}',flush=True);sys.exit(17)")
                self.assertEqual(json.loads(p.exchange('LAST')), {})
                p.wait(timeout=5)  # Observe the actual crash before finalization.
                other = self.child("print('READY',flush=True);sys.stdin.read()")
                self.assertEqual(other.line(), 'READY\n')
        self.assertEqual(other.returncode, 0)
        self.assertEqual(p.returncode, 17)

    def test_ignored_eof_is_force_reaped_and_remains_unsuccessful(self):
        p = None
        with self.assertRaises(BaseExceptionGroup):
            with process_scope():
                p = self.child("sys.stdin.read();print('EOF_IGNORED',flush=True);signal.pause()", cleanup_timeout=.2)
                # EOF is the stimulus. A complete acknowledged line proves entry
                # before finish attempts its finite orderly-shutdown watchdog.
                p.stdin.close()
                self.assertEqual(p.line(), 'EOF_IGNORED\n')
                p.finish(mode='eof')
        self.assertEqual(p.returncode, -signal.SIGKILL)

    def test_descendant_retaining_pipes_is_stopped_after_orderly_leader_exit(self):
        descendant = "import signal;signal.signal(signal.SIGTERM,signal.SIG_IGN);print('HELD',flush=True);signal.pause()"
        code = ("import subprocess\n"
                "child=subprocess.Popen([sys.executable,'-u','-c',"+repr(descendant)+"],stdout=subprocess.PIPE)\n"
                "assert child.stdout.readline()==b'HELD\\n'\n"
                "print('READY',flush=True)\n"
                "sys.stdin.read()\n")
        with process_scope():
            p = self.child(code)
            self.assertEqual(p.line(), 'READY\n')
            p.finish(mode='eof')
            self.assertEqual(p.returncode, 0)
            self.assertFalse(p.open_pipes)
            self.assertFalse(p._group_live(p._end()))

    def test_scope_signal_reaps_a_separately_owned_nested_fixture(self):
        nested = PRELUDE + "print('READY',flush=True);sys.stdin.read()"
        code = ("sys.path.insert(0,'tests')\nfrom fixture_process import FixtureProcess,process_scope\n"
                "with process_scope():\n"
                " p=FixtureProcess([sys.executable,'-u','-c',"+repr(nested)+"])\n"
                " assert p.line()=='READY\\n'\n"
                " print(json.dumps({'inner':p.pid}),flush=True)\n"
                " signal.pause()\n")
        inner = None
        try:
            with self.assertRaises(BaseExceptionGroup):
                with process_scope():
                    outer = self.child(code)
                    inner = json.loads(outer.line())['inner']
                    outer.send_signal(signal.SIGTERM)
                    self.assertNotEqual(outer.wait(timeout=5), 0)
                    with self.assertRaises(ProcessLookupError):
                        os.kill(inner, 0)
        finally:
            if inner:
                try:
                    os.killpg(inner, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_signal_denial_is_preserved_after_forced_owned_recovery(self):
        with self.assertRaises(BaseExceptionGroup):
            with process_scope():
                p = self.child("print('READY',flush=True);sys.stdin.read()")
                self.assertEqual(p.line(), 'READY\n')
                actual = p._signal
                def signal_owned(value):
                    if value == signal.SIGTERM:
                        raise PermissionError('owned SIGTERM denied')
                    actual(value)
                with patch.object(p, '_signal', side_effect=signal_owned):
                    p.finish()
        self.assertIsNotNone(p.returncode)


if __name__ == '__main__':
    unittest.main()
