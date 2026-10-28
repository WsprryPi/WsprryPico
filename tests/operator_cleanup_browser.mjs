// Shipped UI -> actual HTTP/parser/crypto/API. Synthetic board; no hardware/RF.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn} from 'node:child_process';
import {Fixture} from './consumer_sessions.test.mjs';
import {cleanupUiProcesses} from './ui_process_cleanup.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const driver=process.argv[2];
if(!driver) throw Error('Usage: node tests/operator_cleanup_browser.mjs DRIVER [SCREENSHOT_DIRECTORY]');
const output=process.argv[3] && path.resolve(process.argv[3]);
if(output) fs.mkdirSync(output,{recursive:true});
const processGroup=process.platform==='linux';
const f=new Fixture(driver),profile=fs.mkdtempSync(path.join(os.tmpdir(),'pico-operator-cleanup-'));
let chrome,ws,serial=0,dropPinReply=false;
const pending=new Map(),errors=[],reads=[];
const server=http.createServer(async(req,res)=>{
  try {
    if(req.url.startsWith('/api/')) {
      const parts=[];for await(const part of req) parts.push(part);
      const before=dropPinReply ? (await f.command({op:'stats'})).config_sequence : null;
      const response=await f.fetch('192.168.1.53',false,req.url,{method:req.method,headers:{'Content-Type':req.headers['content-type']},body:new Uint8Array(Buffer.concat(parts))});
      reads.push({path:req.url,method:req.method,status:response.status});
      if(dropPinReply && before!==(await f.command({op:'stats'})).config_sequence) {dropPinReply=false;res.destroy();return;}
      res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));return;
    }
    let name=req.url.split('?')[0].slice(1);
    if(['','station','wifi-host'].includes(name)) {
      let html=fs.readFileSync(path.join(root,'src/network/web/index.html'),'utf8');
      // The production entry embeds this bundle and supplies the actual carrier context.
      const bundle=fs.readFileSync(path.join(root,'src/network/bootstrap_web/radio-bundle.js'),'utf8');
      html=html.replace('<script src="/config-validation.js"',()=>`<script>${bundle}</script><script>const factory=globalThis.WsprryPicoConsumerRadio;globalThis.WsprryPicoConsumerRadio=Object.freeze({createClient:()=>factory.createClient(undefined,()=>Date.now(),{authority:'192.168.1.53',interface:'station'})});</script><script src="/config-validation.js"`);
      res.setHeader('Content-Type','text/html');res.end(html);return;
    }
    const scripts={'app.js':'app.min.js','organization.js':'organization.min.js','device-presentation.js':'device-presentation.min.js','config-validation.js':'config-validation.min.js'};
    if(name==='style.css' || scripts[name]) {
      res.setHeader('Content-Type',name.endsWith('.css')?'text/css':'text/javascript');
      res.end(fs.readFileSync(path.join(root,'src/network/web',scripts[name]||name)));return;
    }
    res.writeHead(404);res.end();
  } catch(error) {errors.push(error.message);res.writeHead(500);res.end();}
});
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(fn,label) {
  const end=Date.now()+20000;
  while(Date.now()<end) {if(await fn())return;await pause(40);}
  throw Error('Timed out: '+label);
}
function send(method,params={}) {
  return new Promise((resolve,reject)=>{
    const id=++serial,timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP deadline: '+method));},20000);
    pending.set(id,{resolve:value=>{clearTimeout(timer);resolve(value);},reject});ws.send(JSON.stringify({id,method,params}));
  });
}
async function evaluate(expression) {
  const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
  if(result.exceptionDetails) throw Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
  return result.result.value;
}
const click=id=>evaluate(`document.getElementById(${JSON.stringify(id)}).click()`);
const idle=()=>until(()=>evaluate('typeof busy!=="undefined" && !busy'),'request completion');
const config=async()=>{const c=f.client();await c.identity();return (await c.publicRead('config/4')).json();};
async function edit(name,value,pins=false) {
  await evaluate(`document.getElementById('config').elements[${JSON.stringify(name)}].value=${JSON.stringify(value)};document.getElementById('config').elements[${JSON.stringify(name)}].dispatchEvent(new Event('input',{bubbles:true}));${pins?"document.getElementById('config').elements["+JSON.stringify(name)+"].dispatchEvent(new Event('change',{bubbles:true}));":''}`);
}
async function key(key,code=key) {
  const windowsVirtualKeyCode=key==='Escape'?27:key==='Enter'?13:9;
  await send('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode,text:key==='Enter'?'\r':undefined});
  await send('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode});
}
async function capture(state) {
  for(const [width,height] of [[1280,900],[360,800],[390,844]]) for(const area of ['station','wifi-host']) {
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});
    await click(area==='station'?'station-link':'wifi-host-link');
    for(const theme of ['light','dark']) {
      await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]});
      assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,`${width} ${area} ${theme}`);
    }
    // Inspect both layouts in one batched round; this UI deliberately keeps its light palette.
    if(output) {
      await evaluate(`document.querySelectorAll('#${area}-area [data-operator-section]').forEach(e=>e.open=true)`);
      const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
      fs.writeFileSync(path.join(output,`${state}-${area}-${width}.png`),Buffer.from(shot.data,'base64'));
    }
  }
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  if(output && state==='unlocked') {
    await click('station-link');await evaluate('const e=document.getElementById("station-identity");e.open=true;e.scrollIntoView()');
    const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(output,'station-settings.png'),Buffer.from(shot.data,'base64'));
    await evaluate('scrollTo(0,0)');
  }
  await evaluate('document.documentElement.style.zoom="2"');
  assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'200% zoom');
  await evaluate('document.documentElement.style.zoom=""');
}
try {
  await f.time(1000);await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  chrome=spawn(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
    '--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check',
    '--remote-debugging-port=0','--user-data-dir='+profile,...(process.platform==='linux'?['--no-sandbox']:[]),'about:blank'],{stdio:'ignore',detached:processGroup});
  await until(()=>fs.existsSync(path.join(profile,'DevToolsActivePort')),'Chrome startup');
  const [port]=fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n');
  const pages=await(await fetch(`http://127.0.0.1:${port}/json`)).json();ws=new WebSocket(pages.find(page=>page.type==='page').webSocketDebuggerUrl);
  ws.onmessage=event=>{
    const value=JSON.parse(event.data);
    if(value.method==='Page.javascriptDialogOpening') {void send('Page.handleJavaScriptDialog',{accept:true});return;}
    if(value.method==='Runtime.exceptionThrown') errors.push(value.params.exceptionDetails.exception?.description || value.params.exceptionDetails.text);
    const request=pending.get(value.id);if(request){pending.delete(value.id);value.error?request.reject(Error(value.error.message)):request.resolve(value.result);}
  };
  await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});await send('Page.enable');await send('Runtime.enable');
  await send('Page.navigate',{url:`http://127.0.0.1:${server.address().port}/station`});
  await until(()=>evaluate('typeof settingsLoadedBoot!=="undefined" && !!settingsLoadedBoot && !busy'),'public settings loaded');
  assert.equal(await evaluate('online'),true);
  assert.equal(await evaluate('radio.authenticated'),false);
  assert.equal(await evaluate('document.getElementById("config").elements.callsign.value'),'AA0NT');
  assert.equal(await evaluate('document.getElementById("config").elements.ssid.value'),'test-network');
  assert.equal(await evaluate('document.getElementById("config").elements.password.value'),'');
  assert.equal(await evaluate('document.getElementById("logging-status").textContent.includes("Saved:")'),true);
  assert.match(await evaluate('document.getElementById("gpio-drive-status").textContent'),/Saved: 4 mA/);
  assert.doesNotMatch(await evaluate('document.getElementById("gpio-drive-status").textContent'),/Disconnected|target changed/);
  assert.match(await evaluate('document.getElementById("rf-calibration-status").textContent'),/Saved/);
  assert.match(await evaluate('document.getElementById("ntp-timeout-status").textContent'),/Saved/);
  assert.equal(await evaluate('document.getElementById("udp-logging-controls").textContent.includes("Read settings")'),false);
  for(const id of ['station-settings-lock','wifi-settings-lock']) assert.equal(await evaluate(`document.getElementById('${id}').disabled`),true);
  assert.equal(await evaluate('[...document.querySelectorAll(".access-settings input,.access-settings textarea,.access-settings select")].every(e=>e.matches(":disabled"))'),true);
  assert.equal(await evaluate('document.getElementById("station-area").firstElementChild.id'),'transmitter-status');
  assert.equal(await evaluate('[...document.querySelectorAll("#station-area [data-operator-section]")].slice(-2).map(e=>e.id).join(",")'),'saved-settings,device-diagnostics');
  assert.equal(await evaluate('document.getElementById("console-state").hidden'),true);
  assert.equal(await evaluate('document.getElementById("notice").hidden'),true);
  assert.equal(await evaluate('document.getElementById("section-menu")'),null);
  assert.equal(await evaluate('document.getElementById("local-access").open'),false);
  assert.ok(reads.filter(r=>r.path.startsWith('/api/consumer/v1/read')).length>20);
  assert.equal(reads.every(r=>r.method==='GET'),true);
  assert.equal((await f.command({op:'stats'})).config_sequence,'1');
  console.log('PASS locked public settings, detailed status, redaction, layout and no writes');
  for(const area of ['wifi-host','station']) {
    await evaluate('scrollTo(0,document.body.scrollHeight)');await click(area==='station'?'station-link':'wifi-host-link');
    assert.equal(await evaluate('scrollY'),0);
    assert.equal(await evaluate(`document.getElementById('${area==='station'?'station-link':'wifi-host-link'}').getAttribute('aria-current')`),'page');
  }
  await click('access-toggle');assert.equal(await evaluate('document.activeElement.id'),'local-password');
  await key('Escape');assert.equal(await evaluate('document.activeElement.id'),'access-toggle');
  await capture('locked');
  console.log('PASS top navigation, active view, modal keyboard, mobile, color preferences and zoom');
  await click('access-toggle');await evaluate('document.getElementById("local-password").value="test-password"');await key('Enter');
  await until(()=>evaluate('!busy && online && localAuthenticated && writeState==="ready"'),'authenticated settings read');
  await capture('unlocked');
  await click('station-link');await evaluate('document.getElementById("radio-settings").open=true;document.getElementById("radio-pins").open=true');
  const original=(await config()).config;
  await edit('schedules','invalid unsaved WSPR draft');await edit('rf_gp','3',true);await click('save-pins');await idle();
  assert.equal((await config()).config.pins.rf_gp,3);
  assert.deepEqual((await config()).config.schedules,original.schedules);
  assert.equal(await evaluate('document.getElementById("config").elements.schedules.value'),'invalid unsaved WSPR draft');
  await edit('rf_gp','4',true);await edit('schedules','240 / 0');
  await evaluate('document.getElementById("config").dispatchEvent(new Event("submit",{cancelable:true}))');await idle();
  assert.deepEqual((await config()).config.schedules,original.schedules,'saving progress cannot apply schedules');
  assert.equal((await config()).config.pins.rf_gp,3);
  await click('apply-progress');await idle();
  assert.deepEqual((await config()).config.schedules,[{period_s:240,phase_s:0}]);
  assert.equal((await config()).config.pins.rf_gp,3,'WSPR apply cannot apply a pin draft');
  assert.equal(await evaluate('document.getElementById("progress-error-settings-schedules").textContent'),'Saved value applied.');
  assert.equal(await evaluate('document.getElementById("config").elements.rf_gp.value'),'4');
  assert.equal((await config()).config.enabled,false,'no schedules enabled by fixture');
  console.log('PASS independent pin save, WSPR progress save/apply and unrelated draft preservation');
  const before=(await f.command({op:'stats'})).config_sequence;dropPinReply=true;
  await click('save-pins');await until(()=>evaluate('!busy && !radio.authenticated'),'lost committed reply');
  assert.equal(BigInt((await f.command({op:'stats'})).config_sequence),BigInt(before)+1n);
  await evaluate('refresh(true)');
  assert.equal(await evaluate('document.getElementById("config").elements.rf_gp.value'),'4');
  assert.equal(await evaluate('document.getElementById("config").elements.schedules.value'),'240 / 0');
  assert.equal(await evaluate('document.getElementById("save-pins").disabled'),true);
  assert.equal((await config()).config.pins.rf_gp,4);
  assert.deepEqual(errors,[]);
  console.log('PASS lost pin reply commits once, preserves drafts through public refresh, blocks another save');
  console.log(JSON.stringify({browser:(await send('Browser.getVersion')).product,api:'production HTTP/crypto',hardware:false,screenshots:output?12:0}));
} catch(error) {
  console.error(JSON.stringify({errors,reads:reads.slice(-12),state:ws ? await evaluate('({notice:document.getElementById("notice")?.textContent,online:typeof online!=="undefined"?online:null,busy:typeof busy!=="undefined"?busy:null,settings:typeof settingsLoadedBoot!=="undefined"?settingsLoadedBoot:null})').catch(()=>null):null}));
  throw error;
} finally {
  if(ws) {await send('Browser.close').catch(()=>{});ws.close();}
  await new Promise(resolve=>server.close(resolve));await f.stop();
  await cleanupUiProcesses([chrome],profile,{processGroup});
}
