"""Independent R3 A1 response/counter/overlap audit, plus existing raw USB and Pi gates."""
import json
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_browser_jobs import NAME, PEER
from phase11_5_r3_tls_plan import CASES, validate
from phase11_5_r3_tls_pressure import response, check_transport


def audit_pressure(packet, rows, usb):
    validate(packet)
    require(rows and rows[0]['kind'] == 'start' and rows[-1]['kind'] == 'finish'
            and rows[-1]['value'] == dict(status='CAPTURED_REQUIRES_AUDIT', connections=12),
            'R3 complete pressure trace')
    require([r['sequence'] for r in rows] == list(range(len(rows)))
            and all(a['monotonic_ns'] <= b['monotonic_ns'] for a, b in zip(rows, rows[1:])),
            'R3 trace order')
    require(all(r['kind'] in ('start', 'finish', 'case_begin', 'case_finish', 'tcp_open', 'tls', 'http')
                for r in rows), 'Unexpected pressure operation')
    groups = []
    current = None
    for row in rows[1:-1]:
        if row['kind'] == 'case_begin':
            require(current is None, 'Nested pressure case')
            current = [row]
        else:
            require(current is not None, 'Unbound pressure operation')
            current.append(row)
            if row['kind'] == 'case_finish':
                groups.append(current)
                current = None
    require(current is None and len(groups) == 10, 'Missing or extra pressure case')
    expected = [(job, label) for job, labels in zip(packet['jobs'], CASES) for label in labels]
    result = []
    last_transport = None
    previous_end = None
    for group, (job, label) in zip(groups, expected):
        first, last = group[0], group[-1]
        begin, end = first['monotonic_ns'], last['monotonic_ns']
        require(first['value'] == dict(label=label, job_id=job['job_id'])
                and last['value']['label'] == label and last['value']['job_id'] == job['job_id']
                and 0 <= begin - last['value']['began_ns'] <= 100_000_000,
                'Pressure case identity/start')
        bound = (15 if label == 'positive' or label.startswith('recover-') else
                 {'missing-certificate': 5, 'silent-handshake': 14,
                  'slot-excess': 9, 'duplicate-wtp': 7}[label])
        require(0 < end - last['value']['began_ns'] <= bound * 10**9, 'Pressure case deadline')
        if label.startswith('recover-'):
            require(previous_end is not None and end - previous_end <= 15_000_000_000,
                    'Fresh authenticated recovery exceeded 15 seconds after trigger')
        previous_end = end
        # Bind every trigger and recovery to independent raw-audited samples.
        # A stale copied snapshot cannot manufacture overlap or current RF ownership.
        for kind, budget in (('info', 2_000_000_000), ('status', 6_000_000_000)):
            series = [r for r in usb if r['kind'] == kind]
            preceding = [r for r in series if r['monotonic_ns'] <= begin]
            ending = [r for r in series if r['monotonic_ns'] >= end]
            require(preceding and ending and begin - preceding[-1]['monotonic_ns'] <= budget
                    and ending[0]['monotonic_ns'] - end <= budget, 'Missing independent pressure bracket')
            observed = [r for r in series if preceding[-1]['monotonic_ns'] <= r['monotonic_ns']
                        <= ending[0]['monotonic_ns']]
            for row in observed:
                value = row['value']['value']
                s = value['status'] if kind == 'info' else value
                require(s['boot_id'] == packet['boot_id'] and s['job_id'] == job['job_id']
                        and s['owner_id'] == packet['owner_id'] and s['state'] == 'running'
                        and s['output_active'] is True, 'Pressure lost independent Running overlap')
        opens = [r for r in group if r['kind'] == 'tcp_open']
        labels = ['slot-active', 'slot-pending', 'slot-excess'] if label == 'slot-excess' else [label]
        require([r['value']['label'] for r in opens] == labels, 'Missing/extra network attempt')
        for opened in opens:
            value = opened['value']
            require(value['peer'] == ['10.77.15.10', 18443] and value['local'][0] == '10.77.15.2'
                    and type(value['local'][1]) is int and 1 <= value['local'][1] <= 65535
                    and begin <= value['began_ns'] <= opened['monotonic_ns']
                    and opened['monotonic_ns'] - value['began_ns'] <= 2_000_000_000,
                    'Pressure TCP endpoint/deadline')
        tls = [r for r in group if r['kind'] == 'tls']
        http = [r for r in group if r['kind'] == 'http']
        if label in ('silent-handshake', 'slot-excess'):
            require(not tls and not http and last['value']['close'] in ('eof', 'reset'),
                    'Raw-slot path sent TLS/application traffic')
            if label == 'slot-excess':
                require(last['value']['client_closed_supported_slots'] is True
                        and end - opens[-1]['monotonic_ns'] <= 2_000_000_000,
                        'Excess rejection bound')
            else:
                require(end - opens[0]['monotonic_ns'] <= 12_000_000_000,
                        'Client-observed silent-handshake timeout bound')
        else:
            require(len(tls) in ((0, 1) if label == 'missing-certificate' else (1,)),
                    'Missing/extra authenticated handshake')
            for row in tls:
                require(row['value'] == dict(label=label, peer_sha256=PEER, version='TLSv1.3',
                        alpn='wtp/1' if label == 'duplicate-wtp' else 'http/1.1'), 'TLS identity/protocol')
            if label == 'missing-certificate':
                require(not http and last['value']['alert'] == 116 and last['value']['reason'] ==
                        'TLSV13_ALERT_CERTIFICATE_REQUIRED' and last['value']['library'] == 'SSL',
                        'Certificate failure must be target alert 116')
            elif label == 'duplicate-wtp':
                require(not http and last['value']['close'] in ('eof', 'reset', 'tls-eof')
                        and end - tls[0]['monotonic_ns'] <= 2_000_000_000,
                        'Duplicate WTP must close after verified handshake without application bytes')
            else:
                require(len(http) == 1 and http[0]['value']['label'] == label, 'HTTPS recovery evidence')
                wire = http[0]['value']
                request = f'GET /api/v1/status HTTP/1.1\r\nHost: {NAME}:18443\r\nConnection: close\r\n\r\n'.encode()
                require(bytes.fromhex(wire['request_hex']) == request, 'Unexpected HTTP mutation/request')
                value = response(bytes.fromhex(wire['response_hex']), packet, job)
                transport = value['transport']
                require(transport == last['value']['transport'], 'Reported transport differs from HTTP bytes')
                check_transport(last_transport, transport, label)
                last_transport = transport
        result.append(dict(job_id=job['job_id'], case=label, duration_ns=end - begin))
    return dict(status='PASS', cases=result, tcp_connections=12, https_controls=6,
                limitation='Pending retention and bounded excess only; no pending-expiry or failed-alert-wait claim')


def audit(root, decoder):
    from audit_phase11_5_r2_modes import audit as audit_finite
    packet = validate(json.loads((root / 'jobs.json').read_text()))
    rows = [json.loads(line) for line in (root / 'pressure.jsonl').read_text().splitlines()]
    require((root / 'pressure.jsonl').read_bytes().endswith(b'\n') and rows[0]['value'] ==
            dict(packet_sha256=digest(root / 'jobs.json'), load_sha256=digest(root / 'load.json')),
            'Pressure packet/load hash binding')
    load = json.loads((root / 'load.json').read_text())
    require(load['browser'] is False and load['seconds'] == 300 and load.get('rf_family') == 'R3',
            'R3 controller-only load')
    result = audit_finite(root, decoder, cadence_policy='single-flight-admin-v1', packet_validator=validate)
    usb = [json.loads(line) for line in (root / 'usb-health.jsonl').read_text().splitlines()]
    require(usb[0]['value']['seconds'] == 360, 'R3 full observation window required')
    result['pressure'] = audit_pressure(packet, rows, usb)
    result.update(family='R3', tranche='A1', family_closed=False)
    return result
