'use strict';
// Execute the generated, shipped script against realistic DOM defaults.
process.env.WSPRRY_PICO_BROWSER_SHIPPED='1';
const {fixture}=require('./network_browser_tests.js');
const vm=require('node:vm');
const assert=require('node:assert/strict');
(async()=>{
  const f=await fixture(), e=f.elements;
  const plan=()=>vm.runInContext('messagePlan()',f.context);
  const preview=()=>e['message-form'].oninput();
  const submit=()=>e['message-form'].onsubmit({preventDefault(){}});
  const jobs=()=>f.calls.filter(c=>c.path.endsWith('jobs')).map(c=>JSON.parse(c.options.body));
  assert.equal(e['message-frequency-label'].textContent,'Carrier frequency (Hz)');
  assert.equal(e['message-shift'].disabled,true);
  for(const [mode,first,second,names,duration] of [
    ['qrss','14096900000000000','0','Carrier 14096900 Hz',85000001000n],
    ['fskcw','14096905000000000','14096900000000000','Space 14096900 Hz · Mark 14096905 Hz',85000001000n],
    ['dfcw','14096900000000000','14096905000000000','Dot 14096900 Hz · Dash 14096905 Hz',73000001000n]]) {
    f.prepareMessage(mode,'A E');e['message-frequency'].value='14096900';e['message-repeats'].value='2';e['message-gap'].value='7';
    preview();const p=plan();assert.equal(p.body.frequency_nhz,first);assert.equal(p.body.space_frequency_nhz,second);
    assert.equal(p.duration,duration);assert.equal(p.events,12);assert(e['message-preview'].textContent.includes(names));
    const before=jobs().length;await submit();const sent=jobs().slice(before);
    assert.deepEqual(sent.map(j=>j.operation),['HELLO','CLAIM','LOAD_MESSAGE','ARM']);
    assert.deepEqual(sent[2].body,JSON.parse(JSON.stringify({...p.body,job_id:sent[2].body.job_id})));
    assert.equal(sent[2].body.allow_frequency_adjustment,true);
    assert.deepEqual(Object.keys(sent[2].body).sort(),['allow_frequency_adjustment','frequency_nhz','job_id','message','mode','repeat_count','repeat_gap_ns','space_frequency_nhz','timing']);
  }
  f.prepareMessage('fskcw','AE');e['message-frequency'].value='14096900.123456789';e['message-shift'].value='0.000000001';preview();
  assert.equal(plan().body.frequency_nhz,'14096900123456790');assert.equal(plan().body.space_frequency_nhz,'14096900123456789');
  assert.match(e['message-preview'].textContent,/Space 14096900.123456789 Hz · Mark 14096900.12345679 Hz/);
  const drafts=['frequency','shift','text','dot','dash','intra','character','word','repeats','gap'].map(k=>e['message-'+k].value);
  const before=f.calls.length;
  e['message-result'].textContent='Message armed';
  for(const mode of ['dfcw','qrss','fskcw']) {e['message-mode'].value=mode;e['message-mode'].onchange();assert.deepEqual(['frequency','shift','text','dot','dash','intra','character','word','repeats','gap'].map(k=>e['message-'+k].value),drafts);assert.equal(e['message-shift'].disabled,mode==='qrss');}
  assert.equal(e['message-result'].textContent,'','previous submission feedback does not describe an edited draft');
  assert.equal(f.calls.length,before,'mode exploration sends no requests');
  e['message-shift'].value='bad';e['message-mode'].value='qrss';preview();assert.doesNotThrow(plan);assert.equal(e['message-shift'].disabled,true);
  e['message-mode'].value='dfcw';e['message-mode'].onchange();assert.throws(plan,/Frequency shift/);assert.equal(e['message-shift'].value,'bad');
  for(const mode of ['fskcw','dfcw']) {
    f.prepareMessage(mode);e['message-frequency'].value='14096900';
    for(const value of ['0','-1','bad','1.0000000001','Infinity','NaN','1e2','+1','.5','1.','18446744073.709551616']) {
      e['message-shift'].value=value;preview();const n=jobs().length;await submit();assert.equal(jobs().length,n);assert.equal(e['message-shift'].value,value);
      assert.match(e['message-result'].textContent,/preserved/);assert.equal(e['message-shift'].getAttribute('aria-invalid'),'true');
    }
    e['message-shift'].value='1';e['message-frequency'].value='18446744073.709551615';assert.throws(plan,/plus shift is too large/);
  }
  f.prepareMessage();
  for(const value of ['0','-1','bad','1.0000000001','Infinity','NaN','1e2','+1','.5','1.','18446744073.709551616']) {
    e['message-frequency'].value=value;const n=jobs().length;await submit();assert.equal(jobs().length,n);assert.equal(e['message-frequency'].value,value);
  }
  vm.runInContext(`capabilities.wtp.frequency_ranges=[{minimum_nhz:'1000000000',maximum_nhz:'10000000000'}]`,f.context);
  for(const mode of ['dfcw','fskcw']) {
    f.prepareMessage(mode);e['message-frequency'].value='1';e['message-shift'].value='9';
    assert.equal(mode==='dfcw'?plan().body.space_frequency_nhz:plan().body.frequency_nhz,'10000000000');
    e['message-shift'].value='1';assert.doesNotThrow(plan,'shift >= base is valid in the isolated range');
    e['message-frequency'].value='0.999999999';assert.throws(plan,/frequency is outside/);
    e['message-frequency'].value='9';e['message-shift'].value='1.000000001';assert.throws(plan,/frequency is outside/);
    e['message-frequency'].value='10';e['message-shift'].value='0.000000001';assert.throws(plan,/frequency is outside/);
  }
  e['message-mode'].value='qrss';assert.doesNotThrow(plan);e['message-frequency'].value='10.000000001';assert.throws(plan,/Carrier frequency is outside/);
  console.log('Shipped CW mapping, exact arithmetic, drafts, boundaries and pre-submission rejection passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
