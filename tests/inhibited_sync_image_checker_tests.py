import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_inhibited_sync_image import check


class SyncImageTests(unittest.TestCase):
    def test_event_drain_is_inside_irq_critical_section(self):
        good = """20000120 <sem_acquire_block_until>:
20000130: b672 cpsid i
20000134: e8c3 8f8f stlb r8, [r3]
20000138: bf20 wfe
2000013a: f38c 8810 msr PRIMASK, ip
2000013e: f002 fbd1 bl 20002918 <__best_effort_wfe_or_timeout_veneer>
20000142: 4770 bx lr
"""
        check(good)
        for bad in (good.replace('bf20 wfe', 'bf30 wfi'),
                    good.replace('bf20 wfe', 'bf00 nop'),
                    good.replace('b672 cpsid i', 'b662 cpsie i'),
                    good.replace('stlb r8, [r3]', 'strb r8, [r3]'),
                    good.replace('msr PRIMASK, ip', 'msr CONTROL, ip'),
                    good.replace('best_effort_wfe_or_timeout', 'different_helper'),
                    good.replace('sem_acquire_block_until', 'different_function'),
                    good.replace('20000138: bf20 wfe',
                                 '20000136: f38c 8810 msr PRIMASK, ip\n20000138: bf20 wfe'),
                    '20000120 <sem_acquire_block_until>:\n'):
            with self.subTest(disassembly=bad), self.assertRaises(ValueError):
                check(bad)


if __name__ == '__main__':
    unittest.main()
