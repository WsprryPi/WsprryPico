// Shipped page/bundle -> Chrome -> production HTTP/AEAD; time and board are synthetic.
import assert from 'node:assert/strict';
import {checkLockedControls} from './locked_controls_browser.mjs';
import {checkSi5351} from './si5351_ui_checks.mjs';
import {checkGps} from './gps_ui_checks.mjs';
import {checkGrayLine} from './gray_line_ui_checks.mjs';
import {checkHardwareSaveIsolation} from './hardware_save_checks.mjs';
import {checkControlAlignment} from './control_alignment_checks.mjs';
import {checkContextualHelp} from './contextual_help_browser.mjs';
import {execFileSync} from 'node:child_process';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {BrowserHarness,until,fixtureJson,navigationTransient} from './browser_harness.mjs';
const h=new BrowserHarness();
await h.run(async()=>{

const carrier=process.argv[4] || 'consumer';
if(!['consumer','engineering','field'].includes(carrier))throw Error('Unknown section carrier');
const proxyPort=carrier==='engineering' ? 19154 : carrier==='field' ? 19153 : 19149;
const driver=process.argv[2],output=path.resolve(process.argv[3] || 'build/ui-sections-browser');
if(!driver)throw Error('Usage: node tests/ui_sections_browser.mjs DRIVER [OUTPUT]');
await mkdir(output,{recursive:true});
let profile=await h.profile('pico-session-browser-');
let fixture,chrome,cdp,now=1000;
const send=(...args)=>cdp.send(...args);
const evaluate=expression=>cdp.evaluate(expression);

async function control(value) {
    return fixtureJson('http://127.0.0.1:'+proxyPort+'/.fixture-control',{method:'POST',body:JSON.stringify(value)});
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
    await until(()=>evaluate('location.href==="about:blank"').catch(navigationTransient),'blank document');
    await send('Page.navigate',{url:(carrier==='field'?'http://192.168.4.1/station':'http://192.168.1.53/')+hash});
    await until(()=>evaluate('typeof accessCarrier!=="undefined" && (!!localIdentity || accessCarrier==="certificate") && !busy'),'shipped admitted page');
}
async function login(password='test-password') {
    await until(()=>evaluate('!busy && !submissions.pending && !accessClosing && !accessLoginPending'),'login request owner available');
    await click('access-toggle');
    assert.equal(await evaluate('document.activeElement.id'),'local-password');
    // Polling can briefly disable submission. Submit exactly once when the
    // native form is available; keyboard Enter is covered by the shipped UI fixture.
    await until(()=>evaluate(`!busy && !submissions.pending && !accessClosing && !accessLoginPending && !document.getElementById('login-submit').matches(':disabled') && (document.getElementById('local-password').value=${JSON.stringify(password)},document.getElementById('local-login').requestSubmit(),true)`),'login submit available');
    await idle();
}
const helpWindows=[];
const checks=[];
function pass(name){checks.push(name);console.log('PASS '+name);}
async function capture(state,dialog=false) {
    for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844},{name:'landscape',width:740,height:360}]) {
        await send('Emulation.setDeviceMetricsOverride',{width:view.width,height:view.height,deviceScaleFactor:1,mobile:view.name!=='desktop'});
        if(state==='contextual-help')await evaluate('document.getElementById("radio-settings").scrollIntoView({block:"start"})');
        else if(state==='time-calibration'||state==='beacon-saved-grid')await evaluate('document.getElementById("time-calibration").scrollIntoView({block:"start"})');
        else if(state==='beacon-conflict-comparison')await evaluate('Array.from(document.querySelectorAll("#draft-comparison h4")).find(e=>e.textContent==="Automatic beacon schedule").scrollIntoView({block:"center"})');
        else if(state==='field-settings')await evaluate('document.getElementById("field-access").scrollIntoView({block:"start"})');
        else if(state==='si5351-details')await evaluate('document.querySelector("[data-si-status]").scrollIntoView({block:"end"})');
        else if(state==='si5351-settings')await evaluate('document.getElementById("si5351-settings").scrollIntoView({block:"start"})');
        else if(state.startsWith('gray-line'))await evaluate('document.getElementById("gray-line-controls").scrollIntoView({block:"start"})');
        else if(state.startsWith('gps-'))await evaluate('document.getElementById("gps-settings").scrollIntoView({block:"start"})');
        else if(!dialog)await evaluate('scrollTo(0,0)');
        assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'no horizontal overflow');
        if(process.env.UI_REVIEW_NO_CAPTURE==='1' && !(process.env.GRAY_LINE_REVIEW_CAPTURE==='1' && state.startsWith('gray-line')))continue;
        const gpsClip=state.startsWith('gray-line')?await evaluate('(()=>{const r=document.getElementById("gray-line-controls").getBoundingClientRect();return {x:0,y:r.top+scrollY,width:innerWidth,height:Math.ceil(r.height),scale:1}})()'):state.startsWith('gps-')?await evaluate('(()=>{const r=document.getElementById("gps-settings").getBoundingClientRect();return {x:0,y:r.top+scrollY,width:innerWidth,height:Math.ceil(r.height),scale:1}})()'):null;
        const shot=await send('Page.captureScreenshot',{format:'png',...(gpsClip?{clip:gpsClip,captureBeyondViewport:true}:{})});
        await writeFile(path.join(output,state+'-'+view.name+'.png'),Buffer.from(shot.data,'base64'));
    }
}
try {
    fixture=await h.review(driver,19149,output,{profiles:[carrier==='engineering'?'engineering':carrier==='field'?'consumer-ap':'consumer-lan']});await fixture.ready;
    const started=await h.chrome(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
        '--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check',
        '--remote-debugging-port=0','--user-data-dir='+profile,'--proxy-server=http://127.0.0.1:'+proxyPort,
        '--proxy-bypass-list=<-loopback>','about:blank'],profile);chrome=started.browser.process;
    cdp=await h.connect(started.pages[0].webSocketDebuggerUrl,{dialogs:true});cdp.on('Page.windowOpen',params=>helpWindows.push(params));cdp.on('Runtime.exceptionThrown',event=>console.error('Browser exception',JSON.stringify(event.exceptionDetails)));await send('Runtime.enable');await send('Page.enable');
    await until(()=>evaluate('!!document.documentElement').catch(navigationTransient),'active Chrome page');
    await navigate();
    assert.equal(await evaluate(`document.querySelectorAll('link[rel="icon"]').length`),1);
    const expectedIcon=(await readFile(new URL('../docs/_static/favicon.ico',import.meta.url))).toString('hex');
    for(let attempt=0;attempt<2;attempt++) {
      const icon=await evaluate(`(async()=>{const link=document.querySelector('link[rel="icon"]');
        const response=await fetch(link.href);const bytes=new Uint8Array(await response.arrayBuffer());
        const image=new Image();image.src=link.href;await image.decode();
        return {status:response.status,type:response.headers.get('content-type'),cache:response.headers.get('cache-control'),
          hex:Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join(''),width:image.naturalWidth,height:image.naturalHeight};})()`);
      assert.equal(icon.status,200);assert.equal(icon.type,'image/x-icon');assert.equal(icon.cache,'no-store');
      assert.equal(icon.hex,expectedIcon);assert.ok(icon.width>0&&icon.height>0);
    }
    pass('local shared favicon bytes, browser decoding and repeat delivery before login');
    await until(()=>evaluate('!!settingsLoadedBoot && !busy'),'automatic settings loaded');
    assert.equal(await evaluate('document.getElementById("radio-result-reveal").hidden'),true,'normal startup has no settings-result link');
    if(carrier==='consumer') {await checkLockedControls({evaluate,send,key,section,login,idle,output});pass('native authentication-lock feedback, guarded pointer/touch/keyboard and cleanup');}
    if(carrier==='consumer') {
      // Fail the actual automatic public reads on a new document, without a save.
      const injection=await send('Page.addScriptToEvaluateOnNewDocument',{source:`
        const startupFetch=globalThis.fetch;
        globalThis.fetch=(url,...args)=> ['/ntp-timeout','/rf-calibration'].some(path=>String(url).endsWith(path))
          ? Promise.resolve(new Response(JSON.stringify({error:'Automatic settings read unavailable'}),{status:503,headers:{'Content-Type':'application/json'}})) : startupFetch(url,...args);
      `});
      await navigate();
      await until(()=>evaluate('!loadingSettings && document.getElementById("ntp-timeout-status").textContent!=="Loading timeout…"'),'automatic settings settled');
      assert.equal(await evaluate('document.getElementById("radio-result-reveal").hidden'),true,'automatic read failure is not a save result');
      assert.equal(await evaluate('document.getElementById("local-access").open'),false);
      for(const id of ['ntp-timeout-status','rf-calibration-status'])
        assert.match(await evaluate(`document.getElementById('${id}').textContent`),/Automatic settings read unavailable/,'failed read remains inline');
      assert.equal(await evaluate('document.getElementById("clock").textContent.includes("Unknown")'),false,'independent current clock report survives settings failure');
      await capture('automatic-read-failure');
      await section('time-calibration');
      assert.equal(await evaluate('document.activeElement===document.querySelector("#time-calibration > summary")'),true,'bookmark still focuses the section');
      await login();
      await click('ntp-timeout-read');await idle();
      assert.equal(await evaluate('document.getElementById("radio-result-reveal").hidden'),false,'explicit failed read keeps actionable recovery');
      await click('access-toggle');await idle(); // Retire this regression's login before the capacity scenarios.
      await send('Page.removeScriptToEvaluateOnNewDocument',{identifier:injection.identifier});
      await navigate();
      await until(()=>evaluate('!!settingsLoadedBoot && !busy'),'automatic settings settled');
      assert.equal(await evaluate('document.getElementById("radio-result-reveal").hidden'),true,'reload clears only document-local recovery');
      pass('automatic time/calibration read failures stay inline; explicit recovery and bookmarks remain available');
    }
    await capture('help-status');
    await checkContextualHelp({evaluate,send,key,section,helpWindows});
    pass('native contextual help: collapsed/locked, pointer/keyboard, drafts/files/History, no application requests');
    await capture('contextual-help');
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
      await checkSi5351({evaluate,section,click,idle,capture});
      pass('native Si5351 conditional controls, validation focus, draft isolation, atomic save and direct restoration');
      await checkGps({evaluate,section,click,idle,capture,telemetryFixture:process.env.WSPRRY_PICO_GPS_RESOURCE_DRIVER?JSON.parse(execFileSync(process.env.WSPRRY_PICO_GPS_RESOURCE_DRIVER,{encoding:'utf8'})):null});
      await checkGrayLine({evaluate,section,idle,capture});
      pass('native GPS pin/timing validation focus, QLG3 receive-only protection, atomic save and separate qualification');
      await checkControlAlignment({evaluate,send,section,output:path.join(output,'alignment')});
      pass('content-sized RF/GPS control alignment across engines, labels, help, locks, breakpoints and zoom');
    } else if(carrier==='field') {
      await control({op:'field_clock'});
      await send('Page.bringToFront');
      await login();
      assert.equal(await evaluate('localAuthenticated'),true);
      assert.match(await evaluate('document.getElementById("browser-time-status").textContent'),/Using browser time/);
      await capture('field-time');
      await section('field-access');
      assert.equal(await evaluate('document.getElementById("field-access-settings").disabled'),false);
      await evaluate('document.getElementById("field-access-enabled").checked=true;document.getElementById("field-access-enabled").dispatchEvent(new Event("change"));document.getElementById("field-access-form").requestSubmit()');
      await idle();
      assert.match(await evaluate('document.getElementById("field-access-status").textContent'),/stays available/);
      await capture('field-settings');
      await evaluate('document.getElementById("field-access-enabled").checked=false;document.getElementById("field-access-enabled").dispatchEvent(new Event("change"));document.getElementById("field-access-form").requestSubmit()');
      await idle();
      assert.match(await evaluate('document.getElementById("field-access-status").textContent'),/is off/);
      pass('AP automatic browser time, field persistence read/save, responsive field controls and status');
      await click('access-toggle');await idle();
      await until(()=>evaluate('!busy && online && !!settingsLoadedBoot'),'AP public observations after logout');
      await checkLockedControls({evaluate,send,key,section,login,idle,output});
      pass('captive AP authentication-lock feedback, guarded pointer/touch/keyboard and cleanup');
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
    await until(()=>evaluate('!globalThis.sectionReloadMarker && typeof localIdentity!=="undefined" && !!localIdentity && !busy').catch(navigationTransient),'new document receipt reload');
    assert.equal(await evaluate('document.getElementById("radio-settings").open'),true);
    assert.equal(await evaluate('document.getElementById("consumer-setup").closest("#station-identity")!==null'),true);
    assert.equal(await evaluate('location.hash'),receipt);
    pass('receipt bytes and unrelated History data survive section/Top, reload exposes recovery');
    if (carrier !== 'engineering') {
      const networkReceipt='#save='+encodeURIComponent(JSON.stringify({kind:'network',device:'1'.repeat(32),generation:'1',digest:'b'.repeat(64)}));
      await navigate(networkReceipt);
      assert.equal(await evaluate('document.getElementById("consumer-setup").closest("#wifi-settings")!==null && document.getElementById("wifi-settings").open'),true,'network receipt belongs beside Wi-Fi');
      assert.equal(await evaluate('document.getElementById("consumer-return").hidden'),false);
      await click('station-link');await click('setup-result-reveal');
      assert.equal(await evaluate('document.getElementById("wifi-host-area").hidden'),false,'pending network link returns to Wi-Fi');
      assert.equal(await evaluate('location.hash'),networkReceipt);
    }
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
    await evaluate('document.getElementById("message-text").value="DRAFT";document.getElementById("message-text").dispatchEvent(new Event("input",{bubbles:true}));globalThis.savedRequest=radio.request.bind(radio);globalThis.savedRead=radio.publicRead.bind(radio);globalThis.requestOrder=[];radio.publicRead=async(...args)=>{requestOrder.push(args[0]);if(args[0]==="operations" && !globalThis.releaseRead)await new Promise(resolve=>globalThis.releaseRead=resolve);return savedRead(...args)};radio.request=async(...args)=>{requestOrder.push(args[0]);if(args[0]==="operations" && !globalThis.releaseRead)await new Promise(resolve=>globalThis.releaseRead=resolve);return savedRequest(...args)};document.getElementById("refresh").click()');
    await until(()=>evaluate('!!globalThis.releaseRead'),'held current request');
    await click('submission-lock');assert.equal(await evaluate('document.getElementById("save-config").disabled'),true);
    assert.equal(await evaluate('localAuthenticated'),false);
    assert.equal(await evaluate('document.getElementById("console-message").textContent'),'Unavailable');
    assert.equal(await evaluate('requestOrder.includes("consumer/logout")'),false);
    await evaluate('releaseRead()');await idle();
    assert.equal(await evaluate('radio.authenticated'),false);assert.equal(await evaluate('requestOrder.filter(path=>path==="consumer/logout").length'),1);assert.equal(await evaluate('requestOrder.indexOf("consumer/logout")>requestOrder.indexOf("operations")'),true);
    assert.equal(await evaluate('document.getElementById("message-text").value'),'DRAFT');
    // Exercise the actual registered interval without waiting five wall-clock seconds.
    await evaluate('radio.publicRead=savedRead;globalThis.publicReads=0;const savedPublic=radio.publicRead.bind(radio);radio.publicRead=(...args)=>{publicReads++;return savedPublic(...args)}');
    await until(()=>evaluate('publicReads>0'),'public polling continues after logout');
    await evaluate('radio.request=savedRequest;radio.publicRead=savedRead');
    pass('lock gates immediately, clears private status, serializes logout and keeps public polling');
    await login();
    await evaluate('radio.logout=async()=>{throw Error("synthetic lost logout") }');await click('access-toggle');await idle();
    assert.equal(await evaluate('radio.authenticated'),false);assert.match(await evaluate('document.getElementById("notice").textContent'),/unconfirmed/);
    pass('lost logout clears local authority and reports remote uncertainty');
    await navigate();
    await evaluate('globalThis.originalLogin=radio.login.bind(radio);globalThis.originalLogout=radio.logout.bind(radio);globalThis.cancelLogoutCount=0;radio.logout=async()=>{cancelLogoutCount++;return originalLogout()};radio.login=async(...args)=>{await originalLogin(...args);await new Promise(resolve=>globalThis.releaseLogin=resolve)}');
    await click('access-toggle');await evaluate('document.getElementById("local-password").value="test-password";document.getElementById("local-login").requestSubmit()');
    await until(()=>evaluate('!!globalThis.releaseLogin'),'late successful login');
    await click('submission-cancel');await evaluate('releaseLogin()');await idle();
    assert.equal(await evaluate('radio.authenticated || localAuthenticated'),false);assert.equal(await evaluate('cancelLogoutCount'),1);
    assert.equal(await evaluate('document.getElementById("local-access").open'),false);
    pass('cancelled late login cannot ghost-unlock and cleans only its serialized session');
    for(const [button,resource,editor] of [['rf-calibration-read','rf-calibration','calibrationEditor'],['ntp-timeout-read','ntp-timeout','ntpTimeoutEditor'],['gpio-drive-read','gpio-drive','driveEditor'],['gray-line-1-read','gray-line','grayLineEditor']]) {
      await navigate();await login();await section(resource==='gpio-drive'?'radio-pins':'time-calibration');
      await evaluate(`${editor}.invalidate();controls(online)`);
      await evaluate(`globalThis.editorRequest=radio.request.bind(radio);globalThis.editorRead=radio.publicRead.bind(radio);globalThis.editorOrder=[];radio.request=async(...args)=>{editorOrder.push(args[0]);return editorRequest(...args)};radio.publicRead=async(...args)=>{if(args[0]==='${resource}'&&!globalThis.releaseEditor)await new Promise(resolve=>globalThis.releaseEditor=resolve);return editorRead(...args)}`);
      await click(button);await until(()=>evaluate('!!globalThis.releaseEditor'),'held editor');
      assert.equal(await evaluate('busy'),true);await click('submission-lock');
      assert.equal(await evaluate('editorOrder.includes("consumer/logout")'),false);
      await evaluate('releaseEditor()');await idle();
      assert.equal(await evaluate('radio.authenticated'),false);
      assert.equal(await evaluate('editorOrder.at(-1)'),'consumer/logout');
      assert.equal(await evaluate('document.getElementById("rf-calibration-discard").matches(":disabled") && document.getElementById("ntp-timeout-discard").matches(":disabled")'),true);
    }
    pass('all standalone editors drain before logout and invalidate private readbacks');
    await navigate();await login();
    await control({op:'message_review'});await click('refresh');await idle();
    await section('time-calibration');await idle();
    await evaluate('document.getElementById("rf-manual-ppm").value="1.000";document.getElementById("rf-manual-ppm").dispatchEvent(new Event("input"));globalThis.mutationRequest=radio.request.bind(radio);radio.request=async(...args)=>{if(args[0]==="rf-calibration"&&args[1]==="PUT"){await new Promise(resolve=>globalThis.releaseMutation=resolve);const response=await mutationRequest(...args);const value=await response.json();return {...response,json:async()=>({...value,saved:{mode:"manual",manual_ppm:"2.000"}})}}return mutationRequest(...args)}');
    await click('rf-calibration-save');await until(()=>evaluate('!!globalThis.releaseMutation'),'held settings mutation');
    await evaluate('document.getElementById("time-calibration").querySelector("[data-top]").click()');
    assert.equal(await evaluate('document.getElementById("time-calibration").open'),true,'busy modal blocks underlying navigation');
    await evaluate('releaseMutation()');await idle();
    await evaluate('document.getElementById("time-calibration").querySelector("[data-top]").click()');
    assert.equal(await evaluate('document.getElementById("time-calibration").open'),false);
    assert.equal(await evaluate('document.getElementById("radio-result-reveal").hidden'),false);
    assert.equal(await evaluate('document.getElementById("notice").classList.contains("error")'),true);
    await click('radio-result-reveal');assert.equal(await evaluate('document.getElementById("time-calibration").open'),true);
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
    if(carrier==='consumer') {
      await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
      await navigate();await login();
      await checkSi5351({evaluate,section,click,idle,capture});
      await checkGps({evaluate,section,click,idle,capture});
      await checkGrayLine({evaluate,section,idle,capture});
      pass('consumer encrypted RF/GPS controls retain conditional validation, atomic saves, relocated policy readback, and lock state');
      await checkControlAlignment({evaluate,send,section,output:path.join(output,'alignment')});
      pass('encrypted RF/GPS control alignment across engines, labels, help, locks, breakpoints and zoom');
    }
    await control({op:'hardware_save_review'});
    await navigate();if(carrier!=='engineering')await login();
    await checkHardwareSaveIsolation({evaluate,section,click,idle,capture});
    pass('hardware saves preserve suspended no-dial recurrence and invalid WSPR drafts; LED, button, Si5351, GPS/PPS use production journals');
    const result={carrier,browser:(await send('Browser.getVersion')).product,checks,physical_device:false};
    await writeFile(path.join(output,'results.json'),JSON.stringify(result,null,2)+'\n');
} catch(error) {
    console.error('UI document',cdp ? await evaluate('JSON.stringify({url:location.href,title:document.title,body:document.body?.textContent.slice(0,180),carrier:typeof accessCarrier,busy:typeof busy})').catch(()=>null) : null);
    console.error('UI failure state',cdp ? await evaluate('JSON.stringify({busy,online,writeState,markers:document.querySelectorAll("[data-auth-locked-control]").length,carrier:accessCarrier,authenticated:localAuthenticated,notice:document.getElementById("notice").textContent,field:capabilities?.field_access,context:radio?.context,hidden:document.hidden,fieldSupported:fieldTimeSupported(),focus:document.activeElement.id,open:[...document.querySelectorAll("[data-operator-section][open]")].map(e=>e.id)})').catch(()=>null) : null);
    throw error;
}
});
