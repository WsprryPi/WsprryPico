"""Offline classification of the first R3 A1 pre-job failure; never acceptance credit."""
import json
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_pilot_supervisor import idle, configuration
from phase11_5_r3_preflight import audit_inventory, decode_frame
from phase11_5_rf_observer import validate_info
from phase11_5_time_local import validate_preserved
from audit_phase11_5_idle import audit as audit_idle

PACKET_SHA = 'cab1abf2afffa27d79992b1d84bf393a2f1059ad3a4615829407485d695ca7a4'


def rows(path):
    text = path.read_text()
    require(text.endswith('\n'), 'Truncated failure evidence')
    return [json.loads(line) for line in text.splitlines()]


def audit(root):
    require(digest(root / 'packet.json') == PACKET_SHA, 'Different failed packet')
    packet = json.loads((root / 'packet.json').read_text())
    for relative, sha in packet['case_helper_sha256'].items():
        require(digest(root / relative) == sha, 'Executed helper evidence changed')
    result = json.loads((root / 'r3-result.json').read_text())
    require(result['status'] == 'FAILED' and result['completed_jobs'] == 0
            and result['family_closed'] is False and result['packet_sha256'] == PACKET_SHA
            and result['device_restored'] is True and result['host_restored'] is True
            and not result.get('restore_error') and not result.get('host_restore_error'), 'Failed run/restoration result')
    job_path = root / 'tls-a1/jobs.json'
    jobs = json.loads(job_path.read_text())
    pressure = rows(root / 'tls-a1/pressure.jsonl')
    require(len(pressure) == 2 and [r['sequence'] for r in pressure] == [0, 1]
            and pressure[0]['kind'] == 'start' and pressure[0]['value'] == dict(
                packet_sha256=digest(job_path), load_sha256=digest(root / 'tls-a1/load.json'))
            and pressure[1]['kind'] == 'failure' and pressure[1]['value'] == dict(type='KeyError', error="'job_id'")
            and pressure[0]['monotonic_ns'] <= pressure[1]['monotonic_ns'],
            'Different pressure failure or network attempt present')
    observation = rows(root / 'tls-a1/usb-health.jsonl')
    require(observation[0]['value']['packet_sha256'] == digest(job_path)
            and observation[0]['value']['seconds'] == 360, 'Failed observer packet/window')
    verified = audit_idle(root / 'tls-a1/usb-health.jsonl', root / 'r3-a1-admission.stdout',
                          expected_prejob_failure=True)
    baseline = rows(root / 'r3-a1-admission.stdout')[-1]['value']
    for row in observation:
        if row['kind'] != 'info':
            continue
        info = row['value']['value']
        validate_info(info, baseline)
        require(all(int(info[k]) == 0 for k in ('launch_epoch', 'dma_irqs', 'alarm_irqs', 'tail_irqs')),
                'RF launch or DMA activity in purported pre-job failure')
    require(observation[0]['monotonic_ns'] <= pressure[0]['monotonic_ns'] <=
            pressure[1]['monotonic_ns'] <= observation[-1]['monotonic_ns'], 'Failure outside observation')
    device = json.loads((root / 'device-state.json').read_text())
    management = json.loads((root / 'management-state.json').read_text())
    require(device.get('restored') is True and device['kind'] == 'original' and not device.get('pending')
            and not management.get('pending') and not management.get('blocked')
            and management['counts'] == dict(config=36, **{'wifi-off': 0, 'wifi-on': 0, 'heap-probe': 6})
            and result['final_management_counts'] == management['counts'], 'Restoration state or counters')
    inventories = {}
    for name, serial, identity in (
            ('before-a', packet['serial'], packet['device_id']),
            ('restored-original-boot', packet['serial'], packet['device_id']),
            ('before-b', 'CDDBF8767C506C07', '29f20b7342051ef947aa56cb9d4fab42'),
            ('after-b', 'CDDBF8767C506C07', '29f20b7342051ef947aa56cb9d4fab42')):
        path = root / (name + '.stdout')
        tx = [r for r in rows(path) if r['kind'] == 'tx']
        session = decode_frame(bytes.fromhex(tx[1]['value']['hex']))['session_id']
        value = audit_inventory(path, dict(serial=serial, device_id=identity), session,
                                packet['helper_sha256']['scripts/phase11_5_inventory.py'])
        idle(value)
        inventories[name] = value
    a, b = inventories['restored-original-boot'], inventories['after-b']
    require(a['info']['revision'] == '802c91a7b86e-dirty' and a['wtp']['STATUS']['boot_id'] == device['boot']
            and a['info']['status']['engine'] == 'inhibited-standalone-simulator'
            and b['info']['revision'] == 'dbf1d86f0885-dirty'
            and b['wtp']['STATUS']['boot_id'] == packet['initial_b_boot_id']
            and configuration(a) == configuration(inventories['before-a'])
            and configuration(b) == configuration(inventories['before-b']), 'Original board state not restored')
    host = json.loads((root / 'fixture-state.json').read_text())
    host_rows = rows(root / 'fixture.jsonl')
    require(host.get('restored') is True and host['host_boot'] == packet['host_boot_id'], 'Host fixture not restored')
    cleanup = [r for r in host_rows if r['kind'] == 'cleanup']
    require(len(cleanup) == 1 and cleanup[0]['value']['failures'] == [], 'Host cleanup failure')
    restored_host = next(r['value'] for r in host_rows if r['kind'] == 'host_restored')
    require(restored_host == host['before'] and restored_host['installed_pid'] == '1957', 'Host identity/routes changed')
    after_time = next(r['value'] for r in host_rows if r['kind'] == 'time_local_after')
    validate_preserved(host['time_local_before'], after_time)
    return dict(classification='FAILED_PREJOB_NO_RF_RESTORED', accepted_assertions=0,
                completed_jobs=0, submitted_jobs=0, pressure_connections=0, packet_sha256=PACKET_SHA,
                candidate_boot=jobs['boot_id'], restored_a_boot=a['wtp']['STATUS']['boot_id'],
                unchanged_b_boot=b['wtp']['STATUS']['boot_id'], management_counts=management['counts'],
                host_restored=True, installed_pid=restored_host['installed_pid'], observer=verified)
