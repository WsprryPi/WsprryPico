#!/usr/bin/env python3
"""Opt-in Phase 11.4 Linux case: USB-monitored 150-second withdrawal and peer recovery."""

def main():
    import argparse, atexit, contextlib, datetime, fcntl, hashlib, json, os, select, signal, socket, ssl, struct, subprocess, sys, termios, time, uuid, threading
    from pathlib import Path
    from phase11_4_loop_common import stop_process, validate_info, validate_https, validate_host, require
    from check_usb_target import port, write_all
    from rf_wtp import read_line, WtpPeer, open_port

    def interrupted(signum, frame):
        raise InterruptedError('bounded controller interruption')
    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=['orderly', 'inspect', 'diagnose'])
    p.add_argument('--run', action='store_true')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--boot', required=True)
    p.add_argument('--revision', default='e4ff40a56180-dirty')
    p.add_argument('--trace', action='store_true')
    a = p.parse_args()
    require(a.run and __debug__, 'Explicit --run and nonoptimized Python required')
    os.umask(0o077)
    root = a.output
    root.mkdir(mode=0o700)
    log = (root / 'events.jsonl').open('x')
    print('EVIDENCE ' + str(root), flush=True)
    log_lock = threading.RLock()
    console_lock = threading.RLock()
    monitor_stop = threading.Event()
    monitor_faults = []
    monitor = None

    def _note(kind, value):
        row = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'epoch_ns': time.time_ns(), 'monotonic_ns': time.monotonic_ns(), 'kind': kind, 'value': value}
        log.write(json.dumps(row) + '\n')
        log.flush()
        os.fsync(log.fileno())
        if kind != 'console INFO' and kind not in ['wtp_request', 'wtp_response']:
            print(json.dumps(row), flush=True)

    def note(kind, value):
        with log_lock:
            _note(kind, value)
    C = '/dev/serial/by-id/usb-WsprryPi_WsprryPico_0BF4B4AEC9FFB344-if00'
    DEVICE = 'fd6127d11d6aca42a9905fa3fb1bf1d5'
    REV = a.revision
    NAME = 'wsprrypico-0a60df.local'
    SERVER_SHA = '06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016'

    def _console(cmd='INFO'):
        with port(C) as f:
            write_all(f, b'INFO\n')
            v = read_line(f, time.monotonic() + 5)
            note('console INFO', v)
            validate_info(v, a.boot, REV)
            assert v['device_id'] == DEVICE and v['revision'] == REV and v['deployment_identity_matches'] and (not v['recovery_boot'])
            assert v['status']['engine'] == 'inhibited-standalone-simulator' and v['status']['output_active'] is False and v['status']['storage_healthy'] and (not v['status']['enabled'])
            if cmd != 'INFO':
                write_all(f, (cmd + '\n').encode())
                v = read_line(f, time.monotonic() + 5)
                assert v['ok']
        if cmd != 'INFO':
            note('console ' + cmd, v)
        return v

    def console(cmd='INFO'):
        with console_lock:
            return _console(cmd)
    if a.mode == 'inspect':
        deadline = time.monotonic() + 20
        while not Path(C).exists() and time.monotonic() < deadline:
            time.sleep(.5)
        with port(C) as f:
            write_all(f, b'INFO\n')
            value = read_line(f, time.monotonic() + 5)
        note('RECOVERY_INFO', value)
        log.close()
        return
    before = console()
    boot = before['status']['boot_id']
    IP = before['network']['ipv4']
    assert before['network']['mdns_state'] == 'active' and before['network']['advertised_hostname'] == NAME
    assert IP == '192.168.1.47' and before['network']['enabled'] and (before['network']['requested_enabled'] is None)
    note('clock_observed', before['status']['clock_state'])
    fd = open_port(C[:-2] + '02')

    def close_usb():
        nonlocal fd
        if fd is not None:
            try:
                fcntl.ioctl(fd, termios.TIOCMBIC, struct.pack('I', termios.TIOCM_DTR))
            finally:
                os.close(fd)
                fd = None
    atexit.register(close_usb)
    fcntl.ioctl(fd, termios.TIOCMBIC, struct.pack('I', termios.TIOCM_DTR))
    time.sleep(0.2)
    fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack('I', termios.TIOCM_DTR))
    time.sleep(0.1)
    stale = bytearray()
    until = time.monotonic() + 0.3
    while time.monotonic() < until:
        if select.select([fd], [], [], 0.03)[0]:
            stale.extend(os.read(fd, 4096))
            assert len(stale) < 65536
    (root / 'usb-pre-hello.bin').write_bytes(stale)
    note('pre_hello_drain', {'bytes': len(stale)})

    class LoggedPeer(WtpPeer):

        def _receive(self):
            from validate_wtp_contract import loads_strict
            chunk = os.read(self.fd, 4096)
            if not chunk:
                raise ConnectionError('USB closed')
            raw_wire.write(chunk)
            raw_wire.flush()
            for payload in self.decoder.feed(chunk):
                message = loads_strict(payload.decode('utf-8'))
                assert message.get('protocol') == 'WTP/1' and message.get('session_id') == self.session and (message.get('type') in ('response', 'event'))
                wire.write(json.dumps(message) + '\n')
                wire.flush()
                self.pending.append(message)
    peer = LoggedPeer(fd)
    wire = (root / 'usb-frames.jsonl').open('x')
    raw_wire = (root / 'usb-wire.bin').open('xb')

    def wtp(op, body={}):
        note('wtp_request', {'session': peer.session, 'op': op, 'body': body})
        v = peer.request(op, body)
        wire.flush()
        note('wtp_response', {'op': op, 'body': v})
        return v
    h = wtp('HELLO', {'versions': ['WTP/1'], 'client_name': 'phase11-4-d1-d3', 'client_version': '1'})
    assert h['device_id'] == DEVICE and h['boot_id'] == boot
    caps = wtp('CAPS')
    assert caps['engine'] == 'inhibited-standalone-simulator'

    def status(empty=False):
        s = wtp('STATUS')
        assert s['boot_id'] == boot and s['output_active'] is False
        if empty:
            assert s['owner_id'] is None and s['job_id'] is None and (s['state'] == 'empty')
        return s
    status(True)

    def nss(label):
        start = time.time_ns()
        try:
            r = subprocess.run(['getent', 'ahostsv4', NAME], capture_output=True, text=True, timeout=6)
            value = dict(exit=r.returncode, stdout=r.stdout, stderr=r.stderr)
        except subprocess.TimeoutExpired:
            value = dict(exit=124, stdout='', stderr='timeout')
        value.update(label=label, started_ns=start, ended_ns=time.time_ns())
        note('nss', value)
        return value
    ca = Path('/home/pi/phase11-4-acceptance/controller')

    def https():
        import http.client, io
        cx = ssl.create_default_context(cafile=str(ca / 'client-ca.crt'))
        cx.minimum_version = cx.maximum_version = ssl.TLSVersion.TLSv1_3
        cx.load_cert_chain(str(ca / 'client.crt'), str(ca / 'client.key'))
        cx.set_alpn_protocols(['http/1.1'])
        with socket.create_connection((IP, 18443), timeout=8) as raw:
            with cx.wrap_socket(raw, server_hostname=NAME) as stream:
                assert hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest() == SERVER_SHA and stream.selected_alpn_protocol() == 'http/1.1'
                stream.sendall(f'GET /api/v1/status HTTP/1.1\r\nHost: {NAME}:18443\r\nConnection: close\r\n\r\n'.encode())
                data = b''
                end = time.monotonic() + 10
                while True:
                    stream.settimeout(max(0.001, end - time.monotonic()))
                    part = stream.recv(4096)
                    if not part:
                        break
                    data += part
                    assert len(data) < 65536 and time.monotonic() < end

        class Buffered:

            def makefile(self, mode):
                return io.BytesIO(data)
        r = http.client.HTTPResponse(Buffered())
        r.begin()
        v = json.loads(r.read())
        assert r.status == 200 and v['job']['boot_id'] == boot and (v['job']['output_active'] is False)
        validate_https({'http': r.status, 'server_sha256': SERVER_SHA, 'body': v}, boot)
        note('verified_https', {'http': r.status, 'server_sha256': SERVER_SHA, 'body': v})
        return v

    host_baseline = None
    last_host = 0

    def host_path():
        nonlocal host_baseline, last_host
        value = {}
        for key, cmd in {
            'link': ['/usr/sbin/iw', 'dev', 'wlan1', 'link'],
            'profile': ['nmcli', '-g', 'GENERAL.CON-UUID', 'device', 'show', 'wlan1'],
            'address': ['ip', '-j', '-4', 'addr', 'show', 'dev', 'wlan1'],
            'recovery_active': ['systemctl', 'is-active', 'pi-wifi-recover.timer'],
            'recovery_enabled': ['systemctl', 'is-enabled', 'pi-wifi-recover.timer'],
        }.items():
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            value[key] = result.stdout.strip()
            assert result.returncode == 0, 'host metadata failure: ' + key
        value['mac'] = Path('/sys/class/net/wlan1/address').read_text().strip()
        note('HOST_PATH', value)
        fingerprint = validate_host(value)
        if host_baseline is None:
            host_baseline = fingerprint
        assert fingerprint == host_baseline, 'host association changed during case'
        last_host = time.monotonic()

    def snapshot():
        if time.monotonic() - last_host > 10:
            host_path()
        if monitor_faults:
            raise RuntimeError('independent USB observer failed: ' + str(monitor_faults))
        v = console()
        u = status(True)
        assert v['status']['boot_id'] == boot
        for key in ['station', 'schedules', 'watermark_utc_ns', 'expires_utc_s', 'enabled', 'suspended']:
            assert v['status'][key] == before['status'][key]
        return v

    def wait_observed(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            snapshot()
            time.sleep(min(3, max(0, end - time.monotonic())))

    def tcp_check():
        start = time.time_ns()
        try:
            with socket.create_connection((IP, 18443), timeout=3) as sock:
                result = {'ok': True, 'local': sock.getsockname(), 'peer': sock.getpeername()}
        except OSError as e:
            result = {'ok': False, 'error': type(e).__name__ + ': ' + str(e)}
        result.update(started_ns=start, ended_ns=time.time_ns())
        note('tcp_probe', result)
        return result

    def neighbor():
        r = subprocess.run(['ip', '-j', 'neigh', 'show', IP, 'dev', 'wlan1'], capture_output=True, text=True, timeout=3)
        note('neighbor', {'exit': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr})

    def fault_arp_diagnostic():
        note('fault_arp_begin', {})
        snapshot()
        r = subprocess.run(['/usr/bin/arping', '-b', '-I', 'wlan1', '-c', '3', '-w', '4', IP], capture_output=True, text=True, timeout=6)
        note('fault_broadcast_arp', {'exit': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr})
        snapshot()
        src = bytes.fromhex(Path('/sys/class/net/wlan1/address').read_text().strip().replace(':', ''))
        dst = bytes.fromhex('88a29e0a60df')
        frame = dst + src + bytes.fromhex('0806') + struct.pack('!HHBBH', 1, 2048, 6, 4, 1) + src + socket.inet_aton('192.168.1.117') + bytes(6) + socket.inet_aton(IP)
        with socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(2054)) as raw:
            raw.bind(('wlan1', 0))
            for i in range(3):
                sent = raw.send(frame)
                note('fault_unicast_arp_request', {'hex': frame.hex(), 'bytes': sent})
                time.sleep(1)
        snapshot()
        neighbor()
        tcp_check()
        note('fault_arp_end', {})

    trace_cursor = 0
    def trace_pages():
        nonlocal trace_cursor
        # Bounded work per sample, cursor reads are non-destructive.
        with console_lock:
            with port(C) as f:
                for _ in range(8):
                    write_all(f, ('NETTRACE ' + str(trace_cursor) + '\n').encode())
                    value = read_line(f, time.monotonic() + 5)
                    note('NETTRACE', value)
                    require(value.get('ok') and value.get('device_id') == DEVICE and
                            value.get('revision') == REV and value.get('boot_id') == boot,
                            'trace identity mismatch')
                    trace = value['trace']
                    require(trace['install_errors'] == 0 and trace['intact'], 'trace hooks invalid')
                    events = trace['events']
                    if events:
                        # Initial ring may have overwritten pre-observer startup only.
                        if trace_cursor == 0:
                            trace_cursor = events[0]['seq'] - 1
                        require(events[0]['seq'] == trace_cursor + 1 and all(
                            y['seq'] == x['seq'] + 1 for x, y in zip(events, events[1:])),
                            'trace coverage gap')
                        trace_cursor = events[-1]['seq']
                    if trace_cursor == trace['latest']:
                        break

    def monitor_usb():
        while not monitor_stop.is_set():
            try:
                v = console()
                if a.trace:
                    trace_pages()
                for key in ['station', 'schedules', 'watermark_utc_ns', 'expires_utc_s', 'enabled', 'suspended']:
                    assert v['status'][key] == before['status'][key], 'saved state changed: ' + key
            except BaseException as e:
                monitor_faults.append({'type': type(e).__name__, 'message': str(e)})
                note('USB_MONITOR_FAILURE', monitor_faults[-1])
                return
            monitor_stop.wait(0.25)
    capture = None
    diag = None
    off = False
    recovered = False
    error = None
    try:
        host_path()
        capture_log = (root / 'capture.log').open('xb')
        diag_log = (root / 'diagnostic-capture.log').open('xb')
        capture = subprocess.Popen(['/usr/bin/tcpdump', '-n', '-U', '-i', 'wlan1', '-c', '3000', '-w', str(root / 'mdns.pcap'), 'ip and udp port 5353 and (ether host 88:a2:9e:0a:60:df or host 192.168.1.117 or host 192.168.1.27)'], stdout=capture_log, stderr=capture_log)
        flt = '(arp and (ether host 88:a2:9e:0a:60:df or arp host ' + IP + ')) or (ip and tcp port 18443 and host ' + IP + ') or ((udp port 67 or 68) and udp[36:4]=0x88a29e0a and udp[40:2]=0x60df)'
        diag = subprocess.Popen(['/usr/bin/tcpdump', '-n', '-U', '-i', 'wlan1', '-c', '5000', '-w', str(root / 'diagnostic.pcap'), flt], stdout=diag_log, stderr=diag_log)
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            assert capture.poll() is None and diag.poll() is None, 'capture child exited before ready'
            if all(((root / n).exists() and (root / n).stat().st_size >= 24 for n in ['mdns.pcap', 'diagnostic.pcap'])):
                break
            time.sleep(0.1)
        assert all(((root / n).exists() and (root / n).stat().st_size >= 24 for n in ['mdns.pcap', 'diagnostic.pcap'])), 'missing PCAP headers'
        if a.trace:
            trace_pages()
        monitor = threading.Thread(target=monitor_usb, name='USB observer', daemon=True)
        monitor.start()
        note('OBSERVERS_READY', {})
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as mdns:
            mdns.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            mdns.bind(('', 5353))
            mdns.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton('192.168.1.117'))
            mdns.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
            labels = b''.join((bytes([len(x)]) + x.encode() for x in NAME.split('.'))) + b'\x00'
            mdns.sendto(struct.pack('>6H', 0, 0, 1, 0, 0, 0) + labels + struct.pack('>HH', 1, 1), ('224.0.0.251', 5353))
        note('seed_socket_closed', {})
        wait_observed(3)
        if a.mode == 'diagnose':
            note('READ_ONLY_DIAGNOSTIC', {})
            fault_arp_diagnostic()
            wait_observed(30)
            nss('diagnostic')
            try:
                https()
            except Exception as e:
                note('https_failure', {'type': type(e).__name__, 'message': str(e)})
            raise RuntimeError('read-only diagnostic completed; no OFF/ON requested')
        r = nss('before')
        if not (r['exit'] == 0 and {l.split()[0] for l in r['stdout'].splitlines()} == {IP}):
            note('BASELINE_FAILURE', r)
            fault_arp_diagnostic()
            raise RuntimeError('baseline NSS failed before any OFF')
        https()
        neighbor()
        snapshot()
        note('off_begin', {})
        off = True
        console('WIFI OFF')
        start = time.monotonic()
        assert not snapshot()['network']['enabled']
        while time.monotonic() - start < 1.3:
            snapshot()
            time.sleep(0.1)
        outage_failures = []
        for delay in [3, 10, 40, 80, 125, 145]:
            wait_observed(max(0, delay - (time.monotonic() - start)))
            r = nss('off-' + str(delay))
            if r['exit'] != 2 or r['stdout']:
                outage_failures.append(r)
                note('OUTAGE_LOOKUP_FAILURE', r)
        wait_observed(max(0, 150 - (time.monotonic() - start)))
        note('on_begin', {})
        on = time.monotonic()
        snapshot()
        console('WIFI ON')
        off = False
        first_active = None
        failures = []
        stable_start = None
        successes = 0
        while time.monotonic() - on < 120:
            v = snapshot()
            assert capture.poll() is None and diag.poll() is None
            if v['network']['mdns_state'] != 'active':
                time.sleep(1)
                continue
            assert v['network']['ipv4'] == IP
            if first_active is None:
                first_active = time.monotonic()
                note('local_active', {'seconds_after_on': first_active - on})
            r = nss('restored' if successes == 0 and (not failures) else 'recovery-' + str(time.time_ns()))
            good = r['exit'] == 0 and {l.split()[0] for l in r['stdout'].splitlines()} == {IP}
            if good:
                try:
                    https()
                except Exception as e:
                    good = False
                    note('https_failure', {'type': type(e).__name__, 'message': str(e)})
            if not good:
                failures.append({'seconds_after_on': time.monotonic() - on, 'nss': r})
                note('PEER_RECOVERY_FAILURE', failures[-1])
                tcp_check()
                neighbor()
                stable_start = None
                if len(failures) == 1:
                    fault_arp_diagnostic()
            else:
                if stable_start is None:
                    stable_start = time.monotonic()
                successes += 1
                if successes >= 5 and time.monotonic() - stable_start >= 30:
                    recovered = True
                    break
            wait_observed(5)
        assert recovered, 'peer recovery or stability window failed'
        note('recovery_summary', {'first_active_seconds': first_active - on, 'peer_failures': failures, 'successful_checks': successes, 'stable_seconds': time.monotonic() - stable_start})
        if failures or outage_failures:
            raise RuntimeError('original outage/recovery failures retained; later success is not a clean pass')
        assert first_active - on <= 40, 'local recovery exceeded original 40-second bound'
        note('CASE_PASS', {'scope': 'bounded B2/D2 repeat', 'boot_id': boot})
    except BaseException as e:
        error = e
        note('CASE_FAILURE', {'type': type(e).__name__, 'message': str(e)})
    finally:
        monitor_stop.set()
        if monitor:
            monitor.join(timeout=7)
        try:
            if a.trace and not monitor_faults:
                trace_pages()
            if off:
                snapshot()
                note('cleanup_on_begin', {})
                console('WIFI ON')
                off = False
            wait_observed(6)
            v = snapshot()
            neighbor()
            assert v['network']['enabled'] and v['network']['mdns_state'] == 'active' and (v['network']['ipv4'] == IP), 'cleanup network not recovered'
            r = nss('cleanup')
            assert r['exit'] == 0 and {l.split()[0] for l in r['stdout'].splitlines()} == {IP}, 'cleanup NSS failed'
            https()
            note('CLEANUP_VERIFIED', {'boot_id': boot, 'network': v['network'], 'peer_recovered': recovered})
        finally:
            for proc, stream in [(capture, locals().get('capture_log')), (diag, locals().get('diag_log'))]:
                if proc:
                    note('capture_stop', stop_process(proc))
                if stream:
                    stream.close()
            close_usb()
            wire.close()
            raw_wire.close()
            log.close()
    if error:
        raise error
    print('B2_D2_PASS ' + str(root), flush=True)
if __name__ == '__main__':
    main()
