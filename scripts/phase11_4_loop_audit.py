"""Offline assessments for the repeated B2/D2 harness; never controls hardware."""
import json
from pathlib import Path
import re
import socket
import struct

from audit_phase11_4_mdns_conflict import pcap
from audit_phase11_4_discovery_recovery import audit as acceptance_audit
from phase11_4_loop_common import ADDRESS, DEVICE, NAME, validate_info, validate_host, require
from validate_wtp_contract import crc32c, loads_strict


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def strict_usb(data, expected):
    messages = []
    while data:
        require(len(data) >= 16 and data[:4] == b'WTPF', 'USB framing gap')
        version, encoding, flags, size, crc = struct.unpack('>BBHII', data[4:16])
        require((version, encoding, flags) == (1, 1, 0) and 0 < size <= 65536,
                'USB header invalid')
        require(len(data) >= 16 + size, 'USB frame truncated')
        payload = data[16:16 + size]
        require(crc32c(payload) == crc, 'USB checksum mismatch')
        messages.append(loads_strict(payload.decode()))
        data = data[16 + size:]
    require(messages == expected, 'raw USB and decoded evidence disagree')
    return len(messages)


def diagnostic_packets(path):
    """Decode Ethernet ARP/TCP metadata, preserving all captured direction/times."""
    data = path.read_bytes()
    require(len(data) >= 24 and data[:4] == b'\xd4\xc3\xb2\xa1', 'unsupported PCAP format')
    require(struct.unpack('<I', data[20:24])[0] == 1, 'not an Ethernet capture')
    offset, result = 24, []
    while offset < len(data):
        require(len(data) - offset >= 16, 'truncated PCAP record')
        sec, usec, size, original = struct.unpack('<IIII', data[offset:offset + 16])
        offset += 16
        require(size == original and offset + size <= len(data), 'truncated captured packet')
        wire = data[offset:offset + size]
        offset += size
        require(len(wire) >= 14, 'short Ethernet frame')
        row = {'epoch_ns': sec * 10**9 + usec * 1000,
               'source_mac': wire[6:12].hex(':'), 'destination_mac': wire[:6].hex(':')}
        if wire[12:14] == b'\x08\x06':
            arp = wire[14:]
            require(len(arp) >= 28 and arp[:6] == b'\x00\x01\x08\x00\x06\x04', 'invalid Ethernet ARP')
            row.update(protocol='ARP', operation=struct.unpack('!H', arp[6:8])[0],
                       source=socket.inet_ntoa(arp[14:18]), target=socket.inet_ntoa(arp[24:28]))
        elif wire[12:14] == b'\x08\x00':
            ip = wire[14:]
            require(len(ip) >= 20, 'short IPv4')
            ihl = (ip[0] & 15) * 4
            total = struct.unpack('!H', ip[2:4])[0]
            require(ihl >= 20 and ihl <= total <= len(ip), 'invalid IPv4 lengths')
            row.update(protocol='OTHER_IP', source=socket.inet_ntoa(ip[12:16]),
                       target=socket.inet_ntoa(ip[16:20]))
            if ip[9] == 6:
                tcp = ip[ihl:total]
                require(len(tcp) >= 20, 'short TCP')
                row.update(protocol='TCP', sport=struct.unpack('!H', tcp[:2])[0],
                           dport=struct.unpack('!H', tcp[2:4])[0], flags=tcp[13])
        result.append(row)
    return result


def validate_completed_observers(state, mac, active):
    require('Result=success' in state and 'ExecMainStatus=0' in state,
            'runner exited unsuccessfully despite pass marker')
    restored = [r for r in mac if r['started_ns'] > active + 5 * 10**9]
    require(len(restored) >= 2 and all(r['dns_ok'] and r['https_ok'] for r in restored),
            'Mac post-activation peer reads missing or failed')
    return len(restored)


