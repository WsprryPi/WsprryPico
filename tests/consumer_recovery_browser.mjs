import {fixtureHttpBody} from './fixture_http_body.mjs';
// Independent Chrome contexts -> shipped page -> production HTTP/crypto/recovery.
// Only TCP, flash and time use deterministic fixture boundaries; no hardware/RF.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import {BrowserHarness,until,fixtureJson} from './browser_harness.mjs';
const h=new BrowserHarness();
await h.run(async()=>{
if(!globalThis.WebSocket)throw Error('Node with built-in WebSocket is required');
if(!process.argv[2])throw Error('Usage: node tests/consumer_recovery_browser.mjs CONSUMER_BOOTSTRAP_DRIVER [OUTPUT_DIRECTORY]');
const output=process.argv[3]&&path.resolve(process.argv[3]);
if(output)fs.mkdirSync(output,{recursive:true});
const f=await h.fixture(process.argv[2]);
const profile=await h.profile('pico-recovery-browser-');
let cdp,dropNextReply=false,dropRetirementReply=false;
const dialogs=[];let queue=Promise.resolve();
const server=http.createServer((req,res)=>{queue=queue.then(()=>serve(req,res));});
async function serve(req,res){
  try {
    const url=new URL(req.url.startsWith('http:')?req.url:'http://192.168.1.53'+req.url);
    if(url.hostname!=='192.168.1.53'){res.writeHead(403);res.end();return;}
    const parts=[];for await(const chunk of req)parts.push(chunk);
    const response=await f.fetch(url.hostname,false,url.pathname,{method:req.method,
      headers:{'Content-Type':req.headers['content-type']||'application/json'},body:Buffer.concat(parts)});
    const bytes=await fixtureHttpBody(f,response);
    if(dropRetirementReply&&url.pathname.endsWith('/recovery/finish')){dropRetirementReply=false;res.destroy();return;}
    if(dropNextReply&&url.pathname.endsWith('/request')){dropNextReply=false;res.destroy();return;}
    res.writeHead(response.status,Object.fromEntries(response.headers));res.end(bytes);
  }catch(error){res.writeHead(500);res.end(error.message);}
}
const send=(...args)=>cdp.send(...args);
async function evaluate(session,expression){const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true},session);if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
async function context(){const {browserContextId}=await send('Target.createBrowserContext');const {targetId}=await send('Target.createTarget',{url:'about:blank',browserContextId});const {sessionId}=await send('Target.attachToTarget',{targetId,flatten:true});await send('Page.enable',{},sessionId);await send('Runtime.enable',{},sessionId);await send('Page.navigate',{url:'http://192.168.1.53/'},sessionId);await until(()=>evaluate(sessionId,'typeof localIdentity!=="undefined" && Boolean(localIdentity) && !busy'));return sessionId;}
async function login(session){
  await until(()=>evaluate(session,'!accessClosing && !document.getElementById("access-toggle").disabled'));
  await evaluate(session,'if(!document.getElementById("local-access").open)document.getElementById("access-toggle").click();true');
  assert.equal(await evaluate(session,'document.getElementById("local-access").open'),true,'native access dialog');
  await evaluate(session,'document.getElementById("local-password").value="test-password";document.getElementById("local-login").requestSubmit();true');await until(()=>evaluate(session,'!busy && localAuthenticated && online'));}
{
  await h.server(server,()=>queue);await f.time(1000);await h.listen(server);
  const started=await h.chrome(process.env.CHROME_BIN||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check',
      '--remote-debugging-port=0','--user-data-dir='+profile,'--proxy-server=http://127.0.0.1:'+server.address().port,'--proxy-bypass-list=<-loopback>','about:blank'],profile);
  const port=new URL(started.pages[0].webSocketDebuggerUrl).port;
  const version=await fixtureJson('http://127.0.0.1:'+port+'/json/version');
  cdp=await h.connect(version.webSocketDebuggerUrl);
  cdp.on('Page.javascriptDialogOpening',async(params,session)=>{dialogs.push(params.message);await send('Page.handleJavaScriptDialog',{accept:true},session);});
  const a=await context(),b=await context();await login(a);await f.time(2000);await login(b);
  assert.equal(await evaluate(a,'radio.authenticated'),true);
  // Independent UI drafts survive another client's save and a stale explicit save.
  await evaluate(b,'document.querySelector("[name=schedules]").value="240 / 0";document.querySelector("[name=schedules]").dispatchEvent(new Event("input",{bubbles:true}));true');
  await evaluate(a,'document.querySelector("[name=schedules]").value="360 / 0";document.querySelector("[name=schedules]").dispatchEvent(new Event("input",{bubbles:true}));document.getElementById("config").dispatchEvent(new Event("submit",{cancelable:true}));true');
  await until(()=>evaluate(a,'!busy'));
  await evaluate(b,'document.getElementById("config").dispatchEvent(new Event("submit",{cancelable:true}));true');await until(()=>evaluate(b,'!busy'));
  assert.equal(await evaluate(b,'document.querySelector("[name=schedules]").value'),'240 / 0');assert.equal(await evaluate(b,'radio.authenticated'),true);
  assert.match(await evaluate(b,'document.getElementById("notice").textContent'),/Saved settings changed|Read and review/);
  const peer=f.client();await f.time(3000);await f.login(peer);
  const c=await context();await f.time(4000);
  await evaluate(c,'document.getElementById("local-password").value="test-password";document.getElementById("local-login").dispatchEvent(new Event("submit",{cancelable:true}));true');
  await until(()=>evaluate(c,'!busy'));
  assert.match(await evaluate(c,'document.getElementById("notice").textContent'),/three radio sessions/);
  // Real lost response after production handler commit; no request replay.
  const before=await f.command({op:'stats'});
  const draftBefore=await (await peer.request('progress')).json();dropNextReply=true;
  await evaluate(a,'document.querySelector("[name=schedules]").value="480 / 0";document.querySelector("[name=schedules]").dispatchEvent(new Event("input",{bubbles:true}));document.getElementById("config").dispatchEvent(new Event("submit",{cancelable:true}));true');
  await until(()=>evaluate(a,'!busy && !radio.authenticated'));
  const draftAfter=await (await peer.request('progress')).json();
  assert.equal(BigInt(draftAfter.draft_revision),BigInt(draftBefore.draft_revision)+1n,'lost reply commits draft exactly once');
  assert.deepEqual(draftAfter.fields.schedules,[{period_s:480,phase_s:0}]);
  assert.equal((await f.command({op:'stats'})).config_sequence,before.config_sequence,'saving progress does not apply schedules');
  assert.equal(await evaluate(a,'document.querySelector("[name=schedules]").value'),'480 / 0');
  assert.equal(await evaluate(a,'document.getElementById("save-config").disabled'),true);
  assert.equal((await peer.request('status')).status,200);assert.equal(await evaluate(b,'(async()=> (await radio.request("status")).status)()'),200);
  // Known selector self-recovery with visible dedicated credential entry.
  await send('Page.bringToFront',{},a);await send('Emulation.setFocusEmulationEnabled',{enabled:true},a);
  await evaluate(a,'document.getElementById("access-toggle").click();document.getElementById("login-recovery").open=true;document.getElementById("inspect-logins").focus();true');
  assert.equal(await evaluate(a,'document.activeElement.id'),'inspect-logins');
  await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,nativeVirtualKeyCode:36,text:'\r',unmodifiedText:'\r'},a);await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13},a);
  // The busy state disables the activated button and can move focus to body.
  await until(()=>evaluate(a,'!busy && Boolean(retirementDiscovery)'));
  await evaluate(a,'document.getElementById("retirement-target").value=radio.lostSession.selector;document.getElementById("retirement-target").dispatchEvent(new Event("change"));document.getElementById("retirement-password").value="test-password";document.getElementById("retire-login").click();true');
  await until(()=>evaluate(a,'!busy'));
  assert.match(await evaluate(a,'document.getElementById("retirement-status").textContent'),/retired/);
  assert.equal(await evaluate(a,'document.getElementById("retirement-password").value'),'');
  await f.time(5000);await login(a);
  assert.equal(await evaluate(a,'writeState'),'review');assert.equal(await evaluate(a,'document.getElementById("save-config").disabled'),true);
  assert.equal(await evaluate(a,'document.querySelector("[name=schedules]").value'),'480 / 0');
  assert.equal(await evaluate(a,'document.getElementById("local-login").hidden'),true);
  assert.equal(await evaluate(a,'document.getElementById("local-access").open'),false,'successful login closes access dialog');
  // Fresh page inspection makes deliberate peer impact visible at full capacity.
  await evaluate(c,'document.getElementById("access-toggle").click();document.getElementById("login-recovery").open=true;if(!document.getElementById("local-access").open)document.getElementById("access-toggle").click();document.getElementById("login-recovery").open=true;document.getElementById("inspect-logins").click();true');
  await until(()=>evaluate(c,'!busy && Boolean(retirementDiscovery)'));
  await evaluate(c,`document.getElementById("retirement-target").value=${JSON.stringify(peer.retirementSelector)};document.getElementById("retirement-target").dispatchEvent(new Event("change"));true`);
  if(output) for(const [session,state] of [[a,'saved-review'],[c,'full-capacity-retirement']]) for(const [name,width,height] of [['desktop',1280,900],['mobile',390,844]])for(const theme of ['light','dark']){
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:name==='mobile'},session);
    await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]},session);
    assert.equal(await evaluate(session,'document.documentElement.scrollWidth<=innerWidth'),true);
    const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},session);
    fs.writeFileSync(path.join(output,`${name}-${theme}-${state}.png`),Buffer.from(shot.data,'base64'));
  }
  await evaluate(a,'document.getElementById("review-saved").click();true');await until(()=>evaluate(a,'!busy'));
  assert.equal(await evaluate(a,'document.getElementById("save-config").disabled'),false);
  const victim=peer.retirementSelector;
  await evaluate(c,`document.getElementById("retirement-target").value=${JSON.stringify(victim)};document.getElementById("retirement-target").dispatchEvent(new Event("change"));document.getElementById("retirement-password").value="test-password";document.getElementById("retire-login").click();true`);
  await until(()=>evaluate(c,'!busy'));await assert.rejects(peer.request('status'));
  assert.equal(await evaluate(a,'(async()=> (await radio.request("status")).status)()'),200);assert.equal(await evaluate(b,'(async()=> (await radio.request("status")).status)()'),200);
  await f.time(6000);await login(c);
  // An interrupted authenticated read leaves this browser's occupied selector
  // recoverable through the visible locked-access dialog.
  dropNextReply=true;await evaluate(a,'document.getElementById("refresh").click();true');
  await until(()=>evaluate(a,'!busy'));
  assert.equal(await evaluate(a,'radio.authenticated'),true,'public refresh preserves authentication');
  assert.equal(dropNextReply,true,'public refresh sends no authenticated exchange');
  await evaluate(a,'void action(()=>api("management"));true');
  await until(()=>evaluate(a,'!busy && !radio.authenticated'));

  await evaluate(a,'if(!document.getElementById("local-access").open)document.getElementById("access-toggle").click();document.getElementById("login-recovery").open=true;document.getElementById("inspect-logins").click();true');await until(()=>evaluate(a,'!busy && Boolean(retirementDiscovery)'));
  dropRetirementReply=true;await evaluate(a,'document.getElementById("retirement-target").value=radio.lostSession.selector;document.getElementById("retirement-target").dispatchEvent(new Event("change"));document.getElementById("retirement-password").value="test-password";document.getElementById("retire-login").click();true');
  await until(()=>evaluate(a,'!busy && !radio.authenticated'));assert.equal(await evaluate(a,'document.getElementById("save-config").disabled'),true);assert.equal(await evaluate(a,'writeState'),'readback');assert.match(await evaluate(a,'document.getElementById("notice").textContent'),/unconfirmed/);assert.equal(await evaluate(a,'document.querySelector("[name=schedules]").value'),'480 / 0');
  for(const session of [b,c])assert.equal(await evaluate(session,'(async()=> (await radio.request("status")).status)()'),200);
  assert.ok(dialogs.length>=3);assert.ok(dialogs.every(text=>text.includes('another operator')&&text.includes('radio jobs remain')));
  console.log(JSON.stringify({browser:(await send('Browser.getVersion')).product,independent_contexts:3,conflict_draft_preserved:true,authenticated_retirement:true,known_and_fresh_page:true,lost_commit_once:true,readback_review_required:true,keyboard:true,lost_self_retirement_blocks_save:true,dialogs:dialogs.length,screenshots:output?8:0}));

}
});
