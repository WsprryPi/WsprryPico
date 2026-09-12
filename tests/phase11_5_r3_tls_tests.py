"""Hardware-free R3 bounds, fail-closed admission and adversarial evidence tests."""
import copy
import hashlib
import io
import json
from pathlib import Path
import ssl
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase11_5_r3_tls_plan import (SCHEMA, SOURCE, PHYSICAL, COUNTS, MANAGEMENT_SCOPE,
                                  CASES, jobs, validate, validate_allowance)
from phase11_5_device_management import authorize, digest
from phase11_5_r2_usb_jobs import USBJobs
from phase11_5_r3_tls_pressure import Pressure, response, NAME, PEER
from audit_phase11_5_r3_tls import audit_pressure


def packet():
    return dict(schema=SCHEMA, source_revision=SOURCE, revision=SOURCE[:12], uf2_sha256=PHYSICAL,
                serial='0BF4B4AEC9FFB344', device_id='fd6127d11d6aca42a9905fa3fb1bf1d5',
                system_clock_hz=138000000, pio_divider=1, listener_enabled=True, rf_render_in_ram=True,
                boot_id='2' * 32, owner_id='3' * 32, nonce='1' * 32, submission_path='usb',
                nominal_seconds=300, browser_profile='N', ordinary_browser=False, maximum_renewals=12,
                jobs=jobs('1' * 32), pressure_cases=[list(c) for c in CASES])


def status(p, job):
    return dict(boot_id=p['boot_id'], owner_id=p['owner_id'], job_id=job['job_id'],
                state='running', output_active=True)


def http_bytes(p, job, transport):
    body = json.dumps(dict(job=status(p, job), transport=transport)).encode()
    return b'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body


def evidence():
    p = packet()
    rows, usb = [], []
    now = 10_000_000_000
    transport = dict(active=2, pending=0, admitted=1, rejected=0, timeouts=0,
                     tls_allocation_failures=0)

    def add(kind, value, advance=10_000_000):
        nonlocal now
        now += advance
        rows.append(dict(sequence=len(rows), kind=kind, value=value, monotonic_ns=now))

    add('start', {})
    for index, job in enumerate(p['jobs']):
        now = (10 + index * 140) * 10**9
        for label in CASES[index]:
            began = now
            for kind in ('info', 'status'):
                value = status(p, job)
                usb.append(dict(kind=kind, monotonic_ns=began,
                                value=dict(value=dict(status=value) if kind == 'info' else value)))
            add('case_begin', dict(label=label, job_id=job['job_id']))
            labels = ['slot-active', 'slot-pending', 'slot-excess'] if label == 'slot-excess' else [label]
            for name in labels:
                add('tcp_open', dict(label=name, began_ns=now, peer=['10.77.15.10', 18443],
                                     local=['10.77.15.2', 40000 + len(rows)]))
            value = dict(label=label, job_id=job['job_id'], began_ns=began)
            if label not in ('silent-handshake', 'slot-excess', 'missing-certificate'):
                add('tls', dict(label=label, peer_sha256=PEER, version='TLSv1.3',
                                alpn='wtp/1' if label == 'duplicate-wtp' else 'http/1.1'))
            if label == 'positive' or label.startswith('recover-'):
                transport['admitted'] += 1 if label == 'positive' else 2
                transport['rejected'] += int(label == 'recover-slots')
                transport['timeouts'] += int(label == 'recover-handshake')
                wire = http_bytes(p, job, transport)
                request = f'GET /api/v1/status HTTP/1.1\r\nHost: {NAME}:18443\r\nConnection: close\r\n\r\n'.encode()
                add('http', dict(label=label, request_hex=request.hex(), response_hex=wire.hex()))
                value['transport'] = copy.deepcopy(transport)
            elif label == 'missing-certificate':
                value.update(alert=116, reason='TLSV13_ALERT_CERTIFICATE_REQUIRED', library='SSL')
            else:
                value['close'] = 'eof'
                if label == 'slot-excess':
                    value['client_closed_supported_slots'] = True
            add('case_finish', value)
            for kind in ('info', 'status'):
                v = status(p, job)
                usb.append(dict(kind=kind, monotonic_ns=now + 10_000_000,
                                value=dict(value=dict(status=v) if kind == 'info' else v)))
            now += 500_000_000
    add('finish', dict(status='CAPTURED_REQUIRES_AUDIT', connections=12))
    return p, rows, usb


