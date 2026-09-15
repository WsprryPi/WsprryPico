"""Confirm two immutable harness failures without accepting their incomplete workload."""
import importlib.util
import json

from audit_phase11_5_completion_p1_failure import inputs
from audit_phase11_5_idle import frames
from audit_phase11_5_r3_v2_hour import journal, native_wire
from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_load_reply_target import healthy
from phase11_5_rf_reservation import inactive
from validate_wtp_contract import SchemaValidator

PACKETS={
    'b007878df252c296a1baf5f626fb983e7caabe999d214beaf7a40c46c997b84a': 'event_refresh',
    '0bda1b7f0dc648a2537456352fa10528c6adb45e3b4a0790afed2a219e2de5cb': 'foreign_owner_readiness',
    'af60edcba5e3767abf6dafb5e9982f058b6200a385a9ed2cbfad56794a009fc5': 'reply_timeout',
}


def audit(root):
    sha=digest(root/'packet.json');require(sha in PACKETS,'Exact failed guard packet')
    p,values=inputs(root,sha);kind=PACKETS[sha]
    for phase in ('before','final'):
        inactive({b:values[phase+'-'+b] for b in ('a','b')})
        healthy(values[phase+'-a']['info'],p['boot_id'],p['source_revision'])
    rows=journal(root/'idle.jsonl');require(rows[0]['value']==dict(packet_sha256=sha),'Raw packet identity')
    schema=json.loads((root/'docs/protocol/wtp-1.schema.json').read_text());validator=SchemaValidator(schema)
    requests={};written={};buffers={};replies={}
    for r in rows:
        k,v=r['kind'],r['value']
        if k=='usb_tx':
            q,left=frames(bytes.fromhex(v['hex']));label=v['label']
            require(not left and q==[v['request']] and not validator.errors(q[0],schema) and label not in requests,'Request bytes/schema')
            require(q[0]['op'] in ('HELLO','CLAIM','LOAD','RELEASE'),'No unexpected mutation or RF command')
            requests[label]=q[0];written[label]=0;buffers[label]=b'';replies[label]=[]
        elif k=='usb_write':
            label=v['label'];written[label]+=v['bytes'];require(v['bytes']>0 and written[label]==v['total_written'],'Write evidence')
        elif k=='usb_rx':
            label=v['label'];messages,buffers[label]=frames(buffers[label]+bytes.fromhex(v['hex']))
            for m in messages:
                require(not validator.errors(m,schema) and m['session_id']==requests[label]['session_id'],'Complete response/event schema')
                if m['type']=='response':
                    require(m['ok'] is True and all(m[x]==requests[label][x] for x in ('op','request_id')),'Matched successful prefix')
                    replies[label].append(m)
                else:require(m['boot_id']==p['boot_id'] and m['event'] in ('JOB_STATE','OWNER_RELEASED'),'Idle event')
    require(list(requests)==(['hello','claim-0','load-0']+
                            ['cleanup-HELLO','cleanup-CLAIM','cleanup-RELEASE']),'Exact failed sequence and finite cleanup')
    require(requests['load-0']['body']==p['jobs'][0] and written['load-0']==52105,'Full maximum primary write')
    partial='load-0'
    if kind=='reply_timeout':
        require(not buffers[partial] and not replies[partial] and not any(r['kind']=='usb_rx' and r['value']['label']==partial for r in rows),'No primary reply bytes')
    elif kind=='foreign_owner_readiness':
        require(len(replies[partial])==1 and len(replies[partial][0]['body']['adjustments'])==512 and len(buffers[partial])==16,'Complete LOAD reply followed by incomplete event header; replay never sent')
    else:
        require(buffers[partial] and not replies[partial],'Incomplete USB reply remains unaccepted')
    require(all(not b for label,b in buffers.items() if label!=partial),'No other truncated exchange')
    native,metrics=native_wire(root,p,root/'pi/phase115_tls_observer_test.py')
    require(metrics['connections']==1 and all(s['value']['output_active'] is False for s in native) and
            any(s['value']['state']=='loaded' and s['value']['job_id']==p['jobs'][0]['job_id'] for s in native),'Complete native Loaded/STATUS prefix')
    content=journal(root/'contention.jsonl');failure=next(r for r in (rows if kind=='reply_timeout' else content) if r['kind']=='failure')
    snapshots=[r for r in content if r['kind']=='native_status'];last=snapshots[-1]['value']['value'];host=last['host']
    require(host['session_phase']=='ready' and host['network']['state']=='ready','Session was still ready at false guard')
    if kind=='event_refresh':
        require(host['ready'] is True and host['remote'] is None and host['status_observed_ms'] is None and last['job'] is None,'Actual temporary status invalidation')
    elif kind=='foreign_owner_readiness':
        require(host['ready'] is False and host['remote']==last['job'] and host['remote']['state']=='loaded' and
                host['remote']['owner_id']==p['owner_id'] and int(host['now_ms'])-int(host['status_observed_ms'])<=6000 and
                host['diagnostic']=='WTP endpoint occupied or unsafe; startup made no mutation','Application readiness is foreign-owner admission')
    spec=importlib.util.spec_from_file_location('guard_decoder',root/'pi/phase115_tls_observer_test.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    raw=module.decode((root/'production-tls.bin').read_bytes());closes=[r for r in raw if r['kind']==5]
    require(len(closes)==1 and closes[0]['monotonic_ns']>failure['monotonic_ns'] and
            'Shutdown requested: received SIGTERM signal' in (root/'production.log').read_text(),'Harness stop precedes native closure')
    final=values['final-a']['wtp']['STATUS'];info=values['final-a']['info']
    require(final['state']=='empty' and any(r['job_id']==p['jobs'][0]['job_id'] and r['state']=='aborted' and
            r['output_active'] is False for r in final['terminal_records']) and info['network_wtp_close_reason']==2 and
            info['network_wtp_tls_result']==0,'Authoritative idle abort and peer-close diagnostic')
    for name,state,phase in [('acquired','HELD','before'),('released','RELEASED','final')]:
        r=json.loads((root/('reservation-'+name+'.json')).read_text())
        require(r['packet_sha256']==sha and r['state']==state and r['boards']==inactive({b:values[phase+'-'+b] for b in ('a','b')}),'Reservation reconciliation')
    result=json.loads((root/'run-result.json').read_text());require(result==rows[-1]['value'] and result['status']=='FAILED' and result['rf_jobs']==0,'Preserved failed result')
    return dict(status='NATIVE_IDLE_REPLY_TIMEOUT_CONFIRMED' if kind=='reply_timeout' else 'HARNESS_NATIVE_GUARD_FAILURE_CONFIRMED',packet_sha256=sha,failure=kind,rf_jobs=0,
        capacity_acceptance=False,native=metrics,incomplete_usb_reply=partial,configurations_preserved=True,
        schedules_disabled=True,reservation_released=True,allocator_peak_bytes=info['allocator_peak_bytes'],
        source_revision=p['source_revision'],boot_id=p['boot_id'])
