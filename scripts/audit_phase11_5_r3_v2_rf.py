"""Independent raw S0 wire, cadence, finite lifecycle and target timing audit."""
import json
from pathlib import Path
from phase11_5_inventory import require,loads_console
from phase11_5_device_management import digest
from phase11_5_pilot_supervisor import configuration,B_SERIAL,B_DEVICE
from phase11_5_pilot import SERIAL,DEVICE
from phase11_5_r3_preflight import audit_inventory
from validate_wtp_contract import SchemaValidator
from audit_phase11_5_idle import frames
from audit_phase11_5_r2_modes import transactions
from phase11_5_r3_v2_rf import validate,validate_info,comparator_required,DIAGNOSTIC_POLICY,CLOSURE_POLICY,REPAIR_POLICY,COMPLETION_POLICY,SERIAL_CAPACITY,TERMINAL_POLICY,completion_policy,initial_terminal,recent_clock

PACKET='966cd695df2b2eab36f6999c2afae678ad6eecdb8a3c5ea0871fb5afb2c61fef'


def capacity_request(packet, value, index):
    from audit_phase11_5_r3_v2_admission import decode_requests
    from phase11_5_r3_capacity_plan import wtp_capacity_frame
    from validate_wtp_contract import frame
    diagnostic=packet.get('diagnostic_policy')==DIAGNOSTIC_POLICY
    require('wtp_capacity' in packet and index in ((0,) if diagnostic else (0,1)),
            'Declared WTP capacity exchanges only')
    cap=packet['wtp_capacity'];session=packet['peer_session']
    if index==0:
        expected=wtp_capacity_frame(session,cap['maximum_request_id'])
    else:
        recovery=dict(type='request',protocol='WTP/1',session_id=session,
            request_id=cap['recovery_request_id'],op='PING',body={'token':'after-capacity'})
        expected=wtp_capacity_frame(session,cap['oversized_request_id'],True)+frame(json.dumps(recovery,separators=(',',':')).encode())
    raw=bytes.fromhex(value['hex']);requests=decode_requests(raw)
    require(raw==expected and requests[-1][1]==value['request'] and value['expected_invalid_frames']==index,
        'Exact capacity CRC, length, operation, identity and recovery bytes')
    return len(raw)


