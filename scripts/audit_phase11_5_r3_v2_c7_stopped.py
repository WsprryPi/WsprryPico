"""Reconstruct C7's pre-ARM failure; never grant RF or capacity acceptance."""
import json
from pathlib import Path
from phase11_5_inventory import require, loads_console
from phase11_5_device_management import digest
from phase11_5_r3_preflight import audit_inventory
from phase11_5_pilot_supervisor import configuration, B_SERIAL, B_DEVICE
from phase11_5_r3_v2_rf import validate, validate_info
from audit_phase11_5_idle import frames
from validate_wtp_contract import SchemaValidator

PACKET = '8cfcdfeef0c4513f24fe4dff64eaef1f62bbeaa4054c33d2d6720a3481e4b908'


def audit(root):
    root = Path(root)
    require(digest(root/'packet.json') == PACKET, 'Exact C7 packet')
    p = validate(json.loads((root/'packet.json').read_text()))
    inventories = {}
    for name in ['before-a', 'before-b', 'final-a', 'final-b']:
        b = name.endswith('-b')
        require(not (root/(name+'.stderr')).read_bytes(), 'Inventory stderr')
        v = audit_inventory(root/(name+'.stdout'),
            dict(serial=B_SERIAL if b else p['serial'], device_id=B_DEVICE if b else p['device_id']),
            p['b_session'] if b else p['inventory_session'],
            p['stage_sha256']['scripts/phase11_5_inventory.py'])
        s = v['wtp']['STATUS']
        require(s['boot_id'] == (p['b_boot_id'] if b else p['boot_id']) and
            s['state'] == v['info']['status']['state'] == 'empty' and
            s['output_active'] is v['info']['status']['output_active'] is False and
            s['owner_id'] is s['job_id'] is None, 'Final/initial inactive unowned identity')
        inventories[name] = v
    before, final = inventories['before-a'], inventories['final-a']
    require(configuration(before) == configuration(final), 'A configuration changed')
    b0, b1 = inventories['before-b'], inventories['final-b']
    require(configuration(b0) == configuration(b1) and b0['wtp']['STATUS'] == b1['wtp']['STATUS'] and
        b0['wtp']['CAPS'] == b1['wtp']['CAPS'] and
        b0['info']['revision'] == b1['info']['revision'], 'B changed')
    raw = (root/'rf.jsonl').read_text()
    require(raw.endswith('\n'), 'Truncated journal')
    rows = [json.loads(line) for line in raw.splitlines()]
    require([r['sequence'] for r in rows] == list(range(len(rows))) and
        all(a['monotonic_ns'] <= b['monotonic_ns'] for a,b in zip(rows,rows[1:])), 'Journal sequence')
    require(rows[0]['kind'] == 'start' and rows[0]['value'] == dict(packet_sha256=PACKET,
        baseline_sha256=digest(root/'before-a.stdout'), boot_id=p['boot_id'], seconds=300), 'Start identity')
    require(0 < rows[-1]['monotonic_ns']-rows[0]['monotonic_ns'] <= 450_000_000_000, 'Finite capture')
    result = json.loads((root/'rf-result.json').read_text())
    require(rows[-1]['kind'] == 'finish' and rows[-1]['value'] == result and
        result['status'] == 'STOPPED_REQUIRES_DIAGNOSIS' and result['armed_jobs'] == [] and
        result['completed_jobs'] == [] and result['renewals'] == 0 and result['rf_duration_ns_charged'] == 0,
        'Retain failed outcome and zero ARM')
    require(result['final-a'] == final['wtp']['STATUS'] and result['final-b'] == b1['wtp']['STATUS'],
        'Final result/raw disagreement')
    schema = json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text())
    validator = SchemaValidator(schema)
    console = b''; console_start = None; console_value = None
    wire = b''; messages = []; pending = None; seen = set(); requests = []; failures = []; infos = []
    status_value = None; load_stamp = None; claim = None
    allowed = {'start','finish','console_tx','console_rx','info','info_finish','health','health_finish',
        'wtp_tx','wtp_rx','wtp_message','status','status_finish','failure','contention_starting'}
    for r in rows:
        k,v,t = r['kind'],r['value'],r['monotonic_ns']
        require(k in allowed, 'Undeclared action or RF/capacity stimulus')
        if k == 'console_tx':
            require(console_start is None and not console and console_value is None and
                bytes.fromhex(v['hex']) == b'INFO\n', 'Console command')
            console_start = t
        elif k == 'console_rx':
            require(console_start is not None, 'Unsolicited Console')
            console += bytes.fromhex(v['hex'])
            if b'\n' in console:
                require(console.endswith(b'\n') and console.count(b'\n') == 1 and
                    t-console_start <= 5_000_000_000, 'Console deadline/framing')
                console_value = loads_console(console.decode().strip()); console = b''; console_start = None
        elif k == 'info':
            require(console_value == v['value'] and 0 <= t-v['began_monotonic_ns'] <= 5_000_000_000,
                'Raw INFO disagreement/deadline')
            validate_info(console_value,before,p)
            require(console_value['status']['output_active'] is False and
                all(int(console_value[key]) == 0 for key in ['launch_epoch','dma_irqs','alarm_irqs','tail_irqs']),
                'Unexpected RF')
            infos.append(r); console_value = None
        elif k == 'wtp_tx':
            decoded,left = frames(bytes.fromhex(v['hex']))
            require(not left and decoded == [v['request']] and pending is None, 'Raw request/overlap')
            q = decoded[0]
            require(not validator.errors(q,schema) and q['session_id'] == p['peer_session'] and
                q['request_id'] not in seen and q['op'] in ['HELLO','STATUS','CLAIM','LOAD'], 'Request scope/schema')
            seen.add(q['request_id']); requests.append(q); pending = (t,q)
            if q['op'] == 'LOAD':
                require(load_stamp is None and q['body'] == p['jobs'][0], 'Exact single LOAD')
                load_stamp = t
        elif k == 'wtp_rx':
            require(load_stamp is None, 'Unexpected response bytes after LOAD')
            decoded,wire = frames(wire+bytes.fromhex(v['hex'])); messages.extend(decoded)
        elif k == 'wtp_message':
            require(messages and messages.pop(0) == v and not validator.errors(v,schema) and
                v['session_id'] == p['peer_session'] and v['type'] == 'response' and v['ok'] is True and
                pending is not None and v['request_id'] == pending[1]['request_id'] and
                v['op'] == pending[1]['op'] and t-pending[0] <= 5_000_000_000, 'Raw response disagreement')
            if v['op'] == 'HELLO':
                require(v['body']['device_id'] == p['device_id'] and v['body']['boot_id'] == p['boot_id'], 'HELLO identity')
            if v['op'] == 'STATUS':status_value = v['body']
            if v['op'] == 'CLAIM':
                claim = v['body']; require(claim['owner_id'] == p['owner_id'], 'CLAIM identity')
            pending = None
        elif k == 'status':
            require(status_value == v['value'] and status_value['boot_id'] == p['boot_id'] and
                status_value['state'] == 'empty' and status_value['output_active'] is False,
                'Raw STATUS disagreement'); status_value = None
        elif k == 'health':
            require(v['value']['boot'] == p['host_boot_id'] and v['value']['throttled'] == 'throttled=0x0', 'Host health')
        elif k == 'failure':
            op = ['LOAD','STATUS'][len(failures)] if len(failures) < 2 else None
            require(op and pending is not None and pending[1]['op'] == op and
                v['type'] == 'TimeoutError' and v['error'] == op+' response timeout; no automatic retry; output unknown' and
                5_000_000_000 <= t-pending[0] <= 6_000_000_000, 'Exact unretried timeout')
            failures.append(v); pending = None
    require(len(failures) == 2 and not pending and not wire and not messages and
        not console and console_start is None and console_value is None and status_value is None, 'Incomplete reconstruction')
    require([q['op'] for q in requests].count('CLAIM') == 1 and
        [q['op'] for q in requests][-3:] == ['CLAIM','LOAD','STATUS'], 'One claim/load and final read')
    require(infos and infos[0]['monotonic_ns']-rows[0]['monotonic_ns'] <= 2_000_000_000 and
        rows[-1]['monotonic_ns']-infos[-1]['monotonic_ns'] <= 5_000_000_000 and
        all(0 < b['value']['began_monotonic_ns']-a['value']['began_monotonic_ns'] <= 2_000_000_000
            for a,b in zip(infos,infos[1:])), 'Independent INFO continuity')
    require(result['faults'] == ['wtp action: '+failures[0]['error'], 'wtp: '+failures[1]['error'],
        'supervisor: Nominal contention completion'], 'Failure summary disagreement')
    loaded = [r for r in infos if r['value']['value']['status']['state'] == 'loaded']
    require(loaded and loaded[0]['monotonic_ns'] > load_stamp and claim is not None, 'Device accepted LOAD state')
    terminal = [r for r in final['wtp']['STATUS']['terminal_records'] if r['job_id'] == p['jobs'][0]['job_id']]
    require(len(terminal) == 1 and terminal[0]['state'] == 'aborted' and terminal[0]['output_active'] is False and
        int(terminal[0]['ended_monotonic_ns']) >= int(claim['expires_monotonic_ns']), 'Loaded lease-expiry result')
    validate_info(final['info'],before,p)
    values = [r['value']['value'] for r in infos]+[before['info'],final['info']]
    return dict(status='C7_PRE_ARM_LOAD_REPLY_FAILURE_VERIFIED',acceptance_pass=False,newly_closed_assertions=[],
        packet_sha256=PACKET,source_revision=p['source_revision'],image_sha256=p['image_sha256'],boot_id=p['boot_id'],
        rf_jobs_charged=0,rf_seconds_charged=0,maximum_input_exchanges=0,load_request_wire_bytes=len(bytes.fromhex(
            next(r['value']['hex'] for r in rows if r['kind']=='wtp_tx' and r['value']['request']['op']=='LOAD'))),
        load_response_bytes=0,first_failure=failures[0]['error'],info_samples=len(infos),allocator_failures=0,
        allocator_peak_bytes=max(v['allocator_peak_bytes'] for v in values),heap_capacity_bytes=final['info']['heap_capacity_bytes'],
        core0_stack_used_bytes=max(v['core0_stack_used_bytes'] for v in values),
        core1_stack_used_bytes=max(v['core1_stack_used_bytes'] for v in values),
        final_a=final['wtp']['STATUS'],b_unchanged=True,
        cause='UNRESOLVED: LOAD reply reserve refusal is a source-based hypothesis, not a captured branch.')
