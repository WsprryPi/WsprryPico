#!/usr/bin/env python3
"""Opt-in accelerated engineering cookie evidence; no WTP jobs or RF output.

Caller verifies/programs the exact candidate and restores the baseline afterward.
Evidence includes private passwords/cookies and must never be published verbatim.
"""
import hashlib
import json
from pathlib import Path
import re
import socket
import ssl
import time
import uuid
from phase12_consumer_composition import Evidence, canonical, require
from inhibited_network_acceptance import check_status
from phase12_recovery_device import DEVICE, resource_health, strict
from phase12_composition_audit import counter


def guard(info, source, boot, address, ap_proof):
    require(address=='192.168.4.1' and ap_proof['device_id']==DEVICE and
            ap_proof['boot_id']==boot and ap_proof['source_commit']==source and
            ap_proof['interface']=='wlan2' and ap_proof['destination']==address and
            ap_proof['associated'] is True and ap_proof['local_ipv4']=='192.168.4.2',
            'independent exact B AP association proof required')
    resource_health(info)
    s=info['status']
    require(info['device_id']==DEVICE and info['revision']==source[:12] and
            s['boot_id']==boot and s['engine']=='inhibited-standalone-simulator' and
            s['output_active'] is False and s['enabled'] is False and
            s['state']=='empty',
            'exact inactive B engineering authority')
    require(info['provisioning_source']=='provisioned' and info['lan_wtp_mode']=='engineering-tls' and
            counter(info['softap_session_inactivity_ms'],'session inactivity')==15000 and
            counter(info['softap_session_absolute_ms'],'session absolute')==60000 and
            counter(info['softap_session_capacity'],'session capacity')==4 and s['storage_healthy'] is True and
            info['access_state']=='healthy' and not info.get('bootstrap_reset_pending',False),
            'engineering accelerated session fixture required')
    return counter(info['softap_retained_sessions'],'retained sessions')


class HTTPS:
    def __init__(self,address,hostname,ca,evidence):
        require(re.fullmatch(r'[A-Za-z0-9.-]+',hostname) is not None,'HTTPS hostname')
        self.address,self.hostname,self.evidence=address,hostname,evidence
        require(address=='192.168.4.1','cookie API is B SoftAP only')
        self.context=ssl.create_default_context(cafile=str(ca))
        self.context.minimum_version=ssl.TLSVersion.TLSv1_3
        self.context.maximum_version=ssl.TLSVersion.TLSv1_3
        self.context.set_alpn_protocols(['http/1.1'])
    def __call__(self,method,path,body,cookie,session,deadline):
        payload=b'' if body is None else canonical(body)
        headers={'Host':self.hostname,'Origin':'https://'+self.hostname,
            'X-WsprryPico-Request':'1','Content-Type':'application/json',
            'Content-Length':str(len(payload)),'Connection':'close'}
        if session: headers['X-WsprryPico-Session']=session
        if cookie: headers['Cookie']=cookie
        wire=(method+' '+path+' HTTP/1.1\r\n'+''.join(k+': '+v+'\r\n' for k,v in headers.items())+'\r\n').encode()+payload
        self.evidence.record('http_send_attempt',raw_hex=wire.hex(),sha256=hashlib.sha256(wire).hexdigest())
        def remaining():
            value=min(10,deadline-time.monotonic());require(value>0,'HTTP absolute deadline');return value
        raw=bytearray()
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as tcp:
            tcp.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,b'wlan2\0')
            tcp.bind(('192.168.4.2',0))
            tcp.settimeout(remaining());tcp.connect((self.address,443))
            with self.context.wrap_socket(tcp,server_hostname=self.hostname) as conn:
                require(conn.version()=='TLSv1.3' and conn.selected_alpn_protocol()=='http/1.1',
                        'verified AP TLS version/ALPN')
                conn.settimeout(remaining());conn.sendall(wire)
                while True:
                    conn.settimeout(remaining());chunk=conn.recv(4096)
                    if not chunk: break
                    raw.extend(chunk);require(len(raw)<=32768,'bounded HTTP response')
        require(time.monotonic()<=deadline,'late HTTP response')
        self.evidence.record('http_receive',raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest())
        head,content=bytes(raw).split(b'\r\n\r\n',1);lines=head.decode('ascii').split('\r\n')
        require(re.fullmatch(r'HTTP/1\.1 [0-9]{3} .*',lines[0]) is not None,'HTTP status line')
        parsed={}
        for line in lines[1:]:
            key,value=line.split(':',1);key=key.lower();require(key not in parsed,'duplicate HTTP header');parsed[key]=value.strip()
        require('transfer-encoding' not in parsed and int(parsed['content-length'])==len(content),'HTTP exact length')
        return int(lines[0].split()[1]),strict(content),parsed


