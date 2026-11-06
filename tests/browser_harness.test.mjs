import assert from 'node:assert/strict';
import test from 'node:test';
import http from 'node:http';
import {stat} from 'node:fs/promises';
import {BrowserHarness,fixtureJson} from './browser_harness.mjs';

test('observed stalled fixture body aborts and closes its socket',async()=>{
  const h=new BrowserHarness(),abort=new AbortController();let entered=false;
  await h.run(async()=>{
    const server=await h.server(http.createServer((_req,res)=>{entered=true;res.writeHead(200,{'Content-Type':'application/json'});res.write('{');abort.abort(Error('observed held body'));}));
    await h.listen(server);
    await assert.rejects(fixtureJson('http://127.0.0.1:'+server.address().port,{signal:abort.signal}));
    assert.equal(entered,true);
  });
});
test('fixture control refuses malformed and oversized bodies instead of retrying',async()=>{
  for(const body of ['invalid-json','x'.repeat(65537)]){
    const h=new BrowserHarness();let requests=0;
    await h.run(async()=>{
      const server=await h.server(http.createServer((_req,res)=>{requests++;res.writeHead(200);res.end(body);}));await h.listen(server);
      await assert.rejects(fixtureJson('http://127.0.0.1:'+server.address().port));assert.equal(requests,1);
    });
  }
});
test('failed Chrome acquisition removes its private profile through owned finalization',async()=>{
  const h=new BrowserHarness();let profile;
  await assert.rejects(h.run(async()=>{
    profile=await h.profile('pico-browser-missing-');
    await h.chrome('/nonexistent/wsprry-campaign-browser',[],profile);
  }),/Chrome launch failed/);
  await assert.rejects(stat(profile),{code:'ENOENT'});
});
test('private profiles cannot be reused for another browser surface',async()=>{
  const h=new BrowserHarness();let attempted=false;
  await h.run(async()=>{
    const profile=await h.profile('pico-browser-reuse-');
    h.profiles.set(profile,{owned:true});
    try{await assert.rejects(h.chrome('/nonexistent/wsprry-campaign-browser',[],profile),/profile reuse refused/);attempted=true;}
    finally{h.profiles.delete(profile);}
  });assert.equal(attempted,true);
});

test('navigation retries only qualified cross-document states',async()=>{
  const {navigationTransient}=await import('./browser_harness.mjs');
  assert.equal(navigationTransient({code:-32000,protocolMessage:'Execution context was destroyed.'}),false);
  for(const error of [Error('Execution context was destroyed.'),Object.assign(Error('permission failed'),{code:-32000,protocolMessage:'permission failed'}),new SyntaxError('bad expression'),new assert.AssertionError({message:'wrong value'})])
    assert.throws(()=>navigationTransient(error),value=>value===error);
});
