"""Source-bound command evidence; watchdogs bound hangs, never assert readiness."""
import hashlib
import ast
import sys
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import threading

# Distinct command contexts, not logical test-case counts. Keep both carriers.
HOST_CONTEXTS = (
    'ctest', 'wtp-contract', 'npm', 'packaging', 'browser-lifecycle',
    'frequency', 'first-use', 'session-timeout', 'progress', 'recovery',
    'submission', 'hostname', 'organization', 'wspr', 'message-frequency',
    'operator', 'sections-consumer', 'sections-engineering',
)
NATIVE = {
    'frequency': ('consumer-ui/result.json', {'passed': True, 'policy_rejection': True}),
    'first-use': ('first-wspr-ui/first-use-result.json', {'passed': True, 'profile': 'network'}),
    'session-timeout': ('session-timeout-ui/results.json', {'virtual_time': True, 'draft_preserved': True, 'no_mutations': True}),
    'progress': (None, {'real_crypto': True, 'late_edit': True, 'explicit_application': True}),
    'recovery': (None, {'independent_contexts': 3, 'lost_commit_once': True, 'readback_review_required': True}),
    'submission': ('submission-ui/results.json', {'physical_device': False}),
    'hostname': (None, {'real_crypto': True, 'new_boot_readback': True, 'cancel_countdown': True}),
    'organization': (None, {'real_crypto': True, 'production_routes': True, 'no_navigation_mutations': True}),
    'wspr': (None, {'real_crypto': True, 'type2': True, 'type3': True, 'pair': True}),
    'message-frequency': ('message_frequency_ui_integration/result.json', {'passed': True, 'surfaces': ['consumer', 'engineering']}),
    'operator': (None, {'api': 'production HTTP/crypto', 'hardware': False}),
    'sections-consumer': ('sections-consumer/results.json', {'carrier': 'consumer', 'physical_device': False}),
    'sections-engineering': ('sections-engineering/results.json', {'carrier': 'engineering', 'physical_device': False}),
}


class CommandInterrupted(RuntimeError):
    """Cancellation must escape I/O recovery that catches OSError."""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def framework_evidence(kind, output):
    require('[This part of the test output was removed' not in output, 'Framework output was truncated')
    if kind == 'node-test':
        def count(key):
            values = re.findall(r'^(?:ℹ|#)\s+' + key + r'\s+(\d+)\s*$', output, re.M)
            require(len(values) == 1, 'Missing or duplicate Node test summary: ' + key)
            return int(values[0])
        total, passed = count('tests'), count('pass')
        require(total > 0 and passed == total and all(count(k) == 0 for k in ('fail', 'cancelled', 'skipped', 'todo')),
                'Incomplete or skipped Node test execution')
        require(not re.search(r'^\s*(?:not\s+)?ok\b[^\n]*#\s*(?:SKIP|TODO)\b', output, re.M | re.I),
                'Required Node case was skipped or TODO')
    elif kind == 'unittest':
        totals = re.findall(r'^Ran (\d+) tests? in ', output, re.M)
        require(len(totals) == 1 and int(totals[0]) > 0 and len(re.findall(r'^OK\s*$', output, re.M)) == 1,
                'Missing or incomplete unittest execution')
        require(not re.search(r'\bskipped=[1-9][0-9]*\b|^FAILED\b', output, re.M),
                'Internally skipped or failed unittest execution')
        total = int(totals[0])
    else:
        raise ValueError('Unknown completion framework')
    return {'kind': kind, 'count': total}


def completion_policy(value):
    require(isinstance(value, dict) and set(value) == {'schema', 'tests', 'contexts'} and
            value['schema'] == 'ci-ctest-completion/1', 'Invalid completion policy')
    require(isinstance(value['tests'], dict) and bool(value['tests']), 'Empty framework policy')
    for name, expected in value['tests'].items():
        require(isinstance(name, str) and re.fullmatch(r'[a-zA-Z0-9_-]+', name) and
                isinstance(expected, dict) and set(expected) == {'kind', 'count', 'entrypoint'},
                'Invalid framework identity')
        _completion_expected(expected)
        path = expected['entrypoint']
        require(isinstance(path, str) and re.fullmatch(r'tests/[a-zA-Z0-9_./-]+\.(?:py|mjs|js)', path) and
                '..' not in Path(path).parts and
                (path.endswith('.py') if expected['kind'] == 'unittest' else path.endswith(('.js', '.mjs'))),
                'Invalid framework entrypoint')
    require(isinstance(value['contexts'], dict) and
            set(value['contexts']) == {'npm', 'packaging', 'browser-lifecycle'}, 'Missing standalone framework policy')
    for context, expected in value['contexts'].items():
        require(isinstance(expected, dict) and set(expected) == {'kind', 'count'}, 'Invalid standalone completion')
        _completion_expected(expected)
        require(expected['kind'] == ('unittest' if context == 'packaging' else 'node-test'),
                'Standalone framework kind mismatch')
    return value


