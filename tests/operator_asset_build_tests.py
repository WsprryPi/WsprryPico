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

    def generate(self, version=None, documentation=None):
        return subprocess.run(
            [sys.executable, str(ROOT / 'scripts/generate_web_assets.py'),
             str(self.root), str(self.root / 'assets.cpp')] + ([] if version is None else [version]) + ([] if documentation is None else [documentation]),
            text=True, capture_output=True, check=False)

    def test_fresh_assets_embed(self):
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('radio_parts', (self.root / 'assets.cpp').read_text())

    def test_footer_embeds_selected_firmware_version(self):
        result = self.generate('0.2.0-beta.7')
        self.assertEqual(result.returncode, 0, result.stderr)
        generated = (self.root / 'assets.cpp').read_text()
        self.assertIn('id="firmware-version">0.2.0-beta.7</span>', generated)
        self.assertNotIn('@WSPRRY_PICO_FIRMWARE_VERSION@', generated)

    def test_firmware_version_is_html_escaped(self):
        result = self.generate('<script>alert("version")</script>')
        self.assertEqual(result.returncode, 0, result.stderr)
        generated = (self.root / 'assets.cpp').read_text()
        self.assertIn('&lt;script&gt;alert(&quot;version&quot;)&lt;/script&gt;', generated)

    def test_main_manual_is_explicit_and_unsupported_versions_fail(self):
        result = self.generate('0.1.0-ci.123.1', 'main')
        self.assertEqual(result.returncode, 0, result.stderr)
        generated = (self.root / 'assets.cpp').read_text()
        self.assertIn('https://wsprrypico.readthedocs.io/en/main/configure.html#station-identity', generated)
        self.assertNotIn('https://wsprrypico.readthedocs.io/en/devel/', generated)
        result = self.generate('0.1.0-ci.123.1', '../unknown')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Operator manual version must be main or devel', result.stderr)

    def test_large_html_streams_all_literals(self):
        document = self.root / 'src/network/web/index.html'
        document.write_text(document.read_text().replace('<main ', '<!--' + '界' * 25000 + '--><main ', 1))
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stderr)
        generated = (self.root / 'assets.cpp').read_text()
        self.assertIn('html_0, html_1', generated)
        self.assertIn('radio_html_0, radio_html_1', generated)
        self.assertNotIn('WebAsset{radio_html,', generated)
        self.assertNotIn('WebAsset{html,', generated)
        self.assertNotIn('</html_', generated)
        self.assertIn('</html>', generated)

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
