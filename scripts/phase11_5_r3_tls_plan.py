"""Pure R3 A1 scope. Two finite jobs; no authority or hardware access here."""
import hashlib
import re
from phase11_5_inventory import require
from phase11_5_r2_upload_plan import SOURCE, PHYSICAL

SCHEMA = 'phase11.5-r3-tls-a1-v1'
COUNTS = {'config': 34, 'wifi-off': 0, 'wifi-on': 0, 'heap-probe': 6}
MANAGEMENT_SCOPE = 'R3-A1-config-34-to-36-v1'
CONTINUATION_SCOPE = 'R3-A1b-config-36-to-38-v1'
CONTINUATION_PRIOR = dict(
    root='/home/pi/phase11-5-r3-tls-a1-20260912',
    packet_sha256='cab1abf2afffa27d79992b1d84bf393a2f1059ad3a4615829407485d695ca7a4',
    device_state_sha256='a829e043586516b1e57ce81412a7b01cbff19bbdbcbdef2bd5378b5ae76239d1',
    management_state_sha256='15b688377275ed671a2363ac1163ae92020aafb52151effc5881d556604450ad')
CASES = (
    ('positive', 'missing-certificate', 'recover-certificate', 'silent-handshake', 'recover-handshake'),
    ('positive', 'slot-excess', 'recover-slots', 'duplicate-wtp', 'recover-wtp'),
)


def jobs(nonce):
    from phase11_5_f1_plan import make_job
    require(isinstance(nonce, str) and re.fullmatch('[0-9a-f]{32}', nonce)
            and nonce != '0' * 32, 'R3 nonce')
    result = []
    for index in range(2):
        job = make_job('TONE', 135500, sample_rate_hz=138000000)
        job['total_duration_ns'] = job['events'][0]['duration_ns'] = '100000000000'
        job['job_id'] = hashlib.sha256(f'R3-A1:{nonce}:{index}'.encode()).hexdigest()[:32]
        result.append(job)
    return result


def validate(packet):
    require(packet['schema'] == SCHEMA and packet['source_revision'] == SOURCE
            and packet['revision'] == SOURCE[:12] and packet['uf2_sha256'] == PHYSICAL,
            'R3 selected image')
    require(packet['serial'] == '0BF4B4AEC9FFB344'
            and packet['device_id'] == 'fd6127d11d6aca42a9905fa3fb1bf1d5', 'R3 DUT')
    require(type(packet['system_clock_hz']) is int and packet['system_clock_hz'] == 138000000
            and type(packet['pio_divider']) is int and packet['pio_divider'] == 1
            and packet['listener_enabled'] is True and packet['rf_render_in_ram'] is True,
            'R3 RF configuration')
    for key in ('boot_id', 'owner_id', 'nonce'):
        require(isinstance(packet[key], str) and re.fullmatch('[0-9a-f]{32}', packet[key])
                and packet[key] != '0' * 32, 'R3 nonzero identity')
    require(packet['jobs'] == jobs(packet['nonce']) and packet['submission_path'] == 'usb'
            and packet['nominal_seconds'] == 300 and packet['maximum_renewals'] == 12
            and packet['pressure_cases'] == [list(c) for c in CASES]
            and packet['browser_profile'] == 'N' and packet['ordinary_browser'] is False,
            'R3 frozen jobs/load/injections')
    return packet


def initial_config(scope):
    require(scope in (MANAGEMENT_SCOPE, CONTINUATION_SCOPE), 'Unknown management extension')
    return 34 if scope == MANAGEMENT_SCOPE else 36


def validate_allowance(packet):
    initial = initial_config(packet.get('management_scope'))
    require(packet.get('family') == 'R3' and packet.get('r3_scope') == SCHEMA
            and packet.get('source_revision') == SOURCE
            and packet.get('initial_management_counts') == COUNTS | {'config': initial}
            and packet.get('max_configuration_writes') == initial + 2
            and packet.get('max_idle_heap_probes') == 0
            and packet.get('time_server_mdns') is True,
            'R3 exact cumulative allowance')
    if packet['management_scope'] == CONTINUATION_SCOPE:
        require(packet.get('prior_restored_attempt') == CONTINUATION_PRIOR
                and packet.get('initial_a_boot_id') == '7a772a4eb283b23afdd1e25acbc449cd'
                and packet.get('initial_b_boot_id') == 'feffcd075ab6cb0b74e7e0c2fde6c87f',
                'R3 A1b requires the preserved A1 failure and restored identities')


def validate_prior_failure(packet):
    """Re-audit the consumed attempt before a continuation can set up the host."""
    validate_allowance(packet)
    if packet['management_scope'] == CONTINUATION_SCOPE:
        from pathlib import Path
        from audit_phase11_5_r3_failure import audit
        result = audit(Path(packet['prior_restored_attempt']['root']))
        require(result['management_counts'] == packet['initial_management_counts']
                and result['restored_a_boot'] == packet['initial_a_boot_id']
                and result['unchanged_b_boot'] == packet['initial_b_boot_id'],
                'R3 A1b prior failure reconciliation changed')
        return result


def authorize_management(state, action, argument):
    initial = initial_config(state.get('management_scope'))
    require(state.get('source_revision') == SOURCE and state['counts'] | {'config': 34} == COUNTS,
            'R3 inherited counters/source')
    require(action == 'config' and ((argument == 'test' and state['counts']['config'] == initial)
            or (argument == 'original' and state['counts']['config'] in (initial, initial + 1))),
            'R3 permits one setup and one restoration CONFIG only')
