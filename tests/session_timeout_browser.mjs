import {qualifyNativeChildren} from './ui_fixture_inventory.mjs';
// Shipped page/bundle -> Chrome -> production HTTP/AEAD; time and board are synthetic.
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,mkdir,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {launchChrome} from './chrome_startup.mjs';
import {Cdp} from './browser_cdp.mjs';
import {BrowserScope} from './browser_scope.mjs';
import {launchUiFixture} from './ui_fixture_process.mjs';
import {deadlinePromise,until as waitUntil} from './browser_deadline.mjs';

const driver=process.argv[2],output=path.resolve(process.argv[3] || 'build/session-timeout-browser');
if(!driver)throw Error('Usage: node tests/session_timeout_browser.mjs DRIVER [OUTPUT]');
const sensitivity=process.env.SESSION_PILOT_SENSITIVITY;
if(sensitivity!==undefined&&!['expiry','draft','mutation'].includes(sensitivity))throw Error('Unknown session pilot sensitivity mode');
const holdInitialization=process.env.SESSION_PILOT_HOLD_INIT==='1';
const processGroup=process.platform!=='win32';
const scope=new BrowserScope();
let profile,fixture,browser,cdp,now=1000,browserAcquired=false,expiryClip=null,faultEntered=false,bodyPrimary;
const send=(method,params={})=>cdp.send(method,params);
const evaluate=expression=>cdp.evaluate(expression);
const until=(fn,label)=>waitUntil(fn,label,15000);
async function control(command) {
    return deadlinePromise('fixture-control',(resolve,reject)=>{
        const abort=new AbortController();
        (async()=>{
            const response=await fetch('http://127.0.0.1:19139/.fixture-control',{method:'POST',body:JSON.stringify(command),signal:AbortSignal.any([abort.signal,scope.signal])});
            assert.equal(response.status,200);const result=await response.json();
            assert.ok(result&&typeof result==='object'&&!Array.isArray(result),'actual driver acknowledgement');return result;
        })().then(resolve,reject);
        return()=>abort.abort();
    },15000);
}
async function journal() {
    const value=await control({op:'frequency_state'});
    assert.deepEqual(Object.keys(value).sort(),['enabled','saved_dial_hz','sequence']);
    assert.equal(typeof value.enabled,'boolean');
    assert.ok(value.saved_dial_hz===null||Number.isSafeInteger(value.saved_dial_hz)&&value.saved_dial_hz>=0);
    assert.ok(typeof value.sequence==='string'&&/^[0-9]{1,20}$/.test(value.sequence)&&BigInt(value.sequence)<=0xffffffffffffffffn);
    return value;
}
async function time(ms) {
    now=ms;
    const actual=sensitivity==='expiry'&&expiryClip!==null?Math.min(ms,expiryClip):ms;
    assert.deepEqual(await control({op:'time',ms:String(actual)}),{});
    await evaluate('globalThis.sessionTestTime='+actual);
    if(actual!==ms)faultEntered=true; // Both clock seams acknowledged the bounded frozen-clock defect.
}
async function login() {
    // The shared fixture advances the device by one second on login start.
    now+=1000;
    await evaluate("document.getElementById('access-toggle').click()");
    await evaluate(`globalThis.sessionTestTime=${now};document.getElementById('local-password').value='test-password';document.getElementById('local-login').requestSubmit()`);
    await until(()=>evaluate('!busy && localAuthenticated && online'),'login');
}
async function refresh() {
    await evaluate("document.getElementById('refresh').click()");
    await until(()=>evaluate('!busy'),'refresh');
}
async function expiredLockFeedback() {
    assert.equal(await evaluate('authenticationLockApplies(document.getElementById("access-toggle"))'),true,'expired-session lock remains a keyboard feedback route');
    await send('Page.bringToFront');
    await evaluate('document.getElementById("device-name").focus()');
    await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',modifiers:8,windowsVirtualKeyCode:9});
    await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',modifiers:8,windowsVirtualKeyCode:9});
    assert.equal(await evaluate('document.activeElement.id'),'access-toggle');
    await until(()=>evaluate('!document.getElementById("locked-control-tooltip").hidden'),'expired-session lock feedback');
    assert.equal(await evaluate('document.getElementById("locked-control-tooltip").textContent'),'Controls are locked');
    await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
    await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
    assert.equal(await evaluate('document.getElementById("locked-control-tooltip").hidden'),true);
}
async function capture(state) {
    if(process.env.UI_REVIEW_NO_CAPTURE==='1')return;
    for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]) {
        await send('Emulation.setDeviceMetricsOverride',{width:view.width,height:view.height,deviceScaleFactor:1,mobile:view.name==='mobile'});
        await evaluate("document.getElementById('local-access').scrollIntoView({block:'start'})");
        assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
        const shot=await send('Page.captureScreenshot',{format:'png'});
        await writeFile(path.join(output,state+'-'+view.name+'.png'),Buffer.from(shot.data,'base64'));
    }
}
try{await scope.run(async()=>{
  try{
    await mkdir(output,{recursive:true});
    profile=await scope.own(mkdtemp(path.join(os.tmpdir(),`pico-session-browser-${process.pid}-`)),async value=>{if(!browserAcquired)await rm(value,{recursive:true,force:true});});
    fixture=await scope.own(launchUiFixture(driver,19139,output,{profiles:['consumer-lan'],processGroup}),value=>value.stop());
    if(holdInitialization)await deadlinePromise('observed-initialization-hold',(resolve,reject)=>{
      const interrupted=()=>reject(scope.signal.reason||Error('initialization interrupted'));
      scope.signal.addEventListener('abort',interrupted);if(scope.signal.aborted)interrupted();
      process.send?.({kind:'session-pilot-initialization-held/1'});
      return()=>scope.signal.removeEventListener('abort',interrupted);
    },15000);
    const nativeProfiles=await fixture.ready;
    await qualifyNativeChildren(driver,fixture.process.pid,nativeProfiles);
    console.log(JSON.stringify({kind:'native-fixture-inventory/1',owner:fixture.process.pid,count:nativeProfiles.length,profiles:nativeProfiles.map(value=>value.name)}));
    const initialJournal=await journal();
    assert.deepEqual(nativeProfiles.map(value=>value.name),['consumer-lan']);
    const chrome=launchChrome(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
        '--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check',
        '--remote-debugging-port=0','--user-data-dir='+profile,'--proxy-server=http://127.0.0.1:19139',
        '--proxy-bypass-list=<-loopback>','about:blank'],profile,{processGroup});
    browserAcquired=true;browser=await scope.own(chrome,value=>value.stop());
    const pages=await browser.ready;
    cdp=await scope.own(new Cdp(pages.find(page=>page.type==='page').webSocketDebuggerUrl),value=>value.stop());await cdp.open();
    await send('Page.enable');
    await send('Page.navigate',{url:'http://192.168.1.53/'});
    await until(()=>evaluate('typeof radio!=="undefined" && !!radio && !busy'),'shipped consumer page');
    // Positive runs replace only the clock seam. Named isolated sensitivity
    // runs below deliberately introduce defects; no production source is edited.
    await evaluate('globalThis.sessionTestTime=1000;radio.now=()=>globalThis.sessionTestTime;globalThis.sessionRequests=[];const sessionRequest=radio.request.bind(radio);radio.request=(...args)=>{sessionRequests.push({path:args[0],method:args[1]||"GET"});return sessionRequest(...args)}');
    await login();
    const started=now;expiryClip=started+1800000-1;
    await evaluate('document.querySelector("[name=schedules]").value="240 / 0";document.getElementById("config").dispatchEvent(new Event("input",{bubbles:true}))');
    const draft=()=>evaluate('document.querySelector("[name=schedules]").value');
    if(sensitivity==='draft')await evaluate(`{const clear=radio.clear.bind(radio);radio.clear=()=>{clear();document.getElementById('config').reset();globalThis.sessionSensitivityFaultEntered=true;};}`);
    await time(started+300000);assert.equal(await evaluate('radio.authenticated'),true);
    await time(started+1800000-1);await refresh();
    assert.equal(await evaluate('radio.authenticated && localAuthenticated'),true);
    const renewed=started;
    await time(renewed+1800000-1);
    await evaluate('document.querySelector("[name=schedules]").dispatchEvent(new Event("input",{bubbles:true}));radio.identity()');
    await time(renewed+1800000);await refresh();
    assert.equal(await evaluate('radio.authenticated'),false,'Session expiry must retire authority');
    assert.equal(await evaluate('document.getElementById("access-toggle").getAttribute("aria-label")'),'Unlock controls');
    assert.equal(await evaluate('document.getElementById("local-access").open'),false);
    assert.equal(await evaluate('document.getElementById("local-login").hidden'),false);
    assert.equal(await evaluate('document.getElementById("save-config").disabled'),true);
    assert.equal(await draft(),'240 / 0','Expired sessions must preserve the unsaved draft');
    await expiredLockFeedback();
    await capture('idle-expired');
    await login();
    assert.equal(await draft(),'240 / 0','Expired sessions must preserve the unsaved draft');
    assert.equal(await evaluate('writeState'),'review');
    const fresh=now;
    for(let elapsed=1000000;elapsed<28800000;elapsed+=1000000){await time(fresh+elapsed);await evaluate('radio.request("management")');await refresh();assert.equal(await evaluate('radio.authenticated'),true);}
    await time(fresh+28800000-1);await refresh();
    assert.equal(await evaluate('radio.authenticated'),true);
    await time(fresh+28800000);await refresh();
    assert.equal(await evaluate('radio.authenticated'),false,'Session expiry must retire authority');
    assert.equal(await draft(),'240 / 0','Expired sessions must preserve the unsaved draft');
    assert.equal(await evaluate('document.getElementById("save-config").disabled'),true);
    assert.deepEqual(await evaluate('sessionRequests.filter(request=>!["GET"].includes(request.method))'),[],'Locked workflows must not dispatch mutations');
    if(sensitivity==='mutation'){assert.deepEqual(await control({op:'sensitivity_saved_mutation'}),{});faultEntered=true;}
    assert.deepEqual(await journal(),initialJournal,'Locked workflows must not persist configuration');
    await expiredLockFeedback();
    await capture('absolute-expired');
    const result={browser:(await send('Browser.getVersion')).product,virtual_time:true,fixture_profiles:['consumer-lan'],fixture_driver_starts:nativeProfiles.length,idle_boundary_ms:1800000,absolute_boundary_ms:28800000,public_and_edit_activity_do_not_renew:true,draft_preserved:true,readback_review_required:true,no_mutations:true,journal_unchanged:true,screenshots:process.env.UI_REVIEW_NO_CAPTURE==='1'?0:4};
    await writeFile(path.join(output,'results.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify(result));
  }catch(primary){
    bodyPrimary=primary;
    if(sensitivity&&cdp){
      try{faultEntered ||=!!await cdp.evaluate('globalThis.sessionSensitivityFaultEntered===true');}
      catch(diagnostic){throw new AggregateError([primary,diagnostic],'pilot assertion and fault-observation failed');}
    }
    throw primary;
  }
});}catch(error){
  if(sensitivity){
    const labels={expiry:'Session expiry must retire authority',draft:'Expired sessions must preserve the unsaved draft',mutation:'Locked workflows must not persist configuration'};
    console.error(JSON.stringify({kind:'session-pilot-sensitivity/1',mode:sensitivity,fault_entered:faultEntered,assertion_detected:error.code==='ERR_ASSERTION'&&error.message.includes(labels[sensitivity]),cleanup_completed:error===bodyPrimary}));
  }
  throw error;
}
