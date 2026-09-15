"""Altered evidence must not turn the first completion failure into acceptance."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_completion_p1_failure import audit
from audit_phase11_5_completion_prearm import audit as audit_prearm
from audit_phase11_5_completion_readiness_failure import audit as audit_native_failure

EVIDENCE = os.environ.get('PHASE115_COMPLETION_P1_FAILURE')
PREARM = os.environ.get('PHASE115_COMPLETION_PREARM')
NATIVE_FAILURE = os.environ.get('PHASE115_COMPLETION_NATIVE_FAILURE')
IDLE_FAILURE = os.environ.get('PHASE115_COMPLETION_IDLE_FAILURE')


@unittest.skipUnless(EVIDENCE, 'Private completed packet not supplied')
class Tests(unittest.TestCase):
    def test_preserved_failure(self):
        value = audit(Path(EVIDENCE))
        self.assertFalse(value['capacity_acceptance'])
        self.assertEqual(value['host_bytes_written'], 4096)

    def test_rejects_altered_write_console_and_completion(self):
        for mutation in ('write', 'console', 'completion'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)/'evidence'; shutil.copytree(EVIDENCE, root)
                path = root/'rf.jsonl'
                rows = [json.loads(line) for line in path.read_text().splitlines()]
                if mutation == 'write':
                    next(r for r in rows if r['kind']=='capacity_write')['value']['total_written']=65552
                elif mutation == 'console':
                    next(r for r in rows if r['kind']=='info')['value']['value']['status']['output_active']=True
                else:
                    value = json.loads((root/'rf-result.json').read_text())
                    value['status']='CAPTURED_REQUIRES_AUDIT'; rows[-1]['value']=value
                    (root/'rf-result.json').write_text(json.dumps(value))
                path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
                with self.assertRaises(ValueError):
                    audit(root)


@unittest.skipUnless(PREARM, 'Private pre-ARM packet not supplied')
class PrearmTests(unittest.TestCase):
    def test_failure_without_acceptance(self):
        result = audit_prearm(Path(PREARM))
        self.assertFalse(result['acceptance'])
        self.assertEqual(result['rf_jobs_charged'], 0)

    def test_rejects_missing_request_and_false_accounting(self):
        for mutation in ('request', 'accounting'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)/'evidence'; shutil.copytree(PREARM, root)
                path = root/'rf.jsonl'
                rows = [json.loads(line) for line in path.read_text().splitlines()]
                if mutation == 'request':
                    rows.remove(next(r for r in rows if r['kind'] == 'wtp_tx'))
                else:
                    result = json.loads((root/'rf-result.json').read_text())
                    result['rf_duration_ns_charged'] = 128_000_000_000
                    rows[-1]['value'] = result
                    (root/'rf-result.json').write_text(json.dumps(result))
                path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
                with self.assertRaises(ValueError):
                    audit_prearm(root)


@unittest.skipUnless(NATIVE_FAILURE, 'Private native failure packet not supplied')
class NativeFailureTests(unittest.TestCase):
    def test_failed_native_stream_is_not_capacity_acceptance(self):
        result = audit_native_failure(Path(NATIVE_FAILURE))
        self.assertFalse(result['capacity_acceptance'])
        self.assertFalse(result['native']['full_native_coverage'])
        self.assertEqual(result['native']['received_payload_bytes'], 0)

    def test_altered_incomplete_frame_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'evidence'; shutil.copytree(NATIVE_FAILURE, root)
            path = root/'production-tls.bin'
            raw = path.read_bytes()
            header = bytes.fromhex('5754504601010000000000ff8c4e21fa')
            self.assertEqual(raw.count(header), 1)
            path.write_bytes(raw.replace(header, header[:-1]+b'\x00'))
            with self.assertRaises(ValueError):
                audit_native_failure(root)


@unittest.skipUnless(IDLE_FAILURE, 'Private idle failure packet not supplied')
class IdleFailureTests(unittest.TestCase):
    def test_preserved_idle_failure(self):
        from audit_phase11_5_completion_native_guard_failure import audit as idle_audit
        result=idle_audit(Path(IDLE_FAILURE))
        self.assertFalse(result['capacity_acceptance'])
        self.assertEqual(result['rf_jobs'],0)

    def test_native_wire_corruption_is_rejected(self):
        from audit_phase11_5_completion_native_guard_failure import audit as idle_audit
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'evidence';shutil.copytree(IDLE_FAILURE,root)
            p=root/'production-tls.bin';raw=p.read_bytes()
            self.assertIn(b'"state":"loaded"',raw)
            p.write_bytes(raw.replace(b'"state":"loaded"',b'"state":"armed!"',1))
            with self.assertRaises(ValueError):idle_audit(root)


RESERVE_FAILURE = os.environ.get('PHASE115_COMPLETION_RESERVE_FAILURE')


@unittest.skipUnless(RESERVE_FAILURE, 'Private reserve failure packet not supplied')
class ReserveFailureTests(unittest.TestCase):
    def test_preserved_failure(self):
        from audit_phase11_5_completion_reserve_failure import audit as reserve_audit
        value = reserve_audit(Path(RESERVE_FAILURE))
        self.assertFalse(value['capacity_acceptance'])
        self.assertEqual(value['maximum_load_replies'], 3)
        self.assertEqual(value['allocator_headroom_bytes'], 31680 if value['cleanup_abort_sent'] else 31200)

    def test_rejects_altered_reply_peak_and_reservation(self):
        from audit_phase11_5_completion_reserve_failure import audit as reserve_audit
        for mutation in ('reply', 'peak', 'reservation'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)/'evidence'; shutil.copytree(RESERVE_FAILURE, root)
                if mutation == 'reservation':
                    p = root/'reservation-reconciled.json'; value = json.loads(p.read_text())
                    value['packet_sha256'] = '0'*64; p.write_text(json.dumps(value))
                else:
                    p = root/'idle.jsonl'; rows = [json.loads(line) for line in p.read_text().splitlines()]
                    if mutation == 'peak':
                        next(r for r in rows if r['kind']=='info')['value']['value']['allocator_peak_bytes'] = 0
                    else:
                        r = next(r for r in rows if r['kind']=='usb_rx' and r['value']['label']=='load-2')
                        raw = bytearray.fromhex(r['value']['hex']); raw[-1] ^= 1; r['value']['hex'] = raw.hex()
                    p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
                with self.assertRaises(ValueError): reserve_audit(root)




IDLE_SUCCESS = os.environ.get('PHASE115_COMPLETION_IDLE_SUCCESS')


@unittest.skipUnless(IDLE_SUCCESS, 'Private completed idle packet not supplied')
class IdleSuccessTests(unittest.TestCase):
    def test_complete_bounded_replay(self):
        from audit_phase11_5_completion_native_idle import audit as idle_audit
        value = idle_audit(Path(IDLE_SUCCESS))
        self.assertEqual(value['status'], 'IDLE_NATIVE_RETAINED_LOAD_PASS')
        self.assertEqual(len(value['load_exchange_seconds']), 4)
        self.assertFalse(value['family_closed'])
        self.assertEqual(value['heap_capacity_bytes']-value['allocator_peak_bytes'], 32800)

    def test_rejects_partial_write_missing_native_and_peak_change(self):
        from audit_phase11_5_completion_native_idle import audit as idle_audit
        for change in ('write', 'native', 'peak'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(IDLE_SUCCESS,root)
                if change == 'native':
                    path=root/'production-tls.bin';path.write_bytes(path.read_bytes()[:-32])
                else:
                    path=root/'idle.jsonl';rows=[json.loads(x) for x in path.read_text().splitlines()]
                    if change == 'write':
                        next(r for r in rows if r['kind']=='usb_write' and r['value']['label']=='fresh-id-replay')['value']['bytes']-=1
                    else:
                        next(r for r in rows if r['kind']=='info')['value']['value']['allocator_peak_bytes']+=1
                    path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
                with self.assertRaises(ValueError):idle_audit(root)

CAPACITY_CADENCE = os.environ.get('PHASE115_COMPLETION_CAPACITY_CADENCE')


@unittest.skipUnless(CAPACITY_CADENCE, 'Private capacity cadence packet not supplied')
class CapacityCadenceTests(unittest.TestCase):
    def test_component_acceptance_preserves_failure(self):
        from audit_phase11_5_completion_capacity_cadence import audit
        v=audit(Path(CAPACITY_CADENCE))
        self.assertEqual(v['accepted_components'],['2.1a','2.1d','2.1e'])
        self.assertFalse(v['package_complete']);self.assertEqual(v['http_offers'],0)
        self.assertEqual(v['headroom_bytes'],48136)

    def test_rejects_incomplete_input_false_arm_and_missing_native_bracket(self):
        from audit_phase11_5_completion_capacity_cadence import audit
        for change in ('write','arm','native'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as directory:
                root=Path(directory)/'evidence';shutil.copytree(CAPACITY_CADENCE,root)
                if change=='native':
                    path=root/'production-tls.bin';path.write_bytes(path.read_bytes()[:-32])
                else:
                    path=root/'rf.jsonl';rows=[json.loads(x) for x in path.read_text().splitlines()]
                    if change=='write':next(r for r in rows if r['kind']=='capacity_write')['value']['bytes']-=1
                    else:next(r for r in rows if r['kind']=='arm_acknowledged')['value']['job_id']='0'*32
                    path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
                with self.assertRaises(ValueError):audit(root)


if __name__ == '__main__':
    unittest.main()
