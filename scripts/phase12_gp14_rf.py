#!/usr/bin/env python3
"""Opt-in, B-only, one finite physical GP14/RF acquisition per invocation.

No flashing, station Save, clock setting, synthetic GPIO or automatic retry.
Each next run requires passing RF assessment or a bound reviewed nonqualifying resolution.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time
import types
import uuid

from inhibited_network_acceptance import Evidence, Peer, require
from phase11_5_inventory import exclusive_port
from rf_wtp import read_line, write_all

SERIAL = 'CDDBF8767C506C07'
DEVICE = '29f20b7342051ef947aa56cb9d4fab42'
CASES = ('active_stop', 'armed_stop', 'active_busy', 'armed_busy', 'quick_reset', 'long_ap')
CONTINUATION_CASES = ('quick_reset', 'long_ap')
SOURCE_REVISION = '3e1337074003616c23d9b8749e728c99c71738c6'
IMAGE_SHA256 = '658605e4bc66094849be71ee6bb59c91d335d6e1fb7fe99ad54d96b27cf09aa5'
SETTINGS = dict(format='CF32', sample_rate_hz=250000, bandwidth_hz=200000,
                center_frequency_hz=3550000, gain_db=20, channel=0, agc=False, bias_tee=False)
HELPER_SHA256 = 'b98de116d696846b88eea1b3ad3f1b2a471052fa2ca440f4234fec7087dc5a03'
ATTEMPT_LIMIT, JOB_LIMIT = 17, 12
CHECKPOINT_SHA256 = '64256f87d374a459518f876e14b46ce0d8f61d756c05661ab8c27ae01e0b2106'
READY_MAX_AGE_S = 300


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def job_value(job_id):
    return dict(job_id=job_id, profile='rf-events/1', mode='tone',
                total_duration_ns='20000000000', allow_frequency_adjustment=True,
                events=[dict(offset_ns='0', duration_ns='20000000000', rf_on=True,
                             frequency_nhz='3570100000000000')])


def validate_packet(packet, *, verify_files=True):
    require(packet['schema'] == 'phase12-gp14-rf-v1', 'packet schema')
    require(packet['serial'] == SERIAL and packet['device_id'] == DEVICE, 'B-only target')
    require(re.fullmatch('[0-9a-f]{40}', packet['source_revision']) is not None and
            packet['revision'] == packet['source_revision'][:12], 'clean source identity')
    require(packet['source_revision'] == SOURCE_REVISION and packet['uf2_sha256'] == IMAGE_SHA256,
            'reviewed continuation image required; do not use the stale original packet')
    require(packet['address'] == '192.168.1.53' and packet['port'] == 31417, 'recorded B LAN')
    require(packet['engine'] == 'pio-dma-gp2' and packet['system_clock_hz'] == 138000000,
            'reviewed RF profile')
    require(packet['attenuation_db'] == 60 and packet['receiver_serial'] == '2404058C60',
            'recorded conducted receiver path')
    if verify_files:
        require(digest(packet['uf2']) == packet['uf2_sha256'], 'retained image hash')
        require(digest(packet['capture_helper']) == HELPER_SHA256, 'retained capture helper hash')


def campaign_budget(campaign):
    """The immutable fifteen-attempt checkpoint prevents a partial mirror/reset."""
    checkpoint = campaign / 'ledger-after-quick-reset-15.json'
    require(digest(checkpoint) == CHECKPOINT_SHA256, 'original campaign checkpoint changed/missing')
    ledger = json.loads(checkpoint.read_text())
    require(ledger['attempts'] == 15 and ledger['charged_jobs'] == 10 and
            len(ledger['rows']) == 15, 'original campaign accounting invalid')
    previous = sorted(campaign.glob('run-*/attempt.json'))
    require(all((root/'attempt.json').is_file() for root in campaign.glob('run-*')),
            'incomplete acquisition record')
    for row in ledger['rows']:
        require(re.fullmatch(r'run-[0-9a-f]{32}', row['run']) is not None, 'checkpoint run path')
        root = campaign / row['run']
        require(digest(root/'attempt.json') == row['attempt_sha256'] and
                digest(root/'analysis.json') == row['analysis_sha256'],
                'historical campaign record changed/missing')
    charges = [json.loads(path.read_text())['charged_jobs'] for path in previous]
    require(all(type(charge) is int and charge in (0, 1) for charge in charges), 'RF charge invalid')
    require(len(previous) < ATTEMPT_LIMIT and sum(charges) < JOB_LIMIT,
            'approved cumulative acquisition/RF budget exhausted')
    return previous, sum(charges)


@contextmanager
def campaign_lock(campaign):
    """Serialize accounting through receiver finalization; never wait for another run."""
    fd = os.open(campaign/'.rf-acquisition.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def ready_binding(campaign, case, packet_bytes, previous, charges):
    return dict(schema='phase12-gp14-ready-v1', campaign=str(campaign.resolve()),
                case=case, serial=SERIAL, device_id=DEVICE,
                packet_sha256=hashlib.sha256(packet_bytes).hexdigest(),
                attempts=len(previous), charged_jobs=charges,
                attempt_limit=ATTEMPT_LIMIT, job_limit=JOB_LIMIT,
                runner_sha256=digest(__file__))


def acknowledge_ready(campaign, case, packet_bytes, previous, charges):
    """Call only AFTER the human's fresh Ready, never while parking preparation."""
    value = ready_binding(campaign, case, packet_bytes, previous, charges)
    value.update(acknowledged_utc_s=int(time.time()), ready_id=uuid.uuid4().hex)
    path = campaign / ('ready-' + value['ready_id'] + '.json')
    with path.open('x') as out:
        os.chmod(path, 0o600)
        out.write(json.dumps(value, indent=2) + '\n')
    return path


