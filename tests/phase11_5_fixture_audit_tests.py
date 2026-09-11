#!/usr/bin/env python3
import json
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_network_fixture import payload
from validate_wtp_contract import frame


class FrameAuditTests(unittest.TestCase):
    def test_valid_and_corrupted_capture(self):
        message={'type':'request','protocol':'WTP/1','session_id':'a'*32,
                 'request_id':'b'*32,'op':'PING','body':{}}
        data=frame(json.dumps(message,separators=(',',':')).encode())
        self.assertEqual(payload(data),message)
        corrupt=bytearray(data);corrupt[-1]^=1
        for changed in (data[:15],data[:-1],data+b'\0',b'NOPE'+data[4:],bytes(corrupt),
                        data[:8]+struct.pack('>I',65537)+data[12:]):
            with self.subTest(size=len(changed)),self.assertRaises(ValueError):payload(changed)


if __name__=='__main__':unittest.main()
