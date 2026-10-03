#!/usr/bin/env python3
"""Actual framed response correlation and final authority fail-closure."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import phase12_authority_capture as c
from validate_wtp_contract import frame


class Stream:
    def __init__(self,wrong=None):self.pending=b'';self.requests=[];self.wrong=wrong
    def settimeout(self,value):pass
    def sendall(self,wire):
        request=json.loads(wire[16:]);self.requests.append(request)
        body=dict(device_id=c.DEVICE,boot_id='a'*32,selected_version='WTP/1') if request['op']=='HELLO' else dict(
            boot_id='a'*32,owner_id=None,job_id=None,state='empty',output_active=False)
        if self.wrong=='owned' and request['op']=='STATUS':body['owner_id']='b'*32
        response=dict(type='response',protocol='WTP/1',session_id=request['session_id'],
            request_id=request['request_id'],op=request['op'],ok=True,body=body)
        if self.wrong=='correlation':response['request_id']='c'*32
        self.pending=frame(json.dumps(response).encode())
        if self.wrong=='crc':self.pending=self.pending[:-1]+bytes([self.pending[-1]^1])
    def recv(self,size):
        result,self.pending=self.pending[:size],self.pending[size:];return result


class Tests(unittest.TestCase):
    def test_two_raw_readonly_exchanges(self):
        stream=Stream();value=c.capture(stream,'a'*32,lambda:7201,'plain_lan')
        self.assertEqual([r['op'] for r in stream.requests],['HELLO','STATUS'])
        self.assertEqual(len(value['exchanges']),2)
        self.assertTrue(all(e['request_hex'].startswith('57545046') for e in value['exchanges']))
    def test_corrupt_uncorrelated_or_owned_reply_fails_without_retry(self):
        for wrong in ('crc','correlation','owned'):
            stream=Stream(wrong)
            with self.assertRaises(ValueError):c.capture(stream,'a'*32,lambda:7201,'plain_lan')
            self.assertLessEqual(len(stream.requests),2)


if __name__=='__main__':unittest.main()
