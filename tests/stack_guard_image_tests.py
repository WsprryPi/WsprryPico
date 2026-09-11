#!/usr/bin/env python3
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_stack_guards import validate

BASE = '''10000100 <runtime_init>:
10000100: f000 f880 bl 10000200 <runtime_init_per_core_install_stack_guard>
10000200 <runtime_init_per_core_install_stack_guard>:
10000200: f380 880a msr MSPLIM, r0
10000204: f3bf 8f6f isb sy
10000300 <wsprry_stack_guard_snapshot>:
10000300: f3ef 800a mrs r0, MSPLIM
10000304: f3ef 8108 mrs r1, MSP
10000308: f3ef 8214 mrs r2, CONTROL
'''
CORE1 = '''10000400 <core1_wrapper>:
10000400: f7ff ff00 bl 10000200 <runtime_init_per_core_install_stack_guard>
'''


class GuardImageTests(unittest.TestCase):
    def test_both_startup_shapes(self):
        self.assertEqual(validate(BASE, False)['startup_callers'], ['runtime_init'])
        self.assertEqual(validate(BASE + CORE1, True)['startup_callers'], ['core1_wrapper', 'runtime_init'])

    def test_missing_worker_guard(self):
        with self.assertRaisesRegex(ValueError, 'startup'):
            validate(BASE, True)

    def test_missing_register_readbacks(self):
        for register in ('MSPLIM', 'MSP', 'CONTROL'):
            broken = '\n'.join(line for line in (BASE + CORE1).splitlines()
                               if not ('mrs ' in line and line.endswith(', ' + register)))
            with self.subTest(register=register), self.assertRaisesRegex(ValueError, 'readback'):
                validate(broken, True)

    def test_foreground_can_neither_install_nor_disable_guard(self):
        for operation in ('bl 10000200 <runtime_init_per_core_install_stack_guard>', 'msr MSPLIM, r0'):
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                validate(BASE + CORE1 + '10000500 <foreground>:\n10000500: f000 8800 ' + operation, True)

    def test_missing_write_or_barrier(self):
        for fragment in ('msr MSPLIM, r0', 'isb sy'):
            with self.subTest(fragment=fragment), self.assertRaises(ValueError):
                validate((BASE + CORE1).replace(fragment, 'nop'), True)


if __name__ == '__main__':
    unittest.main()