def campaign(exchange,observe,evidence,password,source,boot,address,
             clock=time.monotonic,sleeper=time.sleep,observe_status=None,observe_ap=None):
    require(observe_ap is not None,'independent AP observer required')
    deadline=clock()+110
    def info(expected=None):
        require(clock()<deadline,'whole campaign deadline')
        value=observe();count=guard(value,source,boot,address,observe_ap())
        require(clock()<=deadline,'late INFO')
        if expected is not None: require(count==expected,'retained session count')
        evidence.record('INFO',value=value);return count
    def call(method,path,body=None,cookie=None,session=None):
        require(clock()<deadline,'whole campaign deadline')
        result=exchange(method,path,body,cookie,session,min(deadline,clock()+10))
        require(clock()<=deadline,'late HTTP');return result
    def login():
        code,value,headers=call('POST','/local/v1/login',dict(version=1,device_id=DEVICE,password=password))
        require(code==200 and value['ok'] is True,'login failed; no retry')
        token=headers['set-cookie'].split(';',1)[0]
        require(re.fullmatch(r'__Host-wsprrypico=[0-9a-f]{32}',token) is not None,'cookie shape')
        return token,uuid.uuid4().hex,value['principal']
    def status(auth,expired=False):
        cookie,session,principal=auth
        code,value,_=call('GET','/local/v1/status',cookie=cookie,session=session)
        if expired: require(code==401 and value['error']['code']=='authentication_required','expiry exact refusal')
        else: require(code==200 and value['device_id']==DEVICE and value['principal']==principal,'authenticated identity')
    def logout(auth):
        code,value,_=call('POST','/local/v1/logout',{},auth[0],auth[1])
        require(code==200 and value['ok'] is True,'logout failed; no retry')
    require(observe_status is not None,'authenticated ownership observer required')
    check_status(observe_status(),boot,unowned=True)
    info(0);filled=clock();sessions=[login() for _ in range(4)]
    require(clock()-filled<15,'pressure population expired before observation')
    require(len({a[0] for a in sessions})==4,'unique session cookies');info(4)
    code,value,_=call('POST','/local/v1/login',dict(version=1,device_id=DEVICE,password=password))
    require(code==409 and value['error']['code']=='busy','fifth session exact capacity refusal')
    info(4)
    for auth in sessions: logout(auth)
    info(0);evidence.record('capacity_reclamation_pass',maximum=4)
    idle=login();status(idle);sleeper(17);status(idle,expired=True);info(0)
    evidence.record('idle_expiry_pass',inactivity_ms=15000)
    absolute=login();started=clock()
    # Keep activity strictly inside the idle interval; finish beyond absolute TTL.
    for tick in range(1,7):
        # Schedule from original login acknowledgement, not the prior reply.
        # HTTP latency must not accumulate into the unchanged 65s bracket.
        sleeper(max(0,started+tick*10-clock()))
        require(clock()-started<=65,'absolute cadence delayed')
        if tick==6 or clock()-started>=60: break
        status(absolute)
    sleeper(2);status(absolute,expired=True);info(0)
    evidence.record('absolute_expiry_pass',absolute_ms=60000)
    check_status(observe_status(),boot,unowned=True)
    evidence.record('session_campaign_complete',rf_jobs=0,simulator_jobs=0,
        owner_grace='PENDING',full_composition_qualified=False,physical_acceptance=False)


def run_device(candidate,manifest,address,boot,hostname,ca,password,evidence_path,observe_info,observe_status,observe_ap):
    """Parent-authorized API after exact candidate verify/program/readback proof."""
    require(candidate in manifest['candidates'] and candidate['role']=='session_deadline' and
            candidate['target']=='WsprryPico' and candidate['fault_stage']==0 and
            candidate['lan_mode'] in ('plain','tls') and
            re.fullmatch('[0-9a-f]{64}',candidate['uf2']['sha256']) is not None,
            'verified engineering session candidate')
    require(re.fullmatch('[0-9a-f]{40}',manifest['source_commit']) is not None and
            re.fullmatch('[0-9a-f]{32}',boot) is not None,'source and boot binding')
    evidence=Evidence(evidence_path)
    try:
        evidence.record('candidate_binding',source_commit=manifest['source_commit'],
                        image_sha256=candidate['uf2']['sha256'],device_id=DEVICE,boot_id=boot)
        campaign(HTTPS(address,hostname,ca,evidence),observe_info,evidence,password,
                 manifest['source_commit'],boot,address,observe_status=observe_status,observe_ap=observe_ap)
    except BaseException as error:
        evidence.record('session_campaign_failed',error=type(error).__name__,retry=False)
        raise
    finally:evidence.close()
