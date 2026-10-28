import {test} from 'node:test';
import assert from 'node:assert/strict';
import {x25519} from '@noble/curves/ed25519.js';
import {sha256} from '@noble/hashes/sha2.js';
import {chacha20poly1305} from '@noble/ciphers/chacha.js';
import {authenticate,begin,b64,header,hex,join,open,seal,text,transcript,retirementSelector} from './radio-crypto.js';
import {RadioClient} from './radio-client.js';
import {prepareNetwork,submitSetup,checkSetup} from './radio-setup.js';

const id={version:1,device_id:'11'.repeat(16),boot_id:'22'.repeat(16),generation:'139',authentication:'saved_wifi_passphrase'};
const privateKey=Uint8Array.from({length:32},(_,i)=>i+1);
const grant={version:1,...id,session_id:'33'.repeat(16),public_key:b64(x25519.getPublicKey(privateKey)),challenge:'44'.repeat(16),login_ms:30000};
const fixed=()=>begin(Uint8Array.from({length:32},(_,i)=>i+65),new Uint8Array(16).fill(0x55));
const vectorState=()=>authenticate(fixed(),grant,'test-only-password',id);
test('default native fetch retains its Window receiver',async()=>{
  const original=globalThis.fetch;
  try {
    globalThis.fetch=function(){assert.equal(this,globalThis);return Promise.resolve(Response.json(id));};
    assert.deepEqual(await new RadioClient().identity(),id);
  } finally {globalThis.fetch=original;}
});
function response(state,sequence,value) {
  const nonce = new Uint8Array(12); new DataView(nonce.buffer).setBigUint64(4,sequence);
  const h=header(state.session,sequence);
  return join(h,chacha20poly1305(state.keys.subarray(32),nonce,join(state.digest,h)).encrypt(text(JSON.stringify(value))));
}
test('fixed transcript, password proof, direction keys and paged-size boundaries',()=>{
  const pending=fixed(); const digest=sha256(transcript(pending,grant));
  const state=authenticate(pending,grant,'test-only-password',id);
  assert.equal(pending.secret.every(b=>b===0),true);
  assert.equal(state.digest.length,32); assert.equal(hex(state.digest),hex(digest));
  assert.notEqual(hex(state.keys.subarray(0,32)),hex(state.keys.subarray(32)));
  const value={status:200,etag:'"revision"',body:{config:{enabled:false}}};
  assert.deepEqual(open(state,1n,response(state,1n,value)),value);
  assert.throws(()=>open(state,2n,response(state,1n,value)));
  const tampered=response(state,1n,value); tampered[30]^=1;
  assert.throws(()=>open(state,1n,tampered));
  const request=seal(state,1n,{pad:'x'.repeat(32714)});
  assert.equal(request.length,32768);
  assert.throws(()=>seal(state,2n,{pad:'x'.repeat(32715)}),/limit/);
  for(const name of ['device_id','boot_id','generation']) assert.throws(()=>authenticate(fixed(),{...grant,[name]:name==='generation'?'140':'66'.repeat(16)},'test-only-password',id));
  assert.throws(()=>authenticate(fixed(),grant,'short',id));
  const other=authenticate(fixed(),grant,'different-password',id);
  assert.notEqual(hex(other.keys),hex(state.keys));
});
test('client login binds identity, never retries mutation, clears uncertain session',async()=>{
  let serverState, starts=0, mutations=0, fail=false, now=1000;
  const fetcher=async(path,options)=>{
    if(path.endsWith('identity')) return Response.json(id);
    if(path.endsWith('start')) {
      starts++; const request=JSON.parse(options.body);
      assert.equal(request.authentication,undefined);
      assert.equal(options.credentials,'omit');
      const pending={...request,secret:new Uint8Array(32)};
      // Test server obtains the same secret with its private key and the browser
      // public key. Importing a shared vector is independent of client randomness.
      const {hkdf}=await import('@noble/hashes/hkdf.js');
      const peer=Uint8Array.from(atob(request.public_key.replace(/-/g,'+').replace(/_/g,'/')+'='),c=>c.charCodeAt(0));
      const digest=sha256(transcript(pending,grant));
      const secret=join(x25519.getSharedSecret(privateKey,peer),sha256(text('test-only-password')));
      serverState={session:grant.session_id,digest,keys:hkdf(sha256,secret,digest,text('WsprryPico radio traffic v1'),64)};
      return Response.json(grant);
    }
    if(path.endsWith('finish')) return new Response(response(serverState,0n,{authenticated:true,device_id:id.device_id,boot_id:id.boot_id}),{headers:{'Content-Type':'application/octet-stream'}});
    mutations++; if(fail) throw new Error('response lost');
    const seq=new DataView(options.body.buffer,options.body.byteOffset+20,8).getBigUint64(0);
    return new Response(response(serverState,seq,{status:200,etag:'"r"',body:{ok:true}}),{headers:{'Content-Type':'application/octet-stream'}});
  };
  const client=new RadioClient(fetcher,()=>now);
  assert.deepEqual(await client.identity(),id);
  await client.login('test-only-password',id); assert.equal(client.authenticated,true);
  const good=await client.request('config'); assert.equal(good.headers.get('ETag'),'"r"');
  fail=true;
  await assert.rejects(client.request('config','PUT',{},'"r"'),/lost/);
  assert.equal(mutations,2); assert.equal(starts,1); assert.equal(client.authenticated,false);
  await assert.rejects(client.request('status'),/Log in/); assert.equal(mutations,2);
  await client.login('test-only-password',id);
  now+=300000; assert.equal(client.authenticated,true);
  now+=1499999; assert.equal(client.authenticated,true);
  now++; assert.equal(client.authenticated,false);
});
test('browser idle renewal retains an independent eight-hour hard deadline',async()=>{
  let now=1000;
  const client=new RadioClient(async(path,options)=>{
    const sequence=new DataView(options.body.buffer,options.body.byteOffset+20,8).getBigUint64(0);
    return new Response(response(client.state,sequence,{status:200,etag:null,body:{ok:true}}),{headers:{'Content-Type':'application/octet-stream'}});
  },()=>now);
  client.state=vectorState();client.sequence=1n;client.started=client.seen=now;
  for(let elapsed=1000000;elapsed<28800000;elapsed+=1000000){now=1000+elapsed;await client.request('status');}
  now=1000+28800000-1;assert.equal(client.authenticated,true);
  now++;assert.equal(client.authenticated,false);
  client.state=vectorState();client.started=client.seen=now;
  now--;assert.equal(client.authenticated,false);
});
test('wrong boot acknowledgement, concurrency and active response substitution fail closed',async()=>{
  const client=new RadioClient(); client.state=vectorState(); client.identityContext=id; client.sequence=1n; client.started=client.seen=Date.now();
  client.busy=true;
  await assert.rejects(client.request('config','PUT',{}),/already/);
  client.busy=false; client.fetcher=async()=>Response.json({status:200});
  await assert.rejects(client.request('config'),/Unexpected/); assert.equal(client.authenticated,false);
  client.state=vectorState(); client.identityContext=id; client.started=client.seen=Date.now();
  client.fetcher=async()=>new Response(response(client.state,99n,{status:200,etag:null,body:{ok:true}}),{headers:{'Content-Type':'application/octet-stream'}});
  await assert.rejects(client.request('config'),/identity/); assert.equal(client.authenticated,false);
});
test('authenticated network setup preserves transactions and never repeats an uncertain submit',async()=>{
  const calls=[];
  let status={generation:139,slot_state:'trial'};
  const client={identity:async()=>id,request:async(path,method,body)=>{
    calls.push({path,method,body});
    assert.ok(path.startsWith('consumer/setup/api/bootstrap/v1/'));
    if(path.endsWith('/start')) return Response.json({version:1,device_id:id.device_id,boot_id:id.boot_id,
      slot_id:'66'.repeat(16),pico_public_key:grant.public_key,slot_expires_in_ms:180000});
    if(path.endsWith('/submit')) throw new Error('reply lost');
    return Response.json(status);
  }};
  const attempt=await prepareNetwork(client,id,{ssid:'test-network',password:'test-only-password',time_server:'time.local'});
  assert.equal(attempt.generation,'140');
  assert.equal(attempt.digest.length,64);
  assert.equal(JSON.stringify(attempt).includes('test-only-password'),false);
  await assert.rejects(submitSetup(client,attempt),/lost/);
  await assert.rejects(submitSetup(client,attempt),/already sent/);
  assert.equal(calls.filter(c=>c.path.endsWith('/submit')).length,1);
  assert.equal(await checkSetup(client,attempt),'unconfirmed');
  status={generation:140,slot_state:'none',request_id_digest:'00'.repeat(32)};
  assert.equal(await checkSetup(client,attempt),'unconfirmed');
  status.request_id_digest=attempt.digest;
  assert.equal(await checkSetup(client,attempt),'saved');
  status={generation:139,slot_state:'none'};
  assert.equal(await checkSetup(client,attempt),'failed');
  const large={...attempt,generation:'9007199254740993'};
  status={generation:9007199254740992,slot_state:'none',request_id_digest:attempt.digest};
  assert.equal(await checkSetup(client,large),'unconfirmed');
  status.generation='9007199254740993';
  assert.equal(await checkSetup(client,large),'saved');
  client.identity=async()=>({...id,device_id:'aa'.repeat(16)});
  await assert.rejects(checkSetup(client,attempt),/different Pico/);
});
test('capacity, pending login and rate refusals have distinct feedback without retries',async()=>{
  for(const [code,status,message] of [['radio_session_capacity',409,/three radio sessions/],['radio_login_pending',409,/30 seconds/],['radio_login_rate_limited',429,/one second/]]){
    let calls=0;const client=new RadioClient(async()=>{calls++;return Response.json({error:{code}},{status});});
    await assert.rejects(client.login('test-password',id),error=>error.code===code&&message.test(error.message));
    assert.equal(calls,1);assert.equal(client.authenticated,false);
  }
});
test('recovery fixed domain vector and altered scope refuse',async()=>{
  const {readFileSync}=await import('node:fs');
  const v=JSON.parse(readFileSync(new URL('../../../engineering/protocol/Consumer-Recovery-v1-vectors.json',import.meta.url)));
  const g={...grant,login_ms:5000,recovery:v.recovery};
  const s=authenticate(fixed(),g,v.password,id,v.recovery);
  assert.equal(retirementSelector(v,v.session_id),v.selector_for_session_id);
  assert.equal(hex(s.digest),v.transcript_sha256);assert.equal(hex(s.finish),v.login_hex);
  assert.notEqual(hex(s.digest),hex(vectorState().digest));
  for(const key of ['target_selector','authority','interface'])assert.throws(()=>authenticate(fixed(),g,v.password,id,{...v.recovery,[key]:key==='target_selector'?'7'.repeat(32):'wrong'}));
});
test('local validation and RNG failure send nothing, retain healthy keys, and release busy',async()=>{
  let calls=0;const c=new RadioClient(async()=>{calls++;throw new Error('must not send');});
  c.state=vectorState();c.identityContext=id;c.sequence=1n;c.started=c.seen=Date.now();
  await assert.rejects(c.request('config','PUT',{pad:'x'.repeat(32724)}));assert.equal(c.sequence,1n);assert.equal(c.authenticated,true);
  await assert.rejects(c.login('short',id));assert.equal(c.authenticated,true);
  const original=globalThis.crypto;
  try{
    Object.defineProperty(globalThis,'crypto',{configurable:true,value:{getRandomValues(){throw new Error('RNG failed');}}});
    await assert.rejects(c.login('test-password',id),/RNG/);assert.equal(c.busy,false);assert.equal(c.authenticated,true);
    await assert.rejects(c.retire('test-password',{...id,authority:'192.168.1.53',interface:'station'},grant.session_id),/RNG/);assert.equal(c.busy,false);assert.equal(c.authenticated,true);
  }finally{Object.defineProperty(globalThis,'crypto',{configurable:true,value:original});}
  assert.equal(calls,0);
  const malformed=new RadioClient(async()=>Response.json({...grant,session_id:'f'.repeat(100000)}));
  await assert.rejects(malformed.login('test-password',id));assert.equal(malformed.lostSession,null);assert.equal(malformed.busy,false);
});
test('network plaintext validation precedes setup reservation and later/contradictory receipts stay unconfirmed',async()=>{
  let calls=0;const client={identity:async()=>id,request:async()=>{calls++;throw new Error('unexpected request');}};
  for(const settings of [{ssid:'réseau',password:'test-password'},{ssid:'x',password:'short'},{ssid:'x',password:'test-password',time_server:'bad name'},{ssid:'x',password:'test-password',time_server:'127.0.0.1'}])await assert.rejects(prepareNetwork(client,id,settings));
  assert.equal(calls,0);
  const attempt={kind:'network',device:id.device_id,generation:'140',digest:'a'.repeat(64),sent:true};
  let status={generation:'141',slot_state:'terminal',request_id_digest:attempt.digest};
  client.request=async()=>Response.json(status);assert.equal(await checkSetup(client,attempt),'unconfirmed');
  status={generation:'140',slot_state:'terminal',request_id_digest:'b'.repeat(64),attempt_request_id_digest:attempt.digest};assert.equal(await checkSetup(client,attempt),'unconfirmed');
  for(const generation of ['-1','1e2','18446744073709551616',null]){status={generation,slot_state:'none'};assert.equal(await checkSetup(client,attempt),'unconfirmed');}
});
test('nonce RNG failure scrubs generated radio and setup private keys before returning',async()=>{
 const network=await import('./crypto.js'),original=globalThis.crypto;
 try {
  for(const create of [()=>begin(),()=>network.begin()])for(const failure of [2,3]){
   let key,calls=0;Object.defineProperty(globalThis,'crypto',{configurable:true,value:{getRandomValues:bytes=>{if(++calls===failure)throw new Error('nonce RNG failed');bytes.fill(7);if(calls===1)key=bytes;return bytes;}}});
   assert.throws(create,/RNG failed/);assert.equal(key.length,32);assert.ok(key.every(b=>b===0));
  }
 } finally {Object.defineProperty(globalThis,'crypto',{configurable:true,value:original});}
});

