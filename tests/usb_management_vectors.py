#!/usr/bin/env python3
"""Check frozen USB-Management/1 vectors against the production endpoint."""
import json
import struct
import subprocess
import sys
from pathlib import Path

driver, fixture = sys.argv[1:]
vectors = json.loads(Path(fixture).read_text())
hello = vectors["hello"]
payload = hello["payload_utf8"].encode("utf-8")
assert json.loads(payload) == hello["payload"]
header = bytes.fromhex(hello["header_hex"])
assert header == b"UMP1" + struct.pack(">I", len(payload))
response = subprocess.run([driver], input=header + payload, capture_output=True,
                          check=True, timeout=5).stdout
assert response[:4] == b"UMP1"
assert struct.unpack(">I", response[4:8])[0] == len(response) - 8
reply = json.loads(response[8:])
assert set(reply) == {"schema", "id", "status", "session", "target", "body",
                      "etag", "delivery_required"}
assert reply["schema"] == "usb-management/1" and reply["id"] == 1
assert reply["status"] == 200 and reply["delivery_required"] is False
assert json.loads(reply["body"])["schema"] == "usb-management-discovery/1"
for refusal in vectors["refusals"]:
    payload = json.dumps(refusal["payload"], separators=(",", ":")).encode()
    wire = b"UMP1" + struct.pack(">I", len(payload)) + payload
    response = subprocess.run([driver], input=wire, capture_output=True,
                              check=True, timeout=5).stdout
    assert not response, refusal["description"]
print("USB-Management/1 frozen vectors pass production endpoint")
