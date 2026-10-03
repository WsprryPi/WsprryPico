#!/usr/bin/env python3
"""Finite B-only Plain LAN simulator control with USB INFO observations; explicit opt-in, no RF.

Parent campaign owns backup/restoration and the independent two-hour observer.
Failures never replay uncertain requests. This driver never flashes/configures.
"""
import argparse
import contextlib
import fcntl
import hashlib
import ipaddress
import json
import os
import re
from pathlib import Path
import select
import socket
import struct
import time
import termios
import uuid

from phase12_candidate_manifest import read_json, verify
from phase12_recovery_device import DEVICE, SERIAL, resource_health, strict
from inhibited_network_acceptance import check_caps, check_clock, check_status, job_value
from validate_wtp_contract import frame
from wtp_monitor import FrameDecoder

ENGINE = 'inhibited-standalone-simulator'
MAX_PAYLOAD = 65536


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


class Evidence:
    def __init__(self, path):
        self.file = Path(path).open('x')
        os.chmod(path, 0o600)
        self.count = 0

    def record(self, kind, **value):
        require(self.count < 10000, 'finite evidence budget')
        self.count += 1
        self.file.write(json.dumps(dict(kind=kind, monotonic_ns=time.monotonic_ns(),
                                      **value), sort_keys=True) + '\n')
        self.file.flush()
        os.fsync(self.file.fileno())

    def close(self):
        self.file.close()


class Peer:
    def __init__(self, fd, carrier, evidence):
        self.fd, self.carrier, self.evidence = fd, carrier, evidence
        self.session = uuid.uuid4().hex
        self.sequence, self.requests = 0, 0
        self.decoder = FrameDecoder()
        self.pending = []
        self.stage_deadline = None

    def write(self, wire, deadline):
        self.evidence.record('wire_send_attempt', carrier=self.carrier,
                             session_id=self.session, raw_hex=wire.hex(),
                             sha256=hashlib.sha256(wire).hexdigest())
        while wire:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('write deadline; do not replay')
            if select.select([], [self.fd], [], remaining)[1]:
                try:
                    sent = os.write(self.fd, wire)
                except BlockingIOError:
                    continue
                require(sent > 0, 'closed write')
                wire = wire[sent:]

    def message(self, deadline):
        while time.monotonic() < deadline:
            if self.pending:
                return self.pending.pop(0)
            if select.select([self.fd], [], [], deadline-time.monotonic())[0]:
                chunk = os.read(self.fd, 4096)
                require(chunk, 'stream closed')
                self.evidence.record('wire_receive', carrier=self.carrier,
                    raw_hex=chunk.hex(), sha256=hashlib.sha256(chunk).hexdigest())
                for payload in self.decoder.feed(chunk):
                    value = strict(payload)
                    require(value.get('protocol') == 'WTP/1' and
                            value.get('session_id') == self.session and
                            value.get('type') in ('response', 'event'), 'wire identity/session')
                    require(len(self.pending) < 64, 'bounded pending events')
                    self.pending.append(value)
        raise TimeoutError('response deadline; do not replay')

    def request(self, op, body, expected=None, padding=None):
        require(self.requests < 1000, 'request budget')
        self.requests += 1
        self.sequence += 1
        request_id = '%032x' % self.sequence
        payload = canonical(dict(type='request', protocol='WTP/1', session_id=self.session,
                                 request_id=request_id, op=op, body=body))
        if padding is not None:
            require(len(payload) <= padding <= MAX_PAYLOAD, 'frame padding bound')
            payload += b' ' * (padding-len(payload))
        deadline = time.monotonic() + 10
        if self.stage_deadline is not None:
            deadline = min(deadline, self.stage_deadline)
        require(time.monotonic() < deadline, 'stage deadline before request')
        self.write(frame(payload), deadline)
        while time.monotonic() < deadline:
            result = self.message(deadline)
            if result['type'] == 'event':
                self.evidence.record('event', carrier=self.carrier, value=result)
                continue
            require(result.get('request_id') == request_id and result.get('op') == op,
                    'response correlation')
            if expected is not None:
                require(result.get('ok') is False and result['error']['code'] == expected,
                        'expected negative: ' + expected)
                return result
            require(result.get('ok') is True, 'unexpected response error: ' + str(result.get('error')))
            return result['body']
        raise TimeoutError('request deadline')

    def frame_boundary(self):
        self.request('STATUS', {}, padding=MAX_PAYLOAD)
        deadline = time.monotonic()+10
        # Declare max+1 without injecting a fake JSON body or three bad frames.
        self.write(b'WTPF'+struct.pack('>BBHII', 1, 1, 0, MAX_PAYLOAD+1, 0), deadline)
        for _ in range(64):
            event = self.message(deadline)
            if event['type'] == 'event' and event.get('event') == 'INVALID_FRAME':
                return
        raise ValueError('missing INVALID_FRAME boundary event')


