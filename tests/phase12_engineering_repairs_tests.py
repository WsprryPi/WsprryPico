#!/usr/bin/env python3
"""Regressions for observed harness failures; imports never access hardware."""
import ast
import copy
import json
import pathlib
from pathlib import Path
import sys
import time
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'scripts'
sys.path.insert(0,str(P))
import phase12_engineering_flash_status_dispatch as flash
import phase12_engineering_setup as module
import phase12_engineering_time_dispatch as m
import phase12_engineering_network_dispatch as network
import phase12_engineering_session_dispatch as session
from wsprrypico_ble import BluezBackend,ClientError
from phase12_fixture_roles import role_map

class OriginalError(Exception):
    def get_dbus_name(self):return 'org.bluez.Error.Failed'
class Evidence:
    def __init__(self):self.rows=[]
    def record(self,kind,**value):self.rows.append(dict(kind=kind,**value))

class FlashSignatureTests(unittest.TestCase):
    def test_inherited_read_empty_options_with_disabled_introspection(self):
        calls=[]
        class Gatt:
            def ReadValue(self,options,**kw):
                calls.append((options,kw))
                if kw.get('signature')!='a{sv}':raise ValueError('Unable to guess signature from an empty dict')
                return b'actual identity bytes'
        backend=BluezBackend.__new__(BluezBackend)
        backend._characteristic=lambda uuid:('/',flash.DeadlineInterface(Gatt(),lambda:.25))
        self.assertEqual(backend.read('identity'),b'actual identity bytes')
        self.assertEqual(calls,[({},dict(timeout=.25,signature='a{sv}'))])
    def test_uncertain_write_explicit_signature_deadline_and_no_retry(self):
        calls=[]
        class Gatt:
            def WriteValue(self,*args,**kw):calls.append(kw);raise TimeoutError('uncertain')
        with self.assertRaises(TimeoutError):flash.DeadlineInterface(Gatt(),lambda:.2).WriteValue([],{'type':'request'})
        self.assertEqual(calls,[dict(timeout=.2,signature='aya{sv}')])

class NetworkReceiptTests(unittest.TestCase):

    def test_actual_parser_empty_disconnected_and_owned_connection_preservation(self):
        tree = ast.parse((P / 'phase12_engineering_network_dispatch.py').read_text())
        node = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'parse_interfaces'))
        ns = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), 'actual', 'exec'), ns)
        for empty in ('', '--'):
            v = ns['parse_interfaces'](('wlan0:disconnected:' + empty + '\nwlan2:connected:owned\n').encode())
            self.assertIsNone(v['wlan0']['connection'])
            self.assertEqual(v['wlan2']['connection'], 'owned')
        self.assertEqual(ns['parse_interfaces'](b'wlan0:disconnected:foreign\n')['wlan0']['connection'], 'foreign')

    def test_actual_guard_retains_original_receipt_and_closes_on_failure(self):
        tree = ast.parse((P / 'phase12_engineering_network_dispatch.py').read_text())
        f = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'execute'))
        start = next((i for i, n in enumerate(f.body) if isinstance(n, ast.Assign) and any((isinstance(t, ast.Name) and t.id == 'evidence' for t in n.targets))))
        nodes = f.body[start:start + 3]
        for selection,wrong in ((selection,wrong) for selection in ('engineering','swapped') for wrong in (False,True,'connected','management')):
            calls = []

            class Evidence:

                def __init__(self, path):
                    pass

                def record(self, event, **kw):
                    calls.append(('record', kw))

                def close(self):
                    calls.append(('close',))

            def require(ok, msg):
                if not ok:
                    raise ValueError(msg)
            roles=role_map(selection);observer=roles['observer'];host_ap=roles['host_ap']
            rows = {observer: dict(state='connected' if wrong=='connected' else 'disconnected', connection='foreign' if wrong is True else None), host_ap: dict(connection='owned'), 'eth0': dict(state='disconnected' if wrong=='management' else 'connected'), 'wlan1': dict(state='connected')}
            ns = dict(root=P, Evidence=Evidence, baseline=b'actual NMstatus', route=b'actualroutes', interfaces=rows, owned='owned', require=require,roles=roles,HOST_AP=host_ap,OBSERVER_INTERFACE=observer)
            code = compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), 'actual', 'exec')
            if wrong:
                with self.assertRaises(ValueError):
                    exec(code, ns)
                self.assertEqual(calls[-1], ('close',))
            else:
                exec(code, ns)
            self.assertEqual(calls[0][1], dict(raw_hex=b'actual NMstatus'.hex(), route_hex=b'actualroutes'.hex(),roles=roles))

