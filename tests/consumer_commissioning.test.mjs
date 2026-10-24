// Production PicoBootstrapServer dispatch/trials/journals; only board boundaries
// are explicit doubles. Real Noble bootstrap/owner and Mbed TLS crypto run.
import assert from 'node:assert/strict';
import {Fixture} from './consumer_sessions.test.mjs';
import {begin as beginWifi,seal as sealWifi} from '../src/network/bootstrap_web/crypto.js';
import {p256} from '../src/network/bootstrap_web/node_modules/@noble/curves/nist.js';
globalThis.WsprryPicoOwnerKey={keygen:()=>p256.keygen(),getPublicKey:(key,compressed)=>p256.getPublicKey(key,compressed)};
async function run(name,fn,args=[]){const f=new Fixture(process.argv[2],args);try{await f.time(1000);await fn(f);console.log('PASS '+name);}finally{await f.stop();}}
await run('Wi-Fi-only setup survives reboot and admits LAN login without station data',async f=>{
 const setup=async(path,body)=>f.fetch('192.168.4.1',true,path,{method:body?'POST':'GET',marker:'Bootstrap',body:body?JSON.stringify(body):undefined});
 const id=await(await setup('/local/v1/identity')).json(),pending=beginWifi();
 const start=await(await setup('/api/bootstrap/v1/start',{version:1,device_id:id.device_id,browser_public_key:pending.browserPublicKey,request_nonce:pending.requestNonce})).json();
 const attempt=sealWifi(pending,start,id.device_id,'Home Wi-Fi','test-password',{timeServer:'pool.ntp.org'});
 assert.equal((await setup('/api/bootstrap/v1/submit',attempt.submit)).status,200);
 await f.time(5000);await f.time(6000);
 const saved=await(await setup('/api/bootstrap/v1/status')).json();
 assert.equal(saved.source,'network_only');assert.equal(saved.generation,1);assert.equal(saved.request_id_digest,attempt.requestDigest);
 assert.equal((await f.command({op:'stats'})).config_sequence,'0');
 await f.command({op:'reboot'});await f.time(8000);
 for(const host of ['192.168.1.53','wsprrypico-0a60df.local']){
   const page=await f.fetch(host,false,'/');assert.equal(page.status,200);
   let bytes=Buffer.from(await page.arrayBuffer()),expected=Number(page.headers.get('content-length'));
   for(let i=0;bytes.length<expected&&i<4;i++){await f.command({op:'complete',socket:f.socket});const wire=Buffer.from((await f.command({op:'wire',socket:f.socket})).wire,'hex');bytes=wire.subarray(wire.indexOf('\r\n\r\n')+4);}
   assert.equal(bytes.length,expected);assert.match(bytes.toString(),/id="local-login"/);
   const a=f.client(host);await f.login(a);
   assert.equal((await(await a.request('config')).json()).config,null);
   assert.equal((await(await a.request('station/2')).json()).station,null);
   assert.equal((await(await a.request('capabilities')).json()).features.consumer_setup_identity,true);
   const status=await(await a.request('status')).json();assert.equal(status.job.output_active,false);
   assert.equal((await f.command({op:'stats'})).config_sequence,'0');
   await a.logout();await f.time(f.now+1000);
   await assert.rejects(f.login(a,'wrong-password'),/password|expired/i);await f.time(f.now+1000);
 }
 const a=f.client();await f.login(a);
 const passwordRead=await a.request('consumer/password'),passwordState=await passwordRead.json();
 assert.equal((await a.request('consumer/password','PUT',{schema:passwordState.schema,target:passwordState.target,password:'independent-pico-password'},passwordRead.headers.get('etag'))).status,200);
 await f.time(f.now+1000);await f.login(a,'independent-pico-password');
 const network=await a.prepareNetwork(await a.identity(),{ssid:'Changed home Wi-Fi',password:'changed-wifi-password',time_server:'pool.ntp.org'});
 await a.submitSetup(network);await f.time(f.now+4000);await f.time(f.now+1000);
 assert.equal((await f.command({op:'stats'})).profile_generation,network.generation);
 await f.command({op:'reboot'});await f.time(f.now+1000);
 await assert.rejects(f.login(a,'changed-wifi-password'),/password/i);
 await f.time(f.now+1000);await f.login(a,'independent-pico-password');
 assert.equal((await(await a.request('station/2')).json()).station,null);
 const station=await a.prepareStation(await a.identity(),{callsign:'K1ABC',locator:'FN42',powerDbm:30});
 await a.submitSetup(station);await f.time(f.now+2000);
 assert.equal((await f.command({op:'stats'})).profile_generation,station.generation);
 await f.command({op:'reboot'});await f.time(f.now+1000);await f.login(a,'independent-pico-password');
 assert.equal((await(await a.request('station/2')).json()).station.callsign,'K1ABC');
},['1'.repeat(32),'--blank']);
await run('real network submit cancelled by authenticated retirement before delivery, stale ACK cannot start trial',async f=>{
 const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
 const identity=await a.identity(),attempt=await a.prepareNetwork(identity,{ssid:'new-network',password:'new-password',time_server:'pool.ntp.org'});
 const before=await f.command({op:'stats'});f.holdNext=true;await a.submitSetup(attempt);const held=f.socket;
 assert.equal((await f.command({op:'stats'})).setup_pending,true);
 await b.retire('test-password',await b.recovery(),a.retirementSelector);
 await f.command({op:'complete',socket:held});await f.time(6000);
 const after=await f.command({op:'stats'});assert.equal(after.trial_starts,before.trial_starts);assert.equal(after.profile_programs,before.profile_programs);assert.equal(after.profile_generation,identity.generation);
 assert.equal(await b.checkSetup(attempt),'failed');await assert.rejects(a.submitSetup(attempt),/already sent/);
});
for(const kind of ['network','station'])await run(`lost ${kind} preparation reply releases only its granted setup on retirement`,async f=>{
 const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);const transport=a.fetcher,identity=await a.identity(),old=a.retirementSelector;
 let preparationRequests=0;
 a.fetcher=async(p,o)=>{const response=await transport(p,o);if(p.endsWith('/request')&&++preparationRequests===(kind==='station'?2:1))throw new Error('lost setup preparation reply');return response;};
 const prepare=c=>kind==='network'?c.prepareNetwork(identity,{ssid:'new-network',password:'new-password',time_server:'pool.ntp.org'}):c.prepareStation(identity,{callsign:'K1ABC',locator:'FN42',powerDbm:30});
 const before=await f.command({op:'stats'});await assert.rejects(prepare(a));a.fetcher=transport;
 assert.equal((await f.command({op:'stats'})).setup_pending,true);
 await b.retire('test-password',await b.recovery(),old);assert.equal((await f.command({op:'stats'})).setup_pending,false);
 assert.equal((await f.command({op:'stats'})).profile_programs,before.profile_programs);
 // A corrected explicit preparation is immediately possible, no 180s expiry.
 const corrected=await prepare(b);assert.ok(corrected.digest);assert.equal((await b.request('status')).status,200);
});
await run('real network accepted delivery commits once; result receipt survives lost traffic and profile activation',async f=>{
 const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
 const attempt=await a.prepareNetwork(await a.identity(),{ssid:'new-network',password:'new-password',time_server:'pool.ntp.org'});
 const before=await f.command({op:'stats'}),transport=a.fetcher;let sends=0;
 a.fetcher=async(p,o)=>{const r=await transport(p,o);if(p.endsWith('/request')){sends++;throw new Error('submit reply lost after complete delivery');}return r;};
 await assert.rejects(a.submitSetup(attempt));assert.equal(sends,1);a.fetcher=transport;
 await f.time(5000);await f.time(6000);const after=await f.command({op:'stats'});
 assert.equal(after.profile_generation,attempt.generation);assert.ok(after.profile_programs>before.profile_programs);assert.equal(after.trial_starts,1);
 await f.command({op:'activate'});await f.time(7000);await f.login(a,'new-password');assert.equal(await a.checkSetup(attempt),'saved');
 assert.equal((await f.command({op:'stats'})).profile_programs,after.profile_programs);await assert.rejects(a.submitSetup(attempt),/already sent/);
});
await run('real network trial explicit failure retains previous durable profile and correctable receipt',async f=>{
 const a=f.client();await f.login(a);const attempt=await a.prepareNetwork(await a.identity(),{ssid:'unreachable',password:'new-password',time_server:'pool.ntp.org'});
 const before=await f.command({op:'stats'});await a.submitSetup(attempt);
 await f.command({op:'bench_network',linked:false,safe:true});await f.time(4000);await f.time(50000);
 const after=await f.command({op:'stats'});assert.equal(after.profile_programs,before.profile_programs);assert.equal(after.profile_generation,before.profile_generation);
 await f.command({op:'bench_network',linked:true,safe:true});await assert.rejects(a.request('status'));await f.login(a);assert.equal(await a.checkSetup(attempt),'failed');
 const corrected=await a.prepareNetwork(await a.identity(),{ssid:'test-network',password:'test-password',time_server:'pool.ntp.org'});await a.submitSetup(corrected);await f.time(53000);await f.time(54000);assert.equal((await f.command({op:'stats'})).profile_generation,corrected.generation);
});
for(const delivered of [false,true])await run(`real station commissioning ${delivered?'complete delivery commits exact receipt':'retirement cancels undelivered submit'}`,async f=>{
 const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
 const attempt=await a.prepareStation(await a.identity(),{callsign:'K1ABC',locator:'FN42',powerDbm:30});const before=await f.command({op:'stats'});
 f.holdNext=!delivered;await a.submitSetup(attempt);const socket=f.socket;
 if(!delivered){await b.retire('test-password',await b.recovery(),a.retirementSelector);await f.command({op:'complete',socket});}
 await f.time(3000);const after=await f.command({op:'stats'});
 assert.equal(after.profile_generation,delivered?attempt.generation:before.profile_generation);
 if(delivered){assert.ok(after.profile_programs>before.profile_programs);await f.command({op:'activate'});await f.time(4000);await f.login(a);assert.equal(await a.checkSetup(attempt),'saved');}
 else{assert.equal(after.profile_programs,before.profile_programs);assert.equal(await b.checkSetup(attempt),'failed');}
});
await run('failed station trial keeps exact receipt and accepts corrected explicit retry before terminal expiry',async f=>{
 const a=f.client();await f.login(a);const attempt=await a.prepareStation(await a.identity(),{callsign:'K1ABC',locator:'FN42',powerDbm:30});
 const before=await f.command({op:'stats'});f.holdNext=true;await a.submitSetup(attempt);const socket=f.socket;
 await f.command({op:'ack',socket,bytes:'65535'});await f.time(1000);await f.command({op:'bench_network',linked:false,safe:true,start_ok:false});await f.time(2000);
 const failed=await f.command({op:'stats'});assert.equal(failed.profile_generation,before.profile_generation);assert.equal(failed.profile_programs,before.profile_programs);assert.notEqual(failed.owner_slot,0);
 await f.command({op:'bench_network',linked:true,safe:true,start_ok:true});await assert.rejects(a.request('status'));await f.time(3000);await f.login(a);
 assert.equal(await a.checkSetup(attempt),'failed');
 const corrected=await a.prepareStation(await a.identity(),{callsign:'K2ABC',locator:'FN31',powerDbm:30});await a.submitSetup(corrected);await f.time(4000);
 assert.equal((await f.command({op:'stats'})).profile_generation,corrected.generation);assert.ok(f.now<60000);
});
await run('accepted restart keeps a committed network setup blocked until actual reboot',async f=>{
 const a=f.client();await f.login(a);const attempt=await a.prepareNetwork(await a.identity(),{ssid:'new-network',password:'new-password',time_server:'pool.ntp.org'});
 await a.submitSetup(attempt);await f.time(5000);await f.time(6000);const committed=await f.command({op:'stats'});assert.equal(committed.profile_generation,attempt.generation);
 const ack=await f.fetch('192.168.4.1',true,'/api/bootstrap/v1/ack',{method:'POST',marker:'Bootstrap',body:JSON.stringify(attempt.ack)});assert.equal(ack.status,200);assert.equal((await ack.json()).state,'accepted');
 await f.time(7000);assert.ok((await f.command({op:'stats'})).restarts>0);
 const pending=(await import('../src/network/bootstrap_web/crypto.js')).begin();
 const response=await f.fetch('192.168.4.1',true,'/api/bootstrap/v1/start',{method:'POST',marker:'Bootstrap',body:JSON.stringify({version:1,device_id:attempt.device,browser_public_key:pending.browserPublicKey,request_nonce:pending.requestNonce})});pending.secretKey.fill(0);
 assert.equal(response.status,409);const after=await f.command({op:'stats'});assert.equal(after.network_slot,0);assert.equal(after.profile_programs,committed.profile_programs);
});

