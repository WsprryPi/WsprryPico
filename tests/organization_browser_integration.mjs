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
import {scanAccessibility} from './ui_review_accessibility.mjs';

if (!globalThis.WebSocket) throw new Error('Use Node with built-in WebSocket; Node 20 needs --experimental-websocket');
if (!process.argv[2]) throw Error('Usage: node tests/organization_browser_integration.mjs CONSUMER_BOOTSTRAP_DRIVER [OUTPUT_DIRECTORY]');
const processGroup=process.platform==='linux';
const noCapture=process.env.PICO_BROWSER_NO_CAPTURE==='1' || process.env.HOSTNAME_BROWSER_NO_CAPTURE==='1';
const output=path.resolve(process.argv[3] || 'build/organization-browser-integration');
await mkdir(output,{recursive:true});
const axeSource=process.env.UI_REVIEW_AXE_PATH ? await readFile(process.env.UI_REVIEW_AXE_PATH,'utf8') : null;
const accessibility=[];
const profile=await mkdtemp(path.join(os.tmpdir(),'p1511-chrome-'));
let f=new Fixture(process.argv[2]);await f.time(1000);
let dropNext=false, dropBootstrap=false, chrome, cdp, cdpB;
const fB=new Fixture(process.argv[2],['2'.repeat(32)]);await fB.time(1000);
const bClient=fB.client();await fB.login(bClient);const bResource=await bClient.request('hostname');const bName=await bResource.json();
await bClient.request('hostname','PUT',{schema:'transmitter-hostname/1',target:bName.target,hostname:'pico-b.local'},bResource.headers.get('etag'));
await fB.command({op:'reboot'});await fB.time(3000); const requests=[];
let proxyQueue=Promise.resolve();
const proxy=http.createServer((req,res)=>{
    proxyQueue=proxyQueue.then(()=>serve(req,res));
});
async function serve(req,res){
    try {
        const u=new URL(req.url.startsWith('http:')?req.url:'http://192.168.1.53'+req.url);
        if(!['192.168.1.53','192.168.4.1','wsprrypico-0a60df.local','pico-a.local','pico-b.local', 'x'.repeat(63)+'.local'].includes(u.hostname)){res.writeHead(403);res.end();return;}
        const chunks=[];for await(const b of req)chunks.push(b);
        if(u.pathname.endsWith('/start'))await f.time(f.now+1000);
        const target=u.hostname==='pico-b.local'?fB:f;
        const response=await target.fetch(u.hostname,u.hostname==='192.168.4.1',u.pathname,
            {method:req.method,body:Buffer.concat(chunks),headers:{'Content-Type':req.headers['content-type']||'application/json'},
                marker:u.pathname.startsWith('/api/owner/')?'Owner':/^\/api\/(bootstrap|recovery)\//.test(u.pathname)?'Bootstrap':'Radio'});
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
        if(dropBootstrap && u.pathname==='/api/bootstrap/v1/submit') { dropBootstrap=false;res.destroy();return; }
        res.writeHead(response.status,Object.fromEntries(response.headers));res.end(bytes);
    }catch(error){res.writeHead(500,{'Content-Type':'text/plain'});res.end(error.message);}
}
await new Promise(resolve=>proxy.listen(0,'127.0.0.1',resolve));
const port=proxy.address().port;
class Cdp {
    constructor(url){this.ws=new WebSocket(url);this.sequence=0;this.pending=new Map();this.ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.method==='Page.javascriptDialogOpening'){void this.send('Page.handleJavaScriptDialog',{accept:true});return;}if(m.id&&this.pending.has(m.id)){const p=this.pending.get(m.id);this.pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result);}};}
    async open(){if(this.ws.readyState===1)return;await new Promise((resolve,reject)=>{this.ws.onopen=resolve;this.ws.onerror=reject;});}
    send(method,params={}){const id=++this.sequence;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{this.pending.delete(id);reject(Error('CDP deadline: '+method));},15000);this.pending.set(id,{resolve:value=>{clearTimeout(timer);resolve(value);},reject:error=>{clearTimeout(timer);reject(error);}});this.ws.send(JSON.stringify({id,method,params}));});}
    async evaluate(expression){const r=await this.send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
}
async function until(fn,label,ms=10000){const end=Date.now()+ms;let last;while(Date.now()<end){try{const r=await fn();if(r)return r;}catch(e){last=e;}await new Promise(r=>setTimeout(r,50));}throw Error('Timed out: '+label+(last?' '+last.message:''));}
async function field(id,value){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});if(${JSON.stringify(id)}==='local-password'&&!document.getElementById('local-access').open)document.getElementById('access-toggle').click();globalThis.WsprryPicoSections?.reveal(e);e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));}`);}
async function click(id){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});globalThis.WsprryPicoSections?.reveal(e);e.click();}`);}
async function capture(name,anchor=null){
    for(const theme of axeSource ? ['light'] : ['light','dark'])for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]){
        await cdp.send('Emulation.setDeviceMetricsOverride',{...view,name:undefined,deviceScaleFactor:1,mobile:view.name==='mobile'});
        await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]});
        if(anchor)await cdp.evaluate(`globalThis.WsprryPicoSections?.reveal(document.getElementById(${JSON.stringify(anchor)}))`);
        await cdp.evaluate(anchor ? `document.getElementById(${JSON.stringify(anchor)}).scrollIntoView({block:'start'})` : 'scrollTo(0,0)');
        assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false,'horizontal overflow');
        if (axeSource) {
          const result=await scanAccessibility(cdp,axeSource);
          accessibility.push({state:name,view:view.name,...result});
          await writeFile(path.join(output,'accessibility.json'),JSON.stringify(accessibility,null,2)+'\n');
          assert.equal(accessibility.at(-1).violations.length,0,'axe violations: '+name+' '+view.name);
          assert.equal(accessibility.at(-1).incomplete.length,0,'axe manual review required: '+name+' '+view.name);
        }
        if(noCapture)continue;
        const image=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
        await writeFile(path.join(output,`${name}-${view.name}-${theme}.png`),Buffer.from(image.data,'base64'));
        if(name==='pico-password-default' && view.name==='desktop' && theme==='light') {
            const clip=await cdp.evaluate('(()=>{const r=document.getElementById("pico-password-form").getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1};})()');
            const detail=await cdp.send('Page.captureScreenshot',{format:'png',clip,captureBeyondViewport:true});
            await writeFile(path.join(output,'pico-password-form.png'),Buffer.from(detail.data,'base64'));
        }
    }
}
try {
    chrome=spawn(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        ['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',
         '--remote-debugging-port=0',`--user-data-dir=${profile}`,`--proxy-server=http://127.0.0.1:${port}`,'--proxy-bypass-list=<-loopback>','about:blank'],{stdio:'ignore',detached:processGroup});
    const debugPort=await until(async()=>Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]),'Chrome startup',60000);
    const page=await until(async()=>(await(await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(p=>p.type==='page'),'page');
    cdp=new Cdp(page.webSocketDebuggerUrl);await cdp.open();await cdp.send('Page.enable');
    // Chromium may expose its initial about:blank target before processing the
    // launch URL. Drive the selected target explicitly on every host.
    // A first-time operator saves only Wi-Fi, then uses the LAN page after a
    // reboot. Exercise the shipped browser scripts with no station/config journal.
    await f.stop();f=new Fixture(process.argv[2],['1'.repeat(32),'--blank']);await f.time(1000);
    await cdp.send('Page.navigate',{url:'http://192.168.4.1/'});
    await until(()=>cdp.evaluate('document.getElementById("submit") && !document.getElementById("submit").disabled'),'first Wi-Fi form');
    await field('ssid','Home Net');await field('password','test-password');await click('submit');
    await until(()=>cdp.evaluate('!document.getElementById("accepted").hidden'),'first Wi-Fi accepted');
    await f.command({op:'bench_network',linked:true,safe:true});
    await f.time(f.now+3000);await f.time(f.now+1000);
    await until(()=>cdp.evaluate('!document.getElementById("connected").hidden'),'Wi-Fi save confirmation');
    assert.equal((await f.command({op:'stats'})).config_sequence,'0');
    await f.command({op:'reboot'});await f.time(7000);
    await cdp.send('Page.navigate',{url:'http://192.168.1.53/'});
    await until(()=>cdp.evaluate('typeof radio!=="undefined" && !!localIdentity && !busy && !document.getElementById("local-login").hidden'),'Wi-Fi-only LAN login');
    await field('local-password','test-password');await cdp.evaluate('document.getElementById("local-login").requestSubmit()');
    await until(()=>cdp.evaluate('typeof online !== "undefined" && online && !busy'),'Wi-Fi-only authenticated controls');
    assert.equal(await cdp.evaluate('document.getElementById("consumer-callsign").value'),'');
    assert.equal(await cdp.evaluate('document.getElementById("consumer-ssid").value'),'Home Net');
    assert.equal((await f.command({op:'stats'})).config_sequence,'0');
    await capture('wifi-only-lan-control','station-area');
    await click('wifi-host-link');
    await until(()=>cdp.evaluate('!!picoPasswordState && !document.getElementById("pico-password-settings").disabled'),'editable Pico password');
    assert.equal(await cdp.evaluate('picoPasswordState.data.wifi_default'),true);
    await capture('pico-password-default','pico-password-form');
    await field('pico-new-password','separate-browser-password');await field('pico-confirm-password','does-not-match');
    await cdp.evaluate('document.getElementById("pico-password-form").requestSubmit()');
    assert.match(await cdp.evaluate('document.getElementById("pico-password-error").textContent'),/do not match/);
    assert.equal(await cdp.evaluate('document.activeElement.id'),'pico-confirm-password');
    await field('pico-confirm-password','separate-browser-password');
    await cdp.evaluate('document.getElementById("pico-password-form").requestSubmit()');
    await until(()=>cdp.evaluate('!localAuthenticated && !busy && document.getElementById("local-status").textContent.includes("Pico password saved")'),'Pico password saved and browser signed out');
    assert.equal(await cdp.evaluate('document.getElementById("pico-new-password").value+document.getElementById("pico-confirm-password").value'),'');
    await f.time(f.now+1000);await field('local-password','separate-browser-password');
    await cdp.evaluate('document.getElementById("local-login").requestSubmit()');
    await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'separate Pico password login');
    assert.equal(await cdp.evaluate('picoPasswordState.data.wifi_default'),false);
    assert.equal(await cdp.evaluate('document.getElementById("consumer-ssid").value'),'Home Net');
    assert.equal((await f.command({op:'stats'})).config_sequence,'0');
    await capture('pico-password-custom','pico-password-form');
    await f.command({op:'reboot'});await f.time(f.now+1000);
    await cdp.send('Page.navigate',{url:'http://192.168.1.53/wifi-host'});
    await until(()=>cdp.evaluate('typeof radio!=="undefined" && !!localIdentity && !busy'),'Pico password persisted across reboot');
    await field('local-password','separate-browser-password');await cdp.evaluate('document.getElementById("local-login").requestSubmit()');
    await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'persisted Pico password authenticated');
    await click('pico-password-default');
    await until(()=>cdp.evaluate('!localAuthenticated && !busy'),'Wi-Fi password restored as default');
    await f.time(f.now+1000);await field('local-password','test-password');await cdp.evaluate('document.getElementById("local-login").requestSubmit()');
    await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'restored default Pico password login');
    assert.equal(await cdp.evaluate('picoPasswordState.data.wifi_default'),true);
    await click('station-link');
    await field('consumer-callsign','K1ABC');await field('consumer-locator','FN42');await field('consumer-power','30');
    await cdp.evaluate('document.getElementById("consumer-station-form").requestSubmit()');
    await until(()=>cdp.evaluate('!busy && savedProgress?.data.station.callsign==="K1ABC"'),'optional station progress after Wi-Fi-only login');
    await click('apply-station-progress');
    await until(()=>cdp.evaluate('!busy && !!consumerAttempt'),'optional station submitted from Wi-Fi-only profile');
    await f.time(f.now+3000);await f.command({op:'activate'});await f.time(f.now+1000);
    assert.equal((await f.command({op:'stats'})).profile_generation,'2');
    await f.command({op:'reboot'});await f.time(f.now+1000);
    await cdp.send('Page.navigate',{url:'http://192.168.1.53/'});
    await until(()=>cdp.evaluate('typeof radio!=="undefined" && !!localIdentity && !busy'),'optional station reboot login');
    await field('local-password','test-password');await cdp.evaluate('document.getElementById("local-login").requestSubmit()');
    await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'optional station authenticated readback');
    assert.equal(await cdp.evaluate('currentConfig.station.callsign'),'K1ABC');
    assert.equal(await cdp.evaluate('currentConfig.wifi.ssid'),'Home Net');
    await capture('optional-station-saved','station-area');
    await cdp.send('Page.navigate',{url:'about:blank'});
    await f.stop();f=new Fixture(process.argv[2]);await f.time(1000);
    await cdp.send('Page.navigate',{url:'http://192.168.1.53/'});
    await until(()=>cdp.evaluate('typeof radio!=="undefined" && !!localIdentity && !busy'),'production control document');
    assert.equal(await cdp.evaluate(`!document.getElementById('station-area').hidden && document.getElementById('wifi-host-area').hidden`),true);
    assert.match(await cdp.evaluate(`document.getElementById('access-toggle').getAttribute('aria-label')`),/Unlock controls/);
    assert.equal(await cdp.evaluate(`document.getElementById('message-settings').disabled`),true,'locked controls cannot submit a message');
    await capture('lan-default');
    await field('local-password','test-password');await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
    await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'login');
    const jumpRequests=requests.length;
    const initialHash=await cdp.evaluate('location.hash');
    for(const id of ['station-identity','radio-settings','message-section']) {
      await cdp.evaluate(`{const section=document.getElementById('${id}');section.open=false;const summary=section.querySelector('summary');summary.scrollIntoView({block:'center'});summary.focus();}`);
      await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r'});
      await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
      await until(()=>cdp.evaluate(`document.getElementById('${id}').open && document.activeElement===document.getElementById('${id}').querySelector('summary')`),'keyboard native section '+id);
    }
    assert.equal(await cdp.evaluate('location.hash'),initialHash,'native disclosures preserve navigation history');assert.equal(requests.length,jumpRequests);
    const messageAX=(await cdp.send('Accessibility.getFullAXTree')).nodes.find(n=>n.role?.value==='textbox' && n.name?.value==='Message');
    assert.ok(messageAX,'message accessible name excludes help prose');
    assert.match(messageAX.description?.value || '',/32-character limit/);
    assert.match(await cdp.evaluate(`document.getElementById('message-preview').textContent`),/Enter a message/);
    assert.equal(await cdp.evaluate(`document.getElementById('message-preview').classList.contains('error')`),false);
    assert.ok(await cdp.evaluate(`document.getElementById('job-heading').getBoundingClientRect().top>=8`),'complete focused outline is visible');
    await capture('message-shortcut','job-heading');
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
    await click('read-saved');await until(()=>cdp.evaluate('!busy && writeState==="review"'),'draft comparison readback');
    await cdp.evaluate(`document.querySelector('#saved-readback-details > summary').click()`);
    assert.match(await cdp.evaluate(`document.getElementById('draft-comparison').textContent`),/PJ4\/AA0NT/);
    assert.equal(await cdp.evaluate(`document.getElementById('draft-comparison').textContent.includes('draft-password')`),false);
    assert.equal(await cdp.evaluate(`document.getElementById('draft-comparison').textContent.includes('Time server')`),false,'sparse omitted matching time server is not a difference');
    await capture('draft-comparison','saved-readback-details');
    await click('review-saved');

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
    if(!noCapture){const zoom=await cdp.send('Page.captureScreenshot',{format:'png'});await writeFile(path.join(output,'organization-zoom.png'),Buffer.from(zoom.data,'base64'));}
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
    await click('refresh');await until(()=>cdp.evaluate('!busy && !localAuthenticated'),'observe retired profile session');
    await field('local-password','test-password');await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
    await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'station save relogin');
    await click('consumer-check-save');await until(()=>cdp.evaluate('!busy && !consumerAttempt'),'explicit station receipt reconciliation');
    const afterStation=await f.command({op:'stats'});
    await click('station-link');await click('wifi-host-link');await click('refresh');await until(()=>cdp.evaluate('!busy'),'post-save area refresh');
    assert.equal((await f.command({op:'stats'})).profile_programs,afterStation.profile_programs,'navigation cannot replay setup');
    assert.equal(await cdp.evaluate('currentConfig.station.callsign'),'K1ABC');
    for(const mode of ['blank']) {
      await cdp.send('Page.navigate',{url:'about:blank'});
      await f.stop();f=new Fixture(process.argv[2]);await f.time(1000);
      await f.command({op:'page_profile',mode});
      await cdp.send('Page.navigate',{url:'http://192.168.4.1/'});
      await until(()=>cdp.evaluate(`!!document.getElementById('wifi-form') && !document.getElementById('credentials').hidden`),'Wi-Fi commissioning '+mode);
      await until(()=>cdp.evaluate(`!document.getElementById('credentials').hidden && document.getElementById('submit').disabled===false`),'usable Wi-Fi commissioning '+mode);
      await capture(mode+'-wifi-first');
      await cdp.send('Page.navigate',{url:'http://192.168.4.1/station'});
      await until(()=>cdp.evaluate(`!!document.getElementById('owner-form') && document.title.includes('Station setup')`),'station commissioning '+mode);
      assert.equal(await cdp.evaluate(`!!document.getElementById('message-form')`),false);
      await until(()=>cdp.evaluate(`!document.getElementById('owner-wifi-first').hidden`),'ready station commissioning '+mode);
      await capture(mode+'-station-setup');
      {
        await cdp.send('Page.navigate',{url:'http://192.168.4.1/'});
        await until(()=>cdp.evaluate(`!document.getElementById('credentials').hidden && !document.getElementById('submit').disabled`),'blank Wi-Fi ready');
        await field('ssid','é');await field('password','setup-password');
        await cdp.evaluate(`document.getElementById('wifi-form').requestSubmit()`);
        await until(()=>cdp.evaluate(`document.getElementById('ssid').getAttribute('aria-invalid')==='true'`),'inline SSID validation');
        assert.equal(await cdp.evaluate('document.activeElement.id'),'ssid');
        await field('ssid','Setup Net');
        assert.equal(await cdp.evaluate(`document.getElementById('ssid').getAttribute('aria-invalid')`),'false');
        await field('time-server','127.0.0.1');await cdp.evaluate(`document.getElementById('wifi-form').requestSubmit()`);
        await until(()=>cdp.evaluate(`document.getElementById('time-server').getAttribute('aria-invalid')==='true'`),'inline time-server validation');
        assert.equal(await cdp.evaluate('document.activeElement.id'),'time-server');
        await capture('wifi-inline-errors');await field('time-server','pool.ntp.org');
        await cdp.evaluate(`document.getElementById('submit').focus()`);
        await cdp.evaluate(`document.getElementById('wifi-form').requestSubmit()`);
        await until(()=>cdp.evaluate(`!document.getElementById('accepted').hidden`),'Wi-Fi accepted without claiming saved');
        assert.equal(await cdp.evaluate('document.activeElement.id'),'page-title','Wi-Fi transition moves focus out of hidden form');
        await capture('wifi-accepted');
        await f.time(f.now+3000);await f.time(f.now+45000);
        await until(()=>cdp.evaluate(`!document.getElementById('retry').hidden`),'failed association remains unsaved');
        assert.equal((await f.command({op:'stats'})).profile_generation,'0');
        await capture('wifi-association-failed');
        await click('retry-button');await field('ssid','Setup Net');await field('password','setup-password');
        const submissions=requests.filter(r=>r.path==='/api/bootstrap/v1/submit').length;
        dropBootstrap=true;await cdp.evaluate(`document.getElementById('wifi-form').requestSubmit()`);
        await until(()=>cdp.evaluate(`!document.getElementById('unconfirmed').hidden`),'lost Wi-Fi reply stays unconfirmed');
        await capture('wifi-unconfirmed');
        assert.equal(requests.filter(r=>r.path==='/api/bootstrap/v1/submit').length,submissions+1,'no automatic Wi-Fi replay');
        await f.command({op:'bench_network',linked:true,safe:true});await f.time(f.now+3000);await f.time(f.now+1000);
        await until(()=>cdp.evaluate(`!document.getElementById('connected').hidden`),'confirmed first Wi-Fi save');
        await capture('wifi-confirmed-next-connection');
      }
    }
    console.log('Recovery boundary: leave provisioning');await cdp.send('Page.navigate',{url:'about:blank'});await f.stop();console.log('Recovery boundary: new fixture');f=new Fixture(process.argv[2]);await f.time(1000);
    await f.command({op:'page_profile',mode:'recovery'});console.log('Recovery boundary: profile ready');
    await cdp.send('Page.navigate',{url:'http://192.168.4.1/recovery.html'});
    await until(()=>cdp.evaluate(`!!document.getElementById('provisioning') && !document.getElementById('provisioning').disabled`),'admitted recovery page');
    await click('provisioning');
    assert.equal(await cdp.evaluate(`document.activeElement.id`),'operation');
    await field('phrase','wrong phrase');assert.equal(await cdp.evaluate(`document.getElementById('execute').disabled`),true);
    await capture('recovery-confirmation','confirm');
    await click('cancel');assert.equal(await cdp.evaluate(`document.activeElement.id`),'provisioning');
    assert.equal((await f.command({op:'stats'})).recovery_requests,0);
    await click('full');await capture('full-erase-confirmation','confirm');await click('cancel');
    assert.equal(await cdp.evaluate('document.activeElement.id'),'full','cancel returns to selected reset origin');
    await click('provisioning');await click('confirm-one');await click('confirm-two');await field('phrase','reset provisioning');
    assert.equal(await cdp.evaluate(`document.getElementById('execute').disabled`),false);
    await cdp.evaluate(`document.getElementById('reset-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`document.getElementById('notice').textContent.includes('Reset accepted')`),'encrypted reset callback admitted');
    assert.equal((await f.command({op:'stats'})).recovery_requests,1);
    await cdp.send('Page.reload');await until(()=>cdp.evaluate(`document.getElementById('notice').textContent.includes('already in progress')`),'pending reset reload');
    assert.equal((await f.command({op:'stats'})).recovery_requests,1,'no destructive replay');
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
    assert.equal(await cdp.evaluate('document.documentElement.lang'),'en');
    await capture('unavailable-recovery');
    await writeFile(path.join(output,'requests.json'),JSON.stringify(requests,null,2)+'\n');
    console.log(JSON.stringify({browser:(await cdp.send('Browser.getVersion')).product,production_routes:true,real_crypto:true,
      wifi_only_lan_after_reboot:true,optional_station_from_wifi_only:true,defaults:true,reciprocal_navigation:true,drafts:true,back_forward_reload:true,no_session_churn:true,no_navigation_mutations:true,station_save_without_message:true,receipt_reconciliation:true,zoom_200:true,section_keyboard_focus:true,accessible_message_name:true,inline_wifi_errors:true,transition_focus:true,recovery_cancel_origin:true}));
} catch(error) {
    console.error(JSON.stringify({requests,driver_stderr:f.stderr,page:cdp?await cdp.evaluate('({url:location.href,text:document.body?.innerText.slice(0,1000)})').catch(e=>e.message):null}));throw error;
} finally {
    cdpB?.ws.close();cdp?.ws.close();
    try {await cleanupUiProcesses([chrome],profile,{processGroup});}
    finally {
        proxy.closeAllConnections();await new Promise(resolve=>proxy.close(resolve));await proxyQueue;
        const stopped=await Promise.allSettled([f.stop(),fB.stop()]);
        const errors=stopped.filter(result=>result.status==='rejected').map(result=>result.reason);
        if(errors.length)throw new AggregateError(errors,'Fixture shutdown failed');
    }
}
