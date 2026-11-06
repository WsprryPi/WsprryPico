from unittest import TestCase,main,mock
from network_socket import BoundedSocket,connect_socket
class Socket:
    def __init__(self):self.budgets=[];self.calls=0;self.closed=False
    def gettimeout(self):return 5
    def settimeout(self,value):self.budgets.append(value)
    def recv(self,count):self.calls+=1;return b'actual partial bytes'
    def close(self):self.closed=True
class Boundaries(TestCase):
    def test_remaining_parent_budget_clamps_partial_read(self):
        s=Socket();b=BoundedSocket(s,12)
        with mock.patch('network_socket.time.monotonic',side_effect=[10,11]):self.assertEqual(b.recv(4096),b'actual partial bytes')
        self.assertEqual(s.budgets,[2])
    def test_late_success_and_expired_precondition_are_refused(self):
        for times,calls in [([12],0),([10,12],1)]:
            s=Socket();b=BoundedSocket(s,12)
            with mock.patch('network_socket.time.monotonic',side_effect=times),self.assertRaises(TimeoutError):b.recv(4096)
            self.assertEqual(s.calls,calls)
    def test_unbounded_socket_timeout_is_refused(self):
        b=BoundedSocket(Socket(),12)
        for value in [None,0,-1,float('inf'),float('nan')]:
            with self.subTest(value=value),self.assertRaises(ValueError):b.settimeout(value)
    def test_operation_and_cleanup_failures_both_survive(self):
        primary=RuntimeError('operation failed');cleanup=RuntimeError('close failed')
        s=Socket();s.close=mock.Mock(side_effect=cleanup)
        with self.assertRaises(BaseExceptionGroup) as caught:
            with BoundedSocket(s,12):raise primary
        self.assertEqual(caught.exception.exceptions,(primary,cleanup))
    def test_failed_tls_acquisition_closes_owned_raw_socket(self):
        s=Socket();context=mock.Mock();context.wrap_socket.side_effect=RuntimeError('actual handshake refusal')
        with mock.patch('network_socket.time.monotonic',return_value=10),mock.patch('network_socket.socket.create_connection',return_value=s):
            with self.assertRaisesRegex(RuntimeError,'handshake refusal'):connect_socket(('127.0.0.1',18443),deadline=12,tls_context=context,server_hostname='127.0.0.1')
        self.assertTrue(s.closed)
if __name__=='__main__':main()
