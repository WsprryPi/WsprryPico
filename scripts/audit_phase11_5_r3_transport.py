"""Offline B1 audit: raw RF/USB, HTTP counters, and actual TCP timeout causality."""
import json
import re
import struct

from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_r3_transport_plan import validate, CASES, SCHEMA_B2
from phase11_5_r3_transport_pressure import partial_request, ack_rules, check_transport
from phase11_5_r3_tls_pressure import response, NAME, PEER
from audit_phase11_5_r3_tls import pressure_bracket


def tcp_packets(raw):
    require(len(raw) >= 24 and raw[:4] == b'\xd4\xc3\xb2\xa1'
            and struct.unpack_from('<HH', raw, 4) == (2, 4)
            and struct.unpack_from('<I', raw, 20)[0] == 1, 'B1 Ethernet microsecond PCAP header')
    offset, result = 24, []
    while offset < len(raw):
        require(len(raw) - offset >= 16, 'Truncated TCP packet header')
        sec, us, size, original = struct.unpack_from('<4I', raw, offset)
        offset += 16
        require(size == original and size >= 54 and len(raw) - offset >= size and us < 1000000,
                'Truncated TCP capture')
        data = raw[offset:offset + size]
        offset += size
        require(data[12:14] == b'\x08\x00', 'Non-IPv4 B1 capture')
        ip = data[14:]
        ihl = (ip[0] & 15) * 4
        total = struct.unpack_from('!H', ip, 2)[0]
        require(ip[0] >> 4 == 4 and ihl >= 20 and ip[9] == 6 and total <= len(ip)
                and total >= ihl + 20 and struct.unpack_from('!H', ip, 6)[0] & 0x3fff == 0,
                'Invalid/fragmented TCP capture')
        tcp = ip[ihl:total]
        header = (tcp[12] >> 4) * 4
        require(20 <= header <= len(tcp), 'Invalid TCP data offset')
        sport, dport, seq, ack = struct.unpack_from('!HHII', tcp)
        result.append(dict(realtime_ns=(sec * 1000000 + us) * 1000,
                           source='.'.join(map(str, ip[12:16])), destination='.'.join(map(str, ip[16:20])),
                           sport=sport, dport=dport, seq=seq, ack=ack, flags=tcp[13],
                           window=struct.unpack_from('!H', tcp, 14)[0], size=len(tcp) - header,
                           payload_hex=tcp[header:].hex()))
    return result


def stream_bytes(flow, source):
    selected = [p for p in flow if p['source'] == source]
    syn = next(p for p in selected if p['flags'] & 2)
    base = (syn['seq'] + 1) % (1 << 32)
    data = {}
    for p in selected:
        if not p['size']:
            continue
        offset = (p['seq'] - base) % (1 << 32)
        payload = bytes.fromhex(p['payload_hex'])
        require(len(payload) == p['size'] and offset + len(payload) <= 131072, 'B1 ciphertext stream bound')
        for index, byte in enumerate(payload, offset):
            require(index not in data or data[index] == byte, 'Conflicting TCP retransmission')
            data[index] = byte
    require(data and set(data) == set(range(max(data) + 1)), 'Missing TCP payload bytes')
    return bytes(data[i] for i in range(len(data)))


