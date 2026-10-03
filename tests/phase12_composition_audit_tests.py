#!/usr/bin/env python3
"""Deterministic negative-path tests; synthesized records are not target evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase12_composition_audit as audit


def fixture(mode='consumer'):
    p = dict(schema='phase12-composition/1', board='B', engine=audit.ENGINE,
             mode=mode, carriers=audit.CARRIERS[mode], source_commit='a'*40,
             image_sha256='b'*64, device_id='c'*32, boot_id='d'*32,
             firmware='123456789abc', duration_s=7200, cadence_s=30,
             max_gap_s=45, pressure_cases=audit.PRESSURE, quiet_s=960,
             max_simulated_jobs=12, max_job_duration_s=60, rf_jobs=0,
             flash_cycles=0, heap_return_tolerance_bytes=1024,
             pool_return_tolerance=0, stack_min_margin_bytes=256, core0_stack_capacity_bytes=4096)
    sample = {k: p[k] for k in ('device_id', 'boot_id', 'firmware', 'engine')}
    sample.update(raw_info_sha256='e'*64, output_active=False, faults=[],
                  storage_healthy=True, guards_valid=True, allocation_failures=0,
                  pool_errors=0, heap_used_bytes=1000, pool_used=0,
                  stack_margin_bytes=512, sessions=0)
    e = dict(schema='phase12-composition-evidence/1',
             plan_sha256=hashlib.sha256(json.dumps(p, sort_keys=True,
                 separators=(',', ':')).encode()).hexdigest(),
             samples=[dict(sample, elapsed_s=t) for t in range(0, 7201, 30)],
             quiet_duration_s=960, quiet_network_requests=0, final_state='empty',
             final_owner=None, final_job=None, provisioning_closed=True,
             simulated_jobs=6, longest_job_s=6, rf_jobs=0, flash_cycles=0,
             coverage={c: dict(wire_identity_verified=True,
                 principal_isolation_verified=True, artifact_sha256='f'*64,
                 states=['loaded', 'armed', 'running']) for c in p['carriers']},
             pressure={c: dict(passed=True, artifact_sha256='f'*64)
                       for c in audit.PRESSURE})
    return p, e


original_validate = audit.validate_evidence


def authority_fixture(p):
    from wsprrypico_ble import wtp_frame
    exchanges=[]
    for index, op in enumerate(('HELLO','STATUS')):
        request=dict(type='request',protocol='WTP/1',session_id='1'*32,
                     request_id=str(index+2)*32,op=op,
                     body={'versions':['WTP/1']} if op=='HELLO' else {})
        body=dict(selected_version='WTP/1',device_id=p['device_id'],boot_id=p['boot_id']) if op=='HELLO' else dict(
            boot_id=p['boot_id'],state='empty',owner_id=None,job_id=None,output_active=False)
        response=dict(request,type='response',ok=True,body=body)
        exchanges.append(dict(request_hex=wtp_frame(request).hex(),response_hex=wtp_frame(response).hex()))
    return dict(schema='phase12-final-authority/1',carrier=p['carriers'][0],
                elapsed_start_s=7200,elapsed_end_s=7201,exchanges=exchanges)


def write_authority(root,p):
    path=root/'authority.json';path.write_text(json.dumps(authority_fixture(p)))
    return dict(artifact_path=path.name,artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest())

def with_artifacts(p, e):
    from phase12_composition_capture_tests import info
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        raw = info(p)
        raw['status'].pop('owner_id',None);raw['status'].pop('job_id',None)
        raw['lan_wtp_mode'] = 'plain' if p['mode'] == 'consumer' else 'engineering-tls'
        raw.update(heap_allocated_bytes=1000, core0_stack_used_bytes=3584,
                   softap_retained_sessions=0)
        wire = json.dumps(raw).encode()
        for index, sample in enumerate(e['samples']):
            path = root / ('info%d.json' % index)
            path.write_text(json.dumps(dict(kind='INFO', transport_raw=True,
                elapsed_start_s=sample['elapsed_s'], elapsed_end_s=sample['elapsed_s'],
                raw_info_hex=wire.hex(), raw_info_sha256=hashlib.sha256(wire).hexdigest(),
                info=raw)))
            sample['raw_info_path'] = path.name
            sample['raw_info_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        proof = root / 'proof.json'
        proof.write_text('{}')
        proofsha = hashlib.sha256(proof.read_bytes()).hexdigest()
        for record in list(e['coverage'].values()) + list(e['pressure'].values()):
            record.update(artifact_path='proof.json', artifact_sha256=proofsha)
        quiet = root / 'quiet.json'
        quiet.write_text(json.dumps(dict(start_s=1200, end_s=2160,
            network_requests=[], ble_requests=[], continuous_observation=True)))
        e['quiet_artifact'] = dict(artifact_path='quiet.json',
            artifact_sha256=hashlib.sha256(quiet.read_bytes()).hexdigest())
        e['final_authority_artifact']=write_authority(root,p)
        return original_validate(p, e, root)

# Synthetic artifact files exercise binding; they grant no target evidence.



class AuditTests(unittest.TestCase):
    def test_counter_canonical_and_range(self):
        for raw, expected in ((0, 0), ('0', 0), ('123', 123),
                              ('18446744073709551615', 18446744073709551615)):
            self.assertEqual(audit.counter(raw, 'counter'), expected)
        for raw in (True, False, -1, '-1', '-0', '+0', '00', '01', ' 0',
                    '0 ', '0.0', 0.0, '', '٠', '18446744073709551616',
                    18446744073709551616, None):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                audit.counter(raw, 'counter')

    def test_modes_require_independent_coverage(self):
        for mode in audit.CARRIERS:
            p, e = fixture(mode)
            result = with_artifacts(p, e)
            self.assertFalse(result['physical_acceptance'])
            self.assertFalse(result['absolute_12h_deadline_covered'])
            del e['coverage'][p['carriers'][-1]]
            with self.assertRaises(KeyError):
                with_artifacts(p, e)

    def test_identity_faults_and_missing_evidence(self):
        for key, value in [('boot_id', '0'*32), ('output_active', True),
                           ('allocation_failures', 1), ('pool_errors', 1),
                           ('guards_valid', False), ('storage_healthy', False),
                           ('stack_margin_bytes', 128), ('faults', ['fault']),
                           ('heap_used_bytes', float('nan'))]:
            p, e = fixture()
            e['samples'][100][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                with_artifacts(p, e)

    def test_cadence_and_reclamation(self):
        for mutation in (lambda e: e['samples'].pop(100),
                         lambda e: e['samples'][-1].update(sessions=1),
                         lambda e: e['samples'][-1].update(heap_used_bytes=3000),
                         lambda e: e.update(quiet_network_requests=1),
                         lambda e: e.update(final_owner='owner'),
                         lambda e: e.update(rf_jobs=1)):
            p, e = fixture()
            mutation(e)
            with self.assertRaises(ValueError):
                with_artifacts(p, e)

    def test_plan_not_runtime_permission(self):
        for key, value in [('engine', 'pio-dma-gp2'), ('board', 'A'),
                           ('firmware', '123-dirty'), ('carriers', ['usb', 'tls_wtp']),
                           ('duration_s', 60), ('flash_cycles', 1),
                           ('heap_return_tolerance_bytes', 8192)]:
            p, _ = fixture()
            p[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                audit.validate_plan(p)

    def test_binding_and_pressure(self):
        p, e = fixture()
        changed = copy.deepcopy(p)
        changed['image_sha256'] = '0'*64
        with self.assertRaises(ValueError):
            with_artifacts(changed, e)
        e['pressure']['disconnect_reclaim']['passed'] = False
        with self.assertRaises(ValueError):
            with_artifacts(p, e)

    def test_normalizer_full_and_partial_capture(self):
        from phase12_composition_capture_tests import info
        p, e = fixture()
        raw = info(p)
        raw['status'].pop('owner_id',None);raw['status'].pop('job_id',None)
        raw.update(heap_allocated_bytes=1000, core0_stack_used_bytes=3584,
                   softap_retained_sessions=0)
        wire = json.dumps(raw).encode()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            proof = root / 'proof.json'
            proof.write_text('{}')
            sha = hashlib.sha256(proof.read_bytes()).hexdigest()
            quiet = root / 'quiet.json'
            quiet.write_text(json.dumps(dict(start_s=1200, end_s=2160,
                network_requests=[], ble_requests=[], continuous_observation=True)))
            metadata = {k: e[k] for k in ('coverage', 'pressure', 'simulated_jobs',
                         'longest_job_s', 'rf_jobs', 'flash_cycles')}
            for entry in list(metadata['coverage'].values()) + list(metadata['pressure'].values()):
                entry.update(artifact_path='proof.json', artifact_sha256=sha)
            metadata['quiet_artifact'] = dict(artifact_path='quiet.json',
                artifact_sha256=hashlib.sha256(quiet.read_bytes()).hexdigest())
            metadata['final_authority_artifact']=write_authority(root,p)
            meta = root / 'meta.json'
            meta.write_text(json.dumps(metadata))
            capture = root / 'capture.jsonl'
            records = [dict(kind='start', plan=p)] + [dict(kind='INFO', transport_raw=True,
                elapsed_start_s=t, elapsed_end_s=t, raw_info_hex=wire.hex(),
                raw_info_sha256=hashlib.sha256(wire).hexdigest(), info=raw)
                for t in range(0, 7201, 30)] + [dict(kind='complete', physical_acceptance=False)]
            capture.write_text('\n'.join(json.dumps(r) for r in records[:-1]))
            with self.assertRaises(ValueError):
                audit.normalize_capture(p, capture, meta, root, root / 'evidence.json')
            self.assertFalse((root / 'composition-info').exists())
            capture.write_text('\n'.join(json.dumps(r) for r in records))
            result = audit.normalize_capture(p, capture, meta, root, root / 'evidence.json')
            self.assertEqual(result['status'], 'RESOURCE_EVIDENCE_REVIEW_REQUIRED')
            self.assertTrue(result['independent_coverage_review_pending'])
            normalized = json.loads((root / 'evidence.json').read_text())
            self.assertEqual(len(normalized['samples']), 241)
            self.assertEqual(normalized['samples'][0]['allocation_failures'], 0)
            self.assertIs(type(normalized['samples'][0]['allocation_failures']), int)
            retained = json.loads((root / normalized['samples'][0]['raw_info_path']).read_text())
            self.assertEqual(retained['info']['allocator_failures'], '0')
            self.assertEqual(bytes.fromhex(retained['raw_info_hex']), wire)
            self.assertEqual(capture.read_text(), '\n'.join(json.dumps(r) for r in records))

    def test_artifact_hash_and_confinement(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / 'proof.json'
            path.write_text('{}')
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(audit.artifact(root, dict(artifact_path='proof.json',
                artifact_sha256=sha)), path.resolve())
            for name, hash_value in [('missing.json', sha),
                                     ('../outside.json', sha),
                                     ('proof.json', '0'*64)]:
                with self.assertRaises(ValueError):
                    audit.artifact(root, dict(artifact_path=name,
                                             artifact_sha256=hash_value))

    def test_authority_rejects_fake_uncorrelated_and_wrong_boot(self):
        from wsprrypico_ble import wtp_frame
        p,_=fixture()
        for mutation in ('crc','correlation','boot','owner','early','fake'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                root=Path(d);proof=authority_fixture(p)
                if mutation in ('correlation','boot','owner'):
                    item=proof['exchanges'][1]
                    response=json.loads(bytes.fromhex(item['response_hex'])[16:])
                    if mutation=='correlation': response['request_id']='f'*32
                    if mutation=='boot': response['body']['boot_id']='f'*32
                    if mutation=='owner': response['body']['owner_id']='f'*32
                    item['response_hex']=wtp_frame(response).hex()
                elif mutation=='crc': proof['exchanges'][1]['response_hex']=proof['exchanges'][1]['response_hex'][:-2]+'00'
                elif mutation=='early': proof['elapsed_start_s']=7199
                else: proof['exchanges'][1]['response_hex']=b'{}\n'.hex()
                path=root/'authority.json';path.write_text(json.dumps(proof))
                ref=dict(artifact_path=path.name,artifact_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                with self.assertRaises(ValueError): audit.final_authority(p,ref,root,7200)

    def test_duplicate_and_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'input.json'
            for content in ('{"a":1,"a":2}', '{"a":NaN}'):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    audit.strict_read(path)


if __name__ == '__main__':
    unittest.main()
