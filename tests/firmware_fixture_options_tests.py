"""Old diagnostic selections must fail before selecting ordinary firmware."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = {
    'WSPRRY_PICO_PHASE12_FAULT_STAGE': ('WSPRRY_PICO_JOURNAL_FAULT_STAGE', '9'),
    'WSPRRY_PICO_PHASE12_INDICATOR_FAULT_FIXTURE': ('WSPRRY_PICO_INDICATOR_FAULT_FIXTURE', 'ON'),
    'WSPRRY_PICO_PHASE12_PHYSICAL_CUT_FIXTURE': ('WSPRRY_PICO_JOURNAL_POWER_CUT_FIXTURE', 'ON'),
    'WSPRRY_PICO_PHASE12_SESSION_DEADLINE_FIXTURE': ('WSPRRY_PICO_SESSION_DEADLINE_FIXTURE', 'ON'),
}


class FixtureOptionTests(unittest.TestCase):
    def check_options(self, values):
        with tempfile.TemporaryDirectory(prefix='firmware-fixture-options-') as directory:
            script = Path(directory) / 'check.cmake'
            script.write_text('cmake_minimum_required(VERSION 3.24)\ninclude("' +
                              (ROOT / 'cmake/legacy_firmware_fixture_options.cmake').as_posix() +
                              '")\nmessage(STATUS "fixture selection allowed")\n')
            return subprocess.run(['cmake', *(f'-D{k}={v}' for k, v in values.items()),
                                   '-P', str(script)], capture_output=True, text=True, timeout=10)

    def test_active_obsolete_controls_are_rejected_with_replacement(self):
        for old, (current, value) in CONTROLS.items():
            with self.subTest(option=old):
                result = self.check_options({old: value})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(old, result.stderr)
                self.assertIn(current, result.stderr)
                self.assertNotIn('fixture selection allowed', result.stdout)

    def test_matching_new_selection_does_not_hide_an_active_old_control(self):
        for old, (current, value) in CONTROLS.items():
            with self.subTest(option=old):
                self.assertNotEqual(self.check_options({old: value, current: value}).returncode, 0)

    def test_existing_disabled_defaults_and_current_controls_are_allowed(self):
        disabled = {old: ('0' if old.endswith('_STAGE') else 'OFF') for old in CONTROLS}
        for values in ({}, disabled,
                       {current: value for current, value in CONTROLS.values()}):
            with self.subTest(options=values):
                result = self.check_options(values)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('fixture selection allowed', result.stdout)


if __name__ == '__main__':
    unittest.main()
