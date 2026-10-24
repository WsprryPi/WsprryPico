'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs'), vm = require('node:vm');
const {frequency,supported,create} = require('../src/network/web/standalone-frequency.js');
const element = value => ({value,disabled:false,hidden:false,textContent:'',setAttribute(k,v){this[k]=v;}});
for (const value of ['', '0', '1e7', '14095600.0', '14,095,600', '-1', '14.0956MHz', '14095600Hz', '14095600 Hz', '014095600', ' 14095600', '74998497']) assert.equal(frequency(value),null);
assert.equal(frequency('14095600'),14095600);
for (const upper of ['65999999000000000','68999999000000000','74999999000000000']) {
  const ranges=[{minimum_nhz:'100000000000000',maximum_nhz:upper}];
  assert.equal(frequency('98503',ranges),98503); assert.equal(frequency('98502',ranges),null);
  const max=Number(BigInt(upper)/1000000000n-1503n);
  assert.equal(frequency(String(max),ranges),max);assert.equal(frequency(String(max+1),ranges),null);
}
assert.equal(supported({schema:'transmitter-standalone-frequency/1',path:'/api/v1/standalone-frequency',method:'PUT',units:'Hz',activation:'next_job',default:null}),true);
(async()=>{
  const ui = {input:element(''),read:element(),save:element(),discard:element(),adopt:element(),status:element()};
  let saved = null, writes = 0, failure = false, target = {scope:'member',device_id:'a'.repeat(32),boot_id:'b'.repeat(32)};
  const editor = create({...ui,exchange:async(method,body,match,resource)=>{
    const station={callsign:'AA0NT',locator:'EM18',power_dbm:37};
    if(resource === 'station/2') return {revision:'r1',data:{schema:'transmitter-station/2',target,station,storage_healthy:true}};
    if(resource === 'progress') return {revision:'r1',data:{schema:'transmitter-progress/1',target,applied_station:station,station_complete:true}};
    if (method === 'PUT') { ++writes; assert.equal(match,'r1'); if (failure) throw Error('Lost reply'); saved = body.frequency_hz; }
    return {revision:'r1',data:{schema:'transmitter-standalone-frequency/1',target,
      frequency_hz:saved,configured:saved!==null,allowed:saved!==null,storage_healthy:true}};
  }});
  editor.setAvailability(true);
  assert.equal(ui.input.disabled,true);
  await ui.read.onclick();
  assert.equal(ui.input.value,''); assert.equal(ui.input.disabled,false); assert.equal(ui.save.disabled,true);
  assert.match(ui.status.textContent,/No WSPR dial frequency/);
  assert.equal(writes,0);
  ui.input.value = '1e7'; ui.input.oninput(); assert.match(ui.status.textContent,/whole WSPR dial frequency/);
  ui.input.value = '14095600'; ui.input.oninput();
  assert.doesNotMatch(ui.status.textContent,/without commas/);
  await ui.save.onclick();
  assert.equal(saved,14095600); assert.equal(writes,1);
  ui.input.value = '7038600'; ui.input.oninput(); failure = true;
  await ui.save.onclick();
  assert.equal(ui.input.value,'7038600'); assert.equal(ui.save.disabled,true);
  assert.match(ui.status.textContent,/Read the saved frequency/);
  failure = false; await ui.read.onclick(); assert.equal(ui.input.value,'7038600');
  editor.setAvailability(false); assert.equal(ui.input.disabled,true);
  target = {...target,boot_id:'c'.repeat(32)};
  editor.setAvailability(true); await ui.read.onclick();
  assert.equal(ui.save.disabled,true); assert.equal(ui.adopt.hidden,false);
  ui.adopt.onclick(); assert.equal(ui.save.disabled,false);
  ui.discard.onclick(); assert.equal(ui.input.value,'14095600'); assert.equal(ui.save.disabled,true);
  assert.match(ui.status.textContent,/draft was discarded/);
  // A late read from a disconnected device cannot reactivate its controls.
  let resolve;
  const pendingUI = {input:element(''),read:element(),save:element(),discard:element(),adopt:element(),status:element()};
  const pending = create({...pendingUI,exchange:()=>new Promise(done=>{resolve=done;})});
  pending.setAvailability(true); const loading = pendingUI.read.onclick(); pending.setAvailability(false);
  resolve({revision:'r1',data:{schema:'transmitter-standalone-frequency/1',target,
    frequency_hz:14095600,allowed:true,storage_healthy:true}});
  await loading;
  assert.equal(pendingUI.input.disabled,true); assert.equal(pendingUI.save.disabled,true);
  // Named first-use states: frequency validity is separate from station readiness.
  const first = {input:element(''),read:element(),save:element(),discard:element(),adopt:element(),status:element()};
  let currentTarget=null;
  let applied = false, complete = false, rev = 'r2', calls = [], failCode = '', mismatch = false;
  const station = {callsign:'AA0NT',locator:'EM18',power_dbm:37};
  const firstEditor = create({...first,context:()=>currentTarget,exchange:async(method,body,match,resource = 'standalone-frequency')=>{
    calls.push([method,resource]);
    if(method === 'PUT') { const e=Error(failCode);e.code=failCode;throw e; }
    const base = {target};
    if(resource === 'station/2') return {revision:rev,data:{...base,schema:'transmitter-station/2',station:applied?station:null,storage_healthy:true,saved_generation:'0'}};
    if(resource === 'progress') return {revision:mismatch?'old':rev,data:{...base,schema:'transmitter-progress/3',applied_station:applied?station:null,station_complete:complete}};
    return {revision:rev,data:{...base,schema:'transmitter-standalone-frequency/1',frequency_hz:null,allowed:false,storage_healthy:true}};
  }});
  firstEditor.setAvailability(true);await first.read.onclick();
  first.input.value='14095600';first.input.oninput();
  assert.equal(first.input['aria-invalid'],'false');assert.equal(first.save.disabled,true);
  assert.match(first.status.textContent,/No applied station.*Save valid station fields.*Apply/);
  await first.save.onclick();assert(!calls.some(c=>c[0]==='PUT'));
  complete=true;rev='r3';firstEditor.observeRevision(rev);await firstEditor.refresh();
  assert.match(first.status.textContent,/saved as a draft.*not applied/);assert.equal(first.save.disabled,true);
  first.input.oninput();assert.match(first.status.textContent,/saved as a draft/);
  applied=true;rev='r4';firstEditor.observeRevision(rev);await firstEditor.refresh();
  assert.equal(first.input.value,'14095600');assert.equal(first.save.disabled,false);
  assert.match(first.status.textContent,/Station settings are applied/);
  failCode='not_configured';await first.save.onclick();
  assert.match(first.status.textContent,/No applied station/);assert.doesNotMatch(first.status.textContent,/before another save/);
  assert.equal(first.input.value,'14095600');assert.equal(first.save.disabled,true);
  await first.save.onclick();assert.equal(calls.filter(c=>c[0]==='PUT').length,1,'no automatic or repeated save');
  mismatch=true;await first.read.onclick();assert.equal(first.save.disabled,true);assert.match(first.status.textContent,/changed during readback/);
  mismatch=false;await first.read.onclick();assert.equal(first.save.disabled,false);
  firstEditor.observeRevision('r5');assert.equal(first.save.disabled,true,'new revision invalidates readiness');
  currentTarget={...target,boot_id:'e'.repeat(32)};await first.read.onclick();
  assert.equal(first.save.disabled,true,'old target readback cannot enable a changed context');
  currentTarget=null;await first.read.onclick();first.discard.onclick();
  assert.doesNotMatch(first.status.textContent,/entry is preserved/,'discard must not claim retention');
  // Supersession between the first and final read cannot install readiness.
  let release;
  const prior = create({...pendingUI,exchange:()=>new Promise(done=>{release=done;})});
  prior.setAvailability(true);const late=pendingUI.read.onclick();prior.invalidate();
  release({revision:'r4',data:{schema:'transmitter-station/2',target,station,storage_healthy:true}});
  await late;
  assert.equal(pendingUI.save.disabled,true);
  // Execute the production app lifecycle: readiness refresh and explicit editor
  // requests hold the shared action lock until their final read has settled.
  const app=fs.readFileSync(require.resolve('../src/network/web/app.js'),'utf8');
  let finishRead, mutations=0;
  const environment=vm.createContext({busy:false,frequencyRefreshing:false,online:true,
    controls(){},frequencyEditor:{refresh:()=>new Promise(done=>{finishRead=done;})}});
  vm.runInContext(app.slice(app.indexOf('async function action('),app.indexOf('async function readPicoPassword(')),environment);
  const automatic=environment.action(async()=>{});await new Promise(setImmediate);
  assert.equal(vm.runInContext('busy && frequencyRefreshing',environment),true);
  await environment.frequencyAction(async()=>{++mutations;});assert.equal(mutations,0,'another request cannot overlap automatic readiness');
  finishRead();await automatic;assert.equal(vm.runInContext('busy',environment),false);
  let finishExplicit;
  const explicit=environment.frequencyAction(()=>new Promise(done=>{finishExplicit=done;}));
  await environment.action(async()=>{++mutations;});assert.equal(mutations,0,'station actions cannot overlap a frequency read/save');
  finishExplicit();await explicit;assert.equal(vm.runInContext('busy || frequencyRefreshing',environment),false);
  console.log('Standalone frequency browser checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