def clock_gate_evidence(rows, packets):
    """Annotate an observed TLS reset; never relabel the original case as PASS."""
    infos = [r for r in rows if r['kind'] == 'console INFO']
    matches = []
    for failed in [r for r in rows if r['kind'] == 'https_failure' and
                   r['value']['type'] == 'ConnectionResetError']:
        when = failed['epoch_ns']
        resets = [p for p in packets if p.get('protocol') == 'TCP' and
                  p.get('source') == ADDRESS and p.get('target') == '192.168.1.117' and
                  p.get('source_mac') == '88:a2:9e:0a:60:df' and p.get('sport') == 18443 and
                  p['flags'] & 4 and abs(p['epoch_ns'] - when) < 100_000_000]
        if not resets:
            continue
        first, last = min(p['epoch_ns'] for p in resets), max(p['epoch_ns'] for p in resets)
        before = [r for r in infos if first - 10**9 <= r['epoch_ns'] <= first]
        after = [r for r in infos if last <= r['epoch_ns'] <= last + 10**9]
        if not before or not after:
            continue
        a, b = before[-1], after[0]
        if (a['value']['status']['clock_state'] == b['value']['status']['clock_state'] == 'unsynchronized'
                and a['value']['network']['accepted'] == b['value']['network']['accepted']):
            matches.append({'failure_epoch_ns': when, 'reset_epoch_ns': first,
                            'clock_before_epoch_ns': a['epoch_ns'], 'clock_after_epoch_ns': b['epoch_ns'],
                            'ntp_accepted': a['value']['network']['accepted'],
                            'interpretation': 'TLS reset while the documented unsynchronized-clock admission gate applies'})
    return matches


