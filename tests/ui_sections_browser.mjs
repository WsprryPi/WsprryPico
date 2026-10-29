// Shipped page/bundle -> Chrome -> production HTTP/AEAD; time and board are synthetic.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile,mkdir} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {cleanupUiProcesses} from './ui_process_cleanup.mjs';

const carrier=process.argv[4] || 'consumer';
const proxyPort=carrier==='engineering' ? 19154 : 19149;
const driver=process.argv[2],output=path.resolve(process.argv[3] || 'build/ui-sections-browser');
if(!driver)throw Error('Usage: node tests/ui_sections_browser.mjs DRIVER [OUTPUT]');
await mkdir(output,{recursive:true});
const profile=await mkdtemp(path.join(os.tmpdir(),'pico-session-browser-'));
const processGroup=process.platform==='linux';
let fixture,chrome,ws,serial=0,now=1000;
const pending=new Map();
function send(method,params={}) {
    const id=++serial;
    return new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>{pending.delete(id);reject(Error('Browser deadline: '+method));},15000);
        pending.set(id,{resolve:value=>{clearTimeout(timer);resolve(value);},reject:error=>{clearTimeout(timer);reject(error);}});
        ws.send(JSON.stringify({id,method,params}));
    });
}
async function evaluate(expression) {
    const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
    if(result.exceptionDetails)throw Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    return result.result.value;
}
async function until(fn,label) {
    const end=Date.now()+15000;
    while(Date.now()<end){if(await fn())return;await new Promise(resolve=>setTimeout(resolve,40));}
    throw Error('Timed out: '+label);
}
async function control(value) {
    const response=await fetch('http://127.0.0.1:19149/.fixture-control',{method:'POST',body:JSON.stringify(value)});
    assert.equal(response.status,200);return response.json();
}
async function click(id) {await evaluate(`document.getElementById(${JSON.stringify(id)}).click()`);}
async function section(id) {await evaluate(`(()=>{const node=document.getElementById('${id}'),area=node.closest('[data-task-area]').dataset.taskArea;history.pushState({...history.state,wsprrypicoPresentation:{section:'${id}',area}},'','/'+area+(/^#(?:save|hostname-return)=/.test(location.hash)?location.hash:'#${id}'));dispatchEvent(new PopStateEvent('popstate'));})()`);}
async function key(key,code=key) {
    await send('Input.dispatchKeyEvent',{type:'keyDown',key,code,text:key==='Enter'?'\r':undefined,windowsVirtualKeyCode:key==='Escape'?27:key==='Enter'?13:9});
    await send('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:key==='Escape'?27:key==='Enter'?13:9});
}
async function idle() {await until(()=>evaluate('typeof busy!=="undefined" && !busy'),'serialized request finished');}
async function navigate(hash='') {
    await send('Page.navigate',{url:'about:blank'});
    await until(()=>evaluate('location.href==="about:blank"').catch(()=>false),'blank document');
    await send('Page.navigate',{url:'http://192.168.1.53/'+hash});
    await until(()=>evaluate('typeof accessCarrier!=="undefined" && (!!localIdentity || accessCarrier==="certificate") && !busy'),'shipped admitted page');
}
async function login(password='test-password') {
    await click('access-toggle');
    assert.equal(await evaluate('document.activeElement.id'),'local-password');
    await evaluate(`document.getElementById('local-password').value=${JSON.stringify(password)}`);
    // Polling can briefly disable submission. Submit exactly once when the
    // native form is available; keyboard Enter is covered by the shipped UI fixture.
    await until(()=>evaluate('!busy && !document.getElementById("login-submit").disabled && (document.getElementById("local-login").requestSubmit(),true)'),'login submit available');
    await idle();
}
const checks=[];
function pass(name){checks.push(name);console.log('PASS '+name);}
async function capture(state,dialog=false) {
    for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844},{name:'landscape',width:740,height:360}]) {
        await send('Emulation.setDeviceMetricsOverride',{width:view.width,height:view.height,deviceScaleFactor:1,mobile:view.name!=='desktop'});
        if(!dialog)await evaluate('scrollTo(0,0)');
        assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'no horizontal overflow');
        if(process.env.UI_REVIEW_NO_CAPTURE==='1')continue;
        const shot=await send('Page.captureScreenshot',{format:'png'});
        await writeFile(path.join(output,state+'-'+view.name+'.png'),Buffer.from(shot.data,'base64'));
    }
}
try {
    let fixtureLog='';
    fixture=spawn(process.execPath,['tests/ui_review_fixture.mjs',driver,'19149',output],{stdio:['ignore','pipe','pipe'],detached:processGroup});
    fixture.stdout.on('data',data=>fixtureLog+=data);fixture.stderr.on('data',data=>fixtureLog+=data);
    await until(()=>fixtureLog.includes('READY;'),'fixture startup');
    chrome=spawn(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
        '--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check',
        '--remote-debugging-port=0','--user-data-dir='+profile,'--proxy-server=http://127.0.0.1:'+proxyPort,
        '--proxy-bypass-list=<-loopback>','about:blank'],{stdio:'ignore',detached:processGroup});
    let debugPort;
    await until(async()=>{try{debugPort=Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);return !!debugPort;}catch{return false;}},'Chrome startup');
    const pages=await(await fetch('http://127.0.0.1:'+debugPort+'/json')).json();
    ws=new WebSocket(pages.find(page=>page.type==='page').webSocketDebuggerUrl);
    ws.onmessage=event=>{const value=JSON.parse(event.data);if(value.method==='Page.javascriptDialogOpening'){void send('Page.handleJavaScriptDialog',{accept:true});return;}const request=pending.get(value.id);if(request){pending.delete(value.id);value.error?request.reject(Error(value.error.message)):request.resolve(value.result);}};
    await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});await send('Page.enable');
    await until(()=>evaluate('!!document.documentElement').catch(()=>false),'active Chrome page');
    await navigate();
    if(carrier==='engineering') {
      assert.equal(await evaluate('accessCarrier'),'certificate');
      assert.equal(await evaluate('document.getElementById("access-toggle").getAttribute("aria-label")'),'Certificate access information');
      await click('access-toggle');
      assert.equal(await evaluate('document.getElementById("local-access").open'),true);
      assert.equal(await evaluate('document.getElementById("local-login").hidden'),true);
      assert.match(await evaluate('document.getElementById("local-description").textContent'),/cannot revoke/);
      assert.equal(await evaluate('online'),true);await key('Escape');
      assert.equal(await evaluate('online'),true);
      pass('certificate carrier retains authority and explains browser-managed certificate access');
    } else {
    assert.equal(await evaluate('document.querySelectorAll("[data-operator-section][open]").length'),0);
    assert.equal(await evaluate('document.getElementById("local-access").open'),false);
    assert.notEqual(await evaluate('document.activeElement.id'),'local-password');
    assert.equal(await evaluate('document.getElementById("transmitter-status").getBoundingClientRect().height>0'),true);
    assert.equal(await evaluate('document.querySelectorAll("h1").length'),1);
    assert.equal(await evaluate('new Set([...document.querySelectorAll("[id]")].map(e=>e.id)).size===document.querySelectorAll("[id]").length'),true);
    pass('fresh entry, one heading, unique IDs, closed modal and disclosures, public status');
    await evaluate(`document.getElementById('message-text').value='CQ CQ DE AA0NT EM18 QRSS TEST 73';const transfer=new DataTransfer();transfer.items.add(new File(['{}'],'draft.json',{type:'application/json'}));document.getElementById('job-file').files=transfer.files;globalThis.originalFile=document.getElementById('job-file').files[0]`);
    const ids=await evaluate('[...document.querySelectorAll("[data-operator-section]")].map(e=>e.id)');
    for(const id of ids) {
        await section(id);
        assert.equal(await evaluate(`document.getElementById('${id}').open`),true);
        assert.equal(await evaluate(`document.activeElement===document.getElementById('${id}').querySelector('summary')`),true);
        await evaluate(`document.getElementById('${id}').querySelector('[data-top]').click()`);
        assert.equal(await evaluate('document.querySelectorAll("[data-operator-section][open]").length'),0);
        assert.equal(await evaluate('document.activeElement.id'),'device-name');
    }
    assert.equal(await evaluate('document.getElementById("message-text").value'),'CQ CQ DE AA0NT EM18 QRSS TEST 73');
    assert.equal(await evaluate('document.getElementById("job-file").files[0]===originalFile'),true);
    pass('section bookmarks and Top links changes only presentation, preserves message and selected file');
    await section('message-section');await section('wifi-settings');
    await evaluate('history.back()');await until(()=>evaluate('!document.getElementById("station-area").hidden'),'Back selects station');
    await evaluate('history.forward()');await until(()=>evaluate('!document.getElementById("wifi-host-area").hidden'),'Forward selects Wi-Fi');
    const receipt='#save='+encodeURIComponent(JSON.stringify({kind:'station',device:'1'.repeat(32),generation:'1',digest:'a'.repeat(64)}));
    await evaluate(`history.replaceState({retained:'unrelated'},'',location.pathname+${JSON.stringify(receipt)})`);
    await section('message-section');
    assert.equal(await evaluate('location.hash'),receipt);assert.equal(await evaluate('history.state.retained'),'unrelated');
    await evaluate('document.getElementById("message-section").querySelector("[data-top]").click()');
    assert.equal(await evaluate('location.hash'),receipt);
    await section('wifi-settings');await evaluate('history.back()');
    await until(()=>evaluate('document.activeElement.id==="device-name"'),'receipt Top history');
    assert.equal(await evaluate('document.querySelectorAll("[data-operator-section][open]").length'),0);
    await evaluate('history.forward()');await until(()=>evaluate('document.getElementById("wifi-settings").open'),'receipt Forward section');
    await evaluate('globalThis.sectionReloadMarker=true');await send('Page.reload');
    await until(()=>evaluate('!globalThis.sectionReloadMarker && typeof localIdentity!=="undefined" && !!localIdentity && !busy').catch(()=>false),'new document receipt reload');
    assert.equal(await evaluate('document.getElementById("saved-settings").open'),true);
    assert.equal(await evaluate('location.hash'),receipt);
    pass('receipt bytes and unrelated History data survive section/Top, reload exposes recovery');
    await navigate('#hostname-form');assert.equal(await evaluate('document.getElementById("hostname-section").open'),true);
    assert.equal(await evaluate('document.getElementById("wifi-host-area").hidden'),false);
    await navigate('#%ZZ');assert.equal(await evaluate('document.querySelectorAll("[data-operator-section][open]").length'),0);
    pass('legacy section bookmark and malformed fragment fail safely');
    await click('access-toggle');assert.equal(await evaluate('document.activeElement.id'),'local-password');
    for(let tab=0;tab<12;tab++){await key('Tab');assert.equal(await evaluate('document.getElementById("local-access").contains(document.activeElement)'),true,JSON.stringify(await evaluate('[...document.getElementById("local-access").querySelectorAll("button,input,summary")].map(e=>({id:e.id,tag:e.tagName,tabIndex:e.tabIndex,rects:e.getClientRects().length,disabled:e.matches(":disabled"),active:e===document.activeElement}))')));}
    await send('Input.dispatchMouseEvent',{type:'mousePressed',x:1,y:1,button:'left',clickCount:1});
    await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:1,y:1,button:'left',clickCount:1});
    assert.equal(await evaluate('document.getElementById("local-access").open'),true);
    await evaluate('document.getElementById("local-password").value="synthetic-cancel"');await key('Escape');
    assert.equal(await evaluate('document.getElementById("local-access").open'),false);assert.equal(await evaluate('document.activeElement.id'),'access-toggle');
    assert.equal(await evaluate('document.getElementById("local-password").value'),'');
    await login('wrong-password');assert.equal(await evaluate('localAuthenticated'),false);
    assert.equal(await evaluate('document.getElementById("local-access").open'),true);
    assert.match(await evaluate('document.getElementById("local-status").textContent'),/rejected|refused|wrong/i);
    assert.equal(await evaluate('document.getElementById("local-password").value'),'');
    await click('access-close');
    await evaluate('(async()=>{globalThis.occupied=[];for(let i=0;i<3;i++){const client=WsprryPicoConsumerRadio.createClient();await client.login("test-password",await client.identity());occupied.push(client)}})()');
    await login();
    assert.equal(await evaluate('localAuthenticated'),false);
    assert.match(await evaluate('document.getElementById("local-status").textContent'),/three|capacity|in use/i);
    await evaluate('document.getElementById("login-recovery").open=true');await click('inspect-logins');await idle();
    assert.equal(await evaluate('document.getElementById("retirement-target").options.length'),4);
    await evaluate('document.getElementById("retirement-target").value=document.getElementById("retirement-target").options[1].value;document.getElementById("retirement-target").dispatchEvent(new Event("change"));document.getElementById("retirement-password").value="test-password"');
    await click('retire-login');await idle();
    assert.match(await evaluate('document.getElementById("retirement-status").textContent'),/retired/);
    assert.equal(await evaluate('localAuthenticated'),false);
    await evaluate('(async()=>{for(const client of occupied)await client.logout().catch(()=>{});occupied=[]})()');
    await click('access-close');await login();
    assert.equal(await evaluate('localAuthenticated && radio.authenticated'),true);
    assert.equal(await evaluate('document.getElementById("local-access").open'),false);
    assert.equal(await evaluate('document.activeElement.id'),'access-toggle');
    pass('native modal focus, Escape, password refusal, scrub and authenticated success');
    await section('message-section');
    await evaluate('document.getElementById("message-text").value="DRAFT";document.getElementById("message-form").dispatchEvent(new Event("input",{bubbles:true}));globalThis.savedRequest=radio.request.bind(radio);globalThis.requestOrder=[];radio.request=async(...args)=>{requestOrder.push(args[0]);if(args[0]==="operations")await new Promise(resolve=>globalThis.releaseRead=resolve);return savedRequest(...args)};document.getElementById("refresh").click()');
    await until(()=>evaluate('!!globalThis.releaseRead'),'held current request');
    await click('access-toggle');assert.equal(await evaluate('document.getElementById("save-config").disabled'),true);
    assert.equal(await evaluate('localAuthenticated'),false);
    assert.equal(await evaluate('document.getElementById("console-message").textContent'),'Unavailable');
    assert.equal(await evaluate('requestOrder.includes("consumer/logout")'),false);
    await evaluate('releaseRead()');await idle();
    assert.equal(await evaluate('radio.authenticated'),false);assert.equal(await evaluate('requestOrder.at(-1)'),'consumer/logout');
    assert.equal(await evaluate('document.getElementById("message-text").value'),'DRAFT');
    // Exercise the actual registered interval without waiting five wall-clock seconds.
    await evaluate('globalThis.publicReads=0;const savedPublic=radio.publicRead.bind(radio);radio.publicRead=(...args)=>{publicReads++;return savedPublic(...args)}');
    await until(()=>evaluate('publicReads>0'),'public polling continues after logout');
    await evaluate('radio.request=savedRequest');
    pass('lock gates immediately, clears private status, serializes logout and keeps public polling');
    await login();
    await evaluate('radio.logout=async()=>{throw Error("synthetic lost logout") }');await click('access-toggle');await idle();
    assert.equal(await evaluate('radio.authenticated'),false);assert.match(await evaluate('document.getElementById("notice").textContent'),/unconfirmed/);
    pass('lost logout clears local authority and reports remote uncertainty');
    await navigate();
    await evaluate('globalThis.originalLogin=radio.login.bind(radio);globalThis.originalLogout=radio.logout.bind(radio);globalThis.cancelLogoutCount=0;radio.logout=async()=>{cancelLogoutCount++;return originalLogout()};radio.login=async(...args)=>{await originalLogin(...args);await new Promise(resolve=>globalThis.releaseLogin=resolve)}');
    await click('access-toggle');await evaluate('document.getElementById("local-password").value="test-password";document.getElementById("local-login").requestSubmit()');
    await until(()=>evaluate('!!globalThis.releaseLogin'),'late successful login');
    await click('access-close');await evaluate('releaseLogin()');await idle();
    assert.equal(await evaluate('radio.authenticated || localAuthenticated'),false);assert.equal(await evaluate('cancelLogoutCount'),1);
    assert.equal(await evaluate('document.getElementById("local-access").open'),false);
    pass('cancelled late login cannot ghost-unlock and cleans only its serialized session');
    for(const [button,resource] of [['rf-calibration-read','rf-calibration'],['ntp-timeout-read','ntp-timeout'],['gpio-drive-read','gpio-drive']]) {
      await navigate();await login();await section(resource==='gpio-drive'?'radio-pins':'radio-settings');
      await evaluate(`globalThis.editorRequest=radio.request.bind(radio);globalThis.editorOrder=[];radio.request=async(...args)=>{editorOrder.push(args[0]);if(args[0]==='${resource}')await new Promise(resolve=>globalThis.releaseEditor=resolve);return editorRequest(...args)}`);
      await click(button);await until(()=>evaluate('!!globalThis.releaseEditor'),'held editor');
      assert.equal(await evaluate('busy'),true);await click('access-toggle');
      assert.equal(await evaluate('editorOrder.includes("consumer/logout")'),false);
      await evaluate('releaseEditor()');await idle();
      assert.equal(await evaluate('radio.authenticated'),false);
      assert.equal(await evaluate('editorOrder.at(-1)'),'consumer/logout');
      assert.equal(await evaluate('document.getElementById("rf-calibration-discard").matches(":disabled") && document.getElementById("ntp-timeout-discard").matches(":disabled")'),true);
    }
    pass('all standalone editors drain before logout and invalidate private readbacks');
    await navigate();await login();
    await control({op:'message_review'});await click('refresh');await idle();
    await section('radio-settings');await click('rf-calibration-read');await idle();
    await evaluate('document.getElementById("rf-manual-ppm").value="1.000";document.getElementById("rf-manual-ppm").dispatchEvent(new Event("input"));globalThis.mutationRequest=radio.request.bind(radio);radio.request=async(...args)=>{if(args[0]==="rf-calibration"&&args[1]==="PUT"){await new Promise(resolve=>globalThis.releaseMutation=resolve);const response=await mutationRequest(...args);const value=await response.json();return {...response,json:async()=>({...value,saved:{mode:"manual",manual_ppm:"2.000"}})}}return mutationRequest(...args)}');
    await click('rf-calibration-save');await until(()=>evaluate('!!globalThis.releaseMutation'),'held settings mutation');
    await evaluate('document.getElementById("radio-settings").querySelector("[data-top]").click()');
    await evaluate('releaseMutation()');await idle();
    assert.equal(await evaluate('document.getElementById("radio-settings").open'),false);
    assert.equal(await evaluate('document.getElementById("radio-result-reveal").hidden'),false);
    assert.equal(await evaluate('document.getElementById("notice").classList.contains("error")'),true);
    await click('radio-result-reveal');assert.equal(await evaluate('document.getElementById("radio-settings").open'),true);
    assert.equal(await evaluate('document.getElementById("rf-manual-ppm").value'),'1.000');
    await evaluate('radio.request=mutationRequest');
    pass('Top cannot hide a failed mutation; global error/reveal preserves the entry');
    await section('message-section');
    assert.equal(await evaluate('document.getElementById("message-settings").disabled'),false);
    await evaluate('document.querySelectorAll("#message-section details").forEach(e=>e.open=true);document.getElementById("message-text").required=true;document.getElementById("message-text").value="";document.getElementById("message-section").open=false;document.getElementById("message-form").reportValidity()');
    assert.equal(await evaluate('document.getElementById("message-section").open'),true);
    assert.equal(await evaluate('document.activeElement.id'),'message-text');
    await evaluate('document.getElementById("message-section").querySelector("[data-top]").click()');
    assert.equal(await evaluate('[...document.querySelectorAll("[data-operator-section] details")].some(e=>e.open)'),false);
    pass('invalid hidden controls reveal before focus; Top closes managed nested disclosures');
    await evaluate('document.getElementById("device-name").textContent="x".repeat(63)+".local"');
    await capture('compact');
    await click('access-toggle');await idle();await click('access-toggle');await evaluate('document.getElementById("device-name").textContent="pico-example.local"');await capture('password-dialog',true);await key('Escape');
    await send('Emulation.setDeviceMetricsOverride',{width:320,height:700,deviceScaleFactor:1,mobile:false});
    await evaluate('document.documentElement.style.fontSize="32px"');
    assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,JSON.stringify(await evaluate('[...document.querySelectorAll("body *")].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,id:e.id,right:e.getBoundingClientRect().right})).slice(0,20)')));
    if(process.env.UI_REVIEW_NO_CAPTURE!=='1'){const zoomShot=await send('Page.captureScreenshot',{format:'png'});await writeFile(path.join(output,'zoom.png'),Buffer.from(zoomShot.data,'base64'));}
    pass('desktop/mobile/landscape, long hostname, zoom and native dialog rendering');
    }
    const result={carrier,browser:(await send('Browser.getVersion')).product,checks,physical_device:false};
    await writeFile(path.join(output,'results.json'),JSON.stringify(result,null,2)+'\n');
} catch(error) {
    console.error('UI failure state',await evaluate('JSON.stringify({busy,online,carrier:accessCarrier,authenticated:localAuthenticated,notice:document.getElementById("notice").textContent,focus:document.activeElement.id,open:[...document.querySelectorAll("[data-operator-section][open]")].map(e=>e.id)})').catch(()=>null));
    throw error;
} finally {
    if(ws){await send('Browser.close').catch(()=>{});ws.close();}await cleanupUiProcesses([chrome,fixture],profile,{processGroup});
}
