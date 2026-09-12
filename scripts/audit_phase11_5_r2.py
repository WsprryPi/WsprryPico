#!/usr/bin/env python3
"""Offline R2 Tone gate audit; never promotes missing modes/submission paths."""
import json
from pathlib import Path
from audit_phase11_5_a3 import audit as audit_actor
from audit_phase11_5_r1 import usb_measurement_costs
from phase11_5_r2_plan import validate, jobs
from phase11_5_inventory import require


def timing(packet, actor, rows):
    validate(packet)
    infos=[r for r in rows if r['kind']=='info']
    require(infos and all(r['value']['value']['allocator_largest_successful_request_bytes']<=18364
                         for r in infos), 'R2 allocation exceeds R1 demonstrated feasibility')
    arms=[r for r in actor if r['kind']=='armed_job']
    releases=[r for r in actor if r['kind']=='request_intent' and
              r['value']['request']['operation']=='RELEASE']
    require(len(arms)==len(releases)==3, 'R2 exact arm/release coverage')
    epochs=set();result=[]
    for job,arm,release in zip(packet['jobs'],arms,releases):
        selected=[r['value']['value'] for r in infos if arm['monotonic_ns'] <= r['monotonic_ns'] < release['monotonic_ns']]
        complete=[i for i in selected if i['status']['state']=='complete']
        require(complete, 'R2 missing completed-job INFO before release')
        last=complete[-1]
        before=[r['value']['value'] for r in infos if r['monotonic_ns']<arm['monotonic_ns']]
        require(before, 'R2 missing prelaunch INFO')
        base=before[-1]
        epoch=int(last['launch_epoch']);target=int(last['launch_target_ns']);observed=int(last['launch_observed_ns'])
        require(epoch>0 and epoch not in epochs and target%1000==0 and 0<=observed-target,
                'R2 launch identity or observation preceding target')
        requested_utc=int(arm['value']['start_utc_ns'])
        require(observed-target < 10**9-requested_utc % 10**9,
                'R2 launch observation outside requested UTC second')
        epochs.add(epoch)
        # A current-job running snapshot binds launch epoch to the independently
        # observed lifecycle window. UTC correlation is bounded by the device's
        # clock uncertainty; it is not an electrical-edge timing measurement.
        running=[i for i in selected if i['status']['state']=='running' and int(i['launch_epoch'])==epoch]
        require(running, 'R2 missing current launch epoch while Running')
        for i in running:
            status=i['status']
            mapped=target+int(status['utc_now_ns'])-int(status['monotonic_now_ns'])
            require(abs(mapped-int(arm['value']['start_utc_ns']))<=int(status['uncertainty_ns'])+1000000,
                    'R2 launch target does not match ARM UTC within recorded uncertainty')
        samples=138000000*int(job['total_duration_ns'])//10**9
        blocks=(samples+524287)//524288
        expected={'dma_irqs':blocks+1,'alarm_irqs':1,'tail_irqs':1,
                  'running_successor_links':blocks-1,'refill_irq_pairs':blocks-1,'running_tail_links':1}
        require({k:last[k]-base[k] for k in expected}==expected, 'R2 per-job DMA/launch/tail deltas')
        short_words=((samples%524288)+31)//32
        require(short_words>0, 'R2 Tone must exercise a short predecessor')
        for key,total in (('refill_full_predecessor',16384),('refill_short_predecessor',short_words)):
            v=last[key]
            require(v is not None and type(v['total_words']) is int and v['total_words']==total and
                    type(v['remaining_words']) is int and 0<v['remaining_words']<=total and
                    v['remaining_words']*4>=total, 'R2 predecessor reserve/length')
        require(last['refill_short_predecessor']['observations']-base['refill_short_predecessor']['observations']==1
                if base['refill_short_predecessor'] else last['refill_short_predecessor']['observations']==1,
                'R2 missing one short predecessor per finite Tone')
        require(int(last['max_refill_irq_to_ready_ns'])<=2849391 and
                int(last['max_dma_irq_ns'])<=2849391,
                'R2 IRQ/refill critical budget')
        result.append(dict(job_id=job['job_id'],epoch=epoch,launch_target_ns=target,
            post_enable_observation_lateness_ns=observed-target,
            max_alarm_callback_ns=int(last['max_alarm_irq_ns']),counter_deltas=expected,
            short_interval_ns=last['refill_short_predecessor']['total_words']*32*10**9/138000000))
    return result


def audit(root,decoder):
    packet=json.loads((root/'jobs.json').read_text());validate(packet)
    result=audit_actor(root,decoder)
    actor=[json.loads(s) for s in (root/'browser-jobs.jsonl').read_text().splitlines()]
    rows=[json.loads(s) for s in (root/'usb-health.jsonl').read_text().splitlines()]
    result['timing']=timing(packet,actor,rows)
    result['observer_cost']=usb_measurement_costs(root/'usb-health.jsonl')
    result.update(family='R2',packet_scope='three browser-owned Tone jobs only',
        completed_jobs=3,required_family_jobs=7,family_closed=False,
        remaining=['QRSS','FSKCW','DFCW','WSPR','production-owned submission','USB-reference submission'],
        timing_limitation='DMA remaining-word reserve includes work before IRQ entry; IRQ-entry-to-ready alone omits interrupt entry latency. Launch is post-enable software observation, not first electrical edge.')
    return result
