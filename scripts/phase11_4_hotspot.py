#!/usr/bin/env python3
"""Opt-in wspr5 D1 fixture. Private input/evidence directory; no RF or jobs.

Linux/root only; wspr5-specific engineering fixture, not an end-user installer.
Use a fresh private evidence directory for each setup.
The fixture owns only its named units/profile/netns and wlan0/wlan2. Management
wlan1 and installed WsprryPi remain active. Never print configuration secrets.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import ssl
import subprocess
import sys
import time
import types

DEVICE = 'fd6127d11d6aca42a9905fa3fb1bf1d5'
SERIAL = '0BF4B4AEC9FFB344'
NAME = 'wsprrypico-0a60df.local'
MAC = '88:a2:9e:0a:60:df'
PROFILE = '921301fe-cdfd-4965-8ac7-c96e9d908ea6'
NETNS = 'phase11-hotspot'
AP_PROFILE = 'phase11-hotspot-ap'
SUBNET = '10.77.14.0/24'
ROOT = None
AP_IF = 'wlan0'
CLIENT_IF = 'wlan2'


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')


def note(kind, value):
    with (ROOT / 'events.jsonl').open('a') as f:
        f.write(json.dumps(dict(epoch_ns=time.time_ns(), kind=kind, value=value)) + '\n')
        f.flush()
        os.fsync(f.fileno())


def cmd(args, check=True, timeout=35):
    try:
        p = subprocess.run([str(x) for x in args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        # TimeoutExpired includes argv, which can contain the AP password.
        note('COMMAND_TIMEOUT', {'program': Path(args[0]).name, 'timeout': timeout})
        raise TimeoutError(f'{Path(args[0]).name} exceeded {timeout}s') from None
    if check and p.returncode:
        # Arguments may contain the temporary PSK. Never include argv in errors.
        note('COMMAND_FAILURE', {'program': Path(args[0]).name, 'exit': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr})
        raise RuntimeError(f'{Path(args[0]).name} exit {p.returncode}: {p.stderr[-800:]}')
    return p


def system_unit(name, args, seconds=1200):
    return cmd(['systemd-run', '--quiet', '--unit=' + name,
                '--property=RuntimeMaxSec=' + str(seconds), '--property=UMask=0077',
                '--property=KillSignal=SIGINT', '--property=TimeoutStopSec=10',
                '--property=WorkingDirectory=' + str(ROOT),
                '--property=StandardOutput=append:' + str(ROOT / (name + '.log')),
                '--property=StandardError=append:' + str(ROOT / (name + '.log')),
                *args])


def host_check():
    assert cmd(['nmcli', '-g', 'GENERAL.CON-UUID', 'device', 'show', 'wlan1']).stdout.strip() == PROFILE
    assert 'default via 192.168.1.1 dev wlan1' in cmd(['ip', '-4', 'route']).stdout
    assert cmd(['systemctl', 'is-active', 'wsprrypi.service']).stdout.strip() == 'active'
    assert cmd(['systemctl', 'is-active', 'pi-wifi-recover.timer']).stdout.strip() == 'active'
    return {k: cmd(v).stdout for k, v in {
        'interfaces': ['ip', '-brief', 'address'], 'routes': ['ip', '-4', 'route'],
        'management': ['iw', 'dev', 'wlan1', 'link'],
        'profiles': ['nmcli', '-f', 'UUID,NAME,DEVICE', 'connection', 'show', '--active'],
        'time': ['chronyc', 'tracking']}.items()}


def console(command='INFO'):
    from check_usb_target import port, write_all
    from rf_wtp import read_line
    with (ROOT / 'usb.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with port('/dev/serial/by-id/usb-WsprryPi_WsprryPico_' + SERIAL + '-if00') as fd:
            write_all(fd, b'INFO\n')
            value = read_line(fd, time.monotonic() + 8)
            s = value['status']
            assert value['device_id'] == DEVICE and value['deployment_identity_matches']
            assert s['engine'] == 'inhibited-standalone-simulator' and not s['enabled']
            assert s['state'] == 'empty' and s['output_active'] is False and s['storage_healthy']
            note('INFO', value)
            if command == 'INFO':
                return value
            assert not value['recovery_boot'], 'Recovery boot: preserve breadcrumbs before another mutation'
            write_all(fd, (command + '\n').encode())
            response = read_line(fd, time.monotonic() + 10)
            note('CONFIG' if command.startswith('CONFIG ') else command, response)
            assert response['ok']
            return response


def usb_check():
    with (ROOT / 'usb.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        p = cmd(['python3', ROOT / 'scripts/wtp_probe.py',
                 '/dev/serial/by-id/usb-WsprryPi_WsprryPico_' + SERIAL + '-if02', '--run'])
    note('USB_WTP', dict(stdout=p.stdout, stderr=p.stderr, exit=p.returncode))
    records = {r['op']: r['body'] for line in p.stdout.splitlines()
               if (r := json.loads(line))['type'] == 'response'}
    assert records['HELLO']['device_id'] == DEVICE
    assert records['CAPS']['engine'] == 'inhibited-standalone-simulator'
    s = records['STATUS']
    assert s['owner_id'] is None and s['job_id'] is None and s['state'] == 'empty'
    assert s['output_active'] is False
    return records


def client_pid():
    return int(cmd(['systemctl', 'show', '-p', 'MainPID', '--value', 'phase11-hotspot-client']).stdout)


def in_client(args, timeout=40, check=True):
    pid = client_pid()
    assert pid > 1
    return cmd(['nsenter', '-t', str(pid), '-m', '-n', *args], timeout=timeout, check=check)


def setup():
    assert not (ROOT / 'setup-started').exists(), 'Use cleanup before another setup'
    before = host_check()
    assert SUBNET.split('/')[0] not in before['routes']
    assert '10.77.14.' not in before['interfaces']
    radio_state = {}
    for interface, mac in [('wlan0', '2c:cf:67:62:76:66'), ('wlan2', 'e8:4e:06:ae:d7:09')]:
        assert Path('/sys/class/net/' + interface + '/address').read_text().strip() == mac
        assert cmd(['nmcli', '-g', 'GENERAL.STATE', 'dev', 'show', interface]).stdout.startswith('30 ')
        power = cmd(['iw', 'dev', interface, 'get', 'power_save']).stdout.strip().split()[-1]
        assert power in ('on', 'off')
        radio_state[mac] = {'interface': interface, 'power_save': power}
    save('radio-before.json', radio_state)
    assert NETNS not in cmd(['ip', 'netns', 'list']).stdout
    assert AP_PROFILE not in cmd(['nmcli', '-g', 'NAME', 'connection', 'show']).stdout
    assert 'Access denied' in cmd(['chronyc', 'accheck', '10.77.14.10']).stdout
    save('host-before.json', before)
    initial = console()
    usb_check()
    save('pico-before.json', initial)
    wifi = json.loads((ROOT / 'original-wifi.json').read_text())
    assert wifi['ssid'] == 'Bohica-IoT'
    wifi['ntp_ipv4'] = initial['network']['ntp_server']
    s = initial['status']
    original = dict(version=1, enabled=False, station=s['station'], wifi=wifi,
                    schedules=s['schedules'], expires_utc_s=s['expires_utc_s'])
    save('restore.json', original)
    # Independent recovery starts before any network or device mutation.
    cmd(['systemd-run', '--quiet', '--unit=phase11-hotspot-cleanup', '--on-active=20m',
         '--property=WorkingDirectory=' + str(ROOT), '--property=UMask=0077',
         '--property=StandardOutput=append:' + str(ROOT / 'cleanup.log'),
         '--property=StandardError=append:' + str(ROOT / 'cleanup.log'),
         '/usr/bin/python3', ROOT / 'scripts/phase11_4_hotspot.py', 'cleanup', '--root', ROOT, '--run'])
    (ROOT / 'setup-started').touch()
    psk = secrets.token_hex(16)
    ssid = 'WsprryPico-Test'
    cfg = json.loads(json.dumps(original))
    cfg['wifi'] = dict(ssid=ssid, password=psk, ntp_ipv4='10.77.14.1')
    save('test-config.json', cfg)
    cmd(['nmcli', 'connection', 'add', 'save', 'no', 'type', 'wifi', 'ifname', AP_IF,
         'con-name', AP_PROFILE, 'ssid', ssid, '802-11-wireless.mode', 'ap',
         '802-11-wireless.band', 'bg', '802-11-wireless.channel', '11',
         '802-11-wireless.powersave', '2',
         'connection.autoconnect', 'no', 'ipv4.method', 'manual',
         'ipv4.addresses', '10.77.14.1/24', 'ipv4.never-default', 'yes',
         'ipv6.method', 'disabled', 'wifi-sec.key-mgmt', 'wpa-psk',
         'wifi-sec.proto', 'rsn', 'wifi-sec.pairwise', 'ccmp', 'wifi-sec.psk', psk])
    cmd(['nmcli', '--wait', '25', 'connection', 'up', AP_PROFILE])
    cmd(['iw', 'dev', AP_IF, 'set', 'power_save', 'off'])
    (ROOT / 'dhcp-hosts').write_text(MAC + ',10.77.14.10,60s\n')
    (ROOT / 'dnsmasq.conf').write_text('\n'.join([
        'port=0', 'interface=' + AP_IF, 'bind-interfaces', 'dhcp-authoritative',
        'dhcp-range=10.77.14.0,static,255.255.255.0,60s',
        'dhcp-hostsfile=' + str(ROOT / 'dhcp-hosts'),
        'dhcp-leasefile=' + str(ROOT / 'leases'), 'dhcp-option=3', 'dhcp-option=6',
        'log-dhcp', 'log-facility=-', 'user=root', 'group=root']) + '\n')
    cmd(['/usr/sbin/dnsmasq', '--test', '--conf-file=' + str(ROOT / 'dnsmasq.conf')])
    system_unit('phase11-hotspot-dhcp', ['/usr/sbin/dnsmasq', '--keep-in-foreground',
                                         '--conf-file=' + str(ROOT / 'dnsmasq.conf')])
    cmd(['chronyc', 'allow', SUBNET])
    cmd(['nmcli', 'device', 'set', CLIENT_IF, 'managed', 'no'])
    cmd(['ip', 'netns', 'add', NETNS])
    client_phy = Path('/sys/class/net/' + CLIENT_IF + '/phy80211').resolve(strict=True).name
    cmd(['iw', 'phy', client_phy, 'set', 'netns', 'name', NETNS])
    cmd(['ip', '-n', NETNS, 'link', 'set', 'lo', 'up'])
    (ROOT / 'wpa.conf').write_text('ctrl_interface=/run/wpa_supplicant\nnetwork={\n'
                                 'ssid="' + ssid + '"\npsk="' + psk + '"\n'
                                 'key_mgmt=WPA-PSK\nproto=RSN\npairwise=CCMP\n}\n')
    (ROOT / 'avahi.conf').write_text('[server]\nhost-name=wspr-hotspot-client\n'
                                   'use-ipv4=yes\nuse-ipv6=no\nallow-interfaces=' + CLIENT_IF + '\n'
                                   'enable-dbus=no\n[publish]\ndisable-publishing=yes\n')
    system_unit('phase11-hotspot-client', ['ip', 'netns', 'exec', NETNS,
                'unshare', '--mount', '--propagation', 'private', 'python3',
                ROOT / 'scripts/phase11_4_hotspot.py', 'client', '--root', ROOT, '--run'])
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if (ROOT / 'client-ready').exists():
            break
        time.sleep(.5)
    assert (ROOT / 'client-ready').exists(), 'Independent client failed to start'
    verify()


def verify():
    save('client-link.json', {'link': in_client(['iw', 'dev', CLIENT_IF, 'link']).stdout,
         'route': in_client(['ip', '-4', 'route']).stdout,
         'netns_inode': in_client(['readlink', '/proc/self/ns/net']).stdout,
         'mount_inode': in_client(['readlink', '/proc/self/ns/mnt']).stdout})
    ap_mac = Path('/sys/class/net/' + AP_IF + '/address').read_text().strip()
    assert 'Connected to ' + ap_mac in json.loads((ROOT / 'client-link.json').read_text())['link']
    assert in_client(['ping', '-c', '2', '-W', '2', '10.77.14.1']).returncode == 0
    save('host-ready.json', host_check())
    note('FIXTURE_READY', {'ap': AP_IF, 'client': CLIENT_IF, 'subnet': SUBNET})
    print('FIXTURE READY: AP and independent wireless client; management unchanged', flush=True)


def client():
    cmd(['mount', '-t', 'tmpfs', '-o', 'mode=755', 'tmpfs', '/run'])
    children = []
    try:
        children.append(subprocess.Popen(['/usr/sbin/wpa_supplicant', '-i', CLIENT_IF, '-c', str(ROOT / 'wpa.conf')]))
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if 'wpa_state=COMPLETED' in cmd(['wpa_cli', '-i', CLIENT_IF, 'status'], check=False).stdout:
                break
            time.sleep(.5)
        assert 'wpa_state=COMPLETED' in cmd(['wpa_cli', '-i', CLIENT_IF, 'status']).stdout
        cmd(['iw', 'dev', CLIENT_IF, 'set', 'power_save', 'off'])
        cmd(['ip', 'address', 'add', '10.77.14.2/24', 'dev', CLIENT_IF])
        children.append(subprocess.Popen(['/usr/sbin/avahi-daemon', '--no-drop-root', '--no-chroot',
                                         '--no-rlimits', '--debug', '-f', str(ROOT / 'avahi.conf')]))
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not Path('/run/avahi-daemon/socket').exists():
            time.sleep(.1)
        assert Path('/run/avahi-daemon/socket').exists()
        (ROOT / 'client-ready').touch()
        while all(p.poll() is None for p in children):
            time.sleep(1)
    finally:
        for p in children:
            p.terminate()


def probe(address, boot):
    from inhibited_network_acceptance import Peer, check_status
    class Evidence:
        def record(self, kind, value):
            note('client_' + kind, value)
    resolved = sorted({r[4][0] for r in socket.getaddrinfo(NAME, 18443, socket.AF_INET, socket.SOCK_STREAM)})
    note('client_native_dns', {'addresses': resolved, 'expected': address})
    assert resolved == [address], 'Native resolver did not return only current address'
    cfg = json.loads((ROOT / 'peer.json').read_text())
    credentials = Path(cfg['credentials'])
    args = types.SimpleNamespace(address=resolved[0], port=18443, hostname=NAME,
        device_id=DEVICE, boot_id=boot, server_sha256=cfg['fingerprint'],
        ca=credentials / 'ca.crt', cert=credentials / 'client.crt', key=credentials / 'client.key')
    peer = Peer(args, Evidence())
    try:
        peer.open()
        check_status(peer.request('STATUS', {}), boot, unowned=True)
    finally:
        peer.close()
    ctx = ssl.create_default_context(cafile=str(args.ca))
    ctx.minimum_version = ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(str(args.cert), str(args.key))
    ctx.set_alpn_protocols(['http/1.1'])
    with socket.create_connection((NAME, 18443), timeout=8) as raw:
        assert raw.getpeername()[0] == address
        with ctx.wrap_socket(raw, server_hostname=NAME) as tls:
            fp = hashlib.sha256(tls.getpeercert(binary_form=True)).hexdigest()
            assert fp == args.server_sha256 and tls.selected_alpn_protocol() == 'http/1.1'
            tls.sendall(('GET /api/v1/status HTTP/1.1\r\nHost: ' + NAME + ':18443\r\nConnection: close\r\n\r\n').encode())
            data = b''
            end = time.monotonic() + 12
            while True:
                tls.settimeout(max(.01, end - time.monotonic()))
                chunk = tls.recv(4096)
                if not chunk:
                    break
                data += chunk
                assert len(data) < 65536 and time.monotonic() < end
    header, body = data.split(b'\r\n\r\n', 1)
    assert header.startswith(b'HTTP/1.1 200 ')
    value = json.loads(body)
    check_status(value['job'], boot, unowned=True)
    assert value['network']['ipv4'] == address and value['network']['advertised_hostname'] == NAME
    note('CLIENT_PASS', {'address': address, 'boot': boot, 'fingerprint': fp, 'status': value})
    print('CLIENT PASS ' + address)


def ready(address=None, boot=None, seconds=120):
    deadline = time.monotonic() + seconds
    last_error = None
    while time.monotonic() < deadline:
        try:
            v = console()
        except (OSError, TimeoutError) as e:
            last_error = type(e).__name__
            note('USB_WAIT', last_error)
            time.sleep(1)
            continue
        assert not v['recovery_boot'], 'Unexpected recovery boot'
        if boot:
            assert v['status']['boot_id'] == boot, 'Unexpected reboot during lease change'
        if (not address or v['network']['ipv4'] == address) and v['network']['mdns_state'] == 'active' and v['status']['clock_state'] == 'synchronized':
            return v
        time.sleep(1)
    raise RuntimeError('Readiness deadline: ' + str(last_error))


def run():
    assert (ROOT / 'client-ready').exists()
    host_check()
    usb_check()
    # Capture both AP and independent client views; no raw traffic is committed.
    for suffix, interface in [('ap', AP_IF), ('peer', CLIENT_IF)]:
        args = ['/usr/bin/tcpdump', '-n', '-U', '-i', interface, '-w', str(ROOT / (suffix + '.pcap')),
                'arp or udp port 67 or udp port 68 or udp port 5353 or tcp port 18443']
        if suffix == 'peer':
            args = ['ip', 'netns', 'exec', NETNS, *args]
        system_unit('phase11-hotspot-capture-' + suffix, args)
    time.sleep(1)
    (ROOT / 'target-changed').touch()
    console('CONFIG ' + json.dumps(json.loads((ROOT / 'test-config.json').read_text())))
    console('REBOOT')
    time.sleep(3)
    initial = ready('10.77.14.10')
    save('hotspot-baseline.json', initial)
    usb_check()
    change()


def change():
    initial = json.loads((ROOT / 'hotspot-baseline.json').read_text())
    boot = initial['status']['boot_id']
    ready('10.77.14.10', boot)
    result = in_client(['python3', ROOT / 'scripts/phase11_4_hotspot.py', 'probe',
              '10.77.14.10', boot, '--root', ROOT, '--run'])
    note('admitted_probe', {'exit': result.returncode, 'stdout': result.stdout})
    # Change only our DHCP binding. Let the client perform a real renewal/NAK/
    # discovery exchange while its Wi-Fi association stays up.
    (ROOT / 'dhcp-hosts').write_text(MAC + ',10.77.14.20,60s\n')
    note('DHCP_BINDING_CHANGE', {'old': '10.77.14.10', 'new': '10.77.14.20', 'boot': boot})
    cmd(['systemctl', 'kill', '-s', 'HUP', 'phase11-hotspot-dhcp'])
    changed = ready('10.77.14.20', boot)
    save('hotspot-changed.json', changed)
    result = in_client(['python3', ROOT / 'scripts/phase11_4_hotspot.py', 'probe',
              '10.77.14.20', boot, '--root', ROOT, '--run'])
    note('changed_probe', {'exit': result.returncode, 'stdout': result.stdout})
    usb_check()
    for field in ('station', 'schedules', 'watermark_utc_ns', 'enabled', 'expires_utc_s'):
        assert initial['status'][field] == changed['status'][field]
    note('DHCP_TRANSITION_PASS', {'old': '10.77.14.10', 'new': '10.77.14.20', 'boot': boot})
    print('DHCP TRANSITION PASS: unchanged boot/name/certificate; native DNS and authenticated WTP/HTTPS', flush=True)


def cleanup():
    if not (ROOT / 'setup-started').exists():
        print('No setup marker: no cleanup actions taken', flush=True)
        return
    failures = []
    for name in ('run', 'change', 'production', 'production-corrected', 'swap', 'swap-resume', 'swap-finish'):
        cmd(['systemctl', 'stop', 'phase11-hotspot-' + name + '.service'], check=False)
    if (ROOT / 'target-changed').exists() and not (ROOT / 'target-restored').exists():
        try:
            usb_check()
            console('CONFIG ' + json.dumps(json.loads((ROOT / 'restore.json').read_text())))
            console('REBOOT')
            time.sleep(3)
            final = ready()
            original = json.loads((ROOT / 'pico-before.json').read_text())
            assert final['network']['ipv4'].startswith('192.168.1.')
            assert final['network']['stable_hostname'] == NAME
            for field in ('station', 'schedules', 'watermark_utc_ns', 'enabled', 'expires_utc_s'):
                assert final['status'][field] == original['status'][field]
            usb_check()
            save('pico-restored.json', final)
            (ROOT / 'target-restored').touch()
        except Exception as e:
            failures.append('Pico restore: ' + str(e))
    for name in ('capture-ap', 'capture-peer', 'client', 'dhcp'):
        cmd(['systemctl', 'stop', 'phase11-hotspot-' + name], check=False)
    cmd(['chronyc', 'deny', SUBNET], check=False)
    # Destroying the final namespace reference returns its physical radio.
    cmd(['ip', 'netns', 'delete', NETNS], check=False)
    client_mac = {'wlan0': '2c:cf:67:62:76:66', 'wlan2': 'e8:4e:06:ae:d7:09'}[CLIENT_IF]
    returned = None
    for _ in range(50):
        returned = next((p.parent.name for p in Path('/sys/class/net').glob('*/address')
                         if p.read_text().strip() == client_mac), None)
        if returned and cmd(['nmcli', '-g', 'GENERAL.DEVICE', 'dev', 'show', returned], check=False).returncode == 0:
            break
        time.sleep(.2)
    if returned:
        try:
            cmd(['nmcli', 'device', 'set', returned, 'managed', 'yes'])
        except Exception as e:
            failures.append('Client management restore: ' + str(e))
    cmd(['nmcli', 'connection', 'delete', AP_PROFILE], check=False)
    try:
        assert returned, 'Client radio did not return to the host namespace'
        for _ in range(50):
            if '10.77.14.' not in cmd(['ip', '-4', 'route']).stdout:
                break
            time.sleep(.2)
        if (ROOT / 'radio-before.json').exists():
            for mac, state in json.loads((ROOT / 'radio-before.json').read_text()).items():
                name = next((p.parent.name for p in Path('/sys/class/net').glob('*/address')
                             if p.read_text().strip() == mac), None)
                assert name, 'Original radio missing: ' + mac
                cmd(['iw', 'dev', name, 'set', 'power_save', state['power_save']])
        for name in ('capture-ap', 'capture-peer', 'client', 'dhcp'):
            assert cmd(['systemctl', 'is-active', 'phase11-hotspot-' + name], check=False).stdout.strip() in ('inactive', 'failed', 'unknown')
        assert 'Access denied' in cmd(['chronyc', 'accheck', '10.77.14.10']).stdout
        save('host-restored.json', host_check())
        save('returned-radio.json', {'mac': client_mac, 'interface': returned})
        assert NETNS not in cmd(['ip', 'netns', 'list']).stdout
        assert AP_PROFILE not in cmd(['nmcli', '-g', 'NAME', 'connection', 'show']).stdout
        assert '10.77.14.' not in cmd(['ip', '-4', 'route']).stdout
    except Exception as e:
        failures.append('Host restore: ' + str(e))
    save('cleanup-result.json', {'failures': failures})
    print('CLEANUP ' + ('PASS' if not failures else 'FAILED: ' + '; '.join(failures)), flush=True)
    assert not failures


def main():
    global ROOT, AP_IF, CLIENT_IF
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['setup', 'client', 'probe', 'run', 'cleanup', 'verify', 'change'])
    p.add_argument('values', nargs='*')
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--run', action='store_true')
    args = p.parse_args()
    if not args.run:
        print('Plan only. Explicit --run is required for network/device operations.')
        return
    if not __debug__ or sys.platform != 'linux' or os.geteuid() != 0:
        raise RuntimeError('Execution requires Linux root and enabled Python assertions')
    os.environ['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'
    os.umask(0o077)
    ROOT = args.root.resolve()
    assert ROOT.is_dir() and ROOT.stat().st_mode & 0o077 == 0
    if (ROOT / 'roles.json').exists():
        roles = json.loads((ROOT / 'roles.json').read_text())
        AP_IF, CLIENT_IF = roles['ap'], roles['client']
        assert {AP_IF, CLIENT_IF} == {'wlan0', 'wlan2'}
    if args.command == 'probe':
        assert len(args.values) == 2 and args.values[0] in ('10.77.14.10', '10.77.14.20')
        probe(*args.values)
    else:
        assert not args.values
        if args.command in ('run', 'change'):
            with (ROOT / 'controller.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                globals()[args.command]()
        else:
            globals()[args.command]()


if __name__ == '__main__':
    main()
