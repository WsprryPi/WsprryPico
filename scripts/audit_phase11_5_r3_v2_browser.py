"""Audit real Chromium target bytes, job ownership, UI observations and physical execution."""
import base64,copy,hashlib,json
from pathlib import Path
from urllib.parse import urlsplit
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_r3_v2_browser_observer import validate
from audit_phase11_5_r3_v2_hour import journal,NAME,PEER
from audit_phase11_5_r3_v2_browser_observer import audit as audit_observer
from audit_phase11_5_r3_v2_rf import timing

PACKET='7b0de46064c8379400a2dc6b937ab5e32b64fe750c15bb18ca2692d8fa10c4f6'
ORIGIN='https://'+NAME+':18443'
ASSETS={'/app.js':'0c713e289fa8fb2aca945d710d777f15b0eb6877d2e02af7d857c69c220c67bc',
 '/style.css':'b355d50badc457d2eca666f5b146c6688d12b971f756916699bfc5d71fcb7e2a'}


def body_bytes(value):
    return base64.b64decode(value['body'],validate=True) if value['base64Encoded'] else value['body'].encode()


def duration_text(ns):
    minutes,ns=divmod(ns,60_000_000_000);seconds,fraction=divmod(ns,1_000_000_000)
    return (str(minutes)+' min ' if minutes else '')+str(seconds)+(
        '.'+f'{fraction:09d}'.rstrip('0') if fraction else '')+' s'


