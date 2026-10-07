"""Linux/wspr5 physical adapter. Every ROM operation selects the named USB serial."""
import contextlib
import fcntl
import json
import os
from pathlib import Path
import struct
import socket
import ipaddress
import subprocess
import time
import uuid

from led_closeout.capture import Captures
from led_closeout.plan import BOARDS, IMAGES, RECEIVER
from led_closeout.runner import admit, quiescent, require, save_json, sha256
from phase11_5_inventory import exclusive_port, exchange
from check_standalone_image import validate_uf2
from validate_wtp_contract import frame, SchemaValidator

FLASH_SIZE, RESERVED, E10 = 4194304, 0x3f3000, 0x3ff000


def tool(argv, timeout=45):
    result = subprocess.run(argv, capture_output=True, timeout=timeout)
    require(result.returncode == 0, 'tool failed: ' + str(argv[0]))
    return result.stdout.decode(errors='strict')


def validate_setup(setup, *, recovery=False):
    require(setup['schema'] == 'phase13.1-led-setup/1' and setup['receiver_serial'] == RECEIVER,
            'setup/receiver identity')
    for name in (('picotool',) if recovery else ('capture_helper', 'ffmpeg', 'picotool')):
        item = setup[name]
        require(Path(item['path']).is_absolute() and sha256(item['path']) == item['sha256'],
                'setup executable hash: ' + name)
    if recovery:
        return
    cam = setup['camera']
    require(cam['device'].startswith('/dev/video') and Path(cam['device']).exists() and
            type(cam['fps']) is int and 30 <= cam['fps'] <= 120 and
            all(type(cam[k]) is int and 320 <= cam[k] <= 4096 for k in ('width', 'height')),
            'prepared camera configuration')
    for name in ('onboard', 'external_high', 'external_low'):
        roi = cam['rois'][name]
        require(len(roi) == 4 and all(type(v) is int and v >= 0 for v in roi) and
                roi[2] > 0 and roi[3] > 0 and roi[0]+roi[2] <= cam['width'] and
                roi[1]+roi[3] <= cam['height'], 'prepared camera ROI: ' + name)
    require(setup['fixtures'] == {'external_high_gp': 15, 'external_low_gp': 16,
                                 'stimulus_gp': 15, 'dut_stop_gp': 14, 'open_drain': True},
            'prepared fixture roles')
    require(isinstance(setup['rf_path'], str) and 1 <= len(setup['rf_path']) <= 512,
            'physical path description')


def validate_manifest(manifest, root):
    require(manifest['schema'] == 'phase13.1-led-candidates/2' and manifest['clean'] is True and
            len(manifest['source_commit']) == 40 and set(manifest['images']) == set(IMAGES) and
            manifest['board'] == 'pico2_w' and manifest['sample_rate_hz'] == 138000000 and
            manifest['sdk_commit'] == '079c6f39023649b154152db30f1d781e884879bc' and
            manifest['picotool_commit'] == '6f6458d792b93685a11423b244a585eaa99eafcf',
            'clean candidate manifest')
    commit = tool(['git', '-C', str(root), 'rev-parse', 'HEAD']).strip()
    require(commit == manifest['source_commit'] and
            not tool(['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=normal']),
            'source checkout differs from candidate')
    for key, image in manifest['images'].items():
        rf, acceptance, selection, gp14 = IMAGES[key]
        require(image['acceptance'] is acceptance and image['selection'] == selection and
                image['gp14'] is gp14 and image['engine'] ==
                ('pio-dma-gp2' if rf else 'inhibited-standalone-simulator') and
                image['revision'] == commit[:12], 'candidate role: ' + key)
        require(sha256(image['uf2']) == image['uf2_sha256'] and
                sha256(image['elf']) == image['elf_sha256'], 'candidate hash: ' + key)
        validate_uf2(Path(image['uf2']).read_bytes())
        pins = image['pins']
        require(pins['engine'] == 'direct' and pins['rf_gp'] == 2 and pins['button_gp'] == 14 and
                pins['i2c_pair'] is None and pins['amplifier_gp'] is None and pins['lpf_gps'] == [],
                'candidate pin roles')
        expected = ('onboard_led', 'external', 'external', 'disabled')[selection]
        require(pins['indicator'] == expected and pins['indicator_gp'] ==
                (15 if selection == 1 else 16 if selection == 2 else None) and
                pins['indicator_active_high'] is (selection != 2), 'candidate indicator')


