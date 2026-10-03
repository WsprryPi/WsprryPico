#!/usr/bin/env python3
"""Offline resource-only review; never infers WTP authority or pressure acceptance."""
import hashlib
import json
from pathlib import Path
from phase12_composition_audit import require, strict_load, validate_plan, counter, number
from phase12_composition_capture import check_info, pools, acl_credits


def review(plan, capture_path):
    validate_plan(plan)
    require(plan['heap_return_tolerance_bytes']<=4096,'predeclared heap return bound')
    path=Path(capture_path)
    require(path.is_file() and path.stat().st_size<=20*1024*1024,'bounded capture file')
    wire=path.read_bytes();lines=wire.splitlines()
    require(len(lines)==243,'exact start/241 INFO/complete records')
    records=[strict_load(line) for line in lines]
    require(records[0]['kind']=='start' and records[0]['plan']==plan and
            records[0]['physical_acceptance'] is False,'predeclared capture plan')
    require(records[-1]['kind']=='complete' and
            records[-1]['status']=='CAPTURE_COMPLETE_REVIEW_REQUIRED' and
            records[-1]['physical_acceptance'] is False,'complete capture required')
    baseline=None;previous=None;minimum_stack=None;maximum_heap=0;max_pools={};previous_acl=None;baseline_acl=None
    def measured(info):
        result={'lwip.'+k:v for k,v in pools(info).items()}
        heap=info['network']['memory'].get('heap')
        if heap is not None:
            require(type(heap) is dict,'lwIP heap metric shape')
            for key in ('used','capacity','peak','errors'):counter(heap[key],'lwIP heap '+key)
            require(heap['errors']==0,'lwIP heap errors')
            result['lwip.heap']=heap
        result.update({'btstack.'+k:v for k,v in info['btstack_pools'].items()})
        for key,pool in result.items():
            require(0<=pool['used']<=pool['peak']<=pool['capacity'],'pool occupancy bounds: '+key)
        return result
    for index,record in enumerate(records[1:-1]):
        require(record['kind']=='INFO' and record['transport_raw'] is True,'actual INFO records')
        begin=number(record['elapsed_start_s'],'sample start');end=number(record['elapsed_end_s'],'sample end')
        require(index*30<=begin<=index*30+45 and 0<=end-begin<=10 and end<=7245,'sample cadence/deadline')
        raw=bytes.fromhex(record['raw_info_hex'])
        require(0<len(raw)<=16384 and hashlib.sha256(raw).hexdigest()==record['raw_info_sha256'],'raw bytes hash')
        info=strict_load(raw)
        require(info==record['info'],'raw/decoded INFO equality')
        canonical=json.dumps(info,sort_keys=True,separators=(',',':')).encode()
        require(hashlib.sha256(canonical).hexdigest()==record['decoded_info_sha256'],'decoded INFO hash')
        check_info(plan,info)
        previous_acl=acl_credits(plan,info,previous_acl)
        if index==0:baseline_acl=previous_acl
        status=info['status']
        require(status['storage_healthy'] is True and info['fault_allocation_recorded'] is False,'storage/allocation guard')
        target=counter(status['monotonic_now_ns'],'target monotonic')
        heap=counter(info['heap_allocated_bytes'],'heap allocated')
        stack=counter(info['core0_stack_used_bytes'],'stack used')
        margin=plan['core0_stack_capacity_bytes']-stack
        require(margin>=plan['stack_min_margin_bytes'],'stack margin')
        minimum_stack=margin if minimum_stack is None else min(minimum_stack,margin)
        maximum_heap=max(maximum_heap,heap);current_pools=measured(info)
        if baseline is None:
            require(begin<=10,'initial observation bracket')
            baseline=(heap,current_pools)
        if previous is not None:
            previous_begin,previous_end,previous_target,prior_pools=previous
            require(0<begin-previous_begin<=45 and target>previous_target,'sample/target monotonic progress')
            delta=(target-previous_target)/1_000_000_000
            # 100 ms bounds sampling skew and RP2350/host oscillator drift over
            # one <=45 s gap. It cannot conceal a prior 30 s queued response.
            require(begin-previous_end-.1<=delta<=end-previous_begin+.1,'stale target sample bracket')
            require(set(current_pools)==set(prior_pools),'measured pool set changed')
            for key,pool in current_pools.items():
                require(pool['capacity']==prior_pools[key]['capacity'] and
                        pool['peak']>=prior_pools[key]['peak'],'pool capacity/peak changed: '+key)
        for key,pool in current_pools.items():max_pools[key]=max(max_pools.get(key,0),pool['used'])
        previous=(begin,end,target,current_pools)
    require(records[-2]['elapsed_start_s']>=7200,'full two-hour interval')
    require(status['state']=='empty','final scheduler state empty')
    for key in ('bootstrap_connected','bootstrap_setup_pending','bootstrap_reset_pending','ble_indication_pending'):
        require(info[key] is False,'final pending state: '+key)
    for key in ('network_active_connections','network_pending_connections','network_buffered_rx_bytes',
                'network_pending_tcp_bytes','bootstrap_pending_tcp_bytes','ble_active_connections',
                'ble_inbound_bytes','ble_outbound_bytes','ble_outbound_frames','softap_retained_sessions'):
        require(counter(info[key],key)==0,'final transport reclamation: '+key)
    require(heap<=baseline[0]+plan['heap_return_tolerance_bytes'],'heap return exceeds predeclared tolerance')
    for key,pool in current_pools.items():require(pool['used']<=baseline[1][key]['used'],'individual pool return: '+key)
    acl_credits(plan,info,previous_acl,final=True,baseline=baseline_acl)
    return dict(status='RESOURCE_ONLY_SOAK_PASS_REVIEW_REQUIRED',capture_sha256=hashlib.sha256(wire).hexdigest(),
        plan_sha256=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        source_commit=plan['source_commit'],mode=plan['mode'],samples=241,duration_s=7200,
        heap_baseline_bytes=baseline[0],heap_final_bytes=heap,heap_peak_observed_bytes=maximum_heap,
        heap_return_tolerance_bytes=plan['heap_return_tolerance_bytes'],minimum_stack_margin_bytes=minimum_stack,
        pool_peak_observed=max_pools,pool_final={k:v['used'] for k,v in current_pools.items()},
        controller_acl_credits=previous_acl,controller_internal_ram_measured=False,
        target_freshness_brackets_verified=True,scheduler_final_state='empty',
        absolute_sample_freshness_proven=False,
        final_owner_verified=False,final_job_identity_verified=False,pressure_qualified=False,
        full_composition_qualified=False,physical_acceptance=False,independent_review_pending=True)
