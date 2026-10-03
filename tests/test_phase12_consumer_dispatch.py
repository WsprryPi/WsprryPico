#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import tempfile
import unittest
import json,hashlib
from unittest.mock import patch
import phase12_consumer_dispatch as dispatch

class Timeline:
    def __init__(self,path): self.rows=[]; self.closed=False
    def record(self,kind,**value): self.rows.append((kind,value))
    def close(self): self.closed=True

class Tests(unittest.TestCase):
    def test_finite_image_names_source_hash_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);candidate=dict(role='restore',fault_stage=0,session_deadline_fixture=False,target='WsprryPico',revision='b'*12,lan_mode='plain',gp14=False,uf2={'sha256':hashlib.sha256(b'exercise').hexdigest()})
            manifest=dict(source_commit='b'*40,candidates=[candidate]);raw=json.dumps(manifest).encode();(root/'manifest.json').write_bytes(raw)
            plan=dict(source_commit='b'*40,image_sha256=candidate['uf2']['sha256'],device_id=dispatch.DEVICE)
            (root/'composition-plan.json').write_text(json.dumps(plan));(root/'exercise.uf2').write_bytes(b'exercise');(root/'restore.uf2').write_bytes(b'original')
            request=dict(image_name='exercise.uf2',manifest_sha256=hashlib.sha256(raw).hexdigest())
            with patch.object(dispatch,'validate_uf2'):
                actual=dispatch.bound_inputs(root,request);self.assertEqual(actual[0]['source_commit'],'b'*40)
                for bad in ('../exercise.uf2','/tmp/exercise.uf2','fault_1.uf2','arbitrary.uf2'):
                    with self.assertRaises(ValueError):dispatch.bound_inputs(root,dict(request,image_name=bad))
                with self.assertRaises(ValueError):dispatch.bound_inputs(root,dict(request,image_name='restore.uf2'))
                plan['source_commit']='a'*40;(root/'composition-plan.json').write_text(json.dumps(plan))
                with self.assertRaises(ValueError):dispatch.bound_inputs(root,request)
    def exercise(self, fail=False, slow=False):
        now=[100]; calls=[]; timeline=Timeline(None)
        def sleep(seconds): now[0]+=seconds
        def driver(path):
            calls.append((now[0]-100,path.name));path.write_bytes(b'actual fixture log')
            if fail: raise TimeoutError('uncertain no retry')
            now[0]+=601 if slow else 60
        with tempfile.TemporaryDirectory() as root:
            def run():
                return dispatch.directed_waves(Path(root),driver,100,clock=lambda:now[0],
                    sleeper=sleep,timeline_factory=lambda _:timeline)
            if fail or slow:
                with self.assertRaises((TimeoutError,ValueError)): run()
            else: self.assertEqual(run(),2)
        return calls,timeline
    def test_fixed_offsets_separate_logs_and_quiet_windows(self):
        calls,timeline=self.exercise()
        self.assertEqual(calls,[(0,'directed-wave-1-wire.jsonl'),(2400,'directed-wave-2-wire.jsonl')])
        self.assertTrue(timeline.closed)
        self.assertEqual(sum(kind=='wave_complete' for kind,_ in timeline.rows),2)
        self.assertTrue(all(len(row['wire_sha256'])==64 for kind,row in timeline.rows if kind=='wave_complete'))
    def test_failure_stops_without_replay_or_second_wave(self):
        calls,timeline=self.exercise(fail=True)
        self.assertEqual(len(calls),1)
        self.assertEqual(timeline.rows[-1][0],'wave_failed')
        self.assertFalse(timeline.rows[-1][1]['retry'])
    def test_overlong_wave_stops_before_quiet_window(self):
        calls,timeline=self.exercise(slow=True)
        self.assertEqual(len(calls),1)
        self.assertEqual(timeline.rows[-1][0],'wave_failed')

if __name__=='__main__':unittest.main()
