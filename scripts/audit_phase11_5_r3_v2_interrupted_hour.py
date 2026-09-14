"""H1a scoped physical-hour audit; its failed USB observer gate remains failed."""
import json
from pathlib import Path
from phase11_5_inventory import require, loads_console
from phase11_5_device_management import digest
from phase11_5_pilot_supervisor import configuration, B_SERIAL, B_DEVICE
from phase11_5_pilot import SERIAL, DEVICE
from phase11_5_r3_preflight import audit_inventory
from validate_wtp_contract import SchemaValidator
from audit_phase11_5_idle import frames
from phase11_5_r3_v2_rf import validate, validate_info
from audit_phase11_5_r3_v2_rf import timing
from audit_phase11_5_r3_v2_hour import journal, native_wire, PEER, NAME

PACKET = 'c5ecb3dcf84eb61b788ede7c2481d10054831cee6c630c5ca4d9c715bc8a8c8c'


def raw_observations(rows, before, packet):
    schema=json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text());validator=SchemaValidator(schema)
    pending={};seen=set();wire=b'';messages=[];console=b'';console_pending=None;console_value=None
    latest_status=None;exchanges=[];events=[];event_id=None;samples={}
    for row in rows:
        kind,v=row['kind'],row['value'];stamp=row['monotonic_ns']
        if kind=='console_tx':
            require(console_pending is None and not console and console_value is None and
                    bytes.fromhex(v['hex'])==b'INFO\n','Unexpected Console operation')
            console_pending=stamp
        elif kind=='console_rx':
            require(console_pending is not None,'Unsolicited Console bytes');console+=bytes.fromhex(v['hex'])
            if b'\n' in console:
                require(console.endswith(b'\n') and console.count(b'\n')==1 and stamp-console_pending<=5_000_000_000,
                        'Console response/deadline')
                console_value=loads_console(console.decode().strip());console=b'';console_pending=None
        elif kind=='wtp_tx':
            values,left=frames(bytes.fromhex(v['hex']));require(not left and values==[v['request']],'Request raw/summary')
            request=values[0]
            require(not validator.errors(request,schema) and request['session_id']==packet['peer_session'] and
                    request['request_id'] not in seen and not pending,'Request schema/session/no retry')
            seen.add(request['request_id']);pending[request['request_id']]=(stamp,request)
        elif kind=='wtp_rx':
            values,wire=frames(wire+bytes.fromhex(v['hex']));messages.extend(values)
        elif kind=='wtp_message':
            require(messages and messages.pop(0)==v and not validator.errors(v,schema) and
                    v['session_id']==packet['peer_session'],'Response raw/summary/schema')
            if v['type']=='event':
                require(v['boot_id']==packet['boot_id'] and v['event'] in ['JOB_STATE','OWNER_RELEASED'] and
                        (event_id is None or int(v['event_id'])==event_id+1),'Event gap/fault/boot')
                event_id=int(v['event_id']);events.append(v);continue
            require(v['ok'] is True and v['request_id'] in pending,'Unmatched/rejected response')
            began,q=pending.pop(v['request_id']);require(q['op']==v['op'] and stamp-began<=5_000_000_000,'Operation/deadline')
            exchanges.append(dict(request=q,response=v,started_ns=began,finished_ns=stamp))
            if q['op']=='STATUS':latest_status=v['body']
            if q['op']=='HELLO':require(v['body']['boot_id']==packet['boot_id'] and v['body']['device_id']==DEVICE,'HELLO identity')
        elif kind in ['info','status','health']:
            samples.setdefault(kind,[]).append(row)
            require(0<=stamp-v['began_monotonic_ns']<=5_000_000_000,'Sample roundtrip')
            if kind=='info':
                require(console_value==v['value'],'INFO not raw');console_value=None;validate_info(v['value'],before,packet)
            elif kind=='status':
                require(latest_status==v['value'] and latest_status['boot_id']==packet['boot_id'],'STATUS not raw/boot');latest_status=None
            else:require(v['value']['boot']==packet['host_boot_id'] and v['value']['throttled']=='throttled=0x0','Host health')
    require(not pending and not wire and not messages and not console and console_pending is None and
            console_value is None and latest_status is None,'Unconsumed/missing wire')
    return samples, exchanges, events


