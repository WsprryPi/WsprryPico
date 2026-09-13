"""B deployment gates reject cross-device and premature access before USB opens."""
import copy
import errno
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase11_5_r3_v2_parallel_b_deploy as deploy


def packet():
    return dict(schema=deploy.SCHEMA,r3_scope=deploy.SCHEMA,serial=deploy.B_SERIAL,device_id=deploy.B_DEVICE,
        source_revision=deploy.SOURCE,authorization_sha256=deploy.AUTHORIZATION,
        runtime_seconds=300,cleanup_seconds=150,flashes=1,bootsel_commands=1,
        rf_jobs=0,arm_commands=0,loads=0,configuration_writes=0,wifi_cycles=0,
        prior_revision='dbf1d86f0885-dirty',prior_boot='feffcd075ab6cb0b74e7e0c2fde6c87f',
        image_sha256=deploy.IMAGE,inventory_session='b'*32,image_file='candidate.uf2',
        root='/home/pi/phase11-5-r3-v2-parallel-b-deploy-test',predecessors=[
            dict(name=name,audit_file='/tmp/'+name,audit_sha256='a'*64,
                 unit=name+'.service',final_b_file='/tmp/'+name+'-b') for name in ['H2b','E1']])


class BDeploymentTests(unittest.TestCase):
    def test_scope_cannot_gain_rf_or_a_authority(self):
        deploy.validate(packet())
        for key,value in [('serial','0BF4B4AEC9FFB344'),('device_id','fd6127d11d6aca42a9905fa3fb1bf1d5'),
            ('arm_commands',1),('loads',1),('rf_jobs',1),('flashes',2),('wifi_cycles',1),
            ('configuration_writes',1),('runtime_seconds',301),('rf_jobs',False),
            ('authorization_sha256','0'*64),('predecessors',[])]:
            p=packet();p[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): deploy.validate(p)

    def test_active_predecessor_rejected_before_inventory(self):
        with patch.object(deploy,'digest',return_value='a'*64), \
             patch.object(deploy.subprocess,'check_output',return_value='MainPID=1\nActiveState=active\n'), \
             patch.object(deploy,'finished') as inventory:
            with self.assertRaisesRegex(ValueError,'still active'): deploy.predecessors_complete(packet())
            inventory.assert_not_called()

    def test_missing_audit_rejected_before_system_or_inventory(self):
        with patch.object(deploy,'digest',side_effect=FileNotFoundError), \
             patch.object(deploy.subprocess,'check_output') as system, \
             patch.object(deploy,'finished') as inventory:
            with self.assertRaises(FileNotFoundError):deploy.predecessors_complete(packet())
            system.assert_not_called();inventory.assert_not_called()

    def test_bootsel_only_b_and_requires_positive_ack(self):
        paths=[];events=[]
        @contextmanager
        def port(path):
            paths.append(str(path));yield 7
        with patch.object(deploy,'exclusive_port',side_effect=port), \
             patch.object(deploy,'exchange',return_value=dict(ok=True,rebooting=True)) as exchange:
            deploy.request_b_bootsel(lambda *v:events.append(v))
            self.assertEqual(paths,['/dev/serial/by-id/usb-WsprryPi_WsprryPico_CDDBF8767C506C07-if00'])
            self.assertEqual(exchange.call_args.args[1],b'BOOTSEL\n')
        with patch.object(deploy,'exclusive_port',side_effect=port), \
             patch.object(deploy,'exchange',side_effect=OSError(errno.ENODEV,'gone')):
            with self.assertRaises(OSError): deploy.request_b_bootsel(lambda *v:None)

    def test_positive_ack_disconnect_is_not_retried(self):
        @contextmanager
        def port(path):
            yield 7
            raise OSError(errno.ENODEV,'gone')
        with patch.object(deploy,'exclusive_port',side_effect=port), \
             patch.object(deploy,'exchange',return_value=dict(ok=True,rebooting=True)) as exchange:
            deploy.request_b_bootsel(lambda *v:None)
            self.assertEqual(exchange.call_count,1)

if __name__=='__main__':unittest.main()
