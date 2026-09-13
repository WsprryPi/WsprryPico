"""Frozen B stimuli cannot smuggle an ARM, widen budgets, or shorten max bytes."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase11_5_r3_v2_parallel_b_plan as plan
from audit_phase11_5_r3_v2_admission import decode_requests
from phase11_5_r3_v2_parallel_b_functional import usb_exchange


def packet():
    return dict(schema=plan.SCHEMA,r3_scope=plan.SCHEMA,serial=plan.B_SERIAL,device_id=plan.B_DEVICE,
        source_revision=plan.SOURCE,image_sha256=plan.IMAGE,authorization_sha256=plan.AUTHORIZATION,seed='a'*32,
        boot_id='b'*32,inventory_session='c'*32,stimuli=plan.stimuli('a'*32),
        runtime_seconds=600,cleanup_seconds=150,rf_jobs=0,arm_commands=0,accepted_loads=1,
        requests=34,tls_connections=6,configuration_writes=0,wifi_cycles=0,flashes=0,
        address='192.168.1.53',tls_name=plan.NAME,tls_peer_sha256=plan.PEER_SHA)


class BPlanTests(unittest.TestCase):
    def test_actual_crc_wire_bounds_and_zero_arm(self):
        p=packet();plan.validate(p);cases=p['stimuli']['usb_cases']
        decoded=[decode_requests(bytes.fromhex(c['wire_hex'])) for c in cases]
        self.assertEqual([s for s,_ in decoded[1]],[65536])
        self.assertEqual(decoded[2][0][0],65537)
        self.assertEqual(len(decoded[2]),2)
        self.assertFalse(any(q['op']=='ARM' for group in decoded for _,q in group))
        for case,group in zip(cases,decoded):self.assertEqual(case['request'],group[-1][1])
        maximum=cases[8]['request']['body']
        self.assertEqual(len(maximum['events']),512)
        self.assertEqual(sum(int(e['duration_ns']) for e in maximum['events']),3600_000_000_000)
        http=p['stimuli']['http_cases']
        self.assertEqual(http[0]['wire_hex'],http[1]['wire_hex'])
        self.assertEqual(len(bytes.fromhex(http[0]['wire_hex']).split(b'\r\n\r\n',1)[1]),32768)
        self.assertEqual(http[3]['declared_body_bytes'],32769)
        self.assertEqual(http[3]['offered_body_bytes'],0)
        self.assertEqual(bytes.fromhex(http[3]['wire_hex']).split(b'\r\n\r\n',1)[1],b'')

    def test_mutation_rejected_before_execution(self):
        for key,value in [('serial','0BF4B4AEC9FFB344'),('arm_commands',1),('requests',256),
                          ('accepted_loads',16),('address','10.77.15.10')]:
            p=packet();p[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):plan.validate(p)
        p=packet();p['stimuli']['usb_cases'][8]['request']['op']='ARM'
        with self.assertRaises(ValueError):plan.validate(p)
        p=packet();p['stimuli']['usb_cases'][1]['wire_hex']=p['stimuli']['usb_cases'][0]['wire_hex']
        with self.assertRaises(ValueError):plan.validate(p)

    def test_direct_arm_rejected_before_emit_or_write(self):
        class Peer:
            emit=lambda *a: (_ for _ in ()).throw(AssertionError('Must not emit'))
        with self.assertRaisesRegex(ValueError,'idle operations'):
            usb_exchange(Peer(),dict(wire_hex='00',request=dict(op='ARM')))

if __name__=='__main__':unittest.main()
