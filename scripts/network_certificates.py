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


def device_id(value):
    if not re.fullmatch(r'[0-9a-fA-F]{32}', value):
        raise argparse.ArgumentTypeError('Device ID must contain exactly 32 hexadecimal characters')
    return value.lower()


def hostname(value):
    if not value.isascii():
        raise argparse.ArgumentTypeError('Hostname must use ASCII only')
    value = value.lower()
    if value.endswith('.'):
        value = value[:-1]
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.local', value):
        raise argparse.ArgumentTypeError('Hostname must be one 1–63 character LDH label followed by .local')
    return value


def mac_address(value):
    if not re.fullmatch(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}', value):
        raise argparse.ArgumentTypeError('MAC address must contain six colon-separated hex bytes')
    octets = bytes.fromhex(value.replace(':', ''))
    if octets[0] & 1 or not any(octets):
        raise argparse.ArgumentTypeError('MAC address must be a nonzero unicast station address')
    return value.lower()


def certificate_sans(path):
    public = openssl('x509', '-in', path, '-noout', '-ext', 'subjectAltName')
    lines = public.strip().splitlines()
    if not lines or lines[0].strip() not in ('X509v3 Subject Alternative Name:', 'X509v3 Subject Alternative Name: critical'):
        raise ValueError('Server certificate requires a subjectAltName extension')
    dns, ips = [], []
    for entry in ''.join(lines[1:]).strip().split(', '):
        if entry.startswith('DNS:'):
            dns.append(entry[4:])
        elif entry.startswith('IP Address:'):
            ips.append(str(ipaddress.IPv4Address(entry[11:])))
        else:
            raise ValueError('Only exact DNS and IPv4 certificate SANs are supported')
    if len(set(dns)) != len(dns) or len(set(ips)) != len(ips):
        raise ValueError('Duplicate server SANs are not supported')
    return sorted(dns), sorted(ips)


def certificate_fingerprint(path):
    return openssl('x509', '-in', path, '-noout', '-fingerprint', '-sha256').strip().split('=', 1)[1].replace(':', '').lower()


def write_manifest(directory, identifier, selected_hostname, addresses):
    manifest = {'schema_version': 1, 'device_id': identifier, 'hostname': selected_hostname,
                'ipv4_sans': sorted(map(str, addresses)),
                'certificate_sha256': certificate_fingerprint(directory / 'server.crt')}
    with (directory / 'deployment.json').open('x') as output:
        json.dump(manifest, output, indent=2)
        output.write('\n')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate deployment manifest field')
        result[key] = value
    return result


