"""Offline adversarial checks of the bounded repaired Pico replay capture."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_load_reply_target import audit,wire_decode
from validate_wtp_contract import frame
from phase11_5_load_reply_recovery_audit_tests import modify_infos,read_rows,write_rows,distribute

def modify_response(root,label,change,padding=b''):
    # USB events can span the last primary RX and first replay RX. Reconstruct
    # the entire stream, preserving each frame's completing chunk and summary.
    rows=read_rows(root,'run.jsonl')
    indices=[i for i,x in enumerate(rows) if x['kind']=='usb_rx']
    summaries=[i for i,x in enumerate(rows) if x['kind']=='usb_message']
    sizes=[len(bytes.fromhex(rows[i]['value']['hex'])) for i in indices]
    buf=bytearray(b''.join(bytes.fromhex(rows[i]['value']['hex']) for i in indices))
    messages=wire_decode(buf);assert not buf and len(messages)==len(summaries)
    offset=0;raw=b'';adjustments=[0]*len(indices);changed=False
    for (message,payload),summary in zip(messages,summaries):
        assert rows[summary]['value']['message']==message
        original_size=len(payload)+16;offset+=original_size
        if rows[summary]['value']['label']==label and message['type']=='response':
            change(message);rows[summary]['value']['message']=message;changed=True
            payload=json.dumps(message,separators=(',',':')).encode()+padding
            cumulative=0
            for index,size in enumerate(sizes):
                cumulative+=size
                if cumulative>=offset:
                    adjustments[index]+=len(payload)+16-original_size;break
        raw+=frame(payload)
    assert changed
    for index,size,extra in zip(indices,sizes,adjustments):
        rows[index]['value']['hex']='00'*(size+extra)
    distribute(rows,indices,raw);write_rows(root,'run.jsonl',rows)


class ValidationTests(unittest.TestCase):
    def test_complete_bounded_acceptance(self):
        value=audit(self.evidence)
        self.assertEqual(value['status'],'LOAD_REPLY_TARGET_PASS')
        self.assertEqual(value['replays_passed'],['identical-replay','fresh-id-replay'])
        self.assertEqual(value['counts'],dict(flashes=1,bootsel=1,preparation_loads=1,primary_loads=1,replays=2,rf_jobs=0,configuration_writes=0,wifi_cycles=0))
        self.assertEqual(value['https_requests'],4)
        self.assertTrue(value['fixture_restored'] and value['b_unchanged'])
        self.assertFalse(value['health_findings'] or value['group2_closed'])
        self.assertEqual(len(value['exchange_tls_brackets']),3)
        self.assertTrue(all(v['comparable'] for v in value['exchange_tls_brackets'].values()))

    def test_lower_pressure_is_limited(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'evidence';shutil.copytree(self.evidence,root)
            modify_infos(root,lambda v:v.update(tls_allocated_bytes=4396))
            value=audit(root)
            self.assertEqual(value['status'],'LOAD_REPLY_TARGET_LIMITED')
            self.assertFalse(value['tls_pressure_comparable'])
            self.assertEqual(len(value['replays_passed']),2)

    def test_altered_evidence_is_rejected(self):
        def document(root,name,change):
            path=root/name;v=json.loads(path.read_text());change(v);path.write_text(json.dumps(v)+'\n')
        def records(root,name,change):
            v=read_rows(root,name);change(v);write_rows(root,name,v)
        def result(root,change):
            document(root,'run-result.json',change);records(root,'run.jsonl',lambda v:change(v[-1]['value']))
        def early_retention(root):
            v=read_rows(root,'run.jsonl');shift=False
            for row in v:
                if row['kind']=='usb_tx' and row['value']['label']=='test-hello':shift=True
                if shift:row['monotonic_ns']-=305000000000
            write_rows(root,'run.jsonl',v)
        def late_replay(root):
            v=read_rows(root,'run.jsonl');shift=False
            for row in v:
                if row['kind']=='usb_message' and row['value']['label']=='fresh-id-replay':shift=True
                if shift:row['monotonic_ns']+=6000000000
            write_rows(root,'run.jsonl',v)
        def replay_padding(root):
            modify_response(root,'identical-replay',lambda v:None,padding=b' ')
        cases={
            'replay_payload_size':replay_padding,
            'primary_adjustment':lambda r:modify_response(r,'primary',lambda v:v['body']['adjustments'][0].update(event_index=9)),
            'identical_adjustment':lambda r:modify_response(r,'identical-replay',lambda v:v['body']['adjustments'][0].update(event_index=9)),
            'fresh_adjustment':lambda r:modify_response(r,'fresh-id-replay',lambda v:v['body']['adjustments'][0].update(event_index=9)),
            'fresh_request_identity':lambda r:modify_response(r,'fresh-id-replay',lambda v:v.update(request_id='f'*32)),
            'wrong_job':lambda r:modify_response(r,'primary',lambda v:v['body'].update(job_id='f'*32)),
            'loaded_output':lambda r:modify_response(r,'loaded-status',lambda v:v['body'].update(output_active=True)),
            'wrong_owner':lambda r:modify_response(r,'test-claim',lambda v:v['body'].update(owner_id='f'*32)),
            'allocation_failure':lambda r:modify_infos(r,lambda v:v.update(allocator_failures='1')),
            'stack_fault':lambda r:modify_infos(r,lambda v:v.update(core0_stack_fault_status=1)),
            'reserve_shortfall':lambda r:modify_infos(r,lambda v:v.update(allocator_peak_bytes=190424)),
            'wrong_firmware':lambda r:modify_infos(r,lambda v:v.update(revision='e256633304e0')),
            'premature_retention':early_retention,
            'late_replay':late_replay,
            'extra_flash':lambda r:document(r,'deployment.json',lambda v:v.update(flashes_started=2)),
            'replay_count':lambda r:result(r,lambda v:v.update(replays=1)),
            'final_output':lambda r:records(r,'post-restoration-a.stdout',lambda v:v[-1]['value']['wtp']['STATUS'].update(output_active=True)),
            'bootsel_raw':lambda r:records(r,'deploy.jsonl',lambda v:next(x for x in v if x['kind']=='tx')['value'].update(hex='00')),
            'deploy_identity':lambda r:records(r,'deploy.jsonl',lambda v:v[0]['value'].update(source='f'*40)),
            'https_status':lambda r:records(r,'network.jsonl',lambda v:next(x for x in v if x['kind']=='https')['value'].update(status=500)),
            'tls_identity':lambda r:records(r,'network.jsonl',lambda v:next(x for x in v if x['kind']=='tls')['value'].update(peer_sha256='0'*64)),
            'short_observation':lambda r:records(r,'network.jsonl',lambda v:v[-1].update(monotonic_ns=v[0]['monotonic_ns']+88000000000)),
            'fixture_cleanup':lambda r:records(r,'fixture.jsonl',lambda v:next(x for x in v if x['kind']=='cleanup')['value'].update(failures=['unrestored'])),
        }
        for label,change in cases.items():
            with self.subTest(case=label),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(self.evidence,root);change(root)
                with self.assertRaises(ValueError):audit(root)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();ValidationTests.evidence=args.evidence.resolve(strict=True)
    unittest.main(argv=[sys.argv[0]])
