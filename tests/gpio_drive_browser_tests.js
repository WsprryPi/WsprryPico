// Exercise the actual editor and emitted writes without a browser or hardware.
const assert = require('node:assert/strict');
const {create,valid,supported} = require('../src/network/web/gpio-drive.js');
function element() { return {value:'',disabled:false,textContent:'',handlers:{},setAttribute(){},addEventListener(k,fn){this.handlers[k]=fn;}}; }
const observation = {schema:'transmitter-gpio-drive/1',target:{scope:'member',device_id:'a'.repeat(32),boot_id:'b'.repeat(32)},saved:4,boot_active:4,pad_readback:null,pending_restart:false,application_error:null,rf_gp:2,execution_engine:'inhibited',storage_healthy:true};
(async()=>{
 const e=Object.fromEntries(['select','read','save','discard','status'].map(k=>[k,element()]));
 let state=structuredClone(observation),version=1,fail=false; const calls=[];
 const controller=create({...e,exchange:async(method,body,revision)=>{
   calls.push({method,body,revision}); if(fail)throw new Error('disconnected');
   if(method==='PUT'){assert.equal(revision,'"'+version+'"');assert.deepEqual(body.target,state.target);state.saved=body.gpio_drive_ma;state.pending_restart=true;++version;}
   return {data:structuredClone(state),revision:'"'+version+'"'};
 }});
 assert.equal(e.select.value,'');controller.setAvailability(true);assert(e.save.disabled);
 await e.read.handlers.click();assert.equal(e.select.value,'4');assert(e.save.disabled);
 for(const value of ['2','8','12','4']) {
   e.select.value=value;e.select.handlers.change();const before=calls.length;assert(!e.save.disabled);assert.equal(calls.length,before);
   await e.save.handlers.click();assert.equal(state.saved,Number(value));assert.match(e.status.textContent,/confirmed saved/);assert(e.save.disabled);
 }
 e.select.value='8';e.select.handlers.change();fail=true;await e.save.handlers.click();assert.equal(e.select.value,'8');assert(e.save.disabled);const count=calls.length;await e.save.handlers.click();assert.equal(calls.length,count);
 fail=false;await e.read.handlers.click();assert.equal(e.select.value,'8');assert(!e.save.disabled);
 state.target.boot_id='c'.repeat(32);controller.invalidate();await e.read.handlers.click();assert(e.save.disabled);assert.equal(e.select.value,'8');
 e.discard.handlers.click();assert.equal(e.select.value,'4');e.select.value='2';e.select.handlers.change();assert(!e.save.disabled);
 controller.setAvailability(false);assert(e.save.disabled);assert.match(e.status.textContent,/unknown/);
 assert(!valid({...observation,saved:6}));assert(!valid({...observation,saved:true}));assert(!valid({...observation,extra:true}));
 console.log('GPIO drive editor: choices, emitted writes, preserved drafts, lost replies, disconnect, boot binding and malformed readback passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
(async()=>{
 const e=Object.fromEntries(['select','read','save','discard','status','saveDraft','applyDraft','draftStatus'].map(k=>[k,element()]));
 let applied=null,draft,version=1;const writes=[];
 const progress=()=>({schema:'transmitter-progress/2',target:observation.target,draft_revision:draft===undefined?'0':'1',fields:draft===undefined?{}:{gpio_drive_ma:draft},apply_domains:{drive:applied!==null}});
 const controller=create({...e,exchange:async(method,body,match,resource='gpio-drive')=>{
   if(method!=='GET'){assert.equal(match,'"'+version+'"');writes.push({resource,body});++version;
     if(resource==='progress/update/2'){draft=body.fields.gpio_drive_ma;return {data:{...progress(),request_id:body.request_id,outcomes:{gpio_drive_ma:'saved'}},revision:'"'+version+'"'};}
     assert.equal(body.application.domain,'drive');applied=draft;return {data:{config:{gpio_drive_ma:applied}},revision:'"'+version+'"'};
   }
   return {data:resource==='progress/2'?progress():{...observation,saved:applied,pending_restart:applied===8},revision:'"'+version+'"'};
 }});
 controller.setAvailability(true);await e.read.handlers.click();assert.equal(e.select.value,'');
 e.select.value='8';e.select.handlers.change();assert(!e.saveDraft.disabled);assert(e.save.disabled);assert(e.applyDraft.disabled);
 await e.saveDraft.handlers.click();assert.equal(applied,null);assert.equal(draft,8);assert.equal(e.select.value,'8');assert.equal(writes.length,1);
 applied=4;await e.read.handlers.click();assert(!e.applyDraft.disabled);await e.applyDraft.handlers.click();assert.equal(applied,8);assert.equal(writes.length,2);assert.equal(e.select.value,'8');
 console.log('GPIO drive progress editor: independent blank-member draft save and explicit domain-only application passed');
})().catch(e=>{console.error(e);process.exitCode=1;});

(async()=>{
 const e=Object.fromEntries(['select','read','save','discard','status','saveDraft','applyDraft','draftStatus'].map(k=>[k,element()]));
 let finish;
 const controller=create({...e,exchange:async(method,body,revision,resource='gpio-drive')=>{
   if(resource==='progress/2')return new Promise(resolve=>{finish=resolve;});
   return {data:structuredClone(observation),revision:'"1"'};
 }});
 controller.setAvailability(true);const pending=controller.load();await new Promise(setImmediate);
 assert.equal(typeof finish,'function');controller.invalidate();
 finish({data:{schema:'transmitter-progress/2',target:observation.target,draft_revision:'0',fields:{},apply_domains:{drive:false}},revision:'"1"'});
 await pending;assert(e.select.disabled);assert(e.save.disabled);assert(e.saveDraft.disabled);
 assert.match(e.status.textContent,/Target or saved revision changed/);
 console.log('GPIO drive editor: target change during progress read cannot revive stale authority');
})().catch(e=>{console.error(e);process.exitCode=1;});

const descriptor={schema:'transmitter-gpio-drive/1',read:'/api/v1/gpio-drive',write:'/api/v1/gpio-drive',method:'PUT',values:[2,4,8,12],default:4,units:'mA',engine:'pio',activation:'restart',config:'/api/v1/config/3',update:'/api/v1/config/update/3',update_schema:'transmitter-config-update/2',hardware:'/api/v1/hardware/2',application:'/api/v1/application/3',progress:'/api/v1/progress/2',progress_schema:'transmitter-progress/2'};
assert(supported(descriptor));assert(!supported(undefined));
for(const [key,value] of Object.entries({method:'POST',units:'ordinal',engine:'si5351',write:'/other',progress:'/api/v1/progress',extra:true}))assert(!supported({...descriptor,[key]:value}));
console.log('GPIO drive descriptor: exact engine, units, methods, versions and closed fields required');
