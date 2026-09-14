"""Actual browser guard rejects stale authority and disabled controls."""
import subprocess,unittest
from pathlib import Path

class BrowserReadyTests(unittest.TestCase):
    def test_actual_ready_guard(self):
        guard=Path(__file__).resolve().parents[1]/'scripts/phase11_5_r3_v2_browser_guard.js'
        script=r'''
const assert=require('node:assert/strict');
const {readyForJob}=require(process.argv[1]);
const expected={boot_id:'b',state:'running',job_id:'j',owner_id:'s',output_active:true};
const ui={job:{...expected},online:true,busy:false,abortDisabled:false};
assert(readyForJob(ui,expected,true));
for(const changed of [{busy:true},{online:false},{abortDisabled:true},{job:null}]) assert(!readyForJob({...ui,...changed},expected,true));
for(const [key,value] of Object.entries({boot_id:'foreign',state:'armed',job_id:'old',owner_id:'foreign',output_active:false}))
 assert(!readyForJob({...ui,job:{...expected,[key]:value}},expected,true));
assert(readyForJob({...ui,abortDisabled:true},expected,false));
// The exact browser-serialized function must work without module closures.
const isolated=eval('('+readyForJob.toString()+')');assert(isolated(ui,expected,true));
'''
        subprocess.run(['node','-e',script,str(guard)],check=True,capture_output=True)

if __name__=='__main__':unittest.main()
