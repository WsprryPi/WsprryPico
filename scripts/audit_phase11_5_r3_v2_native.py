"""Independent native production submission wire audit; no device access."""
import importlib.util
import json
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_r3_v2_native_plan import validate_template
from validate_wtp_contract import SchemaValidator
from audit_phase11_5_idle import frames


def native_wire(root,packet,binding,decoder):
    require(digest(decoder)==packet['stage_sha256']['pi/phase115_tls_observer_test.py'],'Native decoder identity')
    spec=importlib.util.spec_from_file_location('native_production_decoder',decoder)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rows=module.decode((root/'production-tls.bin').read_bytes())
    require(all(r['version']=='P115TLS2' for r in rows),'Native actual complete write evidence')
    loss=packet['native'].get('transport_loss',False)
    schema=json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text());validator=SchemaValidator(schema)
    buffers={};starts={};writes={};pending={};seen=set();exchanges=[];certificates=[];certificate_times=[];events=[];lost_pending=[]
    for row in rows:
        kind,cid,stamp=row['kind'],row['connection_id'],row['monotonic_ns']
        if kind==2:
            require(row['payload'].hex()==packet['peer_sha256'],'Native target certificate');certificates.append(cid);certificate_times.append(stamp)
        if kind==7:writes[cid]=stamp
        if kind==8:writes.pop(cid,None)
        if kind==5:
            outstanding=[k for k in pending if k[0]==cid]
            if loss and cid==1:
                require(all(pending[k][0]['op']=='STATUS' for k in outstanding) and len(outstanding)<=1 and
                    any(x['request']['op']=='ARM' for x in exchanges),'Native loss must follow acknowledged ARM')
                lost_pending.extend(pending.pop(k)[0] for k in outstanding)
                require(not buffers.get((cid,3),b''),'Native partial request write at loss')
                buffers[(cid,4)]=b''
            else:require(not outstanding,'Native connection lost before response')
        if kind not in [3,4]:continue
        key=(cid,kind)
        if kind==3:starts.setdefault(key,writes.pop(cid))
        messages,buffers[key]=frames(buffers.get(key,b'')+row['payload'])
        for message in messages:
            require(not validator.errors(message,schema) and message['session_id']==binding['session_id'],
                'Native frame schema/session')
            token=(cid,message.get('request_id'))
            if kind==3:
                require(message['type']=='request' and message['op'] in
                    ['HELLO','CAPS','STATUS','GET_CLOCK','PING','CLAIM','RENEW','LOAD','ARM','RELEASE'] and
                    message['request_id'] not in seen and not pending,'Native mutation/retry/pipeline scope')
                seen.add(message['request_id']);pending[token]=(message,starts[key])
            elif message['type']=='event':
                require(message['boot_id']==packet['boot_id'] and message['event'] in ['JOB_STATE','OWNER_RELEASED'],
                    'Native foreign/fault event');events.append(message)
            else:
                require(message['type']=='response' and message['ok'] is True and token in pending,'Native response failure')
                q,began=pending.pop(token)
                require(q['op']==message['op'] and 0<=stamp-began<=5_000_000_000,'Native operation deadline')
                if q['op'] in ['HELLO','STATUS']:require(message['body']['boot_id']==packet['boot_id'],'Native response boot')
                if q['op']=='HELLO':require(message['body']['device_id']==packet['device_id'],'Native response device')
                exchanges.append(dict(request=q,response=message,began_monotonic_ns=began,ended_monotonic_ns=stamp,connection_id=cid))
        if not buffers[key]:starts.pop(key,None)
    require(certificates==([1,2] if loss else [1]) and exchanges and not pending and not writes and not any(buffers.values()),'Native complete single connection')
    require([x['request']['op'] for x in exchanges[:3]]==['HELLO','STATUS','CAPS'] and
        sum(x['request']['op']=='HELLO' for x in exchanges)==sum(x['request']['op']=='CAPS' for x in exchanges)==(2 if loss else 1) and
        any(x['request']['op']=='GET_CLOCK' for x in exchanges),'Native negotiated capability and clock path')
    mutations=[x for x in exchanges if x['request']['op'] in ['CLAIM','LOAD','ARM','RELEASE']]
    require([x['request']['op'] for x in mutations]==(['CLAIM','LOAD','ARM'] if loss else ['CLAIM','LOAD','ARM','RELEASE']),'Exactly one native lifecycle')
    claim,load,arm=mutations[:3];release=None if loss else mutations[3]
    require(claim['request']['body']['owner_id']==claim['response']['body']['owner_id']==binding['owner_id'],
        'Native owner binding')
    expected=dict(validate_template(packet['native']['job_template'],packet['native']['mode'],
        packet['native'].get('template_policy','direct-compiler-v1')),job_id=binding['job_id'])
    require(load['request']['body']==expected and load['response']['body']['job_id']==binding['job_id'],
        'Actual native compiler LOAD differs')
    for x in exchanges:
        if x['request']['op']=='RENEW':
            require(x['request']['body']['owner_id']==x['response']['body']['owner_id']==binding['owner_id'],
                'Native renewal owner changed')
    adjustments=load['response']['body']['adjustments']
    require([v['event_index'] for v in adjustments]==[n for n,e in enumerate(expected['events']) if e['rf_on']] and
        all(v['requested_frequency_nhz']==expected['events'][v['event_index']]['frequency_nhz'] for v in adjustments),
        'Native target did not acknowledge expanded frequencies')
    require(arm['request']['body']['job_id']==arm['response']['body']['job_id']==binding['job_id'] and
        arm['request']['body']['start_utc_ns']==arm['response']['body']['start_utc_ns']==binding['start_utc_ns'],
        'Native exact ARM identity/time')
    statuses=[x for x in exchanges if x['request']['op']=='STATUS']
    require(any(x['response']['body']['state']=='complete' and any(t['job_id']==binding['job_id'] and
        t['state']=='complete' and t['output_active'] is False for t in x['response']['body']['terminal_records'])
        and (loss or x['ended_monotonic_ns']<release['began_monotonic_ns']) for x in statuses),
        'Native release preceded authoritative completion')
    require(statuses[-1]['response']['body']['state']==('complete' if loss else 'empty') and
        statuses[-1]['response']['body']['owner_id'] is None and statuses[-1]['response']['body']['output_active'] is False,
        'Native final authority')
    return dict(exchanges=exchanges,arm=arm,job=expected,pid=rows[0]['pid'],events=events,certificate_times=certificate_times,lost_pending=lost_pending,
        started_monotonic_ns=rows[0]['monotonic_ns'],finished_monotonic_ns=rows[-1]['monotonic_ns'])


