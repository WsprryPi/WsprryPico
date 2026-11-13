import {fixtureHttpBody} from './fixture_http_body.mjs';
// Full production dispatcher/streamed assets. TCP/board/time are boundary doubles.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {Fixture} from './consumer_sessions.test.mjs';
async function complete(f,host,ap,path,options) {
  const response = await f.fetch(host,ap,path,options);
  const bytes=await fixtureHttpBody(f,response);
  assert.equal(response.headers.get('cache-control'),'no-store');
  return {response,html:bytes.toString()};
}
// The ACK adapter must finish larger real pages and must never accept a stalled,
// truncated, oversized or malformed response as browser evidence.
{
  const expected=500009;let length=1,bursts=0;
  const response=()=>new Response(Buffer.alloc(1),{headers:{'content-length':String(expected)}});
  const adapter={socket:7,async command(value){
    assert.equal(value.socket,7);
    if(value.op==='complete'){++bursts;length=Math.min(expected,length+100000);return {};}
    return {wire:Buffer.concat([Buffer.from('HTTP/1.1 200 OK\r\n\r\n'),Buffer.alloc(length)]).toString('hex')};
  }};
  assert.equal((await fixtureHttpBody(adapter,response())).length,expected);assert.equal(bursts,6);
  const stalled={socket:7,async command(value){return value.op==='complete'?{}:{wire:Buffer.from('HTTP/1.1 200 OK\r\n\r\nx').toString('hex')};}};
  await assert.rejects(fixtureHttpBody(stalled,response()),/makes progress/);
  await assert.rejects(fixtureHttpBody(stalled,new Response('x',{headers:{'content-length':'bad'}})),/declared response/);
  await assert.rejects(fixtureHttpBody(stalled,new Response('x',{headers:{'content-length':'1048577'}})),/bounded fixture/);
  await assert.rejects(fixtureHttpBody(stalled,new Response('xx',{headers:{'content-length':'1'}})),/exact complete/);
}
// A script may stream multiple C++ literals. Keep the original literal bound
// at its actual storage layer and verify CSP against the whole executed script.
const generated=await readFile(process.argv[3],'utf8');let literals=0;
for(const [,,literal] of generated.matchAll(/= R"(WP[A-Z]+)\(([\s\S]*?)\)\1";/g)) {
  assert.ok(Buffer.byteLength(literal)<65536,'bounded C++ asset literal');++literals;
}
assert.ok(literals>10,'inspect the actual generated asset literals');
const icon=await readFile(new URL('../docs/_static/favicon.ico',import.meta.url));
const f=new Fixture(process.argv[2]);
try {
 await f.time(1000);
 for(const host of ['192.168.1.53','wsprrypico-0a60df.local','192.168.4.1']) {
   const ap=host==='192.168.4.1';
   const before=await f.command({op:'stats'});
   const image=await f.fetch(host,ap,'/favicon.ico');
   assert.equal(image.status,200);assert.equal(image.headers.get('content-type'),'image/x-icon');
   assert.equal(image.headers.get('set-cookie'),null);
   assert.deepEqual(await fixtureHttpBody(f,image),icon);
   assert.equal((await f.command({op:'stats'})).config_sequence,before.config_sequence);
   for(const route of ['/','/index.html','/radio','/station','/wifi-host','/owner.html']) {
     const {response,html}=await complete(f,host,ap,route);
     if(ap&&['/','/index.html'].includes(route)) {
       assert.equal(response.status,302);assert.equal(response.headers.get('location'),'/wifi-host');continue;
     }
     assert.equal(response.status,200);assert.ok(html.includes('id="station-area"')&&html.includes('id="wifi-host-area"'));
     assert.equal((html.match(/id="consumer-station-form"/g)||[]).length,1);
     assert.equal((html.match(/id="consumer-network-form"/g)||[]).length,1);
     assert.match(html,/<link rel="icon" type="image\/x-icon" href="\/favicon.ico">/);
     const csp=response.headers.get('content-security-policy');
     for(const [,script] of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) {
       assert.ok(csp.includes("'sha256-"+createHash('sha256').update(script).digest('base64')+"'"),'each executed script has a CSP hash');

     }
     assert.equal((html.match(/<script>/g)||[]).length,6);
     const radioBinding=html.search(/\bradio\s*=\s*globalThis\.WsprryPicoConsumerRadio/);
     assert.ok(radioBinding>=0 && html.indexOf('WsprryPicoOwnerKey')<radioBinding);
     assert.ok(!html.includes('<script src='));
   }
 }
 for(const path of ['/api/bootstrap/v1/status','/api/owner/v1/public-status','/recovery.html','/api/control/v1/config'])
   assert.equal((await complete(f,'192.168.1.53',false,path)).response.status,403);
 assert.equal((await complete(f,'192.168.4.1',false,'/wifi-host')).response.status,403,'Host cannot fabricate AP context');
 assert.equal((await complete(f,'192.168.1.53',false,'/wifi-host',{method:'POST'})).response.status,403);
 for(const route of ['/radio/','/favicon.ico/']) assert.notEqual((await complete(f,'192.168.1.53',false,route)).response.status,200,'unknown trailing slash is not an HTML/image fallback');
 assert.equal((await complete(f,'evil.example',false,'/favicon.ico')).response.status,403);
 assert.equal((await complete(f,'192.168.4.1',false,'/favicon.ico')).response.status,403);
 assert.equal((await complete(f,'captive.apple.com',true,'/favicon.ico')).response.status,302);
 const captive=await complete(f,'captive.apple.com',true,'/hotspot-detect.html');
 assert.equal(captive.response.status,302);assert.equal(captive.response.headers.get('location'),'http://192.168.4.1/');
 const post=await complete(f,'captive.apple.com',true,'/wifi-host',{method:'POST'});
 assert.equal(post.response.status,405);assert.equal(post.response.headers.get('location'),null);
 for(const mode of ['blank','network','unavailable']) {
   await f.command({op:'page_profile',mode});
   const image=await f.fetch('192.168.4.1',true,'/favicon.ico');
   assert.equal(image.status,200);assert.equal(image.headers.get('content-type'),'image/x-icon');
   assert.deepEqual(await fixtureHttpBody(f,image),icon);
   const root=await complete(f,'192.168.4.1',true,'/');
   assert.equal(root.response.status,mode==='network'?302:200);
   if(mode==='network') {
     assert.equal(root.response.status,302);
     assert.equal(root.response.headers.get('location'),'/wifi-host');
     for(const route of ['/station','/radio','/wifi-host','/owner.html'])
       assert.match((await complete(f,'192.168.4.1',true,route)).html,/id="consumer-station-form"/);
   } else if(mode==='unavailable') {
     assert.ok(!root.html.includes('<form'));assert.match(root.html,/USB Console recovery/);
   } else {
     assert.match(root.html,/id="wifi-form"/);
     assert.ok(!root.html.includes('id="owner-form"'));
     const status=await complete(f,'192.168.4.1',true,'/api/bootstrap/v1/status');
     const observed=JSON.parse(status.html);
     assert.equal(observed.source,mode==='blank'?'unprovisioned':'network_only');
     assert.equal(observed.generation,mode==='blank'?0:1);
     for(const route of ['/station','/radio','/owner.html'])
       assert.match((await complete(f,'192.168.4.1',true,route)).html,/id="owner-form"/);
   }
   assert.equal((await complete(f,'192.168.1.53',false,'/')).response.status,mode==='network'?200:403);
 }
 assert.equal((await f.command({op:'stats'})).api_restarts,0);
 console.log('PASS production AP/LAN aliases, exact Host/interface admission, commissioning/unavailable routes, full streaming and CSP; zero restarts');
} finally {await f.stop();}

