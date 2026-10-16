#!/usr/bin/env python3
"""Validate actual version-2 resource output against its closed wire schema."""
import copy
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_wtp_contract import SchemaValidator

schema = json.loads((ROOT / "docs/protocol/transmitter-application-2.schema.json").read_text())
validator = SchemaValidator(schema)
samples = json.loads(subprocess.check_output([sys.argv[1], "--samples"], text=True))
for name, sample in samples.items():
    errors = validator.errors(sample, schema["$defs"]["application_read"])
    assert not errors, (name, errors)
    assert len(json.dumps(sample, separators=(",", ":")).encode()) <= 4096
    for field, value in [("schema", "transmitter-application/99"), ("unknown", True)]:
        bad = copy.deepcopy(sample)
        bad[field] = value
        assert validator.errors(bad, schema["$defs"]["application_read"])
    bad = copy.deepcopy(sample)
    bad["wspr_plan"]["frame_types"] = ["type99"]
    assert validator.errors(bad, schema["$defs"]["application_read"])
print(f"Closed version-2 schemas validate {len(samples)} actual persisted application responses")
