#!/usr/bin/env python3
"""Probe control-flow tests with fully mocked device I/O."""
import contextlib
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import wtp_probe
from validate_wtp_contract import frame, load_json
from wtp_monitor import FrameDecoder

# The opt-in flag is checked before any device open.
with patch.object(sys, "argv", ["wtp_probe", "/not-a-device"]), patch.object(wtp_probe.os, "open") as opening:
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            wtp_probe.main()
            raise AssertionError("missing opt-in accepted")
        except SystemExit as error:
            assert error.code == 2
    opening.assert_not_called()

vectors=load_json(Path(__file__).resolve().parents[1]/"docs/protocol/test-vectors/wtp-1.json")
bodies={case["message"].get("op"):case["message"].get("body") for case in vectors["schema_cases"]
        if case["valid"] and case["message"].get("type")=="response" and case["message"].get("ok")}
bodies["GET_CLOCK"]={"state":"unsynchronized","utc_now_ns":"0","monotonic_now_ns":"0",
                    "uncertainty_ns":"0","sync_age_ns":"0","leap":"unknown"}
bodies["PING"]={}
decoder=FrameDecoder(); replies=bytearray(); operations=[]
def write(fd,data):
    assert fd==71
    for payload in decoder.feed(data[:7]):
        request=json.loads(payload)
        op=request["op"]; operations.append(op)
        response=dict(type="response",protocol="WTP/1",session_id=request["session_id"],
                      request_id=request["request_id"],op=op,ok=True,body=bodies[op])
        replies.extend(frame(json.dumps(response).encode()))
    return min(7,len(data))
def read(fd,size):
    assert fd==71
    data=bytes(replies[:13]); del replies[:13]; return data
def ready(readable,writable,exceptional,timeout):
    return ([71] if replies else []),writable,[]
with patch.object(sys,"argv",["wtp_probe","/not-a-device","--run"]), \
     patch.object(wtp_probe.os,"open",return_value=71), \
     patch.object(wtp_probe,"configure_raw"), \
     patch.object(wtp_probe.fcntl,"ioctl"), \
     patch.object(wtp_probe.os,"write",side_effect=write), \
     patch.object(wtp_probe.os,"read",side_effect=read), \
     patch.object(wtp_probe.select,"select",side_effect=ready), \
     patch.object(wtp_probe.os,"close") as close:
    with contextlib.redirect_stdout(io.StringIO()):
        wtp_probe.main()
    close.assert_called_once_with(71)
assert operations==["HELLO","CAPS","GET_CLOCK","STATUS","PING"]
print("Opt-in probe and fragmented read-only I/O tests passed")
