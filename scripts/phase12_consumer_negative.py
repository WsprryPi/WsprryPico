#!/usr/bin/env python3
"""Injected source5 OwnerClaim negatives; no device I/O on import.

Run each case on a separately prepared idle boundary. No valid profile save is
submitted. Closing a START response is not cancellation in production.
"""
import base64
import hashlib
import secrets
import time
from phase12_consumer_composition import require, canonical
from phase12_recovery_device import DEVICE, resource_health, strict
from phase12_composition_audit import counter
from inhibited_network_acceptance import check_status

CASES=('WRONG_DEVICE','MALFORMED','COMPETING','EXPIRED','REPLAY','CANCELLED','INTERRUPTED')
BASE='/api/owner/v1/'


def b64(raw):return base64.urlsafe_b64encode(raw).decode().rstrip('=')
def unb64(value):return base64.urlsafe_b64decode(value+'='*((-len(value))%4))


def keys(generation):
    from cryptography.hazmat.primitives.asymmetric import x25519,ec
    from cryptography.hazmat.primitives import serialization
    private=x25519.X25519PrivateKey.generate()
    public=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    owner=ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
    body=dict(version=1,device_id=DEVICE,owner_public_key=b64(owner),browser_public_key=b64(public),
              browser_nonce=secrets.token_hex(16),profile_source=5,generation=str(generation))
    return body,private


def seal(start,body,private,station):
    from cryptography.hazmat.primitives.asymmetric import x25519
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    request_id=secrets.token_hex(16);nonce=secrets.token_bytes(12)
    aad=(b'WsprryPico/Owner-Claim/1\0'+bytes.fromhex(DEVICE)+bytes.fromhex(start['boot_id'])+
         bytes.fromhex(start['slot_id'])+b'http://192.168.4.1'+bytes([5])+
         int(start['generation']).to_bytes(8,'big')+unb64(body['owner_public_key'])+
         unb64(body['browser_public_key'])+unb64(start['pico_public_key'])+
         bytes.fromhex(body['browser_nonce'])+bytes.fromhex(request_id))
    shared=private.exchange(x25519.X25519PublicKey.from_public_bytes(unb64(start['pico_public_key'])))
    key=HKDF(algorithm=hashes.SHA256(),length=32,salt=hashlib.sha256(aad).digest(),
             info=b'WsprryPico owner claim AEAD v1').derive(shared)
    callsign=station['callsign'].encode();locator=station['locator'].encode()
    plain=b'\0\0'+bytes([len(callsign)])+callsign+locator+bytes([station['power_dbm']])
    encrypted=ChaCha20Poly1305(key).encrypt(nonce,plain,aad)
    return dict(version=1,device_id=DEVICE,boot_id=start['boot_id'],slot_id=start['slot_id'],
                request_id=request_id,aead_nonce=b64(nonce),ciphertext=b64(encrypted[:-16]),tag=b64(encrypted[-16:]))


