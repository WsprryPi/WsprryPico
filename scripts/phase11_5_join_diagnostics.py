"""Bounded read-only AP evidence for an explicitly selected retained R3 packet."""
import json
from phase11_5_inventory import require

POLICY='ap-auth-dhcp-v1'
CAPTURE_FILTER='arp or udp port 67 or udp port 68 or udp port 5353 or udp port 123'


def selected(packet):
    value=packet.get('network_join_diagnostics')
    require(value is None or (value==POLICY and packet.get('schema')=='phase11.5-r3-retained-fixture-v1'
            and packet.get('family')=='R3' and packet.get('configuration_writes')==0),
            'Unreviewed network diagnostic scope')
    return value is not None


def select_journal(raw,host_boot,after_ns):
    entries=[]
    for line in raw.splitlines():
        value=json.loads(line)
        require(value['_BOOT_ID']==host_boot.replace('-','') and value['_SYSTEMD_UNIT']=='wpa_supplicant.service',
                'Foreign AP journal identity')
        if int(value['__MONOTONIC_TIMESTAMP'])*1000<after_ns or not value.get('MESSAGE','').startswith('wlan0:'):
            continue
        fields=('__MONOTONIC_TIMESTAMP','__REALTIME_TIMESTAMP','_BOOT_ID','_SYSTEMD_UNIT','_COMM','MESSAGE')
        entries.append({k:value[k] for k in fields})
    return entries


def capture(fixture,label):
    """Read only. The supervisor calls this before any AP cleanup."""
    require(label in ('before-recovery','before-host-cleanup'), 'Unknown AP diagnostic phase')
    trace=[json.loads(s) for s in (fixture.root/'fixture.jsonl').read_text().splitlines()]
    first=trace[0]
    command=['journalctl','-b','--since','@'+str(first['utc_ns']//10**9),
             '-u','wpa_supplicant.service','--no-pager','-o','json']
    result=fixture.cmd(command)
    entries=select_journal(result.stdout,fixture.state['host_boot'],first['monotonic_ns'])
    station=fixture.cmd(['iw','dev','wlan0','station','get','88:a2:9e:0a:60:df'],check=False)
    value=dict(schema='phase11.5-live-ap-diagnostic-v1',phase=label,journal_command=command,
               entries=entries,station=dict(exit=station.returncode,stdout=station.stdout,stderr=station.stderr))
    with (fixture.root/('ap-'+label+'.json')).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
    fixture.note('ap_diagnostic_captured',dict(phase=label,entries=len(entries),station_exit=station.returncode))
    return value