def negotiate(peer, boot):
    hello = peer.request('HELLO', dict(versions=['WTP/1'],
                         client_name='phase12-consumer-composition', client_version='1'))
    require(hello['device_id'] == DEVICE and hello['boot_id'] == boot, 'HELLO B/boot identity')
    caps = peer.request('CAPS', {})
    check_caps(caps)
    require(caps['minimum_lease_ms'] <= 5000 <= caps['maximum_lease_ms'],
            'disconnect lease CAPS')
    return status(peer, boot)


def status(peer, boot, owner=None, job=None, state=None, unowned=False):
    value = peer.request('STATUS', {})
    check_status(value, boot, owner=owner, job=job,
                 states=None if state is None else (state,), unowned=unowned)
    return value


def competitors(owner_peer, foreign, boot, owner, job, state):
    before = status(owner_peer, boot, owner, job, state)
    foreign.request('CLAIM', dict(owner_id=uuid.uuid4().hex, lease_ms=60000), 'BUSY')
    foreign.request('LOAD', job_value(uuid.uuid4().hex), 'NOT_OWNER')
    foreign.request('ABORT', dict(job_id=job), 'NOT_OWNER')
    after = status(owner_peer, boot, owner, job, state)
    require((before['owner_id'], before['job_id'], before['state']) ==
            (after['owner_id'], after['job_id'], after['state']), 'foreign mutation altered authority')


def run_directed(peers, boot, evidence, guard=lambda: None,
                 clock=time.monotonic, sleeper=time.sleep):
    """Exactly six finite simulator jobs, no reconnect/replay on uncertainty."""
    completed = 0
    for carrier in ('usb', 'plain_lan'):
        peer, foreign = peers[carrier], peers['plain_lan' if carrier == 'usb' else 'usb']
        for target in ('loaded', 'armed', 'running'):
            stage_started = clock()
            for candidate in peers.values():
                candidate.stage_deadline = time.monotonic()+60
            guard()
            for candidate in peers.values():
                status(candidate, boot, unowned=True)
            owner, job = uuid.uuid4().hex, uuid.uuid4().hex
            operations = set()
            try:
                operations.add('CLAIM')
                claimed = peer.request('CLAIM', dict(owner_id=owner, lease_ms=60000))
                require(claimed['owner_id'] == owner, 'owner claim')
                operations.add('LOAD')
                peer.request('LOAD', job_value(job))
                status(peer, boot, owner, job, 'loaded')
                if target != 'loaded':
                    guard()
                    start = check_clock(peer.request('GET_CLOCK', {}))
                    operations.add('ARM')
                    peer.request('ARM', dict(job_id=job, start_utc_ns=str(start),
                                             max_start_uncertainty_ns='500000000'))
                    status(peer, boot, owner, job, 'armed')
                    if target == 'running':
                        deadline = clock()+14
                        while clock() < deadline:
                            observation = status(peer, boot, owner, job)
                            if observation['state'] == 'running':
                                break
                            require(observation['state'] == 'armed', 'missed running observation')
                            sleeper(.1)
                        else:
                            raise TimeoutError('running stage deadline')
                require(clock()-stage_started < 60, 'finite stage deadline')
                guard()
                competitors(peer, foreign, boot, owner, job, target)
                operations.add('ABORT')
                peer.request('ABORT', dict(job_id=job))
                status(peer, boot, owner, job, 'aborted')
                operations.add('RELEASE')
                peer.request('RELEASE', {})
                status(peer, boot, unowned=True)
                require(clock()-stage_started <= 60, 'finite stage deadline')
                completed += 1
                evidence.record('directed_case_pass', carrier=carrier, state=target,
                                owner_id=owner, job_id=job)
            except BaseException:
                for candidate in peers.values():
                    candidate.stage_deadline = None
                evidence.record('directed_case_failed', carrier=carrier, state=target,
                                owner_id=owner, job_id=job)
                # Readback only first. Never repeat an ABORT/RELEASE with uncertain delivery.
                try:
                    current = status(peer, boot)
                    if current['owner_id'] == owner and current['job_id'] in (None, job):
                        if current['state'] in ('loaded', 'armed', 'running') and 'ABORT' not in operations:
                            peer.request('ABORT', dict(job_id=job))
                            current = status(peer, boot)
                        if current['state'] in ('empty', 'aborted', 'complete', 'missed') and 'RELEASE' not in operations:
                            peer.request('RELEASE', {})
                except BaseException as error:
                    evidence.record('cleanup_failed', carrier=carrier, error=type(error).__name__)
                raise
    for candidate in peers.values():
        candidate.stage_deadline = None
    require(completed == 6, 'six case limit')
    return completed


