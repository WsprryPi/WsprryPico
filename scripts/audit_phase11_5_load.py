#!/usr/bin/env python3
"""Offline production A2 plaintext/rate audit; no hardware or network access."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from audit_phase11_5_idle import frames
from phase11_5_inventory import require
from validate_wtp_contract import SchemaValidator


def audit(root, observer_decoder, rf_packet=None):
    spec=importlib.util.spec_from_file_location('phase115_observer_decoder',observer_decoder)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    plan=json.loads((root/'load.json').read_text())
    result=json.loads((root/'result.json').read_text())
    require(result==dict(result='CAPTURED_REQUIRES_AUDIT',observer_exit=0,load_exit=0),
            'Coordinator did not complete cleanly')
    text=(root/'load-events.jsonl').read_text();require(text.endswith('\n'),'Truncated load events')
    events=[json.loads(line) for line in text.splitlines()]
    require(events[0]['kind']=='start' and events[0]['value']==plan and
            events[-1]['kind']=='finish' and events[-1]['value']==dict(
                result='CAPTURED_REQUIRES_INDEPENDENT_AUDIT',failures=[],exit=0),'Load result/plan')
    require([r['sequence'] for r in events]==list(range(len(events))) and
            all(a['monotonic_ns']<=b['monotonic_ns'] for a,b in zip(events,events[1:])),
            'Load event order')
    begins=[r for r in events if r['kind']=='nominal_begin']
    ends=[r for r in events if r['kind']=='nominal_finish']
    require(len(begins)==len(ends)==1,'Nominal interval markers')
    begin,end=begins[0]['monotonic_ns'],ends[0]['monotonic_ns']
    require(end-begin>=plan['seconds']*1e9,'Shortened nominal load')
    rows=module.decode((root/'production-tls.bin').read_bytes())
    schema=json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text())
    validator=SchemaValidator(schema)
    sessions=set();buffers={};pending={};responses=[];status_times=[];connections=set();op_counts={}
    write_started={};write_times={};buffer_stamps={};event_id=-1
    for row in rows:
        kind,cid=row['kind'],row['connection_id']
        if kind==7:
            write_started.setdefault(cid,row['monotonic_ns'])
        if kind==3:
            write_times[cid]=write_started.pop(cid,row['monotonic_ns'])
        if kind==2:
            require(row['payload'].hex()=='06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016',
                    'Actual TLS peer fingerprint');connections.add(cid)
        if kind not in (3,4):continue
        key=(cid,kind)
        if kind==3:buffer_stamps.setdefault(key,write_times[cid])
        decoded,buffers[key]=frames(buffers.get(key,b'')+row['payload'])
        for message in decoded:
            require(not validator.errors(message,schema),'Actual production wire schema')
            sessions.add(message['session_id'])
            if kind==3:
                require(message['type']=='request' and message['op'] in ('HELLO','CAPS','STATUS','GET_CLOCK','PING'),
                        'Idle load sent mutation or unexpected operation')
                token=(message['session_id'],message['request_id'])
                require(token not in pending,'Duplicate pending request')
                pending[token]=(message,buffer_stamps[key])
                op_counts[message['op']]=op_counts.get(message['op'],0)+1
                if message['op']=='STATUS' and begin<=row['monotonic_ns']<=begin+plan['seconds']*1e9:
                    status_times.append(row['monotonic_ns'])
            else:
                if message['type']=='event' and rf_packet is not None:
                    from phase11_5_rf_observer import validate_event
                    validate_event(message,plan['boot_id'],rf_packet)
                    require(int(message['event_id'])==event_id+1,'Production RF event gap')
                    event_id=int(message['event_id']);continue
                require(message['type']=='response' and message['ok'] is True,'Unexpected response/event/error')
                request,stamp=pending.pop((message['session_id'],message['request_id']))
                require(message['op']==request['op'],'Response operation mismatch')
                delta=row['monotonic_ns']-stamp;require(0<=delta<=5e9,'Observed write-to-response delay')
                responses.append(delta)
                if message['op'] in ('HELLO','STATUS'):
                    require(message['body']['boot_id']==plan['boot_id'],'Production boot changed')
                if message['op']=='STATUS':
                    status=message['body']
                    if rf_packet is not None:
                        from phase11_5_rf_observer import validate_status
                        validate_status(status,plan['boot_id'],rf_packet)
                    else:
                        require(status['state']=='empty' and status['output_active'] is False and
                                status['owner_id'] is None and status['job_id'] is None,'Idle STATUS authority')
        if not buffers[key]:buffer_stamps.pop(key,None)
    require(len(connections)==len(sessions)==1 and not pending and not write_started and not any(buffers.values()),
            'Production reconnected, changed session or has incomplete I/O')
    require(status_times and len(status_times)>=plan['seconds']-2 and
            max((b-a)/1e9 for a,b in zip(status_times,status_times[1:]))<=2,
            'Nominal production STATUS rate absent/reduced')
    browser=[r for r in events if r['kind']=='browser_get']
    browser_counts={}
    for row in browser:
        value=row['value'];browser_counts[value['path']]=browser_counts.get(value['path'],0)+1
        require(value['status']==200 and row['monotonic_ns']-value['began_monotonic_ns']<=15e9,
                'Browser HTTP result/deadline')
        body=bytes.fromhex(value['body_hex'])
        if value['path']=='/api/v1/status':require(json.loads(body)['job']['boot_id']==plan['boot_id'],
                                                 'Browser boot changed')
    if plan['browser']:
        require(browser_counts.get('/api/v1/status',0)==plan['seconds']//5 and
                all(browser_counts.get(path,0)==plan['seconds']//30 for path in ('/','/style.css','/app.js')),
                'Missing browser status/page/assets workload')
    else:require(not browser,'Unexpected browser workload')
    return dict(boot=plan['boot_id'],seconds=plan['seconds'],production_connections=len(connections),
        logical_sessions=len(sessions),operations=op_counts,nominal_status_count=len(status_times),
        nominal_status_hz=len(status_times)/plan['seconds'],browser_counts=browser_counts,
        max_observed_write_to_response_seconds=max(responses)/1e9,
        timing_origin='SSL_write_ex entry' if rows[0].get('version')=='P115TLS2' else 'successful SSL_write_ex return',
        limitation='Measurement begins at native TLS write; scheduler queue time is outside this metric',
        plaintext_sha256=hashlib.sha256((root/'production-tls.bin').read_bytes()).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path)
    parser.add_argument('--observer-decoder',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(audit(args.root,args.observer_decoder),indent=2))
