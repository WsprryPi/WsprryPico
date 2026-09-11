#!/usr/bin/env python3
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_browser_jobs import checked_reply,main


class BrowserJobsTests(unittest.TestCase):
    def test_claim_response_requires_matching_owner_and_request(self):
        request=dict(session_id='a'*32,request_id='b'*32,operation='CLAIM',body=dict(owner_id='c'*32))
        reply=dict(ok=True,request_id='b'*32,result=dict(owner_id='c'*32,
                   granted_lease_ms=60000,expires_monotonic_ns='123456789'))
        checked_reply(request,200,json.dumps(reply).encode())
        for field,value in [('request_id','d'*32),('ok',False),('extra',True)]:
            bad=dict(reply,**{field:value})
            with self.subTest(field=field),self.assertRaises(ValueError):
                checked_reply(request,200,json.dumps(bad).encode())
        bad=copy.deepcopy(reply);bad['result']['owner_id']='d'*32
        with self.assertRaises(ValueError):checked_reply(request,200,json.dumps(bad).encode())
        with self.assertRaises(ValueError):checked_reply(request,409,json.dumps(reply).encode())

    def test_no_run_has_no_device_or_file_access(self):
        with patch.object(sys,'argv',['actor','--root','/absent']), \
             patch.object(Path,'resolve',side_effect=AssertionError('file accessed')):
            main()


if __name__=='__main__':unittest.main()
