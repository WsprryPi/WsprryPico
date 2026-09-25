#!/usr/bin/env python3
"""Guard the frozen Field-GATT/1 contract across maintained implementations."""

import json
from pathlib import Path
import re


repo = Path(__file__).resolve().parents[1]
web = (repo / "src/provisioning/web/bluefy.js").read_text()
published_web = (repo / "docs/bluefy/bluefy.js").read_text()
linux_client = (repo / "scripts/wsprrypico_ble.py").read_text()
command_header = (repo / "src/provisioning/command.hpp").read_text()
command_source = (repo / "src/provisioning/command.cpp").read_text()
ble_session = (repo / "src/provisioning/ble_session.cpp").read_text()
manager_header = (repo / "src/provisioning/manager.hpp").read_text()
local_access = (repo / "src/provisioning/local_access.cpp").read_text()
profile_header = (repo / "src/provisioning/profile.hpp").read_text()
gatt = (repo / "src/provisioning/pico/gatt_transport.cpp").read_text()
gatt_profile = (repo / "src/provisioning/pico/field_access.gatt").read_text()
contract = (repo / "docs/protocol/Field-GATT.md").read_text()
vectors = json.loads((repo / "docs/protocol/Field-GATT-v1-vectors.json").read_text())

assert vectors["protocol"] == "Field-GATT/1"
assert vectors["wire_version"] == 1
assert vectors["status"] == "frozen"
limits = vectors["limits"]
assert limits == {
    "max_command_bytes": 512,
    "max_status_bytes": 256,
    "max_profile_bytes": 7168,
    "max_fragment_bytes": 64,
    "max_profile_fragments": 7168,
    "profile_session_timeout_ms": 30000,
    "profile_confirmation_timeout_ms": 25000,
    "enrollment_window_ms": 120000,
}
assert vectors["profile_transfer_cases"] == [
    {"bytes": 4096, "result": "accepted"},
    {"bytes": 4097, "result": "accepted"},
    {"bytes": 7168, "result": "accepted"},
    {"bytes": 7169, "result": "oversize"},
]
assert vectors["profile_apply"]["required_order"] == [
    "open",
    "write",
    "profile_step_up",
    "apply",
]
assert vectors["profile_apply"]["apply_reuses_bound_request_id"] is True
assert vectors["profile_apply"]["direct_apply_rejected"] == "authentication_required"
assert vectors["provisional_bond_expiry"] == {
    "erase_bond": True,
    "invalidate_application_session": True,
    "disconnect_link": True,
    "retained_bond_unchanged": True,
    "erase_failure": "fail_closed",
}

assert web == published_web
assert f'const MAX_PROFILE_BYTES = {limits["max_profile_bytes"]};' in web
assert f'MAX_PROFILE_BYTES = {limits["max_profile_bytes"]}' in linux_client
assert f'max_profile_bytes = {limits["max_profile_bytes"]};' in profile_header
assert f'const FRAGMENT_BYTES = {limits["max_fragment_bytes"]};' in web
assert f'FRAGMENT_BYTES = {limits["max_fragment_bytes"]}' in linux_client
assert f'max_fragment_bytes = {limits["max_fragment_bytes"]};' in command_header
assert "fragment_capacity = max_profile_bytes;" in manager_header
assert f'const MAX_COMMAND_BYTES = {limits["max_command_bytes"]};' in web
assert f'MAX_COMMAND_BYTES = {limits["max_command_bytes"]}' in linux_client
assert f'max_command_bytes = {limits["max_command_bytes"]};' in command_header
assert f'const MAX_STATUS_BYTES = {limits["max_status_bytes"]};' in web
assert f'MAX_STATUS_BYTES = {limits["max_status_bytes"]}' in linux_client
assert f'max_notification_bytes = {limits["max_status_bytes"]};' in command_header
assert "PROFILE_CONFIRMATION_TIMEOUT_SECONDS = 25.0" in linux_client
assert "this.confirmationTimeoutMs = options && options.confirmationTimeoutMs" in web
assert ": 25000;" in web
assert "framing" in web and "reassembly in both directions" in web
assert "max_wire_integer = 2147483647;" in command_header

