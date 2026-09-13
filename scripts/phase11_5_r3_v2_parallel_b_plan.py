"""Frozen zero-RF B functional requests; preparation alone opens no endpoints."""
import hashlib
import json
from phase11_5_inventory import require
from phase11_5_r3_v2_admission import maximum_job, DURATION
from phase11_5_r3_capacity_plan import identity, http_capacity_body, wtp_capacity_frame
from validate_wtp_contract import frame
from phase11_5_r3_v2_parallel_b_deploy import B_SERIAL, B_DEVICE, SOURCE, AUTHORIZATION, IMAGE

SCHEMA='phase11.5-r3-v2-parallel-b-functional-v1'
NAME='wsprrypico-0a9d89.local'
PEER_SHA='9cc4967f0a263b4aa94069674837ddcdb8c1946f5a5b407584ce7eee6298cfac'


def stimuli(seed):
    identity(seed)
    def ident(label):return hashlib.sha256((seed+':'+label).encode()).hexdigest()[:32]
    usb_session=ident('usb');http_session=ident('http');owner=ident('owner');job=ident('maximum')
    def usb(label,op,body=None,error=None,invalid=0,prefix=b'',size=None):
        request=dict(type='request',protocol='WTP/1',session_id=usb_session,
                     request_id=ident(label),op=op,body=body or {})
        raw=frame(json.dumps(request,separators=(',',':')).encode())
        if size:raw=wtp_capacity_frame(usb_session,request['request_id'])
        return dict(label=label,request=request,wire_hex=(prefix+raw).hex(),error=error,invalid_frames=invalid)
    hello=dict(versions=['WTP/1'],client_name='R3-parallel-B',client_version='1')
    usb_cases=[usb('hello','HELLO',hello),usb('maximum-status','STATUS',size=65536),
        usb('oversized-recovery','STATUS',invalid=1,prefix=wtp_capacity_frame(usb_session,ident('oversized'),True)),
        usb('claim','CLAIM',dict(owner_id=owner,lease_ms=60000)),
        usb('events-513','LOAD',maximum_job(ident('513'),513),'INVALID_MESSAGE'),usb('after-513','STATUS'),
        usb('overduration','LOAD',maximum_job(ident('overduration-job'),1,DURATION+1),'JOB_LIMIT_EXCEEDED'),
        usb('after-overduration','STATUS'),usb('maximum-load','LOAD',maximum_job(job)),
        usb('loaded-status','STATUS'),usb('loaded-abort','ABORT',dict(job_id=job)),
        usb('release','RELEASE'),usb('final-status','STATUS')]
    http_cases=[]
    def http(label,body,status,code=None,headers_only=False):
        raw=(f'POST /api/v1/jobs HTTP/1.1\r\nHost: {NAME}:18443\r\n'
             f'Origin: https://{NAME}:18443\r\nX-WsprryPico-Request: 1\r\n'
             f'Content-Type: application/json\r\nContent-Length: {len(body)}\r\n'
             'Connection: close\r\n\r\n').encode()
        http_cases.append(dict(label=label,wire_hex=(raw if headers_only else raw+body).hex(),
            declared_body_bytes=len(body),offered_body_bytes=0 if headers_only else len(body),
            expected_status=status,error_code=code))
    maximum=http_capacity_body(http_session,ident('http-maximum'))
    http('http-32768',maximum,200)
    http('http-replay',maximum,200)
    changed=json.loads(maximum);changed['body']['client_name']='changed'
    http('http-conflict',json.dumps(changed,separators=(',',':')).encode(),409,'REQUEST_ID_REUSE')
    # The transport parser rejects oversized Content-Length before API dispatch.
    # API-level 413 applies only to bodies which passed that parser.
    http('http-32769-header',http_capacity_body(http_session,ident('http-oversize'),True),400,'invalid_http',headers_only=True)
    http('http-malformed',b'{',400)
    recovery=http_capacity_body(http_session,ident('http-recovery')).rstrip(b' ')
    http('http-recovery',recovery,200)
    return dict(usb_session=usb_session,http_session=http_session,owner_id=owner,job_id=job,
                usb_cases=usb_cases,http_cases=http_cases)


def validate(packet):
    require(packet['schema']==packet['r3_scope']==SCHEMA and packet['serial']==B_SERIAL and packet['device_id']==B_DEVICE and
            packet['source_revision']==SOURCE and packet['image_sha256']==IMAGE and
            packet['authorization_sha256']==AUTHORIZATION,
            'B-only functional identity')
    identity(packet['seed']);identity(packet['boot_id']);identity(packet['inventory_session'])
    require(packet['stimuli']==stimuli(packet['seed']), 'Changed or RF-capable stimuli')
    for key,value in dict(runtime_seconds=600,cleanup_seconds=150,rf_jobs=0,arm_commands=0,
            accepted_loads=1,requests=34,tls_connections=6,configuration_writes=0,wifi_cycles=0,flashes=0).items():
        # 13 direct USB + six HTTP + three five-request inventory exchanges.
        require(type(packet[key]) is int and packet[key]==value,'Exact B functional budget: '+key)
    require(packet['address']=='192.168.1.53' and packet['tls_name']==NAME and
            packet['tls_peer_sha256']==PEER_SHA,'B network identity')
    return packet
