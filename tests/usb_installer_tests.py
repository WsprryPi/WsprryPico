"""Behavioral installer failure tests: substitute network and the USB writer."""
import contextlib
import copy
from email.message import Message
import fcntl
import io
import json
import os
import pty
import select
import shlex
import shutil
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import termios
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import usb_installer as installer

SERIAL = '1545B6EFBF78028C'


def encoded(value):
    return json.dumps(value).encode()


def uf2():
    def block(flags, address, number, total, family, payload, extension=bytes(220)):
        return (struct.pack('<8I', 0x0A324655, 0x9E5D5157, flags, address, 256, number, total, family)
                + payload + extension + struct.pack('<I', 0x0AB16F30))
    return (block(0xA000, 0x10FFFF00, 0, 2, 0xE48BFF57, b'\xef' * 256,
                  bytes.fromhex('04e35799') + bytes(216)) +
            block(0x2000, 0x10000000, 0, 2, 0xE48BFF59, b'A' * 256) +
            block(0x2000, 0x10000100, 1, 2, 0xE48BFF59, b'B' * 256))


def fixture(branch='devel', modern=False, version=None):
    """Real canonical public metadata with clearly synthetic image/license bytes."""
    base = ROOT / 'tests/fixtures/usb-installer'
    manifest = installer.decode((base / 'release-manifest.json').read_bytes())
    proof = installer.decode((base / 'ci-publication.json').read_bytes())
    if modern:
        manifest = installer.decode(encoded(manifest).replace(b'39084514130', b'40000000000'))
        proof = installer.decode(encoded(proof).replace(b'39084514130', b'40000000000'))
        manifest['update'].update(usb_maintenance=1, postboot_verification=1)
    manifest['workflow']['ref'] = 'refs/heads/' + branch
    proof['branch'] = branch
    for artifact in proof['artifacts']:
        artifact['name'] = artifact['name'].replace('-devel-', '-' + branch + '-')
    if version:
        previous = manifest['firmware_version']
        manifest.update(firmware_version=version, intended_tag='v'+version, channel=installer.version_kind(version))
        manifest['workflow'].update(ref='refs/tags/v'+version, event='workflow_dispatch')
        for asset in manifest['assets']:
            asset['path'] = asset['path'].replace(previous,version)
        proof.update(version=version,tag='v'+version,branch='release')
        for artifact in proof['artifacts']:
            artifact['name'] = artifact['name'].replace('-'+branch+'-','-release-')
    files = {a['path']: (uf2() if a['path'].endswith('.uf2') else b'synthetic test license\n')
             for a in manifest['assets']}
    for asset in manifest['assets']:
        asset.update(bytes=len(files[asset['path']]), sha256=installer.sha(files[asset['path']]))
    files['release-manifest.json'] = encoded(manifest)
    proof.update(manifest_sha256=installer.sha(files['release-manifest.json']),
                 uf2=next(a for a in manifest['assets'] if a['path'].endswith('.uf2')))
    files['ci-publication.json'] = encoded(proof)
    checksums = {a['path']: a['sha256'] for a in manifest['assets']}
    checksums['release-manifest.json'] = installer.sha(files['release-manifest.json'])
    files['SHA256SUMS'] = ''.join(f'{digest}  {name}\n' for name, digest in sorted(checksums.items())).encode()
    return files, manifest, proof


class Network:
    def __init__(self, branch='devel', version=None):
        self.files, self.manifest, self.proof = fixture(branch,version=version)
        self.branch, self.calls = branch, []
        self.tag = self.manifest['intended_tag']
        self.index = dict(schema='wsprrypico-ci-index/1', repository=installer.REPOSITORY,
                          branch=branch, tag=self.tag, source=self.proof['source'],
                          version=self.proof['version'], run_id=self.proof['run_id'], attempt=self.proof['attempt'],
                          uf2=self.proof['uf2'], manifest_sha256=self.proof['manifest_sha256'])
        assets = dict(self.files, **{'audit.zip': b'audit', 'deployment.zip': b'deployment'})
        self.release = dict(tag_name=self.tag, draft=False, prerelease=installer.version_kind(self.proof['version']) != 'stable',
                            assets=[dict(name=n, state='uploaded', size=len(d), digest='sha256:' + installer.sha(d),
                                         browser_download_url=installer.release_asset_url(self.tag, n))
                                    for n, d in assets.items()])
        for artifact in self.proof['artifacts']:
            next(a for a in self.release['assets'] if a['name'] == artifact['kind'] + '.zip')['digest'] = 'sha256:' + artifact['archive_sha256']
        self.run = dict(status='completed', conclusion='success', head_sha=self.proof['source'],
                        head_branch=self.tag if version else branch, path='.github/workflows/software-build.yml',
                        head_repository={'full_name': installer.REPOSITORY}, event='workflow_dispatch' if version else 'push', run_attempt=1)
        self.jobs = {'total_count': 2, 'jobs': [dict(name='verify', id=self.proof['verify_job']['id'], status='completed', conclusion='success'),
                                              dict(name='publish', id=2, status='completed', conclusion='success')]}
        self.unavailable_run = False

    def api(self, path):
        self.calls.append(path)
        if path == 'releases/tags/ci-' + self.branch:
            return dict(tag_name='ci-' + self.branch, draft=False,
                        body='<!-- wsprrypico-ci-index/1\n' + json.dumps(self.index) + '\n-->')
        if path.startswith('releases/tags/ci-'):
            raise installer.HttpFailure(404)
        if path == 'releases/tags/' + self.tag:
            return self.release
        if path.startswith('actions/workflows/software-build.yml/runs?'):
            return {'workflow_runs': []}
        if path == 'releases/latest':
            if self.release['prerelease'] is False:
                return self.release
            raise installer.HttpFailure(404)
        if path.startswith('git/ref/tags/'):
            return {'object': {'type': 'commit', 'sha': self.proof['source']}}
        if path.startswith('actions/runs/'):
            if path.endswith('per_page=100'):
                return self.jobs
            if self.unavailable_run:
                raise installer.HttpFailure(404)
            return self.run
        raise AssertionError('Unexpected network request: ' + path)

    def get(self, url, limit):
        self.calls.append(url)
        return self.files[installer.urllib.parse.unquote(url.rsplit('/', 1)[1])]


