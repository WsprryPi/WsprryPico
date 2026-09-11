#!/usr/bin/env python3
"""Opt-in, read-only eight-hour diagnostic observers for the original Pico."""
import argparse
import datetime
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import signal
import socket
import ssl
import subprocess
import sys
import time

from phase11_4_loop_common import (
    ADDRESS, DEVICE, NAME, SERVER_SHA, stop_process, validate_https, validate_info,
)

CONSOLE = '/dev/serial/by-id/usb-WsprryPi_WsprryPico_0BF4B4AEC9FFB344-if00'
REVISION = '677ec7fde236-dirty'
BOOT = '3b1e15c0a2bb7c29cabd31a1b1ab2597'


def quiet_window(epoch, start, end):
    # Shared wall-clock schedule; actual traffic and USB pool state qualify quietness.
    return epoch < start or epoch >= end - 120 or (epoch - start) % 600 < 120


def emit(value):
    print(json.dumps(value), flush=True)


def usb_sample(wtp=False):
    from check_usb_target import port, write_all
    from rf_wtp import WtpPeer, read_line
    with port(CONSOLE) as fd:
        write_all(fd, b'INFO\n')
        value = read_line(fd, time.monotonic() + 5)
    result = {'info': value, 'anomalies': []}
    # Retain raw reset/fault data even when validation fails. Never reset/recover it.
    try:
        validate_info(value, BOOT, REVISION)
        if any(value[k] for k in ['fault_stage', 'fault_hash', 'fault_pc', 'fault_status']):
            raise ValueError('reset fault breadcrumb present')
        if value['tls_allocation_failures'] or any(
                p['errors'] for p in value['network']['memory'].values()):
            raise ValueError('allocator error observed')
    except Exception as error:
        result['anomalies'].append(str(error))
    emit(result)
    if wtp and value.get('device_id') == DEVICE:
        with port(CONSOLE[:-2] + '02') as fd:
            peer = WtpPeer(fd)
            hello = peer.request('HELLO', {'versions': ['WTP/1'],
                                'client_name': 'phase11-4-diagnostic-soak',
                                'client_version': '1'}, timeout=3)
            caps = peer.request('CAPS', {}, timeout=3)
            status = peer.request('STATUS', {}, timeout=3)
        emit({'wtp': {'hello': hello, 'caps': caps, 'status': status},
              'identity_output_ok': hello['device_id'] == DEVICE and
              hello['boot_id'] == BOOT and status['boot_id'] == BOOT and
              caps['engine'] == 'inhibited-standalone-simulator' and
              status['output_active'] is False and status['state'] == 'empty' and
              status['owner_id'] is None and status['job_id'] is None})


def network_sample(credentials, host):
    result = {}
    code = ('import json,socket,sys;print(json.dumps(socket.getaddrinfo('
            'sys.argv[1],18443,socket.AF_INET,socket.SOCK_STREAM)))')
    try:
        dns = subprocess.run([sys.executable, '-c', code, NAME],
                             capture_output=True, text=True, timeout=6)
        result['dns'] = {'exit': dns.returncode, 'stdout': dns.stdout,
                         'stderr': dns.stderr}
        result['dns_ok'] = dns.returncode == 0 and {
            v[4][0] for v in json.loads(dns.stdout)} == {ADDRESS}
    except Exception as error:
        result.update(dns_ok=False, dns_error=str(error))
    try:
        cx = ssl.create_default_context(cafile=str(credentials / 'client-ca.crt'))
        identity = credentials / 'operator-browser' if host == 'mac' else credentials
        cx.load_cert_chain(str(identity / 'client.crt'), str(identity / 'client.key'))
        cx.minimum_version = cx.maximum_version = ssl.TLSVersion.TLSv1_3
        cx.set_alpn_protocols(['http/1.1'])
        # Direct IP isolates DNS failure; TLS still verifies the certified hostname.
        with socket.create_connection((ADDRESS, 18443), timeout=3) as raw:
            with cx.wrap_socket(raw, server_hostname=NAME) as stream:
                fingerprint = hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest()
                if fingerprint != SERVER_SHA or stream.selected_alpn_protocol() != 'http/1.1':
                    raise ValueError('certificate fingerprint or ALPN mismatch')
                stream.sendall(f'GET /api/v1/status HTTP/1.1\r\nHost: {NAME}:18443\r\n'
                               'Connection: close\r\n\r\n'.encode())
                data = b''
                deadline = time.monotonic() + 5
                while True:
                    stream.settimeout(max(.001, deadline - time.monotonic()))
                    part = stream.recv(4096)
                    if not part:
                        break
                    data += part
                    if len(data) > 65536 or time.monotonic() >= deadline:
                        raise TimeoutError('bounded HTTPS response')
        class Buffered:
            def makefile(self, mode):
                return io.BytesIO(data)
        response = http.client.HTTPResponse(Buffered())
        response.begin()
        value = {'http': response.status, 'server_sha256': fingerprint,
                 'body': json.loads(response.read())}
        result['https'] = value
        validate_https(value, BOOT)
        result['https_ok'] = True
    except Exception as error:
        result.update(https_ok=False, https_error=type(error).__name__ + ': ' + str(error))
    emit(result)


