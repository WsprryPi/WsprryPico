#!/usr/bin/env python3
"""Hardware-free radio role validation and actual adapter routing checks."""
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import phase12_fixture_roles as r
import phase12_engineering_fixture as fixture
import phase12_populated_dispatch as populated
import phase12_consumer_flash_status_dispatch as consumer


class Tests(unittest.TestCase):
    def test_exact_mapping_hash_tamper_and_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertEqual(r.load_roles(root),r.role_map())
            role=r.role_map('swapped');(root/'fixture-roles.json').write_text(json.dumps(role))
            self.assertEqual(r.load_roles(root),role)
            role['observer']='wlan1';(root/'fixture-roles.json').write_text(json.dumps(role))
            with self.assertRaises(ValueError):r.load_roles(root)
            (root/'fixture-roles.json').write_text('{"selection":"engineering","selection":"swapped"}')
            with self.assertRaisesRegex(ValueError,'duplicate'):r.load_roles(root)
        for value in ('wlan1','arbitrary',None):
            with self.assertRaises(ValueError):r.role_map(value)

    def test_bound_role_replacement_or_removal_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);swapped=r.role_map('swapped')
            (root/'fixture-roles.json').write_text(json.dumps(swapped))
            (root/'fixture-roles-bound.json').write_text(json.dumps(swapped))
            self.assertEqual(r.load_roles(root),swapped)
            (root/'fixture-roles.json').write_text(json.dumps(r.role_map()))
            with self.assertRaisesRegex(ValueError,'changed'):r.load_roles(root)
            (root/'fixture-roles.json').unlink()
            with self.assertRaisesRegex(ValueError,'missing'):r.load_roles(root)

    def test_swap_preflight_failure_prevents_ap_actions_and_responder(self):
        root='/home/pi/phase12-recovery-'+'a'*32
        with patch.object(fixture,'load_roles',return_value=r.role_map('swapped')),patch.object(Path,'is_dir',return_value=True),patch.object(Path,'is_symlink',return_value=False),patch.object(fixture,'management',return_value={}),patch.object(fixture,'private_write') as receipt,patch.object(fixture,'preflight',side_effect=ValueError('no AP support')),patch.object(fixture,'command') as mutate,patch.object(fixture.subprocess,'Popen') as launch:
            with self.assertRaisesRegex(ValueError,'no AP support'):
                fixture.action(dict(root=root,authority='USER_AUTHORIZED_UNATTENDED_PHASE12',action='start_ap',interface='wlan0'))
            mutate.assert_not_called();launch.assert_not_called()
            self.assertEqual(receipt.call_args.args[1]['status'],'RADIO_PREFLIGHT_FAILED')

    def read(self,*argv):
        if argv[-1]=='info' and 'dev' in argv:return 'Interface '+argv[-2]+'\n\twiphy '+{'wlan0':'0','wlan1':'1','wlan2':'2'}[argv[-2]]+'\n'
        if argv[-1]=='info':return 'Supported interface modes:\n\t * managed\n\t * AP\nBand 1:\n\t * 2422 MHz [3] (20.0 dBm)\nSupported Ciphers:\n\t * CCMP (00-0f-ac:4)\n'
        if 'GENERAL.STATE' in argv:return '30 (disconnected)\n'
        if argv[-1]=='link':return 'Not connected.\n'
        if 'address' in argv:return '[{"addr_info":[]}]'
        self.fail(argv)

    def test_actual_capabilities_roles_and_bad_phy_channel_mode(self):
        roles=r.role_map('swapped');rows=[]
        def read(*argv):rows.append(argv);return self.read(*argv)
        receipt=r.preflight(roles,read)
        self.assertEqual(receipt['roles_sha256'],roles['sha256'])
        self.assertFalse(any(word in ('add','up','down','delete','set') for row in rows for word in row))
        for replacement,old in [('wiphy 0','wiphy 2'),('managed','AP'),('2422 MHz [3] (disabled)','2422 MHz [3] (20.0 dBm)'),('100 (connected)','30 (disconnected)')]:
            with self.subTest(old=old),self.assertRaises(ValueError):
                r.preflight(roles,lambda *argv:self.read(*argv).replace(old,replacement))

    def test_actual_decimal_channel_and_all_channel_three_fields(self):
        roles=r.role_map('swapped')
        for frequency in ('2422','2422.0','2422.000'):
            with self.subTest(frequency=frequency):
                result=r.preflight(roles,lambda *argv:self.read(*argv).replace('2422 MHz [3]',frequency+' MHz [3]'))
                self.assertEqual(result['status'],'READ_ONLY_CAPABILITIES_READY')
        bad=('2422.1 MHz [3]','2422.0001 MHz [3]','bad MHz [3]',
             '2422.0 MHz [3] (20.0 dBm)\n * 2422 MHz [3]',
             '2422 MHz [3] (20.0 dBm)\n * bad MHz [3]',
             '2422 MHz [3] (20.0 dBm)\n malformed [3]',
             '2422.0 MHz [3] (no IR)','2422.0 MHz [3] [3]')
        for value in bad:
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'legal active channel 3'):
                r.preflight(roles,lambda *argv:self.read(*argv).replace('2422 MHz [3]',value))

    def test_swapped_http_binds_observer_and_association_once(self):
        stream=Mock();stream.getsockname.return_value=('192.168.4.3',456)
        client=populated.HTTP();client.interface='wlan2'
        with patch.object(populated.socket,'socket',return_value=stream):client.connect(populated.time.monotonic()+2)
        stream.setsockopt.assert_called_once_with(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,b'wlan2\0')
        stream.bind.assert_called_once_with(('192.168.4.3',0))
        deadline=consumer.time.monotonic()+10;evidence=Mock()
        with patch.object(consumer,'associate_observer') as join,patch.object(consumer,'identity',return_value={}),patch.object(consumer,'bounded_command',return_value=b''):
            consumer.associate_guarded('owned','WsprryPico-abcdef',deadline,evidence,{},b'',interface='wlan2')
        join.assert_called_once_with('owned','WsprryPico-abcdef',deadline,evidence,interface='wlan2')

    def test_fixture_scope_restores_globals_on_failure(self):
        before=fixture.INTERFACE,fixture.OBSERVER
        with patch.object(fixture,'load_roles',return_value=r.role_map('swapped')),patch.object(fixture,'_action',side_effect=RuntimeError('stop')) as action:
            with self.assertRaises(RuntimeError):fixture.action(dict(root='unused'))
        self.assertEqual((fixture.INTERFACE,fixture.OBSERVER),before)
        self.assertEqual(action.call_args.args[1],r.role_map('swapped'))

    def test_responder_reloads_mapping_in_fresh_process_before_socket(self):
        roles=r.role_map('swapped');root=Path('/home/pi/phase12-recovery-'+'a'*32)
        stream=Mock();stream.__enter__=Mock(return_value=stream);stream.__exit__=Mock(return_value=False)
        stream.recvfrom.side_effect=RuntimeError('stop after bind')
        before=fixture.INTERFACE,fixture.OBSERVER
        try:
            with patch.object(fixture,'load_roles',return_value=roles) as load,patch.object(Path,'is_dir',return_value=True),patch.object(Path,'is_symlink',return_value=False),patch.object(fixture,'private_write') as write,patch.object(fixture.signal,'signal'),patch.object(fixture.socket,'socket',return_value=stream):
                with self.assertRaises(RuntimeError):fixture.serve(root,'b'*32)
            load.assert_called_once_with(root)
            stream.setsockopt.assert_any_call(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,b'wlan0\0')
            for call in write.call_args_list:self.assertEqual(call.args[1]['roles_sha256'],roles['sha256'])
        finally:fixture.INTERFACE,fixture.OBSERVER=before


if __name__=='__main__':unittest.main()
