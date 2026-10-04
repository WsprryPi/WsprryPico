#!/usr/bin/env python3
"""Explicit two-job, RF-inhibited armed/running time-policy continuation."""
import copy
import hashlib
import re
import secrets
import time

from inhibited_network_acceptance import check_caps, check_clock, check_status, job_value
from phase12_composition_audit import counter
from phase12_consumer_composition import require
from phase12_recovery_device import DEVICE, resource_health, strict
from wsprrypico_ble import ClientError

BODY_SECONDS = 180
STAGE_SECONDS = (60, 75)
MAX_STATUS = 32
RUN_DURATION_NS = 20_000_000_000
END_MARGIN_NS = 1_000_000_000
CONFLICT_OFFSET_NS = 60_000_000_000


def preserved(info):
    """Compare actual saved fields, including additional config/pin projections."""
    status = info['status']
    value = {key: info[key] for key in ('provisioning_generation', 'access_generation',
                                       'saved_consumer_profile')}
    value['status'] = {key: status[key] for key in
                       ('station', 'schedules', 'watermark_utc_ns', 'expires_utc_s',
                        'schedule_base_frequency_nhz', 'configured', 'enabled')}
    for container, target in ((info, value), (status, value['status'])):
        for key in container:
            if ('pin' in key or key in ('config', 'configuration', 'saved_configuration',
                                        'saved_config', 'active_config')):
                target[key] = container[key]
    return copy.deepcopy(value)