test('public transmitter status is a bounded read without authentication or renewal',async()=>{
  const value={schema:'transmitter-public-status/1',device_id:id.device_id,boot_id:id.boot_id,state:'running',output_active:true,owned:true,clock_state:'synchronized',utc_now_ns:'1793000000000000000',uncertainty_ns:'1000',engine:'pio-dma-gp2'};
  let result=value, reads=0;
  const client=new RadioClient(async(path,options)=>{
    reads++;assert.equal(path,'/api/consumer/v1/status');assert.equal(options.body,undefined);
    assert.equal(options.credentials,'omit');assert.equal(options.cache,'no-store');
    return Response.json(result);
  });
  assert.deepEqual(await client.publicStatus(),value);assert.equal(client.authenticated,false);
  for(const patch of [{owner_id:'private'},{state:'unknown'},{owned:'yes'},{uncertainty_ns:'-1'},{utc_now_ns:'18446744073709551616'},{engine:'bad\nengine'},{device_id:'wrong'}]){
    result={...value,...patch};await assert.rejects(client.publicStatus());
  }
  assert.equal(reads,8);
});

test('local locking refuses undispatched requests but admits logout and retains refused-logout context',async()=>{
  let calls=0,status=200;
  const client=new RadioClient(async(path)=>{
    calls++;assert.equal(path,'/api/consumer/v1/request');
    return new Response(response(client.state,client.sequence-1n,{status,etag:null,body:status===200?{ok:true}:{error:'busy'}}),{headers:{'Content-Type':'application/octet-stream'}});
  },()=>1000);
  function authorize(){client.state=vectorState();client.identityContext=id;client.sequence=1n;client.started=client.seen=1000;}
  authorize();client.requestAllowed=()=>false;
  await assert.rejects(client.request('config','PUT',{}),error=>error.local===true);
  assert.equal(calls,0);assert.equal(client.sequence,1n);assert.equal(client.authenticated,true);
  await client.logout();assert.equal(calls,1);assert.equal(client.authenticated,false);
  authorize();status=409;
  const selector=client.retirementSelector;
  await assert.rejects(client.logout(),/refused/);
  assert.equal(client.authenticated,false);assert.equal(client.lostSession.selector,selector);
});

