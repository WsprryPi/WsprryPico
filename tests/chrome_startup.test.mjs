import assert from 'node:assert/strict';
import {test} from 'node:test';
import {once} from 'node:events';
import {mkdtemp,readFile,writeFile} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {launchChrome} from './chrome_startup.mjs';
import {cleanupUiProcesses} from './ui_process_cleanup.mjs';

const fixture=`
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
const [mode,profile]=process.argv.slice(1);
if(mode==='late-exit')process.on('SIGUSR2',()=>process.exit(17));
if(mode==='exit') {console.error('fixture startup failure');process.exit(17);}
if(mode==='hang') {console.error('fixture waiting without DevTools');setInterval(()=>{},1000);}
else {
 let requests=0,port;
 const server=http.createServer((req,res)=>{
  fs.writeFileSync(path.join(profile,'probes'),String(++requests));
  if(mode==='stall')return;
  if(mode==='malformed'){res.end('{broken');return;}
  if(mode==='oversized-body'){res.end('x'.repeat(65537));return;}
  if(mode==='late-body'){
   res.writeHead(200,{'Content-Type':'application/json'});res.flushHeaders();
   fs.writeFileSync(path.join(profile,'headers-observed'),'');
   const publish=()=>{if(fs.existsSync(path.join(profile,'release-body'))&&!res.writableEnded)res.end(JSON.stringify([{type:'page',webSocketDebuggerUrl:'ws://127.0.0.1:'+port+'/devtools/page/fixture'}]));};
   fs.watch(profile,publish);publish();return;
  }

  res.setHeader('Content-Type','application/json');
  res.end(JSON.stringify(requests===1 || mode==='no-page'?[]:[{type:'page',webSocketDebuggerUrl:'ws://127.0.0.1:'+port+'/devtools/page/fixture'}]));
 });
 const listen=()=>server.listen(0,'127.0.0.1',()=>{
  port=server.address().port;
  if(mode==='file') {
   fs.writeFileSync(path.join(profile,'DevToolsActivePort'),'');
   const publish=()=>{if(fs.existsSync(path.join(profile,'publish-port'))){
    const value=String(port)+'\\n/devtools/browser/fixture\\n';
    if(fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8')!==value)fs.writeFileSync(path.join(profile,'DevToolsActivePort'),value);
   }};
   fs.watch(profile,publish);publish();
  } else console.error('DevTools listening on ws://127.0.0.1:'+port+'/devtools/browser/fixture');
 });
 if(mode==='cold')setTimeout(listen,21000);else listen();
}
`;
async function withBrowser(mode,check,timeoutMs=2000) {
 const profile=await mkdtemp(path.join(os.tmpdir(),'chrome-startup-test-'));
 const browser=launchChrome(process.execPath,['--input-type=module','-e',fixture,mode,profile],profile,timeoutMs===null?{}:typeof timeoutMs==='object'?timeoutMs:{timeoutMs});
 // Fault-state setup must not leave a rejected startup promise unobserved.
 void browser.ready.catch(()=>{});
 try {await check(browser,profile);}
 finally {await cleanupUiProcesses([browser.process],profile);}
}
async function waitForState(check,label) {
 const deadline=performance.now()+5000;
 while(performance.now()<deadline) {
  try {if(await check())return;}catch(error){if(error.code!=='ENOENT')throw error;}
  await new Promise(resolve=>setTimeout(resolve,20));
 }
 assert.fail(`Fixture state not established: ${label}`);
}
const probed=profile=>async()=>Number(await readFile(path.join(profile,'probes'),'utf8'))>0;
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
  let ready=false;void browser.ready.then(()=>{ready=true;},()=>{});
  await waitForState(()=>JSON.parse(browser.diagnostic()).incompleteDiscoveryReads>0, 'startup reader observed incomplete discovery');
  assert.equal(ready,false,'incomplete discovery must not establish readiness');
  assert.equal(JSON.parse(browser.diagnostic()).probes,0,'empty discovery must not contact an endpoint');
  await writeFile(path.join(profile,'publish-port'),'');
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
test('never treats an endpoint without a page as ready',{timeout:10000},async()=>{
 let now=0;
 await withBrowser('no-page',async(browser,profile)=>{
  await waitForState(probed(profile),'empty page endpoint probed');
  now=750;
  await assert.rejects(browser.ready,/Timed out: Chrome startup/);
  assert(Number(await readFile(path.join(profile,'probes'),'utf8'))>0, 'the empty page endpoint was probed');
 },{timeoutMs:750,now:()=>now});
});
test('bounds a stalled DevTools request by the startup deadline',{timeout:10000},async()=>{
 let now=0;
 await withBrowser('stall',async(browser,profile)=>{
  await waitForState(probed(profile),'request accepted without response');
  now=750;
  await assert.rejects(browser.ready,/Timed out: Chrome startup/);
 },{timeoutMs:750,now:()=>now});
});
test('retains bounded stderr when no endpoint ever appears',{timeout:10000},async()=>{
 let now=0;
 await withBrowser('hang',async browser=>{
  await waitForState(()=>JSON.parse(browser.diagnostic()).firstStderrMs!==null,'child startup stderr captured');
  now=750;
  await assert.rejects(browser.ready,error=>/Timed out: Chrome startup/.test(error.message) && /fixture waiting without DevTools/.test(error.message));
 },{timeoutMs:750,now:()=>now});
});


