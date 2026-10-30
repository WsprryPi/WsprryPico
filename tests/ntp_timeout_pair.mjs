// SPDX-License-Identifier: MIT
// Actual unchanged Pi clients/coordinator plus candidate Pico handlers/journals.
// RAM-backed fixtures only; no physical USB, RF, services or operator settings.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import path from 'node:path';
const [carrier,first,second]=process.argv.slice(2);
if(!['network','usb'].includes(carrier)||!first||!second)
  throw Error('Usage: node ntp_timeout_pair.mjs network BUILD PI_SOURCE | usb PAIR_CLIENT PICO_DRIVER');
const children=[];
function start(command,args=[]) {
  const child=spawn(command,args,{stdio:['pipe','pipe','inherit']});children.push(child);
  const queued=[],waiting=[];
  createInterface({input:child.stdout}).on('line',line=>waiting.length?waiting.shift().resolve(line):queued.push(line));
  child.on('error',error=>{for(const waiter of waiting.splice(0))waiter.reject(error);});
  child.on('exit',code=>{for(const waiter of waiting.splice(0))waiter.reject(Error('Fixture exited '+code));});
  const line=()=>queued.length?Promise.resolve(queued.shift()):new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(Error('Production pair response deadline')),45000);
    waiting.push({resolve:value=>{clearTimeout(timer);resolve(value);},reject:error=>{clearTimeout(timer);reject(error);}});
  });
  return {child,line,send:async command=>{child.stdin.write(command+'\n');return line();}};
}
const config={version:1,enabled:false,station:{callsign:'AA0NT',locator:'EM18',power_dbm:20},wifi:{ssid:'synthetic-network',password:'synthetic-password',ntp_ipv4:'pool.ntp.org'},schedules:[{period_s:120,phase_s:0}]};
const protectedSave=async (call,fields,revision)=>{
  const current=await call({method:'GET',path:'/api/control/v1/member/configuration'});
  assert.equal(current.status,200,JSON.stringify(current));
  assert.equal(current.body.config.version,1,'historical public Config remains version 1');
  const body={schema:'wsprrypi-pico-settings/1',target:current.body.target,operation:'save',config:fields};
  return call({method:'POST',path:'/api/control/v1/member/configuration',revision:revision||current.etag,body:JSON.stringify(body)});
};
try {
  if(carrier==='network') {
    const server=start(path.join(first,'pico_tls_server'),['0','a','settings']);
    assert.match(await server.line(),/^READY /);
    const dump=async()=>JSON.parse((await server.send('DUMP')).replace(/^DUMP /,''));
    const initial=await dump();
    const candidate={...initial.config,version:2,enabled:false,ntp_timeout_s:0,wifi:{...initial.config.wifi,password:'synthetic-password'}};
    assert.equal(JSON.parse(await server.send('CONFIG '+JSON.stringify(candidate))).ok,true);
    const original=await dump();assert.equal(original.config.ntp_timeout_s,0);assert.equal(original.config.version,2);
    const client=start(path.join(first,'wtp_configuration_client'),[path.join(first,'credentials-v3')]);
    const call=async request=>JSON.parse(await client.send(JSON.stringify(request)));
    const firstSave=await protectedSave(call,{station:{callsign:'W1AW'}});assert.equal(firstSave.status,200,JSON.stringify(firstSave));
    let saved=await dump();assert.equal(saved.config.ntp_timeout_s,0);assert.equal(saved.config.station.callsign,'W1AW');
    const context=await call({method:'GET',path:'/api/control/v1/member/configuration'});
    const next=await protectedSave(call,{schedules:[{period_s:240,phase_s:0}],wifi:{ntp_ipv4:'192.0.2.1'}});
    assert.equal(next.status,200,JSON.stringify(next));saved=await dump();
    assert.equal(saved.config.ntp_timeout_s,0);assert.equal(saved.config.version,2);
    assert.equal(saved.password_sha256,original.password_sha256);assert.equal(saved.cursor,original.cursor);
    const stale=await protectedSave(call,{expires_utc_s:0},context.etag);assert.equal(stale.status,412);
    assert.equal((await dump()).generation,saved.generation,'stale request refuses before persistence');
    const unknown=await protectedSave(call,{version:2});assert.equal(unknown.status,400);
    assert.equal((await dump()).generation,saved.generation,'historical public view cannot gain Config v2 authority');
    console.log('PASS actual Pi HTTPS coordinator/current Pico: stored zero, legacy Config views, scoped writes, password/cursor preservation and refusal before writes');
  } else {
    const client=start(first,[second]);
    const call=async request=>JSON.parse(await client.send(JSON.stringify(request)));
    const raw=async(resource,method='GET',body,revision)=>call({raw_resource:resource,method,body:body===undefined?'':JSON.stringify(body),revision:revision||''});
    const wifi=await raw('/api/usb/v1/wifi');assert.equal(wifi.status,200,JSON.stringify(wifi));
    const joined=await raw('/api/usb/v1/wifi','PUT',{schema:'wifi',target:wifi.body.target,
      wifi:{ssid:config.wifi.ssid,password:config.wifi.password,time_server:config.wifi.ntp_ipv4}},wifi.etag);
    assert.equal(joined.status,200,JSON.stringify(joined));
    let read=await raw('/api/control/v1/ntp-timeout');assert.equal(read.status,200,JSON.stringify(read));
    const complete=await raw('/api/control/v1/config','PUT',config,read.etag);assert.equal(complete.status,200,JSON.stringify(complete));
    read=await raw('/api/control/v1/ntp-timeout');
    const write={schema:'ntp-timeout',target:read.body.target,timeout_s:0};
    const saved=await raw('/api/control/v1/ntp-timeout','PUT',write,read.etag);assert.equal(saved.status,200,JSON.stringify(saved));
    assert.equal(saved.body.saved_timeout_s,0);assert.equal(saved.body.pending_restart,true);
    assert.equal((await raw('/api/control/v1/ntp-timeout')).status,409);
    for(const patch of [{schema:'ntp-timeout'},{schema:'ntp-timeout'},{timeout_s:1},{timeout_s:true},{extra:1},{target:[]},{target:{...write.target,device_id:'b'.repeat(32)}}]) {
      const bad=await raw('/api/control/v1/ntp-timeout','PUT',{...write,...patch},saved.etag);
      assert.equal(bad.status,patch.target&&!Array.isArray(patch.target)?409:400,JSON.stringify(bad));
      const current=await raw('/api/control/v1/ntp-timeout');assert.equal(current.etag,saved.etag);assert.equal(current.body.saved_timeout_s,0);
    }
    const next=await protectedSave(call,{station:{callsign:'W1AW'}});assert.equal(next.status,200,JSON.stringify(next));
    read=await raw('/api/control/v1/ntp-timeout');assert.equal(read.body.saved_timeout_s,0);
    const refusal=await raw('/api/control/v1/ntp-timeout','PUT',{...write,timeout_s:60},saved.etag);assert.equal(refusal.status,412);
    assert.equal((await raw('/api/control/v1/ntp-timeout')).etag,read.etag);
    console.log('PASS actual production UMP/ACK Pi/Pico pair: zero timeout, exact version/target/revision/type refusal and legacy scoped-save preservation');
  }
} finally {
  for(const child of children.reverse())if(child.exitCode===null) {
    await new Promise(resolve=>{const timer=setTimeout(()=>child.kill('SIGKILL'),3000);child.once('exit',()=>{clearTimeout(timer);resolve();});child.kill('SIGTERM');});
  }
}
