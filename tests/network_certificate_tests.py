#!/usr/bin/env python3
"""Certificate lifecycle checks use temporary, local credentials only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

script = Path(__file__).resolve().parents[1] / 'scripts/network_certificates.py'
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    def run(*args, success=True):
        result = subprocess.run([sys.executable, str(script), *map(str,args)], capture_output=True, text=True)
        assert (result.returncode == 0) == success, result.stderr
        return result.stdout
    ca, client, renewed = root/'device', root/'operator', root/'renewed'
    run('init','--directory',ca,'--device','pico-test','--address','127.0.0.1')
    original = (ca/'server/server.crt').read_bytes()
    run('init','--directory',ca,'--device','pico-test','--address','127.0.0.1',success=False)
    run('issue-client','--ca-directory',ca,'--name','browser','--output',client)
    run('renew-server','--ca-directory',ca,'--device','pico-test','--address','127.0.0.1','--output',renewed)
    assert original == (ca/'server/server.crt').read_bytes()
    assert original != (renewed/'server.crt').read_bytes()
    for key in root.rglob('*.key'): assert key.stat().st_mode & 0o077 == 0
    password = root/'password'; password.write_text('test-only-long-password'); password.chmod(0o600)
    run('export-browser','--client-directory',client,'--output',root/'browser.p12','--password-file',password)
    run('export-browser','--client-directory',client,'--output',root/'browser.p12','--password-file',password,success=False)
    assert (root/'browser.p12').stat().st_mode & 0o077 == 0
    # Exercise actual password-protected packages, not just file creation.
    # The opt-in Keychain profile must preserve the same client certificate.
    macos = root/'browser-macos.p12'
    run('export-browser','--client-directory',client,'--output',macos,
        '--password-file',password,'--macos-keychain')
    run('export-browser','--client-directory',client,'--output',macos,
        '--password-file',password,'--macos-keychain',success=False)
    assert macos.stat().st_mode & 0o077 == 0
    for package in (root/'browser.p12', macos):
        result = subprocess.run(['openssl','pkcs12','-in',str(package),
            '-passin','file:'+str(password),'-clcerts','-nokeys'], capture_output=True)
        assert result.returncode == 0
        exported = subprocess.run(['openssl','x509','-outform','DER'],
            input=result.stdout, capture_output=True, check=True).stdout
        expected = subprocess.run(['openssl','x509','-in',str(client/'client.crt'),
            '-outform','DER'], capture_output=True, check=True).stdout
        assert exported == expected
        rejected = subprocess.run(['openssl','pkcs12','-in',str(package),
            '-passin','stdin','-noout'], input=b'wrong-test-password\n', capture_output=True)
        assert rejected.returncode != 0
    info = json.loads(run('inspect','--directory',ca))
    assert len(info) == 3 and all(not item['renew_within_30_days'] for item in info)
    assert all('PRIVATE KEY' not in item['certificate'] for item in info)
    identifier = 'a' * 32
    selected = 'wsprrypico-' + identifier + '.local'
    dns_ca, dns_renewed, migrated = root/'dns-device', root/'dns-renewed', root/'migrated'
    run('init', '--directory', dns_ca, '--device-id', identifier.upper())
    bundle = dns_ca/'server'
    manifest = json.loads((bundle/'deployment.json').read_text())
    assert manifest['hostname'] == selected and manifest['device_id'] == identifier
    assert manifest['ipv4_sans'] == []
    assert json.loads(run('validate', '--directory', bundle)) == manifest
    def verify_identity(credentials, option, identity, success=True):
        result = subprocess.run(['openssl', 'verify', '-CAfile', str(credentials/'client-ca.crt'),
            option, identity, str(credentials/'server.crt')], capture_output=True, text=True)
        assert (result.returncode == 0) == success, result.stderr
    verify_identity(bundle, '-verify_hostname', selected)
    verify_identity(bundle, '-verify_hostname', 'attacker.local', success=False)
    verify_identity(bundle, '-verify_ip', '127.0.0.1', success=False)
    verify_identity(ca/'server', '-verify_ip', '127.0.0.1')
    verify_identity(ca/'server', '-verify_ip', '127.0.0.2', success=False)
    verify_identity(ca/'server', '-verify_hostname', selected, success=False)
    run('renew-server', '--ca-directory', dns_ca, '--device-id', identifier,
        '--hostname', selected.upper()+'.', '--output', dns_renewed)
    assert json.loads(run('validate', '--directory', dns_renewed))['hostname'] == selected
    assert (bundle/'server.crt').read_bytes() != (dns_renewed/'server.crt').read_bytes()
    run('renew-server', '--ca-directory', ca, '--device-id', identifier,
        '--address', '192.0.2.10', '--output', migrated)
    assert json.loads(run('validate', '--directory', migrated))['ipv4_sans'] == ['192.0.2.10']
    alias = root/'alias'
    run('renew-server', '--ca-directory', dns_ca, '--device-id', identifier,
        '--hostname', 'Different-Pico.LOCAL.', '--output', alias)
    assert json.loads(run('validate', '--directory', alias))['hostname'] == 'different-pico.local'
    mac_alias = root/'mac-alias'
    run('renew-server', '--ca-directory', dns_ca, '--device-id', identifier,
        '--hostname', 'wsprrypico-0a60df.local', '--output', mac_alias)
    mac_manifest = json.loads(run('validate', '--directory', mac_alias))
    assert mac_manifest['hostname'] == 'wsprrypico-0a60df.local'
    assert mac_manifest['device_id'] == identifier
    verify_identity(mac_alias, '-verify_hostname', 'wsprrypico-0a60df.local')
    verify_identity(mac_alias, '-verify_hostname', selected, success=False)
    assert (mac_alias/'client-ca.crt').read_bytes() == (bundle/'client-ca.crt').read_bytes()
    browser2, controller = root/'browser2', root/'controller'
    for destination in (browser2, controller):
        run('issue-client', '--ca-directory', dns_ca, '--name', destination.name, '--output', destination)
    assert (browser2/'client.crt').read_bytes() != (controller/'client.crt').read_bytes()
    inspect_dns = json.loads(run('inspect', '--directory', bundle))
    assert any('DNS:'+selected in item['subject_alt_name'] for item in inspect_dns)
    for invalid in ('*.local', '-bad.local', 'bad-.local', 'a.b.local', 'foo.local..',
                    'foo.local:443', 'foo_local', 'é.local', 'K.local', 'a'*64+'.local', 'foo.local\n'):
        run('init', '--directory', root/'invalid', '--device-id', identifier,
            '--hostname', invalid, success=False)
        assert not (root/'invalid').exists()
    run('init', '--directory', root/'invalid', '--device-id', 'b'*31, success=False)
    run('init', '--directory', root/'invalid', '--device', 'test', '--hostname', 'foo.local', success=False)
    max_name = root/'max-name'
    run('renew-server', '--ca-directory', dns_ca, '--device-id', identifier,
        '--hostname', 'b'*63+'.local', '--output', max_name)
    original_manifest = (bundle/'deployment.json').read_bytes()
    for field, value in (('hostname', 'other.local'), ('device_id', identifier.upper()),
                         ('ipv4_sans', ['127.0.0.1']), ('certificate_sha256', '0'*64),
                         ('schema_version', True)):
        changed = dict(manifest); changed[field] = value
        (bundle/'deployment.json').write_text(json.dumps(changed))
        run('validate', '--directory', bundle, success=False)
    (bundle/'deployment.json').write_text(original_manifest.decode().replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'))
    run('validate', '--directory', bundle, success=False)
    (bundle/'deployment.json').unlink()
    run('validate', '--directory', bundle, success=False)
    (bundle/'deployment.json').write_bytes(original_manifest)
    original_key = (bundle/'server.key').read_bytes()
    (bundle/'server.key').write_bytes((dns_renewed/'server.key').read_bytes())
    run('validate', '--directory', bundle, success=False)
    (bundle/'server.key').write_bytes(original_key)
    encrypted = subprocess.run(['openssl', 'pkey', '-in', str(bundle/'server.key'),
        '-aes256', '-passout', 'pass:'], capture_output=True, check=True).stdout
    (bundle/'server.key').write_bytes(encrypted)
    run('validate', '--directory', bundle, success=False)
    (bundle/'server.key').write_bytes(original_key)
    (bundle/'server.key').chmod(0o644)
    run('validate', '--directory', bundle, success=False)
    (bundle/'server.key').chmod(0o600)
    assert json.loads(run('validate', '--directory', ca/'server'))['hostname'] == ''

    # Configure the actual credential CMake gate with inert targets, never firmware/hardware.
    source = root/'cmake-source'; source.mkdir()
    (source/'library').mkdir()
    (source/'library/psa_crypto_random.c').write_text('/* configure-only fixture */')
    (source/'empty.cpp').write_text('// configure-only fixture')
    repo = script.parents[1]
    (source/'CMakeLists.txt').write_text(f'''cmake_minimum_required(VERSION 3.24)
project(CertificateGate LANGUAGES C CXX)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
add_library(WsprryPico STATIC empty.cpp)
add_library(WsprryPico-StandaloneRF STATIC empty.cpp)
add_library(pico_mbedtls INTERFACE)
set(PICO_MBEDTLS_PATH "{source}")
set(CMAKE_SOURCE_DIR "{repo}")
include("{repo}/cmake/network.cmake")
''')
    for credentials in (bundle, ca/'server'):
        result = subprocess.run(['cmake', '-S', str(source), '-B', str(root/'cmake-build'),
            '-DWSPRRY_PICO_NETWORK_PORT=18443', '-DWSPRRY_PICO_NETWORK_CREDENTIAL_DIR='+str(credentials)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        header = (root/'cmake-build/generated/network_credentials.hpp').read_text()
        assert ('hostname[] = "'+(selected if credentials == bundle else '')+'"') in header
        assert (root/'cmake-build').stat().st_mode & 0o077 == 0
        assert (root/'cmake-build/generated/network_credentials.hpp').stat().st_mode & 0o077 == 0
    changed = dict(manifest); changed['hostname'] = 'attacker.local'
    (bundle/'deployment.json').write_text(json.dumps(changed))
    result = subprocess.run(['cmake', '-S', str(source), '-B', str(root/'cmake-build'),
        '-DWSPRRY_PICO_NETWORK_PORT=18443', '-DWSPRRY_PICO_NETWORK_CREDENTIAL_DIR='+str(bundle)], capture_output=True, text=True)
    assert result.returncode != 0
    (bundle/'deployment.json').write_bytes(original_manifest)
    generator = script.parent/'generate_network_test_credentials.py'
    test_credentials = root/'ephemeral'
    subprocess.run([sys.executable, str(generator), str(test_credentials), '--dns-only'], check=True, capture_output=True)
    assert json.loads(run('validate', '--directory', test_credentials))['ipv4_sans'] == []
    # Wrong CA, expired leaf and client-only EKU fail independently of manifest SANs.
    saved_cert = (test_credentials/'server.crt').read_bytes()
    for bad in ('expired.crt', 'client.crt', 'rogue.crt'):
        (test_credentials/'server.crt').write_bytes((test_credentials/bad).read_bytes())
        run('validate', '--directory', test_credentials, success=False)
    (test_credentials/'server.crt').write_bytes(saved_cert)
    saved_ca = (test_credentials/'client-ca.crt').read_bytes()
    (test_credentials/'client-ca.crt').write_bytes((dns_ca/'client-ca.crt').read_bytes())
    run('validate', '--directory', test_credentials, success=False)
    (test_credentials/'client-ca.crt').write_bytes(saved_ca)
    before = (test_credentials/'server.key').read_bytes()
    assert subprocess.run([sys.executable, str(generator), str(test_credentials)], capture_output=True).returncode != 0
    assert (test_credentials/'server.key').read_bytes() == before
print('Certificate DNS/IP, manifest/build, renewal, migration, private export and non-overwrite checks passed')