// Recovery is an authenticated setup operation on both consumer carriers.
// The reset callback alone is doubled: production HTTP, AEAD, slots and parsing
// remain in the served Pico implementation; no physical settings are erased.
const {setup}=await import('../src/network/bootstrap_web/radio-setup.js');
const {recoveryKey,recoverySeal}=await import('../src/network/bootstrap_web/recovery-crypto.js');
for(const [host,ap] of [['192.168.1.53',false],['192.168.4.1',true]]) {
 const reset=new Fixture(process.argv[2]);
 try {
  await reset.time(1000);await reset.command({op:'page_profile',mode:'network-recovery'});
  const a=reset.client(host,ap),b=reset.client(host,ap);
  await assert.rejects(a.resetSettings({device_id:'1'.repeat(32),boot_id:'a'.repeat(32)},'erase'),/Log in/);
  await reset.login(a);const identity=await a.identity();
  assert.equal((await a.recoveryStatus(identity)).pending,false);
  const key=recoveryKey(),startBody={version:1,device_id:identity.device_id,browser_public_key:key.public,request_nonce:key.nonce};
  for(const bad of [{...startBody,version:2},{...startBody,extra:true},{...startBody,device_id:'f'.repeat(32)}])
   await assert.rejects(setup(a,'/api/recovery/v1/start',bad));
  const start=await setup(a,'/api/recovery/v1/start',startBody);
  const body=recoverySeal(key,start,identity.device_id,'erase');
  await reset.time(2000);await reset.login(b);
  await assert.rejects(setup(b,'/api/recovery/v1/submit',body),/recovery_login_mismatch/);
  const publicAttempt=await reset.fetch('192.168.4.1',true,'/api/recovery/v1/submit',
   {method:'POST',body:JSON.stringify(body),headers:{'Content-Type':'application/json'},marker:'Bootstrap'});
  assert.equal(publicAttempt.status,403,'authenticated proof cannot cross to public recovery');
  await assert.rejects(setup(a,'/api/recovery/v1/submit',{...body,boot_id:'f'.repeat(32)}));
  await a.logout();
  await assert.rejects(setup(b,'/api/recovery/v1/submit',body));
  assert.equal((await reset.command({op:'stats'})).recovery_requests,0,'logout and rejected proofs never reset');
  const publicKey=recoveryKey();
  const publicStart=await reset.fetch('192.168.4.1',true,'/api/recovery/v1/start',
   {method:'POST',body:JSON.stringify({version:1,device_id:identity.device_id,browser_public_key:publicKey.public,request_nonce:publicKey.nonce}),headers:{'Content-Type':'application/json'},marker:'Bootstrap'});
  assert.equal(publicStart.status,200);
  const publicBody=recoverySeal(publicKey,await publicStart.json(),identity.device_id,'erase');
  await assert.rejects(setup(b,'/api/recovery/v1/submit',publicBody),/recovery_login_mismatch/,'public proof cannot cross into an authenticated login');
  await reset.time(183000); // Expire the public reservation; do not submit a reset.

  assert.equal((await b.resetSettings(await b.identity(),'erase')).state,'reset_pending');
  assert.equal(b.authenticated,false,'successful reset retires the local login');
  assert.equal((await reset.command({op:'stats'})).recovery_requests,1);
 } finally {await reset.stop();}
}
{
 const reset=new Fixture(process.argv[2]);
 try {
  await reset.time(1000);await reset.command({op:'page_profile',mode:'network-recovery'});
  const a=reset.client();await reset.login(a);const identity=await a.identity();
  const fetch=a.fetcher;let requests=0;
  a.fetcher=async(...args)=>{const response=await fetch(...args);if(++requests===3)throw new Error('lost reset reply');return response;};
  await assert.rejects(a.resetSettings(identity,'reset provisioning'),error=>error.unconfirmed===true);
  assert.equal(a.authenticated,false);assert.equal(requests,3,'lost submit is not replayed');
  assert.equal((await reset.command({op:'stats'})).recovery_requests,1);
 } finally {await reset.stop();}
}
console.log('PASS authenticated station/AP recovery, closed parsing, login-bound proofs, logout cancellation and lost-submit refusal');
