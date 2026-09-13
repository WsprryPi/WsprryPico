"""Idle recovery must never gain authority over active or unidentified output."""
import copy
import hashlib
import json
import tempfile
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_reconcile import admission, validate_stage, validate_final

class ReconcileAdmissionTests(unittest.TestCase):
    def test_inhibited_comparator_has_no_rf_telemetry(self):
        v={'wtp':{'STATUS':dict(boot_id='b'*32,state='empty',output_active=False,owner_id=None,job_id=None,terminal_records=[])},
           'info':{'revision':'inhibited'}}
        with patch('phase11_5_r3_v2_reconcile.configuration', return_value={}):
            validate_final(v,copy.deepcopy(v),{},True)
            changed=copy.deepcopy(v);changed['info']['revision']='other'
            with self.assertRaisesRegex(ValueError,'B changed'):validate_final(changed,v,{},True)
            changed=copy.deepcopy(v);changed['wtp']['STATUS']['output_active']=True
            with self.assertRaisesRegex(ValueError,'Final identity'):validate_final(changed,v,{},True)
            with self.assertRaises(KeyError):validate_final(v,copy.deepcopy(v),{},False)

    def test_stage_requires_schema_before_any_inventory_can_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            names=['scripts/phase11_5_inventory.py','scripts/phase11_5_pilot.py','docs/protocol/wtp-1.schema.json']
            for name in names:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(json.dumps({'$schema':'test'}) if name.endswith('.json') else '# helper\n')
            packet={'stage_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}}
            validate_stage(root,packet)
            schema=root/names[-1];schema.unlink()
            with self.assertRaisesRegex(ValueError,'Missing or changed'):validate_stage(root,packet)
            del packet['stage_sha256'][names[-1]]
            with self.assertRaisesRegex(ValueError,'dependency manifest'):validate_stage(root,packet)

    def test_only_known_inactive_unowned_complete_can_be_released(self):
        packet=dict(boot_id='a'*32,allowed_complete_jobs=['b'*32])
        status=dict(boot_id='a'*32,state='complete',output_active=False,owner_id=None,job_id='b'*32,
                    terminal_records=[dict(job_id='b'*32,state='complete',output_active=False)])
        value=dict(wtp={'STATUS':status},info={'status':dict(status)})
        with patch('phase11_5_r3_v2_reconcile.validate_info'):
            self.assertTrue(admission(value,packet))
            for field,replacement in [('state','running'),('state','armed'),('state','loaded'),
                                      ('state','aborted'),('output_active',True),('output_active',None),
                                      ('owner_id','c'*32),('job_id','c'*32),('boot_id','c'*32),
                                      ('terminal_records',[])]:
                altered=copy.deepcopy(value);altered['wtp']['STATUS'][field]=replacement
                with self.subTest(field=field,value=replacement),self.assertRaises(ValueError):admission(altered,packet)
            empty=copy.deepcopy(value)
            empty['wtp']['STATUS'].update(state='empty',job_id=None)
            empty['info']['status'].update(state='empty',job_id=None)
            self.assertFalse(admission(empty,packet))
            empty['info']['status']['output_active']=True
            with self.assertRaises(ValueError):admission(empty,packet)

if __name__=='__main__':unittest.main()
