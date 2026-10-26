#!/usr/bin/env python3
"""Embed original assets and CSP hashes; no external build dependencies."""
import base64
import gzip
import hashlib
import json
import pathlib
import sys

root, output = map(pathlib.Path, sys.argv[1:])
web = root / 'src/network/web'
# Minified artifacts are maintained by the existing pinned npm build. Verify
# exact source/output identity here so ordinary CMake remains Python-only.
groups = {
    'app.min.js': ['operations.js', 'standalone-frequency.js', 'rf-calibration.js', 'amplifier-enable.js', 'gpio-drive.js', 'ntp-timeout.js', 'saved-progress.js', 'utc-datetime.js', 'message-schedule.js', 'app.js'],
    'config-validation.min.js': ['config-validation.js'],
    'device-presentation.min.js': ['device-presentation.js'],
    'organization.min.js': ['organization.js'],
}
manifest = json.loads((web / 'asset-build.json').read_text())
if (manifest.get('schema') != 'operator-assets/1' or
        manifest.get('tool') != 'esbuild/0.28.2' or manifest.get('target') != 'es2020' or
        manifest.get('recipe_sha256') != hashlib.sha256((root / 'scripts/build_operator_assets.mjs').read_bytes()).hexdigest() or
        set(manifest.get('groups', {})) != set(groups)):
    raise ValueError('Invalid operator asset manifest; run npm --prefix src/network/bootstrap_web run build')
for output_name, inputs in groups.items():
    entry = manifest['groups'][output_name]
    expected = {name: hashlib.sha256((web / name).read_bytes()).hexdigest() for name in inputs}
    output_bytes = (web / output_name).read_bytes()
    if (entry.get('inputs') != expected or entry.get('bytes') != len(output_bytes) or
            entry.get('sha256') != hashlib.sha256(output_bytes).hexdigest()):
        raise ValueError('Stale operator assets; run npm --prefix src/network/bootstrap_web run build')
html, css = [(web / name).read_text() for name in ('index.html', 'style.css')]
js = (web / 'app.min.js').read_text()
organization = (web / 'organization.min.js').read_text()
presentation = (web / 'device-presentation.min.js').read_text()
validation = (web / 'config-validation.min.js').read_text()
bootstrap_web = root / 'src/network/bootstrap_web'
radio_js = (bootstrap_web / 'radio-bundle.js').read_text()
radio_html = html.replace('<link rel="stylesheet" href="/style.css">', '<style>' + css + '</style>')
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
recovery_html, recovery_js = [(bootstrap_web / name).read_text()
    for name in ('recovery.html', 'recovery-bundle.js')]
recovery_html = recovery_html.replace('<link rel="stylesheet" href="./style.css">',
    '<style>' + bootstrap_css + '</style>')
# The AP server admits one connection. Stream each setup document with its
# scripts, rather than letting browser preload requests compete for that slot.
# Keep the flash literals separate: the station scripts exceed 64 KiB together.
def script_document(document, tags):
    for tag in tags:
        if document.count(tag) != 1:
            raise ValueError('Missing or repeated setup script tag')
        document = document.replace(tag, '')
    if not document.endswith('</body>\n</html>\n'):
        raise ValueError('Unexpected setup document ending')
    return document.removesuffix('</body>\n</html>\n')

bootstrap_html = script_document(bootstrap_html, ['<script src="./bundle.js" defer></script>'])
owner_html = script_document(owner_html, [
    '<script src="./owner-key-bundle.js" defer></script>',
    '<script src="./owner-bundle.js" defer></script>'])
recovery_html = script_document(recovery_html, ['<script src="./recovery-bundle.js" defer></script>'])
radio_html = radio_html.replace('<script src="/app.js" defer></script>', '').replace('<script src="/device-presentation.js" defer></script>', '').replace('<script src="/organization.js" defer></script>', '').replace('<script src="/config-validation.js" defer></script>', '')
radio_html = radio_html.removesuffix('</body></html>\n')
if '</body>' in radio_html or radio_html == html:
    raise ValueError('Unexpected radio document ending')
