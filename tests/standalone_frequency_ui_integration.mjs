// Real shipped UI and synthetic RAM-backed consumer API; no board or RF access.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile,mkdir} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {cleanupUiProcesses} from './ui_process_cleanup.mjs';
import {firstWsprTransmission} from './standalone_wspr_trial.mjs';

const driver=process.argv[2], output=path.resolve(process.argv[3] || 'build/standalone-frequency-ui');
const firstUse=process.argv[4]?.startsWith('first-use:') ? process.argv[4].slice(10) : null;
const port=firstUse==='refusal' ? 18944 : firstUse ? 18945+['network','usb','overlay','network-backing'].indexOf(firstUse) : 18939;
if (!driver) throw Error('Usage: node standalone_frequency_ui_integration.mjs DRIVER [OUTPUT]');
await mkdir(output,{recursive:true});
const profile=await mkdtemp(path.join(os.tmpdir(),'wsprrypico-frequency-browser-'));
const processGroup=process.platform!=='win32';
let fixture, chrome, cdp;
class Cdp {
  constructor(url) {
    this.ws=new WebSocket(url);this.pending=new Map();this.sequence=0;
    this.ws.onmessage=event=>{const r=JSON.parse(event.data);if(r.method==='Page.javascriptDialogOpening'){void this.send('Page.handleJavaScriptDialog',{accept:true});return;}const p=this.pending.get(r.id);if(p){this.pending.delete(r.id);r.error?p.reject(Error(r.error.message)):p.resolve(r.result);}};
  }
  async open(){if(this.ws.readyState!==1)await new Promise((resolve,reject)=>{this.ws.onopen=resolve;this.ws.onerror=reject;});}
  send(method,params={}){const id=++this.sequence;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{this.pending.delete(id);reject(Error('Browser deadline: '+method));},15000);this.pending.set(id,{resolve:v=>{clearTimeout(timer);resolve(v);},reject:e=>{clearTimeout(timer);reject(e);}});this.ws.send(JSON.stringify({id,method,params}));});}
  async evaluate(expression){const r=await this.send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
}
async function until(fn,label,ms=15000){const end=Date.now()+ms;while(Date.now()<end){if(await fn())return;await new Promise(resolve=>setTimeout(resolve,50));}let detail='';try{detail=await cdp.evaluate(`JSON.stringify({feedback:document.getElementById('standalone-frequency-status')?.textContent,active:document.activeElement?.id,writes:globalThis.frequencyWrites,online:typeof online!=='undefined'&&online,busy:typeof busy!=='undefined'&&busy,notice:document.getElementById('notice')?.textContent,readDisabled:document.getElementById('standalone-frequency-read')?.disabled,inputDisabled:document.getElementById('standalone-frequency')?.disabled,adoptHidden:document.getElementById('standalone-frequency-adopt')?.hidden,observations:globalThis.frequencyObservations})`);}catch{}throw Error('Timed out: '+label+' '+detail);}
async function field(id,value){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});globalThis.WsprryPicoSections?.reveal(e);e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));}`);}
async function click(id){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});globalThis.WsprryPicoSections?.reveal(e);e.click();}`);}
async function login() {
  await until(()=>cdp.evaluate('!busy'),'access request settled');
  const priorBoot=await cdp.evaluate('localIdentity?.boot_id');
  await cdp.evaluate(`document.getElementById('access-toggle').click()`);
  assert.equal(await cdp.evaluate(`document.getElementById('local-access').open`),true,'deliberate password modal');
  await field('local-password','test-password');
  await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
  await until(()=>cdp.evaluate('!busy'),'login response');
  if(await cdp.evaluate(`document.getElementById('local-status').textContent.startsWith('The Pico or its boot changed.')`)) {
    assert.notEqual(await cdp.evaluate('localIdentity.boot_id'),priorBoot,'expected synthetic reboot identified');
    assert.equal(await cdp.evaluate('localAuthenticated || radio.authenticated'),false);
    assert.equal(await cdp.evaluate(`document.getElementById('local-password').value`),'');
    // Review the newly observed boot, then make one separate explicit attempt.
    await field('local-password','test-password');
    await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
    await until(()=>cdp.evaluate('!busy'),'reviewed boot login');
  }
}
async function control(command) {
  const r=await fetch(`http://127.0.0.1:${port}/.fixture-control`,{method:'POST',body:JSON.stringify(command)});
  assert.equal(r.status,200);return r.json();
}
async function capture(name){
  if(process.env.UI_REVIEW_NO_CAPTURE==='1') return;
  for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]){
    await cdp.send('Emulation.setDeviceMetricsOverride',{width:view.width,height:view.height,deviceScaleFactor:1,mobile:view.name==='mobile'});
    await cdp.evaluate(`document.getElementById('${name.includes('text-200') ? 'standalone-frequency-status' : 'standalone-frequency-form'}').scrollIntoView({block:'start'})`);
    assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false,'horizontal overflow');
    const png=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    await writeFile(path.join(output,`${name}-${view.name}.png`),Buffer.from(png.data,'base64'));
  }
}
try {
  let fixtureOutput='';
  fixture=spawn(process.execPath,['tests/ui_review_fixture.mjs',driver,'18939',output,...(process.argv[5]==='transmission' ? ['messages'] : [])],{stdio:['ignore','pipe','pipe'],detached:processGroup});
  fixture.stdout.on('data',data=>{fixtureOutput+=data;});
  fixture.stderr.on('data',data=>{fixtureOutput+=data;});
  await until(()=>fixtureOutput.includes('READY;'),'fixture startup');
  chrome=spawn(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    ['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',
     '--remote-debugging-port=0',`--user-data-dir=${profile}`,`--proxy-server=http://127.0.0.1:${port}`,'--proxy-bypass-list=<-loopback>','about:blank'],{stdio:'ignore',detached:processGroup});
  let debugPort;
  await until(async()=>{try{debugPort=Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);return !!debugPort;}catch{return false;}},'browser startup',30000);
  const pages=await(await fetch(`http://127.0.0.1:${debugPort}/json`)).json();
  cdp=new Cdp(pages.find(p=>p.type==='page').webSocketDebuggerUrl);await cdp.open();await cdp.send('Page.enable');
  await cdp.send('Page.navigate',{url:'http://192.168.1.53/'});
  if(firstUse==='refusal') {
    await until(()=>cdp.evaluate(`typeof online!=='undefined' && online && !busy`),'engineering page');
  } else {
  await until(()=>cdp.evaluate('typeof localIdentity!=="undefined" && !!localIdentity && !busy'),'consumer page');
  await login();
  await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'login');
  }
  await cdp.evaluate(`document.getElementById('station-link').click();const section=document.getElementById('radio-settings');if(!section.open)section.querySelector('summary').click();`);
  await until(()=>cdp.evaluate(`!document.getElementById('standalone-frequency-read').disabled`),'frequency availability');
  await click('standalone-frequency-read');
  await until(()=>cdp.evaluate(`!document.getElementById('standalone-frequency').disabled`),'unset readback');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),true);
  assert.match(await cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent`),firstUse && !['overlay','refusal'].includes(firstUse) ? /No applied station/ : /No WSPR dial frequency/);
  const ax=(await cdp.send('Accessibility.getFullAXTree')).nodes.find(node=>node.role?.value==='textbox' && node.name?.value==='WSPR dial frequency (Hz)');
  assert.ok(ax,'frequency has an explicit accessible label');
  assert.match(ax.description?.value || '',/Enter whole Hz without commas or decimals\. Standalone WSPR places four tones around a center 1,500 Hz above the dial\./);
  await capture('unset');
  if(firstUse==='refusal') {
    await field('standalone-frequency','14095600');
    assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),false);
    await control({op:'forget_engineering_station'});
    // Supply a current revision to isolate not_configured from the independently
    // tested stale-revision guard. The request still runs the production handler.
    await cdp.evaluate(`{const original=api;api=async(...args)=>{if(args[0]==='standalone-frequency' && args[1]==='PUT'){const fresh=await original('standalone-frequency','GET',undefined,undefined,30000,true);args[3]=fresh.revision;}return original(...args);};}`);
    await click('standalone-frequency-save');
    await until(()=>cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent.includes('No applied station')`),'production not_configured guidance');
    assert.doesNotMatch(await cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent`),/before another save/);
    assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'14095600');
    assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),true);
    await capture('not-configured-refusal');
    await click('standalone-frequency-read');
    await until(()=>cdp.evaluate(`!document.getElementById('standalone-frequency').disabled`),'missing station read');
    assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),true);
    console.log('PASS shipped production not_configured: actionable station guidance, retained dial, no read/save loop');
  } else if(firstUse) {
    await cdp.evaluate(`globalThis.frequencyWrites=[];globalThis.frequencyObservations=[];const original=api;api=async(...args)=>{if(args[0]==='standalone-frequency' && args[1]==='PUT')frequencyWrites.push(structuredClone(args[2]));try{const r=await original(...args);frequencyObservations.push({resource:args[0],revision:r.revision,target:r.data.target});return r;}catch(e){frequencyObservations.push({resource:args[0],error:e.message});throw e;}};`);
    const original=await control({op:'frequency_state'});
    await field('standalone-frequency','14095600');
    if(firstUse!=='overlay') {
      assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),true);
      assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').getAttribute('aria-invalid')`),'false');
      await click('standalone-frequency-save');
      assert.deepEqual(await cdp.evaluate('frequencyWrites'),[]);
      await capture('missing-station-draft-retained');
      for(const [id,value] of [['consumer-callsign','AA0NT'],['consumer-locator','EM18'],['consumer-power','37']]) await field(id,value);
      await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
      await until(()=>cdp.evaluate(`!busy && document.getElementById('standalone-frequency-status').textContent.includes('saved as a draft')`),'draft prerequisite');
      assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),true);
      assert.deepEqual(await control({op:'frequency_state'}),original);
      assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'14095600');
      await field('standalone-frequency','14095600');
      assert.match(await cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent`),/saved as a draft/);
      await capture('complete-saved-draft');
      await cdp.send('Emulation.setDeviceMetricsOverride',{width:1280,height:800,deviceScaleFactor:1,mobile:false});
      await cdp.evaluate(`document.getElementById('standalone-frequency-form').scrollIntoView({block:'start'});window.scrollBy(0,-400)`);
      const draftShot=await cdp.send('Page.captureScreenshot',{format:'jpeg',quality:92,captureBeyondViewport:false});
      await writeFile(path.join(output,'station-draft.jpg'),Buffer.from(draftShot.data,'base64'));

      await click('apply-station-progress');
      await until(()=>cdp.evaluate(`!busy && consumerAttempt!==null`),'explicit station submit');
      await control({op:'time',ms:'4000'});await control({op:'reboot'});
      await cdp.evaluate('refresh()');
      await login();
      await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'post-application login');
      await click('consumer-check-save');
      await until(()=>cdp.evaluate(`!busy && consumerAttempt===null && !document.getElementById('standalone-frequency-adopt').hidden`),'post-application target review');
      await click('standalone-frequency-adopt');
      assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),false,'post-application readiness without page reload');
    } else assert.equal(original.sequence,'0','no standalone journal required for applied overlay');
    assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'14095600');
    assert.match(await cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent`),/Station settings are applied|Save frequency/);
    await capture('applied-first-selection-ready');
    await cdp.evaluate(`document.getElementById('standalone-frequency').focus()`);
    for(let i=0;i<2;++i){await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});}
    assert.equal(await cdp.evaluate('document.activeElement.id'),'standalone-frequency-save');
    await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r'});
    await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
    await until(()=>cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent.includes('Saved WSPR dial 14,095,600 Hz for future')`),'first saved dial');
    let accepted=await control({op:'frequency_state'});
    assert.equal(accepted.saved_dial_hz,14095600);assert.equal(accepted.enabled,false);
    assert.equal(await cdp.evaluate('snapshot.job.output_active'),false);
    assert.equal((await cdp.evaluate('frequencyWrites')).length,1);
    await capture('first-save');
    if(process.argv[5]==='transmission') {
      await firstWsprTransmission({cdp,click,field,login,until,control,capture});
      accepted=await control({op:'frequency_state'});
    }
    await field('standalone-frequency','7038600');
    await cdp.evaluate(`globalThis.frequencyTransport=radio.fetcher;radio.fetcher=async()=>{throw Error('Synthetic lost connection before dispatch');};`);
    await click('standalone-frequency-save');
    await until(()=>cdp.evaluate(`!online`),'ambiguous disconnected save');
    await cdp.evaluate('radio.fetcher=frequencyTransport');
    assert.deepEqual(await control({op:'frequency_state'}),accepted,'ambiguous failed write leaves the journal unchanged');
    assert.equal((await cdp.evaluate('frequencyWrites')).length,2,'one explicit attempt; no automatic retry');
    await capture('ambiguous-save');
    await control({op:'reboot'});await cdp.evaluate('refresh()');
    await login();
    await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'reboot login');
    assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'7038600');
    assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),true);
    assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-adopt').hidden`),false);
    assert.deepEqual(await control({op:'frequency_state'}),accepted);
    await capture('reboot-draft-review');
    await cdp.evaluate(`document.documentElement.style.fontSize='200%'`);await capture('text-200-percent');
    const writes=await cdp.evaluate('frequencyWrites');
    await cdp.send('Page.reload');
    await until(()=>cdp.evaluate('typeof localIdentity!=="undefined" && !!localIdentity && !busy && !localAuthenticated'),'fresh page');
    await login();
    await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'fresh page login');
    await click('standalone-frequency-read');
    await until(()=>cdp.evaluate(`!document.getElementById('standalone-frequency').disabled`),'fresh persisted read');
    assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'14095600','unsaved dial is not committed after reload/reboot');
    assert.deepEqual(await control({op:'frequency_state'}),accepted);
    await writeFile(path.join(output,'first-use-result.json'),JSON.stringify({passed:true,profile:firstUse,original,accepted,writes,output_active:false,physical_qualification:false},null,2)+'\n');
    console.log('PASS shipped first-use '+firstUse+': prerequisite, draft, explicit apply, keyboard save, journal/reboot and identity review');
  } else {

  await cdp.send('Emulation.setDeviceMetricsOverride',{width:1280,height:720,deviceScaleFactor:1,mobile:false});
  await cdp.evaluate(`document.getElementById('standalone-frequency-form').scrollIntoView({block:'start'});window.scrollBy(0,-400)`);
  const docshot=await cdp.send('Page.captureScreenshot',{format:'jpeg',quality:92,captureBeyondViewport:false});
  await writeFile(path.join(output,'station-draft.jpg'),Buffer.from(docshot.data,'base64'));
  await cdp.evaluate(`globalThis.frequencyWrites=[];globalThis.frequencyFault=null;const original=api;api=async(...args)=>{if(args[0]==='standalone-frequency' && args[1]==='PUT'){frequencyWrites.push(structuredClone(args[2]));if(frequencyFault){args[2]={...args[2],target:{...args[2].target,device_id:'f'.repeat(32)}};}frequencyFault=null;}return original(...args);};`);
  await field('standalone-frequency','14095600.0');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),true);
  await field('standalone-frequency','14095600');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),false);
  assert.doesNotMatch(await cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent`),/without commas/);
  await cdp.evaluate(`document.getElementById('standalone-frequency').focus()`);
  for(let i=0;i<2;++i){await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});}
  assert.equal(await cdp.evaluate('document.activeElement.id'),'standalone-frequency-save');
  await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,nativeVirtualKeyCode:13,text:'\r'});
  await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
  await until(()=>cdp.evaluate(`!busy && document.getElementById('standalone-frequency-status').textContent.includes('Saved WSPR dial 14,095,600 Hz for future')`),'saved readback');
  assert.equal(await cdp.evaluate(`document.getElementById('config').elements.enabled.checked`),false,'frequency save does not enable a schedule');
  await field('standalone-frequency','bad');
  await click('standalone-frequency-discard');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'14095600');
  assert.match(await cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent`),/draft was discarded/);
  await capture('saved');
  await field('standalone-frequency','1000000');
  await click('standalone-frequency-save');
  await until(()=>cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent.includes('Read the saved frequency')`),'policy rejection');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'1000000');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),true);
  await capture('policy-rejected');
  await click('standalone-frequency-read');
  await until(()=>cdp.evaluate(`!document.getElementById('standalone-frequency').disabled`),'read after rejection');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'1000000');
  await click('standalone-frequency-discard');
  await field('standalone-frequency','3568737');
  // A second actual writer advances the journal revision after editor readback.
  await cdp.evaluate(`(async()=>{const response=await radio.request('standalone-frequency');const r={data:await response.json(),revision:response.headers.get('ETag')};await radio.request('standalone-frequency','PUT',{schema:r.data.schema,target:r.data.target,frequency_hz:14095600},r.revision);})()`);
  await click('standalone-frequency-save');
  await until(()=>cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent.includes('Read the saved frequency')`),'stale save');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'3568737');
  await capture('stale-revision');
  await click('standalone-frequency-read');
  await until(()=>cdp.evaluate(`!document.getElementById('standalone-frequency').disabled`),'fresh read');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'3568737');
  await click('standalone-frequency-save');
  await until(()=>cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent.includes('Saved WSPR dial 3,568,737')`),'save recovered draft');
  const committed=await cdp.evaluate(`(async()=>{const r=await api('standalone-frequency');return r.data;})()`);
  assert.equal(committed.frequency_hz,3568737);
  assert.equal(await cdp.evaluate(`document.getElementById('config').elements.enabled.checked`),false);
  await capture('recovered');
  await field('standalone-frequency','14095600');
  await cdp.evaluate(`frequencyFault='target'`); await click('standalone-frequency-save');
  await until(()=>cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent.includes('Pico identity changed')`),'wrong target');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'14095600');
  await capture('target-rejected');
  await control({op:'reboot'}); await cdp.evaluate('refresh()');
  await login();
  await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'new boot login');
  await click('standalone-frequency-read');
  await until(()=>cdp.evaluate(`!document.getElementById('standalone-frequency').disabled`),'new identity read');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-adopt').hidden`),false);
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),true);
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'14095600');
  await capture('identity-review');
  await click('standalone-frequency-adopt');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),false);
  await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:'dark'}]});
  assert.equal(await cdp.evaluate('getComputedStyle(document.documentElement).colorScheme'),'light');
  await cdp.evaluate(`document.documentElement.style.fontSize='200%'`); await capture('text-200-percent');
  await cdp.evaluate(`document.documentElement.style.fontSize=''`);
  await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:'light'}]});
  const persistedBeforeFault=await control({op:'frequency_state'});
  assert.equal(persistedBeforeFault.saved_dial_hz,3568737);
  await control({op:'flash_failure',fail:true});
  await click('standalone-frequency-save');
  await until(()=>cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent.includes('storage could not be verified')`),'persistence rejection');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'14095600');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),true);
  const failed=await cdp.evaluate(`(async()=>{const r=await api('standalone-frequency');return r.data;})()`);
  assert.equal(failed.frequency_hz,null); assert.equal(failed.storage_healthy,false);
  assert.deepEqual(await control({op:'frequency_state'}),persistedBeforeFault,'journal retains the committed dial and sequence; the unhealthy API withholds runnable settings');
  assert.equal(await cdp.evaluate(`document.getElementById('config').elements.enabled.checked`),false);
  await capture('storage-fault');
  const writes=await cdp.evaluate('frequencyWrites');
  assert.equal(writes[0].frequency_hz,14095600);
  assert(writes.every(w=>Number.isInteger(w.frequency_hz) && Object.keys(w).sort().join(',')==='frequency_hz,schema,target'));
  await writeFile(path.join(output,'frequency-writes.json'),JSON.stringify(writes,null,2)+'\n');
  await writeFile(path.join(output,'result.json'),JSON.stringify({passed:true,frequency_initial:null,frequency_saved_hz:3568737,policy_rejection:true,stale_recovery:true,target_rejection:true,identity_review:true,storage_fault:true,keyboard_save:true,text_zoom:200,themes:['light'],schedule_enabled:false,views:['desktop','mobile'],physical_qualification:false},null,2)+'\n');
  console.log('Consumer frequency UI: unset, explicit save, disabled schedules, desktop/mobile and accessible label passed');
  }
} finally {
  cdp?.ws.close();
  await cleanupUiProcesses([chrome,fixture],profile,{processGroup});
}
