// Real shipped UI and synthetic RAM-backed consumer API; no board or RF access.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile,mkdir,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

const driver=process.argv[2], output=path.resolve(process.argv[3] || 'build/standalone-frequency-ui');
if (!driver) throw Error('Usage: node standalone_frequency_ui_integration.mjs DRIVER [OUTPUT]');
await mkdir(output,{recursive:true});
const profile=await mkdtemp(path.join(os.tmpdir(),'wsprrypico-frequency-browser-'));
let fixture, chrome, cdp;
class Cdp {
  constructor(url) {
    this.ws=new WebSocket(url);this.pending=new Map();this.sequence=0;
    this.ws.onmessage=event=>{const r=JSON.parse(event.data),p=this.pending.get(r.id);if(p){this.pending.delete(r.id);r.error?p.reject(Error(r.error.message)):p.resolve(r.result);}};
  }
  async open(){if(this.ws.readyState!==1)await new Promise((resolve,reject)=>{this.ws.onopen=resolve;this.ws.onerror=reject;});}
  send(method,params={}){const id=++this.sequence;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{this.pending.delete(id);reject(Error('Browser deadline: '+method));},15000);this.pending.set(id,{resolve:v=>{clearTimeout(timer);resolve(v);},reject:e=>{clearTimeout(timer);reject(e);}});this.ws.send(JSON.stringify({id,method,params}));});}
  async evaluate(expression){const r=await this.send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
}
async function until(fn,label,ms=15000){const end=Date.now()+ms;while(Date.now()<end){if(await fn())return;await new Promise(resolve=>setTimeout(resolve,50));}throw Error('Timed out: '+label);}
async function field(id,value){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));}`);}
async function click(id){await cdp.evaluate(`document.getElementById(${JSON.stringify(id)}).click()`);}
async function capture(name){
  for(const view of [{name:'desktop',width:1280,height:900},{name:'mobile',width:390,height:844}]){
    await cdp.send('Emulation.setDeviceMetricsOverride',{width:view.width,height:view.height,deviceScaleFactor:1,mobile:view.name==='mobile'});
    await cdp.evaluate(`document.getElementById('standalone-frequency-form').scrollIntoView({block:'start'})`);
    assert.equal(await cdp.evaluate('document.documentElement.scrollWidth>innerWidth'),false,'horizontal overflow');
    const png=await cdp.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    await writeFile(path.join(output,`${name}-${view.name}.png`),Buffer.from(png.data,'base64'));
  }
}
try {
  let fixtureOutput='';
  fixture=spawn(process.execPath,['tests/ui_review_fixture.mjs',driver,'18939',output],{stdio:['ignore','pipe','pipe']});
  fixture.stdout.on('data',data=>{fixtureOutput+=data;});
  fixture.stderr.on('data',data=>{fixtureOutput+=data;});
  await until(()=>fixtureOutput.includes('READY;'),'fixture startup');
  chrome=spawn(process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    ['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking',
     '--remote-debugging-port=0',`--user-data-dir=${profile}`,'--proxy-server=http://127.0.0.1:18939','--proxy-bypass-list=<-loopback>','about:blank'],{stdio:'ignore'});
  let debugPort;
  await until(async()=>{try{debugPort=Number((await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);return !!debugPort;}catch{return false;}},'browser startup',30000);
  const pages=await(await fetch(`http://127.0.0.1:${debugPort}/json`)).json();
  cdp=new Cdp(pages.find(p=>p.type==='page').webSocketDebuggerUrl);await cdp.open();await cdp.send('Page.enable');
  await cdp.send('Page.navigate',{url:'http://192.168.1.53/'});
  await until(()=>cdp.evaluate('typeof localIdentity!=="undefined" && !!localIdentity && !busy'),'consumer page');
  await field('local-password','test-password');
  await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);
  await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'login');
  await until(()=>cdp.evaluate(`!document.getElementById('standalone-frequency-read').disabled`),'frequency availability');
  await click('standalone-frequency-read');
  await until(()=>cdp.evaluate(`!document.getElementById('standalone-frequency').disabled`),'unset readback');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),true);
  assert.match(await cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent`),/No standalone transmit frequency/);
  const ax=(await cdp.send('Accessibility.getFullAXTree')).nodes.find(node=>node.role?.value==='textbox' && node.name?.value==='Base frequency (Hz)');
  assert.ok(ax,'frequency has an explicit accessible label');
  assert.match(ax.description?.value || '',/No transmit frequency is preselected/);
  await capture('unset');
  await field('standalone-frequency','14097100.0');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),true);
  await field('standalone-frequency','14097100');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency-save').disabled`),false);
  assert.doesNotMatch(await cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent`),/without commas/);
  await click('standalone-frequency-save');
  await until(()=>cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent.includes('Saved 14,097,100 Hz for future')`),'saved readback');
  assert.equal(await cdp.evaluate(`document.getElementById('config').elements.enabled.checked`),false,'frequency save does not enable a schedule');
  await field('standalone-frequency','bad');
  await click('standalone-frequency-discard');
  assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'14097100');
  assert.match(await cdp.evaluate(`document.getElementById('standalone-frequency-status').textContent`),/draft was discarded/);
  await capture('saved');
  await writeFile(path.join(output,'result.json'),JSON.stringify({passed:true,frequency_initial:null,frequency_saved_hz:14097100,schedule_enabled:false,views:['desktop','mobile'],physical_qualification:false},null,2)+'\n');
  console.log('Consumer frequency UI: unset, explicit save, disabled schedules, desktop/mobile and accessible label passed');
} finally {
  cdp?.ws.close();
  for(const process of [chrome,fixture])if(process && process.exitCode===null){process.kill('SIGTERM');await Promise.race([new Promise(resolve=>process.once('exit',resolve)),new Promise(resolve=>setTimeout(resolve,3000))]);}
  await rm(profile,{recursive:true,force:true,maxRetries:10,retryDelay:100});
}
