#!/usr/bin/env python3
"""Probe control-flow tests with fully mocked device I/O."""
import contextlib
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import wtp_probe
from validate_wtp_contract import frame, load_json
from wtp_monitor import FrameDecoder

# The opt-in flag is checked before any device open.
with patch.object(sys, "argv", ["wtp_probe", "/not-a-device"]), patch.object(wtp_probe.os, "open") as opening:
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            wtp_probe.main()
            raise AssertionError("missing opt-in accepted")
        except SystemExit as error:
            assert error.code == 2
    opening.assert_not_called()

with patch.object(sys,"argv",["wtp_probe","/not-a-device","--run"]), patch.object(wtp_probe.os,"open") as opening:
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            wtp_probe.main()
            raise AssertionError("retired probe accepted")
        except SystemExit as error:
            assert error.code == 2
    opening.assert_not_called()
print("Retired probe refuses before device I/O with and without former opt-in")
