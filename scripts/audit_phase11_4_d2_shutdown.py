#!/usr/bin/env python3
"""Offline D2 shutdown sub-assessment; never grants full discovery acceptance."""
import argparse
import json
import re
from pathlib import Path

from phase11_4_loop_common import require, validate_info, validate_host, DEVICE, NAME, ADDRESS
from phase11_4_loop_audit import strict_usb
from phase11_4_trace_audit import trace_events, idle_window, wire_packets
from inhibited_network_acceptance import check_status
from audit_phase11_4_mdns_conflict import pcap


def shutdown_window(rows, boot, revision):
    """Assess continuity and observed disable independently of peer delivery."""
    infos = [r for r in rows if r['kind'] == 'console INFO']
    require(len(infos) >= 3, 'missing USB observations')
    validate_info(infos[0]['value'], boot, revision)
    require(all(r['value'].get('device_id') == DEVICE and r['value'].get('revision') == revision
                for r in infos), 'observation from another device or image')
    changed = [r for r in infos if r['value'].get('recovery_boot') or
               r['value']['status']['boot_id'] != boot]
    if changed:
        value = changed[0]['value']
        return {'result': 'FAIL_BOOT_CHANGED', 'observed_boot': value['status']['boot_id'],
                'recovery_boot': value.get('recovery_boot'),
                'fault_stage': value.get('fault_stage'), 'epoch_ns': changed[0]['epoch_ns']}
    initial = infos[0]['value']
    for row in infos:
        info = row['value']
        validate_info(info, boot, revision)
        require(info['status']['state'] == 'empty', 'nonempty device')
        for key in ('station', 'schedules', 'watermark_utc_ns', 'expires_utc_s', 'enabled', 'suspended'):
            require(info['status'][key] == initial['status'][key], 'saved state changed: ' + key)
    starts = [r for r in rows if r['kind'] == 'off_begin']
    require(len(starts) == 1, 'missing or repeated OFF trigger')
    stops = [r for r in rows if r['kind'] == 'on_begin']
    require(len(stops) == 1, 'missing or repeated ON trigger')
    off, on = starts[0], stops[0]
    require(on['monotonic_ns'] - off['monotonic_ns'] >= 150_000_000_000,
            'outage shorter than 150 seconds')
    controls = [r for r in rows if r['kind'].startswith('console ') and r['kind'] != 'console INFO']
    require([r['kind'] for r in controls] == ['console WIFI OFF', 'console WIFI ON'] and
            all(r['value'].get('ok') is True for r in controls), 'unexpected or failed controls')
    require(off['epoch_ns'] <= controls[0]['epoch_ns'] < on['epoch_ns'] <=
            controls[1]['epoch_ns'], 'control acknowledgements outside trigger windows')
    require(infos[0]['epoch_ns'] < off['epoch_ns'] < on['epoch_ns'] < infos[-1]['epoch_ns'],
            'USB observations do not bracket complete lifecycle')
    gaps = [(b['monotonic_ns'] - a['monotonic_ns']) / 1e9 for a, b in zip(infos, infos[1:])]
    require(all(0 < gap < 7 for gap in gaps), 'USB gap cannot support bounded continuity')
    require(not any(r['kind'] == 'USB_MONITOR_FAILURE' for r in rows), 'USB observer failed')
    disabled = [r for r in infos if off['epoch_ns'] < r['epoch_ns'] < on['epoch_ns'] and
                r['value']['network']['enabled'] is False and
                r['value']['network']['advertised_hostname'] == '']
    require(disabled, 'missing independently observed disabled state')
    return {'result': 'NO_WATCHDOG_IN_OBSERVED_WINDOW', 'boot_id': boot,
            'off_seconds': (on['monotonic_ns'] - off['monotonic_ns']) / 1e9,
            'usb_samples': len(infos), 'maximum_usb_gap_seconds': max(gaps)}


def completed_shutdown_marks(events, lower, upper):
    """Require a complete sequence in this OFF window, excluding earlier cycles."""
    marks = [e for e in events if e['kind'] == 3 and lower <= e['us'] <= upper]
    starts = [e for e in marks if e['result'] == 2]
    require(len(starts) == 1, 'missing or repeated goodbye-start marker')
    start = starts[0]
    end = next((e for e in marks if e['result'] == 3 and e['seq'] > start['seq']), None)
    entering = next((e for e in marks if e['result'] == 4 and end and e['seq'] > end['seq']), None)
    disabled = next((e for e in marks if e['result'] == 5 and entering and e['seq'] > entering['seq']), None)
    require(end and entering and disabled, 'missing completed withdrawal/disable markers')
    require(start['us'] <= end['us'] <= entering['us'] <= disabled['us'],
            'nonmonotonic shutdown markers')
    return start, end, entering, disabled


