#!/usr/bin/env python3
"""Read-only failure triage. Evidence validity, test result and fault attribution are separate.

This does not award acceptance, change a deadline, retry an action, or access
hardware/network. Known attempts are reconstructed from raw bytes before blame
is assigned. Unknown or damaged evidence remains unclassified.
"""
import argparse
import json
from pathlib import Path
from phase11_5_device_management import digest
from phase11_5_inventory import require

A1 = 'cab1abf2afffa27d79992b1d84bf393a2f1059ad3a4615829407485d695ca7a4'
A1B = '590da5a47dc37c1d4c8addea4713ca0cfcb25872a3daaff46a4c9abb9702b218'
A1C = '3167ff5d4c9e58b908ed0d5fcb64a278454a236857f5442ec0662e1e66fc5156'
A1E = '27cd914815b8af8933fb134b44a923add1f09c8748afd0082115e4b1f202a518'
A1F = 'cc557f977c655ac974c60c8343f1e8ba52dbd40b7837fdac9eb8561a63910236'


def base(packet):
    return dict(schema='phase11.5-diagnosis-v1', packet_sha256=packet,
                evidence='UNVERIFIED', execution='UNKNOWN', acceptance='NOT_ESTABLISHED',
                fault_domain='UNDETERMINED', root_cause='UNDETERMINED',
                firmware_defect_confirmed=False, assistant_tooling_defect_confirmed=False,
                completed_rf_jobs=None, authoritative_final_output='UNKNOWN',
                automatic_retry_allowed=False, facts=[], uncertainties=[], next_actions=[])


def readiness(samples):
    """Explain the failed prerequisite, not its unproven underlying cause."""
    require(samples and all(type(s['monotonic_ns']) is int and type(s['link_status']) is int and
            type(s['enabled']) is bool and isinstance(s['ipv4'], str) and
            s['clock_state'] in ('unsynchronized', 'synchronized', 'holdover') for s in samples),
            'Invalid readiness evidence')
    require(all(a['monotonic_ns'] <= b['monotonic_ns'] for a, b in zip(samples, samples[1:])),
            'Readiness chronology')
    last = samples[-1]
    ready = last['enabled'] and last['link_status'] == 3 and bool(last['ipv4']) and last['clock_state'] == 'synchronized'
    if ready:
        gate = 'READY_AT_LAST_SAMPLE'
    elif not last['enabled']:
        gate = 'WIFI_DISABLED'
    elif last['link_status'] == -3:
        gate = 'WIFI_AUTHENTICATION_NOT_ESTABLISHED'
    elif not last['ipv4']:
        gate = 'NETWORK_ADDRESS_NOT_ESTABLISHED'
    else:
        gate = 'CLOCK_NOT_SYNCHRONIZED'
    states = []
    for s in samples:
        current = (s['enabled'], s['link_status'], s['ipv4'], s['clock_state'])
        if not states or states[-1]['state'] != list(current):
            states.append(dict(monotonic_ns=s['monotonic_ns'], state=list(current)))
    return dict(gate=gate, samples=len(samples), elapsed_seconds=(last['monotonic_ns']-samples[0]['monotonic_ns'])/1e9,
                transitions=states, limit_kind='HARNESS_READINESS_ATTEMPT_LIMIT',
                firmware_contract_violation=False,
                explanation='Readiness observations describe the prerequisite. They do not identify a firmware bug or justify extending an authorized window.')


