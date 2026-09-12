#!/usr/bin/env python3
"""Offline R1 evidence audit; never accesses devices, services or networking."""
import argparse
import json
from pathlib import Path
from phase11_5_device_management import R1_SOURCE, digest
from phase11_5_inventory import require, loads_console
from phase11_5_pilot_supervisor import finished
from phase11_5_r1 import resources, matched_quiet, validate_fixture_dns, R1_HELPERS
from audit_phase11_5_idle import audit as audit_idle
from audit_phase11_5_load import audit as audit_load


def probe_exchange(path, size, outcome, boot):
    text=path.read_text();require(text.endswith('\n'),'Truncated probe exchange')
    rows=[json.loads(line) for line in text.splitlines()]
    require(rows and all(a['monotonic_ns']<=b['monotonic_ns'] for a,b in zip(rows,rows[1:])),
            'Probe exchange order')
    commands=[];responses=[];buffer=b'';stamp=None
    for row in rows:
        require(row['kind'] in ('tx','rx'),'Unexpected probe exchange event')
        data=bytes.fromhex(row['value']['hex'])
        if row['kind']=='tx':
            require(not buffer and len(commands)==len(responses),'Overlapping probe command')
            commands.append(data);stamp=row['monotonic_ns']
        else:
            require(len(commands)==len(responses)+1,'Unsolicited probe bytes')
            buffer+=data
            if b'\n' in buffer:
                require(buffer.endswith(b'\n') and buffer.count(b'\n')==1 and
                        0<=row['monotonic_ns']-stamp<=10e9,'Probe framing/deadline')
                responses.append(loads_console(buffer.decode().strip()));buffer=b''
    require(not buffer and commands==[b'INFO\n',f'HEAP PROBE {size}\n'.encode()] and
            len(responses)==2,'Incomplete/unexpected probe operation')
    info,reply=responses
    require(info['revision']==R1_SOURCE[:12] and info['status']['boot_id']==boot and
            info['status']['state']=='empty' and info['status']['output_active'] is False and
            reply.get('ok') is True and reply.get('allocated') is outcome,'Probe authority/outcome')
    return reply


def audit(root):
    packet=json.loads((root/'packet.json').read_text());result=json.loads((root/'r1-result.json').read_text())
    require(packet['family']=='R1' and packet['source_revision']==R1_SOURCE and packet['rf_jobs']==[] and
            result['source']==R1_SOURCE and result['status']=='CAPTURED_REQUIRES_FINAL_REVIEW' and
            result['rf_jobs']==[] and result.get('device_restored') is True,'R1 incomplete or scope changed')
    require(set(packet['case_helper_sha256'])==R1_HELPERS, 'Incomplete R1 helper identity set')
    validate_fixture_dns(json.loads((root/'fixture-dns-admission.json').read_text()))
    for relative,expected in {**packet['helper_sha256'],**packet['case_helper_sha256'],
                             **packet['production_helper_sha256']}.items():
        require((root/relative).resolve().is_relative_to(root) and digest(root/relative)==expected,
                'Evidence helper hash changed')
    intervals={}
    for kind,label,seconds,browser in (('inhibited','r1-inhibited',180,True),
        ('physical','r1-warm',180,True),('physical','r1-controller',180,False),
        ('physical','r1-normal',300,True)):
        target=root/('a2-'+kind+'-'+label+('-nominal' if browser else '-controller'))
        load=json.loads((target/'load.json').read_text())
        require(load['seconds']==seconds and load['browser'] is browser and load['browser_profile']=='N',
                'R1 workload profile changed')
        value=dict(usb=audit_idle(target/'usb-health.jsonl',root/(target.name+'-admission.stdout')),
                   load=audit_load(target,root/'pi/phase115_tls_observer_test.py'),
                   resources=resources(target/'usb-health.jsonl'))
        require(value==result['intervals'][label],'R1 load summary differs from raw audit')
        intervals[label]=value
    for label in ('r1-quiet-before','r1-quiet-after'):
        value=dict(usb=audit_idle(root/(label+'.jsonl'),root/(label+'-admission.stdout')),
                   resources=resources(root/(label+'.jsonl')))
        require(value['usb']['seconds']==360 and value==result['intervals'][label],
                'R1 quiet summary/length differs')
        intervals[label]=value
    require(set(intervals)==set(result['intervals']),'Missing/extra R1 intervals')
    pre=finished(root/'r1-before-probes.stdout','READ_ONLY_INVENTORY')['info']
    post=finished(root/'r1-after-probes.stdout','READ_ONLY_INVENTORY')['info']
    needed=max(intervals['r1-warm']['resources']['allocator_largest_successful_request_bytes'],
               pre['allocator_largest_successful_request_bytes'])
    require(int(pre['allocator_failures'])==0 and int(post['allocator_failures'])==1 and
            post['tls_allocation_failures']==pre['tls_allocation_failures']==0 and
            post['status']['boot_id']==pre['status']['boot_id'],'Probe recovery counters/boot')
    require(len(result['probes'])==3,'Missing/extra probe')
    for probe,(size,outcome) in zip(result['probes'],((needed,True),(pre['heap_capacity_bytes']+1,False),(needed,True))):
        require(probe['bytes']==size and probe['allocated'] is outcome,'Probe plan mismatch')
        expected=probe['management_result']
        candidates=[p for p in root.glob('management-*-exchange.jsonl') if digest(p)==expected['evidence_sha256']]
        require(len(candidates)==1,'Missing/ambiguous raw probe')
        require(probe_exchange(candidates[0],size,outcome,pre['status']['boot_id'])==expected['reply'],
                'Probe summary differs from raw Console')
    for label in ('r1-quiet-before','r1-controller','r1-normal','r1-quiet-after'):
        value=intervals[label]['resources']
        require(value['boot']==pre['status']['boot_id'] and value['clock_hz']==138000000 and
                int(value['last']['allocator_failures'])==1 and
                value['allocator_largest_successful_request_bytes']<=needed,
                'Changed physical identity/failure/necessary allocation after probe')
    delta=matched_quiet(intervals['r1-quiet-before']['resources'],intervals['r1-quiet-after']['resources'])
    require(delta==result['quiet_delta_bytes'],'Quiet delta differs')
    device=json.loads((root/'device-state.json').read_text())
    management=json.loads((root/'management-state.json').read_text())
    host=json.loads((root/'host-fixture-state.json').read_text())
    require(device.get('restored') is True and not device.get('pending') and
            not management.get('pending') and not management.get('blocked') and
            management['counts']=={'config':24,'wifi-off':0,'wifi-on':0,'heap-probe':3},
            'Device restoration/operation budget differs')
    # Host restoration uses its own saved state and independent verification log.
    require(host.get('restored') is True,'Host fixture not restored')
    return dict(family='R1',target_assertions='PASS',quiet_delta_bytes=delta,
                firmware=R1_SOURCE,physical_clock_hz=138000000,intervals=intervals,
                packet_sha256=digest(root/'packet.json'),rf_jobs=[])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path)
    print(json.dumps(audit(p.parse_args().root),indent=2))
