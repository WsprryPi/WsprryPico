'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname,'..');
const amplifier = require('../src/network/web/amplifier-enable.js');
const schema = JSON.parse(fs.readFileSync(path.join(root,'engineering/protocol/control-1.schema.json'))).$defs['amplifier-enable'];
const descriptor = Object.fromEntries(Object.entries(schema.properties).filter(([k])=>k!=='contract').map(([k,v])=>[k,v.const ?? v.enum?.[0] ?? null]));
descriptor.default_active_high = true;
assert(amplifier.supported(descriptor));
assert(amplifier.supported({...descriptor,execution:'inhibited_inactive_only'}));
for (const value of [undefined,null,{}, {...descriptor,activation:'immediate'}, {...descriptor,execution:'physical_verified'}, {...descriptor,unknown:1}]) assert(!amplifier.supported(value));
for (const key of Object.keys(descriptor)) {
  const missing = {...descriptor}; delete missing[key]; assert(!amplifier.supported(missing));
}
const body = {schema:'progress',target:{device_id:'a'.repeat(32)},fields:{pins:{amplifier_gp:18,amplifier_active_high:false}}};
assert.equal(amplifier.select,undefined,'canonical control must not select a historical route');
const context = {globalThis:{}};
vm.runInNewContext(fs.readFileSync(path.join(root,'src/network/web/saved-progress.js'),'utf8'),context);
const valid = context.globalThis.WsprryPicoSavedProgress.valid;
// Use actual API output when the CTest driver argument is supplied.
if (process.argv[2]) {
  const {execFileSync} = require('node:child_process');
  const samples = execFileSync(process.argv[2],['--samples'],{encoding:'utf8'}).trim().split('\n').map(JSON.parse);
  const sample = samples.find(v=>v.schema === 'progress');
  assert.equal(sample.contract,'Wsprry-Control/1');
  delete sample.contract;
  assert(valid(sample));
  const pins = samples.find(v=>v.schema === 'hardware').saved;
  sample.fields.pins = pins;
  assert(valid(sample));
  for (const bad of [null,0,1,'false',[],{}]) {
    const copy = structuredClone(sample); copy.fields.pins.amplifier_active_high = bad;
    assert(!valid(copy));
  }
  const conflict = structuredClone(sample); conflict.fields.pins.amplifier_gp = conflict.fields.pins.rf_gp;
  assert(!valid(conflict));
  const old = structuredClone(sample); old.schema = 'progress'; delete old.apply_domains.drive;
  assert(!valid(old));
}
console.log('Amplifier browser capability negotiation, target-preserving routes and actual draft readback passed');
(async () => {
  const {fixture} = require('./network_browser_tests.js');
  const f = await fixture();
  f.context.WsprryAmplifier = amplifier;
  f.context.amplifierDescriptor = descriptor;
  vm.runInContext('capabilities={amplifier_enable:amplifierDescriptor}; pinChoices={eligible_gps:[2,14,18,19],i2c_pairs:[]}; fillPins({rf_gp:2,button_gp:14,amplifier_gp:18,amplifier_active_high:false,indicator:"onboard_led",indicator_gp:null,indicator_active_high:true})',f.context);
  assert.equal(f.form.amplifier_gp.value,'18');
  assert.equal(f.form.amplifier_active_high.value,'false');
  assert.equal(f.form.amplifier_gp.disabled,false);
  assert.equal(f.form.rf_gp.options.find(v=>v.value==='18').disabled,true);
  const plan = vm.runInContext('readPins()',f.context);
  assert.equal(plan.amplifier_gp,18);
  assert.equal(plan.amplifier_active_high,false);
  const originalFetch = f.context.fetch;
  let selectedPath;
  f.context.fetch = async (route,options) => {
    selectedPath = route;
    if (route === '/api/control/v1/config') return {ok:true,json:async()=>({contract:'Wsprry-Control/1',config:f.config}),headers:{get:()=> '"revision"'}};
    return originalFetch(route,options);
  };
  await vm.runInContext('api("config")',f.context);
  assert.equal(selectedPath,'/api/control/v1/config');
  vm.runInContext('capabilities={};lockPins()',f.context);
  assert.equal(f.form.amplifier_gp.disabled,true);
  assert.equal(f.form.amplifier_active_high.disabled,true);
  console.log('Shipped pin editor: independent polarity, overlap lockouts, disabled older firmware and negotiated API route passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
