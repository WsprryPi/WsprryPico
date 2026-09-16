"""Compose final-image raw RF/native/TCP proofs without old observation-window assumptions."""
import json,re
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_pilot import DEVICE
from phase11_5_r3_v2_pressure_plan import validate
from phase11_5_r3_v2_rf import PACKAGE3_POLICY
from audit_phase11_5_r3_v2_rf import audit as audit_rf
from audit_phase11_5_r3_v2_hour import journal,native_wire,PEER,NAME
from audit_phase11_5_r3_tls import audit_pressure as audit_tls
from audit_phase11_5_r3_transport import audit_pressure as audit_transport,tcp_packets

PACKETS={
 'a96a14455d08caa37fab21e7ef96be5bd5249afdf6471e8450c64a2e5d73f5a4':'T4',
 '9215a8049c83c2319506ef0c76100213a6bf5bb479a06cd283835c684719f095':'T5',
 'eef06c2fefab51ffb7954d1d563c956acb0cbfddf386597163bf91fd927ddce7':'T0',
 '6e866906cd3eaffab9d63e52fd64a54b8b6b44300179d7aacc22a6671e50c3df':'T1A',
}
PACKAGE3_DECODER_SHA256 = "d12fd9525b1e34b7615a9a84ef4ce5f32b65928341b9f2b0bbe5ba617dee02e5"

