"""Offline reassessment of the preserved C8 capture; requires private evidence."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_load_reply_target import audit
from phase11_5_load_reply_target import healthy


class CaptureTests(unittest.TestCase):
    def test_original_stop_is_preserved_and_explained(self):
        value=audit(self.evidence)
        self.assertEqual(value['status'],'LOAD_REPLY_TARGET_FAILED')
        self.assertEqual(value['counts']['primary_loads'],0)
        self.assertEqual(value['counts']['replays'],0)
        self.assertEqual(value['counts']['rf_jobs'],0)
        self.assertTrue(value['fixture_restored'])
        self.assertTrue(value['b_unchanged'])
        info,=value['recovered_failed_info_samples']
        self.assertEqual(info['launch_epoch'],'0')
        self.assertEqual(info['allocator_failures'],'0')
        self.assertEqual(info['tls_allocation_failures'],0)
        self.assertEqual(info['tls_allocated_bytes'],31384)
        spec=importlib.util.spec_from_file_location('frozen_load_target',self.evidence/'frozen/phase11_5_load_reply_target.py')
        frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
        with self.assertRaisesRegex(ValueError,'Idle counters/faults'):frozen.healthy(info,value['boot_id'])
        healthy(info,value['boot_id'])

    def test_altered_evidence_is_rejected(self):
        def modify_json(root,name,change):
            path=root/name;value=json.loads(path.read_text());change(value);path.write_text(json.dumps(value)+'\n')
        def modify_rows(root,name,change):
            path=root/name;value=[json.loads(line) for line in path.read_text().splitlines()];change(value);path.write_text(''.join(json.dumps(row)+'\n' for row in value))
        def change_row(root,name,kind,change):
            modify_rows(root,name,lambda rows:change(next(row for row in rows if row['kind']==kind)))
        def promote(root):
            modify_json(root,'run-result.json',lambda v:v.update(status='CAPTURED_REQUIRES_AUDIT'))
            modify_rows(root,'run.jsonl',lambda r:r[-1]['value'].update(status='CAPTURED_REQUIRES_AUDIT'))
        cases={
            'false_success':promote,
            'declared_primary':lambda r:modify_json(r,'run-result.json',lambda v:v.update(primary_loads=1)),
            'reply_summary':lambda r:change_row(r,'run.jsonl','usb_message',lambda v:v['value']['message'].update(request_id='0'*32)),
            'write_count':lambda r:change_row(r,'run.jsonl','usb_write',lambda v:v['value'].update(bytes=1)),
            'usb_crc':lambda r:change_row(r,'run.jsonl','usb_rx',lambda v:v['value'].update(hex='00'+v['value']['hex'][2:])),
            'hidden_operation':lambda r:change_row(r,'run.jsonl','usb_tx',lambda v:v['value']['request'].update(op='ARM')),
            'truncated_journal':lambda r:(r/'run.jsonl').write_bytes((r/'run.jsonl').read_bytes()[:-1]),
            'sequence':lambda r:modify_rows(r,'run.jsonl',lambda v:v[2].update(sequence=999)),
            'packet_binding':lambda r:modify_json(r,'test-packet.json',lambda v:v.update(owner_id='0'*32)),
            'extra_flash':lambda r:modify_json(r,'deployment.json',lambda v:v.update(flashes_started=2)),
            'final_authority':lambda r:modify_rows(r,'post-restoration-a.stdout',lambda v:v[-1]['value']['wtp']['STATUS'].update(output_active=True)),
            'b_identity':lambda r:modify_rows(r,'post-restoration-b.stdout',lambda v:v[-1]['value']['info'].update(revision='unknown')),
            'tls_identity':lambda r:change_row(r,'network.jsonl','tls',lambda v:v['value'].update(peer_sha256='0'*64)),
            'tls_bytes':lambda r:change_row(r,'network.jsonl','tls_rx',lambda v:v['value'].update(hex='00'+v['value']['hex'][2:])),
            'fixture_cleanup':lambda r:change_row(r,'fixture.jsonl','cleanup',lambda v:v['value'].update(failures=['unrestored'])),
        }
        for label,change in cases.items():
            with self.subTest(case=label),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/'evidence';shutil.copytree(self.evidence,root);change(root)
                with self.assertRaises(ValueError):audit(root)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();CaptureTests.evidence=args.evidence.resolve(strict=True)
    unittest.main(argv=[sys.argv[0]])
