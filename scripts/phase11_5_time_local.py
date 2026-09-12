#!/usr/bin/env python3
"""Opt-in R1 native mDNS/NTP checks and interface-scoped Avahi publication.

Uses the installed Avahi D-Bus API. No DNS emulation, routing, chrony source
changes or device access. Permanent files are hashed, never rewritten.
"""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import signal
import socket
import struct
import subprocess
import time

NAME = 'time.local'
ADDRESS = '10.77.15.1'
CLIENT = '10.77.15.2'
SERVICE = 'org.freedesktop.Avahi'
PERMANENT = (
    '/etc/chrony/chrony.conf', '/etc/chrony/conf.d/gps-hat.conf',
    '/etc/chrony/conf.d/time-local.conf', '/etc/avahi/avahi-daemon.conf',
    '/etc/avahi/services/time-local.service', '/etc/systemd/system/time-local.service',
    '/usr/local/sbin/time-local-publish', '/etc/NetworkManager/dispatcher.d/90-time-local',
    '/usr/local/share/doc/time-local/README.md', '/usr/local/etc/wsprrypi.ini')
RUNTIME = Path('/run/phase115-time-local.py')
DROPIN = Path('/run/systemd/system/time-local.service.d/phase115.conf')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(args):
    return subprocess.check_output(args, text=True, timeout=10).strip()


def lan_addresses():
    values = {}
    for name in ('eth0', 'wlan1'):
        data = json.loads(command(['ip', '-j', '-4', 'address', 'show', 'up', 'dev', name]))
        addresses = [a['local'] for i in data for a in i['addr_info']
                     if ipaddress.ip_address(a['local']) in ipaddress.ip_network('192.168.1.0/24')]
        if addresses:
            values[name] = addresses[0]
    require(values, 'No permanent management LAN address')
    return values


