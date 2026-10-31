'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {fixture}=require('./network_browser_tests.js');
const run=(f,code)=>vm.runInContext(code,f.context);
const submit={preventDefault(){}};
function warns(f) {
  let prevented=false;
  const event={preventDefault(){prevented=true;}};
  f.events.beforeunload(event);
  assert.equal(event.returnValue==='',prevented);
  return prevented;
}
async function fresh(saved=null) {
  return fixture(true,true,false,true,'',true,{scheduleSupport:true,savedMessageSchedule:saved});
}
(async()=>{
  const seed=await fixture(true,true,false,false,'',true,{scheduleSupport:true});
  seed.prepareMessage('qrss','CQ TEST');seed.elements['message-delivery'].value='recurring';
  seed.elements['message-form'].oninput();await seed.elements['message-form'].onsubmit(submit);
  assert.ok(seed.savedMessageSchedule);
  for(const saved of [null,seed.savedMessageSchedule,{...seed.savedMessageSchedule,enabled:false}]) {
    const f=await fresh(saved);
    assert.equal(run(f,'localAuthenticated'),false);
    assert.equal(f.elements['message-settings'].disabled,true);
    assert.equal(warns(f),false,'fresh locked readback is clean');
    await f.elements['local-login'].onsubmit(submit);
    assert.equal(warns(f),false,'login and automatic settings readback are clean');
    await f.elements.refresh.onclick();assert.equal(warns(f),false,'status refresh is clean');
    for(const field of ['text','frequency','dot','mode','start','delivery','interval','until']) {
      const input=f.elements['message-'+field],original=input.value;
      input.value=field==='text'?'':original+'1';f.elements['message-form'].oninput();
      // With no saved schedule the original text is already empty.
      if(input.value===original)input.value='E';
      assert.equal(warns(f),true,'changed '+field+' warns');
      await f.elements.refresh.onclick();assert.equal(warns(f),true,'refresh preserves '+field+' draft');
      input.value=original;f.elements['message-form'].oninput();
      assert.equal(warns(f),false,'reverting '+field+' clears warning');
    }
    if(saved) {
      f.elements['message-text'].value='NEW';f.elements['message-form'].oninput();
      f.elements['message-schedule-adopt'].onclick();assert.equal(warns(f),false,'adopting saved schedule is clean');
      f.elements['message-text'].value='NEW';f.elements['message-form'].oninput();
      await f.elements['message-form'].onsubmit(submit);assert.equal(warns(f),false,'confirmed save is clean');
      f.elements['message-text'].value='LATER';f.elements['message-form'].oninput();
      f.loseScheduleSave=true;await f.elements['message-form'].onsubmit(submit);
      assert.equal(warns(f),true,'unconfirmed save preserves warning');
    }
  }
  for(const edit of [
    f=>{f.form.schedules.value='240 / 0';f.elements.config.oninput();},
    f=>f.elements['consumer-network-form'].oninput(),
    f=>f.elements['consumer-station-form'].oninput(),
    f=>f.elements['engineering-station-form'].listeners.input(),
    f=>f.elements['engineering-network-form'].listeners.input(),
    f=>f.elements['hostname-input'].listeners.input(),
    f=>{f.elements['job-file'].files=[{name:'job.json'}];}
  ]) {
    const f=await fresh();edit(f);assert.equal(warns(f),true,'other drafts retain navigation protection');
  }
  const late=await fresh(seed.savedMessageSchedule);await late.elements['local-login'].onsubmit(submit);
  late.elements['message-text'].value='SUBMITTED';late.elements['message-form'].oninput();
  const previous=late.context.fetch;let finish;
  late.context.fetch=async(...args)=>{
    const response=await previous(...args);
    if(args[0].endsWith('message-schedule')&&args[1].method==='PUT') {
      const json=response.json;response.json=()=>new Promise(resolve=>{finish=async()=>resolve(await json());});
    }
    return response;
  };
  const saving=late.elements['message-form'].onsubmit(submit);await new Promise(setImmediate);
  assert.equal(typeof finish,'function');
  late.elements['message-text'].value='NEWER';late.elements['message-form'].oninput();
  await finish();await saving;assert.equal(warns(late),true,'late edits survive confirmed save');
  late.elements['message-text'].value='SUBMITTED';late.elements['message-form'].oninput();
  assert.equal(warns(late),false,'confirmed submitted values form the baseline');
  for(const target of ['hostname-continue','consumer-resume']) {
    const f=await fresh(seed.savedMessageSchedule);let confirmations=0;
    f.context.confirm=()=>{confirmations++;return false;};
    const handler=target==='hostname-continue'?f.elements[target].onclick:f.elements[target].listeners.click;
    let prevented=false;const event={preventDefault(){prevented=true;}};
    handler(event);assert.equal(confirmations,0,'saved text does not prompt on continuation');
    f.elements['message-text'].value='';f.elements['message-form'].oninput();handler(event);
    assert.equal(confirmations,1);assert.equal(prevented,true,'continuation preserves unsaved draft when cancelled');
  }
  const html=fs.readFileSync(__dirname+'/../src/network/web/index.html','utf8');
  assert.doesNotMatch(html,/id="(?:reload-config|settings-actions)"|class="documentation-note"/);
  assert.match(html,/data-help="WSPR dial and schedules"/,'contextual help remains');
  console.log('Unsaved-change navigation regression tests passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
