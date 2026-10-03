#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import unittest
from unittest.mock import patch
import phase12_consumer_composition as driver

BOOT = 'a'*32

class Evidence:
    def __init__(self): self.records = []
    def record(self, kind, **values): self.records.append((kind, values))

class Peer:
    def __init__(self, shared, name):
        self.shared, self.session, self.calls = shared, name, []
    def request(self, op, body, expected=None, **kwargs):
        self.calls.append((op, body, expected))
        s = self.shared
        if expected:
            actual = 'BUSY' if op == 'CLAIM' and s['owner_id'] else 'NOT_OWNER'
            driver.require(actual == expected, 'negative mismatch')
            return {'ok':False, 'error':{'code':actual}}
        if op == 'STATUS': return dict(s)
        if op == 'CLAIM': s['owner_id'] = body['owner_id']; return dict(s)
        if op == 'LOAD': s.update(job_id=body['job_id'], state='loaded')
        if op == 'GET_CLOCK': return {}
        if op == 'ARM': s['state'] = 'armed'
        if op == 'ABORT': s['state'] = 'aborted'
        if op == 'RELEASE': s.update(owner_id=None, job_id=None, state='empty')
        return {}

class Tests(unittest.TestCase):
    def state(self):
        return dict(boot_id=BOOT, output_active=False, owner_id=None, job_id=None, state='empty')
    def test_run_api_rejects_unbound_candidate_before_device_access(self):
        with self.assertRaises(ValueError):
            driver.run_device({}, {'candidates':[]}, '192.168.1.2', BOOT, '/unused')
        candidate = dict(role='restore', target='WsprryPico', lan_mode='plain',
                         fault_stage=1, uf2={'sha256':'c'*64})
        with self.assertRaises(ValueError):
            driver.run_device(candidate, {'candidates':[candidate], 'source_commit':'b'*40},
                              '192.168.1.2', BOOT, '/unused')

    def test_owned_inhibited_guard_and_identity(self):
        info = dict(device_id=driver.DEVICE, revision='b'*12, access_state='healthy',
                    lan_wtp_mode='plain', network={'ipv4':'192.168.1.2'},
                    status=dict(boot_id=BOOT, engine=driver.ENGINE, enabled=False,
                                output_active=False, storage_healthy=True,
                                state='running', owner_id='owner', job_id='job'))
        with patch.object(driver, 'resource_health') as health:
            driver.composition_guard(info,'b'*40,BOOT,'192.168.1.2')
            health.assert_called_once_with(info)
            with self.assertRaises(ValueError):
                driver.composition_guard(info,'b'*40,BOOT,'192.168.1.2',initial=True)
            info['status']['output_active']=True
            with self.assertRaises(ValueError):
                driver.composition_guard(info,'b'*40,BOOT,'192.168.1.2')
            info['status']['output_active']=False
            info['device_id']='wrong'
            with self.assertRaises(ValueError):
                driver.composition_guard(info,'b'*40,BOOT,'192.168.1.2')

    def test_consumer_lan_three_jobs_usb_info_foreign_refusal(self):
        state=self.state(); peer=Peer(state,'lan'); evidence=Evidence(); refused=[]
        def guard():return {'status':{k:v for k,v in state.items() if k not in ('owner_id','job_id')}}
        def refusal(address,owner_peer,boot,log,**expected):
            refused.append(expected)
            driver.check_status(dict(state),boot,owner=expected['owner'],
                                job=expected['job'],states=(expected['state'],))
        def sleep(_):
            if state['state']=='armed':state['state']='running'
        with patch.object(driver,'check_clock',return_value=1):
            self.assertEqual(driver.run_lan_directed(peer,BOOT,evidence,'192.168.1.2',
                                                    guard,refusal,sleeper=sleep),3)
        self.assertEqual([value['state'] for value in refused],['loaded','armed','running'])
        self.assertEqual(sum(op=='LOAD' for op,_,_ in peer.calls),3)
        self.assertIsNone(state['owner_id'])
    def test_single_lan_reconnect_reclaims_without_info_owner_fields(self):
        state=self.state();old=Peer(state,'old');fresh=Peer(state,'fresh');evidence=Evidence();hooks=[]
        def reconnect(deadline):
            hooks.append('connect');state['owner_id']=None
            return fresh,lambda:hooks.append('close-fresh')
        with patch.object(driver,'negotiate') as hello:
            driver.lan_disconnect_reconnect(old,BOOT,lambda:hooks.append('close-old'),reconnect,evidence)
            hello.assert_called_once_with(fresh,BOOT)
        self.assertEqual(hooks,['close-old','connect','close-fresh'])
        self.assertEqual(evidence.records[-1][0],'lan_disconnect_reconnect_pass')

    def test_consumer_foreign_admission_mutation_cleanup(self):
        state=self.state();peer=Peer(state,'lan');evidence=Evidence()
        def refusal(*args,**kwargs):state['state']='armed'
        with self.assertRaises(ValueError):
            driver.run_lan_directed(peer,BOOT,evidence,'192.168.1.2',
                                    lambda:{'status':dict(state)},refusal)
        self.assertEqual(sum(op=='ABORT' for op,_,_ in peer.calls),1)
        self.assertIsNone(state['owner_id'])
    def test_consumer_uncertain_abort_never_replayed(self):
        state=self.state();peer=Peer(state,'lan');evidence=Evidence();original=peer.request
        def request(op,body,expected=None,**kwargs):
            if op=='ABORT':peer.calls.append((op,body,expected));raise TimeoutError('uncertain')
            return original(op,body,expected,**kwargs)
        peer.request=request
        with self.assertRaises(TimeoutError):
            driver.run_lan_directed(peer,BOOT,evidence,'192.168.1.2',
                                    lambda:{'status':dict(state)},lambda *a,**k:None)
        self.assertEqual(sum(op=='ABORT' for op,_,_ in peer.calls),1)

    def test_six_cases_and_foreign_requests(self):
        state = self.state(); evidence = Evidence()
        peers = {name:Peer(state, name) for name in ('usb','plain_lan')}
        def sleep(_):
            if state['state'] == 'armed': state['state'] = 'running'
        with patch.object(driver, 'check_clock', return_value=1):
            self.assertEqual(driver.run_directed(peers, BOOT, evidence, sleeper=sleep), 6)
        all_calls = [call for peer in peers.values() for call in peer.calls]
        self.assertEqual(sum(op=='LOAD' and expected is None for op,_,expected in all_calls), 6)
        self.assertEqual(sum(expected=='BUSY' for _,_,expected in all_calls),6)
        self.assertEqual(sum(expected=='NOT_OWNER' for _,_,expected in all_calls),12)
        self.assertIsNone(state['owner_id'])
    def test_uncertain_abort_never_replayed(self):
        state=self.state(); evidence=Evidence()
        owner=Peer(state,'usb'); foreign=Peer(state,'plain_lan')
        original=owner.request
        def request(op, body, expected=None, **kwargs):
            if op == 'ABORT' and expected is None:
                owner.calls.append((op,body,expected)); raise TimeoutError('uncertain')
            return original(op,body,expected,**kwargs)
        owner.request=request
        with self.assertRaises(TimeoutError):
            driver.run_directed({'usb':owner,'plain_lan':foreign}, BOOT,evidence)
        self.assertEqual(sum(op=='ABORT' for op,_,_ in owner.calls),1)
        self.assertEqual(state['state'],'loaded')
    def test_foreign_mutation_detected(self):
        state=self.state(); state.update(owner_id='owner',job_id='job',state='loaded')
        owner=Peer(state,'usb'); foreign=Peer(state,'lan'); original=foreign.request
        def request(op,body,expected=None):
            answer=original(op,body,expected)
            if op == 'ABORT': state['state']='aborted'
            return answer
        foreign.request=request
        with self.assertRaises(RuntimeError): driver.competitors(owner,foreign,BOOT,'owner','job','loaded')
    def test_disconnect_reclamation_and_deadline(self):
        state=self.state(); lan=Peer(state,'lan'); usb=Peer(state,'usb'); evidence=Evidence()
        driver.disconnect_reclaim(lan,usb,BOOT,lambda:state.update(owner_id=None),evidence)
        self.assertEqual(evidence.records[-1][0],'disconnect_reclaim_pass')
        with self.assertRaises(TimeoutError):
            driver.disconnect_reclaim(lan,usb,BOOT,lambda:None,evidence, clock=lambda:0, sleeper=lambda _:None)
    def test_dtr_high_attempted_when_flush_fails(self):
        with patch.object(driver.termios,'tcflush',side_effect=OSError('flush failed')):
            with patch.object(driver.fcntl,'ioctl') as ioctl:
                with self.assertRaises(OSError): driver.restore_usb_dtr(17)
                ioctl.assert_called_once_with(17, driver.termios.TIOCMBIS,
                    driver.struct.pack('I',driver.termios.TIOCM_DTR))

    def test_both_carriers_reclaim_with_fresh_usb_session(self):
        state=self.state(); old=Peer(state,'old-usb'); lan=Peer(state,'lan')
        peers={'usb':old,'plain_lan':lan}; fresh=Peer(state,'fresh-usb'); hooks=[]
        def down(): hooks.append('down'); state['owner_id']=None
        def up(): hooks.append('up')
        def close(): hooks.append('lan-close'); state['owner_id']=None
        evidence=Evidence()
        with patch.object(driver,'negotiate') as hello:
            driver.reclaim_both_carriers(peers,BOOT,evidence,down,up,lambda:fresh,close)
            hello.assert_called_once_with(fresh,BOOT)
        self.assertEqual(hooks,['down','up','lan-close'])
        self.assertIs(peers['usb'],fresh)
        self.assertEqual(sum(kind=='disconnect_reclaim_pass' for kind,_ in evidence.records),2)
        self.assertFalse(any(op=='LOAD' for peer in (old,lan,fresh) for op,_,_ in peer.calls))
    def test_usb_dtr_restored_when_reclaim_fails(self):
        peers={'usb':Peer(self.state(),'usb'),'plain_lan':Peer(self.state(),'lan')}
        hooks=[]
        with patch.object(driver,'disconnect_reclaim',side_effect=TimeoutError('uncertain')):
            with self.assertRaises(TimeoutError):
                driver.reclaim_both_carriers(peers,BOOT,Evidence(),lambda:None,
                                            lambda:hooks.append('up'),lambda:None,lambda:None)
        self.assertEqual(hooks,['up'])

    def test_late_unowned_reclaim_is_not_pass(self):
        state=self.state(); lan=Peer(state,'lan'); usb=Peer(state,'usb'); evidence=Evidence()
        ticks=[0]
        original=usb.request
        def request(op,body,expected=None,**kwargs):
            answer=original(op,body,expected,**kwargs)
            if op == 'STATUS' and state['owner_id'] is None:
                ticks[0]=8
            return answer
        usb.request=request
        usb.stage_deadline=123456
        with self.assertRaises(ValueError):
            driver.disconnect_reclaim(lan,usb,BOOT,lambda:state.update(owner_id=None),
                                      evidence, clock=lambda:ticks[0])
        self.assertEqual(usb.stage_deadline,123456)
        self.assertFalse(any(kind=='disconnect_reclaim_pass' for kind,_ in evidence.records))

    def test_excess_timeout_is_not_refusal(self):
        class Sock:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def settimeout(self,value): pass
            def recv(self,value): raise TimeoutError('inconclusive')
        with self.assertRaises(TimeoutError):
            driver.refused_connections('192.168.1.2',Peer(self.state(),'lan'),BOOT,Evidence(),connector=lambda *a,**k:Sock())
    def test_max_frame_and_negative_error_are_checked(self):
        evidence=Evidence(); peer=driver.Peer(-1,'usb',evidence)
        sent=[]; peer.write=lambda wire, deadline:sent.append(wire)
        peer.message=lambda deadline:dict(type='response',request_id='%032x'%peer.sequence,op='STATUS',ok=False,error={'code':'BUSY'})
        with self.assertRaises(ValueError): peer.request('STATUS',{},expected='NOT_OWNER')
        peer.message=lambda deadline:dict(type='response',request_id='%032x'%peer.sequence,op='STATUS',ok=True,body={})
        peer.request('STATUS',{},padding=65536)
        self.assertEqual(len(sent[-1]),65552)
        with self.assertRaises(ValueError): peer.request('STATUS',{},padding=65537)

if __name__ == '__main__': unittest.main()
