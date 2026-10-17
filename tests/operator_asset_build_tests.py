"""Freshness failures prevent shipping stale generated browser scripts."""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class OperatorAssets(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix='operator-assets-')
        self.addCleanup(self.scratch.cleanup)
        self.root = pathlib.Path(self.scratch.name)
        (self.root / 'scripts').mkdir()
        shutil.copy2(ROOT / 'scripts/build_operator_assets.mjs', self.root / 'scripts/build_operator_assets.mjs')
        for directory in ('web', 'bootstrap_web'):
            target = self.root / 'src/network' / directory
            target.mkdir(parents=True)
            for source in (ROOT / 'src/network' / directory).iterdir():
                if source.is_file():
                    shutil.copy2(source, target / source.name)

    def generate(self):
        return subprocess.run(
            [sys.executable, str(ROOT / 'scripts/generate_web_assets.py'),
             str(self.root), str(self.root / 'assets.cpp')],
            text=True, capture_output=True, check=False)

    def test_fresh_assets_embed(self):
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('radio_parts', (self.root / 'assets.cpp').read_text())

    def test_source_edit_requires_regeneration(self):
        source = self.root / 'src/network/web/app.js'
        source.write_text(source.read_text() + '\n// changed source\n')
        result = self.generate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Stale operator assets', result.stderr)

    def test_recipe_change_requires_regeneration(self):
        recipe = self.root / 'scripts/build_operator_assets.mjs'
        recipe.write_text(recipe.read_text() + '\n// changed recipe\n')
        result = self.generate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid operator asset manifest', result.stderr)

    def test_modified_output_is_rejected(self):
        output = self.root / 'src/network/web/app.min.js'
        output.write_text(output.read_text() + '\n')
        result = self.generate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Stale operator assets', result.stderr)


if __name__ == '__main__':
    unittest.main()
