// Real three-session carrier/AEAD -> production dispatch -> durable progress.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {Fixture} from './consumer_sessions.test.mjs';
import {p256} from '../src/network/bootstrap_web/node_modules/@noble/curves/nist.js';
import {x25519} from '../src/network/bootstrap_web/node_modules/@noble/curves/ed25519.js';
const f=new Fixture(process.argv[2]);let assertions=0;const samples=[];
const equal=(a,b)=>{assert.deepEqual(a,b);++assertions;};
try {
 await f.time(1000);const a=f.client(),b=f.client(),c=f.client('192.168.4.1',true);
 await f.login(a);await f.time(2000);await f.login(b);await f.time(3000);await f.login(c);
 const read=async client=>{const r=await client.request('progress');equal(r.status,200);const data=await r.json();samples.push(data);return {data,revision:r.headers.get('etag')};};
 const initial=await read(a),before=await f.command({op:'stats'});
 let serial=0;
 const save=(client,fields,saved)=>client.request('progress/update','POST',{schema:'transmitter-progress/1',target:saved.data.target,request_id:(++serial).toString(16).padStart(32,'0'),fields},saved.revision);
 let r=await save(a,{callsign:'AA0NT/09',power_dbm:'2147483648'},initial);equal(r.status,200);
 const ack=await r.json();samples.push(ack);equal(ack.outcomes,{callsign:'saved',power_dbm:'invalid'});
 equal((await save(b,{locator:'EM18IG'},initial)).status,412);
 let current=await read(b);equal(current.data.fields,{callsign:'AA0NT/09'});
 r=await save(b,{enabled:false,schedules:[{period_s:'2147483648',phase_s:0}],expires_utc_s:'2208988800'},current);equal(r.status,200);
 equal((await r.json()).outcomes,{enabled:'saved',schedules:'invalid',expires_utc_s:'invalid'});
 current=await read(c);const stale=current;
 equal((await save(c,{callsign:'AA0NT/09'},current)).status,200);
 current=await read(a);equal((await save(a,{callsign:'BB1BB'},current)).status,200);
 current=await read(b);equal((await save(b,{callsign:'AA0NT/09'},current)).status,200);
 equal((await save(c,{locator:'EM18'},stale)).status,412);
 // Drop one actual committed reply. Reauthentication/readback never replays it.
 current=await read(a);const fetcher=a.fetcher;
 a.fetcher=async(path,options)=>{const result=await fetcher(path,options);if(path.endsWith('/request'))throw Error('lost reply after dispatch');return result;};
 await assert.rejects(save(a,{locator:null},current));++assertions;a.fetcher=fetcher;
 const committed=await read(b);equal(committed.data.fields.locator,null);
 const sequence=committed.data.draft_revision;
 await c.logout();await f.time(4000);await f.login(a);equal((await read(a)).data.draft_revision,sequence);
 equal((await b.request('status')).status,200);equal((await read(b)).data.draft_revision,sequence);
 const after=await f.command({op:'stats'});
 for(const k of ['profile_generation','profile_programs','config_sequence','trial_starts','api_restarts']) equal(after[k],before[k]);
 for(const path of ['/api/owner/v1/progress','/api/owner/v1/progress/start','/api/owner/v1/claim/progress/start'])
   equal((await f.fetch('192.168.1.53',false,path,{marker:'Owner',method:path.endsWith('start')?'POST':'GET',body:path.endsWith('start')?'{}':''})).status,403);
 const publicRead=await f.fetch('192.168.4.1',true,'/api/owner/v1/progress',{marker:'Owner'});
 const publicData=await publicRead.json(),owner=p256.keygen(),browser=x25519.keygen();
 samples.push(publicData);
 const start={version:1,device_id:publicData.target.device_id,owner_public_key:Buffer.from(p256.getPublicKey(owner.secretKey,false)).toString('base64url'),browser_public_key:Buffer.from(browser.publicKey).toString('base64url'),browser_nonce:'a'.repeat(32),profile_source:5,generation:after.profile_generation,progress_revision:publicRead.headers.get('etag')};
 equal((await f.fetch('192.168.4.1',true,'/api/owner/v1/progress/start',{marker:'Owner',method:'POST',body:JSON.stringify(start)})).status,200);
 owner.secretKey.fill(0);browser.secretKey.fill(0);
 for(const [path,status] of [['/api/owner/v1/progress/submit',400],['/api/owner/v1/claim/submit',403]])
   equal((await f.fetch('192.168.4.1',true,path,{marker:'Owner',method:'POST',body:'{}'})).status,status);
 console.log(execFileSync('python3',[fileURLToPath(new URL('./progress_schema_tests.py',import.meta.url))],{input:JSON.stringify(samples),encoding:'utf8'}).trim());
 console.log(`PASS progress three-client conflicts, same-value/A-B-A, lost reply/readback, logout isolation and AP admission: ${assertions} assertions`);
} finally {await f.stop();}