def run(client, observe_info, source, boot, evidence, sntp_on, sntp_off,
        *, clock=time.monotonic, sleeper=time.sleep, utc=time.time_ns):
    require(client.authorized and client.expected_device_id == DEVICE and
            client.field_session and client.wtp_session and client.evidence is evidence and
            hasattr(client, 'last_response'), 'authorized exact B EvidenceClient required')
    require(re.fullmatch('[0-9a-f]{40}', source) and re.fullmatch('[0-9a-f]{32}', boot),
            'exact source/boot identity')
    require(type(client.generation) is int and client.generation >= 0,
            'client profile generation')
    # This explicit continuation never enables the isolated responder. The
    # parent restores its original standard image and trustworthy time later.
    del sntp_on
    end = clock() + BODY_SECONDS
    stage_end = end
    owner = job = None
    case = None
    sent = set()
    status_counts = {}
    charged = completed = 0
    baseline = previous_monotonic = None
    backend, timeout = client.backend, client.timeout
    primary = None

    class RecordedBackend:
        def __getattr__(self, name):
            return getattr(backend, name)

        def write(self, characteristic, value, *args, **kwargs):
            raw = bytes(value)
            evidence.record('gatt_write_attempt', characteristic=characteristic,
                            raw_hex=raw.hex(), sha256=hashlib.sha256(raw).hexdigest())
            return backend.write(characteristic, value, *args, **kwargs)

    client.backend = RecordedBackend()

    def remaining():
        left = min(end, stage_end) - clock()
        require(left > 0, 'time invalidation absolute deadline')
        return left

    def call(method, *args, **kwargs):
        client.timeout = min(timeout, 5, remaining())
        try:
            result = method(*args, **kwargs)
            remaining()
            return result
        finally:
            client.timeout = timeout

    def wtp(operation, body):
        return call(client.wtp_exchange, operation, body)

    def status(state=None, unowned=False, bind=True):
        key = case or 'setup'
        status_counts[key] = status_counts.get(key, 0) + 1
        require(status_counts[key] <= MAX_STATUS, 'time invalidation STATUS budget')
        value = call(client.wtp_status, boot)
        check_status(value, boot, owner=None if unowned or not bind else owner,
                     job=None if unowned or not bind else job, states=None if state is None else (state,),
                     unowned=unowned)
        evidence.record('authority', case=key, value=value)
        return value

    def info():
        nonlocal baseline
        remaining()
        value, raw = observe_info()
        require(isinstance(raw, bytes) and raw and strict(raw) == value, 'actual INFO wire')
        evidence.record('usb_info', raw_hex=raw.hex(), sha256=hashlib.sha256(raw).hexdigest())
        remaining()
        resource_health(value)
        require(value['device_id'] == DEVICE and value['revision'] == source[:12] and
                value['status']['boot_id'] == boot and
                value['status']['engine'] == 'inhibited-standalone-simulator' and
                value['status']['enabled'] is False and value['status']['output_active'] is False and
                value['status']['storage_healthy'] is True and value['access_state'] == 'healthy' and
                value['provisioning_source'] == 'provisioned' and
                counter(value['provisioning_generation'], 'profile generation') == client.generation,
                'B source boot profile storage disabled output')
        projection = preserved(value)
        if baseline is None:
            baseline = projection
        require(projection == baseline, 'time stimulus changed saved settings/generation/watermark')
        return value

    def sample():
        nonlocal previous_monotonic
        value = wtp('GET_CLOCK', {})
        for key in ('utc_now_ns', 'monotonic_now_ns', 'uncertainty_ns', 'sync_age_ns'):
            counter(value[key], key)
        now = counter(value['monotonic_now_ns'], 'clock monotonic')
        require(previous_monotonic is None or now >= previous_monotonic,
                'time invalidation clock monotonic regression')
        previous_monotonic = now
        evidence.record('clock', value=value)
        return value

    def field():
        value = call(client.field_status)
        require(type(value['time_disagreement']) is bool, 'typed field disagreement')
        evidence.record('field_status', value=value)
        return value

    def submit(offset, expected, before=None):
        nonce = secrets.token_hex(16)
        challenge = call(client._field, 'time_challenge', nonce=nonce)
        require(challenge['nonce'] == nonce, 'field challenge nonce')
        sampled = utc() + offset
        require(type(sampled) is int and sampled >= 0, 'UTC sample')
        client.last_response = None
        evidence.record('field_submission_attempt', offset_ns=offset, expected=expected)
        try:
            response = call(client._field, 'time_submit', without_response=True,
                            nonce=nonce, utc_ns=str(sampled))
        except ClientError:
            response = client.last_response
            require(response and response.get('ok') is False and response.get('error') == expected,
                    'field exact rejection')
            remaining()
        else:
            require(expected == 'accepted' and response.get('accepted') is True,
                    'field expected acceptance')
        evidence.record('field_submission', offset_ns=offset, expected=expected, response=response)
        after = sample()
        value = field()
        if before is not None:
            elapsed = counter(after['monotonic_now_ns'], 'clock monotonic') - counter(
                before['monotonic_now_ns'], 'clock monotonic')
            projected = counter(before['utc_now_ns'], 'clock utc') + elapsed
            bound = counter(before['uncertainty_ns'], 'clock uncertainty') + 251_050_999 + 2 * elapsed
            difference = abs(sampled - projected)
            evidence.record('nonoverlap_bound', difference_ns=str(difference),
                            uncertainty_and_bracket_ns=str(bound), bracket_ns=str(elapsed))
            require(difference > bound, 'nonoverlap not proven')
        if expected == 'accepted':
            require(value['time_source'] == 'controller' and value['time_disagreement'] is False,
                    'accepted controller source')
            check_clock(after)
        else:
            require(value['time_source'] == 'disagreement' and value['time_disagreement'] is True and
                    after['state'] == 'unsynchronized', 'actual disagreement invalidated clock')
        return after

    def begin(name, seconds, duration, lead):
        nonlocal owner, job, case, sent, stage_end, charged
        case = name
        stage_end = min(end, clock() + seconds)
        sent = set()
        status(unowned=True)
        info()
        owner, job = secrets.token_hex(16), secrets.token_hex(16)
        sent.add('CLAIM')
        claim = wtp('CLAIM', dict(owner_id=owner, lease_ms=60000))
        require(claim['owner_id'] == owner, 'owner claim')
        value = job_value(job)
        value['total_duration_ns'] = str(duration)
        value['events'][0]['duration_ns'] = str(duration)
        charged += 1
        require(charged <= 2, 'two-job invalidation budget')
        evidence.record('simulator_job_charge', case=case, simulator_jobs=1, rf_jobs=0)
        sent.add('LOAD')
        loaded = wtp('LOAD', value)
        require(loaded['job_id'] == job and loaded['state'] == 'loaded', 'original loaded reply')
        status('loaded')
        accepted = sample()
        check_clock(accepted)
        start = counter(accepted['utc_now_ns'], 'utc') + lead
        sent.add('ARM')
        armed = wtp('ARM', dict(job_id=job, start_utc_ns=str(start),
                               max_start_uncertainty_ns='500000000'))
        require(armed['job_id'] == job and armed['state'] == 'armed' and
                counter(armed['start_utc_ns'], 'accepted start UTC') == start,
                'original ARM binding')
        selected = counter(armed['start_monotonic_ns'], 'accepted monotonic start')
        check_clock(armed['clock'])
        status('armed')
        evidence.record('accepted_schedule', case=case, start_monotonic_ns=str(selected),
                        start_utc_ns=str(start), duration_ns=str(duration))
        return selected

    def terminal(value, state):
        records = [record for record in value['terminal_records'] if record['job_id'] == job]
        require(len(records) == 1 and records[0]['state'] == state and
                records[0]['output_active'] is False, 'original terminal record')
        return records[0]

    def poll_until(expected, forbidden=()):
        # Reserve the failure read, post-ABORT read and final empty proof.
        allowed = ('armed', 'running') if expected == 'running' else (
            ('armed', 'missed') if expected == 'missed' else ('running', 'complete'))
        while status_counts.get(case, 0) < MAX_STATUS - 3:
            value = status()
            require(value['state'] not in forbidden and value['state'] in allowed,
                    'unexpected local time-policy transition')
            if value['state'] == expected:
                return value
            sleeper(min(1.5, remaining()))
        raise TimeoutError('finite time invalidation STATUS polls')

    def release(name):
        nonlocal completed, owner, job
        sent.add('RELEASE')
        wtp('RELEASE', {})
        status(unowned=True)
        info()
        completed += 1
        evidence.record('time_invalidation_case_complete', case=name, simulator_jobs=1, rf_jobs=0)
        owner = job = None

    try:
        info()
        caps = wtp('CAPS', {})
        check_caps(caps)
        require(counter(caps['max_job_duration_ns'], 'CAPS duration') >= RUN_DURATION_NS and
                counter(caps['maximum_arm_ahead_ns'], 'CAPS ARM lead') >= 20_000_000_000,
                'continuation duration/lead exceeds CAPS')
        status(unowned=True)
        remaining()
        sntp_off()
        remaining()
        initial = field()
        require(initial['time_source'] == 'none' and initial['time_disagreement'] is False and
                sample()['state'] == 'unsynchronized',
                'fresh no-source invalidation prerequisite')
        submit(0, 'accepted')
        selected = begin('armed_clock_invalidation_missed', STAGE_SECONDS[0], 6_000_000_000,
                         20_000_000_000)
        before = sample()
        check_clock(before)
        after = submit(CONFLICT_OFFSET_NS, 'conflict', before)
        require(counter(after['monotonic_now_ns'], 'invalidation time') < selected,
                'armed invalidation observed before launch')
        status('armed')
        info()
        missed = terminal(poll_until('missed', ('running', 'complete')), 'missed')
        require(missed.get('error', {}).get('code') == 'MISSED_START' and
                selected <= counter(missed['ended_monotonic_ns'], 'missed time') <= selected + END_MARGIN_NS,
                'missed original scheduled launch')
        release(case)
        # Recover only after the missed job is released. Both observations use
        # fresh challenges; no rejected or uncertain submission is replayed.
        stage_end = end
        submit(0, 'conflict')
        sleeper(min(1, remaining()))
        submit(0, 'accepted')
        selected = begin('running_clock_invalidation_monotonic_completion', STAGE_SECONDS[1],
                         RUN_DURATION_NS, 10_000_000_000)
        poll_until('running', ('complete',))
        before = sample()
        check_clock(before)
        after = submit(CONFLICT_OFFSET_NS, 'conflict', before)
        require(counter(after['monotonic_now_ns'], 'invalidation time') < selected + RUN_DURATION_NS,
                'running invalidation observed before completion')
        status('running')
        info()
        complete = terminal(poll_until('complete'), 'complete')
        ended = counter(complete['ended_monotonic_ns'], 'terminal monotonic time')
        require(selected + RUN_DURATION_NS <= ended <= selected + RUN_DURATION_NS + END_MARGIN_NS,
                'running clock invalidation changed selected duration')
        require(field()['time_disagreement'] is True and sample()['state'] == 'unsynchronized',
                'running completion requires persisting invalid clock')
        release(case)
        require(charged == completed == 2, 'exact two-job continuation')
        return dict(status='TIME_INVALIDATION_REVIEW_REQUIRED', simulator_jobs=charged,
                    completed_cases=completed, rf_jobs=0, physical_acceptance=False,
                    status_counts=status_counts)
    except BaseException as error:
        primary = error
        # Cleanup consumes only the original body budget, not a renewed case.
        stage_end = end
        if owner:
            try:
                value = status(bind=False)
                if value['owner_id'] == owner and value['job_id'] in (None, job):
                    if value['state'] in ('loaded', 'armed', 'running') and 'ABORT' not in sent:
                        sent.add('ABORT')
                        wtp('ABORT', dict(job_id=job))
                        value = status()
                    if value['state'] in ('empty', 'aborted', 'complete', 'missed') and 'RELEASE' not in sent:
                        sent.add('RELEASE')
                        wtp('RELEASE', {})
                status(unowned=True)
                evidence.record('cleanup_confirmed', unowned=True)
            except BaseException as cleanup:
                try:
                    evidence.record('cleanup_failed', error=type(cleanup).__name__,
                                    pending='root authority readback/restoration')
                except BaseException:
                    pass  # A failed private log must not replace the original body failure.
        raise
    finally:
        client.backend, client.timeout = backend, timeout
        try:
            sntp_off()
        except BaseException as error:
            try:
                evidence.record('fixture_cleanup_failed', error=type(error).__name__)
            except BaseException:
                pass
            if primary is None:
                raise
