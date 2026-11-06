"""A stale generated limit must stop an incremental build before compilation."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/ci'))
import execution


class GeneratedControlBuildTests(unittest.TestCase):
    def test_incremental_build_refuses_stale_generated_limit(self):
        deadline = time.monotonic() + 90  # Failure watchdog, not a speed assertion.
        source_revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
        tracked = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z']).decode().split('\0')
        self.assertTrue(any(tracked))
        with tempfile.TemporaryDirectory(prefix='wsprry-generated-control-') as temporary:
            work = Path(temporary)
            source, build = work/'source', work/'build'
            for name in filter(None, tracked):
                owned = ROOT/name
                if not owned.exists() and not owned.is_symlink():
                    continue  # Mirror tracked deletions in the current candidate.
                target = source/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(owned, target, follow_symlinks=False)

            def command(label, args, success=True):
                audit = work/label
                audit.mkdir()
                log = audit/'command.log'
                remaining = deadline - time.monotonic()
                self.assertGreater(remaining, 0, 'Generated-control build watchdog exhausted')
                try:
                    execution.execute(log, list(map(str, args)), ROOT, source_revision,
                                      context=label, watchdog=remaining)
                except RuntimeError:
                    if success:
                        self.fail(log.read_text()[-8000:])
                else:
                    self.assertTrue(success, 'Stale generated input unexpectedly built')
                return log.read_text()

            configure = ['cmake', '-S', source, '-B', build, '-G', 'Ninja',
                         '-DWSPRRY_PICO_BUILD_TESTS=OFF', '-DWSPRRY_PICO_BUILD_FIRMWARE=OFF']
            command('configure-valid', configure)
            header = source/'src/network/control_contract.hpp'
            original = header.read_text()
            limit = json.loads((source/'engineering/protocol/control-1.schema.json').read_text())['request_limits']['config/update']
            self.assertGreater(limit, 1)
            expected = f'if (resource == "config/update") return {limit};'
            self.assertEqual(original.count(expected), 1)
            header.write_text(original.replace(expected, expected.replace(str(limit), str(limit-1)), 1))
            self.assertGreater(header.stat().st_mtime_ns, (build/'build.ninja').stat().st_mtime_ns,
                               'Generated input timestamp did not advance beyond the configured build')
            refused = command('refuse-stale', ['cmake', '--build', build, '--target', 'wsprrypico_core'], success=False)
            self.assertIn('Stale generated control contract:', refused)
            self.assertIn('control_contract.hpp', refused)
            self.assertNotIn('Building CXX object', refused)
            header.write_text(original)
            command('configure-restored', configure)


if __name__ == '__main__':
    unittest.main()
