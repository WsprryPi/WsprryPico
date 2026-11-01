// Noble client -> production HTTP, session crypto, API, journals and listener.
// No manual profile activation or reboot is allowed during the continuity check.
import assert from 'node:assert/strict';
import {Fixture} from './consumer_sessions.test.mjs';
import {begin,authenticate,open} from '../src/network/bootstrap_web/radio-crypto.js';

for (const ap of [false,true]) {
  const f=new Fixture(process.argv[2]);
  try {
    await f.time(1000);
    await f.command({op:'production_listeners'});
    const host=ap?'192.168.4.1':'192.168.1.53';
    const a=f.client(host,ap), b=f.client(host,ap);
    await f.login(a);await f.time(2000);await f.login(b);
    const oldIdentity=await a.identity();
    const read=await a.request('config'),before=await read.json(),etag=read.headers.get('etag');
    const oldA=a.state, oldB=b.state, startedA=a.started,startedB=b.started;
    const beforeStats=await f.command({op:'stats'});
    // A third login is admitted before transfer, with its original transcript.
    await f.time(3000);
    const pending=begin();
    const grant=await (await f.fetch(host,ap,'/api/consumer/v1/start',{method:'POST',body:JSON.stringify({version:1,device_id:oldIdentity.device_id,boot_id:oldIdentity.boot_id,generation:oldIdentity.generation,public_key:pending.public_key,nonce:pending.nonce})})).json();
    const third=authenticate(pending,grant,'test-password',oldIdentity);
    // Admit a recovery proof before the authority transfer, then defer only
    // its finish request. The original proof and selector must remain valid.
    const recovery=f.client(host,ap), discovery=await recovery.recovery();
    const thirdSelector=discovery.sessions.find(s=>s.state==='pending').selector;
    let resumeRecovery, recoveryReady;
    const ready=new Promise(resolve=>recoveryReady=resolve);
    const gate=new Promise(resolve=>resumeRecovery=resolve);
    const recoveryFetch=recovery.fetcher;
    recovery.fetcher=async(path,options)=>{
      if(path.endsWith('/recovery/finish')) {recoveryReady();await gate;}
      return recoveryFetch(path,options);
    };
    const retirement=recovery.retire('test-password',discovery,thirdSelector);
    await ready;
    const patch=power=>({schema:'config-update',target:{scope:'member',device_id:oldIdentity.device_id,boot_id:oldIdentity.boot_id},mode:'merge',config:{station:{power_dbm:power}}});
    // Invalid/stale input must not start authority transfer.
    assert.equal((await a.request('config/update','POST',patch(1),etag)).status,400);
    assert.equal((await a.request('config/update','POST',patch(0),'"stale"')).status,412);
    assert.equal((await f.command({op:'stats'})).profile_generation,beforeStats.profile_generation);
    f.holdNext=true;
    assert.equal((await b.request('station')).status,200);
    const heldSocket=f.socket;
    const changed=await a.request('config/update','POST',patch(0),etag);
    assert.equal(changed.status,200,JSON.stringify(await changed.json()));
    await f.command({op:'complete',socket:heldSocket});
    assert.equal(a.state,oldA);assert.equal(b.state,oldB);
    assert.equal(a.started,startedA);assert.equal(b.started,startedB);
    assert.equal((await b.request('config/update','POST',patch(3),etag)).status,412);
    // Finishing the already admitted handshake must use its unchanged binding.
    const finish=await f.fetch(host,ap,'/api/consumer/v1/finish',{method:'POST',body:third.finish,headers:{'Content-Type':'application/octet-stream'}});
    assert.equal(finish.status,200);assert.equal(open(third,0n,new Uint8Array(await finish.arrayBuffer())).authenticated,true);
    resumeRecovery();
    assert.equal((await retirement).present,true);
    await a.readPolicy();await b.readPolicy();
    const currentRead=await b.request('config'),current=await currentRead.json();
    assert.equal(current.config.station.power_dbm,0);
    assert.deepEqual(current.config,{...before.config,station:{...before.config.station,power_dbm:0}});
    const setupStatus=await (await a.request('consumer/setup/api/owner/v1/public-status')).json();
    assert.equal(setupStatus.claim_available,false,'established Config station cannot revert to a profile-owned snapshot');
    const transferred=await f.command({op:'stats'});
    const noop=await a.request('config/update','POST',patch(0),currentRead.headers.get('etag'));
    assert.equal(noop.status,200);
    assert.equal((await f.command({op:'stats'})).config_sequence,transferred.config_sequence);
    assert.equal((await f.command({op:'stats'})).profile_programs,transferred.profile_programs);
    await f.time(f.now+61000);
    assert.equal((await a.request('status')).status,200);assert.equal((await b.request('status')).status,200);
    const identity=await a.identity();assert.equal(identity.boot_id,oldIdentity.boot_id);
    assert.equal((await a.publicRead('config')).status,200);
    assert.equal((await f.fetch(host,ap,'/station')).status,200);
    const stats=await f.command({op:'stats'});assert.equal(stats.api_restarts,0);assert.equal(stats.restarts||0,0);
    // Authority-changing profile writes must still close the old sessions.
    await f.command({op:'generation'});
    await assert.rejects(a.request('status'));await assert.rejects(b.request('status'));
    // Reconstruct journals/runtime only after proving live continuity.
    await f.command({op:'reboot'});await f.time(f.now+1000);const after=f.client(host,ap);await f.login(after);
    assert.equal((await (await after.request('config')).json()).config.station.power_dbm,0);
    console.log(`PASS live station Apply: ${ap?'AP':'LAN'}, three retained transcripts, stale/no-op/readback, 61s, reboot persistence`);
  } finally {await f.stop();}
}

