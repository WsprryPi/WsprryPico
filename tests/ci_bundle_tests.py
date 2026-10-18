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
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/ci'))
import bundle
import download
import publish


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
        self.assertIn("github.event_name != 'pull_request'", publisher['if'])
        self.assertIn("github.repository == 'WsprryPi/WsprryPico'", publisher['if'])
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
        self.assertEqual(self.created_boundary, '103ee000')
        self.verify()
        wrong = 0x103f0000 if bundle.source_application_end(self.source) == 0x103ee000 else 0x103ee000
        self.mutate_manifest(lambda v: v['update'].update(application_end=f'{wrong:x}'))
        self.reseal()
        with self.assertRaisesRegex(ValueError, 'Flash reservation differs'):
            self.verify()

    def test_valid_inventory_and_distinct_archive_identity(self):
        result = self.verify()
        self.assertEqual(result['firmware']['frequency_selected_by_image'], None)
        self.assertNotIn('archive_digest', result)

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

    def download_fixture(self, branch, legacy=False):
        event = 'pull_request' if branch == 'pull-request' else 'push'
        ref = 'refs/pull/23/merge' if event == 'pull_request' else 'refs/heads/' + branch
        self.mutate_manifest(lambda v: v.update(
            workflow=dict(v['workflow'], event=event, ref=ref),
            deployment_candidate=branch != 'pull-request'))
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
                   head_sha=self.source, head_branch=branch, event=event,
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
