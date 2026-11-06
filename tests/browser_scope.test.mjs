import assert from 'node:assert/strict';
import test from 'node:test';
import {EventEmitter} from 'node:events';
import {BrowserScope} from './browser_scope.mjs';
import {createDeadlineTools} from './browser_deadline.mjs';
const leaves=error=>error instanceof AggregateError?error.errors.flatMap(leaves):[error];
const deferred=()=>{let resolve;const promise=new Promise(value=>resolve=value);return {promise,resolve};};
function noHooks(host){assert.equal(host.listenerCount('SIGTERM'),0);assert.equal(host.listenerCount('SIGINT'),0);}

test('failed acquisition closes previously owned resources and restores handlers',async()=>{
  const host=new EventEmitter(),owner=new BrowserScope({processImpl:host}),closed=[];const primary=Error('acquisition failed');
  await assert.rejects(owner.run(async()=>{
    await owner.own('first',value=>closed.push(value));await owner.own(Promise.reject(primary),()=>assert.fail('unacquired resource'));
  }),error=>error===primary);
  assert.deepEqual(closed,['first']);noHooks(host);
});
test('one finalizer failure cannot skip independent finalizers or replace the original failure',async()=>{
  const host=new EventEmitter(),owner=new BrowserScope({processImpl:host}),closed=[];const primary=Error('original'),cleanup=Error('cleanup');
  await assert.rejects(owner.run(async()=>{
    await owner.own('first',value=>closed.push(value));await owner.own('second',()=>{throw cleanup;});throw primary;
  }),error=>{assert.ok(leaves(error).includes(primary));assert.ok(leaves(error).includes(cleanup));return true;});
  assert.deepEqual(closed,['first']);noHooks(host);
});
test('signal during observed pending acquisition closes the eventual resource exactly once',async()=>{
  const host=new EventEmitter(),owner=new BrowserScope({processImpl:host}),acquisition=deferred(),closed=[];
  const run=owner.run(async()=>{await owner.own(acquisition.promise,value=>closed.push(value));});
  const failed=assert.rejects(run,error=>leaves(error).some(value=>/interrupted by SIGTERM/.test(value.message)));
  assert.equal(owner.resources.length,1);host.emit('SIGTERM');acquisition.resolve('late');await failed;
  assert.deepEqual(closed,['late']);assert.equal(owner.signal.aborted,true);noHooks(host);
});
test('observed held finalizer has a finite watchdog and later finalizers still run',async()=>{
  let now=0;const timers=new Set(),clock=createDeadlineTools({clock:()=>now,setTimer:fn=>{timers.add(fn);return fn;},clearTimer:fn=>timers.delete(fn)});
  const host=new EventEmitter(),owner=new BrowserScope({processImpl:host,cleanup:clock.deadlinePromise}),entered=deferred(),release=deferred(),closed=[];
  const run=owner.run(async()=>{
    await owner.own('first',value=>closed.push(value));await owner.own('held',()=>{entered.resolve();return release.promise;});throw Error('operation failed');
  });
  const failed=assert.rejects(run,error=>leaves(error).some(value=>/browser-resource-cleanup/.test(value.message)));
  await entered.promise;now=20001;for(const timer of [...timers])timer();await failed;release.resolve();
  assert.deepEqual(closed,['first']);assert.equal(timers.size,0);noHooks(host);
});
test('acquisition after closure cleans the new resource instead of exposing it',async()=>{
  const host=new EventEmitter(),owner=new BrowserScope({processImpl:host}),closed=[];
  await owner.run(async()=>{await owner.close();await assert.rejects(owner.own('late',value=>closed.push(value)),/already closing/);});
  assert.deepEqual(closed,['late']);noHooks(host);
});
test('partial handler registration rolls back the first acquired handler',()=>{
  const host=new EventEmitter(),on=host.on.bind(host);host.on=(name,handler)=>{if(name==='SIGINT')throw Error('registration denied');return on(name,handler);};
  assert.throws(()=>new BrowserScope({processImpl:host}),/registration denied/);noHooks(host);
});

test('replacement fixtures finalize after browsers and HTTP queues regardless of acquisition order',async()=>{
  const scope=new BrowserScope(),closed=[];
  await scope.own('old fixture',value=>closed.push(value),{priority:-10});
  await scope.own('server',value=>closed.push(value),{priority:-5});
  await scope.own('browser',value=>closed.push(value));
  await scope.own('replacement fixture',value=>closed.push(value),{priority:-10});
  await scope.run(async()=>{});
  assert.deepEqual(closed,['browser','server','replacement fixture','old fixture']);
});
