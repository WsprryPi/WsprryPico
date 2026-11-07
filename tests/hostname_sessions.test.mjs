// Production parser, HTTP service, authenticated Noble/Mbed TLS session and journals.
import assert from 'node:assert/strict';
import {Fixture} from './consumer_sessions.test.mjs';
const f = new Fixture(process.argv[2]);
async function call(client,...args) { const r=await client.request(...args);return {status:r.status,revision:r.headers.get('etag'),data:await r.json()}; }
try {
  await f.time(1000);
  const a=f.client(),b=f.client('192.168.4.1',true),c=f.client('wsprrypico-0a60df.local');
  await f.login(a);await f.time(2000);await f.login(b);await f.time(3000);await f.login(c);
  const identity=await a.identity();
  assert.deepEqual(Object.keys(identity).sort(),['authentication','boot_id','device_id','generation','version']);
  const original=await call(a,'config'), old=await call(a,'hostname');
  const stats=await f.command({op:'stats'});
  assert.equal(old.data.active,'wsprrypico-0a60df.local');
  const save=await call(b,'hostname','PUT',{schema:'hostname',target:old.data.target,hostname:'PICO-A.LOCAL.'},old.revision);
  assert.equal(save.status,200);assert.equal(save.data.saved,'pico-a.local');
  assert.equal(save.data.active,old.data.active);assert.equal(save.data.pending_restart,true);
  await assert.rejects(a.request('status'));await assert.rejects(c.request('status'));
  await f.time(4000);await f.login(a);
  let named=await call(a,'hostname');assert.equal(named.data.saved,'pico-a.local');
  assert.deepEqual((await call(a,'config')).data,original.data);
  const after=await f.command({op:'stats'});
  assert.equal(BigInt(after.profile_generation),BigInt(stats.profile_generation)+1n);
  assert.equal(after.config_sequence,stats.config_sequence);assert.equal(after.watermark,stats.watermark);
  assert.equal((await call(a,'hostname','PUT',{schema:'hostname',target:named.data.target,hostname:'pico-a.local'},old.revision)).status,412);
  const noOp=await call(a,'hostname','PUT',{schema:'hostname',target:named.data.target,hostname:'PICO-A.LOCAL.'},named.revision);
  assert.equal(noOp.status,200);assert.equal(noOp.data.generation,named.data.generation);
  const reboot=await call(a,'restart','POST',{},noOp.revision);assert.equal(reboot.status,202);
  assert.equal((await f.command({op:'stats'})).api_restarts,1);
  await f.command({op:'reboot'});await f.time(5000);
  const renamed=f.client('pico-a.local');await f.login(renamed);
  const current=await call(renamed,'hostname');assert.equal(current.data.active,'pico-a.local');
  assert.equal(current.data.pending_restart,false);assert.notEqual(current.data.target.boot_id,old.data.target.boot_id);
  assert.equal(current.data.target.device_id,old.data.target.device_id);
  assert.equal((await c.identity().catch(()=>null)),null); // Obsolete Host is no longer admitted.
  const presentation=await f.fetch('pico-a.local',false,'/api/consumer/v1/presentation');
  assert.equal((await presentation.json()).hostname,'pico-a.local');
  await assert.rejects(f.login(f.client('other.local')));
  const reset=await call(renamed,'hostname','PUT',{schema:'hostname',target:current.data.target,hostname:null},current.revision);
  assert.equal(reset.data.saved,'wsprrypico-0a60df.local');
  console.log('PASS hostname AP/station rename, strict identities, generations, preserved config, restart and old-authority refusal');
} finally {await f.stop();}

// The initial captive portal becomes password authenticated after Wi-Fi setup,
// without station details or a transmitter configuration journal.
const early = new Fixture(process.argv[2],['1'.repeat(32),'--blank']);
try {
  await early.time(1000);
  assert.equal((await early.fetch('192.168.4.1',true,'/api/control/v1/hostname',{method:'PUT',body:'{}'})).status,405);
  await early.command({op:'page_profile',mode:'network'});
  const ap=early.client('192.168.4.1',true);
  const generation=(await early.command({op:'stats'})).profile_generation;
  const forged=await early.fetch('192.168.4.1',true,'/api/consumer/v1/request',{
    method:'POST',body:JSON.stringify({contract:'Wsprry-Control/1',schema:'hostname',hostname:'forged.local'})});
  assert.ok(forged.status>=400 && forged.status<500);
  assert.equal((await early.command({op:'stats'})).profile_generation,generation);
  await early.login(ap);
  const original=await early.command({op:'stats'});
  assert.equal(original.config_sequence,'0');
  const first=await call(ap,'hostname');
  assert.equal(first.status,200);assert.equal(first.data.writable,true);
  assert.equal(first.data.source,'network_profile');
  for(const hostname of ['url://a.local','a.b.local','a_.local','x'.repeat(64)+'.local',42,{}]) {
    assert.equal((await call(ap,'hostname','PUT',{schema:'hostname',target:first.data.target,hostname},first.revision)).status,400);
  }
  assert.equal((await call(ap,'hostname','PUT',{schema:'hostname',target:{...first.data.target,boot_id:'b'.repeat(32)},hostname:'pico-a.local'},first.revision)).status,409);
  const saved=await call(ap,'hostname','PUT',{schema:'hostname',target:first.data.target,hostname:'PICO-A.LOCAL.'},first.revision);
  assert.equal(saved.status,200);assert.equal(saved.data.saved,'pico-a.local');
  assert.equal(saved.data.active,first.data.active);assert.equal(saved.data.pending_restart,true);
  let stats=await early.command({op:'stats'});
  assert.equal(stats.config_sequence,'0');assert.equal(stats.api_restarts,original.api_restarts);
  assert.equal(stats.watermark,original.watermark);
  await assert.rejects(ap.request('status'));
  await early.time(2000);await early.login(ap);
  assert.equal((await call(ap,'hostname','PUT',{schema:'hostname',target:first.data.target,hostname:'pico-b.local'},first.revision)).status,412);
  let readback=await call(ap,'hostname');
  // An accepted save with a lost response still consumes exactly one generation.
  const request=ap.fetcher;let drop=true;
  ap.fetcher=async(...args)=>{const response=await request(...args);if(drop&&args[0].endsWith('/request')){drop=false;throw Error('lost committed reply');}return response;};
  await assert.rejects(call(ap,'hostname','PUT',{schema:'hostname',target:readback.data.target,hostname:'pico-b.local'},readback.revision));
  ap.fetcher=request;ap.clear();await early.time(3000);await early.login(ap);
  readback=await call(ap,'hostname');assert.equal(readback.data.saved,'pico-b.local');
  assert.equal(BigInt(readback.data.generation),BigInt(first.data.generation)+2n);
  const restart=await call(ap,'restart','POST',{},readback.revision);assert.equal(restart.status,202);
  await early.command({op:'reboot'});await early.time(4000);await early.login(ap);
  readback=await call(ap,'hostname');assert.equal(readback.data.active,'pico-b.local');
  assert.equal(readback.data.pending_restart,false);assert.notEqual(readback.data.target.boot_id,first.data.target.boot_id);
  const restored=await call(ap,'hostname','PUT',{schema:'hostname',target:readback.data.target,hostname:null},readback.revision);
  assert.equal(restored.status,200);assert.equal(restored.data.saved,first.data.default);
  stats=await early.command({op:'stats'});assert.equal(stats.config_sequence,'0');
  console.log('PASS initial captive AP hostname editing before station setup, guarded writes, lost reply, explicit restart and default restoration');
} finally {await early.stop();}