def refused_connections(address, peer, boot, evidence, connector=socket.create_connection,
                        owner=None, job=None, state=None):
    """Plain admission permits one WTP session; two additional attempts must close."""
    for attempt in range(2):
        try:
            with connector((address, 31417), timeout=5) as extra:
                extra.settimeout(5)
                try:
                    data = extra.recv(1)
                    require(data == b'', 'excess connection admitted/data received')
                except ConnectionResetError:
                    pass
        except ConnectionRefusedError:
            pass
        # Timeout is inconclusive, never a refusal PASS.
        status(peer, boot, owner=owner, job=job, state=state, unowned=owner is None)
        evidence.record('plain_excess_refused', attempt=attempt+1,
                        primary_session=peer.session, admitted_wtp_limit=1)


def disconnect_reclaim(peer, observer, boot, close, evidence,
                       clock=time.monotonic, sleeper=time.sleep):
    owner = uuid.uuid4().hex
    value = peer.request('CLAIM', dict(owner_id=owner, lease_ms=5000))
    require(value['owner_id'] == owner, 'disconnect owner claim')
    status(observer, boot, owner=owner, state='empty')
    close()
    deadline = clock()+7
    prior_deadline = getattr(observer, 'stage_deadline', None)
    real_deadline = time.monotonic()+7
    try:
        for _ in range(71):
            require(clock() <= deadline, 'disconnect reclamation deadline before STATUS')
            observer.stage_deadline = (real_deadline if prior_deadline is None else
                                       min(real_deadline, prior_deadline))
            current = status(observer, boot)
            require(clock() <= deadline, 'disconnect reclamation deadline after STATUS')
            if current['owner_id'] is None:
                check_status(current, boot, unowned=True)
                evidence.record('disconnect_reclaim_pass', owner_id=owner,
                                disconnected_session=peer.session, job_count=0)
                return
            require(current['owner_id'] == owner and current['job_id'] is None and
                    current['state'] == 'empty', 'unexpected reclaim authority/state')
            sleeper(.1)
        raise TimeoutError('disconnect reclamation finite poll budget')
    finally:
        observer.stage_deadline = prior_deadline


