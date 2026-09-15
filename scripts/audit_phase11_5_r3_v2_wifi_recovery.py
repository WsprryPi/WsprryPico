"""Independent raw inventory and Console audit for a finite idle Wi-Fi cycle."""
import json
from phase11_5_inventory import require,loads_console
from phase11_5_device_management import digest
from phase11_5_r3_v2_wifi_recovery import validate,idle,initial_link
from phase11_5_r3_preflight import audit_inventory


def audit(root,packet_sha):
    require(digest(root/'packet.json')==packet_sha,'Frozen recovery packet')
    p=validate(json.loads((root/'packet.json').read_text()));inventories={}
    if p.get('completion_recovery_policy'):
        for name,sha in p['stage_sha256'].items():
            require(digest(root/name)==sha,'Recovery executed helper identity')
        start=json.loads((root/'before-a.stdout').read_text().splitlines()[0])['monotonic_ns']
        require(start>=p['not_before_monotonic_ns'],'Recovery prerequisite duration')
    for path in sorted(root.glob('*.stdout')):
        label=path.stem;require(not path.with_suffix('.stderr').read_bytes(),'Inventory stderr')
        inventories[label]=audit_inventory(path,dict(serial=p['serial'],device_id=p['device_id']),
            p['inventory_session'],p['stage_sha256']['scripts/phase11_5_inventory.py'])
    baseline=inventories['before-a']
    for value in inventories.values():
        idle(value,baseline,p)
        require(all(value['info'][k]==baseline['info'][k] for k in ['launch_epoch','dma_irqs','alarm_irqs','tail_irqs']),
            'Recovery must not launch RF or change epochs')
    initial_link(baseline['info']['network'],p)
    for enabled,label in [(False,'off'),(True,'on')]:
        path=root/(label+'-exchange.jsonl');raw=path.read_bytes();require(raw.endswith(b'\n'),'Truncated recovery wire')
        rows=[json.loads(l) for l in raw.splitlines()];requests=[];responses=[];pending=None;buf=b'';start=None
        require(all(a['monotonic_ns']<=b['monotonic_ns'] for a,b in zip(rows,rows[1:])),'Recovery timestamps')
        for row in rows:
            data=bytes.fromhex(row['value']['hex'])
            if row['kind']=='tx':
                require(pending is None and not buf,'Overlapping recovery operation');pending=data;requests.append(data);start=row['monotonic_ns']
            else:
                require(row['kind']=='rx' and pending is not None,'Unsolicited recovery bytes');buf+=data
                if b'\n' in buf:
                    require(buf.endswith(b'\n') and buf.count(b'\n')==1 and row['monotonic_ns']-start<=5_000_000_000,
                        'Recovery response framing/deadline')
                    responses.append(loads_console(buf.decode().strip()));buf=b'';pending=None
        require(not buf and pending is None and requests==[b'INFO\n',b'WIFI ON\n' if enabled else b'WIFI OFF\n'] and
            len(responses)==2 and responses[1]==dict(ok=True),'Exactly one acknowledged transition')
        idle(dict(inventories[label+'-before'],info=responses[0]),baseline,p)
        after=[v for name,v in inventories.items() if name.startswith(label+'-after-')]
        require(after and any(v['info']['network']['enabled'] is enabled and
            v['info']['network']['requested_enabled'] is None and not v['info']['network']['withdrawal_pending'] for v in after),
            'Settled network transition')
    result=json.loads((root/'wifi-result.json').read_text());require(result['status']=='RECOVERED_REQUIRES_AUDIT' and
        result['off']==result['on']==1 and result['pending'] is None,'Recovery result accounting')
    final=inventories[result['final_inventory'].removesuffix('.stdout')]
    require(final['info']['network']['link_status']==3 and final['info']['network']['ipv4']=='10.77.15.10' and
        final['wtp']['GET_CLOCK']['state']=='synchronized','Authenticated target inventory IP/clock readiness')
    return dict(status='IDLE_WIFI_RECOVERY_VERIFIED',family_closed=False,packet_sha256=packet_sha,
        source_revision=p['source_revision'],image_sha256=p['image_sha256'],boot_id=p['boot_id'],wifi_cycles=1,
        off_commands=1,on_commands=1,configuration_writes=0,flashes=0,rf_jobs=0,
        final_authority=final['wtp']['STATUS'],final_clock=final['wtp']['GET_CLOCK'])
