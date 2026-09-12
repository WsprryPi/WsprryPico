#!/usr/bin/env python3
"""Offline R1 evidence audit; never accesses devices, services or networking."""
import argparse
import json
from pathlib import Path
from phase11_5_device_management import R1_SOURCE, AMENDED_SOURCE, digest
from phase11_5_device_fixture import candidate_images
from phase11_5_inventory import require, loads_console
from phase11_5_pilot_supervisor import finished
from phase11_5_r1 import resources, matched_quiet, validate_fixture_dns, R1_HELPERS
from audit_phase11_5_idle import audit as audit_idle
from audit_phase11_5_load import audit as audit_load


def probe_exchange(path, size, outcome, boot, source=R1_SOURCE):
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
    require(source in (R1_SOURCE,AMENDED_SOURCE) and info['revision']==source[:12] and info['status']['boot_id']==boot and
            info['status']['state']=='empty' and info['status']['output_active'] is False and
            reply.get('ok') is True and reply.get('allocated') is outcome,'Probe authority/outcome')
    return reply


def usb_measurement_costs(path):
    """Raw audit is prerequisite; validate deadlines and report costs separately."""
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    pending = {}; costs = {'INFO': [], 'STATUS': [], 'HELLO': []}; loads = []; temperatures = []
    for row in rows:
        value = row['value']
        if row['kind'] == 'wtp_tx':
            pending[value['request']['request_id']] = (value['request']['op'], row['monotonic_ns'])
        elif row['kind'] == 'wtp_message' and value['type'] == 'response':
            operation, start = pending.pop(value['request_id'])
            costs[operation].append((row['monotonic_ns']-start)/1e9)
        elif row['kind'] == 'info':
            costs['INFO'].append((row['monotonic_ns']-value['began_monotonic_ns'])/1e9)
        elif row['kind'] == 'health':
            loads.append(float(value['value']['loadavg'].split()[0]))
            temperatures.append(int(value['value']['temperature'])/1000)
    require(not pending and all(values and all(0 <= n <= 5 for n in values) for values in costs.values()),
            'USB individual round-trip deadline or completeness')
    require(loads and temperatures, 'Missing host measurement-cost context')
    return dict(max_usb_roundtrip_seconds={key:max(values) for key,values in costs.items()},
                host_max_loadavg_1m=max(loads), host_max_temperature_c=max(temperatures),
                note='Load average is system-wide runnable/uninterruptible load, not CPU utilization. Costs overlap.')


def target_time_wire(root, kind):
    from phase11_5_time_local import capture_packets, dns_name, mdns_addresses
    start_name = 'before-network-reboot.stdout' if kind == 'inhibited' else 'before-physical-switch.stdout'
    start = json.loads((root/start_name).read_text().splitlines()[0])['utc_ns']
    ready = sorted(root.glob('r1-'+kind+'-ready-*.stdout'),key=lambda p:int(p.stem.split('-')[-1]))[-1]
    end = json.loads(ready.read_text().splitlines()[-1])['utc_ns']
    queries = []; answers = []; ntp_queries = []; ntp_replies = []
    for packet in capture_packets(root/'capture-ap.pcap'):
        if not start <= packet['utc_ns'] <= end: continue
        data = bytes.fromhex(packet['payload'])
        if packet['dport'] == 5353 and packet['source'] == '10.77.15.10' and len(data)>12 and not data[2]&128:
            name, _ = dns_name(data,12)
            if name == 'time.local': queries.append(packet)
        if packet['sport'] == 5353 and packet['source'] == '10.77.15.1' and len(data)>12 and data[2]&128:
            if '10.77.15.1' in mdns_addresses(data): answers.append(packet)
        if packet['dport'] == 123 and packet['source'] == '10.77.15.10' and packet['destination'] == '10.77.15.1':
            ntp_queries.append(packet)
        if packet['sport'] == 123 and packet['source'] == '10.77.15.1' and packet['destination'] == '10.77.15.10':
            ntp_replies.append(packet)
    require(queries and answers and any(q['utc_ns'] <= a['utc_ns'] for q in queries for a in answers),
            'Target mDNS wire exchange missing')
    matched = 0
    for query in ntp_queries:
        q = bytes.fromhex(query['payload'])
        for reply in ntp_replies:
            r = bytes.fromhex(reply['payload'])
            if (len(q) == len(r) == 48 and q[0] == 0x23 and r[0] == 0x24 and r[1] == 1 and
                r[12:16] == b'PPS\0' and r[24:32] == q[40:48] and any(r[40:48]) and
                query['sport'] == reply['dport'] and 0 <= reply['utc_ns']-query['utc_ns'] <= 3_000_000_000):
                matched += 1
    require(matched, 'Target matched-origin stratum 1/PPS NTP exchange missing')
    return dict(start_utc_ns=start,end_utc_ns=end,mdns_queries=len(queries),mdns_answers=len(answers),
                ntp_matched_exchanges=matched,target='10.77.15.10',server='10.77.15.1',name='time.local')


