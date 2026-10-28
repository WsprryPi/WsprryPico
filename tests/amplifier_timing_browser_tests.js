'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),api=require('../src/network/web/amplifier-timing.js');
const schema=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../engineering/protocol/transmitter-amplifier-timing-1.schema.json'),'utf8'));
const descriptor=Object.fromEntries(Object.entries(schema.properties).map(([k,v])=>[k,v.const]));
assert(api.supported(descriptor));
for(const change of [{maximum:1001},{schema:'transmitter-amplifier-timing/2'},{extra:0},{activation:'next_job'}])assert(!api.supported({...descriptor,...change}));
for(const value of ['-1','1.5','1e2','Infinity','NaN','0200','1001',''])assert.equal(api.number(value),null);
(async()=>{
 const node=()=>({value:'',textContent:'',disabled:false,hidden:false,setAttribute(){}});
 const fields=Object.fromEntries(['lead','tail','read','save','discard','adopt','status'].map(k=>[k,node()]));
 let v={schema:descriptor.schema,target:{scope:'member',device_id:'a'.repeat(32),boot_id:'b'.repeat(32)},saved:{lead_ms:200,tail_ms:200},boot_active:{lead_ms:200,tail_ms:200},phase:'inactive',pending_restart:false,output_active:false,rf_active:false,storage_healthy:true};
 let fail=false,puts=0,revision='"1"',delayed=null;
 const editor=api.create({...fields,exchange:async(method,body)=>{
   if(method==='PUT'){++puts;if(fail)throw Error('Lost reply');v={...v,saved:body.timing,pending_restart:true};revision='"2"';}
   if(delayed)return delayed;
   return {data:structuredClone(v),revision};
 }});
 editor.setAvailability(true);await editor.load();assert.equal(fields.lead.value,'200');
 fields.lead.value='350';fields.lead.oninput();assert.equal(fields.save.disabled,false);
 fail=true;await fields.save.onclick();assert.equal(fields.lead.value,'350');assert.equal(fields.save.disabled,true);assert.match(fields.status.textContent,/Read saved timing/);
 fail=false;await editor.load();assert.equal(fields.lead.value,'350');assert.equal(fields.save.disabled,false);
 await fields.save.onclick();assert.deepEqual(v.saved,{lead_ms:350,tail_ms:200});assert.match(fields.status.textContent,/Amplifier timing saved/);
 fields.tail.value='400';fields.tail.oninput();v.target.boot_id='c'.repeat(32);await editor.load();assert.equal(fields.tail.value,'400');assert.equal(fields.save.disabled,true);assert.equal(fields.adopt.hidden,false);
 fields.adopt.onclick();assert.equal(fields.save.disabled,false);
 fields.tail.value='1001';fields.tail.oninput();assert.equal(fields.save.disabled,true);
 const count=puts;await fields.save.onclick();assert.equal(puts,count);
 let resolve;delayed=new Promise(r=>resolve=r);const pending=editor.load();editor.invalidate();resolve({data:v,revision});await pending;assert.equal(fields.save.disabled,true);
 assert(!api.valid({...v,extra:true}));assert(!api.valid({...v,phase:'lead',output_active:false}));assert(!api.valid({...v,phase:'tail',rf_active:true}));
 console.log('Amplifier timing negotiation, input validation, lost reply, draft identity and stale response checks passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
