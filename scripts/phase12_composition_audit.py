#!/usr/bin/env python3
"""Offline preparation/audit for Phase 12 inhibited composition; performs no I/O to devices.

Input evidence is normalized by a separately reviewed observer. Passing this audit
is evidence completeness, never independent RF, wire, phone or hardware acceptance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct

ENGINE = 'inhibited-standalone-simulator'
CARRIERS = {'consumer': ['plain_lan'],
            'engineering': ['usb', 'ble', 'tls_wtp', 'https']}
PRESSURE = ['maximum_sessions', 'maximum_framing', 'busy_mutation',
            'disconnect_reclaim', 'provisioning_close', 'flash_serialization']


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def counter(value, name):
    """Decode a target uint64 counter without changing the retained wire record."""
    if type(value) is int:
        parsed = value
    else:
        require(type(value) is str and re.fullmatch(r'0|[1-9][0-9]{0,19}', value),
                name + ': canonical unsigned decimal counter required')
        parsed = int(value)
    require(0 <= parsed <= 18446744073709551615,
            name + ': uint64 counter out of range')
    return parsed


def number(value, name, low=0):
    require(type(value) in (int, float) and math.isfinite(value) and value >= low,
            name + ': finite number required')
    return value


def digest(value, name, length=64):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{%d}' % length, value),
            name + ': exact lowercase hex required')


def strict_load(content):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON member: ' + key)
            result[key] = value
        return result
    return json.loads(content, object_pairs_hook=pairs,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def strict_read(path):
    return strict_load(Path(path).read_text())


def validate_plan(p):
    require(p['schema'] == 'phase12-composition/1', 'plan schema')
    require(p['board'] == 'B' and p['engine'] == ENGINE, 'B inhibited only')
    require(p['mode'] in CARRIERS and p['carriers'] == CARRIERS[p['mode']],
            'explicit carrier composition; no TLS fallback')
    for field, size in [('source_commit', 40), ('image_sha256', 64),
                        ('device_id', 32), ('boot_id', 32)]:
        digest(p[field], field, size)
    require(isinstance(p['firmware'], str) and p['firmware'] and
            'dirty' not in p['firmware'], 'exact committed firmware required')
    require(p['duration_s'] == 7200 and p['cadence_s'] == 30 and
            p['max_gap_s'] == 45, 'two-hour cadence/gap must be predeclared')
    require(p['pressure_cases'] == PRESSURE and p['quiet_s'] == 960,
            'all directed pressure and >15-minute quiet reclaim required')
    require(p['max_simulated_jobs'] == 12 and p['max_job_duration_s'] == 60,
            'finite simulated job budget')
    require(p['rf_jobs'] == 0 and p['flash_cycles'] == 0,
            'no RF or automated flash pressure loops')
    for key in ('heap_return_tolerance_bytes', 'pool_return_tolerance',
                'stack_min_margin_bytes'):
        require(type(p[key]) is int and p[key] >= 0, key + ': integer required')
    require(p['heap_return_tolerance_bytes'] <= 4096 and
            p['pool_return_tolerance'] == 0 and p['stack_min_margin_bytes'] >= 256,
            'bounded resource tolerance')
    require(type(p['core0_stack_capacity_bytes']) is int and
            256 <= p['core0_stack_capacity_bytes'] <= 65536, 'declared linked stack capacity')
    if 'controller_acl_credits_required' in p:
        require(type(p['controller_acl_credits_required']) is bool, 'ACL measurement plan boolean')
        if p['controller_acl_credits_required']:
            require(p['mode'] == 'engineering' and
                    type(p['controller_acl_min_free_slots']) is int and
                    0 <= p['controller_acl_min_free_slots'] <= 65535,
                    'engineering ACL headroom predeclared')
    return p


def artifact(root, record):
    root = Path(root).resolve()
    path = (root / record['artifact_path']).resolve()
    require(path.is_relative_to(root) and path.is_file(), 'artifact escapes root or missing')
    require(path.stat().st_size <= 1048576, 'artifact size bound')
    digest(record['artifact_sha256'], 'artifact hash')
    require(hashlib.sha256(path.read_bytes()).hexdigest() == record['artifact_sha256'],
            'artifact hash mismatch')
    return path


def final_authority(p, reference, root, final_elapsed):
    """Validate retained complete frames; INFO does not expose ownership IDs."""
    from wsprrypico_ble import crc32c
    proof = strict_read(artifact(root, reference))
    require(proof['schema'] == 'phase12-final-authority/1' and
            proof['carrier'] in p['carriers'], 'authority schema/carrier')
    begin = number(proof['elapsed_start_s'], 'authority start')
    end = number(proof['elapsed_end_s'], 'authority end')
    require(final_elapsed <= begin <= end <= final_elapsed+30,
            'authority must follow final sample within 30 seconds')
    require(len(proof['exchanges']) == 2, 'exact HELLO/STATUS authority exchanges')
    session = None
    requests = set()
    def frame(encoded):
        require(type(encoded) is str and len(encoded) <= 2*(65536+16), 'bounded raw frame')
        wire = bytes.fromhex(encoded)
        require(len(wire) >= 16, 'complete WTP header')
        header, length, crc = struct.unpack('>8sII', wire[:16])
        require(header == b'WTPF\x01\x01\x00\x00' and
                0 < length <= 65536 and len(wire) == length+16 and
                crc32c(wire[16:]) == crc, 'WTP header/length/CRC')
        return strict_load(wire[16:])
    for operation, exchange in zip(('HELLO', 'STATUS'), proof['exchanges']):
        request = frame(exchange['request_hex'])
        response = frame(exchange['response_hex'])
        require(request['type'] == 'request' and response['type'] == 'response' and
                request['protocol'] == response['protocol'] == 'WTP/1' and
                request['op'] == response['op'] == operation and response['ok'] is True,
                'authority operation/protocol')
        for key in ('request_id', 'session_id'):
            digest(request[key], key, 32)
            require(request[key] == response[key], 'authority response correlation')
        require(request['request_id'] not in requests, 'authority duplicate request ID')
        requests.add(request['request_id'])
        session = request['session_id'] if session is None else session
        require(request['session_id'] == session, 'authority connection/session changed')
        body = response['body']
        if operation == 'HELLO':
            require('WTP/1' in request['body']['versions'] and
                    body['selected_version'] == 'WTP/1' and
                    body['device_id'] == p['device_id'] and body['boot_id'] == p['boot_id'],
                    'authority HELLO device/boot')
        else:
            require(request['body'] == {} and body['boot_id'] == p['boot_id'] and
                    body['state'] == 'empty' and body['owner_id'] is None and
                    body['job_id'] is None and body['output_active'] is False,
                    'actual final WTP authority')
    return body


def validate_evidence(p, e, artifact_root=None):
    validate_plan(p)
    encoded = json.dumps(p, sort_keys=True, separators=(',', ':')).encode()
    require(e['plan_sha256'] == hashlib.sha256(encoded).hexdigest(), 'plan binding')
    require(e['schema'] == 'phase12-composition-evidence/1', 'evidence schema')
    samples = e['samples']
    require(artifact_root is not None, 'artifact root required')
    require(len(samples) == 241, 'exact bounded two-hour samples required')
    previous = None
    baseline_raw = None
    previous_acl = None
    baseline_acl = None
    for s in samples:
        t = number(s['elapsed_s'], 'elapsed')
        require(previous is None or 0 < t - previous <= p['max_gap_s'],
                'monotonic cadence gap')
        previous = t
        for key in ('device_id', 'boot_id', 'firmware', 'engine'):
            require(s[key] == p[key], 'identity changed: ' + key)
        raw_path = artifact(artifact_root, {'artifact_path': s['raw_info_path'],
            'artifact_sha256': s['raw_info_sha256']})
        record = strict_read(raw_path)
        require(record['kind'] == 'INFO' and record['transport_raw'] is True,
                'actual serial INFO required')
        require(record['elapsed_start_s'] == t and
                0 <= record['elapsed_end_s'] - t <= 10, 'raw sample timestamps')
        wire = bytes.fromhex(record['raw_info_hex'])
        require(len(wire) <= 16384 and hashlib.sha256(wire).hexdigest() ==
                record['raw_info_sha256'], 'raw serial bytes binding')
        raw = strict_load(wire)
        require(raw == record['info'], 'decoded raw INFO differs')
        from phase12_composition_capture import check_info, pools, acl_credits
        check_info(p, raw)
        previous_acl = acl_credits(p, raw, previous_acl)
        if baseline_acl is None:
            baseline_acl = previous_acl
        if baseline_raw is None:
            baseline_raw = raw
        derived = {'heap_used_bytes': raw['heap_allocated_bytes'],
                   'pool_used': sum(pool['used'] for pool in pools(raw).values()),
                   'sessions': raw['softap_retained_sessions'],
                   'allocation_failures': counter(raw['allocator_failures'], 'allocator_failures'),
                   'pool_errors': sum(pool['errors'] for pool in pools(raw).values()),
                   'stack_margin_bytes': p['core0_stack_capacity_bytes'] - raw['core0_stack_used_bytes']}
        require(all(s[k] == v for k, v in derived.items()), 'normalized metrics differ from INFO')
        require(s['output_active'] is False and s['faults'] == [] and
                s['storage_healthy'] is True and s['guards_valid'] is True,
                'output/fault/storage/stack guard')
        require(s['allocation_failures'] == 0 and s['pool_errors'] == 0,
                'allocation or pool failure')
        number(s['heap_used_bytes'], 'heap')
        number(s['pool_used'], 'pool')
        require(number(s['stack_margin_bytes'], 'stack margin') >=
                p['stack_min_margin_bytes'], 'stack margin')
        require(type(s['sessions']) is int and s['sessions'] >= 0, 'sessions')
    require(0 <= samples[0]['elapsed_s'] <= 10 and samples[-1]['elapsed_s'] >= 7200 and
            samples[-1]['elapsed_s'] <= 7245, 'bounded full interval')
    for key, pool in pools(raw).items():
        require(pool['used'] <= pools(baseline_raw)[key]['used'], 'individual lwIP pool return')
    for key, pool in raw['btstack_pools'].items():
        require(pool['used'] <= baseline_raw['btstack_pools'][key]['used'], 'BTstack pool return')
    acl_credits(p, raw, previous_acl, final=True, baseline=baseline_acl)
    require(raw['status']['state'] == 'empty', 'actual final INFO state')
    authority = final_authority(p, e['final_authority_artifact'], artifact_root,
                                record['elapsed_end_s'])
    require(e['final_state'] == authority['state'] and e['final_owner'] == authority['owner_id']
            and e['final_job'] == authority['job_id'], 'normalized authority differs')
    for field in ('bootstrap_connected', 'bootstrap_setup_pending', 'bootstrap_reset_pending',
                  'ble_indication_pending'):
        require(raw[field] is False, 'actual final pending provisioning')
    for field in ('network_active_connections', 'network_pending_connections',
                  'network_buffered_rx_bytes', 'network_pending_tcp_bytes',
                  'bootstrap_pending_tcp_bytes', 'ble_active_connections',
                  'ble_inbound_bytes', 'ble_outbound_bytes', 'ble_outbound_frames'):
        require(raw[field] == 0, 'actual final transport reclamation')
    baseline, final = samples[0], samples[-1]
    require(final['heap_used_bytes'] <= baseline['heap_used_bytes'] +
            p['heap_return_tolerance_bytes'] and
            final['pool_used'] <= baseline['pool_used'] and final['sessions'] == 0,
            'final resource reclamation')
    quiet = strict_read(artifact(artifact_root, e['quiet_artifact']))
    begin, end = number(quiet['start_s'], 'quiet start'), number(quiet['end_s'], 'quiet end')
    require(0 <= begin < end <= samples[-1]['elapsed_s'] and end-begin >= p['quiet_s'],
            'quiet timestamps')
    require(quiet['network_requests'] == [] and quiet['ble_requests'] == [] and
            quiet['continuous_observation'] is True, 'unperturbed inactivity evidence')
    require(e['quiet_duration_s'] == end-begin and e['quiet_network_requests'] == 0,
            'quiet summary differs')
    require(e['final_state'] == 'empty' and e['final_owner'] is None and
            e['final_job'] is None and e['provisioning_closed'] is True,
            'final authority/provisioning cleanup')
    require(type(e['simulated_jobs']) is int and
            0 < e['simulated_jobs'] <= p['max_simulated_jobs'], 'job count')
    require(0 < number(e['longest_job_s'], 'longest job') <= 60 and
            e['rf_jobs'] == 0 and e['flash_cycles'] == 0, 'job/flash budget')
    coverage = e['coverage']
    for carrier in p['carriers']:
        require(coverage[carrier]['wire_identity_verified'] is True and
                coverage[carrier]['principal_isolation_verified'] is True,
                'missing wire/principal evidence: ' + carrier)
        artifact(artifact_root, coverage[carrier])
        require(coverage[carrier]['states'] == ['loaded', 'armed', 'running'],
                'missing composition states: ' + carrier)
    require(set(e['pressure']) == set(PRESSURE), 'missing pressure case')
    for case in PRESSURE:
        require(e['pressure'][case]['passed'] is True, 'pressure failure: ' + case)
        artifact(artifact_root, e['pressure'][case])
    return {'status': 'RESOURCE_EVIDENCE_REVIEW_REQUIRED', 'hardware_accessed': False,
            'physical_acceptance': False, 'independent_coverage_review_pending': True,
            'absolute_12h_deadline_covered': False,
            'phone_coverage': False, 'mode': p['mode'], 'samples': len(samples)}


def normalize_capture(p, capture_path, metadata_path, artifact_root, output):
    """Export genuine capture records and derive metrics; external proof stays pending."""
    validate_plan(p)
    capture_path, output = Path(capture_path), Path(output)
    require(not output.exists(), 'new evidence output required')
    require(capture_path.stat().st_size <= 20 * 1024 * 1024, 'bounded capture file')
    lines = capture_path.read_text().splitlines()
    require(len(lines) == 243, 'complete start/241 INFO/complete capture required')
    records = [strict_load(line) for line in lines]
    require(records[0]['kind'] == 'start' and records[0]['plan'] == p,
            'capture plan binding')
    require(records[-1]['kind'] == 'complete' and records[-1]['physical_acceptance'] is False,
            'partial or failed capture refused')
    metadata = strict_read(metadata_path)
    require(set(metadata) == {'coverage', 'pressure', 'quiet_artifact',
            'simulated_jobs', 'longest_job_s', 'rf_jobs', 'flash_cycles', 'final_authority_artifact'},
            'explicit external proof metadata required')
    root = Path(artifact_root).resolve()
    require(root.is_dir(), 'existing private artifact root required')
    quiet = strict_read(artifact(root, metadata['quiet_artifact']))
    for entry in list(metadata['coverage'].values()) + list(metadata['pressure'].values()):
        artifact(root, entry)
    from phase12_composition_capture import check_info, pools
    samples = []
    export = root / 'composition-info'
    require(not export.exists(), 'new raw export directory required')
    # Validate every capture before exporting anything.
    for record in records[1:-1]:
        require(record['kind'] == 'INFO' and record['transport_raw'] is True,
                'actual bounded INFO capture required')
        wire = bytes.fromhex(record['raw_info_hex'])
        require(len(wire) <= 16384 and hashlib.sha256(wire).hexdigest() ==
                record['raw_info_sha256'], 'raw serial bytes binding')
        raw = strict_load(wire)
        require(raw == record['info'], 'decoded INFO differs')
        check_info(p, raw)
        samples.append(dict(elapsed_s=record['elapsed_start_s'],
            device_id=raw['device_id'], boot_id=raw['status']['boot_id'],
            firmware=raw['firmware'], engine=raw['status']['engine'],
            output_active=raw['status']['output_active'], faults=[], storage_healthy=True,
            guards_valid=True, allocation_failures=counter(raw['allocator_failures'], 'allocator_failures'),
            pool_errors=sum(pool['errors'] for pool in pools(raw).values()),
            heap_used_bytes=raw['heap_allocated_bytes'],
            pool_used=sum(pool['used'] for pool in pools(raw).values()),
            stack_margin_bytes=p['core0_stack_capacity_bytes'] - raw['core0_stack_used_bytes'],
            sessions=raw['softap_retained_sessions']))
    authority = final_authority(p, metadata['final_authority_artifact'], root,
                                records[-2]['elapsed_end_s'])
    export.mkdir(mode=0o700)
    for index, (record, sample) in enumerate(zip(records[1:-1], samples)):
        path = export / ('%03d.json' % index)
        path.write_text(json.dumps(record, sort_keys=True))
        path.chmod(0o600)
        sample.update(raw_info_path=str(path.relative_to(root)),
                      raw_info_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    raw = records[-2]['info']
    evidence = dict(metadata, schema='phase12-composition-evidence/1',
        plan_sha256=hashlib.sha256(json.dumps(p, sort_keys=True,
            separators=(',', ':')).encode()).hexdigest(), samples=samples,
        quiet_duration_s=quiet['end_s']-quiet['start_s'], quiet_network_requests=len(quiet['network_requests']),
        final_state=authority['state'], final_owner=authority['owner_id'],
        final_job=authority['job_id'], provisioning_closed=not (
            raw['bootstrap_connected'] or raw['bootstrap_setup_pending'] or raw['bootstrap_reset_pending']))
    result = validate_evidence(p, evidence, root)
    with output.open('x') as handle:
        handle.write(json.dumps(evidence, sort_keys=True, indent=2) + '\n')
    output.chmod(0o600)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--metadata', type=Path)
    parser.add_argument('--write-evidence', type=Path)
    args = parser.parse_args()
    try:
        p = validate_plan(strict_read(args.plan))
        if args.capture:
            require(args.metadata is not None and args.artifact_root is not None and
                    args.write_evidence is not None and args.evidence is None, 'normalizer inputs required')
            result = normalize_capture(p, args.capture, args.metadata, args.artifact_root, args.write_evidence)
        else:
            result = validate_evidence(p, strict_read(args.evidence), args.artifact_root) if args.evidence else {
            'status': 'PREPARED_NO_HARDWARE_AUTHORITY', 'hardware_accessed': False,
            'physical_acceptance': False, 'mode': p['mode']}
        print(json.dumps(result, sort_keys=True))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, 'REFUSED: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
