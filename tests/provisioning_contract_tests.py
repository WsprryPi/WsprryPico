#!/usr/bin/env python3
"""Guard the checked-in Bluefy and C++ provisioning wire constants."""

from pathlib import Path
import re


repo = Path(__file__).resolve().parents[1]
web = (repo / "src/provisioning/web/bluefy.js").read_text()
command_header = (repo / "src/provisioning/command.hpp").read_text()
command_source = (repo / "src/provisioning/command.cpp").read_text()
profile_header = (repo / "src/provisioning/profile.hpp").read_text()

assert "const MAX_PROFILE_BYTES = 7168;" in web
assert "max_profile_bytes = 7168;" in profile_header
assert "const FRAGMENT_BYTES = 64;" in web
assert "max_fragment_bytes = 64;" in command_header
assert "const MAX_COMMAND_BYTES = 512;" in web
assert "max_command_bytes = 512;" in command_header
assert "const MAX_STATUS_BYTES = 256;" in web
assert "max_notification_bytes = 256;" in command_header
assert "framing" in web and "reassembly in both directions" in web
assert "max_wire_integer = 2147483647;" in command_header

for name, value in {
    "service": "7d6b0001-5bf1-4f21-a486-3e8f70c12201",
    "identity": "7d6b0002-5bf1-4f21-a486-3e8f70c12201",
    "command": "7d6b0003-5bf1-4f21-a486-3e8f70c12201",
    "status": "7d6b0004-5bf1-4f21-a486-3e8f70c12201",
}.items():
    assert re.search(rf"{name}: \"{re.escape(value)}\"", web)

for operation in ("open", "write", "apply", "cancel"):
    assert f'operation: "{operation}"' in web
    assert f'operation == "{operation}"' in command_source

for field in (
    "version",
    "operation",
    "request_id",
    "session_id",
    "device_id",
    "offset",
    "final",
    "payload",
    "expected_generation",
):
    assert f'"{field}"' in command_source
    assert re.search(rf"\b{field}\b", web)

print("Bluefy/C++ provisioning wire contract is synchronized")
