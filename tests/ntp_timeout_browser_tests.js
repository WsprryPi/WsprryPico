const assert = require('node:assert/strict');
const {minutes,create} = require('../src/network/web/ntp-timeout.js');
for (const text of ['0','1441','01','60.5','1e2',' 60','-1','']) assert.equal(minutes(text),null);
for (const text of ['1','60','1440']) assert.equal(minutes(text),Number(text));
const element = () => ({value:'',disabled:false,hidden:false,textContent:'',attributes:{},setAttribute(k,v){this.attributes[k]=v;}});
async function main() {
  const nodes = Object.fromEntries(['input','read','save','discard','adopt','status'].map(k=>[k,element()]));
  let boot='b'.repeat(32), saved=3600, fail=false, puts=0;
  const target=()=>({scope:'member',device_id:'a'.repeat(32),boot_id:boot});
  const exchange=async (method,body,match)=>{
    if (method==='PUT') {
      ++puts; assert.ok(match); assert.deepEqual(body.target,target());
      if(fail) throw Error('Response lost');
      saved=body.timeout_s;
    }
    return {revision:'r'+saved,data:{schema:'transmitter-ntp-timeout/1',target:target(),saved_timeout_s:saved,
      active_timeout_s:3600,pending_restart:saved!==3600,storage_healthy:true}};
  };
  const editor=create({...nodes,exchange});
  editor.setAvailability(true,false);
  await nodes.read.onclick(); assert.equal(nodes.input.value,'60');
  nodes.input.value='120'; nodes.input.oninput(); assert.ok(nodes.save.disabled);
  editor.setAvailability(true,true); assert.equal(nodes.save.disabled,false);
  await nodes.save.onclick(); assert.equal(saved,7200); assert.equal(puts,1); assert.match(nodes.status.textContent,/Restart/);
  nodes.input.value='90'; nodes.input.oninput(); fail=true;
  await nodes.save.onclick(); assert.equal(puts,2); assert.ok(nodes.save.disabled); assert.equal(nodes.input.value,'90');
  assert.match(nodes.status.textContent,/Read saved timeout/);
  await nodes.save.onclick(); assert.equal(puts,2); // No blind repeat after an ambiguous write.
  fail=false; await nodes.read.onclick(); assert.equal(nodes.input.value,'90');
  boot='c'.repeat(32); editor.invalidate(); await nodes.read.onclick();
  assert.equal(nodes.input.value,'90'); assert.ok(nodes.save.disabled); assert.equal(nodes.adopt.hidden,false);
  nodes.adopt.onclick(); await nodes.save.onclick(); assert.equal(saved,5400);
  nodes.input.value='1e2'; nodes.input.oninput(); assert.ok(nodes.save.disabled); assert.equal(nodes.input.attributes['aria-invalid'],'true');
  nodes.discard.onclick(); assert.equal(nodes.input.value,'90');
  editor.setAvailability(false,false); assert.ok(nodes.read.disabled);
}
main().then(()=>console.log('NTP timeout draft, target, validation and ambiguous-write checks passed.')).catch(e=>{console.error(e);process.exitCode=1;});
