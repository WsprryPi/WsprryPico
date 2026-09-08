'use strict';
// Opt-in actual Chrome rendering of the shipped operator surface, with local
// deterministic HTTP fixtures. No device, certificate or RF access.
const fs = require('node:fs'), http = require('node:http'), path = require('node:path');
const {spawn} = require('node:child_process');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../src/network/web');
const output = path.resolve(process.argv[2] || 'build/phase11-3-ui');
const state = {job:{state:'empty',output_active:false,owner_id:null,job_id:null},
  standalone:{reboot_required:false,storage_healthy:true,uncertainty_ns:'1000000',clock_state:'synchronized',engine:'pio-dma-gp2'},
  network:{enabled:true,link_status:3,ipv4:'192.0.2.10',configured_hostname:'wsprrypico-'+'a'.repeat(32)+'.local',mdns_state:'active',mdns_reason:''}};
const config = {version:1,enabled:false,station:{callsign:'AA0NT',locator:'EM18',power_dbm:37},
  wifi:{ssid:'Test station',password:null,ntp_ipv4:'192.0.2.1'},schedules:[{period_s:120,phase_s:0}],expires_utc_s:0};
let offline = false, chrome, socket;
const server = http.createServer((req,res) => {
  if (req.url.startsWith('/api/')) {
    res.setHeader('Content-Type','application/json'); res.setHeader('ETag','"one"');
    if (offline) {res.writeHead(503);res.end('{"error":{"code":"capacity"}}');return;}
    res.end(JSON.stringify(req.url.endsWith('status') ? state : req.url.endsWith('config') ? {config} :
      {active_job_connections:true,wtp:{maximum_arm_uncertainty_ns:'1000000'}}));return;
  }
  const name = {'/':'index.html','/style.css':'style.css','/app.js':'app.js'}[req.url];
  if (!name) {res.writeHead(404);res.end();return;}
  res.setHeader('Content-Type',name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':'text/html');
  res.end(fs.readFileSync(path.join(root,name)));
});
const pending = new Map(); let sequence = 0;
function send(method,params={}) {return new Promise((resolve,reject)=>{
  const id=++sequence;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));
});}
async function evaluate(expression) {const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
  if(r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function until(fn) {for(let i=0;i<200;i++){if(await fn())return;await new Promise(r=>setTimeout(r,25));}throw new Error('UI deadline');}
(async()=>{
  fs.mkdirSync(output,{recursive:true});
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const profile=fs.mkdtempSync('/tmp/pico-browser-');
  chrome=spawn(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    ['--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check',
     '--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});
  const portFile=path.join(profile,'DevToolsActivePort');await until(()=>fs.existsSync(portFile));
  const port=fs.readFileSync(portFile,'utf8').split('\n')[0];
  const tabs=await (await fetch('http://127.0.0.1:'+port+'/json')).json();
  socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
  socket.onmessage=e=>{const m=JSON.parse(e.data);if(!pending.has(m.id))return;const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result);};
  await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j;});
  await send('Page.enable');
  for(const [name,width,height] of [['desktop',1280,900],['mobile',390,844]]) {
    offline=false;state.network.mdns_state='active';state.job={state:'empty',output_active:false,owner_id:null,job_id:null};
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:name==='mobile'});
    await send('Page.navigate',{url:'http://127.0.0.1:'+server.address().port+'/'});
    await until(()=>evaluate('typeof online !== "undefined" && online && !busy'));
    await evaluate('document.querySelector("[name=password]").value="unsaved-draft"; document.getElementById("config").dispatchEvent(new Event("input"))');
    state.job={state:'armed',output_active:false,owner_id:await evaluate('session'),job_id:'3'.repeat(32)};
    await evaluate('document.getElementById("refresh").click()');await until(()=>evaluate('!busy'));
    assert.equal(await evaluate('document.getElementById("abort").disabled'),false);
    assert.equal(await evaluate('document.querySelector("[name=password]").value'),'unsaved-draft');
    assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'),true);
    let shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
    fs.writeFileSync(path.join(output,name+'-armed.png'),Buffer.from(shot.data,'base64'));
    state.job={...state.job,state:'running',output_active:true,owner_id:'f'.repeat(32)};
    await evaluate('document.getElementById("refresh").click()');await until(()=>evaluate('!busy'));
    assert.equal(await evaluate('document.getElementById("abort").disabled'),true);
    for(const discoveryState of ['conflict','failed']) {
      state.network.mdns_state=discoveryState;
      await evaluate('document.getElementById("refresh").click()');await until(()=>evaluate('!busy'));
      assert.equal(await evaluate('document.querySelector("[name=password]").value'),'unsaved-draft');
      assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'),true);
      shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
      fs.writeFileSync(path.join(output,name+'-'+discoveryState+'.png'),Buffer.from(shot.data,'base64'));
    }
    offline=true;await evaluate('document.getElementById("refresh").click()');await until(()=>evaluate('!busy'));
    assert.equal(await evaluate('document.getElementById("output").textContent'),'Unknown');
    assert.equal(await evaluate('document.querySelector("[name=password]").value'),'unsaved-draft');
    shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
    fs.writeFileSync(path.join(output,name+'-unavailable.png'),Buffer.from(shot.data,'base64'));
  }
  console.log('Desktop/mobile: armed owner controls, foreign running job, unavailable status, preserved password draft, no overflow passed');
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>{if(socket)socket.close();if(chrome)chrome.kill('SIGTERM');server.close();});
