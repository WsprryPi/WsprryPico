#!/usr/bin/env python3
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import rf_wtp

job = rf_wtp.make_job(rf_wtp.GOLDEN37, 3_570_100)
assert job["mode"] == "wspr" and len(job["events"]) == 162
assert job["total_duration_ns"] == "110592000000"
assert job["events"][0]["offset_ns"] == "0"
assert job["events"][-1]["duration_ns"] in ("682666666", "682666667")
for previous, current in zip(job["events"], job["events"][1:]):
    assert int(previous["offset_ns"]) + int(previous["duration_ns"]) == int(current["offset_ns"])
try:
    rf_wtp.make_job("0" * 161, 3_570_100)
except ValueError:
    pass
else:
    raise AssertionError("short symbol input accepted")
try:
    rf_wtp.make_job(rf_wtp.GOLDEN37, 144_490_500)
except ValueError:
    pass
else:
    raise AssertionError("unsupported base frequency accepted")

peer = rf_wtp.WtpPeer.__new__(rf_wtp.WtpPeer)
peer.pending = deque([
    {"type": "event", "event": "JOB_STATE", "body": {"state": "armed"}},
    {"type": "response", "request_id": "wanted", "ok": True, "body": {"state": "complete"}},
    {"type": "event", "event": "JOB_STATE", "body": {"state": "complete"}},
])
response = peer._take_response("wanted")
assert response["body"]["state"] == "complete"
assert peer.next_message(0.1)["body"]["state"] == "armed"
assert peer.next_message(0.1)["body"]["state"] == "complete"
print("RF WTP client job construction passed")

# A matching request counter from a different session is stale evidence.
from unittest.mock import patch
import json
for field, value in (("session_id", "f" * 32), ("protocol", "WTP/2")):
    peer = rf_wtp.WtpPeer(100)
    message = dict(type="response", protocol="WTP/1", session_id=peer.session,
                   request_id="0" * 31 + "1", op="STATUS", ok=True, body={})
    message[field] = value
    with patch.object(rf_wtp.os, "read", return_value=rf_wtp.frame(json.dumps(message).encode())):
        try:
            peer._receive()
        except ValueError:
            pass
        else:
            raise AssertionError("stale response accepted")
peer = rf_wtp.WtpPeer(100)
peer.pending.append(dict(type="response", request_id="0" * 31 + "1", op="LOAD", ok=True, body={}))
with patch.object(rf_wtp, "write_all"):
    try:
        peer.request("STATUS", {})
    except ValueError:
        pass
    else:
        raise AssertionError("wrong operation response accepted")

# Reconnecting one logical session must not reuse request IDs from its cache.
old = rf_wtp.WtpPeer(100)
old.sequence = 27
old.pending.append({"type": "event", "body": {"state": "complete"}})
reconnected = rf_wtp.WtpPeer(101, session=old.session, sequence=old.sequence)
response = dict(type="response", protocol="WTP/1", session_id=old.session,
                request_id=f"{28:032x}", op="HELLO", ok=True, body={"fresh": True})
with patch.object(rf_wtp, "write_all") as write, \
        patch.object(rf_wtp.select, "select", return_value=([101], [], [])), \
        patch.object(rf_wtp.os, "read", return_value=rf_wtp.frame(json.dumps(response).encode())):
    assert reconnected.request("HELLO", {}) == {"fresh": True}
request = json.loads(write.call_args.args[1][16:])
assert request["session_id"] == old.session and request["request_id"] == f"{28:032x}"
assert not reconnected.pending
