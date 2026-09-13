"""Reconstruct A1f, retaining its frozen observation miss and zero acceptance."""
import json
from pathlib import Path
from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_r3_preflight import audit_inventory
from phase11_5_pilot_supervisor import idle, configuration, B_SERIAL, B_DEVICE
from phase11_5_time_local import validate_preserved
from audit_phase11_5_r3_retained_failure import rows
from audit_phase11_5_r2_modes import audit as audit_finite
from audit_phase11_5_r3_tls import audit_pressure
from phase11_5_r3_tls_plan import validate, BRACKET_POLICY

PACKET = 'cc557f977c655ac974c60c8343f1e8ba52dbd40b7837fdac9eb8561a63910236'


def audit(root):
    require(digest(root/'packet.json') == PACKET, 'Different A1f packet')
    p = json.loads((root/'packet.json').read_text())
    for group in ('case_helper_sha256', 'production_helper_sha256'):
        for name, sha in p[group].items():
            require(digest(root/name) == sha, 'Executed A1f helper changed')
    require(json.loads((root/'retained-result.json').read_text()) == dict(status='FAILED',
            packet_sha256=PACKET, family_closed=False, error='ValueError: RF event identity/gap',
            device_inactive_unowned=True, b_unchanged=True, host_restored=True,
            configuration_writes=0, flashes=0), 'A1f original disposition changed')
    require(not list(root.glob('wifi-*-exchange.jsonl')), 'Unexpected additional Wi-Fi cycle')
    case = root/'tls-a1'; packet = validate(json.loads((case/'jobs.json').read_text()))
    require(packet['jobs'] == p['finite_job_templates'] and 'observer_bracket_policy' not in packet,
            'A1f cannot acquire a prospective observation amendment')
    # All independent raw USB, production, lifecycle and timing gates run. The
    # corrected adapter recognizes the actual R3 producer and boot-scoped IDs.
    finite = audit_finite(case, root/'pi/phase115_tls_observer_test.py',
                         cadence_policy='single-flight-admin-v1', packet_validator=validate,
                         baseline_path=root/'r3-a1-admission.stdout')
    pressure = rows(case/'pressure.jsonl'); usb = rows(case/'usb-health.jsonl')
    require([int(r['value']['event_id']) for r in usb if r['kind']=='wtp_message' and
             r['value']['type']=='event'] == list(range(14,26)), 'Different A1f event origin/sequence')
    require(pressure[0]['value'] == dict(packet_sha256=digest(case/'jobs.json'),
            load_sha256=digest(case/'load.json')), 'Pressure input binding')
    try:
        audit_pressure(packet, pressure, usb)
    except ValueError as error:
        require(str(error) == 'Missing independent pressure bracket', 'Different frozen pressure failure')
    else: raise ValueError('Expected frozen A1f observation miss is absent')
    diagnostic = audit_pressure(packet, pressure, usb, diagnostic_bracket_policy=BRACKET_POLICY)
    require(diagnostic['status'] == 'DIAGNOSTIC_ONLY', 'Prospective policy cannot grant A1f acceptance')
    misses = []
    for first,last in zip([r for r in pressure if r['kind']=='case_begin'],
                          [r for r in pressure if r['kind']=='case_finish']):
        for kind,budget in (('info',2_000_000_000),('status',6_000_000_000)):
            series = [r for r in usb if r['kind']==kind]
            before = [r for r in series if r['monotonic_ns']<=first['monotonic_ns']][-1]
            after = next(r for r in series if r['monotonic_ns']>=last['monotonic_ns'])
            preage = first['monotonic_ns']-before['monotonic_ns']
            postlag = after['monotonic_ns']-last['monotonic_ns']
            if preage>budget or postlag>budget:
                misses.append(dict(case=first['value']['label'], sample=kind, preceding_age_ns=preage,
                    following_lag_ns=postlag, frozen_limit_ns=budget,
                    following_request_offset_ns=after['value']['began_monotonic_ns']-last['monotonic_ns'],
                    following_roundtrip_ns=after['monotonic_ns']-after['value']['began_monotonic_ns']))
    require(len(misses)==1 and misses[0]['case']=='recover-slots' and misses[0]['sample']=='info',
            'Different observation miss')
    values = {}
    for name in ('before-b','initial-terminal-before','r3-a1-admission','final-terminal-before','after-b'):
        b = name.endswith('-b')
        values[name] = audit_inventory(root/(name+'.stdout'),
            dict(serial=B_SERIAL if b else p['serial'],device_id=B_DEVICE if b else p['device_id']),
            p['b_inventory_session_id'] if b else p['inventory_session_id'],
            p['case_helper_sha256']['scripts/phase11_5_inventory.py'])
        idle(values[name])
    initial,final = values['initial-terminal-before'],values['final-terminal-before']
    require(configuration(initial)==configuration(final) and
            initial['wtp']['STATUS']['boot_id']==final['wtp']['STATUS']['boot_id']==packet['boot_id'] and
            final['wtp']['STATUS']['terminal_records']==finite['usb']['terminal_records'],
            'A1f final device authority/configuration differs')
    require(configuration(values['before-b'])==configuration(values['after-b']) and
            values['before-b']['wtp']['STATUS']['boot_id']==values['after-b']['wtp']['STATUS']['boot_id']==p['initial_b_boot_id'],
            'Comparator changed')
    host = json.loads((root/'fixture-state.json').read_text()); trace = rows(root/'fixture.jsonl')
    require(host['restored'] is True and host['host_boot']==p['host_boot_id'] and
            next(r['value'] for r in trace if r['kind']=='host_restored')==host['before'] and
            next(r['value'] for r in trace if r['kind']=='cleanup')['failures']==[], 'Host restoration missing')
    validate_preserved(host['time_local_before'],next(r['value'] for r in trace if r['kind']=='time_local_after'))
    return dict(classification='HARNESS_AUDIT_INTEGRATION_AND_FROZEN_OBSERVATION_MISS',
                accepted_assertions=0, packet_sha256=PACKET, completed_jobs=2,
                physical_finite_gates=finite, pressure_diagnostic=diagnostic,
                frozen_observation_misses=misses, final_status=final['wtp']['STATUS'],
                configuration_writes=0,flashes=0,wifi_off=0,wifi_on=0,host_restored=True,
                conclusion='Three audit integration defects are confirmed. The separate frozen sample-completion bracket failed. No firmware contract violation is established; prospective cadence policy is diagnostic only here.')
