#!/usr/bin/env python3
"""Offline acceptance of a controlled two-peer B2/D2 case; never opens devices."""
import argparse
import json
from pathlib import Path
import re

from audit_phase11_4_mdns_conflict import pcap, require
from phase11_4_loop_audit import strict_usb
from phase11_4_loop_common import validate_info
from phase11_4_trace_audit import trace_events, wire_packets
from validate_wtp_contract import unique_object, reject_constant
from audit_phase11_4_recovery import SCHEMA, VALIDATOR

DEVICE = 'fd6127d11d6aca42a9905fa3fb1bf1d5'
NAME = 'wsprrypico-0a60df.local'
ADDRESS = '10.77.14.10'
REVISION = '802c91a7b86e-dirty'
FINGERPRINT = '06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016'
SAVED = ('station', 'schedules', 'watermark_utc_ns', 'expires_utc_s', 'enabled', 'suspended')


def rows(path):
    return [json.loads(line, object_pairs_hook=unique_object, parse_constant=reject_constant)
            for line in path.read_text().splitlines()]


def origin(p):
    return (p['source'] == ADDRESS and p['source_mac'] == '88:a2:9e:0a:60:df' and
            p['ttl'] == 255 and p['sport'] == p['dport'] == 5353)


def has_answer(p, ttl):
    return origin(p) and p['dns']['flags'] == 0x8400 and any(
        r['name'] == NAME and r['type'] == 1 and r['address'] == ADDRESS and
        r['ttl'] == ttl and r['cls'] == 0x8001 for r in p['dns']['records'])


