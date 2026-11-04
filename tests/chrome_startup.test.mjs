import assert from 'node:assert/strict';
import {test} from 'node:test';
import {mkdtemp,readFile} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {launchChrome} from './chrome_startup.mjs';
import {cleanupUiProcesses} from './ui_process_cleanup.mjs';

const fixture=`
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
const [mode,profile]=process.argv.slice(1);
if(mode==='exit') {console.error('fixture startup failure');process.exit(17);}
if(mode==='hang') {console.error('fixture waiting without DevTools');setInterval(()=>{},1000);}
else {
 let requests=0,port;
 const server=http.createServer((req,res)=>{
  fs.writeFileSync(path.join(profile,'probes'),String(++requests));
  if(mode==='stall')return;
  res.setHeader('Content-Type','application/json');
  res.end(JSON.stringify(requests===1 || mode==='no-page'?[]:[{type:'page',webSocketDebuggerUrl:'ws://127.0.0.1:'+port+'/devtools/page/fixture'}]));
 });
 const listen=()=>server.listen(0,'127.0.0.1',()=>{
  port=server.address().port;
  if(mode==='file') {
   fs.writeFileSync(path.join(profile,'DevToolsActivePort'),'');
   setTimeout(()=>fs.writeFileSync(path.join(profile,'DevToolsActivePort'),String(port)+'\\n/devtools/browser/fixture\\n'),30);
  } else console.error('DevTools listening on ws://127.0.0.1:'+port+'/devtools/browser/fixture');
 });
 if(mode==='cold')setTimeout(listen,21000);else listen();
}
`;
async function withBrowser(mode,check,timeoutMs=2000) {
 const profile=await mkdtemp(path.join(os.tmpdir(),'chrome-startup-test-'));
 const browser=launchChrome(process.execPath,['--input-type=module','-e',fixture,mode,profile],profile,timeoutMs===null?{}:{timeoutMs});
 try {await check(browser,profile);}
 finally {await cleanupUiProcesses([browser.process],profile);}
}
test('accepts stderr discovery without requiring a port file, after a real page is ready',async()=>{
 await withBrowser('stderr-only',async(browser,profile)=>{
  const pages=await browser.ready;
  assert.equal(pages[0].type,'page');
  assert(Number(await readFile(path.join(profile,'probes'),'utf8'))>=2);
  await assert.rejects(readFile(path.join(profile,'DevToolsActivePort')),error=>error.code==='ENOENT');
 });
});
test('handles a partially written port file and waits for the page endpoint',async()=>{
 await withBrowser('file',async(browser,profile)=>{
  assert.equal((await browser.ready)[0].type,'page');
  assert(Number(await readFile(path.join(profile,'probes'),'utf8'))>=2);
 });
});
test('allows cold endpoint startup beyond 20 seconds within the shared 60-second budget',{timeout:30000},async()=>{
 await withBrowser('cold',async browser=>{
  assert.equal((await browser.ready)[0].type,'page');
  const timing=JSON.parse(browser.diagnostic());
  assert.equal(timing.budgetMs,60000);
  assert(timing.endpointMs>=21000);
  assert(timing.probes>=2);
 },null);
});
test('reports an early exit with its actual code and stderr',async()=>{
 await withBrowser('exit',async browser=>{
  await assert.rejects(browser.ready,error=>/exited before DevTools/.test(error.message) && /exit=17/.test(error.message) && /fixture startup failure/.test(error.message));
 });
});
test('reports a missing executable without waiting for the startup deadline',{timeout:2000},async()=>{
 const profile=await mkdtemp(path.join(os.tmpdir(),'chrome-startup-test-'));
 const browser=launchChrome(path.join(profile,'missing-chrome'),[],profile);
 try {await assert.rejects(browser.ready,/Chrome launch failed:.*ENOENT/);}
 finally {await cleanupUiProcesses([browser.process],profile);}
});
test('never treats an endpoint without a page as ready',{timeout:2000},async()=>{
 await withBrowser('no-page',async(browser,profile)=>{
  await assert.rejects(browser.ready,/Timed out: Chrome startup/);
  assert(Number(await readFile(path.join(profile,'probes'),'utf8'))>0, 'the empty page endpoint was probed');
 },750);
});
test('bounds a stalled DevTools request by the startup deadline',async()=>{
 await withBrowser('stall',async browser=>{await assert.rejects(browser.ready,/Timed out: Chrome startup/);},750);
});
test('retains bounded stderr when no endpoint ever appears',async()=>{
 await withBrowser('hang',async browser=>{
  await assert.rejects(browser.ready,error=>/Timed out: Chrome startup/.test(error.message) && /fixture waiting without DevTools/.test(error.message));
 },750);
});
