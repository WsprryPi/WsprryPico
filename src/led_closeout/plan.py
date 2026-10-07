"""Finite P13.1 physical cases. Importing or making a plan never opens hardware."""
import json
from phase11_6.plan import raw_job

SCHEMA = 'phase13.1-led-closeout/1'
BOARDS = {
    'A': {'serial': '0BF4B4AEC9FFB344', 'device_id': 'fd6127d11d6aca42a9905fa3fb1bf1d5'},
    'B': {'serial': 'CDDBF8767C506C07', 'device_id': '29f20b7342051ef947aa56cb9d4fab42'},
}
RECEIVER = '2404058C60'
IMAGES = {
    'restore': (False, False, 0, False),
    'onboard': (True, False, 0, False),
    'cue': (True, True, 0, False),
    'high': (True, True, 1, False),
    'low': (True, True, 2, False),
    'disabled': (True, True, 3, False),
    'gp14': (True, True, 0, True),
    'stimulus': (False, True, 0, False),
}
# RF duration is charged in full even for rejected, aborted or ambiguous admission.
# An additional second per admission covers warmup/launch activity.
MAX_JOBS = 18
MAX_RF_NS = 600_000_000_000


def make_plan():
    cases = []
    def add(name, step, image, action='complete', mode='TONE', seconds=16, cue=None):
        job = raw_job(mode, 3_570_100, 'led-closeout-v1:' + name,
                      duration_ns=seconds * 1_000_000_000, message='ET')
        cases.append(dict(id=name, step=step, image=image, action=action, cue=cue,
                          job=job, charge_ns=int(job['total_duration_ns']) + 1_000_000_000,
                          optical='optional when optical evidence is selected',
                          rf='independent SDR recording required'))
    add('warmup', 3, 'onboard', seconds=15)
    for mode in ('WSPR', 'QRSS', 'FSKCW', 'DFCW'):
        add(mode.lower(), 3, 'onboard', mode=mode)
    add('active_abort', 3, 'onboard', 'abort', seconds=20)
    add('armed_cancel', 3, 'onboard', 'cancel', seconds=20)
    add('inhibited', 3, 'restore', 'inhibited', seconds=10)
    add('onboard_ap', 4, 'cue', cue='AP')
    add('onboard_identify', 4, 'cue', cue='IDENTIFY')
    add('external_high', 4, 'high', cue='AP_IDENTIFY')
    add('external_low', 4, 'low', cue='AP_IDENTIFY')
    add('disabled', 4, 'disabled')
    add('standalone_stop', 5, 'cue', 'standalone', mode='WSPR')
    add('gp14_cutoff', 5, 'gp14', 'gp14', seconds=20)
    add('led_write_launch_failure', 5, 'cue', 'fail', seconds=10)
    return dict(schema=SCHEMA, cases=cases, limits=dict(jobs=MAX_JOBS, rf_ns=MAX_RF_NS),
                receiver_serial=RECEIVER, frequency_hz=3_570_100,
                physical_acceptance='NOT_RUN', operator_step=2)


def validate_plan(value):
    # Only the reviewed finite packet is executable. Reject edited actions, pins,
    # duration, budgets and modes rather than silently admitting an arbitrary job.
    if json.dumps(value, sort_keys=True, separators=(',', ':')) != json.dumps(make_plan(), sort_keys=True, separators=(',', ':')):
        raise ValueError('plan differs from the reviewed finite packet')
    if len(value['cases']) > MAX_JOBS or sum(c['charge_ns'] for c in value['cases']) > MAX_RF_NS:
        raise ValueError('plan exceeds its aggregate ceiling')
    if len({c['job']['job_id'] for c in value['cases']}) != len(value['cases']):
        raise ValueError('duplicate job identity')
    return value
