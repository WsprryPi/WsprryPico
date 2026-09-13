"""Offline raw reconstruction of A1c's pre-RF rejoin failure, never R3 acceptance."""
import json
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_pilot import Decoder, SERIAL, DEVICE
from phase11_5_pilot_supervisor import idle, configuration, B_SERIAL, B_DEVICE
from phase11_5_r3_preflight import audit_inventory, decode_frame
from phase11_5_r3_retained import BOOT, PRIOR_JOB, terminal_admission
from phase11_5_time_local import validate_preserved
from validate_wtp_contract import SchemaValidator

PACKET = '3167ff5d4c9e58b908ed0d5fcb64a278454a236857f5442ec0662e1e66fc5156'


def rows(path):
    raw = path.read_text()
    require(raw.endswith('\n'), 'Truncated retained evidence')
    result = [json.loads(s) for s in raw.splitlines()]
    require(result and all(type(r['monotonic_ns']) is int for r in result) and
            all(a['monotonic_ns'] <= b['monotonic_ns'] for a, b in zip(result, result[1:])),
            'Retained evidence chronology')
    return result


def cleanup(path, packet, before, after):
    trace = rows(path)
    require(trace[-1]['monotonic_ns'] - trace[0]['monotonic_ns'] <= 30_000_000_000,
            'Cleanup exceeded deadline')
    schema = json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text())
    validator, decoder = SchemaValidator(schema), Decoder()
    requests, replies, events, queued = [], [], [], []
    pending, began, session = None, None, None
    seen_ids = set()
    for r in trace:
        k, v = r['kind'], r['value']
        if k == 'wtp_tx':
            # A complete response may be followed by a partial asynchronous
            # event in the same USB read. Peer retains that suffix across the
            # next request; final framing/event checks still must consume it.
            require(pending is None and not queued, 'Overlapping cleanup request')
            request = decode_frame(bytes.fromhex(v['hex']))
            require(request == v['request'] and not validator.errors(request, schema), 'Cleanup request bytes/schema')
            if session is None: session = request['session_id']
            require(request['session_id'] == session and request['request_id'] not in seen_ids,
                    'Cleanup session or replay changed')
            seen_ids.add(request['request_id']); requests.append(request); pending = request; began = r['monotonic_ns']
        elif k == 'wtp_rx':
            require(pending is not None, 'Unsolicited cleanup bytes')
            queued.extend(decoder.feed(bytes.fromhex(v['hex'])))
        elif k == 'wtp_message':
            require(queued and queued.pop(0) == v and not validator.errors(v, schema)
                    and v['session_id'] == session, 'Cleanup summary differs from wire/schema')
            if v['type'] == 'event':
                require(v['boot_id'] == BOOT and v['body']['output_active'] is False, 'Cleanup event output/boot')
                events.append((v['event'], v['body']))
            else:
                require(pending is not None and v['ok'] is True and
                        all(v[k] == pending[k] for k in ('request_id', 'op', 'protocol')) and
                        r['monotonic_ns'] - began <= 5_000_000_000, 'Cleanup response binding/deadline')
                replies.append(v['body']); pending = None
        else: raise ValueError('Unexpected cleanup traffic')
    require(pending is None and not queued and not decoder.buffer, 'Incomplete cleanup exchange')
    require([r['op'] for r in requests] == ['HELLO', 'STATUS', 'CLAIM', 'RELEASE', 'STATUS'],
            'Cleanup contains forbidden/missing operation')
    require([r['body'] for r in requests] == [dict(versions=['WTP/1'], client_name='r3-terminal-cleanup',
            client_version='1'), {}, dict(owner_id=packet['cleanup_owner_id'], lease_ms=60000), {}, {}],
            'Cleanup operation body changed')
    require(replies[0]['device_id'] == DEVICE and replies[0]['boot_id'] == BOOT and
            replies[1] == before['wtp']['STATUS'] and replies[4] == after['wtp']['STATUS'] and
            replies[2]['owner_id'] == packet['cleanup_owner_id'] and replies[2]['granted_lease_ms'] == 60000 and
            replies[3] == {} and replies[1]['terminal_records'] == replies[4]['terminal_records'],
            'Cleanup did not preserve terminal history and identity')
    require(events == [('JOB_STATE', dict(job_id=None, state='empty', output_active=False)),
            ('OWNER_RELEASED', dict(owner_id=packet['cleanup_owner_id'], reason='released', output_active=False))],
            'Cleanup event sequence changed')
    return trace[0]['monotonic_ns'], trace[-1]['monotonic_ns']


