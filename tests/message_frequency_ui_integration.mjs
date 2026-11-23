// Real shipped UI and synthetic RAM-backed consumer API; no board or RF access.
import assert from 'node:assert/strict';
import {writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {BrowserHarness,until,fixtureJson} from './browser_harness.mjs';
const h=new BrowserHarness();
await h.run(async()=>{

const driver=process.argv[2], output=path.resolve(process.argv[3] || 'build/message-frequency-ui');
if (!driver) throw Error('Usage: node message_frequency_ui_integration.mjs DRIVER [OUTPUT]');
await mkdir(output,{recursive:true});
let profile;
let fixture, chrome, cdp, fixturePort=19039;

async function field(id,value){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});if(${JSON.stringify(id)}==='local-password'&&!document.getElementById('local-access').open)document.getElementById('access-toggle').click();globalThis.WsprryPicoSections?.reveal(e);e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));}`);}
// Submit once the production form admits it; discovery/polling can briefly disable login.
async function submitLogin(){await until(()=>cdp.evaluate(`!busy && !document.getElementById('login-submit').disabled && (document.getElementById('local-login').requestSubmit(),true)`),'login form available');}
async function click(id){await cdp.evaluate(`document.getElementById(${JSON.stringify(id)}).click()`);}
async function control(command) {
  return fixtureJson('http://127.0.0.1:'+fixturePort+'/.fixture-control',{method:'POST',body:JSON.stringify(command)});
}
async function capture(name,target='job-heading'){
  for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]){
    await cdp.send('Emulation.setDeviceMetricsOverride',{width:view.width,height:view.height,deviceScaleFactor:1,mobile:view.name==='mobile'});
    await cdp.evaluate(`document.getElementById(${JSON.stringify(target)}).scrollIntoView({block:'start'})`);
    assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false,'horizontal overflow');
    if(process.env.PICO_BROWSER_NO_CAPTURE==='1')continue;
    const png=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    await writeFile(path.join(output,`${name}-${view.name}.png`),Buffer.from(png.data,'base64'));
    if(view.name==='mobile' && target==='job-heading') {
      await cdp.evaluate(`document.getElementById('message-preview').scrollIntoView({block:'center'})`);
      const tail=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
      await writeFile(path.join(output,`${name}-preview-mobile.png`),Buffer.from(tail.data,'base64'));
    }
  }
}
function expectedEvents(mode, base, upper, characters=false) {
  const dfcw=mode==='dfcw', fskcw=mode==='fskcw';
  const durations=characters ? [3,3,dfcw?3:9,9,3,0] : [3,3,dfcw?3:9,21,3,7,3,3,dfcw?3:9,21,3,0];
  const marks=characters ? [true,false,true,false,true,false] : [true,false,true,false,true,false,true,false,true,false,true,false];
  let offset=0n;
  return durations.map((seconds,i)=>{
    const internal=characters ? i===1||i===3 : [1,3,7,9].includes(i);
    const on=marks[i] || fskcw && internal;
    const event={offset_ns:String(offset),duration_ns:String(i===durations.length-1 ? 1000n : BigInt(seconds)*1000000000n),rf_on:on,
      frequency_nhz:on ? String(fskcw ? (marks[i]?upper:base) : dfcw && [2,8].includes(i) ? upper:base) : null};
    offset+=BigInt(event.duration_ns);return event;
  });
}
const evidence=[];
{
  fixture=await h.review(driver,19039,output,{profiles:['consumer-lan','engineering'],messages:true});await fixture.ready;
  for(const surface of ['consumer','engineering']) {
    const port=surface==='consumer'?19039:19044;
    fixturePort=port;
    profile=await h.profile('pico-message-'+surface+'-');
    const started=await h.chrome(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',
       '--remote-debugging-port=0',`--user-data-dir=${profile}`,'--proxy-server=http://127.0.0.1:'+port,'--proxy-bypass-list=<-loopback>','about:blank'],profile);chrome=started.browser.process;
    cdp=await h.connect(started.pages[0].webSocketDebuggerUrl,{dialogs:false});await cdp.send('Page.enable');
    await cdp.send('Page.navigate',{url:'http://192.168.1.53/'});
    if(surface==='consumer') {
      await until(()=>cdp.evaluate('typeof localIdentity!=="undefined" && !!localIdentity && !busy'),'consumer page');
      await field('local-password','test-password');await submitLogin();
    }
    await until(()=>cdp.evaluate('typeof online!=="undefined" && online && !busy'),'ready page');
    assert.equal(await cdp.evaluate(`document.getElementById('message-delivery')`),null);
    assert.equal(await cdp.evaluate(`document.getElementById('job-file')`),null);
    assert.equal(await cdp.evaluate(`document.getElementById('message-interval').value`),'10');
    assert.deepEqual(await cdp.evaluate(`['message-text','message-mode','message-frequency','message-shift','message-dot','message-repeats','message-gap'].map(id=>document.getElementById(id).value)`),['73 DE AA0NT','qrss','','5','3','1','3']);
    assert.equal(await cdp.evaluate(`Date.parse(document.getElementById('message-start').value+'Z')%600000`),0);
    await capture(surface+'-initial-defaults');
    await cdp.evaluate(`globalThis.cwRequests=[];globalThis.originalApi=api;api=async(...args)=>{if(args[0]==='message-schedule'&&args[1]==='PUT')cwRequests.push(structuredClone(args[2]));return originalApi(...args);};`);
    const beforeState=await control({op:'frequency_state'});
    async function setStart(){await cdp.evaluate(`document.getElementById('message-start').value=new Date(Number(BigInt(snapshot.standalone.utc_now_ns)/1000000n)+60000).toISOString().slice(0,19).replace('T',' ')`);}
    async function stop(){
      await cdp.evaluate(`(async()=>{const before=await api('schedules/stop');const result=await api('schedules/stop','POST',{schema:'schedule-stop',target:before.data.target,stop:true},before.revision);if(!result.data.stopped)throw Error('Stop unconfirmed');await readMessageSchedule(true);await refresh();})()`);
    }
    async function compileNext(){
      await control({op:'schedule_tick',surface,delta_ns:'58000000000'});
      return control({op:'accepted_job',surface});
    }
    for(const mode of ['qrss','fskcw','dfcw']) {
      for(const [id,value] of Object.entries({mode,text:'A E',frequency:'14096900',shift:'5',dot:'3',dash:'3',intra:'1',character:'3',word:'7',repeats:'2',gap:'7'}))await field('message-'+id,value);
      await cdp.evaluate(`document.getElementById('message-mode').dispatchEvent(new Event('change',{bubbles:true}))`);await setStart();
      const label=mode==='qrss'?'Carrier':mode==='fskcw'?'Space':'Dot';
      const ax=(await cdp.send('Accessibility.getFullAXTree')).nodes.find(n=>n.role?.value==='textbox'&&n.name?.value===label+' frequency (Hz)');assert(ax,'accessible mode label');assert.match(ax.description?.value||'',/Direct RF/);
      const preview=await cdp.evaluate(`document.getElementById('message-preview').textContent`);
      assert(preview.includes(label+' 14096900 Hz'));if(mode!=='qrss')assert(preview.includes((mode==='fskcw'?'Mark':'Dash')+' 14096905 Hz'));
      await capture(surface+'-'+mode);
      await cdp.evaluate(`document.getElementById('message-mode').focus()`);
      const tab=async()=>{await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});};
      await tab();assert.equal(await cdp.evaluate('document.activeElement.id'),'message-frequency');
      await tab();assert.equal(await cdp.evaluate('document.activeElement.id'),mode==='qrss'?'message-dot':'message-shift');
      const count=await cdp.evaluate('cwRequests.length');
      await cdp.evaluate(`document.getElementById('message-submit').focus()`);
      assert.equal(await cdp.evaluate(`document.activeElement.textContent`),'Save and start schedule');
      await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r'});
      await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
      await until(()=>cdp.evaluate(`!busy&&cwRequests.length===${count+1}&&messageScheduleReadback?.data.saved?.enabled`),'saved '+surface+' '+mode);
      const requests=(await cdp.evaluate('cwRequests')).slice(count);assert.equal(requests.length,1);
      const body=requests[0].schedule.message;
      assert.equal(body.frequency_nhz,mode==='fskcw'?'14096905000000000':'14096900000000000');
      assert.equal(body.space_frequency_nhz,mode==='qrss'?'0':mode==='fskcw'?'14096900000000000':'14096905000000000');
      const compiled=await compileNext();assert.equal(compiled.mode,mode);assert.equal(compiled.allow_frequency_adjustment,true);
      assert.equal(compiled.total_duration_ns,mode==='dfcw'?'73000001000':'85000001000');
      assert.deepEqual(compiled.events,expectedEvents(mode,14096900000000000n,14096905000000000n));
      evidence.push({surface,preview,requests,compiled});await stop();
    }
    // The authenticated native settings route retains explicit frequency validation.
    for(const [mode,first,second,accepted] of [
      ['dfcw','14096900000000000','14096905000000000',true],['dfcw','14096905000000000','14096900000000000',false],
      ['dfcw','14096900000000000','14096900000000000',false],['dfcw','14096900000000000','0',false],
      ['fskcw','14096900000000000','14096905000000000',false],['fskcw','14096900000000000','14096900000000000',false],
      ['qrss','14096900000000000','18446744073709551615',true]]) {
      const result=await cdp.evaluate(`(async()=>{const read=await api('message-schedule');const message={...cwRequests[0].schedule.message,message:'AE',repeat_count:1,mode:${JSON.stringify(mode)},frequency_nhz:${JSON.stringify(first)},space_frequency_nhz:${JSON.stringify(second)}};const schedule={...cwRequests[0].schedule,first_start_utc_ns:(BigInt(snapshot.standalone.utc_now_ns)+60000000000n).toString(),message};try{await api('message-schedule','PUT',{schema:'message-schedule',target:read.data.target,schedule},read.revision);return {accepted:true};}catch(error){return {accepted:false,error:error.message};}})()`);
      assert.equal(result.accepted,accepted,mode+' explicit '+first+'/'+second);
      if(accepted){const compiled=await compileNext();assert.deepEqual(compiled.events,expectedEvents(mode,BigInt(first),BigInt(second),true));await stop();}
    }
    // Retired direct jobs and file upload do not provide a fallback.
    assert.equal(await cdp.evaluate(`(async()=>{try{await api('jobs','POST',{});return false;}catch(error){return true;}})()`),true);
    await field('message-mode','dfcw');await field('message-frequency','14096900.123456789');await field('message-shift','0.000000001');await field('message-text','AE');await field('message-repeats','1');await setStart();
    await cdp.evaluate(`document.getElementById('message-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy&&messageScheduleReadback?.data.saved?.enabled`),'fractional native schedule');
    const fractional=await compileNext();assert.deepEqual(fractional.events,expectedEvents('dfcw',14096900123456789n,14096900123456790n,true));evidence.push({surface,fractional});await stop();
    const count=await cdp.evaluate('cwRequests.length');
    await field('message-shift','bad');await field('message-mode','qrss');assert.equal(await cdp.evaluate(`document.getElementById('message-shift').disabled`),true);
    assert.doesNotMatch(await cdp.evaluate(`document.getElementById('message-preview').textContent`),/Frequency shift/);
    await field('message-mode','fskcw');assert.equal(await cdp.evaluate(`document.getElementById('message-shift').value`),'bad');
    await cdp.evaluate(`document.getElementById('message-form').requestSubmit()`);await until(()=>cdp.evaluate('!busy'),'invalid input');
    assert.equal(await cdp.evaluate('cwRequests.length'),count);await capture(surface+'-invalid');
    await field('message-shift','5');await field('message-frequency','14096900');
    const saved=await cdp.evaluate(`JSON.stringify(['message-frequency','message-shift','message-text','message-dot','message-dash'].map(id=>document.getElementById(id).value))`);
    await cdp.evaluate('refresh()');assert.equal(await cdp.evaluate(`JSON.stringify(['message-frequency','message-shift','message-text','message-dot','message-dash'].map(id=>document.getElementById(id).value))`),saved);
    await cdp.send('Network.enable');await cdp.send('Network.emulateNetworkConditions',{offline:true,latency:0,downloadThroughput:-1,uploadThroughput:-1});await cdp.evaluate('refresh()');
    assert.equal(await cdp.evaluate(`document.getElementById('message-frequency-label').textContent`),'Space frequency (Hz)');
    await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1});await cdp.evaluate('refresh()');
    if(surface==='consumer'&&!await cdp.evaluate('localAuthenticated')){await field('local-password','test-password');await submitLogin();}
    await until(()=>cdp.evaluate(`online&&!busy&&!document.getElementById('message-settings').disabled`),'reconnected message editor');
    assert.equal(await cdp.evaluate(`JSON.stringify(['message-frequency','message-shift','message-text','message-dot','message-dash'].map(id=>document.getElementById(id).value))`),saved);
    // Restore is explicit; an uncertain committed save blocks writes until readback.
    for(const [id,value] of Object.entries({mode:'qrss',text:'E',frequency:'14096900',interval:'20'}))await field('message-'+id,value);
    await setStart();await cdp.evaluate(`document.getElementById('message-form').requestSubmit()`);
    await until(()=>cdp.evaluate(`!busy&&messageScheduleReadback?.data.saved?.enabled`),'saved message schedule');
    await field('message-text','KEEP DRAFT');await click('refresh');await until(()=>cdp.evaluate('!busy'),'schedule refresh');
    assert.equal(await cdp.evaluate(`document.getElementById('message-text').value`),'KEEP DRAFT');
    let restoreDialog;const releaseRestore=cdp.on('Page.javascriptDialogOpening',async params=>{restoreDialog=params;await cdp.send('Page.handleJavaScriptDialog',{accept:true});});
    try{await click('message-schedule-adopt');}finally{releaseRestore();}
    assert.match(restoreDialog?.message||'',/Replace the current message draft/);assert.equal(await cdp.evaluate(`document.getElementById('message-text').value`),'E');
    await cdp.evaluate(`{const original=api;api=async(...args)=>{const response=await original(...args);if(args[0]==='message-schedule'&&args[1]==='PUT'){api=original;throw Error('Saved schedule reply lost');}return response;};document.getElementById('message-form').requestSubmit();}`);
    await until(()=>cdp.evaluate('!busy&&messageScheduleUncertain'),'unconfirmed committed schedule save');
    await click('refresh');await until(()=>cdp.evaluate('!busy'),'ordinary refresh during schedule recovery');
    assert.equal(await cdp.evaluate(`document.getElementById('message-submit').disabled`),true);
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-read').hidden`),false);
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-adopt').hidden`),true);
    assert.equal(await cdp.evaluate(`document.getElementById('message-schedule-pause').hidden`),true);
    await capture(surface+'-schedule-recovery','message-schedule-controls');
    await click('message-schedule-read');await until(()=>cdp.evaluate('!busy&&!messageScheduleUncertain'),'explicit schedule readback');
    assert.equal(await cdp.evaluate(`document.getElementById('message-result').textContent`),'');
    await click('message-schedule-pause');await until(()=>cdp.evaluate(`!busy&&messageScheduleReadback?.data.saved?.enabled===false`),'confirmed schedule pause');
    assert.match(await cdp.evaluate(`document.getElementById('message-schedule-status').textContent`),/Save and start schedule/);
    await capture(surface+'-schedule-paused','message-schedule-controls');
    await cdp.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:'dark'}]});assert.equal(await cdp.evaluate('getComputedStyle(document.documentElement).colorScheme'),'light');
    await cdp.evaluate(`document.documentElement.style.fontSize='200%'`);await capture(surface+'-text-200-percent');
    const afterSchedule=await control({op:'frequency_state'});
    assert.equal(afterSchedule.saved_dial_hz,beforeState.saved_dial_hz,'message schedule leaves the WSPR dial unchanged');
    assert.equal(afterSchedule.enabled,beforeState.enabled,'message schedule leaves WSPR enablement unchanged');
    await cdp.stop();cdp=null;await started.browser.stop();chrome=null;
    console.log('PASS '+surface+' shipped native CW schedules, compiled events, explicit API, keyboard, errors, drafts and views');
  }
  await writeFile(path.join(output,'cw-evidence.json'),JSON.stringify(evidence,null,2)+'\n');
  await writeFile(path.join(output,'result.json'),JSON.stringify({passed:true,surfaces:['consumer','engineering'],modes:['qrss','fskcw','dfcw'],themes:['light'],views:['desktop','mobile'],text_zoom:200,physical_qualification:false},null,2)+'\n');
}
});
