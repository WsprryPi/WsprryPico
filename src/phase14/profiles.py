"""Offline journal framing for explicit, reversible Phase 14 profile experiments."""
import hashlib
import json
import struct
import zlib

HEADER=0x3146525050435057
COMMIT=0x31544d4d4f435057
SELECTION=0x324c455350435057


def durable_settings(info):
    from led_closeout.device import retained_settings
    value=retained_settings(info)
    # Scheduler::last_job_ is an in-memory display, empty after a reboot. The
    # separately persisted no-repeat cursor must still compare exactly.
    del value['config']['last_job']
    return value


def restoration_payload(original):
    if type(original) is not bytes or len(original)!=32768:
        raise ValueError('exact original profile/configuration/cursor region required')
    # Profile 16 KiB + configuration 8 KiB. Never rewrite the current cursor
    # at 0x103fd000..0x103fefff from a pre-experiment settings snapshot.
    return original[:24576]


def restoration_settings(original_info,current_info):
    expected=durable_settings(original_info)
    original=int(expected['config']['watermark_utc_ns'])
    current=int(current_info['status']['watermark_utc_ns'])
    if current<original:raise ValueError('current standalone cursor rolled back')
    expected['config']['watermark_utc_ns']=current_info['status']['watermark_utc_ns']
    return expected


def profile(data):
    if len(data)!=16384:raise ValueError('exact profile region required')
    records=[]
    for slot in range(2):
        raw=data[slot*8192:(slot+1)*8192]
        if raw==b'\xff'*8192:continue
        header,commit=raw[:256],raw[-256:]
        hm,sequence,size,version=struct.unpack_from('<QQII',header)
        cm,committed=struct.unpack_from('<QQ',commit)
        payload=raw[256:256+size]
        digest=hashlib.sha256(payload).digest()
        if (hm!=HEADER or cm!=COMMIT or sequence==0 or sequence!=committed or
            not 16<size<=7184 or version!=2 or header[24:56]!=digest or commit[16:48]!=digest or
            zlib.crc32(header[:-4])!=struct.unpack_from('<I',header,252)[0] or
            zlib.crc32(commit[:-4])!=struct.unpack_from('<I',commit,252)[0] or
            struct.unpack_from('<Q',payload)[0]!=SELECTION or payload[8] not in (1,4,5)):
            raise ValueError('invalid or ambiguous profile journal; no rollback')
        records.append((sequence,payload[8],json.loads(payload[16:])))
    if not records or len({v[0] for v in records})!=len(records):
        raise ValueError('profile sequence ambiguity')
    return max(records,key=lambda v:v[0])


def engineering_record(sequence,value):
    if type(sequence) is not int or not 0<sequence<2**64:
        raise ValueError('profile sequence range')
    payload=struct.pack('<Q',SELECTION)+bytes([1])+bytes(7)+json.dumps(value,separators=(',',':')).encode()
    if not 16<len(payload)<=7184:raise ValueError('profile payload size')
    digest=hashlib.sha256(payload).digest();record=bytearray(b'\xff'*16384)
    header,commit=bytearray(b'\xff'*256),bytearray(b'\xff'*256)
    struct.pack_into('<QQII',header,0,HEADER,sequence,len(payload),2);header[24:56]=digest
    struct.pack_into('<QQ',commit,0,COMMIT,sequence);commit[16:48]=digest
    for block in (header,commit):struct.pack_into('<I',block,252,zlib.crc32(block[:-4]))
    record[:256]=header;record[256:256+len(payload)]=payload;record[7936:8192]=commit
    if profile(record)!=(sequence,1,value):raise ValueError('profile encoding mismatch')
    return bytes(record)
