// Opt-in real Chrome acceptance at the Pico's actual HTTP IP/hostname origins.
// Private input: {password,device,ip,hostname}. No credential is printed.
import fs from 'node:fs';
import path from 'node:path';
import dns from 'node:dns/promises';
import {spawn} from 'node:child_process';
import assert from 'node:assert/strict';

const args = process.argv.slice(2);
if (!args.includes('--run')) {
  console.log('Opt-in: --run --private-input <private.json> --output <private-directory> [--settings] [--ap]');
  process.exit(0);
}
const option = name => args[args.indexOf(name) + 1];
assert.ok(args.includes('--private-input') && args.includes('--output'));
const input = JSON.parse(fs.readFileSync(option('--private-input'),'utf8'));
const ap = args.includes('--ap');
assert.match(input.device,/^[0-9a-f]{32}$/);
assert.match(input.ip,/^(\d{1,3}\.){3}\d{1,3}$/);
assert.match(input.hostname,/^[a-z0-9-]{1,63}\.local$/);
if (ap) assert.equal(input.ip,'192.168.4.1');
const output = path.resolve(option('--output'));
fs.mkdirSync(output,{recursive:false,mode:0o700});
const profile = fs.mkdtempSync('/tmp/pico-consumer-browser-');
const chrome = spawn(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  ['--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check',
    '--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});
let socket, sequence = 0;
const pending = new Map(), evidence = {started_utc:new Date().toISOString(),device:input.device,interface:ap?'ap':'station',origins:[],settings:false,errors:[],responses:[]};
const pause = ms => new Promise(resolve=>setTimeout(resolve,ms));
async function until(check,limit=30000) {
  const end = Date.now()+limit;
  while (Date.now()<end) { if (await check()) return; await pause(100); }
  throw new Error('Browser acceptance deadline');
}
function send(method,params={}) { return new Promise((resolve,reject)=>{
  const id=++sequence;
  const timer=setTimeout(()=>{pending.delete(id);reject(new Error('Browser command deadline: '+method));},30000);
  pending.set(id,{resolve:value=>{clearTimeout(timer);resolve(value);},reject:error=>{clearTimeout(timer);reject(error);}});
  socket.send(JSON.stringify({id,method,params}));
}); }
async function evaluate(expression) {
  const result = await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || 'Browser script failed');
  return result.result.value;
}
try {
  await until(()=>fs.existsSync(path.join(profile,'DevToolsActivePort')));
  const port=fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n')[0];
  const tabs=await (await fetch('http://127.0.0.1:'+port+'/json')).json();
  socket=new WebSocket(tabs.find(tab=>tab.type==='page').webSocketDebuggerUrl);
  socket.onmessage=event=>{
    const message=JSON.parse(event.data), request=pending.get(message.id);
    if (message.method==='Runtime.exceptionThrown') evidence.errors.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
    if (message.method==='Network.responseReceived') evidence.responses.push({url:message.params.response.url,status:message.params.response.status});
    if (!request) return;
    pending.delete(message.id); message.error ? request.reject(new Error(message.error.message)) : request.resolve(message.result);
  };
  await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Network.enable');
  evidence.browser=(await send('Browser.getVersion')).product;
  if (!ap) {
    let timer;
    try {
      evidence.resolution=await Promise.race([dns.lookup(input.hostname,{family:4}),
        new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('Hostname resolution deadline')),15000);})]);
    } finally {clearTimeout(timer);}
    assert.equal(evidence.resolution.address,input.ip);
  }
  const urls=ap?['http://192.168.4.1/radio']:[input.ip,input.hostname].map(host=>'http://'+host+'/');
  for (const [index,entry] of urls.entries()) {
    const url=entry+(index===0 && input.receipt?'#save='+encodeURIComponent(JSON.stringify(input.receipt)):'');
    evidence.phase='page '+url;
    await send('Page.navigate',{url});
    await until(()=>evaluate('typeof localIdentity !== "undefined" && localIdentity !== null'));
    assert.equal(await evaluate('localIdentity.device_id'),input.device);
    const environment=await evaluate('({secure:isSecureContext,subtle:typeof crypto.subtle,random:typeof crypto.getRandomValues})');
    assert.equal(environment.secure,false);
    assert.equal(environment.random,'function');
    if (index===0) {
      evidence.phase='wrong password';
      const rejected=await evaluate('(async()=>{try{await radio.login("wrong-acceptance-password",localIdentity);return false}catch{return !radio.authenticated}})()');
      assert.equal(rejected,true);
      await pause(1100);
    }
    evidence.phase='login '+url;
    await evaluate('document.getElementById("local-password").value='+JSON.stringify(input.password)+
      ';document.getElementById("local-login").dispatchEvent(new Event("submit",{cancelable:true}));true');
    await until(()=>evaluate('online && localAuthenticated && !busy'));
    assert.equal(await evaluate('document.getElementById("local-password").value'),'');
    if (index===0 && input.receipt) {
      assert.equal(await evaluate('consumerAttempt?.sent'),true);
      for (const [name,width,height] of [['desktop',1280,900],['mobile',390,844]]) {
        await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:name==='mobile'});
        assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'),true);
        const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
        fs.writeFileSync(path.join(output,'receipt-'+name+'.png'),Buffer.from(shot.data,'base64'),{mode:0o600});
      }
      await evaluate('document.getElementById("consumer-check-save").onclick()');
      assert.equal(await evaluate('consumerAttempt'),null);
      assert.equal(await evaluate('location.hash'),'');
      assert.equal(await evaluate('document.getElementById("consumer-save-status").textContent'),'Your settings were saved and verified.');
      evidence.receipt_verified=true;
    }
    const before=await evaluate('(async()=>({config:(await api("config")).data.config,status:(await api("status")).data}))()');
    assert.equal(before.status.job.output_active,false);
    if (index===0 && args.includes('--settings')) {
      assert.equal(before.config.enabled,false);
      // A reversible radio opt-in while schedules/output are disabled. The
      // original complete config is restored even if verification fails.
      await evaluate('(async()=>{globalThis.acceptanceOriginal=(await api("config")).data.config;return true})()');
      try {
        await evaluate('(async()=>{const read=await api("config");const c=structuredClone(read.data.config);c.allow_non_amateur_frequency=!Boolean(c.allow_non_amateur_frequency);await api("config","PUT",c,read.revision);const saved=(await api("config")).data.config;if(saved.allow_non_amateur_frequency!==c.allow_non_amateur_frequency)throw new Error("Setting readback mismatch");return true})()');
      } finally {
        await evaluate('(async()=>{const read=await api("config");await api("config","PUT",globalThis.acceptanceOriginal,read.revision);return true})()');
      }
      const after=await evaluate('(async()=>({config:(await api("config")).data.config,status:(await api("status")).data}))()');
      assert.deepEqual(after.config,before.config);
      assert.equal(after.status.standalone.watermark_utc_ns,before.status.standalone.watermark_utc_ns);
      evidence.settings=true;
    }
    for (const [name,width,height] of [['desktop',1280,900],['mobile',390,844]]) {
      await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:name==='mobile'});
      assert.equal(await evaluate('document.documentElement.scrollWidth <= innerWidth'),true);
      const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
      fs.writeFileSync(path.join(output,index+'-'+name+'.png'),Buffer.from(shot.data,'base64'),{mode:0o600});
    }
    evidence.origins.push({url,environment,authenticated:true,private_read:true,
      identity:await evaluate('localIdentity'),status:before.status,
      capabilities:await evaluate('capabilities.wtp')});
    await evaluate('radio.logout()');
  }
  evidence.result='PASS';
} catch (error) {
  evidence.result='FAIL';evidence.error=error.message;process.exitCode=1;
  if (socket?.readyState===1) {
    evidence.notice=await evaluate('document.getElementById("notice")?.textContent').catch(()=>null);
    const shot=await send('Page.captureScreenshot',{format:'png'}).catch(()=>null);
    if (shot) fs.writeFileSync(path.join(output,'failure.png'),Buffer.from(shot.data,'base64'),{mode:0o600});
  }
} finally {
  if (socket?.readyState===1)
    await evaluate('typeof radio !== "undefined" && radio ? radio.logout() : null').catch(()=>{});
  socket?.close();chrome.kill('SIGTERM');
  evidence.finished_utc=new Date().toISOString();
  fs.writeFileSync(path.join(output,'result.json'),JSON.stringify(evidence,null,2)+'\n',{mode:0o600});
  console.log(JSON.stringify({result:evidence.result,browser:evidence.browser,origins:evidence.origins.length,settings:evidence.settings,phase:evidence.phase,error:evidence.error,notice:evidence.notice,errors:evidence.errors}));
}
