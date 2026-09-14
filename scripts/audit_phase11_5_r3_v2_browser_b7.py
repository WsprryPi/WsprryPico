"""Reconcile frozen B7 without granting failed observation/cancellation credit."""
import hashlib
import base64
import json
from pathlib import Path
from urllib.parse import urlsplit
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_r3_v2_browser_observer import validate
from audit_phase11_5_r3_v2_browser_observer import audit as observer
from audit_phase11_5_r3_v2_browser import body_bytes, ORIGIN, PEER, ASSETS

PACKET = '22f191f41c43eab0dea11de654dd13ef20235aa72f1ba08c57c01e9b7acbdce3'
JOB = '88b420ee9f4f464492fdb6f71cca32a9'
SESSION = '18726328398e40f89a01efea3baa55e9'


def audit(root):
    require(digest(root/'packet.json') == PACKET, 'Frozen B7 packet')
    packet = validate(json.loads((root/'packet.json').read_text()))
    obs = observer(root, packet, b7_diagnostic=True)
    raw = (root/'browser.jsonl').read_bytes()
    require(raw.endswith(b'\n'), 'Truncated browser journal row')
    rows = [json.loads(line) for line in raw.splitlines()]
    require([r['sequence'] for r in rows] == list(range(len(rows))) and
        all(a['monotonic_ns'] <= b['monotonic_ns'] for a,b in zip(rows, rows[1:])) and
        rows[0]['kind'] == 'start' and rows[0]['value'] == dict(packet_sha256=PACKET,netns=packet['netns']),
        'Browser journal provenance')
    require(all(r['kind'] in ['start','browser_version','request_guard','network_request',
        'network_response','network_body','peer_certificate','dom','arm_charge'] for r in rows),
        'Unexpected browser activity or invented finish')
    require(json.loads((root/'browser-result.json').read_text()) == dict(status='RUNNING',
        rf_jobs_charged=1,rf_duration_ns_charged='155750001000',cases=[]), 'Original unfinished producer result')
    require(json.loads((root/'browser-binding.json').read_text()) ==
        dict(packet_sha256=PACKET,session=SESSION,job_ids=[JOB]), 'Browser binding')
    require([r['value'] for r in rows if r['kind']=='peer_certificate']==[dict(sha256=PEER)], 'Actual certificate')
    requests={};responses={};bodies={};guards={};dom={}
    for r in rows:
        k,v=r['kind'],r['value']
        target,key = (requests,v.get('requestId')) if k=='network_request' else (
            (responses,v.get('requestId')) if k=='network_response' else (
            (bodies,v.get('request_id')) if k=='network_body' else (
            (guards,v.get('network_id')) if k=='request_guard' else (None,None))))
        if target is not None:
            require(key not in target,'Duplicate network evidence');target[key]=r
        if k=='dom':
            name=v['name'];require(name not in dom,'Duplicate DOM');dom[name]=r
            require(json.loads((root/(name+'-dom.json')).read_text())=={k:x for k,x in v.items() if k!='name'},'DOM file/trace')
            require((root/(name+'.png')).read_bytes().startswith(b'\x89PNG\r\n\x1a\n'),'Missing referenced screenshot')
    expected_dom=['initial','file-30001-rejected','case-3-armed','case-3-running','case-3-before-abort']
    expected_dom += [m+'-'+n for m in ['qrss','fskcw','dfcw'] for n in ['31','32','33','spaces-32']]
    require(set(dom)==set(expected_dom),'Missing or invented checkpoint')
    require(set(requests)==set(responses) and set(requests)-set(bodies)=={'101.37'},'Original missing final GET body')
    internal={k for k,r in requests.items() if r['value']['request']['url'].startswith('data:')}
    require(len(internal)<=1 and set(guards)==set(requests)-internal and len(guards)<=packet['maximum_request_count'],
        'Network guard coverage')
    posts=[];assets=set()
    for key,row in requests.items():
        q=row['value']['request'];response=responses[key]['value']['response']
        if key in internal:
            require(q['method']=='GET' and hashlib.sha256(q['url'].encode()).hexdigest()==
                '04e449d20d0365d881a54ed24af7ed00fe79dd9f9e601248f4fd7793003924f2' and
                body_bytes(bodies[key]['value']['body'])==base64.b64decode(q['url'].split(',',1)[1],validate=True),
                'Local browser resource bytes');continue
        url=urlsplit(q['url'])
        require(url.scheme+'://'+url.netloc==ORIGIN and not url.query and not url.fragment,'Foreign target request')
        g=guards[key]['value']['request']
        require(all(g.get(k)==q.get(k) for k in ['method','url','postData']),'Guard/request disagreement')
        require(response['url']==q['url'] and response['securityState']=='secure' and
            response['securityDetails']['protocol']=='TLS 1.3' and not response.get('fromDiskCache',False) and
            not response.get('fromServiceWorker',False),'Authenticated uncached response')
        require(response['status']==200 or (url.path=='/favicon.ico' and response['status']==404),'HTTP result')
        if key=='101.37':
            require(q['method']=='GET' and url.path=='/api/v1/status' and rows[-1]==responses[key],
                'Only final stopped GET is incomplete');continue
        body=bodies[key]['value'];require(body['response']==response,'Response/body binding')
        payload=body_bytes(body['body'])
        require(len(payload)==int(response['headers']['Content-Length']) and
            0<=body['finished']['timestamp']-row['value']['timestamp']<=30,'Body length/deadline')
        if url.path=='/':
            require(hashlib.sha256(payload).hexdigest()=='c2e866fdc8e26efbafeb87a94452d20db8ba83d3cdef4bfe6a70db330771f9b9','Static page identity')
            assets.add('/')
        if url.path in ASSETS:require(hashlib.sha256(payload).hexdigest()==ASSETS[url.path],'Static asset identity')
        if q['method']=='POST':
            require(url.path=='/api/v1/jobs','Foreign mutation route')
            request=json.loads(q['postData']);reply=json.loads(payload)
            require(request['session_id']==SESSION and reply['ok'] is True and
                reply['request_id']==request['request_id'],'Mutation response binding')
            posts.append((request,reply['result'],row['monotonic_ns']))
        else:
            require(q['method']=='GET' and url.path in ['/',*ASSETS,'/favicon.ico','/api/v1/status','/api/v1/config','/api/v1/capabilities'],
                'Undeclared read')
    require(assets=={'/'} and [q['operation'] for q,r,t in posts]==['HELLO','CLAIM','LOAD_MESSAGE','ARM'] and
        len({q['request_id'] for q,r,t in posts})==4,'Exact four mutations; no ABORT or retry')
    hello,claim,load,arm=posts
    require(hello[1]['device_id']==packet['device_id'] and hello[1]['boot_id']==packet['boot_id'] and
        hello[0]['body']==dict(versions=['WTP/1'],client_name='WsprryPico browser',client_version='1') and
        claim[0]['body']==dict(owner_id=SESSION,lease_ms=30000) and claim[1]['owner_id']==SESSION,'Device/owner')
    require(load[0]['body']==dict(packet['cases'][3]['message'],job_id=JOB) and load[1]['job_id']==JOB,'Exact LOAD')
    charge,=[r for r in rows if r['kind']=='arm_charge']
    require(charge['value']==dict(job_id=JOB,duration_ns='155750001000',start_utc_ns=arm[0]['body']['start_utc_ns']) and
        arm[0]['body']['job_id']==arm[1]['job_id']==JOB and arm[1]['state']=='armed' and
        arm[1]['start_utc_ns']==arm[0]['body']['start_utc_ns'],'Acknowledged ARM and full charge')
    statuses=[r['value']['value'] for r in obs['samples']['status'] if r['value']['value']['job_id']==JOB]
    require({'armed','running','complete'}<={s['state'] for s in statuses} and all(
        s['boot_id']==packet['boot_id'] and s['owner_id'] in [SESSION,None] and
        s['output_active'] is (s['state']=='running') for s in statuses),'Independent lifecycle/authority')
    before=obs['inventories']['before-a'];final=obs['inventories']['final-a']
    require(json.loads((root/'browser-observer-result.json').read_text())['final-a']==final['wtp']['STATUS'],
        'Final observer summary must match raw inventory')
    require(final['wtp']['STATUS']['state']=='complete' and final['wtp']['STATUS']['job_id']==JOB and
        final['wtp']['STATUS']['terminal_records'][0]['state']=='complete' and
        final['wtp']['STATUS']['terminal_records'][0]['job_id']==JOB and
        int(final['info']['launch_epoch'])==int(before['info']['launch_epoch'])+1,'One physical launch and retained completion')
    for size in [30000,30001]:
        require((root/f'job-{size}.json').stat().st_size==size and
            json.loads((root/f'job-{size}.json').read_bytes())==packet['cases'][0]['job'],'Real file input')
    require(dom['case-3-running']['value']['state']=='armed' and
        dom['case-3-before-abort']['value']['state']=='running' and
        dom['case-3-before-abort']['value']['abortDisabled'] is True,'Original UI synchronization findings')
    return dict(status='B7_STOPPED_LIFECYCLE_RECONCILED',family_closed=False,
        packet_sha256=PACKET,source_revision=packet['source_revision'],image_sha256=packet['image_sha256'],
        boot_id=packet['boot_id'],job_id=JOB,classification='OBSERVATION_FAILURE',
        delay_cause='UNRESOLVED: host records cannot separate target service, USB delivery, scheduling and logging',
        cadence=obs['cadence'],rf_jobs_charged=1,rf_duration_ns_charged=155750001000,
        physical_launches=1,terminal_completions=1,cancellation_verified=False,full_observation_verified=False,
        physical_timing_acceptance=False,missing_final_get_body='101.37',
        preserved_assertions=['Repaired static page served','One acknowledged finite DFCW ARM',
            'Independent Running then Complete/inactive/unowned authority'],
        final_authority=final['wtp']['STATUS'],visual_review='REQUIRED_SEPARATELY')
