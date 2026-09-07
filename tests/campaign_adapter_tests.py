#!/usr/bin/env python3
"""GPSDO adapter tests use recorded-shaped status responses, never devices."""

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from campaign.live import Rig, FixtureError


class AdapterTests(unittest.TestCase):
    def rig(self, channel, state):
        rig = Rig.__new__(Rig)
        rig.args = SimpleNamespace(gpsdo_output=channel, gpsdo_serial="test")
        rig.commands = []

        def remote(argv, timeout):
            rig.commands.append(argv)
            return json.dumps(state)

        rig.remote = remote
        return rig

    def state(self, **changes):
        return dict(
            serial="test",
            out1=False,
            out2=False,
            pps1=False,
            f1=137500,
            f2=137500,
            sat_lock=True,
            pll_lock=True,
            ant_ok=True,
            **changes,
        )

    def test_failed_receiver_retains_cleanup_ownership(self):
        import io
        import time

        rig = Rig.__new__(Rig)
        receiver = SimpleNamespace(wait=lambda timeout: 1)
        rig.capture = receiver
        rig.capture_log = io.StringIO()
        rig.capture_deadline = time.monotonic() + 1
        rig.idle = lambda: {"output_active": False}
        rig.gps = lambda operation: {}
        rig.remote_dir = "/unused-test-path"
        rig.remote = lambda argv: json.dumps({"cleanup": {"outcome": "unverified"}})
        rig.event = lambda *args, **kwargs: None
        with self.assertRaises(FixtureError):
            rig.finish_capture()
        self.assertIs(rig.capture, receiver)
        self.assertIn("receiver exit or cleanup metadata failed", rig.cleanup())

    def test_channels_are_zero_based_in_library(self):
        for channel in (1, 2):
            state = self.state()
            state[f"out{channel}"] = True
            rig = self.rig(channel, state)
            rig.gps("on", 137500)
            self.assertEqual(rig.commands[0][:3], ["timeout", "--kill-after=2s", "40s"])
            code = rig.commands[0][-1]
            self.assertIn(f"d.set_freq({channel - 1},137500,False)", code)
            self.assertIn(f"d.set_level({channel - 1},True)", code)
            self.assertIn("d.set_pps(False)", code)
            self.assertLess(
                code.index("d.enable(False,False)"), code.index("d.set_freq(")
            )

    def test_pps_is_not_silence(self):
        state = self.state()
        state["pps1"] = True
        with self.assertRaises(FixtureError):
            self.rig(1, state).gps("read")

    def test_lock_loss_or_wrong_output_prevents_reference_use(self):
        for field, value in [
            ("sat_lock", False),
            ("pll_lock", False),
            ("f1", 999),
            ("out2", True),
        ]:
            state = self.state()
            state["out1"] = True
            state[field] = value
            with self.assertRaises(FixtureError):
                self.rig(1, state).gps("active", 137500)


if __name__ == "__main__":
    unittest.main()
