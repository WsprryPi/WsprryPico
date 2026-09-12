#!/usr/bin/env python3
"""Single-use R3 A1 supervisor with independently guarded device and host restoration."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

from phase11_5_inventory import require
from phase11_5_device_fixture import DeviceFixture
from phase11_5_device_management import digest, save
from phase11_5_network_fixture import Fixture, PREFIX
from phase11_5_time_local import fixture_admission
from phase11_5_f1_plan import admit_caps
from phase11_5_r2_modes import CASE_HELPERS
from phase11_5_r3_tls_plan import SCHEMA, SOURCE, PHYSICAL, CASES, jobs, validate, validate_allowance
from audit_phase11_5_r3_tls import audit


def validate_scope(packet):
    validate_allowance(packet)
    require(packet['schema'] == 'phase11.5-device-fixture-v2'
            and packet['runtime_seconds'] == 1800 and packet['network_runtime_seconds'] == 3600
            and packet['device_restoration_seconds'] == packet['network_restoration_seconds'] == 600
            and packet['finite_job_templates'] == jobs(packet['nonce'])
            and packet['pressure_cases'] == [list(c) for c in CASES]
            and packet['maximum_tcp_connections'] == 12 and packet['maximum_renewals'] == 12
            and packet['nominal_seconds'] == 300 and packet['observation_seconds'] == 360
            and packet['fixture_authorized'] is True and packet['current_wiring_confirmed'] is True,
            'R3 frozen scope/limits and required hardware grant')
    require(not packet.get('remaining_modes') and not packet.get('upload_check'),
            'R3 cannot reuse spent R2 authority')


def run_packet(root, packet, device, fixture):
    current = device.check_current('r3-a1-admission')
    target = root / 'tls-a1'
    target.mkdir(mode=0o700)
    rf = dict(schema=SCHEMA, source_revision=SOURCE, revision=SOURCE[:12], uf2_sha256=PHYSICAL,
              serial=packet['serial'], device_id=packet['device_id'], system_clock_hz=138000000,
              pio_divider=1, listener_enabled=True, rf_render_in_ram=True, boot_id=device.state['boot'],
              host_boot_id=packet['host_boot_id'], nonce=packet['nonce'], owner_id=packet['owner_id'],
              jobs=packet['finite_job_templates'], submission_path='usb', nominal_seconds=300,
              maximum_renewals=12, browser_profile='N', ordinary_browser=False,
              pressure_cases=packet['pressure_cases'], baseline=str(root / 'r3-a1-admission.stdout'),
              prior_terminal_records=current['wtp']['STATUS']['terminal_records'])
    validate(rf)
    admit_caps(rf, current['wtp']['CAPS'])
    save(target / 'jobs.json', rf)
    namespaces = {key: fixture.in_client(['readlink', path]).stdout.strip() for key, path in
                  [('netns', '/proc/self/ns/net'), ('mountns', '/proc/self/ns/mnt')]}
    plan = dict(boot_id=device.state['boot'], device_id=packet['device_id'], seconds=300, browser=False,
                address='10.77.15.10', **namespaces, binary=packet['production_binary'],
                binary_sha256=packet['production_binary_sha256'], ini=str(root / 'production.ini'),
                ini_sha256=digest(root / 'production.ini'), observer=packet['production_observer'],
                observer_sha256=packet['production_observer_sha256'],
                ca=str(root / 'credentials/browser/client-ca.crt'),
                browser_cert=str(root / 'credentials/browser/client.crt'),
                browser_key=str(root / 'credentials/browser/client.key'),
                controller_cert=str(root / 'credentials/controller/client.crt'),
                controller_key=str(root / 'credentials/controller/client.key'), browser_profile='N', rf_family='R3')
    save(target / 'load.json', plan)
    pid = fixture.value('systemctl', 'show', PREFIX + '-client', '-p', 'MainPID', '--value')
    commands = dict(
        observer=['python3', str(root / 'scripts/phase11_5_rf_observer.py'), '--packet', str(target / 'jobs.json'),
                  '--baseline', rf['baseline'], '--output', str(target / 'usb-health.jsonl'),
                  '--session-id', secrets.token_hex(16), '--seconds', '360', '--run'],
        load=['nsenter', '-t', pid, '-m', '-n', 'python3', packet['production_driver'],
              '--root', str(target), '--seconds', '300', '--boot', device.state['boot'], '--run'],
        pressure=['nsenter', '-t', pid, '-m', '-n', 'python3', str(root / 'scripts/phase11_5_r3_tls_pressure.py'),
                  '--root', str(target), '--run'])
    save(target / 'execution.json', commands)
    processes, streams = {}, []
    result = dict(status='FAILED')

    def start(label):
        stream = (target / (label + '.log')).open('x')
        streams.append(stream)
        processes[label] = subprocess.Popen(commands[label], stdout=stream, stderr=subprocess.STDOUT)

    def wait_file(name, label, seconds):
        end = time.monotonic() + seconds
        while not (target / name).exists():
            require(time.monotonic() < end and processes[label].poll() is None, 'R3 worker readiness: ' + label)
            require(processes['observer'].poll() is None, 'Observer failed during worker readiness')
            time.sleep(.05)

    try:
        start('observer')
        wait_file('observer-info.json', 'observer', 5)
        wait_file('observer-status.json', 'observer', 5)
        start('load')
        wait_file('ready.json', 'load', 45)
        start('pressure')
        limit = time.monotonic() + 375
        while any(p.poll() is None for p in processes.values()):
            require(time.monotonic() < limit, 'R3 worker deadline')
            failed = [label for label, p in processes.items() if p.poll() not in (None, 0)]
            if failed:
                save(target / 'load-failed.json', dict(workers=failed))
                # Leave the sole USB observer running to its original deadline.
                # It stops future mutation after this marker; output is not inferred.
                for label in ('pressure', 'load'):
                    if processes[label].poll() is None:
                        processes[label].terminate()
            time.sleep(.1)
        require(all(p.returncode == 0 for p in processes.values()), 'R3 worker failed; no retry')
        result['status'] = 'CAPTURED_REQUIRES_AUDIT'
    finally:
        if any(p.poll() is None for p in processes.values()):
            save(target / 'load-failed.json', dict(source='supervisor cleanup'))
        for label, process in processes.items():
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            result[label + '_exit'] = process.returncode
        for stream in streams:
            stream.close()
        save(target / 'result.json', result)
    value = audit(target, root / 'pi/phase115_tls_observer_test.py')
    save(target / 'audit.json', value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--packet-sha256', required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        print('Plan only; no host/device access. A new R3 hardware grant is required.')
        return
    require(os.geteuid() == 0, 'wspr5 root required')
    os.umask(0o077)
    root = args.root.resolve(strict=True)
    require(digest(root / 'packet.json') == args.packet_sha256, 'Frozen R3 packet changed')
    packet = json.loads((root / 'packet.json').read_text())
    validate_scope(packet)
    require(not (root / 'r3-result.json').exists(), 'R3 packet already consumed')
    DeviceFixture(root).verify_helpers()
    require(set(packet['case_helper_sha256']) == CASE_HELPERS, 'R3 complete helper manifest')
    require(set(packet['production_helper_sha256']) == {'pi/phase115_production_load.py',
            'pi/phase115_tls_observer.c', 'pi/phase115_tls_observer_test.py'}, 'R3 production helper manifest')
    for group in ('case_helper_sha256', 'production_helper_sha256', 'private_input_sha256'):
        for relative, sha in packet[group].items():
            require((root / relative).resolve().is_relative_to(root) and digest(root / relative) == sha,
                    'R3 staged input changed')
    for key in ('production_binary', 'production_observer'):
        require(digest(Path(packet[key])) == packet[key + '_sha256'], 'Production artifact changed')
    require(digest(root / 'production.ini') == packet['production_ini_sha256'], 'Production INI changed')
    prior = packet['prior_restored_attempt']
    for name, key in (('device-state.json', 'device_state_sha256'),
                      ('management-state.json', 'management_state_sha256')):
        require(digest(Path(prior['root']) / name) == prior[key], 'Prior restored evidence changed')
    previous = json.loads((Path(prior['root']) / 'management-state.json').read_text())
    require(previous['counts'] == packet['initial_management_counts'] and not previous.get('pending')
            and not previous.get('blocked'), 'R3 inherited management state')
    # Validate the controller's RF-off contract before any fixture or USB action.
    import importlib.util
    spec = importlib.util.spec_from_file_location('r3_pi_load', root / 'pi/phase115_production_load.py')
    import sys
    sys.path.insert(0, str(root / 'pi'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate_ini(root / 'production.ini')
    result = dict(status='RUNNING', family='R3', tranche='A1', family_closed=False,
                  completed_jobs=0, packet_sha256=args.packet_sha256)

    def run(label, argv, timeout):
        result['stage'] = label
        save(root / 'r3-result.json', result)
        with (root / (label + '.log')).open('x') as stream:
            code = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout).returncode
        require(code == 0, 'R3 stage failed: ' + label)

    def device(action):
        run('device-' + action, ['python3', str(root / 'scripts/phase11_5_device_fixture.py'), action,
                                 '--root', str(root), '--run'], 180)

    try:
        run('host-setup', ['python3', str(root / 'scripts/phase11_5_network_fixture.py'), 'setup',
                           '--root', str(root), '--run'], 330)
        fixture = Fixture(root)
        fixture.verify()
        fixture_admission(fixture, root, 'r3-time-admission')
        device('start')
        device('switch')
        dut = DeviceFixture(root)
        for index in range(19):
            current = dut.check_current('r3-ready-' + str(index))
            if (current['wtp']['GET_CLOCK']['state'] == 'synchronized'
                    and current['info']['network']['ipv4'] == '10.77.15.10'
                    and current['info']['network']['ntp_address'] == '10.77.15.1'):
                break
            require(index < 18, 'R3 clock/network readiness')
            time.sleep(5)
        require(time.monotonic_ns() + 450_000_000_000 < dut.state['deadline_monotonic_ns'],
                'R3 observation and restoration reserve')
        result['a1'] = run_packet(root, packet, dut, fixture)
        result.update(status='PASS_REQUIRES_FINAL_REVIEW', completed_jobs=2)
    except BaseException as error:
        result.update(status='FAILED', error=type(error).__name__ + ': ' + str(error))
    finally:
        if (root / 'device-state.json').exists():
            try:
                device('restore')
                counts = json.loads((root / 'management-state.json').read_text())['counts']
                result['final_management_counts'] = counts
                if result['completed_jobs'] == 2:
                    require(counts == dict(config=36, **{'wifi-off': 0, 'wifi-on': 0, 'heap-probe': 6}),
                            'R3 final cumulative counts')
                result['device_restored'] = True
            except BaseException as error:
                result['restore_error'] = str(error)
        if (root / 'fixture-state.json').exists():
            try:
                run('host-cleanup', ['python3', str(root / 'scripts/phase11_5_network_fixture.py'), 'cleanup',
                                     '--root', str(root), '--run'], 600)
                result['host_restored'] = True
            except BaseException as error:
                result['host_restore_error'] = str(error)
        save(root / 'r3-result.json', result)
    require(result['status'] == 'PASS_REQUIRES_FINAL_REVIEW' and result.get('device_restored')
            and result.get('host_restored'), 'R3 incomplete; preserve evidence and reconcile')


if __name__ == '__main__':
    main()
