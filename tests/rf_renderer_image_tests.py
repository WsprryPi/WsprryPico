#!/usr/bin/env python3
"""Reject linked placement regressions without target execution."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_rf_renderer import validate

SYMBOLS = """20001200 00000008 T wsprrypico::rf::Waveform::render(std::span<unsigned long, 4294967295u>)
20010000 00029000 b wsprrypico::rf::start_worker(wsprrypico::time::UtcDiscipline&)::engine
"""
SECTIONS = " 10 .data 00003000 20000120 100f5000 000f7120 2**3"
CODE = """20001200: b510\tpush {r4, lr}
20001202: 2000\tmovs r0, #0
20001204: e7ff\tb.n 20001206 <render+0x6>
20001206: bd10\tpop {r4, pc}
"""


class RendererImageTests(unittest.TestCase):
    def test_ram_and_explicit_flash_control(self):
        self.assertEqual(validate(SYMBOLS, CODE, SECTIONS, "ram")["bytes"], 8)
        flash = SYMBOLS.replace("20001200", "10001200")
        self.assertEqual(validate(flash, "", "", "flash")["placement"], "flash")
        with self.assertRaises(ValueError):
            validate(SYMBOLS, CODE, SECTIONS, "flash")

    def test_rejects_calls_veneers_literals_computed_addresses_and_jumps(self):
        for bad in ("bl 10000100 <memset>", "bl 20002000 <veneer>",
                    "b.w 10000100 <tailcall>", "bx r3", "ldr r0, [pc, #4]",
                    "movt r0, #4096", ".word 0x10000100", "tbb [r0, r1]"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate(SYMBOLS, CODE.replace("movs r0, #0", bad), SECTIONS, "ram")

    def test_rejects_missing_or_wrong_placement_and_copy_image(self):
        for symbols, sections, code in (
                ("", SECTIONS, CODE),
                (SYMBOLS + SYMBOLS, SECTIONS, CODE),
                (SYMBOLS.replace("20001200", "10001200"), SECTIONS, CODE),
                (SYMBOLS.replace("20010000", "10010000"), SECTIONS, CODE),
                (SYMBOLS, SECTIONS.replace("100f5000", "200f5000"), CODE),
                (SYMBOLS, SECTIONS.replace("00003000", "00000004"), CODE),
                (SYMBOLS, SECTIONS, ""),
                (SYMBOLS, SECTIONS, CODE.replace("20001202: 2000\tmovs r0, #0\n", "")),
                (SYMBOLS, SECTIONS, CODE.replace("bd10", "e8bd 8010"))):
            with self.assertRaises(ValueError):
                validate(symbols, code, sections, "ram")


if __name__ == "__main__":
    unittest.main()
