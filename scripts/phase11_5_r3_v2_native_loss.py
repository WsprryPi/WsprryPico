"""Bounded task-owned native socket loss, admitted only after raw ARM ACK.

This is a prospective helper. It is not a standalone runnable packet and never
sends a Pico request. Prefix inspection does not claim a complete TLS audit.
"""
import json
import ctypes
import os
import platform
import re
import socket
import struct
import subprocess
from pathlib import Path
from phase11_5_inventory import require
from audit_phase11_5_idle import frames
from validate_wtp_contract import SchemaValidator


def acknowledged_arm_prefix(data,pid,binding,packet):
    schema=json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text())
    validator=SchemaValidator(schema)
    sequence=0;last=0;active={};writes={};buffers={};pending={};acks=[]
    while len(data)>=64:
        magic,seq,kind,cid,mono,utc,process,length=struct.unpack('>8s7Q',data[:64])
        require(magic==b'P115TLS2' and seq==sequence and mono>=last and process==pid and
            utc>0 and length<=65552,'Native prefix record identity')
        if len(data)<64+length:break
        payload=data[64:64+length];data=data[64+length:];sequence+=1;last=mono
        if seq==0:require(kind==cid==length==0,'Native observer start');continue
        if kind==1:
            require(cid not in active and not payload,'Native prefix connection');active[cid]=False
        elif kind==2:
            require(cid in active and payload.hex()==packet['peer_sha256'],'Native prefix certificate');active[cid]=True
        elif kind==7:
            require(active.get(cid) is True and cid not in writes and payload,'Native prefix write entry');writes[cid]=payload
        elif kind==8:
            require(cid in writes and not payload,'Native prefix failed write');writes.pop(cid)
        elif kind in [3,4]:
            require(active.get(cid) is True and payload,'Native prefix authenticated bytes')
            if kind==3:require(cid in writes and writes.pop(cid).startswith(payload),'Native prefix written bytes')
            key=(cid,kind);messages,buffers[key]=frames(buffers.get(key,b'')+payload)
            for message in messages:
                require(not validator.errors(message,schema) and message['session_id']==binding['session_id'],
                    'Native prefix schema/session')
                token=(cid,message.get('request_id'))
                if kind==3:
                    require(message['type']=='request' and token not in pending,'Native prefix request')
                    pending[token]=message
                elif message['type']=='response':
                    require(token in pending,'Native prefix response without request');request=pending.pop(token)
                    require(request['op']==message['op'] and message['ok'] is True,'Native prefix rejected response')
                    if message['op']=='ARM':
                        require(request['body']['job_id']==message['body']['job_id']==binding['job_id'] and
                            request['body']['start_utc_ns']==message['body']['start_utc_ns']==binding['start_utc_ns'] and
                            message['body']['state']=='armed','Native acknowledged ARM identity')
                        acks.append(dict(connection_id=cid,ack_monotonic_ns=mono,request=request,response=message))
                else:require(message['type']=='event' and message['boot_id']==packet['boot_id'],'Native prefix event')
        elif kind==5:
            require(cid in active and not payload,'Native prefix close');active.pop(cid)
        else:raise ValueError('Native prefix unexpected record')
    require(len(acks)<=1,'Native ARM repeated')
    if not acks:return None
    require(acks[0]['connection_id'] in active,'Native acknowledged connection already closed')
    # Never choose a cut point with a mutating request or partial write in flight.
    if writes or any(buffers.get((cid,3),b'') for cid in active) or any(
        q['op'] not in ['HELLO','CAPS','STATUS','GET_CLOCK','PING'] for q in pending.values()):return None
    return acks[0]


def socket_identity(text,pid):
    lines=[line.split() for line in text.splitlines() if line.strip()]
    require(len(lines)==1,'Exactly one native target socket required')
    row=lines[0]
    require(len(row)>=6 and row[0]=='ESTAB' and row[4]=='10.77.15.10:18443' and
        re.fullmatch(r'10\.77\.15\.2:[0-9]+',row[3]) is not None,'Native target socket tuple')
    owners=re.findall(r'pid=(\d+),fd=(\d+)', ' '.join(row[5:]))
    require(len(owners)==1 and int(owners[0][0])==pid,'Socket owned by another process')
    return dict(local_address='10.77.15.2',local_port=int(row[3].rsplit(':',1)[1]),
        peer_address='10.77.15.10',peer_port=18443,pid=pid,fd=int(owners[0][1]))


def drop_native_socket(pid,emit,mechanism='ss-destroy-v1'):
    query=['ss','-Hntp','dst','10.77.15.10','dport','=','18443']
    raw=subprocess.check_output(query,text=True,timeout=3)
    identity=socket_identity(raw,pid)
    require(Path(f'/proc/{pid}/fd/{identity["fd"]}').readlink().as_posix().startswith('socket:['),
        'Native descriptor no longer a socket')
    emit('transport_loss_pending',dict(identity=identity,ss_before=raw))
    if mechanism=='pidfd-duplicate-shutdown-v1':
        require(platform.system()=='Linux' and platform.machine()=='aarch64','Reviewed pidfd syscall architecture')
        original=Path(f'/proc/{pid}/fd/{identity["fd"]}').readlink().as_posix()
        pidfd=os.pidfd_open(pid)
        try:
            libc=ctypes.CDLL(None,use_errno=True)
            fd=libc.syscall(438,pidfd,identity['fd'],0) # Linux aarch64 pidfd_getfd
            require(fd>=0,'Native pidfd_getfd failed: '+str(ctypes.get_errno()))
            with socket.socket(fileno=fd) as stream:
                local=list(stream.getsockname());peer=list(stream.getpeername())
                duplicate=Path(f'/proc/self/fd/{fd}').readlink().as_posix()
                require(duplicate==original and local==[identity['local_address'],identity['local_port']] and
                    peer==[identity['peer_address'],identity['peer_port']],'Native duplicated socket identity changed')
                stream.shutdown(socket.SHUT_RDWR)
            emit('transport_loss_result',dict(identity=identity,mechanism=mechanism,
                local=local,peer=peer,socket_inode=original,shutdown='SHUT_RDWR',returncode=0))
        finally:os.close(pidfd)
        return identity
    require(mechanism=='ss-destroy-v1','Undeclared native loss mechanism')
    command=['ss','-K','dst','10.77.15.10','dport','=','18443','src','10.77.15.2','sport','=',str(identity['local_port'])]
    result=subprocess.run(command,capture_output=True,text=True,timeout=3)
    emit('transport_loss_result',dict(identity=identity,argv=command,returncode=result.returncode,
        stdout=result.stdout,stderr=result.stderr))
    require(result.returncode==0 and not result.stderr.strip() and
        not subprocess.check_output(query,text=True,timeout=3).strip(),'Native scoped socket loss failed')
    return identity
