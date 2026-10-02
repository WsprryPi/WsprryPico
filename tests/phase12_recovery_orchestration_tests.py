#!/usr/bin/env python3
"""Behavioral failure boundaries for the unattended recovery state machine."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_recovery_orchestrator as r

REV='1'*40
MANIFEST={'source_commit':REV}

def plan():
    return dict(campaign_id='a'*32,schema='phase12-recovery-campaign/1',authority='USER_AUTHORIZED_UNATTENDED_RECOVERY',serial=r.SERIAL,device_id=r.DEVICE,host='wspr5',interface='wlan2',manifest_sha256=hashlib.sha256(r.canonical(MANIFEST)).hexdigest(),source_commit=REV,case_timeout_s=300,max_resume_boots=2,rf_jobs=0,cases=[dict(id=f'{level}-{stage}',kind='reset',level=level,stage=stage) for level in ('provisioning','full') for stage in range(1,8)]+[dict(id=f'profile-{stage}',kind='profile',stage=stage) for stage in range(8,11)])


def info(stage=0,consumed=False,boot='a'*32):
    return dict(allocator_failures='0',tls_allocation_failures=0,core0_stack_fault_status=0,core0_stack_guard_valid=1,fault_stage=0,fault_hash=0,fault_pc=0,fault_status=0,fault_allocation_recorded=False,flash_read_failures='0',flash_erase_failures='0',flash_program_failures='0',btstack_pools={name:dict(used=0,capacity=10,failures=0,faults=0) for name in ('hci_connections','l2cap_channels','l2cap_services','sm_lookup','whitelist')},network=dict(memory=dict(statistics_enabled=True,**{name:dict(used=0,capacity=10,errors=0) for name in ('heap','tcp_pcbs','tcp_listeners','udp_pcbs','timeouts','igmp_groups','tcp_segments','packet_pool')})),device_id=r.DEVICE,revision=REV[:12],access_state='healthy',phase12_fault_stage=stage,phase12_fault_consumed=consumed,status=dict(engine='inhibited-standalone-simulator',output_active=False,enabled=False,state='empty',storage_healthy=True,boot_id=boot))


def inspection():
    return dict(profile_healthy=True,access_loaded=True,access_state=2,operational_healthy=True,profile_source=5,profile_sequence=5,profile_sha256='a'*64,profile_payload=json.dumps(dict(tls_pending=False)),epoch=1,reset_level=0,reset_phase=0,bond_count=0,default_password=True,effective_station=dict(callsign='K1ABC',locator='FN20',power_dbm=30),config=None,watermark=0)


def reset_flash():
    data=bytearray(b'\xff'*r.SIZE)
    data[0x3f7000:0x3fb000]=r.cleared_profile_journal()
    return bytes(data)


class Fake:
    def __init__(self,root,fail=None): self.root=Path(root);self.fail=fail;self.submissions=0;self.restores=0;self.stage=0
    def setup(self): return info()
    def snapshot(self,name):
        data=reset_flash();(self.root/name).write_bytes(data)
        value=inspection()
        if self.fail=='pass' and name.endswith('.after.bin'):
            if self.case['kind']=='reset': value.update(profile_source=2,profile_payload='',epoch=2)
            if self.case.get('level')=='provisioning': value['config']=dict(version=1,enabled=False,station=value['effective_station'],wifi=dict(ssid='',password='',ntp_ipv4='pool.ntp.org'),schedules=[],expires_utc_s=0)
            elif self.stage==10:
                value.update(profile_sequence=6,effective_station=self.station,profile_payload=json.dumps(dict(tls_pending=False,request_sha256='e'*64)))
        return dict(path=name,sha256=r.sha(self.root/name),inspection=value)
    def restore(self,baseline,name):
        self.restores+=1
        if self.fail=='restore' and self.restores>1: raise OSError('restoration lost')
        return dict(info=info(),readback=dict(path=name,sha256='b'*64))
    def deploy(self,role,before,name): self.stage=int(role[6:]);return dict(info=info(self.stage))
    def prepare(self,case,station): self.case=case;self.station=station;return dict(prepared='x',sha256='c'*64,request_id='d'*32,expected_digest='e'*64)
    def submit(self,prepared): self.submissions+=1;return dict(uncertain=True)
    def info(self):
        if self.fail=='identity': out=info(self.stage,True,'b'*32);out['device_id']='f'*32;return out
        if self.fail=='timeout': return info(self.stage,False)
        return info(self.stage,True,'b'*32)
    def stable_restore(self,baseline): return dict(samples=5)
    def cleanup(self): pass


class Tests(unittest.TestCase):
    def test_all_seventeen_unique_cases_and_restoration(self):
        with tempfile.TemporaryDirectory() as d:
            b=Fake(d,'pass');out=r.campaign(plan(),MANIFEST,d,b)
            self.assertEqual(out['status'],'PASS_NAMED_SCOPE');self.assertFalse(out['physical_acceptance']);self.assertFalse(out['hardware_accessed']);self.assertEqual(b.submissions,17);self.assertEqual(len({x['case'] for x in out['cases']}),17);self.assertEqual(b.restores,19)
            r.Ledger(Path(d)/'ledger.jsonl')
    def test_recovery_only_refuses_missing_and_changed_backup(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(OSError):r.recover_existing(plan(),MANIFEST,d,Fake(d))
            r.private_write(Path(d)/'baseline-receipt.json',dict(plan_sha256=hashlib.sha256(r.canonical(plan())).hexdigest(),path='baseline.bin',sha256='f'*64))
            (Path(d)/'baseline.bin').write_bytes(b'\xff'*r.SIZE)
            with self.assertRaisesRegex(ValueError,'backup'):r.recover_existing(plan(),MANIFEST,d,Fake(d))
    def test_exact_plan_rejects_wrong_board_hash_repeat_and_rf(self):
        r.validate_plan(plan(),MANIFEST)
        for key,value in [('campaign_id','../unsafe'),('device_id','f'*32),('manifest_sha256','f'*64),('cases',plan()['cases']+[plan()['cases'][0]]),('rf_jobs',1),('case_timeout_s',301)]:
            p=plan();p[key]=value
            with self.assertRaises(ValueError): r.validate_plan(p,MANIFEST)
    def test_ledger_corrupt_truncated_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'ledger';l=r.Ledger(path);l.record('mutation_attempt','one');r.Ledger(path)
            content=path.read_bytes()
            for altered in [content[:-1],content.replace(b'mutation_attempt',b'mutation_changed'),content.replace(b'"seq":1',b'"seq":1,"seq":1')]:
                path.write_bytes(altered)
                with self.assertRaises(ValueError): r.Ledger(path)
    def test_no_repeat_existing_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            r.Ledger(Path(d)/'ledger.jsonl').record('mutation_attempt','one');b=Fake(d)
            with self.assertRaises(ValueError): r.campaign(plan(),MANIFEST,d,b)
            self.assertEqual(b.submissions,0)
    def test_uncertain_delivery_does_not_repeat_and_restores_after_bad_result(self):
        with tempfile.TemporaryDirectory() as d:
            b=Fake(d);out=r.campaign(plan(),MANIFEST,d,b)
            self.assertEqual(b.submissions,1);self.assertGreaterEqual(b.restores,2)
            self.assertEqual(out['status'],'STOPPED');self.assertFalse(out['physical_acceptance'])
    def test_identity_drift_restores_and_stops(self):
        with tempfile.TemporaryDirectory() as d:
            b=Fake(d,'identity');out=r.campaign(plan(),MANIFEST,d,b)
            self.assertEqual(b.submissions,1);self.assertEqual(out['error']['type'],'ValueError');self.assertEqual(b.restores,2)
    def test_deadline_does_not_repeat(self):
        with tempfile.TemporaryDirectory() as d:
            b=Fake(d,'timeout');elapsed=[0]
            def clock(): elapsed[0]+=30;return elapsed[0]
            out=r.campaign(plan(),MANIFEST,d,b,clock=clock,sleeper=lambda x:None)
            self.assertEqual(b.submissions,1);self.assertIn('deadline',out['error']['message']);self.assertEqual(b.restores,2)
    def test_restoration_failure_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            b=Fake(d,'restore');out=r.campaign(plan(),MANIFEST,d,b)
            self.assertIn('error',out['restoration']);self.assertFalse(out['physical_acceptance'])
    def test_e10_and_full_erase_validation(self):
        before=inspection();after=inspection();after.update(profile_source=2,profile_payload='',epoch=2)
        data=reset_flash()
        r.assess(dict(kind='reset',level='full'),before,after,data,data,{})
        changed=bytearray(data);changed[r.E10]=0
        with self.assertRaisesRegex(ValueError,'E10'): r.assess(dict(kind='reset',level='full'),before,after,data,changed,{})
        changed=bytearray(data);changed[0x3fb000]=0
        with self.assertRaisesRegex(ValueError,'erase'): r.assess(dict(kind='reset',level='full'),before,after,data,changed,{})
    def test_reset_rejects_secret_in_inactive_profile_bank(self):
        before=inspection();after=inspection();after.update(profile_source=2,profile_payload='',epoch=2)
        raw=bytearray(reset_flash());raw[0x3f9100]=42
        with self.assertRaisesRegex(ValueError,'profile banks'):
            r.assess(dict(kind='reset',level='full'),before,after,reset_flash(),raw,{})

    def test_preservation_compares_effective_station(self):
        before=inspection();after=inspection();after.update(profile_source=2,profile_payload='',epoch=2,effective_station=dict(callsign='K2ABC',locator='FN20',power_dbm=30))
        with self.assertRaisesRegex(ValueError,'preserved'): r.assess(dict(kind='reset',level='provisioning'),before,after,reset_flash(),reset_flash(),{})
    def test_resource_faults_close_authority(self):
        for key in ('allocator_failures','tls_allocation_failures','core0_stack_fault_status','fault_stage','flash_program_failures'):
            value=info();value[key]=1
            with self.assertRaises(ValueError): r.safe_info(value)
        value=info();value['network']['memory']['tcp_pcbs']['errors']=1
        with self.assertRaises(ValueError):r.safe_info(value)
        value=info();value['btstack_pools']['hci_connections']=dict(used=0,capacity=1,failures=1,faults=0)
        with self.assertRaises(ValueError):r.safe_info(value)
    def test_missing_btstack_pool_is_not_measurement(self):
        value=info();del value['btstack_pools']['sm_lookup']
        with self.assertRaisesRegex(ValueError,'pool names'):r.safe_info(value)
    def test_empty_ble_physical_bank_rejects_stale_secrets(self):
        data=b'\xff'*8192
        self.assertTrue(r.empty_bond_bank(data))
        header=b'BTstack\0'+b'\xff'*4088
        self.assertTrue(r.empty_bond_bank(header+b'\xff'*4096))
        changed=bytearray(data);changed[128]=0
        self.assertFalse(r.empty_bond_bank(changed))
        before=inspection();after=inspection();after.update(profile_source=2,profile_payload='',epoch=2)
        raw=bytearray(b'\xff'*r.SIZE);raw[0x3f5080]=0
        with self.assertRaisesRegex(ValueError,'BLE'):r.assess(dict(kind='reset',level='full'),before,after,b'\xff'*r.SIZE,raw,{})
    def test_fresh_local_btstack_keys_are_not_peer_bonds(self):
        import struct
        def bank(value):
            records=b''.join(struct.pack('>II',tag,16)+bytes([value])*16 for tag in (0x534d4552,0x534d4952))
            return b'BTstack\0'+records+b'\xff'*(4096-8-len(records))+b'\xff'*4096
        self.assertTrue(r.empty_bond_bank(bank(1)))
        peer=bytearray(bank(1));peer[8:12]=struct.pack('>I',0x42544400)
        self.assertFalse(r.empty_bond_bank(peer))
        before=inspection();after=inspection();after.update(profile_source=2,profile_payload='',epoch=2)
        old=bytearray(reset_flash());old[0x3f5000:0x3f7000]=bank(1)
        new=bytearray(old);new[0x3f5000:0x3f7000]=bank(2)
        r.assess(dict(kind='reset',level='full'),before,after,old,new,{})
        with self.assertRaisesRegex(ValueError,'local BLE'):r.assess(dict(kind='reset',level='full'),before,after,old,old,{})
    def test_provisioning_preserves_complete_config(self):
        before=inspection();before['config']=dict(version=1,enabled=False,station=before['effective_station'],wifi=dict(ssid='old',password='secret',ntp_ipv4='old'),schedules=[dict(period_s=120,phase_s=0)],expires_utc_s=1000)
        after=copy.deepcopy(before);after.update(profile_source=2,profile_payload='',epoch=2)
        after['config']['wifi']=dict(ssid='',password='',ntp_ipv4='pool.ntp.org')
        raw=reset_flash()
        r.assess(dict(kind='reset',level='provisioning'),before,after,raw,raw,{})
        after['config']['expires_utc_s']=1001
        with self.assertRaisesRegex(ValueError,'configuration'):r.assess(dict(kind='reset',level='provisioning'),before,after,raw,raw,{})
    def test_profile_commit_rejects_foreign_digest(self):
        before=inspection();after=copy.deepcopy(before);after.update(profile_sequence=6,profile_payload=json.dumps(dict(request_sha256='f'*64)))
        with self.assertRaisesRegex(ValueError,'digest'):r.assess(dict(kind='profile',stage=10),before,after,b'\xff'*r.SIZE,b'\xff'*r.SIZE,dict(expected_digest='e'*64))
    def test_cold_rearming_stops_without_repeat(self):
        with tempfile.TemporaryDirectory() as d:
            b=Fake(d);counter=[0]
            def rebooting():
                counter[0]+=1
                return info(b.stage,False,f'{counter[0]:032x}')
            b.info=rebooting
            out=r.campaign(plan(),MANIFEST,d,b,sleeper=lambda x:None)
            self.assertIn('cold rearming',out['error']['message']);self.assertEqual(b.submissions,1);self.assertEqual(b.restores,2)
    def test_reboot_bound_with_consumed_fixture(self):
        boots={'a'*32,'b'*32,'c'*32,'d'*32}
        with self.assertRaisesRegex(ValueError,'reboot budget'):
            r.observe_boot(boots,info(1,True,'e'*32),'a'*32,2)
    def test_failed_backup_barrier_prevents_all_writes(self):
        with tempfile.TemporaryDirectory() as d:
            b=Fake(d)
            def lost(name): raise OSError('local backup lost')
            b.snapshot=lost
            out=r.campaign(plan(),MANIFEST,d,b)
            self.assertEqual(b.submissions,0);self.assertEqual(b.restores,0);self.assertEqual(out['status'],'STOPPED')
    def test_lost_campaign_guard_prevents_adapter_invocation(self):
        from unittest.mock import Mock,patch
        b=r.Backend(plan(),dict(source_commit=REV,candidates=[]),'.','.',INSPECTOR or '.')
        b.guard=Mock();b.guard.poll.return_value=1
        with patch('subprocess.run') as invoke:
            with self.assertRaisesRegex(ValueError,'lock lost'):b.call('restore')
            invoke.assert_not_called()
    def test_remote_action_lock_refuses_before_usb(self):
        import phase12_recovery_device as device
        from unittest.mock import patch
        import io
        request=dict(root='/home/pi/phase12-recovery-'+'a'*32,action='info')
        class Input:
            buffer=io.BytesIO(r.canonical(request))
        with patch.object(device.sys,'stdin',Input()),patch.object(device.Path,'is_dir',return_value=True),patch.object(device.Path,'is_symlink',return_value=False),patch.object(device.os,'open',return_value=123),patch.object(device.fcntl,'flock',side_effect=BlockingIOError()),patch.object(device,'console') as console:
            with self.assertRaises(BlockingIOError):device.main()
            console.assert_not_called()
    def test_rejected_observation_is_not_retried(self):
        with tempfile.TemporaryDirectory() as d:
            b=Fake(d);calls=[0]
            def reject(): calls[0]+=1;raise ValueError('allocator fault')
            b.info=reject
            out=r.campaign(plan(),MANIFEST,d,b)
            self.assertEqual(calls[0],1);self.assertEqual(b.submissions,1);self.assertEqual(b.restores,2)
    def test_emergency_rom_accepts_fault_only_for_inhibited_exact_board(self):
        import phase12_recovery_device as device
        value=info();value['allocator_failures']='1'
        with self.assertRaises(ValueError):device.healthy(value,allow_fault=True)
        device.healthy(value,allow_fault=True,repair=True)
        for key in ('device_id','status'):
            bad=copy.deepcopy(value)
            if key=='device_id':bad[key]='f'*32
            else:bad[key]['output_active']=True
            with self.assertRaises(ValueError):device.healthy(bad,allow_fault=True,repair=True)
    def test_ap_suffix_rejects_shell_metacharacters(self):
        self.assertEqual(r.ap_ssid('abc123'),'WsprryPico-abc123')
        for value in ('abc123;id','$(id)','ABC123','abc12',None):
            with self.assertRaisesRegex(ValueError,'suffix'):r.ap_ssid(value)
    def test_profile_http_uses_owner_marker(self):
        import phase12_recovery_device as device
        from unittest.mock import MagicMock,patch
        for route,marker in (('/api/owner/v1/claim/start',b'Owner'),('/api/recovery/v1/start',b'Bootstrap')):
            sock=MagicMock();sock.__enter__.return_value=sock
            sock.recv.return_value=b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}'
            with patch.object(device.socket,'socket',return_value=sock):device.http('wlan2',route,{})
            sent=sock.sendall.call_args.args[0]
            self.assertIn(b'X-WsprryPico-'+marker+b': 1',sent)
            self.assertNotIn(b'X-WsprryPico-'+(b'Bootstrap' if marker==b'Owner' else b'Owner')+b':',sent)
    def test_continuation_requires_exact_three_cases_and_bound_evidence(self):
        p=plan();p.update(schema='phase12-profile-continuation/1',cases=p['cases'][14:],predecessor_ledger_sha256='1'*64,predecessor_result_sha256='2'*64,predecessor_baseline_sha256='3'*64)
        self.assertEqual(len(r.validate_plan(p,MANIFEST)),3)
        p['cases'].insert(0,plan()['cases'][0])
        with self.assertRaises(ValueError):r.validate_plan(p,MANIFEST)
        with tempfile.TemporaryDirectory() as d:
            p['cases']=plan()['cases'][14:];b=Fake(d)
            with self.assertRaisesRegex(ValueError,'requires retained'):r.campaign(p,MANIFEST,d,b)
            self.assertEqual(b.submissions,0);self.assertEqual(b.restores,0)

    def test_http_trickle_cannot_extend_absolute_deadline(self):
        import phase12_recovery_device as device
        from unittest.mock import MagicMock,patch
        sock=MagicMock();sock.__enter__.return_value=sock
        sock.recv.return_value=b'x'
        with patch.object(device.socket,'socket',return_value=sock),patch.object(device.time,'monotonic',side_effect=[0,0,0,5,11]):
            with self.assertRaisesRegex(TimeoutError,'absolute deadline'):
                device.http('wlan2','/api/recovery/status')
        self.assertEqual(sock.recv.call_count,1)

    def test_native_inspector_readonly_empty_and_wrong_size(self):
        if not INSPECTOR: self.skipTest('inspector supplied by CTest')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'flash.bin';p.write_bytes(b'\xff'*r.SIZE)
            value=json.loads(subprocess.check_output([INSPECTOR,str(p)]))
            self.assertTrue(value['profile_healthy']);self.assertEqual(value['access_state'],1);self.assertTrue(value['operational_healthy']);self.assertIsNone(value['effective_station'])
            p.write_bytes(b'bad');self.assertNotEqual(subprocess.run([INSPECTOR,str(p)]).returncode,0)

INSPECTOR=sys.argv.pop() if len(sys.argv)>1 and not sys.argv[-1].startswith('-') else None
if __name__=='__main__': unittest.main()
