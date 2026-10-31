'use strict';
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
require('../src/network/web/message-schedule.js');
const ops=require('../src/network/web/operations.js');
const {fixture}=require('./network_browser_tests.js');
function observation() {
  const boot='a'.repeat(32),job={boot_id:boot,state:'empty',owner_id:null,output_active:false,job_id:null,terminal_records:[]};
  return {schema:'operations',target:{scope:'member',device_id:'1'.repeat(32),boot_id:boot},job,accepted:null,
    standalone:{...job,configured:true,enabled:false,storage_healthy:true,reboot_required:false,suspended:false,frequency_required:false,wspr_pair_pending:false,
      utc_now_ns:'1800000000000000000',uncertainty_ns:'1000',sync_age_ns:'100000000000',clock_state:'holdover',last_error:null,schedules:[{period_s:120,phase_s:0}],expires_utc_s:0,schedule_dial_frequency_nhz:'14095600000000000',engine:'test'},
    message_schedule:{saved:null,state:'not_configured',pause_pending:false,next_start_utc_ns:null,last_start_utc_ns:null,last_job_id:null,last_result:null,last_error:null},
    next_wspr_start_utc_ns:null,correction:{next_ppb:3470,prepared_ppb:2000},reset_allowed:true,network:{enabled:true},transport:null};
}
function active(v,mode='dfcw') {
  v.job.state='running';v.job.job_id='3'.repeat(32);v.job.owner_id='4'.repeat(32);Object.assign(v.standalone,v.job);
  v.accepted={mode,duration_ns:'6000000000',start_utc_ns:'1799999990000000000',event_count:4,frequencies_nhz:['135500000000000','135505000000000'],frequencies_truncated:false,
    message:{text:'TE',frequency_nhz:'135505000000000',space_frequency_nhz:'135500000000000',dot_ns:'3000000000',dash_ns:'3000000000',repeat_gap_ns:'1000000000',repeat_count:2}};
}
function recurring(v) {
  v.message_schedule.saved={enabled:true,first_start_utc_ns:'1800000120000000000',period_s:120,expires_utc_s:0,
    message:{mode:'qrss',message:'CQ AA0NT',frequency_nhz:'135500000000000',space_frequency_nhz:'0',
      timing:{dot_ns:'1000000000',dash_ns:'3000000000',intra_gap_ns:'1000000000',character_gap_ns:'3000000000',word_gap_ns:'7000000000'},repeat_count:1,repeat_gap_ns:'0',allow_frequency_adjustment:true}};
  v.message_schedule.state='waiting';v.message_schedule.next_start_utc_ns='1800000120000000000';
}
(async()=>{
  assert.doesNotMatch(fs.readFileSync(__dirname+'/../src/network/web/index.html','utf8').match(/<p id="public-status-note"[^>]*>/)[0],/aria-live|role=/);
  for(const [input,expected] of [
    ['0','0 Hz'],['1','0.000000001 Hz'],['475000000000','475 Hz'],
    ['999999999999','999.999999999 Hz'],['1000000000000','1 kHz'],
    ['135500000000000','135.5 kHz'],['999999999999999','999.999999999999 kHz'],
    ['1000000000000000','1 MHz'],['14095600000000000','14.0956 MHz'],
    ['18446744073709551615','18446.744073709551615 MHz'],
    [null,'Unavailable'],[undefined,'Unavailable'],['-1','Unavailable'],['01','Unavailable']
  ]) assert.equal(ops.formatFrequency(input),expected);
  assert.equal(ops.formatFrequencies(['135505000000000','135500000000000']),'135.505/135.500 kHz');
  assert.equal(ops.formatFrequencies(['135500000000000','135500000000001']),'135.500000000000/135.500000000001 kHz','one nanohertz remains distinguishable');
  assert.equal(ops.formatFrequencies(['999000000000','1000000000000']),'0.999/1.000 kHz','one common unit across its boundary');
  assert.equal(ops.formatFrequencies([]),'Unavailable');
  const compactCaps={wtp:{maximum_holdover_age_ns:'3600000000000',maximum_arm_uncertainty_ns:'1000000'}};
  for(const mode of ['qrss','fskcw','dfcw','wspr','cw','tone']) {
    const value=observation();active(value,mode);
    if(['wspr','cw','tone'].includes(mode))value.accepted.message=null;
    const view=ops.model(value,compactCaps,'x');
    for(const field of ['mode','frequency','message','progress'])assert.doesNotMatch(view[field],/[\r\n]/,mode+' '+field);
    assert(!view.progress.includes(value.job.job_id));assert(!view.progress.includes('events'));
    if(mode==='wspr') {assert.equal(view.frequencyLabel,'Dial frequency');assert.equal(view.frequency,'Unavailable');assert.equal(view.message,'Encoded WSPR frame');}
    if(mode==='fskcw')assert.equal(view.frequencyLabel,'Space/Mark');
    if(mode==='dfcw')assert.equal(view.frequencyLabel,'Dot/Dash');
  }
  const raw=observation();active(raw,'cw');raw.accepted.message=null;
  raw.accepted.frequencies_nhz=[];assert.equal(ops.model(raw,compactCaps,'x').frequency,'Unavailable');
  raw.accepted.frequencies_nhz=['475000000000'];assert.equal(ops.model(raw,compactCaps,'x').frequency,'475 Hz');
  raw.accepted.frequencies_nhz=['1000000000000','475000000000'];assert.equal(ops.model(raw,compactCaps,'x').frequency,'0.475–1.000 kHz');
  raw.accepted.frequencies_truncated=true;assert.equal(ops.model(raw,compactCaps,'x').frequency,'Multiple frequencies');
  raw.accepted.mode='wspr';assert.equal(ops.model(raw,compactCaps,'x').frequency,'Unavailable','WSPR never shows raw tone lists/spans');
  const local=observation();active(local,'wspr');local.accepted.message=null;
  local.job.owner_id=local.standalone.owner_id='e'.repeat(32);local.standalone.last_job=local.job.job_id;
  local.standalone.wspr_frames=2;local.standalone.wspr_frame=1;
  assert.equal(ops.model(local,compactCaps,'x').frequency,'14.0956 MHz');
  assert.equal(ops.model(local,compactCaps,'x').progress,'Frame 1/2 · ~100%');
  local.standalone.wspr_frame=2;assert.equal(ops.model(local,compactCaps,'x').progress,'Frame 2/2 · ~100%');
  for(const state of ['loaded','armed','running','complete','aborted','missed','failed']) {
    local.job.state=local.standalone.state=state;
    assert.equal(ops.model(local,compactCaps,'x').frequency,'14.0956 MHz','owned matching scheduler job '+state);
  }
  local.job.owner_id=local.standalone.owner_id=null;
  local.standalone.schedule_dial_frequency_nhz='7038600000000000';
  assert.equal(ops.model(local,compactCaps,'x').frequency,'Unavailable','released history cannot inherit a later saved dial');
  local.job.owner_id=local.standalone.owner_id='e'.repeat(32);local.standalone.last_job='1'.repeat(32);
  assert.equal(ops.model(local,compactCaps,'x').frequency,'Unavailable','unrelated scheduler job');
  const progress=observation();active(progress,'qrss');
  progress.standalone.utc_now_ns=(BigInt(progress.accepted.start_utc_ns)+3000000000n).toString();
  assert.equal(ops.model(progress,compactCaps,'x').progress,'Running · ~50%');
  progress.standalone.clock_state='unsynchronized';assert.equal(ops.model(progress,compactCaps,'x').progress,'Running');
  progress.job.state=progress.standalone.state='armed';
  assert.equal(ops.model(progress,compactCaps,'x').progress,'Armed · 07:59:50 UTC');
  progress.standalone.utc_now_ns=(BigInt(progress.accepted.start_utc_ns)+86400000000000n).toString();
  assert.match(ops.model(progress,compactCaps,'x').progress,/^Armed · \d{4}-\d{2}-\d{2} 07:59:50 UTC$/);
  progress.accepted.start_utc_ns='1800000000000000000';progress.standalone.utc_now_ns='1800000000000000000';
  assert.equal(ops.model(progress,compactCaps,'x').progress,'Armed · 08:00 UTC');
  progress.accepted.start_utc_ns='1800000000123456789';
  assert.equal(ops.model(progress,compactCaps,'x').progress,'Armed · 08:00:00.123456789 UTC','non-minute starts retain their exact time');
  const codes=JSON.parse(fs.readFileSync(__dirname+'/../engineering/protocol/wtp-1.schema.json','utf8')).$defs.errorCode.enum;
  for(const code of codes) assert(ops.validError({code,message:code,retryable:false}));
  for(const invalid of [undefined,[],{}, {code:'invented',message:'x',retryable:false},
    {code:'INTERNAL_ERROR',message:'',retryable:false}, {code:'INTERNAL_ERROR',message:'x',retryable:1},
    {code:'INTERNAL_ERROR',message:'x',retryable:false,extra:1},
    {code:'INTERNAL_ERROR',message:'é'.repeat(129),retryable:false},
    {code:'INTERNAL_ERROR',message:'\ud800',retryable:false},
    {code:'INTERNAL_ERROR',message:'x',retryable:false,detail:[]}]) assert.equal(ops.validError(invalid),false);
  assert(ops.validError({code:'INTERNAL_ERROR',message:'é'.repeat(128),retryable:false,detail:{}}));
  const detailed=observation();detailed.message_schedule.last_error={code:'INTERNAL_ERROR',message:'error',retryable:false,detail:{stage:'prepare'}};
  assert(ops.valid(detailed),'the current optional WTP error detail is valid for message errors too');
  const caps={wtp:{maximum_holdover_age_ns:'3600000000000',maximum_arm_uncertainty_ns:'1000000'}};
  const next=x=>ops.model(x,caps,'x').next;
  let scheduled=observation();recurring(scheduled);assert(ops.valid(scheduled));
  assert.equal(next(scheduled),'QRSS: CQ AA0NT');
  for(const mode of ['qrss','fskcw','dfcw']) {scheduled.message_schedule.saved.message.mode=mode;assert.equal(next(scheduled),mode.toUpperCase()+': CQ AA0NT');}
  scheduled.message_schedule.saved.message.mode='qrss';scheduled.standalone.enabled=true;
  for(const start of ['1800000060000000000','1800000120000000000','1800000240000000000']) {
    scheduled.next_wspr_start_utc_ns=start;assert.equal(next(scheduled),'QRSS: CQ AA0NT','message recurrence owns scheduling regardless of WSPR timing');
  }
  for(const state of ['paused','pausing','expired','waiting_for_time','waiting_for_transmitter','recovery_required','restart_required','suspended','unavailable','running']) {
    const blocked=structuredClone(scheduled);blocked.message_schedule.state=state;assert.equal(next(blocked),'',state);
  }
  for(const mutate of [x=>x.message_schedule.pause_pending=true,x=>x.standalone.storage_healthy=false,
    x=>x.standalone.reboot_required=true,x=>x.standalone.suspended=true,x=>x.standalone.clock_state='unsynchronized',
    x=>x.standalone.sync_age_ns='3600000000001',x=>x.standalone.uncertainty_ns='1000001',
    x=>x.job.state='failed',x=>x.message_schedule.next_start_utc_ns=null,
    x=>x.message_schedule.next_start_utc_ns=x.standalone.utc_now_ns,
    x=>x.message_schedule.saved.expires_utc_s=1800000120]) {
    const blocked=structuredClone(scheduled);mutate(blocked);assert.equal(next(blocked),'');
  }
  const armed=structuredClone(scheduled);active(armed,'qrss');armed.job.state=armed.standalone.state='armed';armed.message_schedule.state='armed';
  assert.equal(next(armed),'QRSS: CQ AA0NT');armed.message_schedule.saved.enabled=false;armed.standalone.enabled=false;
  assert.equal(next(armed),'');assert.equal(ops.model(armed,caps,'x').state,'Job armed');
  scheduled.message_schedule.saved.enabled=false;scheduled.message_schedule.state='paused';
  assert.equal(next(scheduled),'WSPR');
  for(const mutate of [x=>x.standalone.enabled=false,x=>x.standalone.configured=false,x=>x.standalone.frequency_required=true,
    x=>x.job.owner_id='4'.repeat(32),x=>x.job.output_active=true,x=>x.standalone.wspr_pair_pending=true,
    x=>x.next_wspr_start_utc_ns=null,x=>x.next_wspr_start_utc_ns=x.standalone.utc_now_ns,
    x=>x.standalone.expires_utc_s=1800000240]) {
    const blocked=structuredClone(scheduled);mutate(blocked);assert.equal(next(blocked),'');
  }
  for(const [correction,text] of [[{next_ppb:0},'0.000'],[{next_ppb:-3470,prepared_ppb:9000},'-3.470'],[null,'Unavailable']]) {
    const corrected=observation();corrected.correction=correction;assert.equal(ops.model(corrected,caps,'x').correction,text);
  }
  let v=observation();assert(ops.valid(v));
  assert.equal(ops.model(v,caps,'9'.repeat(32)).state,'Schedules disabled');
  v.standalone.enabled=true;assert.equal(ops.model(v,caps,'9'.repeat(32)).state,'Waiting for next occurrence');
  assert.equal(ops.model(v,caps,'9'.repeat(32)).next,'');
  v.standalone.sync_age_ns='0';assert.equal(ops.model(v,{wtp:{maximum_holdover_age_ns:'0'}},'x').state,'Waiting for time');
  v.standalone.sync_age_ns='3600000000001';assert.equal(ops.model(v,caps,'9'.repeat(32)).state,'Waiting for time');
  v.message_schedule.saved={enabled:false,first_start_utc_ns:'1800000000000000000',period_s:120,expires_utc_s:0,message:{mode:'qrss',message:'PRIVATE',frequency_nhz:'135500000000000',space_frequency_nhz:'0',timing:{dot_ns:'1000000000',dash_ns:'3000000000',intra_gap_ns:'1000000000',character_gap_ns:'3000000000',word_gap_ns:'7000000000'},repeat_count:1,repeat_gap_ns:'0',allow_frequency_adjustment:true}};v.message_schedule.state='paused';v.standalone.sync_age_ns='0';assert.equal(ops.model(v,caps,'x').state,'Waiting for next occurrence');
  const failed=observation();failed.standalone.enabled=true;failed.standalone.clock_state='synchronized';
  failed.next_wspr_start_utc_ns='1800000120000000000';
  failed.standalone.last_error={code:'INTERNAL_ERROR',message:'INTERNAL_ERROR',retryable:false};
  assert(ops.valid(failed));
  assert.equal(ops.model(failed,caps,'x').state,'WSPR transmission failed');
  assert.match(ops.model(failed,caps,'x').warning,/WSPR occurrence failed.*INTERNAL_ERROR.*skipped/);
  assert.equal(next(failed),'','a failed load must not promise the next transmission');
  failed.standalone.uncertainty_ns='1000001';
  assert.match(ops.model(failed,caps,'x').warning,/Clock uncertainty.*1 ms.*INTERNAL_ERROR/,'simultaneous blockers remain visible');
  failed.standalone.last_error=null;
  assert.match(ops.model(failed,caps,'x').warning,/Clock uncertainty/);
  failed.standalone.uncertainty_ns='1000000';
  assert.equal(ops.model(failed,caps,'x').warning,'','exact clock boundary and confirmed success clear the warning');
  assert.equal(next(failed),'WSPR');
  failed.standalone.last_error={code:'INTERNAL_ERROR',message:'old',retryable:false};
  active(failed);assert.equal(ops.model(failed,caps,'x').state,'Job running');
  assert.doesNotMatch(ops.model(failed,caps,'x').warning,/WSPR occurrence failed/,'accepted-job authority supersedes historical load failure');
  failed.standalone.uncertainty_ns='1000001';assert.match(ops.model(failed,caps,'x').warning,/accepted job remains running/);
  const owned=observation();owned.standalone.enabled=true;owned.standalone.clock_state='synchronized';owned.job.owner_id='4'.repeat(32);
  assert.match(ops.model(owned,caps,'4'.repeat(32)).warning,/This browser.*Release control/);
  assert.match(ops.model(owned,caps,'5'.repeat(32)).warning,/Another controller/);
  owned.job.state=owned.standalone.state='failed';
  assert.doesNotMatch(ops.model(owned,caps,'4'.repeat(32)).warning,/Choose Release control/,'fault recovery must not recommend an ineligible release');
  owned.job.state=owned.standalone.state='complete';owned.job.output_active=true;
  assert.doesNotMatch(ops.model(owned,caps,'4'.repeat(32)).warning,/Choose Release control/,'unknown active output retains recovery guidance');
  const oldMessage=observation();recurring(oldMessage);oldMessage.message_schedule.saved.enabled=false;
  oldMessage.message_schedule.state='expired';oldMessage.standalone.enabled=true;oldMessage.standalone.clock_state='synchronized';
  oldMessage.next_wspr_start_utc_ns='1800000120000000000';
  assert.equal(ops.model(oldMessage,caps,'x').state,'Waiting for next occurrence','expired disabled message history must not mask current WSPR authority');
  const disabled=observation();disabled.standalone.last_error={code:'INTERNAL_ERROR',message:'old',retryable:false};
  assert.equal(ops.model(disabled,caps,'x').warning,'','disabled WSPR does not keep a stale failure banner');
  for(const mutate of [x=>delete x.standalone.last_error,x=>x.standalone.last_error=[],x=>x.standalone.last_error={code:'INTERNAL_ERROR'},x=>x.message_schedule.last_error={code:'bad',message:'bad',retryable:false}]) {
    const bad=structuredClone(disabled);mutate(bad);assert.equal(ops.valid(bad),false);
  }
  active(v);assert(ops.valid(v));
  let view=ops.model(v,caps,'9'.repeat(32));assert.equal(view.state,'Job running');assert.match(view.explanation,/keyed gaps/);assert.equal(view.reset,false);
  assert.equal(view.frequency,'135.505/135.500 kHz');assert.equal(view.progress,'Running · ~100%');assert.equal(view.correction,'3.470');
  assert.match(view.actions,/cannot abort/);
  v.standalone.configured=false;v.standalone.frequency_required=true;assert.equal(ops.model(v,caps,'x').state,'Job running');
  v.message_schedule.state='recovery_required';assert.equal(ops.model(v,caps,'x').state,'Job running');
  for(const mode of ['qrss','fskcw','dfcw','tone','arbitrary']) {
    v=observation();active(v,mode);if(['tone','arbitrary'].includes(mode))v.accepted.message=null;
    assert(ops.valid(v));view=ops.model(v,caps,'x');
    assert.equal(view.frequency,mode==='qrss'?'135.505 kHz':mode==='fskcw'?'135.500/135.505 kHz':mode==='dfcw'?'135.505/135.500 kHz':'135.500–135.505 kHz');
    if(!v.accepted.message)assert.equal(view.message,'Text unavailable');
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
  const basic=await fixture();assert.equal(basic.elements['console-state'].textContent,'Job empty');assert.equal(basic.elements['console-warning'].hidden,true);basic.state.job.state='invented';await basic.elements.refresh.onclick();assert.equal(basic.elements['console-state'].textContent,'Status unavailable');assert.equal(basic.elements.restart.disabled,true);assert.equal(basic.elements.settings.disabled,true);
  const rebound=await fixture();rebound.state.job.boot_id='b'.repeat(32);await rebound.elements.refresh.onclick();assert.equal(rebound.elements['console-state'].textContent,'Job empty');rebound.state.job.boot_id='c'.repeat(32);rebound.hostnameDevice='2'.repeat(32);await rebound.elements.refresh.onclick();assert.equal(rebound.elements['console-state'].textContent,'Status unavailable');assert.equal(rebound.elements.restart.disabled,true);
  const f=await fixture();f.operations=observation();Object.assign(f.operations.network,f.state.network);
  vm.runInContext('capabilities=null',f.context);await f.elements.refresh.onclick();
  assert.equal(f.elements['console-state'].textContent,'Schedules disabled');
  assert.equal(f.elements['console-warning'].hidden,true);assert.equal(f.elements['console-next-item'].hidden,true);
  f.operations.standalone.clock_state='synchronized';f.operations.standalone.enabled=true;f.operations.next_wspr_start_utc_ns='1800000120000000000';
  await f.elements.refresh.onclick();assert.equal(f.elements['console-next'].textContent,'WSPR');assert.equal(f.elements['console-next-item'].hidden,false);
  recurring(f.operations);await f.elements.refresh.onclick();assert.equal(f.elements['console-next'].textContent,'QRSS: CQ AA0NT');
  f.operations.message_schedule.saved.enabled=false;f.operations.standalone.enabled=false;
  await f.elements.refresh.onclick();assert.equal(f.elements['console-next-item'].hidden,true);assert.equal(f.elements['console-next'].textContent,'');
  f.savedHostname='future.local';await f.elements.refresh.onclick();assert.equal(f.elements['device-name'].textContent,'old.local');
  assert.equal(f.elements.network.textContent,'Connected · 127.0.0.1');assert.equal(f.elements.owner.textContent,'Available');
  assert.equal(f.elements['discovery-help'].textContent,'');
  f.operations=structuredClone(failed);f.operations.job.state=f.operations.standalone.state='empty';
  f.operations.job.job_id=f.operations.standalone.job_id=null;f.operations.job.owner_id=f.operations.standalone.owner_id=null;f.operations.accepted=null;
  await f.elements.refresh.onclick();
  assert.equal(f.elements['console-warning'].hidden,false);assert.equal(f.elements['console-state'].hidden,false);
  assert.match(f.elements['console-warning'].textContent,/Clock uncertainty.*INTERNAL_ERROR/);
  f.operations.standalone.last_error=null;f.operations.standalone.uncertainty_ns='1000';
  await f.elements.refresh.onclick();assert.equal(f.elements['console-warning'].hidden,true);
  f.elements['message-text'].value='KEEP DRAFT';active(f.operations);await f.elements.refresh.onclick();
  assert.equal(f.elements['console-state'].textContent,'Job running');assert.equal(f.elements.restart.disabled,true);assert.equal(f.elements['message-text'].value,'KEEP DRAFT');
  f.now+=15001;vm.runInContext('consoleTick()',f.context);assert.equal(f.elements['console-state'].textContent,'Status unavailable');assert.equal(f.elements.restart.disabled,true);assert.equal(f.elements['console-next-item'].hidden,true);assert.match(f.elements['device-name-state'].textContent,/Last confirmed/);
  await f.elements.refresh.onclick();assert.equal(f.elements['console-state'].textContent,'Job running');
  f.operations.target.device_id='2'.repeat(32);await f.elements.refresh.onclick();assert.equal(f.elements['console-state'].textContent,'Status unavailable');assert.equal(f.elements['console-message'].textContent,'Unavailable');
  f.operations=observation();Object.assign(f.operations.network,f.state.network);await f.elements.refresh.onclick();
  let release;f.delayObservation=new Promise(r=>{release=r;});const pending=vm.runInContext('refresh()',f.context);await new Promise(setImmediate);
  vm.runInContext('++observationEpoch; clearConsole("Canceled observation")',f.context);release();await pending;assert.equal(f.elements['console-state'].textContent,'Status unavailable');
  const pub=await fixture(true,true,false,true);pub.state.job.state='running';pub.state.job.output_active=false;await pub.elements.refresh.onclick();
  assert.equal(pub.elements['console-warning'].hidden,true);assert.equal(pub.elements.restart.disabled,true);assert.match(pub.elements['console-message'].textContent,/Unavailable/);
  pub.state.job.state='complete';pub.state.job.output_active=true;await pub.elements.refresh.onclick();assert.equal(pub.elements['console-state'].textContent,'Recovery required');assert.match(pub.elements['console-warning'].textContent,/RF is reported active/);
  const expired=await fixture(true,true,false,true);await expired.elements['local-login'].onsubmit({preventDefault(){}});expired.elements['saved-active-status'].textContent='PRIVATE';expired.elements['saved-readback-details'].hidden=false;expired.radio.authenticated=false;await vm.runInContext('api("status").catch(()=>{})',expired.context);vm.runInContext('controls(true)',expired.context);assert.equal(expired.elements['station-settings-lock'].disabled,true);assert.equal(expired.elements['save-config'].disabled,true);
  const lost=await fixture(true,true,false,true);await lost.elements['local-login'].onsubmit({preventDefault(){}});lost.state.job.owner_id=vm.runInContext('session',lost.context);lost.state.job.state='armed';lost.state.job.job_id='3'.repeat(32);await lost.elements.refresh.onclick();assert.equal(lost.elements.abort.disabled,false);lost.radio.authenticated=false;vm.runInContext('controls(true)',lost.context);assert.equal(lost.elements.abort.disabled,true);assert.equal(lost.elements.restart.disabled,true);assert.equal(lost.elements['station-settings-lock'].disabled,true);
  for(const phase of ['confirmation','readback']) { const late=await fixture();if(phase==='confirmation')late.confirmAdvance=16000;else late.expireResetRead=true;await late.elements.restart.onclick();assert.equal(late.calls.filter(c=>c.path.endsWith('restart')).length,0);assert.match(late.elements.notice.textContent,/No reset was sent/);assert.doesNotMatch(late.elements.notice.textContent,/Cannot read/); }
  const reset=await fixture();reset.operations=observation();Object.assign(reset.operations.network,reset.state.network);vm.runInContext('capabilities=null',reset.context);await reset.elements.refresh.onclick();await reset.elements.restart.onclick();await new Promise(setImmediate);assert.match(reset.elements['restart-status'].textContent,/Same Pico and new boot confirmed/);assert.equal(reset.calls.filter(c=>c.path.endsWith('restart')).length,1);
  console.log('Operations: precedence, modes, keyed gaps, privacy, freshness, cancellation and retained drafts passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
module.exports={observation,active};
