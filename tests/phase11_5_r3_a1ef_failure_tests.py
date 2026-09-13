"""Raw integration and adversarial triage; no network or hardware access."""
import copy
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_a1e_failure import audit as audit_e
from audit_phase11_5_r3_a1f_failure import audit as audit_f
from audit_phase11_5_r3_tls import pressure_bracket
from phase11_5_r3_tls_plan import BRACKET_POLICY
from diagnose_phase11_5 import diagnose
from audit_phase11_5_idle import audit as audit_usb, frames
from validate_wtp_contract import crc32c


class BracketTests(unittest.TestCase):
    def sample(self, start, finish):
        return dict(monotonic_ns=int(finish*1e9),value=dict(began_monotonic_ns=int(start*1e9)))

    def test_prospective_policy_does_not_reinterpret_frozen_packets(self):
        series=[self.sample(0,.2), self.sample(1,1.2), self.sample(2,3.7)]
        with self.assertRaisesRegex(ValueError,'Missing independent pressure bracket'):
            pressure_bracket(series,300_000_000,1_400_000_000,2_000_000_000,None)
        self.assertEqual(pressure_bracket(series,300_000_000,1_400_000_000,2_000_000_000,BRACKET_POLICY),series)

    def test_prospective_policy_rejects_late_start_and_expired_or_negative_reads(self):
        for series in ([self.sample(0,.1),self.sample(3,3.2)],
                       [self.sample(0,.1),self.sample(1,6.01)],
                       [self.sample(.2,.1),self.sample(1,1.2)]):
            with self.assertRaises(ValueError):
                pressure_bracket(series,300_000_000,400_000_000,2_000_000_000,BRACKET_POLICY)
        with self.assertRaises(ValueError):
            pressure_bracket([self.sample(0,.1),self.sample(1,1.2)],300_000_000,400_000_000,2_000_000_000,'unknown')

    def test_stale_boundary_requires_a_read_actually_in_flight(self):
        series=[self.sample(0,.1),self.sample(1,4),self.sample(4.1,4.2)]
        with self.assertRaises(ValueError):
            pressure_bracket(series,2_500_000_000,4_050_000_000,2_000_000_000,BRACKET_POLICY)
        # The long second read is within five seconds, but the delayed next
        # request still fails the independent two-second start cadence.
        self.assertEqual(len(pressure_bracket(series[:2],2_500_000_000,3_000_000_000,
                                             2_000_000_000,BRACKET_POLICY)),2)


