"""Reconstruct B1's early ACK-suppression defect; never award acceptance credit."""
from collections import Counter
import json
from pathlib import Path

from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_pilot_supervisor import idle, configuration, B_SERIAL, B_DEVICE
from phase11_5_r3_preflight import audit_inventory
from phase11_5_r3_transport_plan import validate, CASES
from phase11_5_r3_tls_pressure import response
from phase11_5_r3_transport_pressure import check_transport
from phase11_5_time_local import validate_preserved
from audit_phase11_5_r3_a1e_failure import rows, wifi_exchange
from audit_phase11_5_r3_stopped_observer import audit as stopped_observer
from audit_phase11_5_r3_transport import tcp_packets, audit_case_flow
from audit_phase11_5_r3_tls import pressure_bracket
from audit_phase11_5_r2_modes import timing

PACKET = 'b5359002368fbe2ff4db1dc4b101734f40145887f03ac767e9a01d6634ce7b0b'


def audit(root):
    require(digest(root / 'packet.json') == PACKET, 'Different consumed B1 packet')
    p = json.loads((root / 'packet.json').read_text())
    for group in ('case_helper_sha256', 'production_helper_sha256'):
        for name, sha in p[group].items():
            require(digest(root / name) == sha, 'Frozen B1 helper changed')
    require(json.loads((root / 'retained-result.json').read_text()) == dict(status='FAILED',
            packet_sha256=PACKET, family_closed=False, error='ValueError: R3 worker failed; no retry',
            device_inactive_unowned=True, b_unchanged=True, host_restored=True, configuration_writes=0, flashes=0),
            'B1 failed disposition changed')
    case = root / 'tls-a1'
    rf = validate(json.loads((case / 'jobs.json').read_text()))
    require(rf['jobs'] == p['finite_job_templates'], 'B1 RF identity')
    pressure = rows(case / 'pressure.jsonl')
    require(pressure[0]['value'] == dict(packet_sha256=digest(case / 'jobs.json'), load_sha256=digest(case / 'load.json'))
            and [r['sequence'] for r in pressure] == list(range(79))
            and pressure[-1]['kind'] == 'failure' and pressure[-1]['value'] ==
                dict(type='ValueError', error='R3 socket operation deadline'), 'B1 failure sequence')
    require(all(a['monotonic_ns'] <= b['monotonic_ns'] for a, b in zip(pressure, pressure[1:])), 'B1 chronology')
    failed_begin, = [r for r in pressure if r['kind'] == 'case_begin' and r['value']['label'] == 'failed-alert-wait']
    failed = [r for r in pressure if r['monotonic_ns'] >= failed_begin['monotonic_ns']]
    require([r['kind'] for r in failed] == ['case_begin', 'tcp_open', 'ack_filter_installed',
            'ciphertext_tx', 'ciphertext_rx', 'ack_filter_counters', 'ack_filter_removed', 'failure'],
            'B1 failure reached a different TLS stage')
    # ServerHello is 127 bytes including TLS framing. No authenticated client
    # handshake or fatal alert was observed before this harness timeout.
    server_hello = bytes.fromhex(failed[4]['value']['hex'])
    require(len(server_hello) == 127 and server_hello[:5] == bytes.fromhex('160303007a')
            and server_hello[5] == 2, 'Missing actual ServerHello before suppression stall')
    nft = json.loads(failed[5]['value']['raw_json'])['nftables']
    counters = [x['counter'] for obj in nft if 'rule' in obj for x in obj['rule']['expr'] if 'counter' in x]
    require(counters == [dict(packets=3, bytes=1580)], 'B1 drop counters differ')
    require(failed[2]['monotonic_ns'] < failed[3]['monotonic_ns'] < failed[4]['monotonic_ns'],
            'B1 filter was not installed before the server flight')
    require(json.loads((case / 'ack-filter.json').read_text())['status'] == 'REMOVED', 'B1 filter not removed')
    packets = tcp_packets((case / 'transport.pcap').read_bytes())
    start = json.loads((case / 'tcp-clock-start.json').read_text())
    end = json.loads((case / 'tcp-clock-end.json').read_text())
    offset = start['realtime_ns'] - start['monotonic_ns']
    require(abs(end['realtime_ns'] - end['monotonic_ns'] - offset) < 10000000
            and '0 packets dropped by kernel' in (case / 'tcp-capture.log').read_text(), 'B1 capture incomplete')
    port = failed[1]['value']['local'][1]
    flow = [v for v in packets if v['sport'] == port or v['dport'] == port]
    syn = next(v for v in flow if v['source'] == '10.77.15.2' and v['flags'] == 2)
    client_size = len(bytes.fromhex(failed[3]['value']['hex']))
    require(any(v['source'] == '10.77.15.10' and v['ack'] == (syn['seq'] + 1 + client_size) % (1 << 32)
                for v in flow), 'ClientHello delivery is not proven')
    before_stop = [v for v in flow if v['realtime_ns'] - offset < failed[6]['monotonic_ns']]
    server_payload = [v for v in before_stop if v['source'] == '10.77.15.10' and v['size']]
    require(len(server_payload) == 2 and all(v['payload_hex'] == server_hello.hex() for v in server_payload)
            and not any(v['source'] == '10.77.15.2' and v['ack'] == server_payload[0]['seq'] + 127
                        for v in before_stop), 'B1 did not stall on the unacknowledged server flight')
    observed = stopped_observer(root, p, rf, pressure[-1]['monotonic_ns'])
    require(Counter(q['op'] for q in observed['requests']) ==
            dict(HELLO=1, STATUS=72, CLAIM=2, LOAD=2, GET_CLOCK=2, ARM=2, RENEW=3, RELEASE=1),
            'B1 actual finite work differs')
    arms = []
    for job in rf['jobs']:
        load, = [q for q in observed['requests'] if q['op'] == 'LOAD' and q['body']['job_id'] == job['job_id']]
        arm, = [v for v in observed['exchanges'] if v['request']['op'] == 'ARM' and
                v['request']['body']['job_id'] == job['job_id']]
        require(load['body'] == job and arm['response']['body']['start_utc_ns'] == arm['request']['body']['start_utc_ns'],
                'B1 raw LOAD/ARM differs')
        states = [v['body']['state'] for v in observed['events'] if v['event'] == 'JOB_STATE'
                  and v['body'].get('job_id') == job['job_id']]
        require(states == ['loaded', 'armed', 'running', 'complete'], 'B1 finite lifecycle differs')
        arms.append(dict(job=job, start_utc_ns=arm['request']['body']['start_utc_ns'], monotonic_ns=arm['started_ns']))
    measured = timing(rf, arms, observed['rows'])
    completed, current, previous = [], [], None
    for row in pressure[1:]:
        if row['kind'] == 'case_begin': current = []
        current.append(row)
        if row['kind'] != 'case_finish': continue
        label = current[0]['value']['label']
        job = next(j for j in rf['jobs'] if j['job_id'] == row['value']['job_id'])
        for kind, budget in (('info', 2000000000), ('status', 6000000000)):
            samples = pressure_bracket([v for v in observed['rows'] if v['kind'] == kind],
                      current[0]['monotonic_ns'], row['monotonic_ns'], budget, rf['observer_bracket_policy'])
            for sample in samples:
                value = sample['value']['value']; status = value['status'] if kind == 'info' else value
                require(status['state'] == 'running' and status['output_active'] is True, 'B1 case lost RF overlap')
                require(int(value['launch_epoch']) == row['value']['launch_epoch'] if kind == 'info' else
                        status['job_id'] == job['job_id'] and status['owner_id'] == rf['owner_id'], 'B1 case authority differs')
        if label == 'positive' or label.startswith('recover-'):
            http, = [v for v in current if v['kind'] == 'http']
            transport = response(bytes.fromhex(http['value']['response_hex']), rf, job)['transport']
            require(transport == row['value']['transport'], 'B1 reported counters differ from raw HTTP')
            check_transport(previous, transport, label); previous = transport
        else:
            audit_case_flow(label, current, packets, offset)
        completed.append(label)
    require(completed == list(CASES[0]) + list(CASES[1][:5]), 'B1 preliminary case count/order')
    from audit_phase11_5_r3_retained_failure import cleanup
    values = {}
    for name in ('initial-terminal-before', 'final-terminal-before', 'final-terminal-after', 'before-b', 'after-b'):
        b = name.endswith('-b')
        values[name] = audit_inventory(root / (name + '.stdout'),
            dict(serial=B_SERIAL if b else p['serial'], device_id=B_DEVICE if b else p['device_id']),
            p['b_inventory_session_id'] if b else p['inventory_session_id'], p['case_helper_sha256']['scripts/phase11_5_inventory.py'])
    require(values['final-terminal-before']['wtp']['STATUS'] == observed['last_status'], 'Final inventory disagrees with raw STATUS')
    cleanup(root / 'final-terminal-release.jsonl', p, values['final-terminal-before'], values['final-terminal-after'])
    for name in ('initial-terminal-before', 'final-terminal-after', 'before-b', 'after-b'): idle(values[name])
    require(configuration(values['initial-terminal-before']) == configuration(values['final-terminal-after'])
            and configuration(values['before-b']) == configuration(values['after-b'])
            and values['before-b']['wtp']['STATUS']['boot_id'] == values['after-b']['wtp']['STATUS']['boot_id'] == p['initial_b_boot_id'],
            'B1 configuration/comparator changed')
    host = json.loads((root / 'fixture-state.json').read_text()); trace = rows(root / 'fixture.jsonl')
    require(host['restored'] is True and host['host_boot'] == p['host_boot_id']
            and next(v['value'] for v in trace if v['kind'] == 'host_restored') == host['before']
            and next(v['value'] for v in trace if v['kind'] == 'cleanup')['failures'] == [], 'B1 host not restored')
    validate_preserved(host['time_local_before'], next(v['value'] for v in trace if v['kind'] == 'time_local_after'))
    wifi_exchange(root / 'wifi-off-exchange.jsonl', False); wifi_exchange(root / 'wifi-on-exchange.jsonl', True)
    return dict(classification='HARNESS_ACK_SUPPRESSION_BEFORE_SERVER_FLIGHT', accepted_assertions=0,
                packet_sha256=PACKET, completed_jobs=2, rf_seconds=200, preliminary_cases=completed,
                incomplete_case='failed-alert-wait', unrun_case='recover-alert-wait', dropped=counters[0],
                observation_seconds=observed['seconds'], samples=observed['samples'], timing_diagnostic=measured,
                final_status=values['final-terminal-after']['wtp']['STATUS'], host_restored=True,
                wifi_off=1, wifi_on=1, configuration_writes=0, flashes=0,
                conclusion='Early ACK suppression stalls ServerHello before the intended fatal alert. The PSH-based rule also cannot prove zero payload. No firmware failure is established. Full acceptance remains failed.')