def _completion_expected(value):
    require(value.get('kind') in ('node-test', 'unittest') and type(value.get('count')) is int and
            value['count'] > 0, 'Invalid expected completion count')


def require_unoptimized_python():
    require(sys.flags.optimize == 0, 'Required assertion-based checks cannot run with optimized Python')


def framework_source_kind(path):
    if path.suffix in ('.js', '.mjs'):
        return 'node-test' if re.search(r"(?:from\s*|require\(\s*)['\"]node:test['\"]", path.read_text()) else None
    if path.suffix == '.py':
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                    isinstance(base, ast.Attribute) and base.attr == 'TestCase' or
                    isinstance(base, ast.Name) and base.id == 'TestCase' for base in node.bases):
                return 'unittest'
    return None


def completion_registration(registered, policy, source_root=None, command_root=None):
    completion_policy(policy)
    require(isinstance(registered, dict) and isinstance(registered.get('tests'), list), 'Missing registered commands')
    entries = registered['tests']
    require(all(isinstance(entry, dict) and isinstance(entry.get('name'), str) for entry in entries), 'Invalid registered test identity')
    names = [entry['name'] for entry in entries]
    require(len(names) == len(set(names)) and set(policy['tests']) <= set(names), 'Required framework registration missing')
    root = Path(source_root).resolve() if source_root is not None else None
    command_base = Path(command_root).resolve() if command_root is not None else root
    for entry in entries:
        name, command = entry['name'], entry.get('command', [])
        require(isinstance(command, list) and all(isinstance(arg, str) for arg in command), 'Invalid registered command')
        detected = 'node-test' if command and Path(command[0]).name in ('node', 'node.exe') and '--test' in command else None
        if command and '-m' in command and 'unittest' in command:
            detected = 'unittest'
        if root is not None:
            for arg in command[1:]:
                if arg.startswith('-') or not arg.endswith(('.py', '.js', '.mjs')):
                    continue
                candidate = Path(arg)
                candidate = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
                if candidate.is_relative_to(root) and candidate.is_file():
                    kind = framework_source_kind(candidate)
                    if kind:
                        require(detected in (None, kind), 'Ambiguous registered framework')
                        detected = kind
        expected = policy['tests'].get(name)
        if detected is not None:
            require(expected is not None and expected['kind'] == detected, 'Framework is missing from completion policy: ' + name)
        if expected is not None:
            if root is not None:
                require((root / expected['entrypoint']).is_file(), 'Required framework source missing: ' + name)
            if command_base is not None:
                require(any((Path(arg) if Path(arg).is_absolute() else command_base / arg).resolve() == command_base / expected['entrypoint']
                            for arg in command[1:]), 'Framework command selects the wrong source root: ' + name)
            require(bool(command) and any(arg == expected['entrypoint'] or arg.endswith('/' + expected['entrypoint'])
                                         for arg in command[1:]), 'Required framework command/entrypoint missing: ' + name)


def verify_completion_counts(report, policy):
    completion_policy(policy)
    records = {entry['context']: entry for entry in report['records']}
    for context, expected in policy['contexts'].items():
        observed = records.get(context, {}).get('evidence')
        require(isinstance(observed, dict) and set(observed) == {'kind', 'count'}, 'Missing standalone framework evidence')
        _completion_expected(observed)
        require(observed == expected,
                'Incomplete standalone framework count: ' + context)

