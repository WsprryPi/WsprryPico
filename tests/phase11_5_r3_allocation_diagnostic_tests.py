"""D0 source-bound scope, opt-in and inactive authority checks."""
import copy
import contextlib
import errno
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase11_5_r3_allocation_diagnostic as m


def packet():
    return dict(schema=m.SCHEMA,r3_scope=m.SCHEMA,host_boot_id=m.HOST_BOOT,serial=m.SERIAL,device_id=m.DEVICE,
        prior_boot=m.PRIOR_BOOT,runtime_seconds=600,flashes=1,bootsel_commands=1,maximum_payload_requests=1,
        maximum_payload_bytes=65536,rf_jobs=0,wifi_cycles=0,configuration_writes=0,heap_probes=0,
        image_file='diagnostic.uf2',image_sha256='a'*64,source_revision='b'*40,embedded_revision='b'*12,
        a_session='1'*32,b_session='2'*32,peer_session='3'*32,request_id='4'*32)


class DiagnosticTests(unittest.TestCase):
    def test_no_side_effects_without_opt_in(self):
        with patch.object(sys,'argv',['d0','--root','/absent','--packet-sha256','absent']), \
             patch.object(Path,'read_text',side_effect=AssertionError('file access')), \
             patch.object(m.subprocess,'run',side_effect=AssertionError('process')):
            m.main()

    def test_scope_cannot_expand_or_change_image_identity(self):
        self.assertEqual(m.validate(packet()),packet())
        for key,value in [('rf_jobs',1),('wifi_cycles',1),('configuration_writes',1),('heap_probes',1),
                          ('flashes',2),('maximum_payload_requests',2),('runtime_seconds',601),
                          ('maximum_payload_bytes',65537),('flashes',True),('image_file','../image.uf2'),
                          ('source_revision','z'*40),('embedded_revision','f'*12),('peer_session','1'*32)]:
            with self.subTest(key=key):
                p=packet();p[key]=value
                with self.assertRaises(ValueError):m.validate(p)

    def test_recovery_does_not_substitute_for_inactive_unowned(self):
        value=dict(wtp={'STATUS':dict(state='empty',output_active=False,owner_id=None,job_id=None)},
                   info={'status':dict(state='empty',output_active=False,enabled=False,storage_healthy=True,last_error=None)})
        m.inactive(value)
        for key,changed in [('state','running'),('output_active',True),('owner_id','1'*32),('job_id','2'*32)]:
            p=copy.deepcopy(value);p['wtp']['STATUS'][key]=changed
            with self.assertRaises(ValueError):m.inactive(p)

    def test_only_acknowledged_bootsel_disconnect_cleanup_is_expected(self):
        @contextlib.contextmanager
        def disconnected(path):
            yield 7
            raise OSError(errno.EIO,'device disappeared')
        with patch.object(m,'exclusive_port',disconnected),patch.object(m,'exchange',return_value={'ok':True,'rebooting':True}):
            events=[];m.request_bootsel(lambda *event:events.append(event))
            self.assertEqual([event[0] for event in events],['bootsel_acknowledged','bootsel_disconnect_cleanup'])
        with patch.object(m,'exclusive_port',disconnected),patch.object(m,'exchange',side_effect=OSError(errno.EIO,'no ACK')):
            with self.assertRaises(OSError):m.request_bootsel(lambda *event:None)
        @contextlib.contextmanager
        def bad_cleanup(path):
            yield 7
            raise OSError(errno.EPERM,'unrelated failure')
        with patch.object(m,'exclusive_port',bad_cleanup),patch.object(m,'exchange',return_value={'ok':True,'rebooting':True}):
            with self.assertRaises(OSError):m.request_bootsel(lambda *event:None)

    def test_saved_configuration_distinguishes_runtime_mac_from_saved_identity(self):
        value={'info':{'status':dict(configured=True,enabled=False,station={},schedules=[],watermark_utc_ns='0'),
                       'network':dict(station_mac='',configured_hostname='pico.local',control_configured=True)}}
        resumed=copy.deepcopy(value);resumed['info']['network']['station_mac']='88:a2:9e:0a:60:df'
        self.assertEqual(m.saved_configuration(value),m.saved_configuration(resumed))
        resumed['info']['network']['configured_hostname']='changed.local'
        self.assertNotEqual(m.saved_configuration(value),m.saved_configuration(resumed))


if __name__=='__main__':unittest.main()
