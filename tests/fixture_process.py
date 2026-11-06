"""Owned host fixtures: bounded UTF-8 lines, monotonic I/O, and finite teardown."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import threading
import time

_owner = ContextVar('fixture_owner', default=None)


def channel_operation(action):
    @wraps(action)
    def guarded(self, *args, **kwargs):
        if self.failure is not None:
            raise RuntimeError('stage=fixture-channel; refused after failed operation') from self.failure
        try:
            return action(self, *args, **kwargs)
        except BaseException as error:
            self.failure = self.failure or error
            raise
    return guarded


@contextmanager
def process_scope(timeout=240):
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Finite positive fixture scope watchdog required')
    owner = {'deadline': time.monotonic() + timeout, 'children': [], 'closing': False, 'interruption': None}
    token = _owner.set(owner)
    primary = None
    handlers = {}
    def interrupted(number, frame):
        if owner['interruption'] is None:
            owner['interruption'] = InterruptedError(f'fixture scope interrupted by signal={number}')
            if not owner['closing']:
                raise owner['interruption']
    try:
        if threading.current_thread() is threading.main_thread():
            for number in (signal.SIGINT, signal.SIGTERM):
                handlers[number] = signal.signal(number, interrupted)
        yield
    except BaseException as error:
        primary = error
    finally:
        owner['closing'] = True
        failures = []
        for child in reversed(owner['children']):
            try:
                child.finish()
            except BaseException as error:
                failures.append(error)
        for number, handler in handlers.items():
            try:
                signal.signal(number, handler)
            except BaseException as error:
                failures.append(error)
        _owner.reset(token)
    if owner['interruption'] is not None:
        if primary is None:
            primary = owner['interruption']
        elif primary is not owner['interruption']:
            failures.append(owner['interruption'])
    if failures:
        raise BaseExceptionGroup('fixture operation and cleanup failed', ([primary] if primary else []) + failures)
    if primary is not None:
        raise primary.with_traceback(primary.__traceback__)


class FixtureProcess(subprocess.Popen):
    limit = 1024 * 1024

    def __init__(self, *args, cleanup_timeout=6, **kwargs):
        owner = _owner.get()
        if owner is None:
            raise RuntimeError('FixtureProcess requires process_scope ownership before spawn')
        if type(cleanup_timeout) not in (int, float) or not math.isfinite(cleanup_timeout) or cleanup_timeout <= 0:
            raise ValueError('Finite positive fixture cleanup watchdog required')
        if any(kwargs.get(name, subprocess.PIPE) != subprocess.PIPE for name in ('stdin', 'stdout', 'stderr')):
            raise ValueError('Owned control fixtures require separate stdin/stdout/stderr pipes')
        self.deadline = owner['deadline']
        self.cleanup_timeout = cleanup_timeout
        self.pending = b''
        self.diagnostics = b''
        self.diagnostic_bytes = 0
        self.open_pipes = {}
        self.finished = False
        self.finish_error = None
        self.failure = None
        kwargs.update(start_new_session=os.name != 'nt')
        kwargs.setdefault('stdin', subprocess.PIPE)
        kwargs.setdefault('stdout', subprocess.PIPE)
        kwargs.setdefault('stderr', subprocess.PIPE)
        kwargs.setdefault('text', True)
        super().__init__(*args, **kwargs)
        owner['children'].append(self)  # Before any fallible initialization/I/O.
        self.open_pipes = {self.stdout.fileno(): 'stdout', self.stderr.fileno(): 'stderr'}
        os.set_blocking(self.stdin.fileno(), False)

    def _end(self, timeout=15, deadline=None):
        return min(self.deadline, time.monotonic() + timeout, deadline if deadline is not None else float('inf'))

    def _pump(self, deadline, max_wait=None):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f'stage=fixture-line; pending_bytes={len(self.pending)}; child_exit={self.poll()}; stderr_bytes={self.diagnostic_bytes}; monotonic watchdog expired')
        with selectors.DefaultSelector() as selector:
            for fd in self.open_pipes:
                selector.register(fd, selectors.EVENT_READ)
            events = selector.select(min(remaining, max_wait) if max_wait is not None else remaining)
        if time.monotonic() >= deadline:
            raise TimeoutError('stage=fixture-line; completion exceeded enclosing deadline')
        for key, _ in events:
            fd = key.fd
            data = os.read(fd, 4096)
            if not data:
                del self.open_pipes[fd]
            elif self.open_pipes[fd] == 'stderr':
                self.diagnostic_bytes += len(data)
                self.diagnostics = (self.diagnostics + data)[-65536:]
            else:
                self.pending += data
                if len(self.pending) > self.limit:
                    raise ValueError('stage=fixture-line; response exceeds byte bound')

    @channel_operation
    def line(self, timeout=15, *, deadline=None):
        end = self._end(timeout, deadline)
        while b'\n' not in self.pending:
            if self.stdout.fileno() not in self.open_pipes:
                raise EOFError(f'stage=fixture-line; EOF before complete line; pending_bytes={len(self.pending)}; child_exit={self.poll()}; stderr_bytes={self.diagnostic_bytes}')
            self._pump(end)
        line, self.pending = self.pending.split(b'\n', 1)
        if time.monotonic() >= end:
            raise TimeoutError('stage=fixture-line; late response cannot qualify')
        return (line + b'\n').decode('utf-8', errors='strict')

    @channel_operation
    def send_line(self, value, timeout=15, *, deadline=None):
        end = self._end(timeout, deadline)
        data = (value + '\n').encode('utf-8')
        if len(data) > self.limit:
            raise ValueError('stage=fixture-input; command exceeds byte bound')
        while data:
            remaining = end - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('stage=fixture-input; enclosing deadline expired')
            with selectors.DefaultSelector() as selector:
                selector.register(self.stdin, selectors.EVENT_WRITE)
                ready = selector.select(remaining)
            if time.monotonic() >= end:
                raise TimeoutError('stage=fixture-input; late write cannot qualify')
            if ready:
                try:
                    data = data[os.write(self.stdin.fileno(), data):]
                except BlockingIOError:
                    continue

    @channel_operation
    def exchange(self, value, timeout=15):
        if self.pending:
            raise RuntimeError('stage=fixture-channel; unsolicited buffered reply before request')
        end = self._end(timeout)
        self.send_line(value, deadline=end)
        return self.line(deadline=end)

    def _signal(self, value):
        try:
            if os.name != 'nt':
                os.killpg(self.pid, value)
            elif self.poll() is None:
                self.send_signal(value)
        except ProcessLookupError:
            pass

    def _drain_until_exit(self, deadline, leader_only=False):
        while self.poll() is None or (self.open_pipes and not leader_only):
            if self.open_pipes:
                # A descendant may retain a pipe after leader exit. Polling here
                # observes that transition; a quiet pipe is never an exit oracle.
                self._pump(deadline, max_wait=.02)
            else:
                self.wait(timeout=max(0, deadline - time.monotonic()))
        self.wait(timeout=max(0, deadline - time.monotonic()))

    def _group_live(self, deadline):
        if os.name == 'nt':
            return self.poll() is None
        try:
            os.killpg(self.pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            pass  # A permitted process-state read must still prove no live writers.
        if Path('/proc').is_dir():
            for entry in Path('/proc').iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    if os.getpgid(int(entry.name)) == self.pid:
                        state = (entry / 'stat').read_text().rsplit(')', 1)[1].split()[0]
                        if state != 'Z':
                            return True
                except (ProcessLookupError, FileNotFoundError):
                    continue
            return False
        states = subprocess.check_output(['ps', '-axo', 'pgid=,stat='], text=True,
                                         timeout=max(0, deadline - time.monotonic()))
        return any(int(parts[0]) == self.pid and not parts[1].startswith('Z')
                   for line in states.splitlines() if len(parts := line.split()) == 2)

    def _confirm_group_exit(self, deadline):
        while self._group_live(deadline):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('stage=fixture-cleanup; owned process-group writers remain')
            # Observation pacing, never evidence that a writer has stopped.
            time.sleep(min(.01, remaining))

    def finish(self, mode='term'):
        if self.finished:
            if self.finish_error:
                raise self.finish_error
            return
        self.finished = True
        errors = []
        end = time.monotonic() + self.cleanup_timeout
        try:
            if self.poll() is not None:
                raise RuntimeError(f'stage=fixture-exit; unexpected child_exit={self.returncode}')
            if mode == 'eof':
                self.stdin.close()
            elif mode == 'term':
                self._signal(signal.SIGTERM)
            else:
                raise ValueError('Unknown fixture shutdown policy')
            # Reserve half the finite teardown budget for forced recovery/reaping.
            self._drain_until_exit(end - self.cleanup_timeout / 2, leader_only=True)
            if self.returncode != 0:
                raise RuntimeError(f'stage=fixture-exit; child_exit={self.returncode}; expected=orderly zero exit')
        except BaseException as error:
            errors.append(error)
        finally:
            try:
                self._signal(signal.SIGKILL)  # Includes owned descendants after leader exit.
            except BaseException as error:
                errors.append(error)
            try:
                # Drop already-rejected oversized data while draining the killed writers.
                if self.pending and self.failure is None:
                    errors.append(RuntimeError(f'stage=fixture-reply; unconsumed response bytes={len(self.pending)}'))
                self.pending = b''
                self._drain_until_exit(end)
                self._confirm_group_exit(end)
                if self.pending and self.failure is None:
                    errors.append(RuntimeError(f'stage=fixture-reply; unconsumed shutdown bytes={len(self.pending)}'))
            except BaseException as error:
                errors.append(error)
            for stream in (self.stdin, self.stdout, self.stderr):
                try:
                    stream.close()
                except BaseException as error:
                    errors.append(error)
        if errors:
            self.finish_error = BaseExceptionGroup('owned fixture shutdown failed', errors)
            raise self.finish_error

    def stderr_text(self):
        if not self.finished:
            raise RuntimeError('Read fixture diagnostics only after owned teardown')
        return self.diagnostics.decode('utf-8', errors='replace')