def consume_ready(path, campaign, case, packet_bytes, previous, charges, *, now=None):
    require(path is not None, 'fresh operator Ready acknowledgement required')
    path = Path(path)
    require(not path.is_symlink() and path.parent.resolve() == campaign.resolve(),
            'Ready record must belong to this campaign')
    value = json.loads(path.read_text())
    expected = ready_binding(campaign, case, packet_bytes, previous, charges)
    require(all(type(value.get(key)) is type(item) and value.get(key) == item
                for key, item in expected.items()), 'stale/wrong Ready binding')
    require(re.fullmatch('[0-9a-f]{32}', value.get('ready_id', '')) is not None and
            path.name == 'ready-' + value['ready_id'] + '.json', 'Ready record identity')
    stamp = value.get('acknowledged_utc_s')
    require(type(stamp) is int and 0 <= (time.time() if now is None else now) - stamp <= READY_MAX_AGE_S,
            'Ready acknowledgement expired/future; park and ask again')
    # Consume before USB/receiver access. Even a failed start cannot reuse Ready.
    fd = os.open(str(path) + '.consumed', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as out:
        out.write(digest(path) + '\n')
    return value


def console(text='INFO', deadline_s=5):
    path = '/dev/serial/by-id/usb-WsprryPi_WsprryPico_' + SERIAL + '-if00'
    try:
        with exclusive_port(path) as fd:
            write_all(fd, (text + '\n').encode(), time.monotonic() + 2)
            result = read_line(fd, time.monotonic() + deadline_s)
    except ValueError as error:
        # fuser can see the old CDC node disappear before os.open during an
        # expected reset. Retry only a demonstrably absent path; an occupied
        # existing endpoint or failed ownership check must still stop the run.
        if str(error) == 'Endpoint occupied or ownership check unavailable' and not Path(path).exists():
            raise FileNotFoundError(path) from error
        raise
    require(result.get('ok') is True, 'Console command refused: ' + str(result.get('error', 'unspecified')))
    return result


def check_info(info, packet, boot=None):
    require(info['device_id'] == DEVICE and info['revision'] == packet['revision'], 'USB identity')
    require(info['system_clock_hz'] == 138000000 and
            info['status']['engine'] == 'pio-dma-gp2', 'physical engine/clock')
    require(info.get('gp14_rf_acceptance') is True and int(info['gp14_samples']) > 0,
            'explicit acceptance variant')
    require(not info['recovery_boot'] and not info['gp14_capture_fault'], 'recovery/capture fault')
    for key in ('fault_stage', 'fault_hash', 'fault_pc', 'fault_status', 'provisioning_fault',
                'core0_stack_fault_status', 'core1_stack_fault_status', 'dma_errors'):
        require(info.get(key) == 0, 'target fault: ' + key)
    require(info['core0_stack_guard_valid'] == 1 and info['core1_stack_guard_valid'] == 1,
            'stack guards')
    require(info['allocator_failures'] == '0' and info['status']['storage_healthy'], 'heap/storage')
    require(info['status']['enabled'] is False, 'standalone auto scheduling must be disabled')
    if boot is not None:
        require(info['status']['boot_id'] == boot, 'unexpected reboot')


def cleanup_owned(peer, boot, job_id, owner):
    status = peer.request('STATUS', {})
    require(status['boot_id'] == boot, 'cleanup boot mismatch')
    if status['owner_id'] is None:
        require(status['output_active'] is False, 'unowned output during cleanup')
        return
    require(status['owner_id'] == owner, 'cleanup foreign owner')
    if status['job_id'] == job_id:
        if status['state'] in ('loaded', 'armed', 'running'):
            peer.request('ABORT', dict(job_id=job_id))
            status = peer.request('STATUS', {})
        require(status['boot_id'] == boot and status['output_active'] is False and
                status['state'] in ('aborted', 'complete', 'missed'), 'cleanup terminal unconfirmed')
        if status['owner_id'] is None:
            return
        require(status['owner_id'] == owner, 'cleanup owner changed')
    else:
        require(status['job_id'] is None and status['state'] == 'empty' and
                status['output_active'] is False, 'cleanup foreign job')
    peer.request('RELEASE', {})
    status = peer.request('STATUS', {})
    require(status['boot_id'] == boot and status['owner_id'] is None and
            status['job_id'] is None and status['state'] == 'empty' and
            status['output_active'] is False, 'cleanup unconfirmed')


def _review_no_input_completion(path, case):
    """Resolve an operator timing miss without promoting it to RF acceptance."""
    attempt = json.loads(path.read_text())
    require(attempt['case'] == case and attempt['charged_jobs'] == 1 and
            attempt['status'] == 'FAILED_STOP_CAMPAIGN' and
            attempt.get('error') == 'RuntimeError: physical action timeout' and
            attempt.get('cleanup_verified') is True, 'not a resolved no-input timeout')
    events_path = path.with_name('events.jsonl')
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    observations = [event['value'] for event in events
                    if event['kind'] in ('before_action_info', 'action_info')]
    require(observations and any(info['status']['output_active'] for info in observations),
            'no positive launch observation')
    for info in observations:
        require(info['status']['boot_id'] == attempt['boot_id'] and
                info['gp14_held'] is False and info['gp14_capture_fault'] is False and
                info['gp14_stop_events'] == 0 and info['gp14_reset_events'] == 0 and
                info['rf_safety_inhibited'] is False and
                type(info['rf_safety_input_fault']) is int and info['rf_safety_input_fault'] == 0 and
                int(info['rf_safety_requested_ns']) == 0, 'input or safety fault was observed')
    responses = [event['value'] for event in events if event['kind'] == 'received' and
                 event['value'].get('type') == 'response' and
                 event['value'].get('op') == 'STATUS' and event['value'].get('ok') is True]
    require(responses, 'cleanup status missing')
    final = responses[-1]['body']
    require(final['boot_id'] == attempt['boot_id'] and final['state'] == 'empty' and
            final['owner_id'] is None and final['job_id'] is None and
            final['output_active'] is False and
            any(record['job_id'] == attempt['job_id'] and record['state'] == 'complete' and
                record['output_active'] is False for record in final['terminal_records']),
            'finite completion and inactive cleanup unconfirmed')
    return dict(run=path.parent.name, attempt_sha256=digest(path),
                events_sha256=digest(events_path), independent_rf_pass=False,
                reason='Explicit operator retry after reviewed no-input finite completion')


def review_no_input_retry(path):
    return _review_no_input_completion(path, 'active_stop')


def review_quick_reset_no_input(path):
    """Resolve only historical trial 15; its RF qualification stays false."""
    require(path.parent.name == 'run-986b41d58b2e46569d7aa24ae2dd84e4', 'not historical trial 15')
    review = _review_no_input_completion(path, 'quick_reset')
    packet_path, meta_path = path.with_name('packet.json'), path.with_name('capture.json')
    packet = json.loads(packet_path.read_text())
    validate_packet(packet, verify_files=False)
    attempt = json.loads(path.read_text())
    require(attempt['packet_sha256'] == digest(packet_path) and
            attempt['duration_ns'] == '20000000000' and
            attempt['receiver_completion_after_target_failure'] == 0, 'finite capture/packet binding')
    events = [json.loads(line) for line in path.with_name('events.jsonl').read_text().splitlines()]
    initial = [event['value'] for event in events if event['kind'] == 'initial_info']
    require(len(initial) == 1, 'initial trial identity missing')
    keys = ('saved_consumer_profile', 'access_state', 'access_generation',
            'access_default_password', 'provisioning_source', 'provisioning_generation')
    for event in events:
        if event['kind'] not in ('initial_info', 'before_action_info', 'action_info'):
            continue
        info = event['value']
        check_info(info, packet, attempt['boot_id'])
        require(info['gp14_held'] is False and info['gp14_stop_events'] == 0 and
                info['gp14_reset_events'] == 0 and info['gp14_ap_events'] == 0 and
                info['rf_safety_inhibited'] is False and
                type(info['rf_safety_input_fault']) is int and info['rf_safety_input_fault'] == 0 and
                int(info['rf_safety_requested_ns']) == 0 and
                all(info[key] == initial[0][key] for key in keys),
                'AP event/settings drift observed')
    # INFO's standalone status does not contain job_id. Bind the actual WTP
    # LOAD/ARM responses and terminal history instead of inventing an INFO field.
    for operation in ('LOAD', 'ARM'):
        replies = [event['value'] for event in events if event['kind'] == 'received' and
                   event['value'].get('type') == 'response' and event['value'].get('op') == operation]
        require(len(replies) == 1 and replies[0].get('ok') is True and
                replies[0]['body']['job_id'] == attempt['job_id'], 'foreign/ambiguous WTP admission')
    meta = json.loads(meta_path.read_text())
    require(meta['actual_settings'] == SETTINGS and
            meta['resolved_device'] == dict(driver='sdrplay', serial='2404058C60') and
            meta['overflow_count'] == 0 and meta['timeout_count'] == 0 and
            meta['clipping']['sample_count'] == 0 and meta['cleanup']['outcome'] == 'verified' and
            meta['primary_outcome'] == 'success' and meta['output']['complete'] is True and
            meta['retained_sample_count'] == 10000000 and meta['output']['size_bytes'] == 80000000 and
            path.with_name('capture.cf32').stat().st_size == 80000000 and
            digest(path.with_name('capture.cf32')) == meta['output']['sha256'], 'capture health/integrity')
    return dict(attempt_sha256=review['attempt_sha256'], events_sha256=review['events_sha256'],
                packet_sha256=digest(packet_path), capture_sha256=meta['output']['sha256'],
                capture_metadata_sha256=digest(meta_path), independent_rf_pass=False)


def review_quick_reset_mismatch(path):
    """Close an observed normal reset operationally; RF acceptance stays false."""
    attempt = json.loads(path.read_text())
    require(attempt['case'] == 'active_stop' and attempt['charged_jobs'] == 1 and
            attempt['status'] == 'FAILED_STOP_CAMPAIGN' and
            attempt.get('error') == 'ConnectionError: serial device closed',
            'not the reviewed unexpected quick-reset acquisition')
    info_path = path.with_name('post-failure-info.json')
    info = json.loads(info_path.read_text())
    events_path = path.with_name('events.jsonl')
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    initial = [event['value'] for event in events if event['kind'] == 'initial_info']
    require(len(initial) == 1 and initial[0]['device_id'] == DEVICE and
            initial[0]['revision'] == info['revision'] and
            initial[0]['status']['boot_id'] == attempt['boot_id'] and
            info['system_clock_hz'] == 138000000 and info['status']['engine'] == 'pio-dma-gp2' and
            any(event['kind'] in ('before_action_info', 'action_info') and
                event['value']['status']['boot_id'] == attempt['boot_id'] and
                event['value']['status']['output_active'] is True for event in events),
            'reset/launch image identity unconfirmed')
    require(info['device_id'] == DEVICE and info.get('gp14_rf_acceptance') is True and
            info['status']['boot_id'] != attempt['boot_id'] and
            info['gp14_prior_reset'] is True and 0 < info['gp14_prior_duration_ms'] < 400 and
            info['gp14_prior_rf_decision_after_launch_us'] > 0 and
            info['status']['state'] == 'empty' and info['status']['output_active'] is False and
            info['status']['enabled'] is False and info['status']['storage_healthy'] is True and
            info['gp14_held'] is False and info['gp14_capture_fault'] is False and
            info['recovery_boot'] is False, 'normal reset and inactive readback unconfirmed')
    for key in ('fault_stage', 'fault_hash', 'fault_pc', 'fault_status', 'provisioning_fault',
                'core0_stack_fault_status', 'core1_stack_fault_status', 'dma_errors'):
        require(info[key] == 0, 'reset readback fault: ' + key)
    require(info['core0_stack_guard_valid'] == 1 and info['core1_stack_guard_valid'] == 1 and
            info['allocator_failures'] == '0', 'reset resource health')
    return dict(attempt_sha256=digest(path),
                events_sha256=digest(events_path),
                post_failure_info_sha256=digest(info_path), independent_rf_pass=False)


def finish_capture(capture, deadline):
    """Retain finite receiver completion even when a target action fails."""
    try:
        return capture.wait(timeout=max(0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        capture.terminate()
        try:
            capture.wait(timeout=5)
        except subprocess.TimeoutExpired:
            capture.kill()
            capture.wait(timeout=5)
        return None


def review_legacy_cue_failure(path):
    """Reconcile the historical consumer-guard denial; do not accept cutoff."""
    attempt = json.loads(path.read_text())
    require(attempt['case'] == 'active_stop' and attempt['charged_jobs'] == 1 and
            attempt['status'] == 'FAILED_STOP_CAMPAIGN' and
            attempt.get('error') == 'RuntimeError: Console command refused' and
            attempt.get('cleanup_verified') is True, 'not the reconciled legacy cue failure')
    events_path = path.with_name('events.jsonl')
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    initial = [event['value'] for event in events if event['kind'] == 'initial_info']
    require(len(initial) == 1 and initial[0]['device_id'] == DEVICE and
            initial[0]['revision'] == '62ae4c2c2567' and
            initial[0]['provisioning_source'] == 'consumer_preclock' and
            initial[0]['status']['boot_id'] == attempt['boot_id'] and
            not any(event['kind'] in ('action_info', 'physical_led_cue') for event in events),
            'legacy denial image/action mismatch')
    aborts = [event['value'] for event in events if event['kind'] == 'request' and
              event['value'].get('op') == 'ABORT']
    require(len(aborts) == 1 and aborts[0]['body'] == dict(job_id=attempt['job_id']),
            'same-job abort unconfirmed')
    statuses = [event['value']['body'] for event in events if event['kind'] == 'received' and
                event['value'].get('type') == 'response' and
                event['value'].get('op') == 'STATUS' and event['value'].get('ok') is True]
    require(statuses, 'final status missing')
    final = statuses[-1]
    require(final['boot_id'] == attempt['boot_id'] and final['state'] == 'empty' and
            final['owner_id'] is None and final['job_id'] is None and
            final['output_active'] is False and
            any(record['job_id'] == attempt['job_id'] and record['state'] == 'aborted' and
                record['output_active'] is False for record in final['terminal_records']),
            'inactive aborted job and release unconfirmed')
    return dict(attempt_sha256=digest(path), events_sha256=digest(events_path),
                independent_rf_pass=False)


def wait_button_reset(packet, initial, evidence, *, read=console, now=time.monotonic,
                      pause=time.sleep):
    """No output job is created until an operator's idle quick tap starts a new boot."""
    old_boot = initial['status']['boot_id']
    def require_idle(info):
        stopped = (info['status']['boot_id'] == old_boot and
                   info['status']['state'] == 'aborted' and
                   info['gp14_output_inhibited'] is True and
                   info['rf_safety_inhibited'] is True)
        require(info['status']['output_active'] is False and
                (info['status']['state'] == 'empty' or stopped),
                'ready signal requires empty or GP14-inhibited aborted B')
    require_idle(initial)
    end = now() + 600
    print('WAITING: quick-tap B GP14, release, then watch for triple LED flashes', flush=True)
    while now() < end:
        try:
            info = read()
        except (OSError, ConnectionError, TimeoutError):
            pause(.1)
            continue
        check_info(info, packet)
        require_idle(info)
        if info['status']['boot_id'] != old_boot:
            require(info['gp14_prior_reset'] is True and 0 < info['gp14_prior_duration_ms'] < 400,
                    'operator quick-reset marker missing')
            require(info['gp14_held'] is False and info['gp14_output_inhibited'] is False and
                    info['rf_safety_inhibited'] is False, 'ready tap did not finish released')
            if info['status']['clock_state'] == 'synchronized' and \
                    info['network']['ipv4'] == packet['address']:
                evidence.record('physical_start_info', info)
                return info
        pause(.2)
    raise RuntimeError('physical ready signal timeout; no RF job submitted')


def review_campaign(campaign, previous, retry_no_input_run=None):
    retry_review = None
    for path in previous:
        if path.parent.name == retry_no_input_run:
            retry_review = review_no_input_retry(path)
            continue
        assessment = path.with_name('analysis.json')
        require(assessment.exists(), 'preceding independent RF assessment pending')
        result = json.loads(assessment.read_text())
        if result.get('nonqualifying_no_input_timeout') is True:
            review = review_quick_reset_no_input(path)
            require(result.get('schema') == 'phase12-gp14-nonqualifying-v1' and
                    result.get('case') == 'quick_reset' and
                    all(result.get(key) == value for key, value in review.items()),
                    'historical quick-reset resolution unbound')
            continue
        if result.get('resolved_no_input_timeout') is True:
            review = review_no_input_retry(path)
            require(all(result.get(key) == value for key, value in review.items()),
                    'no-input resolution unbound')
            continue
        if result.get('resolved_wrong_gesture') is True:
            review = review_quick_reset_mismatch(path)
            require(all(result.get(key) == value for key, value in review.items()),
                    'wrong-gesture resolution unbound')
            continue
        if result.get('resolved_legacy_cue_failure') is True:
            review = review_legacy_cue_failure(path)
            require(all(result.get(key) == value for key, value in review.items()),
                    'legacy cue resolution unbound')
            continue
        no_rf = (result.get('resolved_without_rf') is True and
                 json.loads(path.read_text())['charged_jobs'] == 0)
        require((result.get('independent_rf_pass') is True or no_rf) and
                result.get('attempt_sha256') == digest(path), 'preceding RF assessment failed/unbound')
    require(retry_no_input_run is None or retry_review is not None, 'retry run not found')
    return retry_review


def acquire(packet, case, campaign, retry_no_input_run=None, wait_for_button=False, led_cue=False,
            *, ready_file=None, packet_file=None):
    require(ready_file is not None, 'fresh operator Ready acknowledgement required')
    with campaign_lock(campaign):
        return _acquire_locked(packet, case, campaign, retry_no_input_run, wait_for_button, led_cue,
                               ready_file=ready_file, packet_file=packet_file)


def _acquire_locked(packet, case, campaign, retry_no_input_run=None, wait_for_button=False, led_cue=False,
                    *, ready_file=None, packet_file=None):
    require(case in CONTINUATION_CASES and led_cue and not wait_for_button and
            retry_no_input_run is None, 'only the two reviewed LED-cued continuation rows are authorized')
    previous, charges = campaign_budget(campaign)
    retry_review = review_campaign(campaign, previous, retry_no_input_run)
    packet_file = packet_file or campaign/'packet.json'
    require(packet_file.parent.resolve() == campaign.resolve(), 'packet must belong to this campaign')
    packet_bytes = packet_file.read_bytes()
    require(json.loads(packet_bytes) == packet, 'packet changed after validation')
    ready = consume_ready(ready_file, campaign, case, packet_bytes, previous, charges)
    root = campaign / ('run-' + uuid.uuid4().hex)
    evidence = Evidence(root)
    (root/'packet.json').write_bytes(packet_bytes)
    attempt = dict(case=case, packet_sha256=digest(root/'packet.json'), status='STARTING',
                   charged_jobs=0, duration_ns='20000000000', independent_rf_pass=False,
                   operator_ready=ready)
    if retry_review:
        attempt['reviewed_no_input_retry'] = retry_review
    def save():
        (root/'attempt.json').write_text(json.dumps(attempt, indent=2) + '\n')
    save()
    peer = None
    capture = None
    capture_deadline = None
    owner = uuid.uuid4().hex
    job = job_value(uuid.uuid4().hex)
    boot = None
    claim_pending = False
    try:
        initial = console()
        check_info(initial, packet)
        if wait_for_button:
            require(initial.get('gp14_rf_cue_supported') is True, 'physical cue unsupported by image')
            initial = wait_button_reset(packet, initial, evidence)
        require(not initial['gp14_held'] and not initial['gp14_output_inhibited'] and
                not initial['rf_safety_inhibited'] and initial['gp14_rf_busy_used'] == 0,
                'new released-input boot required')
        boot = initial['status']['boot_id']
        evidence.record('initial_info', initial)
        if wait_for_button or led_cue:
            require(initial.get('gp14_rf_cue_supported') is True, 'physical cue unsupported by image')
            cue_ready = console('GP14 RF CUE ' + DEVICE + ' READY')
            require(cue_ready.get('ready') is True, 'physical cue readiness unconfirmed')
            evidence.record('physical_led_ready', cue_ready)
        peer = Peer(types.SimpleNamespace(boot_id=boot), evidence)
        peer.stream = socket.create_connection((packet['address'], packet['port']), timeout=5)
        hello = peer.request('HELLO', dict(versions=['WTP/1'], client_name='GP14-RF-acceptance',
                                         client_version='1'))
        require(hello['device_id'] == DEVICE and hello['boot_id'] == boot, 'LAN/USB identity')
        caps = peer.request('CAPS', {})
        require(caps['engine'] == 'pio-dma-gp2', 'LAN engine')
        status = peer.request('STATUS', {})
        require(status['boot_id'] == boot and status['state'] == 'empty' and
                status['owner_id'] is None and status['job_id'] is None and
                status['output_active'] is False, 'initial WTP authority')
        argv = [packet['capture_helper'], '--enable-physical-sdr', 'sdrplay', '2404058C60',
                '3550000', '10000000', '20', '250000', '200000', '0', 'false', 'false',
                '100000', '55', str(root/'capture.cf32'), str(root/'capture.json'), root.name]
        evidence.record('capture_argv', argv)
        with (root/'receiver.log').open('w') as receiver_log:
            capture = subprocess.Popen(argv, stdout=receiver_log, stderr=subprocess.STDOUT)
        capture_deadline = time.monotonic() + 55
        ready_end = time.monotonic() + 8
        while not (root/'capture.cf32.incomplete').exists() or \
                (root/'capture.cf32.incomplete').stat().st_size < 65536:
            require(time.monotonic() < ready_end and capture.poll() is None, 'receiver readiness')
            time.sleep(.05)
        attempt.update(boot_id=boot, job_id=job['job_id'], owner_id=owner)
        save()
        claim_pending = True
        peer.request('CLAIM', dict(owner_id=owner, lease_ms=60000))
        loaded = peer.request('LOAD', job)
        require(loaded['job_id'] == job['job_id'] and len(loaded['adjustments']) == 1,
                'complete frequency realization')
        adjustment = loaded['adjustments'][0]
        require(adjustment['requested_frequency_nhz'] == '3570100000000000' and
                abs(int(adjustment['realized_frequency_nhz']) - 3570100000000000) <= 50000000000,
                'realization outside conducted tone window')
        clock = peer.request('GET_CLOCK', {})
        require(clock['state'] == 'synchronized' and clock['leap'] == 'normal' and
                int(clock['uncertainty_ns']) <= 500000000, 'clock admission')
        lead = 20000000000 if case.startswith('armed_') else 5000000000
        target = (int(clock['utc_now_ns']) + lead + 999) // 1000 * 1000
        attempt.update(boot_id=boot, job_id=job['job_id'], owner_id=owner, charged_jobs=1,
                       start_utc_ns=str(target), status='ARM_PENDING')
        save()  # Charge an ambiguous ARM before writing; never retry it.
        peer.request('ARM', dict(job_id=job['job_id'], start_utc_ns=str(target),
                                 max_start_uncertainty_ns='500000000'))
        action_end = time.monotonic() + 27
        while True:
            info = console()
            check_info(info, packet, boot)
            evidence.record('before_action_info', info)
            if case.startswith('armed_') or info['status']['output_active']:
                break
            require(time.monotonic() < action_end, 'finite launch timeout')
            time.sleep(.05)
        print('CONTACT NOW: ' + case + ' on B', flush=True)
        if wait_for_button or led_cue:
            cue = console('GP14 RF CUE ' + DEVICE + ' ' + uuid.uuid4().hex)
            require(cue.get('cue') is True, 'physical cue activation unconfirmed')
            evidence.record('physical_led_cue', cue)
        busy = None
        final = None
        while time.monotonic() < action_end:
            try:
                info = console()
            except (OSError, ConnectionError, TimeoutError):
                if case != 'quick_reset':
                    raise
                time.sleep(.1)
                continue
            check_info(info, packet, None if case == 'quick_reset' else boot)
            evidence.record('action_info', info)
            if case.endswith('_busy') and info['gp14_held'] and not busy:
                require(not info['rf_safety_inhibited'], 'stop preceded busy stimulus')
                busy = console('GP14 RF BUSY ' + DEVICE, 7)
                evidence.record('busy', busy)
                continue
            if case == 'quick_reset':
                if info['status']['boot_id'] == boot:
                    continue
                require(info['gp14_prior_reset'] and 0 < info['gp14_prior_duration_ms'] < 400 and
                        info['gp14_prior_rf_decision_after_launch_us'] > 0,
                        'selected quick-release reset evidence')
                final = info
                break
            if info['gp14_stop_verified'] and not info['gp14_held']:
                if case == 'long_ap' and not info['gp14_softap_service_ready']:
                    time.sleep(.1)
                    continue
                final = info
                break
            time.sleep(.08)
        require(final is not None and final['status']['output_active'] is False, 'physical action timeout')
        if case != 'quick_reset':
            require(final['rf_safety_inhibited'] and not final['rf_safety_input_fault'], 'worker latch')
            requested = int(final['rf_safety_requested_ns'])
            stopped = int(final['rf_safety_stopped_ns'])
            require(0 < requested <= stopped and stopped - requested <= 50000000,
                    'worker acknowledgement exceeds decision bound')
            if case.endswith('_busy'):
                require(busy is not None and int(busy['busy_begin_us']) * 1000 < requested <= stopped <
                        int(busy['busy_end_us']) * 1000, 'cutoff outside core-0 busy interval')
            if case.startswith('armed_'):
                require(int(final['launch_epoch']) == 0, 'armed job launched')
            if case != 'long_ap':
                status = peer.request('STATUS', {})
                require(status['boot_id'] == boot and not status['output_active'] and
                        status['owner_id'] is None and status['state'] != 'failed', 'post-stop authority')
                peer.request('CLAIM', dict(owner_id=uuid.uuid4().hex, lease_ms=5000), expected_error='BUSY')
            else:
                require(final['gp14_ap_request_accepts'] == 1 and final['gp14_ap_events'] == 1,
                        'one verified AP request')
        evidence.record('final_info', final)
        attempt['final_boot_id'] = final['status']['boot_id']
        require(finish_capture(capture, capture_deadline) == 0, 'receiver capture failed')
        meta = json.loads((root/'capture.json').read_text())
        require(meta['actual_settings'] == SETTINGS and
                meta['resolved_device'] == dict(driver='sdrplay', serial='2404058C60') and
                meta['overflow_count'] == 0 and meta['timeout_count'] == 0 and
                meta['clipping']['sample_count'] == 0 and
                meta['cleanup']['outcome'] == 'verified' and meta['primary_outcome'] == 'success' and
                meta['output']['complete'] and meta['retained_sample_count'] == 10000000 and
                meta['output']['size_bytes'] == 80000000 and
                (root/'capture.cf32').stat().st_size == 80000000 and
                meta['output']['sha256'] == digest(root/'capture.cf32'), 'capture integrity/settings')
        attempt.update(status='CAPTURED_RF_ASSESSMENT_PENDING', target_checks_passed=True,
                       capture_sha256=digest(root/'capture.cf32'))
        save()
        print('CAPTURED: independent RF assessment pending; ' + str(root), flush=True)
    except BaseException as error:
        attempt.update(status='FAILED_STOP_CAMPAIGN', error=type(error).__name__ + ': ' + str(error))
        save()
        # No mutation replay. Only reconcile this connection's finite, identified job.
        if peer is not None and claim_pending:
            try:
                cleanup_owned(peer, boot, job['job_id'], owner)
                attempt['cleanup_verified'] = True
                save()
            except BaseException:
                attempt['abort_unconfirmed'] = True
                save()
        raise
    finally:
        if peer:
            peer.close()
        if capture and capture.poll() is None:
            attempt['receiver_completion_after_target_failure'] = finish_capture(capture, capture_deadline)
            save()
        evidence.file.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaign', type=Path)
    parser.add_argument('--case', choices=CONTINUATION_CASES, required=True)
    parser.add_argument('--packet-file', type=Path, help='Select the reviewed retained packet explicitly')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--run', action='store_true')
    action.add_argument('--prepare', action='store_true', help='Read-only offline checks; park for human Ready')
    action.add_argument('--acknowledge-ready', action='store_true',
                        help='Create one-use acknowledgement only after the human says Ready')
    parser.add_argument('--ready-file', type=Path, help='One-use record required by --run')
    parser.add_argument('--retry-no-input-run',
                        help='Explicit operator-authorized retry of a reviewed finite no-input timeout')
    parser.add_argument('--wait-button-reset', action='store_true',
                        help='Wait RF-inactive for an operator quick tap, then cue the action with LED flashes')
    parser.add_argument('--led-cue', action='store_true',
                        help='Cue the action on a pre-reset healthy B without waiting for a physical ready tap')
    args = parser.parse_args()
    os.umask(0o077)
    if args.run:
        require(args.ready_file is not None, '--run requires a fresh --ready-file')
    packet_file = args.packet_file or args.campaign/'packet.json'
    require(packet_file.parent.resolve() == args.campaign.resolve(), 'packet must belong to this campaign')
    packet_bytes = packet_file.read_bytes()
    packet = json.loads(packet_bytes)
    validate_packet(packet, verify_files=args.run)
    if not args.run:
        require(args.retry_no_input_run is None and not args.wait_button_reset and not args.led_cue and
                args.ready_file is None, 'physical/retry arguments are not preparation')
        previous, charges = campaign_budget(args.campaign)
        review_campaign(args.campaign, previous)
        if args.acknowledge_ready:
            print(acknowledge_ready(args.campaign, args.case, packet_bytes, previous, charges))
        else:
            print(json.dumps(dict(status='WAITING_FOR_OPERATOR_READY', case=args.case,
                                  attempts=len(previous), charged_jobs=charges,
                                  attempt_limit=ATTEMPT_LIMIT, job_limit=JOB_LIMIT,
                                  hardware_accessed=False, image_files_verified=False)))
        return
    acquire(packet, args.case, args.campaign, args.retry_no_input_run,
            args.wait_button_reset, args.led_cue, ready_file=args.ready_file, packet_file=packet_file)


if __name__ == '__main__':
    main()
