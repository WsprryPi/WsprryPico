"""Offline Pico boundary trace validation. Submission is never radio delivery."""
import json
import struct
from pathlib import Path
from phase11_4_loop_common import DEVICE, require


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


def trace_events(rows, boot, revision):
    events = []
    cursor = None
    final_latest = None
    for row in rows:
        if row['kind'] != 'NETTRACE':
            continue
        v = row['value']
        require(v.get('ok') is True and v.get('device_id') == DEVICE and
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


def assess_trace(directory, boot, revision):
    rows = [json.loads(s) for s in (directory/'events.jsonl').read_text().splitlines()]
    events = trace_events(rows, boot, revision)
    if not any(r['kind']=='off_begin' for r in rows):
        return {'trace_events':len(events), 'first_seq':events[0]['seq'],
                'last_seq':events[-1]['seq'], 'failure_boundary':None,
                'scope':'read-only diagnostic; no B2/D2 cycle', 'events':events}
    marks = [e for e in events if e['kind'] == 3]
    goodbye_start = next(e for e in marks if e['result'] == 2)
    goodbye_end = next(e for e in marks if e['result'] == 3 and e['seq'] > goodbye_start['seq'])
    disabled = next((e for e in marks if e['result'] == 4 and e['seq'] > goodbye_end['seq']), None)
    installed = next((e for e in marks if e['result'] == 1 and e['seq'] > goodbye_end['seq']), None)
    require(events[0]['seq'] < goodbye_start['seq'], 'trace lacks pre-withdrawal coverage')
    if installed is None or disabled is None:
        require(any(r['kind']=='CASE_FAILURE' for r in rows) and
                any(r['kind']=='USB_MONITOR_FAILURE' for r in rows),
                'missing lifecycle trace without observed target interruption')
    mdns = []
    for epoch, wire in wire_packets(directory/'mdns.pcap'):
        if len(wire) < 42 or wire[12:14] != b'\x08\x00':
            continue
        ihl = (wire[14] & 15)*4
        start = 14 + ihl
        require(start+8 <= len(wire), 'short captured UDP')
        size = int.from_bytes(wire[start+4:start+6], 'big')
        require(size >= 8 and start+size <= len(wire), 'bad captured UDP length')
        if wire[6:12].hex() == '88a29e0a60df':
            mdns.append({'epoch_ns':epoch, 'hash':fingerprint(wire[start+8:start+size]),
                         'header': (wire[:34]+wire[start:start+20]).hex(), 'length':len(wire)})
    submitted = [e for e in events if goodbye_start['seq'] < e['seq'] < goodbye_end['seq']
                 and e['kind'] == 2 and bytes.fromhex(e['header'])[12:14] == b'\x08\x00']
    recovery = [e for e in events if installed and e['seq'] > installed['seq']]
    arp = lambda e: bytes.fromhex(e['header'])[12:14] == b'\x08\x06'
    request = lambda e: arp(e) and bytes.fromhex(e['header'])[20:22] == b'\x00\x01' and bytes.fromhex(e['header'])[38:42] == bytes([192,168,1,47])
    replies = [e for e in recovery if arp(e) and e['kind']==2 and bytes.fromhex(e['header'])[20:22]==b'\x00\x02']
    incoming = [e for e in recovery if e['kind']==1 and request(e)]
    result = {'trace_events':len(events), 'first_seq':events[0]['seq'], 'last_seq':events[-1]['seq'],
              'goodbye_submissions':submitted, 'goodbye_fingerprints_observed':[
                  e['hash'] for e in submitted if any(p['hash']==e['hash'] and p['header']==e['header'] and
                      p['length']==e['length'] for p in mdns)],
              'withdrawal_to_disable_us':disabled['us']-goodbye_start['us'] if disabled else None,
              'recovery_trace_present':installed is not None,
              'recovery_arp_requests_received':incoming, 'recovery_arp_replies_submitted':replies,
              'recovery_tx_errors':[e for e in recovery if e['kind']==2 and e['result']!=0],
              'max_recorded_tx_us':max((e['end_us']-e['us'] for e in events if e['kind']==2),default=0),
              'failure_boundary':None}
    if any(r['kind']=='IDLE_CLIENT_WINDOW' for r in rows):
        result.update(idle_window(events, goodbye_start['us']))
    if any(r['kind']=='OUTAGE_LOOKUP_FAILURE' for r in rows) and submitted and not result['goodbye_fingerprints_observed']:
        if all(e['result']==0 for e in submitted):
            result['failure_boundary']='Goodbye submitted successfully through station linkoutput; no matching frame in client capture'
        else:
            result['failure_boundary']='Goodbye station linkoutput rejected submission'
    # These remain bounded observations, not attribution to an AP or radio component.
    return result


def arp_failure_window(directory, boot, revision):
    """Correlate one bounded explicit ARP probe window; never claim radio receipt."""
    import statistics
    rows = [json.loads(s) for s in (directory/'events.jsonl').read_text().splitlines()]
    events = trace_events(rows, boot, revision)
    start = next(r['epoch_ns'] for r in rows if r['kind']=='fault_arp_begin')
    end = next(r['epoch_ns'] for r in rows if r['kind']=='fault_broadcast_arp')
    probe = next(r['value'] for r in rows if r['kind']=='fault_broadcast_arp')
    require('Received 0 response(s)' in probe['stdout'] and probe['exit'] != 0,
            'not a failed broadcast probe')
    infos = [r for r in rows if r['kind']=='console INFO' and start-10**9 <= r['epoch_ns'] <= end+10**9]
    require(len(infos)>=2 and all(r['value']['device_id']==DEVICE and
            r['value']['revision']==revision and r['value']['status']['boot_id']==boot for r in infos),
            'missing identity-bound clock alignment')
    offsets = [r['epoch_ns'] - int(r['value']['status']['monotonic_now_ns']) for r in infos]
    require(max(offsets)-min(offsets)<100_000_000, 'clock alignment uncertainty exceeds 100ms')
    offset = int(statistics.median(offsets))
    require(events[0]['us']*1000+offset < start and events[-1]['us']*1000+offset > end,
            'trace does not bracket ARP window')
    captured = [(ns,wire[:42]) for ns,wire in wire_packets(directory/'diagnostic.pcap')
                if wire[12:14]==b'\x08\x06' and start <= ns <= end+100_000_000]
    pairs = []
    for rx in events:
        b = bytes.fromhex(rx['header'])
        when = rx['us']*1000+offset
        if not (rx['kind']==1 and start <= when <= end and len(b)==42 and
                b[6:12].hex()=='90de8047b9da' and b[20:22]==b'\x00\x01' and
                b[28:32]==bytes([192,168,1,117]) and b[38:42]==bytes([192,168,1,47])):
            continue
        require(any(wire==b and abs(ns-when)<100_000_000 for ns,wire in captured),
                'Pico ARP request not matched to contemporaneous Linux capture')
        expected = (b[6:12] + bytes.fromhex('88a29e0a60df0806000108000604000288a29e0a60df') +
                    bytes([192,168,1,47]) + b[6:12] + bytes([192,168,1,117]))
        replies = [tx for tx in events if tx['kind']==2 and tx['seq']>rx['seq'] and
                   0<=tx['us']-rx['us']<1000 and bytes.fromhex(tx['header'])==expected]
        for tx in replies:
            pairs.append({'request':rx,'reply':tx,'client_reply_captured':any(w==expected for _,w in captured)})
    require(pairs, 'no matched request/reply pair in failed window')
    return {'clock_alignment_spread_ns':max(offsets)-min(offsets), 'window_start_ns':start,
            'window_end_ns':end,'pairs':pairs,'probe':probe,
            'interpretation':'Matched ARP request reached Pico; reply submission result and client capture retained separately'}
