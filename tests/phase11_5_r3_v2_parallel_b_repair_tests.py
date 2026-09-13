"""Repair remains gated by an audited fault, exact B image and finite scope."""
import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_parallel_b_repair import validate,prerequisite

class RepairTests(unittest.TestCase):
    def packet(self):
        p=Path(__file__).resolve().parents[1]/'build/phase11-5-r3-v2-parallel-b-deploy-bd1/stage/packet.json'
        if not p.exists():self.skipTest('Frozen repair packet required')
        return json.loads(p.read_text())
    def test_scope(self):
        validate(self.packet())
        for k,v in [('serial','0BF4B4AEC9FFB344'),('image_sha256','0'*64),('flashes',2),('loads',1),
                ('arm_commands',1),('runtime_seconds',3600),('prior_boot','a'*32),('fault_audit_sha256','0'*64)]:
            p=self.packet();p[k]=v
            with self.subTest(k=k),self.assertRaises(ValueError):validate(p)
    def test_missing_fault_does_not_inspect_or_mutate_hardware(self):
        with patch('phase11_5_r3_v2_parallel_b_repair.digest',return_value='0'*64),patch('subprocess.check_output') as process:
            with self.assertRaises(ValueError):prerequisite(self.packet())
            process.assert_not_called()

if __name__=='__main__':unittest.main()
