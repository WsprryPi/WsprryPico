// Shipped page/bundle -> real browser -> production HTTP/crypto/commissioning.
// Only TCP/board/time boundaries use the existing deterministic fixture.
import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {mkdtemp, readFile, writeFile, mkdir} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {Fixture} from './consumer_sessions.test.mjs';
import {scanAccessibility} from './ui_review_accessibility.mjs';
import {cleanupUiProcesses} from './ui_process_cleanup.mjs';

if (!globalThis.WebSocket) throw new Error('Use Node with built-in WebSocket; Node 20 needs --experimental-websocket');
const output=path.resolve(process.argv[3] || 'build/progress-browser-integration');
await mkdir(output,{recursive:true});
const axeSource=process.env.UI_REVIEW_AXE_PATH ? await readFile(process.env.UI_REVIEW_AXE_PATH,'utf8') : null;
const accessibility=[];
const profile=await mkdtemp(path.join(os.tmpdir(),'p159-chrome-'));
if (!process.argv[2]) throw Error('Usage: node tests/progress_browser_integration.mjs CONSUMER_BOOTSTRAP_DRIVER [OUTPUT_DIRECTORY]');
const processGroup=process.platform==='linux';
let f=new Fixture(process.argv[2]);await f.time(1000);
let engineering=false, engineeringFault=null, radioFault=null, heldReply=null, releaseReply=null, chrome, cdp; const requests=[];
let proxyQueue=Promise.resolve();
const proxy=http.createServer((req,res)=>{proxyQueue=proxyQueue.then(()=>serve(req,res));});
async function serve(req,res){
    try {
        const u=new URL(req.url.startsWith('http:')?req.url:'http://192.168.1.53'+req.url);
        if(!['192.168.1.53','192.168.4.1'].includes(u.hostname)){res.writeHead(403);res.end();return;}
        if(engineering) {
          const chunks=[];for await(const b of req)chunks.push(b);
          const result=await f.command({op:'engineering_request',path:u.pathname,method:req.method,b64:Buffer.concat(chunks).toString('base64url'),match:req.headers['if-match']||''});
          let wire=Buffer.from(result.wire,'hex');
          if(/^\/api\/control\/v1\/progress\/update$/.test(u.pathname)) {
            if(engineeringFault==='future') {engineeringFault=null;const split=wire.indexOf('\r\n\r\n');const body=JSON.parse(wire.subarray(split+4));body.schema='progress9';wire=Buffer.concat([wire.subarray(0,split+4),Buffer.from(JSON.stringify(body))]);}
            if(engineeringFault==='hold') {engineeringFault=null;heldReply=true;await new Promise(resolve=>releaseReply=resolve);heldReply=false;}
          }
          const end=wire.indexOf('\r\n\r\n');
          const lines=wire.subarray(0,end).toString().split('\r\n'),code=Number(lines.shift().split(' ')[1]);
          const headers=Object.fromEntries(lines.map(line=>{const i=line.indexOf(':');return [line.slice(0,i),line.slice(i+1).trim()];}));headers['Content-Length']=String(wire.length-end-4);res.writeHead(code,headers);res.end(wire.subarray(end+4));return;
        }
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
        if(u.pathname==='/api/consumer/v1/request') {
          if(radioFault==='drop') {radioFault=null;res.destroy();return;}
          if(radioFault==='hold') {radioFault=null;heldReply=true;await new Promise(resolve=>releaseReply=resolve);heldReply=false;}
        }
        if(u.pathname === "/") await writeFile(path.join(output,"root.html"),bytes);
        res.writeHead(response.status,Object.fromEntries(response.headers));res.end(bytes);
    }catch(error){res.writeHead(500,{'Content-Type':'text/plain'});res.end(error.message);}
}
await new Promise(resolve=>proxy.listen(0,'127.0.0.1',resolve));
const port=proxy.address().port;
class Cdp {
    constructor(url){this.ws=new WebSocket(url);this.sequence=0;this.pending=new Map();this.ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&this.pending.has(m.id)){const p=this.pending.get(m.id);this.pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result);}};}
    async open(){if(this.ws.readyState===1)return;await new Promise((resolve,reject)=>{this.ws.onopen=resolve;this.ws.onerror=reject;});}
    send(method,params={}){const id=++this.sequence;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{this.pending.delete(id);reject(Error('CDP deadline: '+method));},20000);this.pending.set(id,{resolve:value=>{clearTimeout(timer);resolve(value);},reject:error=>{clearTimeout(timer);reject(error);}});this.ws.send(JSON.stringify({id,method,params}));});}
    async evaluate(expression){const r=await this.send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
}
async function until(fn,label,ms=10000){const end=Date.now()+ms;let last;while(Date.now()<end){try{const r=await fn();if(r)return r;}catch(e){last=e;}await new Promise(r=>setTimeout(r,50));}throw Error('Timed out: '+label+(last?' '+last.message:''));}
async function field(id,value){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)}) || document.querySelector('[name="'+${JSON.stringify(id)}+'"]');globalThis.WsprryPicoSections?.reveal(e);e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));}`);}
async function click(id){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});globalThis.WsprryPicoSections?.reveal(e);e.click();}`);}
async function capture(name){
    if (axeSource && ['engineering-mixed','engineering-late-invalid'].includes(name)) {
      for (const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]) {
        await cdp.send('Emulation.setDeviceMetricsOverride',{...view,name:undefined,deviceScaleFactor:1,mobile:view.name==='mobile'});
        accessibility.push({state:name,view:view.name,...await scanAccessibility(cdp,axeSource)});
        await writeFile(path.join(output,'accessibility.json'),JSON.stringify(accessibility,null,2)+'\n');
          assert.equal(accessibility.at(-1).violations.length,0,'axe violations: '+name+' '+view.name);
          assert.equal(accessibility.at(-1).incomplete.length,0,'axe manual review required: '+name+' '+view.name);
      }
    }
    if (process.env.PROGRESS_BROWSER_NO_CAPTURE === '1') return;
    for(const theme of ['light','dark'])for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]){
        await cdp.send('Emulation.setDeviceMetricsOverride',{...view,name:undefined,deviceScaleFactor:1,mobile:view.name==='mobile'});
        await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]});
        await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(name.startsWith('engineering-')?'engineering-station-form':'consumer-station-form')});WsprryPicoSections.reveal(e);e.scrollIntoView({block:'start'});}`);
        assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false,'horizontal overflow');
        const image=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
        await writeFile(path.join(output,`${name}-${view.name}-${theme}.png`),Buffer.from(image.data,'base64'));
    }
}
try {
    chrome=spawn(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        ['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',
            '--remote-debugging-port=0',`--user-data-dir=${profile}`,`--proxy-server=http://127.0.0.1:${port}`,'--proxy-bypass-list=<-loopback>','about:blank'],{stdio:'ignore',detached:processGroup});
    const debugPort=await until(async()=>Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]),'Chrome startup',60000);
    const page=await until(async()=>(await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(p=>p.type==='page'),'page');
    cdp=new Cdp(page.webSocketDebuggerUrl);await cdp.open();await cdp.send('Page.enable');
    await cdp.send('Page.navigate',{url:'http://192.168.1.53/'});
    await until(()=>cdp.evaluate(`typeof radio !== 'undefined' && !!document.getElementById('local-password')`),'shipped radio page');
    await until(()=>cdp.evaluate(`!busy && !!localIdentity`),'radio discovery complete');
    await field('local-password','test-password');await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
    await until(()=>cdp.evaluate(`localAuthenticated && !busy`),'actual browser login');
    await cdp.evaluate('WsprryPicoSections.recovery()');
    await click('read-saved');
    await until(()=>cdp.evaluate(`savedReadback?.application?.schema==='application' && savedReadback?.progress?.schema==='progress' && writeState==='review' && !busy`),'canonical application and progress saved-state readback');
    await click('review-saved');
    await until(()=>cdp.evaluate(`writeState==='ready' && !busy && !document.getElementById('consumer-station-settings').disabled`),'review enables editing');
    assert.equal(await cdp.evaluate(`savedProgress.data.schema`),'progress');
    const before = await f.command({op:'stats'});
    await field('consumer-callsign','AA0NT/09');await field('consumer-locator','');await field('message-text','');
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-station-form').noValidate`),true,'partial saves bypass native completeness checks');
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-locator').validity.valueMissing`),true);
    await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && savedProgress.data.fields.callsign==='AA0NT/09' && savedProgress.data.fields.locator===null`),'callsign saved beside blank locator/QRSS');
    assert.equal(await cdp.evaluate(`document.getElementById('message-text').value`),'');
    assert.match(await cdp.evaluate(`document.getElementById('progress-station-status').textContent`),/grid locator.*missing/);
    let stats=await f.command({op:'stats'});assert.equal(stats.profile_programs,before.profile_programs);assert.equal(stats.config_sequence,before.config_sequence);assert.equal(stats.api_restarts,0);
    assert.equal(await cdp.evaluate(`savedReadback.progress===savedProgress.data && savedReadback.revision===revision`),true,'confirmed save advances open comparison');
    assert.equal(await cdp.evaluate(`!!JSON.parse(document.getElementById('saved-readback').textContent).application_at_last_read`),true,'last-read application diagnostics preserved');
    await field('consumer-callsign','BB1BB');
    assert.match(await cdp.evaluate(`document.getElementById('draft-comparison').textContent`),/AA0NT\/09/,'comparison includes newly confirmed progress');
    await field('consumer-callsign','AA0NT/09');
    await capture('incomplete-saved');
    await field('consumer-callsign','AA0NT/12');await field('consumer-locator','BAD');await field('consumer-power','0');
    await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && savedProgress.data.fields.callsign==='AA0NT/12' && savedProgress.data.fields.power_dbm===0`),'mixed valid fields saved');
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-locator').value`),'BAD');
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-locator').getAttribute('aria-invalid')`),'true');
    assert.equal(await cdp.evaluate(`savedProgress.data.fields.locator`),null);
    await capture('mixed-errors');
    // Explicit read/review preserves invalid browser text; explicit discard reload adopts saved progress.
    await click('read-saved');await until(()=>cdp.evaluate(`writeState==='review' && !busy`),'readback');
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-locator').value`),'BAD');
    await click('review-saved');await until(()=>cdp.evaluate(`writeState==='ready' && !busy`),'explicit review');
    await field('consumer-callsign','BB1BB');await cdp.evaluate('window.confirm=()=>true');
    await click('reload-config');await until(()=>cdp.evaluate(`!busy && document.getElementById('consumer-callsign').value==='AA0NT/12'`),'reload restores device-saved draft, not applied');
    assert.equal(await cdp.evaluate('progressEdits.size'),0);assert.equal(await cdp.evaluate(`document.getElementById('consumer-locator').value`),'');
    await field('consumer-locator','EM18IG');await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && savedProgress.data.station_complete && savedProgress.data.station.power_dbm===0`),'complete persisted station');
    assert.deepEqual(await cdp.evaluate(`savedProgress.data.wspr_plan.frame_types`),['type2','type3']);
    await field('consumer-locator','BAD');await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && document.getElementById('consumer-locator').getAttribute('aria-invalid')==='true'`),'invalid locator result');
    await click('reload-config');await until(()=>cdp.evaluate(`!busy && document.getElementById('consumer-locator').value==='EM18IG'`),'explicit reload adopts saved valid locator');
    assert.notEqual(await cdp.evaluate(`document.getElementById('consumer-locator').getAttribute('aria-invalid')`),'true');
    assert.match(await cdp.evaluate(`document.getElementById('progress-station-status').textContent`),/WSPR Type 2 \+ Type 3/);
    // Native selection exposes an explicit clear without coercing blank to zero.
    assert.equal(await cdp.evaluate(`Array.from(document.getElementById('consumer-power').options).some(o=>o.value==='')`),true,'native empty power option');
    const beforeClear=await f.command({op:'stats'});
    await field('consumer-power','');await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && savedProgress.data.fields.power_dbm===null`),'native blank power is a saved tombstone');
    const afterClear=await f.command({op:'stats'});
    for(const key of ['profile_programs','config_sequence','api_restarts']) assert.equal(afterClear[key],beforeClear[key],'clear has no applied-profile/config/restart side effect');
    assert.equal(await cdp.evaluate(`document.getElementById('apply-station-progress').matches(':disabled')`),true);
    await field('consumer-power','0');await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && savedProgress.data.station_complete && savedProgress.data.station.power_dbm===0`),'explicit zero restored');
    await capture('complete-unapplied');
    await click('apply-station-progress');
    await until(()=>cdp.evaluate(`document.getElementById('consumer-save-status').textContent.startsWith('Settings accepted.')`),'delivered explicit profile application');
    await f.time(f.now+2000);await f.command({op:'activate'});await f.time(f.now+1000);
    const a=f.client();await f.login(a);const applied=await (await a.request('config')).json();
    assert.equal(applied.config.station.callsign,'AA0NT/12');assert.equal(applied.config.station.locator,'EM18IG');assert.equal(applied.config.station.power_dbm,0);await a.logout();
    // Newly reconstructed runtime/journals keep saved progress through boot without applying it.
    await cdp.send('Page.navigate',{url:'about:blank'});await f.command({op:'reboot'});await f.time(f.now+1000);
    const b=f.client();await f.login(b);const resource=await b.request('progress');const progress=await resource.json();
    assert.equal(progress.fields.callsign,'AA0NT/12');assert.equal(progress.fields.power_dbm,0);assert.equal(progress.matches_applied,true);await b.logout();
    await f.stop();f=new Fixture(process.argv[2]);await f.time(1000);await f.command({op:'page_profile',mode:'network'});
    // A network-only profile now uses the same shipped authenticated management page.
    await cdp.send('Page.navigate',{url:'http://192.168.4.1/station'});
    await until(()=>cdp.evaluate(`typeof localIdentity!=='undefined' && localIdentity && !busy`),'network-only discovery');
    await field('local-password','test-password');await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
    await until(()=>cdp.evaluate(`localAuthenticated && !busy && savedProgress`),'network-only login');
    const networkBefore=await f.command({op:'stats'});
    await field('consumer-callsign','AA0NT');await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && savedProgress.data.fields.callsign==='AA0NT'`),'network-only partial save');
    assert.equal(await cdp.evaluate(`savedProgress.data.station_complete`),false);
    assert.equal((await f.command({op:'stats'})).profile_programs,networkBefore.profile_programs);
    assert.equal((await f.command({op:'stats'})).config_sequence,networkBefore.config_sequence);
    const peer=f.client('192.168.4.1',true);await f.time(f.now+1000);await f.login(peer);
    const beforeLost=await (await peer.request('progress')).json();
    radioFault='drop';await field('consumer-callsign','CC2CC');
    await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && !radio.authenticated`),'lost encrypted progress reply');
    const lostResponse=await peer.request('progress'),lost=await lostResponse.json();
    assert.equal(BigInt(lost.draft_revision),BigInt(beforeLost.draft_revision)+1n);
    assert.equal(lost.fields.callsign,'CC2CC');
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-callsign').value`),'CC2CC');
    // Independent peer edits must be shown by explicit readback without claiming the interrupted save.
    const changed=await peer.request('progress/update','POST',{schema:'progress',target:lost.target,request_id:'b'.repeat(32),fields:{callsign:'BB1BB'}},lostResponse.headers.get('etag'));
    assert.equal(changed.status,200);
    await field('consumer-callsign','DD3DD');await f.time(f.now+1000);
    await field('local-password','test-password');await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && radio.authenticated && writeState==='review'`),'explicit login and readback');
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-callsign').value`),'DD3DD');
    assert.equal(await cdp.evaluate(`savedProgress.data.fields.callsign`),'BB1BB');
    await click('review-saved');await until(()=>cdp.evaluate(`!busy && writeState==='ready'`),'review independent saved progress');
    assert.equal((await (await peer.request('progress')).json()).draft_revision,(await changed.json()).draft_revision,'review does not replay a save');
    radioFault='hold';await field('consumer-callsign','AA0NT');
    await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
    await until(()=>heldReply,'held production progress acknowledgement');
    await field('consumer-callsign','EE4EE');releaseReply();
    await until(()=>cdp.evaluate(`!busy`),'late acknowledgement');
    assert.equal(await cdp.evaluate(`document.getElementById('consumer-callsign').value`),'EE4EE','late acknowledgement preserves newer edit');
    assert.equal(await cdp.evaluate(`savedProgress.data.fields.callsign`),'AA0NT');
    assert.equal((await f.command({op:'stats'})).profile_programs,networkBefore.profile_programs);
    await peer.logout();
    await field('consumer-callsign','AA0NT');await field('consumer-locator','EM18IG');await field('consumer-power','0');
    await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && savedProgress.data.station_complete && savedProgress.data.station.power_dbm===0`),'network-only complete draft');
    await capture('network-complete-draft');
    await cdp.send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
    await cdp.evaluate(`document.documentElement.style.zoom='2';document.getElementById('radio-settings').open=true;document.getElementById('progress-station-status').scrollIntoView()`);
    assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false,'200% zoom horizontal overflow');
    await cdp.evaluate(`document.documentElement.style.zoom=''`);
    await click('apply-station-progress');
    await until(()=>cdp.evaluate(`document.getElementById('consumer-save-status').textContent.startsWith('Settings accepted.')`),'explicit network-only station application');
    await f.time(f.now+2000);await f.command({op:'reboot'});await f.time(f.now+1000);
    const final=f.client();await f.login(final);const saved=await (await final.request('config')).json();
    assert.equal(saved.config.station.callsign,'AA0NT');assert.equal(saved.config.station.locator,'EM18IG');assert.equal(saved.config.station.power_dbm,0);await final.logout();
    // Genuine engineering page/API with the mTLS authentication boundary doubled.
    engineering=true;await cdp.send('Page.navigate',{url:'http://192.168.1.53/'});
    await until(()=>cdp.evaluate(`typeof savedProgress!=='undefined' && savedProgress && !busy && !radio`),'engineering saved progress');
    await click('wifi-host-link');await field('ssid','é');await field('password','test-password');
    await cdp.evaluate(`document.getElementById('engineering-network-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && document.querySelector('[name=ssid]').getAttribute('aria-invalid')==='true'`),'grouped Wi-Fi validation');
    assert.equal(await cdp.evaluate(`['ssid','password'].every(n=>document.querySelector('[name='+n+']').getAttribute('aria-invalid')==='true' && document.querySelector('[name='+n+']').getAttribute('aria-describedby').includes('progress-error-settings-wifi'))`),true);
    await field('password','corrected-password');
    assert.equal(await cdp.evaluate(`['ssid','password'].every(n=>document.querySelector('[name='+n+']').getAttribute('aria-invalid')==='false')`),true,'editing either Wi-Fi member clears group stale error');
    await field('ssid','test');await click('station-link');
    await field('callsign','BB1BB');await field('power_dbm','2147483648');
    await cdp.evaluate(`document.getElementById('engineering-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && savedProgress.data.fields.callsign==='BB1BB'`),'engineering partial save with overflow');
    assert.equal(await cdp.evaluate(`savedProgress.data.last_outcomes.power_dbm`),'invalid');
    assert.equal(await cdp.evaluate(`document.querySelector('[name=power_dbm]').value`),'2147483648');
    assert.equal(await cdp.evaluate(`document.querySelector('[name=power_dbm]').getAttribute('aria-invalid')`),'true');
    await capture('engineering-mixed');
    await field('schedules','2147483648 / 0');await field('expiry','2040-01-01T00:00');
    await cdp.evaluate(`{const e=document.querySelector('[name=enabled]');e.checked=true;e.dispatchEvent(new Event('input',{bubbles:true}));document.getElementById('config').requestSubmit();}`);
    await until(()=>cdp.evaluate(`!busy && savedProgress.data.fields.enabled===true`),'radio partial save beside overflow schedule and expiry');
    assert.equal(await cdp.evaluate(`savedProgress.data.last_outcomes.schedules`),'invalid');
    assert.equal(await cdp.evaluate(`savedProgress.data.last_outcomes.expires_utc_s`),'invalid');
    assert.equal(await cdp.evaluate(`currentConfig.enabled`),false);
    // Contradictory future acknowledgement is uncertain; read/review never retries.
    await field('power_dbm','3e1');await cdp.evaluate(`document.getElementById('engineering-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && savedProgress.data.fields.power_dbm===30`),'native-valid exact integer spelling');
    await field('callsign','CC2CC');engineeringFault='future';
    await cdp.evaluate(`document.getElementById('engineering-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && writeState==='readback'`),'future acknowledgement blocks writes');
    assert.equal(await cdp.evaluate(`document.getElementById('save-engineering-station-progress').matches(':disabled')`),true);
    assert.equal(await cdp.evaluate(`document.querySelector('[name=callsign]').value`),'CC2CC');
    await capture('engineering-unconfirmed');
    await click('read-saved');await until(()=>cdp.evaluate(`!busy && writeState==='review'`),'uncertain progress authoritative readback');
    const uncertainSequence=await cdp.evaluate(`savedProgress.data.draft_revision`);
    await click('review-saved');await until(()=>cdp.evaluate(`!busy && writeState==='ready'`),'uncertain progress explicit review');
    assert.equal(await cdp.evaluate(`savedProgress.data.draft_revision`),uncertainSequence);
    // A delayed acknowledgement cannot replace a newer browser edit.
    await field('callsign','DD3DD');engineeringFault='hold';
    await cdp.evaluate(`document.getElementById('engineering-station-form').requestSubmit()`);
    await until(()=>heldReply,'held committed reply');await field('callsign','EE4EE');releaseReply();
    await until(()=>cdp.evaluate(`!busy && savedProgress.data.fields.callsign==='DD3DD'`),'late acknowledgement reconciliation');
    assert.equal(await cdp.evaluate(`document.querySelector('[name=callsign]').value`),'EE4EE');
    assert.equal(await cdp.evaluate(`progressEdits.has('callsign')`),true);
    assert.match(await cdp.evaluate(`document.getElementById('progress-error-settings-callsign').textContent`),/newer edit remains unsaved/);
    await field('locator','BAD');engineeringFault='hold';
    await cdp.evaluate(`document.getElementById('engineering-station-form').requestSubmit()`);
    await until(()=>heldReply,'engineering rejected earlier locator reply');await field('locator','EM18IG');releaseReply();
    await until(()=>cdp.evaluate(`!busy`),'engineering rejected late acknowledgement');
    const engineeringMixed=await cdp.evaluate(`document.getElementById('progress-error-settings-locator').textContent`);
    assert.match(engineeringMixed,/not saved/i);assert.match(engineeringMixed,/newer edit remains unsaved/);assert.doesNotMatch(engineeringMixed,/Earlier value (was )?saved/);
    assert.equal(await cdp.evaluate(`document.querySelector('[name=locator]').value`),'EM18IG');
    assert.equal(await cdp.evaluate(`progressEdits.has('locator')`),true);
    await capture('engineering-late-invalid');
    await field('locator','');engineeringFault='hold';
    await cdp.evaluate(`document.getElementById('engineering-station-form').requestSubmit()`);
    await until(()=>heldReply,'engineering earlier clear reply');await field('locator','EM18IG');releaseReply();
    await until(()=>cdp.evaluate(`!busy`),'engineering clear late acknowledgement');
    assert.match(await cdp.evaluate(`document.getElementById('progress-error-settings-locator').textContent`),/cleared/i);
    assert.equal(await cdp.evaluate(`savedProgress.data.fields.locator`),null);
    assert.equal(await cdp.evaluate(`document.getElementById('apply-engineering-station-progress').matches(':disabled')`),true);
    // Complete the saved station explicitly before checking the enabled Apply
    // control's keyboard position; clearing correctly disabled that control.
    await cdp.evaluate(`document.getElementById('engineering-station-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy && savedProgress.data.station_complete && !document.getElementById('apply-engineering-station-progress').matches(':disabled')`),'explicit engineering completion after clear');
    await cdp.evaluate(`WsprryPicoSections.reveal(document.getElementById('save-engineering-station-progress'));document.getElementById('save-engineering-station-progress').focus()`);
    await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
    await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
    assert.equal(await cdp.evaluate(`document.activeElement.id`),'apply-engineering-station-progress');
    console.log(JSON.stringify({browser:(await cdp.send('Browser.getVersion')).product,real_crypto:true,callsign_only:true,blank_qrss:true,mixed_outcomes:true,zero_power:true,explicit_reload:true,keep_draft_readback:true,explicit_application:true,reconstructed_reboot:true,network_only_no_profile_promotion:true,engineering_numeric_overflow:true,keyboard:true,future_reply:true,late_edit:true,late_rejected_and_cleared_outcomes:true,network_only_lost_reply_readback:true,native_power_clear:true,captures_enabled:process.env.PROGRESS_BROWSER_NO_CAPTURE!=='1'}));
} catch(error) {
    console.error(JSON.stringify({requests,driver_stderr:f.stderr,page:cdp?await cdp.evaluate(`({url:location.href,text:document.body?.innerText.slice(0,1800)})`).catch(e=>e.message):null}));throw error;
} finally {
    releaseReply?.();cdp?.ws.close();
    try {await cleanupUiProcesses([chrome],profile,{processGroup});}
    finally {proxy.closeAllConnections();await new Promise(resolve=>proxy.close(resolve));await proxyQueue;await f.stop();}
}