for name, vector_name in {
    "service": "service",
    "identity": "identity",
    "command": "command",
    "status": "status",
    "wtpCommand": "wtp_command",
    "wtpStatus": "wtp_status",
}.items():
    value = vectors["uuids"][vector_name]
    assert re.search(rf'{name}: "{re.escape(value)}"', web)
    assert re.search(rf'"{name}": "{re.escape(value)}"', linux_client)

for operation in ("open", "write", "profile_step_up", "profile_step_up_status", "apply", "cancel"):
    assert f'operation: "{operation}"' in web
    assert f'"{operation}"' in linux_client
    assert f'"{operation}"' in ble_session or f'operation == "{operation}"' in command_source

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
    "getpass.getpass",
):
    assert required in linux_client
assert '"Trusted"' not in linux_client
assert "expected_device_path = self.device_path" in linux_client
assert linux_client.count("pairing_request_allowed(str(device), expected_device_path") == 2
assert "bus_name=self.BLUEZ" in linux_client

assert "INDICATE | ENCRYPTION_KEY_SIZE_16 | DYNAMIC" in gatt_profile
assert "WRITE | WRITE_WITHOUT_RESPONSE | ENCRYPTION_KEY_SIZE_16 | DYNAMIC" in gatt_profile
assert vectors["uuids"]["wtp_command"].upper() in gatt_profile
assert vectors["uuids"]["wtp_status"].upper() in gatt_profile
assert "CLIENT_CONFIGURATION_HANDLE" in gatt
assert "att_read_callback_handle_little_endian_16" in gatt
assert "outbound_index_ + 1 == outbound_.size()" in gatt
assert "session_.response_started(now());" in gatt
assert '"request" if response else "command"' in linux_client
assert "owner_->status_cccd_ : owner_->wtp_cccd_) = value;" in gatt
assert "status_cccd_ != GATT_CLIENT_CHARACTERISTICS_CONFIGURATION_INDICATION" in gatt
assert "wtp_indications_enabled()" in gatt
assert "session_.wtp_over_field_status() ? status_cccd_ : wtp_cccd_" in gatt
assert "selected_field_wtp_command" in gatt
assert "owner_->session_.wtp_over_field_status();" in gatt
assert "!field_wtp_selected;" in gatt
assert "handle = wtp_status_handle();" in gatt
assert "if (wtp_carrier_changed)" in gatt
assert "owner_->session_.disconnected();" in gatt
assert "endpoint_->receive" in gatt and "endpoint_->consume_output" in gatt
assert gatt.index(
    "if (owner_->status_cccd_ != GATT_CLIENT_CHARACTERISTICS_CONFIGURATION_INDICATION)"
) < gatt.index("owner_->inbound_.receive")
assert "if (session_.authorized())\n            endpoint_->poll(current);" in gatt
assert "if (session_.poll(current))" in gatt
assert "(void)gap_disconnect(connection_);" in gatt
assert "access_.expire_provisional_bond(now_ms)" in ble_session
assert "(void)ble_disconnect();" in local_access
assert "owner_->endpoint_ && !owner_->endpoint_->closed()" in gatt
assert "if (indication_ == Indication::Wtp)\n        return false;" in gatt
assert "owner_->security_lost();" in gatt
security_callback = gatt[
    gatt.index("case HCI_EVENT_ENCRYPTION_CHANGE:") : gatt.index("case SM_EVENT_JUST_WORKS_REQUEST:")
]
security_failure = security_callback.index("owner_->security_lost();")
security_disconnect = security_callback.index("(void)gap_disconnect(owner_->connection_);")
assert security_failure < security_disconnect
security_lost = gatt[
    gatt.index("void PicoGattTransport::security_lost()") : gatt.index("bool PicoGattTransport::queue")
]
for required in (
    "session_.disconnected()",
    "endpoint_->disconnect()",
    "outbound_.clear()",
    "status_cccd_ = 0",
    "wtp_cccd_ = 0",
    "indication_ = Indication::None",
):
    assert required in security_lost

assert "Status: frozen Field-GATT/1 source contract." in contract
assert "Field-GATT-v1-vectors.json" in contract

print("Field-GATT/1 firmware, Bluefy, native-Pi, documentation, and vectors are synchronized")
