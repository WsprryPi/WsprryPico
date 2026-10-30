// Shipped page/bundle -> real browser -> production HTTP/crypto/commissioning.
// Only TCP/board/time boundaries use the existing deterministic fixture.
import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {mkdtemp, readFile, writeFile, mkdir} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {Fixture} from './consumer_sessions.test.mjs';
import {cleanupUiProcesses} from './ui_process_cleanup.mjs';

if (!globalThis.WebSocket) throw new Error('Use Node with built-in WebSocket; Node 20 needs --experimental-websocket');
if (!process.argv[2]) throw Error('Usage: node tests/wspr_browser_integration.mjs CONSUMER_BOOTSTRAP_DRIVER [OUTPUT_DIRECTORY]');
const processGroup=process.platform==='linux';
const noCapture=process.env.PICO_BROWSER_NO_CAPTURE==='1' || process.env.HOSTNAME_BROWSER_NO_CAPTURE==='1';
const output=path.resolve(process.argv[3] || 'build/wspr-browser-integration');
await mkdir(output,{recursive:true});
const profile=await mkdtemp(path.join(os.tmpdir(),'p158-chrome-'));
let f=new Fixture(process.argv[2]);await f.time(1000);
let chrome, cdp; const requests=[];
let proxyQueue=Promise.resolve();
const proxy=http.createServer((req,res)=>{proxyQueue=proxyQueue.then(()=>serve(req,res));});
async function serve(req,res){
    try {
        const u=new URL(req.url.startsWith('http:')?req.url:'http://192.168.1.53'+req.url);
        if(!['192.168.1.53','192.168.4.1'].includes(u.hostname)){res.writeHead(403);res.end();return;}
        const chunks=[];for await(const b of req)chunks.push(b);
        if(u.pathname.endsWith('/start'))await f.time(f.now+1000);
        const response=await f.fetch(u.hostname,u.hostname==='192.168.4.1',u.pathname,
            {method:req.method,body:Buffer.concat(chunks),headers:{'Content-Type':req.headers['content-type']||'application/json'},
                marker:u.pathname.startsWith('/api/owner/')?'Owner':u.pathname.startsWith('/api/bootstrap/')?'Bootstrap':'Radio'});
        const socket=f.socket;
        let bytes=Buffer.from(await response.arrayBuffer());
        const expected=Number(response.headers.get('content-length'));
        // Explicit TCP-ACK pumping of the existing bounded 100-step fixture, without
        // increasing a production/test deadline or accepting an incomplete response.
        for(let pump=0;bytes.length<expected && pump<4;++pump){
            await f.command({op:'complete',socket});
            const snapshot=await f.command({op:'wire',socket});
            const wire=Buffer.from(snapshot.wire,'hex');bytes=wire.subarray(wire.indexOf('\r\n\r\n')+4);
        }
        assert.equal(bytes.length,expected,'complete production HTTP response');
        requests.push({path:u.pathname,status:response.status,bytes:bytes.length});
        if(u.pathname === "/") await writeFile(path.join(output,"root.html"),bytes);
        res.writeHead(response.status,Object.fromEntries(response.headers));res.end(bytes);
    }catch(error){res.writeHead(500,{'Content-Type':'text/plain'});res.end(error.message);}
}
await new Promise(resolve=>proxy.listen(0,'127.0.0.1',resolve));
const port=proxy.address().port;
class Cdp {
    constructor(url){this.ws=new WebSocket(url);this.sequence=0;this.pending=new Map();this.ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&this.pending.has(m.id)){const p=this.pending.get(m.id);this.pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result);}};}
    async open(){if(this.ws.readyState===1)return;await new Promise((resolve,reject)=>{this.ws.onopen=resolve;this.ws.onerror=reject;});}
    send(method,params={}){const id=++this.sequence;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{this.pending.delete(id);reject(Error('CDP deadline: '+method));},15000);this.pending.set(id,{resolve:value=>{clearTimeout(timer);resolve(value);},reject:error=>{clearTimeout(timer);reject(error);}});this.ws.send(JSON.stringify({id,method,params}));});}
    async evaluate(expression){const r=await this.send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
}
async function until(fn,label,ms=10000){const end=Date.now()+ms;let last;while(Date.now()<end){try{const r=await fn();if(r)return r;}catch(e){last=e;}await new Promise(r=>setTimeout(r,50));}throw Error('Timed out: '+label+(last?' '+last.message:''));}
async function field(id,value){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});if(${JSON.stringify(id)}==='local-password'&&!document.getElementById('local-access').open)document.getElementById('access-toggle').click();globalThis.WsprryPicoSections?.reveal(e);e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));}`);}
// Submit once the production form admits it; discovery/polling can briefly disable login.
async function submitLogin(){await until(()=>cdp.evaluate(`!busy && !document.getElementById('login-submit').disabled && (document.getElementById('local-login').requestSubmit(),true)`),'login form available');}
async function click(id){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});globalThis.WsprryPicoSections?.reveal(e);e.click();}`);}
async function capture(name){
    for(const theme of ['light','dark'])for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]){
        await cdp.send('Emulation.setDeviceMetricsOverride',{...view,name:undefined,deviceScaleFactor:1,mobile:view.name==='mobile'});
        await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]});
        await cdp.evaluate(`document.getElementById('consumer-station-form').scrollIntoView({block:'start'})`);
        assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false,'horizontal overflow');
        if(noCapture)continue;
        const image=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
        await writeFile(path.join(output,`${name}-${view.name}-${theme}.png`),Buffer.from(image.data,'base64'));
    }
}
try {
    chrome=spawn(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        ['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',
            '--remote-debugging-port=0',`--user-data-dir=${profile}`,`--proxy-server=http://127.0.0.1:${port}`,'--proxy-bypass-list=<-loopback>','http://192.168.1.53/'],{stdio:'ignore',detached:processGroup});
    const debugPort=await until(async()=>Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]),'Chrome startup',60000);
    const page=await until(async()=>(await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(p=>p.type==='page'),'page');
    cdp=new Cdp(page.webSocketDebuggerUrl);await cdp.open();await cdp.send('Page.enable');
    await until(()=>cdp.evaluate(`typeof radio !== 'undefined' && !!document.getElementById('local-password')`),'shipped radio page');
    await until(()=>cdp.evaluate(`!busy && !!localIdentity`),'discovery complete before login');
    await field('local-password','test-password');await submitLogin();
    await until(()=>cdp.evaluate(`localAuthenticated && !busy`),'actual browser login');
    await click('read-saved');
    await until(()=>cdp.evaluate(`applicationVersion===2 && writeState==='review' && !busy`),'versioned saved-state readback');
    await click('review-saved');
    await until(()=>cdp.evaluate(`writeState==='ready' && !busy && !document.getElementById('consumer-station-settings').disabled`),'review enables editing');
    await field('consumer-callsign','AA0NT/12');await field('consumer-locator','EM18');
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-wspr-plan')`),null,'no provisional message-type callout');
    await cdp.evaluate(`document.getElementById('consumer-callsign').focus()`);
    await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
    await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
    assert.equal(await cdp.evaluate('document.activeElement.id'),'consumer-locator');
    await capture('type2-draft');
    await field('consumer-callsign','<AA0NT>');await field('consumer-locator','EM18');
    assert.equal(await cdp.evaluate(`(async()=> (await api('wspr-plan','POST',{callsign:'<AA0NT>',locator:'EM18',power_dbm:20})).data.supported)()`),false);
    await field('consumer-locator','EM18IG');
    assert.deepEqual(await cdp.evaluate(`(async()=> (await api('wspr-plan','POST',{callsign:'<AA0NT>',locator:'EM18IG',power_dbm:20})).data.frame_types)()`),['type3']);
    await field('consumer-callsign','W1A/AA0NT');
    await cdp.evaluate(`reviewWspr({callsign:'W1A/AA0NT',locator:'EM18IG',power_dbm:20})`);
    assert.deepEqual(await cdp.evaluate(`(async()=> (await api('wspr-plan','POST',{callsign:'W1A/AA0NT',locator:'EM18IG',power_dbm:20})).data.frame_types)()`),['type2','type3']);
    await field('consumer-callsign','<W1A/AA0NT>');
    await cdp.evaluate(`reviewWspr({callsign:'<W1A/AA0NT>',locator:'EM18IG',power_dbm:20})`);
    assert.deepEqual(await cdp.evaluate(`(async()=> (await api('wspr-plan','POST',{callsign:'<W1A/AA0NT>',locator:'EM18IG',power_dbm:20})).data.frame_types)()`),['type3']);
    await field('consumer-callsign','AA0NT/09');
    await cdp.evaluate(`reviewWspr({callsign:'AA0NT/09',locator:'EM18IG',power_dbm:20})`);
    assert.equal(await cdp.evaluate(`(async()=> (await api('wspr-plan','POST',{callsign:'AA0NT/09',locator:'EM18IG',power_dbm:20})).data.alternate_callsign)()`),'AA0NT/Z');
    await capture('pair-ambiguity');
    const before=await f.command({op:'stats'});
    await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && savedProgress?.data.station_complete && savedProgress.data.fields.callsign==='AA0NT/09'`),'station draft confirmed');
    assert.equal((await f.command({op:'stats'})).profile_programs,before.profile_programs,'draft save does not apply station');
    assert.match(await cdp.evaluate(`document.getElementById('progress-station-status').textContent`),/WSPR Type 2 \+ Type 3/);
    await click('apply-station-progress');
    await until(()=>cdp.evaluate(`!busy && document.getElementById('consumer-save-status').textContent.startsWith('Settings accepted.')`),'one explicit station application');
    await f.time(f.now+2000);await f.command({op:'activate'});await f.time(f.now+1000);
    const a=f.client();await f.login(a);const saved=await (await a.request('config')).json();
    assert.equal(saved.config.station.callsign,'AA0NT/09');assert.equal(saved.config.station.locator,'EM18IG');
    const application=await (await a.request('application/2')).json();assert.equal(application.wspr_plan.type2_ambiguous,true);assert.equal(application.wspr_plan.alternate_callsign,'AA0NT/Z');
    assert.ok((await f.command({op:'stats'})).profile_programs>before.profile_programs);
    await a.logout();
    await cdp.send('Page.navigate',{url:'about:blank'});
    await until(()=>cdp.evaluate(`location.href==='about:blank'`),'old page stopped');
    await f.stop();f=new Fixture(process.argv[2]);await f.time(1000);
    await cdp.send('Page.navigate',{url:'http://192.168.1.53/'});
    await until(()=>cdp.evaluate(`typeof localIdentity!=='undefined' && localIdentity && !busy`),'fresh consumer discovery');
    await field('local-password','test-password');await submitLogin();
    await until(()=>cdp.evaluate(`localAuthenticated && !busy`),'fresh consumer login');
    await field('consumer-callsign','<AA0NT>');await field('consumer-locator','EM18IG');
    await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && savedProgress.data.station_complete && savedProgress.data.fields.callsign==='<AA0NT>'`),'saved Type 3 draft');
    const unsupportedBefore=await f.command({op:'stats'});
    // Double only the unavailable versioned view. The legacy view, crypto,
    // save/apply handlers and journals still run through production code.
    await cdp.evaluate(`globalThis.versionedApplicationReads=0;const actualRequest=radio.request.bind(radio);radio.request=(resource,...args)=>{
      if(['application/2','application/4'].includes(resource)){++versionedApplicationReads;return Promise.reject(Object.assign(new Error('Unsupported application view'),{code:'not_found'}));}
      return actualRequest(resource,...args);
    };`);
    await click('apply-station-progress');
    await until(()=>cdp.evaluate(`!busy && document.getElementById('notice').textContent.includes('has not confirmed Type 2/3')`),'unconfirmed application-view refusal');
    assert.ok(await cdp.evaluate('versionedApplicationReads>0'));
    assert.equal(await cdp.evaluate('applicationVersion'),1,'production legacy view selected for explicit review');
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-callsign').value`),'<AA0NT>');
    assert.equal((await f.command({op:'stats'})).profile_programs,unsupportedBefore.profile_programs);
    assert.equal((await f.command({op:'stats'})).config_sequence,unsupportedBefore.config_sequence);
    assert.equal((await f.command({op:'stats'})).setup_pending,false);
    await capture('unconfirmed-support-draft');
    console.log(JSON.stringify({browser:(await cdp.send('Browser.getVersion')).product,shipped_bundle:true,real_crypto:true,type2:true,type3:true,pair:true,ambiguity:true,commissioning:true,unconfirmed_support_refusal:true,draft_preserved:true,captures_enabled:!noCapture}));
} catch(error) {
    console.error(JSON.stringify({requests,driver_stderr:f.stderr,page:cdp?await cdp.evaluate(`({url:location.href,text:document.body?.innerText.slice(0,600),scripts:[...document.scripts].map(s=>s.src)})`).catch(e=>e.message):null}));
    throw error;
} finally {
    cdp?.ws.close();
    try {await cleanupUiProcesses([chrome],profile,{processGroup});}
    finally {
        proxy.closeAllConnections();await new Promise(resolve=>proxy.close(resolve));await proxyQueue;
        const stopped=await Promise.allSettled([f.stop()]);
        const errors=stopped.filter(result=>result.status==='rejected').map(result=>result.reason);
        if(errors.length)throw new AggregateError(errors,'Fixture shutdown failed');
    }
}
