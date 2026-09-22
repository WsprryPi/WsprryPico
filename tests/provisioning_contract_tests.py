#!/usr/bin/env python3
"""Guard the checked-in Bluefy and C++ provisioning wire constants."""

from pathlib import Path
import re


repo = Path(__file__).resolve().parents[1]
web = (repo / "src/provisioning/web/bluefy.js").read_text()
command_header = (repo / "src/provisioning/command.hpp").read_text()
command_source = (repo / "src/provisioning/command.cpp").read_text()
ble_session = (repo / "src/provisioning/ble_session.cpp").read_text()
profile_header = (repo / "src/provisioning/profile.hpp").read_text()
gatt = (repo / "src/provisioning/pico/gatt_transport.cpp").read_text()
gatt_profile = (repo / "src/provisioning/pico/field_access.gatt").read_text()

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
    "wtpCommand": "7d6b0005-5bf1-4f21-a486-3e8f70c12201",
    "wtpStatus": "7d6b0006-5bf1-4f21-a486-3e8f70c12201",
}.items():
    assert re.search(rf"{name}: \"{re.escape(value)}\"", web)

for operation in ("open", "write", "apply", "cancel"):
    assert f'operation: "{operation}"' in web
    assert f'operation == "{operation}"' in command_source

for operation in ("identify", "field_status", "time_challenge", "time_submit"):
    assert f'operation: "{operation}"' in web
    assert f'name == "{operation}"' in ble_session

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

assert "INDICATE | ENCRYPTION_KEY_SIZE_16 | DYNAMIC" in gatt_profile
assert "WRITE | ENCRYPTION_KEY_SIZE_16 | DYNAMIC" in gatt_profile
assert "7D6B0005-5BF1-4F21-A486-3E8F70C12201" in gatt_profile
assert "7D6B0006-5BF1-4F21-A486-3E8F70C12201" in gatt_profile
assert "CLIENT_CONFIGURATION_HANDLE" in gatt
assert "att_read_callback_handle_little_endian_16" in gatt
assert "owner_->status_cccd_ : owner_->wtp_cccd_) = value;" in gatt
assert "status_cccd_ != GATT_CLIENT_CHARACTERISTICS_CONFIGURATION_INDICATION" in gatt
assert "wtp_cccd_ != GATT_CLIENT_CHARACTERISTICS_CONFIGURATION_INDICATION" in gatt
assert "endpoint_->receive" in gatt and "endpoint_->consume_output" in gatt
assert gatt.index("if (owner_->status_cccd_ != GATT_CLIENT_CHARACTERISTICS_CONFIGURATION_INDICATION)") < gatt.index("owner_->inbound_.receive")
assert "if (session_.authorized())\n            endpoint_->poll(current);" in gatt
assert "owner_->endpoint_ && !owner_->endpoint_->closed()" in gatt
assert "if (indication_ == Indication::Wtp)\n        return false;" in gatt
assert "owner_->security_lost();" in gatt
security_failure = gatt.index("owner_->security_lost();")
security_disconnect = gatt.index("(void)gap_disconnect(owner_->connection_);")
assert security_failure < security_disconnect
security_lost = gatt[gatt.index("void PicoGattTransport::security_lost()"):
                     gatt.index("bool PicoGattTransport::queue")]
for required in ("session_.disconnected()", "endpoint_->disconnect()", "outbound_.clear()",
                 "status_cccd_ = 0", "wtp_cccd_ = 0", "indication_ = Indication::None"):
    assert required in security_lost

print("Bluefy/C++ provisioning wire contract is synchronized")
