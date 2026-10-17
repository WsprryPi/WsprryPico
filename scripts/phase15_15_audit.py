#!/usr/bin/env python3
"""Audit retained P15.15 bench evidence offline and export its sanitized manifest."""
import argparse
import hashlib
import json
import pathlib
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('evidence', type=pathlib.Path)
args = parser.parse_args()
ROOT = args.evidence.resolve()
SRC = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SRC / 'src'), str(SRC / 'scripts')]
from phase14.plan import validate_capture, BOARDS
from validate_wtp_contract import crc32c
from led_closeout.runner import sha256
run = ROOT / 'run-3'
result = json.loads((run / 'result.json').read_text())
assert result['status'] == 'ACQUISITION_COMPLETE' and (not result['errors'])
records = json.loads((run / 'records.json').read_text())
assert len(records) == 26 and len({r['label'] for r in records}) == 26
baseline = sha256(ROOT / 'baseline.uf2')
candidate = sha256(ROOT / 'WsprryPico-StandaloneRF.uf2')
assert baseline == 'c5bbed665fd3d44deba354a7cd76bd63c427cacea655c531db29eb0c1dacc5cf'
assert candidate == 'd8980c56c892fcab28491947f5aa77ef6562645df52006121158f6bcf3694c4a'
artifacts = []
for record in records:
    directory = run / record['label']
    body = json.loads((directory / 'physical.json').read_text())
    assert body == {k: v for k, v in record.items() if k != 'label'}
    b = record['board']
    before = record['before']
    after = record['after']
    boot = before['status']['boot_id']
    assert before['device_id'] == BOARDS[b][1] and before['system_clock_hz'] == after['system_clock_hz'] == 138000000
    assert before['status']['engine'] == after['status']['engine'] == 'pio-dma-gp2'
    assert record['image_sha256'] == (baseline if record['label'].startswith('baseline-') else candidate)
    if not record['label'].startswith('baseline-'):
        assert before['revision'] == after['revision'] == 'd6de1f3cf14d'
    assert record['load']['job_id'] == record['arm']['job_id'] == record['job']['job_id']
    statuses = [x['status'] for x in record['status']]
    assert all((s['boot_id'] == boot and s['job_id'] == record['job']['job_id'] for s in statuses))
    assert statuses[-1]['state'] == ('complete' if record['action'] == 'complete' else 'aborted')
    assert not statuses[-1]['output_active'] and (not after['status']['output_active']) and (after['status']['owner_id'] is None)
    assert not after['status']['enabled'] and after['core1_stack_guard_valid']
    assert all((after[k] == 0 for k in ('dma_errors', 'refill_invalid_reserves', 'core1_stack_fault_status')))
    if record['action'] == 'cancel':
        assert not any((s['output_active'] for s in statuses))
    else:
        assert any((s['state'] == 'running' and s['output_active'] for s in statuses))
    if 'pad_after' in record:
        p = record['pad_after']
        assert p['pad_readback'] == record['ma'] and p['rf_gp'] == 2 and (p['target']['boot_id'] == boot)
    a = dict(
        label=record['label'], board=b, ma=record['ma'], frequency_hz=record['frequency_hz'],
        action=record['action'], image_sha256=record['image_sha256'], revision=before['revision'],
        boot_id=boot, job_id=record['job']['job_id'], physical_sha256=sha256(directory / 'physical.json'),
        terminal=statuses[-1]['state'], output_inactive=True, diagnostics_clean=True)
    if 'capture_sha256' in record:
        metadata = json.loads((directory / 'capture.json').read_text())
        validate_capture(metadata, directory / 'capture.cf32', record['receiver_settings'])
        assert sha256(directory / 'capture.cf32') == record['capture_sha256'] and sha256(directory / 'capture.json') == record['metadata_sha256']
        a.update(capture_sha256=record['capture_sha256'], metadata_sha256=record['metadata_sha256'])
    artifacts.append(a)
