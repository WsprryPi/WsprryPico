#!/usr/bin/env python3
"""Bounded B-only real-byte serial observer for a parent-owned campaign."""
import fcntl
import os
import select
import threading
import termios
import time
from check_usb_target import port
from phase12_recovery_device import CONSOLE,SERIAL,strict,resource_health,require
from rf_wtp import write_all


class Observer:
    def __init__(self):self.mutex=threading.RLock()
    def __call__(self):
        with self.mutex:
            action=os.open('/home/pi/.wsprrypico-recovery-action-'+SERIAL+'.lock',
                           os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
            try:
                end=time.monotonic()+5
                while True:
                    try:fcntl.flock(action,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                    except BlockingIOError:
                        require(time.monotonic()<end,'serial action lock deadline');time.sleep(.02)
                with port(CONSOLE) as fd:
                    fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    termios.tcflush(fd, termios.TCIFLUSH)
                    end=time.monotonic()+5;write_all(fd,b'INFO\n',end);wire=bytearray()
                    while time.monotonic()<end:
                        if select.select([fd],[],[],max(0,end-time.monotonic()))[0]:
                            chunk=os.read(fd,1);require(chunk,'console closed');wire.extend(chunk)
                            require(len(wire)<=16384,'INFO line bound')
                            if chunk==b'\n':
                                if wire.strip():
                                    info=strict(bytes(wire));resource_health(info);return info,bytes(wire)
                                wire.clear()
                    raise TimeoutError('actual INFO deadline')
            finally:os.close(action)
