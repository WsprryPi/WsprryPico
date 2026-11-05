"""Control-channel sensitivity without sleeping or starting a network fixture."""
from collections import deque
from unittest import TestCase, main, mock
from network_control import NetworkControl


class Process:
    deadline = 100
    def __init__(self, replies):
        self.replies = deque(replies)
        self.writes = []
        self.budgets = []
    def send_line(self, value, **kwargs):
        self.writes.append(value)
        self.budgets.append(kwargs['deadline'])
    def line(self, **kwargs):
        self.budgets.append(kwargs.get('deadline'))
        if not self.replies:
            raise TimeoutError('observed withheld ACK')
        return self.replies.popleft() + '\n'


class Controls(TestCase):
    def test_correlated_ack_follows_effect_facts_with_one_enclosing_budget(self):
        p = Process(['NETWORK 0 0 0', 'SYNC 1', 'SYNC 2'])
        with mock.patch('network_control.time.monotonic', return_value=10):
            c = NetworkControl(p);c.send('NETWORK STATUS')
            self.assertEqual(c.line(), 'NETWORK 0 0 0\n')
            c.send('BARRIER')
        self.assertEqual(p.writes, ['NETWORK STATUS', 'SYNC 1', 'BARRIER', 'SYNC 2'])
        self.assertTrue(p.budgets);self.assertEqual(set(p.budgets), {13})

    def test_withheld_ack_is_not_assumed_complete_and_channel_cannot_be_reused(self):
        with mock.patch('network_control.time.monotonic', return_value=10):
            p = Process([]);c = NetworkControl(p)
            with self.assertRaisesRegex(TimeoutError, 'withheld ACK'):c.send('LINK OFF')
            with self.assertRaisesRegex(RuntimeError, 'after failed'):c.send('LINK ON')
        self.assertEqual(p.writes, ['LINK OFF', 'SYNC 1'])

    def test_stale_reordered_and_malformed_ack_fail(self):
        for reply in ['SYNC 0', 'SYNC 2', 'SYNC 1 EXTRA', 'CONTROL ERROR UNKNOWN']:
            with self.subTest(reply=reply), mock.patch('network_control.time.monotonic', return_value=10):
                c = NetworkControl(Process([reply]))
                with self.assertRaises(RuntimeError):c.send('LINK OFF')
                with self.assertRaises(RuntimeError):c.line()

    def test_late_success_is_refused_even_after_receipt(self):
        with mock.patch('network_control.time.monotonic', side_effect=[10,14]):
            c = NetworkControl(Process(['SYNC 1']))
            with self.assertRaisesRegex(TimeoutError, 'Late'):c.send('BARRIER')

    def test_invalid_commands_fail_before_any_write(self):
        p = Process([]);c = NetworkControl(p)
        for command in ['', 'LINK OFF\nLINK ON', 'SYNC 1', 'lowercase', None]:
            with self.subTest(command=command), self.assertRaises(ValueError):c.send(command)
        self.assertEqual(p.writes, [])

    def test_unconsumed_facts_refuse_a_new_command(self):
        with mock.patch('network_control.time.monotonic', return_value=10):
            p = Process(['NETWORK 0 0 0', 'SYNC 1']);c = NetworkControl(p);c.send('NETWORK STATUS')
            with self.assertRaisesRegex(RuntimeError, 'Unconsumed'):c.send('LINK OFF')
        self.assertEqual(len(p.writes),2)


    def test_enclosing_observation_budget_is_propagated_to_all_io(self):
        with mock.patch('network_control.time.monotonic', return_value=10):
            p=Process(['SYNC 1']);NetworkControl(p).send('BARRIER',deadline=11)
        self.assertEqual(set(p.budgets),{11})

    def test_buffered_fact_cannot_qualify_after_its_enclosing_deadline(self):
        with mock.patch('network_control.time.monotonic',side_effect=[10,10,10,14]):
            c=NetworkControl(Process(['NETWORK 0 0 0','SYNC 1']));c.send('NETWORK STATUS')
            with self.assertRaisesRegex(TimeoutError,'Late buffered'):c.line()

if __name__ == '__main__':main()