def audit(root):
    require(digest(root/'packet.json') == PACKET, 'Wrong retained failure packet')
    p = json.loads((root/'packet.json').read_text())
    for name, sha in p['case_helper_sha256'].items():
        require(digest(root/name) == sha, 'Executed helper changed')
    require(digest(root/'baseline-reference.stdout') == p['private_input_sha256']['baseline-reference.stdout'],
            'Retained baseline reference changed')
    require(not (root/'tls-a1').exists() and not list(root.glob('wifi-*-exchange.jsonl')),
            'Pre-RF failure has later execution/mutation evidence')
    order = ['before-b', 'initial-terminal-before', 'initial-terminal-after'] + [
        'network-ready-' + str(i) for i in range(25)] + ['final-terminal-before', 'after-b']
    # Staged private baseline and the time-admission subprocess are separate artifacts.
    require({f.stem for f in root.glob('*.stdout')} == set(order) | {
            'baseline-reference', 'retained-time-admission'}, 'Missing or unexpected capture')
    values, bounds, seen_requests = {}, {}, set()
    for name in order:
        b = name.endswith('-b'); session = p['b_inventory_session_id'] if b else p['inventory_session_id']
        path = root/(name + '.stdout'); raw = rows(path)
        values[name] = audit_inventory(path, dict(serial=B_SERIAL if b else SERIAL,
            device_id=B_DEVICE if b else DEVICE), session, p['case_helper_sha256']['scripts/phase11_5_inventory.py'])
        bounds[name] = raw[0]['monotonic_ns'], raw[-1]['monotonic_ns']
        for r in raw:
            if r['kind'] == 'tx' and bytes.fromhex(r['value']['hex']) != b'INFO\n':
                q = decode_frame(bytes.fromhex(r['value']['hex']))
                identity = q['session_id'], q['request_id']
                require(identity not in seen_requests, 'Cross-capture replay')
                seen_requests.add(identity)
    require(all(bounds[a][1] <= bounds[b][0] for a, b in zip(order, order[1:])), 'Capture order changed')
    baseline = values['initial-terminal-after']
    require(terminal_admission(values['initial-terminal-before'], baseline, {PRIOR_JOB}), 'Missing prior terminal')
    cleanup_bounds = cleanup(root/'initial-terminal-release.jsonl', p, values['initial-terminal-before'], baseline)
    require(bounds['initial-terminal-before'][1] <= cleanup_bounds[0] <= cleanup_bounds[1] <=
            bounds['initial-terminal-after'][0], 'Cleanup outside authoritative brackets')
    for name, value in values.items():
        if name.endswith('-b'):
            idle(value)
            require(value['wtp']['STATUS']['boot_id'] == p['initial_b_boot_id'] and
                    configuration(value) == configuration(values['before-b']), 'B changed')
        elif name != 'initial-terminal-before':
            require(terminal_admission(value, baseline, {PRIOR_JOB}) is False, 'A not Empty/inactive/unowned')
            for key in ('launch_epoch', 'dma_irqs', 'alarm_irqs', 'tail_irqs'):
                require(value['info'][key] == baseline['info'][key], 'New RF activity in pre-RF failure')
    network = [values['network-ready-' + str(i)]['info']['network'] for i in range(25)]
    require(all(n['enabled'] is True and n['link_status'] in (-2, -3, 1) and not n['ipv4'] for n in network)
            and network[-1]['link_status'] == -3, 'Different network failure')
    require(bounds['network-ready-24'][1] - bounds['network-ready-0'][0] >= 120_000_000_000,
            'Readiness window shortened')
    require(all(values['network-ready-' + str(i)]['wtp']['GET_CLOCK']['state'] == 'unsynchronized'
                for i in range(25)), 'Unexpected synchronized readiness')
    result = json.loads((root/'retained-result.json').read_text())
    require(result == dict(status='FAILED', packet_sha256=PACKET, family_closed=False,
            error='ValueError: Retained network/clock did not converge', device_inactive_unowned=True,
            b_unchanged=True, host_restored=True, configuration_writes=0, flashes=0), 'Failure disposition changed')
    host = json.loads((root/'fixture-state.json').read_text()); trace = rows(root/'fixture.jsonl')
    require(host['restored'] is True and host['host_boot'] == p['host_boot_id'], 'Host not restored')
    clean = [r for r in trace if r['kind'] == 'cleanup']
    require(len(clean) == 1 and clean[0]['value']['failures'] == [], 'Host cleanup failure')
    restored = next(r['value'] for r in trace if r['kind'] == 'host_restored')
    require(restored == host['before'] and restored['installed_pid'] == '1957', 'Host identity changed')
    validate_preserved(host['time_local_before'], next(r['value'] for r in trace if r['kind'] == 'time_local_after'))
    return dict(classification='FAILED_PRE_RF_WIFI_AUTHENTICATION', packet_sha256=PACKET,
                accepted_assertions=0, submitted_jobs=0, completed_jobs=0, pressure_connections=0,
                new_rf_launches=0, inventories=len(order), readiness_inventories=25,
                last_link_status=-3, prior_terminal_released=True, final_a_state='empty',
                a_boot=BOOT, b_boot=p['initial_b_boot_id'], host_restored=True,
                configuration_writes=0, flashes=0, wifi_off=0, wifi_on=0,
                raw_sha256={name+'.stdout': digest(root/(name+'.stdout')) for name in order} |
                           {'initial-terminal-release.jsonl': digest(root/'initial-terminal-release.jsonl')})
