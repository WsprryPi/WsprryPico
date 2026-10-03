#!/usr/bin/env python3
"""Injected, B-only T1-T4 runner; importing this module performs no hardware action."""
import secrets
import time

from phase12_composition_audit import counter
from phase12_recovery_orchestrator import DEVICE, safe_info, require
from phase12_recovery_device import strict
from wsprrypico_ble import Client, ClientError

T1_CONFLICT_OFFSET_NS = 60_000_000_000


class EvidenceClient(Client):
    """Retain notification bytes and correlated replies before Client maps errors."""
    def __init__(self, *args, evidence, **kwargs):
        super().__init__(*args, **kwargs)
        self.evidence = evidence
        self.last_response = None

    def _on_status(self, value):
        self.evidence.record('field_notification', hex=bytes(value).hex())
        super()._on_status(value)

    def _on_wtp_status(self, value):
        self.evidence.record('wtp_notification', hex=bytes(value).hex())
        super()._on_wtp_status(value)

    def exchange(self, message, *args, **kwargs):
        # Login passwords must never enter the retained evidence.
        self.evidence.record('field_request', message={k: v for k, v in message.items()
                                                     if k != 'password'})
        self.last_response = None
        return super().exchange(message, *args, **kwargs)

    def _wait(self, responses, request_id, code, timeout=None):
        response = super()._wait(responses, request_id, code, timeout)
        self.last_response = response
        self.evidence.record('correlated_response', response=response)
        return response

    def wtp_exchange(self, operation, body):
        self.evidence.record('wtp_request', operation=operation, body=body)
        return super().wtp_exchange(operation, body)


