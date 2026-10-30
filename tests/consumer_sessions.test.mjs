// Genuine Noble browser client -> production Pico HTTP/parser/session/AEAD/API.
// lwIP calls are deterministic boundary doubles; this is software evidence.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {RadioClient} from '../src/network/bootstrap_web/radio-client.js';
import {seal,open,begin} from '../src/network/bootstrap_web/radio-crypto.js';

export class Fixture {
  constructor(executable,args=[]) {
    this.process=spawn(executable,args,{stdio:['pipe','pipe','pipe']});
    this.lines=createInterface({input:this.process.stdout});
    this.queue=[]; this.stderr=''; this.now=1000;
    this.process.stderr.on('data',bytes=>this.stderr+=bytes);
    this.lines.on('line',line=>{const next=this.queue.shift(); assert.ok(next); next.resolve(JSON.parse(line));});
    this.process.on('exit',code=>{for(const next of this.queue.splice(0))next.reject(new Error(`driver exited ${code}: ${this.stderr}`));});
    this.pending=Promise.resolve();
  }
  command(value) {
    if(value.hex!==undefined){value={...value,b64:Buffer.from(value.hex,'hex').toString('base64url')};delete value.hex;}
    if(typeof value.socket==='number')value={...value,socket:String(value.socket)};
    // Core 0 is serialized, even when independent clients issue concurrent JS calls.
    const result=this.pending.then(()=>new Promise((resolve,reject)=>{
      this.queue.push({resolve,reject}); this.process.stdin.write(JSON.stringify(value)+'\n');
    })); this.pending=result.catch(()=>{}); return result;
  }
  async time(ms) {this.now=ms;await this.command({op:'time',ms:String(ms)});}
  client(host='192.168.1.53',ap=false) {
    const client=new RadioClient((path,options={})=>this.fetch(host,ap,path,options),()=>this.now,{authority:host,interface:ap?'ap':'station'});
    client.host=host; client.ap=ap; return client;
  }
  async fetch(host,ap,path,options={}) {
    const body=options.body instanceof Uint8Array ? Buffer.from(options.body) : Buffer.from(options.body||'');
    const hold=this.holdNext;this.holdNext=false;
    const result=await this.command({op:'request',host,ap,path,method:options.method||'GET',type:options.headers?.['Content-Type']||'application/json',b64:body.toString('base64url'),hold:Boolean(hold),marker:options.marker||'Radio'});
    this.socket=result.socket;
    const wire=Buffer.from(result.wire,'hex'); const end=wire.indexOf('\r\n\r\n'); assert.ok(end>=0);
    const headers=wire.subarray(0,end).toString().split('\r\n');
    const status=Number(headers.shift().split(' ')[1]);
    return new Response(wire.subarray(end+4),{status,headers:headers.map(line=>{const i=line.indexOf(':');return [line.slice(0,i),line.slice(i+1).trim()];})});
  }
  async login(client,password='test-password') {await client.login(password,await client.identity());}
  async stop() {if(this.process.exitCode!==null||this.process.signalCode!==null)return;this.process.stdin.end();await new Promise(resolve=>this.process.once('exit',resolve));}
}
async function run(name,fn) {
  const f=new Fixture(process.argv[2]);
  try {await f.time(1000);await fn(f);console.log('PASS '+name);}
  finally {await f.stop();}
}
if(import.meta.url===new URL(process.argv[1],'file:').href) {
await run('public settings and full observations are read-only without occupying or renewing a login',async f=>{
  for(const [host,ap] of [['192.168.1.53',false],['192.168.4.1',true]]) {
    const client=f.client(host,ap);await client.identity();
    const before=await f.command({op:'stats'});
    const config=await client.publicRead('config');assert.equal(config.status,200);
    const data=await config.json();assert.equal(data.config.station.callsign,'AA0NT');assert.equal(data.config.wifi.password,null);
    const observed=await (await client.publicRead('operations')).json();assert.equal(observed.schema,'operations');assert.equal(observed.job.state,'empty');
    assert.equal((await client.publicRead('logging')).status,200);assert.equal((await client.publicRead('udp-logging')).status,200);
    for(const method of ['POST','PUT','DELETE']) assert.equal((await f.fetch(host,ap,'/api/consumer/v1/read/config',{method,body:'{}'})).status,method==='DELETE'?400:405);
    assert.equal((await f.fetch(host,ap,'/api/consumer/v1/read/jobs')).status,404);
    assert.equal(client.authenticated,false);assert.equal((await f.command({op:'stats'})).config_sequence,before.config_sequence);
    await assert.rejects(client.request('config','PUT',{}),/Log in/);
  }
});
await run('recurring message profile uses authenticated encrypted management and survives reboot',async f=>{
  const a=f.client();await f.login(a);
  const read=await a.request('message-schedule'),resource=await read.json();
  assert.equal(resource.schema,'message-schedule');
  const saved={enabled:false,first_start_utc_ns:'1793001605000000000',period_s:1200,expires_utc_s:0,
    message:{mode:'dfcw',message:'CQ AA0NT',frequency_nhz:'10140000000000000',space_frequency_nhz:'10140005000000000',
      timing:{dot_ns:'1000000000',dash_ns:'3000000000',intra_gap_ns:'1000000000',character_gap_ns:'3000000000',word_gap_ns:'7000000000'},
      repeat_count:1,repeat_gap_ns:'3000000000',allow_frequency_adjustment:true}};
  const body={schema:resource.schema,target:resource.target,schedule:saved};
  assert.equal((await a.request('message-schedule','PUT',body)).status,428);
  const changed=await a.request('message-schedule','PUT',body,read.headers.get('etag'));
  assert.equal(changed.status,200);assert.deepEqual((await changed.json()).saved,saved);
  await f.command({op:'reboot'});await f.time(2000);await f.login(a);
  const after=await a.request('message-schedule'),observed=await after.json();
  assert.deepEqual(observed.saved,saved);assert.equal(observed.state,'paused');
  const pause=await a.request('message-schedule/pause','POST',{schema:observed.schema,target:observed.target,pause:true},after.headers.get('etag'));
  assert.equal(pause.status,200);assert.equal((await pause.json()).pause_pending,false);
});

await run('separate Pico password persists, rejects stale saves and retires all browser logins',async f=>{
  const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
  const read=await a.request('consumer/password'),state=await read.json();
  assert.equal(state.contract,'Wsprry-Control/1');assert.equal(state.schema,'pico-password');assert.equal(state.wifi_default,true);
  const etag=read.headers.get('etag'),body={schema:state.schema,target:state.target,password:'private-pico-password'};
  assert.equal((await a.request('consumer/password','PUT',body)).status,428);
  assert.equal((await a.request('consumer/password','PUT',body,'"stale"')).status,412);
  assert.equal((await a.request('consumer/password','PUT',{...body,password:'short'},etag)).status,400);
  assert.equal((await a.request('consumer/password','PUT',{...body,target:{...body.target,device_id:'2'.repeat(32)}},etag)).status,400);
  const changed=await a.request('consumer/password','PUT',body,etag);
  assert.equal(changed.status,200);assert.equal((await changed.json()).wifi_default,false);
  await assert.rejects(a.request('status'));await assert.rejects(b.request('status'));
  await f.time(3000);await assert.rejects(f.login(a,'test-password'),/password/i);
  await f.time(4000);await f.login(a,'private-pico-password');
  const observed=JSON.stringify(await(await a.request('consumer/password')).json());
  assert.ok(!observed.includes('private-pico-password'));assert.ok(!observed.includes('test-password'));
  await f.command({op:'reboot'});await f.time(5000);await f.login(a,'private-pico-password');
  const saved=await a.request('consumer/password'),savedState=await saved.json();
  assert.equal(savedState.wifi_default,false);
  const restored=await a.request('consumer/password','PUT',{schema:savedState.schema,target:savedState.target,password:null},saved.headers.get('etag'));
  assert.equal(restored.status,200);assert.equal((await restored.json()).wifi_default,true);
  await f.time(6000);await assert.rejects(f.login(a,'private-pico-password'),/password/i);
  await f.time(7000);await f.login(a);assert.equal((await a.request('status')).status,200);
});
await run('three real independent station/hostname sessions, quotas, logout and reuse',async f=>{
  const a=f.client(),b=f.client(),c=f.client('wsprrypico-0a60df.local');
  await f.login(a);await assert.rejects(f.login(b),/second|request|login/i);assert.ok(a.authenticated);
  await f.time(2000);await f.login(b);await f.time(3000);await f.login(c);
  assert.notDeepEqual(a.state.keys,b.state.keys);assert.notDeepEqual(a.state.session,b.state.session);
  for(let i=0;i<3;i++)for(const client of [a,b,c])assert.equal((await client.request('status')).status,200);
  const other=f.client();await f.time(4000);await assert.rejects(f.login(other),/session|request/i);
  const packet=seal(a.state,a.sequence,{method:'GET',path:'/api/control/v1/status',if_match:null,body:null});
  const raw=await f.fetch(a.host,false,'/api/consumer/v1/request',{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:packet});
  const reply=new Uint8Array(await raw.arrayBuffer());assert.throws(()=>open(b.state,a.sequence,reply));
  open(a.state,a.sequence++,reply);
  const retired=a.state.session;await a.logout();assert.ok(b.authenticated&&c.authenticated);
  await f.time(5000);await f.login(a);assert.notDeepEqual(a.state.session,retired);
  assert.equal((await b.request('config')).status,200);
  for(let i=0;i<12;i++){await a.logout();await f.time(6000+i*1000);await f.login(a);}
  const stats=await f.command({op:'stats'});assert.equal(stats.psa_owners,0);assert.equal(stats.connections,0);assert.equal(stats.pending_bytes,0);
});
await run('pending proof, bad password, RNG and allocation failure preserve active client',async f=>{
  const a=f.client();await f.login(a);await f.time(2000);
  let grant;
  const b=new RadioClient(async(path,options)=>{
    const response=await f.fetch('192.168.1.53',false,path,options);
    if(path.endsWith('start')){grant=await response.clone().json();assert.equal((await a.request('status')).status,200);
      const c=f.client();await assert.rejects(f.login(c),/login|request/i);}
    return response;
  },()=>f.now);
  await f.login(b);assert.ok(grant.session_id);await b.logout();
  await f.time(3000);await assert.rejects(f.login(b,'wrong-password'),/password|expired/i);
  assert.equal((await a.request('status')).status,200);
  for(const zero of [false,true]){await f.command({op:'rng',fail:!zero,zero});await f.time(f.now+1000);await assert.rejects(f.login(b));assert.equal((await a.request('status')).status,200);}
  await f.command({op:'rng',fail:false,zero:false});await f.time(6000);await f.login(b);
  // Low-memory admission refuses the addressed HTTP upload before dispatch.
  await f.command({op:'memory',fail:true});await assert.rejects(b.request('config'));
  await f.command({op:'memory',fail:false});assert.equal((await a.request('status')).status,200);
});
await run('unknown IDs, wrong sequence, wrong origin and invalid tag isolate addressed slot',async f=>{
  const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
  const call=async(packet,host=a.host)=>f.fetch(host,false,'/api/consumer/v1/request',{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:packet});
  const envelope={method:'GET',path:'/api/control/v1/status',if_match:null,body:null};
  let p=seal(a.state,a.sequence,envelope);p[4]^=1;assert.equal((await call(p)).status,401);
  assert.equal((await a.request('status')).status,200);
  p=seal(a.state,a.sequence+1n,envelope);assert.equal((await call(p)).status,401);
  p=seal(a.state,a.sequence,envelope);assert.equal((await call(p,'wsprrypico-0a60df.local')).status,403);
  assert.equal((await a.request('status')).status,200);
  p=seal(a.state,a.sequence,envelope);p[p.length-1]^=1;assert.equal((await call(p)).status,401);
  assert.equal((await b.request('status')).status,200);await assert.rejects(a.request('status'));
});
await run('independent idle, login and absolute expiry, and interface invalidation',async f=>{
  const a=f.client(),b=f.client('192.168.4.1',true);await f.login(a);await f.time(2000);await f.login(b);
  await f.time(1800999);assert.equal((await b.request('status')).status,200);
  await f.time(1801000);await assert.rejects(a.request('status'));assert.equal((await b.request('status')).status,200);
  await f.time(1802000);await f.login(a);
  await f.command({op:'listeners',ap:false,ip:'192.168.1.53',host:'wsprrypico-0a60df.local'});
  assert.equal((await a.request('status')).status,200);await assert.rejects(b.request('status'));
  await f.command({op:'listeners',ap:true,ip:'192.168.1.53',host:'wsprrypico-0a60df.local'});
  await f.time(1803000);await f.login(b);
  await f.command({op:'listeners',ap:true,ip:'192.168.1.54',host:'wsprrypico-0a60df.local'});
  assert.equal((await b.request('status')).status,200);await assert.rejects(a.request('status'));
  for(let elapsed=1000000;elapsed<28800000;elapsed+=1000000){await f.time(1803000+elapsed);assert.equal((await b.request('status')).status,200);}
  await f.time(1803000+28800000-1);assert.equal(b.authenticated,true);
  await f.time(1803000+28800000);await assert.rejects(b.request('status'));
  a.host='192.168.1.54';a.fetcher=(p,o)=>f.fetch(a.host,false,p,o);await f.time(f.now+1000);await f.login(a);
  await f.time(f.now-1);await assert.rejects(a.request('status'));
});
await run('server expires idle and absolute sessions even when a client keeps its keys',async f=>{
  const a=f.client();await f.login(a);
  // Freeze the client clock so its local expiry cannot mask a server defect.
  a.now=()=>1000;
  await f.time(301000);assert.equal(a.authenticated,true);
  await a.identity(); // Public traffic does not renew authenticated idle time.
  assert.equal((await a.publicStatus()).state,'empty');
  await f.time(1800999);assert.equal((await a.request('status')).status,200);
  await f.time(3600998);await a.identity();await a.publicStatus();assert.equal(a.authenticated,true);
  await f.time(3600999);await assert.rejects(a.request('status'));
  await f.login(a);
  const started=f.now;
  for(let elapsed=1000000;elapsed<28800000;elapsed+=1000000){await f.time(started+elapsed);assert.equal((await a.request('status')).status,200);}
  await f.time(started+28800000-1);assert.equal((await a.request('status')).status,200);
  await f.time(started+28800000);await assert.rejects(a.request('status'));
});
await run('idle expiry frees one occupied slot without evicting its active peers',async f=>{
  const a=f.client(),b=f.client(),c=f.client(),next=f.client();
  await f.login(a);await f.time(2000);await f.login(b);await f.time(3000);await f.login(c);
  await f.time(1800999);
  assert.equal((await b.request('status')).status,200);assert.equal((await c.request('status')).status,200);
  await assert.rejects(f.login(next),/three radio sessions/);
  await f.time(1801000);await f.login(next);
  assert.equal(a.authenticated,false);
  for(const client of [b,c,next])assert.equal((await client.request('status')).status,200);
});
await run('stale concurrent edits share one journal and keep both logins',async f=>{
  const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
  const ra=await a.request('config'),rb=await b.request('config');assert.equal(ra.headers.get('etag'),rb.headers.get('etag'));
  const app=await (await a.request('application')).json();
  const update={schema:'config-update',target:app.target,mode:'merge',config:{allow_unqualified_frequency:true}};
  assert.equal((await a.request('config/update','POST',update,ra.headers.get('etag'))).status,200);
  assert.equal((await b.request('config/update','POST',update,rb.headers.get('etag'))).status,412);
  assert.ok(a.authenticated&&b.authenticated);
  const fresh=await b.request('config');update.config.allow_non_amateur_frequency=true;
  assert.equal((await b.request('config/update','POST',update,fresh.headers.get('etag'))).status,200);
  const saved=(await (await a.request('config')).json()).config;
  assert.equal(saved.allow_unqualified_frequency,true);assert.equal(saved.allow_non_amateur_frequency,true);
  for(const path of ['station','hardware','pins'])assert.equal((await b.request(path)).status,200);
});
await run('unacknowledged board effect, other logout/reply, partial ACK, FIN and timeout',async f=>{
  const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
  let revision=(await a.request('config')).headers.get('etag');
  f.holdNext=true;assert.equal((await a.request('network','PUT',{enabled:false},revision)).status,200);
  const held=f.socket;assert.equal((await f.command({op:'stats'})).network_pending,true);
  assert.equal((await b.request('status')).status,200);await b.logout();
  await f.command({op:'ack',socket:held,bytes:'1'});assert.equal((await f.command({op:'stats'})).network_enabled,true);
  await f.command({op:'fin',socket:held});assert.equal((await f.command({op:'stats'})).network_pending,false);
  assert.equal((await a.request('status')).status,200);
  await f.time(3000);await f.login(b);revision=(await b.request('config')).headers.get('etag');
  f.holdNext=true;assert.equal((await b.request('network','PUT',{enabled:false},revision)).status,200);
  const pending=f.socket;await a.logout();await f.time(13000);
  assert.equal((await f.command({op:'stats'})).network_enabled,true);
  await f.command({op:'complete',socket:pending}); // stale transport completion
  assert.equal((await b.request('status')).status,200);
  await f.time(14000);await f.login(a);revision=(await a.request('config')).headers.get('etag');
  f.holdNext=true;assert.equal((await a.request('network','PUT',{enabled:false},revision)).status,200);
  const delivered=f.socket;assert.equal((await b.request('status')).status,200);
  await f.command({op:'complete',socket:delivered});assert.equal((await f.command({op:'stats'})).network_enabled,false);
});
await run('abandoned pending proof expires without clearing healthy session',async f=>{
  const a=f.client(),b=f.client();await f.login(a);await f.time(2000);
  const identity=await b.identity(), pending=begin();
  const grant=await b.post('start',{version:1,device_id:identity.device_id,boot_id:identity.boot_id,generation:identity.generation,public_key:pending.public_key,nonce:pending.nonce},false,30000);
  assert.equal((await f.command({op:'stats'})).psa_owners,1);
  await f.time(31999);assert.equal((await a.request('status')).status,200);
  await assert.rejects(f.login(b),/login/i);
  await f.time(32000);assert.equal((await f.command({op:'stats'})).psa_owners,0);
  await f.login(b);assert.notEqual(b.state.session,grant.session_id);
  assert.equal((await a.request('status')).status,200);pending.secret.fill(0);
});
await run('sequence exhaustion and response allocation failure close only addressed session',async f=>{
  const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
  await f.command({op:'exhaust',id:a.state.session});await assert.rejects(a.request('status'));
  assert.equal((await b.request('status')).status,200);
  await f.time(3000);await f.login(a);
  await f.command({op:'handler_memory',fail:true});await assert.rejects(a.request('status'));
  await f.command({op:'handler_memory',fail:false});assert.equal((await b.request('status')).status,200);
});
await run('deferred receipt remains isolated after interface closure, slot reuse and delayed ACK',async f=>{
  const a=f.client('192.168.4.1',true),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
  const revision=(await a.request('config')).headers.get('etag');
  f.holdNext=true;await a.request('network','PUT',{enabled:false},revision);
  const held=f.socket,old=(await f.command({op:'stats'})).transaction;
  await f.command({op:'listeners',ap:false,ip:'192.168.1.53',host:'wsprrypico-0a60df.local'});
  assert.equal((await f.command({op:'stats'})).network_pending,false);
  await f.command({op:'listeners',ap:true,ip:'192.168.1.53',host:'wsprrypico-0a60df.local'});
  await f.time(3000);await f.login(a);
  const fresh=(await a.request('config')).headers.get('etag');
  await f.command({op:'fin',socket:held});
  f.holdNext=true;await a.request('network','PUT',{enabled:false},fresh);
  const next=f.socket;
  await f.command({op:'delivery',tx:old,apply:true});
  assert.equal((await f.command({op:'stats'})).network_pending,true);
  assert.equal((await b.request('status')).status,200);
  await f.command({op:'rst',socket:next});assert.equal((await f.command({op:'stats'})).network_enabled,true);
  await f.command({op:'invalidate'});await assert.rejects(b.request('status'));
});

await run('distinct sessions retain one transmitter owner after logout',async f=>{
  const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
  let request=1;const session='1'.repeat(32),job='2'.repeat(32);
  const command=(client,operation,body)=>client.request('jobs','POST',{session_id:session,request_id:String(request++).padStart(32,'0'),operation,body});
  assert.equal((await command(a,'HELLO',{versions:['WTP/1'],client_name:'test',client_version:'1'})).status,200);
  assert.equal((await command(a,'CLAIM',{owner_id:session,lease_ms:30000})).status,200);
  const revision=(await b.request('config')).headers.get('etag');
  assert.equal((await b.request('network','PUT',{enabled:false},revision)).status,409);
  assert.equal((await command(a,'LOAD',{job_id:job,profile:'rf-events/1',mode:'tone',total_duration_ns:'1000000000',events:[{offset_ns:'0',duration_ns:'1000000000',rf_on:true,frequency_nhz:'3570100000000000'}],allow_frequency_adjustment:false})).status,200);
  await a.logout();const status=await (await b.request('status')).json();assert.equal(status.job.state,'loaded');assert.equal(status.job.owner_id,session);
});
await run('failed save and lost reply retain bounded abandoned session without mutation replay',async f=>{
  const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
  let original=await a.request('config');const app=await (await a.request('application')).json();
  const update={schema:'config-update',target:app.target,mode:'merge',config:{station:{callsign:'K1ABC'}}};
  assert.equal((await a.request('config/update','POST',update,original.headers.get('etag'))).status,409);
  assert.ok(a.authenticated);assert.equal((await b.request('status')).status,200);
  update.config={allow_unqualified_frequency:true};const fetcher=a.fetcher;let sent=0;
  a.fetcher=async(p,o)=>{const response=await fetcher(p,o);if(p.endsWith('/request')){sent++;throw new Error('reply lost after commit');}return response;};
  await assert.rejects(a.request('config/update','POST',update,original.headers.get('etag')),/lost/);assert.equal(sent,1);
  assert.equal(a.authenticated,false);const readback=await (await b.request('config')).json();assert.equal(readback.config.allow_unqualified_frequency,true);
  a.fetcher=fetcher;await f.time(3000);await f.login(a);
  const c=f.client();await f.time(4000);await assert.rejects(f.login(c),/three radio sessions/);
  assert.equal((await a.request('status')).status,200);assert.equal((await b.request('status')).status,200);
});

await run('slow genuine encrypted upload permits another login and two large exchanges reclaim pages',async f=>{
  const a=f.client(),b=f.client();await f.login(a);await f.time(2000);
  const value={method:'POST',path:'/api/control/v1/jobs',if_match:null,body:{pad:''}};
  value.body.pad='x'.repeat(32724-JSON.stringify(value).length);
  const packet=seal(a.state,a.sequence++,value);assert.equal(packet.length,32768);
  const upload=await f.command({op:'request',host:a.host,ap:false,path:'/api/consumer/v1/request',method:'POST',type:'application/octet-stream',hex:Buffer.from(packet).toString('hex'),hold:false,cut:'500'});
  assert.equal(upload.wire,'');await f.login(b);assert.equal((await b.request('status')).status,200);
  await f.command({op:'continue',socket:upload.socket});assert.equal((await a.request('status')).status,200);
  for(const client of [a,b]) {
    const next=seal(client.state,client.sequence++,value);
    f.holdNext=true;const response=await f.fetch(client.host,false,'/api/consumer/v1/request',{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:next});
    assert.equal(response.status,200);
  }
  assert.equal((await f.command({op:'stats'})).connections,2);
  await f.command({op:'complete',socket:0});await f.command({op:'complete',socket:1});
  const stats=await f.command({op:'stats'});assert.equal(stats.pending_bytes,0);assert.equal(stats.connections,0);
  assert.equal((await a.request('status')).status,200);assert.equal((await b.request('status')).status,200);
});

await run('profile generation invalidates all old sessions while shared PSA owner survives',async f=>{
  await f.command({op:'psa_owner',active:true});
  const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
  assert.equal((await f.command({op:'stats'})).psa_owners,1);
  await f.command({op:'generation'});
  await assert.rejects(a.request('status'));await assert.rejects(b.request('status'));
  await f.time(3000);const identity=await a.identity();assert.equal(identity.generation,'2');await f.login(a);
  assert.equal((await f.command({op:'stats'})).psa_owners,1);
  await f.command({op:'psa_owner',active:false});assert.equal((await f.command({op:'stats'})).psa_owners,0);
});

}
