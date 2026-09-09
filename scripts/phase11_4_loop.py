#!/usr/bin/env python3
"""Opt-in Mac coordinator for bounded, independently supervised B2/D2 cases."""
import argparse
import io
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import shlex
import subprocess
import sys
import tarfile
import threading
import time

from phase11_4_loop_common import NAME, ADDRESS, campaign_decision, stop_process


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--credentials', required=True, type=Path)
    p.add_argument('--boot', required=True)
    p.add_argument('--ssh', default='wspr5')
    p.add_argument('--ssh-address', default='192.168.1.117')
    p.add_argument('--max-cases', default=8, type=int)
    p.add_argument('--run', action='store_true')
    a = p.parse_args()
    if not a.run or not 1 <= a.max_cases <= 8:
        p.error('Explicit --run and 1..8 cases required')
    os.umask(0o077)
    a.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    sources = Path(__file__).resolve().parent
    remote = '/home/pi/phase11-4-acceptance/loop-' + str(time.time_ns())
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
           '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2',
           '-o', 'Hostname=' + a.ssh_address, '-o', 'HostKeyAlias=wspr5.local', a.ssh]

    def remote_call(args, **kwargs):
        return subprocess.run(ssh + [shlex.join(args)], timeout=35, check=True, **kwargs)

    remote_call(['mkdir', '-m', '700', remote], capture_output=True)
    names = ['phase11_4_loop_target.py', 'phase11_4_loop_common.py', 'check_usb_target.py',
             'rf_wtp.py', 'wtp_monitor.py', 'validate_wtp_contract.py']
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w') as archive:
        for name in names:
            archive.add(sources / name, arcname=name)
    remote_call(['tar', '-xf', '-', '-C', remote], input=buf.getvalue(), capture_output=True)
    (a.output / 'deployment.json').write_text(json.dumps({'remote': remote, 'boot': a.boot,
                                                       'argv': sys.argv, 'sources': {n: hashlib.sha256((sources/n).read_bytes()).hexdigest() for n in names}}, indent=2) + '\n')
    attempts = []
    decision = 'CONTINUE'
    for number in range(1, a.max_cases + 1):
        case = a.output / f'case-{number:02}'
        case.mkdir(mode=0o700)
        master, slave = pty.openpty()
        dns = subprocess.Popen(['/usr/bin/dns-sd', '-G', 'v4', NAME],
                               stdout=slave, stderr=slave)
        os.close(slave)
        stop = threading.Event()
        observer_errors = []
        native_ready = threading.Event()
        peer_ready = threading.Event()
        def observe_dns():
            data = b''
            try:
                with (case / 'mac-dns-sd.jsonl').open('x') as log:
                    while not stop.is_set():
                        if select.select([master], [], [], .2)[0]:
                            part = os.read(master, 4096)
                            if not part:
                                raise RuntimeError('native DNS observer EOF')
                            log.write(json.dumps({'epoch_ns': time.time_ns(),
                                                  'text': part.decode(errors='replace')}) + '\n')
                            log.flush()
                            os.fsync(log.fileno())
                            data += part
                            if ADDRESS.encode() in data and b'Add' in data:
                                native_ready.set()
                            data = data[-8192:]
                        if dns.poll() is not None:
                            raise RuntimeError('native DNS observer exited')
            except Exception as e:
                observer_errors.append('native DNS: ' + str(e))

        def observe_peer():
            try:
                with (case / 'mac-peer.jsonl').open('x') as log:
                    while not stop.is_set():
                        r = subprocess.run([sys.executable, '-B', str(sources / 'phase11_4_loop_peer.py'),
                                            '--run', '--credentials', str(a.credentials.resolve()),
                                            '--boot', a.boot], capture_output=True, text=True, timeout=22)
                        if r.returncode:
                            raise RuntimeError('Mac peer subprocess: ' + r.stderr)
                        row = json.loads(r.stdout)
                        log.write(json.dumps(row) + '\n')
                        log.flush()
                        os.fsync(log.fileno())
                        if row['dns_ok'] and row['https_ok']:
                            peer_ready.set()
                        stop.wait(8)
            except Exception as e:
                observer_errors.append('Mac peer: ' + str(e))
        threads = [threading.Thread(target=f, daemon=True) for f in (observe_dns, observe_peer)]
        for t in threads:
            t.start()
        unit = 'pico-b2-d2-' + str(time.time_ns())
        dispatched = False
        completed = False
        supervision_error = None
        try:
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline and not (native_ready.is_set() and peer_ready.is_set()):
                if observer_errors:
                    raise RuntimeError(str(observer_errors))
                time.sleep(.2)
            if not (native_ready.is_set() and peer_ready.is_set()):
                raise RuntimeError('Mac baseline or observer readiness failed; no target mutation')
            runner_log = remote + f'/runner-{number:02}.log'
            remote_case = remote + f'/case-{number:02}'
            remote_call(['sudo', '-n', 'systemd-run', '--unit=' + unit,
                         '--property=RuntimeMaxSec=480', '--property=TimeoutStopSec=20',
                         '--property=KillMode=control-group',
                         '--property=StandardOutput=append:' + runner_log,
                         '--property=StandardError=append:' + runner_log,
                         '/usr/bin/python3', '-B', remote + '/phase11_4_loop_target.py',
                         'orderly', '--run', '--output', remote_case, '--boot', a.boot],
                        capture_output=True)
            dispatched = True
            print(json.dumps({'case': number, 'event': 'STARTED', 'unit': unit}), flush=True)
            deadline = time.monotonic() + 510
            while time.monotonic() < deadline:
                if observer_errors:
                    raise RuntimeError(str(observer_errors))
                r = remote_call(['systemctl', 'show', unit, '--property=ActiveState,SubState,Result,ExecMainStatus'],
                                capture_output=True, text=True)
                (case / 'service-state.txt').write_text(r.stdout)
                if 'ActiveState=inactive' in r.stdout or 'ActiveState=failed' in r.stdout:
                    completed = True
                    break
                stop.wait(4)
            else:
                raise TimeoutError('independent Linux supervisor exceeded bound')
        except Exception as e:
            supervision_error = type(e).__name__ + ': ' + str(e)
            observer_errors.append(supervision_error)
        finally:
            if dispatched and not completed:
                # Even a lost SSH session cannot remove the remote systemd deadline.
                try:
                    remote_call(['sudo', '-n', 'systemctl', 'stop', unit], capture_output=True)
                except Exception as e:
                    observer_errors.append('remote stop: ' + str(e))
            stop.set()
            for t in threads:
                t.join(timeout=24)
            if any(t.is_alive() for t in threads):
                observer_errors.append('observer thread did not stop')
            (case / 'mac-dns-stop.json').write_text(json.dumps(stop_process(dns)) + '\n')
            os.close(master)
        if dispatched:
            evidence_fetched = False
            try:
                remote_call(['sudo', '-n', '/usr/bin/python3', '-B', remote + '/phase11_4_loop_target.py',
                             'inspect', '--run', '--output', remote + f'/inspect-{number:02}',
                             '--boot', a.boot], capture_output=True)
            except Exception as e:
                observer_errors.append('post-case USB inspection: ' + str(e))
            try:
                archive = remote_call(['sudo', '-n', 'tar', '-cf', '-', '-C', remote,
                                       f'case-{number:02}', f'runner-{number:02}.log', f'inspect-{number:02}'], capture_output=True).stdout
                (case / 'linux.tar').write_bytes(archive)
                with tarfile.open(fileobj=io.BytesIO(archive)) as t:
                    # Never follow links or accept traversal from an external archive.
                    for member in t.getmembers():
                        dest = (case / member.name).resolve()
                        if not dest.is_relative_to(case.resolve()) or not (member.isdir() or member.isfile()):
                            raise ValueError('unsafe evidence archive member')
                    t.extractall(case, filter='data')
                evidence_fetched = True
            except Exception as e:
                observer_errors.append('evidence fetch: ' + str(e))
            # Preserve the unit result and complete artifacts first. Clear only
            # this finished test unit's failed-state bookkeeping, never globally.
            state_file = case / 'service-state.txt'
            if evidence_fetched and state_file.exists() and 'ActiveState=failed' in state_file.read_text():
                try:
                    remote_call(['sudo', '-n', 'systemctl', 'reset-failed', unit], capture_output=True)
                    (case / 'unit-failed-state-cleared').write_text(unit + '\n')
                except Exception as e:
                    observer_errors.append('test unit bookkeeping cleanup: ' + str(e))
        from phase11_4_loop_audit import assess_case
        assessment = assess_case(case, a.boot)
        assessment['observer_failure'] = bool(observer_errors) or assessment['observer_failure']
        assessment['observer_errors'] = observer_errors
        if assessment['observer_failure']:
            assessment['result'] = 'INVALID'
        attempts.append(assessment)
        (case / 'assessment.json').write_text(json.dumps(assessment, indent=2) + '\n')
        decision = campaign_decision(attempts)
        report = {'decision': decision, 'attempts': attempts, 'remote': remote,
                  'bound': {'clean_cases_required': 8, 'unresolved_failures_limit': 3,
                            'max_cases': a.max_cases}}
        (a.output / 'campaign.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'case': number, 'result': assessment['result'], 'decision': decision,
                          'failure_point': assessment.get('failure_point')}), flush=True)
        if decision != 'CONTINUE':
            break
    if decision == 'CONTINUE':
        report['decision'] = 'HARNESS_INEFFECTIVE'
        report['reason'] = 'Case budget exhausted without a qualifying conclusion'
        (a.output / 'campaign.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
