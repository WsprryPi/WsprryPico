// SPDX-License-Identifier: MIT
'use strict';
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
require('../src/network/web/control-contract.js');
require('../src/network/web/si5351.js');
const gps=require('../src/network/web/gps.js');
const sample=JSON.parse(execFileSync(process.argv[2],{encoding:'utf8'}));
assert(gps.readback(sample,sample.target));
assert(sample.runtime.time_valid && sample.runtime.position_valid);
assert.equal(sample.runtime.position.locator,'EM39AA');
for(const key of Object.keys(sample.saved)){
 const bad=structuredClone(sample.saved);delete bad[key];assert(!gps.valid(bad),key);
}
for(const [key,value] of Object.entries({rx_gp:2,pps_gp:1,tx_gp:0,baud:4800,receiver:'guess',pps_offset_ns:500000001,utc_second_offset:2,maximum_message_delay_ms:1000,minimum_message_delay_ms:801,receiver_uncertainty_us:0,location:'auto',calibration_maximum_age_s:86401}))
 assert(!gps.valid({...sample.saved,[key]:value}),key);
assert(!gps.valid({...sample.saved,enabled:false,location:'gps'}));
assert(!gps.valid({...sample.saved,pairing_qualified:false,automatic_rf_calibration:true}));
assert(gps.valid({...sample.saved,receiver:'e108',tx_gp:0}));
assert(!gps.valid({...sample.saved,receiver:'e108',tx_gp:4}));
const pins={engine:'direct',rf_gp:2,button_gp:14,amplifier_gp:null,lpf_gps:[],indicator:'external',indicator_gp:17};
assert(gps.allocation(sample.saved,pins,null));
assert(!gps.allocation(sample.saved,{...pins,button_gp:3},null));
assert(!gps.allocation(sample.saved,pins,null,[{gp:1}]));
assert(!gps.valid({...sample.saved,pps_gp:6}));
const si={reference_hz:25000000,reference_source:'external_xa',crystal_load_pf:null,address:96,drive_ma:8,transmit_output:0,loopback_output:2,loopback_input_gp:7,rf_gate_gp:null,rf_gate_active_high:true,reference_use:'measurement_only',trusted_uncertainty_ppb:null,manual_correction_ppb:0,automatic_calibration:false};
const i2c={...pins,engine:'i2c',rf_gp:null,i2c_pair:1};
assert(gps.allocation(sample.saved,i2c,si));
assert(!gps.allocation(sample.saved,i2c,{...si,loopback_input_gp:19}));
for(const change of [v=>delete v.runtime.age_ns,v=>v.extra=true,v=>v.runtime.extra=true,v=>v.runtime.position_valid=false,v=>v.runtime.time_valid='true',v=>v.runtime.observation_raw_ns='01',v=>v.runtime.age_ns='18446744073709551616',v=>v.runtime.position.locator='ZZ99AA',v=>v.contract='Wsprry-Control/2']) {
 const bad=structuredClone(sample);change(bad);assert(!gps.readback(bad,sample.target));
}
for(const change of [v=>delete v.runtime.capture_error_bound_ns,
 v=>v.runtime.maximum_irq_latency_ns='0',v=>v.runtime.capture_error_bound_ns='0',
 v=>v.runtime.capture_rejections=-1,v=>v.runtime.irq_latency_ns='4294967296']) {
 const bad=structuredClone(sample);change(bad);assert(!gps.readback(bad,sample.target));
}
assert(!gps.readback(sample,{...sample.target,boot_id:'0'.repeat(32)}));
for(const change of [v=>v.boot_active=null,v=>v.boot_active.enabled=false,
 v=>v.boot_active.pairing_qualified=false,v=>v.storage_healthy=false,
 v=>v.runtime.position.age_ns=String((v.boot_active.position_maximum_age_s+1)*1000000000)]) {
 const bad=structuredClone(sample);change(bad);assert(!gps.readback(bad,sample.target));
}
const calibration={oscillator_error_ppb:10000,uncertainty_ppb:500,observed_raw_ns:'1000000000',age_ns:'0',span_ns:'10000000000',generation:'1',fresh:true};
assert(gps.validCalibration(calibration));
assert(!gps.validCalibration({...calibration,uncertainty_ppb:100002}));
assert(gps.validCalibration({...calibration,uncertainty_ppb:100002,fresh:false}));
assert(!gps.validCalibration({...calibration,generation:'0'}));
assert(!gps.validCalibration({...calibration,age_ns:'18446744073709551615'}));
console.log('Production GPS resource and adapter: closed fields, units, pin conflicts, quality and identity checks passed');
