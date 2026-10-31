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
  const hz=n=>{const b=BigInt(n);return (b/1000000000n).toString()+(b%1000000000n?'.'+(b%1000000000n).toString().padStart(9,'0').replace(/0+$/,''):'')+' Hz';};
  const seconds=n=>{const b=BigInt(n);return (b/1000000000n).toString()+(b%1000000000n?'.'+(b%1000000000n).toString().padStart(9,'0').replace(/0+$/,''):'')+' s';};
  const utc=n=>{if(n===null||!decimal(n))return 'Unavailable';const d=new Date(Number(BigInt(n)/1000000n));return Number.isFinite(d.getTime())?d.toISOString().replace('T',' ').replace('.000Z',' UTC'):'Unavailable';};
  function frequencies(mode,p,values=[],truncated=false) {
    if (p) {
      if (mode==='qrss') return 'Carrier '+hz(p.frequency_nhz);
      const delta=BigInt(p.space_frequency_nhz)-BigInt(p.frequency_nhz);
      const shift=hz(delta<0n?-delta:delta);
      return mode==='dfcw' ? 'Dot '+hz(p.frequency_nhz)+'\nDash '+hz(p.space_frequency_nhz)+' · separation '+shift :
        'Space '+hz(p.space_frequency_nhz)+'\nMark '+hz(p.frequency_nhz)+' · shift '+shift;
    }
    return values.length?'Nominal RF '+values.map(hz).join(' / ')+(truncated?' · additional frequencies retained by the engine':''):'Unavailable';
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
    if(!s.storage_healthy) blockers.push('Saved storage is unhealthy. Resolve the storage fault before transmitting.');
    if(j.state==='failed' || j.output_active&&!['armed','running'].includes(j.state)) blockers.push('RF output or job authority needs recovery. Check output before resetting the Pico.');
    if(s.reboot_required) blockers.push('Saved changes require Reset Pico before new standalone transmissions.');
    if(m.pause_pending) blockers.push('Message-schedule pause is awaiting durable confirmation. Keep the Pico powered.');
    if(m.state==='recovery_required') blockers.push('The message schedule needs recovery. Review its saved result before resuming.');
    if(scheduling) {
      if(s.suspended || m.state==='suspended') blockers.push('Standalone transmissions are suspended. Review the schedule before resuming.');
      if(!clockReady) {
        if(s.clock_state==='unsynchronized') blockers.push('Transmission is blocked: the clock has not synchronized. Check the time-server connection.');
        else if(caps?.wtp?.maximum_arm_uncertainty_ns && BigInt(s.uncertainty_ns)>BigInt(caps.wtp.maximum_arm_uncertainty_ns))
          blockers.push('Transmission is blocked: clock uncertainty exceeds the '+(Number(BigInt(caps.wtp.maximum_arm_uncertainty_ns))/1000000)+' ms limit. Wait for a better time update.');
        else blockers.push('Transmission is blocked: the last clock update is too old. Check the time-server connection.');
      }
      if(s.enabled && !m.saved?.enabled && (!s.configured || s.frequency_required)) blockers.push('WSPR is blocked: complete station settings and save a dial frequency.');
      if(s.enabled && !m.saved?.enabled && !s.schedules.length) blockers.push('WSPR is enabled without any start times. Save a WSPR schedule.');
      if(m.state==='expired' && m.saved?.enabled || s.enabled && !m.saved?.enabled && s.expires_utc_s && BigInt(s.utc_now_ns)>=BigInt(s.expires_utc_s)*1000000000n)
        blockers.push('The standalone schedule has expired. Review its UTC end time.');
      if(!occupied && j.state!=='failed' && !j.output_active && j.owner_id) blockers.push(j.owner_id===session?'Transmission is blocked: this browser holds the transmitter. Choose Release control before the standalone schedule can use it.':'Transmission is blocked: another controller holds the transmitter. Release it through that controller.');
      if(m.saved?.enabled && m.state==='unavailable') blockers.push('The saved message schedule is unavailable. Review its settings before resuming.');
    }
    if(wsprFailure) blockers.push('The last scheduled WSPR transmission failed ('+s.last_error.code+'). '+
      (s.last_error.code==='INTERNAL_ERROR'?'The Pico could not prepare or load the job. ':'Review the station, clock and transmitter settings. ')+
      'That occurrence was skipped; it will not be retried.');
    if(m.saved?.enabled && m.last_error && !occupied) blockers.push('The last scheduled message failed ('+m.last_error.code+'). Review its saved result.');
    if(scheduling && !occupied && !s.wspr_pair_pending && !next && !blockers.length)
      blockers.push('No eligible future transmission is available. Review the schedule and transmitter status.');
    const warning=blockers.length?(occupied?"Future transmissions are blocked. Check the accepted job's current status below. ":'')+blockers.join(' '):'';
    let progress=a?'Job '+j.job_id+' · '+j.state+'\n'+a.event_count+' events · duration '+seconds(a.duration_ns)+(a.start_utc_ns?'\nStart '+utc(a.start_utc_ns):' · start not armed'):'No accepted job';
    if(a&&j.state==='running'&&a.start_utc_ns&&s.clock_state!=='unsynchronized') {
      let elapsed=BigInt(s.utc_now_ns)-BigInt(a.start_utc_ns), duration=BigInt(a.duration_ns);
      elapsed=elapsed<0n?0n:elapsed>duration?duration:elapsed;
      progress+='\nEstimated '+seconds(elapsed)+' / '+seconds(duration)+' · '+(Number(elapsed*1000n/duration)/10).toFixed(1)+'% · still running';
    }
    if(j.job_id&&s.last_job===j.job_id&&s.wspr_frame) progress+='\nStandalone WSPR frame '+s.wspr_frame+' of '+s.wspr_frames+(s.wspr_pair_pending?' · pair in progress':'');
    const correction=v.correction;
    const ppm=n=>Number.isInteger(n)?(n/1000).toFixed(3):'Unavailable';
    return {state,explanation:explanation+(occupied&&(!s.storage_healthy||m.pause_pending||m.state==='recovery_required')?' Accepted job: '+j.state+'. Future-schedule blockers do not declare completion.':''),
      mode:a?(a.mode.toUpperCase()||'RF events')+' · accepted job':m.saved?.enabled?m.saved.message.mode.toUpperCase()+' · saved recurrence':s.enabled?'WSPR · standalone schedule':'No accepted job',
      frequency:a?frequencies(a.mode,a.message,a.frequencies_nhz,a.frequencies_truncated):'No accepted job',
      message:a?.message?a.message.text+'\nDot '+seconds(a.message.dot_ns)+' · '+(a.mode==='dfcw'?'Dash element ':'Dash ')+seconds(a.message.dash_ns)+'\n'+a.message.repeat_count+(a.message.repeat_count===1?' message copy · between-copy gap ':' message copies · between-copy gap ')+seconds(a.message.repeat_gap_ns):a?'Original message and character position unavailable for this RF-event job':'No accepted message',
      progress,next,warning,correction:ppm(correction?.next_ppb),
      reset:v.reset_allowed&&!occupied&&!j.owner_id&&j.output_active===false,
      actions:j.owner_id===session?'This browser owns the job; its eligible Abort and Release controls are below.':j.owner_id?'Another controller or the Pico scheduler owns the transmitter. This browser cannot abort or take over.':'No job owner. Reset requires a current authenticated idle observation.'};
  }
  root.WsprryOperations={supported,valid,basicValid,model,hz,seconds,utc,validError};
  if(typeof module!=='undefined')module.exports=root.WsprryOperations;
})(globalThis);
