import json
from unittest import TestCase,main
from network_replies import ReplyCollector, StrictFrameDecoder
from validate_wtp_contract import frame
SESSION='1'*32
REQUEST='a'*32
BOOT='2'*32
HELLO={'type':'response','protocol':'WTP/1','session_id':SESSION,'request_id':REQUEST,'op':'HELLO','ok':True,'body':{'selected_version':'WTP/1','device_id':'3'*32,'boot_id':BOOT,'product':'test','firmware_version':'test'}}
def wire(value):return json.dumps(value).encode()
def event(identifier='0',**changes):return {'type':'event','protocol':'WTP/1','session_id':SESSION,'boot_id':BOOT,'event_id':identifier,'event':'JOB_STATE','body':{'job_id':'4'*32,'state':'loaded','output_active':False},**changes}
class Replies(TestCase):
    def bound(self):
        c=ReplyCollector(SESSION);self.assertEqual(c.accept([wire(HELLO)],REQUEST,'HELLO'),HELLO);return c
    def test_valid_advisory_and_reply_can_share_one_read(self):
        c=self.bound();self.assertEqual(c.accept([wire(event()),wire(HELLO)],REQUEST,'HELLO'),HELLO);self.assertEqual(c.last_event,0);self.assertFalse(c.gap)
    def test_events_can_precede_a_later_reply_without_fabricating_completion(self):
        c=self.bound();self.assertIsNone(c.accept([wire(event())],REQUEST,'HELLO'));self.assertEqual(c.accept([wire(HELLO)],REQUEST,'HELLO'),HELLO)
    def test_wrong_request_session_and_operation_are_refused(self):
        for field,value in [('request_id','b'*32),('session_id','5'*32),('op','STATUS')]:
            with self.subTest(field=field),self.assertRaises(ValueError):self.bound().accept([wire({**HELLO,field:value})],REQUEST,'HELLO')
    def test_duplicate_response_cannot_be_discarded_after_first_success(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.bound().accept([wire(HELLO),wire(HELLO)],REQUEST,'HELLO')
    def test_event_binding_and_replay_are_refused(self):
        for changed in [event(boot_id='6'*32),event(session_id='7'*32)]:
            with self.assertRaisesRegex(ValueError,'binding'):self.bound().accept([wire(changed)],REQUEST,'HELLO')
        c=self.bound();c.accept([wire(event())],REQUEST,'HELLO')
        with self.assertRaisesRegex(ValueError,'Stale'):c.accept([wire(event())],REQUEST,'HELLO')
    def test_advisory_gaps_require_explicit_status_authority(self):
        c=self.bound();c.accept([wire(event('2'))],REQUEST,'HELLO');self.assertTrue(c.gap)
    def test_malformed_unknown_and_extra_event_fields_fail_before_consumption(self):
        for changed in [event(event='UNKNOWN'),event(extra=True),event(body={'state':'loaded'}),event(protocol='WTP/0')]:
            with self.subTest(message=changed),self.assertRaises(ValueError):self.bound().accept([wire(changed)],REQUEST,'HELLO')
    def test_duplicate_json_keys_are_refused(self):
        with self.assertRaises(ValueError):self.bound().accept([b'{"type":"event","type":"response"}'],REQUEST,'HELLO')

class Framing(TestCase):
    def test_partial_header_and_payload_preserve_exact_bytes(self):
        decoder=StrictFrameDecoder();payload=wire(HELLO);encoded=frame(payload);observed=[]
        for byte in encoded:observed.extend(decoder.feed(bytes([byte])))
        self.assertEqual(observed,[payload]);self.assertEqual(decoder.buffer,b'')
    def test_multiple_frames_remain_visible_to_duplicate_response_checks(self):
        payload=wire(HELLO);self.assertEqual(StrictFrameDecoder().feed(frame(payload)*2),[payload,payload])
    def test_bad_prefix_header_and_checksum_are_not_resynchronized(self):
        encoded=frame(wire(HELLO))
        damaged=bytearray(encoded);damaged[-1]^=1
        wrong_version=bytearray(encoded);wrong_version[4]=2
        for data in [b'junk'+encoded,bytes(damaged)+encoded,bytes(wrong_version)+encoded]:
            with self.subTest(data=data[:16]),self.assertRaises(ValueError):StrictFrameDecoder().feed(data)
    def test_payload_and_input_bounds_are_enforced(self):
        payload=b'x'*65536;decoder=StrictFrameDecoder()
        self.assertEqual(decoder.feed(frame(payload)),[payload])
        with self.assertRaises(ValueError):StrictFrameDecoder().feed(b'x'*65553)

if __name__=='__main__':main()