def validate_bundle(directory):
    directory = Path(directory)
    cert, key, ca = [directory / item for item in ('server.crt', 'server.key', 'client-ca.crt')]
    for path in (cert, key, ca):
        if path.stat().st_size > 65536:
            raise ValueError('Credential exceeds the build input bound')
    if b'ENCRYPTED' in key.read_bytes():
        raise ValueError('Firmware requires an unencrypted owner-only private key')
    if key.stat().st_mode & 0o077:
        raise ValueError('Server private key must not be accessible to group or others')
    # This validates signatures, validity and server purpose, independently of metadata.
    openssl('verify', '-purpose', 'sslserver', '-CAfile', ca, cert)
    if openssl('x509', '-in', cert, '-pubkey', '-noout') != openssl('pkey', '-in', key, '-passin', 'pass:', '-pubout'):
        raise ValueError('Server certificate and private key do not match')
    dns, ips = certificate_sans(cert)
    manifest_path = directory / 'deployment.json'
    if not manifest_path.exists():
        if dns or not ips:
            raise ValueError('Hostname certificates require a deployment.json manifest; legacy requires IP-only SANs')
        return {'schema_version': 1, 'device_id': '', 'hostname': '', 'ipv4_sans': ips,
                'certificate_sha256': certificate_fingerprint(cert)}
    if manifest_path.stat().st_size > 4096:
        raise ValueError('Deployment manifest exceeds 4096 bytes')
    manifest = json.loads(manifest_path.read_text(), object_pairs_hook=unique_object)
    keys = {'schema_version', 'device_id', 'hostname', 'ipv4_sans', 'certificate_sha256'}
    if not isinstance(manifest, dict) or set(manifest) != keys or type(manifest['schema_version']) is not int or manifest['schema_version'] != 1:
        raise ValueError('Invalid deployment manifest schema')
    identifier, selected = manifest['device_id'], manifest['hostname']
    if not isinstance(identifier, str) or device_id(identifier) != identifier:
        raise ValueError('Manifest device ID must be canonical')
    if not isinstance(selected, str) or hostname(selected) != selected:
        raise ValueError('Manifest hostname must be canonical')
    addresses = manifest['ipv4_sans']
    if not isinstance(addresses, list) or len(addresses) > 4 or any(not isinstance(address, str) for address in addresses):
        raise ValueError('Manifest requires at most four IPv4 SAN strings')
    if sorted(str(ipaddress.IPv4Address(address)) for address in addresses) != ips or dns != [selected]:
        raise ValueError('Certificate SANs disagree with deployment manifest')
    if manifest['certificate_sha256'] != certificate_fingerprint(cert):
        raise ValueError('Certificate fingerprint disagrees with deployment manifest')
    return manifest


def server_identity(args):
    addresses = args.address or []
    if len(addresses) > 4 or len(set(addresses)) != len(addresses):
        raise ValueError('Use at most four distinct IPv4 SANs')
    if (args.hostname or args.mac_address) and not args.device_id:
        raise ValueError('--hostname and --mac-address require the stable WTP --device-id')
    if args.device_id and not args.hostname and not args.mac_address:
        raise ValueError('Default hostname requires observed --mac-address; use --hostname for an explicit alias')
    selected = args.hostname or ('wsprrypico-' + args.mac_address.replace(':', '')[-6:] + '.local'
                                 if args.mac_address else None)
    if not args.device and not args.device_id:
        raise ValueError('Provide --device-id for hostname deployment or --device for legacy IP deployment')
    if not selected and not addresses:
        raise ValueError('Legacy deployment requires --address; normal deployment requires --device-id')
    return args.device or args.device_id, selected, addresses


def private_path(value):
    path = Path(value).expanduser().resolve()
    if path.is_relative_to(ROOT) and not path.is_relative_to(ROOT / 'config/local'):
        raise ValueError('Repository credentials must be under ignored config/local/')
    return path


def new_directory(value):
    path = private_path(value)
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    return path