def diagnose(root):
    result = base(None)
    try:
        packet = digest(root/'packet.json'); result['packet_sha256'] = packet
        if packet == A1:
            from audit_phase11_5_r3_failure import audit
            verified = audit(root)
            result.update(execution='STOPPED_BEFORE_RF', fault_domain='ASSISTANT_HARNESS',
                          root_cause='Console INFO was incorrectly treated as WTP STATUS.',
                          assistant_tooling_defect_confirmed=True,
                          completed_rf_jobs=0, authoritative_final_output='INACTIVE',
                          acceptance='PRESSURE_NOT_EXERCISED')
            result['facts'] = ['Raw audit confirms no LOAD/ARM or pressure connection.',
                'The pressure helper failed on an absent job_id field in Console INFO.',
                'The complete 360-second read-only observation and restoration remain valid evidence.']
            result['next_actions'] = ['Repair/test the parser against the actual Console and WTP producers before another hardware attempt.']
        elif packet == A1B:
            from audit_phase11_5_r3_a1b_failure import audit
            verified = audit(root)
            result.update(execution='PARTIAL_RF_COMPLETED', fault_domain='ASSISTANT_HARNESS',
                          root_cause='The harness rejects the valid producer reason phrase and mishandles completed owner expiry.',
                          assistant_tooling_defect_confirmed=True, completed_rf_jobs=verified['completed_jobs'],
                          authoritative_final_output='INACTIVE', acceptance='PRESSURE_UNVERIFIED_OBSERVATION_INCOMPLETE')
            result['facts'] = ['One 100-second Tone completed with authoritative inactive output.',
                'The parser required 200 OK; the unchanged producer emits 200 Response.',
                'The observer stopped at 125.137594288 seconds after rejecting known unowned Complete.',
                'An expected terminal owner release is not an RF failure.']
            result['uncertainties'] = ['The failing HTTP response bytes were not retained. Its actual status/body and any concurrent target error remain unknown.',
                'The completed Tone does not replace the missing pressure assertions or full observation window.']
            result['next_actions'] = ['Test against source-generated HTTP bytes; persist responses before parsing.',
                'Keep observing known completed jobs after a failed load, and reconcile only authoritative state.']
        elif packet == A1C:
            from audit_phase11_5_r3_retained_failure import audit
            verified = audit(root)
            samples = []
            for index in range(25):
                trace = [json.loads(s) for s in (root/f'network-ready-{index}.stdout').read_text().splitlines()]
                value = trace[-1]['value']; n = value['info']['network']
                samples.append(dict(monotonic_ns=trace[-1]['monotonic_ns'], enabled=n['enabled'],
                    link_status=n['link_status'], ipv4=n['ipv4'], clock_state=value['wtp']['GET_CLOCK']['state']))
            result.update(execution='BLOCKED_BEFORE_RF', fault_domain='UNLOCALIZED_NETWORK_PREREQUISITE',
                          completed_rf_jobs=0, authoritative_final_output='INACTIVE',
                          acceptance='PRESSURE_NOT_EXERCISED', readiness=readiness(samples))
            result['facts'] = ['Twenty-five raw-verified readiness inventories did not establish address/clock admission.',
                'Joining transitions were observed; the final link status was -3, CYW43 authentication failure.',
                'The prior completed job was safely cleared without RF; A/B and host cleanup were verified.',
                'No new RF, CONFIG save, flash or Wi-Fi OFF/ON command occurred.']
            result['uncertainties'] = ['The source of authentication failure is unresolved: active AP settings, live credential state and driver/AP interoperability were not isolated.',
                'The readiness attempt limit is a harness limit, not proof that a firmware timing contract failed.',
                'The active AP password comparison was attempted only after the profile had been removed; it is inconclusive.']
            result['next_actions'] = ['Verify the active AP against the retained input while the fixture is alive; report only a match boolean.',
                'Retain timestamped AP authentication events and fresh Pico link observations before assigning fault.',
                'Run a bounded idle Wi-Fi OFF/ON diagnostic only with its explicit hardware approval; a successful cycle proves recovery, not root cause.']
        elif packet == A1E:
            from audit_phase11_5_r3_a1e_failure import audit
            verified = audit(root)
            result.update(execution='PARTIAL_RF_COMPLETED', fault_domain='ASSISTANT_HARNESS',
                          root_cause='Pressure omitted the already supported bounded in-flight INFO admission.',
                          assistant_tooling_defect_confirmed=True, completed_rf_jobs=1,
                          authoritative_final_output='INACTIVE', acceptance='PRESSURE_INCOMPLETE')
            result['facts'] = ['One explicitly approved idle Wi-Fi OFF/ON cycle restored network readiness; the active AP input matched.',
                'INFO completed in 1.739071744 seconds, within its five-second deadline; starts retained the two-second cadence.',
                'The pressure tool stopped on the preceding snapshot while that valid read was in flight.',
                'Load interruption and the unsubmitted second job followed the primary stop; the observer completed 360 seconds.',
                'One Tone completed; final A was Empty, inactive and unowned, with B and host restored.']
            result['uncertainties'] = ['Successful Wi-Fi recovery does not identify the cause of A1c authentication failure.']
            result['next_actions'] = ['Use the same bounded in-flight admission in every consumer; retain the original failure and causal timeline.']
        elif packet == A1F:
            from audit_phase11_5_r3_a1f_failure import audit
            verified = audit(root)
            result.update(execution='RF_AND_TRAFFIC_COMPLETED_AUDIT_FAILED', fault_domain='ASSISTANT_HARNESS_AND_OBSERVATION_GATE',
                          root_cause='Boot-scoped event IDs and R3 result/cadence adapters were mishandled; a separate frozen completion bracket was missed.',
                          assistant_tooling_defect_confirmed=True, completed_rf_jobs=2,
                          authoritative_final_output='INACTIVE', acceptance='FROZEN_OBSERVATION_GATE_FAILED')
            result['facts'] = ['Both Tones, all ten traffic cases, 300-second production load and 360-second USB observation completed.',
                'USB events 14 through 25 were consecutive; reconnecting does not reset the boot-scoped counter.',
                'The shared load auditor still expected R2-only cadence scope and its different result envelope.',
                'One INFO completed 2.262550925 seconds after a case ended, exceeding the frozen two-second completion bracket.',
                'That request began 0.656231927 seconds after the case and took 1.606318998 seconds; its five-second deadline passed.',
                'The original failure and zero acceptance remain; the proposed request-based bracket is diagnostic only for this capture.']
            result['uncertainties'] = ['No firmware timing or resource contract violation is established by this observation miss.']
            result['next_actions'] = ['Review and prospectively freeze consistent observer cadence and response bounds before further hardware execution.',
                'Replay complete raw captures through the entire audit integration before another run.']
        else:
            result.update(execution='UNCLASSIFIED_ATTEMPT', uncertainties=[
                'No independent raw auditor is registered for this packet. An exception string or a generic FAILED summary cannot establish fault attribution.'])
            result['next_actions'] = ['Add raw reconstruction for the new attempt; do not retry hardware to compensate for missing analysis.']
            return result
        require(verified['accepted_assertions'] == 0, 'Failure audit unexpectedly awards acceptance')
        result['evidence'] = 'RAW_RECONSTRUCTED'
        result['audit_classification'] = verified['classification']
        result['audit_result'] = verified
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        packet = result['packet_sha256']; result = base(packet)
        result.update(evidence='AUDIT_NOT_SATISFIED', fault_domain='UNDETERMINED',
                      uncertainties=[type(error).__name__ + ': ' + str(error)],
                      next_actions=['Inspect the raw audit mismatch: it may be missing/corrupt evidence or a different real outcome. Do not infer device safety, assign blame or automatically rerun.'])
    return result


def authorization_diagnosis(record):
    require(record == dict(source='automatic_approval_review', decision='rejected',
            action_executed=False, user_declined=False, reason='Added idle Wi-Fi OFF/ON action requires explicit approval.'),
            'Unrecognized approval evidence')
    value = base(None)
    value.update(evidence='TOOL_REVIEW_RECORD', execution='NOT_STARTED', acceptance='NOT_RUN',
                 fault_domain='AUTHORIZATION', root_cause=record['reason'], completed_rf_jobs=0,
                 facts=['Automatic approval review blocked the launch.', 'The user did not decline the action.'],
                 next_actions=['Ask the user directly for the concrete added action; do not describe automatic review as a user refusal.'])
    return value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--output', type=Path)
    a = p.parse_args(); result = diagnose(a.evidence)
    raw = json.dumps(result, indent=2) + '\n'
    if a.output:
        with a.output.open('x') as stream: stream.write(raw)
    else: print(raw, end='')


if __name__ == '__main__': main()
