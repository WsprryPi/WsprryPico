#!/usr/bin/env python3
"""Actual wire adapter regressions; no hardware dependencies instantiated."""
import json
import sys
import time
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_engineering_flash_status_dispatch as m
from validate_wtp_contract import frame


def framed(value):return frame(json.dumps(value,separators=(',',':')).encode())
class Evidence:
    def __init__(self):self.records=[]
    def record(self,kind,**value):self.records.append((kind,value))


class Tests(unittest.TestCase):
    def test_fragmented_original_frames_and_event(self):
        sent=[];incoming=[];e=Evidence()
        def send(raw,end):
            sent.append(raw);req=m.decode(raw)
            event=framed(dict(protocol='WTP/1',session_id=req['session_id'],type='event',body={}))
            response=framed({**req,'type':'response','ok':True,'body':{'actual':'payload'}})
            incoming.extend([event[:3],event[3:]+response[:19],response[19:]])
        peer=m.WireChannel(send,lambda end:incoming.pop(0),e,'usb')
        request,response=peer.wire_exchange('STATUS',{},time.monotonic()+1)
        self.assertEqual(request,sent[0]);self.assertEqual(m.decode(response)['body'],{'actual':'payload'})
        raw_received=b''.join(r[1]['hex'] and bytes.fromhex(r[1]['hex']) for r in e.records if r[0]=='wtp_rx')
        self.assertTrue(raw_received.endswith(response))
    def test_expired_deadline_emits_nothing(self):
        sent=[];peer=m.WireChannel(lambda raw,end:sent.append(raw),None,Evidence(),'usb')
        with self.assertRaises(Exception):peer.wire_exchange('STATUS',{},time.monotonic()-1)
        self.assertEqual(sent,[])
    def test_crc_invalid_never_accepted(self):
        value=framed({'protocol':'WTP/1','session_id':'s','type':'response','op':'STATUS','request_id':'r'})
        with self.assertRaises(Exception):m.CapturedFrames().feed(value[:-1]+b'x')
    def test_no_resynchronization(self):
        with self.assertRaises(Exception):m.CapturedFrames().feed(b'x'*16)
    def test_wrong_request_refused(self):
        c=m.CapturedFrames();c.feed(framed(dict(protocol='WTP/1',session_id='s',type='response',op='STATUS',request_id='wrong')))
        with self.assertRaises(Exception):c.matching(dict(session_id='s',op='STATUS',request_id='right'))
    def test_events_bounded(self):
        c=m.CapturedFrames()
        with self.assertRaises(Exception):
            for _ in range(66):c.feed(framed(dict(protocol='WTP/1',session_id='s',type='event')))
    def test_partial_response_refused(self):
        c=m.CapturedFrames();c.feed(framed(dict(protocol='WTP/1',session_id='s',type='response',op='STATUS',request_id='r'))[:-1])
        with self.assertRaises(Exception):c.matching(dict(session_id='s',op='STATUS',request_id='r'))
    def test_ble_exact_fragment_capture(self):
        evidence=Evidence();holder={}
        class Client:
            timeout=5
            class Backend:deadline=0
            backend=Backend()
            def wtp_exchange(self,op,body):
                request=framed(dict(protocol='WTP/1',session_id='s',type='request',op=op,body=body,request_id='r'))
                response=framed({**m.decode(request),'type':'response','ok':True,'body':{'reply':True}})
                for kind,key,raw in [('private_gatt_write','wtpCommand',request),('private_gatt_notify','wtpStatus',response)]:
                    for offset in range(0,len(raw),13):
                        holder['peer'].emitted(dict(kind=kind,uuid=m.UUIDS[key],hex=raw[offset:offset+13].hex()))
                return {'reply':True}
        peer=m.BleWire(Client(),evidence);holder['peer']=peer
        tx,rx=peer.wire_exchange('STATUS',{},time.monotonic()+1)
        self.assertEqual(m.decode(tx)['op'],'STATUS');self.assertEqual(m.decode(rx)['body'],{'reply':True})
        self.assertEqual(evidence.records[0][1]['response_hex'],rx.hex())
    def test_ble_decoded_reply_without_actual_notification_rejected(self):
        class Client:
            class Backend:deadline=0
            backend=Backend()
            def wtp_exchange(self,op,body):return {'invented':True}
        with self.assertRaises(Exception):m.BleWire(Client(),Evidence()).wire_exchange('STATUS',{},time.monotonic()+1)
    def test_segment_writes_use_remaining_absolute_timeout(self):
        clock=[0.0];timeouts=[]
        class Characteristic:
            def WriteValue(self,*args,**kwargs):
                timeouts.append(kwargs['timeout']);clock[0]+=.6
        backend=object.__new__(m.DeadlineBackend);backend.deadline=1.5
        bounded=m.DeadlineInterface(Characteristic(),backend.remaining)
        with patch.object(m.time,'monotonic',side_effect=lambda:clock[0]):
            bounded.WriteValue(b'first',{})
            bounded.WriteValue(b'second',{})
            bounded.WriteValue(b'third',{})
            with self.assertRaises(Exception):bounded.WriteValue(b'late',{})
        self.assertAlmostEqual(timeouts[0],1.5);self.assertAlmostEqual(timeouts[1],.9)
        self.assertAlmostEqual(timeouts[2],.3);self.assertEqual(len(timeouts),3)
    def test_stalled_dbus_write_has_explicit_finite_timeout(self):
        received=[]
        class Characteristic:
            def WriteValue(self,*args,**kwargs):
                received.append(kwargs['timeout']);raise TimeoutError('DBus deadline expired')
        bounded=m.DeadlineInterface(Characteristic(),lambda:.25)
        with self.assertRaises(TimeoutError):bounded.WriteValue(b'bytes',{})
        self.assertEqual(received,[.25])
    def test_production_backend_write_passes_timeout_to_dbus(self):
        clock=[1.0];calls=[];emitted=[]
        class DBus:
            @staticmethod
            def Array(value,signature):return value
            Byte=int
            String=str
        class Characteristic:
            def WriteValue(self,*args,**kwargs):calls.append((args,kwargs))
        backend=object.__new__(m.DeadlineBackend);backend.deadline=1.75
        backend.dbus=DBus();backend.emit=emitted.append
        backend._characteristic=lambda uuid:('/',m.DeadlineInterface(Characteristic(),backend.remaining))
        with patch.object(m.time,'monotonic',side_effect=lambda:clock[0]):
            backend.write(m.UUIDS['wtpCommand'],b'actual',True)
            clock[0]=2
            with self.assertRaises(Exception):backend.write(m.UUIDS['wtpCommand'],b'late',True)
        self.assertEqual(calls[0][1],{'timeout':.75,'signature':'aya{sv}'});self.assertEqual(len(calls),1)
        self.assertEqual(bytes(calls[0][0][0]),b'actual')
    def test_client_wait_only_remaining_after_fragment_writes(self):
        backend=object.__new__(m.DeadlineBackend);backend.deadline=10
        client=object.__new__(m.DeadlineClient);client.backend=backend;client.timeout=5
        with patch.object(m.time,'monotonic',return_value=9.75), patch.object(m.Client,'_wait',return_value={}) as wait:
            client._wait({},'id','timeout')
        self.assertEqual(wait.call_args.args[-1],.25)
    def test_event_pump_remains_bounded_under_pending_signal_storm(self):
        clock=[0.0];iterations=[]
        class Context:
            def pending(self):return True
            def iteration(self,blocking):iterations.append(blocking);clock[0]+=.005
        backend=object.__new__(m.DeadlineBackend);backend.deadline=1;backend.context=Context()
        with patch.object(m.time,'monotonic',side_effect=lambda:clock[0]):backend.pump(.02)
        self.assertEqual(iterations,[False]*4)
    def test_proxy_introspection_disabled(self):
        class Bus:
            def get_object(self,*args,**kwargs):return kwargs
        self.assertEqual(m.NoIntrospectionBus(Bus()).get_object('bluez','/'),{'introspect':False})
    def test_authority_rejected_before_io(self):
        with self.assertRaises(Exception):m.bound_plan({'authority':'wrong'})

if __name__=='__main__':unittest.main()