def audit(root):
    require(digest(root/'packet.json')==PACKET,'Unreviewed browser packet')
    packet=validate(json.loads((root/'packet.json').read_text()));observed=audit_observer(root,packet)
    rows=journal(root/'browser.jsonl');require(rows[0]['value']==dict(packet_sha256=PACKET,netns=packet['netns']),
        'Browser provenance')
    require(all(r['kind'] in ['start','finish','browser_version','request_guard','network_request','network_response',
        'network_body','peer_certificate','dom','arm_charge'] for r in rows),'Browser failure/unknown activity')
    result=json.loads((root/'browser-result.json').read_text())
    require(result==rows[-1]['value'] and result['status']=='CAPTURED_REQUIRES_AUDIT' and
        result['rf_jobs_charged']==4 and result['rf_duration_ns_charged']=='452250003000' and len(result['cases'])==4,
        'Browser completion/accounting')
    version,=[r['value'] for r in rows if r['kind']=='browser_version']
    require(version['product'].startswith('Chrome/151.'),'Reviewed actual Chromium version')
    cert,=[r['value'] for r in rows if r['kind']=='peer_certificate'];require(cert==dict(sha256=PEER),'Actual target certificate')
    binding=json.loads((root/'browser-binding.json').read_text());session=binding['session']
    require(binding['packet_sha256']==PACKET and len(set(binding['job_ids']))==4 and
        len(session)==32 and all(c in '0123456789abcdef' for c in session),'Browser identity binding')
    requests={};responses={};bodies={};guards={};dom={};assets=set();posts=[]
    for row in rows:
        k,v=row['kind'],row['value']
        if k=='network_request':
            key=v['requestId'];require(key not in requests and 'redirectResponse' not in v,'Request reused/redirected')
            requests[key]=row
        elif k=='network_response':
            key=v['requestId'];require(key not in responses,'Duplicate response');responses[key]=row
        elif k=='network_body':
            key=v['request_id'];require(key not in bodies,'Duplicate body');bodies[key]=row
        elif k=='request_guard':
            key=v['network_id'];require(key not in guards,'Duplicate guarded request');guards[key]=row
        elif k=='dom':
            require(v['name'] not in dom,'Duplicate DOM checkpoint');dom[v['name']]=row
            require(json.loads((root/(v['name']+'-dom.json')).read_text())=={k:x for k,x in v.items() if k!='name'},
                'DOM file/trace mismatch')
            require((root/(v['name']+'.png')).read_bytes().startswith(b'\x89PNG\r\n\x1a\n'),'Missing rendered checkpoint')
    require(set(requests)==set(responses)==set(bodies)==set(guards) and
        len(requests)==result['request_count']<=packet['maximum_request_count'],'Missing/extra browser network evidence')
    for key,row in requests.items():
        request=row['value']['request'];response=responses[key]['value']['response'];body=bodies[key]['value']
        url=urlsplit(request['url']);require(url.scheme+'://'+url.netloc==ORIGIN and not url.query and not url.fragment,
            'Foreign browser URL')
        require(guards[key]['value']['request']['url']==request['url'] and
            guards[key]['value']['request']['method']==request['method'] and
            guards[key]['value']['request'].get('postData')==request.get('postData'),'Guard differs from actual request')
        require(body['response']==response and response['url']==request['url'] and
            response['securityState']=='secure' and response['securityDetails']['protocol']=='TLS 1.3' and
            not response.get('fromDiskCache',False) and not response.get('fromServiceWorker',False),
            'Actual authenticated uncached target response')
        raw=body_bytes(body['body']);status=int(response['status'])
        require(status==200 or (url.path=='/favicon.ico' and status==404),'Unexpected browser HTTP outcome')
        require(row['monotonic_ns']<=bodies[key]['monotonic_ns'] and
            0<=body['finished']['timestamp']-row['value']['timestamp']<=30,'Browser request deadline')
        if url.path in ASSETS:
            require(hashlib.sha256(raw).hexdigest()==ASSETS[url.path],'Served UI source differs from identified firmware');assets.add(url.path)
        if request['method']=='POST':
            require(url.path=='/api/v1/jobs' and status==200,'Unexpected mutation route')
            q=json.loads(request['postData']);r=json.loads(raw)
            require(q['session_id']==session and r['ok'] is True and r['request_id']==q['request_id'],
                'Browser operation response/session')
            posts.append(dict(request=q,response=r['result'],started=row['monotonic_ns'],ended=bodies[key]['monotonic_ns']))
        else:require(request['method']=='GET' and url.path in ['/',*ASSETS,'/favicon.ico','/api/v1/status','/api/v1/capabilities','/api/v1/config'],
            'Undeclared browser read')
    require(assets==set(ASSETS),'Target UI assets not captured')
    posts.sort(key=lambda p:p['started']);require(len({p['request']['request_id'] for p in posts})==len(posts),'Mutation retried')
    require(dom['file-30001-rejected']['monotonic_ns']<posts[0]['started'] and
        'at most 30,000 bytes' in dom['file-30001-rejected']['value']['notice'],'Oversized file was sent or not rejected')
    for size in [30000,30001]:
        file=root/f'job-{size}.json';require(file.stat().st_size==size and json.loads(file.read_bytes())==packet['cases'][0]['job'],
            'Actual valid file bytes/size')
    for mode in ['qrss','fskcw','dfcw']:
        for count in [31,32,33]:
            preview=dom[f'{mode}-{count}']['value']['preview']
            require(('1–32 characters' if count==33 else f'{count} / 32 characters') in preview,'Message boundary UI')
        require('32 / 32 characters' in dom[mode+'-spaces-32']['value']['preview'],'Spaces not included in boundary')
    index=0;cases=[];charges=[r for r in rows if r['kind']=='arm_charge'];require(len(charges)==4,'ARM charge count')
    for n,c in enumerate(packet['cases']):
        expected=['HELLO','CLAIM','LOAD' if n==0 else 'LOAD_MESSAGE','ARM']
        group=posts[index:index+4];require([p['request']['operation'] for p in group]==expected,'Browser operation ordering')
        index+=4;hello,claim,load,arm=group
        require(hello['request']['body']==dict(versions=['WTP/1'],client_name='WsprryPico browser',client_version='1') and
            hello['response']['boot_id']==packet['boot_id'] and hello['response']['device_id']==packet['device_id'],'HELLO identity')
        require(claim['request']['body']==dict(owner_id=session,lease_ms=30000),'Owner claim')
        q=load['request']['body'];job_id=q['job_id'];require(binding['job_ids'][n]==job_id,'Actual loaded job binding')
        if n==0:
            require(q==c['job'],'File immutable job');job=copy.deepcopy(q)
        else:
            require({k:v for k,v in q.items() if k!='job_id'}==c['message'],'Compact message changed')
            job=copy.deepcopy(c['compiled_job_template']);job['job_id']=job_id
        require(job['total_duration_ns']==c['duration_ns'] and
            load['response']['job_id']==job_id and load['response']['state']=='loaded','Loaded job/duration')
        adjustments=load['response']['adjustments']
        require([a['event_index'] for a in adjustments]==[i for i,e in enumerate(job['events']) if e['rf_on']] and
            all(a['requested_frequency_nhz']==job['events'][a['event_index']]['frequency_nhz'] for a in adjustments),
            'Target adjustments do not represent the frozen expanded message')
        if n:
            preview=dom[f'case-{n}-armed']['value']['preview']
            require(duration_text(int(c['duration_ns'])) in preview and '384 / 512 events' in preview and
                '32 / 32 characters' in preview,'UI exact duration/event count')
        q=arm['request']['body'];charge=charges[n]
        require(q['job_id']==job_id and q['max_start_uncertainty_ns']=='500000000' and
            arm['response']['job_id']==job_id and arm['response']['state']=='armed' and
            arm['response']['start_utc_ns']==q['start_utc_ns'] and
            charge['value']==dict(job_id=job_id,duration_ns=c['duration_ns'],start_utc_ns=q['start_utc_ns']) and
            charge['monotonic_ns']<=arm['ended'],'ARM job/time/accounting')
        terminal=dom[f'case-{n}-terminal'];s=terminal['value']['job'];want='aborted' if n>=2 else 'complete'
        require(s['boot_id']==packet['boot_id'] and s['job_id']==job_id and s['state']==want and s['output_active'] is False,
            'UI terminal authority')
        if n>=2:
            abort=posts[index];index+=1
            require(abort['request']['operation']=='ABORT' and abort['request']['body']==dict(job_id=job_id) and
                abort['response']['state']=='aborted','Owner cancellation')
        if index<len(posts) and posts[index]['request']['operation']=='RELEASE':
            require(posts[index]['request']['body']=={},'Release body');index+=1
        samples=observed['samples'];statuses=[r for r in samples['status'] if r['value']['value']['job_id']==job_id]
        require(any(r['value']['value']['state']=='armed' for r in statuses),'Independent Armed observation')
        term=[r for r in statuses if r['value']['value']['state']==want];require(term,'Independent terminal observation')
        running=[r for r in statuses if r['value']['value']['state']=='running']
        if n==2:require(not running,'Armed cancellation actually ran')
        else:
            require(running and all(r['value']['value']['output_active'] is True for r in running),'Independent Running')
            if n==3:require(abort['started']-running[0]['monotonic_ns']>=120_000_000_000,'Early long-job abort')
            else:require(term[0]['monotonic_ns']-running[0]['monotonic_ns']>=int(c['duration_ns'])-6_000_000_000,'Truncated completed job')
        selected=[r for r in observed['rows'] if r['monotonic_ns']<=terminal['monotonic_ns']]
        metrics=None
        if n<2:
            metrics=timing(packet,[dict(monotonic_ns=charge['monotonic_ns'],job=job,start_utc_ns=q['start_utc_ns'])],selected)[0]
        before=[r['value']['value'] for r in samples['info'] if r['monotonic_ns']<charge['monotonic_ns']][-1]
        after=[r['value']['value'] for r in samples['info'] if r['monotonic_ns']<=terminal['monotonic_ns']][-1]
        if n==2:require(all(after[k]==before[k] for k in ['dma_irqs','alarm_irqs','tail_irqs','launch_epoch']),
            'Armed cancellation launched hardware')
        if n==3:
            screen=dom['case-3-before-abort'];ui=screen['value']
            require(ui['job']['state']=='running' and ui['job']['job_id']==job_id and ui['abortDisabled'] is False,
                'Long-job progress/abort UI authority')
            candidates=[(responses[key]['monotonic_ns'],json.loads(body_bytes(value['value']['body'])))
                for key,value in bodies.items() if requests[key]['value']['request']['url']==ORIGIN+'/api/v1/status' and
                responses[key]['monotonic_ns']<=screen['monotonic_ns']]
            _,snapshot=max(candidates,key=lambda item:item[0])
            require(snapshot['job']==ui['job'],'Progress UI differs from latest target status')
            elapsed=max(0,min(int(c['duration_ns']),int(snapshot['standalone']['utc_now_ns'])-int(q['start_utc_ns'])))
            percent=(elapsed*1000//int(c['duration_ns']))/10
            require(('estimated '+duration_text(elapsed)+' of '+duration_text(int(c['duration_ns']))+' · '+f'{percent:.1f}%')
                in ui['progress'],'Displayed progress differs from actual target clock and immutable duration')
        cases.append(dict(kind=c['kind'],job_id=job_id,result=want,planned_duration_ns=c['duration_ns'],timing=metrics))
    require(index==len(posts),'Unexpected trailing mutation')
    require(result['cases']==[dict(kind=c['kind'],job_id=c['job_id'],planned_duration_ns=c['planned_duration_ns'],result=c['result'],
        **({'observed_running_ns':result['cases'][n]['observed_running_ns']} if n==3 else {})) for n,c in enumerate(cases)],
        'Browser summary differs from independently audited operations')
    return dict(status='B1_ACTUAL_CHROMIUM_FEATURES_VERIFIED',family_closed=False,packet_sha256=PACKET,
        source_revision=packet['source_revision'],image_sha256=packet['image_sha256'],boot_id=packet['boot_id'],
        rf_jobs_charged=4,rf_duration_ns_charged=452250003000,cases=cases,cadence=observed['cadence'],
        rendered_checkpoints=len(dom),rendered_visual_review='REQUIRED_SEPARATELY',network_requests=len(requests),
        maximum_allocator_peak_bytes=max(r['value']['value']['allocator_peak_bytes'] for r in observed['samples']['info']))
