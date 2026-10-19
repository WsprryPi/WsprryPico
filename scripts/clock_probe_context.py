#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only fixture context for an already owned RP1 input measurement.

The caller owns the GPIO request and the canonical device/input locks. This
helper never requests, drives, reconfigures or clears GPIO/power state. Context
is flushed before checks; no unexpected event is discarded or requalified.
"""
import json
import mmap
import os
from pathlib import Path
import re
import struct
import subprocess
import time


def validate_idle(state, baseline):
    if state['levels'] != ['INACTIVE', 'INACTIVE']:
        raise ValueError('Measurement input did not remain idle low')
    for line in ('22', '23'):
        for field in ('ctrl', 'pad'):
            if state['registers'][line][field] != baseline['registers'][line][field]:
                raise ValueError('Measurement input configuration changed')
    if type(state['power_flags']) is not int:
        raise ValueError('Host power receipt is unavailable')
    if state['power_flags'] & 15:
        raise ValueError('Host reports an active power/clock throttle fault')


class InputAudit:
    def __init__(self, directory, request):
        import gpiod
        with gpiod.Chip('/dev/gpiochip0') as chip:
            info = chip.get_info()
            if info.label != 'pinctrl-rp1' or info.num_lines != 54:
                raise ValueError('Context requires the verified RP1 GPIO controller')
        self.request = request
        self.fd = os.open('/dev/gpiomem0', os.O_RDONLY | os.O_CLOEXEC)
        try:
            self.memory = mmap.mmap(self.fd, 0x30000, flags=mmap.MAP_SHARED,
                                    prot=mmap.PROT_READ)
        except BaseException:
            os.close(self.fd)
            raise
        try:
            self.stream = (Path(directory)/'input-context.jsonl').open('x', buffering=1)
        except BaseException:
            self.memory.close()
            os.close(self.fd)
            raise
        self.power_at = -float('inf')
        self.power = None
        self.power_error = None
        self.power_text = None
        try:
            self.baseline = self.record('baseline')
            validate_idle(self.baseline, self.baseline)
        except BaseException:
            self.close()
            raise

    def record(self, kind, **extra):
        if time.monotonic()-self.power_at >= 30:
            self.power = self.power_error = self.power_text = None
            try:
                self.power_text = subprocess.check_output(['vcgencmd', 'get_throttled'],
                                                          text=True, timeout=3).strip()
                match = re.fullmatch(r'throttled=0x([0-9a-fA-F]+)', self.power_text)
                if match:
                    self.power = int(match[1], 16)
                else:
                    self.power_error = 'Unrecognized host power receipt'
            except (OSError, subprocess.SubprocessError) as error:
                self.power_error = repr(error)
            self.power_at = time.monotonic()
        state = {'kind': kind, 'utc_ns': time.time_ns(),
                 'monotonic_ns': time.monotonic_ns(), 'power_flags': self.power,
                 'power_text': self.power_text, 'power_error': self.power_error,
                 'power_read_monotonic_s': self.power_at,
                 'levels': [v.name for v in self.request.get_values([22, 23])],
                 'registers': {str(n): {
                     'ctrl': struct.unpack_from('<I', self.memory, n*8+4)[0],
                     'pad': struct.unpack_from('<I', self.memory, 0x20004+n*4)[0],
                     'status': struct.unpack_from('<I', self.memory, n*8)[0]}
                     for n in (22, 23)}, **extra}
        self.stream.write(json.dumps(state, separators=(',', ':'))+'\n')
        return state

    def idle(self):
        validate_idle(self.record('idle'), self.baseline)

    def close(self):
        try:
            self.stream.close()
        finally:
            try:
                self.memory.close()
            finally:
                os.close(self.fd)