test('independent public reads negotiate an exact target and never grant or renew authority',async()=>{
  const {readFileSync}=await import('node:fs');
  const resources=JSON.parse(readFileSync(new URL('../../../engineering/protocol/pico-public-read-1.schema.json',import.meta.url))).properties.resources.const;
  const descriptor={schema:'pico-public-read/1',target:{scope:'member',device_id:id.device_id,boot_id:id.boot_id},prefix:'/api/consumer/v1/read/',resources};
  let capabilities=descriptor, raw=null, requests=[];
  const client=new RadioClient(async(path,options)=>{
    requests.push(path);assert.equal(options.method||'GET','GET');assert.equal(options.body,undefined);assert.equal(options.credentials,'omit');
    if(path==='/api/consumer/v1/read' && raw!==null) return new Response(raw);
    return Response.json(path.endsWith('/identity')?id:path==='/api/consumer/v1/read'?capabilities:{config:null});
  });
  await client.identity();client.seen=123;
  assert.deepEqual(await (await client.publicRead('config/4')).json(),{config:null});
  assert.equal(client.authenticated,false);assert.equal(client.seen,123);assert.equal(client.sequence,undefined);
  const before=requests.length;await assert.rejects(client.publicRead('jobs'));assert.equal(requests.length,before);
  for(const patch of [{schema:'pico-public-read/2'},{extra:true},{prefix:'/api/v1/'},{resources:[...resources,'restart']},{resources:[...resources,resources[0]]},{target:{...descriptor.target,boot_id:'ff'.repeat(16)}},{target:{...descriptor.target,device_id:'ff'.repeat(16)}}]) {
    capabilities={...descriptor,...patch};client.publicReads=null;
    const before=requests.length;await assert.rejects(client.publicRead('config/4'));assert.equal(requests.length,before+1);
  }
  capabilities=descriptor;
  for(const content of [JSON.stringify(descriptor).replace('"schema":','"schema":"pico-public-read/1","schema":'),JSON.stringify(descriptor).replace('"scope":','"sc\\u006fpe":"member","scope":'),' '.repeat(4097)+JSON.stringify(descriptor),'{"target":{"deep":{"nested":{}}}}']) {
    raw=content;client.publicReads=null;const before=requests.length;
    await assert.rejects(client.publicRead('config/4'));assert.equal(requests.length,before+1);
  }

});


