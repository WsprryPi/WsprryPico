"""Exercise the actual producer's idle transition with delayed independent samples."""
import shutil,subprocess,unittest
from pathlib import Path

class BrowserBoundaryTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node required for actual producer boundary')
    def test_release_waits_for_matching_independent_authority(self):
        root=Path(__file__).resolve().parents[1]
        script=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {sameAuthority}=require('./scripts/phase11_5_r3_v2_browser_guard');
const source=fs.readFileSync('./scripts/phase11_5_r3_v2_browser.js','utf8');
const text=source.slice(source.indexOf('async function idle()'),source.indexOf('\n(async()=>{'));
async function scenario(mutation) {
 const binding={session:'owner'},context={operations:[]};
 const terminal={boot_id:'boot',state:'aborted',job_id:'job',owner_id:'owner',output_active:false};
 let ui={...terminal},reads=0;
 const empty={boot_id:'boot',state:'empty',job_id:null,owner_id:null,output_active:false};
 const candidate={...empty,...mutation};
 const evaluate=async expression=>{
  if(expression==='!busy')return true;
  if(expression==="$('refresh').click()")return;
  if(expression==='snapshot.job')return {...ui};
  if(expression==="$('release').click()") {ui={...empty};return;}
  throw Error('Unexpected UI operation '+expression);
 };
 const observe=()=>++reads===1?terminal:candidate;
 const until=async predicate=>{for(let i=0;i<8;i++)if(await predicate())return;throw Error('bounded observer deadline');};
 const idle=vm.runInNewContext('('+text+')',{assert,binding,context,evaluate,fresh:async()=>observe(),until,sameAuthority});
 if(mutation)await assert.rejects(idle,/bounded observer deadline/);else {await idle();assert.equal(reads,2);}
 assert.deepEqual(context.operations,['RELEASE']);
}
(async()=>{await scenario();for(const mutation of [{boot_id:'other'},{state:'aborted'},{job_id:'other'},{owner_id:'other'},{output_active:true}])await scenario(mutation);})().catch(e=>{console.error(e);process.exitCode=1;});
'''
        subprocess.run(['node','-e',script],cwd=root,check=True,capture_output=True,text=True)

if __name__=='__main__':unittest.main()
