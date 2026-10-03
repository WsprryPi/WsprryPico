#!/usr/bin/env python3
"""Two read-only WTP exchanges retaining exact frames for offline authority audit."""
import hashlib
import json
import socket
import struct
import time
import uuid
from phase12_recovery_device import DEVICE,strict,require
from validate_wtp_contract import frame,crc32c


def capture(stream,boot,elapsed,carrier):
    deadline=time.monotonic()+20
    session=uuid.uuid4().hex;exchanges=[];events=[];begin=elapsed()
    def exact(size):
        value=bytearray()
        while len(value)<size:
            remaining=deadline-time.monotonic();require(remaining>0,'authority deadline')
            stream.settimeout(remaining);part=stream.recv(size-len(value));require(part,'authority EOF')
            value.extend(part)
        return bytes(value)
    for operation in ('HELLO','STATUS'):
        body=dict(versions=['WTP/1'],client_name='phase12-final-authority',client_version='1') if operation=='HELLO' else {}
        message=dict(type='request',protocol='WTP/1',session_id=session,request_id=uuid.uuid4().hex,op=operation,body=body)
        request=frame(json.dumps(message,separators=(',',':')).encode())
        remaining=deadline-time.monotonic();require(remaining>0,'authority send deadline')
        stream.settimeout(remaining);stream.sendall(request)
        while True:
            header=exact(16);magic,length,crc=struct.unpack('>8sII',header)
            require(magic==b'WTPF\x01\x01\x00\x00' and 0<length<=65536,'authority frame bound')
            payload=exact(length);require(crc32c(payload)==crc,'authority CRC');value=strict(payload)
            require(value['protocol']=='WTP/1' and value['session_id']==session,'authority session')
            if value['type']=='event':
                require(len(events)<64 and value['boot_id']==boot,'authority event bound/boot')
                events.append((header+payload).hex());continue
            require(value['type']=='response' and value['request_id']==message['request_id'] and
                    value['op']==operation and value['ok'] is True,'authority correlation')
            status=value['body']
            if operation=='HELLO':
                require(status['device_id']==DEVICE and status['boot_id']==boot and status['selected_version']=='WTP/1','authority HELLO')
            else:
                require(status['boot_id']==boot and status['owner_id'] is None and status['job_id'] is None and
                        status['state']=='empty' and status['output_active'] is False,'authority inactive empty unowned')
            exchanges.append(dict(request_hex=request.hex(),response_hex=(header+payload).hex()));break
    return dict(schema='phase12-final-authority/1',carrier=carrier,elapsed_start_s=begin,elapsed_end_s=elapsed(),
                exchanges=exchanges,events=events)
