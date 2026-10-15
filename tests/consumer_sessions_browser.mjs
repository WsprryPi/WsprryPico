// Opt-in actual Chrome contexts and shipped UI against the Linux crypto/HTTP fixture.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn} from 'node:child_process';
import {Fixture} from './consumer_sessions.test.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const scratch=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);
fs.mkdirSync(out,{recursive:true});
const f=new Fixture('docker',['run','--rm','-i','--network','none','-v',root+':/work/pico:ro','-v',scratch+':/out:ro','wsprrypico-p153-env:local','/out/build-host/consumer_session_driver']);
let chrome,ws;const pending=new Map();let seq=0;
const server=http.createServer(async(req,res)=>{
  try {
    if(req.url.startsWith('/api/')){
      const parts=[];for await(const chunk of req)parts.push(chunk);
      const response=await f.fetch('192.168.1.53',false,req.url,{method:req.method,headers:{'Content-Type':req.headers['content-type']},body:new Uint8Array(Buffer.concat(parts))});
      res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));return;
    }
    if(req.url!=='/'){res.writeHead(404);res.end();return;}
    let html=fs.readFileSync(path.join(root,'src/network/web/index.html'),'utf8');
    const css=fs.readFileSync(path.join(root,'src/network/web/style.css'),'utf8');
    const bundle=fs.readFileSync(path.join(root,'src/network/bootstrap_web/radio-bundle.js'),'utf8');
    const app=fs.readFileSync(path.join(root,'src/network/web/app.js'),'utf8');
    html=html.replace('<link rel="stylesheet" href="/style.css">','<style>'+css+'</style>').replace('<script src="/app.js" defer></script>','');
    html=html.replace('</body>',()=>`<script>${bundle}</script><script>${app}</script></body>`);
    res.setHeader('Content-Type','text/html');res.end(html);
  }catch(error){res.writeHead(500);res.end();console.error(error);}
});
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(fn){for(let i=0;i<250;i++){if(await fn())return;await pause(40);}throw new Error('browser deadline');}
function send(method,params={},sessionId){return new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params,sessionId}));});}
async function evaluate(session,expression){const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true},session);if(r.exceptionDetails)throw new Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
async function context(){const {browserContextId}=await send('Target.createBrowserContext');const {targetId}=await send('Target.createTarget',{url:'about:blank',browserContextId});const {sessionId}=await send('Target.attachToTarget',{targetId,flatten:true});await send('Page.enable',{},sessionId);await send('Runtime.enable',{},sessionId);await send('Page.navigate',{url:`http://127.0.0.1:${server.address().port}/`},sessionId);await until(()=>evaluate(sessionId,'typeof localIdentity!=="undefined" && Boolean(localIdentity)'));return sessionId;}
async function login(session){await evaluate(session,'document.getElementById("local-password").value="test-password";document.getElementById("local-login").dispatchEvent(new Event("submit",{cancelable:true}));true');await until(()=>evaluate(session,'!busy && localAuthenticated && online'));}
try{
  await f.time(1000);await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const profile=fs.mkdtempSync('/tmp/p156-browser-');
  chrome=spawn(process.env.CHROME_BIN||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});
  await until(()=>fs.existsSync(path.join(profile,'DevToolsActivePort')));
  const [port,socket]=fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n');
  ws=new WebSocket('ws://127.0.0.1:'+port+socket);ws.onmessage=e=>{const m=JSON.parse(e.data),p=pending.get(m.id);if(!p)return;pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m.result);};await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
  const a=await context(),b=await context();await login(a);await f.time(2000);await login(b);
  assert.equal(await evaluate(a,'radio.authenticated'),true);
  // Independent UI drafts survive another client's save and a stale explicit save.
  await evaluate(b,'document.querySelector("[name=schedules]").value="240 / 0";document.getElementById("config").dispatchEvent(new Event("input"));true');
  await evaluate(a,'document.querySelector("[name=schedules]").value="360 / 0";document.getElementById("config").dispatchEvent(new Event("input"));document.getElementById("config").dispatchEvent(new Event("submit",{cancelable:true}));true');
  await until(()=>evaluate(a,'!busy'));
  await evaluate(b,'document.getElementById("config").dispatchEvent(new Event("submit",{cancelable:true}));true');await until(()=>evaluate(b,'!busy'));
  assert.equal(await evaluate(b,'document.querySelector("[name=schedules]").value'),'240 / 0');assert.equal(await evaluate(b,'radio.authenticated'),true);
  assert.match(await evaluate(b,'document.getElementById("notice").textContent'),/Saved settings changed/);
  const native=f.client();await f.time(3000);await f.login(native);
  const c=await context();await f.time(4000);
  await evaluate(c,'document.getElementById("local-password").value="test-password";document.getElementById("local-login").dispatchEvent(new Event("submit",{cancelable:true}));true');
  await until(()=>evaluate(c,'!busy'));
  assert.match(await evaluate(c,'document.getElementById("notice").textContent'),/three radio sessions/);
  for(const [name,width,height] of [['desktop',1280,900],['mobile',390,844]])for(const theme of ['light','dark']){
    await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:name==='mobile'},c);
    await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:theme}]},c);
    assert.equal(await evaluate(c,'document.documentElement.scrollWidth<=innerWidth'),true);
    const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true},c);
    fs.writeFileSync(path.join(out,`${name}-${theme}-capacity.png`),Buffer.from(shot.data,'base64'));
  }
  await evaluate(a,'document.getElementById("local-logout").click();true');await until(()=>evaluate(a,'!busy'));
  assert.equal(await evaluate(b,'(async()=> (await radio.request("status")).status)()'),200);
  await f.time(5000);await login(c);
  console.log(JSON.stringify({browser:(await send('Browser.getVersion')).product,independent_contexts:3,conflict_draft_preserved:true,logout_isolated:true,capacity_feedback:true,screenshots:4}));
}finally{if(ws)ws.close();if(chrome)chrome.kill('SIGTERM');await new Promise(resolve=>server.close(resolve));await f.stop();}
