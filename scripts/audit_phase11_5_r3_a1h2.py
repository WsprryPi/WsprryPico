"""Independent A1h2 acceptance: initial TLS/slot subset, never full R3 closure."""
import json
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_r3_preflight import audit_inventory, decode_frame
from phase11_5_pilot_supervisor import idle, configuration, B_SERIAL, B_DEVICE
from phase11_5_time_local import validate_preserved
from audit_phase11_5_r3_a1e_failure import wifi_exchange, rows
from audit_phase11_5_r3_tls import audit as audit_tls

PACKET='474e315dee1d7ba7527105a8c34b572508536224be010d9133ec2aaf8998b0d3'


def audit(root):
    require(digest(root/'packet.json')==PACKET, 'Different A1h2 packet')
    p=json.loads((root/'packet.json').read_text())
    for group in ('case_helper_sha256','production_helper_sha256'):
        for name,sha in p[group].items():require(digest(root/name)==sha, 'Executed helper changed')
    require(p['observer_bracket_policy']=='request-cadence-and-roundtrip-v1' and
            p['network_join_diagnostics']=='ap-auth-dhcp-v1', 'Different approved policy')
    case=root/'tls-a1'
    rf=json.loads((case/'jobs.json').read_text())
    require(rf['jobs']==p['finite_job_templates'] and rf['observer_bracket_policy']==p['observer_bracket_policy'],
            'RF job/policy binding differs')
    result=audit_tls(case,root/'pi/phase115_tls_observer_test.py',baseline_path=root/'r3-a1-admission.stdout')
    require(result==json.loads((case/'audit.json').read_text()), 'Frozen/live raw audit disagrees')
    require(result['pressure']['status']=='PASS' and len(result['pressure']['cases'])==10 and
            result['completed_jobs']==2 and result['family_closed'] is False, 'Incomplete A1 subset')
    require(json.loads((root/'retained-result.json').read_text())==dict(status='PASS_REQUIRES_FINAL_REVIEW',
            packet_sha256=PACKET,family_closed=False,a1=result,device_inactive_unowned=True,
            b_unchanged=True,host_restored=True,configuration_writes=0,flashes=0), 'Final supervisor differs')
    order=['before-b','initial-terminal-before']+[f'diagnostic-ready-{i}' for i in range(7)]+[
        'wifi-recovery-admission','wifi-off-before','wifi-off-after-0','wifi-on-before','wifi-on-after-0',
        'network-ready-0','network-ready-1','r3-a1-admission','final-terminal-before','after-b']
    require({f.stem for f in root.glob('*.stdout')}==set(order)|{'baseline-reference','retained-time-admission'},
            'Missing/extra inventory')
    require({f.name for f in root.glob('wifi-*-exchange.jsonl')}=={'wifi-off-exchange.jsonl','wifi-on-exchange.jsonl'}
            and not list(root.glob('*-release.jsonl')), 'Extra Wi-Fi or cleanup mutation')
    values,bounds,requests={},{},set()
    for name in order:
        b=name.endswith('-b');trace=rows(root/(name+'.stdout'))
        value=audit_inventory(root/(name+'.stdout'),dict(serial=B_SERIAL if b else p['serial'],
            device_id=B_DEVICE if b else p['device_id']),p['b_inventory_session_id'] if b else p['inventory_session_id'],
            p['case_helper_sha256']['scripts/phase11_5_inventory.py'])
        idle(value);values[name]=value;bounds[name]=trace[0]['monotonic_ns'],trace[-1]['monotonic_ns']
        for row in trace:
            if row['kind']=='tx' and bytes.fromhex(row['value']['hex'])!=b'INFO\n':
                q=decode_frame(bytes.fromhex(row['value']['hex']));key=q['session_id'],q['request_id']
                require(key not in requests, 'Inventory replay');requests.add(key)
        if b:
            require(value['wtp']['STATUS']['boot_id']==p['initial_b_boot_id'] and
                    configuration(value)==configuration(values['before-b']), 'B changed')
        else:
            baseline=values['initial-terminal-before']
            require(value['wtp']['STATUS']['boot_id']==p['initial_a_boot_id'] and
                    configuration(value)==configuration(baseline) and value['wtp']['CAPS']==baseline['wtp']['CAPS'],
                    'A identity/configuration/CAPS changed')
            if name!='final-terminal-before':
                require(value['wtp']['STATUS']['terminal_records']==[] and
                        all(value['info'][k]==baseline['info'][k] for k in ('launch_epoch','dma_irqs','alarm_irqs','tail_irqs')),
                        'Unexpected pre-test RF/history')
    require(all(bounds[a][1]<=bounds[b][0] for a,b in zip(order,order[1:])), 'Inventory chronology')
    require(values['wifi-recovery-admission']['info']['network']['link_status'] in (-3,-2), 'Wrong recovery admission')
    require(json.loads((root/'wifi-recovery.json').read_text())==dict(status='CYCLE_COMPLETED_REJOIN_NOT_YET_PROVEN',off=1,on=1),
            'Recovery allowance changed')
    for label,enabled in (('off',False),('on',True)):
        path=root/('wifi-'+label+'-exchange.jsonl');wifi_exchange(path,enabled);trace=rows(path)
        require(bounds['wifi-'+label+'-before'][1]<=trace[0]['monotonic_ns']<=trace[-1]['monotonic_ns']<=
                bounds['wifi-'+label+'-after-0'][0], 'Wi-Fi command chronology')
        n=values['wifi-'+label+'-after-0']['info']['network']
        require(n['enabled'] is enabled and n['requested_enabled'] is None and not n['withdrawal_pending'],
                'Recovery transition unsettled')
    for name in ('network-ready-1','r3-a1-admission'):
        value=values[name]
        require(value['info']['network']['ipv4']=='10.77.15.10' and value['wtp']['GET_CLOCK']['state']=='synchronized',
                'RF preceded readiness')
    require(values['final-terminal-before']['wtp']['STATUS']['terminal_records']==result['usb']['terminal_records'],
            'Final history differs from raw observer')
    require(json.loads((root/'retained-ap-identity.json').read_text())==dict(psk_matches_retained=True), 'AP input mismatch')
    host=json.loads((root/'fixture-state.json').read_text());trace=rows(root/'fixture.jsonl')
    require(host['restored'] is True and host['host_boot']==p['host_boot_id'] and
            next(r['value'] for r in trace if r['kind']=='host_restored')==host['before'] and
            next(r['value'] for r in trace if r['kind']=='cleanup')['failures']==[], 'Host restoration missing')
    validate_preserved(host['time_local_before'],next(r['value'] for r in trace if r['kind']=='time_local_after'))
    for phase in ('before-recovery','before-host-cleanup'):
        value=json.loads((root/('ap-'+phase+'.json')).read_text())
        require(value['schema']=='phase11.5-live-ap-diagnostic-v1' and value['phase']==phase and
                value['station']['exit']==0 and value['station']['stdout'].startswith('Station 88:a2:9e:0a:60:df (on wlan0)\n'),
                'Missing live DUT station evidence')
        require(all(e['_BOOT_ID']==p['host_boot_id'].replace('-','') and
                    e['_SYSTEMD_UNIT']=='wpa_supplicant.service' for e in value['entries']), 'Foreign AP journal')
    return dict(status='PASS_A1_SUBSET',packet_sha256=PACKET,accepted_a1_pressure_cases=10,
                family_closed=False,completed_jobs=2,completed_rf_seconds=200,wifi_off=1,wifi_on=1,
                configuration_writes=0,flashes=0,host_restored=True,b_unchanged=True,
                final_status=values['final-terminal-before']['wtp']['STATUS'],raw_a1=result,
                limitation=result['pressure']['limitation'])
