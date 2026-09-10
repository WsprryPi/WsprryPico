#!/usr/bin/env python3
"""Offline DHCP/mDNS audit for the opt-in wspr5 hotspot fixture. No I/O to devices."""
import argparse
import json
import socket
import struct
from pathlib import Path
from phase11_4_trace_audit import wire_packets
from audit_phase11_4_mdns_conflict import dns

MAC = '88:a2:9e:0a:60:df'
NAME = 'wsprrypico-0a60df.local'


def packets(path):
    dhcp, records = [], []
    for epoch, wire in wire_packets(path):
        if len(wire) < 42 or wire[12:14] != b'\x08\x00':
            continue
        ip = wire[14:]
        ihl = (ip[0] & 15) * 4
        if ip[9] != 17 or ihl < 20 or struct.unpack_from('>H', ip, 6)[0] & 0x3fff:
            continue
        total = struct.unpack_from('>H', ip, 2)[0]
        assert total <= len(ip)
        assert total >= ihl + 8
        udp = ip[ihl:total]
        sport, dport, length, _ = struct.unpack_from('>HHHH', udp)
        assert length == len(udp)
        body = udp[8:]
        source_mac = wire[6:12].hex(':')
        if {sport, dport} == {67, 68} and len(body) >= 240 and body[28:34].hex(':') == MAC:
            assert body[1:3] == b'\x01\x06'
            assert (body[0], sport, dport) in ((1, 68, 67), (2, 67, 68))
            assert body[236:240] == b'\x63\x82\x53\x63'
            options, index = {}, 240
            while index < len(body):
                key = body[index]
                index += 1
                if key == 255:
                    break
                if key == 0:
                    continue
                assert index < len(body) and key not in options
                size = body[index]
                index += 1
                assert index + size <= len(body)
                options[key] = body[index:index + size]
                index += size
            assert len(options.get(53, b'')) == 1
            dhcp.append({'epoch_ns': epoch, 'type': options.get(53, b'\0')[0],
                         'xid': body[4:8].hex(), 'yiaddr': socket.inet_ntoa(body[16:20]),
                         'ciaddr': socket.inet_ntoa(body[12:16]),
                         'requested': socket.inet_ntoa(options[50]) if 50 in options else None,
                         'source_mac': source_mac, 'source': socket.inet_ntoa(ip[12:16])})
        if sport == 5353 and source_mac == MAC:
            message = dns(body)
            if message['flags'] & 0x8000:
                for record in message['records']:
                    if record['name'] == NAME and record['type'] == 1:
                        records.append(dict(epoch_ns=epoch, **record))
    return {'dhcp': dhcp, 'a_records': records}


def assess(directory):
    if not __debug__:
        raise RuntimeError('Audits require assertions; do not use Python -O')
    rows = [json.loads(s) for s in (directory / 'events.jsonl').read_text().splitlines()]
    cases = []
    boundaries = [0] + [r['epoch_ns'] for r in rows if r['kind'] == 'AP_COMPARISON_BEGIN']
    assert len(boundaries) <= 2, 'Only the two recorded hardware arrangements are supported'
    for index, start in enumerate(boundaries):
        end = boundaries[index + 1] if index + 1 < len(boundaries) else 2**64
        group = [r for r in rows if start <= r['epoch_ns'] < end]
        changes = [r for r in group if r['kind'] == 'DHCP_BINDING_CHANGE']
        if not changes:
            continue
        assert len(changes) == 1, 'Unaccounted repeated transition'
        mark = changes[0]
        case_root = directory / 'onboard-ap' if index == 0 and len(boundaries) > 1 else directory
        restore = next((r['epoch_ns'] for r in group if r['kind'] == 'CONFIG' and r['epoch_ns'] > mark['epoch_ns']), end)
        parsed = packets(case_root / 'ap.pcap')
        new = [p for p in parsed['dhcp'] if mark['epoch_ns'] <= p['epoch_ns'] < restore and p['type'] == 5 and p['yiaddr'] == '10.77.14.20']
        assert new, 'No captured real DHCP ACK for the new address'
        ack = new[0]
        assert ack['source'] == '10.77.14.1'
        expected_ap = '2c:cf:67:62:76:66' if index == 0 else 'e8:4e:06:ae:d7:09'
        assert ack['source_mac'] == expected_ap, 'Unexpected DHCP server MAC'
        assert any(p['type'] == 3 and p['xid'] == ack['xid'] and p['requested'] == '10.77.14.20'
                   and p['source_mac'] == MAC and mark['epoch_ns'] <= p['epoch_ns'] <= ack['epoch_ns']
                   for p in parsed['dhcp']), 'New lease lacks matching Pico DHCPREQUEST'
        infos = [r for r in group if r['kind'] == 'INFO' and mark['epoch_ns'] <= r['epoch_ns'] < restore]
        assert infos and all(r['value']['status']['boot_id'] == mark['value']['boot'] for r in infos)
        assert all(r['value']['device_id'] == 'fd6127d11d6aca42a9905fa3fb1bf1d5'
                   and r['value']['status']['engine'] == 'inhibited-standalone-simulator'
                   and r['value']['status']['output_active'] is False
                   and r['value']['status']['enabled'] is False for r in infos)
        assert any(r['value']['network']['ipv4'] == '10.77.14.20' for r in infos)
        positives = [r for r in parsed['a_records'] if ack['epoch_ns'] <= r['epoch_ns'] < restore and r['ttl'] > 0]
        assert positives and all(r['address'] == '10.77.14.20' and r['cls'] == 0x8001 for r in positives)
        before = [r for r in group if r['kind'] == 'CLIENT_PASS' and r['value']['address'] == '10.77.14.10' and r['epoch_ns'] < mark['epoch_ns']]
        after = [r for r in group if r['kind'] == 'CLIENT_PASS' and r['value']['address'] == '10.77.14.20' and ack['epoch_ns'] <= r['epoch_ns'] < restore]
        assert before and before[-1]['value']['boot'] == mark['value']['boot']
        resolved = [r for r in group if r['kind'] == 'client_native_dns' and ack['epoch_ns'] <= r['epoch_ns'] < restore]
        assert resolved and resolved[0]['value']['addresses'] == ['10.77.14.20'], 'Missing current native resolver evidence'
        if after:
            assert before[-1]['value']['fingerprint'] == after[0]['value']['fingerprint']
            assert before[-1]['value']['boot'] == after[0]['value']['boot'] == mark['value']['boot']
        cases.append({'case': index + 1, 'hardware': 'onboard AP / USB client' if index == 0 else 'USB AP / onboard client',
                      'real_dhcp_change': True, 'same_boot': mark['value']['boot'],
                      'new_ack': ack, 'new_positive_a_records': len(positives),
                      'independent_client_complete': bool(after),
                      'recovery_seconds_from_binding': None if not after else (after[0]['epoch_ns'] - mark['epoch_ns']) / 1e9,
                      'retained_command_failures': sum(r['kind'] == 'COMMAND_FAILURE' for r in group)})
    assert cases
    return {'cases': cases, 'scope': 'Controlled DHCP and independent Linux client; not Mac/Chrome or RF acceptance'}


if __name__ == '__main__':
    if not __debug__:
        raise RuntimeError('Audits require assertions; do not use Python -O')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    args = p.parse_args()
    print(json.dumps(assess(args.directory), indent=2))