def snapshot_config(data):
    """Decode the actual Store journal, with its CRC and no torn-record rollback."""
    import zlib
    from phase11_5_inventory import loads_console
    require(len(data) == FLASH_SIZE, 'snapshot flash size')
    sequence, config = 0, None
    seen = set()
    for offset in range(0x3fb000, 0x3fd000, 2048):
        record = data[offset:offset+2048]
        if record == b'\xff'*2048:
            continue
        magic, seq, size = struct.unpack_from('<QQI', record)
        require(magic == 0x32524f5453505757 and seq > 0 and size <= 1984 and
                zlib.crc32(record[:-4]) == struct.unpack_from('<I', record, 2044)[0] and
                seq not in seen, 'invalid/torn standalone config journal')
        seen.add(seq)
        if seq > sequence:
            sequence, config = seq, loads_console(record[32:32+size].decode())
    require(config and config['version'] == 1 and config['enabled'] is False,
            'disabled retained standalone configuration required')
    from led_closeout.candidates import pins
    require(config.get('pins', pins(0)) == pins(0), 'retained pins conflict with LED fixture')
    return config


class Peer:
    def __init__(self, fd, evidence, root):
        self.fd, self.e, self.session = fd, evidence, uuid.uuid4().hex
        self.schema = json.loads((Path(root)/'docs/protocol/wtp-1.schema.json').read_text())
        self.validator = SchemaValidator(self.schema)

    def request(self, op, body):
        request = dict(type='request', protocol='WTP/1', session_id=self.session,
                       request_id=uuid.uuid4().hex, op=op, body=body)
        response = exchange(self.fd, frame(json.dumps(request, separators=(',', ':')).encode()),
                            time.monotonic()+3, self.e.event, True, expected=request)
        require(not self.validator.errors(response, self.schema), 'WTP response schema')
        require(response.get('ok') is True, 'WTP ' + op + ' rejected')
        require(response.get('protocol') == 'WTP/1', 'WTP version')
        return response['body']


