#!/usr/bin/env python3
"""Offline classification of the preserved R2 miss; never an RF acceptance pass."""
import argparse
import hashlib
import json
from pathlib import Path
from audit_phase11_5_idle import frames
from phase11_5_inventory import require, loads_console
from phase11_5_release_missed import admit, BOOT, JOB
from phase11_5_device_fixture import configuration
from phase11_5_time_local import validate_preserved


def rows(path):
    raw = path.read_text()
    require(raw.endswith('\n'), 'Truncated evidence')
    return [json.loads(line) for line in raw.splitlines()]


def inventory(path):
    data = rows(path)
    require(data[0]['kind'] == 'start' and data[-1]['kind'] == 'finish', 'Inventory endpoints')
    require([x['sequence'] for x in data] == list(range(len(data))), 'Inventory sequence')
    console = b''; wire = b''; requests = []; responses = []; reported = []; info = None
    console_mode = True
    for row in data:
        kind, value = row['kind'], row['value']
        if kind == 'tx':
            raw = bytes.fromhex(value['hex'])
            if raw == b'INFO\n':
                require(not requests and not console, 'Repeated INFO')
            else:
                console_mode = False
                decoded, left = frames(raw)
                require(not left and len(decoded) == 1, 'Inventory request framing')
                requests.extend(decoded)
        elif kind == 'rx':
            raw = bytes.fromhex(value['hex'])
            if console_mode:
                console += raw
            else:
                decoded, wire = frames(wire + raw); responses.extend(decoded)
        elif kind == 'info':
            info = loads_console(console.decode().strip())
            require(info == value, 'Reported Console differs from raw')
        elif kind == 'response':
            reported.append(value)
    require(not wire and responses == reported and len(requests) == len(responses), 'Raw inventory mismatch')
    require([q['op'] for q in requests] == ['HELLO','CAPS','GET_CLOCK','STATUS','PING'], 'Inventory scope')
    require(len({q['request_id'] for q in requests}) == 5, 'Inventory request reuse')
    for q, r in zip(requests, responses):
        require(r['ok'] is True and all(q[k] == r[k] for k in ('request_id','session_id','op')), 'Inventory response binding')
    result = dict(result='READ_ONLY_INVENTORY', info=info, wtp={r['op']:r['body'] for r in responses})
    require(result == data[-1]['value'], 'Inventory finish differs from wire')
    return result


def audit(root):
    require(hashlib.sha256((root/'packet.json').read_bytes()).hexdigest() ==
            'e0c01e66189f2d295a38d6e1a294b32e1c2c5e78c56088a1371db9038d48b2e2', 'Frozen packet identity')
    actor = rows(root/'r2-tone/browser-jobs.jsonl')
    require([x['sequence'] for x in actor] == list(range(len(actor))), 'Actor sequence')
    intents = [x['value'] for x in actor if x['kind'] == 'request_intent']
    replies = [x['value'] for x in actor if x['kind'] == 'response']
    require([x['request']['operation'] for x in intents] == ['HELLO','CLAIM','LOAD','ARM'], 'Unexpected RF actions')
    require(len(replies) == 4 and actor[-1]['kind'] == 'failure', 'Actor incomplete failure')
    for q, r in zip(intents, replies):
        wire = bytes.fromhex(q['wire_hex']).split(b'\r\n\r\n', 1)[1]
        body = json.loads(bytes.fromhex(r['body_hex']))
        require(json.loads(wire) == q['request'] and r['http_status'] == 200 and body['ok'] is True and
                q['request']['request_id'] == r['request_id'] == body['request_id'], 'Browser raw correlation')
    require(intents[2]['request']['body'] == actor[0]['value']['packet']['jobs'][0] and
            intents[2]['request']['body']['job_id'] == JOB and
            intents[3]['request']['body']['job_id'] == JOB, 'Job identity')
    missed = inventory(root/'missed-reconciliation-a.stdout')
    admit(missed, missed['wtp']['STATUS'])
    release = rows(root/'missed-release.jsonl'); sent=[]; received=[]; wire=b''
    for x in release:
        if x['kind'] == 'wtp_tx':
            decoded,left=frames(bytes.fromhex(x['value']['hex']))
            require(not left and decoded == [x['value']['request']], 'Retirement request wire')
            sent.extend(decoded)
        elif x['kind'] == 'wtp_rx':
            decoded,wire=frames(wire+bytes.fromhex(x['value']['hex']));received.extend(decoded)
    events=[r for r in received if r['type']=='event']
    require([e['event'] for e in events]==['JOB_STATE','OWNER_RELEASED'] and
            all(e['body']['output_active'] is False for e in events), 'Retirement events')
    received=[r for r in received if r['type']=='response']
    require(not wire and [q['op'] for q in sent] == ['HELLO','STATUS','CLAIM','RELEASE','STATUS'] and
            len(received) == 5, 'Retirement scope')
    for q,r in zip(sent,received):
        require(r['ok'] is True and all(q[k] == r[k] for k in ('request_id','session_id','op')), 'Retirement response binding')
    before=received[1]['body']; after=received[-1]['body']
    require(before == missed['wtp']['STATUS'] and after == dict(boot_id=BOOT,state='empty',output_active=False,
            owner_id=None,job_id=None,terminal_records=before['terminal_records']), 'Retirement altered terminal record')
    require(inventory(root/'missed-release-after.stdout')['wtp']['STATUS'] == after, 'Retirement final inventory')
    a=inventory(root/'restored-original-boot.stdout'); b=inventory(root/'after-b.stdout')
    before_a=inventory(root/'before-a.stdout'); before_b=inventory(root/'before-b.stdout')
    for final, original in ((a,before_a),(b,before_b)):
        status=final['wtp']['STATUS']
        require(status['state']=='empty' and status['output_active'] is False and status['owner_id'] is None and
                status['job_id'] is None and final['info']['revision']==original['info']['revision'] and
                configuration(final)==configuration(original), 'Device restoration')
    require(b['wtp']['STATUS']['boot_id']==before_b['wtp']['STATUS']['boot_id'], 'Pico B changed boot')
    final=json.loads((root/'final-restoration.json').read_text())
    require(final['a_status']==a['wtp']['STATUS'] and final['b_status']==b['wtp']['STATUS'] and
            final['configurations_match'] is True and final['management_counts']==
            {'config':28,'wifi-off':0,'wifi-on':0,'heap-probe':3}, 'Final identity or management counts')
    fixture=json.loads((root/'fixture-state.json').read_text())
    validate_preserved(fixture['time_local_before'],json.loads((root/'permanent-final-verification.json').read_text()))
    log=rows(root/'fixture.jsonl')
    require(fixture['restored'] is True and log[-1]['kind']=='cleanup' and log[-1]['value']['failures']==[] and
            [x['value']['installed_pid'] for x in log if x['kind']=='host_restored']==['1957'], 'Host restoration')
    return dict(classification='VERIFIED_MISSED_START_NOT_ACCEPTED',family_closed=False,completed_jobs=0,
                missed_jobs=1,not_run_jobs=6,launch_observed=False,
                alarm_callback_duration_ns=int(missed['info']['max_alarm_irq_ns']),
                electrical_start_delay_ns=None,terminal_record_preserved_before_restore=True,
                devices_restored=True,host_restored=True,configuration_writes=28)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path)
    print(json.dumps(audit(p.parse_args().root),indent=2))
