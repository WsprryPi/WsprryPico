"""Reconstruct bounded target LOAD exchanges from recorded bytes; no device access."""
import hashlib
import json
from pathlib import Path
import struct

from phase11_5_inventory import require, loads_console
from phase11_5_pilot import Decoder
from phase11_5_pilot_supervisor import configuration, B_SERIAL, B_DEVICE
from phase11_5_r3_preflight import audit_inventory
from phase11_5_r3_allocation_diagnostic import inactive
from phase11_5_load_reply_target import validate_packet, primary, raw_request, response_ok, healthy, C7_JOB, SOURCE, PEER_SHA, SERIAL, DEVICE, PRIOR_JOB, maximum_job
from validate_wtp_contract import loads_strict, SchemaValidator, crc32c


def rows(path):
    text=path.read_text();require(text.endswith('\n'),'Truncated journal');r=[json.loads(line) for line in text.splitlines()]
    require([x['sequence'] for x in r]==list(range(len(r))) and all(a['monotonic_ns']<=b['monotonic_ns'] for a,b in zip(r,r[1:])),'Journal chronology/sequence')
    require(r and r[0]['kind']=='start','Journal start');return r

def wire_decode(buffer):
    out=[]
    while len(buffer)>=16:
        magic,version,encoding,flags,size,crc=struct.unpack('>4sBBHII',buffer[:16])
        require((magic,version,encoding,flags)==(b'WTPF',1,1,0) and 0<size<=65536,'Recorded frame header')
        if len(buffer)<size+16:break
        body=bytes(buffer[16:16+size]);require(crc32c(body)==crc,'Recorded CRC');out.append((loads_strict(body.decode()),body));del buffer[:16+size]
    return out