def audit_case_flow(label, group, packets, offset, schema=None):
    opened = [r for r in group if r['kind'] == 'tcp_open']
    trigger = opened[-1]
    port = trigger['value']['local'][1]
    flow = [p for p in packets if
            (p['source'], p['sport'], p['destination'], p['dport']) in
            (('10.77.15.2', port, '10.77.15.10', 18443), ('10.77.15.10', 18443, '10.77.15.2', port))]
    require(flow, 'Missing B1 TCP flow')
    first = next(p for p in flow if p['source'] == '10.77.15.2' and p['flags'] & 2)
    if label == 'stalled-http-reader':
        began, ended = group[0]['monotonic_ns'], group[-1]['monotonic_ns']
        span = [p for p in flow if p['realtime_ns'] - offset <= ended]
        require(ended - began >= 16000000000
                and any(p['source'] == '10.77.15.2' and p['window'] == 0 for p in span)
                and not any(p['source'] == '10.77.15.2' and p['flags'] & 5 for p in span),
                'Unread application data did not create held TCP backpressure')
        return dict(port=port, held_unread_until_monotonic_ns=ended,
                    proof='fresh slot reuse and timeout counter; no client EOF deadline claim')
    close = next((p for p in flow if p['source'] == '10.77.15.10' and p['flags'] & 5), None)
    require(close is not None, 'Target did not close pressure connection')
    require(trigger['value']['began_ns'] - 10000000 <= first['realtime_ns'] - offset
            <= trigger['monotonic_ns'] + 10000000, 'TCP SYN not bound to pressure socket')
    before_close = [p for p in flow if p['realtime_ns'] <= close['realtime_ns']]
    require(not any(p['source'] == '10.77.15.2' and p['flags'] & 5
                    and p['realtime_ns'] < close['realtime_ns'] for p in before_close),
            'Client manufactured target closure')
    elapsed = (close['realtime_ns'] - first['realtime_ns']) / 1e9
    if label in ('partial-header', 'partial-body'):
        tls, = [r for r in group if r['kind'] == 'tls']
        require(elapsed >= 14.8 and close['realtime_ns'] - offset <= tls['monotonic_ns'] + 15200000000,
                'HTTP activation deadline not established')
    elif label == 'pending-expiry':
        require(9.8 <= elapsed <= 12, 'Separate pending lifetime not established')
        require(not any(p['source'] == '10.77.15.2' and p['size'] for p in before_close),
                'Pending client sent bytes')
        held_port = opened[0]['value']['local'][1]
        require(not any(p['dport'] == held_port and p['source'] == '10.77.15.10'
                        and p['flags'] & 5 and p['realtime_ns'] <= close['realtime_ns'] for p in packets),
                'Active holder ended before pending timeout')
    else:
        alert, = [r for r in group if r['kind'] == 'fatal_alert']
        payloads = [p for p in before_close if p['source'] == '10.77.15.10' and p['size']]
        require(payloads, 'No target TLS alert ciphertext')
        for kind, source in (('ciphertext_tx', '10.77.15.2'), ('ciphertext_rx', '10.77.15.10')):
            logged = b''.join(bytes.fromhex(r['value']['hex']) for r in group if r['kind'] == kind)
            require(logged and logged == stream_bytes(before_close, source),
                    'Alert producer bytes differ from independently captured TCP stream')
        # Last sequence region is the fatal alert. Handle 32-bit wrap explicitly.
        server_syn, = [p for p in flow if p['source'] == '10.77.15.10' and p['flags'] & 2][:1]
        last_end = max((p['seq'] - server_syn['seq']) % (1 << 32) + p['size'] for p in payloads)
        final = next(p for p in payloads if (p['seq'] - server_syn['seq']) % (1 << 32) + p['size'] == last_end)
        expected_ack = (final['seq'] + final['size']) % (1 << 32)
        acked = [p for p in before_close if p['source'] == '10.77.15.2'
                 and p['flags'] & 16 and p['ack'] == expected_ack]
        require(alert['value'] == dict(label=label, alert=116, reason='TLSV13_ALERT_CERTIFICATE_REQUIRED'),
                'Wrong fatal alert identity')
        delay = (close['realtime_ns'] - final['realtime_ns']) / 1e9
        if label == 'failed-alert-ack':
            require(acked and 0 <= delay < 1, 'Acknowledged-alert cleanup branch not established')
        else:
            require(not acked and .8 <= delay <= 1.3, 'Unacknowledged-alert one-second branch not established')
            install, = [r for r in group if r['kind'] == 'ack_filter_installed']
            counter, = [r for r in group if r['kind'] == 'ack_filter_counters']
            removed, = [r for r in group if r['kind'] == 'ack_filter_removed']
            table = install['value']['table']
            b2 = schema == SCHEMA_B2
            if b2:
                from phase11_5_r3_ack_filter import rules, audit_rules
                expected_rules = rules(table, port)
                audit_rules(counter['value']['raw_json'], table, port)
            else:
                expected_rules = ack_rules(table, port)
            require(install['value']['rules'] == expected_rules
                    and removed['value'] == dict(table=table) and counter['value']['table'] == table,
                    'ACK filter scope/cleanup differs')
            sends = [r for r in group if r['kind'] == 'ciphertext_tx']
            if b2:
                flight, = [r for r in group if r['kind'] == 'server_flight_complete']
                before = [r for r in sends if r['monotonic_ns'] < install['monotonic_ns']]
                after = [r for r in sends if r['monotonic_ns'] >= install['monotonic_ns']]
                require(before and len(after) == 1 and flight['monotonic_ns'] < install['monotonic_ns']
                        and flight['value'] == dict(label=label, deferred_client_bytes=len(bytes.fromhex(after[0]['value']['hex'])))
                        and flight['monotonic_ns'] >= next(r for r in group if r['kind'] == 'tls')['monotonic_ns'],
                        'ACK suppression did not follow the verified server flight')
            else:
                require(install['monotonic_ns'] < min(r['monotonic_ns'] for r in sends), 'B1 filter timing')
            require(removed['monotonic_ns'] >= close['realtime_ns'] - offset - 10000000,
                    'ACK filter ended before target closure')
            objects = json.loads(counter['value']['raw_json'])['nftables']
            counts = [x['counter']['packets'] for obj in objects if 'rule' in obj
                      for x in obj['rule']['expr'] if 'counter' in x]
            require(len(counts) == (11 if b2 else 1) and sum(counts) > 0, 'ACK filter did not drop packets')
    return dict(port=port, target_close_after_syn_seconds=elapsed)


