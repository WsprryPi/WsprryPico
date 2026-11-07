// Trusted CDP input against the shipped page and genuine production-handler fixture.
import assert from 'node:assert/strict';
import {until} from './browser_harness.mjs';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
export async function checkLockedControls({evaluate,send,key,section,login,idle,output}) {
  const tip='document.getElementById("locked-control-tooltip")';
  const visible=()=>evaluate(`!${tip}.hidden`);
  const point=async selector=>{
    await evaluate(`{const node=document.querySelector(${JSON.stringify(selector)});WsprryPicoSections.reveal(node);node.scrollIntoView({block:'center'});}`);
    await evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');
    const value=await evaluate(`(()=>{const r=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,width:r.width,height:r.height}})()`);
    assert.ok(value.width>0&&value.height>0,'real rendered target '+selector);
    return {x:value.x,y:value.y};
  };
  async function mouse(selector) {
    console.log('Locked feedback input: '+selector);
    const p=await point(selector);
    await send('Input.dispatchMouseEvent',{type:'mousePressed',...p,button:'left',clickCount:1});
    await send('Input.dispatchMouseEvent',{type:'mouseReleased',...p,button:'left',clickCount:1});
  }
  async function shown() {
    await until(visible,'locked tooltip');
    assert.equal(await evaluate(`${tip}.textContent`),'Controls are locked');
    assert.equal(await evaluate(`(()=>{const r=${tip}.getBoundingClientRect();return r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight})()`),true,'tooltip stays in viewport');
    assert.equal(await evaluate(`(()=>{const t=${tip}.getBoundingClientRect(),r=document.querySelector('[aria-describedby~="locked-control-tooltip"]').getBoundingClientRect();return Math.min(Math.abs(t.bottom-r.top),Math.abs(r.bottom-t.top))<=16})()`),true,'tooltip stays close to target, including zoom');
    assert.equal(await evaluate('document.getElementById("local-access").open'),false,'feedback never opens login');
  }
  await evaluate(`globalThis.lockRequests=[];globalThis.lockFetch=fetch;globalThis.fetch=(url,options)=>{lockRequests.push({url:String(url),method:options?.method||'GET'});return lockFetch(url,options)};globalThis.lockValues=[document.getElementById('consumer-callsign').value,document.getElementById('config').elements.enabled.checked];`);
  await mouse('#restart');await shown();await key('Escape');
  await section('station-identity');
  for(const selector of ['#consumer-callsign','#consumer-power']) {
    assert.equal(await evaluate(`document.querySelector(${JSON.stringify(selector)}).matches(':disabled')`),true);
    await mouse(selector);await shown();await key('Escape');assert.equal(await visible(),false);
  }
  await mouse('#consumer-station-form button[type=submit]');assert.equal(await visible(),false,'pending saved-state review is not an authentication-only save lock');
  await section('wifi-settings');await mouse('#consumer-password-toggle');await shown();
  await mouse('#consumer-network-form button[type=submit]');await shown();
  await section('hostname-section');await mouse('#hostname-save');await shown();await mouse('#hostname-default');await shown();
  await section('station-identity');
  // The native label's text remains an equivalent pointer target.
  await mouse('#consumer-callsign');await shown();
  await key('Tab');assert.equal(await visible(),false,'focus movement dismisses');
  await section('radio-settings');
  await mouse('select[name=rf_engine]');await shown();
  await evaluate(`document.getElementById('config').elements.rf_engine.value='i2c';syncRfEngine()`);
  await mouse('#si5351-settings [data-si=reference_source]');await shown();
  await mouse('#gps-settings [data-gps=enabled]');await shown();
  assert.equal(await evaluate('document.querySelectorAll("#locked-control-tooltip").length'),1,'repeated attempts use one tooltip');
  await evaluate(`globalThis.lockGps=capabilities.gps;capabilities.gps=null;controls(online)`);
  await mouse('#gps-settings [data-gps=enabled]');assert.equal(await visible(),false,'unsupported is not an authentication tooltip');
  await evaluate(`capabilities.gps=lockGps;document.getElementById('config').elements.rf_engine.value='direct';syncRfEngine();controls(online)`);
  // Newly mounted controls, nested labels and form-associated inputs use the same guard.
  await evaluate(`globalThis.lockDynamic=document.createElement('label');lockDynamic.id='lock-dynamic';lockDynamic.innerHTML='Dynamic field <span>nested label</span><input id="lock-dynamic-input" form="config" value="preserve">';document.getElementById('pin-settings').append(lockDynamic);`);
  await until(()=>evaluate('document.getElementById("lock-dynamic-input").hasAttribute("data-auth-locked-control")'),'new field observed');
  await mouse('#lock-dynamic span');await shown();
  await evaluate('lockDynamic.remove()');await until(async()=>!await visible(),'removed target clears tooltip');
  // Exclude busy locks; never temporarily enable native controls.
  await evaluate('busy=true;controls(online)');
  await mouse('select[name=rf_engine]');assert.equal(await visible(),false);
  await evaluate('busy=false;snapshot.job.owner_id="other-owner";controls(online)');
  await mouse('select[name=rf_engine]');assert.equal(await visible(),false,'foreign ownership is not an authentication tooltip');
  await evaluate('snapshot.job.owner_id=null;controls(online)');
  await section('hostname-section');
  for(const width of [390,320,740]) {
    await send('Emulation.setDeviceMetricsOverride',{width,height:width===740?360:844,deviceScaleFactor:1,mobile:true});
    await send('Emulation.setTouchEmulationEnabled',{enabled:true});
    const p=await point('#hostname-input');
    await send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[p]});
    await send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
    await shown();
    assert.equal(await evaluate('document.documentElement.scrollWidth<=innerWidth'),true);
    if(process.env.UI_REVIEW_NO_CAPTURE!=='1') {
      const image=await send('Page.captureScreenshot',{format:'png'});
      await writeFile(path.join(output,'locked-feedback-'+width+'.png'),Buffer.from(image.data,'base64'));
    }
    const scrollBefore=await evaluate('scrollY');
    await send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[p]});
    for(let move=1;move<=4;++move) {
      await send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:p.x,y:p.y+move*20}]});
      await evaluate('new Promise(requestAnimationFrame)');
    }
    await send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
    await until(()=>evaluate(`scrollY!==${scrollBefore}`),'native touch scrolling at '+width+'px');
    await until(async()=>!await visible(),'scroll dismisses');
  }
  await send('Emulation.setTouchEmulationEnabled',{enabled:false});
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await evaluate('document.body.style.zoom="2"');await mouse('#hostname-input');await shown();
  if(process.env.UI_REVIEW_NO_CAPTURE!=='1') {
    const image=await send('Page.captureScreenshot',{format:'png'});
    await writeFile(path.join(output,'locked-feedback-zoom.png'),Buffer.from(image.data,'base64'));
  }
  await evaluate('document.body.style.zoom=""');
  // One existing, named keyboard affordance; no disabled-field tab stops.
  await evaluate('document.querySelector("#hostname-section [data-top]").click()');
  await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',modifiers:8,windowsVirtualKeyCode:9});
  await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',modifiers:8,windowsVirtualKeyCode:9});
  assert.equal(await evaluate('document.activeElement.id'),'access-toggle');
  await shown();
  assert.equal(await evaluate('document.getElementById("locked-control-announcement").textContent'),'Controls are locked');
  assert.match(await evaluate('document.getElementById("access-toggle").getAttribute("aria-describedby")'),/access-state.*locked-control-tooltip/);
  await key('Escape');assert.equal(await visible(),false);
  await key('Enter');
  await mouse('#local-password');await send('Input.insertText',{text:'x'});
  assert.equal(await evaluate('document.getElementById("local-password").value'),'x','modal input is not intercepted by controls behind it');
  assert.equal(await visible(),false);await key('Escape');
  assert.deepEqual(await evaluate(`[document.getElementById('consumer-callsign').value,document.getElementById('config').elements.enabled.checked]`),await evaluate('lockValues'));
  assert.deepEqual(await evaluate('lockRequests.filter(r=>r.method!=="GET")'),[],'locked attempts send no application mutations or login requests');
  await evaluate('globalThis.fetch=lockFetch');
  await section('radio-settings');
  const heldSelector='input[name=enabled]';
  const heldValue=await evaluate('document.getElementById("config").elements.enabled.checked');
  const held=await point(heldSelector);
  await send('Input.dispatchMouseEvent',{type:'mousePressed',...held,button:'left',clickCount:1});await shown();
  await login();
  const released=await point(heldSelector);
  await send('Input.dispatchMouseEvent',{type:'mouseReleased',...released,button:'left',clickCount:1});
  assert.equal(await evaluate('document.getElementById("config").elements.enabled.checked'),heldValue,'unlock between down/up does not activate a previously locked gesture');
  assert.equal(await evaluate('document.querySelectorAll("[data-auth-locked-control]").length'),0,'unlock removes hit markers');
  assert.equal(await visible(),false,'unlock removes obsolete feedback');
  await section('radio-settings');
  const selector='input[name=enabled]';
  const before=await evaluate('document.getElementById("config").elements.enabled.checked');
  await mouse(selector);
  assert.equal(await evaluate('document.getElementById("config").elements.enabled.checked'),!before,'first unlocked interaction works normally');
  await mouse(selector); // Restore the unsaved draft.
  await evaluate('document.querySelector("input[name=enabled]").focus()');
  await send('Input.dispatchKeyEvent',{type:'keyDown',key:' ',code:'Space',windowsVirtualKeyCode:32,text:' '});
  await evaluate('document.getElementById("access-toggle").click()');await idle();
  await send('Input.dispatchKeyEvent',{type:'keyUp',key:' ',code:'Space',windowsVirtualKeyCode:32});
  assert.equal(await evaluate('document.getElementById("config").elements.enabled.checked'),before,'locking while Space is held preserves the checkbox');
  await until(()=>evaluate('!busy && online && !!settingsLoadedBoot'),'signed-out public observations');
  await section('hostname-section');await mouse('#hostname-input');await shown();
  await section('radio-settings');assert.equal(await visible(),false,'navigation dismisses');
  await evaluate('document.querySelector("#radio-settings [data-top]").click()');
  await evaluate('lockedFeedback.destroy();lockedFeedback.destroy()');
  assert.equal(await evaluate('document.querySelectorAll("#locked-control-tooltip,#locked-control-announcement,[data-auth-locked-control]").length'),0,'idempotent teardown removes tooltip, announcement and hit markers');
  console.log('PASS locked native mouse/touch/keyboard feedback, generated GPS/Si5351 fields, dynamic labels, viewport/zoom, exclusions, no mutation and unlocked first interaction');
}