class WarmNetworkTests(unittest.TestCase):

    def test_actual_network_callback_retains_warm_boot_and_fails_before_mutations(self):
        tree = ast.parse((P / 'phase12_engineering_orchestrator.py').read_text())
        fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'accelerated'))
        fn.decorator_list = []
        for fault in (None, 'boot', 'generation', 'late', 'link', 'clock', 'accepted', 'source'):
            calls = []
            now = [0.0]
            original = dict(status=dict(boot_id='b', clock_state='synchronized'), provisioning_source='provisioned', provisioning_generation='2', network=dict(link_status=3, ipv4='192.168.84.2', accepted='1'))
            info = copy.deepcopy(original)
            if fault == 'boot':
                info['status']['boot_id'] = 'foreign'
            if fault == 'generation':
                info['provisioning_generation'] = '3'
            if fault == 'link':
                info['network']['link_status'] = 1
            if fault == 'clock':
                info['status']['clock_state'] = 'unsynchronized'
            if fault == 'accepted':
                info['network']['accepted'] = '0'
            if fault == 'source':
                info['provisioning_source'] = 'consumer_preclock'

            class Backend:
                remote = '/private/retained'

                def info(self):
                    calls.append('INFO')
                    now[0] = 6 if fault == 'late' else 0
                    return info

                def snapshot(self, *a):
                    raise AssertionError('must not enter ROM')

                def deploy(self, *a, **k):
                    raise AssertionError('must not redeploy')

            class Remote:

                def fixture(self, action, *a):
                    calls.append(action)
                    self_outer.assertNotEqual(action, 'sntp_off')

                def stage(self, *a):
                    return 'hash'

                def invoke(self, script, payload, **k):
                    calls.append(('invoke', payload))
                    return {}

                def collect(self, *a):
                    pass
            self_outer = self

            def require(ok, msg):
                if not ok:
                    raise ValueError(msg)
            retained = []
            ns = dict(a=type('Args', (), dict(scope='network',fixture_roles='engineering', preparation_manifest=P / 'manifest'))(), remote=Remote(), time=type('Clock', (), dict(monotonic=staticmethod(lambda: now[0])))(), private_write=lambda path, value: retained.append((path, value)), safe_info=lambda *a: None, preparation={'source_commit': 'a' * 40, 'candidates': [dict(role='engineering', uf2={'sha256': 'image'})]}, counter=lambda v, *a: int(v), require=require, Path=pathlib.Path, __file__=str(P / 'phase12_engineering_orchestrator.py'), sha=lambda p: 'hash', AUTHORITY='authorized', server_sha256='server',role_map=role_map)
            exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), 'actual', 'exec'), ns)
            context = dict(backend=Backend(), info=original, root=P, profile_path='profile', ble_address='peer')
            if fault:
                with self.assertRaises(ValueError):
                    ns['accelerated'](context)
                self.assertFalse(any((isinstance(x, tuple) for x in calls)))
            else:
                ns['accelerated'](context)
                payload = next((x[1] for x in calls if isinstance(x, tuple)))
                self.assertEqual(payload['boot_id'], 'b')
                self.assertEqual(payload['profile_generation'], 2)
            self.assertEqual(retained[0][0].name, 'network-retained-warm-info.json')
            self.assertEqual(retained[0][1], info)

