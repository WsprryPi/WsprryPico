"""Recovery scope and authoritative idle admission, without device access."""
import copy,json,sys,unittest,shutil,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_wifi_recovery import validate,idle,initial_link,SCHEMA
from phase11_5_r3_v2_rf import ASSET_SOURCE,ASSET_IMAGE,COMPLETION_SOURCE,COMPLETION_IMAGE

class WifiRecoveryTests(unittest.TestCase):
    def test_addressless_admission_does_not_cycle_a_healthy_or_disabled_link(self):
        p=dict(initial_link_policy='associated-no-ipv4-v1')
        n=dict(enabled=True,ipv4='',link_status=1,mdns_state='waiting_address');initial_link(n,p)
        for key,value in [('enabled',False),('ipv4','10.77.15.10'),('link_status',3),('mdns_state','advertising')]:
            with self.subTest(key=key),self.assertRaises(ValueError):initial_link(dict(n,**{key:value}),p)
        with self.assertRaises(ValueError):initial_link(n,{})
        for state in (-3,-2,1):
            initial_link(dict(n,link_status=state),dict(initial_link_policy='no-ipv4-after-240-v1'))
        for state in (0,2,3):
            with self.assertRaises(ValueError):
                initial_link(dict(n,link_status=state),dict(initial_link_policy='no-ipv4-after-240-v1'))
    def test_scope_limits(self):
        p=dict(schema=SCHEMA,r3_scope=SCHEMA,standing_authority='R3-COMPLETE-20260913-v2',serial='0BF4B4AEC9FFB344',
            device_id='fd6127d11d6aca42a9905fa3fb1bf1d5',source_revision=ASSET_SOURCE,image_sha256=ASSET_IMAGE,
            runtime_seconds=300,restoration_seconds=150,maximum_wifi_cycles=1,rf_jobs=0,flashes=0,configuration_writes=0,heap_probes=0,
            hypothesis='A stayed at terminal link failure after F1 AP expiry; one idle OFF/ON requests rejoin to verified F2')
        self.assertEqual(validate(p),p)
        current=dict(p,source_revision=COMPLETION_SOURCE,image_sha256=COMPLETION_IMAGE,
            completion_recovery_policy='retained-complete-addressless-v1',initial_link_policy='associated-no-ipv4-v1',
            initial_job_id='b88c7a3082eb4208a7e1f403bc13c9f8',not_before_monotonic_ns=1,
            hypothesis='A remained associated without IPv4 for at least 240 seconds after P1b fixture activation; one inactive OFF/ON restarts acquisition')
        validate(current)
        from phase11_5_r3_v2_wifi_recovery import MEMORY_RECOVERY, MEMORY_HYPOTHESIS
        from phase11_5_r3_v2_rf import MEMORY_SOURCE, MEMORY_IMAGE, MEMORY_BOOT
        memory=dict(p,memory_recovery_policy=MEMORY_RECOVERY,source_revision=MEMORY_SOURCE,
            image_sha256=MEMORY_IMAGE,boot_id=MEMORY_BOOT,initial_link_policy='cold-link-down-v1',
            hypothesis=MEMORY_HYPOTHESIS,initial_job_id=None,not_before_monotonic_ns=1)
        validate(memory)
        n=dict(enabled=True,ipv4='',link_status=-1,mdns_state='waiting_address')
        initial_link(n,memory)
        for k,v in [('ipv4','10.77.15.10'),('link_status',3),('enabled',False)]:
            with self.assertRaises(ValueError):initial_link(dict(n,**{k:v}),memory)
        for k,v in [('boot_id','0'*32),('initial_job_id','job'),('not_before_monotonic_ns',0),
                    ('maximum_wifi_cycles',2),('source_revision',ASSET_SOURCE)]:
            with self.assertRaises(ValueError):validate(dict(memory,**{k:v}))
        for key,value in [('not_before_monotonic_ns',0),('initial_job_id','other'),('initial_link_policy','terminal-failure-v1')]:
            with self.assertRaises(ValueError):validate(dict(current,**{key:value}))
        for key,value in [('serial','CDDBF8767C506C07'),('rf_jobs',1),('flashes',1),('configuration_writes',1),
            ('heap_probes',1),('maximum_wifi_cycles',2),('runtime_seconds',301),('restoration_seconds',151),('image_sha256','0'*64)]:
            q=copy.deepcopy(p);q[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate(q)

    def test_complete_recovery_preserves_inactive_authority(self):
        p=dict(boot_id='boot',completion_recovery_policy='retained-complete-addressless-v1',initial_job_id='job')
        v=dict(info=dict(status=dict(state='complete',output_active=False,enabled=False)),
            wtp=dict(STATUS=dict(boot_id='boot',state='complete',output_active=False,owner_id=None,job_id='job')))
        with patch('phase11_5_r3_v2_wifi_recovery.validate_info'),patch('phase11_5_r3_v2_wifi_recovery.configuration',return_value=None):
            idle(v,v,p)
            for key,value in [('state','armed'),('output_active',True),('owner_id','foreign'),('job_id','other')]:
                changed=copy.deepcopy(v);changed['wtp']['STATUS'][key]=value
                with self.assertRaises(ValueError):idle(changed,v,p)
            changed=copy.deepcopy(v);changed['info']['status']['enabled']=True
            with self.assertRaises(ValueError):idle(changed,v,p)

    def test_live_recorded_authority_rejections(self):
        path=Path(__file__).resolve().parents[1]/'build/phase11-5-r3-v2-fixture-f2/admission.json'
        if not path.exists():self.skipTest('Private recorded admission required')
        r=json.loads(path.read_text());v=next(json.loads(l)['value'] for l in r['inventory_stdout'].splitlines() if json.loads(l)['kind']=='finish')
        p=dict(source_revision=ASSET_SOURCE,boot_id=v['wtp']['STATUS']['boot_id']);idle(v,v,p)
        for mutation in [dict(state='running',output_active=True),dict(owner_id='other'),dict(job_id='other'),dict(boot_id='0'*32)]:
            changed=copy.deepcopy(v);changed['wtp']['STATUS'].update(mutation)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):idle(changed,v,p)
        changed=copy.deepcopy(v);changed['info']['status']['enabled']=True
        with self.assertRaises(ValueError):idle(changed,v,p)