test('timing public reads select their closed independent version and reject malformed peers',async()=>{
  const descriptor={schema:'pico-public-read/2',target:{scope:'member',device_id:id.device_id,boot_id:id.boot_id},prefix:'/api/consumer/v1/read/2/',resources:['amplifier-timing']};
  let advertised=descriptor,reads=[];
  const client=new RadioClient(async(path,options)=>{
    reads.push(path);assert.equal(options.credentials,'omit');
    return Response.json(path.endsWith('/identity')?id:path==='/api/consumer/v1/read/2'?advertised:{saved:{lead_ms:200,tail_ms:200}});
  });
  await client.identity();await client.publicRead('amplifier-timing');
  assert.deepEqual(reads.slice(-2),['/api/consumer/v1/read/2','/api/consumer/v1/read/2/amplifier-timing']);
  for(const patch of [{schema:'pico-public-read/1'},{schema:'pico-public-read/3'},{resources:['amplifier-timing','config']},{prefix:'/api/consumer/v1/read/'},{extra:0},{target:{...descriptor.target,boot_id:'f'.repeat(32)}}]){
    advertised={...descriptor,...patch};client.publicTimingReads=null;const count=reads.length;
    await assert.rejects(client.publicRead('amplifier-timing'));assert.equal(reads.length,count+1);
  }
});
