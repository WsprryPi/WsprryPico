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
            lambda r:(r/'final-b.stdout').write_text(''),
            lambda r:(r/'packet.json').write_text('{}\n'),
            lambda r:edit(r,lambda a:a[-1]['value'].update(rf_duration_ns_charged=10000000000)),
        ]
        for i,mutate in enumerate(mutations):
            with self.subTest(mutation=i),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(source,root);mutate(root)
                with self.assertRaises((ValueError,KeyError,IndexError)):audit(root)
        self.assertEqual(audit(source),original)

if __name__=='__main__':unittest.main()
