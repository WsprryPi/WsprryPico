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
const output=path.resolve(process.argv[3] || 'build/phase15-11-browser');
await mkdir(output,{recursive:true});
const profile=await mkdtemp(path.join(os.tmpdir(),'p1511-chrome-'));
let f=new Fixture(process.argv[2]);await f.time(1000);
let dropNext=false, chrome, cdp, cdpB;
const fB=new Fixture(process.argv[2],['2'.repeat(32)]);await fB.time(1000);
const bClient=fB.client();await fB.login(bClient);const bResource=await bClient.request('hostname');const bName=await bResource.json();
await bClient.request('hostname','PUT',{schema:'transmitter-hostname/1',target:bName.target,hostname:'pico-b.local'},bResource.headers.get('etag'));
await fB.command({op:'reboot'});await fB.time(3000); const requests=[];
const proxy=http.createServer(async(req,res)=>{
    try {
        const u=new URL(req.url.startsWith('http:')?req.url:'http://192.168.1.53'+req.url);
        if(!['192.168.1.53','192.168.4.1','wsprrypico-0a60df.local','pico-a.local','pico-b.local', 'x'.repeat(63)+'.local'].includes(u.hostname)){res.writeHead(403);res.end();return;}
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
async function capture(name,anchor=null){
    if(process.env.HOSTNAME_BROWSER_NO_CAPTURE==='1')return;
    for(const theme of ['light','dark'])for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]){
        await cdp.send('Emulation.setDeviceMetricsOverride',{...view,name:undefined,deviceScaleFactor:1,mobile:view.name==='mobile'});
        await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]});
        await cdp.evaluate(anchor ? `document.getElementById(${JSON.stringify(anchor)}).scrollIntoView({block:'start'})` : 'scrollTo(0,0)');
        assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false,'horizontal overflow');
        const image=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
        await writeFile(path.join(output,`${name}-${view.name}-${theme}.png`),Buffer.from(image.data,'base64'));
    }
}
try {
    chrome=spawn(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        ['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',
         '--remote-debugging-port=0',`--user-data-dir=${profile}`,`--proxy-server=http://127.0.0.1:${port}`,'--proxy-bypass-list=<-loopback>','http://192.168.1.53/'],{stdio:'ignore'});
    const debugPort=await until(async()=>Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]),'Chrome startup',60000);
    const page=await until(async()=>(await(await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(p=>p.type==='page'),'page');
    cdp=new Cdp(page.webSocketDebuggerUrl);await cdp.open();await cdp.send('Page.enable');
    await until(()=>cdp.evaluate('typeof radio!=="undefined" && !!localIdentity'),'production control document');
    assert.equal(await cdp.evaluate(`!document.getElementById('station-area').hidden && document.getElementById('wifi-host-area').hidden`),true);
    await capture('lan-default');
    await field('local-password','test-password');await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
    await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'login');
    const baseline=await f.command({op:'stats'}), starts=requests.filter(r=>r.path.endsWith('/start')).length;
    assert.equal(await cdp.evaluate(`document.getElementById('engineering-station-form').hidden && document.getElementById('engineering-network-form').hidden`),true);
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-station-form').hidden`),false);
    await field('consumer-callsign','PJ4/AA0NT');await field('consumer-locator','EM18IG');
    await field('message-text','KEEP MESSAGE');
    await cdp.evaluate(`document.getElementById('config').elements.schedules.value='240 / 0';document.getElementById('config').dispatchEvent(new Event('input',{bubbles:true}))`);
    await click('wifi-host-link');await field('consumer-ssid','DRAFT NETWORK');await field('consumer-password','draft-password');
    await field('hostname-input','x'.repeat(63)+'.local');
    for(let i=0;i<5;i++){await click('station-link');await click('wifi-host-link');}
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-password').value`),'draft-password');
    assert.equal(requests.filter(r=>r.path.endsWith('/start')).length,starts,'navigation must not allocate sessions');
    assert.equal((await f.command({op:'stats'})).profile_programs,baseline.profile_programs);
    assert.equal((await f.command({op:'stats'})).config_sequence,baseline.config_sequence);
    await capture('wifi-host-drafts','wifi-host-area');
    await click('station-link');await capture('station-drafts','station-area');await click('wifi-host-link');
    await cdp.evaluate('history.back()');await until(()=>cdp.evaluate('location.pathname==="/station"'),'back');
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-callsign').value`),'PJ4/AA0NT');
    assert.equal(await cdp.evaluate(`document.getElementById('message-text').value`),'KEEP MESSAGE');
    await cdp.evaluate('history.forward()');await until(()=>cdp.evaluate('location.pathname==="/wifi-host"'),'forward');
    await cdp.evaluate(`document.getElementById('wifi-host-link').focus()`);
    assert.equal(await cdp.evaluate(`document.activeElement.id`),'wifi-host-link');
    await click('refresh');await until(()=>cdp.evaluate('!busy'),'poll');
    assert.equal(await cdp.evaluate(`document.activeElement.id`),'wifi-host-link','poll keeps keyboard focus');
    assert.equal(await cdp.evaluate(`location.pathname`),'/wifi-host');
    await cdp.send('Emulation.setDeviceMetricsOverride',{width:640,height:450,deviceScaleFactor:1,mobile:false});
    await cdp.evaluate(`document.body.style.zoom='2'`);
    assert.equal(await cdp.evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'200 percent zoom');
    const zoom=await cdp.send('Page.captureScreenshot',{format:'png'});await writeFile(path.join(output,'organization-zoom.png'),Buffer.from(zoom.data,'base64'));
    await cdp.evaluate(`document.body.style.zoom=''`);
    // Bookmark selection survives observation; explicit navigation can override it.
    await cdp.evaluate(`location.hash='hostname-form'`);await click('station-link');
    assert.equal(await cdp.evaluate(`document.getElementById('station-area').hidden`),false);
    await click('wifi-host-link');await cdp.send('Page.reload');
    await until(()=>cdp.evaluate('typeof radio!=="undefined" && !!localIdentity && !localAuthenticated'),'reload requires explicit login');
    assert.equal(await cdp.evaluate(`document.getElementById('wifi-host-area').hidden`),false);
    assert.equal(requests.filter(r=>r.path.endsWith('/start')).length,starts);
    // AP root uses the actual accepted interface to select Wi-Fi/Host.
    await cdp.send('Page.navigate',{url:'http://192.168.4.1/'});
    await until(()=>cdp.evaluate('location.pathname==="/wifi-host" && typeof radio!=="undefined" && !!localIdentity'),'AP Wi-Fi/Host landing');
    await capture('ap-default');
    // A real station save must not validate unrelated empty message inputs.
    await field('local-password','test-password');await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
    await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'AP login');
    const beforeStation=(await f.command({op:'stats'})).profile_generation;
    await click('station-link');await field('consumer-callsign','K1ABC');await field('consumer-locator','FN42');
    assert.equal(await cdp.evaluate(`document.getElementById('message-text').value`),'');
    await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate('!busy && savedProgress?.data.station.callsign==="K1ABC"'),'station progress with empty message');
    assert.equal((await f.command({op:'stats'})).profile_generation,beforeStation,'saving progress does not apply station');
    await click('apply-station-progress');
    await until(()=>cdp.evaluate('!busy && !!consumerAttempt'),'explicit apply station progress');
    const stationReceipt=await cdp.evaluate('location.hash');assert.ok(stationReceipt.startsWith('#save='));
    await click('wifi-host-link');assert.equal(await cdp.evaluate('location.hash'),stationReceipt);
    await f.time(f.now+3000);await f.command({op:'activate'});await f.time(f.now+1000);
    assert.notEqual((await f.command({op:'stats'})).profile_generation,beforeStation);
    await field('local-password','test-password');await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
    await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'station save relogin');
    await click('consumer-check-save');await until(()=>cdp.evaluate('!busy && !consumerAttempt'),'explicit station receipt reconciliation');
    const afterStation=await f.command({op:'stats'});
    await click('station-link');await click('wifi-host-link');await click('refresh');await until(()=>cdp.evaluate('!busy'),'post-save area refresh');
    assert.equal((await f.command({op:'stats'})).profile_programs,afterStation.profile_programs,'navigation cannot replay setup');
    assert.equal(await cdp.evaluate('currentConfig.station.callsign'),'K1ABC');
    for(const mode of ['blank','network']) {
      await f.command({op:'page_profile',mode});
      await cdp.send('Page.navigate',{url:'http://192.168.4.1/'});
      await until(()=>cdp.evaluate(`!!document.getElementById('wifi-form') && !document.getElementById('credentials').hidden`),'Wi-Fi commissioning '+mode);
      await capture(mode+'-wifi-first');
      await cdp.send('Page.navigate',{url:'http://192.168.4.1/station'});
      await until(()=>cdp.evaluate(`!!document.getElementById('owner-form') && document.title.includes('Station setup')`),'station commissioning '+mode);
      assert.equal(await cdp.evaluate(`!!document.getElementById('message-form')`),false);
    }
    const noCrypto=await cdp.send('Page.addScriptToEvaluateOnNewDocument',{source:"Object.defineProperty(globalThis,'crypto',{value:undefined})"});
    await cdp.send('Page.navigate',{url:'http://192.168.4.1/'});
    await until(()=>cdp.evaluate(`!!document.getElementById('browser') && !document.getElementById('browser').hidden`),'captive crypto fallback');
    assert.equal(await cdp.evaluate(`document.getElementById('submit').disabled`),true);
    await capture('missing-crypto');
    await cdp.send('Page.removeScriptToEvaluateOnNewDocument',{identifier:noCrypto.identifier});
    await f.command({op:'page_profile',mode:'unavailable'});
    await cdp.send('Page.navigate',{url:'http://192.168.4.1/'});
    await until(()=>cdp.evaluate(`document.body.innerText.includes('USB Console recovery')`),'unavailable guidance');
    assert.equal(await cdp.evaluate(`document.forms.length`),0);
    await capture('unavailable-recovery');
    console.log(JSON.stringify({browser:(await cdp.send('Browser.getVersion')).product,production_routes:true,real_crypto:true,
      defaults:true,reciprocal_navigation:true,drafts:true,back_forward_reload:true,no_session_churn:true,no_navigation_mutations:true,station_save_without_message:true,receipt_reconciliation:true,zoom_200:true}));
} catch(error) {
    console.error(JSON.stringify({requests,driver_stderr:f.stderr,page:cdp?await cdp.evaluate('({url:location.href,text:document.body?.innerText.slice(0,1000)})').catch(e=>e.message):null}));throw error;
} finally {cdp?.ws.close();chrome?.kill();proxy.close();await f.stop();await fB.stop();}
