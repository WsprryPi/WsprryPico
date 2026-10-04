#!/usr/bin/env python3
"""One-use datagram and one-byte seed controls, entirely file/fake-I/O based."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_engineering_journal_stimuli as s
from phase12_engineering_fixture import ntp_reply


def info(generation=7,boot='b'*32,accepted=0,rejected=0):
    # Exact Scheduler::status keys from the retained c0d source1 USB INFO
    # (634b7d4e29a3961bb587cdb27a8058364848f8979a3ab25857565c829a3cceb3).
    # Only identities, clocks and declared fixture values are substituted.
    # WTP STATUS owner_id/job_id are deliberately absent from this producer.
    return dict(ok=True,device_id=s.DEVICE,revision='a'*12,provisioning_source='provisioned',
        provisioning_generation=str(generation),lan_wtp_mode='engineering-tls',access_state='healthy',
        ble_running=True,ble_active_connections=0,lan_wtp_ready=bool(accepted),lan_wtp_port=0,
        status=dict(ok=True,boot_id=boot,engine='inhibited-standalone-simulator',output_active=False,enabled=False,
            state='empty',storage_healthy=True,reboot_required=False,configured=False,suspended=True,
            station=None,schedules=[],expires_utc_s=0,last_error=None,last_job='',
            monotonic_now_ns='1000000000',utc_now_ns='1791100000000000000' if accepted else '0',
            sync_age_ns='0' if accepted else str(2**64-1),uncertainty_ns='1000' if accepted else str(2**64-1),
            watermark_utc_ns='0',schedule_base_frequency_nhz='3570100000000000',
            clock_state='synchronized' if accepted else 'unsynchronized'),
        network=dict(enabled=True,ipv4='192.168.84.2',link_status=3,ntp_server=s.ADDRESS,accepted=accepted,rejected=rejected))


def fault_info():
    value=info();value.update(provisioning_source='fault',provisioning_generation='0',provisioning_fault=1,
        lan_wtp_ready=False,lan_wtp_port=0,ble_running=False,ble_active_connections=0)
    value['network'].update(enabled=False,ipv4='',link_status=0)
    return value


def raw(value):return json.dumps(value).encode()


def query(nonce):
    value=bytearray(48);value[0]=0x23;value[40:48]=nonce.to_bytes(8,'big');return bytes(value)


def bank(sequence,profile):
    # Independently construct the documented production source-selection layout.
    payload=struct.pack('<Q',0x324c455350435057)+bytes([1])+bytes(7)+profile
    result=bytearray(b'\xff'*8192);result[256:256+len(payload)]=payload
    header=bytearray(b'\xff'*256);commit=bytearray(b'\xff'*256)
    struct.pack_into('<QQII',header,0,0x3146525050435057,sequence,len(payload),2)
    checksum=hashlib.sha256(payload).digest();header[24:56]=checksum
    struct.pack_into('<I',header,252,zlib.crc32(header[:252]))
    struct.pack_into('<QQ',commit,0,0x31544d4d4f435057,sequence);commit[16:48]=checksum
    struct.pack_into('<I',commit,252,zlib.crc32(commit[:252]))
    result[:256]=header;result[-256:]=commit;return bytes(result)


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.now=0.;self.sent=[]
        self.clock=lambda:self.now
        self.utc=1791100000000000000
        self.peer=('192.168.84.2',40000)
        self.old=query(17);self.old_reply=ntp_reply(self.old,self.utc)
        self.new=query(23);self.new_reply=ntp_reply(self.new,self.utc+1000000000)
        s.arm(self.root,'a'*40,7,90,clock=self.clock)
    def control(self,operation,value):return s.control(self.root,operation,raw(value),clock=self.clock)
    def send(self,response,peer):self.sent.append((response,peer));return len(response)
    def respond(self,query=None,reply=None,peer=None,send=None):
        return s.respond(self.root,query or self.new,peer or self.peer,reply or self.new_reply,
            send or self.send,utc_ns=self.utc,clock=self.clock)
    def captured(self):
        self.control('old_bind',info());self.now=1
        self.assertEqual(self.respond(self.old,self.old_reply),'normal')
        self.control('hold',info(accepted=1));self.now=2
        self.control('new_bind',info(8,'d'*32))
    def test_default_and_prebound_datagrams_are_held_without_send(self):
        self.assertEqual(self.respond(),'held');self.assertEqual(self.sent,[])
        self.control('old_bind',info())
        self.assertEqual(self.respond(peer=('192.168.84.3',40001)),'held');self.assertEqual(self.sent,[])
    def test_exact_old_reply_one_attempt_to_new_port_then_usb_rejection_release(self):
        self.captured();self.now=3;peer=('192.168.84.2',49999)
        self.assertEqual(self.respond(peer=peer),'stale');self.assertEqual(self.sent,[(self.old_reply,peer)])
        self.assertEqual(self.respond(peer=peer),'held');self.assertEqual(len(self.sent),1)
        attempt=s.strict((self.root/s.FILES[5]).read_bytes())
        self.assertEqual(bytes.fromhex(attempt['new_query_hex']),self.new)
        self.assertEqual(attempt['old_response_sha256'],s.digest(self.old_reply))
        self.assertEqual(attempt['datagram_attempts'],1)
        self.control('release',info(8,'d'*32,rejected=1))
        self.now=1000
        self.assertEqual(self.respond(),'normal');self.assertEqual(len(self.sent),1)
        self.assertEqual(s.strict((self.root/s.FILES[0]).read_bytes())['end_monotonic_s'],90)
    def test_uncertain_send_consumed_before_call_and_never_replayed(self):
        self.captured();original=OSError('ambiguous send')
        def fail(response,peer):
            self.assertTrue((self.root/s.FILES[5]).exists());self.sent.append((response,peer));raise original
        with self.assertRaises(OSError) as caught:self.respond(send=fail)
        self.assertIs(caught.exception,original)
        self.assertEqual(self.respond(),'held');self.assertEqual(len(self.sent),1)
        with self.assertRaises(ValueError):self.control('release',info(8,'d'*32,rejected=1))
    def test_short_slow_or_exact_deadline_send_never_releases(self):
        for advance,count in [(.5,48),(88,48),(0,47)]:
            with self.subTest(advance=advance,count=count):
                case=Tests();case.setUp();self.addCleanup(case.doCleanups);case.captured()
                def send(response,peer):case.now+=advance;case.sent.append(response);return count
                with self.assertRaises(ValueError):case.respond(send=send)
                self.assertFalse((case.root/s.FILES[6]).exists());self.assertEqual(len(case.sent),1)
    def test_equal_or_late_deadline_refuses_send_and_controls(self):
        self.captured()
        for now in (90,90.001):
            self.now=now
            with self.assertRaisesRegex(ValueError,'original stimulus deadline'):self.respond()
            with self.assertRaises(ValueError):self.control('release',info(8,'d'*32,rejected=1))
        self.assertEqual(self.sent,[])
    def test_same_nonce_wrong_peer_and_corrupted_old_evidence_cannot_send(self):
        self.captured()
        self.assertEqual(self.respond(peer=('192.168.84.3',40000)),'held')
        with self.assertRaisesRegex(ValueError,'distinct actual new nonce'):self.respond(self.old,self.old_reply)
        path=self.root/s.FILES[2];value=s.strict(path.read_bytes());value['response_sha256']='0'*64;path.write_bytes(raw(value))
        with self.assertRaises(ValueError):self.respond()
        self.assertEqual(self.sent,[])
    def test_wrong_generation_reboot_source_or_active_authority_refuses_binding(self):
        self.captured()
        for change in [dict(provisioning_generation='7'),dict(revision='c'*12),dict(provisioning_source='unprovisioned'),
                       dict(status=dict(info()['status'],boot_id='b'*32)),dict(status=dict(info()['status'],output_active=True))]:
            value=info(8,'d'*32);value.update(change)
            with self.assertRaises(ValueError):s.info_binding(raw(value),'a'*40,8,'d'*32)
        self.assertEqual(self.sent,[])
    def test_accepted_or_unobserved_rejection_cannot_release_new_time(self):
        self.captured();self.respond()
        for accepted,rejected in [(1,1),(0,0),(0,2)]:
            with self.subTest(accepted=accepted,rejected=rejected):
                with self.assertRaisesRegex(ValueError,'one stale reply rejected'):self.control('release',info(8,'d'*32,accepted,rejected))
        self.assertFalse((self.root/s.FILES[7]).exists())
    def test_no_restart_rearm_or_repeated_control(self):
        with self.assertRaisesRegex(ValueError,'one fresh stimulus'):s.arm(self.root,'a'*40,7,90,clock=self.clock)
        self.control('old_bind',info())
        with self.assertRaisesRegex(ValueError,'immutable stimulus'):self.control('old_bind',info())
    def test_capture_original_contains_exact_query_reply_and_no_credentials(self):
        self.control('old_bind',info());self.respond(self.old,self.old_reply)
        captured=s.strict((self.root/s.FILES[2]).read_bytes())
        self.assertEqual(bytes.fromhex(captured['query_hex']),self.old)
        self.assertEqual(bytes.fromhex(captured['response_hex']),ntp_reply(self.old,captured['utc_ns']))
        self.assertEqual(captured['old_bind_sha256'],s.digest((self.root/s.FILES[1]).read_bytes()))
        self.assertEqual((self.root/s.FILES[2]).stat().st_mode&0o777,0o600)
    def test_orphan_partial_duplicate_and_symlink_control_refused(self):
        with self.assertRaises(ValueError):self.control('hold',info(accepted=1))
        path=self.root/s.FILES[1];path.write_bytes(b'{')
        with self.assertRaises(ValueError):self.respond()
        path.unlink();path.symlink_to(self.root/s.FILES[0])
        with self.assertRaises(ValueError):self.respond()
    def test_edited_or_orphaned_new_generation_chain_cannot_consume_or_send(self):
        changes=[(s.FILES[4],'arm_sha256','0'*64),(s.FILES[4],'hold_sha256','0'*64),
                 (s.FILES[4],'boot_id','b'*32),(s.FILES[4],'info_sha256','0'*64),
                 (s.FILES[3],'old_sha256','0'*64),(s.FILES[1],'info_sha256','0'*64)]
        for name,key,value in changes:
            with self.subTest(name=name,key=key):
                case=Tests();case.setUp();self.addCleanup(case.doCleanups);case.captured()
                path=case.root/name;receipt=s.strict(path.read_bytes());receipt[key]=value;path.write_bytes(raw(receipt))
                with self.assertRaises(ValueError):case.respond()
                self.assertFalse((case.root/s.FILES[5]).exists());self.assertEqual(case.sent,[])
        case=Tests();case.setUp();self.addCleanup(case.doCleanups);case.captured()
        path=case.root/s.FILES[4];receipt=s.strict(path.read_bytes());old=info()
        receipt.update(info_raw_hex=raw(old).hex(),info_sha256=s.digest(raw(old)),boot_id='b'*32)
        path.write_bytes(raw(receipt))
        with self.assertRaises(ValueError):case.respond()
        self.assertFalse((case.root/s.FILES[5]).exists());self.assertEqual(case.sent,[])
    def test_edited_send_or_release_original_cannot_reopen_normal_replies(self):
        self.captured();self.respond()
        path=self.root/s.FILES[6];receipt=s.strict(path.read_bytes());receipt['sent_bytes']=47;path.write_bytes(raw(receipt))
        with self.assertRaises(ValueError):self.control('release',info(8,'d'*32,rejected=1))
        self.assertFalse((self.root/s.FILES[7]).exists())
        case=Tests();case.setUp();self.addCleanup(case.doCleanups);case.captured();case.respond()
        case.control('release',info(8,'d'*32,rejected=1));path=case.root/s.FILES[7]
        receipt=s.strict(path.read_bytes());receipt['info_sha256']='0'*64;path.write_bytes(raw(receipt))
        case.now=1000
        with self.assertRaises(ValueError):case.respond()
        self.assertEqual(len(case.sent),1)
    def test_boolean_float_or_negative_clock_counters_and_fault_code_refused(self):
        self.captured();self.respond()
        for key,value in [('accepted',False),('accepted',0.0),('rejected',True),('rejected',1.0),('rejected',-1)]:
            with self.subTest(key=key,value=value):
                value_info=info(8,'d'*32,rejected=1);value_info['network'][key]=value
                with self.assertRaises(ValueError):self.control('release',value_info)
        value=fault_info();value['provisioning_fault']=True
        with self.assertRaises(ValueError):s.fault_info(raw(value),'a'*40,'c'*32)
    def test_fault_guard_requires_actual_fresh_storage_fault_and_inactive_no_network(self):
        value=fault_info()
        self.assertEqual(s.fault_info(raw(value),'a'*40,'c'*32),value)
        for change in [dict(provisioning_source='provisioned'),dict(provisioning_generation='7'),
                       dict(provisioning_fault=2),dict(lan_wtp_ready=True),dict(status=dict(value['status'],output_active=True))]:
            changed=copy.deepcopy(value);changed.update(change)
            with self.assertRaises(ValueError):s.fault_info(raw(changed),'a'*40,'c'*32)
        with self.assertRaises(ValueError):s.fault_info(raw(value),'a'*40,'b'*32)
    def test_real_serial_schema_is_admitted_unchanged_without_wtp_identity(self):
        value=info();wire=raw(value)
        self.assertEqual(s.info_binding(wire,'a'*40,7,'b'*32),value)
        self.assertNotIn('owner_id',value['status']);self.assertNotIn('job_id',value['status'])
        self.control('old_bind',value)
        original=s.strict((self.root/s.FILES[1]).read_bytes())
        self.assertEqual(bytes.fromhex(original['info_raw_hex']),wire)
        self.assertEqual(original['info_sha256'],hashlib.sha256(wire).hexdigest())
        fault=fault_info();self.assertEqual(s.fault_info(raw(fault),'a'*40,'c'*32),fault)
        self.assertNotIn('owner_id',fault['status']);self.assertNotIn('job_id',fault['status'])
    def test_missing_serial_or_pending_active_projection_refuses_before_bind(self):
        for key in ('ok','boot_id','clock_state','engine','state','output_active','enabled','storage_healthy','reboot_required'):
            with self.subTest(missing=key):
                value=info();del value['status'][key]
                with self.assertRaisesRegex(ValueError,'complete serial scheduler projection'):self.control('old_bind',value)
        for key,value in [('ok',False),('boot_id','invalid'),('clock_state','unknown'),('engine','pio-dma-gp2'),
                          ('state','loaded'),('output_active',True),('output_active',0),('enabled',True),
                          ('storage_healthy',False),('storage_healthy',1),('reboot_required',True),('reboot_required',0)]:
            with self.subTest(key=key,value=value):
                changed=info();changed['status'][key]=value
                with self.assertRaises(ValueError):self.control('old_bind',changed)
        self.assertFalse((self.root/s.FILES[1]).exists());self.assertEqual(self.sent,[])
    def test_hybrid_wtp_fields_do_not_turn_serial_INFO_into_owner_evidence(self):
        for key,value in [('owner_id',None),('owner_id','e'*32),('job_id',None),('job_id','f'*32)]:
            with self.subTest(key=key,value=value):
                changed=info();changed['status'][key]=value
                with self.assertRaisesRegex(ValueError,'not a WTP ownership/job observation'):self.control('old_bind',changed)
        self.assertFalse((self.root/s.FILES[1]).exists());self.assertEqual(self.sent,[])
    def test_edited_new_INFO_with_valid_hash_still_cannot_admit_stale_send(self):
        self.captured();path=self.root/s.FILES[4];receipt=s.strict(path.read_bytes())
        changed=info(8,'d'*32);changed['status']['reboot_required']=True;wire=raw(changed)
        receipt.update(info_raw_hex=wire.hex(),info_sha256=s.digest(wire));path.write_bytes(raw(receipt))
        with self.assertRaisesRegex(ValueError,'serial-visible'):self.respond()
        self.assertFalse((self.root/s.FILES[5]).exists());self.assertEqual(self.sent,[])
    def test_fault_requires_present_inactive_BLE_and_no_station_or_clock_authority(self):
        for key in ('ble_running','ble_active_connections','lan_wtp_ready','lan_wtp_port'):
            with self.subTest(missing=key):
                value=fault_info();del value[key]
                with self.assertRaisesRegex(ValueError,'present fault carrier'):s.fault_info(raw(value),'a'*40,'c'*32)
        for key in ('enabled','ipv4','link_status','accepted','rejected'):
            with self.subTest(missing_network=key):
                value=fault_info();del value['network'][key]
                with self.assertRaisesRegex(ValueError,'present fault carrier'):s.fault_info(raw(value),'a'*40,'c'*32)
        for key,value in [('ble_running',True),('ble_running',0),('ble_active_connections',1),
                          ('ble_active_connections',False),('ble_active_connections',0.0),
                          ('lan_wtp_ready',True),('lan_wtp_port',443),('lan_wtp_port',False)]:
            with self.subTest(key=key,value=value):
                changed=fault_info();changed[key]=value
                with self.assertRaises(ValueError):s.fault_info(raw(changed),'a'*40,'c'*32)
        for key,value in [('enabled',True),('enabled',0),('link_status',3),('link_status',False),
                          ('ipv4','192.168.84.2'),('accepted',1),('accepted',False),('rejected',1)]:
            with self.subTest(network=key,value=value):
                changed=fault_info();changed['network'][key]=value
                with self.assertRaises(ValueError):s.fault_info(raw(changed),'a'*40,'c'*32)
        changed=fault_info();changed['status']['clock_state']='synchronized'
        with self.assertRaises(ValueError):s.fault_info(raw(changed),'a'*40,'c'*32)


class CorruptionTests(unittest.TestCase):
    def image(self,newest=1):
        raw=bytearray(b'\xff'*s.SIZE)
        for index in (0,1):
            generation,payload=(9,b'{"C":true}') if index==newest else (8,b'{"B":true}')
            at=s.BASE+index*s.SLOT;raw[at:at+s.SLOT]=bank(generation,payload)
        # Non-erased unrelated regions prove whole-image preservation.
        raw[0x3f3000:0x3f7000]=bytes(range(256))*64
        raw[0x3fb000:]=bytes(range(255,-1,-1))*80
        return bytes(raw)
    def test_one_newest_payload_bit_each_slot_all_other_bytes_exact(self):
        for index in (0,1):
            with self.subTest(index=index):
                original=self.image(index);seed,receipt=s.corrupt_newest(original,b'{"C":true}',9)
                differences=[at for at,(a,b) in enumerate(zip(original,seed)) if a!=b]
                self.assertEqual(differences,[s.BASE+index*s.SLOT+s.PAGE+16])
                self.assertEqual(seed[differences[0]]^original[differences[0]],1)
                self.assertEqual(seed[0x3ff000:],original[0x3ff000:])
                self.assertEqual(receipt['newest_bank'],index);self.assertEqual(receipt['older_generation'],8)
                self.assertEqual(s.committed_bank(seed,1-index)['payload'],b'{"B":true}')
                with self.assertRaisesRegex(ValueError,'payload/digest'):s.committed_bank(seed,index)
    def test_wrong_selected_generation_payload_old_equal_or_duplicate_generation_refused(self):
        original=self.image()
        for expected,generation in [(b'wrong',9),(b'{"C":true}',8),(b'{"C":true}',10)]:
            with self.assertRaises(ValueError):s.corrupt_newest(original,expected,generation)
        for generation,payload in [(9,b'{"B":true}'),(8,b'{"C":true}'),(6,b'{"B":true}')]:
            changed=bytearray(original);changed[s.BASE:s.BASE+s.SLOT]=bank(generation,payload)
            with self.assertRaises(ValueError):s.corrupt_newest(bytes(changed),b'{"C":true}',9)
    def test_preexisting_header_commit_payload_corruption_or_truncated_image_refused(self):
        original=self.image()
        for offset in [s.BASE,s.BASE+252,s.BASE+256+16,s.BASE+s.SLOT-256,s.BASE+s.SLOT-4]:
            changed=bytearray(original);changed[offset]^=1
            with self.assertRaises(ValueError):s.corrupt_newest(bytes(changed),b'{"C":true}',9)
        with self.assertRaises(ValueError):s.corrupt_newest(original[:-1],b'{"C":true}',9)

if __name__=='__main__':unittest.main()