def cadence(values, period_ns, begin, end):
    require(values and values[0]['began'] <= begin and values[-1]['ended'] >= end - period_ns,
            'Component observation coverage')
    gaps = [b['began'] - a['began'] for a,b in zip(values, values[1:])]
    require(all(0 < gap <= period_ns for gap in gaps), 'Component observation cadence')
    return dict(samples=len(values), maximum_start_gap_ns=max(gaps, default=0))


def audit(root, decoder):
    require(digest(root/'packet.json') == PACKET, 'Only frozen interrupted H1a packet')
    packet = json.loads((root/'packet.json').read_text()); validate(packet)
    require(len(packet['jobs']) == 1, 'One immutable job')
    job = packet['jobs'][0]
    require(job['mode'] == 'fskcw' and job['total_duration_ns'] == '3600000000000' and
            len(job['events']) == 384 and packet['message_derivation']['message'] == '?'*32,
            'Frozen 32-character physical hour')
    inventories = {}
    for label in ['before-a','before-b','final-a','final-b']:
        b = label.endswith('-b')
        value = audit_inventory(root/(label+'.stdout'),
            dict(serial=B_SERIAL if b else SERIAL, device_id=B_DEVICE if b else DEVICE),
            packet['b_session'] if b else packet['inventory_session'],
            packet['stage_sha256']['scripts/phase11_5_inventory.py'])
        require(not (root/(label+'.stderr')).read_bytes(), 'Inventory stderr')
        s = value['wtp']['STATUS']
        require(s['boot_id'] == (packet['b_boot_id'] if b else packet['boot_id']) and
                s['output_active'] is False and s['owner_id'] is None and
                s['state'] in (['empty','complete'] if label == 'final-a' else ['empty']),
                'Authoritative initial/final inactive unowned state')
        inventories[label] = value
    before, final = inventories['before-a'], inventories['final-a']
    require(configuration(before) == configuration(final) and
            configuration(inventories['before-b']) == configuration(inventories['final-b']) and
            inventories['before-b']['info']['revision'] == inventories['final-b']['info']['revision'] and
            inventories['before-b']['wtp']['STATUS'] == inventories['final-b']['wtp']['STATUS'],
            'A/B preservation')
    validate_info(before['info'], before, packet); validate_info(final['info'], before, packet)
    rows = journal(root/'rf.jsonl')
    require(rows[0]['value'] == dict(packet_sha256=PACKET, baseline_sha256=digest(root/'before-a.stdout'),
            boot_id=packet['boot_id'], seconds=packet['runtime_seconds']), 'Raw observer identity')
    failures = [r for r in rows if r['kind'] == 'failure']
    require(len(failures) == 1 and failures[0]['sequence'] == 80244 and
            failures[0]['monotonic_ns'] == 270355611017663 and failures[0]['value'] ==
            dict(worker='wtp', error='Fresh INFO required', type='ValueError'),
            'Exact preserved observer failure, no additional failures')
    allowed = {'start','finish','console_tx','console_rx','wtp_tx','wtp_rx','wtp_message',
        'info','status','health','info_finish','health_finish','arm_pending','arm_acknowledged',
        'contention_starting','failure'}
    require(all(r['kind'] in allowed for r in rows), 'Unexpected trace operation')
    samples, exchanges, events = raw_observations(rows, before, packet)
    requests = [e['request'] for e in exchanges]
    require(all(q['op'] in ['HELLO','STATUS','GET_CLOCK','CLAIM','LOAD','ARM','RENEW'] for q in requests),
            'Unexpected USB mutation')
    mutation = [q for q in requests if q['op'] in ['CLAIM','LOAD','ARM']]
    require([q['op'] for q in mutation] == ['CLAIM','LOAD','ARM'] and mutation[1]['body'] == job,
            'Actual USB plan and single launch, no retry')
    for q in requests:
        if q['op'] in ['CLAIM','RENEW']:
            require(q['body'] == dict(owner_id=packet['owner_id'], lease_ms=60000), 'Lease identity')
    require(sum(q['op'] == 'RENEW' for q in requests) <= packet['maximum_renewals'], 'Renewal bound')
    arm = next(e for e in exchanges if e['request']['op'] == 'ARM')
    q, a = arm['request']['body'], arm['response']['body']
    require(q['job_id'] == job['job_id'] and q['max_start_uncertainty_ns'] == '500000000' and
            a['start_utc_ns'] == q['start_utc_ns'] and a['clock']['state'] == 'synchronized' and
            a['clock']['leap'] == 'normal', 'Actual guarded ARM')
    require(all(e['started_ns'] < failures[0]['monotonic_ns'] for e in exchanges),
            'Mutation or USB activity after observer stopped')
    metrics = timing(packet, [dict(job=job, start_utc_ns=q['start_utc_ns'], monotonic_ns=arm['started_ns'])], rows)
    native, native_metrics = native_wire(root, packet, decoder)
    running = [s for s in native if s['value']['state'] == 'running']
    require(running and running[-1]['ended']-running[0]['began'] >= 3600_000_000_000-12_000_000_000,
            'Actual full-hour native Running span')
    records = final['wtp']['STATUS']['terminal_records']
    record = next((r for r in records if r['job_id'] == job['job_id']), None)
    require(record is not None and record['state'] == 'complete' and record['output_active'] is False and
            'error' not in record, 'Authoritative retained Complete')
    target = metrics[0]['launch_target_ns']
    require(3600_000_000_000 <= int(record['ended_monotonic_ns'])-target <= 3605_000_000_000,
            'Actual terminal time and full finite duration')
    terminal = [s for s in native if record in s['value']['terminal_records'] and
                s['value']['output_active'] is False and s['value']['state'] in ['empty','complete']]
    require(terminal and terminal[0]['began'] > running[-1]['began'], 'Native Complete after Running')
    begin, end = arm['started_ns'], terminal[0]['ended']
    coverage = {'native_wire': cadence(native, 6_000_000_000, begin, end)}
    for kind, period in [('info', 2_000_000_000), ('health', 6_000_000_000)]:
        values = samples[kind]
        endings = [r for r in rows if r['kind'] == kind+'_finish']
        require(len(endings) == 1 and endings[0]['value'] == dict(samples=len(values)), 'Reader finish/count')
        coverage[kind] = cadence([dict(began=r['value']['began_monotonic_ns'], ended=r['monotonic_ns'])
            for r in values], period, begin, end)
    for s in native:
        v = s['value']
        require(v['boot_id'] == packet['boot_id'] and v['job_id'] in [None,job['job_id']] and
                v['owner_id'] in [None,packet['owner_id']] and v['state'] in ['empty','loaded','armed','running','complete'] and
                v['output_active'] is (v['state'] == 'running'), 'Native identity/authority')
        if running[0]['ended']+6_000_000_000 <= s['began'] <= running[-1]['began']-6_000_000_000:
            require(v['state'] == 'running' and v['job_id'] == job['job_id'], 'Mid-hour lifecycle gap')
    load = journal(root/'contention.jsonl')
    require(all(r['kind'] in ['start','finish','native_status','https_status'] for r in load), 'Load reader failure')
    plan = packet['contention']
    require(load[0]['value'] == dict(packet_sha256=PACKET, policy=plan['policy'], binary_sha256=plan['binary_sha256']),
            'Load provenance')
    load_result = json.loads((root/'contention-result.json').read_text())
    require(load_result == load[-1]['value'] and load_result['status'] == 'CAPTURED_REQUIRES_AUDIT' and
            load_result['native_exit'] == 0 and not (root/'contention-failed.json').exists(), 'Load completion')
    families = {'native_status': [], 'https_status': []}
    expected_request = f'GET /api/v1/status HTTP/1.1\r\nHost: {NAME}:18443\r\nConnection: close\r\n\r\n'.encode()
    for r in load:
        kind, v = r['kind'], r['value']
        if kind not in families: continue
        raw_body = bytes.fromhex(v['body_hex']); body = json.loads(raw_body)
        require(0 <= r['monotonic_ns']-v['began_monotonic_ns'] <= (3 if kind == 'native_status' else 15)*10**9,
                'HTTP reply bound')
        if kind == 'https_status':
            require(bytes.fromhex(v['request_hex']) == expected_request and v['status'] == 200 and
                    v['peer_sha256'] == PEER and int(dict((k.lower(),v) for k,v in v['headers'])['content-length']) == len(raw_body) and
                    body['transport']['active'] == 2 and body['transport']['pending'] == 0, 'TLS body/identity/concurrency')
        else:
            require(body == v['value'], 'Native HTTP raw/summary')
            identity = body.get('host',{}).get('identity')
            if identity is None: continue
            require(identity['device_id'] == DEVICE and identity['boot_id'] == packet['boot_id'], 'Native HTTP identity')
        value = body['job']
        require(value['boot_id'] == packet['boot_id'] and value['job_id'] in [None,job['job_id']] and
                value['owner_id'] in [None,packet['owner_id']] and value['state'] in ['empty','loaded','armed','running','complete'] and
                value['output_active'] is (value['state'] == 'running'), 'HTTP authority')
        families[kind].append(dict(began=v['began_monotonic_ns'], ended=r['monotonic_ns']))
    require(len(families['https_status']) == load_result['https_requests'] <= plan['maximum_https_requests'], 'HTTPS budget')
    for kind, period in [('native_status',6_000_000_000), ('https_status',21_000_000_000)]:
        coverage[kind] = cadence(families[kind], period, begin, end)
    result = json.loads((root/'rf-result.json').read_text())
    require(result == rows[-1]['value'] and result['status'] in ['STOPPED_REQUIRES_DIAGNOSIS','STOPPED_FINAL_STATE_UNVERIFIED'] and
            result['armed_jobs'] == [job['job_id']] and result['completed_jobs'] == [] and
            result['rf_duration_ns_charged'] == 3600_000_000_000 and
            result['faults'] == ['wtp: Fresh INFO required'], 'Original failed runner result preserved')
    return dict(status='H1A_PHYSICAL_FSKCW_HOUR_WITH_FAILED_USB_OBSERVER_GATE',
        packet_sha256=PACKET, source_revision=packet['source_revision'], image_sha256=packet['image_sha256'],
        boot_id=packet['boot_id'], physical_hour_verified=True, family_closed=False,
        full_usb_observation_gate='FAILED', failure=failures[0], jobs=metrics, coverage=coverage,
        native=native_metrics, terminal_record=record, rf_duration_ns_charged=3600_000_000_000,
        source_of_completion='Raw authenticated native WTP and independent Console counters; original RF runner remains failed',
        limitations=['No full-run USB observer credit', 'No saturation or reclamation closure',
                     'Source-impact assessment required for later firmware changes'])


