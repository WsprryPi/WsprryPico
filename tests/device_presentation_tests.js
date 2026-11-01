'use strict';
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {fixture}=require('./network_browser_tests.js');
const {create}=require('../src/network/web/device-presentation.js');
const id='1'.repeat(32),boot='a'.repeat(32),other='2'.repeat(32);
const run=(f,source)=>vm.runInContext(source,f.context);
const text=(f,id)=>f.elements[id].textContent;
(async()=>{
  const f=await fixture();
  assert.equal(text(f,'device-name'),'old.local');
  assert.equal(text(f,'device-id'),id,'engineering ID comes from hostname target, never capabilities');
  assert.equal(text(f,'device-boot'),boot);
  assert.equal(text(f,'device-name-state'),'');assert.equal(f.elements['device-name-state'].hidden,true);
  f.context.location.href='http://forged.local/?hostname=lie.local';
  f.elements['hostname-input'].value='draft.local';f.elements['hostname-input'].listeners.input();
  assert.equal(text(f,'device-name'),'old.local');
  f.savedHostname='new.local';await f.elements.refresh.onclick();
  assert.equal(text(f,'device-name'),'old.local');assert.match(text(f,'device-name-state'),/Saved for restart: new.local/);
  assert.match(f.context.document.title,/old.local.*rename pending/);
  f.offline=true;await f.elements.refresh.onclick();
  assert.equal(text(f,'device-name'),'old.local');assert.match(text(f,'device-name-state'),/Last confirmed/);
  assert.match(f.context.document.title,/last confirmed/);assert.equal(text(f,'device-id'),id);

  const consumer=await fixture(true,true,false,true);
  // Exercise the actual startup presentation fetch with controlled body delivery.
  let release;
  const pending=new Promise(resolve=>{release=resolve;});
  const fetch=consumer.context.fetch;
  consumer.context.fetch=async(path,options)=>path==='/api/consumer/v1/presentation'?
    {ok:true,json:()=>pending}:fetch(path,options);
  const late=run(consumer,'presentationTitle()');
  consumer.elements['local-password'].value='test-password';
  await consumer.elements['local-login'].onsubmit({preventDefault(){}});
  assert.equal(text(consumer,'device-name'),'old.local');
  release({schema:'device-presentation/1',device_id:id,boot_id:boot,hostname:'late.local'});await late;
  assert.equal(text(consumer,'device-name'),'old.local');
  assert.match(text(consumer,'local-status'),/unlocked/);
  const statuses=text(consumer,'local-status');
  await run(consumer,'presentationTitle()'); // already-resolved public response still cannot downgrade auth
  assert.equal(text(consumer,'local-status'),statuses);assert.equal(text(consumer,'device-name'),'old.local');
  const mutations=consumer.calls.filter(c=>c.options?.method && c.options.method!=='GET').length;
  await consumer.elements['local-logout'].onclick();
  assert.match(text(consumer,'local-status'),/signed out/i);assert.equal(text(consumer,'device-name-state'),'');assert.equal(consumer.elements['device-name-state'].hidden,true);
  assert.equal(consumer.calls.filter(c=>c.options?.method && c.options.method!=='GET').length,mutations,'presentation causes no request');

  for (const metadata of [
    {schema:'wrong'}, {schema:'device-presentation/1',device_id:id,boot_id:boot,hostname:'lie.local',unexpected:true}, {schema:'device-presentation/1',device_id:other,boot_id:boot,hostname:'lie.local'},
    {schema:'device-presentation/1',device_id:id,boot_id:'b'.repeat(32),hostname:'lie.local'},
    ...['K.local','<img>.local','X.LOCAL','x'.repeat(64)+'.local','-bad.local',''].map(hostname=>({schema:'device-presentation/1',device_id:id,boot_id:boot,hostname}))
  ]) {
    const invalid=await fixture(true,true,false,true);
    invalid.context.fetch=async()=>({ok:true,json:async()=>metadata});
    await run(invalid,'presentationTitle()');
    assert.equal(text(invalid,'device-name'),'old.local','malformed metadata cannot replace the public-read observation');
    assert.equal(text(invalid,'device-id'),id);
  }
  const publicOnly=await fixture(true,true,false,true);
  publicOnly.context.fetch=async()=>({ok:true,json:async()=>({schema:'device-presentation/1',device_id:id,boot_id:boot,hostname:'public.local'})});
  await run(publicOnly,'presentationTitle()');assert.equal(text(publicOnly,'device-name'),'public.local');
  publicOnly.context.fetch=async()=>({ok:false});await run(publicOnly,'presentationTitle()');
  assert.match(text(publicOnly,'device-name-state'),/Last confirmed/);
  assert.match(publicOnly.context.document.title,/last confirmed/);
  const ordered=await fixture();const originalFetch=ordered.context.fetch;
  let deliver,delay=true;
  ordered.context.fetch=async(path,options)=>{
    const response=await originalFetch(path,options);
    if(delay && path.endsWith('/hostname')) {
      const body=await response.json();
      return {...response,json:()=>new Promise(resolve=>{deliver=()=>resolve(body);})};
    }
    return response;
  };
  const oldRead=run(ordered,'readHostname()');await new Promise(setImmediate);
  delay=false;ordered.state.job.boot_id='b'.repeat(32);ordered.state.network.configured_hostname='new-boot.local';
  await ordered.elements.refresh.onclick();deliver();await oldRead;
  assert.equal(text(ordered,'device-name'),'new-boot.local');
  assert.equal(text(ordered,'device-boot'),'b'.repeat(32));
  assert.equal(run(ordered,'hostnameState.active'),'new-boot.local');

  // Authenticated engineering legacy fallback with no fabricated local boot field.
  const legacy=await fixture();const native=legacy.context.fetch;
  legacy.context.fetch=async(path,options)=>path.endsWith('/hostname')?
    {ok:false,json:async()=>({error:{code:'not_found'}}),headers:{get:()=>null}}:native(path,options);
  await legacy.elements.refresh.onclick();assert.equal(text(legacy,'device-name'),'old.local');
  legacy.state.network.configured_hostname='';await legacy.elements.refresh.onclick();
  assert.match(text(legacy,'device-name-state'),/Last confirmed/);
  assert.equal(text(legacy,'device-id'),id);
  const renamed=await fixture(true,true,true);
  renamed.elements['hostname-input'].value='new.local';
  await renamed.elements['hostname-form'].onsubmit({preventDefault(){}});
  assert.match(text(renamed,'local-status'),/authenticated/);
  assert.match(text(renamed,'device-name-state'),/Rename pending/);
  const local=await fixture(true,true,true);assert.equal(text(local,'device-id'),id);assert.equal(text(local,'device-boot'),boot);

  // Pure controller exercises target binding and request ordering separately from the VM.
  function display() {const elements=new Map();const document={getElementById:id=>{if(!elements.has(id))elements.set(id,{textContent:''});return elements.get(id);}};return {document,elements,p:create(document)};}
  const a=display(),b=display();
  for(const [d,device] of [[a,id],[b,other]]) {
    d.p.bind({device_id:device,boot_id:boot});
    assert.equal(d.p.observe(d.p.request(),{device_id:device,boot_id:boot},'duplicate.local'),true);
    assert.equal(d.elements.get('device-id').textContent,device);
  }
  assert.notEqual(a.elements.get('device-id').textContent,b.elements.get('device-id').textContent);
  const old=a.p.request(),newer=a.p.request();
  assert.equal(a.p.observe(newer,{device_id:id,boot_id:boot},'new.local',{authenticated:true}),true);
  assert.equal(a.p.observe(old,{device_id:id,boot_id:boot},'old.local',{authenticated:true}),false);
  assert.equal(a.p.observe(a.p.request(),{device_id:other,boot_id:boot},'lie.local',{authenticated:true}),false);
  assert.throws(()=>a.p.bind({device_id:other}),/different Pico/);
  const former=a.p.request();a.p.bind({device_id:id,boot_id:'b'.repeat(32)});
  assert.equal(a.elements.get('device-name').textContent,'Hostname unavailable');
  assert.equal(a.p.observe(former,{device_id:id,boot_id:boot},'old.local'),false);
  const long='x'.repeat(63)+'.local';
  assert.equal(a.p.observe(a.p.request(),{device_id:id,boot_id:'b'.repeat(32)},long),true);
  assert.equal(a.elements.get('device-name').textContent.length,69);
  console.log('PASS identity target/name/freshness, delayed public response, malformed metadata, duplicate IDs, legacy/local engineering and no presentation effects');
})().catch(e=>{console.error(e);process.exitCode=1;});