preparations = json.loads((run / 'preparations.json').read_text())
assert {(p['board'], p['ma']) for p in preparations} == {(b, m) for b in ('A', 'B') for m in (2, 4, 8, 12)}
for p in preparations:
    o = p['observed']
    assert p['before']['pad_readback'] is None
    assert o['target']['device_id'] == BOARDS[p['board']][1]
    assert o['target']['boot_id'] == p['before']['target']['boot_id'] == p['loaded']['boot_id'] == p['inactive']['boot_id']
    assert p['loaded']['job_id'] == p['arm']['job_id'] == p['inactive']['job_id']
    assert o['saved'] == p['ma'] and (not o['pending_restart'])
    assert o['rf_gp'] == 2 and o['pad_readback'] == o['boot_active'] == p['ma'] and (o['application_error'] is None)
    assert p['inactive']['state'] == 'armed' and (not p['inactive']['output_active']) and (p['busy_refusal']['status'] == 409)
restarts = json.loads((run / 'restarts.json').read_text())
assert len(restarts) == 11
for r in restarts:
    assert r['before_boot'] != r['after_boot'] and r['before_usb']['devnum'] != r['after_usb']['devnum']
    assert r['before_usb']['path'] == r['after_usb']['path'] and any((x['usb'] is None for x in r['observations']))
    assert len(r['after_usb']['interfaces']) == 6 and r['readback']['body']['target']['boot_id'] == r['after_boot']
    stale = r['stale_session']
    assert stale['new']['session'] != stale['old']['session']
    assert stale['new']['target']['boot_id'] == r['after_boot']
    assert stale['old']['target']['boot_id'] == r['before_boot']
    assert stale['silent_refusal'] and stale['rejected_response'] is None
    view = r['readback']['body']
    assert view['saved'] == view['boot_active'] and (not view['pending_restart'])
arms = []
attempts = []
for number in (1, 2, 3):
    d = ROOT / ('run-' + str(number))
    v = json.loads((d / 'result.json').read_text())
    assert set(v['restored']) == {'A', 'B'}
    for b in ('A', 'B'):
        x = v['restored'][b]
        assert x['original_sha256'] == x['restored_sha256']
    attempts.append(dict(
        attempt=number, status=v['status'], errors=v['errors'], armed_cumulative=v['armed_jobs'],
        budget_cumulative_s=v['rf_budget_seconds'], captures_cumulative=v['captures'],
        exact_original_restoration=True))
    for line in (d / 'events.jsonl').read_text().splitlines():
        e = json.loads(line)
        if e['kind'] != 'tx':
            continue
        raw = bytes.fromhex(e['value']['hex'])
        if not raw.startswith(b'WTPF'):
            continue
        size = int.from_bytes(raw[8:12], 'big')
        assert len(raw) == 16 + size
        assert crc32c(raw[16:]) == int.from_bytes(raw[12:16], 'big')
        request = json.loads(raw[16:])
        if request['op'] == 'ARM':
            arms.append(request['body']['job_id'])
assert len(arms) == len(set(arms)) == result['armed_jobs'] == 34
assert result['rf_budget_seconds'] == 114 and result['captures'] == 18
summary = json.loads((ROOT / 'analysis' / 'summary.json').read_text())
assert len(summary['values']) == 18 and (not summary['pad_acceptance_evaluated'])
for a in artifacts:
    if 'capture_sha256' in a:
        v = summary['values'][a['label']]
        assert all((v[k] == a[k] for k in ('capture_sha256', 'metadata_sha256', 'physical_sha256', 'image_sha256')))
        assert v['observation']['relative_checks_passed'] and (not v['observation']['issues'])
assert all((v['carrier_screen_passed'] for v in summary['comparisons'].values()))
restored = {}
for b, x in result['restored'].items():
    original = (run / (b + '-original.bin')).read_bytes()
    verified = (run / (b + '-restored-verify.bin')).read_bytes()
    assert original == verified
    info = x['after']
    s = info['status']
    assert not s['enabled'] and (not s['output_active']) and (s['owner_id'] is None) and s['suspended']
    regions = [('progress', 0x3f0000, 0x3f7000), ('profile', 0x3f7000, 0x3fb000),
               ('config', 0x3fb000, 0x3fd000), ('cursor', 0x3fd000, 0x3ff000)]
    restored[b] = dict(
        revision=info['revision'], flash_sha256=x['restored_sha256'], full_flash_exact=True,
        owner_id=None, output_active=False, schedules_enabled=False, suspended=True,
        watermark_utc_ns=s['watermark_utc_ns'], clock_hz=info['system_clock_hz'],
        regions={name: hashlib.sha256(original[a:z]).hexdigest() for name, a, z in regions})