class OriginalGattErrorTests(unittest.TestCase):
    def test_failed_logger_preserves_original_uncertain_write_error(self):
        error=OriginalError('original uncertain delivery');calls=[]
        class Characteristic:
            def WriteValue(self,*args):calls.append(args);raise error
        def emit(event):
            if event['kind']=='private_host_ble_sync_error':raise OSError('logging failed')
        backend=object.__new__(module.RecordedBackend);backend.emit=emit
        backend.dbus=SimpleNamespace(Array=lambda value,**kwargs:value,Byte=int,String=str)
        with patch.object(BluezBackend,'_characteristic',return_value=('/exact',Characteristic())):
            with self.assertRaises(ClientError) as raised:backend.write('exact-uuid',b'original')
        self.assertEqual(raised.exception.code,'gatt_write')
        self.assertIs(raised.exception.__context__,error);self.assertEqual(len(calls),1)

    def test_real_inherited_write_retains_original_error_and_no_retry(self):
        events = []
        calls = []

        class Characteristic:

            def WriteValue(self, *args):
                calls.append(args)
                raise OriginalError('actual bounded diagnostic seam')
        backend = object.__new__(module.RecordedBackend)
        backend.emit = events.append
        backend.dbus = SimpleNamespace(Array=lambda value, **kwargs: value, Byte=int, String=str)
        with patch.object(BluezBackend, '_characteristic', return_value=('/exact', Characteristic())):
            with self.assertRaises(ClientError) as raised:
                backend.write('exact-uuid', b'original')
        self.assertEqual(raised.exception.code, 'gatt_write')
        self.assertEqual(len(calls), 1)
        errors = [e for e in events if e['kind'] == 'private_host_ble_sync_error']
        self.assertEqual(errors, [dict(kind='private_host_ble_sync_error', method='WriteValue', uuid='exact-uuid', dbus_name='org.bluez.Error.Failed', message='actual bounded diagnostic seam')])

class FailureInfoTests(unittest.TestCase):

    def request(self):
        return dict(source_commit='a' * 40, boot_id='b' * 32, profile_generation=2)

    def test_one_original_reply_retained_before_wrongboot_guard(self):
        calls = []
        e = Evidence()
        info = dict(device_id=m.DEVICE, revision='a' * 12, status={'boot_id': 'c' * 32}, provisioning_generation=2)
        raw = json.dumps(info).encode()

        def observe():
            calls.append(True)
            return (info, raw)
        m.retain_failure_info(self.request(), observe, e, time.monotonic() + 280)
        self.assertEqual(len(calls), 1)
        self.assertEqual([r['kind'] for r in e.rows], ['failure_usb_info', 'failure_info_unavailable'])
        self.assertEqual(e.rows[0]['raw_hex'], raw.hex())

    def test_deadline_refuses_read_and_observer_failure_never_retries(self):
        calls = []
        e = Evidence()

        def observe():
            calls.append(True)
            raise OSError('original observer failure')
        m.retain_failure_info(self.request(), observe, e, time.monotonic() - 1)
        self.assertEqual(calls, [])
        m.retain_failure_info(self.request(), observe, e, time.monotonic() + 280)
        self.assertEqual(len(calls), 1)
        self.assertEqual(e.rows[-1]['error_type'], 'OSError')

    def test_real_alarm_bounds_slow_observer_and_restores_handler(self):
        import signal
        handler = signal.getsignal(signal.SIGALRM)
        e = Evidence()
        start = time.monotonic()
        m.retain_failure_info(self.request(), lambda: time.sleep(1), e, start + 0.03)
        self.assertLess(time.monotonic() - start, 0.3)
        self.assertEqual(e.rows[-1]['error_type'], 'TimeoutError')
        self.assertEqual(signal.getsignal(signal.SIGALRM), handler)

