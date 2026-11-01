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
