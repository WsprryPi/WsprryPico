#!/usr/bin/env python3
"""Opt-in Linux loopback-only nft test in a newly created network namespace."""
import argparse
import errno
import json
import os
import select
import socket
import struct
import subprocess
import time

from phase11_5_inventory import require
from phase11_5_r3_ack_filter import rules


def checksum(data):
    data += b'\0' if len(data) % 2 else b''
    total = sum(struct.unpack('!' + 'H' * (len(data) // 2), data))
    while total >> 16:
        total = (total & 65535) + (total >> 16)
    return (~total) & 65535


def datagram(ident, words, flags, payload):
    source, destination = socket.inet_aton('127.0.0.1'), socket.inet_aton('127.0.0.2')
    tcp = bytearray(struct.pack('!HHIIBBHHH', 45000, 18443, ident * 100, 1,
                                words << 4, flags, 1024, 0, 0) + bytes(words * 4 - 20) + payload)
    pseudo = source + destination + struct.pack('!BBH', 0, 6, len(tcp))
    struct.pack_into('!H', tcp, 16, checksum(pseudo + tcp))
    ip = bytearray(struct.pack('!BBHHHBBH4s4s', 0x45, 0, 20 + len(tcp), ident, 0, 64, 6, 0,
                              source, destination))
    struct.pack_into('!H', ip, 10, checksum(ip))
    return bytes(ip + tcp)


def exercise(parent):
    require(os.geteuid() == 0 and os.readlink('/proc/self/ns/net') != parent,
            'Run only as root in a newly unshared network namespace')
    links = json.loads(subprocess.check_output(['/usr/sbin/ip', '-j', 'link'], text=True))
    require([v['ifname'] for v in links] == ['lo'], 'Self-test namespace contains a non-loopback interface')
    subprocess.run(['/usr/sbin/ip', 'link', 'set', 'lo', 'up'], check=True, timeout=2)
    table = 'r3b2_loopbackcheck'
    text = rules(table, 45000, '127.0.0.1', '127.0.0.2')
    installed = False
    with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0800)) as capture, \
         socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW) as sender:
        capture.bind(('lo', 0))
        capture.setblocking(False)
        sender.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        try:
            subprocess.run(['/usr/sbin/nft', '-f', '-'], input=text, text=True, check=True, timeout=2)
            installed = True
            expected, dropped, cases = set(), set(), []
            for words in range(5, 16):
                for name, flags, payload, blocked in (
                    ('empty-ack', 16, b'', True), ('data-without-psh', 16, b'client hello', False),
                    ('data-with-psh', 24, b'client hello', False), ('syn', 2, b'', False),
                    ('fin-ack', 17, b'', False), ('rst-ack', 20, b'', False)):
                    ident = 40000 + len(cases)
                    (dropped if blocked else expected).add(ident)
                    wire = datagram(ident, words, flags, payload)
                    cases.append(dict(id=ident, name=name, tcp_header_words=words,
                                      expected_drop=blocked, packet_hex=wire.hex()))
                    try:
                        require(sender.sendto(wire, ('127.0.0.2', 18443)) == len(wire), 'Loopback packet send')
                        cases[-1]['send_errno'] = 0
                    except PermissionError as error:
                        # Raw IP reports an OUTPUT-chain drop synchronously.
                        require(blocked and error.errno == errno.EPERM, 'Unexpected loopback send denial')
                        cases[-1]['send_errno'] = error.errno
            observed = set()
            end = time.monotonic() + 1
            while time.monotonic() < end:
                if not select.select([capture], [], [], .05)[0]:
                    continue
                raw = capture.recv(65535)
                ip = raw[14:]
                if len(ip) < 40 or ip[12:20] != socket.inet_aton('127.0.0.1') + socket.inet_aton('127.0.0.2'):
                    continue
                if struct.unpack_from('!HH', ip, (ip[0] & 15) * 4) != (45000, 18443):
                    continue
                observed.add(struct.unpack_from('!H', ip, 4)[0])
            counters = json.loads(subprocess.check_output(['/usr/sbin/nft', '-j', 'list', 'table', 'ip', table], text=True))
            counts = [x['counter'] for obj in counters['nftables'] if 'rule' in obj
                      for x in obj['rule']['expr'] if 'counter' in x]
            require(observed == expected and not observed & dropped and len(counts) == 11
                    and all(v['packets'] == 1 for v in counts), 'Filter blocked data or passed an empty ACK')
            return dict(status='PASS', scope='new-network-namespace-loopback-only', cases=cases,
                        observed_ids=sorted(observed), dropped_ids=sorted(dropped), counters=counts)
        finally:
            if installed:
                subprocess.run(['/usr/sbin/nft', 'delete', 'table', 'ip', table], check=True, timeout=2)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parent-netns')
    p.add_argument('--run', action='store_true')
    args = p.parse_args()
    if not args.run:
        print('Plan only; no files, sockets, namespaces or rules accessed.')
        return
    require(args.parent_netns is not None, 'Parent namespace identity required')
    print(json.dumps(exercise(args.parent_netns)))


if __name__ == '__main__':
    main()
