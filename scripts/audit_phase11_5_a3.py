#!/usr/bin/env python3
"""Offline exact-three-job A3 audit; no hardware or network access."""
import argparse
import hashlib
import json
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_pilot import validate_packet
from phase11_5_browser_jobs import checked_reply,NAME
from audit_phase11_5_idle import audit as audit_usb
from audit_phase11_5_load import audit as audit_load
from phase11_5_pilot_supervisor import finished


def dma_coverage(packet, baseline, final):
    # A3's validated packet contains exactly three ten-second, single-event
    # Tones. Check cumulative hardware counters against the complete jobs,
    # including the final short data buffer and the separate zero tail.
    validate_packet(packet)
    samples=packet['system_clock_hz']*10
    blocks=(samples+524287)//524288
    count=len(packet['jobs'])
    expected=dict(dma_irqs=count*(blocks+1),tail_irqs=count,alarm_irqs=count,
                  running_successor_links=count*(blocks-1))
    observed={key:final[key]-baseline[key] for key in expected}
    require(observed==expected,'Missing complete-job DMA/launch/tail coverage')
    return observed


def audit(root,decoder):
    packet=json.loads((root/'jobs.json').read_text());validate_packet(packet)
    text=(root/'browser-jobs.jsonl').read_text();require(text.endswith('\n'),'Truncated actor log')
    rows=[json.loads(line) for line in text.splitlines()]
    require(rows[0]['kind']=='start' and rows[0]['value']['packet']==packet and
            rows[-1]['kind']=='finish' and rows[-1]['value']==dict(
                result='CAPTURED_REQUIRES_AUDIT',output_active=False),'Actor did not complete')
    require([r['sequence'] for r in rows]==list(range(len(rows))) and
            all(a['monotonic_ns']<=b['monotonic_ns'] for a,b in zip(rows,rows[1:])), 'Actor order')
    operations=[];pending=None;requests=set();loads=[];arms=[];arm_notes=[];latencies=[]
    for row in rows[1:-1]:
        kind,value=row['kind'],row['value']
        if kind=='request_intent':
            request=value['request'];wire=bytes.fromhex(value['wire_hex'])
            head,body=wire.split(b'\r\n\r\n',1)
            require(head.startswith(b'POST /api/v1/jobs HTTP/1.1\r\n') and
                    f'Host: {NAME}:18443'.encode() in head and
                    f'Content-Length: {len(body)}'.encode() in head and
                    json.loads(body)==request,'Browser request wire mismatch')
            require(pending is None and request['request_id'] not in requests and
                    request['session_id']==packet['browser_session_id'],'Unexpected request/retry/session')
            requests.add(request['request_id']);operations.append(request['operation'])
            pending=(request,row['monotonic_ns'])
            op=request['operation']
            if op=='CLAIM':require(request['body']==dict(owner_id=packet['owner_id'],lease_ms=60000),'CLAIM differs')
            elif op=='LOAD':loads.append(request['body'])
            elif op=='ARM':arms.append(request['body'])
            elif op=='RELEASE':require(request['body']=={},'RELEASE differs')
        elif kind=='response':
            require(pending is not None,'Unbound response');request,began=pending;pending=None
            require(value['request_id']==request['request_id'] and
                    value['began_monotonic_ns']<=began<=row['monotonic_ns'] and
                    row['monotonic_ns']-value['began_monotonic_ns']<=5_000_000_000,
                    'Browser response binding/deadline')
            checked_reply(request,value['http_status'],bytes.fromhex(value['body_hex']))
            latencies.append(row['monotonic_ns']-value['began_monotonic_ns'])
        elif kind=='armed_job':arm_notes.append(value)
        else:raise ValueError('Unexpected actor event or failure')
    require(pending is None and operations==['HELLO']+['CLAIM','LOAD','ARM','RELEASE']*3 and
            loads==packet['jobs'] and len(arms)==len(arm_notes)==3,'Missing/extra operations or changed jobs')
    for job,arm,note in zip(packet['jobs'],arms,arm_notes):
        require(arm['job_id']==job['job_id'] and arm['max_start_uncertainty_ns']=='500000000' and
                note==dict(job=job,start_utc_ns=arm['start_utc_ns']),'ARM differs from frozen job')
    usb=audit_usb(root/'usb-health.jsonl',Path(packet['baseline']),packet)
    counters=dma_coverage(packet,finished(Path(packet['baseline']),'READ_ONLY_INVENTORY')['info'],
                          usb['rf_last_observation'])
    load=audit_load(root,decoder,packet)
    load_events=[json.loads(line) for line in (root/'load-events.jsonl').read_text().splitlines()]
    begin=next(r['monotonic_ns'] for r in load_events if r['kind']=='nominal_begin')
    end=next(r['monotonic_ns'] for r in load_events if r['kind']=='nominal_finish')
    require(all(begin<=r['monotonic_ns']<=end for r in rows if r['kind']=='armed_job'),
            'RF ARM occurred outside nominal workload')
    status_rows=[json.loads(line) for line in (root/'usb-health.jsonl').read_text().splitlines()]
    for job in packet['jobs']:
        require(any(r['kind']=='status' and begin<=r['monotonic_ns']<=end and
                    r['value']['value']['job_id']==job['job_id'] and
                    r['value']['value']['state']=='complete' for r in status_rows),
                'Finite job did not complete within nominal workload')
    permits=[r['value']['request_id'] for r in load_events if r['kind']=='browser_control_permit']
    require(len(permits)==len(requests) and set(permits)==requests,'Browser control grant mismatch')
    require(json.loads((root/'actor-result.json').read_text())==dict(exit=0),'Actor exit')
    return dict(status='CAPTURED_REQUIRES_FINAL_REVIEW',packet_sha256=hashlib.sha256(
        (root/'jobs.json').read_bytes()).hexdigest(),usb=usb,load=load,
        dma_coverage=counters,
        browser_operations=operations,max_browser_job_seconds=max(latencies)/1e9,
        limitation='Retained-history heap comparison remains separate; this is not conducted RF spectral acceptance')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path)
    p.add_argument('--observer-decoder',type=Path,required=True);a=p.parse_args()
    print(json.dumps(audit(a.root,a.observer_decoder),indent=2))
