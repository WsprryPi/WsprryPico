"""Audit real Chromium target bytes, job ownership, UI observations and physical execution."""
import base64,copy,hashlib,json,re
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
    packet_sha=digest(root/'packet.json')
    stopped_b4=packet_sha=='8d37a3a5fb5085716a4add0e6d8b5a1c74c59e36846d31af2b79ba5ba1d51170'
    stopped_b5=packet_sha=='05e1e318b504e3c20e7fb0b233ba42663f52bfd55983e35b1a56f05ced449c80'
    b7=packet_sha=='22f191f41c43eab0dea11de654dd13ef20235aa72f1ba08c57c01e9b7acbdce3'
    b8=packet_sha=='1b0d44f5215c2e6580f8c2bd6ec25b72eb6d9ef76e8c9e85067b2b0dce1e1966'
    b9=packet_sha=='df22c7fea17a0984532c3ee6d4cb4c30c976747d918f449ebe9878f3f4f1f1be'
    require(b9 or b8 or b7 or stopped_b5 or packet_sha in [PACKET,'8d37a3a5fb5085716a4add0e6d8b5a1c74c59e36846d31af2b79ba5ba1d51170','21569af32117cd0ea8bb1117446e3cdf55584325429b5a88abc6b55a3723db5e','ef0a4f7f42182001783878ce3216f08a654104ad86a593f78d0ae60cb00e4254'],'Unreviewed browser packet')
    packet=validate(json.loads((root/'packet.json').read_text()));observed=audit_observer(root,packet)
    rows=journal(root/'browser.jsonl');require(rows[0]['value']==dict(packet_sha256=packet_sha,netns=packet['netns']),
        'Browser provenance')
    require(all(r['kind'] in ['start','finish','browser_version','request_guard','network_request','network_response',
        'network_body','peer_certificate','dom','arm_charge',*(['failure'] if stopped_b4 or stopped_b5 or b8 else []),
        *(['replay_quiet_start'] if stopped_b5 else [])] for r in rows),'Browser failure/unknown activity')
    indices=[1] if stopped_b4 else [2] if stopped_b5 else packet.get('case_indices',[0,1,2,3]);case_count=len(indices)
    planned_ns=sum(int(packet['cases'][n]['duration_ns']) for n in indices)
    result=json.loads((root/'browser-result.json').read_text())
    require(result==rows[-1]['value'] and result['status']==('FAILED' if stopped_b4 or stopped_b5 or b8 else 'CAPTURED_REQUIRES_AUDIT') and
        result['rf_jobs_charged']==case_count and result['rf_duration_ns_charged']==str(planned_ns) and len(result['cases'])==(0 if b8 else case_count),
        'Browser completion/accounting')
    if b8:
        failures=[r['value'] for r in rows if r['kind']=='failure']
        require(result['error']=='Stale independent status' and len(failures)==1 and
            failures[0]['stage']=='producer' and result['error'] in failures[0]['error'],
            'Exact preserved B8 publication-age failure')
    if stopped_b4:
        failures=[r['value'] for r in rows if r['kind']=='failure']
        require(result['error']=='Expected values to be strictly equal:\n\n3 !== 4\n' and len(failures)==1 and
            failures[0]['stage']=='producer' and result['error'] in failures[0]['error'], 'Exact preserved B4 producer assertion')
    if stopped_b5:
        failures=[r['value'] for r in rows if r['kind']=='failure']
        require(result['error']=="Expected values to be strictly equal:\n+ actual - expected\n\n+ 'aborted'\n- 'empty'" and
            len(failures)==1 and failures[0]['stage']=='producer' and result['error'] in failures[0]['error'],
            'Exact preserved B5 stale-observer assertion')
        quiet=[r for r in rows if r['kind']=='replay_quiet_start']
        require(len(quiet)==1 and quiet[0]['value']==dict(seconds=360), 'Quiet interval started but did not complete')
    version,=[r['value'] for r in rows if r['kind']=='browser_version']
    require(version['product'].startswith('Chrome/151.'),'Reviewed actual Chromium version')
    cert,=[r['value'] for r in rows if r['kind']=='peer_certificate'];require(cert==dict(sha256=PEER),'Actual target certificate')
    binding=json.loads((root/'browser-binding.json').read_text());session=binding['session']
    require(binding['packet_sha256']==packet_sha and len(binding['job_ids'])==len(set(binding['job_ids']))==case_count+int(stopped_b4) and
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
    internal={key for key,row in requests.items() if row['value']['request']['url'].startswith('data:')}
    require(len(internal)<=1 and set(requests)-({'100.12'} if b8 else set())==set(responses)==set(bodies) and set(requests)-internal==set(guards) and
        len(guards)==result['request_count']<=packet['maximum_request_count'],'Missing/extra browser network evidence')
    for key,row in requests.items():
        request=row['value']['request']
        if b8 and key=='100.12':
            require(request['method']=='GET' and request['url']==ORIGIN+'/api/v1/status' and
                all(guards[key]['value']['request'].get(k)==request.get(k) for k in ['method','url','postData']) and
                guards[key]['monotonic_ns']<next(r['monotonic_ns'] for r in rows if r['kind']=='failure'),
                'Only B8 final stopped GET lacks a response')
            continue
        response=responses[key]['value']['response'];body=bodies[key]['value']
        if key in internal:
            require(request['method']=='GET' and hashlib.sha256(request['url'].encode()).hexdigest()==
                '04e449d20d0365d881a54ed24af7ed00fe79dd9f9e601248f4fd7793003924f2' and
                body_bytes(body['body'])==base64.b64decode(request['url'].split(',',1)[1],validate=True),'Browser-local date icon')
            continue
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
        require(status==200 or (url.path=='/favicon.ico' and status==404) or
            (stopped_b4 and url.path=='/api/v1/jobs' and status==409),'Unexpected browser HTTP outcome')
        require(row['monotonic_ns']<=bodies[key]['monotonic_ns'] and
            0<=body['finished']['timestamp']-row['value']['timestamp']<=30,'Browser request deadline')
        if url.path=='/':
            require(hashlib.sha256(raw).hexdigest()=='c2e866fdc8e26efbafeb87a94452d20db8ba83d3cdef4bfe6a70db330771f9b9','Target document identity')
            for tag,path in [('style','/style.css'),('script','/app.js')]:
                parts=re.findall(b'<'+tag.encode()+b'>(.*?)</'+tag.encode()+b'>',raw,re.DOTALL)
                require(len(parts)==1 and hashlib.sha256(parts[0]).hexdigest()==ASSETS[path],'Inline asset identity');assets.add(path)
        if url.path in ASSETS:
            require(hashlib.sha256(raw).hexdigest()==ASSETS[url.path],'Served UI source differs from identified firmware');assets.add(url.path)
        if request['method']=='POST':
            require(url.path=='/api/v1/jobs','Unexpected mutation route')
            q=json.loads(request['postData']);r=json.loads(raw)
            rejected=stopped_b4 and q['operation']=='LOAD_MESSAGE' and q['body']['job_id']==binding['job_ids'][1]
            require(q['session_id']==session and r['ok'] is (not rejected) and r['request_id']==q['request_id'] and
                status==(409 if rejected else 200),
                'Browser operation response/session')
            if rejected:
                require(r['error']==dict(code='INTERNAL_ERROR',message='INTERNAL_ERROR',retryable=False), 'Exact rejected LOAD response')
            posts.append(dict(request=q,response=r['error'] if rejected else r['result'],started=row['monotonic_ns'],ended=bodies[key]['monotonic_ns']))
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
    index=0;cases=[];charges=[r for r in rows if r['kind']=='arm_charge'];require(len(charges)==case_count,'ARM charge count')
    for case_index,n in enumerate(indices):
        c=packet['cases'][n]
        expected=['HELLO','CLAIM','LOAD' if n==0 else 'LOAD_MESSAGE','ARM']
        group=posts[index:index+4];require([p['request']['operation'] for p in group]==expected,'Browser operation ordering')
        index+=4;hello,claim,load,arm=group
        require(hello['request']['body']==dict(versions=['WTP/1'],client_name='WsprryPico browser',client_version='1') and
            hello['response']['boot_id']==packet['boot_id'] and hello['response']['device_id']==packet['device_id'],'HELLO identity')
        require(claim['request']['body']==dict(owner_id=session,lease_ms=30000),'Owner claim')
        q=load['request']['body'];job_id=q['job_id'];require(binding['job_ids'][case_index]==job_id,'Actual loaded job binding')
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
        q=arm['request']['body'];charge=charges[case_index]
        require(q['job_id']==job_id and q['max_start_uncertainty_ns']=='500000000' and
            arm['response']['job_id']==job_id and arm['response']['state']=='armed' and
            arm['response']['start_utc_ns']==q['start_utc_ns'] and
            charge['value']==dict(job_id=job_id,duration_ns=c['duration_ns'],start_utc_ns=q['start_utc_ns']) and
            charge['monotonic_ns']<=arm['ended'],'ARM job/time/accounting')
        if b8:
            require(n==3 and len(posts)==4 and set(dom)=={'initial','file-30001-rejected','case-3-armed',
                *[m+'-'+k for m in ['qrss','fskcw','dfcw'] for k in ['31','32','33','spaces-32']]},
                'B8 stopped before Running UI and cancellation')
            final=observed['inventories']['final-a']['wtp']['STATUS']
            statuses=[r['value']['value'] for r in observed['samples']['status'] if r['value']['value']['job_id']==job_id]
            require({'armed','running','complete'}<={v['state'] for v in statuses} and
                all(v['boot_id']==packet['boot_id'] and v['owner_id'] in [None,session] and
                    v['output_active'] is (v['state']=='running') for v in statuses) and
                final['state']=='complete' and final['job_id']==job_id and final['owner_id'] is None and
                final['output_active'] is False and any(t['job_id']==job_id and t['state']=='complete'
                    for t in final['terminal_records']),'B8 independent finite completion')
            try:
                timing(packet,[dict(monotonic_ns=charge['monotonic_ns'],job=job,start_utc_ns=q['start_utc_ns'])],observed['rows'])
            except ValueError as error:
                require(str(error)=='ARM UTC mapping','Preserve exact B8 timing audit finding')
            else:raise ValueError('Original B8 timing finding disappeared')
            before_info=observed['inventories']['before-a']['info']
            final_info=observed['inventories']['final-a']['info']
            require(int(final_info['launch_epoch'])==int(before_info['launch_epoch'])+1,'B8 exact launch count')
            mapping=[dict(monotonic_now_ns=i['status']['monotonic_now_ns'],sync_age_ns=i['status']['sync_age_ns'],
                mapping_error_ns=int(i['launch_target_ns'])+int(i['status']['utc_now_ns'])-int(i['status']['monotonic_now_ns'])-int(q['start_utc_ns']),
                allowed_ns=int(i['status']['uncertainty_ns'])+1000000)
                for i in [r['value']['value'] for r in observed['samples']['info']]
                if i['status']['state']=='running' and int(i['launch_epoch'])==int(final_info['launch_epoch'])]
            cases.append(dict(kind=c['kind'],job_id=job_id,result='complete',planned_duration_ns=c['duration_ns'],timing=None,
                cancellation_verified=False,missing_final_get_response='100.12',failure_classification='CONFIRMED_HARNESS_DEFECT',
                timing_acceptance=False,timing_audit_failure='ARM UTC mapping',timing_cause='UNRESOLVED',clock_mapping=mapping))
            continue
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
    if stopped_b4:
        remaining=posts[index:]
        require([p['request']['operation'] for p in remaining]==['HELLO','CLAIM','LOAD_MESSAGE'], 'Exact unarmed rejected tail')
        hello,claim,load=remaining
        require(hello['request']['body']==dict(versions=['WTP/1'],client_name='WsprryPico browser',client_version='1') and
            hello['response']['boot_id']==packet['boot_id'] and hello['response']['device_id']==packet['device_id'] and
            claim['request']['body']==dict(owner_id=session,lease_ms=30000), 'Rejected tail handshake/owner')
        require(load['request']['body']==dict(packet['cases'][2]['message'],job_id=binding['job_ids'][1]) and
            load['response']==dict(code='INTERNAL_ERROR',message='INTERNAL_ERROR',retryable=False), 'Rejected QRSS identity')
        final=observed['inventories']['final-a']['wtp']['STATUS']
        require(final['job_id']==cases[0]['job_id'] and final['state']=='complete' and final['output_active'] is False and
            final['owner_id'] is None and all(r['job_id']!=binding['job_ids'][1] for r in final['terminal_records']),
            'Rejected QRSS did not replace completed state')
        index+=3
    require(index==len(posts),'Unexpected trailing mutation')
    require(result['cases']==([] if b8 else [dict(kind=c['kind'],job_id=c['job_id'],planned_duration_ns=c['planned_duration_ns'],result=c['result'],
        **({'observed_running_ns':result['cases'][n]['observed_running_ns']} if c['kind']=='running-abort' else {})) for n,c in enumerate(cases)]),
        'Browser summary differs from independently audited operations')
    if stopped_b5:
        before=observed['inventories']['before-a']['info'];final=observed['inventories']['final-a']
        require(final['wtp']['STATUS']['state']=='empty' and all(before[k]==final['info'][k] for k in
            ['dma_irqs','alarm_irqs','tail_irqs','launch_epoch']), 'Armed cancellation had no physical launch')
    return dict(status='B8_FINITE_COMPLETION_WITH_PUBLICATION_HARNESS_FAILURE_VERIFIED' if b8 else 'B4_COMPLETED_FSKCW_AND_REJECTED_QRSS_VERIFIED' if stopped_b4 else
        'B5_ARMED_CANCELLATION_WITH_HARNESS_FAILURE_VERIFIED' if stopped_b5 else ('B9' if b9 else 'B8' if b8 else 'B7' if b7 else 'B1' if packet_sha==PACKET else 'B2')+'_ACTUAL_CHROMIUM_FEATURES_VERIFIED',family_closed=False,packet_sha256=packet_sha,
        source_revision=packet['source_revision'],image_sha256=packet['image_sha256'],boot_id=packet['boot_id'],
        rf_jobs_charged=case_count,rf_duration_ns_charged=planned_ns,cases=cases,cadence=observed['cadence'],
        reused_browser_audit_sha256=packet.get('reused_browser_audit_sha256'),rendered_checkpoints=len(dom),rendered_visual_review='REQUIRED_SEPARATELY',network_requests=len(requests),
        maximum_allocator_peak_bytes=max(r['value']['value']['allocator_peak_bytes'] for r in observed['samples']['info']))
