"""Required CI outcomes use observed executions and qualified completion data."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/ci'))
import execution


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.audit = Path(self.temp.name)
        self.source = 'a' * 40
        self.environment = patch.dict(os.environ, {'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '1'})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def execute(self, code, context='probe'):
        execution.execute(self.audit / 'host.log', [sys.executable, '-c', code], self.audit, self.source, context)
        return json.loads((self.audit / 'execution.json').read_text())

    def verify(self, value):
        execution.verify(value, self.source, 123, 1, ('probe',))
        execution.verify_logs(value, self.audit)

    def test_actual_execution_is_bound_to_source_run_and_log(self):
        value = self.execute("print('actual child completion')")
        self.verify(value)
        for key, wrong in [('source', 'b' * 40), ('run_id', '124'), ('attempt', '2'), ('schema', 'unknown')]:
            changed = copy.deepcopy(value); changed[key] = wrong
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(changed)
        (self.audit / 'host.log').write_text('forged log')
        with self.assertRaisesRegex(ValueError, 'log differs'):
            self.verify(value)

    def test_missing_duplicate_empty_and_extra_fields_refuse(self):
        value = self.execute("print('complete')")
        mutations = [lambda v: v.update(records=[]), lambda v: v['records'].append(v['records'][0]),
                     lambda v: v['records'][0].update(context='wrong'), lambda v: v.update(extra=True),
                     lambda v: v['records'][0].update(extra=True), lambda v: v['records'][0].update(returncode=True),
                     lambda v: v['records'][0].update(elapsed_s=float('nan')),
                     lambda v: v['records'][0]['evidence'].update(count=True),
                     lambda v: v['records'][0].update(log='../outside.log')]
        for mutation in mutations:
            changed = copy.deepcopy(value); mutation(changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.verify(changed)

    def test_nonzero_exit_and_spawn_failure_are_recorded_not_passed(self):
        with self.assertRaisesRegex(RuntimeError, 'child_exit=17'):
            self.execute('raise SystemExit(17)')
        value = json.loads((self.audit / 'execution.json').read_text())
        self.assertEqual(value['records'][0]['outcome'], 'failed')
        with self.assertRaises(ValueError):
            self.verify(value)
        (self.audit / 'execution.json').unlink()
        with self.assertRaisesRegex(RuntimeError, 'stage=missing'):
            execution.execute(self.audit / 'missing.log', ['/no/such/ci-fixture'], self.audit, self.source, 'missing')

    def test_controlled_timeout_retains_primary_and_cleanup_errors(self):
        class Child:
            pid = 42
            returncode = None
            waited = False
            def wait(self, timeout):
                if not self.waited:
                    self.waited = True
                    raise subprocess.TimeoutExpired('observed-held-command', timeout)
                return 0
        with patch.object(execution.subprocess, 'Popen', return_value=Child()), \
             patch.object(execution.os, 'killpg', side_effect=PermissionError('owned signal denied')):
            with self.assertRaises(RuntimeError) as result:
                self.execute('held')
        cause = result.exception.__cause__
        self.assertIsInstance(cause, BaseExceptionGroup)
        self.assertIsInstance(cause.exceptions[0], subprocess.TimeoutExpired)
        self.assertIsInstance(cause.exceptions[1], PermissionError)

    @unittest.skipIf(os.name == 'nt', 'POSIX owned process groups')
    def test_leader_exit_with_observed_descendant_cannot_pass(self):
        code = ("import subprocess,sys\n"
                "p=subprocess.Popen([sys.executable,'-c',\"import signal;print('READY',flush=True);signal.pause()\"],stdout=subprocess.PIPE,text=True)\n"
                "assert p.stdout.readline().strip()=='READY'\n")
        with self.assertRaisesRegex(RuntimeError, 'owned descendants remain'):
            self.execute(code)

    def test_evidence_write_failure_preserves_the_child_failure(self):
        with patch.object(Path, 'write_text', side_effect=OSError('evidence disk full')):
            with self.assertRaises(BaseExceptionGroup) as result:
                self.execute('raise SystemExit(17)')
        self.assertIn('child_exit=17', str(result.exception.exceptions[0]))
        self.assertIn('disk full', str(result.exception.exceptions[1]))

    def test_log_read_failure_preserves_the_child_failure(self):
        with patch.object(Path, 'read_bytes', side_effect=OSError('log storage unavailable')):
            with self.assertRaises(BaseExceptionGroup) as result:
                self.execute('raise SystemExit(17)')
        self.assertIn('child_exit=17', str(result.exception.exceptions[0]))
        self.assertIn('storage unavailable', str(result.exception.exceptions[1]))

    def test_node_summary_requires_actual_nonempty_unskipped_execution(self):
        good = '\n'.join('ℹ '+k+' '+str(v) for k, v in {'tests': 2, 'pass': 2, 'fail': 0, 'cancelled': 0, 'skipped': 0, 'todo': 0}.items())
        self.assertEqual(execution.evidence('npm', good, self.audit), {'kind': 'node-test', 'count': 2})
        for bad in ['', good.replace('tests 2', 'tests 0'), good.replace('skipped 0', 'skipped 1'),
                    good.replace('cancelled 0', 'cancelled 1'), good.replace('pass 2', 'pass 1'), good+'\nℹ tests 2']:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                execution.evidence('npm', bad, self.audit)

    def test_unittest_and_browser_completion_are_qualified(self):
        self.assertEqual(execution.evidence('packaging', 'Ran 2 tests in 1s\n\nOK\n', self.audit)['count'], 2)
        for bad in ['Ran 0 tests in 0s\nOK\n', 'Ran 2 tests in 1s\nOK (skipped=1)\n', 'OK\n']:
            with self.assertRaises(ValueError):
                execution.evidence('packaging', bad, self.audit)
        good = {'real_crypto': True, 'type2': True, 'type3': True, 'pair': True}
        execution.evidence('wspr', json.dumps(good), self.audit)
        for bad in [{}, {**good, 'pair': False}, {**good, 'pair': 1}]:
            with self.assertRaises(ValueError):
                execution.evidence('wspr', json.dumps(bad), self.audit)
        with self.assertRaises(ValueError):
            execution.evidence('wspr', json.dumps(good)+'\n'+json.dumps(good), self.audit)

    def test_submission_completion_requires_nonempty_executed_checks(self):
        result = self.audit / 'submission-ui/results.json'
        result.parent.mkdir()
        for value in [{'physical_device': False}, {'physical_device': False, 'checks': []}]:
            result.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                execution.evidence('submission', '', self.audit)
        result.write_text(json.dumps({'physical_device': False, 'checks': ['observed mutation refusal']}))
        execution.evidence('submission', '', self.audit)

    def test_contract_and_ctest_need_nonempty_completion_summaries(self):
        execution.evidence('ctest', '100% tests passed, 0 tests failed out of 2\n', self.audit)
        execution.evidence('wtp-contract', 'WTP/1 contract valid: 2 schema cases, 2 raw JSON cases, 1 framing case, and 2 transition cases\n', self.audit)
        for context, output in [('ctest', ''), ('ctest', 'No tests were found'),
                                ('ctest', '100% tests passed, 0 tests failed out of 0'),
                                ('wtp-contract', 'WTP/1 contract valid')]:
            with self.subTest(context=context, output=output), self.assertRaises(ValueError):
                execution.evidence(context, output, self.audit)

    def test_ctest_requires_exact_names_and_no_internal_skips(self):
        def check(xml, names=('one',)):
            return execution.ctest_result(ET.fromstring(xml), names)
        self.assertEqual(check('<testsuite><testcase name="one"/></testsuite>'), 1)
        for bad in ['<testsuite/>', '<testsuite><testcase name="wrong"/></testsuite>',
                    '<testsuite><testcase name="one"/><testcase name="one"/></testsuite>',
                    '<testsuite><testcase name="one"><failure/></testcase></testsuite>',
                    '<testsuite><testcase name="one"><skipped/></testcase></testsuite>',
                    '<testsuite><testcase name="one"><system-out>OK (skipped=1)</system-out></testcase></testsuite>']:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                check(bad)

    def framework_fixture(self, kind='node-test', count=2):
        expected={'kind':kind,'count':count,'entrypoint':'tests/one.py' if kind=='unittest' else 'tests/one.test.mjs'}
        policy={'schema':'ci-ctest-completion/1','tests':{'one':expected},'contexts':{
            'npm':{'kind':'node-test','count':2},'packaging':{'kind':'unittest','count':2},
            'browser-lifecycle':{'kind':'node-test','count':2}}}
        registered={'tests':[{'name':'one','command':['python' if kind=='unittest' else 'node',str(self.audit/expected['entrypoint'])]}]}
        output=('Ran '+str(count)+' tests in 0.01s\nOK\n' if kind=='unittest' else
                '\n'.join('# '+key+' '+str(value) for key,value in {'tests':count,'pass':count,'fail':0,'cancelled':0,'skipped':0,'todo':0}.items()))
        suite=ET.Element('testsuite');case=ET.SubElement(suite,'testcase',name='one');ET.SubElement(case,'system-out').text=output
        return policy,registered,suite

    def test_ctest_framework_counts_bind_to_actual_entrypoint_and_output(self):
        for kind in ('node-test','unittest'):
            policy,registered,suite=self.framework_fixture(kind)
            self.assertEqual(execution.ctest_result(suite,['one'],policy,registered,command_root=self.audit),1)

    def test_green_ctest_cannot_hide_zero_or_partial_framework_discovery(self):
        for kind in ('node-test','unittest'):
            policy,registered,_=self.framework_fixture(kind,2)
            for count in (0,1):
                _,_,suite=self.framework_fixture(kind,count)
                with self.subTest(kind=kind,count=count),self.assertRaises(ValueError):execution.ctest_result(suite,['one'],policy,registered)

    def test_green_ctest_cannot_hide_inner_skip_or_forged_duplicate_summary(self):
        policy,registered,suite=self.framework_fixture()
        node=suite.find('testcase/system-out');good=node.text
        for bad in [good.replace('skipped 0','skipped 1'),good+'\n# tests 2',good+'\nok 1 - hidden # SKIP',good.replace('todo 0','todo 1'),good+'\n[This part of the test output was removed since it exceeds the threshold of 1024 bytes.]']:
            node.text=bad
            with self.assertRaises(ValueError):execution.ctest_result(suite,['one'],policy,registered)

    def test_completion_policy_refuses_unknown_fields_types_and_missing_contexts(self):
        policy,_,_=self.framework_fixture()
        for change in [lambda p:p.update(extra=True),lambda p:p['tests']['one'].update(count=True),
                       lambda p:p['tests']['one'].update(entrypoint='tests/../outside.py'),
                       lambda p:p['contexts'].pop('packaging'),lambda p:p['tests']['one'].update(kind='exit')]:
            value=copy.deepcopy(policy);change(value)
            with self.assertRaises(ValueError):execution.completion_policy(value)

    def test_new_framework_source_cannot_be_omitted_from_policy(self):
        policy,registered,_=self.framework_fixture()
        (self.audit/'tests').mkdir()
        (self.audit/'tests/one.test.mjs').write_text("import test from 'node:test';\n")
        other=self.audit/'tests/new.test.mjs';other.write_text("import test from 'node:test';\n")
        registered['tests'].append({'name':'unlisted','command':['node',str(other)]})
        with self.assertRaisesRegex(ValueError,'missing from completion policy'):
            execution.completion_registration(registered,policy,source_root=self.audit)

    def test_framework_with_missing_command_or_wrong_source_root_is_refused(self):
        policy,registered,suite=self.framework_fixture()
        for command in [[],['node','/another-checkout/tests/one.test.mjs']]:
            registered['tests'][0]['command']=command
            with self.assertRaises(ValueError):execution.ctest_result(suite,['one'],policy,registered,command_root=self.audit)

    def test_required_prerequisite_skip_is_not_a_passing_native_case(self):
        policy,registered,suite=self.framework_fixture()
        registered['tests'].append({'name':'native','command':['native']})
        case=ET.SubElement(suite,'testcase',name='native');ET.SubElement(case,'system-out').text='SKIP actual second-IPv4 TLS rebind: unavailable\n'
        with self.assertRaisesRegex(ValueError,'prerequisite was skipped'):
            execution.ctest_result(suite,['one','native'],policy,registered)

    def test_actual_partial_command_records_failure_and_forged_completion_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'Incomplete expected framework discovery'):
            execution.execute(self.audit/'host.log',[sys.executable,'-c',"print('Ran 1 test in 0.01s\\nOK')"],self.audit,self.source,'packaging',expected={'kind':'unittest','count':2})
        value=json.loads((self.audit/'execution.json').read_text());record=value['records'][0]
        self.assertEqual(record['returncode'],0);self.assertEqual(record['outcome'],'failed')
        record['outcome']='passed';record['evidence']['count']=2
        execution.verify(value,self.source,123,1,('packaging',))
        with self.assertRaisesRegex(ValueError,'Completion evidence differs'):execution.verify_logs(value,self.audit)

    def test_standalone_policy_rejects_missing_partial_or_typed_completion(self):
        policy,_,_=self.framework_fixture()
        report={'records':[{'context':context,'evidence':copy.deepcopy(expected)} for context,expected in policy['contexts'].items()]}
        execution.verify_completion_counts(report,policy)
        for change in [lambda r:r['records'].pop(),lambda r:r['records'][0]['evidence'].update(count=1),lambda r:r['records'][0]['evidence'].update(count=True)]:
            value=copy.deepcopy(report);change(value)
            with self.assertRaises(ValueError):execution.verify_completion_counts(value,policy)

    def test_optimized_python_cannot_disable_required_assertions(self):
        from types import SimpleNamespace
        with patch.object(execution.sys,'flags',SimpleNamespace(optimize=1)):
            with self.assertRaisesRegex(ValueError,'optimized Python'):execution.require_unoptimized_python()
        execution.require_unoptimized_python()



if __name__ == '__main__':
    unittest.main()
