#!/usr/bin/env python3
"""Private wspr5 adapter for the authorized B-only inhibited recovery runner."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
import time

SERIAL = 'CDDBF8767C506C07'
DEVICE = '29f20b7342051ef947aa56cb9d4fab42'
CONSOLE = '/dev/serial/by-id/usb-WsprryPi_WsprryPico_' + SERIAL + '-if00'
PICOTOOL = '/home/pi/phase11-4-e1/picotool-build/picotool'
FLASH_SIZE = 4194304
RESERVED = 0x3f3000
E10 = 0x3ff000


def require(ok, message):
    if not ok:
        raise ValueError(message)


def strict(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def execute(argv, timeout=30):
    p = subprocess.run(argv, capture_output=True, timeout=timeout)
    require(p.returncode == 0, 'tool failed: ' + argv[0] + ' exit=' +
            str(p.returncode) + ' stderr=' + p.stderr.decode(errors='replace')[:512])
    return p.stdout.decode()


def console(command, timeout=5):
    import serial
    with serial.Serial(CONSOLE, 115200, timeout=.1, write_timeout=2, exclusive=True) as port:
        port.reset_input_buffer()
        port.write((command + '\n').encode())
        data = b''
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            data += port.read(1024)
            require(len(data) <= 16384, 'console response bound')
            while b'\n' in data:
                line, data = data.split(b'\n', 1)
                if line.startswith(b'{'):
                    return strict(line)
        raise TimeoutError('console timeout')


def resource_health(info):
    legacy = info.get("revision") == "615888e5364b"
    for key in ('allocator_failures', 'tls_allocation_failures', 'core0_stack_fault_status',
                'fault_stage', 'fault_hash', 'fault_pc', 'fault_status',
                'flash_read_failures', 'flash_erase_failures', 'flash_program_failures'):
        if key not in info and legacy: continue
        require(int(info[key]) == 0, 'resource fault: ' + key)
    require(info['core0_stack_guard_valid'] == 1 and info['fault_allocation_recorded'] is False,
            'stack/allocation fault')
    require('btstack_pools' in info or legacy, 'missing BTstack pool telemetry')
    if not legacy:
        require(set(info['btstack_pools']) == {'hci_connections','l2cap_channels',
                'l2cap_services','sm_lookup','whitelist'}, 'missing BTstack pool names')
    for pool in info.get('btstack_pools',{}).values():
        require(pool['failures'] == pool['faults'] == 0 and
                0 <= pool['used'] <= pool['capacity'], 'BTstack pool fault')
    if legacy and 'memory' not in info['network']: return
    memory = info['network']['memory']
    require(memory.get('statistics_enabled',legacy) is True, 'missing network pool telemetry')
    for name in ('heap', 'tcp_pcbs', 'tcp_listeners', 'udp_pcbs', 'timeouts',
                 'igmp_groups', 'tcp_segments', 'packet_pool'):
        if name not in memory and legacy: continue
        pool = memory[name]
        require(pool and pool['errors'] == 0 and 0 <= pool['used'] <= pool['capacity'],
                'network pool fault: ' + name)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def healthy(info, *, allow_fault=False, repair=False):
    require(info.get('device_id') == DEVICE, 'wrong B identity')
    if not repair: resource_health(info)
    s = info['status']
    states = ('empty', 'failed') if allow_fault else ('empty',)
    if repair:
        states += ('aborted', 'complete')
    retained_terminal = repair and s['state'] in ('aborted', 'complete')
    require(s['engine'] == 'inhibited-standalone-simulator' and
            s['output_active'] is False and s['enabled'] is False and
            s['state'] in states and not s.get('owner_id') and
            (retained_terminal or not s.get('job_id')), 'inactive inhibited authority required')
    if not allow_fault:
        require(info['access_state'] in ('healthy', 'erased') and s['storage_healthy'] is True
                and not info.get('bootstrap_reset_pending', False), 'healthy storage required')
    return info


def wait_info(seconds=30, allow_fault=False):
    end = time.monotonic() + seconds
    last = None
    while time.monotonic() < end:
        try:
            return healthy(console('INFO'), allow_fault=allow_fault)
        except (OSError, TimeoutError) as error:
            last = error
            time.sleep(.3)
    raise TimeoutError('device unavailable: ' + type(last).__name__)


def rom(repair=False):
    if Path(CONSOLE).exists():
        healthy(console('INFO'), allow_fault=True, repair=repair)
        result = console('BOOTSEL')
        require(result.get('ok') is True, 'ROM transition refused')
        time.sleep(1)
    # All picotool operations are explicitly serial selected, never -f generic.
    execute([PICOTOOL, 'info', '--ser', SERIAL])


def save(root, name):
    rom()
    path = root / name
    require(not path.exists(), 'snapshot cannot overwrite')
    execute([PICOTOOL, 'save', '-a', '-v', str(path), '-t', 'bin', '--ser', SERIAL], 45)
    require(path.stat().st_size == FLASH_SIZE, 'full flash backup size')
    os.chmod(path, 0o600)
    return {'path': name, 'sha256': digest(path), 'bytes': FLASH_SIZE}


def verify_image(data, uf2):
    from check_standalone_image import validate_uf2
    validate_uf2(uf2)
    for at in range(0, len(uf2), 512):
        address, size = struct.unpack_from('<II', uf2, at+12)
        if address == 0x10ffff00:
            continue
        require(0x10000000 <= address and address+size <= 0x103f3000, 'application bounds')
        require(data[address-0x10000000:address-0x10000000+size] == uf2[at+32:at+32+size],
                'programmed application mismatch')


def deploy(root, request, restore=False):
    rom(repair=restore)
    image = root / request['image']
    backup = root / request['backup']
    require(digest(image) == request['image_sha256'] and digest(backup) == request['backup_sha256'],
            'deployment artifact hash')
    before = backup.read_bytes()
    require(len(before) == FLASH_SIZE, 'backup size')
    if restore:
        reserved = root / ('reserved-' + request['readback'] + '.bin')
        require(not reserved.exists(), 'reserved restoration file exists')
        reserved.write_bytes(before[RESERVED:E10])
        os.chmod(reserved, 0o600)
        execute([PICOTOOL, 'load', '-v', str(reserved), '-t', 'bin', '-o', hex(0x10000000+RESERVED), '--ser', SERIAL], 45)
    execute([PICOTOOL, 'load', '-v', str(image), '--ser', SERIAL], 45)
    path = root / request['readback']
    require(not path.exists(), 'readback cannot overwrite')
    execute([PICOTOOL, 'save', '-a', '-v', str(path), '-t', 'bin', '--ser', SERIAL], 45)
    os.chmod(path, 0o600)
    after = path.read_bytes()
    require(len(after) == FLASH_SIZE and after[RESERVED:] == before[RESERVED:], 'reserved/E10 changed')
    verify_image(after, image.read_bytes())
    execute([PICOTOOL, 'reboot', '--ser', SERIAL])
    info = wait_info()
    require(info['revision'] == request['revision'], 'deployed revision mismatch')
    require(int(info.get('phase12_fault_stage', 0)) == request['stage'], 'deployed stage mismatch')
    require(not info.get('phase12_fault_consumed', False), 'fixture consumed before case')
    return {'info': info, 'readback': {'path': request['readback'], 'sha256': digest(path), 'bytes': FLASH_SIZE}}


def http(interface, path, value=None):
    # Interface-bound socket; management routing is never changed.
    deadline=time.monotonic()+10
    with socket.socket() as sock:
        def remaining():
            seconds=deadline-time.monotonic()
            if seconds<=0: raise TimeoutError('HTTP absolute deadline')
            sock.settimeout(min(6,seconds))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, (interface+'\0').encode())
        remaining()
        sock.connect(('192.168.4.1', 80))
        body = b'' if value is None else json.dumps(value, separators=(',', ':')).encode()
        headers = ('GET' if value is None else 'POST') + ' ' + path + ' HTTP/1.1\r\nHost: 192.168.4.1\r\nConnection: close\r\n'
        if value is not None:
            marker='Owner' if path.startswith('/api/owner/v1/') else 'Bootstrap'
            headers += 'Origin: http://192.168.4.1\r\nContent-Type: application/json\r\nX-WsprryPico-'+marker+': 1\r\nContent-Length: '+str(len(body))+'\r\n'
        remaining()
        sock.sendall(headers.encode()+b'\r\n'+body)
        data = b''
        while b'\r\n\r\n' not in data:
            remaining()
            part = sock.recv(1024)
            require(part, 'HTTP header disconnect')
            data += part
            require(len(data) <= 8192, 'HTTP header bound')
        head, payload = data.split(b'\r\n\r\n', 1)
        code = int(head.split(b' ')[1])
        lengths = [int(x.split(b':', 1)[1]) for x in head.split(b'\r\n') if x.lower().startswith(b'content-length:')]
        require(len(lengths) == 1 and 0 <= lengths[0] <= 8192, 'HTTP content length')
        while len(payload) < lengths[0]:
            remaining()
            part = sock.recv(min(1024, lengths[0]-len(payload)))
            require(part, 'HTTP body disconnect')
            payload += part
        require(len(payload) == lengths[0], 'HTTP body length')
        result = strict(payload)
        require(code == 200, 'HTTP rejected: '+str(code)+': '+str(result.get('error')))
        return result


def b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


def unb64(value):
    raw = base64.urlsafe_b64decode(value+'='*((-len(value))%4))
    require(b64(raw) == value, 'noncanonical base64url')
    return raw


def seal_recovery(level, info, start, private, request_nonce, request_id, nonce):
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    require(level in ('provisioning', 'full'), 'reset level')
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    require(start['device_id'] == DEVICE == info['device_id'] and start['boot_id'] == info['status']['boot_id'], 'recovery start binding')
    aad = b'WsprryPico/Recovery/1\0' + bytes.fromhex(DEVICE) + bytes.fromhex(start['boot_id']) + bytes.fromhex(start['slot_id']) + public + unb64(start['pico_public_key']) + bytes.fromhex(request_nonce) + bytes.fromhex(request_id)
    shared = private.exchange(X25519PublicKey.from_public_bytes(unb64(start['pico_public_key'])))
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=hashlib.sha256(aad).digest(), info=b'WsprryPico recovery AEAD v1').derive(shared)
    command = b'1:1:erase' if level == 'full' else b'1:1:reset provisioning'
    sealed = ChaCha20Poly1305(key).encrypt(nonce, command, aad)
    return dict(version=1, device_id=DEVICE, boot_id=start['boot_id'], slot_id=start['slot_id'], request_id=request_id, aead_nonce=b64(nonce), ciphertext=b64(sealed[:-16]), tag=b64(sealed[-16:]))


def configure_recovery_security(root,info,request):
    # The original recovery profile is open. Source1 engineering selects the
    # existing password-protected production SoftAP after enrollment.
    if info['provisioning_source']!='provisioned':return
    require(info['access_default_password'] is True and info['access_state']=='healthy',
            'retained default access required for secured recovery AP')
    root=Path(root)
    campaign=re.fullmatch('/home/pi/phase12-recovery-([0-9a-f]{32})',str(root))
    require(campaign is not None and request['interface']=='wlan2' and
            request['connection']=='p12-recovery-'+campaign.group(1),
            'exact campaign-owned recovery connection')
    suffix=info['local_suffix']
    require(re.fullmatch('[0-9a-f]{6}',suffix) is not None,'canonical local access suffix')
    execute(['sudo','-n','nmcli','connection','modify',request['connection'],
             'wifi-sec.key-mgmt','wpa-psk','wifi-sec.psk','wspr-'+suffix,
             'wifi-sec.proto','rsn','wifi-sec.pairwise','ccmp','wifi-sec.group','ccmp'],10)


def prepare(root, request):
    from cryptography.hazmat.primitives.asymmetric import x25519, ec
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    info = healthy(console('INFO'))
    require(info['revision'] == request['revision'] and int(info.get('phase12_fault_stage',0)) == request['stage'] and info.get('phase12_fault_consumed') is False, 'pre-mutation fixture binding')
    interface = request['interface']
    configure_recovery_security(root,info,request)
    execute(['sudo', '-n', 'nmcli', 'connection', 'up', request['connection']], 35)
    status = http(interface, '/api/recovery/v1/status')
    require(status['device_id'] == DEVICE and status['boot_id'] == info['status']['boot_id'] and not status['pending'], 'AP device/boot mismatch')
    private = x25519.X25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    nonce_hex, request_id = os.urandom(16).hex(), os.urandom(16).hex()
    nonce = os.urandom(12)
    if request['kind'] == 'reset':
        start = http(interface, '/api/recovery/v1/start', dict(version=1,device_id=DEVICE,browser_public_key=b64(public),request_nonce=nonce_hex))
        body = seal_recovery(request['level'], info, start, private, nonce_hex, request_id, nonce)
        route = '/api/recovery/v1/submit'
        expected_digest = hashlib.sha256(unb64(body['ciphertext'])).hexdigest()
    else:
        owner = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
        current = http(interface, '/api/owner/v1/public-status')
        require(current['device_id'] == DEVICE and current['boot_id'] == info['status']['boot_id'] and current['profile_source'] == 5 and current['claim_available'], 'consumer save precondition')
        start = http(interface, '/api/owner/v1/claim/start',dict(version=1,device_id=DEVICE,owner_public_key=b64(owner),browser_public_key=b64(public),browser_nonce=nonce_hex,profile_source=5,generation=current['generation']))
        require(start['device_id'] == DEVICE and start['boot_id'] == info['status']['boot_id'] and start['browser_public_key']==b64(public) and start['browser_nonce']==nonce_hex, 'claim start binding')
        aad = b'WsprryPico/Owner-Claim/1\0'+bytes.fromhex(DEVICE)+bytes.fromhex(start['boot_id'])+bytes.fromhex(start['slot_id'])+b'http://192.168.4.1'+bytes([5])+int(start['generation']).to_bytes(8,'big')+owner+public+unb64(start['pico_public_key'])+bytes.fromhex(nonce_hex)+bytes.fromhex(request_id)
        shared = private.exchange(x25519.X25519PublicKey.from_public_bytes(unb64(start['pico_public_key'])))
        key = HKDF(algorithm=hashes.SHA256(),length=32,salt=hashlib.sha256(aad).digest(),info=b'WsprryPico owner claim AEAD v1').derive(shared)
        station = request['station']; callsign=station['callsign'].encode(); locator=station['locator'].encode()
        plain = b'\0\0'+bytes([len(callsign)])+callsign+locator+bytes([station['power_dbm']])
        sealed = ChaCha20Poly1305(key).encrypt(nonce,plain,aad)
        body = dict(version=1,device_id=DEVICE,boot_id=start['boot_id'],slot_id=start['slot_id'],request_id=request_id,aead_nonce=b64(nonce),ciphertext=b64(sealed[:-16]),tag=b64(sealed[-16:]))
        route='/api/owner/v1/claim/submit'; expected_digest=hashlib.sha256(bytes.fromhex(request_id)).hexdigest()
    payload = dict(route=route,body=body,interface=interface,device_id=DEVICE,boot_id=info['status']['boot_id'],stage=request['stage'],revision=request['revision'])
    path=root/request['prepared'];require(not path.exists(),'prepared request exists');
    with path.open('x') as out:
        out.write(json.dumps(payload));out.flush();os.fsync(out.fileno())
    sync_directory(root)
    return dict(prepared=request['prepared'],sha256=digest(path),request_id=request_id,expected_digest=expected_digest,info=info)


def main():
    os.umask(0o077)
    request = strict(sys.stdin.buffer.read(65537));require(len(json.dumps(request))<=65536,'request bound')
    root=Path(request['root']);require(re.fullmatch(r'/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)),'private root')
    require(root.is_dir() and not root.is_symlink(),'root missing/symlink')
    for name in ('image','backup','readback','name','prepared'):
        if name in request: require(re.fullmatch(r'[a-z0-9_.-]+',request[name]) and not (root/request[name]).is_symlink(),'artifact path')
    # Distinct from the campaign lease: an orphaned SSH action cannot overlap
    # restoration or another picotool operation, even within one campaign.
    lock = os.open('/home/pi/.wsprrypico-recovery-action-'+SERIAL+'.lock',
                   os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    action=request['action']
    if action=='info': result=healthy(console('INFO'),allow_fault=request.get('allow_fault',False))
    elif action=='reboot_original':
        # The action flock also excludes a still-running snapshot after SSH loss.
        # Exact-serial ROM reboot only: never load, erase, or repeat a snapshot.
        execute([PICOTOOL, 'reboot', '--ser', SERIAL], 30)
        result=wait_info(30,allow_fault=True)
    elif action=='open_ap':
        info=healthy(console('INFO'))
        require(int(info.get('phase12_fault_stage',0)) in range(1,11) and
                info.get('phase12_boot_ap_window_ms')==120000 and
                info.get('phase12_fault_consumed') is False, 'bounded fixture AP unavailable')
        result={'fixture_ap_window_ms':120000};time.sleep(3)
    elif action=='snapshot': result=save(root,request['name'])
    elif action in ('deploy','restore'): result=deploy(root,request,action=='restore')
    elif action=='prepare': result=prepare(root,request)
    elif action=='submit':
        path=root/request['prepared'];require(digest(path)==request['prepared_sha256'],'prepared hash')
        prepared=strict(path.read_bytes());info=healthy(console('INFO'))
        require(info['revision']==prepared['revision'] and info['status']['boot_id']==prepared['boot_id'] and int(info['phase12_fault_stage'])==prepared['stage'] and info['phase12_fault_consumed'] is False,'submit binding')
        marker=path.with_suffix('.sent');require(not marker.exists(),'never repeat destructive request')
        with marker.open('x') as out: out.write('sending\n');out.flush();os.fsync(out.fileno())
        sync_directory(root)
        try: result={'response':http(prepared['interface'],prepared['route'],prepared['body']),'uncertain':False}
        except (OSError,ValueError) as error: result={'uncertain':True,'error':type(error).__name__}
    else: raise ValueError('unknown action')
    print(json.dumps(result,separators=(',',':')))


if __name__=='__main__':
    try: main()
    except Exception as error:
        print(json.dumps({'adapter_error':type(error).__name__,'message':str(error)}));sys.exit(1)
