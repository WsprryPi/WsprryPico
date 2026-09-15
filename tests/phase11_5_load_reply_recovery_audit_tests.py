"""Offline checks of the primary LOAD reply and preserved reserve-limit stop."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_load_reply_target import audit,wire_decode
from phase11_5_load_reply_target import raw_request


def read_rows(root,name):
    return [json.loads(x) for x in (root/name).read_text().splitlines()]


def write_rows(root,name,rows):
    (root/name).write_text(''.join(json.dumps(x)+'\n' for x in rows))


def distribute(rows,indices,raw):
    for number,index in enumerate(indices):
        size=len(bytes.fromhex(rows[index]['value']['hex'])) if number<len(indices)-1 else len(raw)
        rows[index]['value']['hex']=raw[:size].hex();raw=raw[size:]
    assert not raw


def modify_response(root,label,change):
    rows=read_rows(root,'run.jsonl');indices=[];summaries=[]
    for index,row in enumerate(rows):
        if row['kind']=='usb_rx' and row['value']['label']==label:indices.append(index)
        if row['kind']=='usb_message' and row['value']['label']==label:summaries.append(index)
    buffer=bytearray(b''.join(bytes.fromhex(rows[i]['value']['hex']) for i in indices))
    messages=wire_decode(buffer);assert not buffer and len(messages)==len(summaries)
    raw=b''
    for (message,_),index in zip(messages,summaries):
        if message['type']=='response':change(message)
        rows[index]['value']['message']=message;raw+=raw_request(message)
    distribute(rows,indices,raw);write_rows(root,'run.jsonl',rows)


def modify_infos(root,change):
    rows=read_rows(root,'run.jsonl');indices=[]
    for index,row in enumerate(rows):
        if row['kind']=='console_rx':indices.append(index)
        elif row['kind']=='info':
            value=copy.deepcopy(row['value']['value']);change(value)
            row['value']['value']=value;distribute(rows,indices,(json.dumps(value,separators=(',',':'))+'\n').encode());indices=[]
    write_rows(root,'run.jsonl',rows)


class RecoveryTests(unittest.TestCase):
    def test_primary_completes_but_replay_stops_for_reserve(self):
        value=audit(self.evidence)
        self.assertEqual(value['status'],'LOAD_REPLY_TARGET_FAILED')
        self.assertEqual(value['counts'],dict(flashes=0,bootsel=0,preparation_loads=1,primary_loads=1,replays=1,rf_jobs=0,configuration_writes=0,wifi_cycles=1))
        self.assertEqual(value['https_requests'],1)
        self.assertFalse(value['replays_passed'])
        self.assertEqual({x['headroom_bytes'] for x in value['health_findings']},{29288})
        self.assertEqual(value['transactions']['primary']['response_bytes'],54916)
        self.assertEqual(value['transactions']['identical-replay']['written'],52105)
        self.assertIsNone(value['transactions']['identical-replay']['response'])
        self.assertTrue(value['primary_pass'] and value['readiness']['complete'] and value['fixture_restored'] and value['b_unchanged'])
        self.assertEqual(value['wifi']['status'],'WIFI_RECOVERED')
        self.assertFalse(value['group2_closed'])

    def test_lower_pressure_cannot_receive_full_credit(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'evidence';shutil.copytree(self.evidence,root)
            modify_infos(root,lambda v:v.update(tls_allocated_bytes=4396))
            value=audit(root)
            self.assertEqual(value['status'],'LOAD_REPLY_TARGET_FAILED')
            self.assertFalse(value['tls_pressure_comparable'])
            self.assertTrue(value['health_findings'])

    def test_changed_evidence_is_rejected(self):
        def document(root,name,change):
            path=root/name;value=json.loads(path.read_text());change(value);path.write_text(json.dumps(value)+'\n')
        def records(root,name,change):
            rows=read_rows(root,name);change(rows);write_rows(root,name,rows)
        def early_retention(root):
            rows=read_rows(root,'run.jsonl');shift=False
            for row in rows:
                if row['kind']=='usb_tx' and row['value']['label']=='test-hello':shift=True
                if shift:row['monotonic_ns']-=305000000000
            write_rows(root,'run.jsonl',rows)
        def change_result(root,change):
            document(root,'run-result.json',change)
            records(root,'run.jsonl',lambda rows:change(rows[-1]['value']))
        cases={
            'wrong_adjustment':lambda r:modify_response(r,'primary',lambda v:v['body']['adjustments'][0].update(event_index=9)),
            'primary_wrong_job':lambda r:modify_response(r,'primary',lambda v:v['body'].update(job_id='f'*32)),
            'primary_wrong_request':lambda r:modify_response(r,'primary',lambda v:v.update(request_id='f'*32)),
            'active_status':lambda r:modify_response(r,'pre-status-0',lambda v:v['body'].update(output_active=True)),
            'wrong_owner':lambda r:modify_response(r,'test-claim',lambda v:v['body'].update(owner_id='f'*32)),
            'allocation_failure':lambda r:modify_infos(r,lambda v:v.update(allocator_failures='1')),
            'stack_fault_during_reserve_failure':lambda r:modify_infos(r,lambda v:v.update(core0_stack_fault_status=1)),
            'premature_retained_check':early_retention,
            'extra_wifi_cycle':lambda r:document(r,'wifi-state.json',lambda v:v.update(off_started=2)),
            'extra_flash':lambda r:document(r,'deployment.json',lambda v:v.update(flashes_started=1)),
            'primary_count':lambda r:document(r,'run-result.json',lambda v:v.update(primary_loads=2)),
            'final_output':lambda r:records(r,'post-restoration-a.stdout',lambda v:v[-1]['value']['wtp']['STATUS'].update(output_active=True)),
            'wifi_raw_bytes':lambda r:records(r,'wifi.jsonl',lambda v:next(x for x in v if x['kind']=='rx')['value'].update(hex='00')),
            'https_status':lambda r:records(r,'network.jsonl',lambda v:next(x for x in v if x['kind']=='https')['value'].update(status=500)),
            'removed_failure_reason':lambda r:change_result(r,lambda v:v.update(observer_errors=[])),
            'promoted_failed_capture':lambda r:change_result(r,lambda v:v.update(status='CAPTURED_REQUIRES_AUDIT')),
            'tls_identity':lambda r:records(r,'network.jsonl',lambda v:next(x for x in v if x['kind']=='tls')['value'].update(peer_sha256='0'*64)),
            'fixture_cleanup':lambda r:records(r,'fixture.jsonl',lambda v:next(x for x in v if x['kind']=='cleanup')['value'].update(failures=['unrestored'])),
        }
        for label,change in cases.items():
            with self.subTest(case=label),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(self.evidence,root);change(root)
                with self.assertRaises(ValueError):audit(root)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();RecoveryTests.evidence=args.evidence.resolve(strict=True)
    unittest.main(argv=[sys.argv[0]])
