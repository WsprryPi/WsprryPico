import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from console_io import loads_console, exchange
from validate_wtp_contract import frame


class InventoryTests(unittest.TestCase):
    def test_console_native_integer_boundaries(self):
        for value in (2844794185, 2**32-1, 2**64-1, -(2**63)):
            self.assertEqual(loads_console('{"value":'+str(value)+'}'), {'value': value})
        for value in (2**64, -(2**63)-1):
            with self.assertRaisesRegex(ValueError, '64-bit range'):
                loads_console(str(value))

    def test_console_retains_json_integrity_checks(self):
        for source in ('{"hash":0,"hash":1}', 'NaN', 'Infinity', '1.0', '1e2',
                       '"\\ud800"', '['*17+'0'+']'*17):
            with self.subTest(source=source), self.assertRaises(ValueError):
                loads_console(source)

    def test_exchange_separates_console_and_wtp_integer_rules(self):
        # Exact unsigned hash that stopped N1w before its production load began.
        payload = b'{"hash":2844794185}'
        def receive(framed):
            wire = frame(payload) if framed else payload+b'\n'
            with patch('console_io.select.select', return_value=([7], [7], [])), \
                 patch('console_io.os.write', side_effect=lambda fd, data: len(data)), \
                 patch('console_io.os.read', return_value=wire), \
                 patch('console_io.time.monotonic', return_value=0):
                return exchange(7, b'request', 1, lambda *args: None, framed)
        self.assertEqual(receive(False), {'hash':2844794185})
        with self.assertRaisesRegex(ValueError, 'Console-only exchange'):
            receive(True)

    def test_exchange_preserves_stale_console_reply_and_uses_latest(self):
        wire = b'{"value":1}\n{"value":2}\n'
        events = []
        with patch('console_io.select.select', return_value=([7], [7], [])), \
             patch('console_io.os.write', side_effect=lambda fd, data: len(data)), \
             patch('console_io.os.read', return_value=wire), \
             patch('console_io.time.monotonic', return_value=0):
            value = exchange(7, b'INFO\n', 1,
                             lambda kind, body: events.append((kind, body)), False)
        self.assertEqual(value, {'value': 2})
        self.assertEqual(events[-1][0], 'stale_console_reply')

    def test_retired_framing_refused_before_io(self):
        with patch('console_io.os.write') as write, patch('console_io.select.select') as select:
            with self.assertRaisesRegex(ValueError,'Console-only exchange'):
                exchange(7,b'WTPF',1,lambda *args:None,True)
            write.assert_not_called();select.assert_not_called()

if __name__=='__main__':unittest.main()
