#!/usr/bin/env python3
"""Offline eight-case acceptance; same boot, saved state, and client sessions."""
import argparse
import json
from pathlib import Path
from phase11_4_three_radio_audit import audit, rows, require, SAVED


def assess(root):
    paths = sorted(root.glob('case-*'))
    require([p.name for p in paths] == ['case-%02d' % n for n in range(1,9)], 'Exactly eight numbered cases required')
    results = [audit(p, require_resumed_sessions=True) for p in paths]
    fixture = rows(root.parent / 'events.jsonl')
    require(len({r['boot'] for r in results}) == 1, 'Boot changed across cases')
    saved, identities, request_ids, previous_end = None, None, set(), 0
    for path, result in zip(paths, results):
        records = rows(path / 'events.jsonl')
        first = next(r for r in records if r['kind'] == 'INFO')
        off = next(r['epoch_ns'] for r in records if r['kind'] == 'off_begin')
        on = next(r['epoch_ns'] for r in records if r['kind'] == 'on_begin')
        controls = [r for r in fixture if off <= r['epoch_ns'] <= records[-1]['epoch_ns'] and
                    r['kind'] in ('WIFI OFF', 'WIFI ON', 'CONFIG', 'REBOOT')]
        require([r['kind'] for r in controls] == ['WIFI OFF', 'WIFI ON'] and
                all(r['value'].get('ok') is True for r in controls) and
                controls[0]['epoch_ns'] < on < controls[1]['epoch_ns'],
                'Missing, failed or unexpected device control acknowledgement')
        state = {k: first['value']['status'][k] for k in SAVED}
        sessions = {p: result['peers'][p]['sessions'][0] for p in ('1','2')}
        require(saved is None or saved == state, 'Saved state changed between cases')
        require(identities is None or identities == sessions, 'Client session changed between cases')
        require(first['epoch_ns'] > previous_end, 'Overlapping cases')
        previous_end = records[-1]['epoch_ns']
        saved, identities = state, sessions
        for evidence in path.glob('peer*-*/events.jsonl'):
            for r in rows(evidence):
                if r['kind'] == 'client_request':
                    key = (r['value']['session_id'], r['value']['request_id'])
                    require(key not in request_ids, 'A request ID was reused across connections/cases')
                    request_ids.add(key)
    recorded = json.loads((root / 'campaign.json').read_text())
    require(recorded['complete'] is True and len(recorded['cases']) == 8 and
            all(c['result'] == 'PASS' for c in recorded['cases']), 'Campaign did not complete cleanly')
    return dict(result='PASS', B2='PASS', D2='PASS', cases=8, boot=results[0]['boot'],
        authenticated_checks=sum(p['checks'] + 1 for r in results for p in r['peers'].values()),
        max_local_active_seconds=max(r['local_active_seconds'] for r in results),
        max_first_authenticated_seconds=max(p['first_authenticated_seconds'] for r in results for p in r['peers'].values()),
        max_cache_absent_by_seconds=max(p['cache_absent_by_seconds'] for r in results for p in r['peers'].values()),
        max_usb_gap_seconds=max(r['usb_max_gap_seconds'] for r in results),
        unique_peer_sessions=len(set(identities.values())), unique_peer_requests=len(request_ids),
        per_case=results, scope='Eight clean cycles on one inhibited Pico boot, controlled onboard AP, two independent native Linux clients',
        limitation='Does not qualify other infrastructure, macOS, or overnight stability; historical evidence remains retained')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    print(json.dumps(assess(p.parse_args().root), indent=2))