def audit_pressure(packet, rows, usb, packets, clock_offset):
    validate(packet)
    require(rows[0]['kind'] == 'start' and rows[-1]['kind'] == 'finish'
            and rows[-1]['value'] == dict(status='CAPTURED_REQUIRES_AUDIT', connections=15)
            and [r['sequence'] for r in rows] == list(range(len(rows)))
            and all(a['monotonic_ns'] <= b['monotonic_ns'] for a, b in zip(rows, rows[1:])), 'B1 complete ordered trace')
    allowed = {'case_begin', 'case_finish', 'tcp_open', 'tls', 'http', 'request', 'ciphertext_rx',
               'ciphertext_tx', 'fatal_alert', 'ack_filter_installed', 'ack_filter_counters', 'ack_filter_removed',
               'stalled_client_close', 'server_flight_complete'}
    groups, current = [], None
    for row in rows[1:-1]:
        require(row['kind'] in allowed, 'Unexpected B1 operation')
        if row['kind'] == 'case_begin':
            require(current is None, 'Nested B1 case')
            current = []
        require(current is not None, 'Unbound B1 operation')
        current.append(row)
        if row['kind'] == 'case_finish':
            groups.append(current)
            current = None
    require(current is None and len(groups) == 14, 'B1 case count')
    previous, previous_end, epochs, result = None, None, {}, []
    expected = [(job, label) for job, labels in zip(packet['jobs'], CASES) for label in labels]
    for group, (job, label) in zip(groups, expected):
        first, last = group[0], group[-1]
        begin, end = first['monotonic_ns'], last['monotonic_ns']
        epoch = first['value']['launch_epoch']
        require(type(epoch) is int and epoch > 0, 'B1 launch epoch')
        if job['job_id'] not in epochs:
            require(epoch > max(epochs.values(), default=0), 'B1 reused launch epoch')
            epochs[job['job_id']] = epoch
        require(epoch == epochs[job['job_id']] and first['value'] == dict(label=label,
                job_id=job['job_id'], launch_epoch=epoch) and last['value']['label'] == label
                and last['value']['job_id'] == job['job_id'] and last['value']['launch_epoch'] == epoch
                and 0 <= begin - last['value']['began_ns'] <= 100000000, 'B1 case identity')
        bound = 24 if label.startswith('partial-') or label == 'stalled-http-reader' else 18
        require(0 < end - begin <= bound * 10**9, 'B1 case deadline')
        if label.startswith('recover-'):
            require(previous_end is not None and end - previous_end <= 15000000000, 'Late B1 recovery')
        previous_end = end
        for kind, budget in (('info', 2000000000), ('status', 6000000000)):
            series = [r for r in usb if r['kind'] == kind]
            for row in pressure_bracket(series, begin, end, budget, packet['observer_bracket_policy']):
                value = row['value']['value']
                status = value['status'] if kind == 'info' else value
                require(status['boot_id'] == packet['boot_id'] and status['state'] == 'running'
                        and status['output_active'] is True, 'B1 lost independent Running RF')
                require(int(value['launch_epoch']) == epoch if kind == 'info' else
                        status['job_id'] == job['job_id'] and status['owner_id'] == packet['owner_id'],
                        'B1 wrong owner/job/epoch')
        opens = [r for r in group if r['kind'] == 'tcp_open']
        require([r['value']['label'] for r in opens] ==
                (['pending-holder', label] if label == 'pending-expiry' else [label]), 'B1 connection count')
        for opened in opens:
            v = opened['value']
            require(v['peer'] == ['10.77.15.10', 18443] and v['local'][0] == '10.77.15.2'
                    and type(v['local'][1]) is int and 1 <= v['local'][1] <= 65535
                    and begin <= v['began_ns'] <= opened['monotonic_ns']
                    and opened['monotonic_ns'] - v['began_ns'] <= 2000000000, 'B1 connection scope')
        tls = [r for r in group if r['kind'] == 'tls']
        require(len(tls) == 1 and tls[0]['value'] == dict(label='pending-holder' if label == 'pending-expiry' else label,
                peer_sha256=PEER, version='TLSv1.3', alpn='http/1.1'), 'B1 verified TLS identity')
        http = [r for r in group if r['kind'] == 'http']
        flow = None
        common = {'case_begin', 'case_finish', 'tcp_open', 'tls'}
        kinds = {r['kind'] for r in group}
        if label == 'positive' or label.startswith('recover-'):
            require(kinds == common | {'http'} | ({'stalled_client_close'} if label == 'recover-reader' else set()),
                    'Unexpected B1 control operation')
            require(len(http) == 1, 'B1 raw HTTP recovery')
            v = http[0]['value']
            request = f'GET /api/v1/status HTTP/1.1\r\nHost: {NAME}:18443\r\nConnection: close\r\n\r\n'.encode()
            require(v['label'] == label and bytes.fromhex(v['request_hex']) == request, 'B1 recovery request')
            transport = response(bytes.fromhex(v['response_hex']), packet, job)['transport']
            require(transport == last['value']['transport'], 'B1 summary differs from HTTP bytes')
            check_transport(previous, transport, label)
            previous = transport
            if label == 'recover-reader':
                closed, = [r for r in group if r['kind'] == 'stalled_client_close']
                require(closed['monotonic_ns'] >= http[0]['monotonic_ns']
                        and closed['value'] == dict(after_authenticated_recovery=True), 'Stalled reader closed early')
                held = next(r['flow'] for r in result if r['case'] == 'stalled-http-reader')
                require(not any(p['source'] == '10.77.15.2' and p['sport'] == held['port'] and p['flags'] & 5
                                and p['realtime_ns'] - clock_offset < http[0]['monotonic_ns'] for p in packets),
                        'Client closure manufactured reader slot reuse')
        else:
            require(not http, 'Unexpected HTTP operation in trigger')
            requests = [r for r in group if r['kind'] == 'request']
            if label.startswith('partial-'):
                require(kinds == common | {'request'}, 'Unexpected partial request operation')
                require(len(requests) == 1 and requests[0]['value'] ==
                        dict(label=label, request_hex=partial_request(label).hex()), 'Partial request differs')
            elif label == 'stalled-http-reader':
                require(kinds == common | {'request'}, 'Unexpected stalled reader operation')
                request = f'GET /app.js HTTP/1.1\r\nHost: {NAME}:18443\r\nConnection: close\r\n\r\n'.encode()
                require(len(requests) == 1 and requests[0]['value']['request_hex'] == request.hex()
                        and last['value']['client_read_response'] is False
                        and last['value']['socket_held_for_recovery'] is True, 'Stalled reader operation')
            else:
                require(not requests, 'Unexpected trigger application request')
                extra = set() if label == 'pending-expiry' else {'ciphertext_rx', 'ciphertext_tx', 'fatal_alert'}
                if label == 'failed-alert-wait':
                    extra |= {'ack_filter_installed', 'ack_filter_counters', 'ack_filter_removed'}
                    if packet['schema'] == SCHEMA_B2:
                        extra.add('server_flight_complete')
                require(kinds == common | extra, 'Unexpected slot/alert operation')
            flow = audit_case_flow(label, group, packets, clock_offset, packet['schema'])
        result.append(dict(case=label, job_id=job['job_id'], launch_epoch=epoch, duration_ns=end - begin, flow=flow))
    return dict(status='PASS', cases=result, tcp_connections=15, https_controls=8)


