// Shared validation/presentation for the independently versioned draft resource.
// No persistence, networking, job control or secret storage in this helper.
(() => {
  const names = ['callsign','locator','power_dbm','enabled','schedules','expires_utc_s','pins','frequency_policy','wifi','ntp_ipv4'];
  const labels = {callsign:'Callsign',locator:'Grid locator',power_dbm:'Reported power',enabled:'Schedule enablement',schedules:'Schedules',expires_utc_s:'Schedule expiry',pins:'Pin plan',frequency_policy:'Frequency permissions',wifi:'Wi-Fi credentials',ntp_ipv4:'Time server'};
  const errors = {callsign:'use a valid 3–12 character station callsign',locator:'use a valid four- or six-character grid locator',power_dbm:'choose an exact supported power; zero dBm is valid',enabled:'choose enabled or disabled',schedules:'use interval / offset pairs in seconds without overlapping transmissions',expires_utc_s:'use a valid UTC expiry',pins:'use a complete supported pin plan with no conflicts',frequency_policy:'review both frequency permissions together',wifi:'provide a complete valid network name and password pair',ntp_ipv4:'use a valid hostname or IPv4 address'};
  const object = x => x !== null && typeof x === 'object' && !Array.isArray(x);
  const keys = (x, expected) => object(x) && Object.keys(x).sort().join(',') === [...expected].sort().join(',');
  const sequence = x => typeof x === 'string' && /^(0|[1-9][0-9]{0,19})$/.test(x) && BigInt(x) <= 0xffffffffffffffffn;
  const ascii = (x,min,max) => typeof x === 'string' && x.length >= min && x.length <= max && /^[\x20-\x7e]*$/.test(x);
  const call = x => ascii(x,3,12) && /^(?:[A-Z0-9]+(?:\/[A-Z0-9]+)*|<[A-Z0-9]+(?:\/[A-Z0-9]+)*>)$/.test(x) && /[A-Z]/.test(x) && /[0-9]/.test(x) && (!x.startsWith('<') || x.length >= 5);
  const grid = x => typeof x === 'string' && /^[A-R]{2}[0-9]{2}([A-X]{2})?$/.test(x);
  const power = x => typeof x === 'number' && [0,3,7,10,13,17,20,23,27,30,33,37,40,43,47,50,53,57,60].includes(x);
  const station = (x,partial = true) => keys(x,['callsign','locator','power_dbm']) &&
    (partial && x.callsign === null || call(x.callsign)) &&
    (partial && x.locator === null || grid(x.locator)) &&
    (partial && x.power_dbm === null || power(x.power_dbm));
  const outcomes = (x,amplifier = false) => object(x) && Object.keys(x).length <= names.length + (amplifier ? 1 : 0) && Object.entries(x).every(([k,v]) => (names.includes(k) || amplifier && k==='gpio_drive_ma') && ['saved','cleared','invalid'].includes(v));
  function validPlan(p) {
    if (!keys(p,['alternate_callsign','frame_types','frames','rationale','schema','slot_separation_s','supported','type2_ambiguous']) ||
        p.schema !== 'wspr-plan/1' || typeof p.supported !== 'boolean' || typeof p.type2_ambiguous !== 'boolean' ||
        !Array.isArray(p.frame_types) || !Number.isInteger(p.frames) || p.frames !== p.frame_types.length ||
        p.slot_separation_s !== 120 || !ascii(p.rationale,1,512)) return false;
    if (p.supported ? !['type1','type2','type3','type2,type3'].includes(p.frame_types.join(',')) : p.frames !== 0) return false;
    return p.type2_ambiguous ? p.supported && p.frame_types[0] === 'type2' && call(p.alternate_callsign) &&
      /^[A-Z0-9]+\/[A-Z0-9]+$/.test(p.alternate_callsign) : p.alternate_callsign === null;
  }
  function timeServer(x) {
    if (!ascii(x,1,253)) return false;
    if (/^[0-9.]+$/.test(x)) {
      const parts=x.split('.');
      return parts.length===4 && parts.every(v=>/^(0|[1-9][0-9]{0,2})$/.test(v) && Number(v)<=255) && Number(parts[0])>0 && Number(parts[0])<224 && parts[0]!=='127';
    }
    if (x.split('.').every(v=>/^(?:0[xX][0-9a-fA-F]+|[0-9]+)$/.test(v))) return false;
    return x.replace(/\.$/,'').split('.').every(v=>v.length<=63 && /^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$/.test(v));
  }
  const gp = x => Number.isInteger(x) && (x>=0 && x<=22 || x>=26 && x<=28);
  function pins(x,amplifier = false) {
    const members = ['engine','rf_gp','i2c_pair','button_gp','amplifier_gp','lpf_gps','indicator','indicator_gp','indicator_active_high'];
    if (amplifier && Object.hasOwn(x,'amplifier_active_high')) members.push('amplifier_active_high');
    if (!keys(x,members) ||
        x.engine!=='direct' || !gp(x.rf_gp) || x.i2c_pair!==null || !(x.button_gp===null || gp(x.button_gp)) ||
        !(x.amplifier_gp===null || amplifier && gp(x.amplifier_gp)) || !Array.isArray(x.lpf_gps) || x.lpf_gps.length ||
        x.amplifier_active_high!==undefined && typeof x.amplifier_active_high!=='boolean' ||
        !['onboard_led','external','disabled'].includes(x.indicator) || typeof x.indicator_active_high!=='boolean' ||
        (x.indicator==='external' ? !gp(x.indicator_gp) : x.indicator_gp!==null)) return false;
    const assigned=[x.rf_gp,x.button_gp,x.amplifier_gp,x.indicator==='external'?x.indicator_gp:null].filter(v=>v!==null);
    return new Set(assigned).size===assigned.length;
  }
  const gcd = (a,b) => b ? gcd(b,a%b) : a;
  function schedules(x) {
    return Array.isArray(x) && x.length<=8 && x.every((v,i)=>keys(v,['period_s','phase_s']) &&
      Number.isInteger(v.period_s) && v.period_s>=120 && v.period_s<=86400 && v.period_s%120===0 && 86400%v.period_s===0 &&
      Number.isInteger(v.phase_s) && v.phase_s>=0 && v.phase_s<v.period_s && v.phase_s%120===0 &&
      x.slice(0,i).every(p=>p.phase_s%gcd(p.period_s,v.period_s)!==v.phase_s%gcd(p.period_s,v.period_s)));
  }
  function field(k,v,amplifier = false) {
    if (k==='gpio_drive_ma') return amplifier && [2,4,8,12].includes(v);
    if (v===null) return true;
    if (k==='callsign') return call(v);
    if (k==='locator') return grid(v);
    if (k==='power_dbm') return power(v);
    if (k==='enabled') return typeof v==='boolean';
    if (k==='schedules') return schedules(v);
    if (k==='expires_utc_s') return Number.isInteger(v) && (v===0 || v>=1735689600 && v<=2147483647);
    if (k==='pins') return pins(v,amplifier);
    if (k==='wifi') return keys(v,['ssid','password']) && ascii(v.ssid,0,32) && v.password===null;
    if (k==='ntp_ipv4') return timeServer(v);
    if (k==='frequency_policy') return keys(v,['allow_unqualified_frequency','allow_non_amateur_frequency']) &&
      typeof v.allow_unqualified_frequency==='boolean' && typeof v.allow_non_amateur_frequency==='boolean' &&
      (!v.allow_non_amateur_frequency || v.allow_unqualified_frequency);
    return false;
  }
  function valid(x, acknowledgement = false) {
    const amplifier = x?.schema === 'transmitter-progress/3';
    const allowed = amplifier ? [...names,'gpio_drive_ma'] : names;
    const required = ['schema','target','draft_revision','config_revision','profile_revision','fields','last_receipt','last_outcomes','applied_station','station','station_complete','complete','apply_domains','wspr_plan','schedule_enabled','schedule_suspended','matches_applied'];
    if (acknowledgement) required.push('outcomes','request_id');
    if (!keys(x,required) || !['transmitter-progress/1','transmitter-progress/3'].includes(x.schema) ||
        !keys(x.target,['scope','device_id','boot_id']) || x.target.scope !== 'member' ||
        !ascii(x.target.device_id,32,32) || !/^[0-9a-f]{32}$/.test(x.target.device_id) ||
        !ascii(x.target.boot_id,32,32) || !/^[0-9a-f]{32}$/.test(x.target.boot_id) ||
        !sequence(x.draft_revision) || !sequence(x.config_revision) || !sequence(x.profile_revision) ||
        !object(x.fields) || Object.entries(x.fields).some(([k,v])=>!allowed.includes(k)||!field(k,v,amplifier)) ||
        JSON.stringify(x.fields).length>1400 ||
        !(x.last_receipt === null || typeof x.last_receipt === 'string' && /^[0-9a-f]{64}$/.test(x.last_receipt)) ||
        !(x.last_outcomes === null || outcomes(x.last_outcomes,amplifier)) ||
        !(x.applied_station === null || station(x.applied_station,false)) || !station(x.station) ||
        !['complete','station_complete','matches_applied'].every(k => typeof x[k] === 'boolean') ||
        !keys(x.apply_domains,amplifier ? ['station','network','radio','drive','all'] : ['station','network','radio','all']) || Object.values(x.apply_domains).some(v=>typeof v!=='boolean') ||
        x.apply_domains.all!==x.complete ||
        !['schedule_enabled','schedule_suspended'].every(k => x[k] === null || typeof x[k] === 'boolean') ||
        acknowledgement && (!outcomes(x.outcomes,amplifier) || !ascii(x.request_id,32,32) || !/^[0-9a-f]{32}$/.test(x.request_id))) return false;
    const stationComplete=Object.values(x.station).every(v=>v!==null);
    if (x.station_complete!==stationComplete || x.station_complete !== (x.wspr_plan!==null) ||
        x.wspr_plan!==null && !validPlan(x.wspr_plan) ||
        x.complete && (!stationComplete || Object.values(x.fields).includes(null)) ||
        x.apply_domains.station && !stationComplete || x.matches_applied && (!x.complete || x.applied_station===null)) return false;
    for (const k of ['callsign','locator','power_dbm']) {
      if (Object.hasOwn(x.fields,k) && x.station[k]!==x.fields[k]) return false;
      if (!Object.hasOwn(x.fields,k) && x.station[k] !== (x.applied_station?.[k] ?? null)) return false;
    }
    return true;
  }
  const canonical=x=>Array.isArray(x)?x.map(canonical):object(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,canonical(x[k])])):x;
  function confirms(x,request) {
    if (!valid(x,true) || x.request_id!==request.request_id ||
        JSON.stringify(canonical(x.target))!==JSON.stringify(canonical(request.target)) ||
        Object.keys(x.outcomes).sort().join(',')!==Object.keys(request.fields).sort().join(',')) return false;
    for (const [k,result] of Object.entries(x.outcomes)) {
      if (result==='invalid') continue;
      const expected=k==='wifi' && request.fields[k]!==null ? {...request.fields[k],password:null} : request.fields[k];
      if (JSON.stringify(canonical(x.fields[k]))!==JSON.stringify(canonical(expected)) ||
          (result==='cleared')!==(expected===null)) return false;
    }
    return !Object.values(x.outcomes).some(v=>v!=='invalid') ||
      JSON.stringify(canonical(x.outcomes))===JSON.stringify(canonical(x.last_outcomes));
  }
  function summary(x) {
    const missing = ['callsign','locator','power_dbm'].filter(k => x.station[k] === null).map(k => labels[k].toLowerCase());
    let text = 'Saved station draft: callsign ' + (x.station.callsign ?? 'missing') +
      '; grid locator ' + (x.station.locator ?? 'missing') + '; reported power ' +
      (x.station.power_dbm === null ? 'missing' : x.station.power_dbm + ' dBm') + '. ';
    text += missing.length ? 'WSPR station draft is incomplete. ' :
      x.wspr_plan?.supported ? 'WSPR Type ' + x.wspr_plan.frame_types.map(t=>t.slice(4)).join(' + Type ') + ': ' + (x.wspr_plan.frame_types.length === 1 ? 'one frame. ' : 'two frames in adjacent even-minute windows. ') : 'WSPR draft cannot be encoded: ' + (x.wspr_plan?.rationale || 'read current station planning') + '. ';
    text += 'Saving progress does not apply settings or establish transmit readiness. ';
    if (x.schedule_enabled === true) text += x.schedule_suspended === true
      ? 'The enabled schedule remains suspended and retains the previously applied settings.'
      : 'The enabled schedule still uses the previously applied settings.';
    return text;
  }
  function outcomeText(values) {
    return Object.entries(values).map(([k,v]) => v === 'invalid' ? labels[k] + ' was not saved: ' + errors[k] + '.' :
      labels[k] + (v === 'cleared' ? ' cleared in the saved draft.' : ' saved as draft.')).join(' ');
  }
  function fieldOutcomeText(unit,value,newer = false) {
    if (newer) return (value === 'invalid' ? 'Earlier value was not saved: ' + errors[unit] + '.' :
      value === 'cleared' ? 'Earlier value was cleared in the saved draft.' : 'Earlier value was saved as draft.') +
      ' This newer edit remains unsaved.';
    return value === 'invalid' ? 'Not saved: ' + errors[unit] + '.' :
      value === 'cleared' ? 'Cleared in saved draft.' : 'Saved as draft.';
  }
  globalThis.WsprryPicoSavedProgress = Object.freeze({names,labels,errors,valid,confirms,validPlan,summary,outcomeText,fieldOutcomeText});
})();