class HttpFailureTests(unittest.TestCase):
    NOW = 1792350000

    def http_error(self, status, headers=None, message='private upstream detail'):
        fields = Message()
        for name, value in (headers or {}).items():
            fields[name] = value
        return installer.urllib.error.HTTPError(installer.API + 'releases/tags/ci-devel', status,
                                                'upstream failure', fields, io.BytesIO(encoded({'message': message})))

    def refusal(self, status, headers=None, message='private upstream detail'):
        with patch.object(installer.urllib.request, 'urlopen', side_effect=self.http_error(status, headers, message)), \
             patch.object(installer.time, 'time', return_value=self.NOW):
            with self.assertRaises(installer.Refusal) as caught:
                installer.resolve(installer.Https(), 'devel')
        return caught.exception

    def test_primary_limit_survives_cli_without_usb_or_secret_details(self):
        failure = self.http_error(403, {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': str(self.NOW + 90)},
                                  'API rate limit exceeded for private address; secret-header-value')
        with patch.object(installer.urllib.request, 'urlopen', side_effect=failure) as network, \
             patch.object(installer.time, 'time', return_value=self.NOW), \
             patch.object(installer, 'Picotool', side_effect=AssertionError('USB writer requested')), \
             patch.object(installer, 'Management', side_effect=AssertionError('USB control requested')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            code = installer.main(['plan', '--branch', 'devel'])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(result['error_code'], 'github_rate_limited')
        self.assertEqual(result['retry_at'], self.NOW + 91)
        self.assertFalse(result['recovery_required'])
        self.assertIn('anonymous API request limit is exhausted (HTTP 403)', result['error'])
        self.assertIn('UTC', result['error'])
        self.assertNotIn('No verified', result['error'])
        self.assertNotIn('private address', output.getvalue())
        self.assertNotIn('secret-header', output.getvalue())
        self.assertEqual(network.call_count, 1)

    def test_retry_after_seconds_and_http_date_are_honored(self):
        date = installer.datetime.fromtimestamp(self.NOW + 125, installer.timezone.utc)
        for status, headers, deadline in [
                (429, {'Retry-After': '120'}, self.NOW + 121),
                (403, {'Retry-After': date.strftime('%a, %d %b %Y %H:%M:%S GMT')}, self.NOW + 126),
                (403, {'X-RateLimit-Remaining':'0','X-RateLimit-Reset':str(self.NOW + 90),'Retry-After':'120'}, self.NOW + 121)]:
            with self.subTest(status=status, headers=headers):
                error = self.refusal(status, headers)
                self.assertIsInstance(error, installer.GitHubRateLimit)
                self.assertEqual(error.details['retry_at'], deadline)

    def test_secondary_limit_without_usable_headers_has_honest_minimum(self):
        for headers in [{}, {'Retry-After':'invalid'}, {'Retry-After':'9' * 200},
                        {'X-RateLimit-Remaining':'0','X-RateLimit-Reset':'-1'},
                        {'Retry-After':'Wed, 01 Jan 2020 00:00:00 GMT'}]:
            with self.subTest(headers=headers):
                error = self.refusal(403, headers, 'You have exceeded a secondary rate limit.')
                self.assertEqual(error.details['retry_at'], self.NOW + 60)
                self.assertIn('no usable retry time', str(error))
                self.assertIn('at least one minute', str(error))
        self.assertIsInstance(self.refusal(429), installer.GitHubRateLimit)

    def test_missing_bookmark_is_distinct_from_permissions_server_and_connectivity(self):
        self.assertIn('No verified devel', str(self.refusal(404)))
        for status in [401, 403, 500, 503]:
            with self.subTest(status=status):
                error = self.refusal(status)
                self.assertIsInstance(error, installer.HttpFailure)
                self.assertEqual(error.status, status)
                self.assertNotIn('No verified', str(error))
        with patch.object(installer.urllib.request, 'urlopen', side_effect=installer.urllib.error.URLError('private detail')):
            with self.assertRaisesRegex(installer.Refusal, 'check connectivity'):
                installer.resolve(installer.Https(), 'devel')

    def test_limit_at_release_or_live_provenance_is_not_replaced(self):
        for fail_at in ['releases/tags/v', 'actions/runs/']:
            net = Network()
            api = net.api
            error = installer.GitHubRateLimit(403, {'X-RateLimit-Remaining':'0','X-RateLimit-Reset':str(int(installer.time.time()) + 60)})
            def request(path):
                if path.startswith(fail_at):
                    raise error
                return api(path)
            with patch.object(net, 'api', side_effect=request), self.assertRaises(installer.GitHubRateLimit) as caught:
                installer.resolve(net, 'devel')
            self.assertIs(caught.exception, error)

    def test_additional_run_limit_keeps_verified_image_and_retry_guidance(self):
        error = installer.GitHubRateLimit(429, {'Retry-After':'60'})
        with patch.object(Network, 'api', side_effect=error):
            result = installer.recent_ci(Network(), 'devel', {})
        self.assertFalse(result['available'])
        self.assertEqual(result['error_code'], 'github_rate_limited')
        self.assertEqual(result['retry_at'], error.details['retry_at'])
        self.assertEqual(result['reason'], str(error))
        wrapped = installer.TransactionFailure(str(error), {'recovery_required':True}, Path('/private/transaction'), error)
        self.assertEqual(wrapped.details, error.details)


class InstallerTests(unittest.TestCase):
    def test_explicit_beta_final_metadata_and_stable_selection_keep_canonical_provenance(self):
        for version in ('1.0.0-beta.1','1.0.0','1.0.0+build.001'):
            for branch in ('main','devel'):
                with self.subTest(version=version,branch=branch):
                    net=Network(branch,version)
                    _,manifest,image=installer.resolve(net,branch,version)
                    self.assertEqual(manifest['firmware_version'],version)
                    self.assertEqual(len(image),512)
                    self.assertFalse(any('releases/tags/ci-' in c for c in net.calls))
                    self.assertEqual(installer.resolve_installed(net,version)[1]['firmware_version'],version)
                    net.unavailable_run=True
                    self.assertEqual(installer.resolve(net,branch,version)[2],image)
                    if installer.version_kind(version)=='stable':
                        self.assertEqual(installer.resolve(net,branch,stable=True)[1]['firmware_version'],version)

    def test_release_misclassification_tag_swap_preview_and_failed_jobs_refuse_before_usb(self):
        for mutation in ('classification','tag','source','job','skipped','event','event-swap','branch'):
            net=Network(version='1.0.0-beta.1')
            if mutation=='classification':net.release['prerelease']=False
            if mutation=='tag':net.release['tag_name']='v1.0.0'
            if mutation=='source':net.run['head_sha']='a'*40
            if mutation=='job':net.jobs['jobs'][1]['conclusion']='failure'
            if mutation=='skipped':net.jobs['jobs'][1]['conclusion']='skipped'
            if mutation=='event':net.run['event']='pull_request'
            if mutation=='event-swap':net.run['event']='push'
            if mutation=='branch':net.run['head_branch']='devel'
            with self.subTest(mutation=mutation),patch.object(installer,'discover',side_effect=AssertionError('USB opened')):
                with self.assertRaises(installer.Refusal):installer.resolve(net,version='1.0.0-beta.1')

    def test_tag_movement_during_release_download_refuses_before_usb(self):
        net=Network(version='1.0.0-beta.1')
        original=net.api
        reads=0
        def api(path):
            nonlocal reads
            if path=='git/ref/tags/'+net.tag:
                reads+=1
                if reads>1:return {'object':{'type':'commit','sha':'a'*40}}
            return original(path)
        with patch.object(net,'api',side_effect=api),patch.object(installer,'discover',side_effect=AssertionError('USB opened')):
            with self.assertRaisesRegex(installer.Refusal,'tag changed during download'):
                installer.resolve(net,version='1.0.0-beta.1')

    def test_build_metadata_uses_github_encoded_tag_and_asset_components(self):
        version='1.0.0+build.001'
        tag='v'+version
        name=f'WsprryPico-{version}-pico2_w.uf2'
        expected=installer.DOWNLOAD+'v1.0.0%2Bbuild.001/WsprryPico-1.0.0%2Bbuild.001-pico2_w.uf2'
        self.assertEqual(installer.release_asset_url(tag,name),expected)
        net=Network(version=version)
        installer.resolve(net,version=version)
        self.assertIn(expected,net.calls)
        net.release['assets'][0]['browser_download_url']=installer.DOWNLOAD+tag+'/'+net.release['assets'][0]['name']
        with self.assertRaisesRegex(installer.Refusal,'public asset'):
            installer.resolve(net,version=version)

    def test_beta_and_final_preserving_upgrade_and_recovery(self):
        self.upgrade_transaction(version='1.0.0-beta.1',programming_recovery=True)
        self.upgrade_transaction(version='1.0.0',old_version='1.0.0-beta.1',programming_recovery=True)

    def test_public_bundles_on_both_branches(self):
        for branch in ('main', 'devel'):
            with self.subTest(branch=branch):
                net = Network(branch)
                files, manifest, image = installer.resolve(net, branch)
                self.assertEqual(image, b'A' * 256 + b'B' * 256)
                self.assertEqual(manifest['workflow']['ref'], 'refs/heads/' + branch)
                self.assertEqual(sum(c.startswith('releases/tags/ci-') for c in net.calls), 1)

    def test_default_main_does_not_substitute_devel(self):
        net = Network('devel')
        with self.assertRaisesRegex(installer.Refusal, 'No verified main'):
            installer.resolve(net)
        self.assertEqual(net.calls, ['releases/tags/ci-main'])

    def test_explicit_version_does_not_read_bookmark(self):
        net = Network()
        installer.resolve(net, 'devel', net.proof['version'])
        self.assertFalse(any(c.startswith('releases/tags/ci-') for c in net.calls))

    def test_cross_branch_metadata_refused(self):
        net = Network()
        net.index['branch'] = 'main'
        with self.assertRaises(installer.Refusal):
            installer.resolve(net, 'devel')

    def test_bad_run_jobs_receipt_assets_and_bookmark_refuse(self):
        changes = [lambda n: n.run.update(conclusion='failure'),
                   lambda n: n.run.update(status='in_progress'),
                   lambda n: n.run.update(event='pull_request'),
                   lambda n: n.run.update(head_repository={'full_name': 'attacker/fork'}),
                   lambda n: n.jobs['jobs'][1].update(conclusion='skipped'),
                   lambda n: n.jobs['jobs'][0].update(id=0),
                   lambda n: n.release.update(prerelease=False),
                   lambda n: n.release['assets'].pop(),
                   lambda n: n.release['assets'].append(copy.deepcopy(n.release['assets'][0])),
                   lambda n: n.files.update({'SHA256SUMS': b'partial download'}),
                   lambda n: n.index.update(manifest_sha256='0' * 64),
                   lambda n: n.release['assets'][0].update(browser_download_url='https://attacker.invalid/payload')]
        for change in changes:
            net = Network()
            change(net)
            with self.subTest(change=change), self.assertRaises(installer.Refusal):
                installer.resolve(net, 'devel')

    def test_preserved_receipt_after_actions_expiry(self):
        net = Network()
        net.unavailable_run = True
        _, _, image = installer.resolve(net, 'devel')
        self.assertEqual(len(image), 512)

    def test_malformed_json_and_duplicate_fields(self):
        for data in (b'{"schema":1,"schema":1}', b'{"x":NaN}', b'\xff'):
            with self.assertRaises(installer.Refusal):
                installer.decode(data)

    def test_manifest_canonical_schema_and_storage_versions(self):
        files, manifest, _ = fixture()
        for change in (lambda m: m.update(schema_version=2),
                       lambda m: m['firmware'].update(board='pico_w'),
                       lambda m: m['firmware'].update(role='inhibited'),
                       lambda m: m['update'].update(application_end='10400000'),
                       lambda m: m['checks'].update(failed=1),
                       lambda m: m['source'].update(clean=False),
                       lambda m: m.update(unknown='field')):
            other = copy.deepcopy(manifest)
            change(other)
            with self.assertRaises(installer.Refusal):
                installer.verify_bundle(dict(files, **{'release-manifest.json': encoded(other)}), 'devel')

    def test_uf2_unknown_flags_family_alias_wrap_and_numbering(self):
        payload = uf2()
        for offset, value in ((512 + 8, 0x2001), (512 + 12, 0x103EDFFF),
                              (512 + 12, 0x103EE000), (512 + 12, 0x11300000),
                              (512 + 12, 0xFFFFFF00), (512 + 28, 0xE48BFF56),
                              (1024 + 20, 0), (24, 3), (288, 0)):
            changed = bytearray(payload)
            struct.pack_into('<I', changed, offset, value)
            with self.subTest(offset=offset, value=value), self.assertRaises(installer.Refusal):
                installer.uf2_blocks(changed, 0x103EE000)
        for data in (payload[:-1], payload[512:], b''):
            with self.assertRaises(installer.Refusal):
                installer.uf2_blocks(data, 0x103EE000)

    def test_cli_plan_uses_main_and_never_usb_or_tool(self):
        net = Network('main')
        with patch.object(installer, 'Https', return_value=net), \
             patch.object(installer, 'discover', side_effect=AssertionError('USB opened')), \
             patch.object(installer, 'Picotool', side_effect=AssertionError('Tool opened')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(installer.main(['plan']), 0)
        self.assertEqual(json.loads(output.getvalue())['branch'], 'main')

    def test_programming_requires_device_and_operation_confirmation(self):
        net = Network('main')
        with patch.object(installer, 'Https', return_value=net), \
             patch.object(installer, 'Picotool', side_effect=AssertionError('Programming attempted')), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(['install']), 2)

    def test_success_and_failure_results_use_public_result_schema(self):
        net = Network('main')
        record = dict(schema='wsprrypico-usb-transaction/1', stage='failed', recovery_required=True)
        for failure in (False, True):
            with patch.object(installer, 'Https', return_value=net), \
                 patch.object(installer, 'selected', return_value=dict(serial=SERIAL, mode='bootsel', parent='1-1.3')), \
                 patch.object(installer, 'transaction', side_effect=installer.TransactionFailure('fixture', record, Path('/private/fixture')) if failure else None,
                              return_value=dict(record, stage='complete')), \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                code = installer.main(['install', '--device', SERIAL, '--yes', '--board', 'pico2_w'])
            value = json.loads(output.getvalue())
            self.assertEqual(value['schema'], 'wsprrypico-usb-result/1')
            self.assertEqual(value['ok'], not failure)
            self.assertEqual(code, 3 if failure else 0)

    def test_selectors_are_not_silently_ignored(self):
        for choice in (['--version','0.1.0-ci.2.1'], ['--stable'], ['--local-bundle','other']):
            with patch.object(installer, 'Https', side_effect=AssertionError('network requested')), contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(installer.main(['plan','--bundle','fixture',*choice]),2)
            self.assertIn('cannot be combined', json.loads(out.getvalue())['error'])

    def test_no_stable_release_never_substitutes_ci(self):
        net=Network()
        with self.assertRaises(installer.Refusal): installer.resolve(net,'devel',stable=True)
        self.assertEqual(net.calls,['releases/latest'])

    def test_developer_build_failure_never_selects_an_alternate_image(self):
        with patch.object(installer,'build_local',side_effect=installer.Refusal('compiler failed')), \
             patch.object(installer,'resolve',side_effect=AssertionError('fallback selected')), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(installer.main(['plan','--local-build','source','--build-dir','new']),2)
        self.assertIn('compiler failed',json.loads(out.getvalue())['error'])

    def test_modern_upgrade_and_same_boot_recovery_preserve_all_banks(self):
        self.upgrade_transaction()

    def test_postboot_semantic_mismatch_never_releases_maintenance(self):
        self.upgrade_transaction(mismatch=True)

    def test_faulted_postboot_never_releases_maintenance(self):
        self.upgrade_transaction(fault=True)

    def test_explicit_maintenance_decline_needs_no_programming_recovery(self):
        self.upgrade_transaction(declined=True)

    def test_old_provenance_outage_leaves_application_untouched(self):
        self.upgrade_transaction(old_network_failure=True)

    def test_repeated_application_read_failures_remain_recoverable(self):
        self.upgrade_transaction(recovery_retries=True)

    def test_completed_bootsel_recovery_remains_repeatable_in_application(self):
        self.upgrade_transaction(programming_recovery=True)

    def test_legacy_migration_waits_then_preserves_settings_and_finishes(self):
        self.upgrade_transaction(migration=True)

    def test_migration_failure_paths_never_authorize_a_write(self):
        for failure in ('enabled', 'busy', 'not_bootsel', 'wrong_port', 'backup', 'old_image', 'snapshot', 'old_bundle'):
            with self.subTest(failure=failure):
                self.upgrade_transaction(migration=True, migration_failure=failure)

    def test_legacy_migration_semantic_mismatch_keeps_verification_hold(self):
        self.upgrade_transaction(migration=True, mismatch=True)

    def test_legacy_migration_reserved_readback_mismatch_never_boots(self):
        self.upgrade_transaction(migration=True, migration_failure='reserved')

    def test_unchanged_refusals_have_bounded_expiring_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for index in range(10):
                directory=root/(SERIAL+'-'+str(index));directory.mkdir()
                (directory/'transaction.json').write_bytes(encoded(dict(schema='wsprrypico-usb-transaction/1',
                    serial=SERIAL,stage='failed',failure_stage='maintenance_refused',recovery_required=False)))
                os.utime(directory,(1_000_000+index,1_000_000+index))
            with patch.object(installer.time,'time',return_value=1_000_100):installer.prune_transactions(root)
            self.assertEqual({p.name for p in root.iterdir()},{SERIAL+'-'+str(i) for i in range(2,10)})
            with patch.object(installer.time,'time',return_value=2_000_000):installer.prune_transactions(root)
            self.assertEqual(list(root.iterdir()),[])

    def test_unresolved_recovery_is_retained_at_capacity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for index in range(8):
                directory=root/(SERIAL+'-'+str(index));directory.mkdir()
                (directory/'transaction.json').write_bytes(encoded(dict(schema='wsprrypico-usb-transaction/1',
                    serial=SERIAL,stage='failed',recovery_required=True)))
                os.utime(directory,(1,1))
            with self.assertRaisesRegex(installer.Refusal,'Eight unresolved'):installer.prune_transactions(root)
            self.assertEqual(len(list(root.iterdir())),8)

    def test_atomic_state_write_failure_preserves_old_record_and_retries(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'transaction.json';path.write_bytes(b'old record')
            with patch.object(installer.os,'replace',side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):installer.save_json(path,{'stage':'new'})
            self.assertEqual(path.read_bytes(),b'old record')
            self.assertEqual(list(path.parent.iterdir()),[path])
            installer.save_json(path,{'stage':'retried'})
            self.assertEqual(json.loads(path.read_bytes()),{'stage':'retried'})

    def test_private_path_traversal_symlink_git_and_web_roots_refuse(self):
        escaped=Path.home()/'.local/state/wsprrypico-usb/../../../outside'
        with self.assertRaisesRegex(installer.Refusal,'traversal'):installer.private_directory(escaped)
        with tempfile.TemporaryDirectory() as temporary:
            home=Path(temporary).resolve()
            with patch.object(Path,'home',return_value=home):
                root=installer.private_directory(home/'.local/state/wsprrypico-usb')
                self.assertEqual(root.stat().st_mode&0o777,0o700)
                (root/'redirect').symlink_to(home,target_is_directory=True)
                with self.assertRaises(installer.Refusal):installer.private_directory(root/'redirect/private')
                with self.assertRaises(installer.Refusal):installer.private_directory(root/'www/private')
                (root/'.git').write_text('fixture')
                with self.assertRaises(installer.Refusal):installer.private_directory(root/'inside')

    def test_local_identity_outlives_secret_backup_retention(self):
        data=bytearray(uf2());tag=b'WsprryPico USB maintenance 1 postboot verification 1'
        data[544:800]=tag.ljust(256,b'\0');data=bytes(data)
        asset={'path':'WsprryPico-0.0.0-devel-pico2_w.uf2','bytes':len(data),'sha256':installer.sha(data)}
        meta={'schema':'wsprrypico-local-build/1','board':'pico2_w','variant':'normal','version':'0.0.0-devel',
              'source':{'revision':'a'*40,'identity':'a'*12,'dirty':False,'inputs_sha256':'b'*64},
              'usb_update_contract':1,'application_end':'103f0000','uf2':asset}
        files={'local-build.json':encoded(meta),asset['path']:data}
        manifest,image=installer.verify_local(files)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);directory=root/(SERIAL+'-complete');directory.mkdir()
            for name,value in files.items():(directory/name).write_bytes(value)
            record={'schema':'wsprrypico-usb-transaction/1','serial':SERIAL,'uf2_sha256':asset['sha256'],'stage':'complete','recovery_required':False}
            (directory/'transaction.json').write_bytes(encoded(record))
            installer.remember_local(directory,record)
            os.utime(directory,(1,1));installer.prune_transactions(root)
            self.assertFalse(directory.exists())
            flash=image+b'\xff'*(installer.FLASH_SIZE-len(image))
            result=installer.installed_local(root,SERIAL,{'source_revision':'a'*12},flash)
            self.assertEqual(result[2],image)
            with self.assertRaises(installer.Refusal):installer.installed_local(root,'0'*16,{'source_revision':'a'*12},flash)
            self.assertNotIn('backup',next(root.glob('.local-reference-*.json')).read_text())

    def upgrade_transaction(self,mismatch=False,fault=False,declined=False,old_network_failure=False,recovery_retries=False,programming_recovery=False,migration=False,migration_failure=None,version=None,old_version=None):
        files,manifest,_=fixture(modern=True,version=version); image=b'A'*256+b'B'*256
        old_files,old_manifest,_=fixture(modern=True,version=old_version) if old_version else fixture() if migration else (files,manifest,None)
        before=bytearray(b'\xff'*installer.FLASH_SIZE);before[:len(image)]=image
        for offset in range(installer.PERSISTENT_START,installer.FLASH_SIZE,4096):before[offset+17]=71
        original=bytes(before); commands=[]; phase=['application','verification']; snapshots=[0]
        board=lambda:dict(serial=SERIAL,parent='changed' if migration_failure=='wrong_port' and phase[0]=='bootsel' else 'fixed',mode=phase[0],ports={'4':'fixture'})
        def snapshot(_):
            snapshots[0]+=1
            return dict(serial=SERIAL,parent='fixed',target=dict(scope='member',device_id=installer.device_id(SERIAL),boot_id='b'*32),
                revision='"4"',firmware=('0.1.0-ci.2.1' if old_network_failure else old_manifest['firmware_version']) if snapshots[0]==1 else manifest['firmware_version'],source_revision=manifest['source']['revision'][:12],
                status=dict(job=dict(state='failed' if fault and snapshots[0]>1 else 'running' if migration_failure=='busy' else 'empty',output_active=False,owner_id=None),standalone=dict(suspended=False,watermark_utc_ns='7')),
                config={'config':{'enabled':migration_failure=='enabled'}},progress=dict(fields={'callsign':'AA0NT'},draft_revision='3'),
                hostname={'saved':'changed.local' if mismatch and snapshots[0]>1 else 'fixture.local'},
                frequency={'frequency_hz':None},calibration={'saved':None})
        class Tool:
            path='fixture'; identity={'version':'fixture'}
            reads=0
            def __init__(self,_):pass
            def run(self,serial,*args,**_):
                commands.append(args)
                if '-x' in args:phase[0]='application'
                return ' type: RP2350\n chipid: 0x'+serial.lower()+'\n'
            def read_flash(self,serial,path):
                self.reads+=1
                if migration_failure=='backup':raise installer.Refusal('backup failed')
                data=(b'X'+original[1:]) if migration_failure=='old_image' else original
                if migration_failure=='reserved' and self.reads>1:
                    data=data[:installer.PERSISTENT_START]+b'X'+data[installer.PERSISTENT_START+1:]
                path.write_bytes(data);return data
        class Management:
            def __init__(self,_):pass
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def enter_bootsel(self,snapshot):
                if declined:raise installer.MaintenanceDeclined('Firmware refused guarded USB maintenance')
                phase[0]='bootsel'
            def get(self,_):return {'phase':phase[1]}
            def finish_verification(self,_):phase[1]='idle'
        with tempfile.TemporaryDirectory() as temporary:
            args=SimpleNamespace(operation='upgrade',device=SERIAL,board='pico2_w',yes=True,branch='devel',picotool='fixture',state_dir=Path(temporary))
            info=' name: WsprryPico\n version: '+manifest['firmware_version']+'\n description: Standalone PIO/DMA RF '+manifest['source']['revision'][:12]+'\n pico_board: pico2_w\n target chip: RP2350\n'
            with patch.object(installer,'private_directory',return_value=Path(temporary)), \
                 patch.object(installer,'device_lock',lambda _:contextlib.nullcontext()), \
                 patch.object(installer,'Picotool',Tool),patch.object(installer,'command',return_value=info), \
                 patch.object(installer,'selected',wraps=installer.selected), \
                 patch.object(installer,'discover',side_effect=lambda:[board()]), \
                 patch.object(installer,'public_snapshot',side_effect=snapshot),patch.object(installer,'Management',Management), \
                 patch.object(installer,'resolve_installed',side_effect=installer.Refusal('old network unavailable') if old_network_failure else None,return_value=(old_files,old_manifest,image)):
                if migration:
                    if migration_failure in ('enabled','busy'):
                        with self.assertRaises(installer.TransactionFailure):installer.transaction(args,files,manifest,image,Network())
                        self.assertFalse(commands);return
                    result=installer.transaction(args,files,manifest,image,Network())
                    self.assertEqual(result['stage'],'awaiting_bootsel')
                    self.assertTrue(result['manual_bootsel_required'])
                    self.assertFalse(commands);self.assertFalse(list(Path(temporary).glob('*/before.bin')))
                    args.transaction=Path(result['transaction'])
                    phase[0]='application' if migration_failure=='not_bootsel' else 'bootsel'
                    if migration_failure=='snapshot':(args.transaction.parent/'preflight.json').write_text('{}')
                    if migration_failure=='old_bundle':(args.transaction.parent/'installed/SHA256SUMS').write_text('changed')
                    if migration_failure or mismatch:
                        with self.assertRaises(installer.TransactionFailure):installer.recover_transaction(args)
                        self.assertEqual(phase[1],'verification')
                        if migration_failure:
                            if migration_failure=='reserved':
                                self.assertEqual(len([c for c in commands if c[0]=='load']),1)
                                self.assertFalse(any('-x' in c for c in commands));return
                            self.assertFalse(any(c[0]=='load' for c in commands))
                            if migration_failure=='not_bootsel':
                                migration_failure=None;phase[0]='bootsel'
                                self.assertEqual(installer.recover_transaction(args)['stage'],'complete')
                            return
                    else:
                        result=installer.recover_transaction(args)
                        self.assertEqual(result['stage'],'complete');self.assertEqual(phase[1],'idle')
                        self.assertEqual(installer.recover_transaction(args)['stage'],'complete')
                elif mismatch or fault or declined or old_network_failure:
                    reason='Saved semantic state' if mismatch else 'busy' if fault else 'Firmware refused' if declined else 'old network unavailable'
                    with self.assertRaisesRegex(installer.TransactionFailure,reason):installer.transaction(args,files,manifest,image,Network())
                    self.assertEqual(phase[1],'verification')
                else:
                    result=installer.transaction(args,files,manifest,image,Network())
                    self.assertEqual(result['stage'],'complete');self.assertEqual(phase[1],'idle')
                    args.transaction=Path(result['transaction'])
                    if programming_recovery:
                        record=json.loads(args.transaction.read_text())
                        record.update(stage='failed',failure_stage='programming',recovery_required=True)
                        installer.save_json(args.transaction,record);phase[:]=['bootsel','verification']
                        self.assertEqual(installer.recover_transaction(args)['stage'],'complete')
                    if recovery_retries:
                        record=json.loads(args.transaction.read_text())
                        record.update(stage='failed',failure_stage='launching_verification_boot',recovery_required=True)
                        record.pop('verification_release_boot',None)
                        installer.save_json(args.transaction,record);phase[1]='verification'
                        unread=snapshot(board());unread['firmware']='unconfirmed'
                        for _ in range(2):
                            with patch.object(installer,'public_snapshot',return_value=unread):
                                with self.assertRaisesRegex(installer.TransactionFailure,'identity/version'):
                                    installer.recover_transaction(args)
                            self.assertEqual(json.loads(args.transaction.read_text())['failure_stage'],'launching_verification_boot')
                            self.assertEqual(phase[1],'verification')
                    self.assertEqual(installer.recover_transaction(args)['stage'],'complete')
            record=json.loads(next(Path(temporary).glob('*/transaction.json')).read_text())
            if declined or old_network_failure:
                self.assertIn('refused' if declined else 'network unavailable', record['failure_reason'])
            self.assertEqual(record['recovery_required'],mismatch or fault)
            self.assertEqual(len([a for a in commands if a[0]=='load']),0 if declined or old_network_failure else 4 if programming_recovery else 2)
            if declined or old_network_failure:
                self.assertEqual(phase[0],'application');self.assertFalse(list(Path(temporary).glob('*/before.bin')));return
            self.assertEqual(next(Path(temporary).glob('*/after.bin')).read_bytes()[installer.PERSISTENT_START:],original[installer.PERSISTENT_START:])

    def test_initial_classification_distinguishes_e10_from_saved_state(self):
        data=bytearray(b'\xff'*installer.FLASH_SIZE)
        self.assertTrue(all(installer.classify_flash(data).values()))
        data[-256:]=b'\xef'*256
        self.assertTrue(all(installer.classify_flash(data).values()))
        data[4096]=1
        self.assertFalse(installer.classify_flash(data)['application_erased'])
        self.assertTrue(installer.classify_flash(data)['saved_state_erased'])
        data[installer.PERSISTENT_START]=1
        self.assertFalse(installer.classify_flash(data)['saved_state_erased'])

    def test_wrong_or_replaced_usb_identity_refuses(self):
        with patch.object(installer, 'discover', return_value=[]):
            with self.assertRaises(installer.Refusal):
                installer.selected(SERIAL)
        devices = [dict(serial=SERIAL, mode='bootsel', parent='changed', ports={})]
        with patch.object(installer, 'discover', return_value=devices):
            with self.assertRaises(installer.Refusal):
                installer.selected(SERIAL, 'bootsel', 'original')

    def test_nonblank_initial_install_does_not_program(self):
        self.transaction_failure('nonblank')

    def test_backup_failure_does_not_program(self):
        self.transaction_failure('backup')

    def test_flash_preservation_failure_leaves_recovery_record(self):
        self.transaction_failure('preservation')

    def transaction_failure(self, failure):
        files, manifest, _ = fixture()
        image = b'A' * 256 + b'B' * 256
        commands = []
        class Tool:
            path = 'fixture'
            identity = {'sha256': '0' * 64, 'version': 'fixture'}
            reads = 0
            def __init__(self, _): pass
            def run(self, serial, *args, **_):
                commands.append(args)
                return ' type: RP2350\n chipid: 0x' + serial.lower() + '\n'
            def read_flash(self, serial, path):
                self.reads += 1
                if failure == 'backup':
                    raise installer.Refusal('backup read failed')
                data = bytearray(b'\xff' * installer.FLASH_SIZE)
                if failure == 'nonblank': data[0] = 1
                if self.reads > 1:
                    data[:len(image)] = image
                    data[installer.PERSISTENT_START] = 0
                path.write_bytes(data)
                return bytes(data)
        with tempfile.TemporaryDirectory() as temporary:
            args = SimpleNamespace(device=SERIAL, board='pico2_w', state_dir=Path(temporary),
                                   operation='install', branch='devel', picotool='fixture')
            with patch.object(installer, 'Picotool', Tool), \
                 patch.object(installer, 'private_directory', return_value=Path(temporary)), \
                 patch.object(installer, 'command', return_value=' name: WsprryPico\n version: ' + manifest['firmware_version'] + '\n description: Standalone PIO/DMA RF ' + manifest['source']['revision'][:12] + '\n pico_board: pico2_w\n target chip: RP2350\n'), \
                 patch.object(installer, 'device_lock', lambda _: contextlib.nullcontext()), \
                 patch.object(installer, 'selected', return_value=dict(serial=SERIAL, mode='bootsel', parent='fixture')):
                with self.assertRaises(installer.Refusal):
                    installer.transaction(args, files, manifest, image)
            record = json.loads(next(Path(temporary).glob('*/transaction.json')).read_text())
            self.assertEqual(record['stage'], 'failed')
            self.assertEqual(record['recovery_required'], failure == 'preservation')
            self.assertEqual(any(c[0] == 'load' for c in commands), failure == 'preservation')
            self.assertFalse(any(c[0] == 'reboot' for c in commands))
            self.assertNotIn('before.bin', json.dumps(record))


class PicotoolCompatibilityTests(unittest.TestCase):
    def tool(self, version, *, missing=None, usb=True):
        with tempfile.TemporaryDirectory() as temporary:
            binary = Path(temporary)/'picotool'
            binary.write_bytes(b'fixture executable')
            def command(arguments):
                if arguments[1:] == ['version']:
                    return 'picotool v'+version+' (Linux, fixture)'+('' if usb else ' (without USB support)')
                self.assertEqual(arguments[1], 'help')
                operation = arguments[2]
                options = {'info': '-a --ser', 'save': '-r -v -t --ser',
                           'load': '--ignore-partitions -v -u -x --ser',
                           'verify': '-t -o --ser', 'erase': '-r --ser'}[operation]
                return options.replace(missing[1], '') if missing and operation == missing[0] else options
            with patch.object(installer.shutil, 'which', return_value=str(binary)), \
                 patch.object(installer, 'command', side_effect=command):
                return installer.Picotool().identity

    def test_current_and_future_compatible_2x_releases_are_accepted(self):
        for version in ('2.3.0', '2.3.1', '2.3.8', '2.4.0', '2.99.12'):
            with self.subTest(version=version):
                identity = self.tool(version)
                self.assertTrue(identity['version'].startswith('picotool v'+version+' '))
                self.assertEqual(identity['sha256'], installer.sha(b'fixture executable'))

    def test_old_major_new_major_prerelease_and_usb_less_builds_refuse(self):
        for version in ('1.5.0', '2.2.9', '3.0.0', '2.3.1-rc1', 'not-a-version'):
            with self.subTest(version=version), self.assertRaises(installer.Refusal):
                self.tool(version)
        with self.assertRaisesRegex(installer.Refusal, 'USB support'):
            self.tool('2.3.1', usb=False)

    def test_each_required_usb_operation_refuses_missing_options(self):
        for operation, option in (('info', '-a'), ('info', '--ser'), ('save', '-r'), ('save', '-v'),
                                 ('load', '--ignore-partitions'), ('load', '-x'), ('load', '-u'),
                                 ('verify', '-o'), ('verify', '-t'), ('erase', '-r')):
            with self.subTest(operation=operation, option=option), self.assertRaisesRegex(installer.Refusal, operation):
                self.tool('2.4.0', missing=(operation, option))


class FinishedHistoryTests(unittest.TestCase):
    def record(self, root, name, *, recovery=False, stage='complete', operation='upgrade'):
        directory = root/(SERIAL+'-'+name)
        directory.mkdir()
        value = dict(schema='wsprrypico-usb-transaction/1', serial=SERIAL, operation=operation,
                     stage=stage, recovery_required=recovery)
        installer.save_json(directory/'transaction.json', value)
        (directory/'before.bin').write_bytes(b'private fixture backup')
        return directory, value

    def test_verified_application_finishes_at_limit_and_keeps_all_pending_backups(self):
        _, manifest, _ = fixture(modern=True)
        snapshot = dict(target=dict(device_id=installer.device_id(SERIAL), boot_id='b'*32),
            firmware=manifest['firmware_version'], source_revision=manifest['source']['revision'][:12],
            status=dict(job=dict(state='empty', output_active=False, owner_id=None),
                        standalone=dict(suspended=False, watermark_utc_ns='7')),
            config={'config': {'enabled': False}}, progress=dict(fields={}, draft_revision='1'),
            hostname={'saved': 'fixture.local'}, frequency={'frequency_hz': None}, calibration={'saved': None})
        board = dict(serial=SERIAL, mode='application', parent='fixed')
        class Management:
            def __init__(self, _): pass
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def get(self, _): return {'phase': 'verification'}
            def finish_verification(self, _): pass
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old = [self.record(root, str(index))[0] for index in range(2)]
            # Future timestamps must not evict the transaction just verified.
            for index, directory in enumerate(old):
                os.utime(directory, (installer.time.time()+3600+index,)*2)
            pending = [self.record(root, 'pending-'+str(index), recovery=True, stage='failed')[0] for index in range(8)]
            current, record = self.record(root, 'current', recovery=True, stage='launching_verification_boot')
            record['parent'] = 'fixed'
            args = SimpleNamespace(device=SERIAL)
            with patch.object(installer, 'discover', return_value=[board]), \
                 patch.object(installer, 'selected', return_value=board), \
                 patch.object(installer, 'public_snapshot', return_value=snapshot), \
                 patch.object(installer, 'Management', Management):
                result = installer.verify_application(args, None, record, current/'transaction.json', manifest, snapshot)
            self.assertEqual(result['stage'], 'complete')
            self.assertTrue(result['preserved'])
            self.assertNotIn('retention_warning', result)
            self.assertEqual(Path(result['transaction']), current/'transaction.json')
            self.assertEqual((current/'before.bin').read_bytes(), b'private fixture backup')
            complete = [p for p in root.glob('*/transaction.json') if not installer.decode(p.read_bytes())['recovery_required']]
            self.assertEqual(len(complete), 2)
            self.assertFalse(old[0].exists())
            for directory in pending:
                self.assertEqual((directory/'before.bin').read_bytes(), b'private fixture backup')

    def test_completed_refusal_is_trimmed_after_it_is_recorded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(8):
                directory, _ = self.record(root, str(index), stage='failed')
                os.utime(directory, (installer.time.time()+index+1,)*2)
            current, record = self.record(root, 'current', stage='failed')
            installer.trim_finished_history(record, current/'transaction.json')
            self.assertEqual(len(list(root.glob('*/transaction.json'))), 8)
            self.assertTrue(current.exists())

    def test_cleanup_failure_does_not_replace_the_completed_flash_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory, record = self.record(Path(temporary), 'current')
            with patch.object(installer, 'prune_transactions', side_effect=PermissionError('/private/path')):
                installer.trim_finished_history(record, directory/'transaction.json')
            self.assertEqual(record['stage'], 'complete')
            self.assertFalse(record['recovery_required'])
            self.assertIn('retention_warning', record)
            self.assertNotIn('/private/path', record['retention_warning'])
            self.assertTrue((directory/'before.bin').exists())

    def test_pending_and_erase_results_never_trigger_finished_cleanup(self):
        for values in (dict(recovery_required=True), dict(operation='erase'), dict(record_write_failed=True)):
            record = dict(operation='upgrade', recovery_required=False)
            record.update(values)
            with self.subTest(values=values), patch.object(installer, 'prune_transactions') as prune:
                installer.trim_finished_history(record, Path('/unused/transaction.json'))
                prune.assert_not_called()


class EraseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.board = dict(serial=SERIAL, mode='bootsel', parent='same-port', ports={})
        self.flash = bytearray(b'\x5a' * installer.FLASH_SIZE)
        self.calls = []
        self.fault = None
        test = self

        class Tool:
            identity = {'version': 'fixture', 'sha256': 'a' * 64}
            def __init__(self, _): pass
            def read_flash(self, *_): raise AssertionError('Erase must not copy old credentials')
            def run(self, serial, *args, **_):
                test.assertEqual(serial, SERIAL)
                test.calls.append(args)
                if args[0] == 'info':
                    return (' type: ' + ('RP2040' if test.fault == 'chip' else 'RP2350') +
                            '\n chipid: 0x' + ('0' * 16 if test.fault == 'identity' else serial.lower()) +
                            ('\n' if test.fault == 'unknown_size' else
                             '\n flash size: ' + ('2048K' if test.fault == 'size' else '4096K') + '\n'))
                if args[0] == 'erase':
                    test.assertEqual(args, ('erase', '-r', '0x10000000', '0x10400000'))
                    record = next(value for p in test.root.glob('*/transaction.json')
                                  if (value := installer.decode(p.read_bytes())).get('operation') == 'erase'
                                  and value.get('stage') == 'erasing')
                    test.assertEqual(record['stage'], 'erasing')
                    test.assertTrue(record['recovery_required'])
                    test.flash[:] = b'\xff' * installer.FLASH_SIZE
                    if test.fault == 'partial': test.flash[-1] = 0  # Includes the E10 sector.
                    if test.fault == 'disconnect': raise installer.Refusal('USB disconnected during erase')
                    if test.fault == 'port': test.board['parent'] = 'changed-port'
                    return ''
                if args[0] == 'verify':
                    test.assertEqual(args[2:], ('-t', 'bin', '-o', '0x10000000'))
                    expected = args[1].read_bytes()
                    test.assertEqual(expected, b'\xff' * installer.FLASH_SIZE)
                    if test.fault == 'verify' or expected != test.flash:
                        raise installer.Refusal('Full flash comparison failed')
                    return ''
                raise AssertionError(args)

        self.context = contextlib.ExitStack()
        self.context.enter_context(patch.object(installer, 'Picotool', Tool))
        self.context.enter_context(patch.object(installer, 'discover', side_effect=lambda: [self.board]))
        self.context.enter_context(patch.object(installer, 'device_lock', lambda _: contextlib.nullcontext()))
        self.context.enter_context(patch.object(installer, 'private_directory', return_value=self.root))
        self.context.enter_context(patch.object(installer, 'Https', side_effect=AssertionError('Erase must work offline')))
        self.args = SimpleNamespace(device=SERIAL, yes=True, board='pico2_w', state_dir=self.root, picotool='fixture')

    def tearDown(self):
        self.context.close()
        self.temp.cleanup()

    def cli(self, arguments):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = installer.main(arguments)
        return code, json.loads(out.getvalue())

    def test_cli_erases_and_verifies_all_flash_without_network_or_backup(self):
        code, result = self.cli(['erase', '--device', SERIAL, '--board', 'pico2_w', '--yes'])
        self.assertEqual(code, 0)
        self.assertTrue(result['erase_verified'])
        self.assertEqual(result['erased_bytes'], installer.FLASH_SIZE)
        self.assertEqual(result['stage'], 'complete')
        self.assertFalse(result['recovery_required'])
        self.assertEqual(self.flash, b'\xff' * installer.FLASH_SIZE)
        self.assertEqual([c[0] for c in self.calls], ['info', 'erase', 'verify'])
        self.assertEqual({p.name for p in Path(result['transaction']).parent.iterdir()}, {'transaction.json', 'blank.bin'})

    def test_confirmation_and_image_selectors_refuse_before_usb(self):
        for extra in ([], ['--device', SERIAL], ['--device', SERIAL, '--yes'],
                      ['--device', SERIAL, '--board', 'pico2_w'],
                      ['--device', SERIAL, '--board', 'pico2_w', '--yes', '--version', 'anything'],
                      ['--device', SERIAL, '--board', 'pico2_w', '--yes', '--bundle', '/unused']):
            with self.subTest(extra=extra):
                code, result = self.cli(['erase', *extra])
                self.assertEqual(code, 2)
                self.assertFalse(result['recovery_required'])
                self.assertFalse(self.calls)

    def test_erase_retains_old_host_backups_beyond_normal_retention_limits(self):
        backups=[]
        for index in range(4):
            directory=self.root/(SERIAL+'-old-'+str(index));directory.mkdir()
            (directory/'transaction.json').write_bytes(encoded(dict(schema='wsprrypico-usb-transaction/1',
                serial=SERIAL,stage='complete',recovery_required=False)))
            backup=directory/'before.bin';backup.write_bytes(b'private fixture backup');backups.append(backup)
            os.utime(directory,(1,1))
        code,result=self.cli(['erase','--device',SERIAL,'--board','pico2_w','--yes'])
        self.assertEqual(code,0);self.assertTrue(result['erase_verified'])
        self.assertTrue(all(p.read_bytes()==b'private fixture backup' for p in backups))

    def test_wrong_chip_and_identity_never_erase(self):
        for self.fault in ('chip', 'identity'):
            with self.subTest(fault=self.fault), self.assertRaises(installer.TransactionFailure):
                installer.erase_transaction(self.args)
        self.assertTrue(all(c[0] == 'info' for c in self.calls))
        self.assertEqual(self.flash[0], 0x5a)

    def test_uniform_blank_and_content_size_guesses_do_not_block_confirmed_board_erase(self):
        for initial in (0x5a, 0xff):
            self.flash[:]=bytes([initial])*installer.FLASH_SIZE
            self.fault='unknown_size'
            result=installer.erase_transaction(self.args)
            self.assertTrue(result['erase_verified'])
            self.assertEqual(self.flash,b'\xff'*installer.FLASH_SIZE)
        self.fault='size'  # A content-derived 2048K guess is not geometry.
        self.assertTrue(installer.erase_transaction(self.args)['erase_verified'])

    def test_missing_durable_intent_never_authorizes_erase(self):
        real_save = installer.save_json
        def fail_intent(path, record):
            if record['stage'] == 'erasing': raise OSError('Intent could not be saved')
            return real_save(path, record)
        with patch.object(installer, 'save_json', side_effect=fail_intent), self.assertRaises(installer.TransactionFailure):
            installer.erase_transaction(self.args)
        self.assertEqual([c[0] for c in self.calls], ['info'])
        self.assertEqual(self.flash[0], 0x5a)

    def test_partial_erase_last_byte_and_disconnection_never_report_success(self):
        for self.fault in ('partial', 'disconnect', 'verify', 'port'):
            self.board['parent'] = 'same-port'
            with self.subTest(fault=self.fault):
                code, result = self.cli(['erase', '--device', SERIAL, '--board', 'pico2_w', '--yes'])
                self.assertEqual(code, 3)
                self.assertFalse(result['erase_verified'])
                self.assertTrue(result['recovery_required'])
                self.assertEqual(result['stage'], 'failed')

    def test_failed_erase_recovers_on_same_board_and_port_without_image_or_backup(self):
        self.fault = 'partial'
        with self.assertRaises(installer.TransactionFailure) as caught:
            installer.erase_transaction(self.args)
        self.args.transaction = Path(caught.exception.result['transaction'])
        self.fault = None
        self.board['parent'] = 'other-port'
        with self.assertRaises(installer.TransactionFailure): installer.recover_transaction(self.args)
        self.board['parent'] = 'same-port'
        result = installer.recover_transaction(self.args)
        self.assertTrue(result['erase_verified'])
        self.assertFalse(result['recovery_required'])

    def test_running_application_only_prepares_manual_handoff_and_requires_disabled_schedule(self):
        self.board['mode'] = 'application'
        snapshot = {'target': {'device_id': installer.device_id(SERIAL)}, 'config': {'config': {'enabled': False}}}
        with patch.object(installer, 'public_snapshot', return_value=snapshot), \
             patch.object(installer, 'admit_snapshot') as admission:
            result = installer.erase_transaction(self.args)
            admission.assert_called_once_with(snapshot)
            self.assertTrue(result['manual_bootsel_required'])
            self.assertEqual(result['stage'], 'awaiting_bootsel')
            self.assertFalse(self.calls)
            self.assertFalse(list(self.root.glob('*/blank.bin')))
            snapshot['config']['config']['enabled'] = True
            with self.assertRaises(installer.Refusal): installer.erase_transaction(self.args)
        self.board['mode'] = 'bootsel'
        self.args.transaction = Path(result['transaction'])
        self.assertTrue(installer.recover_transaction(self.args)['erase_verified'])


class InteractiveSelectionTests(unittest.TestCase):
    OTHER = '2545B6EFBF78028C'

    class Terminal(io.StringIO):
        def isatty(self):
            return True

    def invoke(self, arguments=None, answer='1\n', fresh=None, human=True, tty=True, open_error=None, boards=None):
        boards = [dict(serial=self.OTHER, mode='bootsel', parent='1-1.4', ports={}),
                  dict(serial=SERIAL, mode='application', parent='1-1.3', ports={})] if boards is None else boards
        terminal = self.Terminal(answer) if isinstance(answer, str) else answer
        messages = self.Terminal() if tty else io.StringIO()
        net = Network('main')
        def transaction(args, *_):
            return dict(stage='complete', serial=args.device, preserved=True, recovery_required=False)
        with patch.object(installer, 'open', return_value=terminal, side_effect=open_error, create=True) as opened, \
             patch.object(installer, 'discover', side_effect=[boards, boards if fresh is None else fresh]) as discovery, \
             patch.object(installer, 'Https', return_value=net) as network, \
             patch.object(installer, 'prepare_standalone_picotool', return_value=None) as tools, \
             patch.object(installer, 'transaction', side_effect=transaction) as programming, \
             patch.object(installer, 'Picotool', side_effect=AssertionError('Real USB tool opened')), \
             patch.object(installer, 'public_snapshot', side_effect=AssertionError('Unselected USB device opened')), \
             contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(messages):
            code = installer.main(['upgrade', '--board', 'pico2_w', '--yes'] if arguments is None else arguments, human=human)
        return SimpleNamespace(code=code, result=json.loads(output.getvalue()), messages=messages.getvalue(),
                               opened=opened, discovery=discovery, network=network, programming=programming, tools=tools)

    def refused(self, result):
        self.assertEqual(result.code, 2)
        self.assertFalse(result.result['ok'])
        self.assertFalse(result.result['recovery_required'])
        result.network.assert_not_called()
        result.programming.assert_not_called()

    def test_menu_orders_serials_and_passes_only_chosen_device_to_preserving_transaction(self):
        result = self.invoke()
        self.assertEqual(result.code, 0)
        self.assertTrue(result.result['preserved'])
        self.assertEqual(result.result['serial'], SERIAL)
        self.assertIn('1. USB ' + SERIAL, result.messages)
        self.assertIn('2. USB ' + self.OTHER, result.messages)
        self.assertIn('Running firmware; USB port 1-1.3', result.messages)
        self.assertIn('BOOTSEL; USB port 1-1.4', result.messages)
        self.assertIn('Selected Pico ' + SERIAL, result.messages)
        self.assertEqual(result.discovery.call_count, 2)
        result.opened.assert_called_once_with('/dev/tty', encoding='utf-8')
        args = result.programming.call_args.args[0]
        self.assertEqual((args.operation, args.board, args.yes, args.device), ('upgrade', 'pico2_w', True, SERIAL))
        self.assertEqual(args.selected_parent, '1-1.3')
        self.assertEqual(args.selected_mode, 'application')

    def test_bootsel_upgrade_refuses_before_tool_setup_network_or_transaction(self):
        for arguments, answer in ((None, '2\n'),
                                  (['upgrade', '--device', self.OTHER, '--board', 'pico2_w', '--yes'], '')):
            with self.subTest(arguments=arguments):
                result = self.invoke(arguments, answer=answer)
                self.refused(result)
                result.tools.assert_not_called()
                self.assertEqual(result.result['error_code'], 'device_mode_mismatch')
                self.assertEqual(result.result['observed_mode'], 'bootsel')
                for detail in ('install instead of upgrade', 'existing saved data', 'without holding BOOTSEL', 'recover command'):
                    self.assertIn(detail, result.result['error'])

    def test_invalid_choices_repeat_without_default_selection(self):
        result = self.invoke(answer='0\n99\n-1\nabc\n' + '9' * 5000 + '\n1\n')
        self.assertEqual(result.result['serial'], SERIAL)
        self.assertEqual(result.messages.count('Enter one of the listed numbers'), 5)
        result.programming.assert_called_once()

    def test_install_menu_selects_bootsel_board_and_preserves_existing_guidance(self):
        result = self.invoke(['install', '--board', 'pico2_w', '--yes'], answer='2\n')
        self.assertEqual(result.code, 0)
        self.assertEqual(result.result['serial'], self.OTHER)
        self.assertIn('Select the Pico to install:', result.messages)
        self.assertIn('The selected Pico is in BOOTSEL', result.messages)

    def test_install_on_running_firmware_explains_preserving_upgrade_without_downloading(self):
        result = self.invoke(['install', '--board', 'pico2_w', '--yes'])
        self.refused(result)
        result.tools.assert_not_called()
        self.assertIn('upgrade instead of install', result.result['error'])

    def test_cancel_empty_eof_and_interrupt_never_start_firmware_work(self):
        class Interrupted(self.Terminal):
            def readline(self, *_):
                raise KeyboardInterrupt
        for answer in ('\n', 'q\n', 'Q\n', '', Interrupted()):
            with self.subTest(answer=repr(answer)):
                result = self.invoke(answer=answer)
                self.refused(result)
                self.assertIn('selection cancelled; no firmware was written', result.result['error'])

    def test_missing_terminal_or_boards_refuse_with_actionable_reason(self):
        for kwargs, reason in ((dict(tty=False), '--device SERIAL'),
                               (dict(open_error=OSError('no controlling terminal')), '--device SERIAL'),
                               (dict(boards=[]), 'No supported USB Pico')):
            with self.subTest(kwargs=kwargs):
                result = self.invoke(**kwargs)
                self.refused(result)
                self.assertIn(reason, result.result['error'])

    def test_changed_or_disconnected_choice_never_falls_back_to_another_board(self):
        for fresh in ([dict(serial=self.OTHER, mode='bootsel', parent='1-1.4', ports={})],
                      [dict(serial=SERIAL, mode='application', parent='other-port', ports={})],
                      [dict(serial=SERIAL, mode='bootsel', parent='1-1.3', ports={})]):
            with self.subTest(fresh=fresh):
                self.refused(self.invoke(fresh=fresh))

    def test_device_change_during_image_resolution_refuses_under_lock_before_transaction(self):
        files, manifest, _ = fixture('main', modern=True)
        image = installer.verify_bundle(files, 'main')[1]
        for operation, mode in (('install', 'bootsel'), ('upgrade', 'application')):
            board = dict(serial=SERIAL, mode=mode, parent='1-1.3', ports={})
            other_mode = dict(board, mode='application' if mode == 'bootsel' else 'bootsel')
            for menu_board, changed in ((board, []), (board, [dict(board, parent='1-1.7')]),
                                        (board, [other_mode]), (other_mode, [board])):
                with self.subTest(operation=operation, menu_board=menu_board, changed=changed):
                    state = {'resolved': False, 'locked': False}
                    def resolve(*_):
                        state['resolved'] = True
                        return files, manifest, image
                    @contextlib.contextmanager
                    def lock(serial):
                        self.assertEqual(serial, SERIAL)
                        state['locked'] = True
                        try:
                            yield
                        finally:
                            state['locked'] = False
                    def discover():
                        if state['resolved']:
                            self.assertTrue(state['locked'])
                            return changed
                        return [menu_board]
                    with patch.object(installer, 'open', return_value=self.Terminal('1\n'), create=True), \
                         patch.object(installer, 'discover', side_effect=discover), \
                         patch.object(installer, 'resolve', side_effect=resolve), \
                         patch.object(installer, 'recent_ci', return_value={}), \
                         patch.object(installer, 'device_lock', side_effect=lock), \
                         patch.object(installer, 'Picotool'), \
                         patch.object(installer, 'private_directory', side_effect=AssertionError('Transaction created')) as private, \
                         patch.object(installer, 'public_snapshot', side_effect=AssertionError('USB opened')) as snapshot, \
                         contextlib.redirect_stderr(self.Terminal()), \
                         contextlib.redirect_stdout(io.StringIO()) as output:
                        code = installer.main([operation, '--board', 'pico2_w', '--yes'], human=True)
                    result = json.loads(output.getvalue())
                    self.assertEqual(code, 2)
                    self.assertFalse(result['ok'])
                    self.assertFalse(result['recovery_required'])
                    private.assert_not_called()
                    snapshot.assert_not_called()

    def test_single_board_still_requires_deliberate_selection(self):
        board = dict(serial=SERIAL, mode='application', parent='1-1.3', ports={})
        self.refused(self.invoke(boards=[board], answer='\n'))
        self.assertEqual(self.invoke(boards=[board], answer='1\n').result['serial'], SERIAL)

    def test_imported_and_json_only_entry_points_never_open_terminal(self):
        for kwargs in (dict(human=False), dict(arguments=['upgrade', '--board', 'pico2_w', '--yes', '--json-only'])):
            with self.subTest(kwargs=kwargs):
                result = self.invoke(**kwargs)
                self.refused(result)
                result.opened.assert_not_called()
                result.discovery.assert_not_called()
                self.assertEqual(result.messages, '')

    def test_explicit_device_bypasses_menu_in_all_entry_points(self):
        for human, extra in ((True, []), (False, []), (True, ['--json-only'])):
            with self.subTest(human=human, extra=extra):
                result = self.invoke(['upgrade', '--device', SERIAL, '--board', 'pico2_w', '--yes', *extra], human=human)
                self.assertEqual(result.code, 0)
                self.assertEqual(result.result['serial'], SERIAL)
                result.opened.assert_not_called()
                self.assertEqual(result.discovery.call_count, 1)
                self.assertEqual(result.messages, '')

    def test_board_and_operation_confirmation_are_required_before_menu(self):
        for arguments in (['upgrade', '--board', 'pico2_w'], ['upgrade', '--yes']):
            with self.subTest(arguments=arguments):
                result = self.invoke(arguments)
                self.refused(result)
                result.opened.assert_not_called()

    def test_read_only_and_explicit_recovery_or_erase_commands_never_offer_menu(self):
        for operation in ('discover', 'plan', 'snapshot', 'recover', 'erase'):
            with self.subTest(operation=operation):
                result = self.invoke([operation])
                result.opened.assert_not_called()
                self.assertNotIn('Choose 1-', result.messages)
                result.programming.assert_not_called()
                self.assertEqual(result.code, 0 if operation in ('discover', 'plan') else 2)


class StandaloneGuidanceTests(unittest.TestCase):
    def waiting(self):
        return dict(operation='upgrade', stage='awaiting_bootsel', manual_bootsel_required=True,
                    recovery_required=True, serial=SERIAL, transaction='/private/fixture/transaction.json')

    def invoke(self, record, operation='upgrade', failure=False, human=True, extra=(), messages=None, terminal_output=False):
        messages = io.StringIO() if messages is None else messages
        stdout = InteractiveSelectionTests.Terminal() if terminal_output else io.StringIO()
        with tempfile.NamedTemporaryFile() as transaction, \
             patch.object(installer, 'selected', return_value=dict(serial=SERIAL, mode='bootsel' if operation == 'install' else 'application', parent='1-1.3')), \
             patch.object(installer, 'Https', return_value=Network('main')), \
             patch.object(installer, 'prepare_standalone_picotool', return_value=None), \
             patch.object(installer, 'transaction', return_value=record,
                          side_effect=installer.TransactionFailure('not ready', record, Path(record['transaction'])) if failure else None), \
             patch.object(installer, 'recover_transaction', return_value=record,
                          side_effect=installer.TransactionFailure('not ready', record, Path(record['transaction'])) if failure else None), \
             contextlib.redirect_stdout(stdout) as output, \
             contextlib.redirect_stderr(messages):
            recovery = ['--transaction', transaction.name] if operation == 'recover' else []
            status = installer.main([operation, '--device', SERIAL, '--board', 'pico2_w', '--yes', *recovery, *extra], human=human)
        expected = {**record, 'schema':'wsprrypico-usb-result/1', 'installer_version':installer.INSTALLER_VERSION,
                    'ok':not failure}
        if failure:
            expected['error'] = 'not ready'
        if terminal_output and human and '--json-only' not in extra and messages.isatty():
            self.assertEqual(output.getvalue(), '')
            self.assertNotIn('wsprrypico-usb-result/1', messages.getvalue())
        else:
            self.assertEqual(output.getvalue(), json.dumps(expected, sort_keys=True) + '\n')
        self.assertEqual(status, 3 if failure else 0)
        return messages.getvalue()

    def test_waiting_upgrade_explains_reconnect_and_continuation(self):
        messages = self.invoke(self.waiting())
        for detail in ('no firmware has been written', SERIAL, 'Unplug', 'Hold BOOTSEL',
                       'same physical USB port', 'Release BOOTSEL', 'do not edit its settings',
                       'recover', '--transaction /private/fixture/transaction.json', '--yes',
                       'Keep USB connected until programming and verification finish'):
            self.assertIn(detail, messages)

    def test_terminal_success_waiting_and_failure_are_distinct_without_raw_json(self):
        cases = ((dict(operation='upgrade', stage='complete', serial=SERIAL, version='1.0.0-beta.1',
                       preserved=True, recovery_required=False), False, 'Firmware verified'),
                 (self.waiting(), False, 'Action required'),
                 (dict(self.waiting(), stage='failed', failure_stage='programming', program_authorized=True),
                  True, 'Unable to continue'))
        for record, failure, expected in cases:
            with self.subTest(stage=record['stage']):
                messages = self.invoke(record, failure=failure, terminal_output=True,
                                       messages=InteractiveSelectionTests.Terminal())
                self.assertIn(expected, messages)
                if record['stage'] != 'complete':
                    self.assertNotIn('Firmware verified', messages)
                    self.assertIn('recover --transaction', messages)
                if failure:
                    self.assertNotIn('no firmware has been written', messages)

    def test_terminal_sections_have_blank_lines_before_and_after_headings(self):
        record = dict(stage='complete', serial=SERIAL, version='1.0.0-beta.1',
                      preserved=True, recovery_required=False)
        messages = self.invoke(record, operation='install', terminal_output=True,
                               messages=InteractiveSelectionTests.Terminal())
        self.assertTrue(messages.startswith('\nWsprryPico USB installer\n\n'))
        for heading in ('Check USB programming tools', 'Check firmware',
                        'Install firmware', 'Firmware verified'):
            with self.subTest(heading=heading):
                self.assertIn('\n\n' + heading + '\n\n', messages)

    def test_json_only_and_imported_results_stay_json_even_when_stdout_is_a_terminal(self):
        for kwargs in (dict(extra=['--json-only']), dict(human=False)):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.invoke(self.waiting(), terminal_output=True,
                    messages=InteractiveSelectionTests.Terminal(), **kwargs), '')

    def test_preflight_refusal_does_not_invent_pending_recovery_for_tool_cleanup(self):
        cleanup = []
        manager = SimpleNamespace(cleanup=lambda args, pending: cleanup.append(pending), close=lambda: None)
        with patch.object(installer, 'selected', return_value=dict(serial=SERIAL, mode='application', parent='1-1.3')), \
             patch.object(installer, 'Https', return_value=Network('main')), \
             patch.object(installer, 'prepare_standalone_picotool', return_value=manager), \
             patch.object(installer, 'transaction', side_effect=installer.Refusal('preflight refused')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            code = installer.main(['upgrade', '--device', SERIAL, '--board', 'pico2_w', '--yes'], human=True)
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(output.getvalue())['recovery_required'])
        self.assertEqual(cleanup, [False])

    def test_failed_pending_continuation_keeps_retry_guidance(self):
        record = dict(self.waiting(), stage='failed', failure_stage='awaiting_bootsel')
        messages = self.invoke(record, operation='recover', failure=True)
        self.assertIn('BOOTSEL reconnect required', messages)
        self.assertIn('recover --transaction', messages)
        self.assertNotIn('installation complete', messages.lower())

    def test_programming_failure_offers_bootsel_recovery_without_untouched_claim(self):
        record = dict(self.waiting(), stage='failed', failure_stage='programming',
                      program_authorized=True, manual_bootsel_required=False)
        messages = self.invoke(record, failure=True)
        self.assertIn('Installation is incomplete', messages)
        self.assertIn('BOOTSEL recovery is required', messages)
        self.assertIn('Hold BOOTSEL', messages)
        self.assertIn('recover --transaction', messages)
        self.assertNotIn('no firmware has been written', messages)

    def test_verification_failure_preserves_hold_and_offers_retry_without_unplug(self):
        for stage in ('launching_verification_boot', 'application_verified_maintenance_held',
                      'verification_release_requested'):
            with self.subTest(stage=stage):
                record = dict(self.waiting(), stage='failed', failure_stage=stage,
                              program_authorized=True, manual_bootsel_required=False)
                messages = self.invoke(record, operation='recover', failure=True)
                self.assertIn('Keep Pico ' + SERIAL + ' connected', messages)
                self.assertIn('recover --transaction', messages)
                self.assertNotIn('Unplug', messages)
                self.assertNotIn('Hold BOOTSEL', messages)

    def test_imported_main_and_json_only_remain_quiet(self):
        self.assertEqual(self.invoke(self.waiting(), human=False), '')
        self.assertEqual(self.invoke(self.waiting(), extra=['--json-only']), '')
        self.assertEqual(self.invoke(self.waiting(), operation='install', extra=['--json-only']), '')

    def test_modern_complete_and_unrelated_failure_do_not_request_reconnect(self):
        self.assertEqual(self.invoke(dict(stage='complete', serial=SERIAL)), '')
        for record in (dict(self.waiting(), manual_bootsel_required=False),
                       dict(self.waiting(), program_authorized=True),
                       dict(self.waiting(), stage='failed', failure_stage='launching_verification_boot')):
            with self.subTest(record=record):
                self.assertEqual(self.invoke(record), '')

    def test_initial_install_confirms_ready_board_and_keeps_json_result(self):
        messages = self.invoke(dict(stage='complete', serial=SERIAL), operation='install')
        for detail in ('The selected Pico is in BOOTSEL', 'Keep USB connected', 'Existing saved data will stop'):
            self.assertIn(detail, messages)
        self.assertNotIn('Hold BOOTSEL', messages)
        self.assertNotIn('recover --transaction', messages)

    def test_disconnected_stderr_cannot_change_result_or_exit_status(self):
        class Disconnected(io.StringIO):
            def write(self, text):
                raise BrokenPipeError('terminal closed')
        for failure in (False, True):
            with self.subTest(failure=failure):
                record = dict(self.waiting(), stage='failed', failure_stage='awaiting_bootsel') if failure else self.waiting()
                self.invoke(record, failure=failure, messages=Disconnected())

    def test_command_formatting_failure_cannot_replace_json_result(self):
        for failure in (False, True):
            with self.subTest(failure=failure), \
                 patch.object(installer, 'continuation_command', side_effect=OSError('directory unavailable')):
                record = dict(self.waiting(), stage='failed', failure_stage='awaiting_bootsel') if failure else self.waiting()
                self.assertEqual(self.invoke(record, failure=failure), '')

    def test_local_continuation_executes_literal_arguments_and_custom_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            hostile = "with spaces ' \" $HOME $(touch INJECTED) `touch INJECTED`;"
            script = root / (hostile + '.py')
            script.write_text('import json,sys\nprint(json.dumps(sys.argv[1:]))\n')
            state = root / hostile / 'state'
            transaction = state / 'transaction.json'
            tool = 'tools/' + hostile + '/picotool'
            args = SimpleNamespace(picotool=tool, state_dir=state)
            record = dict(self.waiting(), transaction=str(transaction))
            with patch.object(installer, '__file__', str(script)), \
                 patch.dict(os.environ, {'WSPRRY_PICO_USB_INSTALLER_REVISION':''}):
                command = installer.continuation_command(args, record)
            result = subprocess.run(['bash', '-c', command], cwd=root, text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), ['recover', '--transaction', str(transaction),
                '--device', SERIAL, '--board', 'pico2_w', '--yes', '--picotool=' + str(Path(tool).absolute()),
                '--state-dir', str(state)])
            self.assertFalse((root / 'INJECTED').exists())

    def test_leading_dash_tool_name_reaches_recovery_parser(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = SimpleNamespace(picotool='--custom-picotool', state_dir=root)
            record = dict(self.waiting(), transaction=str(root / 'missing' / 'transaction.json'))
            with patch.dict(os.environ, {'WSPRRY_PICO_USB_INSTALLER_REVISION':''}):
                command = installer.continuation_command(args, record)
            result = subprocess.run(['bash', '-c', command], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Select an existing private transaction.json', json.loads(result.stdout)['error'])
        self.assertEqual(result.stderr, '')

    def test_unvalidated_bootstrap_revision_cannot_enter_command(self):
        args = SimpleNamespace(picotool='picotool', state_dir=Path('/private/state'))
        with patch.dict(os.environ, {'WSPRRY_PICO_USB_INSTALLER_REVISION':'$(touch INJECTED)'}):
            command = installer.continuation_command(args, self.waiting())
        self.assertNotIn('curl', command)
        self.assertNotIn('INJECTED', command)
        self.assertEqual(shlex.split(command)[:2], [sys.executable, str(Path(installer.__file__).resolve())])

    def bootstrap_fixture(self, root):
        revision = 'a' * 40
        tools = root / 'tools'; tools.mkdir()
        source = root / 'source'; source.mkdir()
        (source / 'install_usb.sh').write_bytes((ROOT / 'scripts/install_usb.sh').read_bytes())
        record = dict(self.waiting(), transaction=str(root / "private ' $HOME $(touch INJECTED) `touch INJECTED`" / 'transaction.json'))
        Path(record['transaction']).parent.mkdir()
        Path(record['transaction']).write_text('{}')
        _, manifest, proof = fixture('main')
        overrides = (f"\n    resolve = lambda *a: ({{'ci-publication.json':{encoded(proof)!r}}}, {manifest!r}, b'')\n"
                     f"    discover = lambda: [dict(serial={SERIAL!r}, mode='application', parent='1-1.3', ports={{}})]\n"
                     "    prepare_standalone_picotool = lambda args: None\n"
                     "    recent_ci = lambda *a: {}\n"
                     f"    transaction = lambda *a: {record!r}\n"
                     "    def recover_transaction(args):\n"
                     "        print(json.dumps(vars(args), default=str), file=sys.stderr)\n"
                     "        return {'stage':'complete'}\n")
        core = (ROOT / 'scripts/usb_installer.py').read_text().replace(
            "if __name__ == '__main__':\n", "if __name__ == '__main__':\n" + overrides)
        (source / 'usb_installer.py').write_text(core)
        (source / 'release-manifest-1.schema.json').write_text('{}')
        curl = tools / 'curl'
        curl.write_text('#!' + sys.executable + '\n' +
            'import json,os,sys\nfrom pathlib import Path\n'
            'url=sys.argv[-1]\n'
            'with open(os.environ["CURL_LOG"],"a") as log: log.write(url+"\\n")\n'
            'if os.environ.get("CURL_FAIL"): sys.exit(22)\n'
            'if url.endswith("commits/devel"): print(json.dumps({"sha":"' + revision + '"}))\n'
            'else: sys.stdout.buffer.write((Path(os.environ["CURL_SOURCE"])/url.rsplit("/",1)[-1]).read_bytes())\n')
        curl.chmod(0o700)
        temporary = root / 'temporary'; temporary.mkdir()
        environment = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'],
                           CURL_LOG=str(root / 'curl.log'), CURL_SOURCE=str(source), TMPDIR=str(temporary),
                           WSPRRY_PICO_USB_INSTALLER_REVISION='')
        return environment, revision, record, temporary

    @unittest.skipIf(os.geteuid() == 0, 'Bootstrap requires an ordinary user')
    def test_piped_bootstrap_uses_terminal_selection_and_formats_terminal_or_redirected_results(self):
        # Feed Bash's script through stdin while the operator answers /dev/tty.
        # Public downloads and programming are substituted; no USB is opened.
        for columns, answer, stdout_tty in ((100, b'bad\n1\n', False), (40, b'\n', False),
                                            (100, b'1\n', True), (40, b'2\n', True)):
            with self.subTest(columns=columns, stdout_tty=stdout_tty), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                environment, _, _, downloads = self.bootstrap_fixture(root)
                core = root / 'source/usb_installer.py'
                devices = [dict(serial=SERIAL, mode='application', parent='1-1.3', ports={}),
                           dict(serial=InteractiveSelectionTests.OTHER, mode='bootsel', parent='1-1.4', ports={})]
                core.write_text(core.read_text().replace('    sys.exit(main(human=True))',
                    f'    discover = lambda: {devices!r}\n'
                    "    transaction = lambda args, *a: dict(stage='complete', serial=args.device, preserved=True, recovery_required=False)\n"
                    '    sys.exit(main(human=True))'))
                master, slave = pty.openpty()
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('4H', 24, columns, 0, 0))
                def claim_terminal():
                    os.setsid()
                    fcntl.ioctl(2, termios.TIOCSCTTY, 0)
                process = None
                try:
                    process = subprocess.Popen(['bash', '-s', '--', 'upgrade', '--board', 'pico2_w', '--yes'],
                        stdin=subprocess.PIPE, stdout=slave if stdout_tty else subprocess.PIPE, stderr=slave,
                        cwd=root, env=environment, preexec_fn=claim_terminal)
                    os.close(slave)
                    slave = None
                    process.stdin.write((ROOT / 'scripts/install_usb.sh').read_bytes())
                    process.stdin.close()
                    process.stdin = None
                    transcript = bytearray()
                    deadline = time.monotonic() + 10
                    while b'press Enter to cancel: ' not in transcript:
                        self.assertLess(time.monotonic(), deadline, transcript.decode(errors='replace'))
                        if select.select([master], [], [], 0.1)[0]:
                            transcript.extend(os.read(master, 4096))
                    os.write(master, answer)
                    output = bytearray()
                    streams = {master: transcript}
                    if not stdout_tty:
                        streams[process.stdout.fileno()] = output
                    deadline = time.monotonic() + 10
                    # Drain both streams before wait(): macOS can hold a session
                    # leader in exit until its controlling PTY has been drained.
                    while streams:
                        self.assertLess(time.monotonic(), deadline, transcript.decode(errors='replace'))
                        for descriptor in select.select(list(streams), [], [], 0.1)[0]:
                            try:
                                data = os.read(descriptor, 4096)
                            except OSError as error:
                                if descriptor != master or error.errno != installer.errno.EIO:
                                    raise
                                data = b''
                            if data:
                                streams[descriptor].extend(data)
                            else:
                                del streams[descriptor]
                    os.close(master)
                    master = None
                    process.wait(timeout=5)
                    if not stdout_tty:
                        process.stdout.close()
                    text = transcript.decode()
                    result = None if stdout_tty else json.loads(output)
                    if stdout_tty:
                        self.assertEqual(output, b'')
                        self.assertNotIn('wsprrypico-usb-result/1', text)
                        self.assertIn('WsprryPico USB installer', text)
                    else:
                        self.assertEqual(len(output.splitlines()), 1)
                    self.assertIn('1. USB ' + SERIAL, text)
                    self.assertIn('2. USB ' + InteractiveSelectionTests.OTHER, text)
                    self.assertIn('Running firmware; USB port 1-1.3', text)
                    self.assertIn('BOOTSEL; USB port 1-1.4', text)
                    self.assertEqual(list(downloads.iterdir()), [])
                    if columns == 100:
                        self.assertEqual(process.returncode, 0, text)
                        if stdout_tty:
                            self.assertIn('Firmware verified', text)
                            self.assertIn('Check firmware', text)
                        else:
                            self.assertEqual(result['serial'], SERIAL)
                            self.assertTrue(result['preserved'])
                            self.assertIn('Enter one of the listed numbers', text)
                    else:
                        self.assertEqual(process.returncode, 2, text)
                        if stdout_tty:
                            self.assertIn('Unable to continue', text)
                            self.assertIn('First installation:', text)
                            self.assertNotIn('Check firmware', text)
                            self.assertNotIn('Firmware verified', text)
                        else:
                            self.assertFalse(result['recovery_required'])
                            self.assertIn('selection cancelled', result['error'])
                finally:
                    if master is not None:
                        os.close(master)
                    if process is not None and process.poll() is None:
                        process.kill()
                        process.communicate(timeout=5)
                    if slave is not None:
                        os.close(slave)

    @unittest.skipIf(os.geteuid() == 0, 'Bootstrap requires an ordinary user')
    def test_piped_bootstrap_continuation_survives_cleanup_and_pins_revision(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            environment, revision, record, downloads = self.bootstrap_fixture(root)
            first = subprocess.run(['bash', '-s', '--', 'upgrade', '--device', SERIAL, '--board', 'pico2_w',
                                    '--yes', '--picotool', "tools/custom ' picotool", '--state-dir', str(root / 'state')],
                input=(ROOT / 'scripts/install_usb.sh').read_text(), env=environment, cwd=root,
                text=True, capture_output=True, timeout=10)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(first.stdout)['stage'], 'awaiting_bootsel')
            self.assertEqual(list(downloads.iterdir()), [])
            command = next(line.strip() for line in first.stderr.splitlines() if line.startswith('  bash '))
            self.assertNotIn('wsprrypico-usb.', command)
            second = subprocess.run(['bash', '-c', command], env=environment, cwd=root,
                                    text=True, capture_output=True, timeout=10)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(json.loads(second.stdout)['stage'], 'complete')
            arguments = json.loads(next(line for line in second.stderr.splitlines() if line.startswith('{')))
            self.assertEqual(arguments['transaction'], record['transaction'])
            self.assertEqual(arguments['device'], SERIAL)
            self.assertEqual(arguments['board'], 'pico2_w')
            self.assertTrue(arguments['yes'])
            self.assertEqual(arguments['picotool'], str(root / "tools/custom ' picotool"))
            self.assertEqual(arguments['state_dir'], str(root / 'state'))
            urls = (root / 'curl.log').read_text().splitlines()
            self.assertEqual(sum(url.endswith('commits/devel') for url in urls), 1)
            self.assertTrue(all('/' + revision + '/' in url for url in urls if not url.endswith('commits/devel')))
            self.assertEqual(list(downloads.iterdir()), [])
            self.assertFalse((root / 'INJECTED').exists())
            failed = subprocess.run(['bash', '-c', command], env=dict(environment, CURL_FAIL='1'), cwd=root,
                                    text=True, capture_output=True, timeout=10)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(failed.stdout, '')

    @unittest.skipIf(os.geteuid() == 0, 'Bootstrap requires an ordinary user')
    def test_bootstrap_rejects_bad_revision_before_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            environment, _, _, downloads = self.bootstrap_fixture(root)
            environment['WSPRRY_PICO_USB_INSTALLER_REVISION'] = '$(touch INJECTED)'
            result = subprocess.run(['bash', '-s'], input=(ROOT / 'scripts/install_usb.sh').read_text(),
                                    env=environment, cwd=root, text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertIn('full lowercase Git commit SHA', result.stderr)
            self.assertFalse((root / 'curl.log').exists())
            self.assertFalse((root / 'INJECTED').exists())
            self.assertEqual(list(downloads.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
