// Real Noble -> production HTTP, session manager and Mbed TLS; no hardware.
import assert from 'node:assert/strict';
import {Fixture} from './consumer_sessions.test.mjs';
import {begin,authenticate,clear,open,header} from '../src/network/bootstrap_web/radio-crypto.js';
const executable=process.argv[2];let passed=0;
async function test(name,fn){const f=new Fixture(executable);try{await f.time(1000);await fn(f);console.log('PASS '+name);passed++;}finally{await f.stop();}}
const scope=(d,target)=>({target_selector:target,authority:d.authority,interface:d.interface});
const start=async(c,d,target)=>{const p=begin();const g=await c.post('recovery/start',{version:1,device_id:d.device_id,boot_id:d.boot_id,generation:d.generation,public_key:p.public_key,nonce:p.nonce,target_selector:target},false,5000);return {p,g};};
await test('public retirement aliases cannot select ordinary traffic or consume a pending password proof',async f=>{
 const a=f.client(),stranger=f.client();await f.login(a);
 const d=await stranger.recovery();assert.notEqual(d.sessions[0].selector,a.state.session);
 const forge=(selector,sequence)=>{const p=new Uint8Array(76);p.set(header(selector,sequence));return p;};
 await assert.rejects(stranger.post('request',forge(d.sessions[0].selector,1n),true,5000));
 assert.equal((await a.request('status')).status,200);
 await f.time(2000);const identity=await stranger.identity(),p=begin();
 const g=await stranger.post('start',{version:1,device_id:identity.device_id,boot_id:identity.boot_id,generation:identity.generation,public_key:p.public_key,nonce:p.nonce},false,5000);
 const pending=(await stranger.recovery()).sessions.find(s=>s.state==='pending');assert.notEqual(pending.selector,g.session_id);
 await assert.rejects(stranger.post('finish',forge(pending.selector,0n),true,5000));
 assert.equal((await f.command({op:'stats'})).psa_owners,1);
 const s=authenticate(p,g,'test-password',identity);const ack=open(s,0n,await stranger.post('finish',s.finish,true,5000));assert.equal(ack.authenticated,true);clear(s);s.finish.fill(0);
 assert.equal((await a.request('status')).status,200);
});
await test('full active pool retirement frees only selected login; no expiry or implicit replacement',async f=>{
 const a=f.client(),b=f.client(),c=f.client();await f.login(a);await f.time(2000);await f.login(b);await f.time(3000);await f.login(c);
 const fresh=f.client(),d=await fresh.recovery(),id=a.retirementSelector;assert.equal(d.sessions.length,3);
 await assert.rejects(f.login(fresh),e=>e.code==='radio_session_capacity');
 await assert.rejects(fresh.retire('wrong-password',d,id),e=>e.code==='radio_recovery_rejected');
 for(const client of [a,b,c])assert.equal((await client.request('status')).status,200);
 await f.time(4000);const result=await fresh.retire('test-password',d,id);assert.equal(result.present,true);
 assert.equal((await fresh.recovery()).sessions.length,2);assert.equal(fresh.authenticated,false);
 await assert.rejects(a.request('status'));for(const client of [b,c])assert.equal((await client.request('config')).status,200);
 await f.login(fresh);assert.equal((await fresh.recovery()).sessions.length,3);
});
await test('lost durable-write reply retains exact public selector; one dispatch and authenticated recovery',async f=>{
 const a=f.client(),b=f.client(),c=f.client();await f.login(a);await f.time(2000);await f.login(b);await f.time(3000);await f.login(c);
 const rev=(await a.request('config')).headers.get('etag'),target=(await (await a.request('application')).json()).target;
 const old=a.retirementSelector,transport=a.fetcher;let mutations=0;
 a.fetcher=async(p,o)=>{const r=await transport(p,o);if(p.endsWith('/request')){mutations++;throw new Error('lost after durable commit');}return r;};
 await assert.rejects(a.request('config/update','POST',{schema:'transmitter-config-update/1',target,mode:'merge',config:{allow_unqualified_frequency:true}},rev));
 assert.equal(mutations,1);assert.equal(a.authenticated,false);assert.equal(a.lostSession.selector,old);
 assert.equal((await (await b.request('config')).json()).config.allow_unqualified_frequency,true);
 a.fetcher=transport;const d=await a.recovery();await a.retire('test-password',d,old);await f.time(4000);await f.login(a);
 assert.equal(mutations,1);assert.equal((await b.request('status')).status,200);assert.equal((await c.request('status')).status,200);
});
await test('lost start and finish replies recover at full ordinary pending/active quotas',async f=>{
 const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
 for(const phase of ['start','finish']){
  await f.time(f.now+1000);const c=f.client(),original=c.fetcher;
  c.fetcher=async(p,o)=>{const r=await original(p,o);if(p.endsWith('/'+phase))throw new Error('lost '+phase);return r;};
  await assert.rejects(f.login(c));c.fetcher=original;const d=await c.recovery();
  assert.equal(d.sessions.length,3);const old=d.sessions.find(s=>s.selector!==a.retirementSelector&&s.selector!==b.retirementSelector);
  assert.equal(old.state,phase==='start'?'pending':'active');
  await c.retire('test-password',d,old.selector);assert.equal((await c.recovery()).sessions.length,2);
  for(const client of [a,b])assert.equal((await client.request('status')).status,200);
 }
});
await test('retirement reply loss before and after effect is safely repeated for same nonreused selector',async f=>{
 const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);const target=a.retirementSelector,d=await b.recovery(),transport=b.fetcher;
 for(const after of [false,true]){
  b.fetcher=async(p,o)=>{if(p.endsWith('recovery/finish')){if(after)await transport(p,o);throw new Error('lost retirement');}return transport(p,o);};
  await assert.rejects(b.retire('test-password',d,target));b.fetcher=transport;
  assert.equal((await b.recovery()).sessions.some(s=>s.selector===target),!after);
  // An abandoned proof, not an ordinary session, has a five-second absolute bound.
  await f.time(f.now+5000);
 }
 const absent=await b.retire('test-password',d,target);assert.equal(absent.present,false);assert.equal((await b.request('status')).status,200);
 await f.time(f.now+1000);await f.login(a);const replacement=a.retirementSelector;assert.notEqual(replacement,target);
 await b.retire('test-password',d,target);assert.equal((await a.request('status')).status,200);
});
await test('retirement cancels only matching undelivered effects; delayed ACK/FIN/RST cannot deliver a later receipt',async f=>{
 const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);let rev=(await a.request('config')).headers.get('etag');
 f.holdNext=true;await a.request('network','PUT',{enabled:false},rev);const socket=f.socket,tx=(await f.command({op:'stats'})).transaction;
 const d=await b.recovery();await b.retire('test-password',d,a.retirementSelector);assert.equal((await f.command({op:'stats'})).network_pending,false);
 await f.command({op:'fin',socket});await f.time(3000);await f.login(a);rev=(await a.request('config')).headers.get('etag');
 f.holdNext=true;await a.request('network','PUT',{enabled:false},rev);const next=f.socket;
 await f.command({op:'delivery',tx,apply:true});assert.equal((await f.command({op:'stats'})).network_pending,true);
 await f.command({op:'rst',socket:next});assert.equal((await f.command({op:'stats'})).network_enabled,true);
 assert.equal((await b.request('status')).status,200);
});
await test('wrong scope/domain/replay, stale identity and oversized/duplicate input do not retire or refresh a peer',async f=>{
 const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);const d=await b.recovery(),target=a.retirementSelector;
 const {p,g}=await start(b,d,target);const s=authenticate(p,g,'test-password',d,scope(d,target)),packet=s.finish.slice();
 let wrong=packet.slice();wrong[wrong.length-1]^=1;await assert.rejects(b.post('recovery/finish',wrong,true,5000));
 await assert.rejects(b.post('recovery/finish',packet,true,5000));assert.equal((await a.request('status')).status,200);clear(s);
 await f.time(3000);const next=await start(b,d,target);
 assert.throws(()=>authenticate(next.p,{...next.g,recovery:{...next.g.recovery,target_selector:b.retirementSelector}},'test-password',d,scope(d,target)));
 await f.time(8000);assert.equal((await f.command({op:'stats'})).psa_owners,0);
 const publicKey=begin();const body={version:1,device_id:d.device_id,boot_id:'f'.repeat(32),generation:d.generation,public_key:publicKey.public_key,nonce:publicKey.nonce,target_selector:target};
 await assert.rejects(b.post('recovery/start',body,false,5000));body.boot_id=d.boot_id;
 const raw=await f.fetch(b.host,false,'/api/consumer/v1/recovery/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body).replace('"version":1','"version":1,"version":1')});assert.equal(raw.status,400);
 const huge=await f.fetch(b.host,false,'/api/consumer/v1/recovery/start',{method:'POST',headers:{'Content-Type':'application/json'},body:' '.repeat(641)});assert.equal(huge.status,413);
 assert.equal((await a.request('status')).status,200);assert.equal((await b.request('status')).status,200);publicKey.secret.fill(0);
});
await test('authority/interface restrictions and failed RNG preserve healthy peers and shared PSA ownership',async f=>{
 const a=f.client(),host=f.client('wsprrypico-0a60df.local'),ap=f.client('192.168.4.1',true);await f.login(a);await f.time(2000);await f.login(host);await f.time(3000);await f.login(ap);
 const d=await host.recovery();assert.equal(d.sessions.length,1);await assert.rejects(host.retire('test-password',d,a.retirementSelector));
 const ad=await a.recovery();await f.command({op:'rng',fail:true});await assert.rejects(a.retire('test-password',ad,a.retirementSelector));
 await f.command({op:'rng',fail:false});for(const client of [a,host,ap])assert.equal((await client.request('status')).status,200);
 assert.equal((await f.command({op:'stats'})).psa_owners,0);
});
await test('bounded repeated retirement/login cycles reclaim proof keys, slots and transport pages',async f=>{
 const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
 for(let i=0;i<16;i++){await b.retire('test-password',await b.recovery(),a.retirementSelector);a.clear();await f.time(f.now+1000);await f.login(a);assert.equal((await b.request('status')).status,200);}
 const stats=await f.command({op:'stats'});assert.equal(stats.psa_owners,0);assert.equal(stats.connections,0);assert.equal(stats.pending_bytes,0);assert.equal((await b.recovery()).sessions.length,2);
});
for(const after of [false,true])await test(`self-retirement reply loss ${after?'after':'before'} effect clears traffic and retains only alias`,async f=>{
 const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);const target=a.retirementSelector,d=await a.recovery(),transport=a.fetcher;
 a.fetcher=async(p,o)=>{if(p.endsWith('recovery/finish')){if(after)await transport(p,o);throw new Error('lost self-retirement');}return transport(p,o);};
 await assert.rejects(a.retire('test-password',d,target),e=>e.unconfirmed===true);assert.equal(a.authenticated,false);assert.equal(a.lostSession.selector,target);assert.equal(a.state,null);
 a.fetcher=transport;assert.equal((await b.recovery()).sessions.some(s=>s.selector===target),!after);assert.equal((await b.request('status')).status,200);
 await f.time(f.now+5000);await a.retire('test-password',d,target);assert.equal(a.lostSession,null);assert.equal((await b.request('status')).status,200);
});
console.log(`${passed} recovery scenarios passed`);
