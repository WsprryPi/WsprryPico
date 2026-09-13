"""Raw A1g prerequisite diagnosis, including AP/DUT disagreement and normal expiry."""
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

PACKET='e512fac77302ee21f6fe7f9536d5c3215dcd997565770684906d4409cbdb0ed4'
JOURNAL='6b1095c7c30b52596a9772f706b8916d719f716e9ae1d553d1f6bb0a951dfe65'


def audit(root):
    require(digest(root/'packet.json')==PACKET, 'Different A1g packet')
    p=json.loads((root/'packet.json').read_text())
    for group in ('case_helper_sha256','production_helper_sha256'):
        for name,sha in p[group].items():require(digest(root/name)==sha, 'Executed helper changed')
    require(not (root/'tls-a1').exists() and not list(root.glob('wifi-*-exchange.jsonl'))
            and not list(root.glob('*-release.jsonl')), 'Unexpected RF/recovery/cleanup mutation')
    require(json.loads((root/'retained-result.json').read_text())==dict(status='FAILED',packet_sha256=PACKET,
            family_closed=False,error='ValueError: Retained network/clock did not converge',
            device_inactive_unowned=True,b_unchanged=True,host_restored=True,configuration_writes=0,flashes=0),
            'Different A1g disposition')
    order=['before-b','initial-terminal-before']+[f'network-ready-{i}' for i in range(25)]+['final-terminal-before','after-b']
    require({q.stem for q in root.glob('*.stdout')}==set(order)|{'baseline-reference','retained-time-admission'},
            'Missing or extra A1g inventory')
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
        if name.startswith('network-ready-'):
            n=value['info']['network']
            require(n['enabled'] is True and n['station_mac']=='88:a2:9e:0a:60:df' and not n['ipv4']
                    and n['link_status'] in (-3,-2,1) and value['wtp']['GET_CLOCK']['state']=='unsynchronized',
                    'Different readiness failure')
            readiness.append(dict(monotonic_ns=bounds[name][1],link_status=n['link_status'],enabled=True,
                                  ipv4='',clock_state='unsynchronized'))
    require(len(readiness)==25 and readiness[-1]['link_status']==-3 and
            readiness[-1]['monotonic_ns']-bounds['network-ready-0'][0]>=120_000_000_000, 'Incomplete readiness interval')
    require(json.loads((root/'retained-ap-identity.json').read_text())==dict(psk_matches_retained=True), 'Active AP input mismatch')
    host=json.loads((root/'fixture-state.json').read_text());trace=rows(root/'fixture.jsonl')
    require(host['restored'] is True and host['host_boot']==p['host_boot_id'] and
            next(r['value'] for r in trace if r['kind']=='host_restored')==host['before'] and
            next(r['value'] for r in trace if r['kind']=='cleanup')['failures']==[], 'Host restoration missing')
    validate_preserved(host['time_local_before'],next(r['value'] for r in trace if r['kind']=='time_local_after'))
    require(digest(root/'supplicant-journal.json')==JOURNAL, 'Supplemental AP journal changed')
    supplement=json.loads((root/'supplicant-journal.json').read_text());entries=supplement['entries']
    require(supplement['schema']=='phase11.5-supplicant-journal-v1' and supplement['exit']==0 and entries,
            'Missing AP journal')
    require(all(r['_BOOT_ID']==p['host_boot_id'].replace('-','') and
                r['_SYSTEMD_UNIT']=='wpa_supplicant.service' and r['_COMM']=='wpa_supplicant' for r in entries),
            'Foreign AP journal source')
    events={}
    for event in ('AP-STA-CONNECTED','EAPOL-4WAY-HS-COMPLETED','AP-STA-DISCONNECTED'):
        selected=[r for r in entries if r['MESSAGE']==f'wlan0: {event} 88:a2:9e:0a:60:df']
        require(len(selected)==1, 'Missing/repeated DUT authentication event')
        events[event]=int(selected[0]['__MONOTONIC_TIMESTAMP'])*1000
    require(bounds['initial-terminal-before'][1]<events['AP-STA-CONNECTED']<=events['EAPOL-4WAY-HS-COMPLETED']
            <bounds['network-ready-0'][0]<bounds['network-ready-24'][1]<events['AP-STA-DISCONNECTED'],
            'AP authentication does not bracket failed DUT readiness')
    return dict(classification='PRE_RF_AP_AUTHENTICATED_DUT_REPORTS_BADAUTH',packet_sha256=PACKET,
                accepted_assertions=0,submitted_jobs=0,completed_jobs=0,pressure_connections=0,
                inventories=len(values),readiness=readiness,ap_events_monotonic_ns=events,
                ap_journal_sha256=JOURNAL,root_cause='UNLOCALIZED_DEVICE_JOIN_STATE_OR_DRIVER_RADIO_EVENT_PATH',
                firmware_defect_confirmed=False,assistant_tooling_defect_confirmed=False,
                final_status=values['final-terminal-before']['wtp']['STATUS'],a_boot=BOOT,b_boot=p['initial_b_boot_id'],
                expired_terminal_jobs=expirations['final-terminal-before'],terminal_expiry_verified=True,
                configuration_writes=0,flashes=0,wifi_off=0,wifi_on=0,host_restored=True,
                limitations=['AP authentication success does not prove target IP readiness or isolate the radio/driver/application cause.',
                    'The pcap filter captured only mDNS/NTP; it cannot establish presence or absence of DHCP.',
                    'The supplemental station table was read after AP cleanup and cannot describe the live association.'])