def ctest_result(suite, names, policy=None, registered=None, command_root=None):
    cases = suite.findall('testcase')
    actual = [case.get('name') for case in cases]
    require(bool(names) and len(actual) == len(set(actual)) == len(names) and set(actual) == set(names),
            'Incomplete, duplicate, or mismatched CTest inventory')
    require(all(case.find(tag) is None for case in cases for tag in ('failure', 'error', 'skipped')),
            'Failed or skipped required CTest suite')
    require(not any(re.search(r'\bskipped=[1-9][0-9]*\b', ''.join(case.itertext())) for case in cases),
            'Internally skipped required CTest suite')
    if policy is not None:
        completion_registration(registered, policy, command_root=command_root)
        for case in cases:
            output = ''.join(case.itertext())
            require(not re.search(r'^\s*SKIP(?:\s|:)', output, re.M), 'Required prerequisite was skipped: ' + case.get('name'))
            expected = policy['tests'].get(case.get('name'))
            if expected is not None:
                observed = framework_evidence(expected['kind'], output)
                require(observed['count'] == expected['count'], 'Incomplete framework discovery: ' + case.get('name'))
            elif re.search(r'^(?:ℹ|#)\s+tests\s+\d+\s*$|^Ran \d+ tests? in ', output, re.M):
                raise ValueError('Observed framework absent from policy: ' + case.get('name'))
    return len(cases)


def evidence(context, output, audit):
    if context == 'ctest':
        totals = re.findall(r'^100% tests passed, 0 tests failed out of (\d+)\s*$', output, re.M)
        require(len(totals) == 1 and int(totals[0]) > 0, 'Missing or incomplete CTest execution summary')
        return {'kind': 'ctest', 'count': int(totals[0])}
    if context == 'wtp-contract':
        totals = re.findall(r'^WTP/1 contract valid: (\d+) schema cases, (\d+) raw JSON cases, (\d+) framing case, and (\d+) transition cases\s*$', output, re.M)
        require(len(totals) == 1 and all(int(x) > 0 for x in totals[0]), 'Missing or empty WTP contract completion')
        return {'kind': 'wtp-contract', 'count': sum(map(int, totals[0]))}
    if context in ('npm', 'browser-lifecycle'):
        return framework_evidence('node-test', output)
    if context == 'packaging':
        return framework_evidence('unittest', output)
    if context in NATIVE:
        filename, expected = NATIVE[context]
        if filename:
            value = json.loads((audit / filename).read_text())
        else:
            candidates = []
            for line in output.splitlines():
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if isinstance(item, dict) and all(type(item.get(k)) is type(v) and item[k] == v for k, v in expected.items()):
                    candidates.append(item)
            require(len(candidates) == 1, 'Missing or ambiguous browser completion evidence: ' + context)
            value = candidates[0]
        require(isinstance(value, dict) and all(type(value.get(k)) is type(v) and value[k] == v for k, v in expected.items()),
                'Incomplete browser context: ' + context)
        if context in ('submission', 'sections-consumer', 'sections-engineering'):
            require('checks' in value, 'Missing browser checks')
        if 'checks' in value:
            require(isinstance(value['checks'], list) and bool(value['checks']) and
                    all(isinstance(x, str) and x for x in value['checks']), 'Empty browser checks')
        return {'kind': 'native-browser', 'count': 1}
    return {'kind': 'exit', 'count': 1}


def execute(log, command, cwd, source, context=None, watchdog=3600, expected=None):
    # Install ownership before spawn. A repeated cancellation cannot interrupt
    # cleanup or turn the first interruption into a successful receipt.
    handlers = {}
    cancellation = {'spawning': False, 'closing': False, 'interruption': None}
    failure = None
    def cancelled(number, frame):
        if cancellation['interruption'] is None:
            cancellation['interruption'] = CommandInterrupted(f'CI command interrupted by signal={number}')
            if not cancellation['spawning'] and not cancellation['closing']:
                raise cancellation['interruption']
    try:
        if threading.current_thread() is threading.main_thread():
            for number in (signal.SIGINT, signal.SIGTERM):
                handlers[number] = signal.signal(number, cancelled)
        return _execute(log, command, cwd, source, context, watchdog, expected, cancellation)
    except BaseException as error:
        failure = error
        raise
    finally:
        cancellation['closing'] = True
        restoration = []
        for number, handler in handlers.items():
            try:
                signal.signal(number, handler)
            except BaseException as error:
                restoration.append(error)
        # A cancellation during receipt persistence or handler handoff must
        # not disappear after the child has already completed successfully.
        interrupted = cancellation['interruption'] if failure is None else None
        if restoration:
            primary = failure if failure is not None else interrupted
            raise BaseExceptionGroup('command and signal restoration failed',
                                     ([primary] if primary is not None else []) + restoration)
        if interrupted is not None:
            raise interrupted


