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
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/ci'))
import bundle


class BundleTests(unittest.TestCase):
    def test_workflow_commands_parse_as_strings(self):
        import yaml
        workflow = yaml.load((ROOT / '.github/workflows/software-build.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertIn('push', workflow['on'])
        for step in workflow['jobs']['verify']['steps']:
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


if __name__ == '__main__':
    unittest.main()