def audit(root, *, packet_digest=PACKET):
    require(packet_digest in [PACKET, 'acde3e3f2f77c89eef5f4d64ced6e0f391fe11991b33e830e9207cf0836be1f7', '6128dbd48ab024057e60691f44c6b2a551ee08d0fd032e542fe535356643b8a5', '6754555f69ac57fc5dae670cb37f3db1ea4fca5f3ce0590f8749c8c47cd92fdf', '4bc1919c3be6acba32a5c952a2fa00ffae65ce12a1cd8164e1dfa86d84558c57', '26e58c73da189aa1d9aecae6b410e392ca2957499632e38caa3b05f14c3d8104', 'aa603d6510059bbc34a6f79627402e477615ef04ff789a8d66992352db619662', '69c5b306bdde2231764b078e47da05cd47e661eef35b0bb294eb83ae1734de18', 'cbc6f4b871841c0cf4f6976e5cde73976699798aa0ccdc3ff65b72dc50c73e8d', '8cfcdfeef0c4513f24fe4dff64eaef1f62bbeaa4054c33d2d6720a3481e4b908', 'd46edf56bd1eaaaae095139ec6cfb39edb627470c769f4d758bed8d7a3d2da83', '3265c16e1a970c79c1beee2bd6a9cf4b9198381ee051a08f5f0dd40d7ed95277', 'a96a14455d08caa37fab21e7ef96be5bd5249afdf6471e8450c64a2e5d73f5a4', '9215a8049c83c2319506ef0c76100213a6bf5bb479a06cd283835c684719f095', '065cb07e6ace4261caf4ba24cb7d6e1417186d1d7c1445bae25d102b256df3b5',
            'da89cf9f703f126ef71e463336674000373749df3c70f98ec7a2bff9fc7a7373',
            'c408f5db396a50a6413334f05b7cc1eda22dab0040023454f28c435241931d41',
            '4eeb2113a40dc386f7839ae40a2e1f1d13b2da23dc86d04eb7ae0131dcfe2304',
            'c5ecb3dcf84eb61b788ede7c2481d10054831cee6c630c5ca4d9c715bc8a8c8c',
            'dd834b829b6745d64385a4b831e96018be51edcf09dcfbc544cc6dc4d4eb82ed',
            'addf150f2832d418c7f198e25edbf29bebaf21a62202fd1a9f072447c0db0da1',
            'eef06c2fefab51ffb7954d1d563c956acb0cbfddf386597163bf91fd927ddce7',
            '6e866906cd3eaffab9d63e52fd64a54b8b6b44300179d7aacc22a6671e50c3df',
            '3c8cea4f50a1e78b62cbb300846f05555360e8e0c91b467c694505b66fc8e3cf',
            'ef709e0ee4f2de33537fa887921815b4c36534ebd7afbb0259c7f8ec9b962d57',
            '1fc1577212f2bcd0c5ea308a9da923b9386863a3dd567d28fd700e4787980cb7'],
            'Unreviewed RF audit packet')
    require(digest(root/'packet.json')==packet_digest,'Frozen RF packet')
    packet=json.loads((root/'packet.json').read_text());validate(packet);inventories={}
    diagnostic=packet.get('diagnostic_policy')==DIAGNOSTIC_POLICY
    recent_admission=diagnostic or completion_policy(packet) or packet.get('closure_policy') in (CLOSURE_POLICY,REPAIR_POLICY,COMPLETION_POLICY,TERMINAL_POLICY)
    labels=['before-a','before-b','final-a','final-b'] if comparator_required(packet) else ['before-a','final-a']
    for label in labels:
        b=label.endswith('-b')
        v=audit_inventory(root/(label+'.stdout'),dict(serial=B_SERIAL if b else SERIAL,device_id=B_DEVICE if b else DEVICE),
            packet['b_session'] if b else packet['inventory_session'],packet['stage_sha256']['scripts/phase11_5_inventory.py'])
        require(not (root/(label+'.stderr')).read_bytes(),'Inventory stderr')
        terminal=label=='before-a' and initial_terminal(packet)
        s=v['wtp']['STATUS'];require(s['boot_id']==(packet['b_boot_id'] if b else packet['boot_id']) and
            s['state']==('complete' if terminal else 'empty') and s['owner_id'] is None and
            s['job_id']==(packet['initial_a_job_id'] if terminal else None) and s['output_active'] is False,
            'Final/initial authority')
        inventories[label]=v
    before=inventories['before-a'];final=inventories['final-a']
    require(configuration(before)==configuration(final),'Preserved A')
    if comparator_required(packet):
        require(configuration(inventories['before-b'])==configuration(inventories['final-b']) and
            inventories['before-b']['info']['revision']==inventories['final-b']['info']['revision'] and
            inventories['before-b']['wtp']['STATUS']==inventories['final-b']['wtp']['STATUS'],'Preserved A/B')
    if completion_policy(packet):
        require(len(before['wtp']['STATUS']['terminal_records'])<=packet['maximum_initial_terminal_records'],
                'Frozen individual-capacity initial retention')
        if 'initial_terminal_jobs' in packet:
            retained=before['wtp']['STATUS']['terminal_records']
            require([r['job_id'] for r in retained]==packet['initial_terminal_jobs'] and
                    all(r['state']=='aborted' and r['output_active'] is False for r in retained),
                    'Exact independently observed retained seed')
    validate_info(before['info'],before,packet);validate_info(final['info'],before,packet)
    raw=(root/'rf.jsonl').read_text();require(raw.endswith('\n'),'Truncated trace')
    rows=[json.loads(s) for s in raw.splitlines()]
    require(rows[0]['kind']=='start' and rows[-1]['kind']=='finish' and
            rows[0]['value']['packet_sha256']==packet_digest and rows[0]['value']['baseline_sha256']==digest(root/'before-a.stdout') and
            rows[0]['value']['boot_id']==packet['boot_id'] and
            [r['sequence'] for r in rows]==list(range(len(rows))) and
            all(a['monotonic_ns']<=b['monotonic_ns'] for a,b in zip(rows,rows[1:])), 'Trace identity/sequence')
    if completion_policy(packet):
        from phase11_5_rf_reservation import inactive
        acquired=json.loads((root/'rf-reservation-acquired.json').read_text())
        released=json.loads((root/'rf-reservation-released.json').read_text())
        for value,state,phase in [(acquired,'HELD','before'),(released,'RELEASED','final')]:
            require(value['state']==state and value['packet_sha256']==packet_digest and
                    value['host_boot']==packet['host_boot_id'] and
                    value['boards']==inactive({name:inventories[phase+'-'+name] for name in ('a','b')}),
                    'Shared reservation state, packet and both-board authority')
        require(acquired['monotonic_ns']<=rows[0]['monotonic_ns'] and
                rows[-1]['monotonic_ns']>=released['monotonic_ns']>=max(
                    r['monotonic_ns'] for r in rows if r['kind']=='job_complete'),
                'Shared RF reservation lifetime')
    allowed=['start','finish','console_tx','console_rx','wtp_tx','wtp_rx','wtp_message','info','status','health',
             'info_finish','status_finish','health_finish','arm_pending','arm_acknowledged','job_complete']
    if 'contention' in packet:
        allowed.append('contention_starting')
        require(len([r for r in rows if r['kind']=='contention_starting'])==1,
                'Missing/extra contention process')
    if 'wtp_capacity' in packet:allowed+=['capacity_tx','capacity_write','capacity_rx','capacity_message']
    if packet.get('capacity_schedule_policy')==SERIAL_CAPACITY:allowed.append('wtp_capacity_complete')
    require(all(r['kind'] in allowed for r in rows),'Unexpected failure/operation')
    schema=json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text());validator=SchemaValidator(schema)
    pending={};seen=set();wire=b'';messages=[];console=b'';console_pending=None;console_value=None
    latest_status=None;exchanges=[];events=[];event_id=None;samples={}
    capacity=None;capacity_count=0;capacity_results=[]
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
        elif kind in ['wtp_tx','capacity_tx']:
            if kind=='capacity_tx':
                require(capacity is None,'Capacity exchange overlapped')
                if recent_admission:
                    info=samples['info'][-1]
                    require(0<=stamp-info['monotonic_ns']<=2_000_000_000 and
                        info['value']['value']['status']['state']=='running' and
                        info['value']['value']['status']['output_active'] is True,
                        'Independent current Running INFO before single capacity stimulus')
                capacity=dict(size=capacity_request(packet,v,capacity_count),written=0,invalid=0,index=capacity_count)
                request=v['request'];capacity_count+=1
            else:
                require(capacity is None,'Ordinary request during capacity exchange')
                values,left=frames(bytes.fromhex(v['hex']));require(not left and values==[v['request']],'Request raw/summary')
                request=values[0]
            require(not validator.errors(request,schema) and request['session_id']==packet['peer_session'] and
                    request['request_id'] not in seen and not pending,'Request schema/session/no retry')
            seen.add(request['request_id']);pending[request['request_id']]=(stamp,request)
        elif kind=='capacity_write':
            require(capacity is not None and type(v['bytes']) is int and 0<v['bytes']<=4096 and
                v['total_written']==capacity['written']+v['bytes']<=capacity['size'],'Capacity complete write accounting')
            capacity['written']=v['total_written']
        elif kind in ['wtp_rx','capacity_rx']:
            values,wire=frames(wire+bytes.fromhex(v['hex']));messages.extend(values)
        elif kind in ['wtp_message','capacity_message']:
            require(messages and messages.pop(0)==v and not validator.errors(v,schema) and
                    v['session_id']==packet['peer_session'],'Response raw/summary/schema')
            if v['type']=='event':
                require(v['boot_id']==packet['boot_id'] and v['event'] in (['INVALID_FRAME'] if kind=='capacity_message' else ['JOB_STATE','OWNER_RELEASED']) and
                        (event_id is None or int(v['event_id'])==event_id+1),'Event gap/fault/boot')
                event_id=int(v['event_id']);events.append(v)
                if kind=='capacity_message':
                    require(capacity is not None and capacity['index']==1 and capacity['invalid']==0,'One expected framing refusal')
                    capacity['invalid']+=1
                continue
            require(v['ok'] is True and v['request_id'] in pending,'Unmatched/rejected response')
            began,q=pending.pop(v['request_id']);require(q['op']==v['op'] and stamp-began<=5_000_000_000,'Operation/deadline')
            exchanges.append(dict(request=q,response=v,started_ns=began,finished_ns=stamp))
            if kind=='capacity_message':
                require(capacity is not None and capacity['written']==capacity['size'] and
                    capacity['invalid']==capacity['index'],'Capacity full write and intended rejection')
                if capacity['index']==0:
                    value=v['body'];require(value['boot_id']==packet['boot_id'] and value['state']=='running' and
                        value['owner_id']==packet['owner_id'] and value['job_id']==packet['jobs'][0]['job_id'] and
                        value['output_active'] is True,'Maximum WTP actual owned Running authority')
                else:require(v['body']=={'token':'after-capacity'},'Same-connection PING recovery')
                capacity_results.append(dict(bytes_written=capacity['written'],invalid_frames=capacity['invalid'],
                    began_ns=began,ended_ns=stamp));capacity=None
            elif q['op']=='STATUS':latest_status=v['body']
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
    require(capacity is None and capacity_count==((1 if diagnostic else 2) if 'wtp_capacity' in packet else 0),
            'Complete declared capacity exchanges')
    if recent_admission:
        for exchange in exchanges:
            if exchange['request']['op'] not in ('CLAIM','ARM'):continue
            info=next(r for r in reversed(samples['info']) if r['monotonic_ns']<=exchange['started_ns'])
            clock=None
            if exchange['request']['op']=='ARM':
                clock=next(e['response']['body'] for e in reversed(exchanges) if
                    e['request']['op']=='GET_CLOCK' and e['finished_ns']<=exchange['started_ns'])
            require(recent_clock(info['value']['value'],clock),'Recent unchanged accepted clock at admission')
    cadence={}
    for kind,period in [('info',1),('status',5),('health',5)]:
        values=samples.get(kind,[]);require(values,'Missing observation family')
        starts=[r['value']['began_monotonic_ns'] for r in values];gaps=[b-a for a,b in zip(starts,starts[1:])]
        endings=[r for r in rows if r['kind']==kind+'_finish']
        if kind=='info' and packet.get('observer_policy')=='single-flight-info-v1':
            from phase11_5_r3_v2_observer_policy import validate_intervals
            require(len(endings)==1 and endings[0]['value']==dict(samples=len(values)),'INFO count/end')
            cadence[kind]=validate_intervals(starts,[r['monotonic_ns'] for r in values],rows[0]['monotonic_ns'],endings[0]['monotonic_ns'])
            continue
        require(len(endings)==1 and endings[0]['value']==dict(samples=len(values)) and
                starts[0]-rows[0]['monotonic_ns']<=(period+1)*10**9 and
                endings[0]['monotonic_ns']-starts[-1]<=(period+1)*10**9 and
                max(gaps,default=0)<=(period+1)*10**9,'Cadence count/start/end/gap')
        cadence[kind]=dict(samples=len(values),max_start_gap_ns=max(gaps,default=0))
    arm_exchanges=[e for e in exchanges if e['request']['op']=='ARM']
    arm_pending=[r for r in rows if r['kind']=='arm_pending']
    arm_acknowledged=[r for r in rows if r['kind']=='arm_acknowledged']
    completed_summaries=[r for r in rows if r['kind']=='job_complete']
    require(len(arm_exchanges)==len(arm_pending)==len(arm_acknowledged)==len(completed_summaries)==len(packet['jobs']),
            'Exact lifecycle summary count')
    for job,exchange,pending_row,ack,complete in zip(packet['jobs'],arm_exchanges,arm_pending,arm_acknowledged,completed_summaries):
        require(pending_row['value']==dict(job=job,start_utc_ns=exchange['request']['body']['start_utc_ns']) and
                ack['value']==exchange['response']['body'] and
                pending_row['monotonic_ns']<=exchange['started_ns']<=exchange['finished_ns']<=ack['monotonic_ns']<complete['monotonic_ns'],
                'ARM summaries must match raw request and response')
        prior_status=next(r for r in reversed(samples['status']) if r['monotonic_ns']<=complete['monotonic_ns'])
        prior_info=next(r for r in reversed(samples['info']) if r['monotonic_ns']<=complete['monotonic_ns'])
        require(complete['value']==dict(job_id=job['job_id'],status=prior_status['value']['value'],info=prior_info['value']['value']) and
                prior_status['value']['value']['state']=='complete','Completion summary must match raw observations')
    arms=transactions(dict(packet,submission_path='usb'),exchanges,events,packet_validator=validate)
    for arm,exchange in zip(arms,arm_exchanges):
        arm.update(request=exchange['request']['body'],acknowledgment=exchange['response']['body'])
    metrics=timing(packet,arms,rows)
    for job in packet['jobs']:
        statuses=[r for r in samples['status'] if r['value']['value']['job_id']==job['job_id']]
        states={r['value']['value']['state'] for r in statuses}
        require({'loaded','armed','running','complete'}<=states,'Observed lifecycle gap')
        running=[r for r in statuses if r['value']['value']['state']=='running']
        require(running and all(r['value']['value']['output_active'] is True for r in running),'Running authority')
        completed=next(r for r in statuses if r['value']['value']['state']=='complete')
        require(completed['monotonic_ns']-running[0]['monotonic_ns']>=int(job['total_duration_ns'])-6_000_000_000,
                'Truncated physical duration')
    prior=before['wtp']['STATUS']['terminal_records'];new=final['wtp']['STATUS']['terminal_records']
    final_infos=[r['value']['value'] for r in samples['info'][-2:]]
    lower=int(final_infos[0]['status']['monotonic_now_ns']);upper=int(final['info']['status']['monotonic_now_ns'])
    kept=[]
    for record in prior:
        expires=int(record['ended_monotonic_ns'])+3600_000_000_000
        require(not lower<expires<=upper,'Ambiguous terminal expiry bracket')
        if expires>upper:kept.append(record)
    expected=[j['job_id'] for j in reversed(packet['jobs'])]+[j['job_id'] for j in kept]
    require([t['job_id'] for t in new]==expected[:8],'Retained terminal order/capacity/expiry')
    for record in new:
        if record['job_id'] in [j['job_id'] for j in packet['jobs']]:
            require(record['state']=='complete' and record['output_active'] is False and 'error' not in record,'Terminal completion')
        else:require(record in kept,'Prior retained record changed')
    result=json.loads((root/'rf-result.json').read_text())
    require(result==rows[-1]['value'] and result['status']=='CAPTURED_REQUIRES_AUDIT' and result['faults']==[] and
            result['armed_jobs']==result['completed_jobs']==[j['job_id'] for j in packet['jobs']] and
            result['rf_duration_ns_charged']==sum(int(j['total_duration_ns']) for j in packet['jobs']) and
            result['renewals']==sum(e['request']['op']=='RENEW' for e in exchanges),'Result accounting')
    return dict(status='S0_STAGED_RF_ADMISSION_VERIFIED' if packet_digest==PACKET else 'FINITE_RF_WIRE_VERIFIED',
        family_closed=False,packet_sha256=packet_digest,
        source_revision=packet['source_revision'],image_sha256=packet['image_sha256'],boot_id=packet['boot_id'],
        cadence=cadence,wtp_capacity=capacity_results,jobs=metrics,rf_jobs=len(packet['jobs']),rf_duration_ns_charged=result['rf_duration_ns_charged'],
        maximum_allocator_peak_bytes=max(r['value']['value']['allocator_peak_bytes'] for r in samples['info']),
        terminal_records=new,physical_hour_or_saturation_verified=False)


