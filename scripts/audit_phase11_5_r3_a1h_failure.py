"""Raw A1h prerequisite diagnosis, including AP/DUT disagreement and normal expiry."""
import json
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_r3_retained import BOOT,terminal_admission
from phase11_5_r3_preflight import audit_inventory,decode_frame
from phase11_5_pilot_supervisor import idle,configuration,B_SERIAL,B_DEVICE
from phase11_5_time_local import validate_preserved
from phase11_5_terminal_history import retained_prior
from audit_phase11_5_r3_retained_failure import rows

PACKET='e59ee91202eb01622fa0185fb0cb2102612ba428edd2a616eeabd82b799e89a9'



def audit(root):
    require(digest(root/'packet.json')==PACKET, 'Different A1h packet')
    p=json.loads((root/'packet.json').read_text())
    for group in ('case_helper_sha256','production_helper_sha256'):
        for name,sha in p[group].items():require(digest(root/name)==sha, 'Executed helper changed')
    require(not (root/'tls-a1').exists() and not list(root.glob('wifi-*-exchange.jsonl'))
            and not list(root.glob('*-release.jsonl')) and not (root/'wifi-recovery.json').exists(), 'Unexpected RF/recovery/cleanup mutation')
    require(json.loads((root/'retained-result.json').read_text())==dict(status='FAILED',packet_sha256=PACKET,
            family_closed=False,error='ValueError: Unexpected recovery network state',
            device_inactive_unowned=True,b_unchanged=True,host_restored=True,configuration_writes=0,flashes=0),
            'Different A1h disposition')
    order=['before-b','initial-terminal-before']+[f'diagnostic-ready-{i}' for i in range(7)]+['wifi-recovery-admission']+['final-terminal-before','after-b']
    require({q.stem for q in root.glob('*.stdout')}==set(order)|{'baseline-reference','retained-time-admission'},
            'Missing or extra A1h inventory')
    values,bounds,requests={},{},set()
    for name in order:
        b=name.endswith('-b');trace=rows(root/(name+'.stdout'))
        values[name]=audit_inventory(root/(name+'.stdout'),dict(serial=B_SERIAL if b else p['serial'],
            device_id=B_DEVICE if b else p['device_id']),p['b_inventory_session_id'] if b else p['inventory_session_id'],
            p['case_helper_sha256']['scripts/phase11_5_inventory.py'])
        bounds[name]=trace[0]['monotonic_ns'],trace[-1]['monotonic_ns']
        for row in trace:
            if row['kind']=='tx' and bytes.fromhex(row['value']['hex'])!=b'INFO\n':
                q=decode_frame(bytes.fromhex(row['value']['hex']));key=q['session_id'],q['request_id']
                require(key not in requests, 'Cross-inventory replay');requests.add(key)
    require(all(bounds[a][1]<=bounds[b][0] for a,b in zip(order,order[1:])), 'Inventory chronology')
    baseline=values['initial-terminal-before'];initial=baseline['wtp']['STATUS']['terminal_records']
    expirations={};readiness=[]
    for name,value in values.items():
        idle(value)
        if name.endswith('-b'):
            require(value['wtp']['STATUS']['boot_id']==p['initial_b_boot_id'] and
                    configuration(value)==configuration(values['before-b']), 'B changed')
            continue
        require(terminal_admission(value,baseline,set()) is False, 'A is not Empty/inactive/unowned')
        require(value['wtp']['CAPS']==baseline['wtp']['CAPS'], 'CAPS changed')
        require(all(value['info'][k]==baseline['info'][k] for k in
                ('launch_epoch','dma_irqs','alarm_irqs','tail_irqs')), 'New RF in prerequisite failure')
        # Inventory protocol orders INFO before STATUS before GET_CLOCK. Their
        # target monotonic values bracket STATUS without assuming host clock rate.
        kept,expired=retained_prior(initial,value['wtp']['CAPS'],int(value['info']['status']['monotonic_now_ns']),
                                   int(value['wtp']['GET_CLOCK']['monotonic_now_ns']))
        require(value['wtp']['STATUS']['terminal_records']==kept, 'Terminal loss/change is not explained by source expiry')
        expirations[name]=[r['job_id'] for r in expired]
        if name.startswith('diagnostic-ready-') or name=='wifi-recovery-admission':
            n=value['info']['network']
            require(n['enabled'] is True and n['station_mac']=='88:a2:9e:0a:60:df' and not n['ipv4']
                    and n['link_status'] in (-3,-2,1) and value['wtp']['GET_CLOCK']['state']=='unsynchronized',
                    'Different readiness failure')
            readiness.append(dict(monotonic_ns=bounds[name][1],link_status=n['link_status'],enabled=True,
                                  ipv4='',clock_state='unsynchronized'))
    require([r['link_status'] for r in readiness]==[1,-3,-3,-3,-3,-3,1,1], 'Different transient admission sequence')
    require(json.loads((root/'retained-ap-identity.json').read_text())==dict(psk_matches_retained=True), 'Active AP input mismatch')
    host=json.loads((root/'fixture-state.json').read_text());trace=rows(root/'fixture.jsonl')
    require(host['restored'] is True and host['host_boot']==p['host_boot_id'] and
            next(r['value'] for r in trace if r['kind']=='host_restored')==host['before'] and
            next(r['value'] for r in trace if r['kind']=='cleanup')['failures']==[], 'Host restoration missing')
    validate_preserved(host['time_local_before'],next(r['value'] for r in trace if r['kind']=='time_local_after'))
    events={}
    for phase in ('before-recovery','before-host-cleanup'):
        value=json.loads((root/('ap-'+phase+'.json')).read_text())
        require(value['schema']=='phase11.5-live-ap-diagnostic-v1' and value['phase']==phase,
                'Wrong live AP phase')
        require(value['station']['exit']==0 and value['station']['stderr']=='' and
                value['station']['stdout'].startswith('Station 88:a2:9e:0a:60:df (on wlan0)\n') and
                all('\t'+k+':\tyes\n' in value['station']['stdout'] for k in ('authorized','authenticated','associated')),
                'Live AP does not prove DUT association')
        entries=value['entries']
        require(all(r['_BOOT_ID']==p['host_boot_id'].replace('-','') and
                    r['_SYSTEMD_UNIT']=='wpa_supplicant.service' and r['_COMM']=='wpa_supplicant' for r in entries),
                'Foreign live AP journal')
        for event in ('AP-STA-CONNECTED','EAPOL-4WAY-HS-COMPLETED'):
            found=[r for r in entries if r['MESSAGE']==f'wlan0: {event} 88:a2:9e:0a:60:df']
            require(len(found)==1, 'Missing/repeated DUT authentication event')
            stamp=int(found[0]['__MONOTONIC_TIMESTAMP'])*1000
            require(bounds['initial-terminal-before'][1]<stamp<bounds['diagnostic-ready-0'][0], 'AP authentication chronology')
            events[event]=stamp
        capture_rows=[r for r in trace if r['kind']=='ap_diagnostic_captured' and r['value']['phase']==phase]
        require(len(capture_rows)==1 and capture_rows[0]['monotonic_ns']<
                next(r['monotonic_ns'] for r in trace if r['kind']=='cleanup'), 'AP diagnostic was not collected before cleanup')
    return dict(classification='PRE_RF_TRANSIENT_JOINING_REJECTED_BY_HARNESS',packet_sha256=PACKET,
                accepted_assertions=0,submitted_jobs=0,completed_jobs=0,pressure_connections=0,
                inventories=len(values),readiness=readiness,ap_events_monotonic_ns=events,
                root_cause='HARNESS_REJECTED_PROGRESS_STATE; NETWORK_CAUSE_UNLOCALIZED',
                firmware_defect_confirmed=False,assistant_tooling_defect_confirmed=True,
                final_status=values['final-terminal-before']['wtp']['STATUS'],a_boot=BOOT,b_boot=p['initial_b_boot_id'],
                configuration_writes=0,flashes=0,wifi_off=0,wifi_on=0,host_restored=True,
                limitations=['The AP authenticated and associated the DUT, but the target IP/driver/radio failure remains unlocalized.',
                    'No DHCP packet was observed in the early AP capture; capture absence alone does not prove the target sent none.'])