def audit(root, require_resumed_sessions=False):
    data = rows(root / 'events.jsonl')
    selected = lambda kind: [r for r in data if r['kind'] == kind]
    def one(kind):
        values = selected(kind)
        require(len(values) == 1, 'Missing/duplicate ' + kind)
        return values[0]
    require(not any(selected(k) for k in ('CASE_FAILURE', 'OBSERVER_FAILURE', 'FINAL_FAILURE',
                'WITHDRAWAL_FAILURE', 'RECOVERY_FAILURE', 'cleanup_on')), 'Recorded failure cannot become PASS')
    require(all(a['epoch_ns'] <= b['epoch_ns'] and a['monotonic_ns'] <= b['monotonic_ns']
                for a, b in zip(data, data[1:])), 'Evidence clock/order changed')
    infos = selected('INFO')
    require(len(infos) > 100, 'Insufficient independent USB evidence')
    before, final = infos[0]['value'], infos[-1]['value']
    boot = before['status']['boot_id']
    for row in infos:
        v = row['value']
        validate_info(v, boot, REVISION)
        require(v['status']['state'] == 'empty', 'Nonempty device')
        require(v['network']['stable_hostname'] == NAME, 'Hostname changed')
        require(all(v['status'][k] == before['status'][k] for k in SAVED), 'Saved state changed')
        require(v['tls_allocation_failures'] == 0, 'TLS allocation error')
        for pool in v['network']['memory'].values():
            require(0 <= pool['used'] <= pool['peak'] <= pool['capacity'] and pool['errors'] == 0,
                    'Pool allocation failure or capacity violation')
    off, on = one('off_begin'), one('on_begin')
    passed = one('CASE_PASS')
    observed = one('OBSERVERS_READY')
    off_ns, on_ns = off['epoch_ns'], on['epoch_ns']
    require((on['monotonic_ns'] - off['monotonic_ns']) / 1e9 >= 150, 'Outage shorter than 150 seconds')
    require(observed['epoch_ns'] < off_ns < on_ns < passed['epoch_ns'], 'Invalid lifecycle')
    monitored = [r['monotonic_ns'] for r in infos if observed['epoch_ns'] <= r['epoch_ns'] <= passed['epoch_ns']]
    gaps = [b-a for a, b in zip([observed['monotonic_ns']] + monitored, monitored + [passed['monotonic_ns']])]
    require(max(gaps) < 2e9, 'Independent USB coverage gap exceeds two seconds')
    require(any(off_ns < r['epoch_ns'] < on_ns and not r['value']['network']['enabled'] and
                r['value']['network']['advertised_hostname'] == '' for r in infos), 'No authoritative withdrawal')
    require(final['network']['enabled'] and final['network']['mdns_state'] == 'active' and
            final['network']['ipv4'] == ADDRESS and final['network']['advertised_hostname'] == NAME,
            'Final discovery not recovered')
    require(final['network']['mdns_goodbye_attempts'] == before['network']['mdns_goodbye_attempts'] + 1 and
            final['network']['mdns_goodbye_failures'] == before['network']['mdns_goodbye_failures'], 'Goodbye counter mismatch')
    active = one('local_active')
    activation = (active['monotonic_ns'] - on['monotonic_ns']) / 1e9
    require(0 < activation <= 40 and abs(activation - active['value']['seconds_after_on']) < .1,
            'Local activation exceeds bound or disagrees with evidence')
    require(passed['epoch_ns'] < on_ns + 120e9, 'Recovery exceeds 120 seconds')
    for kind in ('PEER_STATES', 'PEER_STATES_FINAL'):
        state = one(kind)['value']
        require(set(state) == {'1', '2'}, 'Missing peer role')
        require(state['1']['netns'] != state['2']['netns'] and state['1']['mountns'] != state['2']['mountns'],
                'Peers share a namespace/cache')
        for peer, address in (('1', '10.77.14.2'), ('2', '10.77.14.3')):
            require('Connected to 2c:cf:67:62:76:66' in state[peer]['link'] and
                    address + '/24' in state[peer]['interfaces'] and 'default' not in state[peer]['routes'] and
                    state[peer]['avahi_socket'] == 'socket' and 'mdns' in state[peer]['nss'], 'Peer path/cache not qualified')
    decoded = rows(root / 'usb-frames.jsonl')
    decoded_count = strict_usb((root / 'usb-wire.bin').read_bytes(), decoded)
    responses = selected('wtp_response')
    requests = selected('wtp_request')
    require(len(decoded) == len(responses) == len(requests), 'USB response count mismatch')
    require([r['value']['op'] for r in requests[:2]] == ['HELLO', 'CAPS'] and
            all(r['value']['op'] == 'STATUS' for r in requests[2:]), 'Unexpected USB operation')
    require(len({r['value']['session'] for r in requests}) == 1, 'USB session changed')
    for index, (wire, req, res) in enumerate(zip(decoded, requests, responses), 1):
        require(not VALIDATOR.errors(wire, SCHEMA) and wire['request_id'] == format(index, '032x'),
                'USB schema or request identity mismatch')
        require(wire['type'] == 'response' and wire['ok'] and wire['session_id'] == req['value']['session'] and
                wire['op'] == req['value']['op'] == res['value']['op'] and wire['body'] == res['value']['body'] and
                req['epoch_ns'] < res['epoch_ns'], 'USB request/response mismatch')
        if wire['op'] == 'HELLO':
            require(wire['body']['device_id'] == DEVICE and wire['body']['boot_id'] == boot, 'USB identity mismatch')
        if wire['op'] == 'STATUS':
            s = wire['body']
            require(s['boot_id'] == boot and s['state'] == 'empty' and s['owner_id'] is None and
                    s['job_id'] is None and s['output_active'] is False, 'USB authority changed')
    require(len(requests) >= 6, 'Insufficient USB status checks')
    trace = trace_events(data, boot, REVISION)
    counts, goodbyes = {}, {}
    for label in ('ap', 'peer1', 'peer2'):
        packets = pcap(root / (label + '-mdns.pcap'))
        for kind, count in [('mdns', len(packets)), ('path', len(list(wire_packets(root / (label + '-path.pcap')))))]:
            text = (root / (label + '-' + kind + '.log')).read_text()
            match = re.search(r'(\d+) packets captured', text)
            require(match and int(match[1]) == count and re.search(r'\n0 packets dropped by kernel\n', text),
                    'Capture missing/truncated/dropped: ' + label + '-' + kind)
        counts[label] = len(packets)
        require(any(has_answer(p, 120) and p['epoch_ns'] < off_ns for p in packets), 'Missing actual baseline at ' + label)
        bye = [p for p in packets if has_answer(p, 0) and off_ns <= p['epoch_ns'] < on_ns]
        require(len(bye) == 1, 'Missing/ambiguous actual goodbye at ' + label)
        require(any(r['name'] == '10.14.77.10.in-addr.arpa' and r['type'] == 12 and r['target'] == NAME and
                    r['ttl'] == 0 and r['cls'] == 0x8001 for r in bye[0]['dns']['records']), 'Missing PTR goodbye')
        goodbyes[label] = bye[0]['epoch_ns']
        require(not any(has_answer(p, 120) and off_ns <= p['epoch_ns'] < on_ns for p in packets), 'Positive advertisement while disabled')
        announcements = [p for p in packets if has_answer(p, 120) and on_ns < p['epoch_ns']]
        require(announcements, 'Missing recovery announcement at ' + label)
        probes = [p for p in packets if origin(p) and on_ns < p['epoch_ns'] < announcements[0]['epoch_ns'] and
                  not p['dns']['flags'] & 0x8000 and any(q['name'] == NAME and q['type'] == 255 for q in p['dns']['questions'])]
        require(len(probes) == 3, 'Missing three recovery probes at ' + label)
    peer_results = {}
    for peer in (1, 2):
        lookup_rows = [r for r in selected('NSS') if r['value']['peer'] == peer]
        require(all(r['value']['ended_ns'] <= r['epoch_ns'] for r in lookup_rows), 'Lookup timestamp is in the future')
        lookups = [r['value'] for r in lookup_rows]
        negative = [v for v in lookups if v['label'].startswith('off-')]
        require([v['label'] for v in negative] == ['off-' + str(n) for n in (3,10,40,80,125,145)], 'Missing distributed negatives')
        for v in lookups:
            require(v['started_ns'] < v['ended_ns'], 'Invalid lookup timing')
            if v['label'].startswith('off-'):
                require(v['exit'] == 2 and not v['stdout'] and off_ns < v['started_ns'] < v['ended_ns'] < on_ns,
                        'Stale, failed, timed out, or out-of-window negative lookup')
            else:
                require(v['exit'] == 0 and {s.split()[0] for s in v['stdout'].splitlines()} == {ADDRESS},
                        'Native resolution failed or returned alternate address')
        require(negative[0]['started_ns'] > goodbyes['peer' + str(peer)] + 1e9 and
                negative[-1]['started_ns'] > off_ns + 145e9, 'Negatives lack goodbye grace or full TTL coverage')
        require(negative[0]['ended_ns'] < off_ns + 10e9, 'Cache withdrawal was not prompt')
        auth = [r for r in selected('AUTH') if r['value']['peer'] == peer]
        sessions, request_ids = set(), set()
        require(any(r['epoch_ns'] < off_ns and r['value']['label'] == 'before' for r in auth), 'Missing authenticated baseline')
        recovered = [r for r in auth if r['value']['label'].startswith('recovery-')]
        require(len(recovered) >= 5 and recovered[-1]['epoch_ns'] - recovered[0]['epoch_ns'] >= 30e9,
                'Missing five authenticated checks spanning 30 seconds')
        require(all(on_ns < r['value']['started_ns'] < r['value']['ended_ns'] < on_ns + 120e9 for r in recovered), 'Authentication outside recovery deadline')
        for r in auth:
            v = r['value']
            matching = [n for n in lookups if n['label'] == v['label']]
            require(len(matching) == 1 and matching[0]['ended_ns'] <= v['started_ns'] < v['ended_ns'] <= r['epoch_ns'],
                    'Authenticated check lacks its own preceding native lookup')
            require(v['exit'] == 0 and Path(v['directory']).name == v['directory'], 'Failed or invalid authentication record')
            evidence = rows(root / v['directory'] / 'events.jsonl')
            native = [e['value'] for e in evidence if e['kind'] == 'client_native_dns']
            require(native == [{'addresses': [ADDRESS], 'expected': ADDRESS}], 'Missing native address binding')
            tls = [e['value'] for e in evidence if e['kind'] == 'client_tls']
            require(len(tls) == 1 and tls[0] == dict(destination=ADDRESS, identity=NAME,
                    fingerprint=FINGERPRINT, alpn='wtp/1', version='TLSv1.3'), 'Missing verified WTP TLS evidence')
            sent = [e['value'] for e in evidence if e['kind'] == 'client_request']
            received = [e['value'] for e in evidence if e['kind'] == 'client_received']
            require([q['op'] for q in sent] == ['HELLO', 'CAPS', 'STATUS'] and len(received) == 3,
                    'Missing WTP reads or unexpected operation')
            for q, reply in zip(sent, received):
                require(not VALIDATOR.errors(q, SCHEMA) and not VALIDATOR.errors(reply, SCHEMA) and
                        reply['type'] == 'response' and reply['ok'] and
                        all(reply[k] == q[k] for k in ('session_id', 'request_id', 'op')),
                        'WTP response not bound to request')
                sessions.add(q['session_id'])
                identity = (q['session_id'], q['request_id'])
                require(identity not in request_ids, 'Repeated WTP request identity')
                request_ids.add(identity)
            require(received[0]['body']['device_id'] == DEVICE and received[0]['body']['boot_id'] == boot and
                    received[1]['body']['engine'] == 'inhibited-standalone-simulator', 'WTP device/capability mismatch')
            w = received[2]['body']
            require(w['boot_id'] == boot and w['state'] == 'empty' and w['owner_id'] is None and
                    w['job_id'] is None and w['output_active'] is False, 'WTP status disagreement')
            done = [e['value'] for e in evidence if e['kind'] == 'CLIENT_PASS']
            require(len(done) == 1 and done[0]['boot'] == boot and done[0]['address'] == ADDRESS and
                    done[0]['fingerprint'] == FINGERPRINT, 'Unbound TLS identity')
            status = done[0]['status']
            s, j, n = status['standalone'], status['job'], status['network']
            require(s['boot_id'] == j['boot_id'] == boot and j['state'] == 'empty' and j['owner_id'] is None and
                    j['job_id'] is None and j['output_active'] is False and s['storage_healthy'] and
                    s['engine'] == 'inhibited-standalone-simulator' and s['output_active'] is False and
                    all(s[k] == before['status'][k] for k in SAVED), 'HTTPS state disagreement')
            require(n['ipv4'] == ADDRESS and n['advertised_hostname'] == NAME and n['mdns_state'] == 'active' and
                    n['deployment_identity_matches'] and status['transport']['tls_allocation_failures'] == 0, 'HTTPS discovery/resource mismatch')
        peer_results[str(peer)] = dict(checks=len(recovered), stable_seconds=(recovered[-1]['epoch_ns']-recovered[0]['epoch_ns'])/1e9,
            cache_absent_by_seconds=(negative[0]['ended_ns']-off_ns)/1e9,
            first_authenticated_seconds=(recovered[0]['epoch_ns']-on_ns)/1e9,
            sessions=sorted(sessions))
        if require_resumed_sessions:
            require(len(sessions) == 1, 'Observer churned logical sessions')
    if require_resumed_sessions:
        require(peer_results['1']['sessions'] != peer_results['2']['sessions'], 'Peers share a logical session')
    return dict(result='PASS', B2='PASS', D2='PASS', boot=boot, revision=REVISION,
        local_active_seconds=activation, usb_max_gap_seconds=max(gaps)/1e9,
        usb_frames=decoded_count, trace_events=len(trace), mdns_packets=counts, peers=peer_results,
        scope='Controlled wlan0 AP and two independent native Linux peers; one bounded OFF/ON case')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--resumed-sessions', action='store_true')
    args = parser.parse_args()
    print(json.dumps(audit(args.root, args.resumed_sessions), indent=2))