def issue(ca, destination, common_name, usage, addresses=(), selected_hostname=None, days=365):
    with tempfile.TemporaryDirectory(dir=destination) as temporary:
        temp = Path(temporary)
        key, cert = destination / ('server.key' if usage == 'serverAuth' else 'client.key'), destination / ('server.crt' if usage == 'serverAuth' else 'client.crt')
        openssl('req', '-new', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256', '-nodes',
                '-keyout', key, '-out', temp / 'request.csr', '-subj', '/CN=' + common_name)
        key.chmod(0o600)
        extensions = 'basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=' + usage + '\n'
        sans = (['DNS:' + selected_hostname] if selected_hostname else []) + ['IP:' + str(address) for address in addresses]
        if sans:
            extensions += 'subjectAltName=' + ','.join(sans) + '\n'
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
    init.add_argument('--device', type=name, help='Optional descriptive label; required for legacy IP-only deployment')
    client = commands.add_parser('issue-client', help='Issue a separate identity for a browser or WTP controller')
    client.add_argument('--ca-directory', required=True)
    client.add_argument('--name', type=name, required=True)
    client.add_argument('--output', required=True)
    renew = commands.add_parser('renew-server', help='Create a replacement build bundle; preserve existing credentials')
    renew.add_argument('--ca-directory', required=True)
    renew.add_argument('--device', type=name)
    renew.add_argument('--output', required=True)
    for command in (init, renew):
        command.add_argument('--device-id', type=device_id, help='Stable WTP device identity from existing INFO/HELLO')
        command.add_argument('--hostname', type=hostname, help='Optional deliberate build-time .local alias')
        command.add_argument('--mac-address', type=mac_address, help='Observed Wi-Fi station MAC; required for the default short hostname')
        command.add_argument('--address', type=ipaddress.IPv4Address, action='append', help='Optional explicit IPv4 SAN; repeat up to four times')
    validate = commands.add_parser('validate', help='Validate actual server credentials and public deployment identity for builds')
    validate.add_argument('--directory', required=True)
    export = commands.add_parser('export-browser', help='Export a password-protected PKCS#12 browser identity')
    export.add_argument('--client-directory', required=True)
    export.add_argument('--output', required=True)
    export.add_argument('--password-file', help='Optional private file; otherwise prompt without echo')
    export.add_argument('--macos-keychain', action='store_true',
                        help='Use explicit legacy PKCS#12 wrapping for macOS Keychain import; TLS policy is unchanged')
    inspect = commands.add_parser('inspect', help='Show identities and expiration; does not print private keys')
    inspect.add_argument('--directory', required=True)
    args = parser.parse_args(argv)
    os.umask(0o077)
    if args.command == 'validate':
        print(json.dumps(validate_bundle(Path(args.directory).expanduser().resolve()), sort_keys=True))
    elif args.command == 'init':
        common_name, selected, addresses = server_identity(args)
        directory = new_directory(args.directory)
        openssl('req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:P-256', '-nodes',
                '-keyout', directory / 'ca.key', '-out', directory / 'client-ca.crt', '-days', '3650',
                '-subj', '/CN=' + common_name + ' device CA', '-addext', 'basicConstraints=critical,CA:TRUE',
                '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
        (directory / 'ca.key').chmod(0o600)
        bundle = new_directory(directory / 'server')
        issue(directory, bundle, common_name, 'serverAuth', addresses, selected)
        if selected:
            write_manifest(bundle, args.device_id, selected, addresses)
        validate_bundle(bundle)
        print('CA:', directory, '\nBuild credential directory:', bundle)
    elif args.command in ('issue-client', 'renew-server'):
        ca = private_path(args.ca_directory)
        if args.command == 'renew-server':
            common_name, selected, addresses = server_identity(args)
        directory = new_directory(args.output)
        if args.command == 'issue-client':
            issue(ca, directory, args.name, 'clientAuth')
        else:
            issue(ca, directory, common_name, 'serverAuth', addresses, selected)
            if selected:
                write_manifest(directory, args.device_id, selected, addresses)
            validate_bundle(directory)
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
            # Keychain rejects the OpenSSL 3 default PBES2/AES/SHA-256 package
            # on the physically tested Mac. Keep the modern default elsewhere;
            # this opt-in changes only password wrapping, not certificate/TLS
            # algorithms, identities, validity, trust or private-file policy.
            wrapping = (['-keypbe', 'PBE-SHA1-3DES', '-certpbe', 'PBE-SHA1-3DES',
                         '-macalg', 'sha1'] if args.macos_keychain else [])
            openssl('pkcs12', '-export', '-in', directory / 'client.crt', '-inkey', directory / 'client.key',
                    '-certfile', directory / 'client-ca.crt', '-out', output, *wrapping,
                    '-passout', 'stdin', data=(password+'\n').encode())
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
            results.append({'path':str(path), 'renew_within_30_days':expires <= datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30), 'certificate':public.strip(), 'subject_alt_name':openssl('x509', '-in', path, '-noout', '-ext', 'subjectAltName').strip()})
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, argparse.ArgumentTypeError) as error:
        raise SystemExit(str(error))
