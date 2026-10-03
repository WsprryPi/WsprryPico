#!/usr/bin/env python3
"""Fresh serial input ordering without opening a device."""
import contextlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_serial_observer as observer


class Tests(unittest.TestCase):
    def test_flush_after_port_lock_before_write_returns_fresh_wire(self):
        queue=bytearray(b'{"stale":true}\n');order=[]
        fresh=b'{"fresh":true}\n'
        @contextlib.contextmanager
        def port(_):
            order.append('DTR-high');yield 42
        def flock(fd,_):order.append('lock-'+str(fd))
        def flush(fd,kind):
            self.assertEqual((fd,kind),(42,observer.termios.TCIFLUSH))
            order.append('flush');queue.clear()
        def write(fd,wire,end):
            self.assertEqual(wire,b'INFO\n');order.append('write');queue.extend(fresh)
        def read(fd,size):
            result=bytes(queue[:size]);del queue[:size];return result
        with (patch.object(observer,'port',port),patch.object(observer.os,'open',return_value=12),
              patch.object(observer.os,'close'),patch.object(observer.fcntl,'flock',flock),
              patch.object(observer.termios,'tcflush',flush),patch.object(observer,'write_all',write),
              patch.object(observer.select,'select',return_value=([42],[],[])),
              patch.object(observer.os,'read',read),patch.object(observer,'resource_health')):
            value,wire=observer.Observer()()
        self.assertEqual(value,{'fresh':True});self.assertEqual(wire,fresh)
        self.assertEqual(order,['lock-12','DTR-high','lock-42','flush','write'])
    def test_flush_failure_never_sends_info_and_releases_action_lock(self):
        @contextlib.contextmanager
        def port(_):yield 42
        with (patch.object(observer,'port',port),patch.object(observer.os,'open',return_value=12),
              patch.object(observer.os,'close') as close,patch.object(observer.fcntl,'flock'),
              patch.object(observer.termios,'tcflush',side_effect=OSError('flush failed')),
              patch.object(observer,'write_all') as write):
            with self.assertRaises(OSError):observer.Observer()()
        write.assert_not_called();close.assert_called_once_with(12)


if __name__=='__main__':unittest.main()
