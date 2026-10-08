"""Private loopback byte relay to retain the installed controller's exact WTP job."""
import json
from pathlib import Path
import select
import socket
import struct
import threading
from validate_wtp_contract import crc32c,loads_strict,SchemaValidator


def messages(raw,schema):
    result=[];validator=SchemaValidator(schema)
    while raw:
        if len(raw)<16:raise ValueError('truncated controller WTP header')
        magic,version,encoding,flags,size,crc=struct.unpack('>4sBBHII',raw[:16])
        if (magic,version,encoding,flags)!=(b'WTPF',1,1,0) or not 1<=size<=65536 or len(raw)<16+size:
            raise ValueError('invalid controller WTP frame')
        payload=raw[16:16+size];raw=raw[16+size:]
        if crc32c(payload)!=crc:raise ValueError('controller WTP CRC mismatch')
        value=loads_strict(payload.decode())
        if validator.errors(value,schema):raise ValueError('controller WTP schema mismatch')
        result.append(value)
    return result


def transaction(client,server,schema,device_id,boot,job_id):
    requests=messages(client,schema);responses=messages(server,schema)
    matched={}
    for response in responses:
        if response['type']=='event' and response['boot_id']!=boot:
            raise ValueError('controller event boot substitution')
        if response['type']=='response':
            key=(response['session_id'],response['request_id'],response['op'])
            if key in matched:raise ValueError('duplicate controller response')
            matched[key]=response
    loads=[];arms=[];hellos=[]
    for request in requests:
        if request['type']!='request':raise ValueError('foreign client envelope')
        key=(request['session_id'],request['request_id'],request['op'])
        response=matched.get(key)
        if response is None:raise ValueError('incomplete controller transaction')
        if request['op'] in ('HELLO','LOAD','ARM'):
            if response['ok'] is not True:raise ValueError('controller critical operation rejected')
            if request['op']=='HELLO':
                if response['body']['device_id']!=device_id or response['body']['boot_id']!=boot:
                    raise ValueError('controller peer identity substitution')
                hellos.append(response)
            elif request['op']=='LOAD':loads.append((request,response))
            else:arms.append((request,response))
    if not hellos or len(loads)!=1 or len(arms)!=1 or any(pair[0]['body']['job_id']!=job_id for pair in loads+arms):
        raise ValueError('controller finite job binding')
    return dict(load_request=loads[0][0],load_reply=loads[0][1],arm_request=arms[0][0],arm_reply=arms[0][1],hellos=hellos)


def terminal_proof(server,schema,arm_reply,boot,job_id):
    """Require same-session natural completion after the exact ARM response."""
    armed=False;proof=None
    for index,response in enumerate(messages(server,schema)):
        if response==arm_reply:armed=True;continue
        if not armed or response['session_id']!=arm_reply['session_id']:continue
        candidates=[]
        if response['type']=='event' and response['event']=='JOB_STATE':
            if response['boot_id']!=boot:raise ValueError('terminal event boot substitution')
            candidates=[response['body']]
        elif response['type']=='response' and response['op']=='STATUS' and response['ok']:
            if response['body']['boot_id']!=boot:raise ValueError('terminal status boot substitution')
            candidates=[response['body'],*response['body']['terminal_records']]
        for status in candidates:
            if status.get('job_id')!=job_id or status['state'] not in ('complete','aborted','missed','failed'):continue
            if status['state']!='complete' or status['output_active'] is not False or 'error' in status:
                raise ValueError('controller did not naturally complete with known inactive output')
            if proof is None:
                proof=dict(message_index=index,session_id=response['session_id'],boot_id=boot,terminal=status)
    if proof:return proof
    raise ValueError('same-job completion after ARM not captured')


class Relay:
    def __init__(self,root,address,port,*,listen_port=31582):
        self.root=Path(root);self.address=address;self.port=port
        self.stop=threading.Event();self.error=None;self.terminations=[]
        self.listener=socket.socket();self.listener.bind(('127.0.0.1',listen_port));self.listener.listen(1)
        self.listen_port=self.listener.getsockname()[1]
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def run(self):
        try:
            with (self.root/'client-to-device.bin').open('xb') as outbound,(self.root/'device-to-client.bin').open('xb') as inbound:
                while not self.stop.is_set():
                    if not select.select([self.listener],[],[],.1)[0]:continue
                    connection,_=self.listener.accept()
                    with connection,socket.create_connection((self.address,self.port),timeout=5) as device:
                        connection.setblocking(False);device.setblocking(False)
                        pending={connection:bytearray(),device:bytearray()};eof=set()
                        while not self.stop.is_set():
                            if len(eof)==2 and not any(pending.values()):break
                            reads,writes,_=select.select([s for s in pending if s not in eof],
                                [s for s,data in pending.items() if data],[],.1)
                            reset=False
                            for source in reads:
                                target=device if source is connection else connection
                                try:data=source.recv(65536)
                                except ConnectionResetError:
                                    self.terminations.append(dict(side='controller' if source is connection else 'device',
                                        reason='connection_reset',undelivered_bytes=len(pending[source])))
                                    # Native clients may reset after their completed
                                    # RELEASE while unsolicited events remain unread.
                                    # Preserve both streams; exact transaction validation
                                    # still rejects any missing critical response/frame.
                                    reset=True
                                    break
                                if not data:
                                    eof.add(source)
                                    # A finite controller connection must end with all
                                    # admitted bytes delivered before closing its peer.
                                    if not pending[target]:target.shutdown(socket.SHUT_WR)
                                else:
                                    (outbound if source is connection else inbound).write(data)
                                    pending[target].extend(data)
                                    if len(pending[target])>131104:raise ValueError('controller relay backpressure bound')
                            if reset:break
                            for target in writes:
                                try:sent=target.send(pending[target])
                                except BlockingIOError:continue
                                del pending[target][:sent]
                                source=device if target is connection else connection
                                if source in eof and not pending[target]:target.shutdown(socket.SHUT_WR)
        except BaseException as error:self.error=error
    def close(self):
        self.stop.set();self.thread.join(timeout=6);self.listener.close()
        if self.thread.is_alive():raise TimeoutError('controller relay shutdown')
        if self.error:raise self.error
