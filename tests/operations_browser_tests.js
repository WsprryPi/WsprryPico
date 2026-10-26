'use strict';
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
require('../src/network/web/message-schedule.js');
const ops=require('../src/network/web/operations.js');
const {fixture}=require('./network_browser_tests.js');
function observation() {
  const boot='a'.repeat(32),job={boot_id:boot,state:'empty',owner_id:null,output_active:false,job_id:null,terminal_records:[]};
  return {schema:'transmitter-operations/1',target:{scope:'member',device_id:'1'.repeat(32),boot_id:boot},job,accepted:null,
    standalone:{...job,configured:true,enabled:false,storage_healthy:true,reboot_required:false,suspended:false,frequency_required:false,wspr_pair_pending:false,
      utc_now_ns:'1800000000000000000',uncertainty_ns:'1000',sync_age_ns:'100000000000',clock_state:'holdover',schedules:[{period_s:120,phase_s:0}],expires_utc_s:0,schedule_dial_frequency_nhz:'14095600000000000',engine:'test'},
    message_schedule:{saved:null,state:'not_configured',pause_pending:false,next_start_utc_ns:null,last_start_utc_ns:null,last_job_id:null,last_result:null,last_error:null},
    next_wspr_start_utc_ns:null,correction:{next_ppb:3470,prepared_ppb:2000},reset_allowed:true,network:{enabled:true},transport:null};
}
function active(v,mode='dfcw') {
  v.job.state='running';v.job.job_id='3'.repeat(32);v.job.owner_id='4'.repeat(32);Object.assign(v.standalone,v.job);
  v.accepted={mode,duration_ns:'6000000000',start_utc_ns:'1799999990000000000',event_count:4,frequencies_nhz:['135500000000000','135505000000000'],frequencies_truncated:false,
    message:{text:'TE',frequency_nhz:'135505000000000',space_frequency_nhz:'135500000000000',dot_ns:'3000000000',dash_ns:'3000000000',repeat_gap_ns:'1000000000',repeat_count:2}};
}
(async()=>{
  assert.doesNotMatch(fs.readFileSync(__dirname+'/../src/network/web/index.html','utf8').match(/<p id="public-status-note"[^>]*>/)[0],/aria-live|role=/);
  const caps={wtp:{maximum_holdover_age_ns:'3600000000000',maximum_arm_uncertainty_ns:'1000000'}};
  let v=observation();assert(ops.valid(v));
  assert.equal(ops.model(v,caps,'9'.repeat(32)).state,'Schedules disabled');
  v.standalone.enabled=true;assert.equal(ops.model(v,caps,'9'.repeat(32)).state,'Waiting for next occurrence');
  assert.match(ops.model(v,caps,'9'.repeat(32)).next,/14095600 Hz.*14097100 Hz/);
  v.standalone.sync_age_ns='0';assert.equal(ops.model(v,{wtp:{maximum_holdover_age_ns:'0'}},'x').state,'Waiting for time');
  v.standalone.sync_age_ns='3600000000001';assert.equal(ops.model(v,caps,'9'.repeat(32)).state,'Waiting for time');
  v.message_schedule.saved={enabled:false,first_start_utc_ns:'1800000000000000000',period_s:120,expires_utc_s:0,message:{mode:'qrss',message:'PRIVATE',frequency_nhz:'135500000000000',space_frequency_nhz:'0',timing:{dot_ns:'1000000000',dash_ns:'3000000000',intra_gap_ns:'1000000000',character_gap_ns:'3000000000',word_gap_ns:'7000000000'},repeat_count:1,repeat_gap_ns:'0',allow_frequency_adjustment:true}};v.message_schedule.state='paused';v.standalone.sync_age_ns='0';assert.equal(ops.model(v,caps,'x').state,'Waiting for next occurrence');
  active(v);assert(ops.valid(v));
  let view=ops.model(v,caps,'9'.repeat(32));assert.equal(view.state,'Job running');assert.match(view.explanation,/keyed gaps/);assert.equal(view.reset,false);
  assert.match(view.frequency,/Dot 135505 Hz\nDash 135500 Hz/);assert.match(view.progress,/100.0%.*still running/);assert.match(view.correction,/3.470 ppm.*\nAccepted job: 2.000 ppm/);
  assert.match(view.actions,/cannot abort/);
  v.standalone.configured=false;v.standalone.frequency_required=true;assert.equal(ops.model(v,caps,'x').state,'Job running');
  v.message_schedule.state='recovery_required';assert.equal(ops.model(v,caps,'x').state,'Job running');
  for(const mode of ['qrss','fskcw','dfcw','tone','arbitrary']) {
    v=observation();active(v,mode);if(['tone','arbitrary'].includes(mode))v.accepted.message=null;
    assert(ops.valid(v));view=ops.model(v,caps,'x');
    assert.match(view.frequency,mode==='qrss'?/Carrier/:mode==='fskcw'?/Space.*\nMark/:mode==='dfcw'?/Dot.*\nDash/:/Nominal RF/);
    if(!v.accepted.message)assert.match(view.message,/unavailable/);
  }
  for(const state of ['loaded','armed','running','complete','aborted','missed','failed']) {
    v=observation();active(v);v.job.state=v.standalone.state=state;
    assert(ops.valid(v));view=ops.model(v,caps,'x');
    if(['loaded','armed','running','failed'].includes(state))assert.equal(view.reset,false);
  }
  v=observation();v.job.output_active=true;assert.equal(ops.model(v,caps,'x').state,'Recovery required');
  v=observation();for(const mutate of [x=>x.target.device_id='x',x=>x.job.state='invented',x=>x.standalone.utc_now_ns='bad',x=>x.extra=true,x=>x.job.output_active=null,x=>x.standalone.schedules=[{period_s:0,phase_s:0}]]) {
    const bad=structuredClone(v);mutate(bad);assert.equal(ops.valid(bad),false);
  }
  assert.equal(ops.valid(v,{device_id:'2'.repeat(32),boot_id:v.target.boot_id}),false);
  assert.equal(ops.valid(v,{device_id:v.target.device_id,boot_id:'b'.repeat(32)}),false);
  const basic=await fixture();assert.equal(basic.elements['console-state'].textContent,'Job empty');assert.match(basic.elements['console-explanation'].textContent,/basic status/);basic.state.job.state='invented';await basic.elements.refresh.onclick();assert.equal(basic.elements['console-state'].textContent,'Status unavailable');assert.equal(basic.elements.restart.disabled,true);assert.equal(basic.elements.settings.disabled,true);
  const rebound=await fixture();rebound.state.job.boot_id='b'.repeat(32);await rebound.elements.refresh.onclick();assert.equal(rebound.elements['console-state'].textContent,'Job empty');rebound.state.job.boot_id='c'.repeat(32);rebound.hostnameDevice='2'.repeat(32);await rebound.elements.refresh.onclick();assert.equal(rebound.elements['console-state'].textContent,'Status unavailable');assert.equal(rebound.elements.restart.disabled,true);
  const f=await fixture();f.operations=observation();Object.assign(f.operations.network,f.state.network);
  vm.runInContext('capabilities=null',f.context);await f.elements.refresh.onclick();
  assert.equal(f.elements['console-state'].textContent,'Schedules disabled');
  f.elements['message-text'].value='KEEP DRAFT';active(f.operations);await f.elements.refresh.onclick();
  assert.equal(f.elements['console-state'].textContent,'Job running');assert.equal(f.elements['console-reset'].disabled,true);assert.equal(f.elements['message-text'].value,'KEEP DRAFT');
  f.now+=15001;vm.runInContext('consoleTick()',f.context);assert.equal(f.elements['console-state'].textContent,'Status unavailable');assert.equal(f.elements.restart.disabled,true);
  await f.elements.refresh.onclick();assert.equal(f.elements['console-state'].textContent,'Job running');
  f.operations.target.device_id='2'.repeat(32);await f.elements.refresh.onclick();assert.equal(f.elements['console-state'].textContent,'Status unavailable');assert.equal(f.elements['console-message'].textContent,'Unavailable');
  f.operations=observation();Object.assign(f.operations.network,f.state.network);await f.elements.refresh.onclick();
  let release;f.delayObservation=new Promise(r=>{release=r;});const pending=vm.runInContext('refresh()',f.context);await new Promise(setImmediate);
  vm.runInContext('++observationEpoch; clearConsole("Canceled observation")',f.context);release();await pending;assert.equal(f.elements['console-state'].textContent,'Status unavailable');
  const pub=await fixture(true,true,false,true);pub.state.job.state='running';pub.state.job.output_active=false;await pub.elements.refresh.onclick();
  assert.match(pub.elements['console-explanation'].textContent,/keyed gap/);assert.equal(pub.elements['console-reset'].disabled,true);assert.equal(pub.elements['console-message'].textContent,'Unavailable');
  pub.state.job.state='complete';pub.state.job.output_active=true;await pub.elements.refresh.onclick();assert.equal(pub.elements['console-state'].textContent,'Recovery required');assert.match(pub.elements['console-explanation'].textContent,/RF is reported active/);
  const expired=await fixture(true,true,false,true);await expired.elements['local-login'].onsubmit({preventDefault(){}});expired.elements['saved-active-status'].textContent='PRIVATE';expired.elements['saved-readback-details'].hidden=false;expired.radio.authenticated=false;await vm.runInContext('api("status").catch(()=>{})',expired.context);assert.equal(expired.elements['saved-active-status'].textContent,'');assert.equal(expired.elements['saved-readback-details'].hidden,true);
  const lost=await fixture(true,true,false,true);await lost.elements['local-login'].onsubmit({preventDefault(){}});lost.state.job.owner_id=vm.runInContext('session',lost.context);lost.state.job.state='armed';lost.state.job.job_id='3'.repeat(32);await lost.elements.refresh.onclick();assert.equal(lost.elements.abort.disabled,false);lost.radio.authenticated=false;vm.runInContext('controls(true)',lost.context);assert.equal(lost.elements.abort.disabled,true);assert.equal(lost.elements['console-reset'].disabled,true);assert.equal(vm.runInContext('snapshot',lost.context),null);
  for(const phase of ['confirmation','readback']) { const late=await fixture();if(phase==='confirmation')late.confirmAdvance=16000;else late.expireResetRead=true;await late.elements.restart.onclick();assert.equal(late.calls.filter(c=>c.path.endsWith('restart')).length,0);assert.match(late.elements.notice.textContent,/No reset was sent/);assert.doesNotMatch(late.elements.notice.textContent,/Cannot read/); }
  const reset=await fixture();reset.operations=observation();Object.assign(reset.operations.network,reset.state.network);vm.runInContext('capabilities=null',reset.context);await reset.elements.refresh.onclick();await reset.elements['console-reset'].onclick();await new Promise(setImmediate);assert.match(reset.elements['restart-status'].textContent,/Same Pico and new boot confirmed/);assert.equal(reset.calls.filter(c=>c.path.endsWith('restart')).length,1);
  console.log('Operations: precedence, modes, keyed gaps, privacy, freshness, cancellation and retained drafts passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={observation,active};
