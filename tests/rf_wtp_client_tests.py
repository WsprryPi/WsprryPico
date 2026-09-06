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
    rf_wtp.make_job(rf_wtp.GOLDEN37, 10_140_200)
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
