'use strict';
// Opt-in real target Chromium UI producer. All mutations pass a finite guard.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {spawn}=require('node:child_process'),assert=require('node:assert/strict');
const {guardRequest,ORIGIN,sameAuthority,readyForJob}=require('./phase11_5_r3_v2_browser_guard');
if(!process.argv.includes('--run')) {console.log('Plan only; no browser or target access.');process.exit(0);}
const argument=n=>process.argv[process.argv.indexOf(n)+1];
const root=path.resolve(argument('--root')),packetSha=argument('--packet-sha256');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
assert.equal(hash(fs.readFileSync(root+'/packet.json')),packetSha);
const packet=JSON.parse(fs.readFileSync(root+'/packet.json'));
const admissionOnly=process.argv.includes('--admission-only');
assert.equal(packet.schema,admissionOnly?'phase11.5-r3-v2-browser-trust-v1':'phase11.5-r3-v2-chromium-v1');
if(admissionOnly){assert.equal(packet.maximum_jobs,0);assert.deepEqual(packet.cases,[]);assert.equal(packet.maximum_request_count,15);}assert.equal(packet.standing_authority,'R3-COMPLETE-20260913-v2');
assert.equal(fs.readlinkSync('/proc/self/ns/net'),packet.netns);
const WebSocket=require('/usr/share/nodejs/ws');
let chrome,socket,sequence=0,requestCount=0,context=null,failure=null;
const pending=new Map(),responseWork=new Set(),responses=new Map();
const log=fs.openSync(root+'/browser.jsonl','wx',0o600),start=process.hrtime.bigint(),deadline=start+(admissionOnly?60000000000n:850000000000n);
const result={status:'RUNNING',rf_jobs_charged:0,rf_duration_ns_charged:'0',cases:[]};
const binding={packet_sha256:packetSha,session:null,job_ids:[]};
const ns=()=>process.hrtime.bigint();
function emit(kind,value) {fs.writeSync(log,JSON.stringify({sequence:sequence++,kind,value,monotonic_ns:Number(ns()),utc_ns:Date.now()*1000000})+'\n');fs.fsyncSync(log);}
function save(name,value) {const temp=root+'/'+name+'.tmp';const fd=fs.openSync(temp,'w',0o600);fs.writeSync(fd,JSON.stringify(value)+'\n');fs.fsyncSync(fd);fs.closeSync(fd);fs.renameSync(temp,root+'/'+name);}
function check() {assert(ns()<deadline,'Finite browser deadline');if(failure)throw failure;assert(!fs.existsSync(root+'/observer-failed.json'),'Independent observer failure');}
function observe(kind,age,pending=false) {
  const r=JSON.parse(fs.readFileSync(root+'/observer-'+kind+'.json'));assert.equal(r.packet_sha256,packetSha);
  const elapsed=ns()-BigInt(r.monotonic_ns);assert(elapsed>=0n,'Future independent '+kind);
  if(pending&&elapsed>age)return null;
  assert(elapsed<=age,'Stale independent '+kind);return r.value.value;
}
async function fresh(kind,age) {
  let value=null;
  // A publication can age while the next bounded exchange is in flight.
  // Wait for a fresh completed sample; never consume the stale value.
  await until(()=>{value=observe(kind,age,true);return value!==null;},7);
  return value;
}
function send(method,params={}) {return new Promise((resolve,reject)=>{const id=pending.size+1000+sequence*100000+(send.serial++);const timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP deadline '+method));},20000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});}send.serial=0;
async function evaluate(expression) {const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function until(fn,seconds=20) {const end=ns()+BigInt(seconds)*1000000000n;while(ns()<end){check();if(await fn())return;await new Promise(r=>setTimeout(r,100));}throw Error('UI/observer condition deadline');}
async function shot(name) {const dom=await evaluate(`({state:$('state').textContent,output:$('output').textContent,notice:$('notice').textContent,preview:$('message-preview').textContent,progress:$('job-progress').textContent,owner:$('owner').textContent,job:snapshot?.job,abortDisabled:$('abort').disabled,releaseDisabled:$('release').disabled,online,busy})`);emit('dom', {name,...dom});save(name+'-dom.json',dom);const s=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});fs.writeFileSync(root+'/'+name+'.png',Buffer.from(s.data,'base64'));return dom;}
async function intercepted(event) {
  const request=event.request;
  try {
    check();assert(++requestCount<=packet.maximum_request_count,'Browser request count');
    const q=guardRequest(request,context||{operations:[],index:0});
    emit('request_guard',{network_id:event.networkId,request});
    if(q) {
      context.requestIds.add(q.request_id);
      if(q.operation==='LOAD'||q.operation==='LOAD_MESSAGE') {
        context.jobId=q.body.job_id;assert(!binding.job_ids.includes(q.body.job_id));binding.job_ids.push(q.body.job_id);
        save('browser-binding.json',binding);
      }
      if(q.operation==='ARM') {
        // Hold the actual browser request until an independent observer confirms Loaded.
        await until(async()=>{const s=await fresh('status',6000000000n);return s.state==='loaded'&&s.job_id===q.body.job_id&&s.owner_id===binding.session;},7);
        const i=await fresh('info',2000000000n);assert.equal(i.status.boot_id,packet.boot_id);assert.equal(i.status.output_active,false);
        assert.equal(i.status.clock_state,'synchronized');
        assert(BigInt(q.body.start_utc_ns)-BigInt(i.status.utc_now_ns)>=5000000000n,'Observed ARM lead exhausted');
        ++result.rf_jobs_charged;result.rf_duration_ns_charged=(BigInt(result.rf_duration_ns_charged)+BigInt(context.case.duration_ns)).toString();
        save('browser-result.json',result);emit('arm_charge',{job_id:q.body.job_id,duration_ns:context.case.duration_ns,start_utc_ns:q.body.start_utc_ns});
      }
      ++context.index;
    }
    await send('Fetch.continueRequest',{requestId:event.requestId});
  } catch(error) {
    failure=error;emit('failure',{stage:'request_guard',error:error.message});
    await send('Fetch.failRequest',{requestId:event.requestId,errorReason:'Aborted'}).catch(()=>{});
  }
}
async function event(method,params) {
  if(method==='Fetch.requestPaused') {await intercepted(params);return;}
  if(method==='Network.requestWillBeSent') emit('network_request',params);
  if(method==='Network.responseReceived') {responses.set(params.requestId,params);emit('network_response',params);}
  if(method==='Network.loadingFailed') {emit('network_failed',params);if(params.type!=='Other')failure=Error('Chromium network failure '+params.errorText);}
  if(method==='Network.loadingFinished'&&responses.has(params.requestId)) {
    const response=responses.get(params.requestId);const body=await send('Network.getResponseBody',{requestId:params.requestId});
    emit('network_body',{request_id:params.requestId,response:response.response,body,finished:params});
  }
}
async function messageValues(mode,text,dot='0.25') {
  const values={mode,text,frequency:'135500',shift:'5',dot,repeats:'1',gap:'1',dash:'3',intra:'1',character:'3',word:'7'};
  await evaluate(`(()=>{for(const [k,v] of Object.entries(${JSON.stringify(values)}))$('message-'+k).value=v;messagePreview();})()`);
}
async function matchingUi(expected, cancel=false, click=false) {
  return evaluate(`(()=>{const ready=(${readyForJob.toString()})({job:snapshot?.job,online,busy,abortDisabled:$('abort').disabled},${JSON.stringify(expected)},${cancel});if(ready&&${click})$('abort').click();return ready;})()`);
}
async function idle() {
  await until(()=>evaluate('!busy'),35);await evaluate("$('refresh').click()");await until(()=>evaluate('!busy'));
  const s=await evaluate('snapshot.job');assert.equal(s.output_active,false);
  if(s.owner_id===binding.session) {
    context.operations.push('RELEASE');await evaluate("$('release').click()");await until(()=>evaluate('!busy'));
  }
  const expected=await evaluate('snapshot.job');
  assert.equal(expected.owner_id,null,'Browser owner remains at next case');
  // The USB observer may still hold the terminal sample preceding RELEASE.
  // Wait for its next independent publication before accepting this boundary.
  await until(async()=>sameAuthority(await fresh('status',6000000000n),expected),7);
}
(async()=>{
  emit('start',{packet_sha256:packetSha,netns:fs.readlinkSync('/proc/self/ns/net')});
  const profile=root+'/chrome';assert(!fs.existsSync(profile));fs.mkdirSync(profile);
  chrome=spawn('/usr/bin/chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check','--disable-component-update','--disable-sync','--no-proxy-server','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:['ignore',fs.openSync(root+'/chrome.stdout','wx'),fs.openSync(root+'/chrome.stderr','wx')]});
  await until(()=>fs.existsSync(profile+'/DevToolsActivePort'));const port=fs.readFileSync(profile+'/DevToolsActivePort','utf8').split('\n')[0];
  const tabs=await(await fetch('http://127.0.0.1:'+port+'/json')).json();socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
  socket.on('message',raw=>{const m=JSON.parse(raw);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);clearTimeout(p.timer);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}
    else if(m.method){const work=event(m.method,m.params).catch(e=>{failure=e;emit('failure',{stage:'cdp_event',error:e.message});});responseWork.add(work);work.finally(()=>responseWork.delete(work));}});
  await new Promise((resolve,reject)=>{socket.on('open',resolve);socket.on('error',reject);});
  emit('browser_version',await send('Browser.getVersion'));await send('Page.enable');await send('Network.enable',{maxTotalBufferSize:10000000,maxResourceBufferSize:1000000});
  await send('Network.setCacheDisabled',{cacheDisabled:true});await send('Fetch.enable',{patterns:[{urlPattern:'*',requestStage:'Request'}]});
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url:ORIGIN+'/'});await until(()=>evaluate('typeof online!=="undefined"&&online&&!busy'),40);
  assert.equal(await evaluate('snapshot.job.boot_id'),packet.boot_id);assert.equal(await evaluate('snapshot.job.state'),'empty');
  const cert=await send('Network.getCertificate',{origin:ORIGIN});assert(cert.tableNames.length>0);
  assert.equal(hash(Buffer.from(cert.tableNames[0],'base64')),packet.peer_sha256);emit('peer_certificate',{sha256:packet.peer_sha256});
  binding.session=await evaluate('session');save('browser-binding.json',binding);await shot('initial');
  if(admissionOnly) {assert.equal(result.rf_jobs_charged,0);assert.equal(binding.job_ids.length,0);result.status='BROWSER_TRUST_READ_ONLY_VERIFIED';return;}
  for(const mode of ['qrss','fskcw','dfcw']) {
    for(const count of [31,32,33]) {
      await messageValues(mode,'?'.repeat(count));const preview=await evaluate("$('message-preview').textContent");
      assert(count===33 ? preview.includes('1–32 characters') : preview.includes(count+' / 32 characters'));
      await shot(mode+'-'+count);
    }
    await messageValues(mode,' '.repeat(31)+'E');assert((await evaluate("$('message-preview').textContent")).includes('32 / 32 characters'));
    await shot(mode+'-spaces-32');
  }
  // Reject a real oversized file before any jobs request; preserve the actual File metadata.
  await send('DOM.enable');let doc=await send('DOM.getDocument');let input=await send('DOM.querySelector',{nodeId:doc.root.nodeId,selector:'#job-file'});
  await send('DOM.setFileInputFiles',{nodeId:input.nodeId,files:[root+'/job-30001.json']});
  await evaluate("$('start').value=new Date(Date.now()+20000).toISOString().slice(0,19);$('job').requestSubmit()");
  await until(()=>evaluate('!busy'));assert((await evaluate("$('notice').textContent")).includes('at most 30,000 bytes'));
  assert.equal(binding.job_ids.length,0);await shot('file-30001-rejected');
  for(let n=0;n<packet.cases.length;n++) {
    if(!(packet.case_indices||[0,1,2,3]).includes(n))continue;
    if(result.cases.length && packet.between_case_quiet_seconds) {
      const began=ns();emit('replay_quiet_start',{seconds:packet.between_case_quiet_seconds});
      while(ns()-began<BigInt(packet.between_case_quiet_seconds)*1000000000n) {
        check();const s=await fresh('status',6000000000n);
        assert.equal(s.state,'empty');assert.equal(s.output_active,false);assert.equal(s.owner_id,null);
        await new Promise(r=>setTimeout(r,1000));
      }
      emit('replay_quiet_finish',{elapsed_ns:(ns()-began).toString()});
    }
    const c=packet.cases[n];context={case:c,operations:['HELLO','CLAIM',c.kind==='file-complete'?'LOAD':'LOAD_MESSAGE','ARM'],index:0,
      session:binding.session,requestIds:new Set(),jobId:null,chargedJobs:result.rf_jobs_charged,chargedNs:BigInt(result.rf_duration_ns_charged),utcNowNs:String(Date.now()*1000000)};
    if(c.kind==='file-complete') {
      await send('DOM.setFileInputFiles',{nodeId:input.nodeId,files:[root+'/job-30000.json']});
      assert.equal(await evaluate("$('job-file').files[0].size"),30000);
      await evaluate("$('start').value=new Date(Date.now()+20000).toISOString().slice(0,19);$('job').requestSubmit()");
    } else {
      await messageValues(c.message.mode,c.message.message,c.dot_seconds);
      const preview=await evaluate("messagePlan().duration.toString()");assert.equal(preview,c.duration_ns);
      await evaluate("$('message-start').value=new Date(Date.now()+20000).toISOString().slice(0,19);$('message-form').requestSubmit()");
    }
    await until(()=>evaluate('!busy'),45);check();
    if(context.index!==4) {
      const diagnostic=await shot('case-'+n+'-submission-rejected');
      throw Error('Submission stopped before ARM: '+diagnostic.notice+'; guarded operations '+context.index+'/4');
    }
    assert.equal(await evaluate('snapshot.job.state'),'armed');await shot('case-'+n+'-armed');
    const caseResult={kind:c.kind,job_id:context.jobId,planned_duration_ns:c.duration_ns};
    if(c.kind==='armed-abort') {
      await until(async()=>{const s=await fresh('status',6000000000n);return s.state==='armed'&&s.job_id===context.jobId;},10);
      context.operations.push('ABORT');await evaluate("$('abort').click()");await until(()=>evaluate('!busy'));
      assert.equal(await evaluate('snapshot.job.state'),'aborted');
    } else {
      await until(async()=>{const s=await fresh('status',6000000000n);return s.state==='running'&&s.job_id===context.jobId;},30);
      const runningAt=ns();
      const runningAuthority={boot_id:packet.boot_id,state:'running',job_id:context.jobId,owner_id:binding.session,output_active:true};
      await until(()=>matchingUi(runningAuthority),15);await shot('case-'+n+'-running');
      if(c.kind==='running-abort') {
        while(ns()-runningAt<BigInt(packet.running_abort_after_ns)) {check();await new Promise(r=>setTimeout(r,1000));}
        assert(sameAuthority(await fresh('status',6000000000n),runningAuthority));
        await until(()=>matchingUi(runningAuthority,true),15);
        await shot('case-'+n+'-before-abort');context.operations.push('ABORT');
        // Recheck and click atomically: a polling refresh can start during a screenshot.
        await until(()=>matchingUi(runningAuthority,true,true),15);await until(()=>evaluate('!busy'));
        assert.equal(await evaluate('snapshot.job.state'),'aborted');caseResult.observed_running_ns=(ns()-runningAt).toString();
      } else {
        await until(async()=>{const s=await fresh('status',6000000000n);return s.state==='complete'&&s.job_id===context.jobId;},Math.ceil(Number(c.duration_ns)/1e9)+10);
        await evaluate("$('refresh').click()");await until(()=>evaluate('!busy'));assert.equal(await evaluate('snapshot.job.state'),'complete');
      }
    }
    assert.equal(await evaluate('snapshot.job.output_active'),false);await shot('case-'+n+'-terminal');
    await until(async()=>{const s=await fresh('status',6000000000n);return s.job_id===context.jobId&&
      s.state===(c.kind.includes('abort')?'aborted':'complete')&&s.output_active===false;},7);
    await idle();caseResult.result=c.kind.includes('abort')?'aborted':'complete';result.cases.push(caseResult);save('browser-result.json',result);
  }
  await shot('final');check();result.status='CAPTURED_REQUIRES_AUDIT';
})().catch(error=>{result.status='FAILED';result.error=error.message;emit('failure',{stage:'producer',error:error.stack});process.exitCode=1;}).finally(async()=>{
  if(socket){await Promise.allSettled([...responseWork]);await send('Browser.close').catch(()=>{});socket.close();}
  if(chrome){if(chrome.exitCode===null)chrome.kill('SIGTERM');await new Promise(r=>{chrome.on('exit',r);setTimeout(r,5000);});}
  result.request_count=requestCount;emit('finish',result);save('browser-result.json',result);fs.closeSync(log);
});
