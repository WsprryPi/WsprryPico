'use strict';
// Real Chromium page observer for one finite Phase 11.6 RF job.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {spawn}=require('node:child_process'),assert=require('node:assert/strict');
if(!process.argv.includes('--run')) {console.log('Plan only; no browser or target access.');process.exit(0);}
const arg=n=>process.argv[process.argv.indexOf(n)+1];
const root=path.resolve(arg('--root')),jobId=arg('--job-id'),seconds=Number(arg('--seconds')),refreshMs=Number(arg('--refresh-ms'));
assert(Number.isFinite(seconds)&&seconds>0&&seconds<=3700);assert(Number.isFinite(refreshMs)&&refreshMs>=250&&refreshMs<=60000);assert(jobId==='any'||/^[0-9a-f]{32}$/.test(jobId));
const ORIGIN='https://wsprrypico-0a60df.local:18443';
const PEER='06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016';
const BOOT='b72fed2c17583cc7aba0f1345f76a3b2';
const WebSocket=require('/usr/share/nodejs/ws');
let chrome,socket,failure=null,sequence=0,refreshes=0,unavailableRefreshes=0,observedJob=null;
const pending=new Map(),events=new Set(),states=new Set(),jobs=new Set();
const log=fs.openSync(root+'/browser.jsonl','wx',0o600),deadline=process.hrtime.bigint()+BigInt(Math.ceil(seconds+90))*1000000000n;
const ns=()=>process.hrtime.bigint();
function emit(kind,value){fs.writeSync(log,JSON.stringify({sequence:sequence++,kind,value,monotonic_ns:Number(ns()),utc_ns:Date.now()*1000000})+'\n');fs.fsyncSync(log);}
function save(name,value){const p=root+'/'+name,temp=p+'.tmp';const fd=fs.openSync(temp,'w',0o600);fs.writeSync(fd,JSON.stringify(value,null,2)+'\n');fs.fsyncSync(fd);fs.closeSync(fd);fs.renameSync(temp,p);}
function check(){assert(ns()<deadline,'finite browser deadline');if(failure)throw failure;}
function send(method,params={}){return new Promise((resolve,reject)=>{const id=++send.serial,t=setTimeout(()=>{pending.delete(id);reject(Error('CDP deadline '+method));},15000);pending.set(id,{resolve,reject,t});socket.send(JSON.stringify({id,method,params}));});}send.serial=0;
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function until(fn,seconds=30){const end=ns()+BigInt(seconds)*1000000000n;while(ns()<end){check();if(await fn())return;await new Promise(r=>setTimeout(r,100));}throw Error('browser condition deadline');}
async function shot(name){const state=await evaluate(`({job:snapshot?.job,notice:$('notice').textContent,progress:$('job-progress').textContent,online,busy})`);save(name+'-dom.json',state);const p=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});fs.writeFileSync(root+'/'+name+'.png',Buffer.from(p.data,'base64'));return state;}
async function refresh(){await until(()=>evaluate('!busy'),15);await evaluate("$('refresh').click()");await until(()=>evaluate('!busy'),15);refreshes++;const s=await evaluate('snapshot?.job??null');if(s===null){unavailableRefreshes++;const page=await evaluate(`({notice:$('notice').textContent,online,busy})`);emit('manual_refresh_unavailable',{refresh:refreshes,page});return null;}assert.equal(s.boot_id,BOOT);states.add(s.state);if(s.job_id)jobs.add(s.job_id);emit('manual_refresh',{refresh:refreshes,state:s});return s;}
async function requiredRefresh(seconds=30){let value=null;await until(async()=>{value=await refresh();return value!==null;},seconds);return value;}
(async()=>{
  emit('start',{job_id:jobId,seconds,refresh_interval_ms:refreshMs});const profile=root+'/chrome';assert(!fs.existsSync(profile));fs.mkdirSync(profile);
  chrome=spawn('/usr/bin/chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check','--disable-component-update','--disable-sync','--no-proxy-server','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:['ignore',fs.openSync(root+'/chrome.stdout','wx'),fs.openSync(root+'/chrome.stderr','wx')]});
  await until(()=>fs.existsSync(profile+'/DevToolsActivePort'),20);const port=fs.readFileSync(profile+'/DevToolsActivePort','utf8').split('\n')[0];
  const tabs=await(await fetch('http://127.0.0.1:'+port+'/json')).json();socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
  socket.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);clearTimeout(p.t);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}else if(m.method){events.add(m.method);}});
  await new Promise((resolve,reject)=>{socket.on('open',resolve);socket.on('error',reject);});
  emit('version',await send('Browser.getVersion'));await send('Page.enable');await send('Network.enable');await send('Network.setCacheDisabled',{cacheDisabled:true});await send('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:ORIGIN+'/'});await until(()=>evaluate('typeof online!=="undefined"&&online&&!busy'),40);
  const cert=await send('Network.getCertificate',{origin:ORIGIN});assert(cert.tableNames.length);assert.equal(crypto.createHash('sha256').update(Buffer.from(cert.tableNames[0],'base64')).digest('hex'),PEER);
  await requiredRefresh();await shot('initial');fs.closeSync(fs.openSync(root+'/browser-ready','wx',0o600));
  let sawOverlap=false,lastShot=null;
  while(!fs.existsSync(root+'/browser-stop')){
    if(fs.existsSync(root+'/browser-pause')){
      if(!fs.existsSync(root+'/browser-paused')){fs.closeSync(fs.openSync(root+'/browser-paused','wx',0o600));emit('paused',{job_id:jobId});}
      await new Promise(r=>setTimeout(r,50));continue;
    }
    if(fs.existsSync(root+'/browser-paused')){fs.unlinkSync(root+'/browser-paused');emit('resumed',{job_id:jobId});}
    check();const s=await refresh();
    if(s===null){await new Promise(r=>setTimeout(r,refreshMs));continue;}
    if(s.job_id&&(s.state==='armed'||s.state==='running')&&(jobId==='any'||s.job_id===jobId)){
      if(observedJob&&observedJob!==s.job_id)throw Error('wildcard observer saw multiple active jobs');
      observedJob=s.job_id;sawOverlap=true;if(lastShot!==s.state){await shot('overlap-'+s.state);lastShot=s.state;}
    }
    await new Promise(r=>setTimeout(r,refreshMs));
  }
  const final=await requiredRefresh();await shot('final');
  assert(sawOverlap,'manual page refresh never overlapped Armed/Running');
  if(jobId==='any')assert(observedJob&&jobs.has(observedJob),'page never observed an active production job');
  else assert(jobs.has(jobId),'page never observed expected job');
  assert.equal(final.output_active,false);
  save('browser-result.json',{status:'PASS',page_loaded:true,manual_refreshes:refreshes,unavailable_refreshes:unavailableRefreshes,refresh_interval_ms:refreshMs,manual_refresh_overlap:true,states:[...states].sort(),job_ids:[...jobs].sort(),expected_job_id:jobId,observed_job_id:observedJob,peer_sha256:PEER,events:[...events].sort()});
})().catch(error=>{failure=error;emit('failure',{message:error.message,stack:error.stack});save('browser-result.json',{status:'FAIL',error:error.message,page_loaded:false,manual_refreshes:refreshes,unavailable_refreshes:unavailableRefreshes,states:[...states].sort(),job_ids:[...jobs].sort()});process.exitCode=1;}).finally(async()=>{
  if(socket){await send('Browser.close').catch(()=>{});socket.close();}
  if(chrome&&chrome.exitCode===null){chrome.kill('SIGTERM');await new Promise(r=>{chrome.once('exit',r);setTimeout(r,5000);});}
  emit('finish',{exitCode:process.exitCode||0});fs.closeSync(log);
});
