#!/usr/bin/env python3
"""Generate ephemeral local-test credentials, never deployment credentials."""
import pathlib
import os
import subprocess
import sys

os.umask(0o077)
out = pathlib.Path(sys.argv[1]).resolve()
out.mkdir(mode=0o700, parents=True, exist_ok=True)

def openssl(*args):
    subprocess.run(['openssl', *args], cwd=out, check=True, capture_output=True)

openssl('req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256', '-nodes',
        '-keyout', 'ca.key', '-out', 'client-ca.crt', '-days', '2', '-subj', '/CN=Ephemeral Pico test CA',
        '-addext', 'basicConstraints=critical,CA:TRUE', '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
for name, usage in [('server', 'serverAuth'), ('client', 'clientAuth'), ('other', 'clientAuth'), ('expired', 'clientAuth')]:
    openssl('req', '-new', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256', '-nodes',
            '-keyout', name + '.key', '-out', name + '.csr', '-subj', '/CN=Ephemeral ' + name)
    (out / (name + '.ext')).write_text('basicConstraints=CA:FALSE\nextendedKeyUsage=' + usage +
                                       '\nsubjectAltName=IP:127.0.0.1\nkeyUsage=digitalSignature\n')
    openssl('x509', '-req', '-in', name + '.csr', '-CA', 'client-ca.crt', '-CAkey', 'ca.key',
            '-CAcreateserial', '-out', name + '.crt', '-days', '1', '-extfile', name + '.ext')
# Explicit historical validity works across OpenSSL versions via the CA command.
(out / 'index.txt').write_text('')
(out / 'serial').write_text('1000\n')
(out / 'ca.cnf').write_text('[ca]\ndefault_ca=test\n[test]\ndatabase=index.txt\nnew_certs_dir=.\nserial=serial\ncertificate=client-ca.crt\nprivate_key=ca.key\ndefault_md=sha256\npolicy=subject\n[subject]\ncommonName=supplied\n')
openssl('ca', '-batch', '-config', 'ca.cnf', '-in', 'expired.csr', '-out', 'expired.crt',
        '-startdate', '20200101000000Z', '-enddate', '20210101000000Z', '-extfile', 'expired.ext', '-notext')
openssl('req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256', '-nodes',
        '-keyout', 'rogue.key', '-out', 'rogue.crt', '-days', '1', '-subj', '/CN=Untrusted client',
        '-addext', 'extendedKeyUsage=clientAuth')
for path in out.glob('*.key'):
    path.chmod(0o600)
print('Generated ephemeral TLS test credentials in', out)
