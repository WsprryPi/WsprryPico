// Real shipped UI and synthetic RAM-backed consumer API; no board or RF access.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile,mkdir} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {cleanupUiProcesses} from './ui_process_cleanup.mjs';

const driver=process.argv[2], output=path.resolve(process.argv[3] || 'build/message-frequency-ui');
if (!driver) throw Error('Usage: node message_frequency_ui_integration.mjs DRIVER [OUTPUT]');
await mkdir(output,{recursive:true});
const profile=await mkdtemp(path.join(os.tmpdir(),'wsprrypico-cw-browser-'));
const processGroup=process.platform==='linux';
let fixture, chrome, cdp, fixturePort=19039;
class Cdp {
  constructor(url) {
    this.ws=new WebSocket(url);this.pending=new Map();this.sequence=0;
    this.ws.onmessage=event=>{const r=JSON.parse(event.data),p=this.pending.get(r.id);if(p){this.pending.delete(r.id);r.error?p.reject(Error(r.error.message)):p.resolve(r.result);}};
  }
  async open(){if(this.ws.readyState!==1)await new Promise((resolve,reject)=>{this.ws.onopen=resolve;this.ws.onerror=reject;});}
  send(method,params={}){const id=++this.sequence;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{this.pending.delete(id);reject(Error('Browser deadline: '+method));},15000);this.pending.set(id,{resolve:v=>{clearTimeout(timer);resolve(v);},reject:e=>{clearTimeout(timer);reject(e);}});this.ws.send(JSON.stringify({id,method,params}));});}
  async evaluate(expression){const r=await this.send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
}
async function until(fn,label,ms=15000){const end=Date.now()+ms;while(Date.now()<end){if(await fn())return;await new Promise(resolve=>setTimeout(resolve,50));}let detail='';try{detail=await cdp.evaluate(`JSON.stringify({feedback:document.getElementById('message-result')?.textContent,notice:document.getElementById('notice')?.textContent,active:document.activeElement?.id,writes:globalThis.cwRequests?.slice(-5)})`);}catch{}throw Error('Timed out: '+label+' '+detail);}
async function field(id,value){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});if(${JSON.stringify(id)}==='local-password'&&!document.getElementById('local-access').open)document.getElementById('access-toggle').click();globalThis.WsprryPicoSections?.reveal(e);e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));}`);}
// Submit once the production form admits it; discovery/polling can briefly disable login.
async function submitLogin(){await until(()=>cdp.evaluate(`!busy && !document.getElementById('login-submit').disabled && (document.getElementById('local-login').requestSubmit(),true)`),'login form available');}
async function click(id){await cdp.evaluate(`document.getElementById(${JSON.stringify(id)}).click()`);}
async function control(command) {
  const r=await fetch('http://127.0.0.1:'+fixturePort+'/.fixture-control',{method:'POST',body:JSON.stringify(command)});
  assert.equal(r.status,200);return r.json();
}
async function capture(name,target='job-heading'){
  for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]){
    await cdp.send('Emulation.setDeviceMetricsOverride',{width:view.width,height:view.height,deviceScaleFactor:1,mobile:view.name==='mobile'});
    await cdp.evaluate(`document.getElementById(${JSON.stringify(target)}).scrollIntoView({block:'start'})`);
    assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false,'horizontal overflow');
    if(process.env.PICO_BROWSER_NO_CAPTURE==='1')continue;
    const png=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    await writeFile(path.join(output,`${name}-${view.name}.png`),Buffer.from(png.data,'base64'));
    if(view.name==='mobile' && target==='job-heading') {
      await cdp.evaluate(`document.getElementById('message-preview').scrollIntoView({block:'center'})`);
      const tail=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
      await writeFile(path.join(output,`${name}-preview-mobile.png`),Buffer.from(tail.data,'base64'));
    }
  }
}
function expectedEvents(mode, base, upper, characters=false) {
  const dfcw=mode==='dfcw', fskcw=mode==='fskcw';
  const durations=characters ? [3,3,dfcw?3:9,9,3,0] : [3,3,dfcw?3:9,21,3,7,3,3,dfcw?3:9,21,3,0];
  const marks=characters ? [true,false,true,false,true,false] : [true,false,true,false,true,false,true,false,true,false,true,false];
  let offset=0n;
  return durations.map((seconds,i)=>{
    const internal=characters ? i===1||i===3 : [1,3,7,9].includes(i);
    const on=marks[i] || fskcw && internal;
    const event={offset_ns:String(offset),duration_ns:String(i===durations.length-1 ? 1000n : BigInt(seconds)*1000000000n),rf_on:on,
      frequency_nhz:on ? String(fskcw ? (marks[i]?upper:base) : dfcw && [2,8].includes(i) ? upper:base) : null};
    offset+=BigInt(event.duration_ns);return event;
  });
}
const evidence=[];
try {
  let fixtureOutput='';
  fixture=spawn(process.execPath,['tests/ui_review_fixture.mjs',driver,'19039',output,'messages'],{stdio:['ignore','pipe','pipe'],detached:processGroup});
  fixture.stdout.on('data',data=>fixtureOutput+=data);fixture.stderr.on('data',data=>fixtureOutput+=data);
  await until(()=>fixtureOutput.includes('READY;'),'fixture startup');
  for(const surface of ['consumer','engineering']) {
    const port=surface==='consumer'?19039:19044;
    fixturePort=port;
    chrome=spawn(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      ['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',
       '--remote-debugging-port=0',`--user-data-dir=${profile}`,'--proxy-server=http://127.0.0.1:'+port,'--proxy-bypass-list=<-loopback>','about:blank'],{stdio:'ignore',detached:processGroup});
    let debugPort;
    await until(async()=>{try{debugPort=Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);return !!debugPort;}catch{return false;}},'browser startup',30000);
    const pages=await(await fetch(`http://127.0.0.1:${debugPort}/json`)).json();
    cdp=new Cdp(pages.find(p=>p.type==='page').webSocketDebuggerUrl);await cdp.open();await cdp.send('Page.enable');
    await cdp.send('Page.navigate',{url:'http://192.168.1.53/'});
    if(surface==='consumer') {
      await until(()=>cdp.evaluate('typeof localIdentity!=="undefined" && !!localIdentity && !busy'),'consumer page');
      await field('local-password','test-password');await submitLogin();
    }
    await until(()=>cdp.evaluate('typeof online!=="undefined" && online && !busy'),'ready page');
    assert.equal(await cdp.evaluate(`document.getElementById('message-delivery').value`),'recurring','new CW editor defaults to recurring delivery');
    assert.equal(await cdp.evaluate(`document.getElementById('message-interval').value`),'10');
    assert.deepEqual(await cdp.evaluate(`['message-text','message-mode','message-frequency','message-shift','message-dot','message-repeats','message-gap'].map(id=>document.getElementById(id).value)`),['73 DE AA0NT','qrss','','5','3','1','3']);
    assert.equal(await cdp.evaluate(`Date.parse(document.getElementById('message-start').value+'Z')%600000`),0);
    await capture(surface+'-initial-defaults');
    await field('message-delivery','once');
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-controls').hidden`),true,'Send once without a saved schedule');
    assert.equal(await cdp.evaluate(`document.getElementById('message-frequency-label').textContent`),'Carrier frequency (Hz)');
    assert.equal(await cdp.evaluate(`document.getElementById('message-shift').disabled`),true);
    await cdp.evaluate(`globalThis.cwRequests=[];const originalJob=job;job=async(operation,body={})=>{cwRequests.push({operation,body:structuredClone(body)});return originalJob(operation,body);};`);
    const beforeState=await control({op:'frequency_state'});
    for(const mode of ['qrss','fskcw','dfcw']) {
      for(const [id,value] of Object.entries({mode,text:'A E',frequency:'14096900',shift:'5',dot:'3',dash:'3',intra:'1',character:'3',word:'7',repeats:'2',gap:'7'}))await field('message-'+id,value);
      await cdp.evaluate(`document.getElementById('message-mode').dispatchEvent(new Event('change',{bubbles:true}));document.getElementById('message-start').value=new Date(Number(BigInt(snapshot.standalone.utc_now_ns)/1000000n)+60000).toISOString().slice(0,19)`);
      const label=mode==='qrss'?'Carrier':mode==='fskcw'?'Space':'Dot';
      const ax=(await cdp.send('Accessibility.getFullAXTree')).nodes.find(n=>n.role?.value==='textbox' && n.name?.value===label+' frequency (Hz)');assert(ax,'accessible mode label');assert.match(ax.description?.value||'',/Direct RF/);
      const preview=await cdp.evaluate(`document.getElementById('message-preview').textContent`);
      assert(preview.includes(label+' 14096900 Hz'));if(mode!=='qrss')assert(preview.includes((mode==='fskcw'?'Mark':'Dash')+' 14096905 Hz'));
      await capture(surface+'-'+mode);
      await cdp.evaluate(`document.getElementById('message-mode').focus()`);
      const tab=async()=>{await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});};
      await tab();assert.equal(await cdp.evaluate('document.activeElement.id'),'message-frequency');
      await tab();assert.equal(await cdp.evaluate('document.activeElement.id'),mode==='qrss'?'message-dot':'message-shift');
      const count=await cdp.evaluate('cwRequests.length');
      await cdp.evaluate(`document.querySelector('#message-form button[type=submit]').focus()`);
      assert.equal(await cdp.evaluate(`document.activeElement.textContent`),'Load and arm message');
      await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r'});
      await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
      await until(()=>cdp.evaluate(`!busy && document.getElementById('message-result').textContent.startsWith('Message armed')`),'accepted '+surface+' '+mode);
      const requests=(await cdp.evaluate('cwRequests')).slice(count);assert.deepEqual(requests.map(r=>r.operation),['HELLO','CLAIM','LOAD_MESSAGE','ARM']);
      const body=requests[2].body;
      assert.equal(body.frequency_nhz,mode==='fskcw'?'14096905000000000':'14096900000000000');
      assert.equal(body.space_frequency_nhz,mode==='qrss'?'0':mode==='fskcw'?'14096900000000000':'14096905000000000');
      const compiled=await control({op:'accepted_job',surface});assert.equal(compiled.job_id,body.job_id);assert.equal(compiled.mode,mode);assert.equal(compiled.allow_frequency_adjustment,true);
      assert.equal(compiled.total_duration_ns,mode==='dfcw'?'73000001000':'85000001000');
      assert.deepEqual(compiled.events,expectedEvents(mode,14096900000000000n,14096905000000000n));
      evidence.push({surface,preview,requests,compiled});
      await cdp.evaluate(`(async()=>{await job('ABORT',{job_id:snapshot.job.job_id});await job('RELEASE');await refresh();})()`);
    }
    // Direct API callers retain explicit frequencies, including both DFCW orientations.
    for(const [mode,first,second,accepted] of [
      ['dfcw','14096900000000000','14096905000000000',true],['dfcw','14096905000000000','14096900000000000',true],
      ['dfcw','14096900000000000','14096900000000000',false],['dfcw','14096900000000000','0',false],
      ['fskcw','14096900000000000','14096905000000000',false],['fskcw','14096900000000000','14096900000000000',false],
      ['qrss','14096900000000000','18446744073709551615',true]]) {
      const result=await cdp.evaluate(`(async()=>{await job('HELLO',{versions:['WTP/1'],client_name:'explicit API',client_version:'1'});await job('CLAIM',{owner_id:session,lease_ms:30000});const body={...cwRequests.find(r=>r.operation==='LOAD_MESSAGE').body,job_id:requestId(),message:'AE',repeat_count:1,mode:${JSON.stringify(mode)},frequency_nhz:${JSON.stringify(first)},space_frequency_nhz:${JSON.stringify(second)}};try{await job('LOAD_MESSAGE',body);return {accepted:true,body};}catch(error){return {accepted:false,error:error.message};}})()`);
      assert.equal(result.accepted,accepted,mode+' explicit '+first+'/'+second);
      if(accepted){const compiled=await control({op:'accepted_job',surface});assert.deepEqual(compiled.events,expectedEvents(mode,BigInt(first),BigInt(second),true));await cdp.evaluate(`job('ABORT',{job_id:${JSON.stringify(result.body.job_id)}})`);}
      await cdp.evaluate(`(async()=>{await job('RELEASE');await refresh();})()`);
    }
    // Raw job-file and finite-tone frequencies pass through unchanged.
    for(const mode of ['tone','dfcw']) {
      const events=[{offset_ns:'0',duration_ns:'1000000000',rf_on:true,frequency_nhz:'14096900000000000'}];
      if(mode==='dfcw')events.push({offset_ns:'1000000000',duration_ns:'1000000000',rf_on:true,frequency_nhz:'14096905000000000'});
      const raw={profile:'rf-events/1',mode,job_id:(mode==='tone'?'8':'9').repeat(32),total_duration_ns:mode==='tone'?'1000000000':'2000000000',events,allow_frequency_adjustment:true};
      await cdp.evaluate(`{const file=new File([${JSON.stringify(JSON.stringify(raw))}],'absolute-job.json',{type:'application/json'});const transfer=new DataTransfer();transfer.items.add(file);document.getElementById('job-file').files=transfer.files;document.getElementById('start').value=document.getElementById('message-start').value;document.getElementById('job').requestSubmit();}`);
      await until(()=>cdp.evaluate(`!busy && snapshot.job.state==='armed'`),'raw '+mode);
      const observed=await control({op:'accepted_job',surface});assert.deepEqual(observed.events,events);assert.equal(observed.total_duration_ns,raw.total_duration_ns);evidence.push({surface,raw,observed});
      await cdp.evaluate(`(async()=>{await job('ABORT',{job_id:snapshot.job.job_id});await job('RELEASE');await refresh();})()`);
    }
    // Exact decimal payload reaches the compiler without Number rounding.
    await field('message-mode','dfcw');await field('message-frequency','14096900.123456789');await field('message-shift','0.000000001');await field('message-text','AE');await field('message-repeats','1');
    await cdp.evaluate(`document.getElementById('message-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && snapshot.job.state==='armed'`),'fractional job');
    const fractional=await control({op:'accepted_job',surface});assert.deepEqual(fractional.events,expectedEvents('dfcw',14096900123456789n,14096900123456790n,true));evidence.push({surface,fractional});
    await cdp.evaluate(`(async()=>{await job('ABORT',{job_id:snapshot.job.job_id});await job('RELEASE');await refresh();})()`);
    const count=await cdp.evaluate('cwRequests.length');
    await field('message-shift','bad');await field('message-mode','qrss');assert.equal(await cdp.evaluate(`document.getElementById('message-shift').disabled`),true);
    assert.doesNotMatch(await cdp.evaluate(`document.getElementById('message-preview').textContent`),/Frequency shift/);
    await field('message-mode','fskcw');assert.equal(await cdp.evaluate(`document.getElementById('message-shift').value`),'bad');
    await cdp.evaluate(`document.getElementById('message-form').requestSubmit()`);await until(()=>cdp.evaluate('!busy'),'invalid input');
    assert.equal(await cdp.evaluate('cwRequests.length'),count);await capture(surface+'-invalid');
    await field('message-shift','5');
    // The browser's advertised range permits this input; saved server policy refuses it.
    await field('message-frequency','1000000');
    await cdp.evaluate(`document.getElementById('message-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && document.getElementById('message-result').textContent.includes('preserved')`),'server refusal');
    assert.equal(await cdp.evaluate(`document.getElementById('message-result').closest('fieldset:disabled')`),null,'action feedback remains outside disabled controls');
    assert.equal(await cdp.evaluate(`getComputedStyle(document.getElementById('message-result')).opacity`),'1');
    assert.equal(await cdp.evaluate(`document.getElementById('message-frequency').value`),'1000000');
    assert.equal(await cdp.evaluate(`document.getElementById('message-shift').value`),'5');await capture(surface+'-server-refusal');
    assert.equal((await cdp.evaluate('cwRequests')).at(-1).operation,'LOAD_MESSAGE','failure never proceeds to ARM');
    await cdp.evaluate(`(async()=>{await job('RELEASE');await refresh();})()`);
    const saved=await cdp.evaluate(`JSON.stringify(['message-frequency','message-shift','message-text','message-dot','message-dash'].map(id=>document.getElementById(id).value))`);
    await cdp.evaluate('refresh()');assert.equal(await cdp.evaluate(`JSON.stringify(['message-frequency','message-shift','message-text','message-dot','message-dash'].map(id=>document.getElementById(id).value))`),saved);
    await cdp.send('Network.enable');await cdp.send('Network.emulateNetworkConditions',{offline:true,latency:0,downloadThroughput:-1,uploadThroughput:-1});await cdp.evaluate('refresh()');
    assert.equal(await cdp.evaluate(`document.getElementById('message-frequency-label').textContent`),'Space frequency (Hz)');
    await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1});await cdp.evaluate('refresh()');
    if(surface==='consumer' && !await cdp.evaluate('localAuthenticated')) {
      await field('local-password','test-password');await submitLogin();
    }
    await until(()=>cdp.evaluate(`online && !busy && !document.getElementById('message-settings').disabled`),'reconnected message editor');
    assert.equal(await cdp.evaluate(`document.getElementById('message-frequency-label').textContent`),'Space frequency (Hz)');
    assert.equal(await cdp.evaluate(`document.getElementById('message-shift').disabled`),false);
    assert.equal(await cdp.evaluate(`JSON.stringify(['message-frequency','message-shift','message-text','message-dot','message-dash'].map(id=>document.getElementById(id).value))`),saved);
    assert.deepEqual(await control({op:'frequency_state'}),beforeState,'message preparation never persists standalone settings');
    // Production schedule saves and readback preserve one-time drafts and the
    // explicit recovery barrier after a committed save loses its UI reply.
    for(const [id,value] of Object.entries({mode:'qrss',text:'E',frequency:'14096900',delivery:'recurring',interval:'20'}))await field('message-'+id,value);
    await cdp.evaluate(`document.getElementById('message-start').value=new Date(Number(BigInt(snapshot.standalone.utc_now_ns)/1000000n)+60000).toISOString().slice(0,19);document.getElementById('message-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && messageScheduleReadback?.data.saved?.enabled`),'saved message schedule');
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-read').hidden`),true);
    await field('message-delivery','once');await field('message-text','ONE TIME');await click('refresh');
    await until(()=>cdp.evaluate('!busy'),'schedule refresh');
    assert.deepEqual(await cdp.evaluate(`['message-delivery','message-text'].map(id=>document.getElementById(id).value)`),['once','ONE TIME']);
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-controls').hidden`),false);
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-pause').hidden`),false);
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-adopt').textContent`),'Restore saved schedule');
    await capture(surface+'-schedule-during-send-once','message-schedule-controls');
    let restoreDialog;
    const acceptRestore=event=>{const r=JSON.parse(event.data);if(r.method==='Page.javascriptDialogOpening'){restoreDialog=r.params;void cdp.send('Page.handleJavaScriptDialog',{accept:true});}};
    cdp.ws.addEventListener('message',acceptRestore);
    try{await click('message-schedule-adopt');}finally{cdp.ws.removeEventListener('message',acceptRestore);}
    assert.match(restoreDialog?.message||'',/Replace the current message draft/);
    assert.deepEqual(await cdp.evaluate(`['message-delivery','message-text'].map(id=>document.getElementById(id).value)`),['recurring','E']);
    await cdp.evaluate(`{const original=api;api=async(...args)=>{const response=await original(...args);if(args[0]==='message-schedule'&&args[1]==='PUT'){api=original;throw Error('Saved schedule reply lost');}return response;};document.getElementById('message-form').requestSubmit();}`);
    await until(()=>cdp.evaluate('!busy && messageScheduleUncertain'),'unconfirmed committed schedule save');
    await click('refresh');await until(()=>cdp.evaluate('!busy'),'ordinary refresh during schedule recovery');
    assert.equal(await cdp.evaluate(`document.getElementById('message-submit').disabled`),true);
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-read').hidden`),false);
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-adopt').hidden`),true);
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-pause').hidden`),true);
    await capture(surface+'-schedule-recovery','message-schedule-controls');
    await click('message-schedule-read');await until(()=>cdp.evaluate('!busy && !messageScheduleUncertain'),'explicit schedule readback');
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-read').hidden`),true);
    assert.equal(await cdp.evaluate(`document.getElementById('message-result').textContent`),'');
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-pause').textContent`),'Pause schedule');
    await click('message-schedule-pause');await until(()=>cdp.evaluate(`!busy && messageScheduleReadback?.data.saved?.enabled===false`),'confirmed schedule pause');
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-pause').hidden`),true);
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-help').hidden`),true);
    assert.match(await cdp.evaluate(`document.getElementById('message-schedule-status').textContent`),/Save and start schedule/);
    await capture(surface+'-schedule-paused','message-schedule-controls');
    await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:'dark'}]});assert.equal(await cdp.evaluate('getComputedStyle(document.documentElement).colorScheme'),'light');
    await cdp.evaluate(`document.documentElement.style.fontSize='200%'`);await capture(surface+'-text-200-percent');
    const afterSchedule=await control({op:'frequency_state'});
    assert.equal(afterSchedule.saved_dial_hz,beforeState.saved_dial_hz,'message schedule leaves the WSPR dial unchanged');
    assert.equal(afterSchedule.enabled,beforeState.enabled,'message schedule leaves WSPR enablement unchanged');
    cdp.ws.close();cdp=null;await cleanupUiProcesses([chrome],profile,{processGroup});chrome=null;
    console.log('PASS '+surface+' shipped CW requests, compiled events, explicit API, keyboard, errors, drafts and views');
  }
  await writeFile(path.join(output,'cw-evidence.json'),JSON.stringify(evidence,null,2)+'\n');
  await writeFile(path.join(output,'result.json'),JSON.stringify({passed:true,surfaces:['consumer','engineering'],modes:['qrss','fskcw','dfcw'],themes:['light'],views:['desktop','mobile'],text_zoom:200,physical_qualification:false},null,2)+'\n');
} finally {
  cdp?.ws.close();await cleanupUiProcesses([chrome,fixture],profile,{processGroup});
}
