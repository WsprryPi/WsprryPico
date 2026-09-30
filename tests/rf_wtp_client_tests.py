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

# The GP14 finite tone permits the RF planner's unavoidable frequency rounding.
# Failure cleanup is bound to the known owner/job even before ARM is attempted.
from phase12_gp14_rf import job_value, cleanup_owned
from validate_wtp_contract import SchemaValidator
schema = json.loads((ROOT/'docs/protocol/wtp-1.schema.json').read_text())
validator = SchemaValidator(schema)
finite = job_value('1'*32)
assert finite['allow_frequency_adjustment'] is True
assert finite['total_duration_ns'] == finite['events'][0]['duration_ns'] == '20000000000'
class CleanupPeer:
    def __init__(self, state, *, foreign=False):
        self.state, self.calls = state, []
        self.owner = 'f'*32 if foreign else '2'*32
        self.job = None if state == 'empty' else '1'*32
    def request(self, operation, body):
        request = dict(type='request', protocol='WTP/1', session_id='3'*32,
                       request_id='4'*32, op=operation, body=body)
        assert not validator.errors(request, schema), (operation, body)
        self.calls.append(operation)
        if operation == 'ABORT': self.state = 'aborted'
        if operation == 'RELEASE': self.state, self.owner, self.job = 'empty', None, None
        if operation == 'STATUS':
            return dict(boot_id='boot', state=self.state, owner_id=self.owner,
                        job_id=self.job, output_active=self.state == 'running')
for state, expected in [('empty',['STATUS','RELEASE','STATUS']),
                        ('loaded',['STATUS','ABORT','STATUS','RELEASE','STATUS']),
                        ('running',['STATUS','ABORT','STATUS','RELEASE','STATUS']),
                        ('complete',['STATUS','RELEASE','STATUS'])]:
    peer = CleanupPeer(state);cleanup_owned(peer,'boot','1'*32,'2'*32)
    assert peer.calls == expected
peer = CleanupPeer('loaded',foreign=True)
try: cleanup_owned(peer,'boot','1'*32,'2'*32)
except RuntimeError: pass
else: raise AssertionError('foreign owner touched')
assert peer.calls == ['STATUS']
print('GP14 finite job and schema-valid claim-only/active/terminal cleanup passed')

# A reviewed operator timing miss may be retried explicitly, but an observed
# gesture, input fault, foreign completion or absent cleanup still blocks RF.
from phase12_gp14_rf import review_no_input_retry
from tempfile import TemporaryDirectory
import copy
with TemporaryDirectory() as directory:
    root = Path(directory)/'run-no-input'; root.mkdir()
    attempt = dict(case='active_stop', charged_jobs=1, status='FAILED_STOP_CAMPAIGN',
                   error='RuntimeError: physical action timeout', cleanup_verified=True,
                   boot_id='boot', job_id='1'*32)
    (root/'attempt.json').write_text(json.dumps(attempt))
    observation = dict(status=dict(boot_id='boot', output_active=True), gp14_held=False,
                       gp14_capture_fault=False, gp14_stop_events=0, gp14_reset_events=0,
                       rf_safety_inhibited=False, rf_safety_input_fault=0,
                       rf_safety_requested_ns='0')
    final = dict(boot_id='boot', state='empty', owner_id=None, job_id=None,
                 output_active=False, terminal_records=[dict(job_id='1'*32, state='complete',
                                                            output_active=False)])
    events = [dict(kind='action_info', value=observation),
              dict(kind='received', value=dict(type='response', op='STATUS', ok=True, body=final))]
    def check_retry(values, accepted):
        (root/'events.jsonl').write_text('\n'.join(json.dumps(value) for value in values))
        try: result = review_no_input_retry(root/'attempt.json')
        except RuntimeError:
            assert not accepted
        else:
            assert accepted and result['independent_rf_pass'] is False
    check_retry(events, True)
    for key, value in [('gp14_held', True), ('gp14_stop_events', 1),
                       ('rf_safety_inhibited', True), ('rf_safety_input_fault', 1),
                       ('rf_safety_requested_ns', '1')]:
        rejected = copy.deepcopy(events); rejected[0]['value'][key] = value
        check_retry(rejected, False)
    rejected = copy.deepcopy(events)
    rejected[1]['value']['body']['terminal_records'][0]['job_id'] = 'f'*32
    check_retry(rejected, False)
    check_retry(events[:1], False)
print('Explicit no-input retry preserves failed qualification and rejects safety/cleanup ambiguity')

