#!/usr/bin/env python3
"""Native production-loader roundtrip; dummy PEM/CSR are host structural fixtures."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
FIXTURE=sys.argv.pop(1);INSPECTOR=sys.argv.pop(1)
DEVICE='29f20b7342051ef947aa56cb9d4fab42'
def compact(value):return json.dumps(value,separators=(',',':')).replace('\\n','\\u000a').replace('\\r','\\u000d').replace('\\t','\\u0009')
def profile():
    cert='-----BEGIN CERTIFICATE-----\nAQ==\n-----END CERTIFICATE-----\n'
    key='-----BEGIN PRIVATE KEY-----\nAQ==\n-----END PRIVATE KEY-----\n'
    clients=[]
    for i in (1,2):
        der=bytes((48,i,0))
        clients.append(dict(name='host-only-'+str(i),csr_der=base64.urlsafe_b64encode(der).decode().rstrip('='),
            csr_sha256=hashlib.sha256(der).hexdigest(),public_key_sha256=str(i)*64,
            serial=str(i),not_after_utc='1800000000'))
    return dict(version=1,device_id=DEVICE,owner_epoch='1',
        owners=[base64.urlsafe_b64encode(b'\x04'+bytes(64)).decode().rstrip('=')],
        network=dict(ssid='Host fixture',password='private-test-password',time_server='time.example.org'),
        station=dict(callsign='K1ABC',locator='FN20',power_dbm=30),
        tls=dict(hostname='wsprrypico-0a9d89.local',port=443,ca_certificate=cert,ca_private_key=key,
                 server_certificate=cert,server_private_key=key,ca_not_after_utc='2000000000',server_not_after_utc='1800000000'),
        clients=clients,request_sha256='a'*64)
def config():
    return dict(version=1,enabled=False,station=dict(callsign='K1ABC',locator='FN20',power_dbm=30),
                wifi=dict(ssid='Host fixture',password='private-test-password',ntp_ipv4='time.example.org'),
                schedules=[dict(period_s=240,phase_s=0),dict(period_s=240,phase_s=120)],expires_utc_s=0)
class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        data=bytearray(b'Q'*4194304);data[0x3f7000:0x3ff000]=b'\xff'*32768
        self.original=bytes(data)
        self.files={name:self.root/name for name in ('backup','profile','config','output')}
        self.write('backup',self.original);self.write('profile',compact(profile()).encode());self.write('config',compact(config()).encode())
    def tearDown(self):self.temp.cleanup()
    def write(self,name,value):self.files[name].write_bytes(value);self.files[name].chmod(0o600)
    def run_tool(self,watermark='123456789',extra=()):
        return subprocess.run([FIXTURE,'--backup',str(self.files['backup']),'--consumer-profile',str(self.files['profile']),
            '--config',str(self.files['config']),'--watermark',watermark,'--output',str(self.files['output']),*extra],capture_output=True)
    def refuse(self,watermark='123456789'):
        result=self.run_tool(watermark);self.assertNotEqual(result.returncode,0);self.assertFalse(self.files['output'].exists())
        self.assertNotIn(b'private-test-password',result.stdout+result.stderr)
    def test_roundtrip_two_clients_config_schedule_watermark_and_untouched_regions(self):
        result=self.run_tool();self.assertEqual(result.returncode,0,result.stderr)
        output=self.files['output'].read_bytes();self.assertEqual(len(output),4194304)
        self.assertEqual(output[:0x3f7000],self.original[:0x3f7000]);self.assertEqual(output[0x3ff000:],self.original[0x3ff000:])
        self.assertNotEqual(output[0x3f7000:0x3ff000],self.original[0x3f7000:0x3ff000])
        self.assertEqual(self.files['output'].stat().st_mode&0o777,0o600)
        decoded=json.loads(subprocess.check_output([INSPECTOR,str(self.files['output'])]))
        self.assertTrue(decoded['profile_healthy']);self.assertEqual(json.loads(decoded['profile_payload']),profile())
        self.assertEqual(decoded['config'],config());self.assertEqual(decoded['watermark'],123456789)
        self.assertNotIn(b'private-test-password',result.stdout)
    def test_existing_committed_journals_increment_and_refuse_watermark_regression(self):
        first=self.run_tool();self.assertEqual(first.returncode,0,first.stderr)
        seeded=self.files['output'].read_bytes();self.files['output'].unlink();self.write('backup',seeded)
        self.refuse('123456789')
        changed=profile();changed['station']['callsign']='N0CALL';changed['request_sha256']='b'*64;self.write('profile',compact(changed).encode())
        second=self.run_tool('123456790');self.assertEqual(second.returncode,0,second.stderr)
        loaded=json.loads(subprocess.check_output([INSPECTOR,str(self.files['output'])]))
        self.assertEqual(loaded['profile_sequence'],2);self.assertEqual(loaded['watermark'],123456790)
        self.assertEqual(json.loads(loaded['profile_payload']),changed)
        output=self.files['output'].read_bytes()
        self.assertEqual(output[:0x3f7000],seeded[:0x3f7000]);self.assertEqual(output[0x3ff000:],seeded[0x3ff000:])

    def test_noncanonical_wrong_device_and_enabled_empty_schedule(self):
        for kind in ('noncanonical','wrong-device','enabled','empty','invalid-schedule'):
            with self.subTest(kind=kind):
                p=profile();c=config()
                if kind=='noncanonical':self.write('profile',json.dumps(p,indent=2).encode())
                else:
                    if kind=='wrong-device':p['device_id']='0'*32
                    self.write('profile',compact(p).encode())
                if kind=='enabled':c['enabled']=True
                if kind=='empty':c['schedules']=[]
                if kind=='invalid-schedule':c['schedules'][0]['period_s']=121
                self.write('config',compact(c).encode());self.refuse()
    def test_bad_watermark_and_size_no_result(self):
        for value in ('0','01','-1','18446744073709551616','1junk'):self.refuse(value)
        self.write('backup',self.original[:-1]);self.refuse()
        self.write('backup',self.original+b'x');self.refuse()
    def test_corrupt_journal_refused(self):
        bad=bytearray(self.original);bad[0x3f7000:0x3f7100]=b'\x00'*256
        self.write('backup',bad);self.refuse()
    def test_no_overwrite_or_symlink_output_and_inputs_private(self):
        self.write('output',b'keep');result=self.run_tool();self.assertNotEqual(result.returncode,0);self.assertEqual(self.files['output'].read_bytes(),b'keep')
        self.files['output'].unlink();self.files['output'].symlink_to(self.files['backup']);result=self.run_tool();self.assertNotEqual(result.returncode,0);self.assertEqual(self.files['backup'].read_bytes(),self.original)
        self.files['output'].unlink();self.files['profile'].chmod(0o644);self.refuse()
    def test_malformed_arguments(self):
        result=subprocess.run([FIXTURE,'--backup',str(self.files['backup'])],capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertFalse(self.files['output'].exists())
    def test_reset_intent_refuses_without_actual_one_bond_runtime_checkpoint(self):
        result=subprocess.run([FIXTURE,'--backup',str(self.files['backup']),
            '--prepare-reset-intent','yes','--request-sha256','a'*64,
            '--output',str(self.files['output'])],capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertFalse(self.files['output'].exists())
        self.assertEqual(self.files['backup'].read_bytes(),self.original)
        self.assertNotIn(b'private-test-password',result.stdout+result.stderr)
    def test_rollover_preparation_uses_unchanged_disabled_config_and_preserves_other_regions(self):
        self.assertEqual(self.run_tool().returncode,0)
        seeded=self.files['output'].read_bytes();self.files['output'].unlink();self.write('backup',seeded)
        def prepare():
            return subprocess.run([FIXTURE,'--backup',str(self.files['backup']),
                '--prepare-config-rollover','yes','--output',str(self.files['output'])],capture_output=True)
        result=prepare();self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['appends'],1)
        prepared=self.files['output'].read_bytes()
        self.assertEqual(prepared[:0x3fb000],seeded[:0x3fb000]);self.assertEqual(prepared[0x3fd000:],seeded[0x3fd000:])
        before=json.loads(subprocess.check_output([INSPECTOR,str(self.files['backup'])]))
        after=json.loads(subprocess.check_output([INSPECTOR,str(self.files['output'])]))
        self.assertEqual(before['config'],after['config']);self.assertEqual(after['config_sequence'],before['config_sequence']+1)
        self.assertEqual(before['watermark'],after['watermark']);self.assertEqual(before['cursor_sequence'],after['cursor_sequence'])
        self.files['output'].unlink();self.write('backup',prepared)
        result=prepare();self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['appends'],0)
        self.assertEqual(self.files['output'].read_bytes(),prepared)
    def pending_seed(self):
        self.assertEqual(self.run_tool().returncode,0)
        seeded=self.files['output'].read_bytes();self.files['output'].unlink();self.write('backup',seeded)
        old=profile();pending=dict(version=2,tls_pending=True)
        pending.update({key:value for key,value in old.items() if key!='version'})
        pending['request_sha256']='b'*64
        pending['clients']=[]
        for key in ('ca_certificate','ca_private_key','server_certificate','server_private_key'):pending['tls'][key]=''
        pending['tls']['ca_not_after_utc']='0';pending['tls']['server_not_after_utc']='0'
        self.write('profile',compact(pending).encode());return seeded,pending
    def test_named_pending_fixture_uses_production_parser_and_changes_only_profile(self):
        seeded,pending=self.pending_seed()
        # Default complete-TLS contract is unchanged.
        self.refuse('123456790')
        result=self.run_tool(extra=('--allow-tls-pending','yes'))
        self.assertEqual(result.returncode,0,result.stderr)
        output=self.files['output'].read_bytes()
        self.assertEqual(output[:0x3f7000],seeded[:0x3f7000]);self.assertEqual(output[0x3fb000:],seeded[0x3fb000:])
        decoded=json.loads(subprocess.check_output([INSPECTOR,str(self.files['output'])]))
        self.assertEqual(json.loads(decoded['profile_payload']),pending);self.assertEqual(decoded['profile_sequence'],2)
        self.assertEqual(decoded['config'],config());self.assertEqual(decoded['watermark'],123456789)
    def test_pending_flag_rejects_material_clients_wrong_flag_and_operational_change(self):
        seeded,pending=self.pending_seed()
        for kind in ('material','clients','false-pending','flag','config','watermark','old-request'):
            value=json.loads(json.dumps(pending));config_value=config();extra=('--allow-tls-pending','yes');watermark='123456789'
            if kind=='material':value['tls']['ca_certificate']=profile()['tls']['ca_certificate']
            if kind=='clients':value['clients']=profile()['clients']
            if kind=='false-pending':value=profile()
            if kind=='flag':extra=('--allow-tls-pending','no')
            if kind=='config':config_value['expires_utc_s']=2000000000
            if kind=='watermark':watermark='123456790'
            if kind=='old-request':value['request_sha256']=profile()['request_sha256']
            self.write('profile',compact(value).encode());self.write('config',compact(config_value).encode())
            result=self.run_tool(watermark,extra)
            with self.subTest(kind=kind):
                self.assertNotEqual(result.returncode,0);self.assertFalse(self.files['output'].exists())
                self.assertEqual(self.files['backup'].read_bytes(),seeded)
if __name__=='__main__':unittest.main()
