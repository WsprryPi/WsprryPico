// Real HTTP/parser/AEAD sessions and clock arbiter, with deterministic monotonic time.
import assert from 'node:assert/strict';
import {Fixture} from './consumer_sessions.test.mjs';
const f=new Fixture(process.argv[2]);
try {
  await f.time(1000);
  await f.command({op:'field_clock'});
  assert.equal((await f.command({op:'field_reference',action:'sample'})).reference_state,'awaiting_utc');
  const client=f.client('192.168.4.1',true);
  await f.login(client);
  const id=await client.identity();
  const target={scope:'member',device_id:id.device_id,boot_id:id.boot_id};
  const call=async(path,method='GET',body,revision)=>{
    const r=await client.request('consumer/'+path,method,body,revision);
    const value=await r.json();
    if(r.ok) {
      assert.equal(value.contract,'Wsprry-Control/1');
      assert.deepEqual(value.target,target);
      const names=value.schema==='field-access'?['contract','schema','target','enabled','storage_healthy']:['contract','schema','target','source','clock_state','age_ns','uncertainty_ns','disagreement'];
      assert.deepEqual(Object.keys(value).sort(),names.sort());
    }
    return {status:r.status,value,revision:r.headers.get('etag')};
  };
  let field=await call('field'); assert.equal(field.status,200);assert.equal(field.value.enabled,false);assert.equal(field.value.storage_healthy,true);
  for(const patch of [{enabled:'true'},{enabled:null},{extra:1},{target:{...target,boot_id:'f'.repeat(32)}},{schema:'field-access/2'}])
    assert.equal((await call('field','PUT',{schema:'field-access',target,enabled:true,...patch},field.revision)).status,400);
  assert.equal((await call('field','PUT',{schema:'field-access',target,enabled:true},field.revision)).status,200);
  field=await call('field');assert.equal(field.value.enabled,true);
  assert.equal((await call('field','PUT',{schema:'field-access',target,enabled:false},'"wrong"')).status,412);
  let status=await call('time');assert.equal(status.value.source,'none');
  const nonce='a'.repeat(32), utc=1800000000000000000n;
  const challenge=()=>call('time/challenge','POST',{schema:'browser-time-challenge',target,nonce});
  const submit=(value=utc,patch={})=>call('time/submit','POST',{schema:'browser-time-sample',target,
    sample:{nonce,utc_ns:String(value)},...patch});
  assert.equal((await submit()).status,409,'submit without challenge');
  assert.equal((await challenge()).status,200);
  await f.time(1050);
  assert.equal((await submit()).status,200);
  status=await call('time'); assert.equal(status.value.source,'browser');
  assert.ok(BigInt(status.value.uncertainty_ns)>=300000000n);
  const observed=await client.request('status');
  const clock=(await observed.json()).standalone;
  assert.equal(clock.clock_state,'synchronized');
  assert.equal(clock.uncertainty_ns,status.value.uncertainty_ns);
  assert.equal((await submit()).status,409,'single-use challenge');
  await f.time(2000);
  const disciplined=await f.command({op:'field_reference',action:'get'});
  assert.equal(disciplined.reference_state,'selected');assert.equal(disciplined.rate_ppb,-20000);
  assert.equal(disciplined.age_ns,'950000000');
  assert.equal(BigInt(disciplined.utc_ns),utc+950000000n-19000n);
  assert.equal((await challenge()).status,200);
  await f.time(2201);assert.equal((await submit(utc+1151000000n)).status,409,'late exchange');
  await f.time(3000);assert.equal((await challenge()).status,200);
  assert.equal((await submit(utc,{extra:true})).status,400,'closed validation');
  // Another authenticated browser cannot replace a live source.
  const other=f.client('192.168.4.1',true);await f.login(other);
  const otherCall=async(path,body)=>{const r=await other.request('consumer/time/'+path,'POST',body);return r.status;};
  assert.equal(await otherCall('challenge',{schema:'browser-time-challenge',target,nonce:'b'.repeat(32)}),409,'one bounded challenge');
  await f.time(13001); // Let the unused challenge expire, then try a different source.
  assert.equal(await otherCall('challenge',{schema:'browser-time-challenge',target,nonce:'b'.repeat(32)}),200);
  await f.time(13002);
  assert.equal(await otherCall('submit',{schema:'browser-time-sample',target,sample:{nonce:'b'.repeat(32),utc_ns:String(utc+11952000000n)}}),409);
  await f.time(14000);
  assert.equal((await challenge()).status,200);
  await f.time(14001);
  assert.equal((await submit(utc+12951000000n)).status,200);
  const beforeLoss=await f.command({op:'field_reference',action:'get'});
  const lost=await f.command({op:'field_reference',action:'loss'});
  assert.equal(lost.reference_state,'expired');assert.equal(lost.rate_ppb,-20000);
  assert.equal(lost.utc_ns,beforeLoss.utc_ns);assert.equal(lost.age_ns,beforeLoss.age_ns);
  await f.time(14011);
  const removed=await f.command({op:'field_reference',action:'remove'});
  assert.equal(removed.rate_ppb,0);assert.equal(removed.reference_state,'none');
  assert.equal(removed.age_ns,'10000000');
  const recovered=await f.command({op:'field_reference',action:'sample'});
  assert.equal(recovered.reference_state,'selected');assert.equal(recovered.rate_ppb,-20000);
  assert.equal(recovered.utc_ns,removed.utc_ns);assert.equal(recovered.age_ns,removed.age_ns);

  // Time-only traffic must not renew application authentication.
  for(let ms=44000;ms<1800000;ms+=30000) {
    await f.time(ms); assert.equal((await challenge()).status,200);
    await f.time(ms+1);assert.equal((await submit(utc+BigInt(ms-1050)*1000000n+1000000n)).status,200);
  }
  await f.time(1830000);
  await assert.rejects(client.request('consumer/time'));
  console.log('PASS field persistence, revision refusal, authenticated browser source, challenge freshness/replay, source binding, closed validation, and non-renewing refresh');
} finally {f.process.stdin.end();}