class Device:
    def __init__(self, setup, evidence, root):
        self.setup, self.e, self.root = setup, evidence, Path(root)
        self.stack = contextlib.ExitStack()
        self.snapshots, self.peers, self.peer_contexts = {}, {}, {}
        self.dut = None
        self.capture = Captures(setup, evidence)
        self.snapshot_path = evidence.root/'snapshots.json'

    @staticmethod
    def now(): return time.monotonic()
    @staticmethod
    def sleep(seconds): time.sleep(seconds)

    def base(self, board):
        return '/dev/serial/by-id/usb-WsprryPi_WsprryPico_' + BOARDS[board]['serial']

    def console(self, board, command):
        with exclusive_port(Path(self.base(board)+'-if00')) as fd:
            result = exchange(fd, (command+'\n').encode(), self.now()+3, self.e.event, False)
        require(result.get('ok') is True, 'Console command rejected: ' + command.split()[0])
        return result

    def peer(self, board):
        if board not in self.peers:
            info = self.console(board, 'INFO')
            require(info['device_id'] == BOARDS[board]['device_id'], 'transport Console identity')
            if info.get('provisioning_source') == 'consumer_preclock':
                require(info['lan_wtp_mode'] == 'plain' and
                        type(info['lan_wtp_port']) is int and 1 <= info['lan_wtp_port'] <= 65535,
                        'consumer image needs its ordinary Plain LAN WTP listener')
                address = str(ipaddress.IPv4Address(info['network']['ipv4']))
                require(address != '0.0.0.0', 'consumer station address unavailable')
                connection = socket.create_connection((address, info['lan_wtp_port']), timeout=3)
                connection.setblocking(False)
                context = contextlib.closing(connection)
                context.__enter__()
                fd = connection.fileno()
                self.e.event('transport', dict(board=board, kind='plain-lan', address=address,
                                               port=info['lan_wtp_port']))
            else:
                context = exclusive_port(Path(self.base(board)+'-if02'))
                fd = context.__enter__()
                self.e.event('transport', dict(board=board, kind='usb-cdc'))
            self.peer_contexts[board] = context
            self.peers[board] = Peer(fd, self.e, self.root)
            hello = self.peers[board].request('HELLO', dict(versions=['WTP/1'],
                client_name='LED-closeout', client_version='1'))
            require(hello['device_id'] == BOARDS[board]['device_id'], 'WTP device identity')
        return self.peers[board]

    def close_peer(self, board):
        self.peers.pop(board, None)
        context = self.peer_contexts.pop(board, None)
        if context:
            context.__exit__(None, None, None)

    def info(self, board):
        for _ in range(3):
            value = self.console(board, 'INFO')
            if all(k in value['status'] for k in ('owner_id', 'job_id')):
                return value # Cleanup remains available when LAN/SNTP is unavailable.
            status = self.peer(board).request('STATUS', {})
            require(status['boot_id'] == value['status']['boot_id'], 'Console/WTP boot identity')
            if all(status[k] == value['status'][k] for k in ('state', 'output_active')):
                value['status'].update({k: status[k] for k in ('owner_id', 'job_id')})
                return value
            self.e.event('authority_transition', dict(info=value, status=status))
        raise ValueError('Console/WTP authority did not settle')

    def command(self, board, command):
        result = self.console(board, 'LED TEST '+BOARDS[board]['device_id']+' '+command)
        self.e.event('fixture_command', dict(board=board, command=command, result=result))
        return result

    def request(self, op, body): return self.peer(self.dut).request(op, body)
    def hello(self):
        return self.request('HELLO', dict(versions=['WTP/1'], client_name='LED-closeout', client_version='1'))

    def rom(self, board):
        self.close_peer(board)
        if Path(self.base(board)+'-if00').exists():
            info = self.console(board, 'INFO')
            s = info['status']
            require(info['device_id'] == BOARDS[board]['device_id'] and not s['output_active'] and
                    not s['enabled'], 'unsafe ROM transition')
            self.console(board, 'BOOTSEL')
            self.sleep(1)
        self.pt(board, ['info'])

    def pt(self, board, args):
        return tool([self.setup['picotool']['path']] + args + ['--ser', BOARDS[board]['serial']])

    def journal(self): save_json(self.snapshot_path, self.snapshots)

    def lock_boards(self, board, fixture):
        for key in filter(None, (board, fixture)):
            path = '/tmp/wsprrypico-led-' + BOARDS[key]['serial'] + '.lock'
            fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            self.stack.callback(os.close, fd)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def preflight(self, manifest, board, fixture):
        validate_setup(self.setup)
        validate_manifest(manifest, self.root)
        self.dut = board
        self.lock_boards(board, fixture)
        # Check BOTH entries before any board transitions to ROM.
        entries = {b: self.info(b) for b in filter(None, (board, fixture))}
        for b, info in entries.items():
            quiescent(info, BOARDS[b])
        for b, info in entries.items():
            # Persist identity/ROM intent before the first device mutation.
            backup = self.e.root/(b+'-entry.bin')
            self.snapshots[b] = dict(board=b, serial=BOARDS[b]['serial'], path=str(backup),
                sha256=None, entry_revision=info['revision'], state='SNAPSHOT_PENDING')
            self.journal()
            self.rom(b)
            self.pt(b, ['save', '-a', '-v', str(backup), '-t', 'bin'])
            os.chmod(backup, 0o600)
            require(backup.stat().st_size == FLASH_SIZE, 'entry full-flash size')
            retained = snapshot_config(backup.read_bytes())
            self.e.event('retained_config_checked', dict(board=b, pins=retained.get('pins'), enabled=False))
            self.snapshots[b].update(sha256=sha256(backup), state='SNAPSHOTTED')
            self.journal()
        if fixture:
            self.deploy(fixture, manifest['images']['stimulus'])
            quiescent(self.info(fixture), BOARDS[fixture], manifest['images']['stimulus'])

    def wait_info(self, board):
        deadline = self.now()+90
        while self.now() < deadline:
            try:
                return self.info(board)
            except (OSError, TimeoutError):
                self.close_peer(board)
                self.sleep(.3)
        raise TimeoutError('board boot/readiness deadline')

    def verify(self, board, image, readback, snapshot):
        data = readback.read_bytes()
        before = Path(snapshot['path']).read_bytes()
        require(len(data) == FLASH_SIZE and sha256(snapshot['path']) == snapshot['sha256'] and
                data[RESERVED:] == before[RESERVED:], 'journals/E10 restoration mismatch')
        uf2 = Path(image['uf2']).read_bytes()
        validate_uf2(uf2)
        for offset in range(0, len(uf2), 512):
            address, size = struct.unpack_from('<II', uf2, offset+12)
            if address == 0x10ffff00:
                continue
            require(0x10000000 <= address and address+size <= 0x10000000+RESERVED,
                    'image outside application region')
            require(data[address-0x10000000:address-0x10000000+size] == uf2[offset+32:offset+32+size],
                    'programmed image mismatch')

    def deploy(self, board, image):
        snapshot = self.snapshots[board]
        require(snapshot['sha256'] and sha256(snapshot['path']) == snapshot['sha256'] and
                sha256(image['uf2']) == image['uf2_sha256'], 'immutable deployment artifacts')
        self.rom(board)
        snapshot['state'] = 'DEPLOY_PENDING'
        self.journal()
        # Restore original journals before EVERY candidate, including enabled
        # schedule/one-shot watermark changes. Do not erase the SDK E10 block.
        reserved = self.e.root/(board+'-reserved.bin')
        reserved.write_bytes(Path(snapshot['path']).read_bytes()[RESERVED:E10])
        os.chmod(reserved, 0o600)
        self.pt(board, ['load', '-v', str(reserved), '-t', 'bin', '-o', hex(0x10000000+RESERVED)])
        self.pt(board, ['load', '-v', image['uf2']])
        readback = self.e.root/(board+'-'+uuid.uuid4().hex+'-readback.bin')
        self.pt(board, ['save', '-a', '-v', str(readback), '-t', 'bin'])
        os.chmod(readback, 0o600)
        self.verify(board, image, readback, snapshot)
        self.e.event('flash_verified', dict(board=board, image=image, sha256=sha256(readback)))
        self.pt(board, ['reboot'])
        info = self.wait_info(board)
        quiescent(info, BOARDS[board], image)
        require(info['status']['boot_id'] != snapshot.get('last_boot'), 'stale deployment boot')
        snapshot.update(state='DEPLOYED', last_boot=info['status']['boot_id'])
        self.journal()

    def abort(self, board):
        if board not in self.snapshots:
            return # Preflight refusal must not mutate someone else's active DUT.
        self.close_peer(board)
        if Path(self.base(board)+'-if00').exists():
            before = self.info(board)
            if before['status']['enabled'] and before.get('led_acceptance'):
                self.command(board, 'STOP')
                self.command(board, 'DISABLE')
            try:
                self.console(board, 'ABORT')
            except ValueError:
                # A latched Failed state refuses local ABORT. Lease expiry is
                # bounded and cannot be renewed by this stopped runner.
                pass
            end = self.now()+12
            while True:
                status = self.info(board)['status']
                if not status['output_active'] and status['owner_id'] is None:
                    break
                require(self.now() < end, 'abort/lease cleanup deadline')
                self.sleep(.1)
            require(not status['output_active'] and status['owner_id'] is None and
                    status['state'] not in ('armed', 'running', 'loaded'), 'abort inactivity not confirmed')

    def restore(self, board, image):
        if board not in self.snapshots:
            return 'UNCHANGED'
        require(self.snapshots[board]['sha256'], 'entry backup incomplete; retain STOP')
        self.deploy(board, image)
        info = self.info(board)
        quiescent(info, BOARDS[board], image)
        self.snapshots[board]['state'] = 'VERIFIED_INHIBITED'
        self.journal()
        self.close_peer(board)
        return 'VERIFIED_INHIBITED'

    def start_captures(self, root, duration): self.capture.start(root, duration)
    def captures_healthy(self): self.capture.healthy()
    def finish_captures(self): self.capture.finish()
    def stop_captures(self): self.capture.stop()
    def close(self):
        errors=[]
        try:
            for board in list(self.peers):
                try:
                    self.close_peer(board)
                except OSError as error:
                    errors.append(error)
        finally:
            self.stack.close()
        require(not errors, 'transport teardown uncertain')
