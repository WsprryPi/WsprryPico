'use strict';
const assert = require('node:assert/strict');
const {frequency,supported,create} = require('../src/network/web/standalone-frequency.js');
const element = value => ({value,disabled:false,hidden:false,textContent:'',setAttribute(){}});
for (const value of ['', '0', '1e7', '14097100.0', '14,097,100', '-1', '014097100', ' 14097100', '74999995']) assert.equal(frequency(value),null);
assert.equal(frequency('14097100'),14097100);
assert.equal(supported({schema:'transmitter-standalone-frequency/1',path:'/api/v1/standalone-frequency',method:'PUT',units:'Hz',activation:'next_job',default:null}),true);
(async()=>{
  const ui = {input:element(''),read:element(),save:element(),discard:element(),adopt:element(),status:element()};
  let saved = null, writes = 0, failure = false, target = {scope:'member',device_id:'a'.repeat(32),boot_id:'b'.repeat(32)};
  const editor = create({...ui,exchange:async(method,body,match)=>{
    if (method === 'PUT') { ++writes; assert.equal(match,'r1'); if (failure) throw Error('Lost reply'); saved = body.frequency_hz; }
    return {revision:'r1',data:{schema:'transmitter-standalone-frequency/1',target,
      frequency_hz:saved,configured:saved!==null,allowed:saved!==null,storage_healthy:true}};
  }});
  editor.setAvailability(true);
  assert.equal(ui.input.disabled,true);
  await ui.read.onclick();
  assert.equal(ui.input.value,''); assert.equal(ui.input.disabled,false); assert.equal(ui.save.disabled,true);
  assert.match(ui.status.textContent,/No standalone transmit frequency/);
  assert.equal(writes,0);
  ui.input.value = '1e7'; ui.input.oninput(); assert.match(ui.status.textContent,/whole frequency/);
  ui.input.value = '14097100'; ui.input.oninput();
  assert.doesNotMatch(ui.status.textContent,/without commas/);
  await ui.save.onclick();
  assert.equal(saved,14097100); assert.equal(writes,1);
  ui.input.value = '7040100'; ui.input.oninput(); failure = true;
  await ui.save.onclick();
  assert.equal(ui.input.value,'7040100'); assert.equal(ui.save.disabled,true);
  assert.match(ui.status.textContent,/Read the saved frequency/);
  failure = false; await ui.read.onclick(); assert.equal(ui.input.value,'7040100');
  editor.setAvailability(false); assert.equal(ui.input.disabled,true);
  target = {...target,boot_id:'c'.repeat(32)};
  editor.setAvailability(true); await ui.read.onclick();
  assert.equal(ui.save.disabled,true); assert.equal(ui.adopt.hidden,false);
  ui.adopt.onclick(); assert.equal(ui.save.disabled,false);
  ui.discard.onclick(); assert.equal(ui.input.value,'14097100'); assert.equal(ui.save.disabled,true);
  assert.match(ui.status.textContent,/draft was discarded/);
  // A late read from a disconnected device cannot reactivate its controls.
  let resolve;
  const pendingUI = {input:element(''),read:element(),save:element(),discard:element(),adopt:element(),status:element()};
  const pending = create({...pendingUI,exchange:()=>new Promise(done=>{resolve=done;})});
  pending.setAvailability(true); const loading = pendingUI.read.onclick(); pending.setAvailability(false);
  resolve({revision:'r1',data:{schema:'transmitter-standalone-frequency/1',target,
    frequency_hz:14097100,allowed:true,storage_healthy:true}});
  await loading;
  assert.equal(pendingUI.input.disabled,true); assert.equal(pendingUI.save.disabled,true);
  console.log('Standalone frequency browser checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
