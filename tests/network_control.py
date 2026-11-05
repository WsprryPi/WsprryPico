"""Correlated host-adapter barriers; ACK follows the command and foreground poll."""
from collections import deque
import re
import time


class NetworkControl:
    def __init__(self, process):
        self.process = process
        self.sequence = 0
        self.replies = deque()
        self.failure = None

    def send(self, command, *, deadline=None):
        if self.failure is not None:
            raise RuntimeError('network control refused after failed exchange') from self.failure
        if not isinstance(command, str) or not re.fullmatch(r'[A-Z][A-Z0-9 ]{0,127}', command) or command.startswith('SYNC'):
            raise ValueError('One explicit network control command required')
        if self.replies:
            raise RuntimeError('Unconsumed network control facts before next command')
        self.sequence += 1
        end = min(self.process.deadline, time.monotonic() + 3, deadline if deadline is not None else float('inf'))
        self.fact_deadline = end
        try:
            self.process.send_line(command, deadline=end)
            self.process.send_line(f'SYNC {self.sequence}', deadline=end)
            while True:
                line = self.process.line(deadline=end).strip()
                if time.monotonic() >= end:
                    raise TimeoutError('Late network control ACK cannot qualify')
                if line.startswith('SYNC '):
                    if line != f'SYNC {self.sequence}':
                        raise RuntimeError('Stale or mismatched network control ACK')
                    return
                if line.startswith('CONTROL ERROR'):
                    raise RuntimeError(line)
                if not line or len(self.replies) >= 16:
                    raise RuntimeError('Malformed or excessive network control facts')
                self.replies.append(line)
        except BaseException as error:
            self.failure = error
            raise

    def line(self):
        if self.failure is not None:
            raise RuntimeError('network control refused after failed exchange') from self.failure
        if self.replies:
            if time.monotonic() >= min(self.process.deadline,self.fact_deadline):
                self.failure=TimeoutError('Late buffered control fact cannot qualify')
                raise self.failure
            return self.replies.popleft() + '\n'
        line = self.process.line(timeout=3)
        if line.startswith(('SYNC ', 'CONTROL ERROR')):
            raise RuntimeError('Unexpected network control reply')
        return line