for (const [callsign,locator,types] of [
  ['AA0NT/12','EM18',['type2']],['<AA0NT>','EM18IG',['type3']],
  ['PJ4/AA0NT','EM18IG',['type2','type3']],['W1A/AA0NT','EM18IG',['type2','type3']],['<W1A/AA0NT>','EM18IG',['type3']],['<AA0NT/12>','EM18IG',['type3']]
]) await run(`Type 2/3 actual station commissioning, activation and strict readback: ${callsign}`,async f=>{
 const a=f.client();await f.login(a);
 const support=await a.request('consumer/setup/api/owner/v1/wspr-support');
 assert.equal((await support.json()).station_encoding,'wspr_type123_auto');
 const before=(await (await a.request('config')).json()).config;
 const attempt=await a.prepareStation(await a.identity(),{callsign,locator,powerDbm:30});
 await a.submitSetup(attempt);await f.time(3000);await f.command({op:'activate'});await f.time(4000);await f.login(a);
 assert.equal(await a.checkSetup(attempt),'saved');await assert.rejects(a.submitSetup(attempt),/already sent/);
 const saved=(await (await a.request('config')).json()).config;
 assert.deepEqual(saved.station,{callsign,locator,power_dbm:30});assert.deepEqual(saved.wifi,before.wifi);assert.deepEqual(saved.pins,before.pins);assert.deepEqual(saved.schedules,before.schedules);
 const app=(await (await a.request('application/2')).json());
 assert.equal(app.schema,'transmitter-application/2');assert.deepEqual(app.wspr_plan.frame_types,types);
 assert.equal((await a.request('application')).status,409);
 const programs=(await f.command({op:'stats'})).profile_programs;
 const refused=await a.request('station/2','PUT',{schema:'transmitter-station/2',target:app.target,station:{callsign:'K1ABC',locator:'FN42',power_dbm:30}},(await a.request('config')).headers.get('ETag'));
 assert.equal(refused.status,409);assert.equal((await f.command({op:'stats'})).profile_programs,programs);
});