// Independently pinned encoder oracle: prove the production scheduler consumes
// the new power rather than a retained profile snapshot. All RF is simulated.
{
  const {readFile}=await import('node:fs/promises');
  const f=new Fixture(process.argv[2]);
  try {
    const a=f.client();await f.login(a);
    const identity=await a.identity(),read=await a.request('config');
    const body={schema:'config-update',target:{scope:'member',device_id:identity.device_id,boot_id:identity.boot_id},mode:'merge',config:{station:{power_dbm:20}}};
    const changed=await a.request('config/update','POST',body,read.headers.get('etag'));assert.equal(changed.status,200);
    const enabled=await a.request('config/update','POST',{...body,config:{enabled:true}},changed.headers.get('etag'));assert.equal(enabled.status,200);
    await f.command({op:'schedule_tick',delta_ns:'115000000000'});
    const job=await f.command({op:'accepted_job',surface:'consumer'});assert.equal(job?.mode,'wspr');assert.equal(job.events.length,162);
    const frequencies=[...new Set(job.events.map(e=>e.frequency_nhz))].sort((a,b)=>BigInt(a)<BigInt(b)?-1:1);
    const symbols=job.events.map(e=>String(frequencies.indexOf(e.frequency_nhz))).join('');
    const oracle=await readFile(new URL('./wspr_plan_vectors.hpp',import.meta.url),'utf8');
    const expected=oracle.match(/\{"AA0NT", "EM18", 20, 1,\s*"([0-3]+)"\s*"([0-3]+)"/);
    assert.ok(expected);assert.equal(symbols,expected[1]+expected[2]);
    const before=await f.command({op:'stats'});
    assert.equal((await a.request('config/update','POST',body,enabled.headers.get('etag'))).status,409);
    assert.equal((await f.command({op:'stats'})).config_sequence,before.config_sequence);
    console.log('PASS next scheduled WSPR frame matches independent power-20 oracle; armed edit refuses before writes');
  } finally {await f.stop();}
}

// A transfer between the policy reply and identity observation must trigger
// only a bounded policy reread, never retirement of an otherwise valid login.
{
  const f=new Fixture(process.argv[2]);
  try {
    const a=f.client(),b=f.client();await f.login(a);await f.time(2000);await f.login(b);
    const identity=await a.identity(),read=await a.request('config');
    const keys=b.state,started=b.started;let interleaved=false;
    const fetcher=b.fetcher;
    b.fetcher=async(path,options)=>{
      if(path==='/api/consumer/v1/identity' && !interleaved) {
        interleaved=true;
        const reply=await a.request('config/update','POST',{schema:'config-update',target:{scope:'member',device_id:identity.device_id,boot_id:identity.boot_id},mode:'merge',config:{station:{power_dbm:0}}},read.headers.get('etag'));
        assert.equal(reply.status,200);
      }
      return fetcher(path,options);
    };
    await b.readPolicy();assert.ok(interleaved);assert.equal(b.state,keys);assert.equal(b.started,started);
    assert.equal((await b.request('status')).status,200);
    console.log('PASS station transfer interleaved with policy read preserves original login and uses only read-only reread');
  } finally {await f.stop();}
}

// A retained login must use the current reserved profile generation for a
// later Wi-Fi receipt, while Wi-Fi changes still invalidate that login.
{
  const f=new Fixture(process.argv[2]);
  try {
    const a=f.client();await f.login(a);const oldIdentity=await a.identity();
    const read=await a.request('config');
    assert.equal((await a.request('config/update','POST',{schema:'config-update',target:{scope:'member',device_id:oldIdentity.device_id,boot_id:oldIdentity.boot_id},mode:'merge',config:{station:{power_dbm:0}}},read.headers.get('etag'))).status,200);
    const current=await a.identity();
    const prepared=await a.prepareNetwork(oldIdentity,{ssid:'updated-network',password:'updated-password',time_server:'192.0.2.1'});
    assert.equal(prepared.generation,(BigInt(current.generation)+1n).toString());
    await a.submitSetup(prepared);await f.time(f.now+3001);
    await assert.rejects(a.request('status'));
    await f.command({op:'activate'});await f.time(f.now+1000);
    const fresh=f.client();await f.login(fresh,'updated-password');
    assert.equal(await fresh.checkSetup(prepared),'saved');
    assert.equal((await (await fresh.request('config')).json()).config.station.power_dbm,0);
    console.log('PASS Wi-Fi save after live station transfer uses current receipt, retires old login, and preserves Config station');
  } finally {await f.stop();}
}
