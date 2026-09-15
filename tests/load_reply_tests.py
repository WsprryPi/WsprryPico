"""Exact C7 request, production endpoint/service/planner, modeled reply pressure."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_wtp_contract import frame, SchemaValidator, load_json
from wtp_monitor import FrameDecoder

# Reconstructed protocol data; no captured credentials or device access.
# Compared byte-for-byte with C7 rf.jsonl wtp_tx.hex during Component 4.
def c7_frame():
    body = dict(job_id='8d8734400ddd2d472799f3d08a92e6b5', profile='rf-events/1',
                mode='fskcw', total_duration_ns='128000000000',
                allow_frequency_adjustment=True,
                events=[dict(offset_ns=str(i * 250000000), duration_ns='250000000',
                             rf_on=True, frequency_nhz=str(135500000000000 if i % 2 == 0 else 135495000000000))
                        for i in range(512)])
    q = dict(type='request', protocol='WTP/1', session_id='d2f0af9141101f9a5c0d61e7cdee7983',
             request_id='7082c6ffbb9d466eac3cfc636ba6538a', op='LOAD', body=body)
    result = frame(json.dumps(q, separators=(',', ':')).encode())
    assert len(result) == 52105
    assert hashlib.sha256(result).hexdigest() == 'e5b48b92dd2abd74e670f2b2aed3d660c9b357bd4857be6b64b8affedbcee670'
    return result

DRIVER = sys.argv[1] if len(sys.argv) > 1 else None
class LoadReplyTests(unittest.TestCase):
    def run_model(self, background, replay=False, maximum_status=False):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'c7.bin'
            path.write_bytes(c7_frame())
            run = subprocess.run([DRIVER, str(path), str(background)] + (["maximum-status"] if maximum_status else ["replay"] if replay else []), capture_output=True,
                                 text=True, check=True, timeout=30)
        result = json.loads(run.stdout)
        self.assertEqual(result['state'], 'loaded')
        self.assertEqual(result['starts'], 0)
        return result

    def test_exact_reply_with_retained_job_and_tls_cost(self):
        replies = []
        for background in [0, 18168, 31384, 80000]:
            with self.subTest(background=background):
                r = self.run_model(background)
                self.assertFalse(r['closed'])
                decoded = FrameDecoder()
                payloads = decoded.feed(bytes.fromhex(r['hex']))
                self.assertFalse(decoded.buffer)
                schema = load_json(ROOT / 'docs/protocol/wtp-1.schema.json')
                messages = [json.loads(v) for v in payloads]
                for message in messages:
                    self.assertFalse(SchemaValidator(schema).errors(message, schema))
                response, = [m for m in messages if m['type'] == 'response']
                self.assertTrue(response['ok'])
                self.assertEqual(response['request_id'], '7082c6ffbb9d466eac3cfc636ba6538a')
                self.assertEqual(response['body']['job_id'], '8d8734400ddd2d472799f3d08a92e6b5')
                adjustments = response['body']['adjustments']
                self.assertEqual(len(adjustments), 512)
                for i, a in enumerate(adjustments):
                    self.assertEqual(a, dict(event_index=i,
                        requested_frequency_nhz=str(135500000000000 if i % 2 == 0 else 135495000000000),
                        realized_frequency_nhz=str(135500002652407 if i % 2 == 0 else 135494990274310)))
                reply, = [p for p in payloads if json.loads(p)['type'] == 'response']
                self.assertEqual(len(reply), 54916)
                self.assertGreaterEqual(r['samples'][0]['available'], 6144 + 32768)
                self.assertGreaterEqual(r['samples'][1]['available'], 1024 + 32768)
                replies.append(reply)
        self.assertEqual(len(replies), 4)
        self.assertEqual(replies[0], replies[1])
        self.assertEqual(replies[0], replies[2])

    def test_whole_replay_lifetime_reserve_and_responses(self):
        # 5,751 is fixed from the pre-fix host peak (184,673) versus the
        # measured target peak (190,424). It includes TLS/platform differences;
        # do not add TLS again or treat this calibration as target prediction.
        for background in [0, 5751, 31384]:
            with self.subTest(background=background):
                r = self.run_model(background, replay=True)
                self.assertEqual(r['terminal_records'], 1)
                self.assertEqual(r['preparations'], 2)  # E6 and primary only.
                responses = []
                for index, exchange in enumerate(r['exchanges']):
                    self.assertFalse(exchange['closed'])
                    self.assertEqual(exchange['after_pages'], 0)
                    self.assertEqual(exchange['peak_bytes'], exchange['peak_cpp'] + exchange['peak_pages'])
                    self.assertGreaterEqual(219712 - background - exchange['peak_bytes'], 32768)
                    decoder = FrameDecoder()
                    payloads = decoder.feed(bytes.fromhex(exchange['hex']))
                    self.assertFalse(decoder.buffer)
                    schema = load_json(ROOT / 'docs/protocol/wtp-1.schema.json')
                    messages = [json.loads(p) for p in payloads]
                    for message in messages:
                        self.assertFalse(SchemaValidator(schema).errors(message, schema))
                    response, = [m for m in messages if m['type'] == 'response']
                    self.assertTrue(response['ok'])
                    self.assertEqual(response['request_id'], 'a56745738e684a8094fc0cc3d29bd089' if index == 2 else '7082c6ffbb9d466eac3cfc636ba6538a')
                    self.assertEqual(response['body']['job_id'], '8d8734400ddd2d472799f3d08a92e6b5')
                    self.assertEqual(response['body']['state'], 'loaded')
                    self.assertEqual(response['body']['adjustments'], [dict(event_index=i,
                        requested_frequency_nhz=str(135500000000000 if i % 2 == 0 else 135495000000000),
                        realized_frequency_nhz=str(135500002652407 if i % 2 == 0 else 135494990274310)) for i in range(512)])
                    reply, = [p for p in payloads if json.loads(p)['type'] == 'response']
                    self.assertEqual(len(reply), 54916)
                    responses.append(response)
                self.assertEqual(len(responses), 3)
                self.assertEqual(responses[0], responses[1])
                self.assertEqual(responses[0]['body'], responses[2]['body'])

    def test_maximum_status_with_loaded_job_and_terminal_retention(self):
        # Count the complete 65,536-byte input beside actual service/planner
        # allocations. Fixed modeled background; no target-equivalence claim.
        for background in (0, 5751, 18168):
            r = self.run_model(background, maximum_status=True)
            self.assertEqual(r['preparations'], 2)
            responses = []
            for exchange in r['exchanges']:
                self.assertFalse(exchange['closed'])
                self.assertEqual(exchange['wait_ms'], 0)
                self.assertEqual(exchange['after_pages'], 0)
                self.assertGreaterEqual(219712-background-exchange['peak_bytes'], 32768)
                decoder = FrameDecoder()
                messages = [json.loads(p) for p in decoder.feed(bytes.fromhex(exchange['hex']))]
                self.assertFalse(decoder.buffer)
                schema = load_json(ROOT / 'docs/protocol/wtp-1.schema.json')
                for message in messages:
                    self.assertFalse(SchemaValidator(schema).errors(message, schema))
                response, = [m for m in messages if m['type']=='response']
                self.assertTrue(response['ok'])
                responses.append(response)
            self.assertEqual(responses[1], responses[2])
            status = responses[1]
            self.assertEqual(status['op'], 'STATUS')
            self.assertEqual(status['request_id'], '8'*32)
            self.assertEqual(status['body']['state'], 'loaded')
            self.assertFalse(status['body']['output_active'])
            self.assertEqual(status['body']['job_id'], '8d8734400ddd2d472799f3d08a92e6b5')
            self.assertEqual(len(status['body']['terminal_records']), 1)
        refused = self.run_model(31384, maximum_status=True)
        self.assertTrue(refused['exchanges'][1]['closed'])
        self.assertEqual(refused['exchanges'][1]['wait_ms'], 5000)
        self.assertGreaterEqual(219712-31384-refused['exchanges'][1]['peak_bytes'], 32768)

    def test_uncalibrated_tls_sensitivity_preserves_refusal(self):
        # 31,384 now passes above because replay no longer duplicates events.
        # A separately declared 48,000-byte background still cannot admit even
        # the smaller workspace. Preserve the same reserve and five-second limit.
        r = self.run_model(48000, replay=True)
        self.assertFalse(r['exchanges'][0]['closed'])
        self.assertTrue(r['exchanges'][1]['closed'])
        self.assertEqual(r['exchanges'][1]['hex'], '')
        self.assertEqual(r['exchanges'][1]['after_pages'], 0)
        self.assertEqual(r['exchanges'][1]['wait_ms'], 5000)
        self.assertEqual(r['preparations'], 2)
        self.assertGreaterEqual(219712 - 48000 - r['exchanges'][1]['peak_bytes'], 32768)

    def test_reply_reserve_refusal_preserves_inactive_loaded_job(self):
        r = self.run_model(140000)
        self.assertTrue(r['closed'])
        self.assertEqual(r['hex'], '')
        self.assertEqual(len(r['samples']), 1)
        self.assertLess(r['samples'][0]['available'], 54916 + 1024 + 32768)

if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