def _execute(log, command, cwd, source, context, watchdog, expected, cancellation):
    """The existing 60-minute CI job budget is a hang guard, not a speed oracle."""
    require(type(watchdog) in (int, float) and math.isfinite(watchdog) and watchdog > 0, 'Invalid execution watchdog')
    audit = log.parent
    report = audit / 'execution.json'
    identity = {'source': source, 'run_id': os.environ.get('GITHUB_RUN_ID'), 'attempt': os.environ.get('GITHUB_RUN_ATTEMPT')}
    data = json.loads(report.read_text()) if report.exists() else {'schema': 'ci-execution/1', **identity, 'records': []}
    if report.exists():
        verify(data, source, identity['run_id'], identity['attempt'], ())
    require(all(data[k] == v for k, v in identity.items()), 'Execution evidence source/run mismatch')
    context = context or 'command-' + str(len(data['records']) + 1)
    require(not any(r['context'] == context for r in data['records']), 'Duplicate execution context')
    if context in NATIVE and NATIVE[context][0]:
        require(not (audit / NATIVE[context][0]).exists(), 'Stale browser result before execution')
    started = time.monotonic()
    child = None
    primary = None
    try:
        with log.open('a') as output:
            output.write('+ ' + ' '.join(command) + '\n'); output.flush()
            offset = output.tell()
            try:
                # Defer raising during Popen registration without masking signals in
                # the child. It must inherit ordinary cancellation behavior.
                cancellation['spawning'] = True
                try:
                    child = subprocess.Popen(command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT,
                                             start_new_session=os.name != 'nt')
                finally:
                    cancellation['spawning'] = False
                if cancellation['interruption'] is not None:
                    raise cancellation['interruption']
                child.wait(timeout=watchdog)
                if os.name != 'nt':
                    try:
                        os.killpg(child.pid, 0)
                    except ProcessLookupError:
                        pass
                    else:
                        raise RuntimeError(f'stage={context}; child_exit={child.returncode}; owned descendants remain after leader exit')
                if child.returncode:
                    raise RuntimeError(f'stage={context}; child_exit={child.returncode}; log={log.name}')
            except BaseException as error:
                primary = error
                cancellation['closing'] = True
                if child is not None:
                    failures = []
                    try:
                        if os.name != 'nt':
                            os.killpg(child.pid, signal.SIGKILL)
                        elif child.poll() is None:
                            child.kill()
                    except ProcessLookupError:
                        pass
                    except BaseException as cleanup:
                        failures.append(cleanup)
                    try:
                        child.wait(timeout=5)
                    except BaseException as cleanup:
                        failures.append(cleanup)
                    if failures:
                        primary = BaseExceptionGroup('command and owned cleanup failed', [primary, *failures])
            finally:
                cancellation['closing'] = True
                output.flush()
    except BaseException as finalization:
        if primary is None and cancellation['interruption'] is not None:
            primary = cancellation['interruption']
        if primary is not None and primary is not finalization:
            raise BaseExceptionGroup('command and log finalization failed', [primary, finalization]) from None
        raise
    if primary is None and cancellation['interruption'] is not None:
        primary = cancellation['interruption']
    try:
        raw = log.read_bytes()[offset:]
    except BaseException as diagnostic:
        if primary is None and cancellation['interruption'] is not None:
            primary = cancellation['interruption']
        if primary is not None:
            raise BaseExceptionGroup('command and log read failed', [primary, diagnostic]) from None
        raise
    qualified = None
    if primary is None:
        try:
            qualified = evidence(context, raw.decode(errors='replace'), audit)
            if expected is not None:
                require(isinstance(expected, dict) and set(expected) == {'kind', 'count'}, 'Invalid command completion expectation')
                _completion_expected(expected)
                require(qualified == expected, 'Incomplete expected framework discovery: ' + context)
        except BaseException as error:
            interrupted = cancellation['interruption']
            primary = (BaseExceptionGroup('command cancellation and qualification failed', [interrupted, error])
                       if interrupted is not None and interrupted is not error else error)
    if primary is None and cancellation['interruption'] is not None:
        primary = cancellation['interruption']
    data['records'].append({'context': context, 'command': command, 'cwd': str(cwd),
                            'elapsed_s': time.monotonic() - started,
                            'returncode': child.returncode if child else None,
                            'outcome': 'passed' if primary is None else 'failed',
                            'log': log.name, 'offset': offset, 'bytes': len(raw),
                            'sha256': hashlib.sha256(raw).hexdigest(), 'evidence': qualified})
    temporary = report.with_suffix('.tmp')
    try:
        temporary.write_text(json.dumps(data, indent=2) + '\n'); temporary.replace(report)
        if primary is None and cancellation['interruption'] is not None:
            primary = cancellation['interruption']
            data['records'][-1]['outcome'] = 'failed'
            temporary.write_text(json.dumps(data, indent=2) + '\n'); temporary.replace(report)
    except BaseException as persistence:
        if primary is None and cancellation['interruption'] is not None:
            primary = cancellation['interruption']
        if primary is not None:
            raise BaseExceptionGroup('command and evidence persistence failed', [primary, persistence]) from None
        raise
    if primary is not None:
        raise RuntimeError(f'stage={context}; elapsed={time.monotonic()-started:.3f}s; '
                           f'hang_guard={watchdog}s; log={log.name}; {primary}') from primary


