"""Preserve bounded browser components without converting a stopped run to PASS."""
import base64
import json
from pathlib import Path
from phase11_5_inventory import require, loads_console
from phase11_5_device_management import digest
from phase11_5_r3_preflight import audit_inventory
from phase11_5_pilot_supervisor import configuration
from phase11_5_r3_v2_rf import validate_info
from audit_phase11_5_idle import frames
from audit_phase11_5_r3_capacity_probe import rows
from audit_phase11_5_r3_v2_rf import timing
from audit_phase11_5_r3_v2_browser import body_bytes, ASSETS, ORIGIN, PEER
from validate_wtp_contract import SchemaValidator, unique_object, reject_constant
import hashlib
import re

B3 = 'ef0a4f7f42182001783878ce3216f08a654104ad86a593f78d0ae60cb00e4254'


def audit(root):
    require(digest(root/'packet.json') == B3, 'Frozen B3 packet')
    packet = json.loads((root/'packet.json').read_text())
    inventories = {}
    for name in ['before-a', 'final-a']:
        require(not (root/(name+'.stderr')).read_bytes(), 'Inventory stderr')
        inventories[name] = audit_inventory(root/(name+'.stdout'),
            dict(serial=packet['serial'], device_id=packet['device_id']),
            packet['inventory_session'], packet['stage_sha256']['scripts/phase11_5_inventory.py'])
    before, final = inventories['before-a'], inventories['final-a']
    require(configuration(before) == configuration(final), 'Configuration changed')
    for value in [before, final]:
        s = value['wtp']['STATUS']
        require(s['boot_id'] == packet['boot_id'] and s['state'] == 'empty' and
            s['owner_id'] is s['job_id'] is None and s['output_active'] is False and
            value['info']['status']['output_active'] is False, 'Inactive same-boot boundary')
    validate_info(before['info'], before, packet)
    trace = rows(root/'browser-observer.jsonl')
    require(trace[0]['value'] == dict(packet_sha256=B3,
        baseline_sha256=digest(root/'before-a.stdout'), boot_id=packet['boot_id']), 'Observer provenance')
    result = json.loads((root/'browser-observer-result.json').read_text())
    require(trace[-1]['kind'] == 'finish' and trace[-1]['value'] == result and result == {
        'status':'STOPPED_FINAL_STATE_UNVERIFIED', 'final-a-error':'Allocator reserve/failures',
        'faults':['info: Allocator reserve/failures', 'supervisor: Browser did not finish within finite runtime']},
        'Original failure must remain unchanged')
    schema = json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text())
    validator = SchemaValidator(schema)
    pending = {}; seen = set(); wire = b''; messages = []; console = b''
    console_start = None; info = None; status = None; last_event = None; samples = {k:[] for k in ['info','status','health']}
    rejected_info = []; failures = []
    for row in trace:
        kind, v, stamp = row['kind'], row['value'], row['monotonic_ns']
        if kind == 'console_tx':
            require(console_start is None and info is None and bytes.fromhex(v['hex']) == b'INFO\n', 'Console request')
            console_start = stamp
        elif kind == 'console_rx':
            require(console_start is not None, 'Unsolicited Console')
            console += bytes.fromhex(v['hex'])
            if b'\n' in console:
                require(console.endswith(b'\n') and console.count(b'\n') == 1 and stamp-console_start <= 5_000_000_000, 'INFO framing/deadline')
                info = loads_console(console.decode().strip()); console = b''; console_start = None
        elif kind == 'wtp_tx':
            values, left = frames(bytes.fromhex(v['hex']))
            require(not left and values == [v['request']], 'WTP request raw/summary')
            q = values[0]
            require(not pending and not validator.errors(q,schema) and q['session_id'] == packet['peer_session'] and
                q['op'] in ['HELLO','STATUS'] and q['request_id'] not in seen, 'Observer request scope')
            seen.add(q['request_id']); pending[q['request_id']] = (stamp,q)
        elif kind == 'wtp_rx':
            decoded, wire = frames(wire+bytes.fromhex(v['hex'])); messages.extend(decoded)
        elif kind == 'wtp_message':
            require(messages and messages.pop(0) == v and not validator.errors(v,schema) and
                v['session_id'] == packet['peer_session'], 'WTP response raw/schema')
            if v['type'] == 'event':
                require(v['boot_id'] == packet['boot_id'] and v['event'] in ['JOB_STATE','OWNER_RELEASED'] and
                    (last_event is None or int(v['event_id']) == last_event+1), 'Event identity/sequence')
                last_event = int(v['event_id']); continue
            require(v['ok'] and v['request_id'] in pending, 'Unmatched WTP response')
            began,q = pending.pop(v['request_id'])
            require(q['op'] == v['op'] and stamp-began <= 5_000_000_000, 'WTP reply deadline')
            if q['op'] == 'STATUS': status = v['body']
            else: require(v['body']['device_id'] == packet['device_id'] and v['body']['boot_id'] == packet['boot_id'], 'HELLO identity')
        elif kind in samples:
            require(0 <= stamp-v['began_monotonic_ns'] <= 5_000_000_000, 'Sample deadline')
            if kind == 'info':
                require(info == v['value'], 'INFO raw/summary'); validate_info(info,before,packet); info = None
            elif kind == 'status':
                require(status == v['value'] and status['boot_id'] == packet['boot_id'], 'STATUS raw/summary')
                require(status['output_active'] is (status['state'] == 'running'), 'STATUS authority'); status = None
            else: require(v['value']['boot'] == packet['host_boot_id'] and v['value']['throttled'] == 'throttled=0x0','Host health')
            samples[kind].append(row)
        elif kind == 'failure':
            failures.append(row)
            if v['worker'] == 'info':
                require(info is not None and v['error'] == 'Allocator reserve/failures', 'Failure lacks raw INFO')
                rejected_info.append(info); info = None
        else: require(kind in ['start','finish','browser_starting','status_finish','health_finish'], 'Unknown observer activity')
    require(not pending and not wire and not messages and not console and console_start is None and info is status is None,
        'Incomplete observer bytes')
    require(len(failures) == 2 and len(rejected_info) == 1, 'Failure count')
    failed = rejected_info[0]
    for i in [failed,final['info']]:
        require(i['heap_capacity_bytes'] == 220348 and i['allocator_peak_bytes'] == 194260 and
            int(i['allocator_failures']) == i['tls_allocation_failures'] == 0 and i['recovery_boot'] is False and
            all(i[k] == 0 for k in ['fault_stage','fault_hash','fault_pc','fault_status','core0_stack_fault_status','core1_stack_fault_status']),
            'Exact reserve failure without allocation failure/reset')
    raw_browser = (root/'browser.jsonl').read_text()
    require(raw_browser.endswith('\n'), 'Truncated browser journal')
    browser = [json.loads(line, object_pairs_hook=unique_object, parse_constant=reject_constant)
               for line in raw_browser.splitlines()]
    require([r['sequence'] for r in browser] == list(range(len(browser))) and
        all(a['monotonic_ns'] <= b['monotonic_ns'] for a,b in zip(browser,browser[1:])), 'Browser chronology')
    require(browser[0]['kind'] == 'start' and browser[0]['value'] == dict(packet_sha256=B3,netns=packet['netns']), 'Browser provenance')
    require([r['value'] for r in browser if r['kind']=='peer_certificate']==[dict(sha256=PEER)] and
        len([r for r in browser if r['kind']=='browser_version'])==1, 'Browser certificate/version evidence')
    requests={}; responses={}; bodies={}; guards={}; dom={}; charges=[]
    for row in browser:
        kind,v=row['kind'],row['value']
        if kind in ['network_request','network_response','network_body','request_guard']:
            table,key = {'network_request':(requests,'requestId'),'network_response':(responses,'requestId'),
                'network_body':(bodies,'request_id'),'request_guard':(guards,'network_id')}[kind]
            require(v[key] not in table,'Duplicate browser event'); table[v[key]]=row
        elif kind=='dom':
            require(v['name'] not in dom,'Duplicate DOM');dom[v['name']]=row
            require(json.loads((root/(v['name']+'-dom.json')).read_text()) == {k:x for k,x in v.items() if k!='name'} and
                (root/(v['name']+'.png')).read_bytes().startswith(b'\x89PNG\r\n\x1a\n'),'DOM/screenshot evidence')
        elif kind=='arm_charge':charges.append(row)
        elif kind=='peer_certificate':require(v==dict(sha256=PEER),'Certificate pin')
        else:require(kind in ['start','browser_version'],'Unexpected browser outcome')
    internal = {key for key,row in requests.items() if row['value']['request']['url'].startswith('data:')}
    require(len(internal)==1 and set(requests)-internal==set(guards) and set(responses)==set(bodies) and len(requests)==len(responses)+1,'Exact pending request')
    posts=[]; assets=set()
    for key,row in requests.items():
        q=row['value']['request']
        if key in internal:
            require(q['method']=='GET' and q['url'].startswith('data:image/svg+xml;base64,') and
                hashlib.sha256(q['url'].encode()).hexdigest()=='04e449d20d0365d881a54ed24af7ed00fe79dd9f9e601248f4fd7793003924f2' and
                body_bytes(bodies[key]['value']['body']) == base64.b64decode(q['url'].split(',',1)[1],validate=True),
                'Browser-local date icon bytes')
            continue
        g=guards[key]['value']['request']
        require(q['url'].startswith(ORIGIN+'/') and all(q.get(k)==g.get(k) for k in ['url','method','postData']), 'Guard/request mismatch')
        if key not in responses:
            require(json.loads(q['postData'])['operation']=='ARM','Only next ARM may lack response');continue
        response=responses[key]['value']['response'];body=bodies[key]['value'];raw=body_bytes(body['body'])
        require(body['response']==response and response['url']==q['url'] and response['status']==200 and
            response['securityState']=='secure' and response['securityDetails']['protocol']=='TLS 1.3' and
            not response.get('fromDiskCache',False) and not response.get('fromServiceWorker',False) and
            int(response['headers']['Content-Length'])==len(raw),'Authenticated complete body')
        require(row['monotonic_ns']<=bodies[key]['monotonic_ns'] and
            0<=body['finished']['timestamp']-row['value']['timestamp']<=30,'Browser response deadline')
        if q['url'][len(ORIGIN):] in ASSETS:
            path=q['url'][len(ORIGIN):];require(hashlib.sha256(raw).hexdigest()==ASSETS[path],'Asset identity');assets.add(path)
        if q['url']==ORIGIN+'/':
            require(hashlib.sha256(raw).hexdigest()=='c2e866fdc8e26efbafeb87a94452d20db8ba83d3cdef4bfe6a70db330771f9b9','Served document identity')
            for tag,path in [('style','/style.css'),('script','/app.js')]:
                parts=re.findall(b'<'+tag.encode()+b'>(.*?)</'+tag.encode()+b'>',raw,re.DOTALL)
                require(len(parts)==1 and hashlib.sha256(parts[0]).hexdigest()==ASSETS[path],'Inline asset identity');assets.add(path)
        if q['method']=='POST':
            request=json.loads(q['postData']);reply=json.loads(raw)
            require(reply['ok'] and reply['request_id']==request['request_id'],'Browser operation identity')
            posts.append((row,request,reply['result']))
        else:require(q['method']=='GET' and q['url'][len(ORIGIN):] in
            ['/','/api/v1/capabilities','/api/v1/status','/api/v1/config',*ASSETS],'Unexpected method/path')
    require(assets==set(ASSETS) and len(charges)==1,'Assets/one ARM charge')
    posts.sort(key=lambda p:p[0]['monotonic_ns'])
    require([q['operation'] for _,q,_ in posts]==['HELLO','CLAIM','LOAD','ARM','HELLO','CLAIM','LOAD_MESSAGE'],'Exact accepted operations')
    load,arm=posts[2],posts[3];job=load[1]['body'];job_id=job['job_id']
    binding=json.loads((root/'browser-binding.json').read_text());session=binding['session']
    require(binding['packet_sha256']==B3 and len(set(binding['job_ids']))==2 and
        all(q['session_id']==session for _,q,_ in posts) and len({q['request_id'] for _,q,_ in posts})==len(posts),
        'Browser session/request identity')
    for _,q,r in posts:
        if q['operation']=='HELLO':require(r['boot_id']==packet['boot_id'] and r['device_id']==packet['device_id'],'Browser HELLO identity')
        if q['operation']=='CLAIM':require(q['body']==dict(owner_id=session,lease_ms=30000) and r['owner_id']==session,'Browser owner')
    require(job==packet['cases'][0]['job'] and arm[1]['body']['job_id']==job_id and
        arm[2]['job_id']==job_id and arm[2]['state']=='armed' and arm[2]['start_utc_ns']==arm[1]['body']['start_utc_ns'], 'Tone immutable LOAD/ARM')
    charge=charges[0];require(charge['value']==dict(job_id=job_id,duration_ns='10000000000',start_utc_ns=arm[1]['body']['start_utc_ns']), 'Charge')
    require(charge['monotonic_ns']<=arm[0]['monotonic_ns']+30_000_000_000,'Charge deadline')
    summary=json.loads((root/'browser-result.json').read_text())
    require(summary==dict(status='RUNNING',rf_jobs_charged=1,rf_duration_ns_charged='10000000000',
        cases=[dict(kind='file-complete',job_id=job_id,planned_duration_ns='10000000000',result='complete')]), 'Preserved partial producer accounting')
    terminal=dom['case-0-terminal'];s=terminal['value']['job']
    require(s['job_id']==job_id and s['state']=='complete' and s['output_active'] is False and
        s['boot_id']==packet['boot_id'] and terminal['monotonic_ns']<failures[0]['monotonic_ns'],'Completed Tone before failure')
    for mode in ['qrss','fskcw','dfcw']:
        for count in [31,32,33]:
            require(('1–32 characters' if count==33 else f'{count} / 32 characters') in dom[f'{mode}-{count}']['value']['preview'],'Character UI')
        require('32 / 32 characters' in dom[mode+'-spaces-32']['value']['preview'],'Space counting')
    require('at most 30,000 bytes' in dom['file-30001-rejected']['value']['notice'] and
        dom['file-30001-rejected']['monotonic_ns'] < posts[0][0]['monotonic_ns'],'File rejection before POST')
    until=terminal['monotonic_ns'];prefix=[r for r in trace if r['monotonic_ns']<=until];cadence={}
    for kind,period in [('info',1),('status',5),('health',5)]:
        selected=[r for r in samples[kind] if r['monotonic_ns']<=until];starts=[r['value']['began_monotonic_ns'] for r in selected]
        require(starts and starts[0]-trace[0]['monotonic_ns']<=(period+1)*10**9 and until-starts[-1]<=(period+1)*10**9 and
            max((b-a for a,b in zip(starts,starts[1:])),default=0)<=(period+1)*10**9,'Completed prefix cadence')
        cadence[kind]=len(starts)
    require(any(r['value']['value']['job_id']==job_id and r['value']['value']['state']=='running' for r in samples['status']) and
        any(r['value']['value']['job_id']==job_id and r['value']['value']['state']=='complete' for r in samples['status']),'Independent Tone lifecycle')
    metrics=timing(packet,[dict(monotonic_ns=charge['monotonic_ns'],job=job,start_utc_ns=arm[1]['body']['start_utc_ns'])],prefix)[0]
    require(int(final['info']['launch_epoch'])==metrics['epoch'],'Unexpected later RF launch')
    return dict(status='B3_STOPPED_COMPONENTS_VERIFIED',family_closed=False,packet_sha256=B3,
        source_revision=packet['source_revision'],boot_id=packet['boot_id'],
        classification='SUPPORTED_BROWSER_LOAD_HEAP_RESERVE_VIOLATION',
        harness_finding='Guard-triggered stop incorrectly reported as finite-runtime expiry',
        peak_allocator_bytes=194260,heap_capacity_bytes=220348,reserve_bytes=26088,required_reserve_bytes=32768,
        allocator_failures=0,tls_allocation_failures=0,rf_jobs_charged=1,rf_duration_ns_charged=10000000000,
        preserved_assertions=['Three-mode 31/32/33 and spaces UI','Oversized file rejected before POST','Ten-second browser Tone complete'],
        complete_tone=metrics,completed_prefix_samples=cadence,
        final_authority=final['wtp']['STATUS'],full_browser_pass=False,visual_review='REQUIRED_SEPARATELY')