test('rejects valid page discovery released after the observed logical deadline',{timeout:10000},async()=>{
 let now=0;
 await withBrowser('late-body',async(browser,profile)=>{
  await waitForState(()=>readFile(path.join(profile,'headers-observed')).then(()=>true),'DevTools headers arrived while body is withheld');
  now=751;await writeFile(path.join(profile,'release-body'),'');
  await assert.rejects(browser.ready,/Timed out: Chrome startup/);
 },{timeoutMs:750,now:()=>now});
});
test('partial numeric port without a complete discovery record cannot be probed',{timeout:10000},async()=>{
 await withBrowser('file',async(browser,profile)=>{
  await waitForState(()=>JSON.parse(browser.diagnostic()).incompleteDiscoveryReads>0,'incomplete discovery opened');
  await writeFile(path.join(profile,'DevToolsActivePort'),'123');
  await waitForState(()=>JSON.parse(browser.diagnostic()).lastDiscoveryBytes===3,'numeric fragment actually read');
  assert.equal(JSON.parse(browser.diagnostic()).probes,0);
  await writeFile(path.join(profile,'publish-port'),'');assert.equal((await browser.ready)[0].type,'page');
 });
});
test('oversized discovery refuses before contacting an endpoint',{timeout:10000},async()=>{
 await withBrowser('file',async(browser,profile)=>{
  await waitForState(()=>JSON.parse(browser.diagnostic()).incompleteDiscoveryReads>0,'discovery reader entered');
  await writeFile(path.join(profile,'DevToolsActivePort'),'x'.repeat(4097));
  await assert.rejects(browser.ready,/Chrome discovery failed.*Invalid Chrome discovery file/s);
  assert.equal(JSON.parse(browser.diagnostic()).probes,0);
 });
});


test('malformed and oversized DevTools discovery fail without qualifying readiness',{timeout:10000},async()=>{
 for(const mode of ['malformed','oversized-body'])await withBrowser(mode,async browser=>{
  await assert.rejects(browser.ready,/Invalid Chrome DevTools discovery/);
  assert.equal(JSON.parse(browser.diagnostic()).probes,1,'malformed protocol input must not trigger blind retries');
 });
});


test('observed nonzero Chrome exit after readiness fails owned finalization',{timeout:10000},async()=>{
 await withBrowser('late-exit',async browser=>{
  assert.equal((await browser.ready)[0].type,'page');
  const exited=once(browser.process,'exit');browser.process.kill('SIGUSR2');await exited;
  await assert.rejects(browser.stop(),error=>/Chrome exited unexpectedly/.test(error.message)&&/exit=17/.test(error.message));
 });
});
