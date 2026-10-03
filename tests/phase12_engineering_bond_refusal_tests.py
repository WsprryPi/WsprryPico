#!/usr/bin/env python3
"""Offline exact DBus security-refusal capture tests; never instantiate BlueZ."""
import sys
import time
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_engineering_bond_refusal_dispatch as m


class DBusError(Exception):
    def __init__(self,name,message):self.name=name;self.message=message
    def get_dbus_name(self):return self.name
    def get_dbus_message(self):return self.message


class Tests(unittest.TestCase):
    def exercise(self,name,message):
        emitted=[];backend=object.__new__(m.RefusalBackend);backend.errors=[];backend.emit=emitted.append
        backend._wait=lambda predicate,*args: predicate()
        calls=[]
        class Interface:
            def Connect(self,**kwargs):
                calls.append(kwargs);kwargs['error_handler'](DBusError(name,message))
        class Client:
            timeout=5
            def connect(self,address,device,allow_pairing):
                self.binding=(address,device,allow_pairing)
                backend._async(Interface(),'Connect',5,'connect_failed')
        client=Client();result=m.attempt(client,backend,'AA:BB:CC:DD:EE:FF',time.monotonic()+10)
        self.assertEqual(client.binding,('AA:BB:CC:DD:EE:FF',m.DEVICE,False));self.assertEqual(len(calls),1)
        self.assertLessEqual(calls[0]['timeout'],5)
        self.assertEqual(emitted[0]['name'],name);self.assertEqual(emitted[0]['message'],message)
        self.assertEqual(result['old_peer_attempts'],1);self.assertEqual(result['pairing_attempts'],0)
        return result
    def test_actual_async_authentication_refusal_preserved(self):
        result=self.exercise('org.bluez.Error.AuthenticationFailed','actual daemon authentication failure')
        self.assertTrue(result['cryptographic_peer_refusal_observed'])
        self.assertEqual(result['actual_dbus_errors'][0]['method'],'Connect')
    def test_exact_authentication_rejected(self):
        self.assertTrue(self.exercise('org.bluez.Error.AuthenticationRejected','rejected')['cryptographic_peer_refusal_observed'])
    def test_explicit_key_missing(self):
        self.assertTrue(self.exercise('org.bluez.Error.Failed','PIN or Key Missing')['cryptographic_peer_refusal_observed'])
    def test_generic_error_and_timeout_never_qualify(self):
        for name,message in [('org.bluez.Error.Failed','le-connection-abort-by-local'),
                             ('org.freedesktop.DBus.Error.NoReply','timeout'),('org.bluez.Error.NotReady','adapter off')]:
            self.assertFalse(self.exercise(name,message)['cryptographic_peer_refusal_observed'])
    def test_pairing_async_is_prohibited(self):
        backend=object.__new__(m.RefusalBackend)
        with self.assertRaises(ValueError):backend._async(None,'Pair',1,'failure')
    def test_synchronous_read_error_preserves_actual_dbus_name(self):
        captured=[]
        class Interface:
            def ReadValue(self,*args):raise DBusError('org.bluez.Error.AuthenticationFailed','key rejected')
        backend=object.__new__(m.RefusalBackend);backend.errors=[];backend.emit=captured.append
        with self.assertRaises(DBusError):m.CaptureInterface(Interface(),backend.capture).ReadValue({})
        self.assertEqual(captured[0]['method'],'ReadValue');self.assertTrue(m.qualifies(backend.errors[0]))
    def test_unrelated_manager_error_is_inconclusive(self):
        self.assertFalse(m.qualifies(dict(method='GetManagedObjects',name='org.bluez.Error.AuthenticationFailed',message='error')))
    def test_authority_before_any_input_or_hardware(self):
        with self.assertRaises(ValueError):m.run({'authority':'wrong'})

if __name__=='__main__':unittest.main()
