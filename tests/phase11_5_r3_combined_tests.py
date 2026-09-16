import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_completion_combined import *
from phase11_5_r3_v2_rf import validate,SCHEMA
from phase11_5_r3_v2_admission import maximum_job


def packet(mode='supported'):
    return dict(schema=SCHEMA,r3_scope=SCHEMA,standing_authority='R3-COMPLETE-20260913-v2',
        serial='0BF4B4AEC9FFB344',device_id=DEVICE,source_revision=SOURCE,image_sha256=IMAGE,boot_id=BOOT,
        assertion_ids=['2.2a' if mode=='supported' else '2.2b'],initial_a_state='empty',initial_a_job_id=None,closure_policy=POLICY,runtime_seconds=300,restoration_seconds=150,maximum_renewals=8,
        configuration_writes=0,wifi_cycles=0,heap_probes=0,flashes=0,
        jobs=[maximum_job('a'*32,duration=128000000000)],owner_id='b'*32,peer_session='c'*32,
        inventory_session='d'*32,b_session='e'*32,b_boot_id='f'*32,
        observer_policy='single-flight-info-v1',maximum_initial_terminal_records=0,initial_terminal_records=[],
        b_role='unchanged-comparator',shared_rf_reservation='durable-both-picos-v1',not_before_host_monotonic_ns=1,
        contention=dict(policy='native-wtp-and-https-status-20s-v1',maximum_https_requests=2),
        private_reference_root=PRIVATE_ROOT,private_reference_sha256={n:'f'*64 for n in ['production.ini',*(f'credentials/{role}/{name}' for role in ('controller','browser') for name in ('client-ca.crt','client.crt','client.key'))]},
        combined=dict(mode=mode,seed='1'*32,wtp_request_id='2'*32,cases=cases('1'*32,mode),minimum_resident_delta_bytes=32768,wtp_payload_bytes=32768))


