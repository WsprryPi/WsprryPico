// SPDX-License-Identifier: MIT
'use strict';
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
require('../src/network/web/control-contract.js');
const si=require('../src/network/web/si5351.js');
const sample=JSON.parse(execFileSync(process.argv[2],['--samples'],{encoding:'utf8'}));
assert(si.readback(sample,sample.target));
assert(si.valid(sample.saved));
for(const key of Object.keys(sample.saved)) {
  const missing=structuredClone(sample.saved);delete missing[key];assert(!si.valid(missing),key);
}
for(const [key,value] of Object.entries({address:97,transmit_output:2,loopback_output:0,reference_hz:'25000000',crystal_load_pf:8,loopback_input_gp:6,automatic_calibration:'true',trusted_uncertainty_ppb:100})) {
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
for (const value of [null, 0, '18446744073709551616', '-1', '01']) {
  const bad=structuredClone(sample);bad.runtime.clock_reference_age_ns=value;assert(!si.readback(bad,sample.target));
}
const missingAge=structuredClone(sample);delete missingAge.runtime.clock_reference_age_ns;assert(!si.readback(missingAge,sample.target));
const noReferenceAge=structuredClone(sample);noReferenceAge.runtime.clock_reference_state='none';noReferenceAge.runtime.clock_reference_observed_raw_ns='0';noReferenceAge.runtime.clock_reference_age_ns='1';assert(!si.readback(noReferenceAge,sample.target));
const retained=structuredClone(sample.runtime);retained.reference_measurement=null;retained.clock_reference_state='expired';retained.clock_reference_observed_raw_ns='1';retained.clock_reference_age_ns='110592000000';assert(si.validRuntime(retained),'full WSPR capture gap retains a reportable rate age');
retained.clock_reference_age_ns='18446744073709551615';assert(!si.validRuntime(retained),'reject raw timestamp plus age overflow');

console.log('Shared Si5351 browser validation: explicit None/CLK0, types, allocations, age and bindings passed');

for (const qualification of [{}, {profile_id:'other'}, {profile_id:'qrp-labs-rev6-25mhz-clk0-8ma',system_clock_hz:138000000,i2c_pair:1}]) {
  assert(!si.readback({...sample,qualification},sample.target));
  assert(!si.readback({...sample,physically_qualified:true,qualification},sample.target));
}
assert(!si.readback({...sample,execution_engine:'si5351'},sample.target));
assert.match(si.executionDescription({physically_qualified:true,runtime:{engineering_enabled:false}}), /Qualified hardware profile; ordinary firmware/);
assert.match(si.executionDescription({physically_qualified:true,runtime:{engineering_enabled:true}}), /Qualified hardware profile; engineering firmware/);
assert.match(si.executionDescription({physically_qualified:false,runtime:{engineering_enabled:true}}), /unqualified hardware profile/);
assert.match(si.executionDescription({physically_qualified:false,runtime:{engineering_enabled:false}}), /Match the qualified setup or use engineering firmware/);

const control=globalThis.WsprryControl;
const descriptor=structuredClone(control.descriptors.si5351);
assert.equal(si.profileDescription({...descriptor.ordinary_profile,qualified:false}),'');
const profileText=si.profileDescription({...descriptor.ordinary_profile,qualified:true});
for(const term of ['QRP Labs Rev. 6','25 MHz TCXO into XA','SDA GP4 / SCL GP5','CLK0 at 8 mA','None or CLK2 to GP7','Independent RF gate: None wired','138 MHz']) assert(profileText.includes(term),term);
const ordinary=JSON.parse(execFileSync(process.argv[2],['--qualified-samples'],{encoding:'utf8'}));
assert(si.readback(ordinary,ordinary.target),'actual producer ordinary-profile readback');
assert.equal(ordinary.physically_qualified,descriptor.ordinary_profile.qualified);
assert.equal(ordinary.runtime.engineering_enabled,false);
if (ordinary.physically_qualified) {
  assert.equal(ordinary.execution_engine,'si5351');
  for(const change of [v=>v.qualification.profile_id='other',v=>v.qualification.system_clock_hz=132000000,v=>v.qualification.i2c_pair=0,v=>v.boot_active.drive_ma=4,v=>v.runtime.engineering_enabled=true]) {
    const bad=structuredClone(ordinary);change(bad);assert(!si.readback(bad,bad.target),'qualification mismatch refused');
  }
} else assert.equal(ordinary.execution_engine,'si5351-inhibited');
const sorted=Object.fromEntries(Object.entries(descriptor.ordinary_profile).sort(([a],[b])=>a.localeCompare(b)));
assert(control.supported('si5351',{...descriptor,ordinary_profile:sorted}),'JSON object key order is not semantic');
for(const profile of [{...sorted,extra:true},{...sorted,drive_ma:4},{...sorted,system_clock_hz:'138000000'},{...sorted,frequency_points_hz:[...sorted.frequency_points_hz].reverse()}])
  assert(!control.supported('si5351',{...descriptor,ordinary_profile:profile}),'closed profile values and array order remain exact');

for(const family of [{...descriptor.vhf_pll_family,extra:true},{...descriptor.vhf_pll_family,denominator_span_maximum:4096},{...descriptor.vhf_pll_family,common_p1:false}]) assert(!control.supported('si5351',{...descriptor,vhf_pll_family:family}),'VHF family limits remain exact');
