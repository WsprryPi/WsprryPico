"""Behavioral installer failure tests: substitute network and the USB writer."""
import contextlib
import copy
from email.message import Message
import io
import json
import os
import shutil
from pathlib import Path
import struct
import sys
import tempfile
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


def fixture(branch='devel', modern=False):
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
    def __init__(self, branch='devel'):
        self.files, self.manifest, self.proof = fixture(branch)
        self.branch, self.calls = branch, []
        self.tag = self.manifest['intended_tag']
        self.index = dict(schema='wsprrypico-ci-index/1', repository=installer.REPOSITORY,
                          branch=branch, tag=self.tag, source=self.proof['source'],
                          version=self.proof['version'], run_id=self.proof['run_id'], attempt=self.proof['attempt'],
                          uf2=self.proof['uf2'], manifest_sha256=self.proof['manifest_sha256'])
        assets = dict(self.files, **{'audit.zip': b'audit', 'deployment.zip': b'deployment'})
        self.release = dict(tag_name=self.tag, draft=False, prerelease=True,
                            assets=[dict(name=n, state='uploaded', size=len(d), digest='sha256:' + installer.sha(d),
                                         browser_download_url=installer.DOWNLOAD + self.tag + '/' + n)
                                    for n, d in assets.items()])
        for artifact in self.proof['artifacts']:
            next(a for a in self.release['assets'] if a['name'] == artifact['kind'] + '.zip')['digest'] = 'sha256:' + artifact['archive_sha256']
        self.run = dict(status='completed', conclusion='success', head_sha=self.proof['source'],
                        head_branch=branch, path='.github/workflows/software-build.yml',
                        head_repository={'full_name': installer.REPOSITORY}, event='push', run_attempt=1)
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
        return self.files[url.rsplit('/', 1)[1]]


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

    def upgrade_transaction(self,mismatch=False,fault=False,declined=False,old_network_failure=False,recovery_retries=False,programming_recovery=False,migration=False,migration_failure=None):
        files,manifest,_=fixture(modern=True); image=b'A'*256+b'B'*256
        old_files,old_manifest,_=fixture() if migration else (files,manifest,None)
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
                 patch.object(installer, 'selected', return_value=dict(parent='fixture')):
                with self.assertRaises(installer.Refusal):
                    installer.transaction(args, files, manifest, image)
            record = json.loads(next(Path(temporary).glob('*/transaction.json')).read_text())
            self.assertEqual(record['stage'], 'failed')
            self.assertEqual(record['recovery_required'], failure == 'preservation')
            self.assertEqual(any(c[0] == 'load' for c in commands), failure == 'preservation')
            self.assertFalse(any(c[0] == 'reboot' for c in commands))
            self.assertNotIn('before.bin', json.dumps(record))


if __name__ == '__main__':
    unittest.main()