def run_lan_directed(peer, boot, evidence, address, guard, refusal=None,
                 clock=time.monotonic, sleeper=time.sleep):
    """Three supported consumer LAN jobs observed independently through USB INFO."""
    peers = {'plain_lan':peer}
    refusal = refused_connections if refusal is None else refusal
    completed = 0
    for carrier in ('plain_lan',):
        peer = peers[carrier]
        for target in ('loaded', 'armed', 'running'):
            stage_started = clock()
            for candidate in peers.values():
                candidate.stage_deadline = time.monotonic()+60
            guard()
            for candidate in peers.values():
                status(candidate, boot, unowned=True)
            owner, job = uuid.uuid4().hex, uuid.uuid4().hex
            operations = set()
            try:
                operations.add('CLAIM')
                claimed = peer.request('CLAIM', dict(owner_id=owner, lease_ms=60000))
                require(claimed['owner_id'] == owner, 'owner claim')
                operations.add('LOAD')
                peer.request('LOAD', job_value(job))
                status(peer, boot, owner, job, 'loaded')
                if target != 'loaded':
                    guard()
                    start = check_clock(peer.request('GET_CLOCK', {}))
                    operations.add('ARM')
                    peer.request('ARM', dict(job_id=job, start_utc_ns=str(start),
                                             max_start_uncertainty_ns='500000000'))
                    status(peer, boot, owner, job, 'armed')
                    if target == 'running':
                        deadline = clock()+14
                        while clock() < deadline:
                            observation = status(peer, boot, owner, job)
                            if observation['state'] == 'running':
                                break
                            require(observation['state'] == 'armed', 'missed running observation')
                            sleeper(.1)
                        else:
                            raise TimeoutError('running stage deadline')
                require(clock()-stage_started < 60, 'finite stage deadline')
                guard()
                before = guard()['status']
                require(before['boot_id']==boot and before['state']==target and
                        before['output_active'] is False, 'independent INFO job state')
                owned_before=status(peer,boot,owner,job,target)
                refusal(address, peer, boot, evidence, owner=owner, job=job, state=target)
                after = guard()['status']
                require(after['boot_id']==boot and after['state']==target and
                        after['output_active'] is False, 'independent INFO job state')
                owned_after=status(peer,boot,owner,job,target)
                evidence.record('INFO_authority_limit',owner_id_available=False,job_id_available=False,
                                authority_source='LIVE_LAN_STATUS')
                require((owned_before['owner_id'],owned_before['job_id'],owned_before['state']) ==
                        (owned_after['owner_id'],owned_after['job_id'],owned_after['state']),
                        'foreign admission altered job authority')
                operations.add('ABORT')
                peer.request('ABORT', dict(job_id=job))
                status(peer, boot, owner, job, 'aborted')
                operations.add('RELEASE')
                peer.request('RELEASE', {})
                status(peer, boot, unowned=True)
                require(clock()-stage_started <= 60, 'finite stage deadline')
                completed += 1
                evidence.record('directed_case_pass', carrier=carrier, state=target,
                                owner_id=owner, job_id=job)
            except BaseException:
                for candidate in peers.values():
                    candidate.stage_deadline = None
                evidence.record('directed_case_failed', carrier=carrier, state=target,
                                owner_id=owner, job_id=job)
                # Readback only first. Never repeat an ABORT/RELEASE with uncertain delivery.
                try:
                    current = status(peer, boot)
                    if current['owner_id'] == owner and current['job_id'] in (None, job):
                        if current['state'] in ('loaded', 'armed', 'running') and 'ABORT' not in operations:
                            peer.request('ABORT', dict(job_id=job))
                            current = status(peer, boot)
                        if current['state'] in ('empty', 'aborted', 'complete', 'missed') and 'RELEASE' not in operations:
                            peer.request('RELEASE', {})
                except BaseException as error:
                    evidence.record('cleanup_failed', carrier=carrier, error=type(error).__name__)
                raise
    for candidate in peers.values():
        candidate.stage_deadline = None
    require(completed == 3, 'three case limit')
    return completed


def lan_disconnect_reconnect(peer, boot, close, reconnect, evidence,
                             clock=time.monotonic, sleeper=time.sleep):
    owner=uuid.uuid4().hex
    claimed=peer.request('CLAIM',dict(owner_id=owner,lease_ms=5000))
    require(claimed['owner_id']==owner,'disconnect owner claim')
    deadline=clock()+7
    close()
    fresh,finish=reconnect(deadline)
    try:
        require(fresh.session!=peer.session,'fresh LAN session')
        fresh.stage_deadline=time.monotonic()+max(0,deadline-clock())
        negotiate(fresh,boot)
        for _ in range(71):
            require(clock()<=deadline,'reclaim deadline before STATUS')
            value=status(fresh,boot)
            require(clock()<=deadline,'reclaim deadline after STATUS')
            if value['owner_id'] is None:
                check_status(value,boot,unowned=True)
                evidence.record('lan_disconnect_reconnect_pass',retired_session=peer.session,
                                fresh_session=fresh.session,owner_id=owner,job_count=0)
                return
            require(value['owner_id']==owner and value['job_id'] is None and value['state']=='empty',
                    'unexpected reconnect authority')
            sleeper(.1)
        raise TimeoutError('finite reconnect status poll budget')
    finally:finish()