class CombinedTests(unittest.TestCase):
    def test_two_distinct_frozen_profiles(self):
        for mode in ('supported','overload'):
            p=packet(mode);self.assertEqual(validate(p),p)
            from audit_phase11_5_idle import frames
            wire=combined_frame(p['peer_session'],p['combined']['wtp_request_id']);decoded,left=frames(wire)
            self.assertEqual(len(wire),32784);self.assertFalse(left);self.assertEqual(decoded[0]['op'],'STATUS')
            c=p['combined']['cases'][0];wire=bytes.fromhex(c['wire_hex']);header,body=wire.split(b'\r\n\r\n')
            self.assertEqual(len(body),c['offered_body_bytes'])
            self.assertEqual(c['expected_status'],200 if mode=='supported' else 503)
            self.assertNotEqual(c['wire_hex'],p['combined']['cases'][1]['wire_hex'])
    def test_inactive_predecessor_only_before_load(self):
        from phase11_5_r3_v2_rf import observed_status,initial_terminal
        p=packet();p.update(initial_a_state='complete',initial_a_job_id='7'*32,initial_terminal_records=[dict(job_id='7'*32,state='complete',output_active=False)],maximum_initial_terminal_records=1)
        validate(p);self.assertTrue(initial_terminal(p))
        value=dict(boot_id=BOOT,job_id='7'*32,owner_id=None,state='complete',output_active=False)
        observed_status(value,p,initial=True)
        for change,initial in [({},False),({'owner_id':'8'*32},True),({'output_active':True},True),({'job_id':'8'*32},True)]:
            with self.assertRaises(ValueError):observed_status(dict(value,**change),p,initial=initial)
        p['initial_a_job_id']='8'*32
        with self.assertRaises(ValueError):validate(p)

    def test_wrong_source_scope_counts_or_limits_rejected(self):
        for change in [dict(runtime_seconds=301),dict(flashes=1),dict(configuration_writes=1),
                       dict(assertion_ids=['2.1a']),dict(boot_id='0'*32),dict(closure_policy='unknown'),dict(maximum_initial_terminal_records=1),
                       dict(contention=dict(policy='native-wtp-and-https-status-20s-v1',maximum_https_requests=3))]:
            with self.subTest(change=change),self.assertRaises(ValueError):validate(dict(packet(),**change))
        for mode in ('supported','overload'):
            for key,value in [('minimum_resident_delta_bytes',32767),('wtp_payload_bytes',32767),('cases',cases('3'*32,mode)),('mode','unknown')]:
                p=packet(mode);p['combined'][key]=value
                with self.subTest(mode=mode,key=key),self.assertRaises(ValueError):validate(p)
    def test_independent_residence_gate(self):
        p=packet();status=dict(boot_id=BOOT,job_id=p['jobs'][0]['job_id'],owner_id=p['owner_id'],state='running',output_active=True)
        status.pop('job_id');status.pop('owner_id')
        info_running(status,p)  # Actual INFO has neither WTP identity field.
        with self.assertRaises(ValueError):running(dict(status,job_id=p['jobs'][0]['job_id'],owner_id='foreign'),p)
        warm=dict(packet_sha256='x',monotonic_ns=1,value=dict(value=dict(heap_allocated_bytes=100000,wtp_input_reserved_bytes=0,status=status)))
        sample=copy.deepcopy(warm);sample['monotonic_ns']=3;sample['value']['value']['wtp_input_reserved_bytes']+=32768
        resident(sample,warm,2,p)
        for change in ('low','stale','boot','state','inactive','packet'):
            bad=copy.deepcopy(sample)
            if change=='low':bad['value']['value']['wtp_input_reserved_bytes']-=1
            elif change=='stale':bad['monotonic_ns']=2
            elif change=='packet':bad['packet_sha256']='other'
            else:bad['value']['value']['status'][{'boot':'boot_id','state':'state','inactive':'output_active'}[change]]=False if change=='inactive' else 'other'
            with self.subTest(change=change),self.assertRaises(ValueError):resident(bad,warm,2,p)

    def test_overlap_audit_rejects_adjacent_or_altered_evidence(self):
        from audit_phase11_5_completion_combined import overlap
        for mode in ('supported','overload'):
            p=packet(mode); row=lambda kind,value,stamp:dict(kind=kind,value=value,monotonic_ns=stamp)
            status=dict(boot_id=BOOT,job_id=p['jobs'][0]['job_id'],owner_id=p['owner_id'],state='running',output_active=True)
            status.pop('job_id');status.pop('owner_id')
            warm=dict(packet_sha256='x',monotonic_ns=10,value=dict(value=dict(status=status,heap_allocated_bytes=100000,wtp_input_reserved_bytes=0)))
            sample=copy.deepcopy(warm);sample['monotonic_ns']=30;sample['value']['value'].update(heap_allocated_bytes=132488,wtp_input_reserved_bytes=32784)
            rf=[row('start',dict(packet_sha256='x'),1),row('info',warm['value'],10),row('capacity_tx',{},20),
                row('capacity_write',dict(bytes=32768,total_written=32768),28),row('info',sample['value'],30),
                row('combined_resident',dict(packet_sha256='x',info=sample,baseline=warm,began_ns=19),32),
                row('capacity_write',dict(bytes=16,total_written=32784),45),row('capacity_message',{},50)]
            load=[row('combined_http_ready',dict(packet_sha256='x',info=warm,peer_sha256=PEER,authenticated_ns=5),15)]
            for i,case in enumerate(p['combined']['cases']):
                t=35+i*25
                body=dict(error=dict(code='resource_exhausted')) if i==0 and mode=='overload' else dict(ok=True,result=dict(device_id=DEVICE,boot_id=BOOT))
                load.extend([row('http_tx',case,t),row('http_write_complete',dict(label=case['label'],bytes=len(bytes.fromhex(case['wire_hex']))),t+1),
                    row('http_response',dict(label=case['label'],status=case['expected_status'],peer_sha256=PEER,
                        body_hex=json.dumps(body).encode().hex(),began_monotonic_ns=t-1),t+5)])
            self.assertTrue(overlap(p,rf,load)['authenticated_recovery'])
            for change in ('early_http','early_last_byte','short_write','wrong_status','wrong_peer','fake_info','wrong_packet'):
                a,b=json.loads(json.dumps(rf)),json.loads(json.dumps(load))
                if change=='early_http':b[1]['monotonic_ns']=29
                elif change=='early_last_byte':a[-2]['monotonic_ns']=39
                elif change=='short_write':a[-2]['value']['total_written']-=1
                elif change=='wrong_status':b[3]['value']['status']=400
                elif change=='wrong_peer':b[3]['value']['peer_sha256']='other'
                elif change=='fake_info':a[-3]['value']['info']['value']['value']['wtp_input_reserved_bytes']+=8
                else:b[0]['value']['packet_sha256']='other'
                with self.subTest(mode=mode,change=change),self.assertRaises(ValueError):overlap(p,a,b)

if __name__=='__main__':unittest.main()
