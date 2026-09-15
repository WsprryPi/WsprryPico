"""Audit P1h's failed supported HTTP input and subsequent inactive restoration."""
import json
from pathlib import Path
from audit_phase11_5_idle import frames
from audit_phase11_5_r3_v2_hour import journal
from phase11_5_device_management import digest
from phase11_5_inventory import require, loads_console
from phase11_5_r3_preflight import audit_inventory
from phase11_5_r3_allocation_diagnostic import saved_configuration
from phase11_5_rf_reservation import BOARDS, inactive

PACKET = '6754555f69ac57fc5dae670cb37f3db1ea4fca5f3ce0590f8749c8c47cd92fdf'
RECOVERY_BOOT = 'cb429dd3964439e66e03bb0d93a9863b'


def audit(root):
    require(digest(root/'packet.json') == PACKET, 'Exact failed packet')
    p = json.loads((root/'packet.json').read_text())
    private = json.loads((root/'private-input-hashes.json').read_text())
    require(set(private) == {'production.ini'} | {
        'credentials/'+role+'/'+name for role in ('browser','controller')
        for name in ('client-ca.crt','client.crt','client.key')}, 'Private hash inventory')
    for name, sha in p['stage_sha256'].items():
        require((private[name] if name in private else digest(root/name)) == sha,
                'Executed input identity: '+name)
    values = {}
    for label in ('before-a','before-b','final-a','final-b','recovery-a','restored-a','restored-b'):
        b = label[-1]; serial, device = BOARDS[b]
        path = root/(label+'.stdout')
        raw = journal(path)
        # Additional read-only reconciliation has its own fresh session.
        session = next(frames(bytes.fromhex(r['value']['hex']))[0][0]['session_id']
                       for r in raw if r['kind']=='tx' and r['value']['hex'] != b'INFO\n'.hex())
        values[label] = audit_inventory(path, dict(serial=serial,device_id=device), session,
            p['stage_sha256']['scripts/phase11_5_inventory.py'])
        require(not path.with_suffix('.stderr').read_bytes(), 'Complete inventory')
    for b in BOARDS:
        for phase in ('final','restored'):
            require(saved_configuration(values[phase+'-'+b]) == saved_configuration(values['before-'+b]),
                    'Saved configuration preserved')
    require(values['before-b']['wtp']['STATUS'] == values['restored-b']['wtp']['STATUS'], 'B unchanged')
    require(values['before-a']['info']['revision'] == p['source_revision'][:12] and
            values['before-a']['wtp']['STATUS']['boot_id'] == p['boot_id'], 'Candidate identity')
    fault = dict(recovery_boot=True,fault_stage=14,fault_hash=3833354787,fault_pc=0,fault_status=0,
                 fault_allocation_recorded=True,fault_allocation_request_bytes=32769,
                 fault_allocation_returned_null=True)
    for label in ('final-a','recovery-a','restored-a'):
        v = values[label]
        require(v['info']['revision']==p['source_revision'][:12] and
                v['wtp']['STATUS']['boot_id']==RECOVERY_BOOT and
                all(v['info'][k]==expected for k,expected in fault.items()), 'Retained allocation fault/new boot')
    rows = journal(root/'rf.jsonl'); contention = journal(root/'contention.jsonl')
    require(rows[0]['value']['packet_sha256']==PACKET, 'Execution identity')
    tx, = [r for r in contention if r['kind']=='http_tx']
    require(tx['value']==p['http_capacity']['cases'][0], 'Exact maximum HTTP offer only')
    wire = bytes.fromhex(tx['value']['wire_hex']); header, body = wire.split(b'\r\n\r\n',1)
    require(b'Content-Length: 32768' in header and len(body)==32768 and
            json.loads(body)['operation']=='HELLO', 'Supported maximum request')
    written, = [r for r in contention if r['kind']=='http_write_complete']
    require(written['value']==dict(label='http-32768',bytes=len(wire)) and
            tx['monotonic_ns'] < written['monotonic_ns'] and
            not any(r['kind'] in ('http_rx','http_response','https_status') for r in contention),
            'Full client write without successful response')
    requests=[]; responses=[]; rx=b''; pending_info=None; console=b''; decoded=None; infos=[]
    for row in rows:
        kind,value=row['kind'],row['value']
        if kind=='wtp_tx':
            messages,left=frames(bytes.fromhex(value['hex']))
            require(not left and messages==[value['request']], 'USB request CRC/summary')
            requests.extend(messages)
        elif kind in ('wtp_rx','capacity_rx'):
            messages,rx=frames(rx+bytes.fromhex(value['hex']));responses.extend(messages)
        elif kind=='console_tx':
            require(pending_info is None and not console and decoded is None and
                    bytes.fromhex(value['hex'])==b'INFO\n', 'One solicited INFO')
            pending_info=row['monotonic_ns']
        elif kind=='console_rx':
            require(pending_info is not None, 'Solicited Console bytes')
            console+=bytes.fromhex(value['hex'])
            if console.endswith(b'\n'):
                require(console.count(b'\n')==1, 'INFO framing')
                decoded=loads_console(console.decode().strip());console=b'';pending_info=None
        elif kind=='info':
            require(decoded==value['value'], 'INFO raw/summary')
            infos.append(row);decoded=None
    require(not rx and responses==[r['value'] for r in rows if r['kind'] in ('wtp_message','capacity_message')], 'Response CRC/summaries')
    job,=p['jobs'];load,=[q for q in requests if q['op']=='LOAD'];arm,=[q for q in requests if q['op']=='ARM']
    require(load['body']==job and arm['body']['job_id']==job['job_id'], 'Exact finite job/single ARM')
    for q in (load,arm):
        reply,=[r for r in responses if r.get('type')=='response' and r.get('request_id')==q['request_id']]
        require(reply['ok'] is True and reply['session_id']==p['peer_session'] and
                reply['op']==q['op'] and reply['body']['job_id']==job['job_id'], 'Raw LOAD/ARM acknowledgement')
    last=infos[-1];i=last['value']['value']
    require(written['monotonic_ns'] < last['monotonic_ns'] and
            i['status']['state']=='running' and i['status']['output_active'] is True and
            i['status']['boot_id']==p['boot_id'], 'Fresh raw running observation after request write')
    require(pending_info is not None and not console and decoded is None, 'Preserved final unanswered INFO')
    result=json.loads((root/'rf-result.json').read_text())
    require(result==rows[-1]['value'] and result['status']=='STOPPED_FINAL_STATE_UNVERIFIED' and
            result['armed_jobs']==[job['job_id']] and result['completed_jobs']==[] and
            result['rf_duration_ns_charged']==128000000000, 'Preserved failed runner/full charge')
    for phase,name,state in [('before','acquired','HELD'),('final','released','RELEASED')]:
        r=json.loads((root/('rf-reservation-'+name+'.json')).read_text())
        require(r['packet_sha256']==PACKET and r['state']==state and
                r['boards']==inactive({b:values[phase+'-'+b] for b in BOARDS}), 'Reservation actual inactive authority')
    fr=root/'fixture-restoration';fp=json.loads((fr/'packet.json').read_text())
    require(digest(fr/'packet.json')=='11bd8abc8090433997f40d5fc8ad84b2e0921c5e79a35475e9932456bc0204ad', 'Fixture identity')
    state=json.loads((fr/'fixture-state.json').read_text())
    text=(fr/'fixture.jsonl').read_text();require(text.endswith('\n'), 'Complete fixture trace')
    trace=[json.loads(line) for line in text.splitlines()]
    require(all(a['monotonic_ns']<=b['monotonic_ns'] for a,b in zip(trace,trace[1:])), 'Fixture time order')
    cleanup=next(r for r in reversed(trace) if r['kind']=='cleanup')
    host=next(r for r in reversed(trace) if r['kind']=='host_restored')
    local=next(r for r in reversed(trace) if r['kind']=='time_local_after')
    require(state['restored'] is True and cleanup['value']['failures']==[] and
            cleanup['monotonic_ns']<435459994813000<fp['absolute_host_deadline_monotonic_ns'] and
            host['value']==state['before'], 'Early fixture restoration')
    before=state['time_local_before'];after=local['value']
    require(after['files']==before['files'] and after['addresses']==before['addresses'] and
            all(after['services'][k]['ActiveState']==v['ActiveState'] and
                after['services'][k]['UnitFileState']==v['UnitFileState'] for k,v in before['services'].items()) and
            'PPS' in after['tracking'] and 'Leap status     : Normal' in after['tracking'], 'Protected files/services/management/time')
    for b in BOARDS:
        require(journal(root/('restored-'+b+'.stdout'))[0]['monotonic_ns']>cleanup['monotonic_ns'], 'Post-restoration inventories')
    return dict(status='HTTP_ALLOCATION_FAILURE_AND_INACTIVE_RESTORATION_VERIFIED',packet_sha256=PACKET,
        source_revision=p['source_revision'],prior_boot=p['boot_id'],recovery_boot=RECOVERY_BOOT,
        accepted_components=[],package_complete=False,rf_jobs=1,planned_rf_seconds=128,
        unplanned_watchdog_reboots=1,http_request_bytes=len(wire),http_body_bytes=len(body),
        http_response_observed=False,fault=fault,last_running_info_monotonic_ns=last['monotonic_ns'],
        last_allocator_peak_bytes=i['allocator_peak_bytes'],boards=inactive({b:values['restored-'+b] for b in BOARDS}),
        saved_configurations_preserved=True,schedules_disabled=True,reservation_released=True,
        fixture_restored=True,fixture_cleanup_monotonic_ns=cleanup['monotonic_ns'],installed_pid=host['value']['installed_pid'],
        limitations=['The failed runner could not validate its original boot; fresh raw recovery inventories establish inactive authority.',
                     'The retained allocation size does not prove the exact allocation callsite or heap layout.',
                     'No HTTP capacity acceptance or RF completion credit.'])


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path)
    print(json.dumps(audit(parser.parse_args().root),indent=2))
