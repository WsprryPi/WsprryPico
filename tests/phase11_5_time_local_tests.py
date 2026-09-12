#!/usr/bin/env python3
"""Offline mutation checks for native mDNS/NTP admission and scoped restoration."""
import copy
import contextlib
import io
import json
from pathlib import Path
import socket
import struct
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import phase11_5_time_local as subject
from phase11_5_device_management import configuration
from phase11_5_network_fixture import Fixture


def admission():
    utc = 1789228800000000000
    stamp = (utc//10**9+2208988800) << 32
    q = bytearray(48); q[0] = 0x23; struct.pack_into('!Q', q, 40, stamp)
    r = bytearray(48); r[0] = 0x24; r[1] = 1; r[12:16] = b'PPS\0'
    for offset in (16, 24, 32, 40): struct.pack_into('!Q', r, offset, stamp)
    mq = struct.pack('!6H', 12345, 0, 1, 0, 0, 0)+b'\x04time\x05local\x00\x00\x01\x00\x01'
    mr = (struct.pack('!6H',12345,0x8400,1,1,0,0)+mq[12:]+b'\xc0\x0c'+
          struct.pack('!HHIH',1,1,120,4)+socket.inet_aton(subject.ADDRESS))
    return dict(schema='phase11.5-time-local-admission-v1', status='PASS', name='time.local',
        native_resolution='time.local\t10.77.15.1', native_resolver='getent -s mdns4 ahostsv4',
        native_output='10.77.15.1 STREAM time.local', resolution_elapsed_ns=100,
        start_utc_ns=utc, finish_utc_ns=utc+10**9,
        mdns=dict(query_hex=mq.hex(), reply_hex=mr.hex(), peer=[subject.ADDRESS,5353],
                  local_address=subject.CLIENT, local_port=20000, elapsed_ns=100),
        ntp=dict(query_hex=q.hex(), reply_hex=r.hex(), peer=[subject.ADDRESS,123],
                 address=subject.ADDRESS, local_address=subject.CLIENT, elapsed_ns=100,utc_ns=utc))


class TimeLocalTests(unittest.TestCase):
    def test_complete_admission(self):
        subject.validate_admission(admission())

    def test_native_resolution_wrong_address_failure_and_deadline(self):
        for changes in ({'native_resolution':'time.local\t192.168.1.54'}, {'status':'FAILED'},
                        {'resolution_elapsed_ns':10_000_000_001}, {'name':'clock.phase115.test'}):
            value=admission();value.update(changes)
            with self.assertRaises(ValueError):subject.validate_admission(value)

    def test_ntp_quality_origin_address_and_time_mutations(self):
        original=admission()['ntp'];reply=bytes.fromhex(original['reply_hex'])
        for offset,value in ((0,0xe4),(0,0x23),(1,0),(1,2),(12,88),(24,0),(40,0)):
            bad=copy.deepcopy(original);data=bytearray(reply);data[offset]=value;bad['reply_hex']=data.hex()
            with self.subTest(offset=offset,value=value),self.assertRaises(ValueError):
                subject.validate_ntp(bad,subject.ADDRESS,subject.CLIENT)
        for changes in ({'peer':['192.168.1.54',123]}, {'local_address':'127.0.0.1'},
                        {'elapsed_ns':3_000_000_001}, {'utc_ns':original['utc_ns']+60*10**9},
                        {'reply_hex':reply[:-1].hex()}):
            bad=copy.deepcopy(original);bad.update(changes)
            with self.assertRaises(ValueError):subject.validate_ntp(bad,subject.ADDRESS,subject.CLIENT)

    def test_mdns_wrong_address_error_compression_and_deadline(self):
        original=admission()['mdns'];reply=bytes.fromhex(original['reply_hex'])
        for data in (reply[:-4]+socket.inet_aton('192.168.1.54'), reply[:-1],
                     reply[:2]+b'\x86\x00'+reply[4:], reply[:12]+b'\xc0\x0c'+reply[14:]):
            bad=dict(original,reply_hex=data.hex())
            with self.assertRaises(ValueError):subject.validate_mdns(bad)
        for changes in ({'peer':['192.168.1.54',5353]}, {'elapsed_ns':3_000_000_001}):
            bad=dict(original,**changes)
            with self.assertRaises(ValueError):subject.validate_mdns(bad)

    def test_capture_requires_both_protocols_and_correct_direction(self):
        value=admission();packets=[]
        for protocol,port,destination in (('mdns',5353,'224.0.0.251'),('ntp',123,subject.ADDRESS)):
            for response in (False,True):
                packets.append(dict(utc_ns=value['start_utc_ns']+100+int(response),
                    source=subject.ADDRESS if response else subject.CLIENT,
                    destination=subject.CLIENT if response else destination,
                    sport=port if response else 20000,dport=20000 if response else port,
                    payload=value[protocol]['reply_hex' if response else 'query_hex']))
        with patch.object(subject,'capture_packets',return_value=packets),patch.object(subject,'digest',return_value='hash'):
            subject.validate_capture(Path('/capture'),value)
        for index in range(4):
            bad=packets[:index]+packets[index+1:]
            with patch.object(subject,'capture_packets',return_value=bad),self.assertRaises(ValueError):
                subject.validate_capture(Path('/capture'),value)

    def test_restoration_refuses_changed_ownership_before_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);helper=root/'helper';dropin=root/'dropin'
            helper.write_text('original');dropin.write_text('foreign')
            fixture=Mock();fixture.state={'time_local_override':dict(
                helper_sha256=subject.digest(helper),dropin_sha256='ours')}
            with patch.object(subject,'RUNTIME',helper),patch.object(subject,'DROPIN',dropin):
                with self.assertRaisesRegex(ValueError,'ownership'):subject.restore(fixture)
            self.assertEqual(dropin.read_text(),'foreign');fixture.cmd.assert_not_called()

    def test_final_capture_rejects_partial_header_and_record(self):
        header = struct.pack('<IHHIIII', 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'capture.pcap'
            for tail in (b'\x00', struct.pack('<4I', 1, 0, 10, 10)+b'\x00'):
                path.write_bytes(header+tail)
                with self.assertRaisesRegex(ValueError, 'Incomplete final pcap'):
                    subject.capture_packets(path)
                self.assertEqual(subject.capture_packets(path, allow_live_tail=True), [])

    def test_preservation_rejects_changed_files_services_alias_and_acl(self):
        before=dict(files={'a':'hash'},addresses={'eth0':'192.168.1.54'},resolution='time.local 192.168.1.54',
                    lan_acl='Access allowed',services={name:dict(ActiveState='active',UnitFileState='enabled',MainPID='1')
                    for name in ('time-local','chrony','gpsd','avahi-daemon')})
        after=copy.deepcopy(before);after['services']['time-local']['MainPID']='2'
        subject.validate_preserved(before,after)
        for mutate in (lambda v:v['files'].update(a='changed'),lambda v:v.update(lan_acl='denied'),
                       lambda v:v.update(resolution='wrong'),lambda v:v['services']['chrony'].update(MainPID='2')):
            after=copy.deepcopy(before);mutate(after)
            with self.assertRaises(ValueError):subject.validate_preserved(before,after)

    def test_mdns_configuration_is_explicit_and_legacy_unchanged(self):
        original=dict(enabled=False,expires_utc_s=0,schedules=[])
        wifi=dict(ssid='WsprryPico-Phase115',password='test-only',ntp_ipv4='time.local')
        with self.assertRaises(ValueError):configuration(original,wifi,'test')
        self.assertEqual(configuration(original,wifi,'test','time.local')[0]['wifi'],wifi)
        for name in ('server time.local iburst','10.77.15.1','wspr5.local'):
            with self.assertRaises(ValueError):configuration(original,dict(wifi,ntp_ipv4=name),'test','time.local')

    def test_mixed_discovery_flags_fail_before_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'packet.json').write_text(json.dumps(dict(time_server_dns=True,time_server_mdns=True)))
            fixture=Fixture(root)
            with patch.object(fixture,'preflight',return_value=({},{})),patch.object(fixture,'cmd') as cmd:
                with self.assertRaises(ValueError):fixture.setup()
                cmd.assert_not_called()

    def test_cleanup_restores_publisher_after_namespace_removal(self):
        from phase11_5_network_fixture import HOST_BOOT, NETNS
        with tempfile.TemporaryDirectory() as directory:
            fixture=Fixture(Path(directory));order=[];present=[True]
            fixture.state=dict(token='ours',host_boot=HOST_BOOT,before={'installed_pid':'1957'},
                               units=[],radio={},namespace=True,time_local_override={'owned':True})
            def value(*args):
                if args==('ip','netns','list'):return NETNS if present[0] else ''
                return 'Access denied'
            def command(args,**kwargs):
                if args==['ip','netns','delete',NETNS]:
                    present[0]=False;order.append('namespace')
            with patch.object(Path,'read_text',return_value=HOST_BOOT),\
                 patch.object(fixture,'value',side_effect=value),patch.object(fixture,'cmd',side_effect=command),\
                 patch.object(fixture,'host',return_value=dict(installed_pid='1957',interfaces='',routes='')),\
                 patch.object(subject,'restore',side_effect=lambda _:order.append('publisher')):
                fixture.cleanup()
            self.assertEqual(order,['namespace','publisher'])

    def test_no_run_has_no_network_or_host_access(self):
        with patch.object(sys,'argv',['time-local','probe']),patch.object(subject,'probe') as probe,\
             contextlib.redirect_stdout(io.StringIO()):subject.main()
        probe.assert_not_called()


if __name__=='__main__':unittest.main()
