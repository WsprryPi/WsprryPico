#!/usr/bin/env python3
"""Guard the checked-in Bluefy and C++ provisioning wire constants."""

from pathlib import Path
import re


repo = Path(__file__).resolve().parents[1]
web = (repo / "src/provisioning/web/bluefy.js").read_text()
linux_client = (repo / "scripts/wsprrypico_ble.py").read_text()
command_header = (repo / "src/provisioning/command.hpp").read_text()
command_source = (repo / "src/provisioning/command.cpp").read_text()
ble_session = (repo / "src/provisioning/ble_session.cpp").read_text()
profile_header = (repo / "src/provisioning/profile.hpp").read_text()
gatt = (repo / "src/provisioning/pico/gatt_transport.cpp").read_text()
gatt_profile = (repo / "src/provisioning/pico/field_access.gatt").read_text()

assert "const MAX_PROFILE_BYTES = 7168;" in web
assert "MAX_PROFILE_BYTES = 7168" in linux_client
assert "max_profile_bytes = 7168;" in profile_header
assert "const FRAGMENT_BYTES = 64;" in web
assert "FRAGMENT_BYTES = 64" in linux_client
assert "max_fragment_bytes = 64;" in command_header
assert "const MAX_COMMAND_BYTES = 512;" in web
assert "MAX_COMMAND_BYTES = 512" in linux_client
assert "max_command_bytes = 512;" in command_header
assert "const MAX_STATUS_BYTES = 256;" in web
assert "MAX_STATUS_BYTES = 256" in linux_client
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
    assert re.search(rf'\"{name}\": \"{re.escape(value)}\"', linux_client)

for operation in ("open", "write", "apply", "cancel"):
    assert f'operation: "{operation}"' in web
    assert f'operation == "{operation}"' in command_source
    assert f'"{operation}"' in linux_client

for operation in ("identify", "field_status", "time_challenge", "time_submit"):
    assert f'operation: "{operation}"' in web
    assert f'name == "{operation}"' in ble_session
    assert f'"{operation}"' in linux_client

assert 'operation: "select_wtp_status_carrier"' in web
assert 'name == "select_wtp_status_carrier"' in ble_session
assert '"select_wtp_status_carrier"' not in linux_client

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
    assert re.search(rf"\b{field}\b", linux_client)

for required in (
    '"HELLO"',
    '"STATUS"',
    '"WTP/1"',
    '"NoInputNoOutput"',
    '"profile_permissions"',
    'getpass.getpass',
):
    assert required in linux_client
assert '"Trusted"' not in linux_client
assert "expected_device_path = self.device_path" in linux_client
assert linux_client.count("pairing_request_allowed(str(device), expected_device_path") == 2
assert "bus_name=self.BLUEZ" in linux_client

assert "INDICATE | ENCRYPTION_KEY_SIZE_16 | DYNAMIC" in gatt_profile
assert "WRITE | WRITE_WITHOUT_RESPONSE | ENCRYPTION_KEY_SIZE_16 | DYNAMIC" in gatt_profile
assert "7D6B0005-5BF1-4F21-A486-3E8F70C12201" in gatt_profile
assert "7D6B0006-5BF1-4F21-A486-3E8F70C12201" in gatt_profile
assert "CLIENT_CONFIGURATION_HANDLE" in gatt
assert "att_read_callback_handle_little_endian_16" in gatt
assert "outbound_index_ + 1 == outbound_.size()" in gatt
assert "session_.response_started(now());" in gatt
assert '"request" if response else "command"' in linux_client
assert "owner_->status_cccd_ : owner_->wtp_cccd_) = value;" in gatt
assert "status_cccd_ != GATT_CLIENT_CHARACTERISTICS_CONFIGURATION_INDICATION" in gatt
assert "wtp_indications_enabled()" in gatt
assert "session_.wtp_over_field_status() ? status_cccd_ : wtp_cccd_" in gatt
assert "handle = wtp_status_handle();" in gatt
assert "if (wtp_carrier_changed)" in gatt
assert "owner_->session_.disconnected();" in gatt
assert "endpoint_->receive" in gatt and "endpoint_->consume_output" in gatt
assert gatt.index("if (owner_->status_cccd_ != GATT_CLIENT_CHARACTERISTICS_CONFIGURATION_INDICATION)") < gatt.index("owner_->inbound_.receive")
assert "if (session_.authorized())\n            endpoint_->poll(current);" in gatt
assert "owner_->endpoint_ && !owner_->endpoint_->closed()" in gatt
assert "if (indication_ == Indication::Wtp)\n        return false;" in gatt
assert "owner_->security_lost();" in gatt
security_callback = gatt[gatt.index("case HCI_EVENT_ENCRYPTION_CHANGE:"):
                         gatt.index("case SM_EVENT_JUST_WORKS_REQUEST:")]
security_failure = security_callback.index("owner_->security_lost();")
security_disconnect = security_callback.index("(void)gap_disconnect(owner_->connection_);")
assert security_failure < security_disconnect
security_lost = gatt[gatt.index("void PicoGattTransport::security_lost()"):
                     gatt.index("bool PicoGattTransport::queue")]
for required in ("session_.disconnected()", "endpoint_->disconnect()", "outbound_.clear()",
                 "status_cccd_ = 0", "wtp_cccd_ = 0", "indication_ = Indication::None"):
    assert required in security_lost

print("Bluefy/C++ provisioning wire contract is synchronized")
