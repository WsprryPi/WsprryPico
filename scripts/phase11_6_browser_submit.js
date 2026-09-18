'use strict';
// Actual browser-owned Phase 11.6 LOAD/LOAD_MESSAGE submission.  This script
// drives the shipped page rather than replacing it with direct HTTP requests.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {spawn}=require('node:child_process'),assert=require('node:assert/strict');
if(!process.argv.includes('--run')){console.log('Plan only; no browser or target access.');process.exit(0);}
const arg=n=>process.argv[process.argv.indexOf(n)+1];
const root=path.resolve(arg('--root')),kind=arg('--kind'),jobPath=path.resolve(arg('--job'));
const job=JSON.parse(fs.readFileSync(jobPath,'utf8')),jobId=job.job_id;
assert(['raw','compact'].includes(kind));assert(/^[0-9a-f]{32}$/.test(jobId));
const HOST='wsprrypico-0a60df.local',ADDRESS='10.77.15.10';
const ORIGIN='https://'+HOST+':18443';
const PEER='06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016';
const BOOT='b72fed2c17583cc7aba0f1345f76a3b2';
const WebSocket=require('/usr/share/nodejs/ws');
let chrome,socket,failure=null,sequence=0,refreshes=0,unavailableRefreshes=0;
const pending=new Map(),events=new Set(),states=new Set(),requests=[],responses=[];
const log=fs.openSync(root+'/browser.jsonl','wx',0o600),deadline=process.hrtime.bigint()+3700n*1000000000n;
const ns=()=>process.hrtime.bigint();
function emit(kind,value){fs.writeSync(log,JSON.stringify({sequence:sequence++,kind,value,monotonic_ns:Number(ns()),utc_ns:Date.now()*1000000})+'\n');fs.fsyncSync(log);}
function save(name,value){const p=root+'/'+name,t=p+'.tmp',fd=fs.openSync(t,'wx',0o600);fs.writeSync(fd,JSON.stringify(value,null,2)+'\n');fs.fsyncSync(fd);fs.closeSync(fd);fs.renameSync(t,p);}
function check(){assert(ns()<deadline,'finite browser deadline');if(failure)throw failure;}
function send(method,params={}){return new Promise((resolve,reject)=>{const id=++send.serial,t=setTimeout(()=>{pending.delete(id);reject(Error('CDP deadline '+method));},15000);pending.set(id,{resolve,reject,t});socket.send(JSON.stringify({id,method,params}));});}send.serial=0;
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function until(fn,seconds=30){const end=ns()+BigInt(seconds)*1000000000n;while(ns()<end){check();if(await fn())return;await new Promise(r=>setTimeout(r,100));}throw Error('browser condition deadline');}
async function shot(name){const state=await evaluate(`({job:snapshot?.job,notice:$('notice').textContent,result:$('job-result').textContent,progress:$('job-progress').textContent,online,busy})`);save(name+'-dom.json',state);const p=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});fs.writeFileSync(root+'/'+name+'.png',Buffer.from(p.data,'base64'));return state;}
async function refresh(){await until(()=>evaluate('!busy'),20);await evaluate("$('refresh').click()");await until(()=>evaluate('!busy'),20);refreshes++;const s=await evaluate('snapshot?.job??null');if(s===null){unavailableRefreshes++;const page=await evaluate(`({notice:$('notice').textContent,online,busy})`);emit('manual_refresh_unavailable',{refresh:refreshes,page});return null;}assert.equal(s.boot_id,BOOT);states.add(s.state);emit('manual_refresh',{refresh:refreshes,state:s});return s;}
async function requiredRefresh(seconds=30){let value=null;await until(async()=>{value=await refresh();return value!==null;},seconds);return value;}
function utcInput(utcNs){return new Date(Number(BigInt(utcNs)/1000000n)).toISOString().slice(0,19);}
(async()=>{
  emit('start',{kind,job_id:jobId,job_sha256:crypto.createHash('sha256').update(fs.readFileSync(jobPath)).digest('hex')});
  const profile=root+'/chrome';assert(!fs.existsSync(profile));fs.mkdirSync(profile);
  chrome=spawn('/usr/bin/chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check','--disable-component-update','--disable-sync','--no-proxy-server','--host-resolver-rules=MAP '+HOST+' '+ADDRESS+', EXCLUDE localhost','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:['ignore',fs.openSync(root+'/chrome.stdout','wx'),fs.openSync(root+'/chrome.stderr','wx')]});
  await until(()=>fs.existsSync(profile+'/DevToolsActivePort'),20);const port=fs.readFileSync(profile+'/DevToolsActivePort','utf8').split('\n')[0];
  const tabs=await(await fetch('http://127.0.0.1:'+port+'/json')).json();socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
  socket.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);clearTimeout(p.t);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}else if(m.method){events.add(m.method);if(m.method==='Network.requestWillBeSent'&&m.params.request.url.endsWith('/api/v1/jobs'))requests.push({method:m.params.request.method,postData:m.params.request.postData});if(m.method==='Network.responseReceived'&&m.params.response.url.endsWith('/api/v1/jobs'))responses.push({status:m.params.response.status,mimeType:m.params.response.mimeType});}});
  await new Promise((resolve,reject)=>{socket.on('open',resolve);socket.on('error',reject);});
  emit('version',await send('Browser.getVersion'));await send('Page.enable');await send('DOM.enable');await send('Network.enable');await send('Network.setCacheDisabled',{cacheDisabled:true});await send('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
  const navigation=await send('Page.navigate',{url:ORIGIN+'/'});emit('navigation',navigation);assert(!navigation.errorText,'Page.navigate '+navigation.errorText);await until(()=>evaluate('typeof online!=="undefined"&&online&&!busy'),45);
  const cert=await send('Network.getCertificate',{origin:ORIGIN});assert(cert.tableNames.length);assert.equal(crypto.createHash('sha256').update(Buffer.from(cert.tableNames[0],'base64')).digest('hex'),PEER);
  await requiredRefresh();await shot('initial');fs.closeSync(fs.openSync(root+'/browser-ready','wx',0o600));
  await until(()=>fs.existsSync(root+'/submit.json'),600);const submission=JSON.parse(fs.readFileSync(root+'/submit.json','utf8'));assert(/^[0-9]+$/.test(submission.start_utc_ns));
  const start=utcInput(submission.start_utc_ns);
  if(kind==='raw'){
    const doc=await send('DOM.getDocument',{depth:2}),node=await send('DOM.querySelector',{nodeId:doc.root.nodeId,selector:'#job-file'});assert(node.nodeId);await send('DOM.setFileInputFiles',{nodeId:node.nodeId,files:[jobPath]});
    await evaluate(`$('start').value=${JSON.stringify(start)}`);
    await evaluate("$('job').requestSubmit()");
  }else{
    const f=Number(BigInt(job.frequency_nhz))/1e9,space=BigInt(job.space_frequency_nhz),shift=(BigInt(job.frequency_nhz)-space)/1000000000n;
    const values={
      'message-text':job.message,'message-mode':job.mode,'message-frequency':String(f),
      'message-shift':String(shift),'message-dot':String(Number(BigInt(job.timing.dot_ns))/1e9),
      'message-dash':String(Number(BigInt(job.timing.dash_ns))/Number(BigInt(job.timing.dot_ns))),
      'message-intra':String(Number(BigInt(job.timing.intra_gap_ns))/Number(BigInt(job.timing.dot_ns))),
      'message-character':String(Number(BigInt(job.timing.character_gap_ns))/Number(BigInt(job.timing.dot_ns))),
      'message-word':String(Number(BigInt(job.timing.word_gap_ns))/Number(BigInt(job.timing.dot_ns))),
      'message-repeats':String(job.repeat_count),'message-gap':String(Number(BigInt(job.repeat_gap_ns))/1e9),
      'message-start':start};
    await evaluate(`(()=>{const v=${JSON.stringify(values)};for(const [id,value] of Object.entries(v)){const e=$(id);e.value=value;e.dispatchEvent(new Event('input',{bubbles:true}));}const original=crypto.randomUUID.bind(crypto);let first=true;crypto.randomUUID=()=>{if(first){first=false;return '${jobId.slice(0,8)}-${jobId.slice(8,12)}-${jobId.slice(12,16)}-${jobId.slice(16,20)}-${jobId.slice(20)}';}return original();};$('message-form').requestSubmit();})()`);
  }
  // activePlan contains BigInt timing fields and therefore cannot be returned
  // by value through CDP.  The exact submitted body is retained from the
  // browser's Network request below; keep this UI snapshot string-only.
  await until(()=>evaluate('!busy'),35);const preview=await evaluate(`({result:$('job-result').textContent,preview:$('message-preview').textContent,notice:$('notice').textContent})`);emit('submitted',{start_utc_ns:submission.start_utc_ns,preview});
  // A rejected ARM leaves the preceding LOAD/LOAD_MESSAGE resident until its
  // owner lease expires.  Fail immediately with the complete browser exchange
  // instead of polling that known-non-running job through lease expiry.
  assert.equal(responses.length,requests.length,'browser response count');
  const rejected=responses.findIndex(r=>r.status!==200);
  if(rejected!==-1)throw Error(`browser submission rejected: HTTP ${responses[rejected].status}: ${preview.notice}`);
  let overlap=false,lastShot=null,terminal=null;
  while(true){check();const s=await refresh();if(s!==null&&s.job_id===jobId&&(s.state==='armed'||s.state==='running')){overlap=true;if(lastShot!==s.state){await shot('overlap-'+s.state);lastShot=s.state;}}if(s!==null&&s.job_id===jobId&&['complete','aborted','missed','failed'].includes(s.state)){terminal=s;break;}if(s!==null&&s.job_id===null&&states.has('running')){terminal=s;break;}await new Promise(r=>setTimeout(r,650));}
  assert(overlap,'manual page refresh never overlapped Armed/Running');assert(!states.has('aborted')&&!states.has('missed')&&!states.has('failed'),'browser job did not complete');
  const releaseRequired=Boolean(terminal.owner_id);
  if(releaseRequired){await until(()=>evaluate("!busy&&!$('release').disabled"),20);await evaluate("$('release').click()");await until(()=>evaluate('!busy'),20);}
  const final=await requiredRefresh();await shot('final');assert.equal(final.output_active,false);assert.equal(final.owner_id,null);
  const decoded=requests.map(r=>JSON.parse(r.postData));const operations=decoded.map(r=>r.operation),expected=['HELLO','CLAIM',kind==='raw'?'LOAD':'LOAD_MESSAGE','ARM'];if(releaseRequired)expected.push('RELEASE');assert.deepEqual(operations,expected);assert.equal(new Set(decoded.map(r=>r.request_id)).size,decoded.length);assert.equal(decoded[2].body.job_id,jobId);assert.equal(decoded[3].body.job_id,jobId);assert(responses.every(r=>r.status===200));
  save('browser-result.json',{status:'PASS',kind,page_loaded:true,manual_refreshes:refreshes,unavailable_refreshes:unavailableRefreshes,manual_refresh_overlap:true,states:[...states].sort(),job_id:jobId,peer_sha256:PEER,operations,release_required:releaseRequired,terminal,final,requests:decoded,responses,preview,events:[...events].sort()});
})().catch(error=>{failure=error;emit('failure',{message:error.message,stack:error.stack});save('browser-result.json',{status:'FAIL',error:error.message,kind,page_loaded:false,manual_refreshes:refreshes,unavailable_refreshes:unavailableRefreshes,states:[...states].sort(),requests,responses});process.exitCode=1;}).finally(async()=>{if(socket){await send('Browser.close').catch(()=>{});socket.close();}if(chrome&&chrome.exitCode===null){chrome.kill('SIGTERM');await new Promise(r=>{chrome.once('exit',r);setTimeout(r,5000);});}emit('finish',{exitCode:process.exitCode||0});fs.closeSync(log);});
