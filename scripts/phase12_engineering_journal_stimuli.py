#!/usr/bin/env python3
"""Owned B12J stimuli; import is inert and no socket/device is created here.

The existing private responder supplies sendto. Immutable attempts are consumed
before sending, so an uncertain send is never replayed. The seed builder only
changes one payload byte; production native inspection is an independent gate.
"""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import pwd
import re
import struct
import time
import zlib

DEVICE='29f20b7342051ef947aa56cb9d4fab42'
SIZE=4194304
BASE=0x3f7000
SLOT=8192
PAGE=256
ADDRESS='192.168.84.1'
FILES=('journal-stale-arm.json','journal-stale-old-bind.json','journal-stale-old.json',
       'journal-stale-hold.json','journal-stale-new-bind.json','journal-stale-attempt.json',
       'journal-stale-sent.json','journal-stale-release.json')


def require(value,message):
    if not value:raise ValueError(message)


def strict(raw):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'duplicate JSON member');result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON')))


def digest(raw):return hashlib.sha256(raw).hexdigest()


def unsigned(value,message):
    require(type(value) is int and 0<=value<2**64,message)
    return value


def original(path,limit=65536):
    path=Path(path)
    require(path.is_file() and not path.is_symlink() and 0<path.stat().st_size<=limit,'bounded regular original')
    return path.read_bytes()


def publish(path,value):
    """Exclusive, flushed original. Partial publication prevents future admission."""
    path=Path(path)
    require(not path.exists() and not path.is_symlink(),'immutable stimulus already exists')
    with path.open('xb') as stream:
        os.chmod(path,0o600)
        stream.write(json.dumps(value,sort_keys=True,separators=(',',':')).encode()+b'\n')
        stream.flush();os.fsync(stream.fileno())
    if os.geteuid()==0:
        user=pwd.getpwnam('pi');os.chown(path,user.pw_uid,user.pw_gid)
    directory=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(directory)
    finally:os.close(directory)


def info_binding(raw,source,generation,boot=None):
    value=strict(raw);status=value['status'];network=value['network']
    require(value['device_id']==DEVICE and value['revision']==source[:12] and
            re.fullmatch('[0-9a-f]{40}',source) and
            re.fullmatch('[0-9a-f]{32}',status['boot_id']),'stimulus exact B/source/boot')
    require(type(generation) is int and 0<generation<2**64 and
            value['provisioning_generation']==str(generation) and
            value['provisioning_source']=='provisioned' and value['lan_wtp_mode']=='engineering-tls',
            'stimulus profile authority')
    require(status['engine']=='inhibited-standalone-simulator' and status['output_active'] is False and
            status['enabled'] is False and status['state']=='empty' and status['owner_id'] is None and
            status['job_id'] is None and status['storage_healthy'] is True and value['access_state']=='healthy',
            'stimulus inactive empty unowned inhibited')
    require(boot is None or status['boot_id']==boot,'stimulus same boot')
    peer=ipaddress.IPv4Address(network['ipv4'])
    unsigned(network['accepted'],'exact accepted counter')
    unsigned(network['rejected'],'exact rejected counter')
    require(network['link_status']==3 and peer in ipaddress.IPv4Network(ADDRESS+'/24',strict=False) and
            str(peer) not in (ADDRESS,'192.168.84.0','192.168.84.255') and
            network['ntp_server']==ADDRESS,'owned station/time source')
    return value


def arm(root,source,generation,remaining_s,*,clock=time.monotonic):
    root=Path(root)
    require(type(remaining_s) in (int,float) and 0<remaining_s<=90,'unchanged stale observation budget')
    require(re.fullmatch('[0-9a-f]{40}',source) and type(generation) is int and 0<generation<2**64-1,'arm source/generation')
    require(all(not (root/name).exists() and not (root/name).is_symlink() for name in FILES),'one fresh stimulus only')
    start=clock()
    value=dict(schema='phase12-journal-stale/1',root=str(root),source_commit=source,
               old_generation=generation,start_monotonic_s=start,end_monotonic_s=start+remaining_s,
               old_datagrams_maximum=1,rf_jobs=0)
    publish(root/FILES[0],value)
    return dict(status='STIMULUS_ARMED',arm_sha256=digest(original(root/FILES[0])),end_monotonic_s=value['end_monotonic_s'])