from phase12_gp14_rf import review_quick_reset_mismatch, finish_capture, DEVICE
import subprocess
import time
with TemporaryDirectory() as directory:
    root=Path(directory)
    attempt=dict(case='active_stop', charged_jobs=1, status='FAILED_STOP_CAMPAIGN',
                 error='ConnectionError: serial device closed', boot_id='old')
    (root/'attempt.json').write_text(json.dumps(attempt))
    initial=dict(device_id=DEVICE, revision='62ae4c2c2567', status=dict(boot_id='old'))
    events=[dict(kind='initial_info', value=initial),
            dict(kind='action_info', value=dict(status=dict(boot_id='old',output_active=True)))]
    (root/'events.jsonl').write_text('\n'.join(json.dumps(value) for value in events))
    healthy=dict(device_id=DEVICE, revision='62ae4c2c2567', system_clock_hz=138000000,
                 gp14_rf_acceptance=True, gp14_prior_reset=True, gp14_prior_duration_ms=27,
                 gp14_prior_rf_decision_after_launch_us=12637844,
                 status=dict(boot_id='new', engine='pio-dma-gp2', state='empty',
                             output_active=False, enabled=False, storage_healthy=True),
                 gp14_held=False, gp14_capture_fault=False, recovery_boot=False,
                 core0_stack_guard_valid=1, core1_stack_guard_valid=1, allocator_failures='0')
    for key in ('fault_stage','fault_hash','fault_pc','fault_status','provisioning_fault',
                'core0_stack_fault_status','core1_stack_fault_status','dma_errors'):
        healthy[key]=0
    def reset_review(info, accepted):
        (root/'post-failure-info.json').write_text(json.dumps(info))
        try: result=review_quick_reset_mismatch(root/'attempt.json')
        except RuntimeError: assert not accepted
        else: assert accepted and result['independent_rf_pass'] is False
    reset_review(healthy,True)
    for key,value in [('gp14_prior_duration_ms',400),('gp14_prior_reset',False),
                      ('recovery_boot',True),('fault_stage',1),('revision','other'),
                      ('gp14_prior_rf_decision_after_launch_us',0)]:
        rejected=copy.deepcopy(healthy);rejected[key]=value;reset_review(rejected,False)
    rejected=copy.deepcopy(healthy);rejected['status']['output_active']=True
    reset_review(rejected,False)

# Receiver completion is retained after a target failure; a stuck receiver is
# forcibly reaped at the finite deadline and cannot be mistaken for success.
capture=subprocess.Popen([sys.executable,'-c','import time;time.sleep(.03)'])
assert finish_capture(capture,time.monotonic()+2)==0
capture=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
assert finish_capture(capture,time.monotonic()+.03) is None and capture.poll() is not None
print('Normal-reset resolution remains nonqualifying; finite receiver completion/reaping passed')

# Physical readiness is consumed only after a distinct healthy quick-reset
# boot is released and synchronized. No cue/job can precede that signal.
from phase12_gp14_rf import wait_button_reset
class ReadyEvidence:
    def __init__(self): self.values=[]
    def record(self,kind,value): self.values.append((kind,value))
ready=copy.deepcopy(healthy)
ready.update(gp14_samples='100',gp14_output_inhibited=False,rf_safety_inhibited=False)
ready['status'].update(clock_state='synchronized')
ready['network']=dict(ipv4='192.168.1.53')
old=copy.deepcopy(ready);old['status']['boot_id']='old'
old.update(gp14_output_inhibited=True,rf_safety_inhibited=True)
packet=dict(revision=ready['revision'],address='192.168.1.53')
unsynced=copy.deepcopy(ready);unsynced['status']['clock_state']='unsynchronized'
values=iter([old,unsynced,ready]);evidence=ReadyEvidence()
assert wait_button_reset(packet,old,evidence,read=lambda:next(values),
                         now=lambda:0,pause=lambda _:None)==ready
assert [kind for kind,_ in evidence.values]==['physical_start_info']
for field,value in [('gp14_prior_reset',False),('gp14_held',True),
                    ('rf_safety_inhibited',True),('gp14_capture_fault',True)]:
    rejected=copy.deepcopy(ready);rejected[field]=value;evidence=ReadyEvidence()
    try: wait_button_reset(packet,old,evidence,read=lambda:rejected,
                           now=lambda:0,pause=lambda _:None)
    except RuntimeError: pass
    else: raise AssertionError('unqualified physical ready signal accepted')
    assert evidence.values==[]
times=iter([0,601])
try: wait_button_reset(packet,old,ReadyEvidence(),read=lambda:old,
                       now=lambda:next(times),pause=lambda _:None)
except RuntimeError as error: assert 'no RF job submitted' in str(error)
else: raise AssertionError('ready wait exceeded its no-RF deadline')
print('Physical readiness rejects premature, faulted, held and unsignaled starts')

# An absent CDC path during the ownership preflight is a reconnect condition.
# Existing endpoints with unknown/occupied ownership and other ValueErrors
# remain fatal, and no console request is written before exclusive access.
import phase12_gp14_rf as gp14
for exists,message,exception in [(False,'Endpoint occupied or ownership check unavailable',FileNotFoundError),
                                 (True,'Endpoint occupied or ownership check unavailable',ValueError),
                                 (False,'malformed console readback',ValueError)]:
    with patch.object(gp14,'exclusive_port',side_effect=ValueError(message)), \
            patch.object(gp14.Path,'exists',return_value=exists),patch.object(gp14,'write_all') as write:
        try: gp14.console()
        except exception: pass
        else: raise AssertionError('ownership error misclassified')
        write.assert_not_called()
print('CDC reconnect classification retains exclusive endpoint refusal')
