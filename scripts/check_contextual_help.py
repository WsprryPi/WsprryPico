#!/usr/bin/env python3
"""Validate emitted Pico help links against an independently built operator manual."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.ids = set()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag == 'a' and 'documentation-help' in attrs.get('class', '').split():
            self.links.append(attrs)


def validate(links, site, version="devel"):
    if not links:
        raise ValueError('No emitted help links')
    for attrs in links:
        url = urlsplit(attrs['href'])
        if (url.scheme != 'https' or url.netloc != 'wsprrypico.readthedocs.io'
                or not url.path.startswith(f'/en/{version}/') or url.query
                or '..' in url.path.split('/')):
            raise ValueError('Invalid documentation URL: ' + attrs['href'])
        if (attrs.get('target') != '_blank'
                or set(attrs.get('rel', '').split()) != {'noopener', 'noreferrer'}
                or attrs.get('referrerpolicy') != 'no-referrer'
                or not attrs.get('aria-label', '').startswith(('Help: ', 'Manual: ', 'Getting started: ', 'Use with WsprryPi: '))):
            raise ValueError('Unsafe or unnamed help link: ' + str(attrs))
        target = site / url.path.removeprefix(f'/en/{version}/')
        if not target.is_file():
            raise ValueError('Missing help page: ' + str(target))
        if url.fragment and url.fragment not in Document(target.read_text()).ids:
            raise ValueError('Missing help anchor: ' + attrs['href'])


def emitted_links(version="devel"):
    with tempfile.TemporaryDirectory(prefix='pico-help-') as scratch:
        output = Path(scratch) / 'assets.cpp'
        subprocess.run([sys.executable, str(ROOT / 'scripts/generate_web_assets.py'),
                        str(ROOT), str(output), '0.0.0-devel', version], check=True, capture_output=True)
        generated = output.read_text()
        links = []
        # Inspect every shipped document, including streamed C++ literals.
        for marker in ('WPHTML', 'WPRADIO', 'WPBHTML', 'WPOHTML', 'WPRHTML'):
            chunks = re.findall(r'R"' + marker + r'\((.*?)\)' + marker + '"', generated, re.S)
            if not chunks:
                raise ValueError('Missing embedded document: ' + marker)
            document = Document(''.join(chunks))
            if not document.links:
                raise ValueError('Missing help in embedded document: ' + marker)
            links.extend(document.links)
        if '@WSPRRY_PICO_HELP_BASE@' in generated:
            raise ValueError('Unresolved help base')
        return links


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=ROOT / 'docs/_build/html')
    parser.add_argument('--live', action='store_true', help='Fetch published pages and check their actual IDs')
    parser.add_argument('--version', choices=('main', 'devel'), default='devel')
    args = parser.parse_args()
    links = emitted_links(args.version)
    if args.live:
        with tempfile.TemporaryDirectory(prefix='pico-help-live-') as scratch:
            site = Path(scratch)
            for url in sorted({a['href'].split('#')[0] for a in links}):
                target = site / urlsplit(url).path.removeprefix(f'/en/{args.version}/')
                target.parent.mkdir(parents=True, exist_ok=True)
                result = subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                                         '--max-time', '20', '--output', str(target),
                                         '--write-out', '%{url_effective}', url], check=True,
                                        text=True, capture_output=True)
                if result.stdout != url:
                    raise ValueError('Unexpected documentation redirect: ' + result.stdout)
            validate(links, site, args.version)
        print('Published pages and fragments verified')
    else:
        validate(links, args.site, args.version)
    print(f'Validated {len(links)} emitted help links against {args.site}')
