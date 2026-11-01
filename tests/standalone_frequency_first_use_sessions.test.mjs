// Real consumer session crypto -> production HTTP/API -> independent RAM journals.
import assert from 'node:assert/strict';
import {Fixture} from './consumer_sessions.test.mjs';
import {p256} from '../src/network/bootstrap_web/node_modules/@noble/curves/nist.js';
globalThis.WsprryPicoOwnerKey={keygen:()=>p256.keygen(),getPublicKey:(key,compressed)=>p256.getPublicKey(key,compressed)};
for (const mode of ['network','network-backing','usb','overlay']) {
  const f=new Fixture(process.argv[2]);
  try {
    await f.command({op:'first_use_profile',mode});await f.time(1000);
    const a=f.client();await f.login(a);
    const read=async resource=>{const r=await a.request(resource);assert.equal(r.status,200);return {data:await r.json(),revision:r.headers.get('etag')};};
    let station=await read('station'),frequency=await read('standalone-frequency');
    assert.equal(station.data.station!==null,mode==='overlay');
    assert.equal(frequency.data.frequency_hz,mode==='overlay'?14095600:null);assert.equal(frequency.data.storage_healthy,true);
    const initial=await f.command({op:'frequency_state'});
    if(mode==='overlay') assert.equal(initial.sequence,'0','overlay readiness needs no standalone journal');
    else {
      const body={schema:frequency.data.schema,target:frequency.data.target,frequency_hz:14095600};
      const refused=await a.request('standalone-frequency','PUT',body,frequency.revision);
      assert.equal(refused.status,409);assert.equal((await refused.json()).error.code,'not_configured');
      assert.deepEqual(await f.command({op:'frequency_state'}),initial);
      const p=await read('progress');
      const draft=await a.request('progress/update','POST',{schema:p.data.schema,target:p.data.target,request_id:'d'.repeat(32),fields:{callsign:'AA0NT',locator:'EM18',power_dbm:37}},p.revision);
      assert.equal(draft.status,200);const saved=await draft.json();
      assert.equal(saved.station_complete,true);assert.equal(saved.applied_station,null);
      assert.equal((await read('station')).data.station,null);
      frequency=await read('standalone-frequency');
      assert.equal((await a.request('standalone-frequency','PUT',body,frequency.revision)).status,409);
      assert.deepEqual(await f.command({op:'frequency_state'}),initial);
      const attempt=await a.prepareStation(await a.identity(),{callsign:'AA0NT',locator:'EM18',powerDbm:37,progressRevision:draft.headers.get('etag')});
      await a.submitSetup(attempt);await f.time(3000);await f.command({op:'reboot'});await f.time(4000);await f.login(a);
      assert.equal(await a.checkSetup(attempt),'saved');
    }
    station=await read('station');assert.equal(station.data.station.callsign,'AA0NT');
    frequency=await read('standalone-frequency');assert.equal(frequency.data.frequency_hz,mode==='network-backing'?null:14095600);
    const selected=await a.request('standalone-frequency','PUT',{schema:frequency.data.schema,target:frequency.data.target,frequency_hz:14095600},frequency.revision);
    const body=await selected.json();assert.equal(selected.status,200,JSON.stringify(body));assert.equal(body.frequency_hz,14095600);
    const accepted=await f.command({op:'frequency_state'});assert.equal(accepted.saved_dial_hz,14095600);assert.equal(accepted.enabled,false);
    assert.equal((await read('status')).data.job.output_active,false);
    await f.command({op:'reboot'});await f.time(5000);await f.login(a);
    assert.equal((await read('standalone-frequency')).data.frequency_hz,14095600);
    assert.deepEqual(await f.command({op:'frequency_state'}),accepted);
    assert.equal((await read('status')).data.job.output_active,false);
    await f.command({op:'message_review'}); // Saved settings are boot-applied in the target application.
    let progress=await read('progress');
    let draft=await a.request('progress/update','POST',{schema:progress.data.schema,target:progress.data.target,request_id:'e'.repeat(32),fields:{enabled:true,schedules:[{period_s:240,phase_s:0}]}},progress.revision);
    assert.equal(draft.status,200);let saved=await draft.json();
    assert.equal((await f.command({op:'frequency_state'})).enabled,false,'enable draft alone never starts RF');
    let applied=await a.request('progress/apply','POST',{schema:progress.data.schema,target:progress.data.target,application:{draft_revision:saved.draft_revision,domain:'radio'}},draft.headers.get('etag'));
    assert.equal(applied.status,200,JSON.stringify(await applied.json()));
    assert.equal((await f.command({op:'frequency_state'})).enabled,true);
    const before=await f.command({op:'schedule_tick',delta_ns:'0'}),now=BigInt(before.utc_now_ns),period=240000000000n;
    let start=now/period*period+1000000000n;if(start-now<10000000000n)start+=period;
    assert.equal((await f.command({op:'schedule_tick',delta_ns:String(start-now-5000000000n)})).state,'armed');
    const job=await f.command({op:'accepted_job',surface:'consumer'});assert.equal(job.mode,'wspr');assert.equal(job.events.length,162);
    assert.equal((await f.command({op:'schedule_tick',delta_ns:'5000000000'})).state,'running');
    assert.equal((await f.command({op:'schedule_tick',delta_ns:'110592000000'})).state,'complete');
    progress=await read('progress');
    draft=await a.request('progress/update','POST',{schema:progress.data.schema,target:progress.data.target,request_id:'f'.repeat(32),fields:{enabled:false}},progress.revision);
    assert.equal(draft.status,200);saved=await draft.json();
    assert.equal((await f.command({op:'frequency_state'})).enabled,true);
    applied=await a.request('progress/apply','POST',{schema:progress.data.schema,target:progress.data.target,application:{draft_revision:saved.draft_revision,domain:'radio'}},draft.headers.get('etag'));
    assert.equal(applied.status,200,JSON.stringify(await applied.json()));
    assert.equal((await f.command({op:'frequency_state'})).enabled,false);
    await f.command({op:'schedule_tick',delta_ns:'240000000000'});
    assert.deepEqual(await f.command({op:'accepted_job',surface:'consumer'}),job,'disabled schedule cannot submit a later job');
    if(mode==='overlay') {
      const fresh=await read('standalone-frequency'),transport=a.fetcher;
      let sends=0;
      a.fetcher=async(...args)=>{const reply=await transport(...args);++sends;throw Error('Lost reply after committed frequency');};
      await assert.rejects(a.request('standalone-frequency','PUT',{schema:fresh.data.schema,target:fresh.data.target,frequency_hz:7038600},fresh.revision),/Lost reply/);
      a.fetcher=transport;
      const committed=await f.command({op:'frequency_state'});
      assert.equal(committed.saved_dial_hz,7038600);assert.equal(committed.enabled,false);assert.equal(sends,1);
      await f.time(6000);await f.login(a);
      assert.equal((await read('standalone-frequency')).data.frequency_hz,7038600);
      await f.command({op:'reboot'});await f.time(7000);await f.login(a);
      assert.equal((await read('standalone-frequency')).data.frequency_hz,7038600);
      assert.deepEqual(await f.command({op:'frequency_state'}),committed);assert.equal(sends,1,'ambiguous commit is never repeated');
    }
    console.log('PASS first-use '+mode+': guarded station draft, explicit application, first dial, reboot, schedule enable/apply, WSPR armed/running/complete, disable/apply, no later job; inhibited output');
  } finally {await f.stop();}
}
