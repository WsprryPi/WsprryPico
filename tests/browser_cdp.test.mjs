import assert from 'node:assert/strict';
import test from 'node:test';
import {Cdp} from './browser_cdp.mjs';
import {createDeadlineTools} from './browser_deadline.mjs';
const url='ws://127.0.0.1:12345/devtools/page/owned';
class Socket extends EventTarget {
  readyState=1;sent=[];listeners=new Map();
  constructor(){super();Socket.last=this;}
  addEventListener(name,fn,...rest){const entries=this.listeners.get(name)||new Set();entries.add(fn);this.listeners.set(name,entries);super.addEventListener(name,fn,...rest);}
  removeEventListener(name,fn,...rest){const entries=this.listeners.get(name);entries?.delete(fn);if(entries?.size===0)this.listeners.delete(name);super.removeEventListener(name,fn,...rest);}
  get listenerCount(){return [...this.listeners.values()].reduce((count,entries)=>count+entries.size,0);}
  send(text){if(this.throwSend)throw Error('observed send failure');this.sent.push(JSON.parse(text));}
  message(value){this.dispatchEvent(new MessageEvent('message',{data:typeof value==='string'?value:JSON.stringify(value)}));}
  reply(index,result){this.message({id:this.sent[index].id,result});}
  close(){this.readyState=3;this.dispatchEvent(new Event('close'));}
}
function controlled(){let now=0;const timers=new Set();const tools=createDeadlineTools({clock:()=>now,setTimer:fn=>{timers.add(fn);return fn;},clearTimer:fn=>timers.delete(fn)});return {...tools,expire(value){now=value;for(const timer of [...timers])timer();},timers};}

test('pure transport correlates reordered replies and removes all owned listeners',async()=>{
  const cdp=new Cdp(url,{WebSocketImpl:Socket});await cdp.open();
  const a=cdp.send('A'),b=cdp.send('B');Socket.last.reply(1,{value:'b'});Socket.last.reply(0,{value:'a'});
  assert.deepEqual(await Promise.all([a,b]),[{value:'a'},{value:'b'}]);
  await cdp.stop();assert.equal(cdp.pending.size,0);assert.equal(Socket.last.listenerCount,0);
});
test('a cancelled reply cannot satisfy a later request',async()=>{
  const clock=controlled(),cdp=new Cdp(url,{WebSocketImpl:Socket,deadline:clock.deadlinePromise});
  const held=cdp.send('HELD'),failed=assert.rejects(held,/stage=CDP HELD/);
  assert.equal(Socket.last.sent[0].method,'HELD');clock.expire(15001);await failed;
  const next=cdp.send('NEXT');Socket.last.reply(0,{old:true});assert.equal(cdp.pending.size,1);
  Socket.last.reply(1,{current:true});assert.deepEqual(await next,{current:true});await cdp.stop();assert.equal(clock.timers.size,0);
});
test('synchronous send failure cannot retain a pending entry',async()=>{
  const cdp=new Cdp(url,{WebSocketImpl:Socket});Socket.last.throwSend=true;
  await assert.rejects(cdp.send('FAIL'),/observed send failure/);assert.equal(cdp.pending.size,0);await cdp.stop();
});
test('malformed envelopes and outcomes fail pending work before field consumption',async()=>{
  for(const invalid of ['not-json','null','[]','{"method":""}','{"id":1,"error":null}','{"id":1,"result":null}','{"id":1,"result":{},"error":{"code":1,"message":"bad"}}','{"id":"1","result":{}}']){
    const cdp=new Cdp(url,{WebSocketImpl:Socket});const pending=cdp.send('CHECK');const failed=assert.rejects(pending,/malformed or uncorrelated/);
    Socket.last.message(invalid);await failed;await cdp.stop();assert.equal(cdp.pending.size,0);assert.equal(Socket.last.listenerCount,0);
  }
});
test('a late unexpected socket close after the final reply fails finalization',async()=>{
  const cdp=new Cdp(url,{WebSocketImpl:Socket});const result=cdp.send('LAST');Socket.last.reply(0,{});await result;
  Socket.last.close();await assert.rejects(cdp.stop(),/unexpected close/);assert.equal(Socket.last.listenerCount,0);
});
test('duplicate completed response is an unobserved transport failure',async()=>{
  const cdp=new Cdp(url,{WebSocketImpl:Socket});const result=cdp.send('ONE');Socket.last.reply(0,{});await result;
  Socket.last.reply(0,{});await assert.rejects(cdp.stop(),/malformed or uncorrelated/);
});
test('opening error rejects immediately and leaves no opening subscriptions',async()=>{
  class Connecting extends Socket{readyState=0;}
  const cdp=new Cdp(url,{WebSocketImpl:Connecting});const opening=cdp.open(),failed=assert.rejects(opening,/transport error/);
  Socket.last.dispatchEvent(new Event('error'));await failed;await cdp.stop();assert.equal(Socket.last.listenerCount,0);
});
test('observed stalled opening expires while cleanup retains an independent budget',async()=>{
  class Connecting extends Socket{readyState=0;}
  const clock=controlled(),cdp=new Cdp(url,{WebSocketImpl:Connecting,deadline:clock.deadlinePromise});
  const opening=cdp.open(),failed=assert.rejects(opening,/browser-socket-open/);assert.equal(Socket.last.listenerCount,6);
  clock.expire(15001);await failed;await cdp.stop();assert.equal(Socket.last.readyState,3);assert.equal(Socket.last.listenerCount,0);
});
test('observed unclosed socket remains a failed cleanup with no retained timers/listeners',async()=>{
  class HeldClose extends Socket{close(){this.readyState=2;this.closeEntered=true;}}
  const clock=controlled(),cdp=new Cdp(url,{WebSocketImpl:HeldClose,cleanup:clock.deadlinePromise});
  const stopping=cdp.stop(),failed=assert.rejects(stopping,/browser-socket-close/);
  assert.equal(Socket.last.closeEntered,true);clock.expire(3001);await failed;
  assert.equal(clock.timers.size,0);assert.equal(Socket.last.listenerCount,0);Socket.last.readyState=3;
});