def verify(report, source, run_id, attempt, contexts=HOST_CONTEXTS):
    require(isinstance(report, dict) and set(report) == {'schema', 'source', 'run_id', 'attempt', 'records'}, 'Malformed execution report')
    require(report['schema'] == 'ci-execution/1' and report['source'] == source and
            report['run_id'] == (str(run_id) if run_id is not None else None) and
            report['attempt'] == (str(attempt) if attempt is not None else None), 'Execution report identity mismatch')
    records = report['records']
    require(isinstance(records, list) and bool(records), 'Empty execution evidence')
    names = []
    for record in records:
        require(isinstance(record, dict) and set(record) == {'context', 'command', 'cwd', 'elapsed_s', 'returncode', 'outcome', 'log', 'offset', 'bytes', 'sha256', 'evidence'}, 'Malformed command evidence')
        require(isinstance(record['context'], str) and record['context'] and isinstance(record['command'], list) and
                bool(record['command']) and all(isinstance(x, str) and x for x in record['command']), 'Invalid command identity')
        require(type(record['returncode']) is int and record['returncode'] == 0 and record['outcome'] == 'passed', 'Command did not pass')
        require(type(record['elapsed_s']) in (int, float) and math.isfinite(record['elapsed_s']) and record['elapsed_s'] >= 0, 'Invalid command duration')
        require(isinstance(record['cwd'], str) and record['cwd'] and isinstance(record['log'], str) and
                re.fullmatch(r'[A-Za-z0-9_-]+\.log', record['log']) and
                all(type(record[k]) is int and record[k] >= 0 for k in ('offset', 'bytes')) and
                isinstance(record['sha256'], str) and re.fullmatch('[0-9a-f]{64}', record['sha256']), 'Invalid command log binding')
        e = record['evidence']
        require(isinstance(e, dict) and set(e) == {'kind', 'count'} and type(e['count']) is int and e['count'] > 0 and
                e['kind'] in ('exit', 'node-test', 'unittest', 'native-browser', 'ctest', 'wtp-contract'), 'Invalid completion evidence')
        required_kind = record['context'] if record['context'] in ('ctest', 'wtp-contract') else 'node-test' if record['context'] in ('npm', 'browser-lifecycle') else 'unittest' if record['context'] == 'packaging' else 'native-browser' if record['context'] in NATIVE else 'exit'
        require(e['kind'] == required_kind, 'Execution evidence kind mismatch')
        names.append(record['context'])
    require(len(names) == len(set(names)) and set(contexts) <= set(names), 'Missing or duplicate required execution context')


def verify_logs(report, audit):
    for record in report['records']:
        data = (audit / record['log']).read_bytes()
        raw = data[record['offset']:record['offset'] + record['bytes']]
        require(len(raw) == record['bytes'] and hashlib.sha256(raw).hexdigest() == record['sha256'], 'Execution log differs')
        require(evidence(record['context'], raw.decode(errors='replace'), audit) == record['evidence'], 'Completion evidence differs')