class RawAttemptTests(unittest.TestCase):
    def mutations(self, source, audit, edits):
        original=audit(source)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'evidence';shutil.copytree(source,root)
            for name,mutate in edits:
                with self.subTest(file=name,mutation=mutate.__name__):
                    path=root/name;raw=path.read_text();path.write_text(mutate(raw))
                    with self.assertRaises((ValueError,KeyError,IndexError)):audit(root)
                    path.write_text(raw)
                    self.assertEqual(audit(root),original)
            value=diagnose(root)
            self.assertEqual(value['evidence'],'RAW_RECONSTRUCTED')
            self.assertTrue(value['assistant_tooling_defect_confirmed'])
            self.assertFalse(value['firmware_defect_confirmed'])
            self.assertFalse(value['automatic_retry_allowed'])
            self.assertEqual(value['audit_result']['accepted_assertions'],0)
        return original

    @unittest.skipUnless(os.environ.get('PHASE115_R3_A1E_EVIDENCE'),'Private A1e evidence required')
    def test_a1e_raw_causal_chain_and_partial_event_cleanup(self):
        source=Path(os.environ['PHASE115_R3_A1E_EVIDENCE']).resolve()
        value=self.mutations(source,audit_e,[
            ('retained-result.json',lambda s:s.replace('"configuration_writes": 0','"configuration_writes": 1')),
            ('wifi-recovery.json',lambda s:s.replace('"off": 1','"off": 2')),
            ('wifi-off-exchange.jsonl',lambda s:s.replace('57494649204f46460a','57494649204f4e0a')),
            ('tls-a1/pressure.jsonl',lambda s:s.replace('"alert": 116','"alert": 48')),
            ('tls-a1/pressure.jsonl',lambda s:s.rstrip('\n')),
            ('tls-a1/usb-health.jsonl',lambda s:s.replace('"state": "complete"','"state": "failed"')),
            ('tls-a1/load-events.jsonl',lambda s:s.replace('interrupted 15','unrelated error')),
            ('final-terminal-release.jsonl',lambda s:s.replace('"op": "RELEASE"','"op": "ABORT"')),
            ('final-terminal-release.jsonl',lambda s:s.rstrip('\n')),
            ('after-b.stdout',lambda s:s.replace('feffcd075ab6cb0b74e7e0c2fde6c87f','f'*32)),
            ('fixture-state.json',lambda s:s.replace('"restored": true','"restored": false')),
        ])
        self.assertEqual(value['completed_jobs'],1)
        self.assertEqual(value['causal_timing']['replacement_info_roundtrip_ns'],1739071744)
        self.assertEqual(value['observer_samples'],dict(info=360,status=72,health=72))

    @unittest.skipUnless(os.environ.get('PHASE115_R3_A1F_EVIDENCE'),'Private A1f evidence required')
    def test_a1f_integrates_raw_observer_production_and_all_pressure_cases(self):
        source=Path(os.environ['PHASE115_R3_A1F_EVIDENCE']).resolve()
        value=self.mutations(source,audit_f,[
            ('retained-result.json',lambda s:s.replace('"status": "FAILED"','"status": "PASS"')),
            ('tls-a1/result.json',lambda s:s.replace('"pressure_exit": 0','"pressure_exit": 1')),
            ('tls-a1/result.json',lambda s:s.replace('"status":','"result":')),
            ('tls-a1/pressure.jsonl',lambda s:s.replace('"peer_sha256": "0649','"peer_sha256": "1649')),
            ('tls-a1/pressure.jsonl',lambda s:s.replace('"connections": 12','"connections": 11')),
            ('tls-a1/usb-health.jsonl',lambda s:s.replace('"event_id": "15"','"event_id": "16"')),
            ('tls-a1/usb-health.jsonl',lambda s:s.replace('"state": "complete"','"state": "failed"')),
            ('tls-a1/load-events.jsonl',lambda s:s.replace('"failures": []','"failures": ["injected"]')),
            ('final-terminal-before.stdout',lambda s:s.replace('"output_active": false','"output_active": true')),
            ('r3-a1-admission.stdout',lambda s:s.replace('"revision": "2e43110f0530"','"revision": "changed"')),
            ('fixture.jsonl',lambda s:s.replace('"failures": []','"failures": ["injected"]')),
        ])
        self.assertEqual(value['completed_jobs'],2)
        self.assertEqual(value['physical_finite_gates']['status'],'PASS')
        self.assertEqual(len(value['pressure_diagnostic']['cases']),10)
        self.assertEqual(value['pressure_diagnostic']['status'],'DIAGNOSTIC_ONLY')
        self.assertEqual(value['frozen_observation_misses'][0]['following_lag_ns'],2262550925)

    @unittest.skipUnless(os.environ.get('PHASE115_R3_A1F_EVIDENCE'),'Private A1f evidence required')
    def test_nonzero_event_origin_still_rejects_a_real_gap_in_valid_crc_frames(self):
        root=Path(os.environ['PHASE115_R3_A1F_EVIDENCE']).resolve()
        path=root/'tls-a1/usb-health.jsonl'; baseline=root/'r3-a1-admission.stdout'
        packet=json.loads((root/'tls-a1/jobs.json').read_text())
        self.assertTrue(audit_usb(path,baseline,packet)['raw_wire_verified'])
        trace=[json.loads(s) for s in path.read_text().splitlines()]
        chunks=[r for r in trace if r['kind']=='wtp_rx']
        raw=b''.join(bytes.fromhex(r['value']['hex']) for r in chunks)
        # Replace exactly one two-digit event ID and rebuild its CRC while
        # preserving every original USB chunk boundary and summary.
        output=b'';offset=0;changed=0
        while offset<len(raw):
            length=struct.unpack('>I',raw[offset+8:offset+12])[0]
            body=raw[offset+16:offset+16+length]; message=json.loads(body)
            if message.get('event_id')=='15':
                replacement=body.replace(b'"event_id":"15"',b'"event_id":"16"')
                self.assertNotEqual(body,replacement);body=replacement;changed+=1
            output+=raw[offset:offset+12]+struct.pack('>I',crc32c(body))+body
            offset+=16+length
        self.assertEqual(changed,1);self.assertEqual(len(output),len(raw))
        self.assertFalse(frames(output)[1])
        offset=0
        for row in chunks:
            size=len(bytes.fromhex(row['value']['hex']));row['value']['hex']=output[offset:offset+size].hex();offset+=size
        for row in trace:
            if row['kind']=='wtp_message' and row['value'].get('event_id')=='15':row['value']['event_id']='16'
        with tempfile.TemporaryDirectory() as temp:
            altered=Path(temp)/'usb.jsonl';altered.write_text(''.join(json.dumps(r)+'\n' for r in trace))
            with self.assertRaisesRegex(ValueError,'RF event identity/gap'):
                audit_usb(altered,baseline,packet)


if __name__=='__main__':unittest.main()
