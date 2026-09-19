#!/usr/bin/env python3

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import phase11_6_browser_repair_requal as requal  # noqa: E402


class Phase116BrowserRepairRequalTests(unittest.TestCase):
    def test_mutation_window_requires_ordered_markers(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "browser.jsonl"
            path.write_text("\n".join((
                json.dumps({"kind": "submission_begin", "monotonic_ns": 10}),
                json.dumps({"kind": "mutations_complete", "monotonic_ns": 20}),
            )) + "\n")
            self.assertEqual(requal.journal_window(path), (10, 20))
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            rows[1]["monotonic_ns"] = 9
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
            with self.assertRaisesRegex(ValueError, "timing window"):
                requal.journal_window(path)

    def test_browser_command_is_raw_abort_and_bound_to_boot(self):
        command = requal.browser_command(Path("/private/requal"), {})
        self.assertIn("raw", command)
        self.assertIn("--abort-after-mutations", command)
        self.assertIn(requal.BOOT, command)
        self.assertEqual(command[-1], "--run")


if __name__ == "__main__":
    unittest.main()
