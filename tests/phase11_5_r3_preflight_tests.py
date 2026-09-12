"""Hardware-free negative evidence tests for R3 admission; no sockets or USB."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import phase11_5_r3_preflight as preflight
from validate_wtp_contract import frame


def fixture(label='A'):
    board = preflight.BOARDS[label]
    status = {'boot_id': board['prior_boot'], 'state': 'empty', 'output_active': False,
              'owner_id': None, 'job_id': None, 'terminal_records': []}
    info = {'ok': True, 'device_id': board['device_id'], 'revision': board['revision'],
            'recovery_boot': False, 'fault_stage': 0, 'fault_hash': 0, 'fault_pc': 0, 'fault_status': 0,
            'status': {**status, 'engine': 'inhibited-standalone-simulator', 'configured': True,
                       'enabled': False, 'last_error': None, 'storage_healthy': True,
                       'station': {}, 'schedules': [], 'watermark_utc_ns': '0'}}
    replies = {'HELLO': {'device_id': board['device_id'], 'boot_id': board['prior_boot'],
                        'selected_version': 'WTP/1', 'product': 'WsprryPico', 'firmware_version': 'test'},
               'CAPS': {'profiles': ['rf-events/1'], 'modes': ['wspr', 'tone', 'qrss', 'fskcw', 'dfcw'],
                        'engine': 'inhibited-standalone-simulator', 'max_events': 162,
                        'max_job_duration_ns': '110592000000', 'max_payload_bytes': 65536,
                        'frequency_ranges': [{'minimum_nhz': '100000000000000',
                                              'maximum_nhz': '68999999000000000'}],
                        'minimum_arm_lead_ns': '100000000', 'maximum_arm_ahead_ns': '604800000000000',
                        'maximum_arm_uncertainty_ns': '500000000', 'maximum_holdover_age_ns': '90000000000',
                        'output_disable_timeout_ns': '100000000', 'minimum_lease_ms': 5000,
                        'maximum_lease_ms': 60000, 'response_cache_entries': 8,
                        'response_cache_ttl_seconds': 300, 'terminal_record_entries': 8,
                        'terminal_record_ttl_seconds': 3600},
               'GET_CLOCK': {'state': 'synchronized', 'utc_now_ns': '1000000000',
                             'monotonic_now_ns': '500000000', 'uncertainty_ns': '1000',
                             'sync_age_ns': '1000', 'leap': 'normal'}, 'STATUS': status,
               'PING': {}}
    rows = []

    def note(kind, value):
        rows.append({'kind': kind, 'value': value, 'sequence': len(rows),
                     'serial': board['serial'], 'utc_ns': 1_000_000_000 + len(rows),
                     'monotonic_ns': 1_000_000_000 + len(rows)})

    note('start', {'source_sha256': 'a' * 64})
    note('tx', {'hex': b'INFO\n'.hex()})
    wire = (json.dumps(info) + '\n').encode()
    note('rx', {'hex': wire[:70].hex()})
    note('rx', {'hex': wire[70:].hex()})
    note('info', info)
    for n, op in enumerate(preflight.OPERATIONS):
        request = {'type': 'request', 'protocol': 'WTP/1', 'op': op,
                   'session_id': ('1' if label == 'A' else '2') * 32,
                   'request_id': f'{n + 1:032x}',
                   'body': {'versions': ['WTP/1'], 'client_name': 'phase11-5-inventory',
                            'client_version': '1'} if op == 'HELLO' else {}}
        note('tx', {'hex': frame(json.dumps(request).encode()).hex()})
        response = {**request, 'type': 'response', 'ok': True, 'body': replies[op]}
        wire = frame(json.dumps(response).encode())
        note('rx', {'hex': wire[:19].hex()})
        note('rx', {'hex': wire[19:].hex()})
        note('response', response)
    note('finish', {'result': 'READ_ONLY_INVENTORY', 'info': info, 'wtp': replies})
    return rows


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.packet = preflight.plan(REPO, {'A': '1' * 32, 'B': '2' * 32})

    def audit_rows(self, rows, label='A'):
        path = self.root / 'inventory.jsonl'
        path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        return preflight.audit_inventory(path, preflight.BOARDS[label],
                                         self.packet['sessions'][label], 'a' * 64)

    def test_fragmented_intact_wire(self):
        self.assertEqual(self.audit_rows(fixture())['wtp']['CAPS']['max_events'], 162)

    def test_raw_mutations_rejected_and_intact_rechecked(self):
        def raw_operation(rows):
            request = preflight.decode_frame(bytes.fromhex(rows[5]['value']['hex']))
            request['op'] = 'ABORT'
            rows[5]['value']['hex'] = frame(json.dumps(request).encode()).hex()

        def response_identity(rows):
            response = copy.deepcopy(rows[8]['value'])
            response['session_id'] = '9' * 32
            wire = frame(json.dumps(response).encode())
            rows[6]['value']['hex'], rows[7]['value']['hex'] = wire[:19].hex(), wire[19:].hex()
            rows[8]['value'] = response

        mutations = {
            'missing_record': lambda r: r.pop(6),
            'duplicate_record': lambda r: r.insert(6, copy.deepcopy(r[6])),
            'wrong_serial': lambda r: r[0].update(serial=preflight.BOARDS['B']['serial']),
            'source_mixing': lambda r: r[0]['value'].update(source_sha256='b' * 64),
            'summary_only_pass': lambda r: r[-1]['value']['wtp']['CAPS'].update(max_events=512),
            'console_write': lambda r: r[1]['value'].update(hex=b'CONFIG {}\n'.hex()),
            'forbidden_wtp': raw_operation,
            'foreign_reply': response_identity,
            'partial_wire': lambda r: r[7]['value'].update(hex=r[7]['value']['hex'][:-2]),
            'corrupt_crc': lambda r: r[6]['value'].update(hex='00' + r[6]['value']['hex'][2:]),
            'reversed_time': lambda r: r[8].update(monotonic_ns=0),
            'bool_sequence': lambda r: r[0].update(sequence=False),
            'late_reply': lambda r: r[8].update(monotonic_ns=10_000_000_000),
            'extra_traffic': lambda r: r.insert(-1, copy.deepcopy(r[5])),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                # Break object aliases so a dishonest summary edit cannot also
                # edit the independently captured INFO/response objects.
                rows = json.loads(json.dumps(fixture()))
                mutate(rows)
                with self.assertRaises((ValueError, KeyError)):
                    self.audit_rows(rows)
        self.audit_rows(fixture())

    def test_missing_newline_rejected(self):
        path = self.root / 'bad.jsonl'
        path.write_text('\n'.join(json.dumps(r) for r in fixture()))
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            preflight.audit_inventory(path, preflight.BOARDS['A'], '1' * 32, 'a' * 64)

    def test_exact_packet_rejects_scope_and_budget_changes(self):
        preflight.validate(self.packet, REPO)
        changes = {'additional_config_writes': 2, 'additional_heap_probes': 1,
                   'fixture_activation': True, 'runtime_seconds': 301,
                   'inventory_seconds': True, 'rf_jobs': [{}], 'root': '/tmp/elsewhere',
                   'schema': 'phase11.5-r2-modes-v1', 'new_field': 'ignored?'}
        for key, value in changes.items():
            with self.subTest(key=key):
                packet = copy.deepcopy(self.packet)
                packet[key] = value
                with self.assertRaises(ValueError):
                    preflight.validate(packet, REPO)

    def test_retained_counts_cannot_reset(self):
        self.packet['management_counts'] = {key: 0 for key in preflight.COUNTS}
        with self.assertRaises(ValueError):
            preflight.validate(self.packet, REPO)

    def test_session_reuse_without_cross_board_identity(self):
        self.packet['sessions']['B'] = self.packet['sessions']['A']
        with self.assertRaises(ValueError):
            preflight.validate(self.packet, REPO)

    def values(self):
        return {name: copy.deepcopy(fixture(name[-1])[-1]['value']) for name in preflight.ORDER}

    def test_good_capture_never_closes_acceptance(self):
        result = preflight.assess(self.values(), self.packet)
        self.assertEqual(result['status'], 'READ_ONLY_ADMISSION_CAPTURED')
        self.assertEqual(result['R3_acceptance_assertions_completed'], 0)
        self.assertEqual(result['accepted_configurations'], [])

    def campaign(self):
        self.packet['helper_sha256']['scripts/phase11_5_inventory.py'] = 'a' * 64
        (self.root / 'packet.json').write_text(json.dumps(self.packet))
        (self.root / 'run-intent.json').write_text(json.dumps({
            'packet_sha256': preflight.digest(self.root / 'packet.json'),
            'host_boot_id': preflight.HOST_BOOT, 'started_ns': 1_000_000_000}))
        for index, name in enumerate(preflight.ORDER):
            rows = fixture(name[-1])
            for row in rows:
                row['monotonic_ns'] += index * 1_000_000_000
            # Independent second inventories use fresh requests, same sessions.
            if name.startswith('after'):
                for row in rows:
                    if row['kind'] in ('tx', 'rx'):
                        continue
                    if row['kind'] == 'response':
                        row['value']['request_id'] = f'{int(row["value"]["request_id"], 16) + 10:032x}'
                for offset in range(5, 25, 4):
                    request = preflight.decode_frame(bytes.fromhex(rows[offset]['value']['hex']))
                    request['request_id'] = rows[offset + 3]['value']['request_id']
                    rows[offset]['value']['hex'] = frame(json.dumps(request).encode()).hex()
                    response = frame(json.dumps(rows[offset + 3]['value']).encode())
                    rows[offset + 1]['value']['hex'] = response[:19].hex()
                    rows[offset + 2]['value']['hex'] = response[19:].hex()
            (self.root / (name + '.jsonl')).write_text(''.join(json.dumps(r) + '\n' for r in rows))

    def test_campaign_binding_and_cross_capture_mutations(self):
        self.campaign()
        self.assertEqual(preflight.audit(self.root, self.packet)['status'], 'READ_ONLY_ADMISSION_CAPTURED')
        for mutation in ('swapped', 'replayed', 'packet', 'host'):
            with self.subTest(mutation=mutation):
                self.campaign()
                if mutation == 'swapped':
                    a, b = self.root / 'before-A.jsonl', self.root / 'after-A.jsonl'
                    original = a.read_bytes()
                    a.write_bytes(b.read_bytes())
                    b.write_bytes(original)
                elif mutation == 'replayed':
                    before = self.root / 'before-A.jsonl'
                    rows = [json.loads(s) for s in before.read_text().splitlines()]
                    for row in rows:
                        row['monotonic_ns'] += 2_000_000_000
                    (self.root / 'after-A.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
                else:
                    intent = preflight.read_json(self.root / 'run-intent.json')
                    intent['packet_sha256' if mutation == 'packet' else 'host_boot_id'] = 'wrong'
                    (self.root / 'run-intent.json').write_text(json.dumps(intent))
                with self.assertRaises(ValueError):
                    preflight.audit(self.root, self.packet)
        self.campaign()
        preflight.audit(self.root, self.packet)

    def test_active_unknown_fault_and_changed_boot_block(self):
        for case in ('active', 'unknown', 'fault', 'boot', 'prior_boot', 'config', 'caps'):
            with self.subTest(case=case):
                values = self.values()
                value = values['after-A']
                if case in ('active', 'unknown'):
                    value['wtp']['STATUS']['output_active'] = True if case == 'active' else None
                elif case == 'fault':
                    value['info']['fault_hash'] = 42
                elif case == 'boot':
                    value['wtp']['STATUS']['boot_id'] = 'f' * 32
                elif case == 'prior_boot':
                    for key in ('before-A', 'after-A'):
                        values[key]['wtp']['STATUS']['boot_id'] = 'f' * 32
                elif case == 'config':
                    value['info']['status']['watermark_utc_ns'] = '1'
                else:
                    value['wtp']['CAPS']['max_events'] = 512
                self.assertEqual(preflight.assess(values, self.packet)['status'], 'BLOCKED')

    def test_prepare_is_offline_exclusive_and_run_requires_flag(self):
        command = [sys.executable, str(REPO / 'scripts/phase11_5_r3_preflight.py')]
        result = subprocess.run(command + ['prepare', '--root', str(self.root)],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        repeated = subprocess.run(command + ['prepare', '--root', str(self.root)], capture_output=True)
        self.assertNotEqual(repeated.returncode, 0)
        attempt = subprocess.run(command + ['run', '--root', str(self.root),
                                           '--packet-sha256', result.stdout.strip()],
                                 text=True, capture_output=True)
        self.assertNotEqual(attempt.returncode, 0)
        self.assertIn('Explicit authorization', attempt.stderr)
        self.assertFalse((self.root / 'run-intent.json').exists())


if __name__ == '__main__':
    unittest.main()
