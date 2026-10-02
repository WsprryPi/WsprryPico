#!/usr/bin/env python3
"""Opt-in read-only AP-interface proof; never associate or configure networking.

Run on the acquisition host after capture finalization, using a separately
approved, already-associated Wi-Fi interface. Phone observation stays separate.
"""
import argparse
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time

from phase12_gp14_rf import (campaign_lock, check_info, check_long_ap_final, console, digest, require,
                            validate_packet)

ADDRESS = '192.168.4.1'
WINDOW_NS = 90_000_000_000


def window(attempt, now, host_boot, hostname):
    bracket = attempt['release_host_bracket']
    require(bracket['host_boot_id'] == host_boot and bracket['hostname'] == hostname,
            'collector must share acquisition host and monotonic clock boot')
    start, end = (int(bracket[key]) for key in ('earliest_monotonic_ns', 'latest_monotonic_ns'))
    require(0 < start <= end <= now <= start + WINDOW_NS,
            'release bracket invalid or conservative 90-second window expired')
    return start + WINDOW_NS


def association(output, ssid, bssid):
    match = re.search(r'^Connected to ([0-9a-f:]{17}) \(on ([^ )]+)\)', output, re.M)
    network = re.search(r'^\s*SSID: (.+)$', output, re.M)
    require(match is not None and network is not None and
            match[1].lower() == bssid.lower() and network[1] == ssid,
            'approved AP association not observed')
    return dict(bssid=match[1].lower(), interface=match[2], ssid=network[1])


def http_get(interface, path, deadline):
    begin = time.monotonic_ns()
    remaining = (deadline - begin) / 1e9
    require(remaining > 0, 'AP proof window expired before HTTP')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(min(3, remaining))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, interface.encode() + b'\0')
        sock.connect((ADDRESS, 80))
        source = sock.getsockname()[0]
        require(ipaddress.ip_address(source) in ipaddress.ip_network('192.168.4.0/24') and
                source != ADDRESS, 'HTTP source is not an AP subnet client')
        sock.sendall(('GET ' + path + ' HTTP/1.1\r\nHost: ' + ADDRESS +
                      '\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n').encode())
        response = http.client.HTTPResponse(sock)
        response.begin()
        require(response.status == 200 and response.getheader('Location') is None,
                'read-only AP HTTP failed or redirected')
        body = response.read(1_048_577)
        require(len(body) <= 1_048_576 and time.monotonic_ns() <= deadline,
                'AP HTTP oversized or outside admitted window')
        return dict(path=path, status=200, destination=ADDRESS, source=source,
                    bound_interface=interface, body_sha256=hashlib.sha256(body).hexdigest(),
                    size_bytes=len(body), begin_monotonic_ns=str(begin),
                    end_monotonic_ns=str(time.monotonic_ns())), body
    finally:
        sock.close()


def validate(proof, attempt, packet, attempt_hash, packet_hash):
    require(proof['schema'] == 'phase12-gp14-ap-interface-v1' and
            proof['attempt_sha256'] == attempt_hash and proof['packet_sha256'] == packet_hash and
            proof['boot_id'] == attempt['boot_id'] == attempt['final_boot_id'], 'AP proof binding')
    require(attempt['case'] == 'long_ap' and attempt['target_gesture_checks_passed'] is True and
            attempt['packet_sha256'] == packet_hash, 'long-AP target gesture not verified')
    window(attempt, int(proof['completed_monotonic_ns']), proof['host_boot_id'], proof['hostname'])
    require(int(proof['started_monotonic_ns']) >= int(attempt['release_host_bracket']['latest_monotonic_ns'])
            and int(proof['started_monotonic_ns']) <= int(proof['completed_monotonic_ns']),
            'AP proof collection interval invalid')
    interface = proof['approved_ap_interface']
    require(re.fullmatch(r'[A-Za-z0-9_.-]{1,15}', interface) and
            interface != proof['management_interface'], 'AP/management interface separation required')
    before, after = proof['association_before'], proof['association_after']
    require(before == after and before['interface'] == interface and
            before['ssid'] == proof['approved_ssid'] and before['bssid'] == proof['approved_bssid'],
            'AP association changed or unbound')
    require(proof['identity']['device_id'] == packet['device_id'] and
            proof['identity']['firmware'] == attempt['firmware'], 'AP identity/firmware mismatch')
    for key in ('usb_before', 'usb_after'):
        observation = proof[key]
        check_info(observation['info'], packet, attempt['boot_id'])
        check_long_ap_final(observation['info'])
        require(observation['info']['firmware'] == attempt['firmware'] and
                int(proof['started_monotonic_ns']) <= int(observation['begin_monotonic_ns']) <=
                int(observation['end_monotonic_ns']) <= int(proof['completed_monotonic_ns']),
                'same-boot USB observation unbound')
    require(int(proof['usb_before']['end_monotonic_ns']) <= int(proof['usb_after']['begin_monotonic_ns']),
            'USB observation ordering')
    require([item['path'] for item in proof['http']] == ['/local/v1/identity', '/'], 'HTTP paths')
    for item in proof['http']:
        require(int(proof['usb_before']['end_monotonic_ns']) <= int(item['begin_monotonic_ns']) <=
                int(item['end_monotonic_ns']) <= int(proof['usb_after']['begin_monotonic_ns']),
                'HTTP is not bracketed by same-boot USB health')
        require(item['status'] == 200 and item['destination'] == ADDRESS and
                item['bound_interface'] == interface and item['size_bytes'] > 0 and
                item['source'] != ADDRESS and
                ipaddress.ip_address(item['source']) in ipaddress.ip_network('192.168.4.0/24'),
                'AP-interface HTTP evidence missing')
    require(proof['phone_observation'] == 'PENDING', 'collector cannot prove a phone observation')


