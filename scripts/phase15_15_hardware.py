#!/usr/bin/env python3
"""Finite, identity-bound P15.15 physical acceptance; Linux --run is explicit."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import struct
import termios
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from phase14.live import Rig, CAPTURE, save
from phase14.plan import BOARDS, validate_capture
from led_closeout.device import Peer
from phase11_5_inventory import exclusive_port
from led_closeout.runner import require, sha256

PIC = '/home/pi/phase11-4-e1/picotool-build/picotool'
CLIENT = '/home/pi/p15-gpio-drive-20261017/pi/src/build/wtp-network/wtp_usb_pair_client'
RATE = 250000
FREQUENCIES = (137600, 14097100)
CURSOR = (0x3fd000, 0x3ff000)


def reset_cdc(fd):
    """Match production's idle DTR-low quiet interval and queue discard."""
    bit = struct.pack('I', termios.TIOCM_DTR)
    fcntl.ioctl(fd, termios.TIOCMBIC, bit)
    termios.tcflush(fd, termios.TCIOFLUSH)
    time.sleep(.1)
    termios.tcflush(fd, termios.TCIOFLUSH)
    fcntl.ioctl(fd, termios.TIOCMBIS, bit)


def usb_identity(board):
    matches = []
    for p in Path('/sys/bus/usb/devices').glob('*'):
        try:
            if (p / 'serial').read_text().strip() == BOARDS[board][0]:
                matches.append(dict(path=str(p.resolve()), devnum=(p / 'devnum').read_text().strip(),
                                    interfaces=sorted(q.name for q in p.glob('*:1.*'))))
        except FileNotFoundError:
            pass
    require(len(matches) <= 1, 'ambiguous USB serial')
    return matches[0] if matches else None


def session_probe(board, old=None):
    """A real framed hello, plus a previous-boot token rejection when supplied."""
    with exclusive_port(Path('/dev/serial/by-id/usb-WsprryPi_WsprryPico_' +
                             BOARDS[board][0] + '-if04')) as fd:
        def exchange(value):
            payload = json.dumps(value, separators=(',', ':')).encode()
            pending = b'UMP1' + len(payload).to_bytes(4, 'big') + payload
            incoming = bytearray()
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if pending:
                    if select.select([], [fd], [], .02)[1]:
                        try:
                            pending = pending[os.write(fd, pending):]
                        except BlockingIOError:
                            pass
                if select.select([fd], [], [], .02)[0]:
                    try:
                        incoming.extend(os.read(fd, 65536))
                    except BlockingIOError:
                        pass
                    if len(incoming) >= 8:
                        require(incoming[:4] == b'UMP1', 'probe framing')
                        size = int.from_bytes(incoming[4:8], 'big')
                        require(0 < size <= 65536, 'probe response bound')
                        if len(incoming) == size + 8:
                            return json.loads(incoming[8:])
            return None
        hello = exchange(dict(schema='usb-management/1', id=1, operation='hello'))
        require(hello and hello['status'] == 200 and not hello['delivery_required'], 'physical session probe hello')
        if old:
            require(hello['session'] != old['session'] and hello['target']['boot_id'] != old['target']['boot_id'],
                    'restart reused boot/session')
            rejected = exchange(dict(schema='usb-management/1', id=2, operation='request',
                session=old['session'], target=old['target'], method='GET', path='/api/v1/gpio-drive',
                body='', if_match=''))
            require(rejected is None or rejected['status'] >= 400, 'previous-boot session accepted')
            return dict(old=old, new=hello, rejected_response=rejected,
                        silent_refusal=rejected is None)
        return hello


