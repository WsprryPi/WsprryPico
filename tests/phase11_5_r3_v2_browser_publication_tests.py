"""Actual Chromium producer waits for fresh publications without relaxing age."""
import subprocess,unittest
from pathlib import Path

class PublicationTests(unittest.TestCase):
    def test_actual_consumer_wait_and_rejection(self):
        script=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('scripts/phase11_5_r3_v2_browser.js','utf8');
const text=source.slice(source.indexOf('function observe('),source.indexOf('function send('));
async function test(mode) {
 let calls=0;const stale={packet_sha256:'packet',monotonic_ns:0,value:{value:{stale:true}}};
 const current={packet_sha256:mode==='foreign'?'foreign':'packet',monotonic_ns:mode==='future'?9000000000:6020000000,value:{value:{fresh:true}}};
 const env={assert,root:'/unused',packetSha:'packet',ns:()=>6030000000n,
  fs:{readFileSync:()=>JSON.stringify(++calls===1||mode==='never'?stale:current)},
  until:async fn=>{for(let n=0;n<3;n++)if(await fn())return;throw Error('bounded wait');}};
 const fresh=vm.runInNewContext(text+';fresh',env);
 if(mode==='normal'){const value=await fresh('status',6000000000n);assert(value.fresh);assert.equal(calls,2);}
 else await assert.rejects(()=>fresh('status',6000000000n),mode==='never'?/bounded wait/:mode==='future'?/Future independent/:/foreign/);
}
(async()=>{for(const mode of ['normal','never','foreign','future'])await test(mode);})().catch(e=>{console.error(e);process.exitCode=1;});
'''
        r=subprocess.run(['node','-e',script],cwd=Path(__file__).resolve().parents[1],text=True,capture_output=True)
        self.assertEqual(r.returncode,0,r.stderr)

if __name__=='__main__':unittest.main()