def restore_usb_dtr(fd):
    try:
        termios.tcflush(fd, termios.TCIOFLUSH)
    finally:
        # Restoration is attempted even if stale-buffer flushing fails. Failure
        # propagates and prevents negotiation on a potentially dirty stream.
        fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack('I', termios.TIOCM_DTR))


def reclaim_both_carriers(peers, boot, evidence, usb_down, usb_up, usb_factory,
                          lan_close, guard=lambda: None):
    old_usb = peers['usb']
    try:
        guard()
        disconnect_reclaim(old_usb, peers['plain_lan'], boot, usb_down, evidence)
    finally:
        # Always restore DTR, including an uncertain claim/disconnect observation.
        usb_up()
    fresh_usb = usb_factory()
    require(fresh_usb.session != old_usb.session, 'USB reconnect requires fresh session')
    negotiate(fresh_usb, boot)
    status(fresh_usb, boot, unowned=True)
    peers['usb'] = fresh_usb
    guard()
    disconnect_reclaim(peers['plain_lan'], fresh_usb, boot, lan_close, evidence)
    guard()
    status(fresh_usb, boot, unowned=True)


def composition_guard(info, source, boot, address, initial=False):
    require(info.get('device_id') == DEVICE, 'wrong B identity')
    resource_health(info)
    state = info['status']
    require(state['engine'] == ENGINE and state['output_active'] is False and
            state['enabled'] is False and state['state'] in
            ('empty', 'loaded', 'armed', 'running', 'aborted', 'complete', 'missed'),
            'inactive inhibited composition authority required')
    require(info['access_state'] in ('healthy', 'erased') and
            state['storage_healthy'] is True and not info.get('bootstrap_reset_pending', False),
            'healthy composition storage required')
    require(info['revision'] == source[:12] and state['boot_id'] == boot and
            info['lan_wtp_mode'] == 'plain' and info['network']['ipv4'] == address,
            'INFO exact image/mode/address/boot')
    if initial:
        require(state['state'] == 'empty', 'initial INFO empty required; authority via LAN STATUS')
    return info


