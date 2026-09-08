#!/usr/bin/env python3
"""Local, per-device certificate lifecycle. Never installs trust or accesses a Pico."""
import argparse
import datetime
import getpass
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def openssl(*args, data=None):
    result = subprocess.run(['openssl', *map(str, args)], input=data, capture_output=True)
    if result.returncode:
        raise RuntimeError('OpenSSL failed: ' + result.stderr.decode(errors='replace').strip())
    return result.stdout.decode()


def name(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,63}', value):
        raise argparse.ArgumentTypeError('Use 1–64 letters, digits, dots or hyphens')
    return value


def private_path(value):
    path = Path(value).expanduser().resolve()
    if path.is_relative_to(ROOT) and not path.is_relative_to(ROOT / 'config/local'):
        raise ValueError('Repository credentials must be under ignored config/local/')
    return path


def new_directory(value):
    path = private_path(value)
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    return path


def issue(ca, destination, common_name, usage, address=None, days=365):
    with tempfile.TemporaryDirectory(dir=destination) as temporary:
        temp = Path(temporary)
        key, cert = destination / ('server.key' if usage == 'serverAuth' else 'client.key'), destination / ('server.crt' if usage == 'serverAuth' else 'client.crt')
        openssl('req', '-new', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256', '-nodes',
                '-keyout', key, '-out', temp / 'request.csr', '-subj', '/CN=' + common_name)
        key.chmod(0o600)
        extensions = 'basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=' + usage + '\n'
        if address:
            extensions += 'subjectAltName=IP:' + str(ipaddress.IPv4Address(address)) + '\n'
        (temp / 'extensions').write_text(extensions)
        openssl('x509', '-req', '-in', temp / 'request.csr', '-CA', ca / 'client-ca.crt', '-CAkey', ca / 'ca.key',
                '-set_serial', '0x' + os.urandom(16).hex(), '-days', days, '-extfile', temp / 'extensions', '-out', cert)
        (destination / 'client-ca.crt').write_bytes((ca / 'client-ca.crt').read_bytes())
    return cert


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init', help='Create one device CA and initial server build bundle')
    init.add_argument('--directory', required=True)
    init.add_argument('--device', type=name, required=True)
    init.add_argument('--address', type=ipaddress.IPv4Address, required=True)
    client = commands.add_parser('issue-client', help='Issue a separate identity for a browser or WTP controller')
    client.add_argument('--ca-directory', required=True)
    client.add_argument('--name', type=name, required=True)
    client.add_argument('--output', required=True)
    renew = commands.add_parser('renew-server', help='Create a replacement build bundle; preserve existing credentials')
    renew.add_argument('--ca-directory', required=True)
    renew.add_argument('--device', type=name, required=True)
    renew.add_argument('--address', type=ipaddress.IPv4Address, required=True)
    renew.add_argument('--output', required=True)
    export = commands.add_parser('export-browser', help='Export a password-protected PKCS#12 browser identity')
    export.add_argument('--client-directory', required=True)
    export.add_argument('--output', required=True)
    export.add_argument('--password-file', help='Optional private file; otherwise prompt without echo')
    inspect = commands.add_parser('inspect', help='Show identities and expiration; does not print private keys')
    inspect.add_argument('--directory', required=True)
    args = parser.parse_args(argv)
    os.umask(0o077)
    if args.command == 'init':
        directory = new_directory(args.directory)
        openssl('req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256', '-nodes',
                '-keyout', directory / 'ca.key', '-out', directory / 'client-ca.crt', '-days', '3650',
                '-subj', '/CN=' + args.device + ' device CA', '-addext', 'basicConstraints=critical,CA:TRUE',
                '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
        (directory / 'ca.key').chmod(0o600)
        bundle = new_directory(directory / 'server')
        issue(directory, bundle, args.device, 'serverAuth', args.address)
        print('CA:', directory, '\nBuild credential directory:', bundle)
    elif args.command in ('issue-client', 'renew-server'):
        ca = private_path(args.ca_directory)
        directory = new_directory(args.output)
        issue(ca, directory, args.name if args.command == 'issue-client' else args.device,
              'clientAuth' if args.command == 'issue-client' else 'serverAuth', getattr(args, 'address', None))
        print('New credential bundle:', directory)
    elif args.command == 'export-browser':
        directory = private_path(args.client_directory)
        output = private_path(args.output)
        if args.password_file:
            password_path = private_path(args.password_file)
            if password_path.stat().st_mode & 0o077:
                raise ValueError('Password file must not be accessible to group or others')
            password = password_path.read_text().rstrip('\n')
        else:
            password = getpass.getpass('PKCS#12 password: ')
            if password != getpass.getpass('Repeat password: '):
                raise ValueError('Passwords do not match')
        if len(password) < 12 or '\n' in password or '\r' in password:
            raise ValueError('Use a password of at least 12 characters without line breaks')
        # Reserve the output exclusively; never overwrite an earlier identity.
        with output.open('xb'):
            pass
        try:
            openssl('pkcs12', '-export', '-in', directory / 'client.crt', '-inkey', directory / 'client.key',
                    '-certfile', directory / 'client-ca.crt', '-out', output, '-passout', 'stdin', data=(password+'\n').encode())
        except Exception:
            output.unlink()
            raise
        output.chmod(0o600)
        print('Browser identity:', output)
    else:
        directory = private_path(args.directory)
        results = []
        for path in sorted(directory.rglob('*.crt')):
            public = openssl('x509', '-in', path, '-noout', '-subject', '-issuer', '-dates', '-fingerprint', '-sha256')
            expiry = openssl('x509', '-in', path, '-noout', '-enddate').strip().split('=',1)[1]
            expires = datetime.datetime.strptime(expiry, '%b %d %H:%M:%S %Y %Z').replace(tzinfo=datetime.timezone.utc)
            results.append({'path':str(path), 'renew_within_30_days':expires <= datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30), 'certificate':public.strip()})
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        raise SystemExit(str(error))
