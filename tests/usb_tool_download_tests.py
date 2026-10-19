"""Standalone prerequisite, download, cache and cleanup failure boundaries; no USB."""
import contextlib
import fcntl
import io
import json
import os
import pty
import select
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import termios
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import usb_installer as installer


def archive(tar=False):
    tool = ('#!' + sys.executable + '\nimport sys\n'
            'if sys.argv[1:] == ["version"]: print("picotool v2.3.1 (fixture)")\n'
            'elif sys.argv[1] == "help": print("-a -r -v -t -u -x -o --ser --ignore-partitions")\n'
            'else: raise RuntimeError("USB operation prohibited in this test")\n').encode()
    entries = [('picotool/picotool', tool), ('picotool/support.json', b'{"fixture":true}')]
    output = io.BytesIO()
    if tar:
        with tarfile.open(fileobj=output, mode='w:gz') as package:
            for name, data in entries:
                item = tarfile.TarInfo(name)
                item.size = len(data)
                package.addfile(item, io.BytesIO(data))
    else:
        with zipfile.ZipFile(output, 'w') as package:
            for name, data in entries:
                package.writestr(name, data)
    return output.getvalue()


class DownloadTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name).resolve()
        self.state = self.home / '.local/state/wsprrypico-usb'
        self.data = archive()
        self.args = SimpleNamespace(picotool=None, download_picotool=True, tool_cleanup='keep',
                                    json_only=True, state_dir=self.state)
        self.calls = []
        def get(url, limit):
            self.calls.append((url, limit))
            return self.data
        self.client = SimpleNamespace(get=get)
        original_which = shutil.which
        for mock in (patch.object(Path, 'home', return_value=self.home),
                     patch.object(installer, 'tool_platform', return_value='mac'),
                     patch.object(installer, 'TOOL_DOWNLOADS', {'mac': ('fixture.zip', len(self.data), installer.sha(self.data))}),
                     patch.object(installer, 'Https', return_value=self.client),
                     patch.object(installer.shutil, 'which', side_effect=lambda name: None if name == 'picotool' else original_which(name))):
            mock.start()
            self.addCleanup(mock.stop)

    def obtain(self):
        with contextlib.redirect_stderr(io.StringIO()):
            manager = installer.prepare_standalone_picotool(self.args)
        self.addCleanup(manager.close)
        return manager

    def cleanup(self, manager, pending=False, policy='remove'):
        self.args.tool_cleanup = policy
        with contextlib.redirect_stderr(io.StringIO()) as messages:
            manager.cleanup(self.args, pending)
        return messages.getvalue()

    def test_official_origin_integrity_capabilities_and_exact_support_files(self):
        manager = self.obtain()
        self.assertEqual(self.calls, [(installer.TOOL_ORIGIN + installer.TOOL_RELEASE + '/fixture.zip', len(self.data))])
        tool = installer.Picotool(self.args.picotool)
        self.assertIn('v2.3.1', tool.identity['version'])
        self.assertEqual(tool.identity['sha256'], installer.sha(Path(self.args.picotool).read_bytes()))
        self.assertEqual((manager.package/'picotool/support.json').read_bytes(), b'{"fixture":true}')
        self.assertFalse(list(manager.root.glob('.download-*')))

    def test_cache_reused_without_another_download(self):
        first = self.obtain()
        package = first.package
        first.close()
        self.args.picotool = None
        second = self.obtain()
        self.assertEqual(second.package, package)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(list(second.root.glob('?'*64))), 1)

    def test_existing_compatible_explicit_tool_is_untouched(self):
        executable = self.home/'existing-picotool'
        with zipfile.ZipFile(io.BytesIO(self.data)) as package:
            executable.write_bytes(package.read('picotool/picotool'))
        executable.chmod(0o700)
        before = executable.read_bytes()
        self.args.picotool = str(executable)
        manager = installer.prepare_standalone_picotool(self.args)
        self.assertIsNone(manager)
        self.assertEqual(self.calls, [])
        self.assertEqual(executable.read_bytes(), before)

    def test_missing_explicit_tool_never_downloads_a_fallback(self):
        self.args.picotool = str(self.home/'missing')
        with self.assertRaises(installer.Refusal): installer.prepare_standalone_picotool(self.args)
        self.assertEqual(self.calls, [])

    def test_invalid_nested_tool_path_never_cleans_user_copies(self):
        manager = self.obtain()
        original = manager.package
        user_files = manager.root/'user-files'
        user_files.mkdir(mode=0o700)
        copied = user_files/original.name
        shutil.copytree(original, copied)
        manager.close()
        self.args.picotool = str(copied/'picotool/picotool')
        self.args.tool_cleanup = 'remove'
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaisesRegex(installer.Refusal, 'Invalid managed picotool path'):
            installer.prepare_standalone_picotool(self.args)
        self.assertTrue((copied/'picotool/picotool').is_file())
        self.assertTrue(original.is_dir())

    def test_managed_tool_on_path_reports_runtime_failure_without_reacquiring_its_lock(self):
        manager = self.obtain()
        executable = self.args.picotool
        manager.close()
        self.args.picotool = None
        with patch.object(installer.shutil, 'which', return_value=executable), \
             patch.object(installer, 'Picotool', side_effect=installer.Refusal('runtime unavailable')), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaisesRegex(installer.Refusal, 'runtime unavailable'):
            installer.prepare_standalone_picotool(self.args)
        self.assertEqual(len(self.calls), 1)
        lease = installer.ManagedPicotool()
        lease.close()

    def test_unattended_missing_tool_needs_separate_download_consent(self):
        self.args.download_picotool = False
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaisesRegex(installer.Refusal, '--download-picotool'):
            installer.prepare_standalone_picotool(self.args)
        self.assertEqual(self.calls, [])
        self.assertFalse((self.home/'.cache').exists())

    def test_interactive_download_decline_never_fetches_or_creates_cache(self):
        self.args.download_picotool = self.args.json_only = False
        with patch.object(installer.sys.stderr, 'isatty', return_value=True), \
             patch.object(installer, 'terminal_confirm', return_value=False), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(installer.Refusal):
            installer.prepare_standalone_picotool(self.args)
        self.assertFalse(self.calls)
        self.assertFalse((self.home/'.cache').exists())

    def test_wrong_digest_or_size_never_extracts_or_executes(self):
        for payload in (self.data[:-1], b'X'+self.data[1:]):
            self.args.picotool = None
            with patch.object(self.client, 'get', return_value=payload), \
                 patch.object(installer, 'extract_picotool') as extract, \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaisesRegex(installer.Refusal, 'SHA-256'):
                installer.prepare_standalone_picotool(self.args)
            extract.assert_not_called()
        manager = installer.ManagedPicotool()
        manager.close()  # Failed preparation released the lock.

    def test_unrunnable_download_can_be_cleaned_without_replacing_the_original_error(self):
        self.args.tool_cleanup = 'remove'
        with patch.object(installer,'Picotool',side_effect=[installer.Refusal('missing'),installer.Refusal('runtime unavailable')]), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaisesRegex(installer.Refusal,'runtime unavailable'):
            installer.prepare_standalone_picotool(self.args)
        root = self.home/'.cache/wsprrypico-usb/tools'
        self.assertFalse(list(root.glob('?'*64)))
        self.assertFalse(list(root.glob('.download-*')))

    def test_failed_network_does_not_leave_partial_files_or_lock(self):
        with patch.object(self.client, 'get', side_effect=installer.Refusal('offline')), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaisesRegex(installer.Refusal, 'offline'):
            installer.prepare_standalone_picotool(self.args)
        manager = installer.ManagedPicotool()
        self.assertFalse(list(manager.root.glob('.download-*')))
        manager.close()

    def test_changed_binary_and_forged_local_receipt_are_refused(self):
        manager = self.obtain()
        executable = Path(self.args.picotool)
        executable.write_bytes(b'user work')
        receipt = json.loads((manager.package/'.tool.json').read_text())
        receipt['files']['picotool/picotool'] = installer.sha(b'user work')
        installer.save_json(manager.package/'.tool.json', receipt)
        with self.assertRaisesRegex(installer.Refusal, 'files changed'): manager.verify(manager.package)
        with self.assertRaises(installer.Refusal): self.cleanup(manager)
        self.assertEqual(executable.read_bytes(), b'user work')

    def test_changed_retained_archive_is_refused(self):
        manager = self.obtain()
        data = manager.package/'.archive'
        data.write_bytes(b'X'+data.read_bytes()[1:])
        with self.assertRaisesRegex(installer.Refusal, 'SHA-256'): manager.verify(manager.package)

    def test_added_user_file_prevents_cleanup(self):
        manager = self.obtain()
        added = manager.package/'my-notes.txt'
        added.write_text('retain me')
        added.chmod(0o600)
        with self.assertRaises(installer.Refusal): self.cleanup(manager)
        self.assertEqual(added.read_text(), 'retain me')

    def test_cleanup_removes_only_managed_package_and_keeps_private_backups(self):
        manager = self.obtain()
        transaction = self.state/'serial-complete'
        transaction.mkdir(mode=0o700)
        (transaction/'transaction.json').write_text('{"schema":"wsprrypico-usb-transaction/1","recovery_required":false}')
        (transaction/'before.bin').write_bytes(b'private saved settings')
        self.assertIn('Removed', self.cleanup(manager))
        self.assertFalse(manager.package.exists())
        self.assertEqual((transaction/'before.bin').read_bytes(), b'private saved settings')

    def test_pending_result_retains_tool_even_with_explicit_cleanup(self):
        manager = self.obtain()
        with patch.object(installer, 'terminal_confirm', side_effect=AssertionError('cleanup offered')):
            self.assertIn('retained', self.cleanup(manager, True))
        self.assertTrue(manager.package.exists())

    def test_other_nested_state_domain_pending_record_retains_tool(self):
        manager = self.obtain()
        old = self.state/'custom-state/serial-pending'
        old.mkdir(parents=True)
        (old/'transaction.json').write_text('{"schema":"wsprrypico-usb-transaction/1","recovery_required":true}')
        self.assertIn('retained', self.cleanup(manager))
        self.assertTrue(manager.package.exists())

    def test_unreadable_or_malformed_state_never_authorizes_cleanup(self):
        manager = self.obtain()
        bad = self.state/'serial-pending'
        bad.mkdir()
        (bad/'transaction.json').write_text('incomplete')
        with self.assertRaises(ValueError): self.cleanup(manager)
        with patch.object(installer.os, 'walk', side_effect=PermissionError('private state unreadable')):
            with self.assertRaises(PermissionError): self.cleanup(manager)
        self.assertTrue(manager.package.exists())

    def test_default_noninteractive_cleanup_keeps_tool_and_explicit_keep_never_prompts(self):
        manager = self.obtain()
        with patch.object(installer, 'terminal_confirm', side_effect=AssertionError('prompted')):
            self.cleanup(manager, policy='ask')
            self.cleanup(manager, policy='keep')
        self.assertTrue(manager.package.exists())

    def test_interactive_cleanup_can_decline_or_accept(self):
        manager = self.obtain()
        self.args.json_only = False
        class Terminal(io.StringIO):
            def isatty(self): return True
        self.args.tool_cleanup = 'ask'
        for answer in (False, True):
            with contextlib.redirect_stderr(Terminal()), patch.object(installer, 'terminal_confirm', return_value=answer):
                manager.cleanup(self.args, False)
            self.assertEqual(manager.package.exists(), not answer)

    def test_lock_blocks_concurrent_managed_updates_and_recovery_path_takes_same_lock(self):
        manager = self.obtain()
        with self.assertRaises(installer.Refusal): installer.ManagedPicotool()
        manager.close()
        lease = self.obtain()  # Explicit retained --picotool from a recovery command.
        self.assertEqual(lease.package, manager.package)
        with self.assertRaises(installer.Refusal): installer.ManagedPicotool()

    def test_cache_symlink_and_unknown_package_path_are_refused(self):
        manager = self.obtain()
        outside = self.home/'outside'
        outside.mkdir()
        link = manager.root/('0'*64)
        link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(installer.Refusal): manager.verify(link)
        self.assertEqual(list(outside.iterdir()), [])

    def test_low_disk_space_refuses_before_network_or_cache_creation(self):
        with patch.object(installer.shutil, 'disk_usage', return_value=SimpleNamespace(free=0)), self.assertRaisesRegex(installer.Refusal, '128 MiB'):
            installer.prepare_standalone_picotool(self.args)
        self.assertFalse(self.calls)
        self.assertFalse((self.home/'.cache').exists())

    def test_empty_state_index_and_unknown_transactions_prevent_cleanup(self):
        manager = self.obtain()
        transaction = self.state/'unknown'
        transaction.mkdir()
        for record in ({'recovery_required':False}, None, [], False, 1, 'unknown'):
            (transaction/'transaction.json').write_text(json.dumps(record))
            with self.assertRaisesRegex(installer.Refusal, 'Unknown private transaction'): self.cleanup(manager)
        installer.save_json(manager.root/'.states.json', [])
        with self.assertRaisesRegex(installer.Refusal, 'Unknown picotool state index'): self.cleanup(manager)
        self.assertTrue(manager.package.exists())

    def test_nonregular_recovery_records_never_block_reading_or_authorize_cleanup(self):
        manager = self.obtain()
        transaction = self.state/'transaction.json'
        transaction.mkdir()
        with self.assertRaisesRegex(installer.Refusal, 'Unknown private recovery record'): self.cleanup(manager)
        transaction.rmdir()
        os.mkfifo(transaction)
        with self.assertRaisesRegex(installer.Refusal, 'Unknown private recovery record'): self.cleanup(manager)
        self.assertTrue(manager.package.exists())

    def test_json_only_never_prompts_for_cleanup_even_with_a_terminal(self):
        manager = self.obtain()
        self.args.tool_cleanup = 'ask'
        with patch.object(installer.sys.stderr,'isatty',return_value=True), \
             patch.object(installer,'terminal_confirm',side_effect=AssertionError('JSON-only prompted')):
            manager.cleanup(self.args,False)
        self.assertTrue(manager.package.exists())

    def test_missing_registered_state_directory_prevents_cleanup(self):
        manager = self.obtain()
        self.state.rmdir()
        with self.assertRaisesRegex(installer.Refusal,'storage is missing'): self.cleanup(manager)
        self.assertTrue(manager.package.exists())


