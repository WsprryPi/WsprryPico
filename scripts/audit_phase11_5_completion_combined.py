"""Independently bind P2 allocation overlap and classified outcome to raw RF/native evidence."""
import json
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_completion_combined import validate_profile, resident, running, PEER, DEVICE
from audit_phase11_5_r3_v2_rf import audit as audit_rf
from audit_phase11_5_r3_v2_hour import journal, native_wire


def overlap(packet, rf, load):
    c=packet['combined']; primary,recovery=c['cases']
    one=lambda rows,kind:single([r for r in rows if r['kind']==kind],kind)
    ready=one(load,'combined_http_ready'); held=one(rf,'combined_resident')
    tx=one(rf,'capacity_tx'); final=one(rf,'capacity_message')
    info={(r['monotonic_ns']):r for r in rf if r['kind']=='info'}
    warm=ready['value']['info']; sample=held['value']['info']
    expected=rf[0]['value']['packet_sha256']
    require(ready['value']['packet_sha256']==held['value']['packet_sha256']==warm['packet_sha256']==sample['packet_sha256']==expected, 'Exact overlap packet identity')
    for snap in (warm,sample):
        require(snap['monotonic_ns'] in info and info[snap['monotonic_ns']]['value']==snap['value'],
                'Residence must match independently decoded raw INFO')
    resident(sample,warm,held['value']['began_ns'],packet)
    require(held['value']['baseline']==warm and ready['value']['peer_sha256']==PEER and
            ready['value']['authenticated_ns']<warm['monotonic_ns']<=ready['monotonic_ns']<tx['monotonic_ns'] and
            held['value']['began_ns']<=tx['monotonic_ns']<=held['monotonic_ns'], 'Warm TLS and WTP allocation ordering')
    selected=[r for r in load if r['kind'] in ('http_tx','http_write_complete','http_response')]
    require([r['kind'] for r in selected]==['http_tx','http_write_complete','http_response']*2,'Exact P2 HTTP exchanges')
    for case,index in zip((primary,recovery),(0,3)):
        offered,written,reply=selected[index:index+3]
        require(offered['value']==case and written['value']==dict(label=case['label'],bytes=len(bytes.fromhex(case['wire_hex']))),
                'Exact complete HTTP bytes')
        value=reply['value']; body=json.loads(bytes.fromhex(value['body_hex']))
        require(value['label']==case['label'] and value['status']==case['expected_status'] and value['peer_sha256']==PEER and
                0<=reply['monotonic_ns']-value['began_monotonic_ns']<=15_000_000_000,'HTTP classification/identity/deadline')
        if case['error_code']:
            require(body['error']['code']==case['error_code'],'Exact allocation refusal')
        else:
            require(body['ok'] is True and body['result']['device_id']==DEVICE and
                    body['result']['boot_id']==packet['boot_id'],'Successful authenticated HELLO')
    writes=[r for r in rf if r['kind']=='capacity_write']; require(writes,'Missing WTP writes')
    primary_tx,primary_write,primary_reply=selected[:3]
    require(held['monotonic_ns']<=primary_tx['monotonic_ns'] and
            0<=primary_tx['monotonic_ns']-sample['monotonic_ns']<=2_000_000_000 and
            sample['monotonic_ns']<primary_reply['monotonic_ns']<writes[-1]['monotonic_ns']<=final['monotonic_ns'] and
            writes[-1]['value']==dict(bytes=1,total_written=32784) and
            sum(r['value']['bytes'] for r in writes)==32784 and
            all(r['value']['total_written']<=32783 for r in writes[:-1]) and
            writes[-2]['value']['total_written']==32783, 'Actual resident overlap and withheld final byte')
    require(final['monotonic_ns']-tx['monotonic_ns']<=5_000_000_000,'Original whole WTP deadline')
    require(selected[3]['monotonic_ns']>final['monotonic_ns'],'Recovery follows WTP completion')
    return dict(mode=c['mode'],wtp_wire_bytes=32784,http_primary_status=primary_reply['value']['status'],
                http_declared_body_bytes=primary['declared_body_bytes'],http_offered_body_bytes=primary['offered_body_bytes'],
                observed_resident_delta_bytes=sample['value']['value']['wtp_input_reserved_bytes']-warm['value']['value']['wtp_input_reserved_bytes'],
                observed_heap_delta_bytes=sample['value']['value']['heap_allocated_bytes']-warm['value']['value']['heap_allocated_bytes'],
                wtp_exchange_ns=final['monotonic_ns']-tx['monotonic_ns'],
                resident_before_http_ns=primary_tx['monotonic_ns']-sample['monotonic_ns'],
                http_response_before_final_byte_ns=writes[-1]['monotonic_ns']-primary_reply['monotonic_ns'],
                authenticated_recovery=True)


