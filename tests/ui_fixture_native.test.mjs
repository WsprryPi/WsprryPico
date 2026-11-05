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
async function nativeChildren(group,expected){
  const rows=[];
  if(process.platform==='linux'){
    for(const entry of await readdir('/proc')){
      if(!/^\d+$/.test(entry))continue;
      try{
        const text=await readFile(`/proc/${entry}/stat`,'utf8'),fields=text.slice(text.lastIndexOf(') ')+2).split(' ');
        if(Number(fields[2])===group&&Number(entry)!==group&&fields[0]!=='Z')rows.push({pid:Number(entry),parent:Number(fields[1]),executable:await readlink(`/proc/${entry}/exe`)});
      }catch(error){if(error.code!=='ENOENT'&&error.code!=='ESRCH')throw error;}
    }
  }else{
    const {stdout}=await execute('ps',['-axo','pid=,ppid=,pgid=,comm='],{timeout:5000});
    for(const line of stdout.split('\n')){const match=line.trim().match(/^(\d+)\s+(\d+)\s+(\d+)\s+(.*)$/);if(match&&Number(match[3])===group&&Number(match[1])!==group)rows.push({pid:Number(match[1]),parent:Number(match[2]),executable:match[4]});}
  }
  assert.equal(rows.length,expected.length,'OS inventory must contain exactly the selected native drivers');
  assert.deepEqual(rows.map(value=>value.pid).sort((a,b)=>a-b),expected.map(value=>value.driver_pid).sort((a,b)=>a-b));
  const binary=await realpath(driver);
  for(const row of rows){assert.equal(row.parent,group);assert.ok(row.executable===binary||(process.platform!=='linux'&&row.executable===path.basename(binary)),'each process must execute the actual candidate driver');}
}
async function owned(t,port,profiles,check){
  const output=await mkdtemp(path.join(os.tmpdir(),'pico-selected-profiles-'));
  const server=launchUiFixture(driver,port,output,{profiles});let primary;
  try{const records=await server.ready;await nativeChildren(server.process.pid,records);await check(records,t.signal);}
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
