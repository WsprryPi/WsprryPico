#!/usr/bin/env python3
"""Wire tests: real C++ endpoint, independent schema and monitor decoding; no USB."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_wtp_contract import SchemaValidator, load_json, frame, loads_strict
from wtp_monitor import FrameDecoder

schema = load_json(ROOT / "docs/protocol/wtp-1.schema.json")
validator = SchemaValidator(schema)
vectors = load_json(ROOT / "docs/protocol/test-vectors/wtp-1.json")

class Peer:
    def __init__(self):
        self.p = subprocess.Popen([sys.argv[1]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.seq = 0
        self.session = "1" * 32
        self.decoder = FrameDecoder()
        self.events = []
        self.call(action="connect", principal="usb-physical")
    def call(self, **control):
        self.p.stdin.write(json.dumps(control) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        assert line, f"driver stopped: {self.p.poll()}"
        result = json.loads(line)
        messages = []
        for payload in self.decoder.feed(bytes.fromhex(result.get("hex", ""))):
            value = loads_strict(payload.decode("utf-8"))
            errors = validator.errors(value, schema)
            assert not errors, (value, errors)
            messages.append(value)
            if value["type"] == "event":
                self.events.append(value)
        result["messages"] = messages
        return result
    def request(self, op, body=None, rid=None, **extra):
        self.seq += 1
        value = dict(type="request", protocol="WTP/1", session_id=self.session,
                     request_id=rid or f"{self.seq:032x}", op=op, body=body or {})
        value.update(extra)
        return value
    def send(self, value, **control):
        raw = value if isinstance(value, bytes) else json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode()
        wire = frame(raw)
        results = []
        for offset in range(0, len(wire), 1024):
            result = self.call(action="send", hex=wire[offset:offset+1024].hex(), **control)
            results.extend(result["messages"])
        result["messages"] = results
        return result
    def ask(self, op, body=None, **extra):
        result = self.send(self.request(op, body, **extra))
        responses = [m for m in result["messages"] if m["type"] == "response"]
        assert len(responses) == 1, result
        return responses[0]
    def hello(self):
        return self.ask("HELLO", {"versions":["WTP/1"], "client_name":"tests", "client_version":"1"})
    def reconnect(self, principal="usb-physical"):
        self.call(action="disconnect")
        self.decoder = FrameDecoder()
        self.call(action="connect", principal=principal)
    def close(self):
        self.p.stdin.close()
        assert self.p.wait(timeout=5) == 0

def ok(response):
    assert response["ok"], response
    return response["body"]
def error(response, code):
    assert not response["ok"] and response["error"]["code"] == code, response

def job(identifier="3"*32):
    return dict(job_id=identifier, profile="rf-events/1", mode="tone", total_duration_ns="1000000",
                events=[dict(offset_ns="0",duration_ns="1000000",rf_on=True,frequency_nhz="14000000000000000")])

# Normative request fixtures and raw JSON rejection cases exercise the decoder.
p=Peer()
for case in vectors["schema_cases"]:
    if case["message"].get("type") != "request":
        continue
    raw=json.dumps(case["message"], separators=(",", ":")).encode()
    result=p.call(action="decode",hex=raw.hex())
    structural = not validator.errors(case["message"], schema)
    assert result["valid"] == structural, case["name"]
    if structural and not case["valid"]:
        peer=Peer(); ok(peer.hello())
        ok(peer.ask("CLAIM",{"owner_id":"2"*32,"lease_ms":5000}))
        response=peer.send(case["message"])["messages"][0]
        assert not response["ok"], case["name"]
        peer.close()
for case in vectors["raw_json_cases"]:
    assert not p.call(action="decode",hex=case["json"].encode().hex())["json"], case["name"]
for raw in [b'{"a":1,"\\u0061":2}', b'{"a":"\xc0\xaf"}', b'{"a":"\xed\xa0\x80"}',
            b'{"a":"\xf4\x90\x80\x80"}', b'\xef\xbb\xbf{}', b'{"a":-2147483649}',
            b'{"a":1e0}', b'{"a":01}', b'{"a":true,}', b'{}{}', b'{"a":"\\udfff"}']:
    assert not p.call(action="decode",hex=raw.hex())["json"], raw
for raw in [b'{"a":-2147483648,"b":2147483647}', b'{"a":"\\ud83d\\ude80"}', b'{"a":"\xcf\x80"}']:
    assert p.call(action="decode",hex=raw.hex())["json"], raw
p.close()

# Complete operation mapping, read-only snapshots, Unicode, no RF, ownership.
p=Peer()
error(p.ask("STATUS"),"HELLO_REQUIRED")
hello=ok(p.hello())
assert hello["device_id"] == "d"*32
caps=ok(p.ask("CAPS")); assert caps["engine"] == "inhibited-no-rf"
assert ok(p.ask("PING",{"token":"π\u0000🚀"}))["token"] == "π\u0000🚀"
clock_req=p.request("GET_CLOCK")
original=p.send(clock_req)["messages"][0]
p.call(action="clock",synchronized=True,now_ns="1000000000")
assert p.send(clock_req)["messages"][0] == original
status_req=p.request("STATUS")
original=p.send(status_req)["messages"][0]
ok(p.ask("CLAIM",{"owner_id":"2"*32,"lease_ms":5000}))
assert p.send(status_req)["messages"][0] == original
ok(p.ask("RENEW",{"owner_id":"2"*32,"lease_ms":10000}))
ok(p.ask("LOAD",job()))
# Operation-body schema precedes ownership; parsed-value idempotency still holds.
error(p.ask("RENEW",{"owner_id":"2"*32,"lease_ms":True}),"INVALID_MESSAGE")
error(p.ask("LOAD",dict(job(), extra=0)),"INVALID_MESSAGE")
error(p.ask("ARM",{"job_id":"3"*32,"start_utc_ns":"01","max_start_uncertainty_ns":"0"}),"INVALID_MESSAGE")
arm_req=p.request("ARM",{"job_id":"3"*32,"start_utc_ns":"1002000000000","max_start_uncertainty_ns":"100"})
arm=p.send(arm_req)["messages"][0]; ok(arm)
p.call(action="clock",synchronized=True,now_ns="2000000000")
assert p.send(arm_req)["messages"][0] == arm
# A request must service an active engine even without an outer-loop poll.
p.call(action="clock",synchronized=True,now_ns="2001000000",poll=False)
received=p.send(p.request("STATUS"),poll=False)["messages"]
assert ok(next(m for m in received if m["type"] == "response"))["state"] == "complete"
assert any(m["type"] == "event" and m["body"].get("state") == "complete" for m in received)
error(p.ask("ABORT",{"job_id":"3"*32}),"INVALID_STATE")
ok(p.ask("RELEASE"))
ok(p.ask("CLAIM",{"owner_id":"2"*32,"lease_ms":5000}))
ok(p.ask("LOAD",job("4"*32)))
ok(p.ask("ABORT",{"job_id":"4"*32}))
status=ok(p.ask("STATUS")); assert status["state"] == "aborted" and not status["output_active"]
assert any(e["body"].get("state")=="running" for e in p.events)
ids=[int(e["event_id"]) for e in p.events]; assert ids == list(range(len(ids)))
p.reconnect(); error(p.ask("STATUS"),"HELLO_REQUIRED"); ok(p.hello())
assert ok(p.ask("STATUS"))["state"] == "aborted"
p.reconnect("different-principal"); error(p.hello(),"AUTHENTICATION_REQUIRED")
p.reconnect(); ok(p.hello())
# A repeated request ID with a malformed body is a replay conflict, not schema error.
r=p.request("PING"); ok(p.send(r)["messages"][0]); r["body"]={"extra":True}
result=p.send(r); error(result["messages"][0],"REQUEST_ID_REUSE"); assert result["closed"]
assert not p.send(p.request("STATUS"))["messages"]
p.reconnect(); ok(p.hello())
p.call(action="reset"); assert p.call(action="flush")["closed"]
p.reconnect(); new=ok(p.hello()); assert new["boot_id"] != hello["boot_id"]
assert ok(p.ask("STATUS"))["owner_id"] is None
p.close()

# Fragmented/combined framing, short TX, bounded backpressure and logical close.
p=Peer(); raw=json.dumps(p.request("HELLO",{"versions":["WTP/1"],"client_name":"t","client_version":"1"})).encode()
wire=frame(raw)
for byte in wire[:-1]:
    assert not p.call(action="send",hex=bytes([byte]).hex())["messages"]
assert p.call(action="send",hex=wire[-1:].hex())["messages"][0]["ok"]
a=p.request("PING",{"token":"one"}); b=p.request("PING",{"token":"two"})
combined=frame(json.dumps(a).encode())+frame(json.dumps(b).encode())
result=p.call(action="send",hex=combined.hex(),drain=False)
assert not result["messages"] and result["pending"]>0
for _ in range(10): assert not p.call(action="flush",limit=1)["messages"]
messages=p.call(action="flush")["messages"]
assert [m["body"]["token"] for m in messages] == ["one","two"]
p.send(p.request("PING"),drain=False)
p.call(action="clock",synchronized=False,now_ns="5000000000",drain=False)
assert p.call(action="flush")["closed"]
p.reconnect(); ok(p.hello())
p.call(action="send",hex=frame(b'{}')[:10].hex())
p.call(action="clock",synchronized=False,now_ns="10000000000")
assert p.call(action="flush")["closed"]
p.reconnect(); ok(p.hello())
for _ in range(3):
    bad=bytearray(frame(b'{}')); bad[-1]^=1
    result=p.call(action="send",hex=bad.hex())
assert result["closed"] and any(e["event"]=="INVALID_FRAME" for e in p.events)
p.reconnect()
result=p.send(p.request("HELLO",{"versions":["WTP/2"],"client_name":"t","client_version":"1"}))
error(result["messages"][0],"UNSUPPORTED_VERSION"); assert result["closed"]
p.close()

# Lease expiration and missed starts are observed even without further input.
p=Peer(); ok(p.hello()); ok(p.ask("CLAIM",{"owner_id":"2"*32,"lease_ms":5000})); ok(p.ask("LOAD",job()))
p.call(action="clock",synchronized=False,now_ns="5000000000")
assert ok(p.ask("STATUS"))["state"]=="empty"
assert any(e["event"]=="JOB_STATE" and e["body"]["state"]=="aborted" for e in p.events)
assert any(e["event"]=="OWNER_RELEASED" for e in p.events)
ok(p.ask("CLAIM",{"owner_id":"2"*32,"lease_ms":5000})); ok(p.ask("LOAD",job("4"*32)))
error(p.ask("ARM",{"job_id":"4"*32,"start_utc_ns":"1006000000000","max_start_uncertainty_ns":"100"}),"CLOCK_UNSYNCHRONIZED")
p.call(action="clock",synchronized=True)
ok(p.ask("ARM",{"job_id":"4"*32,"start_utc_ns":"1006000000000","max_start_uncertainty_ns":"100"}))
p.call(action="clock",synchronized=True,now_ns="6000000001")
assert any(e["event"]=="MISSED_START" for e in p.events)
error(p.ask("NOT_AN_OPERATION",{"extra":True}),"UNKNOWN_OPERATION")
p.close()
print("WTP endpoint wire, schema, replay, lifecycle, pressure and rejection tests passed")

# Largest legal payload, event array limit, UTF-8 byte limits, and decoded keys.
p=Peer(); ok(p.hello())
raw=json.dumps(p.request("PING")).encode()
result=p.send(raw+b' '*(65536-len(raw)))
ok(result["messages"][0])
error(p.ask("PING",{"token":"π"*33}),"INVALID_MESSAGE")
ok(p.ask("PING",{"token":"π"*32}))
ok(p.ask("CLAIM",{"owner_id":"2"*32,"lease_ms":5000}))
large=job(); large["total_duration_ns"]="512"
large["events"]=[dict(offset_ns=str(i),duration_ns="1",rf_on=False) for i in range(512)]
ok(p.ask("LOAD",large))
invalid=dict(large,events=large["events"]+[dict(offset_ns="512",duration_ns="1",rf_on=False)])
error(p.ask("LOAD",invalid),"INVALID_MESSAGE")
assert ok(p.ask("STATUS"))["job_id"]=="3"*32
p.close()

# Deterministic syntax differential checks, including nesting and duplicate keys.
import random
rng=random.Random(731)
p=Peer()
for depth in range(1,19):
    raw=('{"x":'*(depth-1)+'{}'+'}'*(depth-1)).encode()
    assert p.call(action="decode",hex=raw.hex())["json"] == (depth<=16)
seeds=[b'{"x":0}',b'{"x":"hello"}',b'{"x":[1,true,null,{"y":"\\u0061"}]}']
for _ in range(300):
    source=bytearray(rng.choice(seeds)); pos=rng.randrange(len(source))
    source[pos]=rng.choice(b'{}[],:"\\0129-+eEtn \x00\xff')
    try:
        parsed=loads_strict(bytes(source).decode('utf-8'))
        expected=isinstance(parsed,dict)
    except (ValueError,UnicodeError):
        expected=False
    assert p.call(action="decode",hex=source.hex())["json"] == expected, source
# Cross-session requests cannot mutate the established connection's owner.
ok(p.hello()); ok(p.ask("CLAIM",{"owner_id":"2"*32,"lease_ms":5000}))
result=p.send(p.request("RELEASE",session_id="9"*32))
responses=[m for m in result["messages"] if m["type"]=="response"]
error(responses[0],"SESSION_REPLACED"); assert result["closed"]
p.reconnect(); ok(p.hello()); assert ok(p.ask("STATUS"))["owner_id"]=="2"*32
p.close()
print("Maximum payload/event bounds and deterministic JSON differential checks passed")

# Invalid HELLOs cannot consume the service's finite session table.
p=Peer()
for i in range(20):
    p.session=f"{i+100:032x}"
    error(p.ask("HELLO",{"versions":["WTP/1"],"client_name":"x"}),"INVALID_MESSAGE")
p.session="1"*32; ok(p.hello())
# Schema rejection precedes ownership rejection.
error(p.ask("ARM",{"job_id":"3"*32,"start_utc_ns":"-1","max_start_uncertainty_ns":"0"}),"INVALID_MESSAGE")
ok(p.ask("CLAIM",{"owner_id":"2"*32,"lease_ms":5000})); ok(p.ask("LOAD",job()))
p.call(action="clock",synchronized=True)
ok(p.ask("ARM",{"job_id":"3"*32,"start_utc_ns":"1001000000000","max_start_uncertainty_ns":"100"}))
p.call(action="clock",synchronized=True,now_ns="1000000000")
p.call(action="fault")
assert any(e["event"]=="DEVICE_FAULT" for e in p.events)
assert ok(p.ask("STATUS"))["output_active"]
error(p.ask("ABORT",{"job_id":"3"*32}),"OUTPUT_STATE_UNKNOWN")
p.close()
print("Invalid negotiation resource and fault-event tests passed")

# Retained resource idempotency survives newer jobs and response-cache eviction.
p=Peer(); ok(p.hello()); ok(p.ask("CLAIM",{"owner_id":"2"*32,"lease_ms":60000}))
p.call(action="clock",synchronized=True)
first=job(); ok(p.ask("LOAD",first))
arm_body={"job_id":"3"*32,"start_utc_ns":"1001000000000","max_start_uncertainty_ns":"100"}
original_arm=ok(p.ask("ARM",arm_body))
ok(p.ask("ABORT",{"job_id":"3"*32}))
ok(p.ask("LOAD",job("4"*32)))
for _ in range(10): ok(p.ask("PING"))
assert ok(p.ask("LOAD",first))["job_id"]=="3"*32
assert ok(p.ask("ARM",arm_body))==original_arm
status=ok(p.ask("STATUS")); assert status["job_id"]=="4"*32 and status["state"]=="loaded"
error(p.ask("LOAD",dict(first,total_duration_ns="2")),"JOB_ID_CONFLICT")
ok(p.ask("ABORT",{"job_id":"4"*32}))
# Fill eight terminal records, touch the oldest, then add a ninth. LRU retains
# the touched result and evicts the formerly second-oldest result.
for i in range(5,11):
    identifier=f"{i:032x}"; ok(p.ask("LOAD",job(identifier))); ok(p.ask("ABORT",{"job_id":identifier}))
ok(p.ask("LOAD",first))
identifier=f"{11:032x}"; ok(p.ask("LOAD",job(identifier))); ok(p.ask("ABORT",{"job_id":identifier}))
records=ok(p.ask("STATUS"))["terminal_records"]
assert "3"*32 in [r["job_id"] for r in records]
assert "4"*32 not in [r["job_id"] for r in records]
assert len(records)==8
p.call(action="clock",synchronized=True,now_ns="3600000000000")
ok(p.hello()); ok(p.ask("CLAIM",{"owner_id":"2"*32,"lease_ms":5000}))
assert not ok(p.ask("STATUS"))["terminal_records"]
error(p.ask("ARM",arm_body),"JOB_NOT_FOUND")
p.close()
print("Retained LOAD/ARM results, terminal LRU and expiry tests passed")