def audit(root,packet_sha):
    from phase11_5_r3_v2_native_observer import validate
    from phase11_5_r3_v2_native_plan import validate_initial,validate_binding,validate_ini,PI_BINARY
    from audit_phase11_5_r3_v2_browser_observer import audit as observer
    from audit_phase11_5_r3_v2_hour import journal
    from audit_phase11_5_r3_v2_rf import timing
    require(digest(root/'packet.json')==packet_sha,'Frozen native packet')
    stopped_n1=packet_sha=='a0260a2b0da99c33a9091e77e359a81f22d4b9e855a13f8f5f0461d51638a2b6'
    stopped_n0=stopped_n1 or packet_sha=='2a3d8c11635c48dda176c006b668bc1286114bdb7398791c12be96cbc83ab029'
    stopped_n2=packet_sha=='5e18bbe50867720be83a42ee3a0b431640f2d3520da16f4dd98612e75bb06be4'
    stopped_n4=packet_sha=='6b332a2f69a8f9b53dee5d8eeb83ac171beea475ee580df317b2f8deb7ce2894'
    stopped=stopped_n0 or stopped_n2 or stopped_n4
    original_failure='Native unexpected subsequent dispatch' if stopped_n1 else 'Native application identity/job drift'
    if stopped_n2:original_failure='Original native session must remain blocked before explicit reconciliation'
    if stopped_n4:original_failure='Native orderly exit failed'
    packet=validate(json.loads((root/'packet.json').read_text()))
    observed=observer(root,packet,prefix='native')
    validate_initial(observed['inventories']['before-a']['wtp']['STATUS'],packet)
    rows=journal(root/'native.jsonl');require(rows[0]['value']==dict(packet_sha256=packet_sha,
        mode=packet['native']['mode'],binary_sha256=PI_BINARY),'Native producer provenance')
    require(all(r['kind'] in ['start','finish','job_charge','process_starting','process_started','native_status',
        'binding','independent_terminal','process_exit',
        *(['failure','failed_process_cleanup'] if stopped else []),
        *(['arm_ack_before_loss','transport_loss_pending','transport_loss_result','reconciliation_pending','reconciliation_response']
            if packet['native'].get('transport_loss',False) else [])] for r in rows),'Native failure/undeclared action')
    def one(kind):
        selected=[r for r in rows if r['kind']==kind];require(len(selected)==1,'Native unique '+kind);return selected[0]
    charge=one('job_charge');execution=json.loads((root/'native-execution.json').read_text())
    require(charge['value']==dict(execution,rf_jobs=1) and execution['job_template']==packet['native']['job_template'] and
        digest(root/'production-job.ini')==execution['ini_sha256'],'Native charge/input binding')
    binding=one('binding');b=binding['value']
    require(json.loads((root/'native-binding.json').read_text())==dict(packet_sha256=packet_sha,**b),'Native binding file')
    validate_binding(b,packet,execution['start_utc_ns'],binding['utc_ns'])
    require(digest(root/'production-base.ini')==packet['native']['base_ini_sha256'],'Native base INI identity')
    validate_ini((root/'production-job.ini').read_text(),(root/'production-base.ini').read_text(),
        packet['native']['mode'],execution['start_utc_ns'],Path(packet['root']))
    started=one('process_started');exit=one('failed_process_cleanup' if stopped and not stopped_n4 else 'process_exit')
    if stopped:require(one('failure')['value']==dict(type='ValueError',error=original_failure),'Original native failure')
    if stopped_n0:
        require(one('failure')['value']==dict(type='ValueError',error=original_failure),
            'Original N0 producer failure')
        candidates=[r for r in observed['samples']['status'] if any(t['job_id']==b['job_id'] and t['state']=='complete'
            for t in r['value']['value']['terminal_records'])]
        require(candidates,'N0 missing independent completion')
        row=candidates[0];status=row['value']['value']
        terminal=dict(monotonic_ns=row['monotonic_ns'],value=dict(status=status,
            record=next(t for t in status['terminal_records'] if t['job_id']==b['job_id'])))
    else:terminal=one('independent_terminal')
    require(one('process_starting')['value']['argv']==[packet['native']['binary'],'--backend','wtp','-i',
        str(Path(packet['root'])/'production-job.ini'),'--socket-loopback-only','--socket-loopback-family','ipv4',
        '--allow-unqualified-frequency','--allow-non-amateur-frequency'],'Native exact production invocation')
    require(started['value']['binary_sha256']==PI_BINARY and exit['value']==dict(returncode=1
        if packet['native'].get('transport_loss',False) and not stopped_n2 else 0) and
        charge['monotonic_ns']<one('process_starting')['monotonic_ns']<started['monotonic_ns']<binding['monotonic_ns']<
        terminal['monotonic_ns'] and (abs(terminal['monotonic_ns']-exit['monotonic_ns'])<=6_000_000_000
            if stopped_n0 else terminal['monotonic_ns']<exit['monotonic_ns']),'Native charge/binding/terminal/exit order')
    # N2's exact failed host loss command left the original TLS connection alive.
    # Preserve positive submission only; the requested loss assertion stays FAILED.
    if stopped_n2:
        from phase11_5_r3_v2_native_plan import configuration_template
        wire_packet=dict(packet,native=dict(packet['native'],transport_loss=False,
            template_policy='production-config-builder-v1',job_template=configuration_template(packet['native']['job_template'])))
    else:wire_packet=packet
    wire=native_wire(root,wire_packet,b,root/'pi/phase115_tls_observer_test.py')
    require(wire['pid']==started['value']['pid'] and binding['monotonic_ns']<wire['arm']['began_monotonic_ns'] and
        one('process_starting')['monotonic_ns']<=wire['started_monotonic_ns']<=wire['finished_monotonic_ns']<=exit['monotonic_ns'] and
        rows[-1]['monotonic_ns']-rows[0]['monotonic_ns']<=packet['runtime_seconds']*10**9,
        'Actual native PID and pre-ARM binding')
    hosts=[];host_completed=False
    from phase11_5_r3_v2_native_plan import validate_host_scope
    for row in rows:
        if row['kind']!='native_status':continue
        v=row['value'];body=json.loads(bytes.fromhex(v['body_hex']))
        require(body==v['value'] and 0<=row['monotonic_ns']-v['began_monotonic_ns']<=3_000_000_000,
            'Native raw host status/deadline')
        if row['monotonic_ns']>=binding['monotonic_ns']:
            require(body['host']['identity']['device_id']==packet['device_id'] and
                body['host']['identity']['boot_id']==packet['boot_id'],'Native host identity')
            host_completed=validate_host_scope(body['host'],b,packet,host_completed)
            hosts.append(row)
    require(hosts and max((y['monotonic_ns']-x['monotonic_ns'] for x,y in zip(hosts,hosts[1:])),default=0)<=2_000_000_000 and
        terminal['monotonic_ns']-hosts[-1]['monotonic_ns']<=(6 if stopped_n0 else 2)*1_000_000_000,'Native host observation coverage')
    if stopped_n0:
        require(host_completed and hosts[-1]['value']['value']['host']['job_id']==b['job_id'][:-16]+'0000000000000002' and
            hosts[-1]['monotonic_ns']<one('failure')['monotonic_ns']<exit['monotonic_ns'],'N0 exact queued-successor finding')
    independent=[r['value']['value'] for r in observed['samples']['status']]
    s=terminal['value']['status'];t=terminal['value']['record']
    require(s in independent and t in s['terminal_records'] and t['job_id']==b['job_id'] and t['state']=='complete' and
        t['output_active'] is False and s['output_active'] is False and 'error' not in t,'Native independent terminal raw binding')
    require(any(s['job_id']==b['job_id'] and s['state']=='running' and s['output_active'] is True for s in independent),
        'Native independent Running evidence')
    timing_packet=dict(wire_packet,sample_mapping_policy='waveform-absolute-nearest-v1') if stopped_n2 else packet
    arm=wire['arm'];metrics=timing(timing_packet,[dict(monotonic_ns=arm['began_monotonic_ns'],job=wire['job'],
        start_utc_ns=arm['request']['body']['start_utc_ns'],request=arm['request']['body'],
        acknowledgment=arm['response']['body'])],observed['rows'])[0]
    result=json.loads((root/'native-result.json').read_text())
    expected_result=dict(status='FAILED' if stopped else 'CAPTURED_REQUIRES_AUDIT',rf_jobs_charged=1,
        rf_duration_ns_charged=int(packet['native'].get('duration_charge_ns',packet['native']['job_template']['total_duration_ns'])))
    if stopped:expected_result['error']=original_failure
    else:expected_result.update(job_id=b['job_id'],terminal=t,**(dict(transport_loss_attempts=1,same_session_reconciled=True)
        if packet['native'].get('transport_loss',False) else {}))
    if stopped_n4:
        require(packet['native'].get('transport_loss') is True and
            exit['monotonic_ns']<one('failure')['monotonic_ns'],'N4 preserved exit expectation failure')
        expected_result.update(transport_loss_attempts=1,same_session_reconciled=True)
    if stopped_n2:
        expected_result['transport_loss_attempts']=1
        failed_loss=one('transport_loss_result')['value']
        require(failed_loss['returncode']==0 and failed_loss['stderr']=='RTNETLINK answers: Invalid argument\n' and
            all(r['kind'] not in ['reconciliation_pending','reconciliation_response'] for r in rows),
            'N2 original failed loss and no reconciliation')
    require(result==rows[-1]['value']==expected_result,'Native result accounting')
    if packet['native'].get('transport_loss',False) and not stopped_n2:
        from phase11_5_r3_v2_native_loss import socket_identity
        ack=one('arm_ack_before_loss');pending_loss=one('transport_loss_pending');lost=one('transport_loss_result')
        reconcile=one('reconciliation_pending');recovered=one('reconciliation_response')
        require(ack['value']['request']==arm['request'] and ack['value']['response']==arm['response'] and
            ack['value']['ack_monotonic_ns']==arm['ended_monotonic_ns'] and ack['value']['connection_id']==1 and
            arm['ended_monotonic_ns']<=ack['monotonic_ns']<=pending_loss['monotonic_ns']<=lost['monotonic_ns']<
            terminal['monotonic_ns']<reconcile['monotonic_ns']<recovered['monotonic_ns']<exit['monotonic_ns'],
            'Native acknowledged loss/local completion/reconciliation order')
        identity=socket_identity(pending_loss['value']['ss_before'],wire['pid'])
        require(identity==pending_loss['value']['identity']==lost['value']['identity'] and
            lost['value']['returncode']==0,'Native exact task-owned socket loss')
        if packet['native'].get('loss_mechanism')=='pidfd-duplicate-shutdown-v1':
            import re
            require(lost['value']==dict(identity=identity,mechanism='pidfd-duplicate-shutdown-v1',
                local=[identity['local_address'],identity['local_port']],
                peer=[identity['peer_address'],identity['peer_port']],
                socket_inode=lost['value']['socket_inode'],shutdown='SHUT_RDWR',returncode=0) and
                re.fullmatch(r'socket:\[[0-9]+\]',lost['value']['socket_inode']) is not None,
                'Native pidfd shutdown scope')
        else:
            require(not lost['value']['stderr'].strip() and lost['value']['argv']==
                ['ss','-K','dst','10.77.15.10','dport','=','18443','src','10.77.15.2','sport','=',str(identity['local_port'])],
                'Native socket destroy reported an error')
        require(reconcile['value']==dict(url='http://127.0.0.1:31425/api/wtp/recover',
            body_hex=b'{"operation":"reconcile"}'.hex(),session_id=b['session_id']) and
            wire['certificate_times'][1]>reconcile['monotonic_ns'],'No early reconnect or new-session substitution')
        reply=json.loads(bytes.fromhex(recovered['value']['body_hex']))
        require(reply==recovered['value']['value'] and reply['ok'] is True and reply['status']['phase']=='idle' and
            reply['status']['session_id']==b['session_id'] and reply['status']['identity']['boot_id']==packet['boot_id'],
            'Native raw same-session reconciliation')
        prior=hosts[-1]['value']['value']['host'];status=reply['status']
        require(terminal['monotonic_ns']<hosts[-1]['monotonic_ns']<reconcile['monotonic_ns'] and
            prior['phase']=='blocked' and prior['recovery_required'] is True and
            prior['session_id']==b['session_id'] and prior['job_id']==b['job_id'],
            'Native remains blocked until explicit recovery')
        require(status['identity']['device_id']==packet['device_id'] and status['job_id']==b['job_id'] and
            status['ready'] is True and status['recovery_required'] is False and status['worker_active'] is False and
            status['remote']==dict(boot_id=packet['boot_id'],job_id=b['job_id'],state='complete',
                output_active=False,owner_id=None) and status['job']['authoritative'] is True and
            status['job']['state']=='complete' and status['job']['job_id']==b['job_id'] and
            status['job']['output_active'] is False,'Native reconciled completion authority')
    return dict(status='N4_NATIVE_LOSS_RECONCILIATION_WITH_EXIT_EXPECTATION_FAILURE_VERIFIED' if stopped_n4 else 'N2_NATIVE_DFCW_COMPLETION_WITH_FAILED_LOSS_VERIFIED' if stopped_n2 else 'N1_NATIVE_FSKCW_COMPLETION_WITH_HARNESS_FAILURE_VERIFIED' if stopped_n1 else 'N0_NATIVE_QRSS_COMPLETION_WITH_HARNESS_FAILURE_VERIFIED' if stopped_n0 else 'ACTUAL_NATIVE_SUBMISSION_VERIFIED',family_closed=False,packet_sha256=packet_sha,
        source_revision=packet['source_revision'],image_sha256=packet['image_sha256'],boot_id=packet['boot_id'],
        native_source_revision=packet['native']['source_revision'],native_binary_sha256=PI_BINARY,
        mode=packet['native']['mode'],job_id=b['job_id'],session_id=b['session_id'],rf_jobs_charged=1,
        rf_duration_ns_charged=int(packet['native'].get('duration_charge_ns',packet['native']['job_template']['total_duration_ns'])),timing=metrics,cadence=observed['cadence'],
        wire_operations={op:sum(x['request']['op']==op for x in wire['exchanges']) for op in sorted({x['request']['op'] for x in wire['exchanges']})},
        final_authority=observed['inventories']['final-a']['wtp']['STATUS'])
