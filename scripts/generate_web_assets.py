#!/usr/bin/env python3
"""Embed original assets and CSP hashes; no external build dependencies."""
import base64
import gzip
import hashlib
import pathlib
import sys

root, output = map(pathlib.Path, sys.argv[1:])
web = root / 'src/network/web'
html, css, js = [(web / name).read_text() for name in ('index.html', 'style.css', 'app.js')]
html = html.replace('<link rel="stylesheet" href="/style.css">', '<style>' + css + '</style>')
html = html.replace('<script src="/app.js" defer></script>', '')
html = html.replace('</body>', '<script>' + js + '</script></body>')
hash_for = lambda text: base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()
csp = "default-src 'self'; style-src 'sha256-" + hash_for(css) + "'; script-src 'sha256-" + hash_for(js) + "'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
source = '#include "network/assets.hpp"\nnamespace wsprrypico::network {\nnamespace {\n'
for name, text in [('html', html), ('css', css), ('js', js), ('csp', csp)]:
    marker = 'WP' + name.upper()
    if ')' + marker + '"' in text:
        raise ValueError('Raw string delimiter in ' + name)
    source += f'constexpr char {name}[] = R"{marker}({text}){marker}";\n'
source += '''}
std::string_view web_csp() { return csp; }
std::optional<WebAsset> web_asset(std::string_view path) {
    if (path == "/") return WebAsset{html, "text/html; charset=utf-8"};
    if (path == "/style.css") return WebAsset{css, "text/css; charset=utf-8"};
    if (path == "/app.js") return WebAsset{js, "text/javascript; charset=utf-8"};
    return {};
}
}
'''
output.parent.mkdir(parents=True, exist_ok=True)
if not output.exists() or output.read_text() != source:
    output.write_text(source)
print(f'Browser document: {len(html.encode())} bytes; gzip: {len(gzip.compress(html.encode(), mtime=0))} bytes (informational; served uncompressed)')
