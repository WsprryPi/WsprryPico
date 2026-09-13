"""Failure attribution must follow raw evidence, never an exception's wording."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from diagnose_phase11_5 import diagnose, readiness, authorization_diagnosis


class DiagnosisTests(unittest.TestCase):
    def test_unknown_failure_message_does_not_blame_firmware_or_ai(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'packet.json').write_text('{}')
            (root/'result.json').write_text(json.dumps(dict(status='FAILED',error='Firmware DMA fault caused by AI timeout')))
            value = diagnose(root)
            self.assertEqual(value['fault_domain'], 'UNDETERMINED')
            self.assertIsNone(value['completed_rf_jobs'])
            self.assertEqual(value['authoritative_final_output'], 'UNKNOWN')
            self.assertFalse(value['firmware_defect_confirmed'])
            self.assertFalse(value['assistant_tooling_defect_confirmed'])
            self.assertFalse(value['automatic_retry_allowed'])

    def test_readiness_reports_which_prerequisite_not_unproven_cause(self):
        sample = dict(monotonic_ns=100, enabled=True, link_status=-3, ipv4='',clock_state='unsynchronized')
        value = readiness([sample, sample|dict(monotonic_ns=200)])
        self.assertEqual(value['gate'], 'WIFI_AUTHENTICATION_NOT_ESTABLISHED')
        self.assertFalse(value['firmware_contract_violation'])
        cases = [(dict(enabled=False), 'WIFI_DISABLED'),
                 (dict(link_status=-2), 'NETWORK_ADDRESS_NOT_ESTABLISHED'),
                 (dict(link_status=3,ipv4='10.77.15.10'), 'CLOCK_NOT_SYNCHRONIZED'),
                 (dict(link_status=3,ipv4='10.77.15.10',clock_state='synchronized'), 'READY_AT_LAST_SAMPLE')]
        for change, expected in cases:
            self.assertEqual(readiness([sample|change])['gate'],expected)
        with self.assertRaises(ValueError):readiness([sample,sample|dict(monotonic_ns=0)])

    def test_automatic_review_is_not_a_user_refusal_or_hardware_failure(self):
        record=dict(source='automatic_approval_review',decision='rejected',action_executed=False,
                    user_declined=False,reason='Added idle Wi-Fi OFF/ON action requires explicit approval.')
        value=authorization_diagnosis(record)
        self.assertEqual(value['execution'],'NOT_STARTED')
        self.assertEqual(value['fault_domain'],'AUTHORIZATION')
        self.assertFalse(value['assistant_tooling_defect_confirmed'])
        with self.assertRaises(ValueError):authorization_diagnosis(record|dict(user_declined=True))

    @unittest.skipUnless(all(os.environ.get(k) for k in ('PHASE115_R3_FAILURE_EVIDENCE',
        'PHASE115_R3_A1B_EVIDENCE','PHASE115_R3_A1C_EVIDENCE')), 'Three private attempt archives required')
    def test_known_attempts_keep_completed_work_and_distinguish_fault_domains(self):
        a=diagnose(Path(os.environ['PHASE115_R3_FAILURE_EVIDENCE']))
        b=diagnose(Path(os.environ['PHASE115_R3_A1B_EVIDENCE']))
        c=diagnose(Path(os.environ['PHASE115_R3_A1C_EVIDENCE']))
        for value in (a,b,c):
            self.assertEqual(value['evidence'],'RAW_RECONSTRUCTED')
            self.assertFalse(value['firmware_defect_confirmed'])
            self.assertFalse(value['automatic_retry_allowed'])
        self.assertTrue(a['assistant_tooling_defect_confirmed'])
        self.assertTrue(b['assistant_tooling_defect_confirmed'])
        self.assertEqual((a['completed_rf_jobs'],b['completed_rf_jobs'],c['completed_rf_jobs']),(0,1,0))
        self.assertFalse(c['assistant_tooling_defect_confirmed'])
        self.assertEqual(c['root_cause'],'UNDETERMINED')
        self.assertEqual(c['readiness']['gate'],'WIFI_AUTHENTICATION_NOT_ESTABLISHED')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'evidence';shutil.copytree(Path(os.environ['PHASE115_R3_A1C_EVIDENCE']),root)
            path=root/'network-ready-24.stdout';path.write_text(path.read_text().replace('"output_active": false','"output_active": true'))
            damaged=diagnose(root)
            self.assertNotEqual(damaged['evidence'],'RAW_RECONSTRUCTED')
            self.assertEqual(damaged['authoritative_final_output'],'UNKNOWN')
            self.assertFalse(damaged['firmware_defect_confirmed'])
            self.assertFalse(damaged['assistant_tooling_defect_confirmed'])


if __name__ == '__main__':unittest.main()