def audit(root, decoder, *, baseline_path=None):
    from audit_phase11_5_r2_modes import audit as audit_finite
    packet = validate(json.loads((root / 'jobs.json').read_text()))
    raw = (root / 'pressure.jsonl').read_bytes()
    rows = [json.loads(line) for line in raw.splitlines()]
    require(raw.endswith(b'\n') and rows[0]['value'] == dict(packet_sha256=digest(root / 'jobs.json'),
            load_sha256=digest(root / 'load.json')), 'B1 packet/load bytes')
    load = json.loads((root / 'load.json').read_text())
    require(load['browser'] is False and load['seconds'] == 300 and load['rf_family'] == 'R3', 'B1 load scope')
    start, end = [json.loads((root / ('tcp-clock-' + k + '.json')).read_text()) for k in ('start', 'end')]
    offsets = [v['realtime_ns'] - v['monotonic_ns'] for v in (start, end)]
    require(end['monotonic_ns'] > start['monotonic_ns'] and abs(offsets[1] - offsets[0]) <= 10000000,
            'TCP and observer clock mapping changed')
    log = (root / 'tcp-capture.log').read_text()
    require(re.search(r'\b0 packets dropped by kernel\b', log)
            and json.loads((root / 'result.json').read_text())['capture_exit'] == 0, 'TCP capture incomplete')
    packets = tcp_packets((root / 'transport.pcap').read_bytes())
    installed, = [r for r in rows if r['kind'] == 'ack_filter_installed']
    require(installed['value']['packet_sha256'] == digest(root / 'jobs.json')
            and installed['value']['netns'] == load['netns'], 'ACK filter authority/namespace')
    result = audit_finite(root, decoder, cadence_policy='single-flight-admin-v1', packet_validator=validate,
                          baseline_path=baseline_path)
    usb = [json.loads(line) for line in (root / 'usb-health.jsonl').read_text().splitlines()]
    require(usb[0]['value']['seconds'] == 360, 'B1 observation window')
    result['pressure'] = audit_pressure(packet, rows, usb, packets, offsets[0])
    epochs = {v['job_id']: v['epoch'] for v in result['timing']}
    require(all(epochs[v['job_id']] == v['launch_epoch'] for v in result['pressure']['cases']), 'B1 raw ARM epochs')
    require(json.loads((root / 'ack-filter.json').read_text())['status'] == 'REMOVED', 'B1 ACK filter not removed')
    result.update(family='R3', tranche='B2' if packet['schema'] == SCHEMA_B2 else 'B1', family_closed=False)
    return result