def audit(root):
    root = root.resolve(strict=True)
    packet=json.loads((root/'packet.json').read_text());result=json.loads((root/'r1-result.json').read_text())
    source=packet['source_revision']
    require(packet['family']=='R1' and source in (R1_SOURCE,AMENDED_SOURCE) and packet['rf_jobs']==[] and
            result['source']==source and result['status']=='CAPTURED_REQUIRES_FINAL_REVIEW' and
            result['rf_jobs']==[] and result.get('device_restored') is True,'R1 incomplete or scope changed')
    require(packet['images'] == {kind:dict(file=name,sha256=sha)
            for kind,(name,sha) in candidate_images(source).items()} and
            packet['selected_physical_clock_hz'] == 138000000 and packet['pio_divider'] == 1 and
            packet['rf_render_in_ram'] is True, 'Frozen R1 image/clock/layout identity differs')
    require(set(packet['case_helper_sha256'])==R1_HELPERS, 'Incomplete R1 helper identity set')
    if packet.get('time_server_mdns'):
        from phase11_5_time_local import validate_admission, validate_capture, validate_preserved
        require(packet.get('time_server_dns') is False and packet['time_server_dns_name'] == 'time.local',
                'R1 native mDNS packet changed')
        for side in ('ap', 'client'):
            require('0 packets dropped by kernel' in (root/('capture-'+side+'.log')).read_text(),
                    'Capture loss or missing capture stop record')
        for kind in ('inhibited', 'physical'):
            value = json.loads((root/('fixture-time-'+kind+'.stdout')).read_text())
            validate_admission(value)
            for side in ('ap', 'client'):
                validate_capture(root/('capture-'+side+'.pcap'), value)
            ready = sorted(root.glob('r1-'+kind+'-ready-*.stdout'),
                           key=lambda path: int(path.stem.split('-')[-1]))
            require(ready, 'Target time readiness evidence missing')
            observed = finished(ready[-1], 'READ_ONLY_INVENTORY')
            require(observed['wtp']['GET_CLOCK']['state'] == 'synchronized' and
                    observed['info']['network']['ntp_address'] == '10.77.15.1' and
                    observed['info']['network']['ntp_server'] == 'time.local' and
                    observed['info']['network']['ntp_resolution'] == 'resolved' and
                    observed['info']['network']['accepted'] > 0 and
                    observed['wtp']['STATUS']['boot_id'] == result['intervals'][
                        'r1-inhibited' if kind == 'inhibited' else 'r1-warm']['resources']['boot'],
                    'Target time.local readiness or workload boot differs')
        events = [json.loads(line) for line in (root/'fixture.jsonl').read_text().splitlines()]
        restored = [e['value'] for e in events if e['kind'] == 'time_local_after']
        host_state = json.loads((root/'host-fixture-state.json').read_text())
        require(restored, 'Permanent time.local restoration missing')
        validate_preserved(host_state['time_local_before'], restored[-1])
    else:
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
        require(probe_exchange(candidates[0],size,outcome,pre['status']['boot_id'],source)==expected['reply'],
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
    initial = packet.get('initial_management_counts', {'config':22,'wifi-off':0,'wifi-on':0,'heap-probe':0})
    expected_counts = dict(initial, config=initial['config']+2, **{'heap-probe':initial['heap-probe']+3})
    require(device.get('restored') is True and not device.get('pending') and
            not management.get('pending') and not management.get('blocked') and
            management['counts']==expected_counts,
            'Device restoration/operation budget differs')
    # Host restoration uses its own saved state and independent verification log.
    require(host.get('restored') is True,'Host fixture not restored')
    paths = {label: root/('a2-'+kind+'-'+label+('-nominal' if browser else '-controller'))/'usb-health.jsonl'
             for kind,label,browser in (('inhibited','r1-inhibited',True),('physical','r1-warm',True),
                                       ('physical','r1-controller',False),('physical','r1-normal',True))}
    paths.update({label:root/(label+'.jsonl') for label in ('r1-quiet-before','r1-quiet-after')})
    costs = {label:usb_measurement_costs(path) for label,path in paths.items()}
    time_wire = ({kind:target_time_wire(root,kind) for kind in ('inhibited','physical')}
                 if packet.get('time_server_mdns') else {})
    return dict(family='R1',target_assertions='PASS',measurement_details=costs,target_time_wire=time_wire,quiet_delta_bytes=delta,
                firmware=source,physical_clock_hz=138000000,intervals=intervals,
                packet_sha256=digest(root/'packet.json'),rf_jobs=[])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path)
    print(json.dumps(audit(p.parse_args().root),indent=2))