def host_sample(host):
    commands = ([['/usr/sbin/iw', 'dev', 'wlan1', 'link'],
                 ['/usr/sbin/iw', 'dev', 'wlan1', 'get', 'power_save'],
                 ['nmcli', '-g', 'GENERAL.CON-UUID', 'device', 'show', 'wlan1'],
                 ['ip', '-j', '-4', 'addr', 'show', 'dev', 'wlan1'],
                 ['systemctl', 'is-active', 'pi-wifi-recover.timer', 'wsprrypi.service'],
                 ['systemctl', 'is-enabled', 'pi-wifi-recover.timer']]
                if host == 'linux' else [['/sbin/ifconfig', 'en0'],
                                        ['/usr/sbin/scutil', '--nwi']])
    for command in commands:
        try:
            r = subprocess.run(command, capture_output=True, text=True, timeout=4)
            emit({'command': command, 'exit': r.returncode,
                  'stdout': r.stdout, 'stderr': r.stderr})
        except Exception as error:
            emit({'command': command, 'error': str(error)})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', action='store_true')
    p.add_argument('--host', choices=['linux', 'mac'], required=True)
    p.add_argument('--credentials', type=Path, required=True)
    p.add_argument('--output', type=Path)
    p.add_argument('--start', type=float)
    p.add_argument('--end', type=float)
    p.add_argument('--worker', choices=['usb', 'network', 'host'])
    p.add_argument('--sample', choices=['usb', 'wtp', 'network', 'host'])
    p.add_argument('--no-capture', action='store_true',
                   help='Mac-only fallback when BPF access is unavailable')
    a = p.parse_args()
    if not a.run:
        p.error('explicit --run authorization required')
    if a.no_capture and a.host != 'mac':
        p.error('Linux packet observer is required')
    os.umask(0o077)
    if a.sample:
        if a.sample in ['usb', 'wtp']:
            if a.host != 'linux':
                p.error('USB observer is only on wspr5')
            usb_sample(a.sample == 'wtp')
        elif a.sample == 'network':
            network_sample(a.credentials, a.host)
        else:
            host_sample(a.host)
        return
    if not a.output or a.start is None or a.end is None or not 0 < a.end-a.start <= 28800:
        p.error('output and explicit start/end required, maximum eight hours')
    a.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    base = [sys.executable, '-B', str(Path(__file__).resolve()), '--run',
            '--host', a.host, '--credentials', str(a.credentials)]
    remaining = max(0, a.end - time.time())
    deadline = time.monotonic() + remaining  # clock correction cannot extend runtime
    log = (a.output / ((a.worker or 'supervisor') + '.jsonl')).open('x')
    def note(kind, value):
        log.write(json.dumps({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                             'epoch_ns': time.time_ns(), 'monotonic_ns': time.monotonic_ns(),
                             'kind': kind, 'value': value}) + '\n')
        log.flush()
        os.fsync(log.fileno())
    note('started', vars(a) | {'output': str(a.output), 'credentials': str(a.credentials)})
    def interrupted(signum, frame):
        raise InterruptedError('observer terminated')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    if a.worker:
        interval = {'usb': 5, 'network': 30, 'host': 300}[a.worker]
        count = 0
        while time.monotonic() < deadline and time.time() < a.end:
            epoch = time.time()
            quiet = quiet_window(epoch, a.start, a.end)
            if epoch >= a.start and not (a.worker == 'network' and quiet):
                sample = 'wtp' if a.worker == 'usb' and count % 12 == 0 else a.worker
                begin = time.monotonic()
                try:
                    r = subprocess.run(base + ['--sample', sample],
                                       capture_output=True, text=True, timeout=22)
                    note('sample', {'sample': sample, 'quiet_scheduled': quiet,
                                    'started_epoch': epoch, 'duration': time.monotonic()-begin,
                                    'exit': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr})
                except subprocess.TimeoutExpired as error:
                    note('sample_timeout', {'sample': sample, 'started_epoch': epoch,
                                           'stdout': (error.stdout or b'').decode(errors='replace'),
                                           'stderr': (error.stderr or b'').decode(errors='replace')})
                count += 1
            time.sleep(max(0, min(interval, deadline-time.monotonic(), a.end-time.time())))
        note('interval_finished', {'samples': count, 'review_required': True})
        return
    children = {}
    handles = []
    try:
        if a.no_capture:
            note('capture_unavailable', 'Mac BPF access unavailable; native DNS/HTTPS continue')
        else:
            capture_log = (a.output / 'capture.stderr').open('x')
            handles.append(capture_log)
            children['capture'] = subprocess.Popen(
                ['tcpdump', '-i', 'wlan1' if a.host == 'linux' else 'en0', '-n', '-s', '128',
                 '-U', '-c', '500000', '-w', str(a.output / 'network.pcap'),
                 'ether host 88:a2:9e:0a:60:df or host 192.168.1.47'],
                stdout=capture_log, stderr=capture_log)
        for worker in (['usb', 'network', 'host'] if a.host == 'linux' else ['network', 'host']):
            out = (a.output / (worker + '.stderr')).open('x')
            handles.append(out)
            children[worker] = subprocess.Popen(base + ['--output', str(a.output),
                '--start', str(a.start), '--end', str(a.end), '--worker', worker],
                stdout=out, stderr=out)
        if a.host == 'mac':
            children['awake'] = subprocess.Popen(['/usr/bin/caffeinate', '-i', '-s',
                                                  '-t', str(int(remaining)+60)])
        while time.monotonic() < deadline and time.time() < a.end:
            note('observer_health', {name: child.poll() for name, child in children.items()})
            time.sleep(max(0, min(30, deadline-time.monotonic(), a.end-time.time())))
        # Worker/capture closure is recorded separately from the interval ending.
        note('interval_finished', {'review_required': True})
    finally:
        for name, child in children.items():
            if name != 'capture' and child.poll() is None:
                try:
                    child.wait(timeout=25)
                except subprocess.TimeoutExpired:
                    pass
            note('child_closed', {'name': name, **stop_process(child)})
        for handle in handles:
            handle.close()
        note('closed', {'review_required': True})


if __name__ == '__main__':
    main()
