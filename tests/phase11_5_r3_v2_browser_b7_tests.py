"""Frozen failed B7 evidence: scope preservation and adversarial rejection."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_phase11_5_r3_v2_browser_b7 import audit
from audit_phase11_5_r3_v2_browser_observer import audit as strict_observer

SOURCE=Path(__file__).resolve().parents[1]/'build/phase11-5-r3-v2-browser-b7/evidence'

@unittest.skipUnless(SOURCE.exists(),'Private B7 evidence required')
class B7EvidenceTests(unittest.TestCase):
    def test_intact_original_failure_and_mutations(self):
        expected=audit(SOURCE)
        self.assertFalse(expected['cancellation_verified'])
        self.assertFalse(expected['full_observation_verified'])
        with self.assertRaises(ValueError):
            strict_observer(SOURCE,json.loads((SOURCE/'packet.json').read_text()))
        def edit(root,file,kind,fn):
            p=root/file;rows=[json.loads(line) for line in p.read_text().splitlines()]
            fn(next(r for r in rows if r['kind']==kind));p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        changes=[
            lambda r:(r/'case-3-before-abort.png').write_bytes(b''),
            lambda r:(r/'job-30000.json').write_bytes(b'{}'),
            lambda r:(r/'final-a.stdout').write_text(''),
            lambda r:(r/'observer-failed.json').write_text('{}'),
            lambda r:(r/'browser-result.json').write_text('{}'),
            lambda r:(r/'browser-binding.json').write_text('{}'),
            lambda r:edit(r,'browser.jsonl','arm_charge',lambda x:x['value'].update(duration_ns='1')),
            lambda r:edit(r,'browser.jsonl','peer_certificate',lambda x:x['value'].update(sha256='0'*64)),
            lambda r:edit(r,'browser.jsonl','network_body',lambda x:x['value']['body'].update(body='{}',base64Encoded=False)),
            lambda r:edit(r,'browser.jsonl','request_guard',lambda x:x['value']['request'].update(url='https://other.invalid/')),
            lambda r:edit(r,'browser-observer.jsonl','failure',lambda x:x['value'].update(error='firmware failed')),
            lambda r:edit(r,'browser-observer.jsonl','info',lambda x:x['value']['value']['status'].update(boot_id='0'*32)),
            lambda r:(r/'browser.jsonl').write_bytes((r/'browser.jsonl').read_bytes()[:-1]),
        ]
        for n,change in enumerate(changes):
            with self.subTest(mutation=n),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)/'evidence';shutil.copytree(SOURCE,root);change(root)
                with self.assertRaises((ValueError,KeyError,IndexError,FileNotFoundError)):audit(root)
        self.assertEqual(audit(SOURCE),expected)

if __name__=='__main__':unittest.main()
