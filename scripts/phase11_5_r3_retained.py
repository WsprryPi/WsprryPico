#!/usr/bin/env python3
"""Opt-in R3 TLS packet on the retained physical baseline; no flash or CONFIG path."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from phase11_5_inventory import require, exclusive_port, exchange
from phase11_5_pilot import Peer, SERIAL, DEVICE
from phase11_5_pilot_supervisor import finished, configuration, idle, B_SERIAL, B_DEVICE
from phase11_5_device_management import admit, digest, save
from phase11_5_network_fixture import Fixture, HOST_BOOT
from phase11_5_r3_tls_plan import SOURCE, SCHEMA, jobs, CASES
from phase11_5_r3_tls import run_packet, CASE_HELPERS
from phase11_5_time_local import fixture_admission

SCHEMA_RETAINED = 'phase11.5-r3-retained-fixture-v1'
BOOT = '9c5aec394269e0b57ca16d73ad3d12b6'
PRIOR_JOB = '91bd2c3d57e3e74f7de183203796f463'


def validate(packet):
    from phase11_5_join_diagnostics import selected
    selected(packet)
    from phase11_5_r3_tls_plan import BRACKET_POLICY
    require(packet.get('observer_bracket_policy') in (None, BRACKET_POLICY), 'Unknown observer bracket policy')
    for name in ('nonce', 'owner_id', 'inventory_session_id', 'b_inventory_session_id', 'cleanup_owner_id'):
        require(isinstance(packet.get(name), str) and re.fullmatch('[0-9a-f]{32}', packet[name])
                and packet[name] != '0' * 32, 'Retained identity: ' + name)
    require(len({packet[name] for name in ('owner_id', 'inventory_session_id',
            'b_inventory_session_id', 'cleanup_owner_id')}) == 4, 'Distinct retained principals')
    require(packet['schema'] == SCHEMA_RETAINED and packet['family'] == 'R3'
            and packet['r3_scope'] == SCHEMA and packet['source_revision'] == SOURCE
            and packet['initial_a_boot_id'] == BOOT and packet['host_boot_id'] == HOST_BOOT
            and packet['serial'] == SERIAL and packet['device_id'] == DEVICE,
            'Retained R3 identity')
    require(packet['configuration_writes'] == packet['flashes'] == packet['heap_probes'] == 0
            and packet['network_runtime_seconds'] == 1800 and packet['network_restoration_seconds'] == 600
            and packet['finite_job_templates'] == jobs(packet['nonce'])
            and packet['pressure_cases'] == [list(c) for c in CASES]
            and packet['maximum_renewals'] == 12 and packet['maximum_tcp_connections'] == 12
            and packet['nominal_seconds'] == 300 and packet['observation_seconds'] == 360,
            'Retained R3 exact finite scope')
    require(packet['time_server_mdns'] is True and packet['time_server_dns'] is False
            and packet['retained_wifi_sha256'] == 'fc42b65f177e62afc6664ffc1f13bc14e7711d7cd51c9d191c2e0c580d620764',
            'Retained network baseline')
    recovery = packet.get('wifi_recovery')
    require(recovery is None or recovery == dict(scope='r3-a1d-idle-rejoin-v1',
            maximum_off=1, maximum_on=1,
            prior_packet_sha256='3167ff5d4c9e58b908ed0d5fcb64a278454a236857f5442ec0662e1e66fc5156',
            prior_evidence_sha256='b5db3b325cc0b695eb99812241e7b6bddf6c38d9124b8356305c6be1f032a45f'),
            'Unknown Wi-Fi recovery scope')
    return packet


def terminal_admission(value, baseline, allowed_jobs):
    s, info = value['wtp']['STATUS'], value['info']
    require(s['boot_id'] == info['status']['boot_id'] == BOOT
            and s['output_active'] is False and s['owner_id'] is None
            and info['status']['output_active'] is False and info['status']['enabled'] is False
            and info['status']['last_error'] is None and not info['recovery_boot']
            and info['status']['storage_healthy'] is True and info['revision'] == SOURCE[:12]
            and configuration(value) == configuration(baseline), 'Terminal cleanup identity/configuration/output')
    # Reuse all original admission/resource gates without mutating the evidence.
    from phase11_5_rf_observer import validate_info
    validate_info(info, baseline)
    require(s['state'] in ('empty', 'complete') and info['status']['state'] == s['state'], 'Cleanup terminal state')
    if s['state'] == 'empty':
        require(s['job_id'] is None, 'Empty job identity')
        return False
    require(s['job_id'] in allowed_jobs and any(r['job_id'] == s['job_id'] and r['state'] == 'complete'
            and r['output_active'] is False and 'error' not in r for r in s['terminal_records']),
            'Unknown/non-complete job cannot be released')
    return True


class RetainedDUT:
    def __init__(self, root, packet):
        self.root, self.packet = root, packet
        self.state = dict(boot=BOOT)
        self.session = packet['inventory_session_id']
        self.baseline = finished(root / 'baseline-reference.stdout', 'READ_ONLY_INVENTORY')

    def inventory(self, label, serial=SERIAL, device=DEVICE):
        with (self.root / (label + '.stdout')).open('xb') as out, (self.root / (label + '.stderr')).open('xb') as err:
            code = subprocess.run(['python3', str(self.root / 'scripts/phase11_5_inventory.py'),
                '--serial', serial, '--device-id', device, '--session-id', self.session if serial == SERIAL
                else self.packet['b_inventory_session_id'], '--run'], stdout=out, stderr=err, timeout=65).returncode
        require(code == 0, 'Read-only retained inventory failed: ' + label)
        return finished(self.root / (label + '.stdout'), 'READ_ONLY_INVENTORY')

    def check_current(self, label):
        value = self.inventory(label)
        admit(value, self.baseline, SOURCE)
        return value

    def reconcile(self, label, allowed_jobs):
        value = self.inventory(label + '-before')
        if not terminal_admission(value, self.baseline, allowed_jobs):
            return value
        end = time.monotonic() + 30
        with (self.root / (label + '-release.jsonl')).open('x') as log:
            def emit(kind, value):
                log.write(json.dumps(dict(kind=kind, value=value, monotonic_ns=time.monotonic_ns())) + '\n')
                log.flush(); os.fsync(log.fileno())
            def checkpoint(): require(time.monotonic() < end, 'Terminal release deadline')
            with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02')) as fd:
                peer = Peer(fd, emit, checkpoint, BOOT)
                hello = peer.request('HELLO', dict(versions=['WTP/1'], client_name='r3-terminal-cleanup', client_version='1'))
                require(hello['device_id'] == DEVICE and hello['boot_id'] == BOOT, 'Cleanup HELLO')
                require(peer.request('STATUS') == value['wtp']['STATUS'], 'Terminal changed before claim')
                owner = self.packet['cleanup_owner_id']
                claim = peer.request('CLAIM', dict(owner_id=owner, lease_ms=60000))
                require(claim['owner_id'] == owner and claim['granted_lease_ms'] == 60000, 'Cleanup lease')
                peer.request('RELEASE')
                final = peer.request('STATUS')
                require(final['state'] == 'empty' and final['job_id'] is None and final['owner_id'] is None
                        and final['output_active'] is False and final['boot_id'] == BOOT
                        and final['terminal_records'] == value['wtp']['STATUS']['terminal_records'], 'Cleanup changed history/output')
        return self.check_current(label + '-after')

    def recover_wifi(self):
        """One explicitly frozen volatile OFF/ON cycle; no flash, CONFIG or RF."""
        require(self.packet.get('wifi_recovery') is not None, 'No Wi-Fi recovery scope')
        value = self.check_current('wifi-recovery-admission')
        from phase11_5_join_diagnostics import selected
        if selected(self.packet):
            # JOINING/NOIP are progress states, not permission to cycle and not
            # a failed attempt. Observe until an existing admission state appears.
            deadline = time.monotonic() + 30
            for index in range(30):
                network = value['info']['network']
                if network['link_status'] not in (1, 2):
                    break
                require(network['enabled'] is True and not network['ipv4'],
                        'Unexpected transient recovery state')
                require(time.monotonic() + 1 < deadline and index < 29,
                        'Recovery admission did not settle within 30 seconds')
                time.sleep(1)
                value = self.check_current('wifi-recovery-wait-' + str(index))
                require(time.monotonic() < deadline, 'Recovery admission reply exceeded its 30-second window')
        if value['info']['network']['link_status'] == 3:
            save(self.root / 'wifi-recovery.json', dict(status='NOT_NEEDED', off=0, on=0))
            return
        require(value['info']['network']['enabled'] is True and
                value['info']['network']['link_status'] in (-3, -2) and
                not value['info']['network']['ipv4'], 'Unexpected recovery network state')
        state = dict(status='RUNNING', off=0, on=0)
        with (self.root / 'wifi-recovery.json').open('x') as f: json.dump(state, f)
        for enabled in (False, True):
            label = 'on' if enabled else 'off'
            current = self.check_current('wifi-' + label + '-before')
            with (self.root / ('wifi-' + label + '-exchange.jsonl')).open('x') as log:
                def emit(kind, value):
                    log.write(json.dumps(dict(kind=kind, value=value, monotonic_ns=time.monotonic_ns())) + '\n')
                    log.flush(); os.fsync(log.fileno())
                with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as fd:
                    info = exchange(fd, b'INFO\n', time.monotonic() + 5, emit, False)
                    admit(dict(current, info=info), self.baseline, SOURCE)
                    require(info['network']['enabled'] is not enabled, 'Wi-Fi changed before command')
                    state[label] = 1; state['pending'] = label
                    save(self.root / 'wifi-recovery.json', state)
                    ack = exchange(fd, b'WIFI ON\n' if enabled else b'WIFI OFF\n',
                                   time.monotonic() + 5, emit, False)
                    require(ack == {'ok': True}, 'Wi-Fi recovery command rejected')
            for index in range(11):
                after = self.check_current('wifi-' + label + '-after-' + str(index))
                n = after['info']['network']
                if n['enabled'] is enabled and not n['withdrawal_pending'] and n['requested_enabled'] is None: break
                require(index < 10, 'Wi-Fi transition did not settle'); time.sleep(.5)
            del state['pending']; save(self.root / 'wifi-recovery.json', state)
        state['status'] = 'CYCLE_COMPLETED_REJOIN_NOT_YET_PROVEN'
        save(self.root / 'wifi-recovery.json', state)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True); p.add_argument('--packet-sha256', required=True)
    p.add_argument('--run', action='store_true'); args = p.parse_args()
    if not args.run:
        print('Plan only; no access. Retained R3 packet execution must be authorized.'); return
    require(os.geteuid() == 0 and Path('/proc/sys/kernel/random/boot_id').read_text().strip() == HOST_BOOT, 'Host identity')
    os.umask(0o077); root = args.root.resolve(strict=True)
    require(digest(root / 'packet.json') == args.packet_sha256, 'Frozen packet changed')
    packet = validate(json.loads((root / 'packet.json').read_text()))
    require(packet['root'] == str(root) and set(packet['case_helper_sha256']) == CASE_HELPERS, 'Root/helper manifest')
    require(set(packet['production_helper_sha256']) == {'pi/phase115_production_load.py',
            'pi/phase115_tls_observer.c', 'pi/phase115_tls_observer_test.py'}, 'Production helper manifest')
    require(set(packet['private_input_sha256']) == {'retained-wifi.json', 'baseline-reference.stdout',
            'pi/phase115_tls_observer.so'} | {'credentials/' + role + '/' + name
            for role in ('controller', 'browser') for name in ('client-ca.crt', 'client.crt', 'client.key')},
            'Retained private input manifest')
    for group in ('case_helper_sha256', 'production_helper_sha256', 'private_input_sha256'):
        for name, sha in packet[group].items():
            require((root / name).resolve().is_relative_to(root) and digest(root / name) == sha, 'Frozen input changed')
    for key in ('production_binary', 'production_observer'):
        require(digest(Path(packet[key])) == packet[key + '_sha256'], 'Production artifact')
    require(digest(root / 'production.ini') == packet['production_ini_sha256'], 'Production INI')
    sys.path.insert(0, str(root / 'pi'))
    import phase115_production_load as load
    load.validate_ini(root / 'production.ini')
    with (root / 'retained-result.json').open('x') as f: json.dump(dict(status='RUNNING'), f)
    result = dict(status='FAILED', packet_sha256=args.packet_sha256, family_closed=False)
    dut = RetainedDUT(root, packet)
    before_b = None
    try:
        before_b = dut.inventory('before-b', B_SERIAL, B_DEVICE); idle(before_b)
        require(before_b['wtp']['STATUS']['boot_id'] == packet['initial_b_boot_id'], 'Comparator boot')
        dut.reconcile('initial-terminal', {PRIOR_JOB})
        host_started = time.monotonic()
        with (root / 'host-setup.log').open('x') as log:
            code = subprocess.run(['python3', str(root / 'scripts/phase11_5_network_fixture.py'), 'setup',
                                   '--root', str(root), '--run'], stdout=log, stderr=subprocess.STDOUT, timeout=330).returncode
        require(code == 0, 'Host setup failed')
        fixture = Fixture(root); fixture.verify(); fixture_admission(fixture, root, 'retained-time-admission')
        # This comparison is performed on wspr5 and emits no credential value.
        wifi = json.loads((root / 'retained-wifi.json').read_text())
        actual = fixture.value('nmcli', '--show-secrets', '-g', '802-11-wireless-security.psk',
                               'connection', 'show', 'phase115-closure-ap')
        require(actual == wifi['password'], 'Active AP differs from retained Wi-Fi input')
        save(root / 'retained-ap-identity.json', dict(psk_matches_retained=True))
        from phase11_5_join_diagnostics import selected, capture
        if selected(packet):
            for index in range(7):
                current = dut.check_current('diagnostic-ready-' + str(index))
                if current['info']['network']['link_status'] == 3:
                    break
                if index < 6:
                    time.sleep(5)
            capture(fixture, 'before-recovery')
        if packet.get('wifi_recovery') is not None:
            dut.recover_wifi()
        for index in range(25):
            current = dut.check_current('network-ready-' + str(index))
            if current['wtp']['GET_CLOCK']['state'] == 'synchronized' and current['info']['network']['ipv4'] == '10.77.15.10': break
            require(index < 24, 'Retained network/clock did not converge'); time.sleep(5)
        require(time.monotonic() + 375 < host_started + packet['network_runtime_seconds'],
                'Insufficient fixture lifetime for the complete RF observation')
        result['a1'] = run_packet(root, packet, dut, fixture)
        result['status'] = 'PASS_REQUIRES_FINAL_REVIEW'
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        try:
            final = dut.reconcile('final-terminal', {PRIOR_JOB} | {j['job_id'] for j in packet['finite_job_templates']})
            idle(final); result['device_inactive_unowned'] = True
            if before_b is not None:
                b = dut.inventory('after-b', B_SERIAL, B_DEVICE); idle(b)
                require(b['wtp']['STATUS']['boot_id'] == before_b['wtp']['STATUS']['boot_id'] and
                        configuration(b) == configuration(before_b), 'Comparator changed')
                result['b_unchanged'] = True
        except BaseException as error: result['device_cleanup_error'] = str(error)
        if (root / 'fixture-state.json').exists():
            from phase11_5_join_diagnostics import selected, capture
            if selected(packet):
                try:
                    capture(Fixture(root), 'before-host-cleanup')
                except BaseException as error:
                    result['diagnostic_capture_error'] = type(error).__name__ + ': ' + str(error)
            try:
                with (root / 'host-cleanup.log').open('x') as log:
                    code = subprocess.run(['python3', str(root / 'scripts/phase11_5_network_fixture.py'), 'cleanup',
                        '--root', str(root), '--run'], stdout=log, stderr=subprocess.STDOUT, timeout=600).returncode
                require(code == 0, 'Host cleanup failed'); result['host_restored'] = True
            except BaseException as error: result['host_cleanup_error'] = str(error)
        result['configuration_writes'] = result['flashes'] = 0
        if not (result.get('device_inactive_unowned') and result.get('b_unchanged') and result.get('host_restored')) or result.get('diagnostic_capture_error'):
            result['status'] = 'FAILED'
        save(root / 'retained-result.json', result)
    require(result['status'] == 'PASS_REQUIRES_FINAL_REVIEW' and result.get('device_inactive_unowned')
            and result.get('b_unchanged') and result.get('host_restored'), 'Retained R3 attempt failed; preserve evidence')


if __name__ == '__main__': main()
