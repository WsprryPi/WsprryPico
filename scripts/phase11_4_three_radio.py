#!/usr/bin/env python3
"""Opt-in wspr5 B2/D2 fixture: wlan0 AP, wlan2/wlan1 isolated peers, Ethernet.

Engineering acceptance only. All raw evidence and configuration stay in a fresh
owner-only root. The independent cleanup timer precedes the first mutation.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import phase11_4_hotspot as h
from phase11_4_loop_common import recovery_tls_ready, validate_info, stop_process
from phase11_4_radio_diagnostic import ethernet_check

REVISION = '802c91a7b86e-dirty'
ADDRESS = '10.77.14.10'
RADIOS = {'wlan0': '2c:cf:67:62:76:66', 'wlan2': 'e8:4e:06:ae:d7:09',
          'wlan1': '90:de:80:47:b9:da'}
PEERS = {1: ('wlan2', 'phase11-hotspot', 'phase11-hotspot-client', '10.77.14.2'),
         2: ('wlan1', 'phase11-second', 'phase11-second-client', '10.77.14.3')}
SAVED = ('station', 'schedules', 'watermark_utc_ns', 'expires_utc_s', 'enabled', 'suspended')
ROOT = None
SERIES = 'series-1'
BASE_CONSOLE = h.console
BASE_UNIT = h.system_unit


def console(command='INFO', boot=None):
    v = BASE_CONSOLE()
    validate_info(v, boot or v['status']['boot_id'], REVISION)
    if command == 'INFO':
        return v
    if boot:
        assert v['status']['boot_id'] == boot
    return BASE_CONSOLE(command)


def in_peer(peer, args, timeout=40, check=True):
    pid = int(h.cmd(['systemctl', 'show', '-p', 'MainPID', '--value', PEERS[peer][2]]).stdout)
    assert pid > 1, 'Peer service is not running'
    return h.cmd(['nsenter', '-t', str(pid), '-m', '-n', *args], timeout=timeout, check=check)


def peer_state(peer):
    interface, ns, unit, address = PEERS[peer]
    state = {key: in_peer(peer, args).stdout.strip() for key, args in {
        'link': ['iw', 'dev', interface, 'link'],
        'interfaces': ['ip', '-brief', 'address'], 'routes': ['ip', '-4', 'route'],
        'netns': ['readlink', '/proc/self/ns/net'], 'mountns': ['readlink', '/proc/self/ns/mnt'],
        'nss': ['cat', '/etc/nsswitch.conf'],
        'avahi_socket': ['stat', '-c', '%F', '/run/avahi-daemon/socket']}.items()}
    assert 'Connected to ' + RADIOS['wlan0'] in state['link']
    assert address + '/24' in state['interfaces'] and 'default' not in state['routes']
    assert state['avahi_socket'] == 'socket' and 'mdns' in state['nss']
    return state


def setup():
    assert not (ROOT / 'roles.json').exists(), 'This fixture fixes all three MAC-bound roles'
    ethernet_check()
    for interface, mac in RADIOS.items():
        assert Path('/sys/class/net/' + interface + '/address').read_text().strip() == mac
    assert h.cmd(['nmcli', '-g', 'GENERAL.CON-UUID', 'dev', 'show', 'wlan1']).stdout.strip() == h.PROFILE
    assert h.cmd(['systemctl', 'is-active', 'pi-wifi-recover.timer']).stdout.strip() == 'active'
    assert h.cmd(['systemctl', 'is-enabled', 'pi-wifi-recover.timer']).stdout.strip() == 'enabled'
    h.save('second-before.json', {
        'power': h.cmd(['iw', 'dev', 'wlan1', 'get', 'power_save']).stdout.strip().split()[-1],
        'link': h.cmd(['iw', 'dev', 'wlan1', 'link']).stdout,
        'profile': h.PROFILE})

    def prepare():
        (ROOT / 'second-owned').touch()
        h.cmd(['systemctl', 'stop', 'pi-wifi-recover.timer', 'pi-wifi-recover.service'])
        h.cmd(['nmcli', 'device', 'set', 'wlan1', 'managed', 'no'])

    h.setup(cleanup_entrypoint=ROOT / 'scripts/phase11_4_three_radio.py',
            prepare_network=prepare, cleanup_unit='phase11-three-cleanup', cleanup_after='50m')
    second = ROOT / 'second'
    second.mkdir(mode=0o700)
    (second / 'wpa.conf').write_bytes((ROOT / 'wpa.conf').read_bytes())
    (second / 'avahi.conf').write_text((ROOT / 'avahi.conf').read_text().replace(
        'wspr-hotspot-client', 'wspr-second-client').replace('wlan2', 'wlan1'))
    h.cmd(['ip', 'netns', 'add', 'phase11-second'])
    phy = Path('/sys/class/net/wlan1/phy80211').resolve(strict=True).name
    h.cmd(['iw', 'phy', phy, 'set', 'netns', 'name', 'phase11-second'])
    h.cmd(['ip', '-n', 'phase11-second', 'link', 'set', 'lo', 'up'])
    h.system_unit('phase11-second-client', ['ip', 'netns', 'exec', 'phase11-second',
        'unshare', '--mount', '--propagation', 'private', 'python3',
        ROOT / 'scripts/phase11_4_three_radio.py', 'second', '--root', ROOT, '--run'])
    deadline = time.monotonic() + 35
    while not (second / 'client-ready').exists() and time.monotonic() < deadline:
        time.sleep(.5)
    assert (second / 'client-ready').exists(), 'Second peer startup failed'
    states = {str(p): peer_state(p) for p in PEERS}
    assert states['1']['netns'] != states['2']['netns']
    assert states['1']['mountns'] != states['2']['mountns']
    h.save('peers-ready.json', states)
    (ROOT / 'target-changed').touch()
    console('CONFIG ' + json.dumps(json.loads((ROOT / 'test-config.json').read_text())))
    console('REBOOT')
    time.sleep(3)
    initial = h.ready(ADDRESS)
    validate_info(initial, initial['status']['boot_id'], REVISION)
    h.save('hotspot-baseline.json', initial)
    h.usb_check()
    print('THREE RADIO READY', flush=True)


def cleanup():
    if not (ROOT / 'setup-started').exists():
        return
    (ROOT / 'cleanup-started').touch()
    h.cmd(['systemctl', 'stop', 'phase11-three-campaign'], check=False)
    with (ROOT / 'controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        faults = []
        h.cmd(['systemctl', 'stop', 'phase11-second-client'], check=False)
        h.cmd(['ip', 'netns', 'delete', 'phase11-second'], check=False)
        try:
            if (ROOT / 'second-owned').exists():
                deadline = time.monotonic() + 20
                found = None
                while time.monotonic() < deadline:
                    found = next((p.parent.name for p in Path('/sys/class/net').glob('*/address')
                                  if p.read_text().strip() == RADIOS['wlan1']), None)
                    if found and h.cmd(['nmcli', 'dev', 'show', found], check=False).returncode == 0:
                        break
                    time.sleep(.5)
                assert found, 'Second client radio did not return'
                h.cmd(['nmcli', 'device', 'set', found, 'managed', 'yes'])
                h.cmd(['nmcli', '--wait', '60', 'connection', 'up', 'uuid', h.PROFILE,
                       'ifname', found], timeout=65)
                state = json.loads((ROOT / 'second-before.json').read_text())
                h.cmd(['iw', 'dev', found, 'set', 'power_save', state['power']])
                assert h.cmd(['nmcli', '-g', 'GENERAL.CON-UUID', 'dev', 'show', found]).stdout.strip() == state['profile']
                assert state['link'].splitlines()[0] == h.cmd(['iw', 'dev', found, 'link']).stdout.splitlines()[0]
                h.cmd(['systemctl', 'start', 'pi-wifi-recover.timer'])
        except Exception as e:
            faults.append('Second peer restore: ' + str(e))
            h.cmd(['systemctl', 'start', 'pi-wifi-recover.timer'], check=False)
        try:
            h.cleanup()
        except Exception as e:
            faults.append('Base fixture restore: ' + str(e))
        try:
            assert h.cmd(['systemctl', 'is-active', 'pi-wifi-recover.timer']).stdout.strip() == 'active'
            assert h.cmd(['systemctl', 'is-enabled', 'pi-wifi-recover.timer']).stdout.strip() == 'enabled'
            assert 'phase11-' not in h.cmd(['ip', 'netns', 'list']).stdout
            assert h.cmd(['nmcli', '-g', 'GENERAL.CON-UUID', 'dev', 'show', 'wlan1']).stdout.strip() == h.PROFILE
            h.save('final-host.json', ethernet_check())
        except Exception as e:
            faults.append('Final host verification: ' + str(e))
        h.save('three-cleanup.json', {'failures': faults})
        if not faults:
            h.cmd(['systemctl', 'stop', 'phase11-three-cleanup.timer'], check=False)
        assert not faults, faults
        print('THREE RADIO CLEANUP PASS', flush=True)


class Usb:
    """Persistent read-only WTP session with raw bytes for a strict offline audit."""
    def __init__(self, root, boot, note):
        from rf_wtp import WtpPeer, open_port
        from validate_wtp_contract import loads_strict
        self.note, self.boot = note, boot
        self.raw = (root / 'usb-wire.bin').open('xb')
        self.decoded = (root / 'usb-frames.jsonl').open('x')
        self.fd = open_port('/dev/serial/by-id/usb-WsprryPi_WsprryPico_' + h.SERIAL + '-if02')
        outer = self
        class Logged(WtpPeer):
            def _receive(self):
                chunk = os.read(self.fd, 4096)
                if not chunk:
                    raise ConnectionError('USB closed')
                outer.raw.write(chunk)
                outer.raw.flush()
                for payload in self.decoder.feed(chunk):
                    value = loads_strict(payload.decode())
                    outer.decoded.write(json.dumps(value) + '\n')
                    outer.decoded.flush()
                    self.pending.append(value)
        self.peer = Logged(self.fd)
        hello = self.request('HELLO', {'versions': ['WTP/1'], 'client_name': 'three-radio', 'client_version': '1'})
        assert hello['device_id'] == h.DEVICE and hello['boot_id'] == boot
        assert self.request('CAPS')['engine'] == 'inhibited-standalone-simulator'
        self.status()

    def request(self, op, body=None):
        self.note('wtp_request', {'op': op, 'session': self.peer.session, 'body': body or {}})
        value = self.peer.request(op, body or {})
        self.note('wtp_response', {'op': op, 'body': value})
        return value

    def status(self):
        value = self.request('STATUS')
        assert value['boot_id'] == self.boot and value['state'] == 'empty'
        assert value['owner_id'] is None and value['job_id'] is None and value['output_active'] is False
        return value

    def close(self):
        import termios, struct
        try:
            fcntl.ioctl(self.fd, termios.TIOCMBIC, struct.pack('I', termios.TIOCM_DTR))
        finally:
            os.close(self.fd)
            self.raw.close()
            self.decoded.close()


def run_case(number, boot):
    from check_usb_target import port, write_all
    from rf_wtp import read_line
    from audit_phase11_4_mdns_conflict import pcap
    from phase11_4_three_radio_audit import has_answer
    root = ROOT / SERIES / ('case-%02d' % number)
    root.mkdir(mode=0o700)
    log_lock = threading.RLock()
    def note(kind, value):
        with log_lock, (root / 'events.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(epoch_ns=time.time_ns(), monotonic_ns=time.monotonic_ns(),
                                        kind=kind, value=value)) + '\n')
            stream.flush()
    def info():
        value = console(boot=boot)
        note('INFO', value)
        for field in SAVED:
            assert value['status'][field] == initial['status'][field], 'Saved state changed: ' + field
        return value
    initial = console(boot=boot)
    note('INFO', initial)
    assert initial['network']['ipv4'] == ADDRESS and initial['network']['mdns_state'] == 'active'
    captures, streams, usb = [], [], None
    stop = threading.Event()
    faults, monitor = [], None
    cursor = 0
    def trace():
        nonlocal cursor
        with (ROOT / 'usb.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            with port('/dev/serial/by-id/usb-WsprryPi_WsprryPico_' + h.SERIAL + '-if00') as fd:
                for _ in range(40):
                    write_all(fd, ('NETTRACE ' + str(cursor) + '\n').encode())
                    value = read_line(fd, time.monotonic() + 5)
                    note('NETTRACE', value)
                    assert value.get('ok') and value['device_id'] == h.DEVICE and value['revision'] == REVISION and value['boot_id'] == boot
                    t = value['trace']
                    assert t['intact'] and not t['install_errors']
                    for event in t['events']:
                        assert cursor == 0 or event['seq'] == cursor + 1, 'Trace coverage gap'
                        cursor = event['seq']
                    if cursor == t['latest']:
                        return
                raise RuntimeError('Trace did not drain within its bound')
    def observe():
        while not stop.is_set():
            try:
                info()
                trace()
            except Exception as e:
                faults.append(type(e).__name__ + ': ' + str(e))
                note('OBSERVER_FAILURE', faults[-1])
                return
            stop.wait(.25)
    def wait_until(deadline):
        while time.monotonic() < deadline:
            assert not faults, faults
            assert all(p.poll() is None for p in captures), 'Capture exited early'
            stop.wait(min(.25, deadline - time.monotonic()))
    def nss(peer, label):
        start = time.time_ns()
        try:
            p = in_peer(peer, ['getent', 'ahostsv4', h.NAME], timeout=6, check=False)
            result = dict(exit=p.returncode, stdout=p.stdout, stderr=p.stderr)
        except TimeoutError:
            result = dict(exit=124, stdout='', stderr='timeout')
        result.update(peer=peer, label=label, started_ns=start, ended_ns=time.time_ns())
        note('NSS', result)
        return result
    def both_nss(label):
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(lambda peer: nss(peer, label), PEERS))
    def positive(values):
        return all(v['exit'] == 0 and {s.split()[0] for s in v['stdout'].splitlines()} == {ADDRESS} for v in values)
    def authenticated(peer, label):
        start = time.time_ns()
        # Sequential peers avoid testing TLS capacity rather than recovery.
        output = root / ('peer%d-%s' % (peer, label))
        output.mkdir(mode=0o700)
        credentials = json.loads((ROOT / 'peer.json').read_text())
        credentials['session_id'] = json.loads((ROOT / 'peer-sessions.json').read_text())[str(peer)]
        (output / 'peer.json').write_text(json.dumps(credentials))
        result = in_peer(peer, ['python3', ROOT / 'scripts/phase11_4_hotspot.py', 'probe', ADDRESS,
            boot, '--root', output, '--run'], timeout=35, check=False)
        note('AUTH', dict(peer=peer, label=label, exit=result.returncode, stdout=result.stdout,
                         stderr=result.stderr, started_ns=start, ended_ns=time.time_ns(), directory=output.name))
        return result.returncode == 0
    error, off = None, False
    try:
        note('PEER_STATES', {str(p): peer_state(p) for p in PEERS})
        ethernet_check()
        for label, interface, ns in [('ap', 'wlan0', None), ('peer1', 'wlan2', 'phase11-hotspot'), ('peer2', 'wlan1', 'phase11-second')]:
            for kind, flt in [('mdns', 'ip and udp port 5353'), ('path', 'arp or udp port 67 or udp port 68 or tcp port 18443')]:
                name = label + '-' + kind
                stream = (root / (name + '.log')).open('xb')
                args = ['/usr/bin/tcpdump', '-n', '-U', '-i', interface, '-w', str(root / (name + '.pcap')), flt]
                if ns:
                    args = ['ip', 'netns', 'exec', ns, *args]
                captures.append(subprocess.Popen(args, stdout=stream, stderr=stream))
                streams.append(stream)
        wait_until(time.monotonic() + 1)
        assert all(p.stat().st_size >= 24 for p in root.glob('*.pcap')) and len(list(root.glob('*.pcap'))) == 6
        usb = Usb(root, boot, note)
        trace()
        monitor = threading.Thread(target=observe, daemon=True)
        monitor.start()
        note('OBSERVERS_READY', {})
        values = both_nss('before')
        assert positive(values), 'Native baseline failed before OFF'
        assert all(authenticated(p, 'before') for p in PEERS), 'Authenticated baseline failed before OFF'
        # Capture one real fresh answer at each NIC; no injected name/address mapping.
        for peer in PEERS:
            in_peer(peer, ['python3', ROOT / 'scripts/phase11_4_three_radio.py', 'seed', '--root', ROOT, '--run'])
        wait_until(time.monotonic() + 3)
        for label in ('ap', 'peer1', 'peer2'):
            assert any(has_answer(p, 120) for p in pcap(root / (label + '-mdns.pcap'))), 'Missing baseline packet at ' + label
        assert positive(both_nss('seed-closed')), 'Native baseline after seed failed'
        note('off_begin', {})
        off = True
        console('WIFI OFF', boot)
        began = time.monotonic()
        usb.status()
        failures = []
        for delay in (3, 10, 40, 80, 125, 145):
            wait_until(began + delay)
            values = both_nss('off-' + str(delay))
            if not all(v['exit'] == 2 and not v['stdout'] for v in values):
                failures.append('Negative lookup failed at ' + str(delay))
                note('WITHDRAWAL_FAILURE', values)
        wait_until(began + 150)
        usb.status()
        note('on_begin', {})
        on = time.monotonic()
        console('WIFI ON', boot)
        off = False
        active, first, count = None, None, 0
        while time.monotonic() < on + 120:
            value = info()
            if value['network']['mdns_state'] == 'active' and active is None:
                active = time.monotonic()
                note('local_active', {'seconds_after_on': active - on})
            if active is None and time.monotonic() > on + 40:
                raise RuntimeError('Local activation exceeded 40 seconds')
            if active is None or not recovery_tls_ready(value):
                wait_until(time.monotonic() + 1)
                continue
            values = both_nss('recovery-' + str(count))
            good = positive(values)
            for peer in PEERS:
                if not authenticated(peer, 'recovery-' + str(count)):
                    good = False
            if not good:
                failures.append('Recovery check failed at ' + str(count))
                note('RECOVERY_FAILURE', values)
                # Retain the first failed state and boundary trace; do not retry it into a pass.
                break
            count += 1
            first = first or time.monotonic()
            if count >= 5 and time.monotonic() - first >= 30 and time.monotonic() < on + 120:
                break
            wait_until(time.monotonic() + 8)
        assert count >= 5 and first and time.monotonic() - first >= 30 and time.monotonic() < on + 120, 'Recovery stability window failed'
        assert active and active - on <= 40
        usb.status()
        note('PEER_STATES_FINAL', {str(p): peer_state(p) for p in PEERS})
        ethernet_check()
        assert not failures, failures
        note('CASE_PASS', {'boot': boot, 'checks_per_peer': count, 'stable_seconds': time.monotonic() - first})
    except Exception as e:
        error = type(e).__name__ + ': ' + str(e)
        note('CASE_FAILURE', error)
    finally:
        stop.set()
        if monitor:
            monitor.join(timeout=12)
            if monitor.is_alive():
                note('OBSERVER_FAILURE', 'Observer did not stop')
                error = error or 'Observer did not stop'
        try:
            info()
            if not faults:
                trace()
            if off:
                note('cleanup_on', {})
                console('WIFI ON', boot)
            if usb:
                usb.status()
        except Exception as e:
            note('FINAL_FAILURE', type(e).__name__ + ': ' + str(e))
            error = error or str(e)
        for process in captures:
            note('CAPTURE_STOP', stop_process(process))
        for stream in streams:
            stream.close()
        if usb:
            usb.close()
    print('CASE %02d %s' % (number, error or 'COMPLETE; OFFLINE AUDIT REQUIRED'), flush=True)
    return root, error


def campaign():
    from phase11_4_three_radio_audit import audit
    with (ROOT / 'controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not (ROOT / 'cleanup-started').exists()
        series = ROOT / SERIES
        series.mkdir(mode=0o700)
        if not (ROOT / 'peer-sessions.json').exists():
            import uuid
            h.save('peer-sessions.json', {str(p): uuid.uuid4().hex for p in PEERS})
        boot = json.loads((ROOT / 'hotspot-baseline.json').read_text())['status']['boot_id']
        results = []
        for number in range(1, 9):
            root, error = run_case(number, boot)
            try:
                result = audit(root, require_resumed_sessions=True)
            except Exception as e:
                result = {'result': 'FAIL', 'error': type(e).__name__ + ': ' + str(e)}
            results.append(result)
            (series / 'campaign.json').write_text(json.dumps({'cases': results,
                'complete': number == 8 and all(r['result'] == 'PASS' for r in results)}, indent=2) + '\n')
            print(json.dumps({'case': number, 'audit': result}), flush=True)
            # A single newly localized failure is enough to stop and inspect, rather than repeat blindly.
            if error or result['result'] != 'PASS':
                break


def main():
    global ROOT, SERIES
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['setup', 'cleanup', 'second', 'campaign', 'seed'])
    p.add_argument('--root', required=True, type=Path)
    p.add_argument('--run', action='store_true')
    p.add_argument('--series', default='series-1', help='Fresh evidence subdirectory for the campaign')
    a = p.parse_args()
    if not a.run:
        print('Plan only; --run requires the intended hardware authorization.')
        return
    if not __debug__ or sys.platform != 'linux' or os.geteuid() != 0:
        raise RuntimeError('Execution requires Linux root and enabled Python assertions')
    os.umask(0o077)
    os.environ['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'
    ROOT = a.root.resolve()
    SERIES = a.series
    if not SERIES.startswith('series-') or not SERIES[7:].isdigit():
        raise ValueError('Expected a numbered series directory')
    assert ROOT.is_dir() and ROOT.stat().st_mode & 0o077 == 0
    h.ROOT, h.AP_IF, h.CLIENT_IF = ROOT, 'wlan0', 'wlan2'
    h.host_check = ethernet_check
    h.console = console
    h.system_unit = lambda name, args, seconds=3300: BASE_UNIT(name, args, seconds)
    if a.command == 'second':
        h.ROOT, h.CLIENT_IF = ROOT / 'second', 'wlan1'
        h.client('10.77.14.3')
    elif a.command == 'seed':
        import socket, struct
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('', 5353))
            s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
            labels = b''.join(bytes([len(x)]) + x.encode() for x in h.NAME.split('.')) + b'\0'
            # Direct question requests a genuine Pico multicast answer, shared by both native caches.
            s.sendto(struct.pack('>6H', 0, 0, 1, 0, 0, 0) + labels + struct.pack('>HH', 1, 1), (ADDRESS, 5353))
            time.sleep(2)
    else:
        globals()[a.command]()


if __name__ == '__main__':
    main()