class FlashHostDiagnosticTests(unittest.TestCase):

    def test_actual_emitter_retains_original_error_without_auth_values_or_replay(self):
        t = ast.parse((P / 'phase12_engineering_flash_status_dispatch.py').read_text())
        callback = next((n for n in ast.walk(t) if isinstance(n, ast.FunctionDef) and n.name == 'emitted' and (len(n.args.args) == 1)))
        rows = []

        class Evidence:

            def record(self, kind, **value):
                rows.append(dict(kind=kind, **value))
        env = dict(evidence=Evidence(), holder={}, UUIDS={'wtpCommand': 'command', 'wtpStatus': 'status'})
        exec(compile(ast.fix_missing_locations(ast.Module(body=[callback], type_ignores=[])), 'actual-emitter', 'exec'), env)
        original = dict(kind='private_host_ble_async_error', method='Connect', code='connect_failed', dbus_name='org.bluez.Error.Failed', message='original actual failure')
        env['emitted'](original)
        env['emitted'](dict(kind='private_gatt_write', uuid='field', hex='private-password'))
        self.assertEqual(rows, [dict(kind='ble_host_error', value=original)])
        backend = object.__new__(module.RecordedBackend)
        backend.emit = env['emitted']
        calls = []

        class OriginalError(Exception):

            def get_dbus_name(self):
                return 'org.bluez.Error.Failed'

        class Interface:

            def Connect(self, **kwargs):
                calls.append(True)
                kwargs['error_handler'](OriginalError('one original Connect failure'))

        def async_call(self, interface, method, timeout, code, *args):
            state = []
            getattr(interface, method)(error_handler=state.append)
            if state:
                raise ClientError(code)
        with patch.object(BluezBackend, '_async', async_call):
            with self.assertRaises(ClientError):
                backend._async(Interface(), 'Connect', 5, 'connect_failed')
        self.assertEqual(len(calls), 1)
        self.assertEqual(rows[-1]['value']['dbus_name'], 'org.bluez.Error.Failed')
        self.assertEqual(rows[-1]['value']['message'], 'one original Connect failure')

class NetworkActivationDiagnosticTests(unittest.TestCase):

    def test_one_timeout_retains_original_partial_bytes_and_exception(self):
        e = Evidence()
        error = subprocess.TimeoutExpired(['original'], 20, output=b'partial stdout', stderr=b'actual partial stderr')
        with patch.object(network.subprocess, 'run', side_effect=error) as run:
            with self.assertRaises(subprocess.TimeoutExpired) as caught:
                network.activate_owned_observer('p12-observer-' + 'a' * 32, e)
        self.assertIs(caught.exception, error)
        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs['timeout'], 20)
        self.assertEqual(bytes.fromhex(e.rows[0]['stderr_hex']), b'actual partial stderr')
        self.assertEqual(len(e.rows), 1)

    def test_logger_failure_preserves_exact_timeout_and_one_attempt(self):

        class RaisingEvidence:

            def record(self, *args, **kwargs):
                raise OSError('evidence storage failed')
        error = subprocess.TimeoutExpired(['original'], 20, output=b'x' * 40000, stderr=b'y' * 40000)
        with patch.object(network.subprocess, 'run', side_effect=error) as run:
            with self.assertRaises(subprocess.TimeoutExpired) as caught:
                network.activate_owned_observer('p12-observer-' + 'a' * 32, RaisingEvidence())
        self.assertIs(caught.exception, error)
        run.assert_called_once()
        self.assertEqual(run.call_args.kwargs['timeout'], 20)
        e = Evidence()
        with patch.object(network.subprocess, 'run', side_effect=error):
            with self.assertRaises(subprocess.TimeoutExpired):
                network.activate_owned_observer('p12-observer-' + 'a' * 32, e)
        self.assertEqual(len(bytes.fromhex(e.rows[0]['stdout_hex'])), 32768)
        self.assertTrue(e.rows[0]['stdout_truncated'] and e.rows[0]['stderr_truncated'])

    def test_failed_return_retains_raw_and_wrong_owned_name_never_calls(self):
        e = Evidence()
        with patch.object(network.subprocess, 'run', return_value=SimpleNamespace(returncode=4, stdout=b'out', stderr=b'failure')) as run:
            with self.assertRaises(ValueError):
                network.activate_owned_observer('p12-observer-' + 'a' * 32, e)
            self.assertEqual(e.rows[0]['returncode'], 4)
            run.assert_called_once()
            with self.assertRaises(ValueError):
                network.activate_owned_observer('unowned', e)
            run.assert_called_once()