for script in (bootstrap_js, owner_key_js, owner_js, recovery_js, radio_js, js, organization, validation, presentation):
    if '</script' in script.lower():
        raise ValueError('Setup script contains an HTML closing tag')
html = html.replace('<link rel="stylesheet" href="/style.css">', '<style>' + css + '</style>')
html = html.replace('<script src="/app.js" defer></script>', '').replace('<script src="/device-presentation.js" defer></script>', '').replace('<script src="/organization.js" defer></script>', '').replace('<script src="/config-validation.js" defer></script>', '')
html = html.replace('</body>', '<script>' + validation + '</script><script>' + presentation + '</script><script>' + js + '</script><script>' + organization + '</script></body>')
hash_for = lambda text: base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()
csp = "default-src 'self'; style-src 'sha256-" + hash_for(css) + "'; script-src 'sha256-" + hash_for(js) + "' 'sha256-" + hash_for(validation) + "' 'sha256-" + hash_for(presentation) + "' 'sha256-" + hash_for(organization) + "'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
radio_policy = ("default-src 'none'; connect-src 'self'; style-src 'sha256-" + hash_for(css) +
                "'; script-src 'sha256-" + hash_for(radio_js) + "' 'sha256-" + hash_for(js) +
                "' 'sha256-" + hash_for(owner_key_js) + "' 'sha256-" + hash_for(validation) + "' 'sha256-" + hash_for(presentation) + "' 'sha256-" + hash_for(organization) +
                "'; img-src data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
bootstrap_policy = ("default-src 'none'; script-src 'self' " +
                    ' '.join("'sha256-" + hash_for(script) + "'"
                             for script in (bootstrap_js, owner_key_js, owner_js, recovery_js)) + "; "
                    "style-src 'self' 'sha256-" + hash_for(bootstrap_css) + "'; "
                    "connect-src 'self'; img-src 'self' data:; "
                    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
literal_names = {}
source = '#include "network/assets.hpp"\nnamespace wsprrypico::network {\nnamespace {\n'
for name, text, marker in [
    ('html', radio_html, 'WPHTML'), ('css', css, 'WPCSS'),
    ('js', js, 'WPJS'), ('presentation', presentation, 'WPPRES'), ('organization', organization, 'WPORG'), ('validation', validation, 'WPVALID'), ('csp', csp, 'WPCSP'),
    ('radio_html', radio_html, 'WPRADIO'), ('radio_js', radio_js, 'WPRADIOJS'),
    ('radio_policy', radio_policy, 'WPRADIOCSP'),
    ('bootstrap_html', bootstrap_html, 'WPBHTML'),
    ('bootstrap_css', bootstrap_css, 'WPBCSS'),
    ('bootstrap_js', bootstrap_js, 'WPBJS'),
    ('recovery_html', recovery_html, 'WPRHTML'),
    ('recovery_js', recovery_js, 'WPRJS'),
    ('owner_html', owner_html, 'WPOHTML'),
    ('owner_js', owner_js, 'WPOJS'),
    ('owner_key_js', owner_key_js, 'WPOKEY'),
    ('bootstrap_policy', bootstrap_policy, 'WPBCSP'),
]:
    if ')' + marker + '"' in text:
        raise ValueError('Raw string delimiter in ' + name)
    # Keep each translation-unit literal below the portable C++ 64 KiB limit.
    # The transport streams parts contiguously; CSP still hashes the exact script.
    encoded = text.encode()
    chunks = []
    while encoded:
        end = min(len(encoded), 60000)
        while end < len(encoded) and encoded[end] & 0xc0 == 0x80:
            end -= 1
        chunks.append(encoded[:end].decode())
        encoded = encoded[end:]
    literal_names[name] = [name] if len(chunks) == 1 else [f'{name}_{i}' for i in range(len(chunks))]
    for identifier, chunk in zip(literal_names[name], chunks):
        if len(chunk.encode()) >= 65536:
            raise ValueError('Oversized C++ asset literal: ' + identifier)
        source += f'constexpr char {identifier}[] = R"{marker}({chunk}){marker}";\n'
    if name != 'radio_js' and (name.endswith('_js') or name == 'js'):
        source += f'constexpr std::string_view {name}_parts[] = {{' + ', '.join(literal_names[name]) + '};\n'
documents = '''
WebAsset script_asset(std::span<const std::string_view> parts) {
    return parts.size() == 1 ? WebAsset{parts.front(), "text/javascript; charset=utf-8"}
                             : WebAsset{{}, "text/javascript; charset=utf-8", parts};
}
constexpr std::string_view html_parts[] = {
    html, "<script>", validation, "</script><script>", presentation, "</script><script>", js, "</script><script>", organization, "</script></body>\\n</html>\\n"};
constexpr std::string_view bootstrap_parts[] = {
    bootstrap_html, "<script>", bootstrap_js, "</script></body>\\n</html>\\n"};
constexpr std::string_view recovery_parts[] = {
    recovery_html, "<script>", recovery_js, "</script></body>\\n</html>\\n"};
constexpr std::string_view owner_parts[] = {
    owner_html, "<script>", owner_key_js, "</script><script>", owner_js,
    "</script></body>\\n</html>\\n"};
constexpr std::string_view radio_parts[] = {
    radio_html, "<script>", owner_key_js, "</script><script>", radio_js, "</script><script>", validation, "</script><script>", presentation, "</script><script>", js, "</script><script>", organization,
    "</script></body>\\n</html>\\n"};
}

'''
for name, identifiers in literal_names.items():
    if name.endswith('_js') or name == 'js':
        documents = documents.replace(', ' + name + ',', ', ' + ', '.join(identifiers) + ',')
source += documents
source += '''
std::string_view consumer_radio_csp() { return radio_policy; }
std::optional<WebAsset> consumer_radio_asset() {
    return WebAsset{radio_html, "text/html; charset=utf-8", radio_parts};
}
std::string_view web_csp() { return csp; }
std::optional<WebAsset> web_asset(std::string_view path) {
    if (path == "/" || path == "/index.html" || path == "/radio" || path == "/station" || path == "/wifi-host" || path == "/owner.html") return WebAsset{html, "text/html; charset=utf-8", html_parts};
    if (path == "/style.css") return WebAsset{css, "text/css; charset=utf-8"};
    if (path == "/config-validation.js") return WebAsset{validation, "text/javascript; charset=utf-8"};
    if (path == "/device-presentation.js") return WebAsset{presentation, "text/javascript; charset=utf-8"};
    if (path == "/organization.js") return WebAsset{organization, "text/javascript; charset=utf-8"};
    if (path == "/app.js") return script_asset(js_parts);
    return {};
}
std::string_view bootstrap_csp() { return bootstrap_policy; }
std::optional<WebAsset> bootstrap_asset(std::string_view path) {
    if (path == "/index.html") return WebAsset{bootstrap_html, "text/html; charset=utf-8", bootstrap_parts};
    if (path == "/style.css") return WebAsset{bootstrap_css, "text/css; charset=utf-8"};
    if (path == "/bundle.js") return script_asset(bootstrap_js_parts);
    if (path == "/recovery.html") return WebAsset{recovery_html, "text/html; charset=utf-8", recovery_parts};
    if (path == "/recovery-bundle.js") return script_asset(recovery_js_parts);
    if (path == "/owner.html") return WebAsset{owner_html, "text/html; charset=utf-8", owner_parts};
    if (path == "/owner-bundle.js") return script_asset(owner_js_parts);
    if (path == "/owner-key-bundle.js") return script_asset(owner_key_js_parts);
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
