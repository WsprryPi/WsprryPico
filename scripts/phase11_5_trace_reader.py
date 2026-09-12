"""Bounded, diagnostic-only NETTRACE reads on an already exclusive Console FD.

The caller owns endpoint authorization, lifecycle and INFO scheduling. This
reader limits new page starts to 50 ms per drain; an in-flight exchange retains
its five-second deadline and must complete or fail before another command.
Additional trace traffic is not the frozen nominal acceptance workload.
"""
import time

from phase11_5_inventory import exchange, require


class TraceReader:
    def __init__(self, device, boot, revision, emit, *, clock=time.monotonic, transfer=exchange):
        self.device, self.boot, self.revision = device, boot, revision
        self.emit, self.clock, self.transfer = emit, clock, transfer
        self.cursor = 0

    def drain(self, fd):
        deadline = self.clock() + 0.050
        for _ in range(16):
            now = self.clock()
            if now >= deadline:
                return
            reply = self.transfer(fd, ('NETTRACE '+str(self.cursor)+'\n').encode(),
                                  now+5, self.emit, False)
            self.emit('NETTRACE', reply)
            require(reply.get('ok') is True and reply.get('device_id') == self.device and
                    reply.get('boot_id') == self.boot and reply.get('revision') == self.revision,
                    'NETTRACE identity changed')
            trace = reply['trace']
            require(trace['intact'] is True and trace['install_errors'] == 0,
                    'NETTRACE hooks invalid')
            require(type(trace['latest']) is int and trace['latest'] >= self.cursor and
                    trace['oldest'] == max(1, trace['latest']-255) and
                    len(trace['events']) <= 8, 'NETTRACE ring metadata invalid')
            cursor = self.cursor
            for event in trace['events']:
                require(type(event['seq']) is int and
                        trace['oldest'] <= event['seq'] <= trace['latest'] and
                        event['seq'] == (cursor+1 if cursor else trace['oldest']),
                        'NETTRACE overwritten or gap')
                cursor = event['seq']
            require(cursor == trace['latest'] or cursor > self.cursor, 'NETTRACE made no progress')
            self.cursor = cursor
            if cursor == trace['latest']:
                return
        # A backlog resumes after the next INFO sample; a ring gap fails there.