def read_info(fd):
    deadline = time.monotonic()+5
    os.set_blocking(fd, False)
    wire = b'INFO\n'
    while wire:
        remaining = deadline-time.monotonic()
        require(remaining > 0, 'INFO write deadline')
        if select.select([], [fd], [], remaining)[1]:
            count = os.write(fd, wire)
            require(count > 0, 'INFO write closed')
            wire = wire[count:]
    raw = bytearray()
    while time.monotonic() < deadline:
        if select.select([fd], [], [], max(0, deadline-time.monotonic()))[0]:
            chunk = os.read(fd, 1)
            require(chunk, 'INFO closed')
            raw.extend(chunk)
            require(len(raw) <= 65536, 'INFO bounded line')
            if chunk == b'\n':
                if raw.strip():
                    return strict(bytes(raw))
                raw.clear()
    raise TimeoutError('INFO read deadline')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'artifact-root', 'evidence'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--role', choices=['consumer', 'restore'], required=True)
    parser.add_argument('--address', required=True)
    parser.add_argument('--boot-id', required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    manifest = read_json(args.manifest)
    verify(manifest, args.artifact_root)
    candidate = next(c for c in manifest['candidates'] if c['role'] == args.role)
    require(candidate['target'] == 'WsprryPico' and candidate['lan_mode'] == 'plain' and
            candidate['fault_stage'] == 0, 'ordinary inhibited plain candidate')
    require(re.fullmatch(r'[0-9a-f]{32}', args.boot_id) is not None, 'exact boot id')
    ip = ipaddress.IPv4Address(args.address)
    require(ip.is_private and not ip.is_loopback and not ip.is_multicast and not ip.is_unspecified,
            'explicit private station IPv4')
    if not args.run:
        print(json.dumps(dict(status='PREPARED_NO_HARDWARE', max_jobs=3, rf_jobs=0,
                              source_commit=manifest['source_commit'])))
        return
    run_device(candidate, manifest, args.address, args.boot_id, args.evidence)


def run_device(candidate, manifest, address, boot_id, evidence_path, observe_info=None):
    """Hardware API: caller authorizes run and verifies/programs/reads back image.

    CLI callers verify all manifest artifacts first. Remote parent dispatch may
    call this only after that same proof; this function does not flash images.
    observe_info, if supplied, must return a fresh actual INFO dict through the
    parent shared console mutex with bounded I/O, never a cached observation.
    """
    require(candidate in manifest['candidates'], 'candidate manifest binding')
    require(candidate['role'] in ('consumer', 'restore') and
            candidate['target'] == 'WsprryPico' and candidate['lan_mode'] == 'plain' and
            candidate['fault_stage'] == 0, 'ordinary inhibited plain candidate')
    require(re.fullmatch(r'[0-9a-f]{40}', manifest['source_commit']) is not None,
            'exact source commit')
    require(re.fullmatch(r'[0-9a-f]{64}', candidate['uf2']['sha256']) is not None,
            'exact UF2 digest')
    require(re.fullmatch(r'[0-9a-f]{32}', boot_id) is not None, 'exact boot id')
    ip = ipaddress.IPv4Address(address)
    require(ip.is_private and not ip.is_loopback and not ip.is_multicast and not ip.is_unspecified,
            'explicit private station IPv4')
    os.umask(0o077)
    from check_usb_target import port
    console = '/dev/serial/by-id/usb-WsprryPi_WsprryPico_'+SERIAL+'-if00'
    wtp = console[:-2]+'02'
    evidence = Evidence(evidence_path)
    def guard(initial=False):
        if observe_info is None:
            with port(console) as console_fd:
                fcntl.flock(console_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                observed = read_info(console_fd)
        else:
            # Parent supplies a fresh bounded raw-serial observer under the same
            # mutex as the independent soak collector; identity checks stay here.
            observed = observe_info()
        require(observed.get('provisioning_source') == 'consumer_preclock',
                'supported consumer source5 required')
        info = composition_guard(observed, manifest['source_commit'],
                                 boot_id, address, initial)
        evidence.record('INFO', value=info, image_sha256=candidate['uf2']['sha256'])
        return info
    with contextlib.ExitStack() as stack:
        lock_fd = os.open('/tmp/wsprrypico-consumer-composition-'+SERIAL+'.lock',
                          os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        lock = stack.enter_context(os.fdopen(lock_fd, 'a'))
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            guard(initial=True)
            sock = stack.enter_context(socket.create_connection((address, 31417), timeout=5))
            sock.setblocking(False)
            peer = Peer(sock.fileno(), 'plain_lan', evidence)
            negotiate(peer, boot_id)
            guard()
            peer.frame_boundary()
            status(peer, boot_id, unowned=True)
            jobs = run_lan_directed(peer, boot_id, evidence, address, guard)
            def reconnect(deadline):
                remaining=deadline-time.monotonic()
                require(remaining>0,'reconnect deadline')
                fresh_socket=socket.create_connection((address,31417),timeout=min(5,remaining))
                fresh_socket.setblocking(False)
                return Peer(fresh_socket.fileno(),'plain_lan',evidence),fresh_socket.close
            lan_disconnect_reconnect(peer,boot_id,sock.close,reconnect,evidence)
            guard(initial=True)
            evidence.record('driver_complete', jobs=jobs, rf_jobs=0,
                            physical_acceptance=False, resource_soak_pending=True,
                            coverage='PLAIN_LAN_CONTROL_USB_INFO', usb_wtp_supported=False)
        except BaseException as error:
            evidence.record('driver_failed', error=type(error).__name__+': '+str(error))
            raise
        finally:
            evidence.close()


if __name__ == '__main__':
    main()
