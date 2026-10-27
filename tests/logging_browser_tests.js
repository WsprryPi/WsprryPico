'use strict';
const assert=require('node:assert/strict'),vm=require('node:vm');
const {fixture}=require('./network_browser_tests.js');
const run=(f,code)=>vm.runInContext(code,f.context);
(async()=>{
 const f=await fixture(true,true,false,true);
 f.elements['access-toggle'].onclick();f.elements['local-password'].value='test-password';
 await f.elements['local-login'].onsubmit({preventDefault(){}});
 for (const id of ['logging-read','logging-settings','logging-enabled','logging-severity','logging-status']) f.elements[id]={disabled:true,checked:false,value:'6',textContent:''};
 const previous=f.context.fetch;
 f.context.fetch=async(url,options)=>url.endsWith('/logging')?{ok:true,status:200,headers:{get:()=> '"logging1"'},json:async()=>({schema:'transmitter-logging/1',target:{scope:'member',device_id:'1'.repeat(32),boot_id:'a'.repeat(32)},saved:{enabled:true,maximum_severity:6},active:{enabled:true,connected:true,streaming:true,dropped:'0'}})}:previous(url,options);
 await run(f,'readLogging()');assert.equal(f.elements['logging-settings'].disabled,false);
 await f.elements['access-toggle'].onclick();
 assert.equal(f.elements['logging-settings'].disabled,true);assert.equal(f.elements['logging-read'].disabled,true);
 assert.equal(run(f,'loggingSnapshot'),null);assert.match(f.elements['logging-status'].textContent,/unconfirmed/);
 run(f,'controls(true)');assert.equal(f.elements['logging-settings'].disabled,true,'lock cannot be bypassed by status availability');
 console.log('Pico logging form retires readback and disables editing on lock/disconnect');
})().catch(error=>{console.error(error);process.exitCode=1;});
