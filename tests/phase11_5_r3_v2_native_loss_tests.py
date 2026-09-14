"""No hardware: native loss requires actual written ARM and complete matching ACK."""
import copy,json,struct,sys,unittest
from unittest.mock import patch,MagicMock
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_native_loss import acknowledged_arm_prefix,socket_identity,drop_native_socket
from validate_wtp_contract import frame

class NativeLossTests(unittest.TestCase):
    def setUp(self):
        self.binding=dict(session_id='1'*32,job_id='3'*32,start_utc_ns='1800000000000000000')
        self.packet=dict(peer_sha256='ab'*32,boot_id='2'*32)
        self.request=dict(type='request',protocol='WTP/1',session_id='1'*32,request_id='4'*32,op='ARM',
            body=dict(job_id='3'*32,start_utc_ns=self.binding['start_utc_ns'],max_start_uncertainty_ns='500000000'))
        self.response=dict(type='response',protocol='WTP/1',session_id='1'*32,request_id='4'*32,op='ARM',ok=True,
            body=dict(job_id='3'*32,state='armed',start_utc_ns=self.binding['start_utc_ns'],start_monotonic_ns='100000000000',
                clock=dict(state='synchronized',utc_now_ns='1799999990000000000',monotonic_now_ns='90000000000',
                    uncertainty_ns='250000',sync_age_ns='1000000000',leap='normal')))
    def encoded(self,response=None,request=None):
        q=frame(json.dumps(request or self.request).encode());r=frame(json.dumps(response or self.response).encode())
        records=[(0,0,b''),(1,1,b''),(2,1,bytes.fromhex(self.packet['peer_sha256'])),(7,1,q),(3,1,q),(4,1,r)]
        return b''.join(struct.pack('>8s7Q',b'P115TLS2',n,k,c,n+1,n+1,42,len(b))+b for n,(k,c,b) in enumerate(records))
    def test_ack_and_partial_publication(self):
        raw=self.encoded();r=acknowledged_arm_prefix(raw,42,self.binding,self.packet)
        self.assertEqual(r['response'],self.response)
        self.assertIsNone(acknowledged_arm_prefix(raw[:-1],42,self.binding,self.packet))
        self.assertEqual(acknowledged_arm_prefix(raw+b'P115',42,self.binding,self.packet),r)
    def test_wrong_identity_or_uncertain_ack(self):
        for field,value in [('session_id','5'*32),('request_id','5'*32),('ok',False),('op','LOAD')]:
            response=copy.deepcopy(self.response);response[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                acknowledged_arm_prefix(self.encoded(response),42,self.binding,self.packet)
        response=copy.deepcopy(self.response);response['body']['job_id']='5'*32
        with self.assertRaises(ValueError):acknowledged_arm_prefix(self.encoded(response),42,self.binding,self.packet)
        with self.assertRaises(ValueError):acknowledged_arm_prefix(self.encoded(),43,self.binding,self.packet)
        bad=bytearray(self.encoded());bad[-1]^=1
        with self.assertRaises(ValueError):acknowledged_arm_prefix(bytes(bad),42,self.binding,self.packet)
    def test_no_cut_during_partial_or_mutating_write(self):
        raw=self.encoded();request=dict(self.request,request_id='6'*32,op='RENEW',body=dict(owner_id='7'*32,lease_ms=60000))
        payload=frame(json.dumps(request).encode())
        def record(n,kind,body):return struct.pack('>8s7Q',b'P115TLS2',n,kind,1,n+1,n+1,42,len(body))+body
        self.assertIsNone(acknowledged_arm_prefix(raw+record(6,7,payload),42,self.binding,self.packet))
        self.assertIsNone(acknowledged_arm_prefix(raw+record(6,7,payload)+record(7,3,payload),42,self.binding,self.packet))

    def test_socket_scope(self):
        row='ESTAB 0 0 10.77.15.2:44444 10.77.15.10:18443 users:(("native",pid=42,fd=9))\n'
        self.assertEqual(socket_identity(row,42)['local_port'],44444)
        for changed in [row+row,row.replace('pid=42','pid=43'),row.replace('10.77.15.10','192.168.1.53'),
            row.replace(':18443',':22'),row.replace('ESTAB','CLOSE-WAIT'),'']:
            with self.subTest(row=changed),self.assertRaises(ValueError):socket_identity(changed,42)

    def test_socket_destroy_zero_exit_with_error_is_failure(self):
        row='ESTAB 0 0 10.77.15.2:44444 10.77.15.10:18443 users:(("native",pid=42,fd=9))\n'
        with patch('phase11_5_r3_v2_native_loss.subprocess') as proc,patch('phase11_5_r3_v2_native_loss.Path') as path:
            proc.check_output.return_value=row
            proc.run.return_value=MagicMock(returncode=0,stdout='',stderr='RTNETLINK answers: Invalid argument')
            path.return_value.readlink.return_value.as_posix.return_value='socket:[99]'
            with self.assertRaisesRegex(ValueError,'socket loss failed'):drop_native_socket(42,lambda *_:None)

    def test_pidfd_duplicate_identity_and_cleanup(self):
        row='ESTAB 0 0 10.77.15.2:44444 10.77.15.10:18443 users:(("native",pid=42,fd=9))\n'
        for peer,accepted in [(('10.77.15.10',18443),True),(('192.168.1.53',18443),False)]:
            with patch('phase11_5_r3_v2_native_loss.subprocess') as proc,patch('phase11_5_r3_v2_native_loss.Path') as path, \
                patch('phase11_5_r3_v2_native_loss.platform') as plat,patch('phase11_5_r3_v2_native_loss.os') as os, \
                patch('phase11_5_r3_v2_native_loss.ctypes') as libc,patch('phase11_5_r3_v2_native_loss.socket.socket') as sock:
                proc.check_output.return_value=row;path.return_value.readlink.return_value.as_posix.return_value='socket:[99]'
                plat.system.return_value='Linux';plat.machine.return_value='aarch64';os.pidfd_open.return_value=20
                libc.CDLL.return_value.syscall.return_value=21
                stream=sock.return_value.__enter__.return_value
                stream.getsockname.return_value=('10.77.15.2',44444);stream.getpeername.return_value=peer
                events=[]
                if accepted:
                    drop_native_socket(42,lambda k,v:events.append((k,v)),'pidfd-duplicate-shutdown-v1')
                    self.assertEqual(events[-1][1]['socket_inode'],'socket:[99]');stream.shutdown.assert_called_once()
                else:
                    with self.assertRaisesRegex(ValueError,'identity changed'):
                        drop_native_socket(42,lambda k,v:events.append((k,v)),'pidfd-duplicate-shutdown-v1')
                    stream.shutdown.assert_not_called()
                os.close.assert_called_once_with(20)
if __name__=='__main__':unittest.main()
