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
bootstrap_web = root / 'src/network/bootstrap_web'
bootstrap_html, bootstrap_css, bootstrap_js = [
    (bootstrap_web / name).read_text()
    for name in ('index.html', 'style.css', 'bundle.js')
]
bootstrap_html = bootstrap_html.replace(
    '<link rel="stylesheet" href="./style.css">',
    '<style>' + bootstrap_css + '</style>')
owner_html, owner_js, owner_key_js = [
    (bootstrap_web / name).read_text()
    for name in ('owner.html', 'owner-bundle.js', 'owner-key-bundle.js')
]
owner_html = owner_html.replace(
    '<link rel="stylesheet" href="./style.css">',
    '<style>' + bootstrap_css + '</style>')
html = html.replace('<link rel="stylesheet" href="/style.css">', '<style>' + css + '</style>')
html = html.replace('<script src="/app.js" defer></script>', '')
html = html.replace('</body>', '<script>' + js + '</script></body>')
hash_for = lambda text: base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()
csp = "default-src 'self'; style-src 'sha256-" + hash_for(css) + "'; script-src 'sha256-" + hash_for(js) + "'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
bootstrap_policy = ("default-src 'none'; script-src 'self'; "
                    "style-src 'self' 'sha256-" + hash_for(bootstrap_css) + "'; "
                    "connect-src 'self'; img-src 'self' data:; "
                    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
source = '#include "network/assets.hpp"\nnamespace wsprrypico::network {\nnamespace {\n'
for name, text, marker in [
    ('html', html, 'WPHTML'), ('css', css, 'WPCSS'),
    ('js', js, 'WPJS'), ('csp', csp, 'WPCSP'),
    ('bootstrap_html', bootstrap_html, 'WPBHTML'),
    ('bootstrap_css', bootstrap_css, 'WPBCSS'),
    ('bootstrap_js', bootstrap_js, 'WPBJS'),
    ('owner_html', owner_html, 'WPOHTML'),
    ('owner_js', owner_js, 'WPOJS'),
    ('owner_key_js', owner_key_js, 'WPOKEY'),
    ('bootstrap_policy', bootstrap_policy, 'WPBCSP'),
]:
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
std::string_view bootstrap_csp() { return bootstrap_policy; }
std::optional<WebAsset> bootstrap_asset(std::string_view path) {
    if (path == "/index.html") return WebAsset{bootstrap_html, "text/html; charset=utf-8"};
    if (path == "/style.css") return WebAsset{bootstrap_css, "text/css; charset=utf-8"};
    if (path == "/bundle.js") return WebAsset{bootstrap_js, "text/javascript; charset=utf-8"};
    if (path == "/owner.html") return WebAsset{owner_html, "text/html; charset=utf-8"};
    if (path == "/owner-bundle.js") return WebAsset{owner_js, "text/javascript; charset=utf-8"};
    if (path == "/owner-key-bundle.js") return WebAsset{owner_key_js, "text/javascript; charset=utf-8"};
    return {};
}
}
'''
output.parent.mkdir(parents=True, exist_ok=True)
if not output.exists() or output.read_text() != source:
    output.write_text(source)
print(f'Browser document: {len(html.encode())} bytes; gzip: {len(gzip.compress(html.encode(), mtime=0))} bytes (informational; served uncompressed)')
print(f'Bootstrap bundle embedded: {len(bootstrap_js.encode())} bytes')
print(f'Owner bundle embedded: {len(owner_js.encode())} bytes')
print(f'Owner key bundle embedded: {len(owner_key_js.encode())} bytes')
