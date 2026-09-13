"""Prospective immutable HTTP stimuli for A's under-RF retention exercise."""
import hashlib
import json
from phase11_5_inventory import require
from phase11_5_r3_capacity_plan import identity

NAME='wsprrypico-0a60df.local'
POLICY='r3-v2-retention-sessions-replay-v1'


def cases(seed,owner_id):
    identity(seed);identity(owner_id)
    def ident(label):return hashlib.sha256((seed+':'+label).encode()).hexdigest()[:32]
    sessions=[ident('session-'+str(n)) for n in range(15)]
    result=[]
    def make(label,session,request_id,op,body,status=200,error=None,phase='saturate'):
        request=dict(session_id=session,request_id=request_id,operation=op,body=body)
        raw=json.dumps(request,separators=(',',':')).encode()
        header=(f'POST /api/v1/jobs HTTP/1.1\r\nHost: {NAME}:18443\r\n'
                f'Origin: https://{NAME}:18443\r\nX-WsprryPico-Request: 1\r\n'
                f'Content-Type: application/json\r\nContent-Length: {len(raw)}\r\n'
                'Connection: close\r\n\r\n').encode()
        result.append(dict(label=label,phase=phase,request=request,wire_hex=(header+raw).hex(),
                           expected_status=status,error_code=error))
    def hello(label,session,request_id,version='1',status=200,error=None,phase='saturate'):
        make(label,session,request_id,'HELLO',dict(versions=['WTP/1'],client_name='R3-retention',
             client_version=version),status,error,phase)
    # The 360-second initial quiet interval leaves exactly the USB observer and
    # continuously polling native WTP session. HTTP GET does not create sessions.
    ids=[ident('replay-'+str(n)) for n in range(9)]
    for n in range(14):
        hello('session-'+str(n),sessions[n],ident('hello-'+str(n)))
    hello('session-17-overflow',sessions[14],ident('overflow'),status=409,error='BUSY')
    for n in range(8):hello('replay-fill-'+str(n),sessions[0],ids[n])
    for n in range(8):hello('replay-conflict-'+str(n),sessions[0],ids[n],'2',409,'REQUEST_ID_REUSE')
    hello('replay-touch-oldest',sessions[0],ids[0])
    hello('replay-ninth',sessions[0],ids[8])
    # Verify touched entry before the evicted entry so neither conclusion can
    # be confused with 300-second expiry even at every 15-second reply bound.
    hello('replay-touched-retained',sessions[0],ids[0],'2',409,'REQUEST_ID_REUSE')
    hello('replay-evicted-second',sessions[0],ids[1],'2')
    # Waiting 360 s from the LAST preceding response exceeds both source TTLs;
    # valid non-owning RENEW distinguishes absence from an extant non-owner.
    renew=dict(owner_id=owner_id,lease_ms=60000)
    make('session-13-expired',sessions[13],ident('expired-13'),'RENEW',renew,409,'HELLO_REQUIRED','expired')
    make('session-0-expired',sessions[0],ident('expired-0'),'RENEW',renew,409,'HELLO_REQUIRED','expired')
    hello('replay-expired-and-session-reused',sessions[0],ids[0],'2',phase='expired')
    hello('overflow-session-now-admitted',sessions[14],ident('overflow'),phase='expired')
    return result


def validate_plan(plan,owner_id):
    require(plan['policy']==POLICY and plan['cases']==cases(plan['seed'],owner_id),'Frozen retention cases')
    require(type(plan['initial_quiet_seconds']) is int and plan['initial_quiet_seconds']==360 and
            type(plan['expiry_quiet_seconds']) is int and plan['expiry_quiet_seconds']==360 and
            type(plan['maximum_connections']) is int and plan['maximum_connections']==39,
            'Retention real-time/count bounds')
    require(plan['running_duration_ns']=='1020000000000','Whole-case RF reserve')
    # Worst allowed 15-second replies, an actual TTL interval, and an observation
    # allowance all fit inside the finite 1020-second RF job.
    require(len(plan['cases'])==39 and len(plan['cases'])*15+360+60<=1020,'Retention deadline arithmetic')
    return plan
