#!/usr/bin/env python3
"""Opt-in, host-only wspr5 fixture for the Phase 11.5 contention campaign.

Does not open USB, flash, submit jobs, change Pico configuration, or touch the
installed WsprryPi process. A separate campaign controls the DUT. This fixture
owns an isolated AP, one client namespace, a temporary chrony ACL and a bounded
pause of the Wi-Fi recovery timer. All setup steps have write-ahead ownership
records; a separately armed cleanup service precedes the first host mutation.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time

from phase11_5_inventory import require

PREFIX = 'phase115-closure'
NETNS = PREFIX + '-client'
PROFILE = PREFIX + '-ap'
SUBNET = '10.77.15.0/24'
AP_ADDRESS = '10.77.15.1'
CLIENT_ADDRESS = '10.77.15.2'
DUT_ADDRESS = '10.77.15.10'
DUT_MAC = '88:a2:9e:0a:60:df'
TIME_NAME = 'clock.phase115.test'
RADIOS = {'wlan0': '2c:cf:67:62:76:66', 'wlan2': 'e8:4e:06:ae:d7:09'}
MANAGEMENT = '90:de:80:47:b9:da'
ETHERNET = '2c:cf:67:62:76:64'
HOST_BOOT = '220e53ca-ca95-4206-9581-dbe28aa1eeb8'
MANAGEMENT_PROFILE = '921301fe-cdfd-4965-8ac7-c96e9d908ea6'
INSTALLED_SHA = 'c19461bc6d2ebe7cae61798ad9acae8d43dfbec3ee57c288e4ef41e9c82b8273'
RUN_SECONDS = 21000  # 5 h 50 min; last ten minutes reserved for host restoration.
UNIT_SUFFIXES = ('cleanup.timer', 'cleanup.service', 'client.service', 'dhcp.service',
                 'capture-ap.service', 'capture-client.service', 'campaign.service', 'time-local.service')


def fixture_wifi(root, packet, mdns, dns):
    """Select credentials before host mutation; retained inputs never rewrite the DUT."""
    expected_ntp = 'time.local' if mdns else TIME_NAME if dns else AP_ADDRESS
    retained = packet.get('retained_wifi_sha256')
    if retained is None:
        return dict(ssid='WsprryPico-Phase115', password=secrets.token_hex(16), ntp_ipv4=expected_ntp)
    require(packet.get('schema') == 'phase11.5-r3-retained-fixture-v1' and packet.get('family') == 'R3'
            and packet.get('configuration_writes') == 0 and mdns and not dns,
            'Retained Wi-Fi requires the explicit no-write R3 lifecycle')
    raw = (root / 'retained-wifi.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest() == retained, 'Retained Wi-Fi input changed')
    value = json.loads(raw)
    require(set(value) == {'ssid', 'password', 'ntp_ipv4'} and value['ssid'] == 'WsprryPico-Phase115'
            and value['ntp_ipv4'] == expected_ntp and isinstance(value['password'], str)
            and len(value['password']) == 32 and all(c in '0123456789abcdef' for c in value['password']),
            'Unexpected retained Wi-Fi configuration')
    return value


class Fixture:
    def __init__(self, root):
        self.root = root
        self.state_path = root / 'fixture-state.json'
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        self.deadline = None

    def note(self, kind, value):
        with (self.root / 'fixture.jsonl').open('a') as stream:
            stream.write(json.dumps({'monotonic_ns': time.monotonic_ns(),
                'utc_ns': time.time_ns(), 'kind': kind, 'value': value}) + '\n')
            stream.flush()
            os.fsync(stream.fileno())

    def save(self):
        path = self.root / 'fixture-state.tmp'
        with path.open('w') as stream:
            json.dump(self.state, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        path.replace(self.state_path)
        fd = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def intent(self, key):
        self.state[key] = True
        self.save()

    def cmd(self, args, check=True, timeout=35):
        # PSKs can occur in argv; never report command arguments or output on an
        # exception. Full sensitive fixture files stay owner-only, outside Git.
        if self.deadline is not None:
            timeout = min(timeout, self.deadline - time.monotonic())
            require(timeout > 0, 'Fixture setup deadline exceeded')
        try:
            result = subprocess.run([str(arg) for arg in args], capture_output=True,
                                    text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            self.note('timeout', {'program': Path(args[0]).name, 'seconds': timeout})
            raise TimeoutError('Fixture command deadline: ' + Path(args[0]).name) from None
        if check and result.returncode:
            self.note('command_failed', {'program': Path(args[0]).name,
                                         'exit': result.returncode})
            raise RuntimeError('Fixture command failed: ' + Path(args[0]).name)
        return result

    def value(self, *args):
        return self.cmd(args).stdout.strip()

    def host(self, paused=False):
        require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == HOST_BOOT,
                'Host boot changed')
        for name, mac in {'eth0': ETHERNET, 'wlan1': MANAGEMENT}.items():
            require(Path('/sys/class/net/' + name + '/address').read_text().strip() == mac,
                    'Management interface identity changed')
        require(Path('/sys/class/net/eth0/carrier').read_text().strip() == '1',
                'Ethernet carrier absent')
        require(Path('/proc/sys/net/ipv4/ip_forward').read_text().strip() == '0',
                'Host forwarding must already be disabled; fixture does not change sysctls')
        require('fe80::2ecf:67ff:fe62:7664' in self.value('ip', '-6', 'address', 'show', 'dev', 'eth0'),
                'Verified Ethernet management address absent')
        require(self.value('nmcli', '-g', 'GENERAL.CON-UUID', 'device', 'show', 'wlan1') ==
                MANAGEMENT_PROFILE, 'Ordinary management connection changed')
        require(self.value('systemctl', 'is-active', 'wsprrypi.service') == 'active',
                'Installed service changed')
        require(hashlib.sha256(Path('/usr/local/bin/wsprrypi').read_bytes()).hexdigest() ==
                INSTALLED_SHA, 'Installed binary changed')
        require(self.value('systemctl', 'is-enabled', 'pi-wifi-recover.timer') == 'enabled',
                'Recovery timer enablement changed')
        active = self.cmd(['systemctl', 'is-active', 'pi-wifi-recover.timer'], check=False)
        require(active.stdout.strip() == ('inactive' if paused else 'active'),
                'Recovery timer activity differs from the fixture stage')
        return {'interfaces': self.value('ip', '-brief', 'address'),
                'routes': self.value('ip', '-4', 'route'),
                'installed_pid': self.value('systemctl', 'show', '-p', 'MainPID', '--value',
                                            'wsprrypi.service')}

    def preflight(self):
        require(not self.state, 'Fresh private fixture root required')
        space = os.statvfs(self.root)
        require(space.f_bavail * space.f_frsize >= 1 << 30, 'Less than 1 GiB evidence space')
        before = self.host()
        require('10.77.15.' not in before['interfaces'] + before['routes'],
                'Fixture subnet already present')
        require(NETNS not in self.value('ip', 'netns', 'list'), 'Namespace exists')
        require(PROFILE not in self.value('nmcli', '-g', 'NAME', 'connection', 'show'),
                'AP profile exists')
        for suffix in UNIT_SUFFIXES:
            name = PREFIX + '-' + suffix
            state = self.value('systemctl', 'show', '--property=LoadState', '--value', name)
            require(state == 'not-found', 'Fixture unit name already exists: ' + name)
        require(self.cmd(['systemctl', 'is-active', 'pi-wifi-recover.service'],
                         check=False).stdout.strip() == 'inactive', 'Recovery service is running')
        require('Access denied' in self.value('chronyc', 'accheck', DUT_ADDRESS),
                'Existing chrony ACL would be changed')
        radio = {}
        for name, mac in RADIOS.items():
            require(Path('/sys/class/net/' + name + '/address').read_text().strip() == mac,
                    'Radio identity changed')
            require(self.value('nmcli', '-g', 'GENERAL.STATE', 'dev', 'show', name).startswith('30 '),
                    'Radio is in use')
            power = self.value('iw', 'dev', name, 'get', 'power_save').split()[-1]
            require(power in ('on', 'off'), 'Unknown power-save setting')
            radio[mac] = {'interface': name, 'power_save': power}
        self.note('preflight', before)
        return before, radio

    def unit(self, suffix, args):
        name = PREFIX + '-' + suffix + '.service'
        require(suffix + '.service' in UNIT_SUFFIXES and suffix != 'cleanup', 'Unknown unit')
        self.state.setdefault('units', []).append(name)
        self.save()  # Intent is durable even if systemd starts it then the caller disconnects.
        self.cmd(['systemd-run', '--quiet', '--collect', '--unit=' + name,
            '--description=' + self.state['token'], '--property=UMask=0077',
            '--property=RuntimeMaxSec=' + str(self.state.get('runtime_seconds', RUN_SECONDS)), '--property=TimeoutStopSec=10',
            '--property=KillSignal=SIGINT', '--property=WorkingDirectory=' + str(self.root),
            '--property=StandardOutput=append:' + str(self.root / (suffix + '.log')),
            '--property=StandardError=append:' + str(self.root / (suffix + '.log')), *args])

    def setup(self):
        self.deadline = time.monotonic() + 300
        before, radio = self.preflight()
        packet = json.loads((self.root / 'packet.json').read_text())
        from phase11_5_join_diagnostics import selected, CAPTURE_FILTER
        join_diagnostics = selected(packet)
        dns_fixture = packet.get('time_server_dns', False)
        require(type(dns_fixture) is bool, 'Explicit DNS fixture selection required')
        mdns_fixture = packet.get('time_server_mdns', False)
        require(type(mdns_fixture) is bool and not (mdns_fixture and dns_fixture),
                'Select native mDNS or legacy DNS, never both')
        wifi = fixture_wifi(self.root, packet, mdns_fixture, dns_fixture)
        permanent = None
        if mdns_fixture:
            from phase11_5_time_local import baseline, DROPIN, RUNTIME
            require(not DROPIN.exists() and not RUNTIME.exists(), 'Temporary time.local owner exists')
            permanent = baseline()
        runtime = packet.get('network_runtime_seconds', RUN_SECONDS)
        require(type(runtime) is int and 0 < runtime <= RUN_SECONDS, 'Bounded host runtime')
        absolute = packet.get('absolute_host_deadline_monotonic_ns')
        if absolute is not None:
            require(type(absolute) is int and time.monotonic_ns() + (runtime+600)*1_000_000_000
                    <= absolute, 'Original host restoration deadline would be exceeded')
        self.state = {'version': 1, 'token': 'Phase115 fixture ' + secrets.token_hex(16),
                      'host_boot': HOST_BOOT, 'before': before, 'radio': radio, 'units': [],
                      'time_server_dns': dns_fixture, 'runtime_seconds': runtime,
                      'time_server_mdns': mdns_fixture, 'time_local_before': permanent}
        self.save()
        # Arm cleanup before pausing the timer or touching a radio. Cleanup owns
        # only host resources, and cannot erase/reboot an unknown Pico state.
        self.cmd(['systemd-run', '--quiet', '--unit=' + PREFIX + '-cleanup',
            '--description=' + self.state['token'], '--on-active=' + str(runtime) + 's',
            '--property=UMask=0077', '--property=RuntimeMaxSec=600',
            '--property=TimeoutStartSec=600', '--property=WorkingDirectory=' + str(self.root),
            '--property=StandardOutput=append:' + str(self.root / 'cleanup.log'),
            '--property=StandardError=append:' + str(self.root / 'cleanup.log'),
            '/usr/bin/python3', str(Path(__file__).resolve()), 'cleanup', '--root', str(self.root), '--run'])
        self.intent('cleanup_armed')
        self.intent('timer_paused')
        self.cmd(['systemctl', 'stop', 'pi-wifi-recover.timer', 'pi-wifi-recover.service'])
        psk, ssid = wifi['password'], wifi['ssid']
        (self.root / 'pico-wifi.json').write_text(json.dumps(wifi) + '\n')
        self.intent('ap_profile')
        self.cmd(['nmcli', 'connection', 'add', 'save', 'no', 'type', 'wifi', 'ifname', 'wlan0',
            'con-name', PROFILE, 'ssid', ssid, '802-11-wireless.mode', 'ap',
            '802-11-wireless.band', 'bg', '802-11-wireless.channel', '11',
            '802-11-wireless.powersave', '2', 'connection.autoconnect', 'no',
            'ipv4.method', 'manual', 'ipv4.addresses', AP_ADDRESS + '/24',
            'ipv4.never-default', 'yes', 'ipv6.method', 'disabled',
            'wifi-sec.key-mgmt', 'wpa-psk', 'wifi-sec.proto', 'rsn',
            'wifi-sec.pairwise', 'ccmp', 'wifi-sec.psk', psk])
        if join_diagnostics:
            # Start before AP activation: a later capture can miss the entire
            # association/DHCP attempt while the fixture is still being built.
            self.unit('capture-ap', ['/usr/bin/tcpdump', '--immediate-mode', '-i', 'wlan0', '-U', '-s', '0',
                '-w', str(self.root/'capture-ap.pcap'), CAPTURE_FILTER])
            end = time.monotonic() + 5
            while not (self.root/'capture-ap.pcap').exists() and time.monotonic() < end:
                time.sleep(.1)
            require((self.root/'capture-ap.pcap').exists(), 'Early diagnostic capture did not start')
            self.verify_join_capture()
            self.note('join_capture_before_ap', dict(filter=CAPTURE_FILTER))
        self.cmd(['nmcli', '--wait', '25', 'connection', 'up', PROFILE])
        self.cmd(['iw', 'dev', 'wlan0', 'set', 'power_save', 'off'])
        (self.root / 'dhcp-hosts').write_text(DUT_MAC + ',' + DUT_ADDRESS + ',60s\n')
        (self.root / 'dnsmasq.conf').write_text('\n'.join([
            'port=53' if dns_fixture else 'port=0', 'interface=wlan0', 'bind-interfaces', 'dhcp-authoritative',
            'dhcp-range=10.77.15.0,static,255.255.255.0,60s',
            'dhcp-hostsfile=' + str(self.root / 'dhcp-hosts'),
            'dhcp-leasefile=' + str(self.root / 'leases'), 'dhcp-option=3',
            'dhcp-option=6,' + AP_ADDRESS if dns_fixture else 'dhcp-option=6',
            'log-dhcp', 'log-facility=-', 'user=root', 'group=root'] +
            (['except-interface=lo', 'listen-address=' + AP_ADDRESS, 'no-hosts', 'no-resolv',
              'local=/phase115.test/', 'address=/' + TIME_NAME + '/' + AP_ADDRESS,
              'local-ttl=30', 'log-queries'] if dns_fixture else [])) + '\n')
        self.cmd(['/usr/sbin/dnsmasq', '--test', '--conf-file=' + str(self.root / 'dnsmasq.conf')])
        self.unit('dhcp', ['/usr/sbin/dnsmasq', '--keep-in-foreground',
                            '--conf-file=' + str(self.root / 'dnsmasq.conf')])
        self.intent('chrony_acl')
        self.cmd(['chronyc', 'allow', SUBNET])
        self.intent('client_unmanaged')
        self.cmd(['nmcli', 'device', 'set', 'wlan2', 'managed', 'no'])
        self.intent('namespace')
        self.cmd(['ip', 'netns', 'add', NETNS])
        phy = Path('/sys/class/net/wlan2/phy80211').resolve(strict=True).name
        self.cmd(['iw', 'phy', phy, 'set', 'netns', 'name', NETNS])
        self.cmd(['ip', '-n', NETNS, 'link', 'set', 'lo', 'up'])
        (self.root / 'wpa.conf').write_text('ctrl_interface=/run/wpa_supplicant\nnetwork={\n'
            'ssid="' + ssid + '"\npsk="' + psk + '"\nkey_mgmt=WPA-PSK\nproto=RSN\npairwise=CCMP\n}\n')
        (self.root / 'avahi.conf').write_text('[server]\nhost-name=phase115-client\n'
            'use-ipv4=yes\nuse-ipv6=no\nallow-interfaces=wlan2\nenable-dbus=no\n'
            '[publish]\ndisable-publishing=yes\n')
        self.unit('client', ['ip', 'netns', 'exec', NETNS, 'unshare', '--mount',
            '--propagation', 'private', '/usr/bin/python3', str(Path(__file__).resolve()),
            'client', '--root', str(self.root), '--run'])
        deadline = time.monotonic() + 35
        while not (self.root / 'client-ready').exists() and time.monotonic() < deadline:
            time.sleep(.2)
        require((self.root / 'client-ready').exists(), 'Independent client did not start')
        if mdns_fixture:
            from phase11_5_time_local import install
            install(self)
            time.sleep(3)  # Avahi probe/announcement settling; no acceptance from this wait.
            if not join_diagnostics:
                self.unit('capture-ap', ['/usr/bin/tcpdump', '--immediate-mode', '-i', 'wlan0', '-U', '-s', '0',
                    '-w', str(self.root/'capture-ap.pcap'), 'udp port 5353 or udp port 123'])
            pid = self.value('systemctl', 'show', '-p', 'MainPID', '--value', PREFIX+'-client')
            self.unit('capture-client', ['nsenter', '-t', pid, '-m', '-n', '/usr/bin/tcpdump', '--immediate-mode',
                '-i', 'wlan2', '-U', '-s', '0', '-w', str(self.root/'capture-client.pcap'),
                'udp port 5353 or udp port 123'])
            time.sleep(1)
            for side in ('ap', 'client'):
                require((self.root/('capture-'+side+'.pcap')).exists(), 'Capture not started')
        self.verify()
        self.intent('ready')
        self.note('ready', {'host_only': True, 'expires_after_seconds': runtime})
        self.deadline = None

    def in_client(self, args, timeout=35, check=True):
        pid = int(self.value('systemctl', 'show', '-p', 'MainPID', '--value', PREFIX + '-client'))
        require(pid > 1, 'Client namespace supervisor absent')
        require(self.value('systemctl', 'show', '-p', 'Description', '--value', PREFIX + '-client') ==
                self.state['token'], 'Client unit ownership changed')
        return self.cmd(['nsenter', '-t', str(pid), '-m', '-n', *args], timeout=timeout, check=check)

    def verify_join_capture(self):
        require(self.value('systemctl', 'is-active', PREFIX + '-capture-ap.service') == 'active',
                'Diagnostic capture is not active')

    def verify(self):
        from phase11_5_join_diagnostics import selected
        if selected(json.loads((self.root/'packet.json').read_text())):
            self.verify_join_capture()
        current = self.host(paused=True)
        require(current['installed_pid'] == self.state['before']['installed_pid'],
                'Installed application restarted')
        peer = {label: self.in_client(args).stdout for label, args in {
            'link': ['iw', 'dev', 'wlan2', 'link'], 'routes': ['ip', '-4', 'route'],
            'addresses': ['ip', '-brief', 'address'], 'netns': ['readlink', '/proc/self/ns/net'],
            'mountns': ['readlink', '/proc/self/ns/mnt']}.items()}
        require('Connected to ' + RADIOS['wlan0'] in peer['link'], 'Wrong AP')
        require('default' not in peer['routes'] and CLIENT_ADDRESS + '/24' in peer['addresses'],
                'Client isolation differs from plan')
        require(peer['netns'].strip() != os.readlink('/proc/self/ns/net') and
                peer['mountns'].strip() != os.readlink('/proc/self/ns/mnt'), 'Namespace isolation absent')
        self.note('verified', {'host': current, 'peer': peer})

    def stop_owned(self, name):
        load = self.value('systemctl', 'show', '-p', 'LoadState', '--value', name)
        if load == 'not-found':
            return
        require(self.value('systemctl', 'show', '-p', 'Description', '--value', name) ==
                self.state['token'], 'Refusing to stop a unit with changed ownership: ' + name)
        self.cmd(['systemctl', 'stop', name])

    def settle(self, observation, message, seconds=20):
        # NetworkManager's method reply can precede address removal and the
        # final disconnected state. Observe convergence without replaying a
        # mutation or treating a transient state as completed restoration.
        deadline = time.monotonic() + seconds
        while True:
            if observation():
                return
            require(time.monotonic() < deadline, message)
            time.sleep(.2)

    def cleanup(self):
        self.deadline = None
        if not self.state or self.state.get('restored'):
            return
        require(self.state['host_boot'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'Host boot changed; automatic cleanup ownership requires reconciliation')
        failures = []
        def attempt(label, action):
            try:
                action()
            except Exception as error:
                failures.append({'step': label, 'type': type(error).__name__, 'message': str(error)})
        for name in reversed(self.state['units']):
            attempt(name, lambda name=name: self.stop_owned(name))
        if self.state.get('chrony_acl'):
            attempt('chrony', lambda: self.cmd(['chronyc', 'deny', SUBNET]))
        def remove_namespace():
            if NETNS in self.value('ip', 'netns', 'list'):
                self.cmd(['ip', 'netns', 'delete', NETNS])
        def remove_ap():
            if PROFILE in self.value('nmcli', '-g', 'NAME', 'connection', 'show'):
                self.cmd(['nmcli', 'connection', 'delete', PROFILE])
        if self.state.get('namespace'):
            attempt('namespace', remove_namespace)
        if self.state.get('ap_profile'):
            attempt('AP profile', remove_ap)
        def restore_radios():
            # Namespace teardown can return its radio asynchronously after 20 s.
            # Keep this inside the independently bounded ten-minute cleanup.
            deadline = time.monotonic() + 60
            found = {}
            while time.monotonic() < deadline:
                found = {p.read_text().strip(): p.parent.name
                         for p in Path('/sys/class/net').glob('*/address')}
                if all(mac in found for mac in RADIOS.values()):
                    break
                time.sleep(.2)
            require(all(mac in found for mac in RADIOS.values()), 'Radio did not return')
            if self.state.get('client_unmanaged'):
                self.cmd(['nmcli', 'device', 'set', found[RADIOS['wlan2']], 'managed', 'yes'])
            for mac, before in self.state['radio'].items():
                self.cmd(['iw', 'dev', found[mac], 'set', 'power_save', before['power_save']])
                self.settle(lambda: self.value('nmcli', '-g', 'GENERAL.STATE', 'device', 'show',
                                               found[mac]).startswith('30 '),
                            'Restored radio is not disconnected')
        if self.state.get('ap_profile') or self.state.get('client_unmanaged'):
            attempt('radios', restore_radios)
        if self.state.get('time_local_override'):
            from phase11_5_time_local import restore
            attempt('time.local publisher', lambda: restore(self))
        if self.state.get('timer_paused'):
            attempt('recovery timer', lambda: self.cmd(['systemctl', 'start', 'pi-wifi-recover.timer']))
        def verify_host():
            current = None
            def converged():
                nonlocal current
                current = self.host()
                require(current['installed_pid'] == self.state['before']['installed_pid'],
                        'Installed service restarted')
                return '10.77.15.' not in current['interfaces'] + current['routes']
            self.settle(converged, 'Fixture subnet remains')
            require(NETNS not in self.value('ip', 'netns', 'list'), 'Namespace remains')
            require('Access denied' in self.value('chronyc', 'accheck', DUT_ADDRESS), 'Chrony ACL remains')
            if self.state.get('time_server_mdns'):
                from phase11_5_time_local import baseline, validate_preserved
                after = baseline()
                self.note('time_local_after', after)
                validate_preserved(self.state['time_local_before'], after)
            self.note('host_restored', current)
        attempt('final host', verify_host)
        self.note('cleanup', {'failures': failures, 'pico_state': 'not inspected or changed by host cleanup'})
        require(not failures, 'Host cleanup incomplete; inspect private fixture log')
        # Do not stop the executing cleanup service itself.
        if self.state.get('cleanup_armed'):
            self.stop_owned(PREFIX + '-cleanup.timer')
        self.state['restored'] = True
        self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('setup', 'cleanup', 'verify', 'client'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        print('Plan only: no host or device access. --run requires network-fixture authorization.')
        return
    require(sys.platform == 'linux' and os.geteuid() == 0 and __debug__, 'Linux root required')
    root = args.root.resolve(strict=True)
    require(root.is_dir() and root.stat().st_mode & 0o077 == 0, 'Private existing root required')
    os.umask(0o077)
    os.environ['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'
    def interrupted(signum, frame):
        raise InterruptedError('Fixture interrupted')
    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    if args.command == 'client':
        # Existing qualified namespace worker has no USB, job or host-role action.
        import phase11_4_hotspot as old
        old.ROOT, old.CLIENT_IF = root, 'wlan2'
        old.client(CLIENT_ADDRESS)
    else:
        # One setup/cleanup actor globally, including independent timer cleanup.
        # Setup has a five-minute deadline; no lock is held by the client worker.
        with Path('/run/lock/phase115-closure.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            fixture = Fixture(root)
            try:
                getattr(fixture, args.command)()
            except BaseException:
                if args.command == 'setup':
                    fixture.cleanup()
                raise


if __name__ == '__main__':
    main()
