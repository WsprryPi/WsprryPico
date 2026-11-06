"""Strict WTP replies with explicitly validated advisory events, never silent skips."""
import json
import struct
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_wtp_contract import SchemaValidator, loads_strict, validate_message_semantics, crc32c
from wtp_monitor import MAGIC, HEADER_SIZE, MAX_PAYLOAD
_SCHEMA=json.loads((Path(__file__).resolve().parents[1]/'engineering/protocol/wtp-1.schema.json').read_text())
_VALIDATOR=SchemaValidator(_SCHEMA)


class ReplyCollector:
    def __init__(self, session):
        self.session=session
        self.reset()

    def reset(self):
        self.boot=None
        self.last_event=-1
        self.gap=False

    def accept(self, payloads, request_id, operation):
        reply=None
        for payload in payloads:
            message=loads_strict(payload.decode('utf-8',errors='strict'))
            errors=_VALIDATOR.errors(message,_SCHEMA)
            if errors:raise ValueError('Invalid current WTP message: '+str(errors[:3]))
            errors=validate_message_semantics(message)
            if errors:raise ValueError('Invalid current WTP semantics: '+str(errors[:3]))
            if message['type']=='event':
                if self.boot is None or message['session_id']!=self.session or message['boot_id']!=self.boot:
                    raise ValueError('Advisory event session/boot binding mismatch')
                identifier=int(message['event_id'])
                if identifier<=self.last_event:raise ValueError('Stale or duplicate advisory event')
                self.gap |= identifier!=self.last_event+1
                self.last_event=identifier
                continue
            if message['type']!='response' or (message['session_id'],message['request_id'],message['op'])!=(self.session,request_id,operation):
                raise ValueError('Unexpected or stale WTP response correlation')
            if reply is not None:raise ValueError('Duplicate WTP response')
            reply=message
            if operation=='HELLO' and message['ok']:self.boot=message['body']['boot_id']
        return reply


class StrictFrameDecoder:
    """Exact network framing. Operator monitor resynchronization is not a test oracle."""
    def __init__(self):self.buffer=bytearray()
    def feed(self, data):
        if len(data)>HEADER_SIZE+MAX_PAYLOAD:raise ValueError('Network frame input exceeds bounded read size')
        self.buffer.extend(data)
        payloads=[]
        while self.buffer:
            if not MAGIC.startswith(bytes(self.buffer[:len(MAGIC)])):
                raise ValueError('Unexpected network frame magic; refusing resynchronization')
            if len(self.buffer)<HEADER_SIZE:break
            version,encoding,flags,length,checksum=struct.unpack('>BBHII',self.buffer[4:HEADER_SIZE])
            if version!=1 or encoding!=1 or flags!=0 or not 1<=length<=MAX_PAYLOAD:
                raise ValueError('Invalid current network frame header')
            if len(self.buffer)<HEADER_SIZE+length:break
            payload=bytes(self.buffer[HEADER_SIZE:HEADER_SIZE+length])
            if crc32c(payload)!=checksum:raise ValueError('Invalid network frame checksum')
            del self.buffer[:HEADER_SIZE+length]
            payloads.append(payload)
        return payloads
