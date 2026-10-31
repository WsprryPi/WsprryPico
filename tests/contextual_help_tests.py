"""Missing or renamed manual destinations fail even if firmware URLs agree."""
import importlib.util
import re
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('help_check', ROOT / 'scripts/check_contextual_help.py')
help_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(help_check)


class HelpLinks(unittest.TestCase):
    def test_shipped_destinations(self):
        for version in ('main', 'devel'):
            help_check.validate(help_check.emitted_links(version), ROOT / 'docs/_build/html', version)

    def test_inline_icons_in_every_source_page(self):
        # Page-level help must sit beside its heading; Manual remains readable.
        pages = [ROOT / 'src/network/web/index.html',
                 *(ROOT / 'src/network/bootstrap_web').glob('*.html')]
        for page in pages:
            text = page.read_text()
            for link in re.findall(r'<a class="documentation-help".*?</a>', text):
                with self.subTest(page=page.name, link=link[:100]):
                    if 'aria-label="Manual:' in link:
                        self.assertIn('>Manual</a>', link)
                        continue
                    self.assertIn('aria-hidden="true" focusable="false"', link)
                    self.assertIn('width="16" height="16"', link)
                    self.assertIn('stroke="currentColor"', link)
                    self.assertNotRegex(link, r'<(?:img|script|use)\b')
                    self.assertRegex(link, r'aria-label="Help: [^"]+"')
            for summary in re.findall(r'<summary[^>]*>.*?</summary>', text, re.S):
                self.assertIn('documentation-help', summary, (page, summary))
            for section in re.findall(r'<section\b[^>]*>.*?</section>', text, re.S):
                self.assertIn('documentation-help', section, (page, section[:80]))
            if page.parent.name == 'bootstrap_web' and 'documentation-help' in text:
                self.assertRegex(text, r'<div class="help-heading"><h1[^>]*>.*?</h1><a class="documentation-help"')

    def test_missing_page_anchor_and_unsafe_urls_fail(self):
        attrs = {'href': 'https://wsprrypico.readthedocs.io/en/devel/topic.html#answer',
                 'target': '_blank', 'rel': 'noopener noreferrer',
                 'referrerpolicy': 'no-referrer', 'aria-label': 'Help: Topic (online, opens in a new tab)'}
        with tempfile.TemporaryDirectory() as scratch:
            site = Path(scratch)
            with self.assertRaisesRegex(ValueError, 'Missing help page'):
                help_check.validate([attrs], site)
            (site / 'topic.html').write_text('<h2 id="renamed">Answer</h2>')
            with self.assertRaisesRegex(ValueError, 'Missing help anchor'):
                help_check.validate([attrs], site)
            (site / 'topic.html').write_text('<h2 id="answer">Answer</h2>')
            help_check.validate([attrs], site)
            for url in ['http://wsprrypico.readthedocs.io/en/devel/topic.html',
                        'https://example.com/en/devel/topic.html',
                        'https://wsprrypico.readthedocs.io/en/latest/topic.html',
                        attrs['href'].replace('#answer', '?device=secret#answer')]:
                with self.subTest(url=url), self.assertRaisesRegex(ValueError, 'Invalid documentation URL'):
                    help_check.validate([{**attrs, 'href': url}], site)


if __name__ == '__main__':
    unittest.main()