final = json.loads((ROOT / 'final-state.json').read_text())
assert final['service_active']
reference = final['reference']
assert not reference['out1'] and (not reference['out2'])
for b in ('A', 'B'):
    info = final['boards'][b]
    s = info['status']
    assert info['device_id'] == BOARDS[b][1] and info['revision'] == restored[b]['revision']
    assert info['system_clock_hz'] == 138000000
    assert not s['output_active'] and (not s['enabled']) and s['suspended'] and (s['owner_id'] is None)
    assert s['watermark_utc_ns'] == restored[b]['watermark_utc_ns']
manifest = dict(
    schema='phase15-15-hardware-results/1', status='ACCEPTED_SCOPED_WITH_RF_OBSERVATIONS',
    spectral_screens_passed=summary['all_screens_passed'],
    acceptance_basis=(
        'Operator direction on 2026-10-17: in-span energy does not invalidate the testing unless it '
        'prevents detecting and validating the pad checks. All pad, identity, persistence, USB and '
        'lifecycle checks remain valid; numerical spectral failures are retained as nonblocking observations.'),
    source=dict(
        pico='d6de1f3cf14dc49266c4401c3bca91b8ce9da688',
        pi='fe701cf4c2b05e46cb84927188984084503d1cea',
        baseline='46b256c636fb44c8ed059000d7b3f3b94cceea9e',
        candidate_uf2_sha256=candidate, baseline_uf2_sha256=baseline, clock_hz=138000000,
        sdk='079c6f39023649b154152db30f1d781e884879bc', arm_gnu='15.3.1'),
    setup=dict(
        boards={b: dict(serial=v[0], device_id=v[1]) for b, v in BOARDS.items()}, rf_gp=2,
        receiver='2404058C60',
        path=('GP2/GND per Pico -> individual 20 dB attenuator -> combiner -> 40 dB attenuation '
              '-> RSP1B; no antenna or LPF'),
        receiver_settings=dict(sample_rate_hz=250000, bandwidth_hz=200000, gain_db=20,
                               channel=0, agc=False, bias_tee=False)),
    attempts=attempts,
    budget=dict(armed_jobs=34, possible_rf_s=114, captures=18, receiver_s=360, cf32_bytes=720000000),
    pad_readbacks=[dict(
        board=p['board'], ma=p['ma'], actual=p['observed']['pad_readback'], rf_gp=p['observed']['rf_gp'],
        boot_id=p['observed']['target']['boot_id'], unknown_before_arm=True,
        inactive_while_read=True, busy_write_status=409) for p in preparations],
    restarts=[dict(
        board=r['board'], ma=r['readback']['body']['saved'], before_boot=r['before_boot'],
        after_boot=r['after_boot'], old_devnum=r['before_usb']['devnum'],
        new_devnum=r['after_usb']['devnum'], physical_removal_observed=True,
        three_cdc_roles_rediscovered=True, stale_session_refused=True) for r in restarts],
    artifacts=artifacts, measurements=summary['values'], comparisons=summary['comparisons'],
    restoration=restored,
    final_state=dict(service_active=True, reference_serial=reference['serial'],
                     reference_outputs=[reference['out1'], reference['out2']],
                     fresh_identity_and_idle_check=True),
    helpers=json.loads((run / 'entry.json').read_text())['helpers'],
    harness_sha256=sha256(ROOT / 'harness-run-3.py'),
    analysis_sha256=sha256(SRC / 'scripts/phase15_15_analysis.py'), auditor_sha256=sha256(__file__),
    audit=('All original capture/metadata hashes, framing CRCs, independent ARM cardinality, '
           'exact images/boards/boots, pad observations, physical enumeration changes '
           'and all three original-flash restorations verified.'),
    limitations=summary['limitations'])
(ROOT / 'hardware-manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
print(json.dumps(dict(status=manifest['status'], arms=len(arms), captures=18, pads=len(preparations),
                      restarts=len(restarts), restored=restored, comparisons=summary['comparisons']), indent=2))
