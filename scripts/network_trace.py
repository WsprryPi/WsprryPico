"""Offline network trace framing, identity and idle-window validation."""
import struct
from usb_inventory import require

def fingerprint(data):
    value = 2166136261
    for b in data:
        value = ((value ^ b) * 16777619) & 0xffffffff
    return value

def wire_packets(path):
    data = path.read_bytes()
    require(data[:4] == b'\xd4\xc3\xb2\xa1' and len(data) >= 24 and
            struct.unpack_from('<I', data, 20)[0] == 1, 'trace audit needs Ethernet PCAP')
    offset = 24
    while offset < len(data):
        require(offset + 16 <= len(data), 'truncated PCAP record')
        sec, usec, size, original = struct.unpack_from('<IIII', data, offset)
        offset += 16
        require(size == original and offset + size <= len(data), 'truncated packet')
        yield sec * 10**9 + usec * 1000, data[offset:offset+size]
        offset += size

def trace_events(rows, boot, revision, device):
    events = []
    cursor = None
    final_latest = None
    for row in rows:
        if row['kind'] != 'NETTRACE':
            continue
        v = row['value']
        require(v.get('ok') is True and v.get('device_id') == device and
                v.get('revision') == revision and v.get('boot_id') == boot, 'trace identity mismatch')
        t = v['trace']
        require(t['intact'] is True and t['install_errors'] == 0, 'trace hooks invalid')
        require(t['oldest'] == max(1, t['latest'] - 255) and
                t['overwritten'] == max(0, t['latest'] - 256), 'trace ring metadata inconsistent')
        require(len(t['events']) <= 8, 'unbounded trace page')
        for e in t['events']:
            require(cursor is None or e['seq'] == cursor + 1, 'trace sequence gap or duplicate')
            require(t['oldest'] <= e['seq'] <= t['latest'] and
                    e['us'] <= e['end_us'] and e['kind'] in (1,2,3), 'trace event metadata invalid')
            header = bytes.fromhex(e['header'])
            require(len(header) <= 66 and e['generation'] > 0, 'trace header/generation invalid')
            if e['kind'] != 3:
                require(len(header) >= 14, 'trace packet missing Ethernet metadata')
            cursor = e['seq']
            events.append(e)
        final_latest = t['latest']
    require(events and cursor == final_latest, 'trace not fully drained')
    return events

def idle_window(events, shutdown_us):
    """Require eight seconds of trace coverage and no TCP through shutdown."""
    cutoff = shutdown_us - 8_000_000
    tcp = []
    for event in events:
        header = bytes.fromhex(event['header'])
        if (event['kind'] in (1, 2) and len(header) >= 34 and
                header[12:14] == b'\x08\x00' and header[23] == 6 and
                cutoff <= event['us'] < shutdown_us):
            tcp.append(event)
    return {'idle_client_window_verified': bool(events) and not tcp and events[0]['us'] <= cutoff,
            'tcp_during_idle_window': tcp}
