"""Real advertised boundary encodings, CRC and integral RF sample arithmetic."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase11_5_r3_capacity_plan import maximum_job, wtp_capacity_frame, http_capacity_body, browser_capacity_file
from validate_wtp_contract import crc32c, SchemaValidator
from validate_wtp_contract import frame
from phase11_5_pilot import Decoder

DRIVER=Path(os.environ.get('PHASE115_ENDPOINT_DRIVER','build-host/endpoint_driver'))


class CapacityTests(unittest.TestCase):
    def test_maximum_job_reaches_both_advertised_limits_with_integral_samples(self):
        job = maximum_job('1' * 32)
        self.assertEqual(len(job['events']), 162)
        self.assertEqual(int(job['total_duration_ns']), 110592000000)
        self.assertEqual(sum(int(v['duration_ns']) for v in job['events']), 110592000000)
        end = 0
        for event in job['events']:
            self.assertEqual(int(event['offset_ns']), end)
            self.assertEqual(int(event['duration_ns']) * 138000000 % 1000000000, 0)
            self.assertEqual(int(event['frequency_nhz']), 135500000000000)
            end += int(event['duration_ns'])
        self.assertNotEqual(job['job_id'], maximum_job('2' * 32)['job_id'])

    def test_maximum_and_one_over_frames_have_truthful_lengths_and_crc(self):
        schema = json.loads((Path(__file__).resolve().parents[1] / 'docs/protocol/wtp-1.schema.json').read_text())
        validator = SchemaValidator(schema)
        for oversized, size in ((False, 65536), (True, 65537)):
            raw = wtp_capacity_frame('1' * 32, '2' * 32, oversized)
            magic, version, encoding, flags, length, crc = struct.unpack('!4sBBHII', raw[:16])
            self.assertEqual((magic, version, encoding, flags, length), (b'WTPF', 1, 1, 0, size))
            self.assertEqual(len(raw), size + 16)
            self.assertEqual(crc32c(raw[16:]), crc)
            self.assertFalse(validator.errors(json.loads(raw[16:]), schema))

    def test_http_capacity_uses_an_actually_supported_non_rf_operation(self):
        for oversized, size in ((False, 32768), (True, 32769)):
            raw = http_capacity_body('1' * 32, '2' * 32, oversized)
            self.assertEqual(len(raw), size)
            self.assertEqual(json.loads(raw)['operation'], 'HELLO')

    def test_browser_file_sizes_are_real_utf8_bytes(self):
        job = maximum_job('1' * 32)
        for oversized, size in ((False, 30000), (True, 30001)):
            raw = browser_capacity_file(job, oversized)
            self.assertEqual(len(raw), size)
            self.assertEqual(json.loads(raw), job)

    @unittest.skipUnless(DRIVER.is_file(), 'Compiled endpoint unavailable')
    def test_actual_endpoint_maximum_rejection_and_same_connection_recovery(self):
        with subprocess.Popen([str(DRIVER)], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, text=True) as process:
            def control(**value):
                process.stdin.write(json.dumps(value) + '\n'); process.stdin.flush()
                result = json.loads(process.stdout.readline())
                self.assertFalse(result['closed'])
                self.assertEqual(result['pending'], 0)
                return Decoder().feed(bytes.fromhex(result['hex']))
            def request(op, n, body):
                return dict(type='request', protocol='WTP/1', session_id='1'*32,
                            request_id=f'{n:032x}', op=op, body=body)
            def send(raw):
                # The driver's control JSON has its own bounded parser. Feed
                # transport chunks so its wrapper does not reject the test.
                replies = []
                for offset in range(0, len(raw), 4096):
                    replies.extend(control(action='send', hex=raw[offset:offset+4096].hex()))
                return replies
            control(action='connect', principal='usb-physical')
            hello = request('HELLO', 2, dict(versions=['WTP/1'], client_name='capacity', client_version='1'))
            self.assertTrue(send(frame(json.dumps(hello).encode()))[0]['ok'])
            status = send(wtp_capacity_frame('1'*32, '3'*32))
            self.assertEqual(len(status), 1)
            self.assertTrue(status[0]['ok'])
            self.assertEqual(status[0]['body']['state'], 'empty')
            ping = request('PING', 4, {'token': 'C0-after-oversize'})
            raw = wtp_capacity_frame('1'*32, '5'*32, True) + frame(json.dumps(ping).encode())
            result = send(raw)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]['event'], 'INVALID_FRAME')
            self.assertEqual(result[1]['request_id'], ping['request_id'])
            self.assertTrue(result[1]['ok'])
            self.assertEqual(result[1]['body'], ping['body'])
            process.stdin.close()
            self.assertEqual(process.wait(timeout=5), 0)


if __name__ == '__main__':
    unittest.main()