def timing(packet, arms, rows):
    infos=[r for r in rows if r['kind']=='info']
    require(infos and max(r['value']['value']['allocator_largest_successful_request_bytes'] for r in infos)<=65552,
            'Allocation exceeds same-boot E0a demonstrated request')
    result=[];epochs=set()
    for n,arm in enumerate(arms):
        start=arm['monotonic_ns'];end=arms[n+1]['monotonic_ns'] if n+1<len(arms) else 2**64
        before=[r['value']['value'] for r in infos if r['monotonic_ns']<start]
        selected=[r['value']['value'] for r in infos if start<=r['monotonic_ns']<end]
        require(before and selected,'Missing per-job INFO window')
        base,last=before[-1],selected[-1]
        job=arm['job'];samples=138000000*int(job['total_duration_ns'])//10**9
        if packet.get('sample_mapping_policy')=='waveform-absolute-nearest-v1':
            from phase11_5_r3_v2_arm_mapping import waveform_samples
            from phase11_5_r3_v2_native_plan import validate_template
            require(packet['schema']=='phase11.5-r3-v2-native-v1' and
                packet['native']['template_policy']=='production-config-builder-v1','Native sample mapping scope')
            validate_template(job,job['mode'],'production-config-builder-v1')
            samples=waveform_samples(job)
        else:require(138000000*int(job['total_duration_ns'])%10**9==0,'Nonintegral sample count')
        blocks=(samples+524287)//524288
        expected=dict(dma_irqs=blocks+1,alarm_irqs=1,tail_irqs=1,running_successor_links=blocks-1,
                      refill_irq_pairs=blocks-1,running_tail_links=1)
        require({k:last[k]-base[k] for k in expected}==expected,'Per-job DMA/refill/launch/tail deltas')
        epoch=int(last['launch_epoch']);target=int(last['launch_target_ns']);observed=int(last['launch_observed_ns'])
        require(epoch>int(base['launch_epoch']) and epoch not in epochs and target%1000==0 and
                observed>=target and int(last['launch_delay_ns'])==observed-target,'Launch telemetry identity')
        epochs.add(epoch)
        running=[i for i in selected if i['status']['state']=='running' and int(i['launch_epoch'])==epoch]
        require(running,'Running current launch epoch absent')
        if packet.get('timing_mapping_policy')=='acknowledged-monotonic-launch-v1':
            from phase11_5_r3_v2_arm_mapping import validate_mapping
            require(packet['schema'] in ['phase11.5-r3-v2-native-v1','phase11.5-r3-v2-usb-rf-v1'],
                    'Prospective native/USB RF mapping scope')
            validate_mapping(arm['request'],arm['acknowledgment'],target)
        else:
            for i in running:
                s=i['status'];mapped=target+int(s['utc_now_ns'])-int(s['monotonic_now_ns'])
                require(abs(mapped-int(arm['start_utc_ns']))<=int(s['uncertainty_ns'])+1000000,'ARM UTC mapping')
        short=(samples%524288+31)//32
        require(short>0,'Expected short predecessor absent')
        previous=base['refill_short_predecessor']
        current=last['refill_short_predecessor']
        require(current and current['observations']-(previous['observations'] if previous else 0)==1,
                'One short predecessor required per job')
        # Instrumentation retains the worst remaining/total ratio across this boot.
        # If an earlier job remains worst, do not relabel its total as this job's.
        allowed={short}
        if previous:allowed.add(previous['total_words'])
        require(current['total_words'] in allowed,'Short predecessor length not bound to this or prior job')
        for key,total in (('refill_full_predecessor',16384),('refill_short_predecessor',current['total_words'])):
            v=last[key]
            require(v and v['total_words']==total and 0<v['remaining_words']<=total and
                    v['remaining_words']*4>=total,'Worst predecessor reserve below 25 percent')
        require(int(last['max_dma_irq_ns'])<=2849391 and int(last['max_refill_irq_to_ready_ns'])<=2849391,
                'Full-block critical deadline')
        result.append(dict(job_id=job['job_id'],mode=job['mode'],epoch=epoch,expected_counter_deltas=expected,
            duration_ns=int(job['total_duration_ns']),launch_target_ns=target,post_enable_delay_ns=observed-target,
            short_words=short,short_interval_ns=short*32*10**9/138000000,
            short_75_percent_budget_ns=short*24*10**9/138000000,
            cumulative_worst_short=current))
    return result
