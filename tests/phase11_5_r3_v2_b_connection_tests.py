import socket,sys,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_parallel_b_functional import connect_http
class ConnectionTests(unittest.TestCase):
    def packet(self):return dict(address='192.168.1.53',network_path=dict(interface='wlan1',source_address='192.168.1.117'))
    def test_bound_socket(self):
        with patch.object(socket,'SO_BINDTODEVICE',25,create=True),patch.object(socket,'socket') as constructor:
            stream=constructor.return_value
            self.assertIs(connect_http(self.packet()),stream)
            stream.setsockopt.assert_called_once_with(socket.SOL_SOCKET,25,b'wlan1\0')
            stream.bind.assert_called_once_with(('192.168.1.117',0));stream.connect.assert_called_once_with(('192.168.1.53',18443))
            stream.close.assert_not_called()
    def test_failure_closes(self):
        with patch.object(socket,'SO_BINDTODEVICE',25,create=True),patch.object(socket,'socket') as constructor:
            constructor.return_value.connect.side_effect=TimeoutError()
            with self.assertRaises(TimeoutError):connect_http(self.packet())
            constructor.return_value.close.assert_called_once()
    def test_wrong_path_no_socket(self):
        p=self.packet();p['network_path']['interface']='wlan0'
        with patch.object(socket,'socket') as constructor:
            with self.assertRaises(ValueError):connect_http(p)
            constructor.assert_not_called()
if __name__=='__main__':unittest.main()
