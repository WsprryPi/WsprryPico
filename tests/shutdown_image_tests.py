#!/usr/bin/env python3
"""The image gate must inspect call sites, not only wrapper symbol presence."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from check_shutdown_image import CALLS, validate

class ImageTests(unittest.TestCase):
    def test_call_interception(self):
        text=''.join('1000 <'+caller+'>:\n'+''.join(' 1000: f000 bl 2000 <__wrap_'+op+'>\n' for op in ops)
                     for caller,ops in CALLS.items())
        self.assertEqual(validate(text),CALLS)
        for ops in CALLS.values():
            for op in ops:
                with self.subTest(op=op),self.assertRaises(ValueError):
                    validate(text.replace('<__wrap_'+op+'>','<'+op+'>'))
    def test_symbols_alone_refused(self):
        text=''.join('1000 <__wrap_'+op+'>:\n 1000: 4770 bx lr\n' for ops in CALLS.values() for op in ops)
        with self.assertRaises(ValueError):validate(text)
if __name__=='__main__':unittest.main()
