"""Offline remaining-mode wire, lifecycle, workload and exact DMA evidence audit."""
import json
import hashlib
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_r2_modes_plan import validate
from phase11_5_pilot_supervisor import finished
from audit_phase11_5_idle import audit as audit_usb
from audit_phase11_5_load import audit as audit_load
from audit_phase11_5_r1 import usb_measurement_costs


def transactions(packet, exchanges, events, *, packet_validator=validate):
    """Bind actual production or USB wire mutations to the frozen event list."""
    packet_validator(packet)
    requests=[v['request'] for v in exchanges]
    mut=[q for q in requests if q['op'] not in ('HELLO','CAPS','STATUS','GET_CLOCK','PING','RENEW')]
    require([q['op'] for q in mut]==['CLAIM','LOAD','ARM','RELEASE']*len(packet['jobs']),
            'Missing/extra/reordered RF mutation; no retry')
    require(sum(q['op']=='RENEW' for q in requests)<=packet['maximum_renewals'],'Renewal budget')
    for q in requests:
        if q['op'] in ('CLAIM','RENEW'):
            require(q['body']==dict(owner_id=packet['owner_id'],lease_ms=60000),'Owner/lease differs')
    arms=[]
    for n,job in enumerate(packet['jobs']):
        claim,load,arm,release=mut[n*4:n*4+4]
        require(load['body']==job and release['body']=={},'Wire job differs from finite plan')
        require(arm['body']['job_id']==job['job_id'] and arm['body']['max_start_uncertainty_ns']=='500000000',
                'ARM job/uncertainty')
        arm_ex=next(v for v in exchanges if v['request']==arm)
        reply=arm_ex['response']['body']
        require(reply['start_utc_ns']==arm['body']['start_utc_ns'] and reply['clock']['state']=='synchronized' and
                reply['clock']['leap']=='normal','ARM guarded clock/target')
        if packet['submission_path']=='production':
            require(arm['body']['start_utc_ns']==packet['production_binding']['start_utc_ns'],
                    'Production schedule changed after binding')
        states=[]
        for ex in exchanges:
            if ex['request']['op']=='STATUS':states.append(ex['response']['body'])
        states += [e['body'] for e in events if e.get('event')=='JOB_STATE']
        relevant=[s for s in states if s.get('job_id')==job['job_id']]
        require({'loaded','armed','running','complete'}<={s['state'] for s in relevant} and
                any(s['state']=='running' and s['output_active'] for s in relevant) and
                all(s['state']=='running' or not s['output_active'] for s in relevant),
                'Wire lifecycle/output coverage')
        require(any(s['state']=='complete' and not s['output_active'] for s in relevant), 'Finite completion')
        arms.append(dict(job=job,start_utc_ns=arm['body']['start_utc_ns'],monotonic_ns=arm_ex['started_ns']))
    return arms


def timing(packet, arms, rows):
    infos=[r for r in rows if r['kind']=='info']
    require(infos and max(r['value']['value']['allocator_largest_successful_request_bytes'] for r in infos)<=18364,
            'Allocation exceeds reused R1 demonstrated request')
    result=[];epochs=set()
    for n,arm in enumerate(arms):
        start=arm['monotonic_ns'];end=arms[n+1]['monotonic_ns'] if n+1<len(arms) else 2**64
        before=[r['value']['value'] for r in infos if r['monotonic_ns']<start]
        selected=[r['value']['value'] for r in infos if start<=r['monotonic_ns']<end]
        require(before and selected,'Missing per-job INFO window')
        base,last=before[-1],selected[-1]
        job=arm['job'];samples=138000000*int(job['total_duration_ns'])//10**9
        require(138000000*int(job['total_duration_ns'])%10**9==0,'Nonintegral sample count')
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


def audit(root,decoder,*,cadence_policy='strict-start-gap-v1',packet_validator=validate,baseline_path=None):
    packet=json.loads((root/'jobs.json').read_text());packet_validator(packet)
    first=json.loads((root/'usb-health.jsonl').read_text().splitlines()[0])
    require(first['kind']=='start' and first['value']['packet_sha256']==hashlib.sha256((root/'jobs.json').read_bytes()).hexdigest(),
            'Mode packet is not the observer-frozen packet')
    # Collected evidence may live away from the execution host. audit_usb
    # still verifies the baseline's frozen content hash before using it.
    usb=audit_usb(root/'usb-health.jsonl',Path(packet['baseline']) if baseline_path is None else baseline_path,packet)
    load=audit_load(root,decoder,packet,cadence_policy=cadence_policy)
    rows=[json.loads(s) for s in (root/'usb-health.jsonl').read_text().splitlines()]
    if packet['submission_path']=='usb':
        pending={};exchanges=[];events=[]
        for r in rows:
            if r['kind']=='wtp_tx':pending[r['value']['request']['request_id']]=(r['value']['request'],r['monotonic_ns'])
            elif r['kind']=='wtp_message':
                msg=r['value']
                if msg['type']=='event':events.append(msg);continue
                req,start=pending.pop(msg['request_id'])
                require(0<=r['monotonic_ns']-start<=5*10**9,'USB transaction deadline')
                exchanges.append(dict(request=req,response=msg,started_ns=start,finished_ns=r['monotonic_ns']))
        require(not pending,'Unfinished USB wire')
        arms=transactions(packet,exchanges,events,packet_validator=packet_validator)
    else:arms=load.pop('mode_arms')
    mode_timing=timing(packet,arms,rows)
    nominal=[json.loads(s) for s in (root/'load-events.jsonl').read_text().splitlines()]
    begin=next(r['monotonic_ns'] for r in nominal if r['kind']=='nominal_begin')
    end=next(r['monotonic_ns'] for r in nominal if r['kind']=='nominal_finish')
    require(all(begin<=a['monotonic_ns']<=end for a in arms),'ARM outside nominal workload')
    final=usb['rf_last_observation']
    # Complete counters must already be observed before nominal workload finishes.
    last=next(r for r in reversed(rows) if r['kind']=='info' and r['monotonic_ns']<=end)['value']['value']
    require(all(last[k]==final[k] for k in ('dma_irqs','tail_irqs','alarm_irqs')),
            'Finite work outlasted nominal workload')
    return dict(status='PASS',source_revision=packet['source_revision'],boot=packet['boot_id'],
                submission_path=packet['submission_path'],completed_jobs=len(packet['jobs']),
                timing=mode_timing,usb=usb,load=load,observer_cost=usb_measurement_costs(root/'usb-health.jsonl'))