class ArchiveAndRequirementsTests(unittest.TestCase):
    def test_terminal_consent_and_cleanup_preserve_piped_stdin_at_wide_and_narrow_widths(self):
        code = ('import json,sys\n'
                'sys.path.insert(0,sys.argv[1])\nimport usb_installer as installer\n'
                'download=installer.terminal_confirm("Use an official verified picotool download?")\n'
                'cleanup=installer.terminal_confirm("Remove downloaded tools? Private backups will be kept.")\n'
                'print(json.dumps(dict(download=download,cleanup=cleanup,stdin=sys.stdin.read())))\n')
        for columns, answers in ((100,(b'maybe\ny\n',b'y\n')),(40,(b'n\n',b'\n'))):
            with self.subTest(columns=columns):
                master,slave=pty.openpty()
                fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('4H',24,columns,0,0))
                def terminal():
                    os.setsid();fcntl.ioctl(2,termios.TIOCSCTTY,0)
                process=None
                try:
                    process=subprocess.Popen([sys.executable,'-I','-S','-B','-c',code,str(ROOT/'scripts')],
                        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=slave,preexec_fn=terminal)
                    os.close(slave);slave=None
                    process.stdin.write(b'piped script input\n');process.stdin.close();process.stdin=None
                    text=bytearray()
                    for marker,answer in zip((b'picotool download? [y/N]: ',b'backups will be kept. [y/N]: '),answers):
                        deadline=time.monotonic()+10
                        while marker not in text:
                            self.assertLess(time.monotonic(),deadline,text.decode(errors='replace'))
                            if select.select([master],[],[],0.1)[0]: text.extend(os.read(master,4096))
                        os.write(master,answer)
                    output=bytearray();streams={master:text,process.stdout.fileno():output}
                    deadline=time.monotonic()+10
                    while streams:
                        self.assertLess(time.monotonic(),deadline,text.decode(errors='replace'))
                        for descriptor in select.select(list(streams),[],[],0.1)[0]:
                            try: data=os.read(descriptor,4096)
                            except OSError as error:
                                if descriptor!=master or error.errno!=installer.errno.EIO: raise
                                data=b''
                            if data: streams[descriptor].extend(data)
                            else: del streams[descriptor]
                    os.close(master);master=None
                    process.wait(timeout=5);process.stdout.close()
                    self.assertEqual(process.returncode,0,text.decode())
                    self.assertEqual(json.loads(output),dict(download=columns==100,cleanup=columns==100,stdin='piped script input\n'))
                    self.assertIn('Private backups will be kept.',text.decode())
                finally:
                    if master is not None: os.close(master)
                    if process is not None and process.poll() is None:
                        process.kill();process.communicate(timeout=5)
                    if slave is not None: os.close(slave)

    @unittest.skipIf(os.geteuid() == 0, 'Bootstrap requires an ordinary user')
    def test_bootstrap_reports_missing_old_python_windows_and_wsl_before_network(self):
        for problem in ('missing', 'old', 'windows', 'wsl'):
            with self.subTest(problem=problem), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                system = 'MINGW64_NT' if problem == 'windows' else 'Linux'
                release = 'microsoft-standard-WSL2' if problem == 'wsl' else 'native'
                (root/'uname').write_text('#!'+sys.executable+'\nimport sys\nprint('+repr(system)+' if sys.argv[1]=="-s" else '+repr(release)+')\n')
                (root/'curl').write_text('#!'+sys.executable+'\nfrom pathlib import Path\nPath('+repr(str(root/'network-used'))+').touch()\n')
                for tool in ('uname', 'curl'): (root/tool).chmod(0o700)
                if problem == 'old':
                    (root/'python3').write_text('#!'+sys.executable+'\nimport subprocess,sys\n'
                        'code="import sys;sys.version_info=(3,9,0);sys.version=\'3.9.0\';"+sys.argv[2]\n'
                        'sys.exit(subprocess.call([sys.executable,"-c",code]))\n')
                    (root/'python3').chmod(0o700)
                result = subprocess.run(['/bin/bash',str(ROOT/'scripts/install_usb.sh'),'discover'],
                    env={**os.environ,'PATH':str(root)},text=True,capture_output=True,timeout=5)
                self.assertEqual(result.returncode,2,result.stderr)
                self.assertFalse((root/'network-used').exists())
                self.assertNotIn('Traceback',result.stderr)
                expected = {'missing':'was not found','old':'Found Python 3.9.0','windows':'Native Windows','wsl':'WSL USB flashing'}[problem]
                self.assertIn(expected,result.stderr)
                if problem in ('missing','old'):
                    self.assertIn('python.org/downloads/',result.stderr)
                    self.assertIn('rerun',result.stderr)

    def test_cleanup_failure_does_not_replace_verified_firmware_result(self):
        manager = SimpleNamespace(cleanup=lambda *_: (_ for _ in ()).throw(PermissionError('fixture')), close=lambda: None)
        complete = {'stage':'complete','erase_verified':True,'recovery_required':False}
        with patch.object(installer,'prepare_standalone_picotool',return_value=manager), \
             patch.object(installer,'erase_transaction',return_value=complete), \
             contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()) as messages:
            code = installer.main(['erase','--device','1545B6EFBF78028C','--board','pico2_w','--yes'],human=True)
        self.assertEqual(code,0)
        self.assertTrue(json.loads(output.getvalue())['ok'])
        self.assertIn('cleanup is unconfirmed',messages.getvalue())

    def test_tar_and_zip_valid_archives_keep_support_files(self):
        for tar in (True, False):
            entries = installer.picotool_archive(archive(tar=tar), 'fixture.tar.gz' if tar else 'fixture.zip')
            self.assertEqual(set(entries), {'picotool/picotool', 'picotool/support.json'})

    def test_archive_traversal_symlinks_duplicates_conflicts_and_oversize_are_refused(self):
        for fault in ('traversal', 'symlink', 'duplicate', 'conflict', 'oversize'):
            output = io.BytesIO()
            with tarfile.open(fileobj=output, mode='w:gz') as package:
                for name in (('same', 'same') if fault == 'duplicate' else ('same', 'same/child') if fault == 'conflict' else ('../escape' if fault == 'traversal' else 'picotool/picotool',)):
                    item = tarfile.TarInfo(name)
                    if fault == 'symlink': item.type, item.linkname = tarfile.SYMTYPE, '/outside'
                    if fault == 'oversize': item.size = 33*1024*1024
                    package.addfile(item, io.BytesIO(bytes(item.size)) if item.size else None)
            with self.subTest(fault=fault), self.assertRaises((installer.Refusal, tarfile.TarError)):
                installer.picotool_archive(output.getvalue(), 'fixture.tar.gz')

    def test_platform_mapping_and_unsupported_abi(self):
        for system, machine, expected in (('Darwin','arm64','mac'),('Darwin','x86_64','mac'),
                                           ('Linux','aarch64','aarch64-lin'),('Linux','x86_64','x86_64-lin')):
            with patch.object(installer.platform,'system',return_value=system), patch.object(installer.platform,'machine',return_value=machine), patch.object(installer.platform,'release',return_value='native'):
                self.assertEqual(installer.tool_platform(),expected)
        for system, machine, release in (('Windows','AMD64','native'),('Linux','armv7l','native'),('Linux','x86_64','microsoft-standard-WSL2')):
            with patch.object(installer.platform,'system',return_value=system), patch.object(installer.platform,'machine',return_value=machine), patch.object(installer.platform,'release',return_value=release), self.assertRaises(installer.Refusal):
                installer.tool_platform()

    def test_old_python_and_native_windows_exit_before_unix_imports(self):
        for setup, expected in (("sys.version_info=(3,9,0)", 'Python 3.10 or newer'),
                                ("sys.platform='win32'", 'Native Windows')):
            code = 'import sys\n'+setup+'\nexec(compile(open(sys.argv[1]).read(),sys.argv[1],"exec"))'
            result = subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(ROOT/'scripts/usb_installer.py')],capture_output=True,text=True,timeout=5)
            self.assertEqual(result.returncode,2)
            self.assertIn(expected,result.stderr)
            self.assertNotIn('Traceback',result.stderr)
            self.assertEqual(result.stdout,'')

    def test_imported_entry_cannot_download_and_explicit_tool_never_overridden(self):
        for arguments in (['upgrade','--download-picotool'], ['plan','--download-picotool'],
                          ['upgrade','--picotool','custom','--download-picotool']):
            with patch.object(installer,'prepare_standalone_picotool',side_effect=AssertionError('downloaded')), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(installer.main(arguments),2)
            self.assertFalse(json.loads(output.getvalue())['ok'])


if __name__ == '__main__': unittest.main()