class WifiRecoveryAuditTests(unittest.TestCase):
    def test_actual_recovery_and_mutations(self):
        from audit_phase11_5_r3_v2_wifi_recovery import audit
        source=Path(__file__).resolve().parents[1]/'build/phase11-5-r3-v2-wifi-w0/evidence'
        if not source.exists():self.skipTest('Private W0 evidence required')
        sha='9f966046ea29d5062a8699157e951cf67f83526dd437a2c8d8ed89a3657ceda6'
        expected=audit(source,sha)
        def change_wire(root,name):
            p=root/name;raw=p.read_text();p.write_text(raw.replace('57494649204f46460a','57494649204f4e0a'))
        changes=[lambda r:(r/'before-a.stdout').write_text(''),
            lambda r:(r/'off-exchange.jsonl').write_text(''),
            lambda r:change_wire(r,'off-exchange.jsonl'),
            lambda r:(r/'on-exchange.jsonl').write_bytes((r/'on-exchange.jsonl').read_bytes()[:-1]),
            lambda r:(r/'wifi-result.json').write_text('{}'),
            lambda r:(r/'ready-2.stdout').write_text(''),
            lambda r:(r/'packet.json').write_text('{}')]
        for n,change in enumerate(changes):
            with self.subTest(mutation=n),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/'evidence';shutil.copytree(source,root);change(root)
                with self.assertRaises((ValueError,KeyError,IndexError)):audit(root,sha)
        self.assertEqual(audit(source,sha),expected)

if __name__=='__main__':unittest.main()