def assess_case(case, boot, revision='e4ff40a56180-dirty'):
    result = {'result': 'FAIL', 'observer_failure': False, 'failure_point': None,
              'failure_messages': [], 'scope': 'bounded B2/D2 physical case'}
    folders = sorted(case.glob('case-*/events.jsonl'))
    if len(folders) != 1:
        result.update(observer_failure=True, failure_messages=['missing unique Linux event file'])
        return result
    directory = folders[0].parent
    rows = read_rows(folders[0])
    selected = lambda kind: [r for r in rows if r['kind'] == kind]
    infos = selected('console INFO')
    result['usb_samples'] = len(infos)
    result['peer_failures'] = len(selected('PEER_RECOVERY_FAILURE'))
    result['outage_failures'] = len(selected('OUTAGE_LOOKUP_FAILURE'))
    result['baseline_failed'] = bool(selected('BASELINE_FAILURE'))
    result['failure_messages'] = [r['value'] for r in selected('CASE_FAILURE')]
    result['off_commands'] = len(selected('console WIFI OFF'))
    for path in case.glob('inspect-*/events.jsonl'):
        for row in read_rows(path):
            if row['kind'] == 'RECOVERY_INFO':
                v = row['value']
                result['final_info'] = v
                if (v.get('device_id') == DEVICE and v.get('revision') == revision
                        and v.get('recovery_boot') and v['status']['boot_id'] != boot
                        and v.get('fault_stage') in (15, 16)):
                    result['failure_point'] = {15: 'watchdog during final mDNS removal',
                                               16: 'watchdog during station disable'}[v['fault_stage']]
    try:
        # Failed cases still require authentic, complete observers before localization.
        for v in infos:
            if not v['value'].get('recovery_boot'):
                validate_info(v['value'], boot, revision)
        expected = read_rows(directory / 'usb-frames.jsonl')
        result['raw_usb_frames'] = strict_usb((directory / 'usb-wire.bin').read_bytes(), expected)
        packets = pcap(directory / 'mdns.pcap')
        diagnostic = diagnostic_packets(directory / 'diagnostic.pcap')
        for name, decoded in [('capture.log', packets), ('diagnostic-capture.log', diagnostic)]:
            text = (directory / name).read_text()
            match = re.search(r'(\d+) packets captured', text)
            require(match and int(match[1]) == len(decoded) and
                    re.search(r'\n0 packets dropped by kernel\n', text), 'capture missing/count/drop failure')
        result['mdns_packets'] = len(packets)
        result['diagnostic_packets'] = len(diagnostic)
        result['clock_gated_tls_resets'] = clock_gate_evidence(rows, diagnostic)
        result['pico_arp_packets'] = [p for p in diagnostic if p.get('protocol') == 'ARP' and p.get('source') == ADDRESS]
        result['linux_arp_requests'] = sum(p.get('protocol') == 'ARP' and p.get('operation') == 1 and
                                          p.get('source') == '192.168.1.117' and p.get('target') == ADDRESS for p in diagnostic)
        result['pico_tcp_packets'] = sum(p.get('protocol') == 'TCP' and p.get('source') == ADDRESS for p in diagnostic)
        result['tcp_probes'] = [r['value'] for r in selected('tcp_probe')]
        result['host_observations'] = len(selected('HOST_PATH'))
        require(result['host_observations'] >= 1, 'no independent host path evidence')
        fingerprints = {validate_host(r['value']) for r in selected('HOST_PATH')}
        require(len(fingerprints) == 1, 'host association changed in recorded evidence')
        # NIC receipt does not prove delivery to Avahi. This localizes a boundary,
        # not an internal daemon cause. Require a valid unicast reply within lookup.
        for row in selected('nss'):
            v = row['value']
            if v['exit'] == 0 or v['label'].startswith('off-'):
                continue
            valid = [p for p in packets if v['started_ns'] <= p['epoch_ns'] <= v['ended_ns'] and
                     p['source'] == ADDRESS and p['source_mac'] == '88:a2:9e:0a:60:df' and
                     p['destination'] == '192.168.1.117' and p['sport'] == p['dport'] == 5353 and
                     p['ttl'] == 255 and p['dns']['flags'] == 0x8400 and
                     any(r['type'] == 1 and r['name'] == NAME and r['address'] == ADDRESS and
                         r['ttl'] == 120 and r['cls'] == 0x8001 for r in p['dns']['records'])]
            if valid:
                result['failure_point'] = 'Linux received valid unicast mDNS answer but NSS lookup failed'
                result['localizing_packets'] = valid
        failures = selected('PEER_RECOVERY_FAILURE') + selected('BASELINE_FAILURE')
        mac = read_rows(case / 'mac-peer.jsonl')
        result['mac_success_during_failed_recovery'] = [r for r in mac if r.get('https_ok') and failures and
            min(f['epoch_ns'] for f in failures) <= r['https_started_ns'] <= max(f['epoch_ns'] for f in failures)]
        result['usb_max_gap_seconds'] = max((b['monotonic_ns'] - a['monotonic_ns']) / 1e9
                                            for a, b in zip(infos, infos[1:])) if len(infos) > 1 else None
        result['usb_monitor_faults'] = [r['value'] for r in selected('USB_MONITOR_FAILURE')]
        if selected('OBSERVERS_READY'):
            start = selected('OBSERVERS_READY')[0]['monotonic_ns']
            endings = selected('CASE_PASS') + selected('CASE_FAILURE')
            end = min(r['monotonic_ns'] for r in endings) if endings else start
            monitored = [r for r in infos if start <= r['monotonic_ns'] <= end]
            gaps = [(b['monotonic_ns'] - a['monotonic_ns']) / 1e9
                    for a, b in zip(monitored, monitored[1:])]
            result['independent_usb_max_gap_seconds'] = max(gaps, default=0)
            if not result['usb_monitor_faults']:
                require(monitored and result['independent_usb_max_gap_seconds'] < 2,
                        'independent USB observation gap exceeded two seconds')
        result['memory'] = {
            'heap_min': min(r['value']['heap_allocated_bytes'] for r in infos),
            'heap_max': max(r['value']['heap_allocated_bytes'] for r in infos),
            'heap_final': infos[-1]['value']['heap_allocated_bytes'],
            'tls_allocation_errors': max(r['value']['tls_allocation_failures'] for r in infos),
            'pool_allocation_errors': max(pool['errors'] for r in infos
                for pool in r['value']['network']['memory'].values()),
        }
        if selected('CASE_PASS'):
            result['acceptance'] = acceptance_audit(directory, case / 'mac-dns-sd.jsonl', revision)
            state = (case / 'service-state.txt').read_text().splitlines()
            active = selected('local_active')[0]['epoch_ns']
            result['mac_recovered_checks'] = validate_completed_observers(state, mac, active)
            result['result'] = 'PASS'
    except Exception as e:
        result['observer_failure'] = True
        result['audit_error'] = type(e).__name__ + ': ' + str(e)
        result['failure_point'] = None
    return result