def audit(directory, boot, revision):
    rows = [json.loads(line) for line in (directory / 'events.jsonl').read_text().splitlines()]
    require(all(a['epoch_ns'] <= b['epoch_ns'] and a['monotonic_ns'] <= b['monotonic_ns']
                for a, b in zip(rows, rows[1:])), 'nonmonotonic evidence')
    shutdown = shutdown_window(rows, boot, revision)
    if shutdown['result'] == 'FAIL_BOOT_CHANGED':
        return {'shutdown': shutdown, 'full_D2': 'FAIL', 'scope': 'reset observation; review retained USB authority'}
    frames = [json.loads(line) for line in (directory / 'usb-frames.jsonl').read_text().splitlines()]
    strict_usb((directory / 'usb-wire.bin').read_bytes(), frames)
    requests = [r['value'] for r in rows if r['kind'] == 'wtp_request']
    replies = [r for r in frames if r['type'] == 'response']
    require(len(requests) == len(frames) == len(replies), 'USB response count mismatch')
    require(len({r['session'] for r in requests}) == 1, 'USB session changed')
    require(len({r['request_id'] for r in replies}) == len(replies), 'replayed USB response')
    for request, reply in zip(requests, replies):
        require(request['op'] in ('HELLO', 'CAPS', 'STATUS') and reply['op'] == request['op'] and
                reply['session_id'] == request['session'] and reply.get('ok') is True,
                'unexpected USB operation or response')
        if reply['op'] == 'HELLO':
            require(reply['body']['device_id'] == DEVICE and reply['body']['boot_id'] == boot,
                    'wrong USB HELLO identity')
        elif reply['op'] == 'CAPS':
            require(reply['body']['engine'] == 'inhibited-standalone-simulator', 'wrong engine')
        else:
            check_status(reply['body'], boot, unowned=True)
    events = trace_events(rows, boot, revision)
    off = next(r['epoch_ns'] for r in rows if r['kind'] == 'off_begin')
    on = next(r['epoch_ns'] for r in rows if r['kind'] == 'on_begin')
    infos = [r for r in rows if r['kind'] == 'console INFO']
    before_off = [r for r in infos if r['epoch_ns'] < off][-1]
    before_on = [r for r in infos if r['epoch_ns'] < on][-1]
    lower = int(before_off['value']['status']['monotonic_now_ns']) // 1000
    upper = int(before_on['value']['status']['monotonic_now_ns']) // 1000
    # Initial ring context can contain marks from an earlier case. Only the
    # current OFF interval can establish this case's shutdown completion.
    start, end, entering, disabled = completed_shutdown_marks(events, lower, upper)
    shutdown.update(trace_events=len(events), goodbye_call_us=end['us']-start['us'],
                    goodbye_return_to_disable_entry_us=entering['us']-end['us'],
                    station_disable_call_us=disabled['us']-entering['us'],
                    **idle_window(events, start['us']))
    paths = [validate_host(r['value'], profile='921301fe-cdfd-4965-8ac7-c96e9d908ea6',
                           ssid='Bohica-IoT') for r in rows if r['kind'] == 'HOST_PATH']
    require(paths and len(set(paths)) == 1, 'host path changed')
    packets = pcap(directory / 'mdns.pcap')
    for name in ('capture.log', 'diagnostic-capture.log'):
        statistics = (directory/name).read_text()
        require(re.search(r'^0 packets dropped by kernel$', statistics, re.MULTILINE),
                'capture loss or absent statistics')
        count = re.search(r'^(\d+) packets captured$', statistics, re.MULTILINE)
        capture = 'mdns.pcap' if name == 'capture.log' else 'diagnostic.pcap'
        require(count and int(count[1]) == len(list(wire_packets(directory/capture))),
                'capture count mismatch')
    require(len([r for r in rows if r['kind'] == 'capture_stop' and r['value']['exit'] == 0]) == 2,
            'captures did not exit normally')
    off = next(r['epoch_ns'] for r in rows if r['kind'] == 'off_begin')
    on = next(r['epoch_ns'] for r in rows if r['kind'] == 'on_begin')
    def matching(packet, ttl):
        return (packet.get('source') == ADDRESS and packet.get('source_mac') == '88:a2:9e:0a:60:df' and
                packet.get('sport') == packet.get('dport') == 5353 and packet.get('ttl') == 255 and
                packet.get('dns', {}).get('flags') == 0x8400 and
                any(r.get('type') == 1 and r.get('name') == NAME and r.get('address') == ADDRESS and
                    r.get('ttl') == ttl and r.get('cls') == 0x8001 for r in packet['dns']['records']))
    baseline = [p for p in packets if p['epoch_ns'] < off and matching(p, 120)]
    goodbyes = [p for p in packets if off <= p['epoch_ns'] < on and matching(p, 0) and
               any(r.get('type') == 12 and r.get('name') == '47.1.168.192.in-addr.arpa' and
                   r.get('target') == NAME and r.get('ttl') == 0 and r.get('cls') == 0x8001
                   for r in p['dns']['records'])]
    positives = [p for p in packets if p['epoch_ns'] > on and matching(p, 120)]
    failures = [r for r in rows if r['kind'] in ('BASELINE_FAILURE', 'CASE_FAILURE',
                'OUTAGE_LOOKUP_FAILURE', 'PEER_RECOVERY_FAILURE', 'https_failure')]
    return {'shutdown': shutdown, 'host_path': paths[0],
            'delivery': {'captured_baseline': len(baseline), 'captured_matching_goodbyes': len(goodbyes),
                         'captured_recovery_positives': len(positives), 'capture_packets': len(packets)},
            'retained_failures': failures, 'full_D2': 'NOT_GRANTED_BY_THIS_SUBASSESSMENT',
            'scope': 'USB shutdown continuity and packet observations; complete native cache/recovery audit remains required'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--boot', required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.directory, args.boot, args.revision), indent=2))
