"""Raw R0a recovery audit, retaining its inhibited-comparator harness failure."""
import json
from pathlib import Path
from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_pilot import SERIAL, DEVICE
from phase11_5_pilot_supervisor import B_SERIAL, B_DEVICE
from phase11_5_r3_preflight import audit_inventory
from phase11_5_r3_v2_reconcile import admission, validate_final
from audit_phase11_5_idle import frames
from validate_wtp_contract import SchemaValidator

PACKET='951e45b570756b4ea640a3efcdd4a21d935a0256ae29aaf2a72b3af55a4a6a25'


def audit(root):
    packet_sha=digest(root/'packet.json')
    r0c=packet_sha in ['d7329b92520247345ecc7fd8ed6c8e6074217bb94a84a22c4db3060e874effec','b02bb43f2e231b9012915f5777051270515e0aa3fabca747c82844905be003e1','ec07a3f4909ed039d04dbafcb17b4c5ef6fe31d2de38f6dbc4f0cd35b23783e4',
        'ff9dfbe305085cbcf113c31011cf94870a4670e86d682824f2074b359f7b2eff',
        '26a82356596d845846b8c1145d883cd380d1051e57f84cc8ceb38adbd86163cf',
        '0141c9ae7c44bf8d74b720a64ec623cfa8c9217d92b0f0e8f4faac8459d81711']
    require(packet_sha==PACKET or r0c,'Frozen recovery packet')
    p=json.loads((root/'packet.json').read_text());values={}
    for label in (['before-a','after-a'] if r0c else ['before-a','before-b','after-a','after-b']):
        b=label.endswith('-b')
        values[label]=audit_inventory(root/(label+'.stdout'),dict(serial=B_SERIAL if b else SERIAL,device_id=B_DEVICE if b else DEVICE),
            p['b_session'] if b else p['inventory_session'],p['stage_sha256']['scripts/phase11_5_inventory.py'])
        require(not (root/(label+'.stderr')).read_bytes(),'Inventory stderr')
    require(admission(values['before-a'],p),'Expected known inactive Complete')
    for b in ([False] if r0c else [False,True]):
        suffix='b' if b else 'a'
        validate_final(values['after-'+suffix],values['before-'+suffix],p,b)
    text=(root/'reconcile.jsonl').read_text();require(text.endswith('\n'),'Truncated recovery journal')
    rows=[json.loads(s) for s in text.splitlines()]
    require(rows[0]['kind']=='start' and rows[0]['value']==dict(packet_sha256=packet_sha,needed=True) and
        rows[-1]['kind']=='finish' and rows[-1]['value']==dict(released=True) and
        all(a['monotonic_ns']<=b['monotonic_ns'] for a,b in zip(rows,rows[1:])) and
        all(r['kind'] in ['start','finish','wtp_tx','wtp_rx','wtp_message'] for r in rows),'Recovery journal envelope')
    schema=json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text())
    validator=SchemaValidator(schema);pending={};seen=set();wire=b'';messages=[];exchanges=[];events=[]
    for row in rows:
        kind,v,stamp=row['kind'],row['value'],row['monotonic_ns']
        if kind=='wtp_tx':
            decoded,left=frames(bytes.fromhex(v['hex']))
            require(not left and decoded==[v['request']],'Raw recovery request')
            q=decoded[0];token=q['request_id']
            require(not validator.errors(q,schema) and q['session_id']==p['peer_session'] and
                    token not in seen and not pending,'Recovery request identity/no retry')
            seen.add(token);pending[token]=(q,stamp)
        elif kind=='wtp_rx':
            decoded,wire=frames(wire+bytes.fromhex(v['hex']));messages.extend(decoded)
        elif kind=='wtp_message':
            require(messages and messages.pop(0)==v and not validator.errors(v,schema) and
                    v['session_id']==p['peer_session'],'Raw recovery response')
            if v['type']=='event':
                require(v['boot_id']==p['boot_id'],'Recovery event boot');events.append(v)
                continue
            require(v['ok'] is True and v['request_id'] in pending,'Recovery response match')
            q,began=pending.pop(v['request_id'])
            require(q['op']==v['op'] and 0<=stamp-began<=5_000_000_000,'Recovery response deadline')
            exchanges.append(dict(request=q,response=v))
    require(not pending and not messages and not wire,'Incomplete recovery wire')
    require([(e['event'],e['body']) for e in events]==[
        ('JOB_STATE',dict(job_id=None,state='empty',output_active=False)),
        ('OWNER_RELEASED',dict(owner_id=p['owner_id'],reason='released',output_active=False))] and
        int(events[1]['event_id'])==int(events[0]['event_id'])+1,'Exact idle recovery events')
    require([e['request']['op'] for e in exchanges]==['HELLO','STATUS','CLAIM','RELEASE','STATUS'],'Exactly one idle CLAIM/RELEASE')
    require(exchanges[1]['response']['body']==values['before-a']['wtp']['STATUS'] and
        exchanges[2]['request']['body']==dict(owner_id=p['owner_id'],lease_ms=60000) and
        exchanges[2]['response']['body']['owner_id']==p['owner_id'] and
        exchanges[3]['request']['body']=={} and
        exchanges[4]['response']['body']==values['after-a']['wtp']['STATUS'] and
        values['before-a']['wtp']['STATUS']['terminal_records']==values['after-a']['wtp']['STATUS']['terminal_records'],
        'Recovery authority, owner and retained history')
    r=json.loads((root/'result.json').read_text())
    require('error' not in r and r['rf_jobs']==r['rf_duration_ns_charged']==0 and
        r['claim_attempts']==r['release_attempts']==1 and r['after-a']==values['after-a']['wtp']['STATUS'],
        'Recovery accounting')
    if r0c:
        require(r['status']=='RECONCILED_INACTIVE_UNOWNED' and 'after-b' not in r and
            'after-b-error' not in r, 'A-only recovery completion')
    else:
        require(r['status']=='FAILED' and r['after-b-error']=="'launch_epoch'",'Original comparator-field failure retained')
    return dict(status='IDLE_RECONCILIATION_INDEPENDENTLY_VERIFIED',packet_sha256=packet_sha,
        source_revision=p['source_revision'],image_sha256=p['image_sha256'],boot_id=p['boot_id'],
        final_a=values['after-a']['wtp']['STATUS'],final_b=None if r0c else values['after-b']['wtp']['STATUS'],
        b_unchanged=None if r0c else True,configuration_unchanged=True,rf_counters_unchanged=True,rf_jobs=0,
        claim_attempts=1,release_attempts=1,
        original_runner_status=r['status'],preserved_finding=None if r0c else 'R0a assumed RF telemetry on the inhibited B image')
