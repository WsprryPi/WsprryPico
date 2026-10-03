#!/usr/bin/env python3
"""Resource schemas/vectors checked against real hardware-free API responses."""
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_wtp_contract import SchemaValidator, ValidationError, loads_strict

DRIVER = Path(sys.argv.pop(1))
SCHEMA = json.loads((ROOT / "docs/protocol/transmitter-application-1.schema.json").read_text())
VECTORS = json.loads((ROOT / "docs/protocol/transmitter-application-1-vectors.json").read_text())
VALIDATOR = SchemaValidator(SCHEMA)


def run_driver(*args):
    result = subprocess.run([str(DRIVER), *args], check=True, capture_output=True, text=True)
    return loads_strict(result.stdout)


def inventory():
    text = (ROOT / "docs/transmitter-application-contract.md").read_text()
    table = text.split("| Current WsprryPi setting |")[1].split("\nRelated Pi settings")[0]
    return [re.split(r"(?<!\\)\|", line)[1].strip().replace("`", "").replace(r"\|", "|")
            for line in table.splitlines() if line.startswith("| ") and not line.startswith("| ---")]


class ApplicationSchemaTests(unittest.TestCase):
    def test_requests_against_firmware_parser(self):
        names = set()
        for vector in VECTORS["vectors"]:
            with self.subTest(vector=vector["name"]):
                self.assertNotIn(vector["name"], names)
                names.add(vector["name"])
                raw = vector["raw"]
                definition = SCHEMA["$defs"][vector["schema_definition"]]
                try:
                    value = loads_strict(raw)
                    structural = not VALIDATOR.errors(value, definition)
                except ValidationError:
                    structural = False
                structural = structural and len(raw.encode()) <= definition["x-maxWireBytes"]
                self.assertEqual(structural, vector["structural_valid"])
                actual = run_driver("--request", "/api/v1/" + vector["resource"], raw)
                self.assertEqual(actual["status"], vector["http_status"])
                if actual["status"] == 200:
                    errors = VALIDATOR.errors(actual["body"], SCHEMA["$defs"][vector["resource"] + "_read"])
                    self.assertEqual(errors, [])

    def test_emitted_configured_blank_pending_and_unhealthy_resources(self):
        samples = run_driver("--samples")
        for name, value in samples.items():
            with self.subTest(sample=name):
                kind = {"application": "application_read", "station": "station_read",
                        "hardware": "hardware_read", "pending": "hardware_read",
                        "blank": "application_read", "unhealthy": "application_read"}[name]
                definition = SCHEMA["$defs"][kind]
                self.assertEqual(VALIDATOR.errors(value, definition), [])
                self.assertLessEqual(len(json.dumps(value, separators=(",", ":")).encode()),
                                     definition["x-maxWireBytes"])
        self.assertIsNone(samples["blank"]["hardware"]["active"])
        self.assertIsNone(samples["unhealthy"]["station"]["station"])
        self.assertIsNone(samples["unhealthy"]["hardware"]["saved"])
        self.assertTrue(samples["pending"]["pending_restart"])
        self.assertEqual(samples["pending"]["active"]["rf_gp"], 2)
        self.assertEqual(samples["pending"]["saved"]["rf_gp"], 28)

    def test_objects_are_closed_and_inventory_is_complete(self):
        def visit(value):
            if isinstance(value, dict):
                if value.get("type") == "object":
                    self.assertIs(value["additionalProperties"], False)
                    self.assertTrue(value["required"])
                if "$ref" in value:
                    VALIDATOR.resolve(value["$ref"])
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(SCHEMA)
        coverage = json.loads((ROOT / "docs/protocol/transmitter-application-1-coverage.json").read_text())
        self.assertEqual([row["source_setting"] for row in coverage["settings"]], inventory())
        for row in coverage["settings"]:
            self.assertIn(row["disposition"], {"implemented_pico_adapter", "partial_pico_adapter",
                                                "platform_specific", "unavailable"})
            self.assertTrue(row["notes"])
            if row["disposition"] in {"implemented_pico_adapter", "partial_pico_adapter"}:
                self.assertTrue(row["resource_field"])

    def test_emitted_configuration_fault(self):
        value = run_driver("--fault")
        self.assertEqual(VALIDATOR.errors(value, SCHEMA["$defs"]["hardware_read"]), [])
        self.assertEqual(value["application_error"], "output_disable_failed")
        self.assertTrue(value["pending_restart"])
        self.assertEqual(value["saved"]["rf_gp"], 28)
        self.assertEqual(value["active"]["rf_gp"], 2)


if __name__ == "__main__":
    unittest.main()
