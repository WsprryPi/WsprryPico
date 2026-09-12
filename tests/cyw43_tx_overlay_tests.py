#!/usr/bin/env python3
"""Compile the actual pinned send functions against deterministic bus/credit input."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_cyw43_tx_overlay import prepare, transform, SHA256

SOURCE = Path(sys.argv.pop(1)).resolve() if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else None


class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(SOURCE, 'Pass the existing pinned CYW43 driver path')
        self.raw = (SOURCE / 'src/cyw43_ll.c').read_bytes()
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), SHA256)

    def test_original_and_repaired_real_send_functions(self):
        for fixed, text in [(False, self.raw.decode()), (True, transform(self.raw))]:
            with self.subTest(fixed=fixed), tempfile.TemporaryDirectory() as tmp:
                # Exact source bodies, not a reimplementation of the send algorithm.
                core = text[text.index('struct sdpcm_header_t {'):text.index('static int sdpcm_process_rx_packet(')]
                source = Path(tmp) / 'test.c'
                source.write_text(text[:text.index('#include')] +
                    (ROOT / 'tests/cyw43_tx_overlay_harness.c').read_text() + core +
                    (ROOT / 'tests/cyw43_tx_overlay_cases.c').read_text())
                exe = Path(tmp) / 'test'
                subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-function', '-DEXPECT_FIXED=' + str(int(fixed)), str(source), '-o', str(exe)],
                    check=True, timeout=30)
                subprocess.run([str(exe)], check=True, timeout=10)

    def test_changed_source_is_rejected(self):
        with self.assertRaises(ValueError):
            transform(self.raw + b'\n')

    def test_in_sdk_output_is_rejected_before_writing(self):
        with self.assertRaises(ValueError):
            prepare(SOURCE, SOURCE / 'forbidden-overlay')
        self.assertFalse((SOURCE / 'forbidden-overlay').exists())

    def test_symlinked_output_cannot_modify_sdk(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'cyw43_ll.c').symlink_to(SOURCE / 'src/cyw43_ll.c')
            with self.assertRaises(ValueError):
                prepare(SOURCE, Path(tmp))
            self.assertEqual((SOURCE / 'src/cyw43_ll.c').read_bytes(), self.raw)

    def test_output_and_source_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            prepare(SOURCE, Path(tmp))
            self.assertEqual((Path(tmp) / 'cyw43_ll.c').read_text(), transform(self.raw))
            self.assertEqual((SOURCE / 'src/cyw43_ll.c').read_bytes(), self.raw)


if __name__ == '__main__':
    unittest.main()
