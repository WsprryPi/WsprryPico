#!/usr/bin/env python3
"""Real OpenSSL P256 credentials plus native production journals; no device I/O."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_populated_fixture as builder
NATIVE=Path(sys.argv.pop(1)).resolve();INSPECTOR=Path(sys.argv.pop(1)).resolve()
OPENSSL=shutil.which('openssl')
class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.baseline=self.root/'baseline.bin'
        self.output=self.root/'populated';self.setup_credentials()
    def tearDown(self):self.temp.cleanup()
    def setup_credentials(self):
        r=self.root;ca=r/'ca.crt';cakey=r/'ca.key';key=r/'server.key';csr=r/'server.csr';server=r/'server.crt'
        host='wsprrypico-0a9d89.local';ou='/OU='+builder.DEVICE
        # Compact synthetic DNs retain the device OU and hostname SAN. Explicit
        # extensions avoid ambient OpenSSL defaults and keep the real P256 TLS
        # object inside the production 2,304-byte canonical limit.
        request_config=r/'request.conf'
        builder.write(request_config,b'[req]\ndistinguished_name=subject\n[subject]\n')
        builder.command([OPENSSL,'req','-new','-x509','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256','-nodes',
            '-config',request_config,'-keyout',cakey,'-out',ca,'-days','365','-subj','/CN=CA'+ou,'-sha256',
            '-addext','basicConstraints=critical,CA:TRUE','-addext','keyUsage=critical,keyCertSign,cRLSign',
            '-addext','subjectKeyIdentifier=hash','-addext','authorityKeyIdentifier=keyid:always'])
        builder.command([OPENSSL,'req','-new','-newkey','ec','-pkeyopt','ec_paramgen_curve:P-256','-nodes',
            '-config',request_config,'-keyout',key,'-out',csr,'-subj',ou,'-sha256'])
        extensions=r/'extensions';builder.write(extensions,('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=serverAuth\nsubjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid:always\nsubjectAltName=DNS:'+host+'\n').encode())
        builder.command([OPENSSL,'x509','-req','-in',csr,'-CA',ca,'-CAkey',cakey,'-set_serial','17','-days','30','-sha256','-extfile',extensions,'-out',server])
        builder.command([OPENSSL,'verify','-x509_strict','-CAfile',ca,'-purpose','sslserver','-verify_hostname',host,server])
        profile=dict(version=1,device_id=builder.DEVICE,owner_epoch='0',owners=[],
            network=dict(ssid='Host Test',password='private-test-password',time_server='time.example.org'),
            station=dict(callsign='K1ABC',locator='FN20',power_dbm=30),
            tls=dict(hostname=host,port=443,ca_certificate=ca.read_text(),ca_private_key=cakey.read_text(),
                server_certificate=server.read_text(),server_private_key=key.read_text(),
                ca_not_after_utc=str(builder.expiry(OPENSSL,ca)),server_not_after_utc=str(builder.expiry(OPENSSL,server))),
            clients=[],request_sha256='a'*64)
        self.profile=profile
        self.assertLessEqual(len(builder.canonical(profile['tls'])),2304)
        config=dict(version=1,enabled=False,station=profile['station'],wifi=dict(ssid='Host Test',password='private-test-password',ntp_ipv4='time.example.org'),schedules=[dict(period_s=240,phase_s=0)],expires_utc_s=0)
        for name,value in (('profile.json',profile),('config.json',config)):builder.write(r/name,builder.canonical(value))
        backup=r/'empty.bin';builder.write(backup,b'\xff'*4194304)
        builder.command([NATIVE,'--backup',backup,'--consumer-profile',r/'profile.json','--config',r/'config.json',
                         '--watermark','1','--output',self.baseline])
    def test_real_populated_roundtrip_two_distinct_csr_and_certificate_bindings(self):
        receipt=builder.build(self.baseline,self.output,INSPECTOR,NATIVE,OPENSSL)
        self.assertEqual((receipt['client_count'],receipt['owner_count'],receipt['schedule_count']),(2,0,2))
        loaded=builder.strict(builder.command([INSPECTOR,self.output/'populated.bin']))
        profile=builder.strict(loaded['profile_payload']);self.assertEqual(profile['tls'],self.profile['tls'])
        self.assertEqual(profile['network'],self.profile['network']);self.assertFalse(loaded['config']['enabled'])
        self.assertEqual(profile['owner_epoch'],'0');self.assertNotEqual(profile['request_sha256'],'a'*64)
        self.assertEqual([c['public_key_sha256'] for c in profile['clients']],sorted(c['public_key_sha256'] for c in profile['clients']))
        for client in profile['clients']:
            der=base64.urlsafe_b64decode(client['csr_der']+'='*((-len(client['csr_der']))%4))
            self.assertLessEqual(len(der),320);self.assertEqual(hashlib.sha256(der).hexdigest(),client['csr_sha256'])
            public=builder.public_der(OPENSSL,csr=self.output/(client['name']+'.csr'))
            self.assertEqual(hashlib.sha256(public).hexdigest(),client['public_key_sha256'])
            self.assertEqual(public,builder.public_der(OPENSSL,certificate=self.output/(client['name']+'.crt')))
            builder.command([OPENSSL,'verify','-x509_strict','-CAfile',self.output/'ca.crt',
                '-purpose','sslclient',self.output/(client['name']+'.crt')])
        original=self.baseline.read_bytes();result=(self.output/'populated.bin').read_bytes()
        self.assertEqual(result[:0x3f7000],original[:0x3f7000]);self.assertEqual(result[0x3ff000:],original[0x3ff000:])
        self.assertNotIn('private-test-password',json.dumps(receipt))
        for path in self.output.iterdir():self.assertEqual(path.stat().st_mode&0o777,0o600)
    def test_owned_network_override_preserves_tls_and_disables_scheduler(self):
        network=dict(ssid='p12-0123456789ab',password='0123456789abcdef0123456789abcdef',time_server='192.168.84.1')
        # Match the actual orchestrator's sorted private_write output rather
        # than supplying an already production-ordered input object.
        path=self.root/'owned-network.json';builder.write(path,json.dumps(network,sort_keys=True,separators=(',',':')).encode())
        receipt=builder.build(self.baseline,self.output,INSPECTOR,NATIVE,OPENSSL,path)
        loaded=builder.strict(builder.command([INSPECTOR,self.output/'populated.bin']))
        generated=builder.strict(loaded['profile_payload'])
        self.assertEqual(generated['network'],network);self.assertEqual(generated['tls'],self.profile['tls'])
        self.assertEqual(loaded['config']['wifi']['ntp_ipv4'],'192.168.84.1');self.assertFalse(loaded['config']['enabled'])
        self.assertEqual(set(receipt['preserved_regions']),{'application','access','ble','E10'})

    def test_population_preserves_nondefault_pin_plan_and_schedule_expiry(self):
        config=builder.strict((self.root/'config.json').read_bytes())
        config['expires_utc_s']=2000000000
        config['pins']=dict(engine='direct',rf_gp=3,i2c_pair=None,button_gp=22,
            amplifier_gp=None,lpf_gps=[],indicator='external',indicator_gp=16,
            indicator_active_high=False)
        (self.root/'config.json').unlink();builder.write(self.root/'config.json',builder.canonical(config))
        self.baseline.unlink()
        builder.command([NATIVE,'--backup',self.root/'empty.bin','--consumer-profile',self.root/'profile.json',
            '--config',self.root/'config.json','--watermark','1','--output',self.baseline])
        before=builder.strict(builder.command([INSPECTOR,self.baseline]))
        builder.build(self.baseline,self.output,INSPECTOR,NATIVE,OPENSSL)
        after=builder.strict(builder.command([INSPECTOR,self.output/'populated.bin']))
        self.assertEqual(after['config']['pins'],before['config']['pins'])
        self.assertEqual(after['config']['expires_utc_s'],2000000000)
        self.assertFalse(after['config']['enabled'])
        self.assertEqual(after['config']['station'],before['config']['station'])
        self.assertEqual(after['config']['wifi'],before['config']['wifi'])
        self.assertEqual(len(after['config']['schedules']),2)

    def test_consumer_profile_without_operational_config_gets_declared_defaults(self):
        original=self.baseline.read_bytes()
        erased=bytearray(original)
        # Store's two config banks occupy 0x3fb000..0x3fcfff. Keep both cursor
        # banks at 0x3fd000..0x3fefff, the consumer profile and E10 untouched.
        erased[0x3fb000:0x3fd000]=b'\xff'*8192
        self.baseline.unlink();builder.write(self.baseline,erased)
        before=builder.strict(builder.command([INSPECTOR,self.baseline]))
        self.assertTrue(before['profile_healthy']);self.assertTrue(before['operational_healthy'])
        self.assertEqual(before['profile_source'],5);self.assertIsNone(before['config'])
        self.assertEqual(before['watermark'],1)
        self.assertEqual(erased[:0x3fb000],original[:0x3fb000])
        self.assertEqual(erased[0x3fd000:],original[0x3fd000:])
        receipt=builder.build(self.baseline,self.output,INSPECTOR,NATIVE,OPENSSL)
        after=builder.strict(builder.command([INSPECTOR,self.output/'populated.bin']))
        expected=dict(version=1,enabled=False,station=self.profile['station'],
            wifi=dict(ssid='Host Test',password='private-test-password',ntp_ipv4='time.example.org'),
            schedules=[dict(period_s=240,phase_s=0),dict(period_s=240,phase_s=120)],expires_utc_s=0)
        self.assertEqual(after['config'],expected)
        self.assertNotIn('pins',after['config']) # Source-defined default plan.
        self.assertEqual(builder.strict(after['profile_payload'])['tls'],self.profile['tls'])
        self.assertGreater(after['watermark'],before['watermark'])
        result=(self.output/'populated.bin').read_bytes()
        self.assertEqual(result[:0x3f7000],erased[:0x3f7000])
        self.assertEqual(result[0x3ff000:],erased[0x3ff000:])
        self.assertEqual(set(receipt['preserved_regions']),{'application','access','ble','E10'})

    def test_private_inputs_and_existing_output_fail_before_seeding(self):
        self.output.mkdir();(self.output/'keep').write_bytes(b'keep')
        with self.assertRaises(ValueError):builder.build(self.baseline,self.output,INSPECTOR,NATIVE,OPENSSL)
        self.assertEqual((self.output/'keep').read_bytes(),b'keep')
        self.baseline.chmod(0o644)
        with self.assertRaises(ValueError):builder.build(self.baseline,self.root/'other',INSPECTOR,NATIVE,OPENSSL)
        self.assertFalse((self.root/'other').exists())
    def test_wrong_B_inspector_result_rejected_before_any_credentials_written(self):
        loaded=builder.strict(builder.command([INSPECTOR,self.baseline]));profile=builder.strict(loaded['profile_payload']);profile['device_id']='0'*32
        loaded['profile_payload']=builder.canonical(profile).decode()
        with patch.object(builder,'command',return_value=builder.canonical(loaded)):
            with self.assertRaises(ValueError):builder.build(self.baseline,self.output,INSPECTOR,NATIVE,OPENSSL)
        self.assertFalse(self.output.exists())
    def test_canonical_control_escapes_and_source_key_preservation(self):
        value={'pem':'first\nlast\r\t','quoted':'a"b\\c'};encoded=builder.canonical(value)
        self.assertIn(b'\\u000a',encoded);self.assertNotIn(b'\\n',encoded);self.assertEqual(builder.strict(encoded),value)
if __name__=='__main__':unittest.main()