class NetworkFallbackObservationTests(unittest.TestCase):

    def test_exact_fresh_security_and_budget(self):
        raw = b'BSS 88:a2:9e:0a:9d:89(on wlan0)\n freq: 2422.0\n capability: ESS Privacy\n SSID: WsprryPico-0a9d89\n RSN:\n  * Group cipher: CCMP\n  * Pairwise ciphers: CCMP\n  * Authentication suites: PSK\n'
        calls = []

        def run(a, **kw):
            calls.append((a, kw))
            return SimpleNamespace(returncode=0, stdout=raw, stderr=b'')
        e = Evidence()
        network.fallback_beacon(e, 30, run, lambda: 0)
        compatible=raw+b' WPA:\n  * Group cipher: CCMP\n  * Pairwise ciphers: CCMP\n  * Authentication suites: PSK\n'
        network.fallback_beacon(Evidence(),30,lambda *a,**k:SimpleNamespace(returncode=0,stdout=compatible,stderr=b''),lambda:0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1]['timeout'], 5)
        for bad in [b'', raw.replace(b'Privacy', b'OPEN'), raw + raw, raw.replace(b'2422.0', b'2412.0'), raw.replace(b'88:a2:9e:0a:9d:89', b'88:a2:9e:0a:9d:88'), raw.replace(b'Pairwise ciphers: CCMP', b'Pairwise ciphers: CCMP TKIP'), raw.replace(b'Authentication suites: PSK', b'Authentication suites: SAE'), raw.replace(b'  * Pairwise ciphers: CCMP\n', b'')]:
            with self.assertRaises(ValueError):
                network.fallback_beacon(Evidence(), 30, lambda *a, **k: SimpleNamespace(returncode=0, stdout=bad, stderr=b''), lambda: 0)
        with self.assertRaises(ValueError):
            network.fallback_beacon(e, 20, run, lambda: 0)
        self.assertEqual(len(calls), 1)

    def test_actual_activation_callback_original_failure_and_late_beacon(self):
        calls = []
        original = subprocess.TimeoutExpired('one up', 20)

        def activate(name, e):
            calls.append(name)
            raise original

        def broken(*a):
            raise OSError('diagnostic storage failed')
        with self.assertRaises(subprocess.TimeoutExpired) as raised:
            network.observe_then_activate('owned', Evidence(), 30, beacon=lambda *a: None, activate=activate, diagnose=broken, clock=lambda: 0)
        self.assertIs(raised.exception, original)
        self.assertEqual(calls, ['owned'])
        for now in (10, 31):
            with self.assertRaises(ValueError):
                network.observe_then_activate('owned', Evidence(), 30, beacon=lambda *a: None, activate=activate, clock=lambda: now)
        self.assertEqual(calls, ['owned'])

    def test_passive_timeout_partial_bounds_and_no_late_calls(self):
        calls = []

        def run(a, **kw):
            calls.append(a)
            raise subprocess.TimeoutExpired(a, kw['timeout'], output=b'x' * 40000, stderr=b'y' * 20000)
        e = Evidence()
        network.failure_window(e, 10, run, lambda: 0)
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(('connection' not in a and 'up' not in a for a in calls)))
        self.assertTrue(all((v['stdout_truncated'] and v['stderr_truncated'] for v in e.rows)))
        network.failure_window(e, 0, run, lambda: 0)
        self.assertEqual(len(calls), 3)

