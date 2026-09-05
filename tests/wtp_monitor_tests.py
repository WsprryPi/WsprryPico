#!/usr/bin/env python3
"""Hardware-free tests for the WTP serial monitor decoder."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_wtp_contract import frame  # noqa: E402
from wtp_monitor import FrameDecoder  # noqa: E402


class FrameDecoderTests(unittest.TestCase):
    def test_fragmented_and_combined_frames(self) -> None:
        first = frame(b'{"one":1}')
        second = frame(b'{"two":2}')
        decoder = FrameDecoder()
        self.assertEqual(decoder.feed(first[:7]), [])
        self.assertEqual(decoder.feed(first[7:] + second), [b'{"one":1}', b'{"two":2}'])

    def test_crc_failure_is_discarded(self) -> None:
        invalid = bytearray(frame(b"{}"))
        invalid[-1] ^= 1
        decoder = FrameDecoder()
        self.assertEqual(decoder.feed(bytes(invalid) + frame(b'{"ok":true}')), [b'{"ok":true}'])

    def test_invalid_header_resynchronizes(self) -> None:
        invalid = bytearray(frame(b"{}"))
        invalid[4] = 2
        decoder = FrameDecoder()
        self.assertEqual(decoder.feed(b"noise" + bytes(invalid) + frame(b"{}")), [b"{}"])


if __name__ == "__main__":
    unittest.main()
