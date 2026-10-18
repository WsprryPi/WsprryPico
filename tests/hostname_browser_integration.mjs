// Shipped page/bundle -> real browser -> production HTTP/crypto/commissioning.
// Only TCP/board/time boundaries use the existing deterministic fixture.
import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {mkdtemp, readFile, writeFile, mkdir} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {Fixture} from './consumer_sessions.test.mjs';

if (!globalThis.WebSocket) throw new Error('Use Node with built-in WebSocket; Node 20 needs --experimental-websocket');
const output=path.resolve(process.argv[3] || 'build/hostname-browser-integration');
await mkdir(output,{recursive:true});
const profile=await mkdtemp(path.join(os.tmpdir(),'p1510-chrome-'));
let f=new Fixture(process.argv[2]);await f.time(1000);
let old=false, dropNext=false, blockPresentation=true, failRadioRequests=false, chrome, cdp, cdpB;
let captures=0;
const fB=new Fixture(process.argv[2],['2'.repeat(32)]);await fB.time(1000);
const bClient=fB.client();await fB.login(bClient);const bResource=await bClient.request('hostname');const bName=await bResource.json();
await bClient.request('hostname','PUT',{schema:'transmitter-hostname/1',target:bName.target,hostname:'pico-b.local'},bResource.headers.get('etag'));
await fB.command({op:'reboot'});await fB.time(3000); const requests=[];
const proxy=http.createServer(async(req,res)=>{
    try {
        const u=new URL(req.url.startsWith('http:')?req.url:'http://192.168.1.53'+req.url);
        if(!['192.168.1.53','192.168.4.1','wsprrypico-0a60df.local','pico-a.local','pico-b.local', 'x'.repeat(63)+'.local'].includes(u.hostname)){res.writeHead(403);res.end();return;}
        if(old && ['/api/v1/application/2','/api/owner/v1/wspr-support'].includes(u.pathname)){
            res.writeHead(404,{'Content-Type':'application/json'});res.end('{"error":{"code":"not_found"}}');return;
        }
        if(blockPresentation && u.pathname==='/api/consumer/v1/presentation' || failRadioRequests && u.pathname==='/api/consumer/v1/request') {
            res.writeHead(503,{'Content-Type':'application/json'});res.end('{"error":{"code":"unavailable"}}');return;
        }
        const chunks=[];for await(const b of req)chunks.push(b);
        if(u.pathname.endsWith('/start'))await f.time(f.now+1000);
        const target=u.hostname==='pico-b.local'?fB:f;
        const response=await target.fetch(u.hostname,u.hostname==='192.168.4.1',u.pathname,
            {method:req.method,body:Buffer.concat(chunks),headers:{'Content-Type':req.headers['content-type']||'application/json'},
                marker:u.pathname.startsWith('/api/owner/')?'Owner':u.pathname.startsWith('/api/bootstrap/')?'Bootstrap':'Radio'});
        const socket=target.socket;
        let bytes=Buffer.from(await response.arrayBuffer());
        const expected=Number(response.headers.get('content-length'));
        // Explicit TCP-ACK pumping of the existing bounded 100-step fixture, without
        // increasing a production/test deadline or accepting an incomplete response.
        for(let pump=0;bytes.length<expected && pump<4;++pump){
            await target.command({op:'complete',socket});
            const snapshot=await target.command({op:'wire',socket});
            const wire=Buffer.from(snapshot.wire,'hex');bytes=wire.subarray(wire.indexOf('\r\n\r\n')+4);
        }
        assert.equal(bytes.length,expected,'complete production HTTP response');
        requests.push({path:u.pathname,status:response.status,bytes:bytes.length});
        if(u.pathname === "/") await writeFile(path.join(output,"root.html"),bytes);
        if(dropNext && u.pathname.endsWith('/request')) { dropNext=false;res.destroy();return; }
        res.writeHead(response.status,Object.fromEntries(response.headers));res.end(bytes);
    }catch(error){res.writeHead(500,{'Content-Type':'text/plain'});res.end(error.message);}
});
await new Promise(resolve=>proxy.listen(0,'127.0.0.1',resolve));
const port=proxy.address().port;
class Cdp {
    constructor(url){this.ws=new WebSocket(url);this.sequence=0;this.pending=new Map();this.ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.method==='Page.javascriptDialogOpening'){void this.send('Page.handleJavaScriptDialog',{accept:true});return;}if(m.id&&this.pending.has(m.id)){const p=this.pending.get(m.id);this.pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result);}};}
    async open(){if(this.ws.readyState===1)return;await new Promise((resolve,reject)=>{this.ws.onopen=resolve;this.ws.onerror=reject;});}
    send(method,params={}){const id=++this.sequence;return new Promise((resolve,reject)=>{this.pending.set(id,{resolve,reject});this.ws.send(JSON.stringify({id,method,params}));});}
    async evaluate(expression){const r=await this.send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
}
async function until(fn,label,ms=10000){const end=Date.now()+ms;let last;while(Date.now()<end){try{const r=await fn();if(r)return r;}catch(e){last=e;}await new Promise(r=>setTimeout(r,50));}throw Error('Timed out: '+label+(last?' '+last.message:''));}
async function field(id,value){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));}`);}
async function click(id){await cdp.evaluate(`document.getElementById(${JSON.stringify(id)}).click()`);}
async function capture(name){
    if(process.env.HOSTNAME_BROWSER_NO_CAPTURE==='1')return;
    for(const theme of ['light','dark'])for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]){
        await cdp.send('Emulation.setDeviceMetricsOverride',{...view,name:undefined,deviceScaleFactor:1,mobile:view.name==='mobile'});
        await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]});
        await cdp.evaluate('scrollTo(0,0)');
        assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false,'horizontal overflow');
        const image=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
        ++captures;await writeFile(path.join(output,`${name}-${view.name}-${theme}.png`),Buffer.from(image.data,'base64'));
    }
}
try {
    chrome=spawn(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        ['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',
            '--remote-debugging-port=0',`--user-data-dir=${profile}`,`--proxy-server=http://127.0.0.1:${port}`,'--proxy-bypass-list=<-loopback>','about:blank'],{stdio:'ignore'});
    const debugPort=await until(async()=>Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]),'Chrome startup',60000);
    const page=await until(async()=>(await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(p=>p.type==='page'),'page');
    cdp=new Cdp(page.webSocketDebuggerUrl);await cdp.open();await cdp.send('Page.enable');
    await cdp.send('Page.navigate',{url:'http://192.168.1.53/'});
    await until(()=>cdp.evaluate(`typeof radio !== 'undefined' && !!document.getElementById('local-password')`),'shipped radio page');

    async function login() {
        await field('local-password','test-password');
        await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
        await until(()=>cdp.evaluate(`localAuthenticated && !busy && online`),'login and hostname readback');
    }
    await until(()=>cdp.evaluate('!busy && !!localIdentity'),'unknown metadata state');
    assert.equal(await cdp.evaluate(`document.getElementById('device-name').textContent`),'Hostname unavailable');
    assert.equal(await cdp.evaluate(`document.getElementById('device-id').textContent`),'1'.repeat(32));
    assert.equal(await cdp.evaluate(`document.querySelectorAll('h1').length`),1);
    await capture('unknown-name');
    blockPresentation=false;
    await cdp.send('Page.reload');
    await until(()=>cdp.evaluate(`document.title==='wsprrypico-0a60df.local - Station control' && !busy`),'IP initial tab title');
    async function identity(name,device='1'.repeat(32)) {
        assert.equal(await cdp.evaluate(`document.getElementById('device-name').textContent`),name);
        assert.equal(await cdp.evaluate(`document.getElementById('device-id').textContent`),device);
        assert.match(await cdp.evaluate('document.title'),new RegExp('^'+name.replaceAll('.','\\.')));
        assert.equal(await cdp.evaluate(`document.getElementById('local-status').textContent.includes(${JSON.stringify(device)})`),false);
    }
    await identity('wsprrypico-0a60df.local');
    const diagnosticsBefore=await f.command({op:'stats'}), diagnosticsRequests=requests.length;
    await cdp.send('Page.bringToFront');
    await cdp.evaluate(`document.querySelector('#device-diagnostics summary').focus()`);
    await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',text:'\r',unmodifiedText:'\r',windowsVirtualKeyCode:13,nativeVirtualKeyCode:36});
    await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
    await until(()=>cdp.evaluate(`document.getElementById('device-diagnostics').open`),'keyboard disclosure');
    assert.equal(await cdp.evaluate(`{const s=getSelection(),r=document.createRange();r.selectNodeContents(document.getElementById('device-id'));s.removeAllRanges();s.addRange(r);s.toString()}`),'1'.repeat(32));
    await capture('signed-out-station-diagnostics');
    await click('wifi-host-link');await capture('signed-out-wifi-diagnostics');
    const diagnosticsAfter=await f.command({op:'stats'});
    for(const key of ['config_sequence','profile_generation','profile_programs','api_restarts'])
        assert.equal(diagnosticsAfter[key],diagnosticsBefore[key],key+' unchanged by diagnostics/navigation');
    assert.equal(requests.length,diagnosticsRequests,'Diagnostics/navigation emit no requests, including session/job mutations');
    await field('local-password','wrong-password');await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
    await until(()=>cdp.evaluate('!busy'),'rejected login');
    assert.equal(await cdp.evaluate('localAuthenticated'),false);await identity('wsprrypico-0a60df.local');
    assert.match(await cdp.evaluate(`document.getElementById('notice').textContent`),/failed|rejected|password|authentication/);
    await capture('rejected-login');
    await login();
    await identity('wsprrypico-0a60df.local');await capture('authenticated-wifi-diagnostics');
    await click('station-link');await capture('authenticated-station-diagnostics');
    await click('wifi-host-link');
    assert.equal(await cdp.evaluate('hostnameState.saved'),'wsprrypico-0a60df.local');
    await field('hostname-input','K.local');
    await cdp.evaluate(`document.getElementById('hostname-form').dispatchEvent(new Event('submit',{cancelable:true}))`);
    await until(()=>cdp.evaluate('!busy'),'invalid hostname');
    assert.match(await cdp.evaluate(`document.getElementById('notice').textContent`),/full .local hostname/);
    assert.equal(await cdp.evaluate('document.title'),'wsprrypico-0a60df.local - Station control');
    await field('hostname-input','x'.repeat(63)+'.local');
    await cdp.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
    await cdp.evaluate(`document.getElementById('hostname-input').focus()`);
    await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
    assert.equal(await cdp.evaluate('document.activeElement.id'),'hostname-save');
    await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
    await capture('max-name-draft');
    await field('message-text','KEEP DRAFT');
    await field('hostname-input','pico-a.local');
    const before=await f.command({op:'stats'});
    await cdp.evaluate(`document.getElementById('hostname-form').requestSubmit()`);
    await until(()=>cdp.evaluate('!busy && !localAuthenticated'),'profile save logs in again');
    assert.equal(await cdp.evaluate(`document.getElementById('message-text').value`),'KEEP DRAFT');
    assert.equal((await f.command({op:'stats'})).profile_generation,'2');
    await login();
    assert.equal(await cdp.evaluate('hostnameState.saved'),'pico-a.local');
    assert.equal(await cdp.evaluate('document.title'),'wsprrypico-0a60df.local - Station control (rename pending)');
    assert.equal(await cdp.evaluate(`document.getElementById('hostname-save').disabled`),true);
    await click('hostname-review');
    await identity('wsprrypico-0a60df.local');
    assert.match(await cdp.evaluate(`document.getElementById('device-name-state').textContent`),/Saved for restart: pico-a.local/);
    await capture('saved-rename-pending');
    await click('restart');await until(()=>cdp.evaluate('reconnectRunning && !busy'),'one-shot restart/countdown');
    await capture('restart-countdown');
    await click('restart-cancel');
    const attempts=(await f.command({op:'stats'})).api_restarts;
    await new Promise(r=>setTimeout(r,2200));
    assert.equal((await f.command({op:'stats'})).api_restarts,attempts);
    await f.command({op:'reboot'});await f.time(5000);
    await login();
    assert.equal(await cdp.evaluate('document.title'),'pico-a.local - Station control');
    assert.match(await cdp.evaluate(`document.getElementById('restart-status').textContent`),/Same Pico and new boot confirmed/);
    assert.equal(await cdp.evaluate(`document.getElementById('message-text').value`),'KEEP DRAFT');
    assert.equal((await f.command({op:'stats'})).config_sequence,before.config_sequence);
    await identity('pico-a.local');await capture('verified-new-boot');
    // New origin carries only expected nonsecret context and needs a fresh password.
    const boot=await cdp.evaluate('hostnameState.target.boot_id');
    const receipt='#'+new URLSearchParams({'hostname-return':JSON.stringify({device:'1'.repeat(32),boot:'f'.repeat(32),name:'pico-a.local'})});
    await cdp.send('Page.navigate',{url:'http://pico-a.local/'+receipt});
    await until(()=>cdp.evaluate('typeof localIdentity!=="undefined" && !!localIdentity'),'hostname origin');
    assert.equal(await cdp.evaluate('localAuthenticated'),false);
    await login();assert.equal(await cdp.evaluate('document.title'),'pico-a.local - Station control');
    // Lost reply after a committed rename never resubmits; fresh login/read/review recovers.
    await field('hostname-input','wsprrypico-0a60df.local');dropNext=true;
    await cdp.evaluate(`document.getElementById('hostname-form').requestSubmit()`);
    await until(()=>cdp.evaluate('!busy && !radio.authenticated'),'lost save reply');
    assert.equal((await f.command({op:'stats'})).profile_generation,'3');
    assert.match(await cdp.evaluate('document.title'),/last confirmed|connection unknown/);
    await login();assert.equal(await cdp.evaluate('hostnameState.saved'),'wsprrypico-0a60df.local');
    assert.equal(await cdp.evaluate(`document.getElementById('hostname-save').disabled`),true);
    await click('hostname-review');
    assert.equal(await cdp.evaluate(`document.getElementById('hostname-save').disabled`),false);

    // Two device-bound production fixtures in separate real browser tabs.
    const tabB=await cdp.send('Target.createTarget',{url:'http://pico-b.local/'});
    const infoB=await until(async()=>(await(await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(p=>p.id===tabB.targetId),'second Pico tab');
    cdpB=new Cdp(infoB.webSocketDebuggerUrl);await cdpB.open();
    await until(()=>cdpB.evaluate('document.title==="pico-b.local - Station control"'),'second Pico title');
    assert.match(await cdp.evaluate('document.title'),/^pico-a.local - Station control/);
    await cdp.send('Emulation.setDeviceMetricsOverride',{width:640,height:450,deviceScaleFactor:1,mobile:false});
    await cdp.evaluate(`document.body.style.zoom='2';document.getElementById('hostname-form').scrollIntoView()`);
    assert.equal(await cdp.evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'200% zoom no overflow');
    if(process.env.HOSTNAME_BROWSER_NO_CAPTURE!=='1') { ++captures;const zoom=await cdp.send('Page.captureScreenshot',{format:'png'});
    await writeFile(path.join(output,'zoom-200-percent.png'),Buffer.from(zoom.data,'base64')); }
    await cdp.evaluate(`document.body.style.zoom=''`);
    assert.equal(await cdpB.evaluate(`document.getElementById('device-id').textContent`),'2'.repeat(32));
    assert.equal(await cdpB.evaluate(`document.getElementById('device-name').textContent`),'pico-b.local');
    // A receipt for a different full device refuses login before sending credentials.
    const wrong='#'+new URLSearchParams({'hostname-return':JSON.stringify({device:'2'.repeat(32),boot,name:'pico-a.local'})});
    await cdp.send('Page.navigate',{url:'http://pico-a.local/'+wrong});
    await until(()=>cdp.evaluate(`document.getElementById('notice')?.textContent.includes('different Pico')`),'wrong return identity');
    const starts=requests.filter(r=>r.path.endsWith('/start')).length;
    await field('local-password','test-password');await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
    await until(()=>cdp.evaluate('!busy'),'wrong-device explicit login refused');
    assert.equal(requests.filter(r=>r.path.endsWith('/start')).length,starts);
    assert.equal((await f.command({op:'stats'})).profile_generation,'3');
    // Maximum name comes from a real persisted profile/new boot, never a DOM injection.
    await cdp.send('Page.navigate',{url:'http://192.168.1.53/'});
    await until(()=>cdp.evaluate('!busy && !!localIdentity'),'return by IP');await login();
    await click('wifi-host-link');await click('hostname-review');
    const longName='x'.repeat(63)+'.local';await field('hostname-input',longName);
    await cdp.evaluate(`document.getElementById('hostname-form').requestSubmit()`);
    await until(()=>cdp.evaluate('!busy && !localAuthenticated'),'long name saved');
    await f.command({op:'reboot'});await f.time(f.now+3000);
    await cdp.send('Page.navigate',{url:'http://'+longName+'/'});
    await until(()=>cdp.evaluate(`!busy && document.getElementById('device-name').textContent===${JSON.stringify(longName)}`),'long name applied');
    await identity(longName);await cdp.evaluate(`document.getElementById('device-diagnostics').open=true`);
    await capture('maximum-active-hostname');await login();
    await cdp.send('Emulation.setDeviceMetricsOverride',{width:640,height:450,deviceScaleFactor:1,mobile:false});
    await cdp.evaluate(`document.body.style.zoom='2';scrollTo(0,0)`);
    assert.equal(await cdp.evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'long identity at 200% zoom');
    if(process.env.HOSTNAME_BROWSER_NO_CAPTURE!=='1') {++captures;const zoom=await cdp.send('Page.captureScreenshot',{format:'png'});await writeFile(path.join(output,'long-name-zoom-200.png'),Buffer.from(zoom.data,'base64'));}
    await cdp.evaluate(`document.body.style.zoom=''`);
    await f.time(f.now+300001);await click('refresh');
    await until(()=>cdp.evaluate('!busy && !localAuthenticated && !radio.authenticated'),'session expiry');
    assert.match(await cdp.evaluate(`document.getElementById('local-status').textContent`),/Session ended/);
    assert.match(await cdp.evaluate(`document.getElementById('device-name-state').textContent`),/Last confirmed/);
    await capture('session-expired');await login();
    failRadioRequests=true;await click('refresh');await until(()=>cdp.evaluate('!busy && !online'),'connection failure');
    assert.match(await cdp.evaluate(`document.getElementById('device-name-state').textContent`),/Last confirmed/);
    assert.match(await cdp.evaluate('document.title'),/last confirmed/);await capture('disconnected-last-confirmed');
    console.log(JSON.stringify({identity_heading:true,full_id_diagnostics:true,keyboard_disclosure:true,no_diagnostics_effects:true,unknown_name:true,long_active_name:true,stale_agreement:true,browser:(await cdp.send('Browser.getVersion')).product,served_assets:true,real_crypto:true,
        initial_title:true,hostname_origin:true,canonical_validation:true,generation_save:true,new_boot_readback:true,
        lost_reply_no_replay:true,wrong_device_no_login:true,draft_preserved:true,cancel_countdown:true,screenshots:captures,two_device_tabs:true,zoom_200:true}));
} catch(error) {
    console.error(JSON.stringify({requests,driver_stderr:f.stderr,page:cdp?await cdp.evaluate(`({url:location.href,text:document.body?.innerText.slice(0,600),scripts:[...document.scripts].map(s=>s.src)})`).catch(e=>e.message):null}));
    throw error;
} finally {
    cdpB?.ws.close();cdp?.ws.close();chrome?.kill();proxy.close();await f.stop();await fB.stop();
}
