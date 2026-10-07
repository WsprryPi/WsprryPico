"""Unattended case orchestration with injected, identity-bound physical adapters."""
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from led_closeout.plan import BOARDS, MAX_JOBS, MAX_RF_NS, validate_plan


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save_json(path, value):
    """Atomic, directory-synced state, private even during a crash."""
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with open(temporary, 'w', opener=lambda p, f: os.open(p, f, 0o600)) as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Evidence:
    def __init__(self, root, plan, board, fixture):
        self.root = Path(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.state = dict(schema=plan['schema'], board=board, fixture=fixture,
                          jobs=0, rf_ns=0, attempts=[], result='PREPARING',
                          physical_acceptance='NOT_ASSESSED', cleanup='NOT_STARTED')
        save_json(self.root / 'plan.json', plan)
        self.save()

    def save(self):
        save_json(self.root / 'state.json', self.state)

    def event(self, kind, data):
        with open(self.root / 'events.jsonl', 'a', opener=lambda p, f: os.open(p, f, 0o600)) as stream:
            stream.write(json.dumps(dict(monotonic_ns=time.monotonic_ns(), utc_ns=time.time_ns(),
                                         kind=kind, data=data), sort_keys=True) + '\n')
            stream.flush()
            os.fsync(stream.fileno())

    def charge(self, case, boot):
        require(self.state['jobs'] < MAX_JOBS and
                self.state['rf_ns'] + case['charge_ns'] <= MAX_RF_NS, 'RF budget exhausted')
        require(case['id'] not in {a['case'] for a in self.state['attempts']}, 'case already charged')
        self.state['jobs'] += 1
        self.state['rf_ns'] += case['charge_ns']
        attempt = dict(case=case['id'], job_id=case['job']['job_id'], boot_id=boot,
                       charge_ns=case['charge_ns'], result='ADMISSION_PENDING')
        self.state['attempts'].append(attempt)
        self.save() # BEFORE ambiguous ARM or locally scheduled admission.
        return attempt


def admit(info, identity, image=None, boot=None):
    require(info.get('ok') is True and info.get('device_id') == identity['device_id'], 'DUT identity')
    status = info['status']
    require(isinstance(status['output_active'], bool), 'missing output authority')
    if boot is not None:
        require(status['boot_id'] == boot, 'DUT rebooted during case')
    if image:
        require(info['revision'] == image['revision'], 'candidate revision')
        require(status['engine'] == image['engine'], 'candidate engine')
        require(info['led_boot_pins'] == image['pins'], 'candidate pins')
        require(info['led_acceptance'] is image['acceptance'], 'candidate fixture')
        if image['engine'] == 'pio-dma-gp2':
            require(info['system_clock_hz'] == 138000000, 'RF system clock')
        if image['acceptance']:
            require(info['led_selection'] == image['selection'], 'candidate selection')
    return status


def quiescent(info, identity, image=None):
    status = admit(info, identity, image)
    require(status['output_active'] is False and status['enabled'] is False and
            status['state'] in ('empty', 'completed', 'aborted') and
            not status.get('owner_id') and
            (status['state'] != 'empty' or not status.get('job_id')), 'DUT not quiescent')
    require(status['storage_healthy'] is True and info['access_state'] in ('healthy', 'erased') and
            not info.get('bootstrap_reset_pending', False) and
            not info.get('fault_stage', 0), 'DUT storage/recovery unhealthy')
    return status


class Runner:
    """The backend owns locks, verified flash, transport, clock and capture handles."""
    def __init__(self, plan, manifest, board, backend, evidence, *, fixture=None, steps=(3, 4, 5), cases=None):
        self.plan = validate_plan(plan)
        require(board in BOARDS and (fixture is None or fixture in BOARDS and fixture != board),
                'named distinct boards required')
        require(set(steps) <= {3, 4, 5} and bool(steps), 'invalid autonomous steps')
        available = [c for c in plan['cases'] if c['step'] in steps]
        if cases is not None:
            require(bool(cases) and len(cases) == len(set(cases)) and
                    set(cases) <= {c['id'] for c in available}, 'invalid canonical case selection')
            available = [c for c in available if c['id'] in cases]
        require(available and all(c['image'] in manifest['images'] for c in available),
                'selected case image unavailable')
        self.cases = available
        require(not any(c['action'] == 'gp14' for c in available) or fixture,
                'GP14 needs a prepared second Pico fixture')
        self.manifest, self.board, self.backend, self.e = manifest, board, backend, evidence
        self.identity, self.fixture, self.steps = BOARDS[board], fixture, steps
        self.owner, self.boot = uuid.uuid4().hex, None
        self.lease_at = 0
        self.gpio = getattr(backend, 'setup', {}).get('evidence_mode') == 'gpio-readback'

    def checked_pin(self, info, image, on):
        if not self.gpio:
            return
        prefix = 'indicator_onboard' if image['selection'] == 3 else 'indicator_pin'
        require(info.get(prefix+'_readback_known') is True and
                type(info.get(prefix+'_readback_error')) is int and info[prefix+'_readback_error'] == 0 and
                info.get(prefix+'_readback_on') is on, 'hardware LED GPIO readback mismatch/unknown')

    def observe(self, image):
        self.backend.captures_healthy()
        info = self.backend.info(self.board)
        status = admit(info, self.identity, image, self.boot)
        self.e.event('info', info)
        # Consumer Console scheduler STATUS has no owner/job; backend attaches
        # WTP authority under these same fields from a checked matching boot.
        return info, status

    def renew(self):
        if self.backend.now() >= self.lease_at:
            self.backend.request('RENEW' if self.lease_at else 'CLAIM',
                                 dict(owner_id=self.owner, lease_ms=20000))
            self.lease_at = self.backend.now() + 2

    def wait(self, image, until, predicate, *, lease=True):
        while self.backend.now() < until:
            if lease:
                self.renew()
            info, status = self.observe(image)
            if predicate(info, status):
                return info, status
            self.backend.sleep(.1)
        raise TimeoutError('case status deadline')

    def cues(self, case, active=False):
        if case['cue']:
            for command in case['cue'].split('_'):
                if active or command == 'AP':
                    self.backend.command(self.board, command)

    def execute_case(self, case):
        image = self.manifest['images'][case['image']]
        self.backend.deploy(self.board, image)
        status = quiescent(self.backend.info(self.board), self.identity, image)
        self.boot = status['boot_id']
        clock_deadline = self.backend.now()+90
        while True:
            try:
                clock = self.backend.request('GET_CLOCK', {})
            except (OSError, TimeoutError):
                clock = dict(state='unavailable')
            if clock['state'] == 'synchronized' and clock['leap'] == 'normal' and int(clock['uncertainty_ns']) <= 500000000:
                break
            require(self.backend.now() < clock_deadline, 'clock readiness deadline')
            self.backend.sleep(.5)
        require(self.backend.hello()['boot_id'] == self.boot, 'Console/WTP boot mismatch')
        case_root = self.e.root / case['id']
        case_root.mkdir(mode=0o700)
        # Standalone may wait up to one 120-second boundary, then a finite WSPR job.
        duration = 260 if case['action'] == 'standalone' else int(case['job']['total_duration_ns']) / 1e9 + (25 if self.gpio else 90)
        self.backend.start_captures(case_root, duration)
        try:
            if case['action'] == 'standalone':
                self.e.charge(case, self.boot)
                self.backend.command(self.board, 'SCHEDULE')
                info, status = self.wait(image, self.backend.now() + 130,
                    lambda i, s: s['state'] == 'running' and s['output_active'], lease=False)
                require(status['owner_id'] == 'e' * 32 and status['job_id'], 'standalone owner')
                self.checked_pin(info, image, True)
                self.backend.sleep(1)
                self.backend.command(self.board, 'STOP')
                self.backend.command(self.board, 'DISABLE')
                self.wait(image, self.backend.now() + 5,
                          lambda i, s: s['state'] == 'empty' and not s['output_active'] and
                          s['owner_id'] is None and s['job_id'] is None, lease=False)
                final_info, _ = self.observe(image)
                self.checked_pin(final_info, image, False)
            else:
                if case['action'] == 'fail':
                    self.backend.command(self.board, 'FAIL')
                self.lease_at = 0
                self.renew()
                loaded = self.backend.request('LOAD', case['job'])
                require(loaded['job_id'] == case['job']['job_id'], 'LOAD job identity')
                self.renew() # Keep preparation RPCs within the finite lease.
                # Loaded is explicitly non-RF; cue tests also observe external OFF here.
                self.cues(case)
                loaded_info, loaded_status = self.observe(image)
                require(loaded_status['state'] == 'loaded' and not loaded_status['output_active'],
                        'LOAD unexpectedly active')
                require(loaded_status['owner_id'] == self.owner and loaded_status['job_id'] == case['job']['job_id'],
                        'loaded ownership changed')
                require(not loaded_info['tx_indicator_requested'], 'LOAD requested a TX indication')
                if not case['cue']:
                    self.checked_pin(loaded_info, image, False)
                if image['selection'] in (1,2):
                    require(loaded_info['indicator_output_known'] and not loaded_info['indicator_output_on'],
                            'external LED used for a non-TX cue')
                self.backend.sleep(1)
                self.renew()
                clock_requested = self.backend.now()
                clock = self.backend.request('GET_CLOCK', {})
                require(clock['state'] == 'synchronized' and clock['leap'] == 'normal' and
                        int(clock['uncertainty_ns']) <= 500000000, 'accepted clock required')
                clock_age_ns = int((self.backend.now()-clock_requested)*1e9+.999)
                target = (int(clock['utc_now_ns']) + clock_age_ns + 5_000_000_999) // 1000 * 1000
                self.e.charge(case, self.boot)
                self.backend.request('ARM', dict(job_id=case['job']['job_id'], start_utc_ns=str(target),
                                                max_start_uncertainty_ns='500000000'))
                armed_at = self.backend.now()
                action = case['action']
                if action == 'cancel':
                    _, armed = self.observe(image)
                    require(armed['state'] == 'armed' and not armed['output_active'], 'armed cancellation')
                    self.backend.request('ABORT', dict(job_id=case['job']['job_id']))
                ran = acted = False
                inactive_since = None
                terminal = None
                end = armed_at + duration - 8
                while self.backend.now() < end:
                    if not (action == 'gp14' and acted):
                        self.renew() # GP14 may have already cleared the owner.
                    info, s = self.observe(image)
                    require((s['owner_id'] == self.owner or action == 'gp14' and acted and s['owner_id'] is None) and
                            s['job_id'] == case['job']['job_id'], 'case ownership changed')
                    if s['state'] == 'running':
                        if action != 'inhibited' and not s['output_active']:
                            # Hardware can finish between the foreground poll and
                            # Console snapshot. Accept only a short reconciliation
                            # interval; never count inactive Running as an RF run.
                            if inactive_since is None:
                                inactive_since = self.backend.now()
                            require(self.backend.now()-inactive_since < 1, 'running engine stayed inactive')
                            self.backend.sleep(.1)
                            continue
                        inactive_since = None
                        if not ran:
                            running_at = self.backend.now()
                            ran = True
                            self.cues(case, active=True) # Exercise Identify/AP while TX is actually active.
                        if action != 'inhibited':
                            require(s['output_active'] is True, 'running without active engine')
                            if image['selection'] != 3:
                                require(info['indicator_output_known'] and info['indicator_output_on'] and
                                        info['tx_indicator_ready'], 'active TX lacks checked indicator')
                                self.checked_pin(info, image, True)
                            else:
                                require(not info['tx_indicator_requested'] and not info['indicator_output_on'],
                                        'disabled indication requested an output')
                                self.checked_pin(info, image, False)
                        else:
                            require(not s['output_active'] and not info['tx_indicator_requested'],
                                    'inhibited job requested RF indication')
                            self.checked_pin(info, image, False)
                        if not acted and action in ('abort', 'gp14') and self.backend.now() - running_at >= 1:
                            acted = True
                            if action == 'abort':
                                self.backend.request('ABORT', dict(job_id=case['job']['job_id']))
                            else:
                                self.backend.command(self.fixture, 'HOLD')
                    if s['state'] in ('completed', 'aborted', 'failed'):
                        terminal = s
                        break
                    self.backend.sleep(.1)
                require(terminal is not None, 'missing terminal state')
                expected = 'failed' if action == 'fail' else 'aborted' if action in ('cancel', 'abort', 'gp14') else 'completed'
                require(terminal['state'] == expected, 'unexpected terminal state')
                if expected == 'completed' and ran:
                    require(self.backend.now()-running_at >= int(case['job']['total_duration_ns'])/1e9-3,
                            'premature completion')
                require(not terminal['output_active'], 'terminal engine still active')
                require(ran or action in ('cancel', 'fail'), 'premature terminal without running observation')
                if action == 'fail':
                    require(info['led_rejected_writes'] > 0 and not ran, 'fault did not block launch')
                if action == 'gp14':
                    require(info.get('rf_safety_inhibited') is True and acted, 'missing GP14 safety latch')
                if action != 'fail' and terminal['owner_id'] is not None:
                    self.backend.request('RELEASE', {})
                self.wait(image, self.backend.now() + 22,
                    lambda i, s: not s['output_active'] and s['owner_id'] is None and
                    (image['selection'] == 3 or not i['tx_indicator_requested']), lease=False)
                if not case['cue']:
                    final_info, _ = self.observe(image)
                    self.checked_pin(final_info, image, False)
            if case['action'] == 'complete':
                self.cues(case, active=True) # Independent post-TX Identify observation.
            self.backend.sleep(3) # Capture post-stop cues/tail; no operator response needed.
            self.backend.finish_captures()
            if self.gpio and hasattr(self.backend, 'assess_rf'):
                self.backend.assess_rf(case, case_root)
            self.e.state['attempts'][-1]['result'] = ('PASS_GPIO_FUNCTIONAL' if self.gpio else
                                                    'AUTOMATION_PASS_PHYSICAL_REVIEW_PENDING')
            self.e.save()
        except BaseException as error:
            self.e.event('case_failure', dict(case=case['id'], type=type(error).__name__, message=str(error)))
            # Always stop transmitter before waiting for capture teardown.
            self.backend.abort(self.board)
            raise
        finally:
            self.backend.stop_captures()

    def run(self):
        failure = None
        try:
            save_json(self.e.root/'manifest.json', self.manifest)
            if hasattr(self.backend, 'select_cases'):
                self.backend.select_cases(self.cases)
            self.e.state.update(selected_cases=[c['id'] for c in self.cases],
                                evidence_mode='gpio-readback' if self.gpio else 'optical')
            self.backend.preflight(self.manifest, self.board, self.fixture)
            self.e.state['result'] = 'RUNNING'
            self.e.save()
            for case in self.cases:
                self.execute_case(case)
            self.e.state['result'] = ('PASS_GPIO_FUNCTIONAL_RF_REVIEW_PENDING' if self.gpio else
                                      'AUTOMATION_PASS_PHYSICAL_REVIEW_PENDING')
        except BaseException as error:
            failure = error
            self.e.state['result'] = 'STOP'
            self.e.event('failure', dict(type=type(error).__name__, message=str(error)))
        finally:
            # Backend tracks each snapshot durably before its first mutation.
            # Attempt both boards even if one fails to stop/restore.
            errors, dispositions = [], []
            for board in (self.board, self.fixture):
                if board:
                    try:
                        self.backend.abort(board)
                        dispositions.append(self.backend.restore(board, self.manifest['images']['restore']))
                    except BaseException as error:
                        errors.append(dict(board=board, type=type(error).__name__, message=str(error)))
            try:
                self.backend.stop_captures()
            except BaseException as error:
                errors.append(dict(stage='capture_cleanup', type=type(error).__name__, message=str(error)))
            self.e.state['cleanup'] = ('STOP_UNCERTAIN' if errors else 'UNCHANGED_NO_MUTATIONS'
                                       if dispositions and all(x == 'UNCHANGED' for x in dispositions)
                                       else 'VERIFIED_INHIBITED')
            if errors:
                self.e.state['result'] = 'STOP'
                self.e.event('cleanup_failure', errors)
            self.e.save()
        if failure:
            raise failure
        require(self.e.state['cleanup'] == 'VERIFIED_INHIBITED', 'restoration uncertain')
        return self.e.state
