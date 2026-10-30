"""Distribution integrity and wrong-identity failures must be hard failures."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import call, patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/ci'))
import bundle
import download
import publish
import run as ci_run


class TestingInputTests(unittest.TestCase):
    def test_documentation_version_uses_actual_build_stream(self):
        for ref, expected in [('refs/heads/main', 'main'), ('refs/heads/devel', 'devel'),
                              ('refs/tags/v1.0.0-beta.1', 'devel'),
                              ('refs/tags/v1.0.0', 'main')]:
            with self.subTest(ref=ref), patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'push', 'GITHUB_REF': ref}, clear=True):
                self.assertEqual(ci_run.documentation_version(), expected)
        with patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'push', 'GITHUB_REF': 'refs/heads/arbitrary'}, clear=True):
            with self.assertRaises(ValueError):
                ci_run.documentation_version()

    def test_semver_policy_matches_schema_and_rejects_unsafe_or_reserved_versions(self):
        schema = bundle.read_json(bundle.SCHEMA)['properties']['firmware_version']
        self.assertEqual(schema['pattern'], '^' + bundle.SEMVER + '$')
        self.assertEqual(schema['maxLength'], bundle.MAX_VERSION)
        for version, kind in [('1.0.0-beta.1', 'prerelease'), ('1.0.0', 'stable'),
                              ('12.34.56-rc.0+build.001', 'prerelease'), ('1.0.0+001', 'stable'),
                              ('0.1.0-ci.123.1', 'ci'), ('0.1.0-testing.1', 'testing')]:
            self.assertEqual(bundle.version_kind(version), kind)
        for version in ('v1.0.0', '01.0.0', '1.00.0', '1.0.01', '1.0', '1.0.0-beta.01',
                        '1.0.0+', '1.0.0-a..b', '1.0.0\n', '1.0.0/evil', '1.0.0;touch',
                        '1.0.0-' + 'a'*128, '1.0.0-ci.1.1', '0.1.0-ci.0.1',
                        '0.1.0-testing.01', '0.1.0-ci.1.1+forged', None):
            with self.subTest(version=version), self.assertRaises(ValueError):
                bundle.version_kind(version)

    def test_release_tag_inputs_require_exact_source_and_maintained_history(self):
        for version in ('1.0.0-beta.1', '1.0.0', '1.0.0+build.1'):
            for event in ('push', 'workflow_dispatch'):
                env = dict(CI_PROFILE='consumer', CI_STREAM='release', GITHUB_RUN_ID='123',
                           GITHUB_RUN_ATTEMPT='1', GITHUB_EVENT_NAME=event,
                           GITHUB_REF='refs/tags/v'+version, CI_EVENT_SHA='a'*40,
                           GITHUB_REPOSITORY='WsprryPi/WsprryPico')
                def capture(*args):
                    return 'a'*40 if args[:2] == ('git', 'rev-parse') else ''
                with self.subTest(version=version,event=event), patch.dict(os.environ,env,clear=True), \
                     patch.object(ci_run,'check_control_policy') as control_policy, \
                     patch.object(ci_run,'capture',side_effect=capture), \
                     patch.object(ci_run.Path,'exists',return_value=False), \
                     patch.object(ci_run.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
                    self.assertEqual(ci_run.inputs()[1], version)
                    control_policy.assert_called_once_with(stable_release=bundle.version_kind(version) == 'stable')
                    with patch.object(ci_run.subprocess,'run',return_value=SimpleNamespace(returncode=1)):
                        with self.assertRaisesRegex(ValueError,'maintained'):
                            ci_run.inputs()
                    with patch.dict(os.environ,{'CI_EVENT_SHA':'b'*40}):
                        with self.assertRaisesRegex(ValueError,'checkout'):
                            ci_run.inputs()
                    with patch.dict(os.environ,{'CI_MAKE_LATEST':'true'}):
                        with self.assertRaisesRegex(ValueError,'explicit manual'):
                            ci_run.inputs()
                    with patch.dict(os.environ,{'CI_TESTING_VERSION':'0.1.0-testing.1'}):
                        with self.assertRaises(ValueError):
                            ci_run.inputs()

    def test_first_stable_control_release_is_guarded_before_build(self):
        env = dict(CI_PROFILE='consumer', CI_STREAM='release', GITHUB_RUN_ID='123',
                   GITHUB_RUN_ATTEMPT='1', GITHUB_EVENT_NAME='push',
                   GITHUB_REF='refs/tags/v1.0.0', GITHUB_REPOSITORY='WsprryPi/WsprryPico')
        from check_control_policy import check_files, validate
        policy, schema = check_files()
        policy.update(phase='prerelease', first_release=None, schema_sha256=None)
        def guard(stable_release):
            validate(policy, schema, stable_release)
        with patch.dict(os.environ, env, clear=True), patch.object(ci_run, 'check_control_policy', side_effect=guard):
            with self.assertRaisesRegex(ValueError, 'First stable release requires'):
                ci_run.inputs()

    def test_stable_publication_refuses_prerelease_control_before_download(self):
        from check_control_policy import check_files, validate
        policy, schema = check_files()
        policy.update(phase='prerelease', first_release=None, schema_sha256=None)
        env = dict(GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REF='refs/tags/v1.0.0',
                   GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='1', GITHUB_SHA='a'*40)
        def guard(stable_release):
            validate(policy, schema, stable_release)
        with patch.dict(os.environ, env, clear=True), patch.object(sys, 'argv', ['publish.py', '--destination', '/unused']), \
             patch.object(publish, 'require_authorization'), patch.object(publish, 'check_control_policy', side_effect=guard), \
             patch.object(publish.download, 'retrieve') as retrieve:
            with self.assertRaisesRegex(ValueError, 'First stable release requires'):
                publish.main()
            retrieve.assert_not_called()

    def test_obsolete_testing_producer_refuses_before_build(self):
        env = dict(CI_PROFILE='consumer', CI_STREAM='devel', GITHUB_RUN_ID='123',
                   GITHUB_RUN_ATTEMPT='1', GITHUB_EVENT_NAME='workflow_dispatch',
                   GITHUB_REF='refs/heads/devel', CI_EVENT_SHA='a'*40,
                   GITHUB_REPOSITORY='WsprryPi/WsprryPico', CI_TESTING_VERSION='0.1.0-testing.1')
        def capture(*args):
            return 'a'*40 if args[:2] == ('git', 'rev-parse') else ''
        with patch.dict(os.environ, env, clear=True), patch.object(ci_run, 'capture', side_effect=capture), \
             patch.object(ci_run.Path, 'exists', return_value=False):
            with self.assertRaisesRegex(ValueError, 'unsupported for Control/1'):
                ci_run.inputs()
            for field, value in [('GITHUB_EVENT_NAME','push'), ('GITHUB_REF','refs/heads/main'),
                                 ('CI_TESTING_VERSION','0.1.0-testing.0'),
                                 ('CI_TESTING_VERSION','0.1.0-testing.1;bad'),
                                 ('CI_TESTING_VERSION','0.1.0-ci.123.1')]:
                with self.subTest(field=field,value=value), patch.dict(os.environ,{field:value}):
                    with self.assertRaises(ValueError):
                        ci_run.inputs()
            with patch.dict(os.environ, {'CI_TESTING_VERSION':''}):
                self.assertEqual(ci_run.inputs()[1], '0.1.0-ci.123.1')
            with patch.dict(os.environ, {'CI_VERSION':'0.1.0-testing.2'}):
                with self.assertRaises(ValueError):
                    ci_run.inputs()


class TagPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tag = 'v0.1.0-ci.1.1'
        self.source = 'a'*40
        self.ref = {'object': {'type': 'commit', 'sha': self.source}}

    def test_existing_correct_tag_needs_no_mutation_or_delay(self):
        with patch.object(publish, 'api', return_value=self.ref) as api, patch('time.sleep') as sleep:
            publish.ensure_tag(self.tag, self.source)
        api.assert_called_once_with('git/ref/tags/' + self.tag, missing=True)
        sleep.assert_not_called()

    def test_new_tag_can_become_visible_on_last_retry(self):
        responses = [None, {}, None, None, None, None, None, self.ref]
        with patch.object(publish, 'api', side_effect=responses) as api, patch('time.sleep') as sleep:
            publish.ensure_tag(self.tag, self.source)
        self.assertEqual(sleep.call_args_list, [call(1), call(2), call(4), call(8), call(16)])
        self.assertEqual([c for c in api.call_args_list if c.args[0] == 'git/refs'],
                         [call('git/refs', 'POST', {'ref': 'refs/tags/' + self.tag, 'sha': self.source})])

    def test_missing_new_tag_exhausts_retries_without_recreating_it(self):
        with patch.object(publish, 'api', side_effect=[None, {}, *([None]*6)]) as api, \
             patch('time.sleep') as sleep:
            with self.assertRaisesRegex(ValueError, 'still not visible.*' + self.tag):
                publish.ensure_tag(self.tag, self.source)
        self.assertEqual(sleep.call_args_list, [call(1), call(2), call(4), call(8), call(16)])
        self.assertEqual(api.call_count, 8)
        self.assertEqual([c for c in api.call_args_list if c.args[0] == 'git/refs'],
                         [call('git/refs', 'POST', {'ref': 'refs/tags/' + self.tag, 'sha': self.source})])

    def test_visible_wrong_source_fails_without_further_retries(self):
        wrong = {'object': {'type': 'commit', 'sha': 'b'*40}}
        for responses, delays in [([wrong], []), ([None, {}, None, wrong], [call(1)])]:
            with self.subTest(responses=responses), \
                 patch.object(publish, 'api', side_effect=responses) as api, patch('time.sleep') as sleep:
                with self.assertRaisesRegex(ValueError, 'different source') as error:
                    publish.ensure_tag(self.tag, self.source)
                self.assertIn(self.tag, str(error.exception))
                self.assertIn(self.source, str(error.exception))
                self.assertIn('b'*40, str(error.exception))
                self.assertEqual(api.call_count, len(responses))
                self.assertEqual(sleep.call_args_list, delays)

    def test_api_errors_are_not_retried(self):
        for responses in ([None, RuntimeError('HTTP 403')], [None, {}, RuntimeError('HTTP 403')]):
            with self.subTest(responses=responses), \
                 patch.object(publish, 'api', side_effect=responses) as api, patch('time.sleep') as sleep:
                with self.assertRaisesRegex(RuntimeError, 'HTTP 403'):
                    publish.ensure_tag(self.tag, self.source)
                self.assertEqual(api.call_count, len(responses))
                sleep.assert_not_called()


class BundleTests(unittest.TestCase):
    def test_workflow_commands_parse_as_strings(self):
        import yaml
        workflow = yaml.load((ROOT / '.github/workflows/software-build.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(set(workflow['on']['push']['branches']), {'devel', 'main'})
        self.assertEqual(set(workflow['on']['pull_request']['branches']), {'devel', 'main'})
        self.assertNotIn('paths-ignore', workflow['on']['push'])
        self.assertNotIn('paths', workflow['on']['push'])
        self.assertNotIn('concurrency', workflow)  # Every push must start its build.
        self.assertEqual(workflow['permissions'], {'contents':'read'})
        publisher = workflow['jobs']['publish']
        self.assertEqual(publisher['needs'], 'verify')
        self.assertEqual(workflow['on']['push']['tags'], ['v*'])
        self.assertIn("github.event_name == 'workflow_dispatch'", publisher['if'])
        self.assertIn('inputs.publish', publisher['if'])
        self.assertEqual(workflow['on']['workflow_dispatch']['inputs']['publish']['default'], 'false')
        self.assertEqual(workflow['on']['workflow_dispatch']['inputs']['make_latest']['default'], 'false')
        self.assertIn("github.repository == 'WsprryPi/WsprryPico'", publisher['if'])
        self.assertNotIn('testing_version', workflow['on']['workflow_dispatch']['inputs'])
        self.assertNotIn('CI_TESTING_VERSION', workflow['jobs']['verify']['env'])
        self.assertEqual(publisher['permissions'], {'contents':'write','actions':'read'})
        self.assertEqual(publisher['concurrency']['group'], 'firmware-publication-${{ github.ref }}')
        self.assertEqual(publisher['concurrency']['queue'], 'max')
        for job in workflow['jobs'].values():
            for step in job['steps']:
                if 'run' in step:
                    self.assertIsInstance(step['run'], str)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.deploy, self.audit = self.base / 'deployment', self.base / 'audit'
        self.deploy.mkdir()
        (self.audit / 'consumer').mkdir(parents=True)
        (self.audit / 'consumer/WsprryPico.uf2').write_bytes(b'fixture image; not target evidence')
        for name in ('LICENSE.md', 'THIRD_PARTY_NOTICES.md', 'DEPENDENCY-LICENSES.txt'):
            (self.deploy / name).write_text('fixture license\n')
        self.source = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
        self.version = '0.1.0-ci.1.1'
        self.checks = dict(registered=1, passed=1, failed=0, skipped=0, test_names=['fixture'],
                           wtp_contract='passed', browser_npm='passed', packaging_failure_tests='passed',
                           consumer_ui='passed', compatibility_rf='passed', inhibited_regression='passed',
                           reproducibility='identical', historical_evidence_skips=[])
        pins = bundle.read_json(ROOT / 'scripts/ci/inputs.json')
        overlays = {}
        for name in bundle.CONSUMER_OVERLAYS:
            path = self.audit / 'consumer/overlays' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('synthetic overlay; not linked-image evidence\n')
            overlays[name] = bundle.sha(path)
        def dependency(name, repository):
            return {'repository': repository, 'revision': pins[name], 'submodules': [f' {v} {k}' for k,v in pins['sdk_submodules'].items()] if name == 'sdk' else []}
        self.inputs = dict(pins=pins, toolchain_archive_sha256=pins['toolchain_sha256'],
                           sdk=dependency('sdk', 'https://github.com/raspberrypi/pico-sdk.git'),
                           picotool=dependency('picotool', 'https://github.com/raspberrypi/picotool.git'),
                           companion=dependency('companion', 'https://github.com/WsprryPi/WsprryPi.git'),
                           harness=dependency('harness', 'https://github.com/WsprryPi/WsprryPi-Qualification-Harness.git'),
                           environment={}, overlays={'consumer': overlays}, linked_resources=pins['linked_resource_sha256'], python_lock_sha256='a' * 64, npm_lock_sha256='b' * 64)
        (self.audit / 'registered-tests.json').write_text(json.dumps({'tests':[{'name':'fixture'}]}))
        (self.audit / 'host-tests.xml').write_text('<testsuite><testcase name="fixture"/></testsuite>')
        (self.audit / 'evidence-skips.json').write_text('[]\n')
        env = dict(GITHUB_EVENT_NAME='push', GITHUB_REF='refs/heads/devel', CI_WORKFLOW_SHA=self.source,
                    GITHUB_RUN_ID='1', GITHUB_RUN_ATTEMPT='1')
        with patch.dict(os.environ, env):
            bundle.create(self.deploy, self.audit, self.source, self.version, ['consumer'], self.checks, self.inputs)
        # Synthetic payload represents the frozen source, including during an
        # uncommitted layout migration. The creator still emits the current boundary.
        self.created_boundary = bundle.read_json(self.deploy / 'release-manifest.json')['update']['application_end']
        self.mutate_manifest(lambda v: v['update'].update(application_end=f'{bundle.source_application_end(self.source):x}'))
        self.reseal()

    def verify(self, **kwargs):
        # Synthetic fixture has no ELF. Actual image inspection is mandatory in
        # the CLI; these tests isolate untrusted manifests and artifact inventories.
        with patch.object(bundle, 'required_tests', return_value={'fixture'}):
            return bundle.verify(self.deploy, self.audit, kwargs.get('source', self.source),
                                  kwargs.get('version', self.version), inspect=False)

    def mutate_manifest(self, change):
        path = self.deploy / 'release-manifest.json'
        value = bundle.read_json(path)
        change(value)
        path.write_text(json.dumps(value) + '\n')

    def reseal(self):
        # Model a modified sidecar whose attacker recomputes its integrity hashes.
        path = self.deploy / 'release-manifest.json'
        value = json.loads(path.read_text())
        value['audit_assets'] = [bundle.descriptor(p, self.audit)
                                 for p in sorted(self.audit.rglob('*')) if p.is_file()]
        path.write_text(json.dumps(value) + '\n')
        (self.deploy / 'SHA256SUMS').write_text(''.join(
            hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n'
            for p in sorted(self.deploy.iterdir()) if p.name != 'SHA256SUMS'))

    def test_layout_is_bound_to_frozen_source(self):
        self.assertEqual(self.created_boundary, '103ec000')
        manifest = bundle.read_json(self.deploy / 'release-manifest.json')
        self.assertEqual(manifest['schema_version'], 2)
        self.assertEqual(manifest['update']['storage_contract'], 2)
        self.verify()
        # A schema-valid contract-2 manifest must still match its frozen source.
        with patch.object(bundle, 'source_application_end', return_value=0x103ee000):
            with self.assertRaisesRegex(ValueError, 'Flash reservation differs'):
                self.verify()
        # Contract 2 cannot borrow either historical contract-1 reservation.
        from jsonschema import ValidationError
        for wrong in (0x103ee000, 0x103f0000):
            self.mutate_manifest(lambda v: v['update'].update(application_end=f'{wrong:x}'))
            self.reseal()
            with self.assertRaises(ValidationError):
                self.verify()

    def test_valid_inventory_and_distinct_archive_identity(self):
        result = self.verify()
        self.assertEqual(result['firmware']['frequency_selected_by_image'], None)
        self.assertNotIn('archive_digest', result)

    def test_ordinary_bundle_keeps_installer_schema_interpreter_compatibility(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        import usb_installer
        usb_installer.schema_check(bundle.read_json(self.deploy / 'release-manifest.json'),
                                   bundle.read_json(bundle.SCHEMA))

    def test_tampered_payload_and_checksum_file_fail(self):
        uf2 = next(self.deploy.glob('*.uf2'))
        uf2.write_bytes(b'altered' + uf2.read_bytes()[7:])
        with self.assertRaises(ValueError):
            self.verify()

    def test_wrong_source_and_version_fail(self):
        for kwargs in ({'source': 'c' * 40}, {'version': '0.1.0-ci.2.1'}):
            with self.assertRaises(ValueError):
                self.verify(**kwargs)

    def test_inhibited_metadata_and_incomplete_checks_fail(self):
        from jsonschema import ValidationError
        for change in (lambda v: v['firmware'].update(role='inhibited'),
                       lambda v: v['checks'].update(failed=1)):
            original = (self.deploy / 'release-manifest.json').read_bytes()
            self.mutate_manifest(change)
            with self.assertRaises((ValueError, ValidationError)):
                self.verify()
            (self.deploy / 'release-manifest.json').write_bytes(original)

    def test_extra_missing_duplicate_and_symlink_assets_fail(self):
        extra = self.deploy / 'extra.uf2'
        extra.write_bytes(b'unexpected diagnostic')
        with self.assertRaises(ValueError):
            self.verify()
        extra.unlink()
        victim = self.deploy / 'LICENSE.md'
        contents = victim.read_bytes()
        victim.unlink()
        with self.assertRaises(ValueError):
            self.verify()
        outside = self.base / 'outside'
        outside.write_bytes(contents)
        victim.symlink_to(outside)
        with self.assertRaises(ValueError):
            self.verify()
        victim.unlink()
        victim.write_bytes(contents)
        self.mutate_manifest(lambda v: v['assets'].__setitem__(0, copy.deepcopy(v['assets'][1])))
        with self.assertRaises(ValueError):
            self.verify()

    def test_traversal_and_duplicate_json_are_rejected(self):
        self.mutate_manifest(lambda v: v['assets'][0].update(path='../outside'))
        with self.assertRaises(ValueError):
            self.verify()
        path = self.base / 'duplicate.json'
        path.write_text('{"version":1,"version":2}')
        with self.assertRaises(ValueError):
            bundle.read_json(path)

    def test_forged_source_tree_and_dependency_provenance_fail(self):
        self.mutate_manifest(lambda v: v['source'].update(tree='0' * 40))
        self.reseal()
        with self.assertRaisesRegex(ValueError, 'Source tree'):
            self.verify()
        self.mutate_manifest(lambda v: v['source'].update(
            tree=subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', self.source + '^{tree}'], text=True).strip()))
        self.mutate_manifest(lambda v: v['build_inputs']['sdk'].update(revision='c' * 40))
        data = json.loads((self.deploy / 'release-manifest.json').read_text())
        (self.audit / 'build-inputs.json').write_text(json.dumps(data['build_inputs']))
        self.reseal()
        with self.assertRaisesRegex(ValueError, 'Wrong dependency source'):
            self.verify()

    def test_forged_check_inventory_and_failed_audit_report_fail(self):
        self.mutate_manifest(lambda v: v['checks'].update(test_names=['invented']))
        self.reseal()
        with self.assertRaisesRegex(ValueError, 'Test reports'):
            self.verify()
        self.mutate_manifest(lambda v: v['checks'].update(test_names=['fixture']))
        (self.audit / 'host-tests.xml').write_text('<testsuite><testcase name="fixture"><failure/></testcase></testsuite>')
        self.reseal()
        with self.assertRaisesRegex(ValueError, 'failed or skipped'):
            self.verify()

    def test_missing_overlay_inventory_fails_even_when_resealed(self):
        self.mutate_manifest(lambda v: v['build_inputs'].update(overlays={}))
        data = json.loads((self.deploy / 'release-manifest.json').read_text())
        (self.audit / 'build-inputs.json').write_text(json.dumps(data['build_inputs']))
        self.reseal()
        with self.assertRaisesRegex(ValueError, 'overlay inventory'):
            self.verify()

    def test_frozen_source_inventory_does_not_read_working_tree(self):
        self.assertIn('standalone_tests', bundle.required_tests(self.source))
        with self.assertRaises(ValueError):
            bundle.required_tests('HEAD')

    def test_explicit_inventory_without_a_legacy_registration_loop(self):
        snapshot = {
            'CMakeLists.txt': 'add_test(NAME retained_behavior_tests COMMAND driver)\n',
            'cmake/network_host_tests.cmake': 'add_test(NAME network_regression_tests COMMAND driver)\n',
            'cmake/host_client_interop.cmake': '',
            'cmake/network_client_interop.cmake': '',
        }

        def frozen_capture(*args):
            if 'ls-tree' in args:
                return 'cmake/network_host_tests.cmake'
            revision, path = args[-1].split(':', 1)
            self.assertEqual(revision, self.source)
            return snapshot[path]

        with patch.object(bundle, 'capture', side_effect=frozen_capture):
            self.assertEqual(bundle.required_tests(self.source),
                             {'retained_behavior_tests', 'network_regression_tests'})

    def test_renamed_compatibility_program_is_rejected_before_payload_acceptance(self):
        directory = self.audit / 'consumer'
        (directory / 'WsprryPico.elf').write_bytes(b'synthetic ELF fixture')
        report = ('File renamed.elf:\nProgram Information\n'
                  '    name: WsprryPico-StandaloneRF\n'
                  f'    version: {self.version}\n'
                  f'    description: Standalone PIO/DMA RF {self.source[:12]}\n'
                  '    target chip: RP2350\n    image type: ARM Secure\n'
                  'Build Information\n    sdk version: 2.3.1\n'
                  '    pico_board: pico2_w\n    build attributes: Release\n')
        (directory / 'picotool-info.txt').write_text(report)
        with patch.object(bundle, 'capture', side_effect=lambda *args:
                          'picotool v2.3.0 (fixture)' if args[-1] == 'version' else report):
            with self.assertRaisesRegex(ValueError, 'program identity mismatch'):
                bundle.inspect_profile(directory, 'consumer', self.version, self.source)

    def download_fixture(self, branch, legacy=False, event=None):
        event = event or ('pull_request' if branch == 'pull-request' else 'push')
        ref = ('refs/tags/v' + self.version if branch == 'release' else
               'refs/pull/23/merge' if event == 'pull_request' else 'refs/heads/' + branch)
        self.mutate_manifest(lambda v: v.update(
            workflow=dict(v['workflow'], event=event, ref=ref),
            deployment_candidate=branch != 'pull-request' and not bundle.is_testing_version(self.version)))
        self.reseal()
        archives, records = {}, []
        for identifier, (kind, folder) in enumerate((('firmware', self.deploy), ('audit', self.audit)), 1):
            archive = self.base / f'{branch}-{kind}.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                for path in sorted(folder.rglob('*')):
                    if path.is_file():
                        output.write(path, path.relative_to(folder).as_posix())
            archives[identifier] = archive
            records.append(dict(id=identifier,
                name=f'WsprryPico-{kind}-1-1-consumer' if legacy else bundle.artifact_name(kind, branch, 1, 1),
                digest='sha256:' + bundle.sha(archive), expired=False, expires_at='2030-01-01T00:00:00Z'))
        run = dict(status='completed', conclusion='success', run_attempt=1,
                   head_sha=self.source, head_branch='v'+self.version if branch == 'release' else branch, event=event,
                   path='.github/workflows/software-build.yml', workflow_id=7,
                   head_repository={'full_name':download.REPOSITORY}, html_url='https://github.com/'+download.REPOSITORY+'/actions/runs/1')
        responses = {'actions/runs/1/attempts/1':run,
                     'actions/workflows/software-build.yml':{'id':7,'path':run['path']},
                     'actions/runs/1/attempts/1/jobs':{'total_count':len(download.required_jobs(self.source)),
                         'jobs':[{'id':9,'name':name,'status':'completed','conclusion':'success'}
                                 for name in download.required_jobs(self.source)]},
                     'actions/runs/1/artifacts?per_page=100':{'total_count':2,'artifacts':records}}
        args = SimpleNamespace(branch=branch, run=1, attempt=1, source=self.source,
                               version=self.version, destination=self.base / (branch + '-download'))
        return args, responses, archives

    def retrieve_fixture(self, args, responses, archives, publication=False):
        verifier = bundle.verify
        actual_capture = bundle.capture
        tool = self.base / 'trusted-fixture-picotool'
        tool.write_text('synthetic inspection-tool identity')
        with patch.object(download, 'api', side_effect=responses.__getitem__), \
             patch.object(download, 'fetch_archive', side_effect=lambda a,p: p.write_bytes(archives[a['id']].read_bytes())), \
             patch.object(bundle, 'required_tests', return_value={'fixture'}), \
             patch.object(bundle, 'verify', side_effect=lambda d,a,s,v,**kw:verifier(d,a,s,v,inspect=False)), \
             patch.object(bundle, 'inspect_payload'), \
             patch.object(bundle, 'capture', side_effect=lambda *a:
                          'picotool v2.3.0 (fixture)' if a == ('picotool','version') else actual_capture(*a)), \
             patch.object(download.shutil, 'which', return_value=str(tool)):
            return download.retrieve(args, for_publication=publication)

    def test_both_branch_downloads_remain_distinct(self):
        for branch in ('devel', 'main'):
            with self.subTest(branch=branch):
                args, responses, archives = self.download_fixture(branch)
                receipt = self.retrieve_fixture(args, responses, archives)
                self.assertEqual(receipt['branch'], branch)
                self.assertTrue(receipt['verified'])
                self.assertTrue(all('-' + branch + '-' in a['name'] for a in receipt['artifacts']))
        self.assertTrue((self.base / 'devel-download/verified-download.json').is_file())
        self.assertTrue((self.base / 'main-download/verified-download.json').is_file())

    def test_original_devel_artifacts_remain_downloadable(self):
        args, responses, archives = self.download_fixture('devel', legacy=True)
        self.assertTrue(self.retrieve_fixture(args, responses, archives)['verified'])

    def testing_fixture(self):
        self.version = '0.1.0-testing.1'
        manifest_path = self.deploy / 'release-manifest.json'
        manifest = json.loads(manifest_path.read_text())
        payload = next(a for a in manifest['assets'] if a['path'].endswith('.uf2'))
        target = self.deploy / f'WsprryPico-{self.version}-pico2_w.uf2'
        (self.deploy / payload['path']).rename(target)
        payload.update(bundle.descriptor(target, self.deploy))
        manifest.update(firmware_version=self.version, intended_tag='v'+self.version,
                        deployment_candidate=False, testing_release=bundle.testing_metadata(self.source))
        manifest['workflow'].update(event='workflow_dispatch',ref='refs/heads/devel')
        manifest_path.write_text(json.dumps(manifest))
        self.reseal()

    def test_testing_metadata_uses_current_control_and_bound_companion(self):
        from jsonschema import Draft202012Validator
        metadata = bundle.testing_metadata(self.source)
        self.assertEqual(metadata['api'], ['Wsprry-Control/1'])
        schema = json.loads(bundle.SCHEMA.read_text())['properties']['testing_release']
        Draft202012Validator(schema).validate(metadata)
        # The schema checks a closed SHA-shaped record; source-aware verification
        # binds that revision to the exact pinned companion rather than a stale
        # schema literal. A well-shaped foreign revision must still fail.
        self.testing_fixture()
        self.mutate_manifest(lambda m: m['testing_release']['companion'].update(
            software_tested_revision='f' * 40))
        with self.assertRaisesRegex(ValueError, 'Testing release metadata mismatch'):
            self.verify()

    def test_testing_manifest_requires_exact_metadata_and_manual_devel(self):
        from jsonschema import ValidationError
        self.testing_fixture()
        self.verify()
        baseline = (self.deploy / 'release-manifest.json').read_text()
        for mutation in (
                lambda m: m.pop('testing_release'),
                lambda m: m['testing_release']['gpio_drive_ma'].update(default=12),
                lambda m: m['testing_release']['references'].__setitem__(0, 'https://example.org/stale'),
                lambda m: m['workflow'].update(event='push'),
                lambda m: m['workflow'].update(ref='refs/heads/main'),
                lambda m: m.update(deployment_candidate=True)):
            (self.deploy / 'release-manifest.json').write_text(baseline)
            self.mutate_manifest(mutation)
            self.reseal()
            with self.assertRaises((ValueError, ValidationError)):
                self.verify()

    def test_creator_emits_testing_metadata_and_refuses_automatic_release(self):
        created = self.base / 'testing-created'
        created.mkdir()
        for name in ('LICENSE.md', 'THIRD_PARTY_NOTICES.md', 'DEPENDENCY-LICENSES.txt'):
            (created / name).write_bytes((self.deploy / name).read_bytes())
        env = dict(GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REF='refs/heads/devel',
                   CI_WORKFLOW_SHA=self.source, GITHUB_RUN_ID='1', GITHUB_RUN_ATTEMPT='1')
        version = '0.1.0-testing.1'
        with patch.dict(os.environ, env):
            bundle.create(created, self.audit, self.source, version, ['consumer'], self.checks, self.inputs)
        with patch.object(bundle, 'required_tests', return_value={'fixture'}):
            result = bundle.verify(created, self.audit, self.source, version, inspect=False)
        self.assertFalse(result['deployment_candidate'])
        self.assertEqual(result['testing_release'], bundle.testing_metadata(self.source))
        for event,ref in [('push','refs/heads/devel'), ('workflow_dispatch','refs/heads/main')]:
            rejected = self.base / ('rejected-'+event)
            rejected.mkdir()
            with patch.dict(os.environ, dict(env,GITHUB_EVENT_NAME=event,GITHUB_REF=ref)):
                with self.assertRaisesRegex(ValueError, 'manual devel dispatch'):
                    bundle.create(rejected, self.audit, self.source, version, ['consumer'], self.checks, self.inputs)

    def test_testing_download_requires_successful_dispatch_and_skipped_publisher(self):
        self.testing_fixture()
        args, responses, archives = self.download_fixture('devel', event='workflow_dispatch')
        jobs = responses['actions/runs/1/attempts/1/jobs']['jobs']
        next(j for j in jobs if j['name']=='publish')['conclusion']='skipped'
        self.assertTrue(self.retrieve_fixture(args,responses,archives)['verified'])
        args.destination = self.base / 'rejected-testing'
        with self.assertRaises(ValueError):
            self.retrieve_fixture(args,responses,archives,publication=True)
        for event in ('push','pull_request'):
            responses['actions/runs/1/attempts/1']['event']=event
            with self.assertRaises(ValueError):
                self.retrieve_fixture(args,responses,archives)
        responses['actions/runs/1/attempts/1']['event']='workflow_dispatch'
        for name in ('verify','publish'):
            job=next(j for j in jobs if j['name']==name)
            original=job['conclusion']
            job['conclusion']='failure'
            with self.assertRaises(ValueError):
                self.retrieve_fixture(args,responses,archives)
            job['conclusion']=original
        args.version='0.1.0-ci.1.1'
        with self.assertRaises(ValueError):
            self.retrieve_fixture(args,responses,archives)

    def test_wrong_branch_preview_and_partial_run_are_rejected(self):
        for change in ('wrong-branch', 'preview', 'failed', 'incomplete'):
            with self.subTest(change=change):
                args, responses, archives = self.download_fixture('main')
                run = responses['actions/runs/1/attempts/1']
                if change == 'wrong-branch': run['head_branch'] = 'devel'
                if change == 'preview': run['event'] = 'pull_request'
                if change == 'failed': run['conclusion'] = 'failure'
                if change == 'incomplete': run['status'] = 'in_progress'
                with self.assertRaisesRegex(ValueError, 'canonical main build'):
                    self.retrieve_fixture(args, responses, archives)
                self.assertFalse(args.destination.exists())

    def test_main_manifest_cannot_be_relabelled_as_devel(self):
        args, responses, archives = self.download_fixture('main')
        args.branch = 'devel'
        responses['actions/runs/1/attempts/1']['head_branch'] = 'devel'
        for kind, record in zip(('firmware','audit'), responses['actions/runs/1/artifacts?per_page=100']['artifacts']):
            record['name'] = bundle.artifact_name(kind, 'devel', 1, 1)
        with self.assertRaisesRegex(ValueError, 'different CI run/attempt'):
            self.retrieve_fixture(args, responses, archives)

    def test_main_never_falls_back_to_devel_or_legacy_artifacts(self):
        for name in ('WsprryPico-firmware-devel-1-1-consumer','WsprryPico-firmware-1-1-consumer'):
            with self.assertRaisesRegex(ValueError, 'immutable artifact for main'):
                download.select_artifact({'artifacts':[{'name':name,'expired':False}]}, 'firmware','main',1,1)

    def test_downloaded_archive_digest_is_enforced(self):
        args, responses, archives = self.download_fixture('devel')
        responses['actions/runs/1/artifacts?per_page=100']['artifacts'][0]['digest'] = 'sha256:' + '0'*64
        with self.assertRaisesRegex(ValueError, 'archive SHA-256 mismatch'):
            self.retrieve_fixture(args, responses, archives)

    def test_pull_request_bundle_is_preview_only(self):
        self.download_fixture('pull-request')
        self.assertFalse(self.verify()['deployment_candidate'])

    def test_untrusted_event_or_ref_cannot_select_a_branch_stream(self):
        for event, ref in [('push','refs/heads/feature'), ('push','refs/tags/v1'),
                           ('pull_request','refs/heads/main'), ('pull_request_target','refs/heads/main')]:
            with self.assertRaises(ValueError):
                bundle.build_stream(event, ref)

    def publication_fixture(self, branch='devel'):
        args, responses, archives = self.download_fixture(branch)
        receipt = self.retrieve_fixture(args, responses, archives)
        receipt['verification'] = 'accepted-verify-job-and-payload'
        return args, receipt

    def release_fixture(self, version):
        manifest = bundle.read_json(self.deploy / 'release-manifest.json')
        payload = next(a for a in manifest['assets'] if a['path'].endswith('.uf2'))
        self.version = version
        path = self.deploy / f'WsprryPico-{version}-pico2_w.uf2'
        (self.deploy / payload['path']).rename(path)
        payload.update(bundle.descriptor(path, self.deploy))
        manifest.update(firmware_version=version, intended_tag='v'+version,
                        channel=bundle.version_kind(version), deployment_candidate=True)
        manifest['workflow'].update(ref='refs/tags/v'+version)
        (self.deploy / 'release-manifest.json').write_text(json.dumps(manifest))
        self.reseal()

    def test_tag_manifest_creation_download_publication_and_expired_archive_roundtrip(self):
        for version in ('1.0.0-beta.1', '1.0.0', '1.0.0-rc.2+build.001'):
            with self.subTest(version=version):
                self.release_fixture(version)
                self.verify()
                if '+' in version:
                    self.assertIn('%2B',publish.asset_url('v'+version,f'WsprryPico-{version}-pico2_w.uf2'))
                args, responses, archives = self.download_fixture('release', event='workflow_dispatch')
                args.destination = self.base / version
                with patch.object(publish,'tag_commit',return_value=self.source):
                    receipt = self.retrieve_fixture(args,responses,archives)
                receipt['verification'] = 'accepted-verify-job-and-payload'
                releases,tags,mutations,api,upload = self.publication_service()
                tags['v'+version] = self.source
                with patch.object(publish,'api',side_effect=api), patch.object(publish.subprocess,'run',side_effect=upload):
                    tag = publish.preserve(receipt,args.destination)
                    self.assertEqual(releases[tag]['prerelease'], bundle.version_kind(version) != 'stable')
                    self.assertEqual(releases[tag]['make_latest'],'false')
                    self.assertEqual(len(releases[tag]['assets']),9)
                    before = copy.deepcopy(mutations)
                    publish.preserve(receipt,args.destination)
                    self.assertEqual(mutations,before)
                original = args.destination
                args.destination = self.base / (version+'-expired')
                actual_run = subprocess.run
                def fetch(command,stdout,**kwargs):
                    if command[0] != 'gh':
                        return actual_run(command,stdout=stdout,**kwargs)
                    identifier = int(command[-1].split('/')[-1])
                    filename = next(a['name'] for a in releases[tag]['assets'] if a['id']==identifier)
                    stdout.write((original/filename).read_bytes())
                verifier = bundle.verify
                with patch.object(publish,'api',side_effect=api), \
                     patch.object(download.subprocess,'run',side_effect=fetch), \
                     patch.object(download,'inspection_tool',return_value={'path':'fixture'}), \
                     patch.object(bundle,'required_tests',return_value={'fixture'}), \
                     patch.object(bundle,'verify',side_effect=lambda d,a,s,v:verifier(d,a,s,v,inspect=False)):
                    self.assertEqual(download.retrieve_published(args)['version'],version)

    def test_readonly_tag_download_allows_skipped_publish_but_rejects_failure_and_source_swap(self):
        self.release_fixture('1.0.0-beta.1')
        args,responses,archives = self.download_fixture('release')
        publisher = next(j for j in responses['actions/runs/1/attempts/1/jobs']['jobs'] if j['name']=='publish')
        publisher['conclusion'] = 'skipped'
        with patch.object(publish,'tag_commit',return_value=self.source), patch.object(download,'optional_publication',return_value=True):
            self.assertTrue(self.retrieve_fixture(args,responses,archives)['verified'])
            publisher['conclusion'] = 'failure'
            with self.assertRaisesRegex(ValueError,'publication job'):
                self.retrieve_fixture(args,responses,archives)

    def test_release_creator_and_manifest_reject_channel_ref_and_run_swaps(self):
        import usb_installer
        from jsonschema import ValidationError
        for version in ('1.0.0-beta.1','1.0.0','1.0.0-foo-testing.1+build.0'):
            created = self.base / ('create-'+version)
            created.mkdir()
            for name in ('LICENSE.md','THIRD_PARTY_NOTICES.md','DEPENDENCY-LICENSES.txt'):
                (created/name).write_bytes((self.deploy/name).read_bytes())
            env = dict(GITHUB_EVENT_NAME='push',GITHUB_REF='refs/tags/v'+version,
                       CI_WORKFLOW_SHA=self.source,GITHUB_RUN_ID='1',GITHUB_RUN_ATTEMPT='1')
            with patch.dict(os.environ,env):
                bundle.create(created,self.audit,self.source,version,['consumer'],self.checks,self.inputs)
            with patch.object(bundle,'required_tests',return_value={'fixture'}):
                manifest=bundle.verify(created,self.audit,self.source,version,inspect=False)
            usb_installer.schema_check(manifest,bundle.read_json(bundle.SCHEMA))
        self.release_fixture('1.0.0-beta.1')
        baseline=(self.deploy/'release-manifest.json').read_text()
        for mutate in (lambda m:m.update(channel='stable'),
                       lambda m:m.update(deployment_candidate=False),
                       lambda m:m['workflow'].update(ref='refs/tags/v1.0.0-beta.2'),
                       lambda m:m['workflow'].update(ref='refs/heads/devel'),
                       lambda m:m['workflow'].update(event='pull_request'),
                       lambda m:m.update(intended_tag='v1.0.0')):
            (self.deploy/'release-manifest.json').write_text(baseline)
            self.mutate_manifest(mutate)
            self.reseal()
            with self.assertRaises((ValueError,ValidationError)):self.verify()

    def test_beta_cannot_be_latest_and_tag_movement_cannot_publish_a_draft(self):
        self.release_fixture('1.0.0-beta.1')
        args,responses,archives=self.download_fixture('release')
        with patch.object(publish,'tag_commit',return_value=self.source):
            receipt=self.retrieve_fixture(args,responses,archives)
        receipt['verification']='accepted-verify-job-and-payload'
        with patch.object(publish,'api',side_effect=AssertionError('mutation')):
            with self.assertRaisesRegex(ValueError,'latest stable'):
                publish.preserve(dict(receipt,make_latest=True),args.destination)
        releases,tags,mutations,api,upload=self.publication_service()
        tag='v'+self.version
        tags[tag]=self.source
        def moved(command,**kwargs):
            upload(command,**kwargs)
            tags[tag]='b'*40
        with patch.object(publish,'api',side_effect=api),patch.object(publish.subprocess,'run',side_effect=moved):
            with self.assertRaisesRegex(ValueError,'changed before publication'):
                publish.preserve(receipt,args.destination)
        self.assertTrue(releases[tag]['draft'])
        self.assertFalse(any(method=='PATCH' for _,method,_ in mutations))
        with patch.object(publish,'tag_commit',return_value='b'*40):
            with self.assertRaisesRegex(ValueError,'tag/source'):
                self.retrieve_fixture(args,responses,archives)

    def test_final_latest_selection_is_explicit_and_does_not_advance_ci_bookmarks(self):
        self.release_fixture('1.0.0')
        args,responses,archives=self.download_fixture('release',event='workflow_dispatch')
        with patch.object(publish,'tag_commit',return_value=self.source):
            receipt=self.retrieve_fixture(args,responses,archives)
        receipt.update(verification='accepted-verify-job-and-payload',make_latest=True)
        releases,tags,mutations,api,upload=self.publication_service()
        tags['v1.0.0']=self.source
        with patch.object(publish,'api',side_effect=api),patch.object(publish.subprocess,'run',side_effect=upload):
            publish.preserve(receipt,args.destination)
        self.assertEqual(set(releases),{'v1.0.0'})
        self.assertIs(releases['v1.0.0']['prerelease'],False)
        self.assertEqual(releases['v1.0.0']['make_latest'],'true')

    def test_tag_publication_collector_binds_current_job_to_exact_tag_run(self):
        self.release_fixture('1.0.0-beta.1')
        args,responses,archives=self.download_fixture('release',event='workflow_dispatch')
        responses['actions/runs/1/attempts/1'].update(status='in_progress',conclusion=None)
        publisher=next(j for j in responses['actions/runs/1/attempts/1/jobs']['jobs'] if j['name']=='publish')
        publisher.update(status='in_progress',conclusion=None)
        env=dict(GITHUB_ACTIONS='true',GITHUB_JOB='publish',GITHUB_RUN_ID='1',GITHUB_RUN_ATTEMPT='1',
                 GITHUB_SHA=self.source,GITHUB_REF='refs/tags/v'+self.version,GITHUB_REPOSITORY=download.REPOSITORY)
        with patch.dict(os.environ,env),patch.object(publish,'tag_commit',return_value=self.source):
            self.assertEqual(self.retrieve_fixture(args,responses,archives,publication=True)['branch'],'release')
            with patch.dict(os.environ,{'GITHUB_REF':'refs/tags/v1.0.0-beta.2'}):
                with self.assertRaisesRegex(ValueError,'current trusted publisher'):
                    self.retrieve_fixture(args,responses,archives,publication=True)

    def test_tag_movement_before_download_receipt_is_refused(self):
        self.release_fixture('1.0.0-beta.1')
        args,responses,archives=self.download_fixture('release')
        with patch.object(publish,'tag_commit',side_effect=[self.source,'b'*40]):
            with self.assertRaisesRegex(ValueError,'tag changed during download'):
                self.retrieve_fixture(args,responses,archives)
        self.assertFalse((args.destination/'verified-download.json').exists())

    def test_only_manual_optin_authorizes_firmware_publication(self):
        env = dict(CI_PUBLISH='true',GITHUB_ACTIONS='true',GITHUB_JOB='publish',
                   GITHUB_EVENT_NAME='workflow_dispatch',GITHUB_REPOSITORY=download.REPOSITORY)
        with patch.dict(os.environ,env,clear=True):
            publish.require_authorization()
            for field,value in [('CI_PUBLISH','false'),('GITHUB_ACTIONS','false'),('GITHUB_JOB','verify'),
                                ('GITHUB_EVENT_NAME','push'),('GITHUB_EVENT_NAME','pull_request'),
                                ('GITHUB_REPOSITORY','fork/WsprryPico')]:
                with self.subTest(field=field,value=value), patch.dict(os.environ,{field:value}), \
                     patch.object(publish,'api',side_effect=AssertionError('network mutation')):
                    with self.assertRaisesRegex(ValueError,'explicit manual'):
                        publish.require_authorization()

    def publication_service(self):
        releases, tags, mutations = {}, {}, []
        def api(path, method='GET', data=None, missing=False):
            if method != 'GET': mutations.append((path, method, copy.deepcopy(data)))
            if path.startswith('releases/tags/'):
                value = releases.get(path.removeprefix('releases/tags/'))
                if value and value['draft']: value = None
                if value is None and not missing: raise ValueError('Missing fake release')
                return copy.deepcopy(value)
            if path == 'graphql':
                release = releases.get(data['variables']['tag'])
                return {'data':{'repository':{'release':
                    {'databaseId':release['id'],'isDraft':release['draft']} if release else None}}}
            if path.startswith('git/ref/tags/'):
                source = tags.get(path.removeprefix('git/ref/tags/'))
                return {'object':{'type':'commit','sha':source}} if source else None
            if path == 'git/refs':
                tags[data['ref'].removeprefix('refs/tags/')] = data['sha']
                return {}
            if path == 'releases' and method == 'POST':
                value = dict(data, id=len(releases)+1, assets=[])
                releases[value['tag_name']] = value
                return copy.deepcopy(value)
            if path.startswith('releases/') and method == 'PATCH':
                value = next(v for v in releases.values() if str(v['id']) == path.split('/')[1])
                value.update(data)
                return copy.deepcopy(value)
            if path.startswith('releases/') and method == 'GET':
                return copy.deepcopy(next(v for v in releases.values() if str(v['id']) == path.split('/')[1]))
            raise AssertionError((path, method, data))
        def upload(command, **kwargs):
            self.assertEqual(command[:3], ['gh','release','upload'])
            tag, path = command[3], Path(command[4])
            releases[tag]['assets'].append(dict(id=len(releases[tag]['assets'])+1, name=path.name,
                size=path.stat().st_size, digest='sha256:' + bundle.sha(path), state='uploaded'))
        return releases, tags, mutations, api, upload

    def test_permanent_release_is_complete_before_index_and_retry_is_idempotent(self):
        args, receipt = self.publication_fixture()
        releases, tags, mutations, api, upload = self.publication_service()
        with patch.object(publish, 'api', side_effect=api), patch.object(publish.subprocess, 'run', side_effect=upload):
            tag = publish.preserve(receipt, args.destination)
            self.assertEqual(len(releases[tag]['assets']), 9)
            self.assertFalse(releases[tag]['draft'])
            self.assertEqual(tags[tag], self.source)
            before = copy.deepcopy(mutations)
            publish.preserve(receipt, args.destination)
            self.assertEqual(mutations, before)  # Published bytes are never replaced.
            receipt['manifest_sha256'] = bundle.sha(args.destination / 'deployment/release-manifest.json')
            publish.update_index(receipt)
            self.assertEqual(publish.resolve('devel')['source'], self.source)
            self.assertNotIn('ci-main', releases)
            self.assertEqual(tags['ci-devel'], self.source)
            self.assertEqual(releases['ci-devel']['assets'], [])

    def test_publication_waits_for_new_tag_visibility_before_creating_release(self):
        args, receipt = self.publication_fixture()
        releases, tags, mutations, api, upload = self.publication_service()
        tag = 'v' + self.version
        hidden_reads = 2
        visible = False
        def delayed_visibility(path, method='GET', data=None, missing=False):
            nonlocal hidden_reads, visible
            if path == 'git/ref/tags/' + tag and tag in tags:
                if hidden_reads:
                    hidden_reads -= 1
                    return None
                visible = True
            if path == 'releases' and method == 'POST':
                self.assertTrue(visible, 'Release creation must wait for verified tag identity')
            return api(path, method, data, missing)
        with patch.object(publish, 'api', side_effect=delayed_visibility), \
             patch.object(publish.subprocess, 'run', side_effect=upload), patch('time.sleep') as sleep:
            publish.preserve(receipt, args.destination)
        self.assertEqual(sleep.call_args_list, [call(1), call(2)])
        self.assertEqual(tags[tag], self.source)
        self.assertFalse(releases[tag]['draft'])
        self.assertEqual(len(releases[tag]['assets']), 9)
        self.assertEqual(sum(path == 'git/refs' for path, _, _ in mutations), 1)

    def test_partial_draft_recovers_but_published_asset_mutation_is_rejected(self):
        args, receipt = self.publication_fixture()
        releases, tags, mutations, api, upload = self.publication_service()
        calls = 0
        def interrupted(command, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 3: raise RuntimeError('interrupted upload')
            upload(command)
        tag = 'v' + self.version
        with patch.object(publish, 'api', side_effect=api):
            with patch.object(publish.subprocess, 'run', side_effect=interrupted):
                with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                    publish.preserve(receipt, args.destination)
            self.assertTrue(releases[tag]['draft'])
            self.assertEqual(len(releases[tag]['assets']), 2)
            with patch.object(publish.subprocess, 'run', side_effect=upload):
                publish.preserve(receipt, args.destination)
                self.assertEqual(len(releases[tag]['assets']), 9)
                releases[tag]['assets'][0]['digest'] = 'sha256:' + '0'*64
                with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                    publish.preserve(receipt, args.destination)

    def test_existing_wrong_tag_never_moves(self):
        releases, tags, mutations, api, upload = self.publication_service()
        tags['v' + self.version] = '0'*40
        with patch.object(publish, 'api', side_effect=api):
            with self.assertRaisesRegex(ValueError, 'different source'):
                publish.ensure_tag('v' + self.version, self.source)
        self.assertEqual(mutations, [])

    def test_new_version_discovery_does_not_scan_release_history(self):
        def api(path, method='GET', data=None, missing=False):
            if path == 'releases/tags/v' + self.version: return None
            if path == 'graphql': return {'data':{'repository':{'release':None}}}
            raise AssertionError('Unnecessary release-history query: ' + path)
        with patch.object(publish,'api',side_effect=api) as calls:
            self.assertIsNone(publish.find_version_release('v' + self.version))
            self.assertEqual(calls.call_count, 2)

    def test_index_creation_recovers_after_orphaned_fixed_tag(self):
        args, receipt = self.publication_fixture()
        receipt['manifest_sha256'] = bundle.sha(args.destination / 'deployment/release-manifest.json')
        releases, tags, mutations, api, upload = self.publication_service()
        tags['ci-devel'] = 'a'*40  # A prior publisher stopped after creating its tag.
        with patch.object(publish,'api',side_effect=api), patch.object(publish,'ancestor',return_value=True):
            publish.update_index(receipt)
        self.assertEqual(tags['ci-devel'], 'a'*40)
        self.assertEqual(publish.parse_index(releases['ci-devel']['body'],'devel')['source'], self.source)

    def test_index_ancestry_prevents_old_rerun_and_cross_branch_rollback(self):
        previous = dict(branch='devel', source='a'*40, run_id=10, attempt=1)
        candidate = dict(branch='devel', source='b'*40, run_id=20, attempt=1)
        with patch.object(publish, 'ancestor', side_effect=lambda a,b:(a,b)==('a'*40,'b'*40)):
            self.assertTrue(publish.advance(previous, candidate))
            older = dict(previous, run_id=100)
            self.assertFalse(publish.advance(candidate, older))
        self.assertFalse(publish.advance(previous, dict(previous, run_id=9)))
        self.assertTrue(publish.advance(previous, dict(previous, attempt=2)))
        with patch.object(publish, 'ancestor', return_value=False):
            with self.assertRaisesRegex(ValueError, 'Diverged'):
                publish.advance(previous, candidate)
        with self.assertRaisesRegex(ValueError, 'Cross-branch'):
            publish.advance(previous, dict(candidate, branch='main'))

    def test_publication_collector_requires_current_trusted_job(self):
        args, responses, archives = self.download_fixture('devel')
        with self.assertRaisesRegex(ValueError, 'current trusted publisher'):
            self.retrieve_fixture(args, responses, archives, publication=True)
        responses['actions/runs/1/attempts/1'].update(status='in_progress', conclusion=None)
        responses['actions/runs/1/attempts/1/jobs'] = {'total_count':2, 'jobs':[
            dict(id=9,name='verify',status='completed',conclusion='success'),
            dict(id=10,name='publish',status='in_progress',conclusion=None)]}
        env = dict(GITHUB_ACTIONS='true',GITHUB_JOB='publish',GITHUB_RUN_ID='1',GITHUB_RUN_ATTEMPT='1',
                   GITHUB_SHA=self.source,GITHUB_REF='refs/heads/devel',GITHUB_REPOSITORY=download.REPOSITORY)
        with patch.dict(os.environ,env), patch.object(download,'required_jobs',return_value={'verify','publish'}):
            receipt = self.retrieve_fixture(args, responses, archives, publication=True)
            self.assertEqual(receipt['verification'], 'accepted-verify-job-and-payload')
            self.assertEqual(receipt['verify_job']['id'], 9)

    def test_preserved_archive_download_outlives_actions_storage(self):
        args, receipt = self.publication_fixture('main')
        releases, tags, mutations, api, upload = self.publication_service()
        with patch.object(publish, 'api', side_effect=api), patch.object(publish.subprocess,'run',side_effect=upload):
            tag = publish.preserve(receipt, args.destination)
        original = args.destination
        args.destination = self.base / 'preserved-main-download'
        actual_run = subprocess.run
        def fetch(command, stdout, **kwargs):
            if command[0] != 'gh': return actual_run(command, stdout=stdout, **kwargs)
            identifier = int(command[-1].split('/')[-1])
            filename = next(a['name'] for a in releases[tag]['assets'] if a['id'] == identifier)
            stdout.write((original / filename).read_bytes())
        verifier = bundle.verify
        with patch.object(publish,'api',side_effect=api), \
             patch.object(download,'api',side_effect=AssertionError('Actions storage expired')), \
             patch.object(download.subprocess,'run',side_effect=fetch), \
             patch.object(download,'inspection_tool',return_value={'path':'fixture-tool','sha256':'a'*64,'version':'fixture'}), \
             patch.object(bundle,'required_tests',return_value={'fixture'}), \
             patch.object(bundle,'verify',side_effect=lambda d,a,s,v:verifier(d,a,s,v,inspect=False)):
            downloaded = download.retrieve_published(args)
        self.assertEqual(downloaded['branch'], 'main')
        self.assertEqual(downloaded['uf2'], receipt['uf2'])
        self.assertEqual(bundle.sha(original / 'audit.zip'), bundle.sha(args.destination / 'audit.zip'))


if __name__ == '__main__':
    unittest.main()
