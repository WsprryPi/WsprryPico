'use strict';
// Presentation of one device observation. No transport, storage or RF authority.
(function(root) {
  const id=v=>typeof v==='string'&&/^[0-9a-f]{32}$/.test(v);
  const decimal=v=>typeof v==='string'&&/^(0|[1-9][0-9]{0,19})$/.test(v)&&BigInt(v)<=18446744073709551615n;
  const keys=(v,k)=>v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join(',')===k.split(',').sort().join(',');
  const states=['empty','loaded','armed','running','complete','aborted','missed','failed'];
  const validError=value=>root.WsprryMessageSchedule?.validError(value)===true;
  const clocks=['synchronized','holdover','unsynchronized'];
  const control=root.WsprryControl || (typeof module!=='undefined' && module.exports ? require('./control-contract.js') : null);
  const supported=value=>!!control && control.supported('operations_status',value);
  function basicValid(v,boot) {
    const j=v?.job,s=v?.standalone,n=v?.network;
    return !!j&&states.includes(j.state)&&id(j.boot_id)&&(!boot||j.boot_id===boot)&&
      (j.job_id===null||id(j.job_id))&&(j.owner_id===null||id(j.owner_id))&&typeof j.output_active==='boolean'&&
      !!s&&typeof s.storage_healthy==='boolean'&&typeof s.reboot_required==='boolean'&&clocks.includes(s.clock_state)&&decimal(s.uncertainty_ns)&&
      typeof s.engine==='string'&&s.engine.length<=64&&!!n&&typeof n.enabled==='boolean';
  }
  function valid(v,expected) {
    if (!keys(v,'schema,target,job,accepted,standalone,message_schedule,next_wspr_start_utc_ns,correction,reset_allowed,network,transport') || v.schema!=='operations' ||
        !keys(v.target,'scope,device_id,boot_id') || v.target.scope!=='member' || !id(v.target.device_id) || !id(v.target.boot_id) ||
        expected && (v.target.device_id!==expected.device_id || v.target.boot_id!==expected.boot_id) ||
        v.job?.boot_id!==v.target.boot_id || !states.includes(v.job.state) || typeof v.job.output_active!=='boolean' ||
        !(v.job.owner_id===null||id(v.job.owner_id)) || !(v.job.job_id===null||id(v.job.job_id)) ||
        typeof v.reset_allowed!=='boolean' || !v.network || typeof v.network.enabled!=='boolean') return false;
    const s=v.standalone, m=v.message_schedule, a=v.accepted;
    if(v.correction!==null&&(!v.correction||!Number.isInteger(v.correction.next_ppb)||!(v.correction.prepared_ppb===null||Number.isInteger(v.correction.prepared_ppb))))return false;
    if(!keys(m,'saved,state,pause_pending,next_start_utc_ns,last_start_utc_ns,last_job_id,last_result,last_error') || !validError(m.last_error))return false;
    if (!s || !validError(s.last_error) || s.boot_id!==v.target.boot_id || s.job_id!==v.job.job_id || s.state!==v.job.state ||
        !clocks.includes(s.clock_state) || ![s.utc_now_ns,s.uncertainty_ns,s.sync_age_ns].every(decimal) ||
        !['configured','enabled','storage_healthy','reboot_required','suspended','frequency_required','wspr_pair_pending'].every(k=>typeof s[k]==='boolean') ||
        !Array.isArray(s.schedules)||s.schedules.length>8 || !s.schedules.every(x=>Number.isInteger(x.period_s)&&x.period_s>0&&Number.isInteger(x.phase_s)&&x.phase_s>=0&&x.phase_s<x.period_s) ||
        !Number.isSafeInteger(s.expires_utc_s)||s.expires_utc_s<0 || !(s.schedule_dial_frequency_nhz===null||decimal(s.schedule_dial_frequency_nhz)) ||
        !root.WsprryMessageSchedule?.valid({schema:'message-schedule',target:v.target,writable:false,...m},v.target) ||
        !(v.next_wspr_start_utc_ns===null||decimal(v.next_wspr_start_utc_ns))) return false;
    if (a===null) return v.job.job_id===null;
    if (!v.job.job_id || !keys(a,'mode,duration_ns,start_utc_ns,event_count,frequencies_nhz,frequencies_truncated,message') || typeof a.mode!=='string'||a.mode.length>32||
        !decimal(a.duration_ns)||BigInt(a.duration_ns)===0n || !(a.start_utc_ns===null||decimal(a.start_utc_ns)) ||
        !Number.isInteger(a.event_count)||a.event_count<1||a.event_count>512||!Array.isArray(a.frequencies_nhz)||a.frequencies_nhz.length>4||!a.frequencies_nhz.every(decimal)||typeof a.frequencies_truncated!=='boolean') return false;
    const p=a.message;
    return p===null || keys(p,'text,frequency_nhz,space_frequency_nhz,dot_ns,dash_ns,repeat_gap_ns,repeat_count')&&['qrss','fskcw','dfcw'].includes(a.mode)&&typeof p.text==='string'&&p.text.length<=32&&
      [p.frequency_nhz,p.space_frequency_nhz,p.dot_ns,p.dash_ns,p.repeat_gap_ns].every(decimal)&&Number.isInteger(p.repeat_count)&&p.repeat_count>=1&&p.repeat_count<=512;
  }
  // Exact decimal scaling from nominal nanohertz. One bounded value/list at a
  // time; no floating-point conversion, lookup tables or retained snapshots.
  function formatFrequencies(values,separator='/') {
    if (!values.length || !values.every(decimal)) return 'Unavailable';
    const numbers=values.map(BigInt), maximum=numbers.reduce((a,b)=>a>b?a:b);
    const digits=maximum>=1000000000000000n?15:maximum>=1000000000000n?12:9;
    const divisor=10n**BigInt(digits), unit=digits===15?'MHz':digits===12?'kHz':'Hz';
    const parts=numbers.map(n=>[(n/divisor).toString(),(n%divisor).toString().padStart(digits,'0').replace(/0+$/,'')]);
    const precision=Math.max(...parts.map(p=>p[1].length));
    return parts.map(p=>p[0]+(precision?'.'+p[1].padEnd(precision,'0'):'')).join(separator)+' '+unit;
  }
  const formatFrequency=n=>formatFrequencies([n]);
  const utc=n=>{if(n===null||!decimal(n))return 'Unavailable';const d=new Date(Number(BigInt(n)/1000000n));return Number.isFinite(d.getTime())?d.toISOString().replace('T',' ').replace('.000Z',' UTC'):'Unavailable';};
  function armedStart(start,now) {
    const text=utc(start), today=utc(now);
    if (text==='Unavailable' || today==='Unavailable') return '';
    const fraction=(BigInt(start)%1000000000n).toString().padStart(9,'0').replace(/0+$/,'');
    const second=text.slice(17,19), time=text.slice(11,16)+(second!=='00'||fraction?':'+second+(fraction?'.'+fraction:''):'');
    return (text.slice(0,10)===today.slice(0,10)?'':text.slice(0,10)+' ')+time+' UTC';
  }
  function frequencies(a,s,j) {
    if(a.mode==='wspr') {
      // CONFIG and independently owned dial updates require Scheduler::idle(),
      // which refuses an owner. The matching local scheduler job therefore
      // still has the dial used at preparation. Released history/external jobs
      // have no such binding; never substitute their current saved dial.
      return j.owner_id==='e'.repeat(32) && id(s.last_job) && s.last_job===j.job_id &&
        s.storage_healthy && decimal(s.schedule_dial_frequency_nhz) && BigInt(s.schedule_dial_frequency_nhz)>0n
        ?formatFrequency(s.schedule_dial_frequency_nhz):'Unavailable';
    }
    const p=a.message;
    if(p) return a.mode==='qrss'?formatFrequency(p.frequency_nhz):
      formatFrequencies(a.mode==='fskcw'?[p.space_frequency_nhz,p.frequency_nhz]:[p.frequency_nhz,p.space_frequency_nhz]);
    if(a.frequencies_truncated) return 'Multiple frequencies';
    const values=a.frequencies_nhz;
    if(values.length<2) return values.length?formatFrequency(values[0]):'Unavailable';
    const numbers=values.map(BigInt), low=numbers.reduce((a,b)=>a<b?a:b), high=numbers.reduce((a,b)=>a>b?a:b);
    return formatFrequencies([String(low),String(high)],'–');
  }
  function model(v,caps,session) {
    const j=v.job,s=v.standalone,m=v.message_schedule,a=v.accepted;
    const occupied=['loaded','armed','running'].includes(j.state);
    const clockReady=s.clock_state!=='unsynchronized' &&
      !(s.clock_state==='holdover'&&(!caps?.wtp?.maximum_holdover_age_ns||BigInt(caps.wtp.maximum_holdover_age_ns)===0n||BigInt(s.sync_age_ns)>BigInt(caps.wtp.maximum_holdover_age_ns))) &&
      !(caps?.wtp?.maximum_arm_uncertainty_ns&&BigInt(s.uncertainty_ns)>BigInt(caps.wtp.maximum_arm_uncertainty_ns));
    const wsprFailure=!!(s.enabled && !m.saved?.enabled && s.last_error && !occupied && !s.wspr_pair_pending);
    let state='Idle', explanation='No accepted job is active. Review future transmissions below.';
    if (!s.storage_healthy || j.state==='failed' || j.output_active&&!['armed','running'].includes(j.state)) {state='Recovery required';explanation='Output or storage authority needs recovery. Check Transmitter status; RF-off alone does not clear a fault.';}
    else if (occupied) {
      state=j.state==='running'?'Job running':j.state==='armed'?'Job armed':'Job loaded';
      explanation=j.state==='running'?(j.output_active?'The accepted job is running or completing amplifier tail. RF and amplifier activity are reported separately in Radio pins.':'The accepted job is still running. RF is off at this observation, including possible keyed gaps.'):
        j.state==='armed'?'The Pico holds an accepted job for its scheduled UTC start.':'A complete job is loaded; it has not started.';
    } else if (m.state==='recovery_required') {state='Schedule recovery required';explanation='A recurring occurrence has an unresolved recovery barrier. It will not replay automatically.';}
    else if (m.pause_pending) {state='Pause awaiting save';explanation='Future message occurrences are paused in memory. Keep the Pico powered until durable confirmation.';}
    else if (s.reboot_required) {state='Reset required';explanation='Saved changes need a normal Pico restart before new standalone jobs.';}
    else if (s.suspended || m.state==='suspended') {state='Standalone paused';explanation='Standalone operation is suspended. Review the saved schedule before resuming.';}
    else if (m.saved && !m.saved.enabled && !s.enabled) {state='Message schedule paused';explanation='The saved message schedule is disabled. Any accepted job keeps its own lifecycle.';}
    else if (m.saved?.enabled && m.state==='expired' || s.enabled && !m.saved?.enabled && s.expires_utc_s && BigInt(s.utc_now_ns)>=BigInt(s.expires_utc_s)*1000000000n) {state='Schedule expired';explanation='No further occurrence can start within the saved UTC schedule.';}
    else if (s.enabled || m.saved?.enabled) {
      if (!clockReady) {state='Waiting for time';explanation='The clock does not currently meet admission limits. An accepted job retains its own lifecycle.';}
      else if (s.enabled&&(!s.configured||s.frequency_required)) {state='Standalone setup required';explanation='Complete station settings and save a WSPR dial frequency before standalone operation.';}
      else if (j.owner_id) {state='Transmitter reserved';explanation='A controller holds the transmitter. Reading this page grants no ownership.';}
      else if (wsprFailure) {state='WSPR transmission failed';explanation='The last scheduled WSPR transmission failed before successful admission.';}
      else {state='Waiting for next occurrence';explanation='The saved schedule is enabled. The Pico prepares and checks each future job locally.';}
    } else if (['complete','aborted','missed'].includes(j.state)) {state='Job '+j.state;explanation='The Pico confirmed this job’s terminal state. Future schedules are shown separately.';}
    else if (j.owner_id) {state='Transmitter reserved';explanation='A controller holds the transmitter. Reading this page grants no ownership.';}
    else {state=s.configured?'Schedules disabled':'Standalone not configured';explanation='No standalone schedule is enabled. External controllers can submit complete jobs through their own authority.';}
    let next='';
    const future=(start,expiry)=>start!==null && BigInt(start)>BigInt(s.utc_now_ns) &&
      (!expiry || BigInt(start)<BigInt(expiry)*1000000000n);
    // The scheduler reserves recurrence authority for an enabled message schedule,
    // even when its next slot is later than a saved WSPR slot or is blocked.
    if (!wsprFailure && clockReady && s.storage_healthy && !s.reboot_required && !s.suspended && j.state!=='failed' &&
        !m.pause_pending && m.state!=='recovery_required') {
      if (m.saved?.enabled) {
        if (['waiting','armed'].includes(m.state) && future(m.next_start_utc_ns,m.saved.expires_utc_s))
          next=m.saved.message.mode.toUpperCase()+': '+m.saved.message.message;
      } else if (s.enabled && s.configured && !s.frequency_required && !occupied && !j.owner_id &&
          !j.output_active && !s.wspr_pair_pending && future(v.next_wspr_start_utc_ns,s.expires_utc_s)) next='WSPR';
    }
    const blockers=[];
    const scheduling=s.enabled || m.saved?.enabled;
    if(!s.storage_healthy) blockers.push('Storage fault; recover before transmitting.');
    if(j.state==='failed' || j.output_active&&!['armed','running'].includes(j.state)) blockers.push('Output recovery required; check output before reset.');
    if(s.reboot_required) blockers.push('Reset required for saved changes.');
    if(m.pause_pending) blockers.push('Future messages paused; pause not yet saved. Keep the Pico powered.');
    if(m.state==='recovery_required') blockers.push('Message schedule needs recovery; review its saved result.');
    if(scheduling) {
      if(s.suspended || m.state==='suspended') blockers.push('Standalone suspended; review the schedule before resuming.');
      if(!clockReady) {
        if(s.clock_state==='unsynchronized') blockers.push('Clock not synchronized; check the time server.');
        else if(caps?.wtp?.maximum_arm_uncertainty_ns && BigInt(s.uncertainty_ns)>BigInt(caps.wtp.maximum_arm_uncertainty_ns))
          blockers.push('Clock uncertainty exceeds '+(Number(BigInt(caps.wtp.maximum_arm_uncertainty_ns))/1000000)+' ms; wait for a better update.');
        else blockers.push('Clock update too old; check the time server.');
      }
      if(s.enabled && !m.saved?.enabled && (!s.configured || s.frequency_required)) blockers.push('WSPR setup incomplete; save station settings and dial frequency.');
      if(s.enabled && !m.saved?.enabled && !s.schedules.length) blockers.push('WSPR has no start times; save a schedule.');
      if(m.state==='expired' && m.saved?.enabled || s.enabled && !m.saved?.enabled && s.expires_utc_s && BigInt(s.utc_now_ns)>=BigInt(s.expires_utc_s)*1000000000n)
        blockers.push('Schedule expired; review its UTC end time.');
      if(!occupied && j.state!=='failed' && !j.output_active && j.owner_id) blockers.push(j.owner_id===session?'This browser holds the transmitter; choose Release control for standalone schedules.':'Another controller holds the transmitter; release it through that controller.');
      if(m.saved?.enabled && m.state==='unavailable') blockers.push('Message schedule unavailable; review its settings.');
    }
    if(wsprFailure) blockers.push('WSPR occurrence failed ('+s.last_error.code+'); skipped without retry. Review station, clock and transmitter settings.');
    if(m.saved?.enabled && m.last_error && !occupied) blockers.push('Message occurrence failed ('+m.last_error.code+'); review its saved result.');
    if(scheduling && !occupied && !s.wspr_pair_pending && !next && !blockers.length)
      blockers.push('No eligible next transmission; review the schedule and transmitter.');
    const warning=blockers.length?(occupied?'Future transmissions blocked; accepted job remains '+j.state+'. ':'')+blockers.join(' '):'';
    let progress=a?j.state[0].toUpperCase()+j.state.slice(1):'—';
    if(a && j.state==='armed') {
      const start=armedStart(a.start_utc_ns,s.utc_now_ns);
      if(start) progress+=' · '+start;
    }
    if(a && j.state==='running' && a.start_utc_ns && s.clock_state!=='unsynchronized') {
      const duration=BigInt(a.duration_ns);
      let elapsed=BigInt(s.utc_now_ns)-BigInt(a.start_utc_ns);
      elapsed=elapsed<0n?0n:elapsed>duration?duration:elapsed;
      progress+=' · ~'+((elapsed*100n+duration/2n)/duration)+'%';
    }
    if(a?.mode==='wspr' && j.state==='running' && id(s.last_job) && s.last_job===j.job_id &&
        s.wspr_frames===2 && Number.isInteger(s.wspr_frame) && s.wspr_frame>=1 && s.wspr_frame<=2)
      progress=progress.replace('Running','Frame '+s.wspr_frame+'/2');
    const correction=v.correction;
    const ppm=n=>Number.isInteger(n)?(n/1000).toFixed(3):'Unavailable';
    return {state,explanation:explanation+(occupied&&(!s.storage_healthy||m.pause_pending||m.state==='recovery_required')?' Accepted job: '+j.state+'. Future-schedule blockers do not declare completion.':''),
      mode:a?(a.mode==='tone'?'Test tone':a.mode.toUpperCase()||'RF events'):m.saved?.enabled?m.saved.message.mode.toUpperCase()+' · scheduled':s.enabled?'WSPR · scheduled':'No job',
      frequencyLabel:a?.mode==='wspr'?'Dial frequency':a?.message?({qrss:'Carrier',fskcw:'Space/Mark',dfcw:'Dot/Dash'}[a.mode]):'Frequency',
      frequency:a?frequencies(a,s,j):'—',
      message:a?.mode==='wspr'?'Encoded WSPR frame':a?.message?a.message.text:a?(a.mode==='tone'&&a.frequencies_nhz.length===1&&!a.frequencies_truncated?'—':'Text unavailable'):'—',
      progress,next,warning,correction:ppm(correction?.next_ppb),
      reset:v.reset_allowed&&!occupied&&!j.owner_id&&j.output_active===false,
      actions:j.owner_id===session?'This browser owns the job; its eligible Abort and Release controls are below.':j.owner_id?'Another controller or the Pico scheduler owns the transmitter. This browser cannot abort or take over.':'No job owner. Reset requires a current authenticated idle observation.'};
  }
  root.WsprryOperations={supported,valid,basicValid,model,formatFrequency,formatFrequencies,utc,validError};
  if(typeof module!=='undefined')module.exports=root.WsprryOperations;
})(globalThis);
