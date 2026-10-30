"""Missing or renamed manual destinations fail even if firmware URLs agree."""
import importlib.util
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
