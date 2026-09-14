"""Reject false component credit while retaining the original failed run."""
import json, os, shutil, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_v2_interrupted_hour import audit, audit_c1, cadence

class InterruptedHourTests(unittest.TestCase):
    def test_cadence_does_not_hide_missing_end_or_gap(self):
        self.assertEqual(cadence([{'began':0,'ended':1},{'began':2,'ended':3}],2,0,3)['samples'],2)
        for rows, begin, end in [([{'began':1,'ended':2}],0,2),
                                 ([{'began':0,'ended':1}],0,4),
                                 ([{'began':0,'ended':1},{'began':3,'ended':4}],0,4)]:
            with self.subTest(rows=rows), self.assertRaises(ValueError): cadence(rows,2,begin,end)

    def test_actual_and_adversarial_mutations(self):
        c1 = os.environ.get('PHASE115_R3_V2_C1_COMPONENT_EVIDENCE')
        source = c1 or os.environ.get('PHASE115_R3_V2_H1A_COMPONENT_EVIDENCE')
        if not source: self.skipTest('Private H1a completed archive required')
        source = Path(source)
        def check(root): return (audit_c1 if c1 else audit)(root, root/'pi/phase115_tls_observer_test.py')
        original = check(source)
        if c1:
            self.assertEqual(original['maximum_events'],512)
            self.assertEqual(original['original_runner_status'],'FAILED')
        else:
            self.assertTrue(original['physical_hour_verified'])
            self.assertEqual(original['full_usb_observation_gate'], 'FAILED')
        def edit(root, filename, change):
            path=root/filename;rows=[json.loads(s) for s in path.read_text().splitlines()]
            change(rows);path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        def rf(root, change): edit(root,'rf.jsonl',change)
        def first(rows, kind): return next(r for r in rows if r['kind']==kind)
        def last_info(rows): return next(r for r in reversed(rows) if r['kind']=='info')['value']['value']
        mutations = [
            lambda r: rf(r, lambda a: first(a,'failure')['value'].update(error='different failure')),
            lambda r: rf(r, lambda a: a.pop(30)),
            lambda r: rf(r, lambda a: last_info(a).update(tail_irqs=0)),
            lambda r: rf(r, lambda a: first(a,'info')['value']['value'].update(allocator_failures='1')),
            lambda r: rf(r, lambda a: first(a,'health')['value']['value'].update(throttled='throttled=0x1')),
            lambda r: rf(r, lambda a: first(a,'info_finish')['value'].update(samples=1)),
            lambda r: rf(r, lambda a: first(a,'wtp_rx')['value'].update(hex='00')),
            lambda r: edit(r,'contention.jsonl',lambda a:first(a,'https_status')['value'].update(peer_sha256='0'*64)),
            lambda r: (r/'production-tls.bin').write_bytes((r/'production-tls.bin').read_bytes()[:-1]),
            lambda r: (r/'packet.json').write_text('{}\n'),
            lambda r: (r/'final-a.stdout').write_text(''),
            lambda r: rf(r, lambda a: a[-1]['value'].update(status='CAPTURED_REQUIRES_AUDIT')),
        ]
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=index), tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(source,root);mutation(root)
                with self.assertRaises((ValueError, KeyError, IndexError)): check(root)
        self.assertEqual(check(source), original)

if __name__ == '__main__': unittest.main()
