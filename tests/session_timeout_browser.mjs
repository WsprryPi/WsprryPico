// Shipped page/bundle -> Chrome -> production HTTP/AEAD; time and board are synthetic.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile,mkdir} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {cleanupUiProcesses} from './ui_process_cleanup.mjs';

const driver=process.argv[2],output=path.resolve(process.argv[3] || 'build/session-timeout-browser');
if(!driver)throw Error('Usage: node tests/session_timeout_browser.mjs DRIVER [OUTPUT]');
await mkdir(output,{recursive:true});
const profile=await mkdtemp(path.join(os.tmpdir(),'pico-session-browser-'));
const processGroup=process.platform!=='win32';
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
async function time(ms) {
    now=ms;
    const response=await fetch('http://127.0.0.1:19139/.fixture-control',{method:'POST',body:JSON.stringify({op:'time',ms:String(ms)})});
    assert.equal(response.status,200);
    await evaluate('globalThis.sessionTestTime='+ms);
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
try {
    let fixtureLog='';
    fixture=spawn(process.execPath,['tests/ui_review_fixture.mjs',driver,'19139',output],{stdio:['ignore','pipe','pipe'],detached:processGroup});
    fixture.stdout.on('data',data=>fixtureLog+=data);fixture.stderr.on('data',data=>fixtureLog+=data);
    await until(()=>fixtureLog.includes('READY;'),'fixture startup');
    chrome=spawn(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
        '--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check',
        '--remote-debugging-port=0','--user-data-dir='+profile,'--proxy-server=http://127.0.0.1:19139',
        '--proxy-bypass-list=<-loopback>','about:blank'],{stdio:'ignore',detached:processGroup});
    let debugPort;
    await until(async()=>{try{debugPort=Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);return !!debugPort;}catch{return false;}},'Chrome startup');
    const pages=await(await fetch('http://127.0.0.1:'+debugPort+'/json')).json();
    ws=new WebSocket(pages.find(page=>page.type==='page').webSocketDebuggerUrl);
    ws.onmessage=event=>{const value=JSON.parse(event.data),request=pending.get(value.id);if(request){pending.delete(value.id);value.error?request.reject(Error(value.error.message)):request.resolve(value.result);}};
    await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
    await send('Page.enable');
    await send('Page.navigate',{url:'http://192.168.1.53/'});
    await until(()=>evaluate('typeof radio!=="undefined" && !!radio && !busy'),'shipped consumer page');
    // Inject only the clock seam; use the shipped client and UI without replacements.
    await evaluate('globalThis.sessionTestTime=1000;radio.now=()=>globalThis.sessionTestTime;globalThis.sessionRequests=[];const sessionRequest=radio.request.bind(radio);radio.request=(...args)=>{sessionRequests.push({path:args[0],method:args[1]||"GET"});return sessionRequest(...args)}');
    await login();
    const started=now;
    await evaluate('document.querySelector("[name=schedules]").value="240 / 0";document.getElementById("config").dispatchEvent(new Event("input",{bubbles:true}))');
    const draft=()=>evaluate('document.querySelector("[name=schedules]").value');
    await time(started+300000);assert.equal(await evaluate('radio.authenticated'),true);
    await time(started+1800000-1);await refresh();
    assert.equal(await evaluate('radio.authenticated && localAuthenticated'),true);
    const renewed=now;
    await time(renewed+1800000-1);
    await evaluate('document.querySelector("[name=schedules]").dispatchEvent(new Event("input",{bubbles:true}));radio.identity()');
    await time(renewed+1800000);await refresh();
    assert.equal(await evaluate('radio.authenticated'),false);
    assert.equal(await evaluate('document.getElementById("access-toggle").getAttribute("aria-label")'),'Unlock controls');
    assert.equal(await evaluate('document.getElementById("local-access").open'),false);
    assert.equal(await evaluate('document.getElementById("local-login").hidden'),false);
    assert.equal(await evaluate('document.getElementById("save-config").disabled'),true);
    assert.equal(await draft(),'240 / 0');
    await capture('idle-expired');
    await login();
    assert.equal(await draft(),'240 / 0');
    assert.equal(await evaluate('writeState'),'review');
    const fresh=now;
    for(let elapsed=1000000;elapsed<28800000;elapsed+=1000000){await time(fresh+elapsed);await refresh();assert.equal(await evaluate('radio.authenticated'),true);}
    await time(fresh+28800000-1);await refresh();
    assert.equal(await evaluate('radio.authenticated'),true);
    await time(fresh+28800000);await refresh();
    assert.equal(await evaluate('radio.authenticated'),false);
    assert.equal(await draft(),'240 / 0');
    assert.equal(await evaluate('document.getElementById("save-config").disabled'),true);
    assert.deepEqual(await evaluate('sessionRequests.filter(request=>!["GET"].includes(request.method))'),[]);
    await capture('absolute-expired');
    const result={browser:(await send('Browser.getVersion')).product,virtual_time:true,idle_boundary_ms:1800000,absolute_boundary_ms:28800000,public_and_edit_activity_do_not_renew:true,draft_preserved:true,readback_review_required:true,no_mutations:true,screenshots:process.env.UI_REVIEW_NO_CAPTURE==='1'?0:4};
    await writeFile(path.join(output,'results.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify(result));
} finally {
    if(ws)ws.close();
    await cleanupUiProcesses([chrome,fixture],profile,{processGroup});
}
