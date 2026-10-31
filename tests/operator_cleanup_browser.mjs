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
const filterOnly=process.argv.includes('--filter-ui-only') || process.env.WSPRRY_PICO_FILTER_UI_ONLY==='1';
if(output) fs.mkdirSync(output,{recursive:true});
const processGroup=process.platform==='linux';
const f=new Fixture(driver),profile=fs.mkdtempSync(path.join(os.tmpdir(),'pico-operator-cleanup-'));
let chrome,ws,serial=0,dropPinReply=false;
let screenshotCount=0;
function saveScreenshot(name,shot) {
  fs.writeFileSync(path.join(output,name),Buffer.from(shot.data,'base64'));
  ++screenshotCount;
}
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
      let html=fs.readFileSync(path.join(root,'src/network/web/index.html'),'utf8').replace('@WSPRRY_PICO_FIRMWARE_VERSION@','test-firmware');
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
async function checkStatusTypography(context) {
  const type=await evaluate(`(()=>{const root=getComputedStyle(document.documentElement);return {family:root.fontFamily,size:parseFloat(root.fontSize),values:Array.from(document.querySelectorAll('#transmitter-status dd')).map(e=>{const s=getComputedStyle(e);return {id:e.id,family:s.fontFamily,size:parseFloat(s.fontSize),weight:s.fontWeight,lineHeight:parseFloat(s.lineHeight)}})}})()`);
  assert.equal(type.values.length,11,'both status grids and the conditional next value are covered');
  for(const value of type.values) {
    assert.equal(value.family,type.family,`${context} ${value.id} system font`);
    assert.equal(value.size,type.size,`${context} ${value.id} body-sized value`);
    assert.equal(value.weight,'400',`${context} ${value.id} consistent regular value`);
    assert.equal(value.lineHeight,type.size*1.5,`${context} ${value.id} readable value leading`);
  }
}
const config=async()=>{const c=f.client();await c.identity();return (await c.publicRead('config')).json();};
async function edit(name,value,pins=false) {
  await evaluate(`document.getElementById('config').elements[${JSON.stringify(name)}].value=${JSON.stringify(value)};document.getElementById('config').elements[${JSON.stringify(name)}].dispatchEvent(new Event('input',{bubbles:true}));${pins?"document.getElementById('config').elements["+JSON.stringify(name)+"].dispatchEvent(new Event('change',{bubbles:true}));":''}`);
}
async function key(key,code=key) {
  const windowsVirtualKeyCode=key==='Escape'?27:key==='Enter'?13:9;
  await send('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode,text:key==='Enter'?'\r':undefined});
  await send('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode});
}
async function checkStatusGrid() {
  const original=await evaluate(`['console-message','hostname'].map(id=>[id,document.getElementById(id).textContent])`);
  await evaluate(`document.getElementById('console-message').textContent='ABCDEFGHIJKLMNOPQRSTUVWXYZ123456\\nDot 3000000000 s · 512 copies';document.getElementById('hostname').textContent='a'.repeat(63)+'.'+'b'.repeat(63)+'.'+'c'.repeat(63)+'.'+'d'.repeat(57)+'.local';`);
  for(const width of [1280,900,899,650,600,599,390,320]) {
    await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<600});
    const grid=await evaluate(`(()=>{const lists=document.querySelectorAll('#transmitter-status dl');const list=lists[0],s=getComputedStyle(list);return {lists:lists.length,columns:s.gridTemplateColumns.split(' ').length,align:s.textAlign,overflow:document.documentElement.scrollWidth>innerWidth,items:[...list.children].filter(e=>!e.hidden).map(e=>{const r=e.getBoundingClientRect(),d=e.querySelector('dd').getBoundingClientRect();return {x:r.left,y:r.top,ddx:d.left,align:getComputedStyle(e).textAlign};})};})()`);
    assert.equal(grid.lists,1,'all transmitter observations share one grid');
    const columns=width>=900?3:width>=600?2:1;
    assert.equal(grid.columns,columns,`${width}px uses ${columns} columns`);
    assert.equal(grid.overflow,false,`${width}px has no horizontal overflow`);
    assert(grid.items.every(item=>['left','start'].includes(item.align)&&Math.abs(item.x-item.ddx)<1),'every field remains left aligned');
    for(let at=0;at<Math.min(columns,grid.items.length);++at)assert.equal(grid.items[at].y,grid.items[0].y,'first row aligns');
    if(grid.items.length>columns)assert.equal(grid.items[columns].x,grid.items[0].x,'following rows begin at the left edge');
  }
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await evaluate("document.body.style.zoom='2'");
  assert.equal(await evaluate('document.documentElement.scrollWidth>innerWidth'),false,'long status values remain within the page at 200% zoom');
  await evaluate("document.body.style.zoom=''");
  await evaluate(`for(const [id,value] of ${JSON.stringify(original)})document.getElementById(id).textContent=value;`);
}
async function capture(state) {
  if(filterOnly)return;
  for(const [width,height] of [[1280,900],[650,900],[360,800],[390,844]]) for(const area of ['station','wifi-host']) {
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});
    await click(area==='station'?'station-link':'wifi-host-link');
    for(const theme of ['light','dark']) {
      await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]});
      assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,`${width} ${area} ${theme}`);
      const headings=await evaluate(`Array.from(document.querySelectorAll('#${area}-area [data-operator-section]>summary')).map(e=>{const label=e.querySelector(':scope>h2')||e,style=getComputedStyle(label);let opacity=1;for(let p=label;p;p=p.parentElement)opacity*=Number(getComputedStyle(p).opacity);return {opacity,color:style.color,family:style.fontFamily,size:style.fontSize,weight:style.fontWeight,lineHeight:style.lineHeight}})`);
      const type=await evaluate('({family:getComputedStyle(document.documentElement).fontFamily,size:parseFloat(getComputedStyle(document.documentElement).fontSize)*1.25})');
      assert.ok(headings.length>0);
      for(const heading of headings) {
        assert.equal(heading.opacity,1,`${state} ${area} disclosure remains readable`);
        assert.equal(heading.color,'rgb(37, 49, 61)',`${state} ${area} disclosure uses body text color`);
        assert.equal(heading.family,type.family,'all peer labels use the established system font');
        assert.equal(parseFloat(heading.size),type.size,'all peer labels share the disclosure size');
        assert.equal(heading.weight,'600','rendered h2 labels inherit the disclosure weight');
        assert.equal(parseFloat(heading.lineHeight),type.size*1.5,'all peer labels share the disclosure line height');
      }
      if(area==='station') {
        await checkStatusTypography(`${state} ${width} ${theme}`);
        const buttons=await evaluate(`['restart','abort','release'].map(id=>{const e=document.getElementById(id),r=e.getBoundingClientRect();return {top:r.top,left:r.left,right:r.right,height:r.height}})`);
        assert.ok(buttons.every(b=>b.height>=44),'transmitter actions retain touch targets');
        if(width>=650) assert.equal(new Set(buttons.map(b=>b.top)).size,1,'transmitter actions share a row when space permits');
        else assert.ok(new Set(buttons.map(b=>b.top)).size>1,'transmitter actions wrap on narrow screens');
      }
    }
    // Inspect both layouts in one batched round; this UI deliberately keeps its light palette.
    if(output) {
      if(state==='locked' && area==='station' && [1280,390].includes(width)) {
        await evaluate('document.querySelectorAll("#station-area [data-operator-section]").forEach(e=>e.open=false);document.getElementById("radio-settings").scrollIntoView()');
        const headings=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
        saveScreenshot(`${state}-headings-${width}.png`,headings);
        await evaluate('scrollTo(0,0)');
      }
      await evaluate(`document.querySelectorAll('#${area}-area [data-operator-section]').forEach(e=>e.open=true)`);
      const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
      saveScreenshot(`${state}-${area}-${width}.png`,shot);
    }
  }
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  if(output && state==='unlocked') {
    await click('station-link');await evaluate('const e=document.getElementById("radio-settings");e.open=true;e.scrollIntoView()');
    const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});saveScreenshot('station-settings.png',shot);

    for(const [width,height,name] of [[1280,1000,'desktop'],[390,844,'mobile']]) {
      await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});
      for(const id of ['radio-settings','time-calibration']) {
        await evaluate(`document.getElementById('${id}').open=true;document.getElementById('${id}').scrollIntoView()`);
        assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
        const clip=await evaluate(`(()=>{const r=document.getElementById('${id}').getBoundingClientRect();return {x:0,y:r.top+scrollY,width:innerWidth,height:r.height,scale:1}})()`);
        saveScreenshot(id+'-'+name+'.png',await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip}));
      }
    }
    await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
    await evaluate('scrollTo(0,0)');
  }
  const zoomArea=await evaluate('document.getElementById("station-area").hidden ? "wifi-host" : "station"');
  await evaluate('document.documentElement.style.zoom="2"');
  assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'200% zoom');
  for(const area of ['station','wifi-host']) {
    await click(area==='station'?'station-link':'wifi-host-link');
    if(area==='station') await checkStatusTypography(`${state} 200% zoom`);
    const types=await evaluate(`Array.from(document.querySelectorAll('#${area}-area [data-operator-section]>summary')).map(e=>{const s=getComputedStyle(e.querySelector(':scope>h2')||e);return [s.fontFamily,s.fontSize,s.fontWeight,s.lineHeight].join('|')})`);
    assert.equal(new Set(types).size,1,`${area} disclosure typography stays consistent at 200% zoom`);
  }
  await evaluate('document.documentElement.style.zoom=""');
  await click(zoomArea==='station'?'station-link':'wifi-host-link');
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
  assert.equal(await evaluate('document.getElementById("console-state").hidden'),await evaluate('document.getElementById("console-warning").hidden'));
  if(await evaluate('snapshot.standalone.reboot_required'))
    assert.match(await evaluate('document.getElementById("console-warning").textContent'),/Reset Pico/);
  else assert.equal(await evaluate('document.getElementById("console-warning").hidden'),true);
  assert.equal(await evaluate('document.getElementById("console-next-item").hidden'),true);
  assert.equal(await evaluate('document.getElementById("console-next").textContent'),'');
  assert.match(await evaluate('document.getElementById("console-correction").textContent'),/^(?:-?\d+\.\d{3}|Unavailable)$/);
  assert.equal(await evaluate('document.getElementById("hostname").textContent'),await evaluate('hostnameState.active'));
  for(const id of ['console-explanation','console-local','console-utc','console-observed','engine','discovery'])
    assert.equal(await evaluate(`document.getElementById('${id}')`),null);
  assert.equal(await evaluate('document.getElementById("notice").hidden'),true);
  assert.equal(await evaluate('document.getElementById("section-menu")'),null);
  assert.equal(await evaluate('document.getElementById("local-access").open'),false);
  assert.ok(reads.filter(r=>r.path.startsWith('/api/consumer/v1/read')).length>20);
  assert.equal(reads.every(r=>r.method==='GET'),true);
  assert.equal((await f.command({op:'stats'})).config_sequence,'1');
  assert.equal(await evaluate('document.getElementById("saved-settings").hidden'),true);
  assert.equal(await evaluate('document.getElementById("consumer-setup").hidden'),true);
  assert.equal(await evaluate('document.getElementById("saved-active-status").textContent'),'');
  console.log('PASS locked public settings, detailed status, redaction, layout and no writes');
  for(const area of ['wifi-host','station']) {
    await evaluate('scrollTo(0,document.body.scrollHeight)');await click(area==='station'?'station-link':'wifi-host-link');
    assert.equal(await evaluate('scrollY'),0);
    assert.equal(await evaluate(`document.getElementById('${area==='station'?'station-link':'wifi-host-link'}').getAttribute('aria-current')`),'page');
  }
  await click('access-toggle');assert.equal(await evaluate('document.activeElement.id'),'local-password');
  await key('Escape');assert.equal(await evaluate('document.activeElement.id'),'access-toggle');
  assert.equal(await evaluate('document.getElementById("access-toggle").getAttribute("data-access")'),'locked');
  assert.equal(await evaluate('getComputedStyle(document.getElementById("access-toggle")).borderTopColor'),'rgb(177, 61, 50)');
  assert.equal(await evaluate('document.getElementById("firmware-version").textContent'),'test-firmware');
  assert.equal(await evaluate('!window.dispatchEvent(new Event("beforeunload",{cancelable:true}))'),false,'fresh locked page has no unsaved warning');
  await checkStatusGrid();
  await capture('locked');
  console.log('PASS top navigation, active view, modal keyboard, mobile, color preferences and zoom');
  await click('access-toggle');await evaluate('document.getElementById("local-password").value="test-password"');await key('Enter');
  await until(()=>evaluate('!busy && online && localAuthenticated && writeState==="ready"'),'authenticated settings read');
  assert.equal(await evaluate('getComputedStyle(document.getElementById("access-toggle")).borderTopColor'),'rgb(40, 116, 65)');
  assert.equal(await evaluate('document.getElementById("notice").hidden'),true);
  assert.equal(await evaluate('document.getElementById("saved-settings").hidden'),true);
  assert.equal(await evaluate('document.getElementById("consumer-save-recovery").hidden'),true);
  assert.equal(await evaluate('document.getElementById("reload-config")'),null);
  assert.equal(await evaluate('document.querySelector(".documentation-note")'),null);
  assert.equal(await evaluate('!window.dispatchEvent(new Event("beforeunload",{cancelable:true}))'),false,'login readback has no unsaved warning');
  await capture('unlocked');
  await evaluate('document.getElementById("radio-pins").open=true');
  await click('amplifier-timing-read');await idle();
  await until(()=>evaluate('document.getElementById("amplifier-lead-ms").value==="200"'),'amplifier timing default');
  assert.equal(await evaluate('document.getElementById("amplifier-tail-ms").value'),'200');
  assert.equal(await evaluate('document.getElementById("radio-pins").contains(document.getElementById("amplifier-lead-ms"))'),true);
  if(output && !filterOnly) for(const [width,height,name] of [[1280,1100,'desktop'],[390,1100,'mobile']]) {
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});
    await evaluate('document.querySelectorAll("[data-operator-section]").forEach(e=>e.open=e.id==="radio-pins");scrollTo(0,0)');
    assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
    const layout=await send('Page.getLayoutMetrics');
    const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width,height:layout.cssContentSize.height,scale:1}});
    saveScreenshot('amplifier-timing-'+name+'.png',shot);
  }
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  assert.equal(await evaluate('document.getElementById("amplifier-timing-settings").contains(document.querySelector("[name=amplifier_gp]"))'),true);
  for(const width of [1280,650,390,360]) {
    await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width<600});
    const row=await evaluate('Array.from(document.querySelectorAll(".led-fields select")).map(e=>e.getBoundingClientRect().top)');
    assert.equal(new Set(row).size,1,'LED controls share a row at '+width);
    assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
  }
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await edit('rf_gp','3',true);
  await edit('amplifier_gp','20',true);await edit('amplifier_active_high','false',true);
  await evaluate('document.getElementById("amplifier-lead-ms").value="350";document.getElementById("amplifier-lead-ms").dispatchEvent(new Event("input",{bubbles:true}))');
  await click('amplifier-timing-save');await idle();
  assert.match(await evaluate('document.getElementById("amplifier-timing-status").textContent'),/Amplifier config saved/);
  const ampConfig=await config();
  assert.equal(ampConfig.config.pins.amplifier_gp,20);assert.equal(ampConfig.config.pins.amplifier_active_high,false);
  assert.equal(ampConfig.config.pins.rf_gp,2);assert.equal(await evaluate('document.getElementById("config").elements.rf_gp.value'),'3');
  const ampClient=f.client();await ampClient.identity();
  assert.equal((await (await ampClient.publicRead('amplifier-timing')).json()).saved.lead_ms,350);
  await edit('rf_gp','2',true);await edit('amplifier_gp','',true);await edit('amplifier_active_high','true',true);
  await evaluate('document.getElementById("amplifier-lead-ms").value="200";document.getElementById("amplifier-lead-ms").dispatchEvent(new Event("input",{bubbles:true}))');
  await click('amplifier-timing-save');await idle();
  assert.match(await evaluate('document.getElementById("amplifier-timing-status").textContent'),/Amplifier config saved/);
  console.log('PASS lock borders, quiet unlock, footer version, LED row and amplifier config save preserving unrelated drafts');
  const selectorButton=text=>evaluate(`Array.from(document.querySelectorAll('#filter-selector-controls button')).find(b=>b.textContent===${JSON.stringify(text)}).click()`);
  const selectorField=(label,value)=>evaluate(`(()=>{const l=Array.from(document.querySelectorAll('#filter-selector-controls label')).find(l=>l.firstChild?.textContent===${JSON.stringify(label)});const input=l.querySelector('input,select');input.value=${JSON.stringify(String(value))};input.dispatchEvent(new Event('input',{bubbles:true}));})()`);
  await selectorButton('Read saved selectors');await idle();
  await selectorButton('Add selector');await selectorField('Selector name','HF filters');await selectorField('Pico GPIO',6);await selectorField('Polarity','false');
  await selectorButton('Add frequency range');await selectorField('Range name','40m');await selectorField('Selector',1);await selectorField('From (Hz)',7000000);await selectorField('Through (Hz)',7300000);await selectorField('Selection policy','required');
  assert.equal(await evaluate(`Array.from(document.querySelectorAll('#filter-selector-controls button')).find(b=>b.textContent==='Save selectors').disabled`),false);
  await selectorField('Through (Hz)',6000000);assert.equal(await evaluate(`Array.from(document.querySelectorAll('#filter-selector-controls button')).find(b=>b.textContent==='Save selectors').disabled`),true);await selectorField('Through (Hz)',7300000);
  if(output)for(const [width,height,name] of [[1280,1000,'desktop'],[390,1000,'mobile']]){
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});
    await evaluate('document.getElementById("radio-pins").open=true;document.getElementById("filter-selector-controls").scrollIntoView()');
    assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true,'selector '+name);
    const clip=await evaluate('(()=>{const r=document.getElementById("filter-selector-controls").getBoundingClientRect();return {x:0,y:r.top+scrollY,width:innerWidth,height:r.height,scale:1};})()');
    const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip});saveScreenshot('filter-pico-'+name+'.png',shot);
  }
  await selectorButton('Save selectors');await idle();
  assert.match(await evaluate('document.getElementById("filter-selector-controls").innerText'),/Selectors saved/);
  const settingsClient=f.client();await settingsClient.identity();const selectorSaved=await (await settingsClient.publicRead('filter-selector')).json();assert.equal(selectorSaved.saved.selectors[0].gp,6);assert.equal(selectorSaved.saved.selectors[0].active_high,false);assert.equal(selectorSaved.pending_restart,true);
  await selectorButton('Read saved selectors');await idle();await selectorField('Selection policy','fixed_manual');await selectorButton('Remove range');await selectorButton('Remove selector 1');await selectorButton('Save selectors');await idle();
  console.log('PASS selector editor -> production HTTP/crypto, declared coverage validation, GPIO/polarity save, restart and default restoration');
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});

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
  assert.equal(await evaluate('document.getElementById("saved-settings").hidden'),false);
  await f.time(f.now+1000);
  await click('access-toggle');await evaluate('document.getElementById("local-password").value="test-password"');
  await until(()=>evaluate('!busy && !document.getElementById("login-submit").disabled && (document.getElementById("local-login").requestSubmit(),true)'),'login available');
  await until(()=>evaluate('!busy && localAuthenticated && writeState==="review"'),'uncertain save login readback');
  await click('read-saved');await idle();
  assert.equal(await evaluate('writeState'),'review','reading must not acknowledge an uncertain save');
  assert.equal(await evaluate('document.getElementById("save-pins").disabled'),true);
  await click('read-saved');await idle();
  assert.equal(await evaluate('writeState'),'review');
  if(output && !filterOnly) for(const [width,height,name] of [[1280,1000,'desktop'],[390,844,'mobile']]) {
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});
    await evaluate('document.getElementById("saved-settings").open=true;document.getElementById("saved-settings").scrollIntoView()');
    assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
    const clip=await evaluate('(()=>{const r=document.getElementById("saved-settings").getBoundingClientRect();return {x:0,y:r.top+scrollY,width:innerWidth,height:r.height,scale:1}})()');
    saveScreenshot('contextual-recovery-'+name+'.png',await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip}));
  }
  await f.time(f.now+1000);
  const concurrent=f.client();await f.login(concurrent);
  const hardware=await concurrent.request('hardware'),hw=await hardware.json();
  assert.equal((await concurrent.request('hardware','PUT',{schema:hw.schema,target:hw.target,pins:{...hw.saved,button_gp:13}},hardware.headers.get('etag'))).status,200);
  const afterConcurrent=(await f.command({op:'stats'})).config_sequence;
  await click('review-saved');await idle();
  assert.equal(await evaluate('writeState'),'readback');
  assert.equal(await evaluate('document.getElementById("save-pins").disabled'),true);
  assert.equal(await evaluate('document.getElementById("config").elements.button_gp.value'),'14');
  assert.equal((await f.command({op:'stats'})).config_sequence,afterConcurrent,'stale comparison approval writes nothing');
  await click('read-saved');await idle();await click('review-saved');await idle();
  assert.equal(await evaluate('writeState'),'ready');
  assert.equal(await evaluate('document.getElementById("saved-settings").hidden'),true);
  assert.equal(await evaluate('document.getElementById("recovery-reveal").hidden'),true);
  assert.equal(await evaluate('document.activeElement.id'),'device-name');
  assert.equal((await f.command({op:'stats'})).config_sequence,afterConcurrent,'review and approval never replay a save');
  console.log('PASS contextual recovery, readback protection, explicit review and concurrent-revision invalidation through production HTTP/crypto');
  // Current timeout writes and public loading survive a boot.
  await evaluate('{const e=document.getElementById("ntp-timeout-minutes");e.value="0";e.dispatchEvent(new Event("input",{bubbles:true}));}');
  await click('ntp-timeout-save');await idle();
  if(!await evaluate('document.getElementById("ntp-timeout-status").textContent.startsWith("NTP timeout saved:")')) {
    assert.equal(await evaluate('document.getElementById("ntp-timeout-read").hidden'),false,'stale revision exposes a readback action');
    await click('ntp-timeout-read');await idle();await click('ntp-timeout-save');await idle();
  }
  assert.match(await evaluate('document.getElementById("ntp-timeout-status").textContent'),/saved: never expire/i);
  assert.equal(await evaluate('document.getElementById("ntp-timeout-read").hidden'),true);
  await f.command({op:'reboot'});await f.time(f.now+1000);
  await send('Page.navigate',{url:`http://127.0.0.1:${server.address().port}/station`});
  await until(()=>evaluate('typeof localIdentity!=="undefined" && !!localIdentity && typeof settingsLoadedBoot!=="undefined" && settingsLoadedBoot===localIdentity.boot_id && !busy'),'zero timeout automatic postboot read');
  assert.equal(await evaluate('document.getElementById("ntp-timeout-minutes").value'),'0');
  assert.equal(await evaluate('document.getElementById("ntp-timeout-read").hidden'),true);
  assert.equal(await evaluate('document.getElementById("rf-calibration-read").hidden'),true);
  assert.equal(await evaluate('document.getElementById("amplifier-timing-read").hidden'),true);
  assert.equal(await evaluate('(async()=> (await radio.publicRead("ntp-timeout")).status)()'),200,'the canonical resource represents zero after reboot');
  assert.equal((await f.fetch('192.168.1.53',false,'/api/consumer/v1/read/3/ntp-timeout/2')).status,404,'obsolete public catalog routes are absent');
  console.log('PASS zero timeout save, stale-revision recovery, reboot persistence, automatic public load and historical-version refusal');

  // Drive the real scheduler into a bounded memory refusal, then read it through
  // production public HTTP and the shipped UI. The synthetic sink emits no RF.
  const scheduleClient=f.client();await f.login(scheduleClient);
  const frequencyRead=await scheduleClient.request('standalone-frequency');
  const frequency=await frequencyRead.json();
  assert.equal((await scheduleClient.request('standalone-frequency','PUT',{schema:'standalone-frequency',target:frequency.target,frequency_hz:7038600},frequencyRead.headers.get('etag'))).status,200);
  const configRead=await scheduleClient.request('config');
  const application=await (await scheduleClient.request('application')).json();
  assert.equal((await scheduleClient.request('config/update','POST',{schema:'config-update',target:application.target,mode:'merge',config:{enabled:true,schedules:[{period_s:120,phase_s:0}]}},configRead.headers.get('etag'))).status,200);
  let operations=await (await scheduleClient.request('operations')).json();
  const advanceToPreparation=value=>{
    const now=BigInt(value.standalone.utc_now_ns),period=120000000000n;
    let slot=now/period*period+1000000000n;
    const watermark=BigInt(value.standalone.watermark_utc_ns);
    while(slot<=now+5000000000n || slot<=watermark)slot+=period;
    return (slot-now-5000000000n).toString();
  };
  const rejected=await f.command({op:'schedule_tick',delta_ns:advanceToPreparation(operations),free_bytes:'64000'});
  assert.equal(rejected.last_error?.code,'INTERNAL_ERROR',JSON.stringify(rejected));
  await click('refresh');await idle();
  assert.equal(await evaluate('document.getElementById("console-warning").hidden'),false);
  assert.equal(await evaluate('document.getElementById("console-state").hidden'),false);
  assert.match(await evaluate('document.getElementById("console-warning").textContent'),/INTERNAL_ERROR.*skipped/);
  assert.equal(await evaluate('document.getElementById("console-next-item").hidden'),true);
  await f.command({op:'schedule_tick',delta_ns:'0',uncertainty_ns:'600000000'});
  await click('refresh');await idle();
  assert.match(await evaluate('document.getElementById("console-warning").textContent'),/clock uncertainty.*INTERNAL_ERROR/);
  await checkStatusGrid();
  if(output)for(const [width,height,name] of [[1280,1000,'desktop'],[650,1000,'tablet'],[390,1000,'mobile']]) {
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});
    await click('station-link');await evaluate('scrollTo(0,0)');
    const shot=await send('Page.captureScreenshot',{format:'png'});saveScreenshot('transmission-blocked-'+name+'.png',shot);
  }
  operations=await (await scheduleClient.request('operations')).json();
  const admitted=await f.command({op:'schedule_tick',delta_ns:advanceToPreparation(operations),uncertainty_ns:'1000'});
  assert.equal(admitted.last_error,null);
  await click('refresh');await idle();
  assert.equal(await evaluate('document.getElementById("console-state").textContent'),'Job armed');
  assert.equal(await evaluate('document.getElementById("console-warning").hidden'),true,'confirmed admission clears the failure banner');
  console.log('PASS recorded WSPR admission failure, simultaneous clock blocker, recovery and left-aligned 3/2/1 grid through production HTTP');

  console.log(JSON.stringify({browser:(await send('Browser.getVersion')).product,api:'production HTTP/crypto',hardware:false,screenshots:screenshotCount}));
} catch(error) {
  console.error(JSON.stringify({errors,reads:reads.slice(-12),state:ws ? await evaluate('({notice:document.getElementById("notice")?.textContent,online:typeof online!=="undefined"?online:null,busy:typeof busy!=="undefined"?busy:null,settings:typeof settingsLoadedBoot!=="undefined"?settingsLoadedBoot:null})').catch(()=>null):null}));
  throw error;
} finally {
  if(ws) {await send('Browser.close').catch(()=>{});ws.close();}
  await new Promise(resolve=>server.close(resolve));await f.stop();
  await cleanupUiProcesses([chrome],profile,{processGroup});
}
