'use strict';
(function(root){
  const keys=(v,n)=>v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join(',')===n.split(',').sort().join(',');
  const decimal=v=>typeof v==='string'&&/^(0|[1-9][0-9]{0,19})$/.test(v)&&BigInt(v)<=18446744073709551615n;
  const id=v=>typeof v==='string'&&/^[0-9a-f]{32}$/.test(v);
  const errorCodes=["INVALID_FRAME","INVALID_MESSAGE","UNSUPPORTED_VERSION","HELLO_REQUIRED","UNKNOWN_OPERATION","AUTHENTICATION_REQUIRED","SESSION_REPLACED","BUSY","NOT_OWNER","LEASE_EXPIRED","REQUEST_ID_REUSE","INVALID_STATE","JOB_NOT_FOUND","JOB_ID_CONFLICT","JOB_LIMIT_EXCEEDED","UNSUPPORTED_PROFILE","UNSUPPORTED_MODE","FREQUENCY_REJECTED","ARM_CONFLICT","CLOCK_UNSYNCHRONIZED","CLOCK_UNCERTAIN","LEAP_UNSAFE","ARM_TOO_LATE","ARM_TOO_FAR","MISSED_START","OUTPUT_STATE_UNKNOWN","DEVICE_FAULT","INTERNAL_ERROR"];
  function validError(value) {
    if (value===null) return true;
    if (!value || typeof value!=='object' || Array.isArray(value) ||
        !['code','message','retryable'].every(key=>Object.hasOwn(value,key)) ||
        Object.keys(value).some(key=>!['code','message','retryable','detail'].includes(key)) ||
        !errorCodes.includes(value.code) || typeof value.message!=='string' || !value.message.length || value.message.length>256 ||
        typeof value.retryable!=='boolean' || Object.hasOwn(value,'detail') &&
        (!value.detail || typeof value.detail!=='object' || Array.isArray(value.detail))) return false;
    let bytes=0;
    for(const character of value.message) {
      const point=character.codePointAt(0);
      if(point>=0xd800 && point<=0xdfff) return false;
      bytes+=point<=0x7f?1:point<=0x7ff?2:point<=0xffff?3:4;
    }
    return bytes<=256;
  }
  const states=['not_configured','unavailable','pausing','recovery_required','paused','suspended','restart_required','waiting_for_time','expired','waiting','waiting_for_transmitter','empty','loaded','armed','running','complete','failed','aborted','missed'];
  function schedule(v){
    if(!keys(v,'enabled,first_start_utc_ns,period_s,expires_utc_s,message')||typeof v.enabled!=='boolean'||!decimal(v.first_start_utc_ns)||BigInt(v.first_start_utc_ns)<1735689600000000000n||BigInt(v.first_start_utc_ns)>=4102444800000000000n||!Number.isInteger(v.period_s)||v.period_s<60||v.period_s>86400||v.period_s%60||!Number.isSafeInteger(v.expires_utc_s)||v.expires_utc_s<0||v.expires_utc_s>4102444800||(v.expires_utc_s&&BigInt(v.expires_utc_s)*1000000000n<=BigInt(v.first_start_utc_ns)))return false;
    const m=v.message;
    return keys(m,'mode,message,frequency_nhz,space_frequency_nhz,timing,repeat_count,repeat_gap_ns,allow_frequency_adjustment')&&['qrss','fskcw','dfcw'].includes(m.mode)&&typeof m.message==='string'&&m.message.length>0&&m.message.length<=32&&m.message.trim().length>0&&/^[A-Za-z0-9 /?.,+=-]+$/.test(m.message)&&
      decimal(m.frequency_nhz)&&BigInt(m.frequency_nhz)>0n&&decimal(m.space_frequency_nhz)&&(m.mode!=='dfcw'||BigInt(m.frequency_nhz)<BigInt(m.space_frequency_nhz))&&(m.mode!=='fskcw'||BigInt(m.space_frequency_nhz)>0n&&BigInt(m.frequency_nhz)>BigInt(m.space_frequency_nhz))&&keys(m.timing,'dot_ns,dash_ns,intra_gap_ns,character_gap_ns,word_gap_ns')&&Object.values(m.timing).every(x=>decimal(x)&&BigInt(x)>0n)&&Number.isInteger(m.repeat_count)&&m.repeat_count>=1&&m.repeat_count<=512&&decimal(m.repeat_gap_ns)&&(m.repeat_count===1||BigInt(m.repeat_gap_ns)>0n)&&typeof m.allow_frequency_adjustment==='boolean';
  }
  function valid(v,context={}){
    return keys(v,'schema,target,writable,saved,state,pause_pending,next_start_utc_ns,last_start_utc_ns,last_job_id,last_result,last_error')&&v.schema==='message-schedule'&&keys(v.target,'scope,device_id,boot_id')&&v.target.scope==='member'&&id(v.target.device_id)&&id(v.target.boot_id)&&
      (!context.device_id||context.device_id===v.target.device_id)&&(!context.boot_id||context.boot_id===v.target.boot_id)&&typeof v.writable==='boolean'&&typeof v.pause_pending==='boolean'&&states.includes(v.state)&&
      (v.saved===null||schedule(v.saved))&&[v.next_start_utc_ns,v.last_start_utc_ns].every(x=>x===null||decimal(x))&&(v.last_job_id===null||id(v.last_job_id))&&(v.last_result===null||['complete','failed','aborted','missed'].includes(v.last_result))&&
      validError(v.last_error);
  }
  const api={valid,schedule,validError};root.WsprryMessageSchedule=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
