#!/usr/bin/env python3
"""Fresh isolated imports of the actual engineering parent's staged helper union."""
import ast,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'scripts'
ENTRYPOINTS=('phase12_engineering_dispatch','phase12_engineering_flash_status_dispatch',
    'phase12_engineering_journal_dispatch','phase12_engineering_time_dispatch',
    'phase12_engineering_network_dispatch','phase12_engineering_session_dispatch',
    'phase12_engineering_bond_refusal_dispatch','phase12_engineering_fixture','phase12_engineering_setup')
def declared():
    tree=ast.parse((ROOT/'phase12_engineering_orchestrator.py').read_text())
    return {node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and
            isinstance(node.value,str) and node.value.endswith('.py') and (ROOT/node.value).is_file()}
class Tests(unittest.TestCase):
    def prepare(self,directory,exclude=()):
        for name in declared()-set(exclude):shutil.copyfile(ROOT/name,Path(directory)/name)
    def imported(self,directory,name):
        code='import sys;sys.path.insert(0,sys.argv[1]);__import__(sys.argv[2])'
        return subprocess.run([sys.executable,'-I','-c',code,directory,name],cwd=directory,capture_output=True,text=True)
    def test_all_actual_dispatch_stages_import_without_repo_or_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            self.prepare(directory)
            for entry in ENTRYPOINTS:
                with self.subTest(entry=entry):
                    result=self.imported(directory,entry);self.assertEqual(result.returncode,0,result.stderr)
    def test_missing_actual_transitive_helper_fails_isolated_import(self):
        with tempfile.TemporaryDirectory() as directory:
            self.prepare(directory,('phase12_recovery_orchestrator.py',))
            result=self.imported(directory,'phase12_engineering_flash_status_dispatch')
            self.assertNotEqual(result.returncode,0);self.assertIn('phase12_recovery_orchestrator',result.stderr)
if __name__=='__main__':unittest.main()
