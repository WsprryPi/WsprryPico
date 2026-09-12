import copy
import json
import tempfile
from types import SimpleNamespace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r2_plan import validate,AMENDED_SCHEMA,AMENDED_SOURCE,AMENDED_IMAGE
from phase11_5_device_fixture import candidate_images
from phase11_5_r2_amended_plan import INHIBITED,INITIAL_COUNTS
from phase11_5_r2_tests import packet
from phase11_5_r2_amended import admit_handoff, main
from phase11_5_r2 import R2_HELPERS
from phase11_5_r2_plan import jobs

class Amended(unittest.TestCase):
    def test_closed_identity_and_legacy(self):
        old=packet();validate(old)
        new=dict(old,schema=AMENDED_SCHEMA,source_revision=AMENDED_SOURCE,revision=AMENDED_SOURCE[:12],uf2_sha256=AMENDED_IMAGE)
        validate(new)
        self.assertEqual(candidate_images(AMENDED_SOURCE)['inhibited'][1],INHIBITED)
        for key in ('schema','source_revision','revision','uf2_sha256'):
            bad=copy.deepcopy(new);bad[key]=old[key]
            with self.subTest(key=key),self.assertRaises(ValueError):validate(bad)
    def test_counts_are_cumulative(self):
        self.assertEqual(INITIAL_COUNTS,{'config':28,'wifi-off':0,'wifi-on':0,'heap-probe':3})
        with self.assertRaises(ValueError):candidate_images('f'*40)

    def test_plan_only_without_access(self):
        with patch.object(sys,'argv',['amended','--root','/absent','--packet-sha256','absent']), \
             patch('phase11_5_r2_amended.Path.resolve',side_effect=AssertionError('accessed')):
            main()

    def test_coordinator_reports_running_then_disposition_without_retry(self):
        for fail in (False,True):
            with self.subTest(fail=fail),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);boot='5'*32
                original=dict(source_revision=AMENDED_SOURCE,rf_jobs=[],rf_nonce='1'*32,
                              current_wiring_confirmed=True,fixture_authorized=True)
                names=R2_HELPERS|{'scripts/phase11_5_r2_amended.py','scripts/phase11_5_r2_amended_plan.py'}
                p=dict(original,rf_jobs=jobs('1'*32),parent_packet_sha256='sha',
                       r2_helper_sha256={n:'sha' for n in names})
                for n in names:
                    path=root/n;path.parent.mkdir(parents=True,exist_ok=True);path.touch()
                for name,value in [('packet.json',original),('r2-amended-packet.json',p),
                    ('r1-result.json',{}),('management-state.json',{}),
                    ('r1-ready-for-r2.json',dict(source=AMENDED_SOURCE,boot=boot,packet_sha256='sha',r1_result_sha256='sha',deadline_monotonic_ns=0)),
                    ('r2-modes-completion.json',dict(source=AMENDED_SOURCE,boot=boot,status='NOT_RUN'))]:
                    (root/name).write_text(json.dumps(value))
                def gate(*args):
                    self.assertEqual(json.loads((root/'r2-result.json').read_text())['status'],'RUNNING')
                    if fail:raise ValueError('injected gate failure')
                    return {'completed_jobs':3,'family_closed':False}
                fixture=SimpleNamespace(state={'boot':boot},verify_helpers=lambda:None)
                with patch.object(sys,'argv',['amended','--root',str(root),'--packet-sha256','sha','--run']), \
                     patch('phase11_5_r2_amended.os.geteuid',return_value=0), \
                     patch('phase11_5_r2_amended.os.umask'), \
                     patch('phase11_5_r2_amended.digest',return_value='sha'), \
                     patch('phase11_5_r2_amended.DeviceFixture',return_value=fixture), \
                     patch('phase11_5_r2_amended.Fixture'), \
                     patch('phase11_5_r2_amended.admit_handoff'), \
                     patch('phase11_5_r2_amended.tone_packet',side_effect=gate) as called:
                    if fail:
                        with self.assertRaises(ValueError):main()
                    else:main()
                    called.assert_called_once()
                outcome=json.loads((root/'r2-completion.json').read_text())
                self.assertEqual(outcome['status'],'FAILED' if fail else 'TONE_GATE_PASSED_R2_REMAINS_OPEN')
                self.assertEqual(outcome['completed_jobs'],0 if fail else 3)
                self.assertEqual(outcome['boot'],boot)
                self.assertFalse(outcome['family_closed'])

    def test_resource_handoff_rejects_incomplete_or_changed_evidence(self):
        source=AMENDED_SOURCE;boot='5'*32;now=1000000000
        p={'source_revision':source}
        ready=dict(source=source,boot=boot,deadline_monotonic_ns=now+451000000000,
                   largest_successful_request_bytes=18364)
        resources=dict(boot=boot,clock_hz=138000000,heap_capacity_bytes=218284,
                       allocator_largest_successful_request_bytes=18364)
        result=dict(source=source,status='CAPTURED_REQUIRES_FINAL_REVIEW',rf_jobs=[],
                    quiet_delta_bytes=-8,probes=[dict(bytes=n,allocated=v) for n,v in
                    ((18364,True),(218285,False),(18364,True))],
                    intervals={name:dict(resources=copy.deepcopy(resources)) for name in
                    ('r1-inhibited','r1-warm','r1-controller','r1-normal','r1-quiet-before','r1-quiet-after')})
        device=dict(boot=boot,kind='physical',deadline_monotonic_ns=ready['deadline_monotonic_ns'])
        management=dict(counts=dict(INITIAL_COUNTS,config=29,**{'heap-probe':6}))
        args=[p,ready,result,device,management,now]
        admit_handoff(*args)
        mutations=[lambda a:a[0].update(source_revision='f'*40),
            lambda a:a[2].update(status='FAILED'),lambda a:a[2]['intervals'].pop('r1-normal'),
            lambda a:a[2].update(rf_jobs=[{}]),lambda a:a[3].update(boot='6'*32),
            lambda a:a[3].update(restored=True),lambda a:a[3].update(pending='flash'),
            lambda a:a[4]['counts'].update(config=1),lambda a:a[4].update(blocked=True),
            lambda a:a[2]['probes'][1].update(allocated=True),
            lambda a:a[2].update(quiet_delta_bytes=1025),
            lambda a:a[2]['intervals']['r1-normal']['resources'].update(clock_hz=150000000),
            lambda a:a[2]['intervals']['r1-normal']['resources'].update(heap_capacity_bytes=218285),
            lambda a:a[2]['intervals']['r1-normal']['resources'].update(allocator_largest_successful_request_bytes=18365)]
        for mutation in mutations:
            changed=copy.deepcopy(args);mutation(changed)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):admit_handoff(*changed)
        with self.assertRaises(ValueError):admit_handoff(*args[:-1],now+1000000000)

if __name__=='__main__':unittest.main()
