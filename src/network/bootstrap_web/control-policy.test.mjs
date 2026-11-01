import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const control=require('../web/control-contract.js');
const gpio=require('../web/gpio-drive.js');
const timing=require('../web/amplifier-timing.js');
const target={scope:'member',device_id:'a'.repeat(32),boot_id:'b'.repeat(32)};
const node=()=>({value:'',disabled:false,hidden:false,textContent:'',options:[],listeners:{},setAttribute(){},addEventListener(name,fn){this.listeners[name]=fn;}});
test('advertised GPIO subset disables unsupported edits before any request',async()=>{
 const fields=Object.fromEntries(['select','read','save','discard','status'].map(k=>[k,node()]));
 fields.select.options=[2,4,8,12].map(v=>({value:String(v),disabled:false}));let writes=0;
 const value={schema:'gpio-drive',target,saved:4,boot_active:4,pad_readback:null,pending_restart:false,application_error:null,rf_gp:2,execution_engine:'pio',storage_healthy:true};
 const view=gpio.create({...fields,exchange:async method=>{if(method!=='GET')writes++;return {data:value,revision:'"r"'};}});
 const admitted={...control.descriptors.gpio_drive,values:[2,4],default:2};assert(gpio.supported(admitted));
 view.setPolicy(admitted);view.setAvailability(true);await view.load();
 assert.equal(fields.select.options.find(v=>v.value==='8').disabled,true);
 fields.select.value='8';fields.select.listeners.change();assert.equal(fields.save.disabled,true);await fields.save.listeners.click();assert.equal(writes,0);
 fields.select.value='2';fields.select.listeners.change();assert.equal(fields.save.disabled,false);
 view.setPolicy({...admitted,values:[16],default:16});assert.equal(fields.save.disabled,true);
});
test('advertised timing limits constrain bounds and block otherwise physical values',async()=>{
 const fields=Object.fromEntries(['lead','tail','read','save','discard','adopt','status'].map(k=>[k,node()]));let writes=0;
 const value={schema:'amplifier-timing',target,saved:{lead_ms:200,tail_ms:200},boot_active:{lead_ms:200,tail_ms:200},pending_restart:false,phase:'inactive',output_active:false,rf_active:false,storage_healthy:true};
 const view=timing.create({...fields,exchange:async method=>{if(method!=='GET')writes++;return {data:value,revision:'"r"'};}});
 const admitted={...control.descriptors.amplifier_timing,minimum:100,maximum:300,default_lead_ms:150,default_tail_ms:150};assert(timing.supported(admitted));
 view.setPolicy(admitted);view.setAvailability(true);await view.load();assert.equal(fields.lead.min,'100');assert.equal(fields.tail.max,'300');
 fields.lead.value='99';fields.lead.oninput();assert.equal(fields.save.disabled,true);await fields.save.onclick();assert.equal(writes,0);
 fields.lead.value='250';fields.lead.oninput();assert.equal(fields.save.disabled,false);
 view.setPolicy({...admitted,minimum:500,maximum:300});assert.equal(fields.save.disabled,true);
});
const wtpCaps=()=>({profiles:['rf-events/1'],modes:['wspr','tone'],engine:'test',frequency_ranges:[{minimum_nhz:'100000000000000',maximum_nhz:'30000000000000000'}],max_payload_bytes:65536,max_events:512,max_job_duration_ns:'3600000000000',minimum_arm_lead_ns:'1000000',maximum_arm_ahead_ns:'300000000000',maximum_arm_uncertainty_ns:'500000000',maximum_holdover_age_ns:'3600000000000',output_disable_timeout_ns:'50000000',minimum_lease_ms:5000,maximum_lease_ms:60000,response_cache_entries:8,response_cache_ttl_seconds:300,terminal_record_entries:8,terminal_record_ttl_seconds:3600});
test('capabilities reject closed-root and nested WTP drift while allowing explicit boolean feature extensions',()=>{
 const features=Object.fromEntries(['config','schedules','jobs','network','application','station','hardware','consumer_setup_identity','softap','ble','restart'].map(k=>[k,true]));
 const base={contract:control.contract,wtp:wtpCaps(),features,application_resources:control.descriptors.application_resources,configuration_updates:control.descriptors.configuration_updates,management_carriers:control.descriptors.management_carriers,active_job_connections:false,max_network_connections:2,max_wtp_connections:1,max_pending_connections:1,max_handshakes:1,max_body_bytes:32768};
 assert.equal(control.validCapabilities(base),true);
 assert.equal(control.validCapabilities({...base,features:{...features,future_feature:true}}),true);
 for(const patch of [{extra:true},{contract:'Wsprry-Control/2'},{max_network_connections:33},{features:{...features,'bad/name':true}},{features:{...features,future_feature:'true'}},{wtp:{...wtpCaps(),extra:true}},{wtp:{...wtpCaps(),max_events:'512'}},{wtp:{...wtpCaps(),frequency_ranges:[{minimum_nhz:'300',maximum_nhz:'100'}]}}])assert.equal(control.validCapabilities({...base,...patch}),false,JSON.stringify(patch));
 for(const name of ['features','application_resources','configuration_updates','management_carriers']){const missing={...base};delete missing[name];assert.equal(control.validCapabilities(missing),false,name);}
});
