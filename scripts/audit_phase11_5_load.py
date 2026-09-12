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


def status_cadence(requests, begin, seconds):
    """Audit request starts, not TLS write completion or response timestamps."""
    nominal = [r for r in requests if begin <= r['started_ns'] <= begin + seconds * 10**9]
    require(all(a['started_ns'] <= b['started_ns'] for a, b in zip(requests, requests[1:])),
            'Production STATUS starts out of order')
    gaps = [(b['started_ns'] - a['started_ns'], a, b) for a, b in zip(nominal, nominal[1:])]
    worst = max(gaps, key=lambda item: item[0]) if gaps else None
    result = dict(nominal_status_count=len(nominal),
                  nominal_status_hz=len(nominal) / seconds,
                  nominal_max_status_start_gap_ns=worst[0] if worst else None,
                  worst_status_start_gap_requests=[worst[1], worst[2]] if worst else [])
    require(len(nominal) >= seconds - 2 and worst is not None and worst[0] <= 2_000_000_000,
            'Nominal production STATUS rate absent/reduced: ' + json.dumps(result, sort_keys=True))
    return result


def audit_normal_browser(events, seconds, start):
    require(seconds in (180, 300), 'Unfrozen normal browser interval')
    refresh = (20, 40, 60, 100, 130, 160) if seconds == 180 else (30, 70, 110, 190, 230, 270)
    page = ['/', '/api/v1/capabilities', '/api/v1/status', '/api/v1/config']
    expected = sorted([(0, 'initialize', page), (seconds // 2, 'reload', page)] +
                      [(offset, 'refresh', ['/api/v1/status']) for offset in refresh])
    rows = [r for r in events if r['kind'] in
            ('browser_action_start', 'browser_action_finish', 'browser_get')]
    position = 0
    latencies = []
    for index, (offset, action, paths) in enumerate(expected):
        require(position < len(rows), 'Missing normal browser action')
        first = rows[position];position += 1
        value = first['value'];due = start + offset * 10**9
        require(first['kind'] == 'browser_action_start' and value['index'] == index and
                value['action'] == action and value['paths'] == paths and
                abs(value['scheduled_monotonic_ns'] - due) <= 1000 and
                0 <= first['monotonic_ns'] - due <= 15e9, 'Normal browser action order/schedule')
        previous = first['monotonic_ns']
        for path in paths:
            require(position < len(rows), 'Missing action request')
            row = rows[position];position += 1
            require(row['kind'] == 'browser_get' and row['value']['path'] == path and
                    previous <= row['value']['began_monotonic_ns'] <= row['monotonic_ns'],
                    'Normal browser request/action mismatch')
            previous = row['monotonic_ns']
        require(position < len(rows), 'Missing action finish')
        last = rows[position];position += 1
        require(last['kind'] == 'browser_action_finish' and
                last['value'] == dict(index=index, action=action) and
                previous <= last['monotonic_ns'] <= start + seconds * 10**9 and
                0 <= last['monotonic_ns'] - first['monotonic_ns'] <= len(paths) * 15e9,
                'Normal browser action completion/deadline')
        latencies.append((last['monotonic_ns'] - first['monotonic_ns']) / 1e9)
    require(position == len(rows), 'Extra normal browser traffic')
    return dict(actions=len(expected), refresh_actions=len(refresh),
                action_latencies_seconds=latencies)


def normal_response(path, body, boot, idle=True):
    if path == '/':
        require(b'<style' in body and b'<script' in body, 'Normal page lacks embedded assets')
        return
    value = json.loads(body)
    require(type(value) is dict and value.get('ok') is not False, 'Normal browser API error')
    if path == '/api/v1/capabilities':
        require(value.get('api_version') == 1 and type(value.get('wtp')) is dict and
                type(value.get('features')) is dict and type(value.get('active_job_connections')) is bool,
                'Normal capabilities initialization failed')
    elif path == '/api/v1/config':
        config = value.get('config')
        require(type(config) is dict and config.get('enabled') is False and
                type(config.get('station')) is dict and type(config.get('schedules')) is list and
                config.get('wifi', {}).get('password') is None,
                'Normal config initialization/redaction failed')
    elif path == '/api/v1/status':
        status = value['job']
        require(status['boot_id'] == boot and type(value.get('standalone')) is dict and
                type(value.get('network')) is dict, 'Normal status initialization failed')
        if idle:
            require(status['state'] == 'empty' and status['output_active'] is False and
                    status['owner_id'] is None and status['job_id'] is None and
                    status['terminal_records'] == [], 'Normal idle browser authority differs')
    else:
        raise ValueError('Unfrozen normal browser resource')


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
    require(rows and all(row.get('version')=='P115TLS2' for row in rows),
            'Production STATUS start cadence requires native TLS write-entry timestamps (P115TLS2)')
    schema=json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text())
    validator=SchemaValidator(schema)
    sessions=set();buffers={};pending={};responses=[];status_requests=[];connections=set();op_counts={}
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
                if message['op']=='STATUS':
                    status_requests.append(dict(request_id=message['request_id'],
                        started_ns=buffer_stamps[key],write_completed_ns=row['monotonic_ns']))
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
    cadence=status_cadence(status_requests,begin,plan['seconds'])
    browser=[r for r in events if r['kind']=='browser_get']
    browser_counts={}
    for row in browser:
        value=row['value'];browser_counts[value['path']]=browser_counts.get(value['path'],0)+1
        require(value['status']==200 and row['monotonic_ns']-value['began_monotonic_ns']<=15e9,
                'Browser HTTP result/deadline')
        body=bytes.fromhex(value['body_hex'])
        if plan.get('browser_profile', 'S') == 'N':
            require(value['peer_sha256']=='06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016',
                    'Normal browser TLS identity differs')
            normal_response(value['path'], body, plan['boot_id'], idle=rf_packet is None)
        if value['path']=='/api/v1/status':require(json.loads(body)['job']['boot_id']==plan['boot_id'],
                                                 'Browser boot changed')
    normal = {}
    require(plan.get('browser_profile', 'S') in ('N', 'S'), 'Unknown browser profile')
    if plan['browser'] and plan.get('browser_profile', 'S') == 'N':
        normal = audit_normal_browser(events, plan['seconds'],
                    begins[0]['value']['schedule_start_monotonic_ns'])
    elif plan['browser']:
        require(browser_counts.get('/api/v1/status',0)==plan['seconds']//5 and
                all(browser_counts.get(path,0)==plan['seconds']//30 for path in ('/','/style.css','/app.js')),
                'Missing browser status/page/assets workload')
    else:require(not browser,'Unexpected browser workload')
    return dict(boot=plan['boot_id'],seconds=plan['seconds'],production_connections=len(connections),
        logical_sessions=len(sessions),operations=op_counts,**cadence,browser_counts=browser_counts,
        **({'normal_browser':normal} if normal else {}),
        max_observed_write_to_response_seconds=max(responses)/1e9,
        timing_origin='SSL_write_ex entry',
        limitation='Measurement begins at native TLS write; scheduler queue time is outside this metric',
        plaintext_sha256=hashlib.sha256((root/'production-tls.bin').read_bytes()).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path)
    parser.add_argument('--observer-decoder',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(audit(args.root,args.observer_decoder),indent=2))