def ntp_query(address):
    q = bytearray(48); q[0] = 0x23
    now = time.time_ns()
    stamp = ((now // 10**9 + 2208988800) << 32) | ((now % 10**9) << 32) // 10**9
    struct.pack_into('!Q', q, 40, stamp)
    value = dict(query_hex=q.hex(), address=address, utc_ns=now)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(3); sock.connect((address, 123))
        start = time.monotonic_ns(); sock.send(q)
        reply = sock.recv(512)
        value.update(reply_hex=reply.hex(), local_address=sock.getsockname()[0],
                     peer=list(sock.getpeername()), elapsed_ns=time.monotonic_ns()-start)
    return value


def validate_ntp(value, address, local=None):
    q, r = bytes.fromhex(value['query_hex']), bytes.fromhex(value['reply_hex'])
    require(len(q) == len(r) == 48 and q[0] == 0x23 and any(q[40:48]), 'NTP framing/query')
    require(r[0] >> 6 == 0 and (r[0] >> 3) & 7 == 4 and r[0] & 7 == 4 and
            r[1] == 1 and r[12:16] == b'PPS\0', 'NTP not synchronized stratum 1/PPS')
    require(r[24:32] == q[40:48] and any(r[16:24]) and any(r[32:40]) and any(r[40:48]),
            'NTP origin or server timestamps invalid')
    transmit = struct.unpack('!Q', r[40:48])[0] / 2**32 - 2208988800
    require(abs(transmit-value['utc_ns']/1e9) <= 5, 'NTP timestamp outside fresh request window')
    require(value['address'] == address and value['peer'] == [address, 123] and
            0 <= value['elapsed_ns'] <= 3_000_000_000 and
            (local is None or value['local_address'] == local), 'NTP address/deadline')


def dns_name(data, offset, seen=None):
    seen = set() if seen is None else seen
    labels = []; end = None
    while True:
        require(offset < len(data) and offset not in seen, 'Truncated/cyclic DNS name')
        seen.add(offset); size = data[offset]; offset += 1
        if size & 0xc0 == 0xc0:
            require(offset < len(data), 'Truncated DNS pointer')
            pointer = ((size & 63) << 8) | data[offset]
            name, _ = dns_name(data, pointer, seen)
            labels.append(name); end = offset+1; break
        require(size < 64 and offset+size <= len(data), 'Malformed DNS label')
        if not size:
            end = offset; break
        labels.append(data[offset:offset+size].decode('ascii').lower()); offset += size
    return '.'.join(labels), end


def mdns_addresses(data):
    require(len(data) >= 12, 'Truncated mDNS header')
    _, flags, qd, an, ns, ar = struct.unpack_from('!6H', data)
    require(flags & 0x820f == 0x8000, 'mDNS error/truncation/not a response')
    offset = 12
    for _ in range(qd):
        _, offset = dns_name(data, offset); offset += 4
    addresses = []
    for _ in range(an+ns+ar):
        name, offset = dns_name(data, offset)
        require(offset+10 <= len(data), 'Truncated mDNS record')
        kind, klass, ttl, size = struct.unpack_from('!HHIH', data, offset); offset += 10
        require(offset+size <= len(data), 'Truncated mDNS rdata')
        if name == NAME and kind == 1 and klass & 0x7fff == 1 and ttl:
            require(size == 4, 'Invalid mDNS A record')
            addresses.append(socket.inet_ntoa(data[offset:offset+size]))
        offset += size
    require(offset == len(data), 'Trailing mDNS bytes')
    return addresses


def mdns_query():
    q = struct.pack('!6H', 12345, 0, 1, 0, 0, 0)+b'\x04time\x05local\x00\x00\x01\x00\x01'
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((CLIENT, 0)); sock.settimeout(3)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(CLIENT))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
        start = time.monotonic_ns(); sock.sendto(q, ('224.0.0.251', 5353))
        r, peer = sock.recvfrom(4096)
        return dict(query_hex=q.hex(), reply_hex=r.hex(), peer=list(peer),
                    local_port=sock.getsockname()[1], local_address=CLIENT,
                    elapsed_ns=time.monotonic_ns()-start)


def validate_mdns(value):
    q, r = bytes.fromhex(value['query_hex']), bytes.fromhex(value['reply_hex'])
    require(q == struct.pack('!6H', 12345, 0, 1, 0, 0, 0)+b'\x04time\x05local\x00\x00\x01\x00\x01' and
            r[:2] == q[:2] and value['peer'] == [ADDRESS, 5353] and
            value['local_address'] == CLIENT and 0 <= value['elapsed_ns'] <= 3_000_000_000,
            'mDNS query/peer/deadline')
    require(set(mdns_addresses(r)) == {ADDRESS}, 'mDNS wrong/unreachable/multiple address selection')


def capture_packets(path, allow_live_tail=False):
    data = Path(path).read_bytes()
    require(len(data) >= 24, 'Missing capture header')
    formats = {b'\xd4\xc3\xb2\xa1': ('<', 1000), b'\xa1\xb2\xc3\xd4': ('>', 1000),
               b'\x4d\x3c\xb2\xa1': ('<', 1), b'\xa1\xb2\x3c\x4d': ('>', 1)}
    require(data[:4] in formats, 'Unsupported pcap')
    endian, scale = formats[data[:4]]
    require(struct.unpack_from(endian+'I', data, 20)[0] == 1, 'Capture must be Ethernet')
    offset = 24; packets = []
    while offset+16 <= len(data):
        seconds, fraction, size, original = struct.unpack_from(endian+'4I', data, offset); offset += 16
        if offset+size > len(data):
            require(allow_live_tail, 'Incomplete final pcap record')
            break  # Only live admission may observe a record still being appended.
        frame = data[offset:offset+size]; offset += size
        require(size == original, 'Truncated captured packet')
        if len(frame) < 34 or frame[12:14] != b'\x08\x00': continue
        ip = frame[14:]; ihl = (ip[0] & 15)*4
        if ip[9] != 17: continue
        require(ihl >= 20 and len(ip) >= ihl+8 and struct.unpack_from('!H', ip, 6)[0] & 0x3fff == 0,
                'Fragmented/short UDP evidence')
        source, destination = socket.inet_ntoa(ip[12:16]), socket.inet_ntoa(ip[16:20])
        sport, dport, length, _ = struct.unpack_from('!4H', ip, ihl)
        require(length >= 8 and ihl+length <= len(ip), 'Truncated UDP evidence')
        packets.append(dict(utc_ns=seconds*10**9+fraction*scale, source=source, destination=destination,
                            sport=sport, dport=dport, payload=ip[ihl+8:ihl+length].hex()))
    require(allow_live_tail or offset == len(data), 'Incomplete final pcap header')
    return packets


def validate_capture(path, admission, allow_live_tail=False):
    packets = [p for p in capture_packets(path, allow_live_tail=allow_live_tail) if
               admission['start_utc_ns'] <= p['utc_ns'] <= admission['finish_utc_ns']]
    for protocol, port, destination in (('mdns', 5353, '224.0.0.251'), ('ntp', 123, ADDRESS)):
        value = admission[protocol]
        queries = [p for p in packets if p['source'] == CLIENT and p['destination'] == destination and
                   p['dport'] == port and p['payload'] == value['query_hex']]
        replies = [p for p in packets if p['source'] == ADDRESS and p['destination'] == CLIENT and
                   p['sport'] == port and p['payload'] == value['reply_hex']]
        require(queries and replies and queries[0]['utc_ns'] <= replies[-1]['utc_ns'] and
                queries[0]['sport'] == replies[-1]['dport'], 'Missing captured '+protocol+' request/response')
    return dict(sha256=digest(path), matched_protocols=['mdns', 'ntp'])


def baseline():
    result = dict(files={p: digest(p) for p in PERMANENT}, services={}, addresses=lan_addresses())
    for service in ('time-local', 'chrony', 'gpsd', 'avahi-daemon'):
        result['services'][service] = {key: command(['systemctl', 'show', service, '-p', key, '--value'])
                                      for key in ('ActiveState', 'UnitFileState', 'MainPID')}
        require(result['services'][service]['ActiveState'] == 'active' and
                result['services'][service]['UnitFileState'] == 'enabled', 'Permanent service unhealthy')
    result['tracking'] = command(['chronyc', 'tracking'])
    result['sources'] = command(['chronyc', 'sources', '-v'])
    require('50505300 (PPS)' in result['tracking'] and 'Normal' in result['tracking'], 'PPS health')
    result['lan_acl'] = command(['chronyc', 'accheck', '192.168.1.10'])
    require('Access allowed' in result['lan_acl'], 'Permanent LAN ACL absent')
    result['resolution'] = command(['avahi-resolve-host-name', '-4', NAME])
    address = result['resolution'].split()[-1]
    require(address == next(iter(result['addresses'].values())), 'Permanent alias address changed')
    result['wspr5'] = command(['avahi-resolve-host-name', '-4', 'wspr5.local'])
    result['ntp'] = ntp_query(address); validate_ntp(result['ntp'], address)
    return result


def validate_preserved(before, after):
    require(before['files'] == after['files'] and before['addresses'] == after['addresses'],
            'Permanent files or management addresses changed')
    for name in before['services']:
        for key in ('ActiveState', 'UnitFileState'):
            require(before['services'][name][key] == after['services'][name][key], 'Service state changed')
        if name != 'time-local':
            require(before['services'][name]['MainPID'] == after['services'][name]['MainPID'],
                    'Unrelated permanent service restarted')
    require(before['resolution'] == after['resolution'] and before['lan_acl'] == after['lan_acl'],
            'Permanent alias or LAN grant changed')


def publish(lan):
    import dbus  # Installed on wspr5; no host-test dependency.
    bus = dbus.SystemBus()
    server = dbus.Interface(bus.get_object(SERVICE, '/'), SERVICE+'.Server')
    group = dbus.Interface(bus.get_object(SERVICE, server.EntryGroupNew()), SERVICE+'.EntryGroup')
    if lan:
        interfaces = lan_addresses()
        address = next(iter(interfaces.values()))  # Same wired-first policy as permanent publisher.
        records = [(socket.if_nametoindex(name), address) for name in interfaces]
    else:
        records = [(socket.if_nametoindex('wlan0'), ADDRESS)]
    for interface, address in records:
        group.AddAddress(dbus.Int32(interface), dbus.Int32(0), dbus.UInt32(16), NAME, address)
    group.Commit()
    stop = False
    def interrupted(*_):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGINT, interrupted); signal.signal(signal.SIGTERM, interrupted)
    try:
        deadline = time.monotonic()+10
        while not stop:
            state = int(group.GetState())
            require(state not in (3, 4), 'Avahi publication collision/failure')
            require(state == 2 or time.monotonic() < deadline, 'Avahi publication deadline')
            time.sleep(.25)
    finally:
        group.Free()


