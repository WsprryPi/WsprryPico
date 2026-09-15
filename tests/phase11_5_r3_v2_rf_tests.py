import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_rf import validate,SCHEMA,SERIAL,DEVICE

class FiniteRfPacketTests(unittest.TestCase):
    def packet(self):
        p=dict(schema=SCHEMA,r3_scope=SCHEMA,standing_authority='R3-COMPLETE-20260913-v2',serial=SERIAL,device_id=DEVICE,
            source_revision='7d183978d08d77d5de668911be041bb188c851f5',
            image_sha256='38daadfdb38e7ce9f35c3c327cd3b160d12e9040d50a31c97db0a3f2ce6eedd1',
            runtime_seconds=100,restoration_seconds=150,maximum_renewals=8,configuration_writes=0,wifi_cycles=0,
            heap_probes=0,flashes=0,jobs=[dict(job_id='a'*32,profile='rf-events/1',mode='tone',
            total_duration_ns='10000000000',allow_frequency_adjustment=True,
            events=[dict(offset_ns='0',duration_ns='10000000000',rf_on=True,frequency_nhz='135500000000000')])])
        for i,k in enumerate(['owner_id','peer_session','inventory_session','b_session','boot_id','b_boot_id'],1):p[k]=f'{i:032x}'
        return p
    def test_capacity_exchange_yields_between_five_second_observer_intervals(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from phase11_5_r3_v2_rf import capacity_step, guarded_action
        p=self.packet();p['wtp_capacity']=dict(maximum_request_id='a'*32,oversized_request_id='b'*32,recovery_request_id='c'*32)
        job=p['jobs'][0];peer=SimpleNamespace(session=p['peer_session']);calls=[];now=[0.0]
        def exchange(peer,raw,q,emit,invalid_frames=0):
            calls.append((q['op'],len(raw),invalid_frames));now[0]+=(3.15 if q['op']=='STATUS' else 3.51)
            return dict(boot_id=p['boot_id'],job_id=job['job_id'],owner_id=p['owner_id'],state='running',output_active=True) if q['op']=='STATUS' else q['body']
        with patch('phase11_5_r3_capacity_probe.exchange_capacity',side_effect=exchange):
            capacity_step(peer,p,job,0,lambda *_:None)
            self.assertEqual(calls,[('STATUS',65552,0)])
            self.assertLess(now[0],5)  # STATUS can run at its original next start.
            now[0]=5
            capacity_step(peer,p,job,1,lambda *_:None)
            self.assertEqual(len(calls),2);self.assertEqual(calls[-1][0::2],('PING',1))
            self.assertLess(now[0],10)
        faults=[]
        with patch('phase11_5_r3_capacity_probe.exchange_capacity',side_effect=ValueError('partial write')) as failed:
            action=lambda _:capacity_step(peer,p,job,0,lambda *_:None)
            guarded_action(action,None,faults,lambda *_:None)
            guarded_action(action,None,faults,lambda *_:None)
            self.assertEqual(failed.call_count,1);self.assertTrue(faults)

    def test_fresh_read_workspace_capacity_packet(self):
        from phase11_5_r3_v2_rf import READ_POLICY, READ_SOURCE, READ_IMAGE, READ_BOOT, SERIAL_CAPACITY
        from phase11_5_r3_v2_admission import maximum_job
        from phase11_5_r3_capacity_plan import http_capacity_cases
        p=self.packet()
        p.update(source_revision=READ_SOURCE,image_sha256=READ_IMAGE,boot_id=READ_BOOT,
            closure_policy=READ_POLICY,capacity_schedule_policy=SERIAL_CAPACITY,
            observer_policy='single-flight-info-v1',runtime_seconds=300,initial_a_state='empty',
            initial_a_job_id=None,maximum_initial_terminal_records=0,b_role='unchanged-comparator',
            shared_rf_reservation='durable-both-picos-v1',not_before_host_monotonic_ns=1,
            jobs=[maximum_job('a'*32,duration=128000000000)],
            wtp_capacity=dict(maximum_request_id='a'*32,oversized_request_id='b'*32,recovery_request_id='c'*32),
            http_capacity=dict(seed='d'*32,cases=http_capacity_cases('d'*32)),
            contention=dict(policy='native-wtp-and-https-status-20s-v1',maximum_https_requests=16))
        self.assertEqual(validate(p),p)
        for k,v in [('closure_policy',None),('boot_id','0'*32),('image_sha256','0'*64),
                    ('initial_a_state','complete'),('maximum_initial_terminal_records',1),('flashes',1),
                    ('runtime_seconds',301),('configuration_writes',1)]:
            with self.subTest(key=k),self.assertRaises(ValueError):validate(dict(p,**{k:v}))
    def test_http_pages_capacity_retains_exact_idle_seed(self):
        from phase11_5_r3_v2_rf import HTTP_POLICY, HTTP_SOURCE, HTTP_IMAGE, HTTP_BOOT, SERIAL_CAPACITY
        from phase11_5_r3_v2_admission import maximum_job
        from phase11_5_r3_capacity_plan import http_capacity_cases
        p=self.packet()
        p.update(source_revision=HTTP_SOURCE,image_sha256=HTTP_IMAGE,boot_id=HTTP_BOOT,
            closure_policy=HTTP_POLICY,capacity_schedule_policy=SERIAL_CAPACITY,
            observer_policy='single-flight-info-v1',runtime_seconds=300,initial_a_state='empty',
            initial_a_job_id=None,initial_terminal_jobs=['1'*32,'2'*32,'3'*32],maximum_initial_terminal_records=3,b_role='unchanged-comparator',
            shared_rf_reservation='durable-both-picos-v1',not_before_host_monotonic_ns=1,
            jobs=[maximum_job('a'*32,duration=128000000000)],
            wtp_capacity=dict(maximum_request_id='a'*32,oversized_request_id='b'*32,recovery_request_id='c'*32),
            http_capacity=dict(seed='d'*32,cases=http_capacity_cases('d'*32)),
            contention=dict(policy='native-wtp-and-https-status-20s-v1',maximum_https_requests=16))
        self.assertEqual(validate(p),p)
        for k,v in [('closure_policy',None),('boot_id','0'*32),('image_sha256','0'*64),
                    ('initial_a_state','complete'),('maximum_initial_terminal_records',1),('flashes',1),
                    ('runtime_seconds',301),('configuration_writes',1)]:
            with self.subTest(key=k),self.assertRaises(ValueError):validate(dict(p,**{k:v}))

        from phase11_5_r3_v2_rf import SHARING_POLICY, SHARING_SOURCE, SHARING_IMAGE, SHARING_BOOT
        sharing=dict(p,closure_policy=SHARING_POLICY,source_revision=SHARING_SOURCE,
                     image_sha256=SHARING_IMAGE,boot_id=SHARING_BOOT)
        self.assertEqual(validate(sharing),sharing)
        for k,v in [('closure_policy',HTTP_POLICY),('boot_id',HTTP_BOOT),('image_sha256',HTTP_IMAGE),
                    ('source_revision',HTTP_SOURCE),('maximum_initial_terminal_records',0)]:
            with self.subTest(sharing_key=k),self.assertRaises(ValueError):validate(dict(sharing,**{k:v}))

        from phase11_5_r3_v2_rf import MEMORY_POLICY, MEMORY_SOURCE, MEMORY_IMAGE, MEMORY_BOOT
        memory=dict(p,closure_policy=MEMORY_POLICY,source_revision=MEMORY_SOURCE,
                    image_sha256=MEMORY_IMAGE,boot_id=MEMORY_BOOT)
        self.assertEqual(validate(memory),memory)
        for bad in [dict(closure_policy=SHARING_POLICY),dict(boot_id=SHARING_BOOT),
                    dict(image_sha256=SHARING_IMAGE),dict(source_revision=SHARING_SOURCE),
                    dict(initial_terminal_jobs=[],maximum_initial_terminal_records=0),
                    dict(runtime_seconds=301),dict(flashes=1)]:
            with self.subTest(memory_change=bad),self.assertRaises(ValueError):validate(dict(memory,**bad))

    def test_independent_b_requires_new_image_and_explicit_parallel_scope(self):
        from phase11_5_r3_v2_rf import comparator_required,REPAIRED_SOURCE,REPAIRED_IMAGE,B_PARALLEL_AUTHORIZATION
        p=self.packet();self.assertTrue(comparator_required(p))
        p['b_role']='independent-zero-rf'
        with self.assertRaises(ValueError):validate(p)
        p.update(source_revision=REPAIRED_SOURCE,image_sha256=REPAIRED_IMAGE)
        with self.assertRaises(ValueError):validate(p)
        p['b_parallel_authorization_sha256']=B_PARALLEL_AUTHORIZATION
        p.pop('b_session');p.pop('b_boot_id')
        self.assertEqual(validate(p),p);self.assertFalse(comparator_required(p))
        p['image_sha256']='0'*64
        with self.assertRaises(ValueError):validate(p)

    def test_capacity_stimuli_reject_wrong_crc_size_and_recovery(self):
        import json
        from phase11_5_r3_capacity_plan import wtp_capacity_frame
        from validate_wtp_contract import frame
        from audit_phase11_5_r3_v2_rf import capacity_request
        p=self.packet();cap=dict(maximum_request_id='a'*32,oversized_request_id='b'*32,recovery_request_id='c'*32)
        p['wtp_capacity']=cap;validate(p)
        raw=wtp_capacity_frame(p['peer_session'],cap['maximum_request_id'])
        value=dict(hex=raw.hex(),request=json.loads(raw[16:]),expected_invalid_frames=0)
        self.assertEqual(capacity_request(p,value,0),65552)
        for damaged in [raw[:-1],raw[:12]+bytes([raw[12]^1])+raw[13:],wtp_capacity_frame(p['peer_session'],'d'*32)]:
            with self.assertRaises(ValueError):capacity_request(p,dict(value,hex=damaged.hex()),0)
        q=dict(type='request',protocol='WTP/1',session_id=p['peer_session'],request_id=cap['recovery_request_id'],
            op='PING',body={'token':'after-capacity'})
        raw=wtp_capacity_frame(p['peer_session'],cap['oversized_request_id'],True)+frame(json.dumps(q,separators=(',',':')).encode())
        value=dict(hex=raw.hex(),request=q,expected_invalid_frames=1)
        self.assertEqual(capacity_request(p,value,1),len(raw))
        with self.assertRaises(ValueError):capacity_request(p,value,0)
        with self.assertRaises(ValueError):capacity_request(p,dict(value,expected_invalid_frames=0),1)

    def test_http_boundary_cases_are_supported_operations_at_declared_layer(self):
        import json
        from phase11_5_r3_capacity_plan import http_capacity_cases
        cases=http_capacity_cases('1'*32)
        self.assertEqual([c['expected_status'] for c in cases],[200,400,200])
        for case in cases:
            headers,body=bytes.fromhex(case['wire_hex']).split(b'\r\n\r\n',1)
            self.assertIn(('Content-Length: '+str(case['declared_body_bytes'])).encode(),headers)
            self.assertEqual(len(body),case['offered_body_bytes'])
            if body:self.assertEqual(json.loads(body)['operation'],'HELLO')
        self.assertEqual(len(bytes.fromhex(cases[0]['wire_hex']).split(b'\r\n\r\n',1)[1]),32768)
        self.assertEqual((cases[1]['declared_body_bytes'],cases[1]['offered_body_bytes']),(32769,0))
        from phase11_5_r3_v2_parallel_b_functional import http_exchange
        with self.assertRaises(ValueError):http_exchange(Path('/nonexistent'),{},cases[0],lambda *_:None,target=('wrong','0'*64,'0'*32))

    def test_bounds(self):
        p=self.packet();self.assertEqual(validate(p),p)
        for key,value in [('runtime_seconds',40),('runtime_seconds',28801),('flashes',1),
                          ('configuration_writes',1),('wifi_cycles',1),('maximum_renewals',513)]:
            q=copy.deepcopy(p);q[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(q)
        for key,value in [('frequency_nhz','140000000000000'),('offset_ns','1'),('duration_ns','3600000000001'),('rf_on',1)]:
            q=copy.deepcopy(p);q['jobs'][0]['events'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(q)
        q=copy.deepcopy(p);q['jobs']*=17
        with self.assertRaises(ValueError):validate(q)

    def test_diagnostic_identity_cannot_admit_a_broader_campaign(self):
        from phase11_5_r3_v2_rf import DIAGNOSTIC_SOURCE,DIAGNOSTIC_IMAGE
        p=self.packet();p.update(source_revision=DIAGNOSTIC_SOURCE,image_sha256=DIAGNOSTIC_IMAGE,
            runtime_seconds=180,maximum_renewals=5,
            wtp_capacity=dict(maximum_request_id='a'*32,oversized_request_id='b'*32,recovery_request_id='c'*32))
        p['jobs'][0]['total_duration_ns']='90000000000'
        p['jobs'][0]['events'][0]['duration_ns']='90000000000'
        self.assertEqual(validate(p),p)
        for key,value in [('runtime_seconds',181),('maximum_renewals',6),
                          ('allocator_failure_baseline',1),('contention',{}),('http_capacity',{})]:
            q=copy.deepcopy(p);q[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(q)
        q=copy.deepcopy(p);q['image_sha256']='0'*64
        with self.assertRaises(ValueError):validate(q)


class RawRfAuditTests(unittest.TestCase):
    def test_intact_and_mutations(self):
        import json,os,shutil,tempfile
        from audit_phase11_5_r3_v2_rf import audit
        source=os.environ.get('PHASE115_R3_V2_CORE_EVIDENCE') or os.environ.get('PHASE115_R3_V2_S0_EVIDENCE')
        packet_digest=os.environ.get('PHASE115_R3_V2_CORE_PACKET')
        raw_audit=audit
        def audit(root):return raw_audit(root,**({'packet_digest':packet_digest} if packet_digest else {}))
        if not source:self.skipTest('Private S0 evidence required')
        source=Path(source);original=audit(source)
        def edit(root,fn):
            p=root/'rf.jsonl';a=[json.loads(s) for s in p.read_text().splitlines()];fn(a)
            p.write_text(''.join(json.dumps(r)+'\n' for r in a))
        def first(a,k):return next(r for r in a if r['kind']==k)
        mutations=[
            lambda r:edit(r,lambda a:a.pop(30)),
            lambda r:edit(r,lambda a:first(a,'info')['value']['value'].update(allocator_failures='1')),
            lambda r:edit(r,lambda a:first(a,'health')['value']['value'].update(throttled='throttled=0x1')),
            lambda r:edit(r,lambda a:first(a,'status')['value']['value'].update(output_active=True)),
            lambda r:edit(r,lambda a:first(a,'info_finish')['value'].update(samples=1)),
            lambda r:edit(r,lambda a:first(a,'wtp_rx')['value'].update(hex='00')),
            lambda r:edit(r,lambda a:first(a,'status')['value'].update(began_monotonic_ns=0)),
            lambda r:(r/('final-b.stdout' if (r/'final-b.stdout').exists() else 'final-a.stdout')).write_text(''),
            lambda r:(r/'packet.json').write_text('{}\n'),
            lambda r:edit(r,lambda a:a[-1]['value'].update(rf_duration_ns_charged=10000000000)),
        ]
        for i,mutate in enumerate(mutations):
            with self.subTest(mutation=i),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(source,root);mutate(root)
                with self.assertRaises((ValueError,KeyError,IndexError)):audit(root)
        self.assertEqual(audit(source),original)


class DiagnosticCaptureTests(unittest.TestCase):
    def test_closure_packet_is_exact_and_does_not_expand_c5(self):
        from phase11_5_r3_v2_rf import CLOSURE_POLICY,DIAGNOSTIC_POLICY
        from phase11_5_r3_capacity_plan import http_capacity_cases
        p,_=self.baseline()
        p.update(closure_policy=CLOSURE_POLICY,observer_policy='single-flight-info-v1',runtime_seconds=300,
            maximum_renewals=8,wtp_capacity=dict(maximum_request_id='a'*32,oversized_request_id='b'*32,
                recovery_request_id='c'*32),http_capacity=dict(seed='d'*32,cases=http_capacity_cases('d'*32)),
            contention=dict(policy='native-wtp-and-https-status-20s-v1',maximum_https_requests=16))
        p['jobs'][0].update(mode='fskcw',total_duration_ns='128000000000',events=[
            dict(offset_ns=str(n*250000000),duration_ns='250000000',rf_on=True,
                frequency_nhz=str(135500000000000 if n%2==0 else 135495000000000)) for n in range(512)])
        self.assertEqual(validate(p),p)
        for key,value in [('closure_policy','unknown'),('runtime_seconds',301),('maximum_renewals',9),
                          ('diagnostic_policy',DIAGNOSTIC_POLICY),('allocator_failure_baseline',1)]:
            bad=copy.deepcopy(p);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(bad)
        for change in ['count','frequency','duration','http','wtp','contention']:
            bad=copy.deepcopy(p)
            if change=='count':bad['jobs'][0]['events'].pop()
            elif change=='frequency':bad['jobs'][0]['events'][1]['frequency_nhz']='135500000000000'
            elif change=='duration':bad['jobs'][0]['total_duration_ns']='129000000000'
            else:bad.pop({'http':'http_capacity','wtp':'wtp_capacity','contention':'contention'}[change])
            with self.subTest(change=change),self.assertRaises((ValueError,KeyError)):validate(bad)

    def baseline(self):
        from phase11_5_r3_v2_rf import DIAGNOSTIC_SOURCE,DIAGNOSTIC_IMAGE
        packet=FiniteRfPacketTests().packet()
        packet.update(source_revision=DIAGNOSTIC_SOURCE,image_sha256=DIAGNOSTIC_IMAGE)
        info=dict(device_id=DEVICE,revision=DIAGNOSTIC_SOURCE[:12],system_clock_hz=138000000,
            rf_render_in_ram=True,recovery_boot=False,engine_diagnostic='',heap_capacity_bytes=220328,
            allocator_peak_bytes=140152,allocator_failures='0',tls_allocation_failures=0,
            refill_full_predecessor=None,refill_short_predecessor=None,rf_max_service_gap_ns='100000',
            network=dict(accepted=5,link_status=3),
            status=dict(boot_id=packet['boot_id'],engine='pio-dma-gp2',storage_healthy=True,
                enabled=False,last_error=None,watermark_utc_ns='0',state='running',output_active=True,
                clock_state='synchronized',sync_age_ns='1000000000',utc_now_ns='20000000000',monotonic_now_ns='10000000000'))
        for k in ['fault_stage','fault_hash','fault_pc','fault_status','dma_errors',
                  'refill_invalid_reserves','exhausted_successor_links','refill_irq_unpaired',
                  'running_successor_links','refill_irq_pairs']:info[k]=0
        for core in [0,1]:
            p=f'core{core}_stack_'
            info.update({p+'guard_valid':1,p+'fault_status':0,p+'guard_bottom':1000,p+'guard_limit':5096})
        return packet,dict(info=info)

    def test_failure_latches_mutation_stop_but_retains_subsequent_info(self):
        from phase11_5_r3_v2_rf import capture_diagnostic_info,guarded_action,validate_info
        packet,base=self.baseline();validate_info(base['info'],base,packet)
        faults=[];events=[];actions=[];emit=lambda *a:events.append(a)
        bad=copy.deepcopy(base['info']);bad.update(allocator_failures='1',allocator_last_failure_request_bytes=65552)
        observed=[]
        for state in ['running','running','complete']:
            sample=copy.deepcopy(bad);sample['status'].update(state=state,output_active=state=='running')
            observed.append(capture_diagnostic_info(sample,base,packet,faults,emit))
            guarded_action(lambda _:actions.append('another stimulus'),sample,faults,emit)
        self.assertEqual(len(observed),3);self.assertEqual(len(faults),1);self.assertEqual(actions,[])
        self.assertEqual(observed[-1]['allocator_last_failure_request_bytes'],65552)
        with self.assertRaises(ValueError):validate_info(observed[-1],base,packet)

    def test_other_faults_stop_mutations_and_identity_change_is_fatal(self):
        from phase11_5_r3_v2_rf import capture_diagnostic_info,guarded_action
        packet,base=self.baseline()
        for k,v in [('dma_errors',1),('engine_diagnostic','refill_starved')]:
            bad=copy.deepcopy(base['info']);bad[k]=v;faults=[];actions=[]
            capture_diagnostic_info(bad,base,packet,faults,lambda *_:None)
            guarded_action(lambda _:actions.append(1),bad,faults,lambda *_:None)
            self.assertTrue(faults);self.assertEqual(actions,[])
        for change in ['boot','device','revision','output']:
            bad=copy.deepcopy(base['info'])
            if change=='boot':bad['status']['boot_id']='f'*32
            elif change=='device':bad['device_id']='f'*32
            elif change=='revision':bad['revision']='bad'
            else:bad['status']['output_active']=None
            with self.subTest(change=change),self.assertRaises(ValueError):
                capture_diagnostic_info(bad,base,packet,[],lambda *_:None)

    def test_recent_sample_does_not_admit_c4_stale_clock_or_mapping_change(self):
        from phase11_5_r3_v2_rf import recent_clock
        _,base=self.baseline();info=base['info'];self.assertTrue(recent_clock(info))
        clock=dict(state='synchronized',leap='normal',sync_age_ns='1100000000',
            utc_now_ns='20100000000',monotonic_now_ns='10100000000',uncertainty_ns='10000000')
        self.assertTrue(recent_clock(info,clock))
        for key,value in [('sync_age_ns','57652560000'),('leap','unknown'),
                          ('utc_now_ns','20125805000'),('monotonic_now_ns','13000000000')]:
            bad=dict(clock);bad[key]=value
            with self.subTest(key=key):self.assertFalse(recent_clock(info,bad))
        info['status']['sync_age_ns']='57652560000';self.assertFalse(recent_clock(info))

    def test_single_maximum_policy_rejects_extra_stimuli_and_duration(self):
        from phase11_5_r3_v2_rf import DIAGNOSTIC_POLICY
        packet,_=self.baseline();packet.update(diagnostic_policy=DIAGNOSTIC_POLICY,
            runtime_seconds=240,maximum_renewals=5,observer_policy='single-flight-info-v1',
            wtp_capacity=dict(maximum_request_id='a'*32))
        packet['jobs'][0]['total_duration_ns']=packet['jobs'][0]['events'][0]['duration_ns']='90000000000'
        validate(packet)
        import json
        from phase11_5_r3_capacity_plan import wtp_capacity_frame
        from audit_phase11_5_r3_v2_rf import capacity_request
        raw=wtp_capacity_frame(packet['peer_session'],packet['wtp_capacity']['maximum_request_id'])
        value=dict(hex=raw.hex(),request=json.loads(raw[16:]),expected_invalid_frames=0)
        self.assertEqual(capacity_request(packet,value,0),65552)
        with self.assertRaises(ValueError):capacity_request(packet,value,1)
        for key,value in [('runtime_seconds',241),('diagnostic_policy','unknown'),('contention',{}),('http_capacity',{})]:
            bad=copy.deepcopy(packet);bad[key]=value
            with self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(packet);bad['wtp_capacity']['oversized_request_id']='b'*32
        with self.assertRaises(ValueError):validate(bad)


class PagedRepairRetestTests(unittest.TestCase):
    def test_candidate_requires_exact_policy_and_workload(self):
        import json
        from phase11_5_r3_v2_rf import REPAIR_SOURCE,REPAIR_IMAGE,REPAIR_POLICY,CLOSURE_POLICY
        # Use the same bounded workload constructor as the existing C6 test.
        p,_=DiagnosticCaptureTests().baseline()
        from phase11_5_r3_capacity_plan import http_capacity_cases
        p.update(source_revision=REPAIR_SOURCE,image_sha256=REPAIR_IMAGE,closure_policy=REPAIR_POLICY,
            observer_policy='single-flight-info-v1',runtime_seconds=300,maximum_renewals=8,
            wtp_capacity=dict(maximum_request_id='a'*32,oversized_request_id='b'*32,recovery_request_id='c'*32),
            http_capacity=dict(seed='d'*32,cases=http_capacity_cases('d'*32)),
            contention=dict(policy='native-wtp-and-https-status-20s-v1',maximum_https_requests=16))
        p['jobs'][0].update(mode='fskcw',total_duration_ns='128000000000',events=[
            dict(offset_ns=str(n*250000000),duration_ns='250000000',rf_on=True,
                frequency_nhz=str(135500000000000 if n%2==0 else 135495000000000)) for n in range(512)])
        self.assertEqual(validate(p),p)
        for key,value in [('closure_policy',CLOSURE_POLICY),('image_sha256','0'*64),
                          ('runtime_seconds',301),('allocator_failure_baseline',1)]:
            bad=copy.deepcopy(p);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(p);bad.pop('closure_policy')
        with self.assertRaises(ValueError):validate(bad)
        from phase11_5_r3_v2_rf import native_running
        job=dict(boot_id=p['boot_id'],job_id=p['jobs'][0]['job_id'],owner_id=p['owner_id'],state='running',output_active=True)
        record=dict(packet_sha256='a'*64,observed_monotonic_ns=100,job=job)
        self.assertTrue(native_running(record,p,'a'*64,101))
        for key,value in [('state','armed'),('boot_id','f'*32),('job_id','f'*32),('owner_id',None),('output_active',False)]:
            bad=copy.deepcopy(record);bad['job'][key]=value
            self.assertFalse(native_running(bad,p,'a'*64,101))
        for now in [99,3000000101]:
            with self.assertRaises(ValueError):native_running(record,p,'a'*64,now)
        with self.assertRaises(ValueError):native_running(record,p,'b'*64,101)

if __name__=='__main__':unittest.main()
