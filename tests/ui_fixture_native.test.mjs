import {qualifyNativeChildren} from './ui_fixture_inventory.mjs';
// Real native driver inventory and public handlers, independent of echoed labels.
import assert from 'node:assert/strict';
import test from 'node:test';
import {readdir,readFile,readlink,realpath,mkdtemp,rm,access} from 'node:fs/promises';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import os from 'node:os';
import path from 'node:path';
import {launchUiFixture} from './ui_fixture_process.mjs';
import {preserveCleanup} from './browser_deadline.mjs';
import {RadioClient} from '../src/network/bootstrap_web/radio-client.js';
const execute=promisify(execFile),driver=process.argv[2];
if(!driver)throw Error('Actual consumer_bootstrap_driver path required');
await access(driver);
async function owned(t,port,profiles,check){
  const output=await mkdtemp(path.join(os.tmpdir(),'pico-selected-profiles-'));
  const server=launchUiFixture(driver,port,output,{profiles});let primary;
  try{const records=await server.ready;await qualifyNativeChildren(driver,server.process.pid,records);await check(records,t.signal);}
  catch(error){primary=error;throw error;}
  finally{await preserveCleanup(primary,[async()=>{await server.stop();await rm(output,{recursive:true,force:true});}]);}
}
async function publicConfig(record,signal,iface){
  const client=new RadioClient((resource,options={})=>fetch(record.proxy+resource,{...options,signal:AbortSignal.any([signal,...(options.signal?[options.signal]:[])])}),()=>1000,{authority:record.authority,interface:iface});
  const identity=await client.identity();assert.equal(identity.version,1);assert.equal(identity.device_id,'1'.repeat(32));
  const response=await client.publicRead('config');assert.equal(response.status,200);const body=await response.json();assert.equal(body.contract,'Wsprry-Control/1');return body.config;
}

test('pilot selection starts exactly one actual native driver and serves applied settings',{timeout:20000},async t=>{
  await owned(t,19439,['consumer-lan'],async(records,signal)=>{
    assert.deepEqual(records.map(value=>value.name),['consumer-lan']);assert.equal(records[0].proxy,'http://127.0.0.1:19439');
    const config=await publicConfig(records[0],signal,'station');assert.ok(config&&typeof config==='object'&&!Array.isArray(config));assert.ok(config.station);
  });
});
test('sparse reordered selection preserves original offsets, authority, and actual profile state',{timeout:20000},async t=>{
  await owned(t,19459,['network-only','consumer-lan'],async(records,signal)=>{
    const network=records.find(value=>value.name==='network-only'),consumer=records.find(value=>value.name==='consumer-lan');
    assert.equal(network.proxy,'http://127.0.0.1:19461');assert.equal(network.authority,'192.168.4.1');
    assert.equal(consumer.proxy,'http://127.0.0.1:19459');assert.equal(consumer.authority,'192.168.1.53');
    assert.equal(await publicConfig(network,signal,'ap'),null,'network-only handler must not expose an applied station');
    assert.ok(await publicConfig(consumer,signal,'station'),'configured handler must remain independent');
  });
});
test('omitting selection retains all ten original opt-in profiles and their ports',{timeout:20000},async t=>{
  await owned(t,19479,undefined,async records=>{
    assert.deepEqual(records.map(value=>value.name),['consumer-lan','blank','network-only','unavailable','consumer-ap','engineering','first-use-network','first-use-usb','first-use-overlay','first-use-network-backing']);
    assert.deepEqual(records.map(value=>Number(new URL(value.proxy).port)),[19479,19480,19481,19482,19483,19484,19485,19486,19487,19488]);
  });
});
