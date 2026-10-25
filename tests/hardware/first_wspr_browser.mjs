// Opt-in device-served UI -> real standalone WSPR. No simulator or RF inhibit.
// Private input: {device,ip,hostname,password,dial_hz,station:{callsign,
// locator,power_dbm},receiver:{host,serial,executable,directory}}.
// The receiver is an installed wspq-capture-soapy on the explicitly selected
// SSH host. One expiring scheduled frame; no automatic RF retries.
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,mkdtemp} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import {cleanupUiProcesses} from '../ui_process_cleanup.mjs';

const args=process.argv.slice(2),option=name=>args[args.indexOf(name)+1];
assert.ok(args.includes('--run') && args.includes('--private-input') && args.includes('--output'));
const input=JSON.parse(await readFile(option('--private-input'),'utf8'));
assert.match(input.device,/^[0-9a-f]{32}$/);assert.match(input.ip,/^(\d{1,3}\.){3}\d{1,3}$/);
const dial=input.dial_hz,receiver=input.receiver;
const restoration=args.includes('--restore-schedules') || args.includes('--verify-restored');
if(restoration)assert.ok(args.includes('--original-snapshot'));
if(!args.includes('--observe-only') && !restoration) {
  assert.ok(Number.isSafeInteger(dial) && dial>0);
  assert.match(receiver.host,/^[a-zA-Z0-9][a-zA-Z0-9_.-]*$/);
  assert.match(receiver.serial,/^[a-zA-Z0-9]+$/);
  assert.ok(receiver.executable.startsWith('/') && receiver.directory.startsWith('/'));
  if(!args.includes('--resume'))assert.ok(input.station?.callsign && input.station?.locator && Number.isInteger(input.station.power_dbm));
}
const output=path.resolve(option('--output'));await mkdir(output,{mode:0o700});
const profile=await mkdtemp(path.join(os.tmpdir(),'pico-first-wspr-live-'));
const evidence={started:new Date().toISOString(),device:input.device,events:[],http:[],physical_rf:true};
let chrome,cdp,capture;
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function record(phase,detail={}) {const event={phase,utc:new Date().toISOString(),...detail};evidence.events.push(event);console.log(JSON.stringify(event));await writeFile(path.join(output,'result.json'),JSON.stringify(evidence,null,2),{mode:0o600});}
class Cdp {
  constructor(url){this.ws=new WebSocket(url);this.sequence=0;this.pending=new Map();this.ws.onmessage=e=>{const r=JSON.parse(e.data);if(r.method==='Page.javascriptDialogOpening'){void this.send('Page.handleJavaScriptDialog',{accept:true});return;}if(r.method==='Network.responseReceived'||r.method==='Network.loadingFailed'){evidence.http.push({utc:new Date().toISOString(),url:r.params.response?.url,status:r.params.response?.status,error:r.params.errorText});if(evidence.http.length>512)evidence.http.shift();}const p=this.pending.get(r.id);if(p){this.pending.delete(r.id);r.error?p.reject(Error(r.error.message)):p.resolve(r.result);}};}
  async open(){if(this.ws.readyState!==1)await new Promise((r,j)=>{this.ws.onopen=r;this.ws.onerror=j;});}
  send(method,params={}){const id=++this.sequence;return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{this.pending.delete(id);reject(Error('CDP deadline: '+method));},30000);this.pending.set(id,{resolve:v=>{clearTimeout(timer);resolve(v);},reject:e=>{clearTimeout(timer);reject(e);}});this.ws.send(JSON.stringify({id,method,params}));});}
  async evaluate(expression){const r=await this.send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
}
async function until(fn,label,ms=60000){const end=Date.now()+ms;while(Date.now()<end){if(await fn())return;await pause(200);}throw Error('Timed out: '+label);}
async function field(id,value){await cdp.evaluate(`{const e=document.getElementById(${JSON.stringify(id)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('input',{bubbles:true}));}`);}
async function click(id){await cdp.evaluate(`document.getElementById(${JSON.stringify(id)}).click()`);await until(()=>cdp.evaluate('!busy'),'action '+id);}
async function login(){await field('local-password',input.password);await cdp.evaluate(`document.getElementById('local-login').requestSubmit()`);await until(()=>cdp.evaluate('localAuthenticated && online && !busy'),'login');}
async function status(){
  await click('refresh');
  if(!await cdp.evaluate('localAuthenticated && radio.authenticated')) {
    await record('browser login ended; reconnecting for status only');
    await login();
  }
  return cdp.evaluate('snapshot ? ({job:snapshot.job,standalone:snapshot.standalone}) : null');
}
async function finishSetup(){
  await until(()=>cdp.evaluate('!busy && consumerAttempt!==null'),'setup receipt');
  const oldBoot=await cdp.evaluate('localIdentity.boot_id');
  await until(async()=>{
    try{return (await cdp.evaluate('radio.identity()')).boot_id!==oldBoot;}catch{return false;}
  },'setup restart',120000);
  const end=Date.now()+120000;
  while(Date.now()<end){
    await pause(1500);
    await cdp.evaluate(`action(()=>refresh())`);
    if(!await cdp.evaluate('localAuthenticated && radio.authenticated'))await login();
    await click('consumer-check-save');
    if(await cdp.evaluate('consumerAttempt===null'))return;
  }
  throw Error('Setup application not confirmed; no save was repeated');
}
async function restart(){
  const boot=await cdp.evaluate('localIdentity.boot_id');
  await cdp.evaluate(`document.getElementById('wifi-host-link').click()`);await click('restart');
  await until(async()=>{try{return (await cdp.evaluate('radio.identity()')).boot_id!==boot;}catch{return false;}},'explicit radio-settings restart',90000);
  await cdp.evaluate('action(()=>refresh())');
  if(!await cdp.evaluate('localAuthenticated && radio.authenticated'))await login();
  if(await cdp.evaluate(`writeState!=='ready'`)){await click('read-saved');await click('review-saved');}
  await cdp.evaluate(`document.getElementById('station-link').click()`);
  await record('explicit restart confirmed; radio settings boot-applied');
}
const quote=s=>"'"+String(s).replaceAll("'","'\\''")+"'";
function receive(start){
  const root=receiver.directory;
  const name=path.basename(output).replace(/[^a-zA-Z0-9-]/g,'-');
  const prefix=root+'/first-wspr-'+name;
  evidence.receiver={host:receiver.host,serial:receiver.serial,iq:prefix+'.cf32',metadata:prefix+'-capture.json'};
  const tool=receiver.executable;
  const argv=[tool,'--enable-physical-sdr','sdrplay',receiver.serial,String(dial+11500),'32000000','20','250000','200000','0','false','false','100000','150',prefix+'.cf32',prefix+'-capture.json','first-wspr-'+name];
  const py=`import os,time;time.sleep(max(0,${start-8}-time.time()));os.execv(${JSON.stringify(tool)},${JSON.stringify(argv)})`;
  const child=spawn('ssh',[receiver.host,'python3 -c '+quote(py)],{stdio:['ignore','pipe','pipe']});let log='';
  child.stdout.on('data',b=>{log+=b;});child.stderr.on('data',b=>{log+=b;});
  child.done=new Promise((resolve,reject)=>{child.on('error',reject);child.on('exit',code=>{void writeFile(path.join(output,'receiver.log'),log,{mode:0o600});code===0?resolve():reject(Error('Receiver exit '+code+': '+log.slice(-800)));});});
  // Retain rejection until the foreground joins it after the finite frame.
  child.done.catch(()=>{});return child;
}
try {
  chrome=spawn(process.env.CHROME_BIN||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--disable-gpu','--disable-background-networking','--no-first-run','--no-default-browser-check','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore',detached:true});
  let port;await until(async()=>{try{port=(await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];return true;}catch{return false;}},'Chrome');
  const tabs=await(await fetch('http://127.0.0.1:'+port+'/json')).json();cdp=new Cdp(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await cdp.open();await cdp.send('Page.enable');await cdp.send('Network.enable');
  await cdp.send('Page.navigate',{url:'http://'+input.ip+'/'});await until(()=>cdp.evaluate(`typeof localIdentity!=='undefined' && localIdentity!==null && !busy`),'Pico page');
  assert.equal(await cdp.evaluate('localIdentity.device_id'),input.device);await login();
  assert.equal(await cdp.evaluate('snapshot.standalone.engine'),'pio-dma-gp2');
  await record('real RF image and browser authenticated',{engine:await cdp.evaluate('snapshot.standalone.engine')});
  if(args.includes('--observe-only')) {
    const observed=await status();
    assert.ok(observed,'authoritative status must be available');
    await record('read-only browser reconnection',observed);
    evidence.result='PASS';await record('PASS status only; no RF job submitted');
  } else if(args.includes('--restore-schedules') || args.includes('--verify-restored')) {
    const original=JSON.parse(await readFile(option('--original-snapshot'),'utf8'));
    assert.equal(original.target.device_id,input.device);
    const saved=original.config.config;
    assert.equal(saved.enabled,false,'this cleanup only restores originally disabled schedules');
    assert.equal(await cdp.evaluate('snapshot.job.output_active'),false);
    if(!args.includes('--verify-restored')) {
    if(await cdp.evaluate(`writeState!=='ready'`)){await click('read-saved');await click('review-saved');}
    await cdp.evaluate(`{const f=document.getElementById('config').elements;f.enabled.checked=false;f.enabled.dispatchEvent(new Event('input',{bubbles:true}));f.schedules.value=${JSON.stringify(saved.schedules.map(s=>s.period_s+' / '+s.phase_s).join('\n'))};f.schedules.dispatchEvent(new Event('input',{bubbles:true}));f.expiry.value=${JSON.stringify(saved.expires_utc_s?new Date(saved.expires_utc_s*1000).toISOString().slice(0,19):'')};f.expiry.dispatchEvent(new Event('input',{bubbles:true}));document.getElementById('config').requestSubmit();}`);
    await until(()=>cdp.evaluate('!busy'),'original schedule draft');await click('apply-progress');await click('refresh');
    if(await cdp.evaluate('snapshot.standalone.reboot_required'))await restart();
    }
    await click('refresh');
    const final=await cdp.evaluate(`(async()=>({config:(await api('config')).data.config,status:snapshot.standalone}))()`);
    for(const key of ['enabled','schedules','expires_utc_s'])assert.deepEqual(final.config[key],saved[key]);
    const pins=p=>({amplifier_active_high:true,indicator_active_high:true,...p});
    assert.deepEqual(pins(final.config.pins),pins(saved.pins));
    assert.equal(final.status.output_active,false);assert.equal(final.status.suspended,false);assert.equal(final.status.reboot_required,false);
    evidence.result='PASS';await record(args.includes('--verify-restored') ? 'PASS original schedule readback; no settings changed' : 'PASS original schedules restored through browser Save and Apply',{enabled:final.config.enabled,schedules:final.config.schedules,expires_utc_s:final.config.expires_utc_s,pins:final.config.pins,gpio_drive_ma:final.status.gpio_drive_ma,rf_image:'pio-dma-gp2'});
  } else {
  if(args.includes('--time-server') && await cdp.evaluate('snapshot.network.ntp_server')!==option('--time-server')) {
    await cdp.evaluate(`document.getElementById('wifi-host-link').click()`);
    await field('consumer-password',input.password);await field('consumer-time-server',option('--time-server'));
    await cdp.evaluate(`document.getElementById('consumer-network-form').requestSubmit()`);await finishSetup();
    await record('local reference time server saved and verified');
    await cdp.evaluate(`document.getElementById('station-link').click()`);
  }
  if(await cdp.evaluate(`writeState!=='ready'`)){await click('read-saved');await click('review-saved');}
  if(!args.includes('--resume')) {
    for(const [id,value] of [['consumer-callsign',input.station.callsign],['consumer-locator',input.station.locator],['consumer-power',String(input.station.power_dbm)]])await field(id,value);
    await cdp.evaluate(`document.getElementById('consumer-station-form').requestSubmit()`);await until(()=>cdp.evaluate('!busy'),'station draft');
    await click('apply-station-progress');await finishSetup();
  }
  await record(args.includes('--resume') ? 'existing applied station read back' : 'station saved and applied');
  await click('standalone-frequency-read');
  if(!args.includes('--resume')) {
    assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),'');
    await field('standalone-frequency',String(dial));await click('standalone-frequency-save');
  }
  assert.equal(await cdp.evaluate('writeState'),'ready');assert.equal(await cdp.evaluate(`document.getElementById('save-config').disabled`),false);
  await click('standalone-frequency-read');assert.equal(await cdp.evaluate(`document.getElementById('standalone-frequency').value`),String(dial));
  await record('first dial saved; schedule controls remain usable');
  await click('refresh');
  if(await cdp.evaluate('snapshot.standalone.reboot_required || snapshot.standalone.suspended'))await restart();
  // Wait for the device's own admissible clock, never infer it from login.
  const clockDeadline=Date.now()+240000;
  while(Date.now()<clockDeadline){await click('refresh');if(await cdp.evaluate(`snapshot.standalone.clock_state==='synchronized' && BigInt(snapshot.standalone.uncertainty_ns)<=BigInt(capabilities.wtp.maximum_arm_uncertainty_ns)`))break;await pause(3000);}
  assert.equal(await cdp.evaluate(`snapshot.standalone.clock_state==='synchronized' && BigInt(snapshot.standalone.uncertainty_ns)<=BigInt(capabilities.wtp.maximum_arm_uncertainty_ns)`),true,'real clock must permit ARM');
  assert.equal(await cdp.evaluate('snapshot.standalone.reboot_required'),false);
  const phase=args.includes('--phase') ? Number(option('--phase')) : 0;
  const periodSeconds=args.includes('--period') ? Number(option('--period')) : 240;
  assert.ok([120,240].includes(periodSeconds) && [0,120].includes(phase) && phase<periodSeconds);
  const now=BigInt(await cdp.evaluate('snapshot.standalone.utc_now_ns')),period=BigInt(periodSeconds)*1000000000n;
  let start=now/period*period+BigInt(phase)*1000000000n+1000000000n;if(start-now<30000000000n)start+=period;
  const expiry=Number(start/1000000000n)+116;
  await cdp.evaluate(`{const f=document.getElementById('config').elements;f.schedules.value=${JSON.stringify(periodSeconds+' / '+phase)};f.schedules.dispatchEvent(new Event('input',{bubbles:true}));f.expiry.value=${JSON.stringify(new Date(expiry*1000).toISOString().slice(0,19))};f.expiry.dispatchEvent(new Event('input',{bubbles:true}));}`);
  await cdp.evaluate(`document.getElementById('config').requestSubmit()`);await until(()=>cdp.evaluate('!busy'),'schedule draft');await click('apply-progress');
  await cdp.evaluate(`{const e=document.getElementById('config').elements.enabled;e.checked=true;e.dispatchEvent(new Event('input',{bubbles:true}));document.getElementById('config').requestSubmit();}`);await until(()=>cdp.evaluate('!busy'),'enable draft');await click('apply-progress');await click('refresh');
  assert.equal(await cdp.evaluate('snapshot.standalone.enabled'),true);assert.equal(await cdp.evaluate('snapshot.standalone.suspended'),false);
  if(await cdp.evaluate('snapshot.standalone.reboot_required'))await restart();
  capture=receive(Number(start/1000000000n));
  await record('standalone RF schedule enabled',{start_utc:new Date(Number(start/1000000n)).toISOString(),expires_utc:new Date(expiry*1000).toISOString(),period_s:periodSeconds,phase_s:phase,dial_hz:dial,center_hz:dial+1500});
  let sawArmed=false,sawRunning=false,sawRf=false,completed=false;
  const end=expiry*1000+20000;
  while(Date.now()<end){
    const s=await status();
    if(!s){await pause(1000);continue;}
    if(s.job.state==='armed' && !sawArmed){sawArmed=true;await record('real Pico WSPR armed',{job:s.job.job_id});}
    if(s.job.state==='running'){sawRf ||= s.job.output_active===true;if(!sawRunning){sawRunning=true;await record('real Pico WSPR running',{job:s.job.job_id,output_active:s.job.output_active,clock_uncertainty_ns:s.standalone.uncertainty_ns});}}
    if(sawRunning && s.job.state==='complete'){completed=true;await record('real Pico WSPR complete',{job:s.job.job_id,output_active:s.job.output_active});break;}
    if(['failed','missed','aborted'].includes(s.job.state))throw Error('Physical job ended '+s.job.state);
    await pause(1000);
  }
  assert.ok(sawArmed && sawRunning && sawRf && completed,'physical armed/running/active/completion must all be observed');
  await capture.done;
  evidence.result='PASS';await record('PASS real first WSPR transmission',{rf_inhibited:false,automatic_retries:0});
  }
} catch(error){evidence.result='FAIL';evidence.error=error.message;if(cdp?.ws.readyState===1)evidence.ui=await cdp.evaluate(`({notice:document.getElementById('notice')?.textContent,setup:document.getElementById('consumer-save-status')?.textContent,login:document.getElementById('local-status')?.textContent,writeState,authenticated:localAuthenticated})`).catch(()=>null);await record('FAIL',{error:error.message});process.exitCode=1;}
finally {if(cdp?.ws.readyState===1)await cdp.evaluate('radio?.logout()').catch(()=>{});cdp?.ws.close();await cleanupUiProcesses([chrome],profile,{processGroup:true});}
