"""Source-bound command evidence; watchdogs bound hangs, never assert readiness."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time

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


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ctest_result(suite, names):
    cases = suite.findall('testcase')
    actual = [case.get('name') for case in cases]
    require(bool(names) and len(actual) == len(set(actual)) == len(names) and set(actual) == set(names),
            'Incomplete, duplicate, or mismatched CTest inventory')
    require(all(case.find(tag) is None for case in cases for tag in ('failure', 'error', 'skipped')),
            'Failed or skipped required CTest suite')
    require(not any(re.search(r'\bskipped=[1-9][0-9]*\b', ''.join(case.itertext())) for case in cases),
            'Internally skipped required CTest suite')
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
        def count(key):
            values = re.findall(r'^(?:ℹ|#)\s+' + key + r'\s+(\d+)\s*$', output, re.M)
            require(len(values) == 1, 'Missing or duplicate Node test summary: ' + key)
            return int(values[0])
        total, passed = count('tests'), count('pass')
        require(total > 0 and passed == total and all(count(k) == 0 for k in ('fail', 'cancelled', 'skipped', 'todo')),
                'Incomplete or skipped Node test execution')
        return {'kind': 'node-test', 'count': total}
    if context == 'packaging':
        totals = re.findall(r'^Ran (\d+) tests? in ', output, re.M)
        require(len(totals) == 1 and int(totals[0]) > 0 and re.search(r'^OK\s*$', output, re.M),
                'Missing or incomplete unittest execution')
        require(not re.search(r'\bskipped=[1-9][0-9]*\b', output), 'Internally skipped unittest execution')
        return {'kind': 'unittest', 'count': int(totals[0])}
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
        if 'checks' in value:
            require(isinstance(value['checks'], list) and bool(value['checks']) and
                    all(isinstance(x, str) and x for x in value['checks']), 'Empty browser checks')
        return {'kind': 'native-browser', 'count': 1}
    return {'kind': 'exit', 'count': 1}


def execute(log, command, cwd, source, context=None, watchdog=3600):
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
    with log.open('a') as output:
        output.write('+ ' + ' '.join(command) + '\n'); output.flush()
        offset = output.tell()
        try:
            child = subprocess.Popen(command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT,
                                     start_new_session=os.name != 'nt')
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
            output.flush()
    raw = log.read_bytes()[offset:]
    qualified = None
    if primary is None:
        try:
            qualified = evidence(context, raw.decode(errors='replace'), audit)
        except BaseException as error:
            primary = error
    data['records'].append({'context': context, 'command': command, 'cwd': str(cwd),
                            'elapsed_s': time.monotonic() - started,
                            'returncode': child.returncode if child else None,
                            'outcome': 'passed' if primary is None else 'failed',
                            'log': log.name, 'offset': offset, 'bytes': len(raw),
                            'sha256': hashlib.sha256(raw).hexdigest(), 'evidence': qualified})
    temporary = report.with_suffix('.tmp')
    try:
        temporary.write_text(json.dumps(data, indent=2) + '\n'); temporary.replace(report)
    except BaseException as persistence:
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