class R3Tests(unittest.TestCase):
    def test_exact_finite_jobs_and_caps_dispatch(self):
        from phase11_5_f1_plan import validate_rf_packet, admit_caps
        p = packet()
        validate_rf_packet(p)
        self.assertEqual(sum(int(j['total_duration_ns']) for j in p['jobs']), 200_000_000_000)
        caps = dict(modes=['tone'], profiles=['rf-events/1'], max_events=162,
                    max_job_duration_ns='110592000000', frequency_ranges=[
                        dict(minimum_nhz='100000000000000', maximum_nhz='200000000000000')])
        admit_caps(p, caps)
        caps['max_job_duration_ns'] = '99000000000'
        with self.assertRaises(ValueError):
            admit_caps(p, caps)
        for change in (lambda v: v['jobs'][0].update(total_duration_ns='110592000000'),
                       lambda v: v.update(source_revision='f' * 40), lambda v: v.update(pio_divider=True),
                       lambda v: v['pressure_cases'][0].append('rogue-certificate'),
                       lambda v: v.update(ordinary_browser=True), lambda v: v.update(maximum_renewals=13),
                       lambda v: v.update(nonce='0' * 32), lambda v: v.update(system_clock_hz=150000000)):
            bad = copy.deepcopy(p)
            change(bad)
            with self.assertRaises(ValueError):
                validate(bad)

    def test_cumulative_allowance_cannot_widen_old_packets(self):
        state = dict(source_revision=SOURCE, pending=None, blocked=False, counts=copy.deepcopy(COUNTS),
                     deadline_monotonic_ns=2_000_000_000)
        with patch('phase11_5_device_management.time.monotonic_ns', return_value=10**9):
            with self.assertRaises(ValueError):
                authorize(state, 'config', 'test')
            state['management_scope'] = MANAGEMENT_SCOPE
            authorize(state, 'config', 'test')
            for action, argument in (('heap-probe', None), ('wifi-off', None), ('wifi-on', None),
                                     ('config', 'schedule-variant')):
                with self.assertRaises(ValueError):
                    authorize(state, action, argument)
            state['counts']['config'] = 35
            with self.assertRaises(ValueError):
                authorize(state, 'config', 'test')
            authorize(state, 'config', 'original')
            state['counts']['config'] = 36
            with self.assertRaises(ValueError):
                authorize(state, 'config', 'original')
            state['counts']['config'] = 35
            state['pending'] = {'unknown': True}
            with self.assertRaises(ValueError):
                authorize(state, 'config', 'original')

    def test_r3_allowance_requires_specific_scope(self):
        p = dict(family='R3', r3_scope=SCHEMA, source_revision=SOURCE, management_scope=MANAGEMENT_SCOPE,
                 initial_management_counts=COUNTS, max_configuration_writes=36, max_idle_heap_probes=0,
                 time_server_mdns=True)
        validate_allowance(p)
        for key, value in [('family', 'R2'), ('r3_scope', 'R3'), ('max_configuration_writes', 37),
                           ('max_idle_heap_probes', 6), ('management_scope', None)]:
            with self.assertRaises(ValueError):
                validate_allowance(dict(p, **{key: value}))

    def test_no_run_never_resolves_root(self):
        import phase11_5_r3_tls as runner
        import phase11_5_r3_tls_pressure as pressure
        for module, args in ((runner, ['--packet-sha256', 'absent']), (pressure, [])):
            with patch.object(sys, 'argv', ['r3', '--root', '/absent'] + args), \
                    patch.object(module.Path, 'resolve', side_effect=AssertionError('file access')):
                module.main()

    def test_usb_waits_for_matching_pressure_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            p = packet()
            (root / 'jobs.json').write_text(json.dumps(p))
            (root / 'ready.json').write_text(json.dumps(dict(boot_id=p['boot_id'], start_monotonic_ns=0)))
            actor = USBJobs(p, root, None, None, None)
            idle = dict(state='empty', owner_id=None, output_active=False)
            with patch('phase11_5_r2_usb_jobs.time.monotonic_ns', return_value=10**9):
                actor.observe(idle)
                self.assertEqual(actor.phase, 'idle')
                (root / 'pressure-ready.json').write_text(json.dumps(dict(packet_sha256='wrong')))
                with self.assertRaises(ValueError):
                    actor.observe(idle)
                actor.index = 1
                actor.observe(idle)
                (root / 'pressure-job-0.json').write_text(json.dumps(dict(packet_sha256=digest(root / 'jobs.json'),
                                                                        status='FAILED', job_id=p['jobs'][0]['job_id'])))
                with self.assertRaises(ValueError):
                    actor.observe(idle)
                (root / 'load-failed.json').write_text('{}')
                actor.observe(idle)
                self.assertTrue(actor.blocked)

    def test_complete_pressure_evidence(self):
        value = audit_pressure(*evidence())
        self.assertEqual(len(value['cases']), 10)
        self.assertEqual(value['https_controls'], 6)

    def test_evidence_mutations_fail_and_intact_passes_again(self):
        def change_http(rows):
            row = next(r for r in rows if r['kind'] == 'http')
            wire = bytes.fromhex(row['value']['response_hex']).replace(b'"active": 2', b'"active": 1')
            row['value']['response_hex'] = wire.hex()

        mutations = [
            lambda p, r, u: r.pop(),
            lambda p, r, u: r[1]['value'].update(job_id='f' * 32),
            lambda p, r, u: next(v for v in r if v['kind'] == 'tls')['value'].update(peer_sha256='f' * 64),
            lambda p, r, u: next(v for v in r if v['kind'] == 'tcp_open')['value'].update(peer=['192.168.1.1', 18443]),
            lambda p, r, u: next(v for v in r if v['kind'] == 'http')['value'].update(request_hex=b'POST /api/v1/jobs'.hex()),
            lambda p, r, u: change_http(r),
            lambda p, r, u: next(v for v in r if v['kind'] == 'case_finish' and v['value']['label'] == 'missing-certificate')['value'].update(reason='UNEXPECTED_EOF_WHILE_READING'),
            lambda p, r, u: next(v for v in r if v['kind'] == 'case_finish' and v['value']['label'] == 'recover-handshake')['value']['transport'].update(timeouts=0),
            lambda p, r, u: next(v for v in r if v['kind'] == 'case_finish' and v['value']['label'] == 'slot-excess')['value'].update(client_closed_supported_slots=False),
            lambda p, r, u: u[0]['value']['value']['status'].update(output_active=False),
            lambda p, r, u: u[-1]['value']['value'].update(boot_id='f' * 32),
            lambda p, r, u: u.clear(),
            lambda p, r, u: r[-1]['value'].update(connections=13),
            lambda p, r, u: r[2].update(monotonic_ns=r[1]['monotonic_ns'] - 1),
        ]
        for mutation in mutations:
            data = evidence()
            mutation(*data)
            with self.assertRaises((ValueError, KeyError)):
                audit_pressure(*data)
        audit_pressure(*evidence())

    def test_http_framing_cannot_accept_truncation_duplicate_lengths_or_foreign_owner(self):
        p = packet()
        wire = http_bytes(p, p['jobs'][0], dict(active=2, pending=0))
        response(wire, p, p['jobs'][0])
        for bad in (wire[:-1], wire + b'x', wire.replace(b'Content-Length:', b'Content-Length: 1\r\nContent-Length:'),
                    wire.replace(('3' * 32).encode(), ('4' * 32).encode())):
            with self.assertRaises((ValueError, json.JSONDecodeError)):
                response(bad, p, p['jobs'][0])

    def test_missing_certificate_requires_exact_alert_not_generic_disconnect(self):
        p = object.__new__(Pressure)
        p.job = packet()['jobs'][0]
        p.emit = lambda *args: None
        p.checkpoint = lambda: None
        p.pause = lambda seconds: None
        for reason, accepted in [('TLSV13_ALERT_CERTIFICATE_REQUIRED', True),
                                 ('UNEXPECTED_EOF_WHILE_READING', False), ('CERTIFICATE_VERIFY_FAILED', False)]:
            error = ssl.SSLError(1, reason)
            error.reason = reason
            error.library = 'SSL'
            with patch.object(p, 'tls', side_effect=error):
                if accepted:
                    p.run_case('missing-certificate', None, None, None)
                else:
                    with self.assertRaises(ValueError):
                        p.run_case('missing-certificate', None, None, None)

    def test_recovery_counter_failure_prevents_pass_marker(self):
        p = object.__new__(Pressure)
        p.job = packet()['jobs'][0]
        emitted = []
        p.emit = lambda kind, value: emitted.append(kind)
        p.last_transport = dict(admitted=2, rejected=0, timeouts=0, tls_allocation_failures=0)
        p.positive = lambda *args: dict(admitted=4, rejected=0, timeouts=0, tls_allocation_failures=0)
        with self.assertRaisesRegex(ValueError, 'Target counters'):
            p.run_case('recover-handshake', None, None, None)
        self.assertNotIn('case_finish', emitted)

    def test_pressure_checkpoint_rejects_stale_foreign_or_dead_observer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            p = packet()
            packet_path = root / 'jobs.json'
            packet_path.write_text(json.dumps(p))
            probe = object.__new__(Pressure)
            probe.root, probe.packet, probe.packet_path = root, p, packet_path
            probe.sha, probe.observer, probe.job, probe.deadline = digest(packet_path), None, p['jobs'][0], 20
            originals = {}
            for kind in ('info', 'status'):
                value = status(p, p['jobs'][0])
                originals[kind] = dict(packet_sha256=probe.sha, pid=123, pid_start_ticks='567',
                                       monotonic_ns=10**9, value=dict(value=dict(status=value) if kind == 'info' else value))

            def restore():
                probe.observer = None
                for kind, value in originals.items():
                    (root / f'observer-{kind}.json').write_text(json.dumps(value))

            read = Path.read_text
            process_stat = '123 (observer) S ' + '0 ' * 18 + '567'
            with patch('phase11_5_r3_tls_pressure.time.monotonic', return_value=1), \
                    patch('phase11_5_r3_tls_pressure.time.monotonic_ns', return_value=10**9), \
                    patch.object(Path, 'read_text', lambda path, *a, **kw: process_stat
                                 if str(path) == '/proc/123/stat' else read(path, *a, **kw)):
                restore()
                probe.checkpoint()
                mutations = [lambda v: v.update(monotonic_ns=-2_000_000_000),
                             lambda v: v.update(packet_sha256='f' * 64),
                             lambda v: v.update(pid_start_ticks='568'),
                             lambda v: v['value']['value']['status'].update(boot_id='4' * 32),
                             lambda v: v['value']['value']['status'].update(output_active=False),
                             lambda v: v['value']['value']['status'].update(owner_id=None)]
                for mutation in mutations:
                    restore()
                    value = copy.deepcopy(originals['info'])
                    mutation(value)
                    (root / 'observer-info.json').write_text(json.dumps(value))
                    with self.assertRaises(ValueError):
                        probe.checkpoint()
                restore()
                (root / 'observer-failure.json').write_text('{}')
                with self.assertRaises(ValueError):
                    probe.checkpoint()

    def test_stager_checks_all_bytes_before_creating_root_and_refuses_replay(self):
        from phase11_5_r3_tls_stage import unpack
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            target = parent / 'stage'
            source = parent / 'private'
            source.write_bytes(b'private fixture input')
            own_sha = hashlib.sha256(b'helper').hexdigest()
            p = dict(root=str(target), r3_scope=SCHEMA,
                     stage_sha256={'scripts/phase11_5_r3_tls_stage.py': own_sha},
                     remote_copy_inputs={'original-config.json': dict(path=str(source), sha256=digest(source))})

            def archive(extra=None):
                data = {'packet.json': json.dumps(p).encode(), 'scripts/phase11_5_r3_tls_stage.py': b'helper'}
                if extra:
                    data.update(extra)
                raw = io.BytesIO()
                with tarfile.open(fileobj=raw, mode='w') as tar:
                    for name, value in data.items():
                        entry = tarfile.TarInfo(name)
                        entry.size = len(value)
                        tar.addfile(entry, io.BytesIO(value))
                return raw.getvalue(), hashlib.sha256(data['packet.json']).hexdigest()

            for extra in ({'../escape': b'x'}, {'unknown': b'x'}):
                data, sha = archive(extra)
                with self.assertRaises(ValueError):
                    unpack(data, sha, target, own_sha)
                self.assertFalse(target.exists())
            data, sha = archive()
            source.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                unpack(data, sha, target, own_sha)
            self.assertFalse(target.exists())
            source.write_bytes(b'private fixture input')
            self.assertEqual(unpack(data, sha, target, own_sha)['status'], 'STAGED_ONLY')
            with self.assertRaises(ValueError):
                unpack(data, sha, target, own_sha)


if __name__ == '__main__':
    unittest.main()
