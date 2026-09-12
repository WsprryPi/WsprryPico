#!/usr/bin/env python3
"""One amended Tone gate after the complete new-candidate R1 baseline.

Uses the already armed restoration supervisor. No fixture extension, retry,
configuration write or restoration is performed by this process.
"""
import argparse
import json
import os
from pathlib import Path
import time

from phase11_5_inventory import require
from phase11_5_device_management import digest, save
from phase11_5_device_fixture import DeviceFixture
from phase11_5_network_fixture import Fixture
from phase11_5_r2_amended_plan import SOURCE, INITIAL_COUNTS
from phase11_5_r2_plan import jobs
from phase11_5_r2 import tone_packet, R2_HELPERS


def admit_handoff(packet, ready, result, device, management, now_ns):
    require(packet['source_revision'] == ready['source'] == result['source'] == SOURCE,
            'Amended handoff source')
    require(result['status'] == 'CAPTURED_REQUIRES_FINAL_REVIEW' and result['rf_jobs'] == [],
            'Complete resource baseline required before RF')
    require(set(result['intervals']) == {'r1-inhibited', 'r1-warm', 'r1-controller',
            'r1-normal', 'r1-quiet-before', 'r1-quiet-after'}, 'All six R1 intervals required')
    require(device['boot'] == ready['boot'] and device['kind'] == 'physical' and
            not device.get('pending') and not device.get('restored'), 'Live physical handoff')
    require(device['deadline_monotonic_ns'] == ready['deadline_monotonic_ns'] and
            now_ns + 450_000_000_000 < ready['deadline_monotonic_ns'],
            'Insufficient Tone gate time plus restoration handoff reserve')
    require(management['counts'] == dict(INITIAL_COUNTS, config=29, **{'heap-probe':6}) and
            not management.get('pending') and not management.get('blocked'), 'Cumulative operation counts')
    needed = ready['largest_successful_request_bytes']
    require(needed == 18364 and len(result['probes']) == 3 and
            [(p['bytes'], p['allocated']) for p in result['probes']] ==
            [(needed, True), (218285, False), (needed, True)], 'Exact candidate allocation probes')
    require(abs(result['quiet_delta_bytes']) <= 1024, 'Matched quiet baseline')
    for label in ('r1-warm', 'r1-controller', 'r1-normal', 'r1-quiet-before', 'r1-quiet-after'):
        value = result['intervals'][label]['resources']
        require(value['boot'] == ready['boot'] and value['clock_hz'] == 138000000 and
                value['heap_capacity_bytes'] == 218284 and
                value['allocator_largest_successful_request_bytes'] <= needed,
                'Resource evidence bound to current physical image')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--packet-sha256', required=True)
    p.add_argument('--run', action='store_true')
    args = p.parse_args()
    if not args.run:
        print('Plan only; no host or device access.')
        return
    require(os.geteuid() == 0, 'wspr5 root required')
    os.umask(0o077)
    root = args.root.resolve(strict=True)
    frozen = root/'r2-amended-packet.json'
    require(digest(frozen) == args.packet_sha256, 'Frozen amended RF packet changed')
    packet = json.loads(frozen.read_text())
    original = json.loads((root/'packet.json').read_text())
    require(packet['parent_packet_sha256'] == digest(root/'packet.json') and
            packet['rf_jobs'] == jobs(packet['rf_nonce']) and
            packet['current_wiring_confirmed'] is True and packet['fixture_authorized'] is True,
            'Amended finite scope and authority')
    expected = R2_HELPERS | {'scripts/phase11_5_r2_amended.py', 'scripts/phase11_5_r2_amended_plan.py'}
    require(set(packet['r2_helper_sha256']) == expected, 'Complete amended helper manifest')
    for relative, sha in packet['r2_helper_sha256'].items():
        path = (root/relative).resolve(strict=True)
        require(path.is_relative_to(root) and digest(path) == sha, 'Amended helper changed')
    require(all(packet[k] == original[k] for k in original if k != 'rf_jobs'), 'Parent scope changed')
    d = DeviceFixture(root)
    d.verify_helpers()
    ready = json.loads((root/'r1-ready-for-r2.json').read_text())
    result = json.loads((root/'r1-result.json').read_text())
    require(ready['packet_sha256'] == digest(root/'packet.json') and
            ready['r1_result_sha256'] == digest(root/'r1-result.json'), 'R1 handoff evidence changed')
    admit_handoff(packet, ready, result, d.state,
                  json.loads((root/'management-state.json').read_text()), time.monotonic_ns())
    outcome = dict(source=SOURCE, boot=ready['boot'], status='RUNNING', completed_jobs=0,
                   required_jobs=7, family_closed=False, packet_sha256=args.packet_sha256)
    require(not (root/'r2-result.json').exists() and not (root/'r2-completion.json').exists(), 'No RF replay')
    save(root/'r2-result.json', outcome)
    try:
        outcome['tone'] = tone_packet(root, packet, d, Fixture(root))
        outcome.update(status='TONE_GATE_PASSED_R2_REMAINS_OPEN', completed_jobs=3)
        save(root/'r2-tone-ready.json', dict(source=SOURCE, boot=ready['boot'],
            audit_sha256=digest(root/'r2-tone/audit.json'),
            deadline_monotonic_ns=ready['deadline_monotonic_ns']))
        # A separately reviewed later-mode packet may use the remaining time.
        # The first packet never authorizes arbitrary extra jobs or extends the
        # device deadline. Return disposition before the R1 handoff deadline.
        while not (root/'r2-modes-completion.json').exists() and \
                time.monotonic_ns()+60_000_000_000 < ready['deadline_monotonic_ns']:
            time.sleep(.2)
        if (root/'r2-modes-completion.json').exists():
            later=json.loads((root/'r2-modes-completion.json').read_text())
            require(later.get('source')==SOURCE and later.get('boot')==ready['boot'],
                    'Later-mode disposition identity')
            outcome['later_modes']=later
        else:
            outcome['remaining_reason']='No completed later-mode packet before bounded restoration handoff'
    except BaseException as error:
        outcome['status'] = 'FAILED'
        outcome['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        save(root/'r2-result.json', outcome)
        # This marker conveys disposition only. The original supervisor still
        # requires authoritative idle/output/owner checks before restoration.
        save(root/'r2-completion.json', outcome)
    require(outcome['completed_jobs'] == 3, 'Amended Tone gate incomplete; preserve evidence')


if __name__ == '__main__':
    main()