def collect(root, interface, management, ssid, bssid):
    with campaign_lock(root.parent):
        require(not (root/'ap-interface-proof.json').exists(), 'AP interface proof already retained')
        previous_mask = os.umask(0o077)
        try:
            return _collect_locked(root, interface, management, ssid, bssid)
        finally:
            os.umask(previous_mask)


def _collect_locked(root, interface, management, ssid, bssid):
    attempt_path, packet_path = root/'attempt.json', root/'packet.json'
    attempt, packet = json.loads(attempt_path.read_text()), json.loads(packet_path.read_text())
    validate_packet(packet, verify_files=False)
    host_boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    hostname, started = socket.gethostname(), time.monotonic_ns()
    deadline = window(attempt, started, host_boot, hostname)
    require(attempt['case'] == 'long_ap' and attempt.get('target_gesture_checks_passed') is True and
            attempt['boot_id'] == attempt['final_boot_id'], 'completed same-boot long-AP required')
    require(re.fullmatch(r'[A-Za-z0-9_.-]{1,15}', interface) and interface != management,
            'explicit separate approved AP interface required')
    require(re.fullmatch(r'[0-9a-f:]{17}', bssid), 'approved AP BSSID required')
    require((Path('/sys/class/net')/interface/'phy80211').exists(), 'AP interface is not Wi-Fi')
    hashes = dict(attempt_sha256=digest(attempt_path), packet_sha256=digest(packet_path))
    def usb():
        require(time.monotonic_ns() < deadline, 'AP proof window expired before USB observation')
        begin = time.monotonic_ns()
        info = console()  # Exclusive CDC INFO only; no occupied-port retry or mutation.
        check_info(info, packet, attempt['boot_id'])
        check_long_ap_final(info)
        require(info['firmware'] == attempt['firmware'], 'USB firmware changed')
        return dict(begin_monotonic_ns=str(begin), end_monotonic_ns=str(time.monotonic_ns()), info=info)
    def link():
        remaining = (deadline - time.monotonic_ns()) / 1e9
        require(remaining > 0, 'AP proof window expired before association observation')
        result = subprocess.run(['iw', 'dev', interface, 'link'], check=True, capture_output=True,
                                text=True, timeout=min(3, remaining))
        return association(result.stdout, ssid, bssid)
    usb_before = usb()
    before = link()
    identity_http, identity_body = http_get(interface, '/local/v1/identity', deadline)
    page_http, _ = http_get(interface, '/', deadline)
    after = link()
    usb_after = usb()
    proof = dict(schema='phase12-gp14-ap-interface-v1', **hashes, boot_id=attempt['boot_id'],
                 host_boot_id=host_boot, hostname=hostname, started_monotonic_ns=str(started),
                 completed_monotonic_ns=str(time.monotonic_ns()), approved_ap_interface=interface,
                 management_interface=management, approved_ssid=ssid, approved_bssid=bssid,
                 association_before=before, association_after=after,
                 usb_before=usb_before, usb_after=usb_after,
                 identity=json.loads(identity_body), http=[identity_http, page_http],
                 phone_observation='PENDING')
    require(digest(attempt_path) == hashes['attempt_sha256'] and
            digest(packet_path) == hashes['packet_sha256'], 'acquisition changed during collection')
    validate(proof, attempt, packet, **dict(attempt_hash=hashes['attempt_sha256'],
                                        packet_hash=hashes['packet_sha256']))
    with (root/'ap-interface-proof.json').open('x') as out:
        out.write(json.dumps(proof, indent=2) + '\n')
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    parser.add_argument('--run', action='store_true', required=True)
    parser.add_argument('--approved-ap-interface', required=True)
    parser.add_argument('--management-interface', required=True)
    parser.add_argument('--approved-ssid', required=True)
    parser.add_argument('--approved-bssid', required=True)
    args = parser.parse_args()
    collect(args.run_directory, args.approved_ap_interface, args.management_interface,
            args.approved_ssid, args.approved_bssid.lower())
    print('AP interface proof retained; phone observation and independent RF assessment pending')


if __name__ == '__main__':
    main()
