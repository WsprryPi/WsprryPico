#!/usr/bin/env python3
"""Stage authority and actual AP socket/identity guards, no host operations."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_engineering_session_dispatch as sessions
import phase12_engineering_time_dispatch as time_jobs


class Tests(unittest.TestCase):
    def test_missing_human_authority_stops_before_private_inputs(self):
        for module in (sessions,time_jobs):
            with patch.object(module,'private_bytes') as read:
                with self.assertRaises(ValueError):module.run({'authority':'not authorized'})
                read.assert_not_called()
    def observe_ap(self,wrong_boot=False,wrong_source=False):
        root=Path('/home/pi/phase12-recovery-'+'a'*32)
        outputs=['p12-recovery-'+'a'*32,'WsprryPico-0a9d89',json.dumps([
            dict(addr_info=[dict(local='192.168.4.2',prefixlen=24)])])]
        info=dict(device_id=sessions.DEVICE,revision='b'*12,
                  status=dict(boot_id='wrong' if wrong_boot else 'c'*32))
        stream=MagicMock();stream.getsockname.return_value=('192.168.4.9' if wrong_source else '192.168.4.2',1234)
        socket=MagicMock();socket.__enter__.return_value=stream
        with patch.object(sessions,'command',side_effect=outputs),patch.object(sessions.socket,'socket',return_value=socket):
            value=sessions.ap_observation(root,'b'*40,'c'*32,lambda:info,lambda *a,**kw:None)
        return value,stream
    def test_ap_proof_binds_actual_socket_to_spare_adapter(self):
        value,stream=self.observe_ap()
        stream.setsockopt.assert_called_once_with(sessions.socket.SOL_SOCKET,sessions.socket.SO_BINDTODEVICE,b'wlan2\0')
        stream.connect.assert_called_once_with(('192.168.4.1',443))
        self.assertEqual(value['local_ipv4'],'192.168.4.2')
    def test_changed_boot_or_socket_source_rejected(self):
        for options in ({'wrong_boot':True},{'wrong_source':True}):
            with self.assertRaises(ValueError):self.observe_ap(**options)


if __name__=='__main__':unittest.main()