def install(fixture):
    """Write-ahead ownership; cleanup is already armed by the fixture."""
    require(not DROPIN.exists() and not RUNTIME.exists(), 'Temporary publisher path already owned')
    data = Path(__file__).read_bytes()
    dropin = ('# '+fixture.state['token']+'\n[Service]\nExecStart=\n'
              'ExecStart=/usr/bin/python3 '+str(RUNTIME)+' publish-lan --run\n').encode()
    fixture.state['time_local_override'] = dict(helper_sha256=hashlib.sha256(data).hexdigest(),
                                               dropin_sha256=hashlib.sha256(dropin).hexdigest())
    fixture.save()
    with RUNTIME.open('xb') as stream:
        stream.write(data)
    RUNTIME.chmod(0o644)
    DROPIN.parent.mkdir(exist_ok=True)
    with DROPIN.open('xb') as stream:
        stream.write(dropin)
    DROPIN.chmod(0o644)
    fixture.cmd(['systemctl', 'daemon-reload'])
    fixture.cmd(['systemctl', 'restart', 'time-local.service'])
    fixture.unit('time-local', ['/usr/bin/python3', str(RUNTIME), 'publish-ap', '--run'])


def restore(fixture):
    owned = fixture.state.get('time_local_override')
    if not owned:
        return
    for path, key in ((DROPIN, 'dropin_sha256'), (RUNTIME, 'helper_sha256')):
        require(not path.exists() or digest(path) == owned[key], 'Temporary publisher ownership changed')
    if DROPIN.exists():
        DROPIN.unlink()
    fixture.cmd(['systemctl', 'daemon-reload'])
    fixture.cmd(['systemctl', 'restart', 'time-local.service'])
    time.sleep(3)  # Register the original publisher after final radio/interface convergence.
    if RUNTIME.exists():
        RUNTIME.unlink()
    if DROPIN.parent.exists() and not list(DROPIN.parent.iterdir()):
        DROPIN.parent.rmdir()