def audit(root):
    p=validate_packet(json.loads((root/'test-packet.json').read_text()));packet_sha=hashlib.sha256((root/'test-packet.json').read_bytes()).hexdigest()
    r=rows(root/'run.jsonl');require(r[0]['value']['packet_sha256']==packet_sha,'Run packet identity')
    result=json.loads((root/'run-result.json').read_text());require(r[-1]['kind']=='finish' and r[-1]['value']==result,'Recorded completion')
    schema=loads_strict((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text());validator=SchemaValidator(schema)
    transactions={};active=None;buffer=bytearray();messages=[];console=bytearray();infos=[];failures=[];console_start=None;console_end=None
    allowed={'start','usb_tx','usb_write','usb_rx','usb_message','console_tx','console_rx','info','failure','finish','cleanup_tx','cleanup_rx'}
    for row in r:
        k,v=row['kind'],row['value'];require(k in allowed,'Undeclared trace activity')
        if k=='usb_tx':
            label=v['label'];require(label not in transactions,'Duplicate exchange label')
            require(active is None or active['response'] is not None or label.startswith('cleanup-'),'Overlapping test exchanges')
            if label.startswith('cleanup-') and (active is None or not active['label'].startswith('cleanup-')):buffer.clear();messages.clear()
            raw=bytes.fromhex(v['hex']);q=v['request'];require(raw==raw_request(q) and not validator.errors(q,schema),'Request bytes/schema')
            require(q['op'] in ['HELLO','STATUS','CLAIM','LOAD','ABORT','RELEASE'],'Unexpected operation')
            active=dict(label=label,request=q,start=row['monotonic_ns'],written=0,wire_bytes=len(raw),response=None)
            transactions[label]=active
        elif k=='usb_write':
            require(active and v['label']==active['label'] and type(v['bytes']) is int and 0<v['bytes']<=4096,'Write identity/progress')
            active['written']+=v['bytes'];require(v['total_written']==active['written']<=active['wire_bytes'],'Actual write accounting')
        elif k=='usb_rx':
            require(active and v['label']==active['label'],'RX exchange identity');buffer.extend(bytes.fromhex(v['hex']));messages.extend(wire_decode(buffer))
        elif k=='usb_message':
            require(messages,'Response summary lacks raw bytes');message,payload=messages.pop(0);require(message==v['message'] and not validator.errors(message,schema),'Response raw/summary/schema')
            require(active and v['label']==active['label'] and message['session_id']==active['request']['session_id'],'Response session/label')
            if message['type']=='response':
                require(active['response'] is None and all(message[key]==active['request'][key] for key in ['op','request_id']),'Response pairing')
                require(active['written']==active['wire_bytes'],'Response before full write')
                active.update(response=message,response_bytes=len(payload),response_sha256=hashlib.sha256(payload).hexdigest(),elapsed_ns=row['monotonic_ns']-active['start'])
                require(0<=active['elapsed_ns']<=5000000000,'Recorded response deadline')
        elif k=='console_tx':
            require(bytes.fromhex(v['hex'])==b'INFO\n' and not console and console_start is None,'Single-flight INFO');console_start=row['monotonic_ns']
        elif k=='console_rx':
            require(console_start is not None,'Unsolicited INFO bytes');console.extend(bytes.fromhex(v['hex']));console_end=row['monotonic_ns']
        elif k=='info':
            require(console.endswith(b'\n') and console.count(b'\n')==1 and loads_console(console.decode().strip())==v['value'] and 0<=console_end-console_start<=5000000000,'INFO raw/summary/deadline');console.clear();console_start=None;infos.append(row)
        elif k=='failure':failures.append(v)
        elif k=='cleanup_tx':require(bytes.fromhex(v['hex']) in [b'INFO\n',b'ABORT\n'],'Cleanup operation')
    require(not messages,'Unreported raw responses')
    permitted={'prime-hello','prime-claim','prime-load','prime-abort','prime-release','test-hello','retained-status','test-claim','primary','identical-replay','fresh-id-replay','loaded-status','test-abort','test-release',*[f'pre-status-{i}' for i in range(7)],'cleanup-hello','cleanup-claim','cleanup-release'}
    require(set(transactions)<=permitted,'Undeclared USB exchange')
    require(result['primary_loads']==int('primary' in transactions) and result['replays']==sum(label in transactions for label in ['identical-replay','fresh-id-replay']) and result['rf_jobs']==0,'Recorded operation counts')
    if 'prime-load' in transactions:
        t=transactions['prime-load'];require(t['request']['body']==maximum_job(PRIOR_JOB),'Exact preparation job')
        if t['response']:
            require(t['response']['ok'] and t['response']['body']['job_id']==PRIOR_JOB,'Preparation response')
            response_ok(dict(t['response'],body=dict(t['response']['body'],job_id=C7_JOB)))
    if 'retained-status' in transactions and transactions['retained-status']['response']:
        t=transactions['retained-status'];b=t['response']['body'];require(t['start']-transactions['prime-release']['start']-transactions['prime-release']['elapsed_ns']>=310000000000,'Retained request-cache aging')
        require(b['state']=='empty' and b['owner_id'] is None and b['output_active'] is False and len(b['terminal_records'])==1 and b['terminal_records'][0]['job_id']=='c339ee30075d458ccc3047bb3d8f8b18' and b['terminal_records'][0]['state']=='aborted','Retained state evidence')
    primary_tx=transactions.get('primary');primary_pass=False;replays=[]
    if primary_tx:
        require(primary_tx['request']==primary(),'Exact primary request')
        if primary_tx['response']:
            response_ok(primary_tx['response']);primary_pass=primary_tx['response']['ok'] and primary_tx['response_bytes']==54916
    for label in ['identical-replay','fresh-id-replay']:
        t=transactions.get(label)
        if t and t['response']:
            require(primary_pass,'Replay before successful primary');response_ok(t['response'])
            expected=primary() if label=='identical-replay' else dict(primary(),request_id=p['fresh_request_id'])
            require(t['request']==expected and dict(t['response'],request_id=primary_tx['response']['request_id'])==primary_tx['response'],'Replay content')
            replays.append(label)
    deployment=json.loads((root/'deployment.json').read_text());require(deployment['bootsel_commands']==deployment['flashes_started']==1 and deployment['status']=='CANDIDATE_VERIFIED','One verified candidate')
    def inventory(name,b=False):
        require(not (root/(name+'.stderr')).read_bytes(),'Inventory stderr')
        return audit_inventory(root/(name+'.stdout'),dict(serial=B_SERIAL if b else SERIAL,device_id=B_DEVICE if b else DEVICE),p['b_session'] if b else p['inventory_session'],p['stage_sha256']['scripts/phase11_5_inventory.py'])
    # Supplemental read-only evidence never replaces or rewrites the failed run.
    final_a_name='post-restoration-a' if (root/'post-restoration-a.stdout').exists() else 'final-a'
    final_b_name='post-restoration-b' if (root/'post-restoration-b.stdout').exists() else 'final-b'
    final=inventory(final_a_name);inactive(final);healthy(final['info'],deployment['boot_id'])
    before=inventory('before-a');require(configuration(final)==configuration(before),'A configuration preserved')
    final_b=inventory(final_b_name,True);before_b=inventory('before-b',True);inactive(final_b)
    require(final_b['wtp']['STATUS']['boot_id']==before_b['wtp']['STATUS']['boot_id'] and final_b['info']['revision']==before_b['info']['revision'] and configuration(final_b)==configuration(before_b),'B unchanged')
    fixture=json.loads((root/'fixture-state.json').read_text()) if (root/'fixture-state.json').exists() else {}
    fixture_restored=fixture.get('restored') is True
    if fixture_restored:
        fr=[json.loads(x) for x in (root/'fixture.jsonl').read_text().splitlines()]
        clean=[x for x in fr if x['kind']=='cleanup'];require(clean and clean[-1]['value']['failures']==[],'Fixture cleanup evidence')
    network_status='NOT_RUN';tls_samples=[];https_count=0
    if (root/'network.jsonl').exists():
        nr=rows(root/'network.jsonl');require(nr[0]['value']['packet_sha256']==packet_sha,'Network packet identity')
        nb=bytearray();nm=[];pending=None;https_starts=[];tls_replies=0
        for row in nr:
            kind,value=row['kind'],row['value']
            require(kind in ['start','tls','tls_tx','tls_rx','tls_message','https','failure','finish'],'Undeclared network trace activity')
            if kind=='tls_tx':
                q=value['request'];require(pending is None and q['op'] in ['HELLO','STATUS'] and q['session_id']==p['tls_session'] and raw_request(q)==bytes.fromhex(value['hex']) and not validator.errors(q,schema),'Read-only TLS request')
                pending=(q,row['monotonic_ns'])
            elif kind=='tls_rx':nb.extend(bytes.fromhex(value['hex']));nm.extend(wire_decode(nb))
            elif kind=='tls_message':
                require(nm and nm.pop(0)[0]==value and not validator.errors(value,schema),'TLS raw/summary/schema')
                if value['type']=='response':
                    require(pending is not None and value['ok'] and all(value[k]==pending[0][k] for k in ['session_id','request_id','op']) and row['monotonic_ns']-pending[1]<=5000000000,'TLS response identity/deadline')
                    if value['op']=='STATUS':require(value['body']['boot_id']==deployment['boot_id'] and value['body']['output_active'] is False,'TLS status authority')
                    pending=None;tls_replies+=1
                else:require(value['boot_id']==deployment['boot_id'],'TLS event boot')
            if row['kind']=='tls':require(row['value']['peer_sha256']==PEER_SHA and row['value']['version']=='TLSv1.3' and row['value']['alpn'] in ['wtp/1','http/1.1'],'TLS identity')
            if row['kind']=='https':
                v=row['value'];https_starts.append(v['began_ns']);require(bytes.fromhex(v['request_hex']).startswith(b'GET /api/v1/status HTTP/1.1\r\n'),'Ordinary status GET');body=json.loads(bytes.fromhex(v['body_hex']));require(v['status']==200 and body['job']['boot_id']==deployment['boot_id'] and body['job']['output_active'] is False,'HTTPS status/identity');https_count+=1
        require(https_count<=4 and not nm,'HTTPS count/TLS summaries')
        if result['status']=='CAPTURED_REQUIRES_AUDIT':require(not nb and pending is None and tls_replies>=13,'Complete TLS observations')
        require(all(b-a>=20000000000 for a,b in zip(https_starts,https_starts[1:])),'HTTPS spacing')
        network_status=json.loads((root/'network-result.json').read_text())['status'] if (root/'network-result.json').exists() else 'INTERRUPTED'
    recovered_infos=[]
    if console:
        require(result['status']=='FAILED' and failures and console.endswith(b'\n') and console.count(b'\n')==1 and 0<=console_end-console_start<=5000000000,'Incomplete failed INFO evidence')
        recovered_infos.append(dict(monotonic_ns=console_end,value=dict(began_ns=console_start,value=loads_console(console.decode().strip()))))
    for row in infos+recovered_infos:
        healthy(row['value']['value'],deployment['boot_id'])
        if primary_tx and abs(row['monotonic_ns']-primary_tx['start'])<=2000000000:tls_samples.append(row['value']['value']['tls_allocated_bytes'])
    comparable=bool(tls_samples) and min(tls_samples)>=31384
    success=result['status']=='CAPTURED_REQUIRES_AUDIT' and primary_pass and len(replays)==2 and network_status=='COMPLETE' and https_count==4 and fixture_restored and not failures
    if success:
        expected=['prime-hello','prime-claim','prime-load','prime-abort','prime-release','test-hello','retained-status',*[f'pre-status-{i}' for i in range(7)],'test-claim','primary','identical-replay','fresh-id-replay','loaded-status','test-abort','test-release']
        require(list(transactions)==expected and all(t['response'] and t['response']['ok'] for t in transactions.values()),'Complete successful operation schedule')
        loaded=transactions['loaded-status']['response']['body']
        require(loaded['boot_id']==deployment['boot_id'] and loaded['state']=='loaded' and loaded['job_id']==C7_JOB and loaded['owner_id']==p['owner_id'] and loaded['output_active'] is False,'Loaded authority')
        require(not buffer and not console and len(infos)>=60,'Complete observer trace')
        require(primary_tx['start']-infos[0]['value']['began_ns']>=30000000000 and infos[-1]['monotonic_ns']-(primary_tx['start']+primary_tx['elapsed_ns'])>=30000000000,'Observation bracket')
    return dict(status='LOAD_REPLY_TARGET_PASS' if success and comparable else 'LOAD_REPLY_TARGET_LIMITED' if success else 'LOAD_REPLY_TARGET_FAILED',group2_closed=False,packet_sha256=packet_sha,source_revision=SOURCE,image_sha256=p['image_sha256'],boot_id=deployment['boot_id'],primary_pass=primary_pass,replays_passed=replays,transactions=transactions,network_status=network_status,https_requests=https_count,tls_bracket_bytes=tls_samples,tls_pressure_comparable=comparable,info_samples=len(infos),recovered_failed_info_samples=[x['value']['value'] for x in recovered_infos],failures=failures,fixture_restored=fixture_restored,final_authority=final['wtp']['STATUS'],final_inventory_files=[final_a_name,final_b_name],b_unchanged=True,counts=dict(flashes=1,bootsel=1,preparation_loads=int('prime-load' in transactions),primary_loads=int(primary_tx is not None),replays=sum(label in transactions for label in ['identical-replay','fresh-id-replay']),rf_jobs=0,configuration_writes=0,wifi_cycles=0))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('--output',type=Path,required=True,help='Private output; contains reconstructed protocol data')
    args=parser.parse_args()
    value=audit(args.root)
    args.output.write_text(json.dumps(value,indent=2)+'\n')
    print(value['status'])
