"""Finite P2 overlap: one held 32 KiB WTP input and one declared HTTP outcome."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import select
import socket
import ssl
import time
import threading
from contextlib import contextmanager
from phase11_5_inventory import require
from phase11_5_device_management import digest, save
from phase11_5_r3_capacity_plan import http_capacity_cases, identity, padded_json

POLICY = 'phase115-completion-combined-v1'
SOURCE = '8dd6f0812292e9264c2a72745078a95ee606c191'
IMAGE = 'ccfdf60b2b927b4a3fd14cc9254a6748334d584ebad0d672771939ab2369b40d'
PRIVATE_ROOT = '/home/pi/phase11-5-memory-pressure-rf-20260915'
BOOT = '7a04779b8018624574066260fce9d0d8'
NAME = 'wsprrypico-0a60df.local'
PEER = '06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016'
DEVICE = 'fd6127d11d6aca42a9905fa3fb1bf1d5'


def cases(seed, mode):
    identity(seed); require(mode in ('supported', 'overload'), 'Declared P2 case')
    ident = lambda label: hashlib.sha256((seed + ':' + label).encode()).hexdigest()[:32]
    primary = http_capacity_cases(ident('primary'))[2 if mode == 'supported' else 0]
    primary['label'] = mode
    if mode == 'overload':
        primary.update(wire_hex=bytes.fromhex(primary['wire_hex']).split(b'\r\n\r\n')[0].hex()+'0d0a0d0a',
                       offered_body_bytes=0, expected_status=503, error_code='resource_exhausted')
    recovery = http_capacity_cases(ident('recovery'))[2]
    recovery['label'] = 'recovery'
    return [primary, recovery]


def combined_frame(session, request):
    from validate_wtp_contract import frame
    value=dict(type='request',protocol='WTP/1',session_id=identity(session),request_id=identity(request),op='STATUS',body={})
    return frame(padded_json(value,32768))


def validate_profile(p):
    require(p.get('private_reference_root') == PRIVATE_ROOT and isinstance(p.get('private_reference_sha256'),dict) and
            set(p['private_reference_sha256']) == {'production.ini', *('credentials/'+role+'/'+name for role in ('controller','browser') for name in ('client-ca.crt','client.crt','client.key'))} and
            all(isinstance(h,str) and len(h)==64 and all(c in '0123456789abcdef' for c in h) for h in p['private_reference_sha256'].values()), 'Existing lab private references only')
    require(p.get('assertion_ids')==['2.2a' if p['combined']['mode']=='supported' else '2.2b'], 'Exact P2 assertion scope')
    c = p['combined']; identity(c['seed']); identity(c['wtp_request_id'])
    require(set(c) == {'mode', 'seed', 'wtp_request_id', 'cases', 'minimum_resident_delta_bytes', 'wtp_payload_bytes'} and
            c['cases'] == cases(c['seed'], c['mode']) and c['minimum_resident_delta_bytes'] == 32768 and c['wtp_payload_bytes']==32768,
            'Frozen P2 stimuli and allocation gate')
    require((p['source_revision'], p['image_sha256'], p['boot_id']) == (SOURCE, IMAGE, BOOT) and
            p['closure_policy'] == POLICY and p['runtime_seconds'] == 300 and p['maximum_renewals'] == 8 and
            p['observer_policy'] == 'single-flight-info-v1' and
            p['contention']['policy'] == 'native-wtp-and-https-status-20s-v1' and
            p['contention']['maximum_https_requests'] == 2 and
            not any(k in p for k in ('wtp_capacity', 'http_capacity', 'capacity_schedule_policy',
                                    'allocator_failure_baseline', 'diagnostic_policy')),
            'Exact P2 source, observation and workload')
    require(len(p['jobs']) == 1 and p['jobs'][0]['mode'] == 'fskcw' and
            p['jobs'][0]['total_duration_ns'] == '128000000000' and p['jobs'][0]['events'] == [
                dict(offset_ns=str(n*250000000), duration_ns='250000000', rf_on=True,
                     frequency_nhz=str(135500000000000 if n % 2 == 0 else 135495000000000))
                for n in range(512)], 'Exact finite P2 RF plan')
    records = p['initial_terminal_records']
    require(isinstance(records, list) and len(records) == p['maximum_initial_terminal_records'] <= 8 and
            len({identity(r['job_id']) for r in records}) == len(records) and
            all(r['state'] in ('complete', 'aborted') and r['output_active'] is False for r in records),
            'Frozen retained records')
    require((p.get('initial_a_state'),p.get('initial_a_job_id'))==('empty',None) or
            (p.get('initial_a_state')=='complete' and any(r['job_id']==p.get('initial_a_job_id') and r['state']=='complete' for r in records)),
            'Exact inactive predecessor in retained records')
    require(type(p['not_before_host_monotonic_ns']) is int and p['not_before_host_monotonic_ns'] > 0,
            'Frozen P2 start')
    return p


def running(value, p):
    require(value['boot_id'] == p['boot_id'] and value['job_id'] == p['jobs'][0]['job_id'] and
            value['owner_id'] == p['owner_id'] and value['state'] == 'running' and
            value['output_active'] is True, 'Same owned Running RF')


def info_running(value, p):
    # INFO carries scheduler state; job and owner identities come from WTP STATUS.
    require(value['boot_id']==p['boot_id'] and value['state']=='running' and
            value['output_active'] is True, 'Independent INFO Running state')


def snapshot(root, p, *, after=0):
    from phase11_5_browser_jobs import admit_snapshot
    sha = digest(root/'packet.json'); now = time.monotonic_ns()
    values = {k: json.loads((root/('observer-'+k+'.json')).read_text()) for k in ('status', 'info', 'console_tx')}
    for k, age in [('status', 6_000_000_000), ('info', 2_000_000_000)]:
        admit_snapshot(values[k], now, age, sha, values['console_tx'] if k == 'info' else None,
                       'INFO' if k == 'info' else 'STATUS')
    require(not (root/'observer-failure.json').exists(), 'Independent observer failed')
    running(values['status']['value']['value'], p); info_running(values['info']['value']['value']['status'], p)
    require(values['info']['monotonic_ns'] > after, 'New independent INFO required')
    return values


def resident(sample, baseline, began, p):
    require(sample['packet_sha256'] == baseline['packet_sha256'] and
            sample['monotonic_ns'] > began > baseline['monotonic_ns'], 'Residence observation order/identity')
    info = sample['value']['value']; info_running(info['status'], p)
    require(info['heap_allocated_bytes'] - baseline['value']['value']['heap_allocated_bytes'] >=
            p['combined']['minimum_resident_delta_bytes'], 'Full WTP input not observed resident')


def usb_step(peer, root, p, emit):
    sha = digest(root/'packet.json')
    ready = json.loads((root/'combined-http-ready.json').read_text())
    require(ready['packet_sha256'] == sha and 0 <= time.monotonic_ns()-ready['monotonic_ns'] <= 6_000_000_000,
            'Fresh established HTTP peer required')
    raw = combined_frame(peer.session, p['combined']['wtp_request_id'])
    request = json.loads(raw[16:]); began = time.monotonic_ns(); deadline = time.monotonic()+5
    emit('capacity_tx', dict(request=request, hex=raw.hex(), expected_invalid_frames=0))
    written = 0; published = False; released = False
    while time.monotonic() < deadline:
        peer.checkpoint()
        if not published and written >= 4096:
            sample = json.loads((root/'observer-info.json').read_text())
            if (sample['monotonic_ns'] > began and sample['value']['value']['heap_allocated_bytes'] -
                    ready['info']['value']['value']['heap_allocated_bytes'] >= p['combined']['minimum_resident_delta_bytes']):
                resident(sample, ready['info'], began, p)
                record = dict(packet_sha256=sha, began_ns=began, info=sample, baseline=ready['info'])
                emit('combined_resident', record); save(root/'combined-usb-resident.json', record); published = True
        if not released and (root/'combined-http-response.json').exists():
            reply = json.loads((root/'combined-http-response.json').read_text())
            require(published and reply['packet_sha256'] == sha and reply['mode'] == p['combined']['mode'] and
                    began < reply['monotonic_ns'] <= time.monotonic_ns(), 'Exact HTTP result before last byte')
            released = True
        limit = len(raw) if released else len(raw)-1
        reads, writes, _ = select.select([peer.fd], [peer.fd] if written < limit else [], [], .01)
        if writes:
            try:
                n = os.write(peer.fd, raw[written:min(written+4096, limit)])
                require(n > 0, 'P2 USB write stalled'); written += n
                emit('capacity_write', dict(bytes=n, total_written=written))
            except BlockingIOError: pass
        if reads:
            try: data = os.read(peer.fd, 4096)
            except BlockingIOError: continue
            require(data, 'P2 USB EOF'); emit('capacity_rx', dict(hex=data.hex()))
            for v in peer.decoder.feed(data):
                require(not peer.validator.errors(v, peer.schema) and v['session_id'] == peer.session,
                        'P2 USB schema/session')
                emit('capacity_message', v)
                require(v['type'] == 'response' and v['request_id'] == request['request_id'] and
                        v['op'] == 'STATUS' and v['ok'] is True and released and written == len(raw),
                        'Complete supported WTP response required')
                running(v['body'], p)
                save(root/'combined-usb-complete.json', dict(packet_sha256=sha, monotonic_ns=time.monotonic_ns()))
                return
    raise TimeoutError('P2 original five-second WTP exchange deadline')


@contextmanager
def response_deadline(stream, deadline):
    def expire():
        try: stream.shutdown(socket.SHUT_RDWR)
        except OSError: pass
    timer=threading.Timer(max(.001,deadline-time.monotonic()),expire);timer.daemon=True;timer.start()
    try: yield
    finally: timer.cancel();timer.join(1)


def run_http(root, p, emit, stop, end):
    from phase11_5_r3_v2_parallel_b_functional import http_exchange
    sha = digest(root/'packet.json'); c = p['combined']; primary, recovery = c['cases']
    def check(deadline=end):
        require(time.monotonic() < deadline and not stop.is_set() and
                not (root/'rf-observation-done.json').exists() and not (root/'observer-failure.json').exists(),
                'P2 finite deadline or observation failure')
    while True:
        check()
        try: admission = snapshot(root, p); break
        except (FileNotFoundError, ValueError): stop.wait(.05)
    private=Path(p['private_reference_root'])
    ctx = ssl.create_default_context(cafile=private/'credentials/browser/client-ca.crt')
    ctx.minimum_version = ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(private/'credentials/browser/client.crt', private/'credentials/browser/client.key')
    ctx.set_alpn_protocols(['http/1.1']); began = time.monotonic_ns(); deadline = time.monotonic()+15
    emit('combined_http_admission', admission)
    with socket.create_connection(('10.77.15.10',18443),timeout=5) as raw:
        with ctx.wrap_socket(raw,server_hostname=NAME) as stream:
            require(stream.selected_alpn_protocol()=='http/1.1' and
                    hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest()==PEER, 'P2 authenticated peer')
            with response_deadline(stream,deadline):
                authenticated = time.monotonic_ns()
                while True:
                    check(deadline)
                    try: warmed = snapshot(root, p, after=authenticated); break
                    except (FileNotFoundError, ValueError): stop.wait(.01)
                ready = dict(packet_sha256=sha, monotonic_ns=time.monotonic_ns(), info=warmed['info'],
                             authenticated_ns=authenticated, peer_sha256=PEER)
                emit('combined_http_ready', ready); save(root/'combined-http-ready.json',ready)
                while not (root/'combined-usb-resident.json').exists(): check(deadline); stop.wait(.01)
                record=json.loads((root/'combined-usb-resident.json').read_text())
                require(record['packet_sha256']==sha, 'P2 resident packet')
                resident(record['info'], ready['info'], record['began_ns'], p)
                require(0 <= time.monotonic_ns()-record['info']['monotonic_ns'] <= 2_000_000_000,
                        'Fresh resident allocation before HTTP')
                snapshot(root,p)
                emit('http_tx',primary); stream.settimeout(max(.001,deadline-time.monotonic()))
                wire=bytes.fromhex(primary['wire_hex']); stream.sendall(wire)
                emit('http_write_complete',dict(label=primary['label'],bytes=len(wire)))
                response=http.client.HTTPResponse(stream); response.begin(); body=response.read(131073)
                check(deadline); require(len(body)<=131072, 'P2 HTTP response bound')
                value=json.loads(body)
                emit('http_response',dict(label=primary['label'],status=response.status,headers=response.getheaders(),
                     body_hex=body.hex(),peer_sha256=PEER,began_monotonic_ns=began))
                require(response.status==primary['expected_status'], 'Declared supported/overload outcome')
                if c['mode']=='overload': require(value['error']['code']=='resource_exhausted','Intended admission refusal')
                else: require(value['ok'] is True and value['result']['device_id']==DEVICE and
                              value['result']['boot_id']==p['boot_id'],'Supported HTTP identity')
                save(root/'combined-http-response.json',dict(packet_sha256=sha,mode=c['mode'],monotonic_ns=time.monotonic_ns()))
    while not (root/'combined-usb-complete.json').exists(): check(); stop.wait(.01)
    require(json.loads((root/'combined-usb-complete.json').read_text())['packet_sha256']==sha,'P2 USB completion packet')
    admission=snapshot(root,p); emit('combined_recovery_admission',admission)
    http_exchange(private,dict(p,address='10.77.15.10'),recovery,emit,target=(NAME,PEER,DEVICE))
    save(root/'combined-complete.json',dict(packet_sha256=sha,mode=c['mode'],monotonic_ns=time.monotonic_ns()))
