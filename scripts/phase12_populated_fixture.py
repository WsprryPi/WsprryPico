#!/usr/bin/env python3
"""Offline private populated B snapshot using real retained TLS and P256 CSRs.

No device, network or RF actions. Native production journals validate output.
Only a redacted receipt is printed. Client public-key digest is DER SPKI SHA256.
"""
import argparse
import base64
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import time
from phase12_recovery_device import DEVICE, strict

SPKI_PREFIX=bytes.fromhex('3059301306072a8648ce3d020106082a8648ce3d030107034200')


def require(ok,message):
    if not ok:raise ValueError(message)


def canonical(value):
    return json.dumps(value,separators=(',',':'),ensure_ascii=False).replace('\\n','\\u000a').replace('\\r','\\u000d').replace('\\t','\\u0009').encode()


def private_read(path,maximum):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        metadata=os.fstat(fd)
        require(stat.S_ISREG(metadata.st_mode) and metadata.st_mode&0o077==0 and
                0<=metadata.st_size<=maximum,'private bounded input required')
        with os.fdopen(fd,'rb',closefd=False) as file:data=file.read(maximum+1)
        require(len(data)==metadata.st_size,'input changed/oversize')
        return data
    finally:os.close(fd)


def write(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as file:
        os.fchmod(file.fileno(),0o600);file.write(data);file.flush();os.fsync(file.fileno())


def command(args,input=None):
    result=subprocess.run([str(v) for v in args],input=input,capture_output=True,timeout=30)
    require(result.returncode==0,'offline command failed (private diagnostics retained only in memory)')
    require(len(result.stdout)<=131072,'bounded command output');return result.stdout


def expiry(openssl,certificate):
    text=command([openssl,'x509','-in',certificate,'-noout','-enddate']).decode().strip()
    require(text.startswith('notAfter='),'certificate expiry')
    value=datetime.datetime.strptime(text[9:],'%b %d %H:%M:%S %Y GMT').replace(tzinfo=datetime.timezone.utc)
    return int(value.timestamp())


def public_der(openssl,key=None,certificate=None,csr=None):
    if key:return command([openssl,'pkey','-in',key,'-pubout','-outform','DER'])
    kind='x509' if certificate else 'req';path=certificate or csr
    public=command([openssl,kind,'-in',path,'-pubkey','-noout'])
    return command([openssl,'pkey','-pubin','-outform','DER'],input=public)


def p256(raw):
    require(len(raw)==len(SPKI_PREFIX)+65 and raw.startswith(SPKI_PREFIX) and raw[len(SPKI_PREFIX)]==4,
            'actual P256 uncompressed SPKI required')


def build(backup,output_dir,inspector,native,openssl='openssl',network_file=None):
    os.umask(0o077)
    baseline=private_read(backup,4194304);require(len(baseline)==4194304,'exact full flash')
    require(not output_dir.exists() and not output_dir.is_symlink(),'new private output directory required')
    # Production loader output contains secrets: never forward stdout/stderr.
    loaded=strict(command([inspector,backup]))
    require(loaded['profile_healthy'] is True and loaded['profile_source']==5 and
            loaded['operational_healthy'] is True,'healthy consumer baseline journals')
    prior=strict(loaded['profile_payload'])
    require(prior['device_id']==DEVICE and prior['version']==1,'actual B TLS-complete profile')
    output_dir.mkdir(mode=0o700)
    tls=prior['tls']
    for field,name in (('ca_certificate','ca.crt'),('ca_private_key','ca.key'),
                       ('server_certificate','server.crt'),('server_private_key','server.key')):
        write(output_dir/name,tls[field].encode())
    ca,ca_key,server,server_key=[output_dir/name for name in ('ca.crt','ca.key','server.crt','server.key')]
    for certificate,key in ((ca,ca_key),(server,server_key)):
        cert_public=public_der(openssl,certificate=certificate);key_public=public_der(openssl,key=key)
        p256(cert_public);require(cert_public==key_public,'retained TLS key pair mismatch')
        details=command([openssl,'x509','-in',certificate,'-noout','-text']).decode()
        require('Signature Algorithm: ecdsa-with-SHA256' in details and 'ASN1 OID: prime256v1' in details,
                'retained TLS P256/SHA256 credential contract')
        subject=command([openssl,'x509','-in',certificate,'-noout','-subject','-issuer','-nameopt','RFC2253']).decode()
        require(subject.count('OU='+DEVICE)==2,'retained exact device OU identity')
    command([openssl,'verify','-CAfile',ca,'-purpose','sslserver','-verify_hostname',tls['hostname'],server])
    ca_expiry=expiry(openssl,ca);server_expiry=expiry(openssl,server)
    require(ca_expiry==int(tls['ca_not_after_utc']) and server_expiry==int(tls['server_not_after_utc']) and
            time.time()+90000<min(ca_expiry,server_expiry),'actual retained certificate date binding')
    profile=copy.deepcopy(prior)
    if network_file is not None:
        network=strict(private_read(network_file,2048))
        require(set(network)=={'ssid','password','time_server'},'exact private network object')
        # The production parser requires its serializer's field order. Private
        # host writers may sort JSON keys, so rebuild the typed network object.
        profile['network']={key:network[key] for key in ('ssid','password','time_server')}
    # Production open setup intentionally preserves zero owner keys/epoch0.
    profile['owner_epoch']=prior['owner_epoch']
    profile['request_sha256']=secrets.token_hex(32)
    require(profile['request_sha256']!=prior['request_sha256'],'new request binding')
    extensions=output_dir/'client-extensions.conf'
    write(extensions,b'basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=clientAuth\n')
    clients=[];serials=set()
    for index in (1,2):
        name='p12-'+str(index);key=output_dir/(name+'.key');csr=output_dir/(name+'.csr');cert=output_dir/(name+'.crt')
        command([openssl,'req','-new','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256','-nodes',
            '-keyout',key,'-out',csr,'-subj','/CN='+name,'-sha256',
            '-addext','basicConstraints=critical,CA:FALSE','-addext','keyUsage=critical,digitalSignature',
            '-addext','extendedKeyUsage=clientAuth']);key.chmod(0o600);csr.chmod(0o600)
        command([openssl,'req','-in',csr,'-verify','-noout'])
        der=command([openssl,'req','-in',csr,'-outform','DER']);require(1<=len(der)<=320,'CSR exceeds production320byte bound')
        csr_public=public_der(openssl,csr=csr);p256(csr_public)
        require(csr_public==public_der(openssl,key=key),'CSR/private key binding')
        text=command([openssl,'req','-in',csr,'-noout','-text']).decode()
        require('TLS Web Client Authentication' in text and 'TLS Web Server Authentication' not in text and
                'CA:FALSE' in text and 'Digital Signature' in text,'clientAuth-only CSR purpose')
        serial=int.from_bytes(secrets.token_bytes(8),'big') or index
        require(serial not in serials,'unique nonzero client serial');serials.add(serial)
        command([openssl,'x509','-req','-in',csr,'-CA',ca,'-CAkey',ca_key,'-set_serial',str(serial),
                 '-days','1','-sha256','-extfile',extensions,'-out',cert]);cert.chmod(0o600)
        command([openssl,'verify','-CAfile',ca,'-purpose','sslclient',cert])
        expires=expiry(openssl,cert);require(expires<=ca_expiry,'client lifetime within CA')
        require(public_der(openssl,certificate=cert)==csr_public,'issued exact client public key')
        clients.append(dict(name=name,csr_der=base64.urlsafe_b64encode(der).decode().rstrip('='),
            csr_sha256=hashlib.sha256(der).hexdigest(),public_key_sha256=hashlib.sha256(csr_public).hexdigest(),
            serial=str(serial),not_after_utc=str(expires)))
    profile['clients']=sorted(clients,key=lambda value:value['public_key_sha256'])
    network=profile['network'];station=profile['station']
    config=dict(version=1,enabled=False,station=copy.deepcopy(station),
        wifi=dict(ssid=network['ssid'],password=network['password'],ntp_ipv4=network['time_server']),
        schedules=[dict(period_s=240,phase_s=0),dict(period_s=240,phase_s=120)],expires_utc_s=0)
    watermark=max(int(loaded['watermark'])+1,time.time_ns())
    require(0<watermark<=2**64-1,'watermark range')
    profile_path=output_dir/'consumer-profile.json';config_path=output_dir/'config.json';result=output_dir/'populated.bin'
    write(profile_path,canonical(profile));write(config_path,canonical(config))
    command([native,'--backup',backup,'--consumer-profile',profile_path,'--config',config_path,
             '--watermark',str(watermark),'--output',result])
    after=strict(command([inspector,result]));require(after['profile_healthy'] and after['operational_healthy'] and
        after['profile_payload'].encode()==canonical(profile) and after['config']==config and
        after['watermark']==watermark,'native exact production readback')
    generated=private_read(result,4194304)
    require(generated[:0x3f7000]==baseline[:0x3f7000] and generated[0x3ff000:]==baseline[0x3ff000:],
            'application/access/BLE/E10 preservation')
    require(private_read(backup,4194304)==baseline,'baseline file changed')
    receipt=dict(status='OFFLINE_POPULATED_FIXTURE_READY',device_id=DEVICE,baseline_sha256=hashlib.sha256(baseline).hexdigest(),
        fixture_sha256=hashlib.sha256(generated).hexdigest(),client_count=2,owner_count=len(profile['owners']),
        schedule_count=2,enabled=False,watermark=str(watermark),public_key_digest_encoding='SHA256_DER_SPKI',
        preserved_regions={name:hashlib.sha256(baseline[start:end]).hexdigest() for name,start,end in
            [('application',0,0x3f3000),('access',0x3f3000,0x3f5000),
             ('ble',0x3f5000,0x3f7000),('E10',0x3ff000,4194304)]},
        rf_jobs=0,physical_acceptance=False)
    write(output_dir/'receipt.json',canonical(receipt))
    fd=os.open(output_dir,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for field in ('backup','output-dir','inspector','native'):parser.add_argument('--'+field,type=Path,required=True)
    parser.add_argument('--openssl',default='openssl');parser.add_argument('--network-file',type=Path)
    args=parser.parse_args()
    print(json.dumps(build(args.backup,args.output_dir,args.inspector,args.native,args.openssl,args.network_file)))
if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps(dict(status='OFFLINE_FIXTURE_STOPPED',error_type=type(error).__name__)))
        raise SystemExit(1)