class SessionStopOrderingTests(unittest.TestCase):

    def invoke(self, *, generation=2, boot='boot', fail=None):
        events = []

        class Client:

            def connect(self, address, device, allow_pairing):
                events.append(('connect', address, device, allow_pairing))
                if fail:
                    raise fail
                return {'generation': generation}

            def authorize(self, password):
                events.append('authorize')

            def enable_local_control(self):
                events.append('hello')
                return {'boot_id': boot}
        try:
            session.authenticate_then_stop(Client(), {'ble_address': 'bound-peer', 'profile_generation': 2}, 'private', 'boot', lambda: events.append('stop'), lambda: events.append('management'))
        except Exception as error:
            return (events, error)
        return (events, None)

    def test_authenticated_then_single_stop(self):
        events, error = self.invoke()
        self.assertIsNone(error)
        self.assertEqual(events, [('connect', 'bound-peer', session.DEVICE, False), 'authorize', 'hello', 'stop', 'management'])

    def test_connect_refusal_has_no_station_change_or_retry(self):
        failure = RuntimeError('refused')
        events, error = self.invoke(fail=failure)
        self.assertIs(error, failure)
        self.assertEqual(len(events), 1)

    def test_auth_and_late_deadline_errors_prevent_stop(self):
        for stage in ('authorize', 'hello', 'deadline'):
            events = []
            failure = RuntimeError(stage)

            class Client:

                def connect(self, *args, **kwargs):
                    events.append('connect')
                    return {'generation': 2}

                def authorize(self, *args):
                    events.append('authorize')
                    if stage == 'authorize':
                        raise failure

                def enable_local_control(self):
                    events.append('hello')
                    if stage == 'hello':
                        raise failure
                    return {'boot_id': 'boot'}

            def deadline():
                events.append('deadline')
                if stage == 'deadline':
                    raise failure
            with self.assertRaises(RuntimeError) as caught:
                session.authenticate_then_stop(Client(), {'ble_address': 'bound-peer', 'profile_generation': 2}, 'private', 'boot', lambda: events.append('stop'), lambda: events.append('management'), deadline)
            self.assertIs(caught.exception, failure)
            self.assertEqual(events.count('connect'), 1)
            self.assertNotIn('stop', events)
            self.assertNotIn('management', events)

    def test_stop_error_is_not_replayed(self):
        events = []

        class Client:

            def connect(self, *args, **kwargs):
                events.append('connect')
                return {'generation': 2}

            def authorize(self, *args):
                events.append('authorize')

            def enable_local_control(self):
                return {'boot_id': 'boot'}
        failure = RuntimeError('stop failed')

        def stop():
            events.append('stop')
            raise failure
        with self.assertRaises(RuntimeError) as caught:
            session.authenticate_then_stop(Client(), {'ble_address': 'bound-peer', 'profile_generation': 2}, 'private', 'boot', stop, lambda: events.append('management'))
        self.assertIs(caught.exception, failure)
        self.assertEqual(events, ['connect', 'authorize', 'stop'])

    def test_wrong_generation_has_no_station_change(self):
        events, error = self.invoke(generation=3)
        self.assertIsInstance(error, ValueError)
        self.assertEqual(len(events), 1)

    def test_wrong_boot_has_no_station_change(self):
        events, error = self.invoke(boot='foreign')
        self.assertIsInstance(error, ValueError)
        self.assertNotIn('stop', events)

import phase12_engineering_network as portable_network
import phase12_engineering_network_tests as network_model

class NetworkLiveFiveRegressions(unittest.TestCase):

    def test_supported_rsn_with_compatible_extra_wpa_ie(self):
        raw = b'BSS 88:a2:9e:0a:9d:89(on wlan0)\n\tfreq: 2422.0\n\tcapability: ESS Privacy\n\tSSID: WsprryPico-0a9d89\n\tRSN:\t * Version: 1\n\t\t * Group cipher: CCMP\n\t\t * Pairwise ciphers: CCMP\n\t\t * Authentication suites: PSK\n\tWPA:\t * Version: 1\n\t\t * Group cipher: CCMP\n\t\t * Pairwise ciphers: CCMP\n\t\t * Authentication suites: PSK\n'

        def invoke(value):
            network.fallback_beacon(Evidence(), 30, lambda *a, **k: SimpleNamespace(returncode=0, stdout=value, stderr=b''), lambda: 0)
        invoke(raw)
        invoke(raw.split(b'\tWPA:')[0])
        for bad in (raw.replace(b'Pairwise ciphers: CCMP', b'Pairwise ciphers: TKIP', 1), raw.replace(b'Authentication suites: PSK', b'Authentication suites: SAE', 1), raw.replace(b'RSN:', b'UNKNOWN:'), raw + raw):
            with self.assertRaises(ValueError):
                invoke(bad)

    def test_down_only_actual_owned_active_connection(self):
        name = 'p12-observer-' + 'a' * 32
        for active in (b'', b'--\n'):
            calls = []
            network.disconnect_owned_observer(name, lambda a: (calls.append(a), active)[1])
            self.assertEqual(len(calls), 1)
        calls = []

        def command(a):
            calls.append(a)
            return (name + '\n').encode()
        network.disconnect_owned_observer(name, command)
        self.assertEqual(calls[-1], ['sudo', '-n', 'nmcli', 'connection', 'down', name])
        calls = []
        with self.assertRaises(ValueError):
            network.disconnect_owned_observer(name, lambda a: (calls.append(a), b'management')[1])
        self.assertEqual(len(calls), 1)

    def test_actual_body_error_survives_two_cleanup_errors_and_ledger_failure(self):
        f = network_model.Tests()
        f.setup_case()
        primary = ValueError('beacon refused')
        actions = []

        def associate(args):
            if args.get('action') == 'disconnect_owned':
                raise OSError('down failed')
            raise primary

        def control(action):
            actions.append(action)
            if action == 'station_up':
                raise RuntimeError('restore failed')
            f.fixture(action)

        class BrokenEvidence:

            def record(self, kind, **data):
                if kind == 'network_cleanup_failed':
                    raise OSError('ledger failed')
        with patch.object(portable_network, 'resource_health'):
            with self.assertRaises(ValueError) as raised:
                portable_network.run(f.context, control, f.info, f.authority, associate, f.ap, BrokenEvidence(), clock=lambda: f.clock, sleeper=lambda x: setattr(f, 'clock', f.clock + x))
        self.assertIs(raised.exception, primary)
        self.assertEqual(actions, ['station_down', 'station_up'])
        self.assertEqual(len(primary.__notes__), 2)