def audit(root,decoder):
    packet_sha=digest(root/'packet.json')
    packet=validate(json.loads((root/'packet.json').read_text()))
    package3=packet.get('closure_policy')==PACKAGE3_POLICY
    require(packet_sha in PACKETS or package3,'Unreviewed pressure packet')
    plan=packet['contention']
    require((root/'jobs.json').read_bytes()==(root/'packet.json').read_bytes(),'Pressure packet copy changed')
    base=audit_rf(root,packet_digest=packet_sha);rf=journal(root/'rf.jsonl')
    load=journal(root/'contention.jsonl');pressure=journal(root/'pressure.jsonl')
    require(load[0]['value']==dict(packet_sha256=packet_sha,policy=plan['policy'],binary_sha256=plan['binary_sha256']) and
        all(r['kind'] in ['start','finish','native_status','https_status'] for r in load),'Contention identity/failure')
    result=json.loads((root/'contention-result.json').read_text())
    require(result==load[-1]['value'] and result['status']=='CAPTURED_REQUIRES_AUDIT' and
        result['native_exit']==result['pressure_exit']==result['capture_exit']==0 and
        not (root/'contention-failed.json').exists(),'Contention completion')
    require(pressure[0]['value']==dict(packet_sha256=packet_sha,load_sha256=digest(root/'load.json')) and
        not (root/'load-failed.json').exists(),'Pressure provenance/completion')
    for index,job in enumerate(packet['jobs']):
        require(json.loads((root/f'pressure-job-{index}.json').read_text())==
            dict(status='PASS',packet_sha256=packet_sha,job_id=job['job_id']),'Pressure job completion marker')
    load_plan=json.loads((root/'load.json').read_text())
    require(load_plan['browser'] is False and load_plan['seconds']==packet['runtime_seconds'] and
        load_plan['boot_id']==packet['boot_id'] and load_plan['device_id']==DEVICE and
        load_plan['netns']==plan['netns'] and load_plan['mountns']==plan['mountns'] and
        load_plan['address']=='10.77.15.10','Pressure workload scope')
    ready=json.loads((root/'contention-ready.json').read_text())
    require(ready['packet_sha256']==packet_sha and ready['boot_id']==packet['boot_id'] and
        ready['observed_monotonic_ns']<next(r['monotonic_ns'] for r in rf if r['kind']=='arm_pending'),
        'Contention must be ready before ARM')
    https=[r for r in load if r['kind']=='https_status'];require(len(https)==result['https_requests']==1,'Initial HTTPS only')
    row=https[0];v=row['value'];body=json.loads(bytes.fromhex(v['body_hex']))
    request=f'GET /api/v1/status HTTP/1.1\r\nHost: {NAME}:18443\r\nConnection: close\r\n\r\n'.encode()
    headers={k.lower():v for k,v in v['headers']}
    require(bytes.fromhex(v['request_hex'])==request and v['status']==200 and v['peer_sha256']==PEER and
        body['job']['boot_id']==packet['boot_id'] and body['transport']['active']==2 and body['transport']['pending']==0 and
        int(headers['content-length'])==len(bytes.fromhex(v['body_hex'])) and
        0<=row['monotonic_ns']-v['began_monotonic_ns']<=15_000_000_000 and
        row['monotonic_ns']<=ready['observed_monotonic_ns'],'Initial HTTPS authentication/body/deadline')
    native,metrics=native_wire(root,packet,decoder,
        decoder_sha256=PACKAGE3_DECODER_SHA256 if package3 else None)
    host=[]
    for row in load:
        if row['kind']!='native_status':continue
        v=row['value'];body=json.loads(bytes.fromhex(v['body_hex']))
        require(body==v['value'] and 0<=row['monotonic_ns']-v['began_monotonic_ns']<=3_000_000_000,'Native HTTP body/deadline')
        if row['monotonic_ns']>=ready['observed_monotonic_ns']:
            identity=body['host']['identity']
            require(identity['device_id']==DEVICE and identity['boot_id']==packet['boot_id'],'Native HTTP identity')
            host.append(dict(began=v['began_monotonic_ns'],ended=row['monotonic_ns'],value=body['job']))
    coverage=[]
    for job in packet['jobs']:
        statuses=[r for r in rf if r['kind']=='status' and r['value']['value']['job_id']==job['job_id'] and r['value']['value']['state']=='running']
        require(statuses,'Missing USB Running interval')
        begin=statuses[0]['monotonic_ns'];end=statuses[-1]['monotonic_ns']
        for name,samples in [('native_wire',native),('native_http',host)]:
            selected=[s for s in samples if begin-6_000_000_000<=s['began']<=end+6_000_000_000]
            require(selected and selected[0]['began']<=begin and selected[-1]['began']>=end and
                all(0<b['began']-a['began']<=6_000_000_000 for a,b in zip(selected,selected[1:])),name+' pressure cadence')
            for sample in selected:
                if begin+6_000_000_000<=sample['began'] and sample['ended']<=end-6_000_000_000:
                    s=sample['value'];require(s['boot_id']==packet['boot_id'] and s['state']=='running' and
                        s['output_active'] is True and s['job_id']==job['job_id'] and s['owner_id']==packet['owner_id'],name+' pressure authority')
            coverage.append(dict(job_id=job['job_id'],family=name,samples=len(selected)))
    start,end=[json.loads((root/('tcp-clock-'+k+'.json')).read_text()) for k in ['start','end']]
    offsets=[v['realtime_ns']-v['monotonic_ns'] for v in [start,end]]
    require(start['monotonic_ns']<pressure[0]['monotonic_ns']<pressure[-1]['monotonic_ns']<end['monotonic_ns'] and
        abs(offsets[1]-offsets[0])<=10_000_000,'TCP clock mapping/coverage')
    require(re.search(r'\b0 packets dropped by kernel\b',(root/'pressure-capture.stderr').read_text()),'TCP capture drops')
    packets=tcp_packets((root/'pressure.pcap').read_bytes())
    if packet['pressure_family']=='tls':
        checked=audit_tls(packet,pressure,rf)
    else:
        installed,=[r for r in pressure if r['kind']=='ack_filter_installed']
        require(installed['value']['packet_sha256']==packet_sha and installed['value']['netns']==load_plan['netns'],
            'ACK filter packet/namespace')
        checked=audit_transport(packet,pressure,rf,packets,offsets[0])
        require(json.loads((root/'ack-filter.json').read_text())['status']=='REMOVED','ACK filter cleanup')
    epochs={j['job_id']:j['epoch'] for j in base['jobs']}
    require(all(epochs[c['job_id']]==c['launch_epoch'] for c in checked['cases']),'Pressure raw ARM epoch mismatch')
    label=('PACKAGE3_'+packet['pressure_family'].upper()) if package3 else PACKETS[packet_sha]
    base.update(status=label+'_PRESSURE_VERIFIED',pressure=checked,native=metrics,
        contention_coverage=coverage,tcp_packets=len(packets),physical_hour_or_saturation_verified=True,
        family_closed=False)
    return base