class Management:
    def __init__(self, rig, board):
        self.rig, self.board = rig, board
        self.errors = open(rig.e.root / 'native-client.log', 'a')
        self.process = subprocess.Popen([CLIENT, '--usb', rig.device.base(board) + '-if02',
                                         BOARDS[board][0], BOARDS[board][1]],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.errors, text=True, bufsize=1)

    def command(self, value):
        p = self.process
        p.stdin.write(json.dumps(value, separators=(',', ':')) + '\n')
        p.stdin.flush()
        require(select.select([p.stdout], [], [], 16)[0], 'management response deadline')
        line = p.stdout.readline()
        require(bool(line), 'management client closed')
        result = json.loads(line)
        require('failure' not in result, 'management failure: ' + str(result.get('failure')))
        return result

    def api(self, resource, method='GET', body=None, revision=''):
        result = self.command(dict(raw_resource='/api/v1/' + resource, method=method,
                                   body='' if body is None else json.dumps(body, separators=(',', ':')),
                                   revision=revision))
        self.rig.e.event('management', dict(board=self.board, resource=resource, method=method,
                                           response=result))
        require(result['status'] in (200, 202), 'management ' + resource + ': ' + str(result))
        return result

    def close(self):
        if self.process:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=3)
            self.process.stdout.close()
            self.process = None
            self.errors.close()