def probe():
    """Native Avahi lookup inside the actual independent client namespaces."""
    value = dict(schema='phase11.5-time-local-admission-v1', name=NAME,
                 netns=os.readlink('/proc/self/ns/net'), mountns=os.readlink('/proc/self/ns/mnt'),
                 start_utc_ns=time.time_ns(), status='FAILED')
    try:
        value['mdns'] = mdns_query(); validate_mdns(value['mdns'])
        began = time.monotonic_ns()
        value['native_resolver'] = 'getent -s mdns4 ahostsv4'
        value['native_output'] = command(['getent', '-s', 'mdns4', 'ahostsv4', NAME])
        addresses = {line.split()[0] for line in value['native_output'].splitlines()}
        require(addresses == {ADDRESS}, 'Native mDNS returned wrong/multiple addresses')
        value['native_resolution'] = NAME+'\t'+next(iter(addresses))
        value['resolution_elapsed_ns'] = time.monotonic_ns()-began
        address = value['native_resolution'].split()[-1]
        require(address == ADDRESS, 'Native mDNS returned an unreachable/wrong fixture address')
        value['ntp'] = ntp_query(address)
        validate_ntp(value['ntp'], ADDRESS, CLIENT)
        value['status'] = 'PASS'
    except Exception as error:
        value['error'] = type(error).__name__+': '+str(error)
    value['finish_utc_ns'] = time.time_ns()
    print(json.dumps(value), flush=True)
    require(value['status'] == 'PASS', 'Native mDNS/NTP admission failed')


def validate_admission(value):
    require(value['schema'] == 'phase11.5-time-local-admission-v1' and value['status'] == 'PASS' and
            value['name'] == NAME and
            value['native_resolver'] == 'getent -s mdns4 ahostsv4' and
            {line.split()[0] for line in value['native_output'].splitlines()} == {ADDRESS} and
            value['native_resolution'].split() == [NAME, ADDRESS] and
            0 <= value['resolution_elapsed_ns'] <= 10_000_000_000 and
            value['finish_utc_ns'] >= value['start_utc_ns'], 'Incomplete native mDNS admission')
    validate_mdns(value['mdns'])
    validate_ntp(value['ntp'], ADDRESS, CLIENT)


def fixture_admission(fixture, root, label):
    result = fixture.in_client(['python3', str(root/'scripts/phase11_5_time_local.py'), 'probe', '--run'],
                               timeout=20, check=False)
    with (root/(label+'.stdout')).open('x') as stream:
        stream.write(result.stdout)
    with (root/(label+'.stderr')).open('x') as stream:
        stream.write(result.stderr)
    require(result.returncode == 0, 'Native mDNS/NTP admission failed; inspect preserved response/captures')
    value = json.loads(result.stdout); validate_admission(value)
    require(value['netns'] != os.readlink('/proc/self/ns/net') and
            value['mountns'] != os.readlink('/proc/self/ns/mnt'), 'Client namespace isolation absent')
    time.sleep(.3)  # Allow packet-buffer writes before inspecting both live captures.
    for side in ('ap', 'client'):
        validate_capture(fixture.root/('capture-'+side+'.pcap'), value, allow_live_tail=True)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('publish-lan', 'publish-ap', 'probe', 'baseline'))
    parser.add_argument('--run', action='store_true'); args = parser.parse_args()
    if not args.run:
        print('Plan only; no network or service access.'); return
    if args.action.startswith('publish-'):
        publish(args.action == 'publish-lan')
    elif args.action == 'probe':
        probe()
    else:
        print(json.dumps(baseline(), indent=2))


if __name__ == '__main__':
    main()
