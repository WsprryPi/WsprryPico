#!/usr/bin/env python3
"""Opt-in wspr5 three-radio diagnostic; Ethernet management, inhibited Pico A only.

Requires a fresh private root, original-wifi.json and peer.json, plus the
repository helpers/schema under that root. Hardware roles are MAC-bound.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import struct
import sys
import time

import phase11_4_hotspot as h

MANAGEMENT_MAC = '90:de:80:47:b9:da'
ETHERNET_MAC = '2c:cf:67:62:76:64'
BSSID = '7a:cd:d6:f2:f6:c5'
BASE_HOST_CHECK = h.host_check


def radio_frames(path, live=False):
    data = path.read_bytes()
    if len(data) < 24 or data[:4] != b'\xd4\xc3\xb2\xa1':
        raise ValueError('Incomplete or unsupported monitor PCAP')
    if struct.unpack_from('<HH', data, 4) != (2, 4):
        raise ValueError('Unsupported PCAP version')
    if struct.unpack_from('<I', data, 20)[0] != 127:
        raise ValueError('Monitor capture is not radiotap')
    frames = []
    offset = 24
    while offset + 16 <= len(data):
        sec, us, size, original = struct.unpack_from('<IIII', data, offset)
        if us >= 1_000_000:
            raise ValueError('Invalid PCAP microseconds')
        if offset + 16 + size > len(data):
            if live:
                break  # Live writer may not have completed the last record yet.
            raise ValueError('Incomplete monitor record')
        if size != original:
            raise ValueError('Truncated monitor frame')
        wire = data[offset + 16:offset + 16 + size]
        offset += 16 + size
        if len(wire) < 8 or wire[0] != 0:
            continue
        rt = struct.unpack_from('<H', wire, 2)[0]
        if rt < 8 or rt + 10 > len(wire):
            continue
        present = struct.unpack_from('<I', wire, 4)[0]
        fields = 8
        bitmap = present
        while bitmap & 0x80000000:
            if fields + 4 > rt:
                raise ValueError('Incomplete radiotap presence bitmap')
            bitmap = struct.unpack_from('<I', wire, fields)[0]
            fields += 4
        if present & 1:  # TSFT precedes Flags and is aligned to eight bytes.
            fields = (fields + 7) // 8 * 8 + 8
        if present & 2:
            if fields >= rt:
                raise ValueError('Missing radiotap Flags field')
            if wire[fields] & 0x40:  # Receiver explicitly marked a bad FCS.
                continue
        w = wire[rt:]
        fc = struct.unpack_from('<H', w)[0]
        kind, subtype = (fc >> 2) & 3, (fc >> 4) & 15
        if fc & 3 or kind == 3 or (kind != 1 and len(w) < 24):
            continue
        addresses = [w[4:10].hex(':')]
        if len(w) >= 16:
            addresses.append(w[10:16].hex(':'))
        if kind != 1 and len(w) >= 24:
            addresses.append(w[16:22].hex(':'))
        frame = {'epoch_ns': sec * 10**9 + us * 1000,
                       'type': kind, 'subtype': subtype, 'retry': bool(fc & 0x800),
                       'protected': bool(fc & 0x4000), 'addresses': addresses,
                       'bytes': len(w)}
        if kind == 0 and not frame['protected']:
            if subtype == 11 and len(w) >= 30:
                frame['authentication'] = dict(zip(('algorithm', 'transaction', 'status'),
                                                     struct.unpack_from('<HHH', w, 24)))
            if subtype in (1, 3) and len(w) >= 30:
                frame['association_status'] = struct.unpack_from('<H', w, 26)[0]
        frames.append(frame)
    if not live and offset != len(data):
        raise ValueError('Incomplete monitor record header')
    return frames


def ethernet_check():
    assert Path('/sys/class/net/eth0/address').read_text().strip() == ETHERNET_MAC
    assert Path('/sys/class/net/eth0/carrier').read_text().strip() == '1'
    assert h.cmd(['systemctl', 'is-active', 'wsprrypi.service']).stdout.strip() == 'active'
    return {k: h.cmd(v).stdout for k, v in {
        'interfaces': ['ip', '-brief', 'address'], 'routes': ['ip', '-4', 'route'],
        'management': ['ip', '-6', 'address', 'show', 'dev', 'eth0'],
        'profiles': ['nmcli', '-f', 'UUID,NAME,DEVICE', 'connection', 'show', '--active'],
        'time': ['chronyc', 'tracking']}.items()}


def prepare_monitor():
    assert not Path('/sys/class/net/radiomon0').exists(), 'Monitor name already owned'
    h.cmd(['systemctl', 'stop', 'pi-wifi-recover.timer', 'pi-wifi-recover.service'])
    h.cmd(['nmcli', 'device', 'disconnect', 'wlan1'])
    h.cmd(['nmcli', 'device', 'set', 'wlan1', 'managed', 'no'])
    h.cmd(['ip', 'link', 'set', 'wlan1', 'down'])
    h.cmd(['iw', 'dev', 'wlan1', 'set', 'power_save', 'off'])
    h.cmd(['ip', 'link', 'set', 'wlan1', 'up'])
    phy = Path('/sys/class/net/wlan1/phy80211').resolve(strict=True).name
    (h.ROOT / 'monitor-child-created').touch()
    h.cmd(['iw', 'phy', phy, 'interface', 'add', 'radiomon0', 'type', 'monitor',
           'flags', 'control', 'otherbss'])


def start_monitor():
    # Association supplies the channel context required by this mt7921u radio.
    # The station has no IP configuration; radiomon0 remains a passive observer.
    h.system_unit('phase11-radio-monitor-station', ['/usr/sbin/wpa_supplicant',
                  '-i', 'wlan1', '-c', str(h.ROOT / 'wpa.conf')])
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        link = h.cmd(['iw', 'dev', 'wlan1', 'link']).stdout
        if 'Connected to e8:4e:06:ae:d7:09' in link and 'freq: 2462' in link:
            break
        time.sleep(.2)
    else:
        raise RuntimeError('Monitor station did not join controlled AP')
    h.cmd(['ip', 'link', 'set', 'radiomon0', 'up'])
    h.system_unit('phase11-hotspot-capture-monitor', ['/usr/bin/tcpdump', '-n', '-U',
                  '-s', '0', '-i', 'radiomon0', '-w', str(h.ROOT / 'monitor.pcap')])
    h.note('MONITOR_STARTED', ethernet_check())


def setup():
    assert not (h.ROOT / 'setup-started').exists()
    before = BASE_HOST_CHECK()
    assert 'Connected to ' + BSSID in before['management']
    assert Path('/sys/class/net/wlan1/address').read_text().strip() == MANAGEMENT_MAC
    assert 'monitor' in h.cmd(['iw', 'phy', Path('/sys/class/net/wlan1/phy80211').resolve().name, 'info']).stdout
    h.save('management-before.json', before)
    h.save('management-power.json', {'value': h.cmd(['iw', 'dev', 'wlan1', 'get', 'power_save']).stdout.strip().split()[-1]})
    h.save('roles.json', {'ap': 'wlan2', 'client': 'wlan0'})
    h.setup(cleanup_entrypoint=h.ROOT / 'scripts/phase11_4_radio_diagnostic.py',
            prepare_network=prepare_monitor, cleanup_unit='phase11-radio-cleanup')
    start_monitor()
    admit_monitor()


def admit_monitor():
    h.in_client(['ping', '-c', '5', '-W', '1', '10.77.14.1'])
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        path = h.ROOT / 'monitor.pcap'
        frames = radio_frames(path, live=True) if path.exists() and path.stat().st_size >= 24 else []
        beacon = any(f['type'] == 0 and f['subtype'] == 8 and
                     'e8:4e:06:ae:d7:09' in f['addresses'] for f in frames)
        client_data = any(f['type'] == 2 and '2c:cf:67:62:76:66' in f['addresses']
                          and 'e8:4e:06:ae:d7:09' in f['addresses'] for f in frames)
        if beacon and client_data:
            h.save('monitor-admission.json', {'beacon': beacon, 'client_data': client_data,
                   'frames': len(frames), 'scope': 'Observed radiotap frames; not proof of complete radio capture'})
            print('MONITOR ADMITTED: AP beacons and independent client traffic', flush=True)
            return
        time.sleep(.5)
    raise RuntimeError('Monitor lacks AP beacon or client traffic; do not configure Pico')


def trace():
    from check_usb_target import port, write_all
    from rf_wtp import read_line
    expected = json.loads((h.ROOT / 'trace-boot.json').read_text())
    cursor = 0
    while True:
        info = h.console()
        assert info['status']['boot_id'] == expected['boot']
        with (h.ROOT / 'usb.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            with port('/dev/serial/by-id/usb-WsprryPi_WsprryPico_' + h.SERIAL + '-if00') as fd:
                for _ in range(64):
                    write_all(fd, ('NETTRACE ' + str(cursor) + '\n').encode())
                    v = read_line(fd, time.monotonic() + 5)
                    assert v['ok'] and v['device_id'] == h.DEVICE and v['boot_id'] == expected['boot']
                    t = v['trace']
                    assert t['intact'] and t['install_errors'] == 0
                    for e in t['events']:
                        if cursor:
                            assert e['seq'] == cursor + 1, 'Pico trace sequence gap'
                        cursor = e['seq']
                    h.note('NETTRACE', v)
                    if cursor == t['latest']:
                        break
                else:
                    raise RuntimeError('Trace collector cannot drain ring')
        (h.ROOT / 'trace-ready').touch()
        time.sleep(.1)


def reference(address, boot, label):
    h.note('REFERENCE_BEGIN', {'label': label, 'address': address, 'boot': boot})
    p = h.in_client(['python3', h.ROOT / 'scripts/phase11_4_hotspot.py', 'probe',
                    address, boot, '--root', h.ROOT, '--run'], check=False)
    h.note('REFERENCE_END', {'label': label, 'exit': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr})
    h.save(label + '.json', {'exit': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr})
    assert h.cmd(['systemctl', 'is-active', 'phase11-radio-trace']).stdout.strip() == 'active'
    return p.returncode == 0


def active_fixture():
    assert (h.ROOT / 'setup-started').exists(), 'Fixture has not been set up'
    for marker in ('cleanup-started', 'radio-cleanup-result.json', 'target-restored'):
        assert not (h.ROOT / marker).exists(), 'Use a fresh fixture after cleanup'
    for unit in ('phase11-radio-cleanup.timer', 'phase11-hotspot-client',
                 'phase11-hotspot-dhcp', 'phase11-hotspot-capture-monitor'):
        assert h.cmd(['systemctl', 'is-active', unit]).stdout.strip() == 'active', unit
    assert h.cmd(['nmcli', '-g', 'GENERAL.CONNECTION', 'device', 'show', 'wlan2']).stdout.strip() == h.AP_PROFILE
    assert 'Connected to e8:4e:06:ae:d7:09' in h.in_client(['iw', 'dev', 'wlan0', 'link']).stdout


def run():
    active_fixture()
    assert (h.ROOT / 'monitor-admission.json').exists()
    ethernet_check()
    h.usb_check()
    for suffix, iface in [('ap', 'wlan2'), ('peer', 'wlan0')]:
        args = ['/usr/bin/tcpdump', '-n', '-U', '-s', '0', '-i', iface,
                '-w', str(h.ROOT / (suffix + '.pcap')),
                'arp or udp port 67 or udp port 68 or udp port 5353 or tcp port 18443']
        if suffix == 'peer':
            args = ['ip', 'netns', 'exec', h.NETNS, *args]
        h.system_unit('phase11-hotspot-capture-' + suffix, args)
    (h.ROOT / 'target-changed').touch()
    h.console('CONFIG ' + json.dumps(json.loads((h.ROOT / 'test-config.json').read_text())))
    h.console('REBOOT')
    time.sleep(3)
    initial = h.ready('10.77.14.10')
    h.save('hotspot-baseline.json', initial)
    boot = initial['status']['boot_id']
    h.save('trace-boot.json', {'boot': boot, 'revision': initial['revision']})
    h.system_unit('phase11-radio-trace', ['python3', h.ROOT / 'scripts/phase11_4_radio_diagnostic.py',
                  'trace', '--root', h.ROOT, '--run'])
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not (h.ROOT / 'trace-ready').exists():
        time.sleep(.1)
    assert (h.ROOT / 'trace-ready').exists()
    good = reference('10.77.14.10', boot, 'reference-baseline')
    h.note('BASELINE_RESULT', {'pass': good, 'boot': boot})
    print('BASELINE ' + ('PASS; ready for production comparison' if good else 'FAILED; no DHCP change'), flush=True)
    if not good:
        raise RuntimeError('Unchanged-address baseline failed: analyze before DHCP')


def change():
    active_fixture()
    ethernet_check()
    assert json.loads((h.ROOT / 'reference-baseline.json').read_text())['exit'] == 0
    # The actual production observer is independently audited before mutation.
    production = json.loads((h.ROOT / 'production-baseline/PASS.json').read_text())
    audit = json.loads((h.ROOT / 'production-baseline/audit.json').read_text())
    initial = json.loads((h.ROOT / 'hotspot-baseline.json').read_text())
    boot = initial['status']['boot_id']
    assert production['host']['identity']['boot_id'] == boot
    assert audit['load'] == audit['arm'] == 0
    assert all(op in ('HELLO', 'STATUS', 'CAPS') for op in audit['tx_ops'])
    assert h.cmd(['systemctl', 'is-active', 'phase11-radio-trace']).stdout.strip() == 'active'
    h.ready('10.77.14.10', boot)
    (h.ROOT / 'dhcp-hosts').write_text(h.MAC + ',10.77.14.20,60s\n')
    h.note('DHCP_BINDING_CHANGE', {'old': '10.77.14.10', 'new': '10.77.14.20', 'boot': boot})
    h.cmd(['systemctl', 'kill', '-s', 'HUP', 'phase11-hotspot-dhcp'])
    changed = h.ready('10.77.14.20', boot)
    h.save('hotspot-changed.json', changed)
    assert reference('10.77.14.20', boot, 'reference-changed')
    h.usb_check()
    for field in ('station', 'schedules', 'watermark_utc_ns', 'enabled', 'expires_utc_s'):
        assert initial['status'][field] == changed['status'][field]
    h.note('DHCP_TRANSITION_PASS', {'old': '10.77.14.10', 'new': '10.77.14.20', 'boot': boot})
    print('DHCP PASS: same boot, native discovery, authenticated WTP and HTTPS', flush=True)


def cleanup():
    if not (h.ROOT / 'setup-started').exists():
        print('No setup marker; no cleanup mutation')
        return
    (h.ROOT / 'cleanup-started').touch()
    for name in ('phase11-radio-run', 'phase11-radio-trace',
                 'phase11-radio-production', 'phase11-radio-change'):
        h.cmd(['systemctl', 'stop', name], check=False)
    # A directly invoked controller may not belong to one of those units.
    # The marker refuses new work; serialize restoration with an existing one.
    with (h.ROOT / 'controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        restore()


def restore():
    failures = []
    try:
        h.cleanup()
    except Exception as e:
        failures.append('Base fixture: ' + str(e))
    h.cmd(['systemctl', 'stop', 'phase11-hotspot-capture-monitor',
           'phase11-radio-monitor-vif', 'phase11-radio-monitor-check',
           'phase11-radio-monitor-associated', 'phase11-radio-monitor-station'], check=False)
    try:
        child = Path('/sys/class/net/radiomon0')
        if (h.ROOT / 'monitor-child-created').exists() and child.exists():
            assert (child / 'phy80211').resolve() == Path('/sys/class/net/wlan1/phy80211').resolve()
            assert Path('/sys/class/net/wlan1/address').read_text().strip() == MANAGEMENT_MAC
            h.cmd(['iw', 'dev', 'radiomon0', 'del'])
    except Exception as e:
        failures.append('Monitor child: ' + str(e))
    try:
        assert Path('/sys/class/net/wlan1/address').read_text().strip() == MANAGEMENT_MAC
        h.cmd(['ip', 'link', 'set', 'wlan1', 'down'])
        h.cmd(['iw', 'dev', 'wlan1', 'set', 'type', 'managed'])
        h.cmd(['nmcli', 'device', 'set', 'wlan1', 'managed', 'yes'])
        h.cmd(['iw', 'dev', 'wlan1', 'set', 'power_save',
               json.loads((h.ROOT / 'management-power.json').read_text())['value']])
        deadline = time.monotonic() + 15
        state = ''
        while time.monotonic() < deadline:
            state = h.cmd(['nmcli', '-g', 'GENERAL.STATE', 'device', 'show', 'wlan1'], check=False).stdout
            if state.startswith(('30 ', '100 ')):
                break
            time.sleep(.2)
        assert state.startswith(('30 ', '100 ')), 'Management radio not ready in NetworkManager'
        if not state.startswith('100 '):
            h.cmd(['nmcli', '--wait', '25', 'connection', 'up', 'uuid', h.PROFILE, 'ifname', 'wlan1'])
    except Exception as e:
        failures.append('Management radio: ' + str(e))
    try:
        h.cmd(['systemctl', 'start', 'pi-wifi-recover.timer'])
        h.cmd(['systemctl', 'start', 'pi-wifi-recover.service'], timeout=55)
        final = BASE_HOST_CHECK()
        assert 'Connected to ' + BSSID in final['management']
        h.save('management-restored.json', final)
    except Exception as e:
        failures.append('Final management: ' + str(e))
    h.save('radio-cleanup-result.json', {'failures': failures})
    print('RADIO CLEANUP ' + ('PASS' if not failures else json.dumps(failures)), flush=True)
    assert not failures


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['setup', 'run', 'change', 'trace', 'cleanup'])
    p.add_argument('--root', required=True, type=Path)
    p.add_argument('--run', action='store_true')
    a = p.parse_args()
    if not a.run:
        print('Plan only; explicit --run required')
        return
    if not __debug__ or sys.platform != 'linux' or os.geteuid() != 0:
        raise RuntimeError('Linux root and enabled assertions required')
    os.umask(0o077)
    os.environ['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'
    h.ROOT = a.root.resolve()
    assert h.ROOT.is_dir() and h.ROOT.stat().st_mode & 0o077 == 0
    h.AP_IF, h.CLIENT_IF = 'wlan2', 'wlan0'
    h.host_check = ethernet_check
    if a.command in ('setup', 'run', 'change'):
        with (h.ROOT / 'controller.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            globals()[a.command]()
    else:
        globals()[a.command]()


if __name__ == '__main__':
    main()
