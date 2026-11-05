import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import test from 'node:test';
import {launchUiFixture} from './ui_fixture_process.mjs';
import {parseProfileSelection} from './ui_fixture_profiles.mjs';
import {createDeadlineTools} from './browser_deadline.mjs';
class Child extends EventEmitter{
  pid=424242;exitCode=null;signalCode=null;
  stdout=Object.assign(new EventEmitter(),{destroy(){this.destroyed=true;}});
  stderr=Object.assign(new EventEmitter(),{destroy(){this.destroyed=true;}});
  kill(){this.exitCode=0;this.emit('exit',0,null);this.stdout.emit('end');return true;}
}
const record={name:'consumer-lan',url:'http://192.168.1.53/',proxy:'http://127.0.0.1:19000',pid:424242,driver_pid:424243,authority:'192.168.1.53'};
function fixture(options={}){const child=new Child(),server=launchUiFixture('/test/driver',19000,'/test/output',{profiles:['consumer-lan'],processGroup:false,spawnImpl:()=>child,...options});return {child,server};}
function publish(child,value=record){child.stdout.emit('data',Buffer.from(JSON.stringify(value)+'\nREADY; observed\n'));}

test('invalid selection and port inputs refuse before any child spawn',()=>{
  let calls=0;const spawnImpl=()=>{calls++;throw Error('must not spawn');};
  for(const profiles of [[],['unknown'],['consumer-lan','consumer-lan'],[''],['consumer-lan,engineering'],null])assert.throws(()=>launchUiFixture('/driver',19000,'/output',{profiles,spawnImpl}));
  for(const port of [0,-1,65536,1.5,NaN])assert.throws(()=>launchUiFixture('/driver',port,'/output',{spawnImpl}));
  assert.equal(calls,0);
  for(const args of [['--profiles='],['--profiles=consumer-lan,'],['--profiles=consumer-lan','--profiles=engineering'],['messages','messages'],['unknown']])assert.throws(()=>parseProfileSelection(args,19000));
});
test('sparse selection retains original offsets and default selection retains all definitions',()=>{
  assert.deepEqual(parseProfileSelection(['--profiles=engineering,consumer-lan'],19000).selected.map(value=>[value.name,value.index]),[['engineering',5],['consumer-lan',0]]);
  assert.equal(parseProfileSelection([],19000).selected.length,10);
  assert.throws(()=>parseProfileSelection(['--profiles=engineering'],65535),/port range/);
});
test('partial UTF-8/control records do not establish readiness until complete inventory',async()=>{
  const {child,server}=fixture();const bytes=Buffer.from(JSON.stringify({...record,synthetic_password:'λ'}));
  const split=bytes.indexOf(Buffer.from('λ'))+1;
  child.stdout.emit('data',bytes.subarray(0,split));assert.equal(server.records.size,0);
  child.stdout.emit('data',Buffer.concat([bytes.subarray(split),Buffer.from('\nREADY; observed\n')]));
  assert.equal((await server.ready)[0].driver_pid,424243);await server.stop();
  assert.equal(child.listenerCount('exit'),0);assert.equal(child.stdout.listenerCount('data'),0);assert.equal(child.stdout.destroyed,true);
});
test('wrong source identity, authority, port, type, and malformed inventory refuse',async()=>{
  for(const value of [{...record,pid:99},{...record,authority:'wrong'},{...record,proxy:'http://127.0.0.1:19001'},{...record,driver_pid:true},{...record,extra:true},null]){
    const {child,server}=fixture();const failed=assert.rejects(server.ready,/invalid readiness/);publish(child,value);await failed;await assert.rejects(server.stop(),/invalid readiness/);
  }
});
test('observed incomplete record times out, closes owned pipes, and cannot remain pending',async()=>{
  let now=0;const timers=new Set(),tools=createDeadlineTools({clock:()=>now,setTimer:fn=>{timers.add(fn);return fn;},clearTimer:fn=>timers.delete(fn)});
  const {child,server}=fixture({deadline:tools.deadlinePromise});const failed=assert.rejects(server.ready,/fixture-startup/);
  child.stdout.emit('data',Buffer.from('{"name":'));assert.equal(server.records.size,0);
  now=20001;for(const timer of [...timers])timer();await failed;await assert.rejects(server.stop(),/fixture-startup/);
  assert.equal(timers.size,0);assert.equal(child.stdout.destroyed,true);assert.equal(child.stderr.destroyed,true);
});
test('late nonzero owner exit after READY remains a failed finalization',async()=>{
  const {child,server}=fixture();publish(child);await server.ready;
  child.exitCode=17;child.emit('exit',17,null);await assert.rejects(server.stop(),/child_exit=17/);
});
test('expired enclosing acquisition cannot spawn an unowned child',()=>{
  let calls=0;assert.throws(()=>launchUiFixture('/driver',19000,'/output',{spawnImpl:()=>{calls++;},deadline:()=>{throw Error('enclosing deadline expired');}}),/enclosing deadline/);assert.equal(calls,0);
});
