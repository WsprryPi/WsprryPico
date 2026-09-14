"""Offline checks of the retained-image continuation and readiness failure."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_load_reply_target import audit


class ContinuationTests(unittest.TestCase):
    def test_no_load_or_flash_and_original_deadline_preserved(self):
        value=audit(self.evidence)
        self.assertEqual(value['status'],'LOAD_REPLY_TARGET_FAILED')
        self.assertTrue(all(count==0 for count in value['counts'].values()))
        self.assertFalse(value['readiness']['complete'])
        self.assertEqual(value['readiness']['samples'],43)
        self.assertTrue(value['fixture_restored'])
        self.assertTrue(value['b_unchanged'])
        self.assertEqual(value['final_authority']['state'],'empty')

    def test_changed_readiness_or_lineage_is_rejected(self):
        def document(root,name,change):
            path=root/name;value=json.loads(path.read_text());change(value);path.write_text(json.dumps(value)+'\n')
        def records(root,name,change):
            path=root/name;value=[json.loads(x) for x in path.read_text().splitlines()];change(value);path.write_text(''.join(json.dumps(x)+'\n' for x in value))
        cases={
            'ready_without_address':lambda r:records(r,'readiness.jsonl',lambda v:v[-1].update(kind='finish',value=dict(status='PICO_NETWORK_READY'))),
            'info_summary':lambda r:records(r,'readiness.jsonl',lambda v:next(x for x in v if x['kind']=='info')['value']['network'].update(ipv4='10.77.15.10')),
            'readiness_operation':lambda r:records(r,'readiness.jsonl',lambda v:next(x for x in v if x['kind']=='tx')['value'].update(hex=b'WIFI ON\n'.hex())),
            'readiness_sequence':lambda r:records(r,'readiness.jsonl',lambda v:v[1].update(sequence=999)),
            'prior_primary':lambda r:document(r,'prerequisite/run-result.json',lambda v:v.update(primary_loads=1)),
            'extended_deadline':lambda r:document(r,'prerequisite/test-packet.json',lambda v:v.update(work_deadline_utc_ns=v['work_deadline_utc_ns']+1)),
            'extra_flash':lambda r:document(r,'deployment.json',lambda v:v.update(flashes_started=1)),
            'final_authority':lambda r:records(r,'post-restoration-a.stdout',lambda v:v[-1]['value']['wtp']['STATUS'].update(output_active=True)),
        }
        for label,change in cases.items():
            with self.subTest(case=label),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(self.evidence,root);change(root)
                with self.assertRaises(ValueError):audit(root)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();ContinuationTests.evidence=args.evidence.resolve(strict=True)
    unittest.main(argv=[sys.argv[0]])