class Campaign:
    def __init__(self, args):
        self.args = args
        self.rig = Rig(args.output, ROOT)
        self.original = {}
        self.in_rom = set()
        self.managed = None
        self.records = []
        self.restarts = []
        self.preparations = []
        self.armed = 0
        self.rf_budget = 0
        self.captures = 0
        self.original_service = False
        self.stopped_service = False
        self.current_image = {}
        self.claim = None
        if args.resume_from:
            previous = json.loads((args.resume_from / 'result.json').read_text())
            require(not any('restoration' in error or 'cleanup' in error for error in previous['errors']) and
                    set(previous['restored']) == {'A', 'B'}, 'previous cleanup must be verified')
            self.armed = previous['armed_jobs']
            self.rf_budget = previous['rf_budget_seconds']
            self.captures = previous['captures']
            for record in json.loads((args.resume_from / 'records.json').read_text()):
                expected_image = args.baseline if record['label'].startswith('baseline-') else args.candidate
                require(record['result'] == 'CONTROL_COMPLETE' and
                        record['image_sha256'] == sha256(expected_image), 'only exact completed cells may be reused')
                original = args.resume_from / record['label']
                require(json.loads((original / 'physical.json').read_text()) ==
                        {k:v for k,v in record.items() if k != 'label'}, 'retained control record integrity')
                if 'capture_sha256' in record:
                    require(sha256(original / 'capture.cf32') == record['capture_sha256'] and
                            sha256(original / 'capture.json') == record['metadata_sha256'], 'retained capture integrity')
                (self.rig.e.root / record['label']).symlink_to(original.resolve(), target_is_directory=True)
                self.records.append(record)
            for name in ('preparations', 'restarts'):
                path = args.resume_from / (name + '.json')
                if path.exists():
                    setattr(self, name, json.loads(path.read_text()))
                    save(self.rig.e.root / path.name, getattr(self, name))
            save(self.rig.e.root / 'resumed-cells.json', dict(root=str(args.resume_from), records=self.records,
                                                              budget=previous))

    def idle(self, board):
        info = self.rig.idle(board)
        require(info['system_clock_hz'] == 138000000, 'normal clock changed')
        return info

    def wait(self, board, old_boot=None, seconds=70):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                info = self.idle(board)
                if old_boot is None or info['status']['boot_id'] != old_boot:
                    return info
            except (OSError, TimeoutError, ValueError):
                pass
            time.sleep(.2)
        raise TimeoutError('fresh idle Console unavailable')

    def rom(self, board):
        self.close_management()
        self.rig.device.rom(board)
        self.in_rom.add(board)

    def pt(self, board, *args):
        result = subprocess.run([PIC, *map(str, args), '--ser', BOARDS[board][0]],
                                capture_output=True, text=True, timeout=100)
        self.rig.e.event('picotool', dict(board=board, args=list(map(str, args)),
                                         returncode=result.returncode,
                                         stdout=result.stdout, stderr=result.stderr))
        require(result.returncode == 0, 'picotool failed: ' + result.stderr[-1000:])

    def flash(self, board, image):
        self.rom(board)
        self.pt(board, 'load', '-v', image)
        self.pt(board, 'reboot')
        self.in_rom.discard(board)
        info = self.wait(board)
        self.rig.device.console(board, 'ABORT')
        self.current_image[board] = sha256(image)
        self.rig.e.event('deployment', dict(board=board, image_sha256=sha256(image), info=info))

    def connect(self, board):
        self.close_management()
        self.managed = Management(self.rig, board)
        return self.managed

    def close_management(self):
        if self.managed:
            self.managed.close()
            self.managed = None

    def restart(self, board):
        before = self.idle(board)
        self.close_management()
        old_session = session_probe(board)
        identity = usb_identity(board)
        observations = []
        stop = threading.Event()

        def watch():
            prior = object()
            while not stop.is_set():
                current = usb_identity(board)
                if current != prior:
                    observations.append(dict(monotonic_ns=time.monotonic_ns(), usb=current))
                    prior = current
                stop.wait(.01)

        thread = threading.Thread(target=watch)
        thread.start()
        try:
            api = self.managed or self.connect(board)
            view = api.api('gpio-drive')
            response = api.api('restart', 'POST', {}, view['etag'])
            require(response['status'] == 202, 'explicit deferred restart refused')
            self.close_management()
            after = self.wait(board, before['status']['boot_id'])
            require(not after['status']['output_active'], 'output active after restart')
        finally:
            stop.set()
            thread.join(timeout=2)
        current = usb_identity(board)
        require(identity and current and current['path'] == identity['path'] and
                current['devnum'] != identity['devnum'] and
                any(x['usb'] is None for x in observations), 'physical USB removal/addition absent')
        require(len(current['interfaces']) == 6 and
                all(Path(self.rig.device.base(board) + '-if' + role).exists()
                    for role in ('00', '02', '04')), 'three CDC roles not rediscovered')
        stale = session_probe(board, old_session)
        api = self.connect(board)
        value = api.api('gpio-drive')
        require(value['body']['target']['boot_id'] == after['status']['boot_id'], 'new USB session boot')
        record = dict(board=board, before_boot=before['status']['boot_id'],
                      after_boot=after['status']['boot_id'], before_usb=identity, after_usb=current,
                      observations=observations, stale_session=stale, readback=value)
        self.restarts.append(record)
        save(self.rig.e.root / 'restarts.json', self.restarts)
        return value

    def drive(self, board, ma, sticky=False):
        api = self.connect(board)
        view = api.api('gpio-drive')
        boot = view['body']['boot_active']
        choices = [ma]
        if sticky:
            choices = [2 if boot != 2 else 8, boot, ma]
        for selected in choices:
            old = api.api('gpio-drive')
            saved = api.api('gpio-drive', 'PUT', dict(schema='transmitter-gpio-drive/1',
                            target=old['body']['target'], gpio_drive_ma=selected), old['etag'])
            require(saved['body']['saved'] == selected and saved['body']['boot_active'] == boot,
                    'save hot-applied drive or lost value')
            if selected != boot or sticky:
                require(saved['body']['pending_restart'], 'sticky restart not retained')
        readback = self.restart(board)
        require(readback['body']['saved'] == ma and readback['body']['boot_active'] == ma and
                not readback['body']['pending_restart'] and readback['body']['application_error'] is None,
                'drive persistence/activation failed')
        return readback

    @contextlib.contextmanager
    def peer(self, board):
        self.idle(board)
        with exclusive_port(Path(self.rig.device.base(board) + '-if02')) as fd:
            reset_cdc(fd)
            peer = Peer(fd, self.rig.e, ROOT, timeout=10)
            hello = peer.request('HELLO', dict(versions=['WTP/1'], client_name='P15.15', client_version='1'))
            require(hello['device_id'] == BOARDS[board][1], 'USB WTP identity')
            yield peer

    def prepare(self, board, ma):
        clock_deadline = time.monotonic() + 150
        while True:
            info = self.idle(board)
            if info['status']['clock_state'] == 'synchronized' and int(info['status']['uncertainty_ns']) <= 500000000:
                break
            require(time.monotonic() < clock_deadline, 'clock readiness for inactive pad probe')
            time.sleep(1)
        api = self.connect(board)
        initial = api.api('gpio-drive')['body']
        require(initial['pad_readback'] is None and initial['rf_gp'] == 2,
                'fresh-boot unknown observation or selected GPIO mismatch')
        self.close_management()
        with self.peer(board) as peer:
            owner = uuid.uuid4().hex
            peer.request('CLAIM', dict(owner_id=owner, lease_ms=30000))
            self.claim = (board, owner)
            value = self.job(FREQUENCIES[1], 1)
            peer.request('LOAD', value, timeout=30)
            try:
                loaded = peer.request('STATUS', {})
                require(loaded['state'] == 'loaded' and not loaded['output_active'], 'LOAD energized output')
                clock = peer.request('GET_CLOCK', {})
                start = (int(clock['utc_now_ns']) // 1000000000 + 15) * 1000000000
                require(self.armed < 36 and self.rf_budget + 1 <= 180, 'inactive probe budget')
                self.armed += 1
                self.rf_budget += 1
                arm = peer.request('ARM', dict(job_id=value['job_id'], start_utc_ns=str(start),
                                              max_start_uncertainty_ns='500000000'))
                observed = self.connect(board).api('gpio-drive')['body']
                require(observed['pad_readback'] == ma and observed['boot_active'] == ma and
                        observed['rf_gp'] == 2 and
                        observed['target']['boot_id'] == peer.boot and
                        observed['application_error'] is None, 'actual SDK getter readback failed')
                rejected = self.managed.command(dict(raw_resource='/api/v1/gpio-drive', method='PUT',
                    body=json.dumps(dict(schema='transmitter-gpio-drive/1', target=observed['target'],
                                         gpio_drive_ma=4 if ma != 4 else 8)),
                    revision=self.managed.api('gpio-drive')['etag']))
                require(rejected['status'] == 409, 'busy drive mutation accepted')
                inactive = peer.request('STATUS', {})
                require(inactive['state'] == 'armed' and not inactive['output_active'],
                        'inactive pad probe reached launch; abort immediately')
                self.preparations.append(dict(board=board, ma=ma, before=initial, loaded=loaded,
                                              arm=arm, inactive=inactive, observed=observed, busy_refusal=rejected))
                save(self.rig.e.root / 'preparations.json', self.preparations)
            finally:
                self.close_management()
                peer.request('ABORT', dict(job_id=value['job_id']))
                peer.request('RELEASE', {})
                self.claim = None
        self.idle(board)

    @staticmethod
    def job(frequency, seconds):
        return dict(job_id=uuid.uuid4().hex, profile='rf-events/1', mode='tone',
                    total_duration_ns=str(seconds * 1000000000), allow_frequency_adjustment=True,
                    events=[dict(offset_ns='0', duration_ns=str(seconds * 1000000000),
                                 rf_on=True, frequency_nhz=str(frequency * 1000000000))])

    def run_job(self, board, ma, frequency, label, action='complete', capture=True):
        seconds = 5 if action == 'complete' else 2
        require(self.armed < 36 and self.rf_budget + seconds <= 180 and self.captures < 30,
                'frozen campaign budget exhausted')
        self.close_management()
        before = self.idle(board)
        self.idle('B' if board == 'A' else 'A')
        clock_deadline = time.monotonic() + 150
        while before['status']['clock_state'] != 'synchronized' or int(before['status']['uncertainty_ns']) > 500000000:
            require(time.monotonic() < clock_deadline, 'bounded clock readiness unavailable')
            time.sleep(1)
            before = self.idle(board)
        directory = self.rig.e.root / label
        directory.mkdir(mode=0o700)
        record = dict(board=board, ma=ma, frequency_hz=frequency, action=action,
                      image_sha256=self.current_image[board], before=before,
                      helper_sha256=sha256(CAPTURE), requested_duration_s=seconds, status=[])
        settings = dict(format='CF32', sample_rate_hz=RATE, bandwidth_hz=200000,
                        center_frequency_hz=frequency - 25000, gain_db=20, channel=0,
                        agc=False, bias_tee=False)
        record['receiver_settings'] = settings
        process = None
        log = open(directory / 'capture.log', 'x')
        job = self.job(frequency, seconds)
        record['job'] = job
        try:
            with self.peer(board) as peer:
                owner = uuid.uuid4().hex
                peer.request('CLAIM', dict(owner_id=owner, lease_ms=30000))
                self.claim = (board, owner)
                record['load'] = peer.request('LOAD', job, timeout=30)
                if capture:
                    import shutil
                    require(shutil.disk_usage(directory).free > 2 * 1024**3 + 20 * RATE * 8, 'storage reserve')
                    argv = [CAPTURE, '--enable-physical-sdr', 'sdrplay', '2404058C60',
                            str(frequency - 25000), str(20 * RATE), '20', str(RATE), '200000',
                            '0', 'false', 'false', '100000', '55', str(directory / 'capture.cf32'),
                            str(directory / 'capture.json'), label]
                    record['receiver_command'] = argv
                    process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                    self.captures += 1
                    deadline = time.monotonic() + 10
                    while not (directory / 'capture.cf32.incomplete').exists() or (directory / 'capture.cf32.incomplete').stat().st_size < 65536:
                        require(process.poll() is None and time.monotonic() < deadline, 'receiver readiness')
                        time.sleep(.05)
                    time.sleep(1)
                clock = peer.request('GET_CLOCK', {})
                require(clock['state'] == 'synchronized' and int(clock['uncertainty_ns']) <= 500000000,
                        'clock outside unchanged ARM admission')
                start = (int(clock['utc_now_ns']) // 1000000000 + 3) * 1000000000
                # Reserve before delivery: an uncertain ARM consumes its full
                # possible RF window and must never create free retry budget.
                self.armed += 1
                self.rf_budget += seconds
                record['arm'] = peer.request('ARM', dict(job_id=job['job_id'], start_utc_ns=str(start),
                                                        max_start_uncertainty_ns='500000000'))
                self.rig.e.event('armed', dict(label=label, armed=self.armed, budget_s=self.rf_budget))
                deadline = time.monotonic() + seconds + 12
                acted = False
                while True:
                    status = peer.request('STATUS', {})
                    record['status'].append(dict(monotonic_ns=time.monotonic_ns(), status=status))
                    if action == 'cancel' and status['state'] == 'armed' and not acted:
                        record['abort'] = peer.request('ABORT', dict(job_id=job['job_id']))
                        acted = True
                    if action == 'abort' and status['state'] == 'running' and not acted:
                        time.sleep(.3)
                        record['abort'] = peer.request('ABORT', dict(job_id=job['job_id']))
                        acted = True
                    if status['state'] in ('complete', 'aborted', 'failed', 'missed'):
                        require(status['state'] == ('complete' if action == 'complete' else 'aborted') and
                                not status['output_active'], 'job lifecycle failed')
                        break
                    require(time.monotonic() < deadline, 'finite job completion deadline')
                    time.sleep(.05)
                peer.request('RELEASE', {})
                self.claim = None
            if process:
                require(process.wait(timeout=45) == 0, 'capture helper failed')
                metadata = json.loads((directory / 'capture.json').read_text())
                validate_capture(metadata, directory / 'capture.cf32', settings)
                record['capture_sha256'] = sha256(directory / 'capture.cf32')
                record['metadata_sha256'] = sha256(directory / 'capture.json')
            record['after'] = self.idle(board)
            for field in ('dma_errors', 'refill_invalid_reserves', 'core1_stack_fault_status'):
                require(record['after'][field] == 0, 'target diagnostic failure: ' + field)
            require(record['after']['core1_stack_guard_valid'], 'RF worker stack guard invalid')
            require(any(x['status']['state'] == 'running' for x in record['status'])
                    if action != 'cancel' else not any(x['status']['output_active'] for x in record['status']),
                    'lifecycle running/cancel observation missing')
            if label.startswith(('candidate', 'bracket', 'lifecycle')):
                observed = self.connect(board).api('gpio-drive')['body']
                require(observed['pad_readback'] == ma and observed['application_error'] is None,
                        'pad readback changed across job')
                record['pad_after'] = observed
            record['result'] = 'CONTROL_COMPLETE'
            self.records.append(dict(label=label, **record))
        except BaseException as error:
            record['error'] = repr(error)
            raise
        finally:
            if process and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=8)
            log.close()
            save(directory / 'physical.json', record)
            save(self.rig.e.root / 'records.json', self.records)

    def snapshot(self, board):
        before = self.idle(board)
        self.rom(board)
        path = self.rig.e.root / (board + '-original.bin')
        verify = self.rig.e.root / (board + '-original-verify.bin')
        self.pt(board, 'save', '-r', '0x10000000', '0x10400000', '-v', path, '-t', 'bin')
        self.pt(board, 'save', '-r', '0x10000000', '0x10400000', '-v', verify, '-t', 'bin')
        require(path.stat().st_size == 4194304 and sha256(path) == sha256(verify), 'full flash snapshot mismatch')
        self.original[board] = dict(info=before, path=str(path), sha256=sha256(path))
        save(self.rig.e.root / 'originals.json', self.original)
        self.pt(board, 'reboot')
        self.in_rom.discard(board)
        self.wait(board, before['status']['boot_id'])

    def restore(self, board):
        original = self.original[board]
        if board not in self.in_rom:
            self.idle(board)
            self.rom(board)
        current = self.rig.e.root / (board + '-latest-cursor.bin')
        self.pt(board, 'save', '-r', hex(0x10000000 + CURSOR[0]), hex(0x10000000 + CURSOR[1]),
                '-v', current, '-t', 'bin')
        data = bytearray(Path(original['path']).read_bytes())
        require(sha256(original['path']) == original['sha256'], 'original backup changed')
        require(current.stat().st_size == CURSOR[1] - CURSOR[0], 'cursor preservation size')
        data[CURSOR[0]:CURSOR[1]] = current.read_bytes()
        target = self.rig.e.root / (board + '-restoration.bin')
        target.write_bytes(data)
        self.pt(board, 'load', '-v', target, '-t', 'bin', '-o', '0x10000000')
        verify = self.rig.e.root / (board + '-restored-verify.bin')
        self.pt(board, 'save', '-r', '0x10000000', '0x10400000', '-v', verify, '-t', 'bin')
        require(sha256(target) == sha256(verify), 'restored flash verification failed')
        self.pt(board, 'reboot')
        self.in_rom.discard(board)
        after = self.wait(board)
        self.rig.device.console(board, 'ABORT')
        after = self.idle(board)
        require(after['revision'] == original['info']['revision'] and
                int(after['status']['watermark_utc_ns']) >= int(original['info']['status']['watermark_utc_ns']),
                'original firmware/cursor not restored')
        result = dict(restored_sha256=sha256(verify), original_sha256=original['sha256'],
                      latest_cursor_sha256=sha256(current), unchanged_except_cursor=True, after=after)
        save(self.rig.e.root / (board + '-restored.json'), result)
        return result

    def execute(self):
        result = dict(status='RUNNING', errors=[], restored={})
        try:
            self.original_service = subprocess.run(['systemctl', 'is-active', '--quiet', 'wsprrypi']).returncode == 0
            if self.original_service:
                subprocess.run(['systemctl', 'stop', 'wsprrypi'], check=True, timeout=30)
                self.stopped_service = True
            from phase14_reference import gps
            reference = gps()
            require(not reference['out1'] and not reference['out2'], 'another conducted reference is active')
            save(self.rig.e.root / 'entry.json', dict(reference=reference, service_active=self.original_service,
                helpers={p: sha256(p) for p in (PIC, CLIENT, CAPTURE)},
                images={str(p): sha256(p) for p in (self.args.candidate, self.args.baseline)},
                plan=dict(strengths=[4, 2, 8, 12], frequencies=list(FREQUENCIES),
                          tone_captures=18, inactive_pad_probes=8, cancel_jobs=4, abort_jobs=4,
                          max_armed=36, max_rf_seconds=180)))
            for board in ('A', 'B'):
                self.snapshot(board)
            for board in ('A', 'B'):
                frequencies = FREQUENCIES if board == 'A' else (FREQUENCIES[1],)
                done = {record['label'] for record in self.records}
                if any('baseline-' + board + '-' + str(f) not in done for f in frequencies):
                    self.flash(board, self.args.baseline)
                    for frequency in frequencies:
                        label = 'baseline-' + board + '-' + str(frequency)
                        if label in done:
                            continue
                        self.run_job(board, 4, frequency, label)
                self.flash(board, self.args.candidate)
                for ma in (4, 2, 8, 12):
                    labels = ['candidate-' + board + '-' + str(ma) + '-' + str(f) for f in frequencies]
                    if board == 'A':
                        labels += ['lifecycle-' + a + '-' + str(ma) for a in ('cancel','abort')]
                    if all(label in done for label in labels):
                        continue
                    self.drive(board, ma, sticky=ma == 4)
                    if not any(p['board'] == board and p['ma'] == ma for p in self.preparations):
                        self.prepare(board, ma)
                    for frequency in frequencies:
                        label = 'candidate-' + board + '-' + str(ma) + '-' + str(frequency)
                        if label not in done:
                            self.run_job(board, ma, frequency, label)
                    if board == 'A':
                        for action in ('cancel', 'abort'):
                            label = 'lifecycle-' + action + '-' + str(ma)
                            if label not in done:
                                self.run_job(board, ma, FREQUENCIES[1], label, action, False)
                self.drive(board, 4)
                for frequency in frequencies:
                    label = 'bracket-' + board + '-' + str(frequency)
                    if label not in done:
                        self.run_job(board, 4, frequency, label)
            require(gps() == reference, 'reference state changed')
            result['status'] = 'ACQUISITION_COMPLETE'
        except BaseException as error:
            result['status'] = 'FAILED'
            result['errors'].append(repr(error))
        finally:
            self.close_management()
            if self.claim:
                board, owner = self.claim
                try:
                    current = self.rig.info(board)['status']
                    require(current['owner_id'] in (None, owner), 'another owner replaced test claim')
                    if current['owner_id'] == owner:
                        self.rig.device.console(board, 'ABORT')
                    self.claim = None
                except BaseException as error:
                    result['errors'].append('owned cleanup: ' + repr(error))
            for board in ('A', 'B'):
                if board in self.original:
                    try:
                        result['restored'][board] = self.restore(board)
                    except BaseException as error:
                        result['errors'].append(board + ' restoration: ' + repr(error))
                elif board in self.in_rom:
                    # Snapshot failure occurs before any flash write. Return
                    # the unchanged image from ROM even without a valid backup.
                    try:
                        self.pt(board, 'reboot')
                        self.in_rom.discard(board)
                        self.wait(board)
                    except BaseException as error:
                        result['errors'].append(board + ' unchanged-image reboot: ' + repr(error))
            if self.stopped_service:
                try:
                    subprocess.run(['systemctl', 'start', 'wsprrypi'], check=True, timeout=30)
                    require(subprocess.run(['systemctl', 'is-active', '--quiet', 'wsprrypi']).returncode == 0,
                            'service restoration failed')
                except BaseException as error:
                    result['errors'].append('service restoration: ' + repr(error))
            result.update(armed_jobs=self.armed, rf_budget_seconds=self.rf_budget,
                          captures=self.captures, preparations=len(self.preparations), restarts=len(self.restarts))
            if result['errors']:
                result['status'] = 'FAILED'
            save(self.rig.e.root / 'result.json', result)
            self.rig.close()
        print(json.dumps(dict(status=result['status'], errors=result['errors'], armed_jobs=self.armed,
                              captures=self.captures, restored=list(result['restored'])), indent=2))
        return result['status'] == 'ACQUISITION_COMPLETE'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--resume-from', type=Path)
    args = parser.parse_args()
    require(args.run and sys.platform.startswith('linux') and os.geteuid() == 0,
            'explicit Linux exclusive-owner execution required')
    os.umask(0o077)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda number, frame: (_ for _ in ()).throw(InterruptedError(str(number))))
    return 0 if Campaign(args).execute() else 1


if __name__ == '__main__':
    raise SystemExit(main())