def run(case,exchange,observe_info,observe_wtp,source,boot,evidence,station,
        *,cancel_boundary=None,interrupted_start=None,clock=time.monotonic,sleeper=time.sleep):
    """exchange(method,path,body,deadline)->(code,value,request_bytes,response_bytes).

    cancel_boundary returns a named actual AP_WITHDRAWAL same-boot receipt or
    REBOOT receipt {before_boot_id,boot_id,profile_generation,reboot_attempts:1}.
    REBOOT must independently verify the same B/image/generation before return.
    interrupted_start sends exactly once then closes before observing response;
    it returns actual request bytes. Missing boundary adapters remain PENDING.
    Caller owns image/profile proof, AP association and restoration.
    """
    require(case in CASES,'finite selected case');deadline=clock()+120
    def record_wire(kind,raw):
        require(isinstance(raw,bytes) and raw and len(raw)<=32768,'actual bounded wire evidence')
        evidence.record(kind,raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest())
    def http(method,path,body=None):
        require(clock()<deadline,'whole negative deadline')
        code,value,request,response=exchange(method,path,body,min(deadline,clock()+10))
        require(clock()<=deadline,'late HTTP')
        record_wire('http_request',request);record_wire('http_response',response)
        request_head,request_body=request.split(b'\r\n\r\n',1)
        require(request_head.startswith((method+' '+path+' HTTP/1.1\r\n').encode()),'actual HTTP route')
        headers={}
        for line in request_head.split(b'\r\n')[1:]:
            key,header_value=line.split(b':',1);key=key.lower();require(key not in headers,'duplicate request header');headers[key]=header_value.strip()
        require(headers.get(b'host')==b'192.168.4.1','exact AP Host')
        if method=='POST':
            require(headers.get(b'origin')==b'http://192.168.4.1' and
                    headers.get(b'x-wsprrypico-owner')==b'1' and
                    headers.get(b'content-type')==b'application/json','actual OwnerClaim request markers')
        require(strict(request_body)==body if body is not None else request_body==b'','actual request body')
        response_head,response_body=response.split(b'\r\n\r\n',1)
        require(response_head.startswith(('HTTP/1.1 '+str(code)+' ').encode()) and
                strict(response_body)==value,'response wire binding')
        return code,value
    def observe():
        require(clock()<deadline,'whole negative deadline')
        info,raw=observe_info();require(strict(raw)==info,'actual INFO wire binding');record_wire('usb_info',raw)
        resource_health(info)
        s=info['status']
        require(info['device_id']==DEVICE and info['revision']==source[:12] and s['boot_id']==boot and
                info['provisioning_source']=='consumer_preclock' and s['engine']=='inhibited-standalone-simulator' and
                s['enabled'] is False and s['output_active'] is False and s['state']=='empty' and
                s['storage_healthy'] is True and info['access_state']=='healthy','healthy source5 exactB authority')
        if observe_wtp is None:
            evidence.record('wtp_authority_unverified',owner_verified=False,job_identity_verified=False)
        else:
            status=observe_wtp();check_status(status,boot,unowned=True);evidence.record('actual_wtp_status',value=status)
        code,public=http('GET',BASE+'public-status');require(code==200,'public status')
        require(public['device_id']==DEVICE and public['boot_id']==boot and public['profile_source']==5,'public source/identity')
        code,slot=http('GET',BASE+'claim/status');require(code==200,'claim status')
        require(slot['device_id']==DEVICE and slot['boot_id']==boot and slot['profile_source']==5 and
                counter(slot['generation'],'slot generation')==counter(public['generation'],'public generation'),
                'slot identity/generation')
        require(clock()<=deadline,'late observation')
        return public,slot
    def reject(result,code,error):
        require(result[0]==code and result[1].get('error',{}).get('code')==error,'exact negative response')
    initial,slot=observe();generation=counter(initial['generation'],'generation')
    require(initial['claim_available'] is True and slot['slot_state']=='none','fresh idle claim boundary')
    if case=='CANCELLED' and cancel_boundary is None or case=='INTERRUPTED' and interrupted_start is None:
        evidence.record('case_pending',case=case,reason='supported physical boundary adapter absent',
                        no_cancel_endpoint=True);return dict(status='PENDING',case=case)
    body,private=keys(generation)
    if case=='WRONG_DEVICE':
        body['device_id']='0'*len(DEVICE);reject(http('POST',BASE+'claim/start',body),403,'unavailable')
    elif case=='MALFORMED':
        body['owner_public_key']='malformed';reject(http('POST',BASE+'claim/start',body),400,'invalid_request')
    elif case=='INTERRUPTED':
        wire=interrupted_start(BASE+'claim/start',body,min(deadline,clock()+10))
        record_wire('interrupted_start_request',wire)
        head,payload=wire.split(b'\r\n\r\n',1)
        require(head.startswith(b'POST /api/owner/v1/claim/start HTTP/1.1\r\n') and
                strict(payload)==body,'interrupted exact start request')
        _,current=observe();require(current['slot_state']=='granted','interrupted START must retain granted slot')
        evidence.record('interrupted_start_semantics',response_close_cancels=False)
        sleeper(62);_,current=observe();require(current['slot_state']=='none','interrupted START eventual expiry')
    else:
        code,start=http('POST',BASE+'claim/start',body);require(code==200,'single start admission')
        require(start['device_id']==DEVICE and start['boot_id']==boot and start['browser_nonce']==body['browser_nonce'] and
                start['browser_public_key']==body['browser_public_key'] and
                counter(start['generation'],'start generation')==generation,'claim binding')
        if case=='COMPETING':
            competing,_=keys(generation);reject(http('POST',BASE+'claim/start',competing),409,'busy')
            _,current=observe();require(current['slot_state']=='granted','competing START changed slot')
            sleeper(62)
        elif case=='CANCELLED':
            sealed=seal(start,body,private,station)
            receipt=cancel_boundary()
            if receipt['boundary']=='REBOOT':
                require(receipt['before_boot_id']==boot and receipt['boot_id']!=boot and
                        isinstance(receipt['boot_id'],str) and len(receipt['boot_id'])==32 and
                        all(c in '0123456789abcdef' for c in receipt['boot_id']) and
                        receipt['reboot_attempts']==1 and type(receipt['reboot_attempts']) is int and
                        counter(receipt['profile_generation'],'reboot generation')==generation,
                        'single exact reboot cancellation proof')
                boot=receipt['boot_id']
                new_public,new_slot=observe()
                require(counter(new_public['generation'],'new generation')==generation and
                        new_slot['slot_state']=='none','reboot fresh slot/generation')
            else:
                require(receipt['boundary']=='AP_WITHDRAWAL' and receipt['withdrawn'] is True and
                        receipt['reactivated'] is True and receipt['boot_id']==boot,
                        'named same-boot cancellation proof')
            evidence.record('cancel_boundary',receipt=receipt)
            reject(http('POST',BASE+'claim/submit',sealed),403,'unavailable')
        else:
            sealed=seal(start,body,private,station)
            if case=='EXPIRED':
                sleeper(62);reject(http('POST',BASE+'claim/submit',sealed),403,'unavailable')
            elif case=='REPLAY':
                # Correct envelope, deliberately unauthentic tag: consumes but cannot commit.
                tag=bytearray(unb64(sealed['tag']));tag[0]^=1;sealed['tag']=b64(tag)
                code,value=http('POST',BASE+'claim/submit',sealed)
                require(code==200 and value['state']=='failed' and value['generation']=='0','bad tag failclosed')
                reject(http('POST',BASE+'claim/submit',sealed),403,'unavailable')
                sleeper(62)
    final,slot=observe()
    require(counter(final['generation'],'generation')==generation and final['station']==initial['station'] and
            final['owner_exists']==initial['owner_exists'] and slot['slot_state']=='none' and final['claim_available'] is True,
            'negative altered persisted public state or leaked slot')
    evidence.record('negative_case_complete',case=case,generation=str(generation),rf_jobs=0,
                    simulator_jobs=0,physical_acceptance=False,wtp_owner_verified=observe_wtp is not None,
                    wtp_job_identity_verified=observe_wtp is not None)
    return dict(status='NEGATIVE_REVIEW_REQUIRED',case=case,rf_jobs=0,simulator_jobs=0,
                wtp_owner_verified=observe_wtp is not None,wtp_job_identity_verified=observe_wtp is not None)