def state(root,*,clock=time.monotonic):
    raw=original(Path(root)/FILES[0]);value=strict(raw)
    require(value['schema']=='phase12-journal-stale/1' and value['root']==str(root) and
            type(value['old_datagrams_maximum']) is int and value['old_datagrams_maximum']==1 and
            type(value['rf_jobs']) is int and value['rf_jobs']==0 and
            re.fullmatch('[0-9a-f]{40}',value['source_commit']) and
            type(value['old_generation']) is int and 0<value['old_generation']<2**64-1 and
            type(value['start_monotonic_s']) in (int,float) and type(value['end_monotonic_s']) in (int,float) and
            0<value['end_monotonic_s']-value['start_monotonic_s']<=90 and
            value['start_monotonic_s']<=clock()<value['end_monotonic_s'],'original stimulus deadline')
    return value,digest(raw)


def chain(root,through,*,clock=time.monotonic):
    """Revalidate retained raw wires and every parent link before any send."""
    root=Path(root);value,arm_sha=state(root,clock=clock)
    levels=('old_bind','old','hold','new_bind','attempt','sent','release')
    require(through in levels,'named chain boundary');result={}
    generation=value['old_generation'];source=value['source_commit'];previous=value['start_monotonic_s']
    for name,filename in zip(levels,FILES[1:]):
        raw=original(root/filename);record=strict(raw);result[name]=(record,digest(raw))
        if name not in ('sent',):require(record['arm_sha256']==arm_sha,'original chain arm')
        if name in ('old_bind','hold','new_bind','release'):
            wire=bytes.fromhex(record['info_raw_hex'])
            require(record['info_sha256']==digest(wire),'original INFO hash')
            new=name in ('new_bind','release')
            expected_boot=None if name in ('old_bind','new_bind') else result['new_bind' if new else 'old_bind'][0]['boot_id']
            info=info_binding(wire,source,generation+new,expected_boot)
            if name in ('old_bind','new_bind'):
                require(record['boot_id']==info['status']['boot_id'] and record['peer']==info['network']['ipv4'],
                        'original INFO boot/peer projection')
            if name!='hold':
                require(info['status']['clock_state']=='unsynchronized' and info['network']['accepted']==0,
                        'original unadopted clock')
            if name=='old_bind':require(info['network']['rejected']==0,'fresh old clock counters')
            if name=='hold':
                require(record['old_sha256']==result['old'][1] and info['status']['clock_state']=='synchronized' and
                        info['network']['accepted']>0,'original A clock/capture hold')
            if name=='new_bind':
                require(record['hold_sha256']==result['hold'][1] and info['status']['boot_id']!=result['old_bind'][0]['boot_id'] and
                        info['network']['rejected']==0,'original fresh B epoch')
            if name=='release':
                require(record['attempt_sha256']==result['attempt'][1] and record['sent_sha256']==result['sent'][1] and
                        info['network']['rejected']==1,'original rejection release')
            stamp=record['monotonic_s']
        elif name=='old':
            query=bytes.fromhex(record['query_hex']);reply=bytes.fromhex(record['response_hex'])
            require(record['old_bind_sha256']==result['old_bind'][1] and record['peer'][0]==result['old_bind'][0]['peer'] and
                    len(query)==48 and query[0]==0x23 and query[40:48]!=bytes(8) and len(reply)==48 and
                    record['query_sha256']==digest(query) and record['response_sha256']==digest(reply), 'original captured query/reply')
            utc=record['utc_ns'];require(type(utc) is int and 0<=utc<(2**32-2208988800)*10**9,'original era-zero UTC')
            seconds,nanos=divmod(utc,10**9);timestamp=struct.pack('>II',seconds+2208988800,(nanos<<32)//10**9)
            expected=bytearray(48);expected[:4]=bytes([0x24,1,6,236]);expected[8:12]=struct.pack('>I',66)
            expected[12:16]=b'LOCL';expected[16:24]=timestamp;expected[24:32]=query[40:48]
            expected[32:40]=expected[40:48]=timestamp
            require(reply==bytes(expected),'exact retained responder reply')
            stamp=record['received_monotonic_s']
        elif name=='attempt':
            query=bytes.fromhex(record['new_query_hex']);old=result['old'][0]
            require(record['new_bind_sha256']==result['new_bind'][1] and record['old_sha256']==result['old'][1] and
                    record['old_response_sha256']==old['response_sha256'] and record['peer'][0]==result['new_bind'][0]['peer'] and
                    type(record['peer'][1]) is int and 0<record['peer'][1]<=65535 and
                    type(record['datagram_attempts']) is int and record['datagram_attempts']==1 and record['rf_jobs']==0 and
                    len(query)==48 and query[0]==0x23 and query[40:48]!=bytes(8) and
                    query[40:48]!=bytes.fromhex(old['query_hex'])[40:48] and record['new_query_sha256']==digest(query),
                    'original one-use distinct new query/attempt')
            received=record['received_monotonic_s'];stamp=record['send_attempt_monotonic_s']
            require(type(received) in (int,float) and previous<=received<=stamp and stamp-received<.5,'original immediate send bracket')
        else:
            attempt=result['attempt'][0];stamp=record['completed_monotonic_s']
            require(record['attempt_sha256']==result['attempt'][1] and type(record['sent_bytes']) is int and
                    record['sent_bytes']==48 and type(record['datagram_attempts']) is int and record['datagram_attempts']==1 and
                    stamp-attempt['received_monotonic_s']<.5,'original exact completed send')
        require(type(stamp) in (int,float) and previous<=stamp<value['end_monotonic_s'],'original chain monotonic order/deadline')
        previous=stamp
        if name==through:break
    return result


def control(root,operation,raw=None,*,clock=time.monotonic):
    root=Path(root);value,arm_sha=state(root,clock=clock)
    if operation=='old_bind':
        info=info_binding(raw,value['source_commit'],value['old_generation'])
        require(info['status']['clock_state']=='unsynchronized' and int(info['network']['accepted'])==0,
                'fresh A unsynchronized before capture')
        publish(root/FILES[1],dict(arm_sha256=arm_sha,info_raw_hex=raw.hex(),info_sha256=digest(raw),
            boot_id=info['status']['boot_id'],peer=info['network']['ipv4'],monotonic_s=clock()))
    elif operation=='hold':
        originals=chain(root,'old',clock=clock)
        bound=originals['old_bind'][0];old=originals['old'][0]
        info=info_binding(raw,value['source_commit'],value['old_generation'],bound['boot_id'])
        require(old['arm_sha256']==arm_sha and old['old_bind_sha256']==digest(original(root/FILES[1])) and
                old['peer'][0]==info['network']['ipv4'] and int(info['network']['accepted'])>0 and
                info['status']['clock_state']=='synchronized','actual A reply and clock before hold')
        publish(root/FILES[3],dict(arm_sha256=arm_sha,old_sha256=digest(original(root/FILES[2])),
            info_raw_hex=raw.hex(),info_sha256=digest(raw),monotonic_s=clock()))
    elif operation=='new_bind':
        originals=chain(root,'hold',clock=clock)
        old_bind=originals['old_bind'][0];hold=originals['hold'][0]
        info=info_binding(raw,value['source_commit'],value['old_generation']+1)
        require(hold['arm_sha256']==arm_sha and info['status']['boot_id']!=old_bind['boot_id'] and
                info['status']['clock_state']=='unsynchronized' and int(info['network']['accepted'])==0 and
                int(info['network']['rejected'])==0,'fresh B before one stale datagram')
        publish(root/FILES[4],dict(arm_sha256=arm_sha,hold_sha256=digest(original(root/FILES[3])),
            info_raw_hex=raw.hex(),info_sha256=digest(raw),boot_id=info['status']['boot_id'],
            peer=info['network']['ipv4'],monotonic_s=clock()))
    elif operation=='release':
        originals=chain(root,'sent',clock=clock)
        bound=originals['new_bind'][0];attempt=originals['attempt'][0];sent=originals['sent'][0]
        info=info_binding(raw,value['source_commit'],value['old_generation']+1,bound['boot_id'])
        require(attempt['arm_sha256']==arm_sha and sent['attempt_sha256']==digest(original(root/FILES[5])) and
                sent['sent_bytes']==48 and info['status']['clock_state']=='unsynchronized' and
                int(info['network']['accepted'])==0 and int(info['network']['rejected'])==1,
                'one stale reply rejected without adopting time')
        publish(root/FILES[7],dict(arm_sha256=arm_sha,attempt_sha256=digest(original(root/FILES[5])),
            sent_sha256=digest(original(root/FILES[6])),info_raw_hex=raw.hex(),info_sha256=digest(raw),monotonic_s=clock()))
    else:raise ValueError('named one-use stimulus control')
    state(root,clock=clock)
    return dict(status='STIMULUS_'+operation.upper(),arm_sha256=arm_sha,rf_jobs=0)


def respond(root,query,peer,fresh_reply,send,*,utc_ns,clock=time.monotonic):
    """Called only by the existing owned socket. No timer/retry/socket here."""
    root=Path(root)
    # The proof's immutable release completes within its original deadline.
    # Later ordinary replies use the pre-existing responder lifetime, without
    # reopening or extending this one-use proof.
    if (root/FILES[7]).exists():
        released=strict(original(root/FILES[7]))
        chain(root,'release',clock=lambda:released['monotonic_s'])
        return 'normal'
    value,arm_sha=state(root,clock=clock)
    require(type(query) is bytes and len(query)==48 and query[0]==0x23 and query[40:48]!=bytes(8) and
            type(fresh_reply) is bytes and len(fresh_reply)==48 and fresh_reply[24:32]==query[40:48],
            'actual supported correlated query/reply')
    require(type(peer[1]) is int and 0<peer[1]<=65535,'actual source UDP port')
    if not (root/FILES[1]).exists():return 'held'
    if not (root/FILES[3]).exists():
        chain(root,'old' if (root/FILES[2]).exists() else 'old_bind',clock=clock)
        bound_raw=original(root/FILES[1]);bound=strict(bound_raw)
        require(bound['arm_sha256']==arm_sha,'original old binding')
        if peer[0]!=bound['peer']:return 'held'
        if not (root/FILES[2]).exists():
            publish(root/FILES[2],dict(arm_sha256=arm_sha,old_bind_sha256=digest(bound_raw),peer=list(peer),
                query_hex=query.hex(),response_hex=fresh_reply.hex(),query_sha256=digest(query),
                response_sha256=digest(fresh_reply),utc_ns=utc_ns,received_monotonic_s=clock()))
        return 'normal'
    if not (root/FILES[4]).exists() or (root/FILES[5]).exists():return 'held'
    chain(root,'new_bind',clock=clock)
    bound_raw=original(root/FILES[4]);bound=strict(bound_raw)
    if peer[0]!=bound['peer']:return 'held'
    old_raw=original(root/FILES[2]);old=strict(old_raw);old_reply=bytes.fromhex(old['response_hex'])
    require(old['arm_sha256']==arm_sha and old['response_sha256']==digest(old_reply) and
            old_reply[24:32]==bytes.fromhex(old['query_hex'])[40:48] and
            query[40:48]!=old_reply[24:32],'distinct actual new nonce and exact old reply')
    attempted=clock()
    publish(root/FILES[5],dict(arm_sha256=arm_sha,new_bind_sha256=digest(bound_raw),old_sha256=digest(old_raw),
        old_response_sha256=digest(old_reply),peer=list(peer),new_query_hex=query.hex(),new_query_sha256=digest(query),
        received_monotonic_s=attempted,send_attempt_monotonic_s=clock(),datagram_attempts=1,rf_jobs=0))
    # Durability happens before the only send. Failure/uncertainty consumes it.
    state(root,clock=clock)
    require(clock()-attempted<.5,'bounded immediate stale send')
    count=send(old_reply,peer)
    completed=clock()
    require(completed<value['end_monotonic_s'] and completed-attempted<.5 and count==48,'bounded exact stale send')
    publish(root/FILES[6],dict(attempt_sha256=digest(original(root/FILES[5])),sent_bytes=count,
        completed_monotonic_s=completed,datagram_attempts=1))
    return 'stale'


def committed_bank(raw,index):
    base=BASE+index*SLOT;header=raw[base:base+PAGE];commit=raw[base+SLOT-PAGE:base+SLOT]
    hm,sequence,length,version=struct.unpack_from('<QQII',header)
    cm,committed=struct.unpack_from('<QQ',commit)
    require(hm==0x3146525050435057 and cm==0x31544d4d4f435057 and sequence==committed and
            0<sequence<2**64 and 16<length<=7184 and version==2,'two complete source-selection banks')
    require(zlib.crc32(header[:-4])==struct.unpack_from('<I',header,PAGE-4)[0] and
            zlib.crc32(commit[:-4])==struct.unpack_from('<I',commit,PAGE-4)[0],'original header/commit CRC')
    payload=raw[base+PAGE:base+PAGE+length]
    require(hashlib.sha256(payload).digest()==header[24:56]==commit[16:48] and
            struct.unpack_from('<Q',payload)[0]==0x324c455350435057 and payload[8]==1 and
            payload[9:16]==bytes(7),'original committed runtime payload/digest')
    return dict(index=index,base=base,sequence=sequence,payload=payload[16:],payload_sha256=digest(payload[16:]))


def corrupt_newest(raw,expected_profile,expected_generation):
    require(type(raw) is bytes and len(raw)==SIZE and type(expected_profile) is bytes and
            type(expected_generation) is int and 1<expected_generation<2**64,'exact corruption inputs')
    banks=[committed_bank(raw,index) for index in (0,1)]
    require(banks[0]['sequence']!=banks[1]['sequence'],'unique original bank generations')
    newest=max(banks,key=lambda bank:bank['sequence']);older=min(banks,key=lambda bank:bank['sequence'])
    require(newest['sequence']==expected_generation and newest['payload']==expected_profile and
            older['sequence']==expected_generation-1 and older['payload']!=expected_profile,
            'selected exact C and intact preceding B')
    offset=newest['base']+PAGE+16
    result=bytearray(raw);result[offset]^=1;seed=bytes(result)
    require(seed[:offset]==raw[:offset] and seed[offset+1:]==raw[offset+1:] and
            seed[offset]^raw[offset]==1 and seed[0x3ff000:]==raw[0x3ff000:],'one payload byte only/E10 exact')
    receipt=dict(schema='phase12-journal-corrupt-newest/1',input_sha256=digest(raw),output_sha256=digest(seed),
        byte_offset=offset,xor=1,newest_bank=newest['index'],newest_generation=newest['sequence'],
        older_bank=older['index'],older_generation=older['sequence'],newest_profile_sha256=digest(expected_profile),
        older_profile_sha256=older['payload_sha256'],header_commit_older_and_all_other_bytes_equal=True,
        e10_sha256=digest(raw[0x3ff000:]),rf_jobs=0)
    return seed,receipt


def fault_info(raw,source,previous_boot):
    info=strict(raw);status=info['status']
    require(info['device_id']==DEVICE and info['revision']==source[:12] and
            re.fullmatch('[0-9a-f]{40}',source) and re.fullmatch('[0-9a-f]{32}',status['boot_id']) and
            status['boot_id']!=previous_boot,'fresh exact fault B boot')
    require(info['provisioning_source']=='fault' and info['provisioning_generation']=='0' and
            type(info['provisioning_fault']) is int and info['provisioning_fault']==1 and info['lan_wtp_ready'] is False and
            info['network']['ipv4'] in ('','0.0.0.0') and info['network']['link_status']!=3,
            'explicit profile storage fault without old station/TLS authority')
    require(status['engine']=='inhibited-standalone-simulator' and status['output_active'] is False and
            status['enabled'] is False and status['state']=='empty' and status['owner_id'] is None and
            status['job_id'] is None and status['storage_healthy'] is True and info['access_state']=='healthy',
            'fault admission guard: inactive empty unowned inhibited, unrelated storage healthy')
    return info