def run(client, observe_info, source, boot, evidence, sntp_on, sntp_off,
        *, clock=time.monotonic, sleeper=time.sleep, utc=time.time_ns):
    """Caller supplies an already authorized/bound BLE client and isolated fixture.

    observe_info returns (decoded INFO, exact wire bytes). sntp callbacks control
    only the separately approved B fixture. No job or ownership mutation occurs.
    No failed/uncertain challenge or submission is retried.
    """
    require(client.authorized and client.expected_device_id == DEVICE and
            client.field_session and client.wtp_session, 'authorized exact B client')
    require(len(source) == 40 and all(c in '0123456789abcdef' for c in source), 'source identity')
    start = clock()
    def check():
        require(clock()-start <= 300, 'T1-T4 total deadline')
        info, raw = observe_info()
        require(isinstance(raw, bytes) and raw, 'actual INFO bytes required')
        require(strict(raw) == info, 'INFO decoded/wire mismatch')
        evidence.record('usb_info', hex=raw.hex(), decoded=info)
        for key in ('allocator_failures', 'tls_allocation_failures', 'core0_stack_fault_status',
                    'fault_stage', 'fault_hash', 'fault_pc', 'fault_status',
                    'flash_read_failures', 'flash_erase_failures', 'flash_program_failures'):
            require(counter(info[key], key) == 0, 'resource fault: '+key)
        safe_info(info, source[:12])
        require(info['status']['boot_id'] == boot and
                info.get('phase12_fault_stage', 0) == 0, 'boot/ordinary image binding')
        status = client.wtp_status(boot)
        require(status['boot_id'] == boot and status['state'] == 'empty' and
                status['owner_id'] is None and status['job_id'] is None and
                status['output_active'] is False, 'actual WTP empty/unowned authority')
        evidence.record('authority_observation', status=status)
        field = client.field_status()
        snapshot = client.wtp_exchange('GET_CLOCK', {})
        for key in ('utc_now_ns', 'monotonic_now_ns', 'uncertainty_ns', 'sync_age_ns'):
            counter(snapshot[key], key)
        evidence.record('clock_observation', field=field, clock=snapshot)
        return field, snapshot

    def submit(offset, expected):
        previous_field, previous = check()
        nonce = secrets.token_hex(16)
        challenge = client._field('time_challenge', nonce=nonce)
        require(challenge.get('nonce') == nonce, 'challenge nonce binding')
        # Sample only after the matching complete challenge response.
        sampled = utc()+offset
        require(type(sampled) is int and sampled >= 0, 'UTC sample')
        client.last_response = None
        try:
            reply = client._field('time_submit', without_response=True,
                                  nonce=nonce, utc_ns=str(sampled))
        except ClientError:
            reply = client.last_response
            require(isinstance(reply, dict) and reply.get('ok') is False and
                    reply.get('error') == expected, 'expected actual rejection missing')
        else:
            require(expected == 'accepted' and reply.get('accepted') is True,
                    'unexpected time acceptance')
        evidence.record('time_stimulus', offset_ns=offset, utc_ns=str(sampled),
                        expected=expected, response=reply)
        after = check()
        if offset and previous_field['time_source'] == 'controller':
            prior_mono = counter(previous['monotonic_now_ns'], 'monotonic_now_ns')
            after_mono = counter(after[1]['monotonic_now_ns'], 'monotonic_now_ns')
            require(after_mono >= prior_mono, 'clock monotonic regression')
            elapsed = after_mono-prior_mono
            projected = counter(previous['utc_now_ns'], 'utc_now_ns')+elapsed
            # Submission occurred inside this observed bracket. Firmware fixed
            # controller margin is 250000000+1050999 ns; conservatively add the
            # whole bracket twice for challenge age and sample projection.
            bound = counter(previous['uncertainty_ns'], 'uncertainty_ns')+251_050_999+2*elapsed
            evidence.record('nonoverlap_bound', difference_ns=str(abs(sampled-projected)),
                            uncertainty_and_bracket_ns=str(bound), bracket_ns=str(elapsed))
            require(abs(sampled-projected) > bound, 'T1 nonoverlap not proven')
        return after

    try:
        sntp_off()
        field, _ = check()
        require(field['time_source'] == 'none' and not field['time_disagreement'],
                'fresh no-source controller prerequisite')
        submit(0, 'accepted')
        field, _ = submit(T1_CONFLICT_OFFSET_NS, 'conflict')
        require(field['time_source'] == 'disagreement' and field['time_disagreement'], 'T1 latch')
        evidence.record('case_complete', case='T1', physical_acceptance=False)
        field, _ = submit(0, 'conflict')
        require(field['time_disagreement'], 'T2 first sample must retain latch')
        sleeper(1)
        field, snapshot = submit(0, 'accepted')
        require(field['time_source'] == 'controller' and not field['time_disagreement'], 'T2 recovery')
        evidence.record('case_complete', case='T2', physical_acceptance=False)
        # The accepted T2 observation is T3's sole baseline; never refresh it.
        age_previous = counter(snapshot['sync_age_ns'], 'sync_age_ns')
        mono_previous = counter(snapshot['monotonic_now_ns'], 'monotonic_now_ns')
        # Full authority/INFO guards bookend the interval; lean clock polling
        # avoids repeating four transactions across a three-second window.
        for age_s in (89, 91, 181):
            deadline = min(start+300, clock()+age_s+5)
            for _ in range(2048):
                require(clock() < deadline, 'T3 target age deadline')
                snapshot = client.wtp_exchange('GET_CLOCK', {})
                require(clock() < deadline and clock()-start <= 300, 'T3 clock response deadline')
                for key in ('utc_now_ns', 'monotonic_now_ns', 'uncertainty_ns', 'sync_age_ns'):
                    counter(snapshot[key], key)
                mono = counter(snapshot['monotonic_now_ns'], 'monotonic_now_ns')
                require(mono >= mono_previous, 'T3 monotonic regression')
                mono_previous = mono
                age = counter(snapshot['sync_age_ns'], 'sync_age_ns')
                require(age >= age_previous, 'T3 clock age reset')
                age_previous = age
                if age >= age_s*1_000_000_000:
                    require(age <= (age_s+3)*1_000_000_000, 'T3 observation bracket missed')
                    # This observation follows, rather than precedes, the
                    # qualifying clock sample at the expiry boundary.
                    field = client.field_status()
                    require(clock() < deadline and clock()-start <= 300, 'T3 field response deadline')
                    require(field['time_source'] != 'sntp' and not field['time_disagreement'], 'T3 source changed')
                    break
                sleeper(min(.1, (age_s*1_000_000_000-age)/1_000_000_000))
            else:
                raise TimeoutError('finite T3 clock poll count')
            if age_s >= 91:
                require(field['time_source'] == 'none', 'T3 controller remained valid')
            if age_s == 181:
                require(snapshot['state'] == 'unsynchronized', 'T3 discipline did not expire')
            evidence.record('age_boundary', age_s=age_s, clock=snapshot, field=field)
        final_field, final_snapshot = check()
        require(clock()-start <= 300 and
                counter(final_snapshot['monotonic_now_ns'], 'monotonic_now_ns') >= mono_previous and
                counter(final_snapshot['sync_age_ns'], 'sync_age_ns') >= age_previous and
                final_field['time_source'] == 'none' and not final_field['time_disagreement'],
                'T3 final guard deadline, source or clock changed')
        evidence.record('case_complete', case='T3', physical_acceptance=False,
                        arm_refusal_tested=False)
        sntp_on()
        deadline = min(start+295, clock()+60)
        while True:
            field, snapshot = check()
            if field['time_source'] == 'sntp' and snapshot['state'] == 'synchronized':
                break
            require(clock() < deadline, 'T4 accepted SNTP prerequisite missing')
            sleeper(1)
        field, _ = submit(5_000_000_000, 'busy')
        require(field['time_source'] == 'sntp' and not field['time_disagreement'], 'T4 source mutation')
        evidence.record('case_complete', case='T4', physical_acceptance=False)
        return dict(status='LIVE_CASES_COMPLETE_REVIEW_REQUIRED', cases=['T1','T2','T3','T4'],
                    rf_jobs=0, simulated_jobs=0, physical_acceptance=False,
                    t3_arm_refusal_tested=False)
    finally:
        sntp_off()