class RecoveryLedgerCleanupTests(unittest.TestCase):
    def scenario(self, *, restore_error=False, primary_error=False, cleanup_error=False):
        import tempfile
        import phase12_recovery_orchestrator as recovery
        events=[]
        class Ledger:
            seq=0
            def __init__(self,*args):pass
            def record(self,event,*args,**kwargs):
                events.append(event)
                if event in ('final_restoration_pass','final_restoration_failed','host_cleanup_failed','campaign_failed'):
                    raise OSError('ledger unavailable')
        class Backend:
            def setup(self):return {}
            def snapshot(self,name):return dict(path=name,sha256='a'*64,inspection=dict(profile_healthy=True,access_state=2,operational_healthy=True,config={'enabled':primary_error},effective_station={'callsign':'SYNTHETIC'},profile_source=1))
            def restore(self,baseline,name):
                events.append(name)
                if restore_error and name=='final-restoration.bin':raise RuntimeError('original restore failure')
                return dict(readback=name)
            def stable_restore(self,*args):return dict(samples=5)
            def cleanup(self):
                events.append('actual_cleanup')
                if cleanup_error:raise RuntimeError('cleanup failure')
        with tempfile.TemporaryDirectory() as d,patch.object(recovery,'Ledger',Ledger),patch.object(recovery,'validate_plan',return_value=[]),patch.object(recovery,'safe_info',return_value={}):
            result=recovery.campaign({'schema':'synthetic-plan'},{'source_commit':'a'*40},d,Backend())
        return events,result
    def test_both_final_ledger_writes_fail_cleanup_still_called(self):
        events,result=self.scenario()
        self.assertIn('final_restoration_pass',events);self.assertIn('final_restoration_failed',events)
        self.assertEqual(events.count('actual_cleanup'),1);self.assertEqual(result['status'],'STOPPED')
        self.assertEqual(result['recording_errors'][0]['event'],'final_restoration_failed')
    def test_original_restore_failure_retained_despite_failed_record(self):
        events,result=self.scenario(restore_error=True)
        self.assertEqual(events.count('actual_cleanup'),1)
        self.assertEqual(result['restoration']['message'],'original restore failure')
        self.assertEqual(result['restoration']['error'],'RuntimeError')
    def test_original_primary_error_survives_all_failed_cleanup_records(self):
        events,result=self.scenario(primary_error=True,cleanup_error=True)
        self.assertEqual(events.count('actual_cleanup'),1);self.assertEqual(result['error']['type'],'ValueError')
        self.assertEqual(result['error']['message'],'baseline scheduling enabled')
        self.assertIn('host_cleanup_failed',[v['event'] for v in result['recording_errors']])

if __name__=='__main__':unittest.main()
