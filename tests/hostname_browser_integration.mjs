// Shipped page/bundle -> real browser -> production HTTP/crypto/commissioning.
// Only TCP/board/time boundaries use the existing deterministic fixture.
import assert from 'node:assert/strict';
import http from 'node:http';
import {writeFile, readFile, mkdir} from 'node:fs/promises';
import path from 'node:path';
import {BrowserHarness,until,fixtureJson} from './browser_harness.mjs';
const h=new BrowserHarness();
const cancellationSensitivity=process.env.HOSTNAME_CANCEL_SENSITIVITY;
let cancellationFaultEntered=false,cancellationAssertion;
try{await h.run(async()=>{
if(cancellationSensitivity!==undefined&&cancellationSensitivity!=='1')throw Error('Unknown hostname sensitivity mode');

if (!globalThis.WebSocket) throw new Error('Use Node with built-in WebSocket; Node 20 needs --experimental-websocket');
if (!process.argv[2]) throw Error('Usage: node tests/hostname_browser_integration.mjs CONSUMER_BOOTSTRAP_DRIVER [OUTPUT_DIRECTORY]');
const noCapture=process.env.PICO_BROWSER_NO_CAPTURE==='1' || process.env.HOSTNAME_BROWSER_NO_CAPTURE==='1';
const output=path.resolve(process.argv[3] || 'build/hostname-browser-integration');
await mkdir(output,{recursive:true});
const profile=await h.profile('p1510-chrome-');
let f=await h.fixture(process.argv[2]);await f.time(1000);await f.command({op:'reboot'});await f.time(1000);
let dropNext=false, blockPresentation=true, failRadioRequests=false, chrome, cdp, cdpB;
let captures=0;
const fB=await h.fixture(process.argv[2],['2'.repeat(32)]);await fB.time(1000);
const bClient=fB.client();await fB.login(bClient);const bResource=await bClient.request('hostname');const bName=await bResource.json();
await bClient.request('hostname','PUT',{schema:'hostname',target:bName.target,hostname:'pico-b.local'},bResource.headers.get('etag'));
await fB.command({op:'reboot'});await fB.time(3000); const requests=[];
let proxyQueue=Promise.resolve();
const proxy=http.createServer((req,res)=>{proxyQueue=proxyQueue.then(()=>serve(req,res));});
async function serve(req,res){
    try {
        const u=new URL(req.url.startsWith('http:')?req.url:'http://192.168.1.53'+req.url);
        if(!['192.168.1.53','192.168.4.1','wsprrypico-0a60df.local','pico-a.local','pico-b.local', 'x'.repeat(63)+'.local'].includes(u.hostname)){res.writeHead(403);res.end();return;}
        if(blockPresentation && u.pathname==='/api/consumer/v1/presentation' || failRadioRequests && (u.pathname==='/api/consumer/v1/request' || u.pathname==='/api/consumer/v1/read/operations')) {
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
        if(u.pathname === "/" && response.status===200 && response.headers.get('content-type')?.startsWith('text/html'))
            await writeFile(path.join(output,"root.html"),bytes);
        if(dropNext && u.pathname.endsWith('/request')) { dropNext=false;res.destroy();return; }
        res.writeHead(response.status,Object.fromEntries(response.headers));res.end(bytes);
    }catch(error){res.writeHead(500,{'Content-Type':'text/plain'});res.end(error.message);}
}
await h.server(proxy,()=>proxyQueue);await h.listen(proxy);
const port=proxy.address().port;

async function field(id,value){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});if(${JSON.stringify(id)}==='local-password'&&!document.getElementById('local-access').open)document.getElementById('access-toggle').click();globalThis.WsprryPicoSections?.reveal(e);e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));}`);}
// Submit once the production form admits it; discovery/polling can briefly disable login.
async function submitLogin(){await until(()=>cdp.evaluate(`typeof busy!=="undefined" && !busy && !document.getElementById('login-submit').disabled && (document.getElementById('local-login').requestSubmit(),true)`),'login form available');}
async function click(id){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});globalThis.WsprryPicoSections?.reveal(e);e.click();}`);}
async function capture(name,target){
    if(process.env.HOSTNAME_BROWSER_CAPTURE_PREFIX && !name.startsWith(process.env.HOSTNAME_BROWSER_CAPTURE_PREFIX))return;
    for(const theme of ['light','dark'])for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]){
        await cdp.send('Emulation.setDeviceMetricsOverride',{...view,name:undefined,deviceScaleFactor:1,mobile:view.name==='mobile'});
        await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]});
        await cdp.evaluate(target?`document.getElementById(${JSON.stringify(target)}).scrollIntoView({block:'start'})`:'scrollTo(0,0)');
        assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false,'horizontal overflow');
        if(noCapture)continue;
        const image=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
        ++captures;await writeFile(path.join(output,`${name}-${view.name}-${theme}.png`),Buffer.from(image.data,'base64'));
    }
}
try {
    const started=await h.chrome(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',
            '--remote-debugging-port=0',`--user-data-dir=${profile}`,`--proxy-server=http://127.0.0.1:${port}`,'--proxy-bypass-list=<-loopback>','about:blank'],profile);chrome=started.browser.process;
    const debugPort=new URL(started.pages[0].webSocketDebuggerUrl).port;
    cdp=await h.connect(started.pages[0].webSocketDebuggerUrl,{dialogs:true});await cdp.send('Page.enable');
    await cdp.send('Page.navigate',{url:'http://192.168.1.53/'});
    await until(()=>cdp.evaluate(`typeof radio !== 'undefined' && !!document.getElementById('local-password')`),'shipped radio page');

    async function login() {
        await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy && !!localIdentity'),'identity read complete before login');
        await field('local-password','test-password');
        await submitLogin();
        await until(()=>cdp.evaluate(`localAuthenticated && !busy && online`),'login and hostname readback');
    }
    await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy && !!localIdentity'),'unknown metadata state');
    // Detailed public readback can confirm the active name even when the optional
    // lightweight presentation endpoint is unavailable.
    assert.equal(await cdp.evaluate(`document.getElementById('device-name').textContent`),'wsprrypico-0a60df.local');
    assert.equal(await cdp.evaluate(`document.getElementById('device-id').textContent`),'1'.repeat(32));
    assert.equal(await cdp.evaluate(`document.querySelectorAll('h1').length`),1);
    await capture('unknown-name');
    blockPresentation=false;
    await cdp.evaluate('globalThis.hostnameReloadMarker=true');
    await cdp.send('Page.reload');
    await until(()=>cdp.evaluate(`!globalThis.hostnameReloadMarker && typeof busy!=='undefined' && !busy && document.getElementById('device-name').textContent==='wsprrypico-0a60df.local'`),'IP initial hostname readback');
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
    await field('local-password','wrong-password');await submitLogin();
    await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy'),'rejected login');
    assert.equal(await cdp.evaluate('localAuthenticated'),false);await identity('wsprrypico-0a60df.local');
    assert.match(await cdp.evaluate(`document.getElementById('notice').textContent`),/failed|rejected|password|authentication/);
    await capture('rejected-login');
    await login();
    await identity('wsprrypico-0a60df.local');await capture('authenticated-wifi-diagnostics');
    await click('station-link');await capture('authenticated-station-diagnostics');
    // Shipped console observes genuine accepted jobs through encrypted HTTP.
    assert.equal(await cdp.evaluate(`document.getElementById('console-state').textContent`),'Schedules disabled');
    const other=f.client();await f.time(f.now+1000);await f.login(other);let operationSequence=0;
    const scheduleRead=await other.request('message-schedule'),schedule=await scheduleRead.json();
    const scheduleNow=await (await other.request('operations')).json();
    const recurring={enabled:true,first_start_utc_ns:(BigInt(scheduleNow.standalone.utc_now_ns)+600000000000n).toString(),period_s:1200,expires_utc_s:0,
        message:{mode:'qrss',message:'CQ AA0NT',frequency_nhz:'135500000000000',space_frequency_nhz:'0',
            timing:{dot_ns:'1000000000',dash_ns:'3000000000',intra_gap_ns:'1000000000',character_gap_ns:'3000000000',word_gap_ns:'7000000000'},
            repeat_count:1,repeat_gap_ns:'0',allow_frequency_adjustment:true}};
    const scheduled=await other.request('message-schedule','PUT',{schema:schedule.schema,target:schedule.target,schedule:recurring},scheduleRead.headers.get('etag'));
    assert.equal(scheduled.status,200);
    await click('refresh');await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy'),'enabled recurrence');
    assert.equal(await cdp.evaluate(`document.getElementById('console-next').textContent`),'QRSS: CQ AA0NT');
    assert.equal(await cdp.evaluate(`document.getElementById('console-next-item').hidden`),false);
    await capture('operations-next-message','operations-console');
    const paused=await other.request('message-schedule/pause','POST',{schema:schedule.schema,target:schedule.target,pause:true},scheduled.headers.get('etag'));
    assert.equal(paused.status,200);
    await click('refresh');await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy'),'paused recurrence');
    assert.equal(await cdp.evaluate(`document.getElementById('console-next-item').hidden`),true);
    assert.equal(await cdp.evaluate(`document.getElementById('console-next').textContent`),'');
    const logicalOwner='8'.repeat(32);
    async function radioJob(operation,body={}) {
        const response=await other.request('jobs','POST',{session_id:logicalOwner,request_id:(++operationSequence).toString(16).padStart(32,'0'),operation,body});
        assert.equal(response.status,200,operation);return response.json();
    }
    await radioJob('HELLO',{versions:['WTP/1'],client_name:'console fixture',client_version:'1'});
    await field('message-text','PRESERVE LOCAL DRAFT');
    for(const mode of ['qrss','fskcw','dfcw','tone','cw','wspr']) {
        await radioJob('CLAIM',{owner_id:logicalOwner,lease_ms:60000});
        const jobId=(100+operationSequence).toString(16).padStart(32,'0');
        if(['tone','cw','wspr'].includes(mode)) await radioJob('LOAD',{job_id:jobId,profile:'rf-events/1',mode,total_duration_ns:'10000000000',allow_frequency_adjustment:false,events:[{offset_ns:'0',duration_ns:'10000000000',rf_on:true,frequency_nhz:'135500000000000'}]});
        else await radioJob('LOAD_MESSAGE',{job_id:jobId,mode,message:'TE',frequency_nhz:mode==='dfcw'?'135505000000000':'135500000000000',space_frequency_nhz:mode==='qrss'?'0':mode==='dfcw'?'135500000000000':'135495000000000',timing:{dot_ns:'3000000000',dash_ns:'9000000000',intra_gap_ns:'1000000000',character_gap_ns:'3000000000',word_gap_ns:'7000000000'},repeat_count:1,repeat_gap_ns:'0',allow_frequency_adjustment:true});
        const before=await (await other.request('operations')).json();
        const start=(BigInt(before.standalone.utc_now_ns)+2000000000n).toString();
        await radioJob('ARM',{job_id:jobId,start_utc_ns:start,max_start_uncertainty_ns:'1000'});
        await click('refresh');await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy'),'armed operations');
        assert.equal(await cdp.evaluate(`document.getElementById('console-state').textContent`),'Job armed');
        assert.equal(await cdp.evaluate(`document.getElementById('restart').disabled`),true);
        await f.command({op:'schedule_tick',delta_ns:'2000000000'});
        await click('refresh');await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy'),'running operations');
        assert.equal(await cdp.evaluate(`document.getElementById('console-state').textContent`),'Job running');
        assert.equal(await cdp.evaluate(`document.getElementById('console-frequency').textContent`),mode==='fskcw'?'135.495/135.500 kHz':mode==='dfcw'?'135.505/135.500 kHz':mode==='wspr'?'Unavailable':'135.5 kHz');
        assert.equal(await cdp.evaluate(`document.getElementById('console-frequency-label').textContent`),({qrss:'Carrier',fskcw:'Space/Mark',dfcw:'Dot/Dash',wspr:'Dial frequency'}[mode]||'Frequency'));
        assert.equal(await cdp.evaluate(`document.getElementById('console-message').textContent`),mode==='wspr'?'Encoded WSPR frame':mode==='cw'?'Text unavailable':mode==='tone'?'—':'TE');
        assert.equal(await cdp.evaluate(`document.getElementById('owner').textContent`),'Other controller');
        assert.match(await cdp.evaluate(`document.getElementById('console-progress').textContent`),/^Running · ~\d+%$/);
        assert.equal(await cdp.evaluate(`document.getElementById('hostname')`),null);
        for(const width of [1280,390]) {
            await cdp.send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<600});
            const typography=await cdp.evaluate(`Array.from(document.querySelectorAll('#transmitter-status dd')).map(e=>{const s=getComputedStyle(e);return [s.fontFamily,s.fontSize,s.fontWeight,s.lineHeight].join('|')})`);
            assert.equal(new Set(typography).size,1,`${mode} compact accepted-job and device-state values share typography at ${width}px`);
            assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false,`${mode} status wraps at ${width}px`);
        }
        if(mode==='dfcw') await capture('operations-running-dfcw','operations-console');
        assert.equal(await cdp.evaluate(`document.getElementById('message-text').value`),'PRESERVE LOCAL DRAFT');
        await radioJob('ABORT',{job_id:jobId});await radioJob('RELEASE');
    }
    await other.logout();await click('refresh');await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy'),'operations released');
    await capture('operations-idle','operations-console');
    await cdp.evaluate('document.getElementById("message-section").open=true');
    await cdp.evaluate(`document.getElementById('message-text').focus()`);
    const picoUtc=await cdp.evaluate('snapshot.standalone.utc_now_ns');
    for(const timezoneId of ['Asia/Tokyo','America/New_York','UTC']) {
        await cdp.send('Emulation.setTimezoneOverride',{timezoneId});await cdp.evaluate('consoleTick()');
        assert.equal(await cdp.evaluate('Intl.DateTimeFormat().resolvedOptions().timeZone'),timezoneId);
        assert.equal(await cdp.evaluate('snapshot.standalone.utc_now_ns'),picoUtc,'local timezone cannot change device time used for scheduling');
        assert.equal(await cdp.evaluate(`document.activeElement.id`),'message-text','clock ticks retain focus');
    }
    await cdp.send('Emulation.setTimezoneOverride',{timezoneId:'America/Chicago'});

    await click('wifi-host-link');
    await cdp.evaluate('document.getElementById("hostname-section").open=true');
    assert.equal(await cdp.evaluate('hostnameState.saved'),'wsprrypico-0a60df.local');
    await field('hostname-input','K.local');
    await cdp.evaluate(`document.getElementById('hostname-form').dispatchEvent(new Event('submit',{cancelable:true}))`);
    await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy'),'invalid hostname');
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
    await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy && !localAuthenticated'),'profile save logs in again');
    assert.equal(await cdp.evaluate(`document.getElementById('message-text').value`),'KEEP DRAFT');
    assert.equal((await f.command({op:'stats'})).profile_generation,'2');
    await login();
    assert.equal(await cdp.evaluate('hostnameState.saved'),'pico-a.local');
    assert.equal(await cdp.evaluate(`document.getElementById('device-name').textContent`),'wsprrypico-0a60df.local');
    assert.equal(await cdp.evaluate('document.title'),'wsprrypico-0a60df.local - Station control (rename pending)');
    assert.equal(await cdp.evaluate(`document.getElementById('hostname-save').disabled`),true);
    await click('hostname-review');
    await identity('wsprrypico-0a60df.local');
    assert.match(await cdp.evaluate(`document.getElementById('device-name-state').textContent`),/Saved for restart: pico-a.local/);
    await capture('saved-rename-pending');
    await cdp.evaluate(`document.getElementById('message-section').open=true`);
    // Capture the actual first countdown callback while monitorRestart enters
    // synchronously. Restore the global scheduler before any unrelated task runs.
    await cdp.evaluate(`globalThis.reconnectBoundary={};const originalMonitor=monitorRestart;monitorRestart=(...args)=>{const nativeTimer=globalThis.setTimeout;globalThis.setTimeout=(callback,delay,...values)=>{if(delay!==1000)throw Error('Unexpected reconnect timer boundary');if(reconnectBoundary.callback)throw Error('Duplicate initial reconnect timer');Object.assign(reconnectBoundary,{callback,values,delay,called:0});return 0;};try{const task=originalMonitor(...args);reconnectBoundary.task=task;reconnectBoundary.epoch=reconnectEpoch;return task;}finally{globalThis.setTimeout=nativeTimer;monitorRestart=originalMonitor;}};`);
    await click('restart');await until(()=>cdp.evaluate('reconnectRunning && !busy && typeof reconnectBoundary.callback==="function"'),'actual reconnect callback held');
    await capture('restart-countdown');
    await click('restart-cancel');
    const attempts=(await f.command({op:'stats'})).api_restarts;
    if(cancellationSensitivity){
      await cdp.evaluate('reconnectEpoch=reconnectBoundary.epoch;reconnectRunning=true');
      cancellationFaultEntered=true;
    }
    const cancellation=await cdp.evaluate(`(async()=>{const nativeTimer=globalThis.setTimeout;let next;const scheduled=new Promise(resolve=>next=resolve);globalThis.setTimeout=(callback,delay,...values)=>{if(delay===1000){reconnectBoundary.next={callback,values};next({finished:false});return 0;}return nativeTimer(callback,delay,...values);};try{reconnectBoundary.called++;reconnectBoundary.callback(...reconnectBoundary.values);return {...await Promise.race([reconnectBoundary.task.then(()=>({finished:true})),scheduled]),called:reconnectBoundary.called,delay:reconnectBoundary.delay};}finally{globalThis.setTimeout=nativeTimer;}})()`);
    assert.equal(cancellation.called,1,'actual scheduled callback executed exactly once');
    assert.equal(cancellation.delay,1000,'observed product countdown boundary');
    try{assert.equal(cancellation.finished,true,'cancelled reconnect must finish after its actual scheduled callback');}
    catch(error){cancellationAssertion=error;throw error;}
    assert.equal(await cdp.evaluate('reconnectRunning'),false);
    assert.equal((await f.command({op:'stats'})).api_restarts,attempts);
    const previousBoot=await cdp.evaluate('localIdentity.boot_id');
    await f.command({op:'reboot'});await f.time(5000);
    await click('refresh');await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy && !localAuthenticated'),'old-boot session withdrawn before unlock');
    assert.equal(await cdp.evaluate('radio.authenticated'),false,'public reboot observation retires old keys');
    assert.notEqual(await cdp.evaluate('localIdentity.boot_id'),previousBoot,'new boot observed before explicit login');
    assert.equal(await cdp.evaluate(`document.getElementById('local-login').hidden`),false);
    assert.equal(await cdp.evaluate(`document.getElementById('message-text').value`),'KEEP DRAFT');
    await login();
    assert.equal(await cdp.evaluate('document.title'),'pico-a.local - Station control');
    assert.equal(await cdp.evaluate(`document.getElementById('device-name').textContent`),'pico-a.local');
    assert.match(await cdp.evaluate(`document.getElementById('restart-status').textContent`),/Same Pico and new boot confirmed/);
    assert.equal(await cdp.evaluate(`document.getElementById('message-text').value`),'KEEP DRAFT');
    assert.equal((await f.command({op:'stats'})).config_sequence,before.config_sequence);
    assert.equal(await cdp.evaluate(`document.getElementById('message-section').open`),true,'same-tab reset retains expanded controls; only hostname-return links collapse them');
    await identity('pico-a.local');await capture('verified-new-boot');
    // New origin carries only expected nonsecret context and needs a fresh password.
    const boot=await cdp.evaluate('hostnameState.target.boot_id');
    const receipt='#'+new URLSearchParams({'hostname-return':JSON.stringify({device:'1'.repeat(32),boot:'f'.repeat(32),name:'pico-a.local'})});
    await cdp.send('Page.navigate',{url:'http://pico-a.local/'+receipt});
    await until(()=>cdp.evaluate('typeof localIdentity!=="undefined" && !!localIdentity'),'hostname origin');
    assert.equal(await cdp.evaluate('localAuthenticated'),false);
    assert.equal(await cdp.evaluate(`!document.getElementById('station-area').hidden && document.getElementById('wifi-host-area').hidden`),true,'hostname arrival selects Station Control before sign-in');
    // Stale History/expanded disclosures cannot override the validated return.
    await cdp.evaluate(`history.replaceState({retained:'keep',wsprrypicoPresentation:{section:'hostname-section',area:'wifi-host'}},'',location.href);document.querySelectorAll('[data-operator-section],details details').forEach(e=>e.open=true);scrollTo(0,500);dispatchEvent(new PopStateEvent('popstate'));`);
    assert.equal(await cdp.evaluate(`!document.getElementById('station-area').hidden && ![...document.querySelectorAll('[data-operator-section],details details')].some(e=>e.open) && scrollY===0`),true,'return overrides stale WiFi History and closes nested controls');
    await login();assert.equal(await cdp.evaluate('document.title'),'pico-a.local - Station control');
    await until(()=>cdp.evaluate(`returnReceipt===null && !busy && !document.getElementById('station-area').hidden && ![...document.querySelectorAll('[data-operator-section],details details')].some(e=>e.open) && scrollY===0`),'verified hostname return stays collapsed at Station Control top');
    assert.equal(await cdp.evaluate('history.state.retained'),'keep','return preserves unrelated History data');
    assert.equal(await cdp.evaluate('location.pathname'),'/station');
    assert.equal(await cdp.evaluate('location.hash'),'','verified return removes only its receipt');

    // Lost reply after a committed rename never resubmits; fresh login/read/review recovers.
    await field('hostname-input','wsprrypico-0a60df.local');dropNext=true;
    await cdp.evaluate(`document.getElementById('hostname-form').requestSubmit()`);
    await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy && !radio.authenticated'),'lost save reply');
    assert.equal((await f.command({op:'stats'})).profile_generation,'3');
    assert.match(await cdp.evaluate('document.title'),/last confirmed|connection unknown/);
    await login();assert.equal(await cdp.evaluate('hostnameState.saved'),'wsprrypico-0a60df.local');
    assert.equal(await cdp.evaluate(`document.getElementById('hostname-save').disabled`),true);
    await click('hostname-review');
    assert.equal(await cdp.evaluate(`document.getElementById('hostname-save').disabled`),false);

    // Two device-bound production fixtures in separate real browser tabs.
    const tabB=await cdp.send('Target.createTarget',{url:'http://pico-b.local/'});
    const infoB=await until(async()=>(await fixtureJson(`http://127.0.0.1:${debugPort}/json`)).find(p=>p.id===tabB.targetId),'second Pico tab');
    cdpB=await h.connect(infoB.webSocketDebuggerUrl,{dialogs:true});
    await until(()=>cdpB.evaluate('document.title==="pico-b.local - Station control"'),'second Pico title');
    assert.match(await cdp.evaluate('document.title'),/^pico-a.local - Station control/);
    await cdp.send('Emulation.setDeviceMetricsOverride',{width:640,height:450,deviceScaleFactor:1,mobile:false});
    await cdp.evaluate(`document.body.style.zoom='2';document.getElementById('hostname-form').scrollIntoView()`);
    assert.equal(await cdp.evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'200% zoom no overflow');
    if(!noCapture) { ++captures;const zoom=await cdp.send('Page.captureScreenshot',{format:'png'});
    await writeFile(path.join(output,'zoom-200-percent.png'),Buffer.from(zoom.data,'base64')); }
    await cdp.evaluate(`document.body.style.zoom=''`);
    assert.equal(await cdpB.evaluate(`document.getElementById('device-id').textContent`),'2'.repeat(32));
    assert.equal(await cdpB.evaluate(`document.getElementById('device-name').textContent`),'pico-b.local');
    // A receipt for a different full device refuses login before sending credentials.
    const wrong='#'+new URLSearchParams({'hostname-return':JSON.stringify({device:'2'.repeat(32),boot,name:'pico-a.local'})});
    await cdp.send('Page.navigate',{url:'http://pico-a.local/'+wrong});
    await until(()=>cdp.evaluate(`document.getElementById('notice')?.textContent.includes('different Pico')`),'wrong return identity');
    const starts=requests.filter(r=>r.path.endsWith('/start')).length;
    await field('local-password','test-password');await submitLogin();
    await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy'),'wrong-device explicit login refused');
    assert.equal(requests.filter(r=>r.path.endsWith('/start')).length,starts);
    assert.equal((await f.command({op:'stats'})).profile_generation,'3');
    // Maximum name comes from a real persisted profile/new boot, never a DOM injection.
    await cdp.send('Page.navigate',{url:'http://192.168.1.53/'});
    await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy && !!localIdentity'),'return by IP');await login();
    await click('wifi-host-link');await click('hostname-review');
    const longName='x'.repeat(63)+'.local';await field('hostname-input',longName);
    await cdp.evaluate(`document.getElementById('hostname-form').requestSubmit()`);
    await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy && !localAuthenticated'),'long name saved');
    await f.command({op:'reboot'});await f.time(f.now+3000);
    await cdp.send('Page.navigate',{url:'http://'+longName+'/'});
    await until(()=>cdp.evaluate(`typeof busy!=="undefined" && !busy && document.getElementById('device-name').textContent===${JSON.stringify(longName)}`),'long name applied');
    await identity(longName);await cdp.evaluate(`document.getElementById('device-diagnostics').open=true`);
    await capture('maximum-active-hostname');await login();
    await cdp.send('Emulation.setDeviceMetricsOverride',{width:640,height:450,deviceScaleFactor:1,mobile:false});
    await cdp.evaluate(`document.body.style.zoom='2';scrollTo(0,0)`);
    assert.equal(await cdp.evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'long identity at 200% zoom');
    if(!noCapture && !process.env.HOSTNAME_BROWSER_CAPTURE_PREFIX) {++captures;const zoom=await cdp.send('Page.captureScreenshot',{format:'png'});await writeFile(path.join(output,'long-name-zoom-200.png'),Buffer.from(zoom.data,'base64'));}
    await cdp.evaluate(`document.body.style.zoom=''`);
    const idleLimit=await cdp.evaluate('(async()=> (await api("management")).data.limits.idle_ms)()');
    // Only the server's fixture clock advances here. Discover its expiry with
    // an explicit authenticated read; public polling must not renew the login.
    await f.time(f.now+idleLimit+1);await cdp.evaluate('void action(()=>api("management"))');
    await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy && !localAuthenticated && !radio.authenticated'),'session expiry');
    assert.match(await cdp.evaluate(`document.getElementById('local-status').textContent`),/locked|expired|unconfirmed/i);
    assert.match(await cdp.evaluate(`document.getElementById('device-name-state').textContent`),/Last confirmed/);
    await capture('session-expired');await login();
    failRadioRequests=true;await click('refresh');await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy && !online'),'connection failure');
    assert.match(await cdp.evaluate(`document.getElementById('device-name-state').textContent`),/Last confirmed/);
    assert.equal(await cdp.evaluate('radio.authenticated'),true,'public observation failure does not retire a valid login');
    assert.match(await cdp.evaluate('document.title'),/last confirmed/);await capture('disconnected-last-confirmed');
    // Start at the actual blank captive portal, save Wi-Fi, and rename while
    // the station/configuration journal is still absent.
    failRadioRequests=false;
    await cdp.send('Page.navigate',{url:'about:blank'});
    await f.stop();f=await h.fixture(process.argv[2],['1'.repeat(32),'--blank']);await f.time(1000);
    await cdp.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
    await cdp.send('Page.navigate',{url:'http://192.168.4.1/'});
    await until(()=>cdp.evaluate('!!document.getElementById("submit") && !document.getElementById("submit").disabled'),'blank captive Wi-Fi form');
    await capture('captive-blank-setup');
    await field('ssid','Home Net');await field('password','test-password');await click('submit');
    await until(()=>cdp.evaluate('!document.getElementById("accepted").hidden'),'initial Wi-Fi accepted');
    await f.command({op:'bench_network',linked:true,safe:true});await f.time(f.now+3000);await f.time(f.now+1000);
    await until(()=>cdp.evaluate('!document.getElementById("connected").hidden'),'initial Wi-Fi committed');
    await f.command({op:'reboot'});await f.time(f.now+1000);
    await cdp.send('Page.navigate',{url:'http://192.168.4.1/'});
    await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy && !!hostnameState'),'initial captive hostname readback');
    assert.equal(await cdp.evaluate('location.pathname'),'/wifi-host');
    assert.ok((await readFile(path.join(output,'root.html'))).length>0,'captive redirect preserves the retained HTML audit snapshot');
    assert.equal(await cdp.evaluate('hostnameState.source'),'network_profile');
    assert.equal(await cdp.evaluate('hostnameState.writable'),true);
    assert.equal((await f.command({op:'stats'})).config_sequence,'0','station setup is not a rename prerequisite');
    const readyClick=async id=>until(()=>cdp.evaluate(`!busy && !submissions.pending && !accessClosing && !accessLoginPending && !document.getElementById(${JSON.stringify(id)}).matches(':disabled') && (document.getElementById(${JSON.stringify(id)}).click(),true)`),'captive action available: '+id);
    await login();await field('hostname-input','-bad.local');
    const initialPrograms=(await f.command({op:'stats'})).profile_programs;
    await cdp.evaluate('document.getElementById("hostname-input").focus()');await readyClick('hostname-save');
    await until(()=>cdp.evaluate('!busy && document.getElementById("hostname-input").getAttribute("aria-invalid")==="true"'),'inline hostname validation');
    assert.equal((await f.command({op:'stats'})).profile_programs,initialPrograms,'invalid name makes no write');
    await capture('captive-hostname-invalid','hostname-section');
    await field('hostname-input','PICO-A.LOCAL.');await readyClick('hostname-save');
    await until(()=>cdp.evaluate('!busy && !localAuthenticated'),'initial hostname saved');
    assert.equal((await f.command({op:'stats'})).api_restarts,0,'saving does not restart the Pico');
    assert.equal((await f.command({op:'stats'})).config_sequence,'0','saving does not configure a station');
    await login();
    assert.equal(await cdp.evaluate('hostnameState.saved'),'pico-a.local');
    assert.equal(await cdp.evaluate('hostnameState.active'),'wsprrypico-0a60df.local');
    assert.equal(await cdp.evaluate('hostnameState.pending_restart'),true);
    await capture('captive-hostname-pending','hostname-section');
    console.log('PASS captive hostname saved before station setup; old boot remains active');
    await readyClick('restart');
    await until(async()=> (await f.command({op:'stats'})).api_restarts===1,'explicit initial-setup restart');
    await f.command({op:'reboot'});await f.time(f.now+1000);
    await cdp.send('Page.bringToFront');
    await cdp.evaluate('globalThis.item25ReloadMarker=true');
    await cdp.send('Page.reload');
    await until(()=>cdp.evaluate('!globalThis.item25ReloadMarker && typeof busy!=="undefined" && !busy && !!hostnameState'),'new captive document after reboot');
    await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy && hostnameState?.active==="pico-a.local"'),'AP address survives hostname activation');
    await login();await cdp.evaluate('WsprryPicoSections.reveal(document.getElementById("hostname-section"))');await capture('captive-hostname-active','hostname-section');
    await readyClick('hostname-default');await readyClick('hostname-save');
    await until(()=>cdp.evaluate('!busy && !localAuthenticated'),'initial hostname default restored');
    await login();await click('hostname-review');
    assert.equal(await cdp.evaluate('hostnameState.saved'),'wsprrypico-0a60df.local');
    await field('hostname-input','pico-b.local');await readyClick('hostname-save');
    await until(()=>cdp.evaluate('!busy && !localAuthenticated'),'initial hostname selected again');
    await login();
    // A pending rename retains the existing station/Wi-Fi restart guard.
    assert.equal(await cdp.evaluate('document.getElementById("consumer-station-settings").matches(":disabled")'),true);
    await readyClick('restart');await until(async()=> (await f.command({op:'stats'})).api_restarts===1,'explicit second hostname restart');
    await f.command({op:'reboot'});await f.time(f.now+1000);
    await cdp.send('Page.bringToFront');await cdp.evaluate('globalThis.item25ReloadMarker=true');await cdp.send('Page.reload');
    await until(()=>cdp.evaluate('!globalThis.item25ReloadMarker && typeof busy!=="undefined" && !busy && hostnameState?.active==="pico-b.local"'),'second hostname active before station setup');
    await login();
    // Station application is a separate explicit transaction and preserves
    // the selected and active name without enabling schedules.
    await field('consumer-callsign','K1ABC');await field('consumer-locator','FN42');await field('consumer-power','30');
    await readyClick('save-station-progress');
    await until(()=>cdp.evaluate('!busy && savedProgress?.data.station.callsign==="K1ABC"'),'initial station progress');
    await readyClick('apply-station-progress');
    await until(()=>cdp.evaluate('!busy'),'initial station application settled');
    assert.equal(await cdp.evaluate('!!consumerAttempt'),true,
      'station application result: '+await cdp.evaluate('JSON.stringify({writeState,currentConfig,consumerAttempt,status:document.getElementById("consumer-save-status").textContent,notice:document.getElementById("notice").textContent})'));
    await f.time(f.now+3000);await f.command({op:'activate'});await f.time(f.now+1000);
    await f.command({op:'reboot'});await f.time(f.now+1000);
    await cdp.send('Page.bringToFront');
    await cdp.evaluate('globalThis.item25ReloadMarker=true');
    await cdp.send('Page.reload');
    await until(()=>cdp.evaluate('!globalThis.item25ReloadMarker && typeof busy!=="undefined" && !busy && !!hostnameState'),'new captive document after reboot');
    await until(()=>cdp.evaluate('typeof busy!=="undefined" && !busy && !!localIdentity'),'station application reboot');
    await login();
    assert.equal(await cdp.evaluate('hostnameState.saved'),'pico-b.local');
    assert.equal(await cdp.evaluate('hostnameState.active'),'pico-b.local');
    assert.equal(await cdp.evaluate('currentConfig.station.callsign'),'K1ABC');
    assert.equal(await cdp.evaluate('currentConfig.wifi.ssid'),'Home Net');
    assert.equal(await cdp.evaluate('currentConfig.enabled'),false,'hostname and station saves do not enable schedules');
    await cdp.evaluate('WsprryPicoSections.reveal(document.getElementById("hostname-section"))');
    await capture('captive-hostname-station-applied','hostname-section');
    console.log('PASS blank captive Wi-Fi setup, authenticated early hostname editing, explicit restart, defaults and later station preservation');
    console.log(JSON.stringify({identity_heading:true,full_id_diagnostics:true,keyboard_disclosure:true,no_diagnostics_effects:true,public_hostname_without_presentation:true,long_active_name:true,stale_agreement:true,browser:(await cdp.send('Browser.getVersion')).product,served_assets:true,real_crypto:true,
        initial_title:true,hostname_origin:true,canonical_validation:true,generation_save:true,new_boot_readback:true,
        lost_reply_no_replay:true,wrong_device_no_login:true,draft_preserved:true,cancel_countdown:true,screenshots:captures,two_device_tabs:true,zoom_200:true}));
} catch(error) {
    console.error(JSON.stringify({requests:requests.slice(-30),driver_stderr:f.stderr,page:cdp?await cdp.evaluate(`({url:location.href,text:document.body?.innerText.slice(0,600),scripts:[...document.scripts].map(s=>s.src)})`).catch(e=>e.message):null}));
    throw error;
}
});}catch(error){
  if(cancellationSensitivity)console.log(JSON.stringify({kind:'hostname-cancel-sensitivity/1',fault_entered:cancellationFaultEntered,assertion_detected:error===cancellationAssertion,cleanup_completed:error===cancellationAssertion}));
  throw error;
}
