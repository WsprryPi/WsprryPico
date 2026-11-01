// Shipped page/bundle -> Chrome -> production HTTP/AEAD; time and board are synthetic.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile,mkdir} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {cleanupUiProcesses} from './ui_process_cleanup.mjs';

const proxyPort=19149;
const driver=process.argv[2],output=path.resolve(process.argv[3] || 'build/submission-ui');
if(!driver)throw Error('Usage: node tests/submission_ui_browser.mjs DRIVER [OUTPUT]');
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
async function click(id) {await evaluate(`document.getElementById(${JSON.stringify(id)}).click()`);}
async function section(id) {await evaluate(`(()=>{const node=document.getElementById('${id}'),area=node.closest('[data-task-area]').dataset.taskArea;history.pushState({...history.state,wsprrypicoPresentation:{section:'${id}',area}},'','/'+area+(/^#(?:save|hostname-return)=/.test(location.hash)?location.hash:'#${id}'));dispatchEvent(new PopStateEvent('popstate'));})()`);}
async function key(key,code=key) {
    await send('Input.dispatchKeyEvent',{type:'keyDown',key,code,text:key==='Enter'?'\r':key===' '?' ':undefined,windowsVirtualKeyCode:key==='Escape'?27:key==='Enter'?13:key===' '?32:9});
    await send('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:key==='Escape'?27:key==='Enter'?13:key===' '?32:9});
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

    // Delay real encrypted login completion; all HTTP, crypto and policy work is production.
    await click('access-toggle');
    await evaluate(`globalThis.loginCount=0;globalThis.originalLogin=radio.login.bind(radio);radio.login=async(...args)=>{loginCount++;await originalLogin(...args);await new Promise(resolve=>globalThis.finishLogin=resolve);};document.getElementById('local-password').value='test-password';document.getElementById('local-login').requestSubmit();`);
    await until(()=>evaluate('typeof finishLogin==="function"'),'real encrypted login');
    assert.equal(await evaluate('busy && submissions.pending && document.getElementById("submission-busy").matches(":modal")'),true);
    assert.equal(await evaluate('document.getElementById("local-access").open'),true,'overlay stacks over access dialog');
    assert.equal(await evaluate('document.getElementById("submission-busy").contains(document.activeElement)'),true);
    assert.equal(await evaluate('document.querySelector("main").getAttribute("aria-busy")'),'true');
    assert.equal(await evaluate('document.getElementById("submission-message").getAttribute("aria-live")'),'polite');
    await evaluate(`document.getElementById('local-login').requestSubmit();document.getElementById('local-login').onsubmit({preventDefault(){}});document.getElementById('refresh').onclick();`);
    await key('Enter');await key(' ','Space');
    await send('Emulation.setTouchEmulationEnabled',{enabled:true});
    for(let tap=0;tap<2;tap++) {
      await send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:10,y:10}]});
      await send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
    }
    assert.equal(await evaluate('loginCount'),1,'queued forms, keyboard, touch and direct handlers do not allocate another session');
    await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
    for(const theme of ['light','dark']) {
      await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme},{name:'prefers-reduced-motion',value:'reduce'}]});
      await capture('submission-'+theme,true);
      assert.equal(await evaluate('getComputedStyle(document.getElementById("submission-busy")).animationName'),'none');
      assert.equal(await evaluate('getComputedStyle(document.getElementById("submission-busy"),"::backdrop").backgroundColor.includes("0.48") || getComputedStyle(document.getElementById("submission-busy"),"::backdrop").backgroundColor.includes("0.62")'),true);
    }
    await key('Escape');await evaluate('finishLogin()');await idle();
    assert.equal(await evaluate('localAuthenticated || radio.authenticated || document.getElementById("submission-busy").open'),false);
    await evaluate('radio.login=originalLogin');
    pass('synchronous admission, nested modal stacking, duplicate forms, cancellation, live status, themes, reduced motion and responsive busy rendering');
    await login();assert.equal(await evaluate('localAuthenticated'),true);
    await evaluate(`globalThis.handoffFetch=radio.fetcher;globalThis.handoffStage=0;radio.fetcher=async(...args)=>{const response=await handoffFetch(...args);if(String(args[0]).endsWith('/request') && handoffStage<2){handoffStage++;await new Promise(resolve=>{globalThis['drain'+handoffStage]=resolve;});}return response;};void action(()=>refresh(false,true),{background:true});`);
    await until(()=>evaluate('typeof drain1==="function"'),'actual encrypted poll held');
    assert.equal(await evaluate('document.getElementById("refresh").disabled'),false,'polling leaves operator controls available');
    await click('refresh');
    const foregroundToken=await evaluate('submissions.token.id');
    assert.equal(await evaluate('document.getElementById("submission-busy").open && !submissions.token.background'),true,'foreground admitted immediately');
    assert.equal(await evaluate('handoffStage'),1,'foreground dispatch waits for the current exchange');
    await evaluate('document.getElementById("refresh").onclick();drain1()');
    await until(()=>evaluate('typeof drain2==="function"'),'foreground request after poll drain');
    assert.equal(await evaluate('submissions.token.id'),foregroundToken,'old completion cannot release the foreground token');
    assert.equal(await evaluate('document.getElementById("submission-busy").open'),true);
    await evaluate('drain2()');await idle();await evaluate('radio.fetcher=handoffFetch');
    assert.equal(await evaluate('localAuthenticated && radio.authenticated'),true);
    pass('foreground priority drains one genuine encrypted poll without refusal, crypto overlap, stale continuation or old-token release');
    await section('time-calibration');
    await evaluate(`document.getElementById('ntp-timeout-minutes').value='11';document.getElementById('ntp-timeout-minutes').dispatchEvent(new Event('input',{bubbles:true}));globalThis.putCount=0;globalThis.originalRequest=radio.request.bind(radio);radio.request=async(path,method,...args)=>{const result=await originalRequest(path,method,...args);if(path==='ntp-timeout' && method==='PUT'){putCount++;await new Promise(resolve=>globalThis.finishPut=resolve);}return result;};document.getElementById('ntp-timeout-save').click();`);
    await until(()=>evaluate('typeof finishPut==="function"'),'actual timeout mutation committed');
    await evaluate(`document.getElementById('ntp-timeout-save').onclick();document.getElementById('consumer-network-form').requestSubmit();document.getElementById('refresh').onclick();`);
    assert.equal(await evaluate('putCount'),1);
    await click('submission-lock');
    assert.equal(await evaluate('accessClosing && !localAuthenticated'),true,'lock gates immediately');
    await evaluate('finishPut()');await idle();
    assert.equal(await evaluate('radio.authenticated || accessClosing || submissions.pending'),false);
    assert.equal(await evaluate('document.getElementById("ntp-timeout-minutes").value'),'11','draft preserved during locking');
    await evaluate('radio.request=originalRequest');await login();
    await evaluate('void action(()=>ntpTimeoutEditor.load())');await idle();
    assert.match(await evaluate('document.getElementById("ntp-timeout-status").textContent'),/11 minutes/);
    pass('one actual mutation under direct and form conflicts; lock drains requests and retains drafts and the durable result');

    // Lose one committed reply through the actual adapter, then release its late response.
    await evaluate(`globalThis.realFetch=radio.fetcher;globalThis.dropReply=false;globalThis.requestTrace=[];radio.request=async(path,method,...args)=>{requestTrace.push({path,method});if(path==='ntp-timeout' && method==='PUT')dropReply=true;return originalRequest(path,method,...args);};radio.fetcher=async(url,options)=>{const response=await realFetch(url,options);if(dropReply && String(url).endsWith('/request')){dropReply=false;await new Promise((resolve,reject)=>{globalThis.releaseLate=resolve;globalThis.rejectLate=()=>reject(new DOMException('Delayed response deadline','TimeoutError'));});}return response;};document.getElementById('ntp-timeout-minutes').value='12';document.getElementById('ntp-timeout-minutes').dispatchEvent(new Event('input',{bubbles:true}));document.getElementById('ntp-timeout-save').click();`);
    await until(()=>evaluate('typeof rejectLate==="function"'),'committed encrypted reply held');
    await evaluate('rejectLate()');await idle();
    assert.equal(await evaluate('radio.authenticated'),false);
    assert.equal(await evaluate('document.getElementById("submission-busy").open'),false);
    assert.equal(await evaluate('document.getElementById("ntp-timeout-minutes").value'),'12');
    assert.match(await evaluate('document.getElementById("ntp-timeout-status").textContent'),/Read saved timeout/);
    assert.equal(await evaluate('requestTrace.filter(x=>x.path==="ntp-timeout" && x.method==="PUT").length'),1);
    await evaluate('releaseLate();radio.fetcher=realFetch;radio.request=originalRequest');
    await login();await evaluate('void action(()=>ntpTimeoutEditor.load())');await idle();
    assert.match(await evaluate('document.getElementById("ntp-timeout-status").textContent'),/12 minutes/);
    pass('lost committed reply clears authority, retains draft and readback requirement; late completion cannot restore a session or replay a mutation');
    await evaluate('void action(()=>udpEditor.read())');await idle();
    await evaluate(`const port=document.querySelector('#udp-logging-controls [name=destination_port]');port.value='515';port.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#udp-logging-controls form').requestSubmit();`);await idle();
    assert.match(await evaluate('document.querySelector("#udp-logging-controls > p:last-child").textContent'),/Saved revision/);
    assert.equal(await evaluate('(async()=> (await (await radio.request("udp-logging")).json()).saved.destination_port)()'),515);
    await evaluate('void action(readLogging)');await idle();
    await evaluate('document.getElementById("logging-enabled").checked=true;document.getElementById("logging-form").requestSubmit()');await idle();
    assert.equal(await evaluate('(async()=> (await (await radio.request("logging")).json()).saved.enabled)()'),true);
    pass('UDP and USB logging retain resource eligibility inside the outer action and confirm real journal-backed saves');

    await section('message-section');
    await evaluate(`globalThis.jobTrace=[];radio.request=async(path,method,...args)=>{if(path==='jobs')jobTrace.push(args[0].operation);const result=await originalRequest(path,method,...args);if(path==='jobs' && args[0].operation==='LOAD_MESSAGE')await new Promise(resolve=>globalThis.finishLoad=resolve);return result;};const put=(id,value)=>{const e=document.getElementById(id);e.value=value;e.dispatchEvent(new Event('input',{bubbles:true}));};put('message-delivery','once');put('message-text','E');put('message-mode','qrss');put('message-frequency','14097100');put('message-dot','1');put('message-repeats','1');put('message-gap','0');put('message-start',new Date(utcNowMs()+60000).toISOString().slice(0,19).replace('T',' '));document.getElementById('message-form').requestSubmit();`);
    await until(()=>evaluate('typeof finishLoad==="function"'),'real message loaded before ARM');
    await click('submission-abort');await evaluate('finishLoad()');await idle();
    await until(()=>evaluate('!stopRequested && !busy'),'deferred abort completed');
    assert.equal(await evaluate('jobTrace.includes("ARM")'),false);
    assert.equal(await evaluate('jobTrace.filter(op=>op==="ABORT").length'),1);
    assert.equal(await evaluate('snapshot.job.output_active'),false);
    assert.equal(await evaluate('snapshot.job.state'),'aborted');
    await evaluate('radio.request=originalRequest;void action(async()=>{await job("RELEASE");await refresh();})');await idle();
    pass('foreground abort drains an actual loaded job, invalidates the pending ARM continuation and confirms inactive output');

    await evaluate(`radio.request=async(path,method,...args)=>{const result=await originalRequest(path,method,...args);if(path==='operations')await new Promise(resolve=>globalThis.finishPoll=resolve);return result;};void action(()=>refresh(false,true),{background:true});`);
    await until(()=>evaluate('typeof finishPoll==="function"'),'pending production poll');
    assert.equal(await evaluate('document.getElementById("submission-busy").open'),false,'background reads do not dim the page');
    await evaluate('dispatchEvent(new PageTransitionEvent("pagehide",{persisted:true}))');
    assert.equal(await evaluate('submissions.suspended && accessClosing && !localAuthenticated'),true);
    await evaluate('finishPoll()');await until(()=>evaluate('!busy'),'old observation drained');
    assert.equal(await evaluate('accessClosing'),true,'suspension never admits a new mutation');
    await evaluate('radio.request=originalRequest;dispatchEvent(new PageTransitionEvent("pageshow",{persisted:true}))');
    await until(()=>evaluate('!accessClosing && !busy'),'restored page drains logout');
    assert.equal(await evaluate('localAuthenticated || radio.authenticated || submissions.pending'),false);
    pass('polling remains visually quiet and page suspension invalidates observations, retains ownership and drains lock on restoration');
    const result={browser:(await send('Browser.getVersion')).product,checks,physical_device:false};
    await writeFile(path.join(output,'results.json'),JSON.stringify(result,null,2)+'\n');
} catch(error) {
    console.error('UI failure state',await evaluate('JSON.stringify({busy,online,carrier:accessCarrier,authenticated:localAuthenticated,notice:document.getElementById("notice").textContent,focus:document.activeElement.id,open:[...document.querySelectorAll("[data-operator-section][open]")].map(e=>e.id)})').catch(()=>null));
    throw error;
} finally {
    if(ws){await send('Browser.close').catch(()=>{});ws.close();}await cleanupUiProcesses([chrome,fixture],profile,{processGroup});
}