def single(values, label):
    require(len(values)==1,'Exact count: '+label); return values[0]


def audit(root, expected):
    require(digest(root/'packet.json')==expected,'Frozen P2 packet')
    p=validate_profile(json.loads((root/'packet.json').read_text()))
    require(json.loads((root/'private-input-hashes.json').read_text())==p['private_reference_sha256'], 'Existing private input hashes')
    for name,sha in p['stage_sha256'].items():
        require(not name.startswith('credentials/') and name!='production.ini' and digest(root/name)==sha,'Executed public helper identity')
    result=audit_rf(root,packet_digest=expected);rf=journal(root/'rf.jsonl');load=journal(root/'contention.jsonl')
    allowed={'start','finish','native_status','combined_http_admission','combined_http_ready',
             'combined_recovery_admission','http_tx','http_write_complete','http_response'}
    require(all(r['kind'] in allowed for r in load) and load[0]['value']==dict(packet_sha256=expected,
            policy=p['contention']['policy'],binary_sha256=p['contention']['binary_sha256']), 'P2 native helper provenance')
    end=json.loads((root/'contention-result.json').read_text())
    require(end==load[-1]['value'] and end==dict(status='CAPTURED_REQUIRES_AUDIT',https_requests=2,native_exit=0),
            'Complete bounded native/HTTP run')
    metrics=overlap(p,rf,load)
    native,counts=native_wire(root,p,root/'pi/phase115_tls_observer_test.py')
    require(counts['connections']==1 and all(0<b['began']-a['began']<=6_000_000_000 for a,b in zip(native,native[1:])),
            'Continuous independent native connection')
    arm=single([r for r in rf if r['kind']=='arm_acknowledged'],'ARM')['monotonic_ns']
    load_began=single([r for r in rf if r['kind']=='wtp_tx' and r['value']['request']['op']=='LOAD'],'LOAD')['monotonic_ns']
    complete=single([r for r in rf if r['kind']=='job_complete'],'completion')['monotonic_ns']
    require(native[0]['ended']<arm and native[-1]['ended']>=complete-6_000_000_000,'Native coverage')
    for s in native:
        v=s['value'];require(v['boot_id']==p['boot_id'] and v['owner_id'] in (None,p['owner_id']) and
             (v['job_id'] in (None,p['jobs'][0]['job_id']) or
              (s['ended']<load_began and v['state']=='complete' and v['owner_id'] is None and v['job_id']==p['initial_a_job_id'])) and v['output_active'] is (v['state']=='running'),'Native ownership preserved')
    for rows in [rf,load]:
        selected=[r for r in rows if r['kind'] in ('capacity_tx','capacity_message','http_tx','http_response')]
        for r in selected:
            before=[s for s in native if s['ended']<=r['monotonic_ns']]
            after=[s for s in native if s['began']>=r['monotonic_ns']]
            require(before and after and r['monotonic_ns']-before[-1]['ended']<=6_000_000_000 and
                    after[0]['began']-r['monotonic_ns']<=6_000_000_000,'Native brackets around combined exchange')
            running(before[-1]['value'],p); running(after[0]['value'],p)
    result.update(status='P2_'+p['combined']['mode'].upper()+'_VERIFIED',combined=metrics,native=counts,
                  accepted_assertions=['2.2a' if p['combined']['mode']=='supported' else '2.2b'],
                  limitations=['One frozen simultaneous allocation profile; no P3 timeout or P5 reclamation credit.'])
    return result