def audit_c1(root, decoder):
    """Score C1's completed capacity component, retaining its exact guard failure."""
    from phase11_5_r3_v2_observer_policy import validate_intervals
    frozen='3c8cea4f50a1e78b62cbb300846f05555360e8e0c91b467c694505b66fc8e3cf'
    require(digest(root/'packet.json')==frozen,'Only frozen C1 component')
    packet=json.loads((root/'packet.json').read_text());validate(packet)
    job,=packet['jobs']
    require(len(job['events'])==512 and job['total_duration_ns']=='384000000000','C1 capacity/duration')
    inventories=[]
    for label in ['before-a','final-a']:
        value=audit_inventory(root/(label+'.stdout'),dict(serial=SERIAL,device_id=DEVICE),
            packet['inventory_session'],packet['stage_sha256']['scripts/phase11_5_inventory.py'])
        require(not (root/(label+'.stderr')).read_bytes(),'Inventory stderr')
        s=value['wtp']['STATUS']
        require(s['boot_id']==packet['boot_id'] and s['output_active'] is False and s['owner_id'] is None and
            s['state']==('empty' if label=='before-a' else 'complete') and
            s['job_id']==(None if label=='before-a' else job['job_id']),'C1 final/initial authority')
        inventories.append(value)
    before,final=inventories
    require(configuration(before)==configuration(final),'C1 configuration preserved')
    for v in inventories:validate_info(v['info'],before,packet)
    rows=journal(root/'rf.jsonl')
    require(rows[0]['value']==dict(packet_sha256=frozen,baseline_sha256=digest(root/'before-a.stdout'),
        boot_id=packet['boot_id'],seconds=480),'C1 raw identity')
    failure,=[r for r in rows if r['kind']=='failure']
    require(failure['sequence']==3413 and failure['monotonic_ns']==341967858240262 and failure['value']==dict(
        worker='wtp action',error='Fresh INFO required: age_ns=2176692630, limit_ns=2000000000',type='ValueError'),
        'Exact C1 failed guard retained')
    allowed={'start','finish','console_tx','console_rx','wtp_tx','wtp_rx','wtp_message','info','status','health',
        'info_finish','status_finish','health_finish','arm_pending','arm_acknowledged','contention_starting','failure'}
    require(all(r['kind'] in allowed for r in rows),'Unexpected C1 activity')
    samples,exchanges,events=raw_observations(rows,before,packet)
    mutation=[e for e in exchanges if e['request']['op'] not in ['HELLO','STATUS','GET_CLOCK']]
    require([e['request']['op'] for e in mutation]==['CLAIM','LOAD','ARM','RENEW'] and
        all(e['finished_ns']<failure['monotonic_ns'] for e in mutation),'Single finite ARM; mutations stopped')
    claim,load,arm,renew=mutation
    require(load['request']['body']==job and all(e['request']['body']==dict(owner_id=packet['owner_id'],lease_ms=60000)
        for e in [claim,renew]),'Actual maximum job and owner')
    pending,=[r for r in rows if r['kind']=='arm_pending'];ack,=[r for r in rows if r['kind']=='arm_acknowledged']
    q,a=arm['request']['body'],arm['response']['body']
    require(pending['value']==dict(job=job,start_utc_ns=q['start_utc_ns']) and ack['value']==a and
        pending['monotonic_ns']<=arm['started_ns']<=arm['finished_ns']<=ack['monotonic_ns'] and
        q['job_id']==job['job_id'] and q['max_start_uncertainty_ns']=='500000000','Raw ARM charge/ACK')
    metrics=timing(packet,[dict(job=job,start_utc_ns=q['start_utc_ns'],monotonic_ns=arm['started_ns'],
        request=q,acknowledgment=a)],rows)
    states=[r['value']['value'] for r in samples['status']]
    require({'loaded','armed','running','complete'}<={s['state'] for s in states},'Full C1 lifecycle')
    for s in states:
        require(s['job_id'] in [None,job['job_id']] and s['owner_id'] in [None,packet['owner_id']] and
            s['output_active'] is (s['state']=='running'),'C1 identity/output')
        if s['state']=='running':require(s['owner_id']==packet['owner_id'],'Running owner lost')
    records=final['wtp']['STATUS']['terminal_records'];record,=records
    require(record==dict(job_id=job['job_id'],state='complete',output_active=False,
        ended_monotonic_ns=record['ended_monotonic_ns']) and
        384000000000<=int(record['ended_monotonic_ns'])-metrics[0]['launch_target_ns']<=389000000000,
        'Actual finite terminal duration')
    coverage={}
    for kind,period in [('info',2_000_000_000),('status',6_000_000_000),('health',6_000_000_000)]:
        values=samples[kind];ending,=[r for r in rows if r['kind']==kind+'_finish']
        require(ending['value']==dict(samples=len(values)),'Full reader count')
        starts=[r['value']['began_monotonic_ns'] for r in values]
        if kind=='info':coverage[kind]=validate_intervals(starts,[r['monotonic_ns'] for r in values],
            rows[0]['monotonic_ns'],ending['monotonic_ns'])
        else:
            require(starts[0]-rows[0]['monotonic_ns']<=period and ending['monotonic_ns']-starts[-1]<=period and
                all(0<b-a<=period for a,b in zip(starts,starts[1:])),'C1 cadence')
            coverage[kind]=dict(samples=len(values),maximum_start_gap_ns=max(b-a for a,b in zip(starts,starts[1:])))
    last_info=next(r for r in reversed(samples['info']) if r['monotonic_ns']<=failure['monotonic_ns'])
    next_info=next(r for r in samples['info'] if r['monotonic_ns']>failure['monotonic_ns'])
    require(last_info['monotonic_ns']==341965681530206 and
        0<=failure['monotonic_ns']-last_info['monotonic_ns']-2176692630<1_000_000 and
        next_info['value']['began_monotonic_ns']<failure['monotonic_ns']<next_info['monotonic_ns'] and
        next_info['monotonic_ns']-next_info['value']['began_monotonic_ns']<=5_000_000_000,
        'Original age guard failed during bounded in-flight INFO')
    native,native_metrics=native_wire(root,packet,decoder)
    running=[r for r in samples['status'] if r['value']['value']['state']=='running']
    end=next(r['monotonic_ns'] for r in samples['status'] if r['value']['value']['state']=='complete')
    families={'native_wire':(native,6_000_000_000)}
    load_rows=journal(root/'contention.jsonl');plan=packet['contention']
    require(load_rows[0]['value']==dict(packet_sha256=frozen,policy=plan['policy'],binary_sha256=plan['binary_sha256']) and
        all(r['kind'] in ['start','finish','native_status','https_status'] for r in load_rows),'Nominal provenance')
    host=[];https=[];host_missing=[]
    for r in load_rows:
        k,v=r['kind'],r['value']
        if k not in ['native_status','https_status']:continue
        raw=bytes.fromhex(v['body_hex']);body=json.loads(raw)
        require(0<=r['monotonic_ns']-v['began_monotonic_ns']<=(3 if k=='native_status' else 15)*10**9,'HTTP deadline')
        if k=='https_status':
            expected=f'GET /api/v1/status HTTP/1.1\r\nHost: {NAME}:18443\r\nConnection: close\r\n\r\n'.encode()
            require(bytes.fromhex(v['request_hex'])==expected and v['status']==200 and v['peer_sha256']==PEER and
                int(dict((k.lower(),v) for k,v in v['headers'])['content-length'])==len(raw) and
                body['transport']['active']==2 and body['transport']['pending']==0,'Authenticated concurrent HTTPS')
            dest=https
        else:
            require(body==v['value'],'Native HTTP raw/summary')
            ident=body.get('host',{}).get('identity')
            if ident is None:continue
            require(ident['device_id']==DEVICE and ident['boot_id']==packet['boot_id'],'Native HTTP identity');dest=host
        if body['job'] is None:
            require(k=='native_status','Missing HTTPS authority');host_missing.append(r['monotonic_ns']);continue
        dest.append(dict(began=v['began_monotonic_ns'],ended=r['monotonic_ns'],value=body['job']))
    # Native wire supplies authority; preserve nullable host HTTP publication separately.
    families.update(https=(https,21_000_000_000))
    for name,(values,period) in families.items():
        coverage[name]=cadence(values,period,arm['started_ns'],end)
        active=[v for v in values if v['value']['state']=='running']
        require(active and active[-1]['ended']-active[0]['began']>=384000000000-2*period,'Full RF nominal overlap')
        for v in values:
            s=v['value'];require(s['boot_id']==packet['boot_id'] and s['job_id'] in [None,job['job_id']] and
                s['owner_id'] in [None,packet['owner_id']] and s['output_active'] is (s['state']=='running'),'Nominal authority')
            if running[0]['monotonic_ns']+period<=v['began'] and v['ended']<=running[-1]['monotonic_ns']-period:
                require(s['state']=='running' and s['owner_id']==packet['owner_id'],'Nominal RF continuity')
    lr=json.loads((root/'contention-result.json').read_text())
    require(lr==load_rows[-1]['value']==dict(status='CAPTURED_REQUIRES_AUDIT',https_requests=len(https),native_exit=0) and
        len(https)<=plan['maximum_https_requests'],'Native orderly finish/budget')
    result=json.loads((root/'rf-result.json').read_text())
    require(result==rows[-1]['value']==dict(status='STOPPED_FINAL_STATE_UNVERIFIED',armed_jobs=[job['job_id']],
        completed_jobs=[],renewals=1,rf_duration_ns_charged=384000000000,**{'final-a-error':'Inactive/unowned admission'},
        faults=['wtp action: '+failure['value']['error']]),'Original failed C1 result retained')
    return dict(status='C1_MAXIMUM_EVENT_COMPLETION_WITH_NOMINAL_CONTENTION_VERIFIED',family_closed=False,
        original_runner_status='FAILED',failure_classification='Confirmed harness expectation defect',failure=failure,
        packet_sha256=frozen,source_revision=packet['source_revision'],image_sha256=packet['image_sha256'],
        boot_id=packet['boot_id'],jobs=metrics,coverage=coverage,native=native_metrics,https_requests=len(https),
        terminal_record=record,maximum_events=512,rf_duration_ns_charged=384000000000,
        native_http_missing_job_publications=host_missing,native_http_authority_credit=False,
        maximum_allocator_peak_bytes=max(r['value']['value']['allocator_peak_bytes'] for r in samples['info']),
        maximum_heap_allocated_bytes=max(r['value']['value']['heap_allocated_bytes'] for r in samples['info']),
        limitations=['No maximum WTP/HTTP body or USB pressure claim','No retention/reclamation closure'])
