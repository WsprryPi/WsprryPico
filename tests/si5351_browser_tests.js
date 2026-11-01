// SPDX-License-Identifier: MIT
'use strict';
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const si=require('../src/network/web/si5351.js');
const sample=JSON.parse(execFileSync(process.argv[2],['--samples'],{encoding:'utf8'}));
assert(si.readback(sample,sample.target));
assert(si.valid(sample.saved));
for(const key of Object.keys(sample.saved)) {
  const missing=structuredClone(sample.saved);delete missing[key];assert(!si.valid(missing),key);
}
for(const [key,value] of Object.entries({address:97,transmit_output:2,loopback_output:0,reference_hz:'25000000',crystal_load_pf:8,loopback_input_gp:6,automatic_calibration:true,trusted_uncertainty_ppb:100})) {
  assert(!si.valid({...sample.saved,[key]:value}),key);
}
const none={...sample.saved,loopback_output:null,loopback_input_gp:null};assert(si.valid(none));
const zero={...sample.saved,transmit_output:1,loopback_output:0};assert(si.valid(zero));
const plan={engine:'i2c',rf_gp:null,i2c_pair:1,button_gp:14,amplifier_gp:null,lpf_gps:[],indicator:'onboard_led',indicator_gp:null};
assert(si.allocation(sample.saved,plan));
assert(!si.allocation(sample.saved,{...plan,i2c_pair:7}));
assert(!si.allocation(sample.saved,plan,[{gp:7}]));
assert(si.allocation(sample.saved,plan,[{gp:12}]));
assert(!si.readback(sample,{...sample.target,boot_id:'0'.repeat(32)}));
const altered=structuredClone(sample);altered.runtime.clock_reference_state='gps';assert(!si.readback(altered,sample.target));
altered.runtime.clock_reference_state='none';altered.runtime.reference_measurement.age_ns='30000000001';assert(!si.readback(altered,sample.target));
assert(!si.readback({...sample,contract:'Wsprry-Control/2'},sample.target));
console.log('Shared Si5351 browser validation: explicit None/CLK0, types, allocations, age and bindings passed');
