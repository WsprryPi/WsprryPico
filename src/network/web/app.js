'use strict';
// Pure ownership calculation used by the settings selects and offline checks.
function pinOwners(plan, except) {
  const owners = new Map();
  const claim = (gp, role) => { if (gp !== null && gp !== undefined && role !== except) owners.set(gp, role); };
  claim(plan.rf_gp, 'RF output'); claim(plan.button_gp, 'Switch');
  claim(plan.amplifier_gp, 'Amplifier');
  (plan.lpf_gps || []).forEach((gp,i) => claim(gp, 'LPF ' + (i+1)));
  if (plan.indicator === 'external') claim(plan.indicator_gp, 'Indicator');
  return owners;
}
if (typeof module !== 'undefined') module.exports = {pinOwners};

const $ = id => document.getElementById(id);
const passwordFields = ['local-password','config-password','consumer-password','retirement-password'];
function setPasswordVisible(id, visible) {
  const input = $(id), toggle = $(id + '-toggle');
  const blocked = input.readOnly || input.disabled || input.matches?.(':disabled');
  visible = Boolean(visible && !blocked);
  // Keep the same input node and its selection; only presentation changes.
  const type = visible ? 'text' : 'password';
  if (input.type !== type) {
    const start = input.selectionStart, end = input.selectionEnd, direction = input.selectionDirection;
    input.type = type;
    if (start !== null && start !== undefined) input.setSelectionRange(start,end,direction);
  }
  const name = id === 'local-password' ? $('local-password-label').textContent.replace(/^[A-Z]/,c => c.toLowerCase()) : 'Wi-Fi password';
  const label = (visible ? 'Hide ' : 'Show ') + name;
  toggle.setAttribute('aria-label',label);
  toggle.setAttribute('aria-pressed',String(visible));
  toggle.title = label;
  toggle.disabled = Boolean(blocked);
  $(id + '-slash').toggleAttribute('hidden',!visible);
}
function clearPassword(id) {
  $(id).value = '';
  setPasswordVisible(id,false);
}
function clearPasswords() { for (const id of passwordFields) clearPassword(id); }
for (const id of passwordFields) {
  $(id + '-toggle').onclick = () => setPasswordVisible(id,$(id).type === 'password');
  setPasswordVisible(id,false);
}
for (const [form,id] of [['local-login','local-password'],['config','config-password'],['consumer-network-form','consumer-password']])
  $(form).onreset = () => setPasswordVisible(id,false);
globalThis.addEventListener?.('pagehide',clearPasswords);
const requestId = () => typeof crypto.randomUUID === 'function' ? crypto.randomUUID().replaceAll('-','') :
  [...crypto.getRandomValues(new Uint8Array(16))].map(b => b.toString(16).padStart(2,'0')).join('');
const radio = globalThis.WsprryPicoConsumerRadio?.createClient();
let session = requestId();
let activePlan = null, capabilitiesBoot = null, pinChoices = null;
let revision = '', currentConfig = null, snapshot = null, capabilities = null, busy = false, online = false, dirty = false, expectedPause = false, observedAt = '';
let localIdentity = null, localAuthenticated = false;
let writeState = 'readback', savedReadback = null, saveAttempt = null, retirementDiscovery = null;
function validWsprPlan(p) {
  if (!p || Object.keys(p).sort().join(',') !== 'alternate_callsign,frame_types,frames,rationale,schema,slot_separation_s,supported,type2_ambiguous' ||
      p.schema !== 'wspr-plan/1' || typeof p.supported !== 'boolean' || typeof p.type2_ambiguous !== 'boolean' ||
      !Array.isArray(p.frame_types) || !Number.isInteger(p.frames) || p.frames !== p.frame_types.length ||
      p.slot_separation_s !== 120 || typeof p.rationale !== 'string' || p.rationale.length < 1 || p.rationale.length > 512) return false;
  if (p.supported ? !['type1','type2','type3','type2,type3'].includes(p.frame_types.join(',')) : p.frames !== 0) return false;
  return p.type2_ambiguous ? p.supported && p.frame_types[0] === 'type2' && typeof p.alternate_callsign === 'string' &&
    p.alternate_callsign.length <= 12 && /^[A-Z0-9]+\/[A-Z0-9]+$/.test(p.alternate_callsign) : p.alternate_callsign === null;
}
let applicationVersion = 1;
async function readApplication() {
  try {
    const result = await api('application/2');
    if (Object.keys(result.data).sort().join(',') !== 'capabilities,hardware,reboot_required,recurrence,schema,station,target,wspr_plan' ||
        result.data.schema !== 'transmitter-application/2' ||
        (result.data.wspr_plan !== null && !validWsprPlan(result.data.wspr_plan)) ||
        result.data.capabilities?.station_encoding !== 'wspr_type123_auto')
      throw new Error('Unknown WSPR application support. Your draft is preserved.');
    applicationVersion = 2;
    return result;
  } catch (error) {
    if (error.code !== 'not_found') throw error;
    applicationVersion = 1;
    return api('application');
  }
}
async function reviewWspr(station, output) {
  if (applicationVersion !== 2) {
    if (/[<>/]/.test(station.callsign))
      throw new Error('This firmware has not confirmed Type 2/3 support. Your station draft is preserved.');
    return;
  }
  const result = await api('wspr-plan','POST',station);
  const plan = result.data;
  if (!validWsprPlan(plan))
    throw new Error('The Pico did not confirm the WSPR plan. Your draft is preserved.');
  if ($(output)) $(output).textContent = 'Draft plan: ' + plan.frame_types.join(' → ') + '. ' + plan.rationale;
  if (!plan.supported) throw new Error(plan.rationale);
}
function validSavedConfig(c) {
  if (c === null) return true;
  const object = v => v && typeof v === 'object' && !Array.isArray(v);
  const ascii = (v,min,max) => typeof v === 'string' && v.length >= min && v.length <= max && /^[\x20-\x7e]*$/.test(v);
  const gp = v => v === null || Number.isInteger(v) && (v >= 0 && v <= 22 || v >= 26 && v <= 28);
  if (!object(c) || c.version !== 1 || typeof c.enabled !== 'boolean' ||
      !object(c.station) || !ascii(c.station.callsign,3,12) || !/^(?:[A-Z0-9]+(?:\/[A-Z0-9]+)*|<[A-Z0-9]+(?:\/[A-Z0-9]+)*>)$/.test(c.station.callsign) || !/^[A-Ra-r]{2}[0-9]{2}([A-Xa-x]{2})?$/.test(c.station.locator) ||
      ![0,3,7,10,13,17,20,23,27,30,33,37,40,43,47,50,53,57,60].includes(c.station.power_dbm) ||
      !object(c.wifi) || !ascii(c.wifi.ssid,0,32) || c.wifi.password !== null || !ascii(c.wifi.ntp_ipv4,1,253) ||
      !Array.isArray(c.schedules) || c.schedules.length > 8 || !c.schedules.every(s=>object(s) &&
        Number.isInteger(s.period_s) && s.period_s >= 120 && s.period_s <= 86400 && s.period_s % 120 === 0 && 86400 % s.period_s === 0 &&
        Number.isInteger(s.phase_s) && s.phase_s >= 0 && s.phase_s < s.period_s && s.phase_s % 120 === 0) ||
      c.expires_utc_s !== undefined && (!Number.isSafeInteger(c.expires_utc_s) || c.expires_utc_s !== 0 && (c.expires_utc_s < 1735689600 || c.expires_utc_s >= 4102444800))) return false;
  for (const name of ['allow_unqualified_frequency','allow_non_amateur_frequency']) if (c[name] !== undefined && typeof c[name] !== 'boolean') return false;
  if (c.pins !== undefined) {
    const p=c.pins;
    if (!object(p) || !['direct','i2c'].includes(p.engine) || !gp(p.rf_gp) || !gp(p.button_gp) || !gp(p.amplifier_gp) || !gp(p.indicator_gp) ||
        !(p.i2c_pair === null || Number.isInteger(p.i2c_pair) && p.i2c_pair >= 0 && p.i2c_pair < 12) ||
        !Array.isArray(p.lpf_gps) || p.lpf_gps.length > 26 || !p.lpf_gps.every(n=>n !== null && gp(n)) ||
        !['onboard_led','external','disabled'].includes(p.indicator) || typeof p.indicator_active_high !== 'boolean') return false;
  }
  return true;
}
function checkedConfig(result, allowNull = true) {
  if (!Object.hasOwn(result.data,'config') || !validSavedConfig(result.data.config) || !allowNull && result.data.config === null || !result.revision) {
    requireReadback(); const e = new Error('Saved settings response is malformed; your draft is preserved'); e.unconfirmed=true; throw e;
  }
  return result.data.config;
}
function requireReadback() {
  writeState = 'readback'; revision = ''; savedReadback = null;
  $('saved-readback-details').hidden = true;
  $('saved-active-status').textContent = 'Saved and active observations need fresh readback.';
  $('save-reconcile-status').textContent = 'Saved-state readback required. Your draft is preserved. A status refresh or login cannot confirm an interrupted save.';
}
async function readSavedKeepingDraft() {
  requireReadback();
  const before = await readApplication();
  const saved = await api('config');
  const config = checkedConfig(saved), after = await readApplication();
  if (!before.data.target || JSON.stringify(before.data.target) !== JSON.stringify(after.data.target) ||
      before.revision !== saved.revision || after.revision !== saved.revision) throw new Error('Pico context or saved revision changed during readback');
  savedReadback = {target:after.data.target,revision:saved.revision,config};
  if ($('saved-wspr-plan')) $('saved-wspr-plan').textContent = after.data.wspr_plan
    ? 'Saved plan: ' + after.data.wspr_plan.frame_types.join(' → ') + '. ' + after.data.wspr_plan.rationale
    : 'Saved plan: this firmware supports Type 1 only.';
  $('saved-readback').textContent = JSON.stringify({saved_config:config,application:after.data},null,2);
  $('saved-readback').hidden = false; writeState = 'review';
  $('saved-readback-details').hidden = false;
  const h = after.data.hardware;
  const pins = p => p === null || !p ? 'Unknown / unavailable' : `RF GP${p.rf_gp}; switch ${p.button_gp === null ? 'disabled' : 'GP' + p.button_gp}; indicator ${p.indicator}`;
  $('saved-active-status').textContent = `Saved pins: ${pins(h?.saved)}. Active pins: ${pins(h?.active)}. ` +
    (h?.pending_restart === true ? 'Saved pins require restart. ' : h?.pending_restart === false ? 'No pin restart is pending. ' : 'Restart requirement is unconfirmed. ') +
    (h?.storage_healthy === false ? 'Storage fault. ' : '') + (h?.application_error ? `Application fault: ${h.application_error}. ` : '') +
    (after.data.station?.storage_healthy === false ? 'Station storage fault.' : '');
  $('save-reconcile-status').textContent = 'Current saved settings are shown below. Your draft is unchanged. Review differences before enabling a new explicit save. Matching values do not prove which earlier request saved them.';
}
function readSetupReceipt(hash) {
  if (typeof hash !== 'string' || !hash.startsWith('#save=') || hash.length > 512) return null;
  try {
    const v = JSON.parse(decodeURIComponent(hash.slice(6)));
    if (!v || typeof v !== 'object' || Object.keys(v).sort().join(',') !== 'device,digest,generation,kind' ||
        !['network','station'].includes(v.kind) || typeof v.device !== 'string' || !/^[0-9a-f]{32}$/.test(v.device) ||
        typeof v.digest !== 'string' || !/^[0-9a-f]{64}$/.test(v.digest) || typeof v.generation !== 'string' ||
        !/^[1-9][0-9]{0,19}$/.test(v.generation) || BigInt(v.generation) > 0xffffffffffffffffn) return null;
    return {...v,sent:true};
  } catch (_) { return null; }
}
let consumerAttempt = radio ? readSetupReceipt(globalThis.location?.hash) : null, consumerSetupDirty = false;
function setupReceiptHash() {
  if (!consumerAttempt) return '';
  const {kind,device,generation,digest} = consumerAttempt;
  return '#save=' + encodeURIComponent(JSON.stringify({kind,device,generation,digest}));
}
function updateSetupReceipt() {
  const hash = setupReceiptHash();
  try { history.replaceState(null,'',location.pathname + location.search + hash); } catch (_) {}
  const hostname = snapshot?.network.configured_hostname;
  const usable = typeof hostname === 'string' && /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.local$/.test(hostname);
  $('consumer-resume').hidden = !hash || !usable;
  if (hash && usable) $('consumer-resume').href = 'http://' + hostname + '/' + hash;
}
const notice = (text, error = false) => { $('notice').textContent = text; $('notice').classList.toggle('error', error); };
async function api(path, method = 'GET', body, etag, timeout = 30000) {
  const headers = {};
  if (localIdentity) headers['X-WsprryPico-Session'] = session;
  if (method !== 'GET') Object.assign(headers, {'Content-Type':'application/json','X-WsprryPico-Request':'1'});
  if (etag) headers['If-Match'] = etag;
  let response;
  const settingWrite = method !== 'GET' && ['config','config/2','config/update','config/update/2','schedules','station','station/2','hardware'].includes(path);
  if (settingWrite) {
    if (writeState !== 'ready' || !revision) throw new Error('Read and review saved settings before a new save');
    // Bounded context; credentials are never retained in the attempt record.
    const intended = JSON.parse(JSON.stringify(body));
    if (intended.wifi) intended.wifi.password = null;
    saveAttempt = {target:localIdentity ? {...localIdentity} : snapshot?.job.boot_id,path,revision:etag,intended,sent:true};
  }
  try {
    response = radio ? await radio.request(path,method,body,etag,timeout) :
      await fetch('/api/v1/' + path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(timeout), cache:'no-store'});
  } catch (error) {
    if (error.local) { if (saveAttempt) saveAttempt.sent=false; throw error; }
    error.unconfirmed = true;
    if (settingWrite) requireReadback();
    snapshot = null; $('state').textContent = 'Unknown · request unconfirmed';
    $('output').textContent = 'Unknown'; $('job-progress').textContent = 'Progress unavailable · request unconfirmed'; controls(false);
    if (radio && !radio.authenticated) { localAuthenticated = false; $('local-login').hidden = false; $('local-logout').hidden = true; }
    throw error;
  }
  let data;
  try {
    data = await response.json();
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('Invalid API response');
  } catch (error) {
    if (settingWrite) requireReadback();
    error.unconfirmed = true; throw error;
  }
  if (!response.ok || data.ok === false) {
    const code = typeof data.error === 'string' ? data.error : data.error?.code;
    const explanation = {
      revision_conflict:'Saved settings changed. Your edits are preserved. Read current saved settings and review them before a new save',
      precondition_failed:'Saved revision changed. Your edits are preserved. Read and review current saved settings',
      pin_conflict:`GP${data.gp} is already assigned to ${data.owner}; choose a different pin for ${data.role}`,
      invalid_gp:'Choose an exposed Pico GPIO from the listed options',
      unsupported_pin_adapter:'The selected amplifier, LPF or I²C RF adapter is not implemented',
      message_length_limit_32:'Use at most 32 characters, including spaces',
      unsupported_message_character:'The message contains a character outside the supported Morse alphabet',
      message_has_no_marks:'Include at least one Morse character',
      message_duration_overflow:'The timing or repetition is too large to calculate a finite job',
      invalid_message_timing_or_repetition:'Use positive dot, dash and gap lengths and a finite repeat count',
      resource_exhausted:'The Pico has insufficient free memory for this request. Check status before retrying',
      consumer_setup_identity_required:'Change the saved station identity or Wi-Fi network through the setup pages',
      invalid_station:'Check the callsign, locator (A–R fields, two digits, optional A–X subsquare) and exact supported reported WSPR power',
      unsupported_station_encoding:'The Pico cannot encode this complete station. Check affix lengths, brackets and six-character locator requirements. Your draft is preserved'
    };
    let message = explanation[code] || code || 'Request rejected';
    if (code === 'message_duration_limit_exceeded') message = 'Calculated duration: ' + durationText(BigInt(data.calculated_duration_ns)) + '. Maximum: ' + durationText(BigInt(data.max_job_duration_ns));
    if (code === 'message_event_limit_exceeded') message = data.calculated_events + ' events exceed the device limit of ' + data.max_events + '. Reduce repetition or use a simpler message';
    const error = new Error(message); error.code = code; error.serverResponse=true; throw error;
  }
  return {data, revision:response.headers.get('ETag')};
}
async function local(path, method = 'GET', body, timeout = 30000) {
  const headers = {'X-WsprryPico-Session':session};
  if (method !== 'GET') Object.assign(headers, {'Content-Type':'application/json','X-WsprryPico-Request':'1'});
  const response = await fetch('/local/v1/' + path, {method, headers, body:body === undefined ? undefined : JSON.stringify(body), signal:AbortSignal.timeout(timeout), cache:'no-store'});
  const data = await response.json();
  if (!response.ok) { const error = new Error(data.error?.code || 'Local request rejected'); error.code = data.error?.code; throw error; }
  return data;
}
async function supplyPhoneTime() {
  const nonce = requestId();
  const common = {version:1,device_id:localIdentity.device_id,session_id:session,nonce};
  await local('time/challenge','POST',common);
  await local('time/submit','POST',{...common,utc_ns:(BigInt(Date.now())*1000000n).toString()});
}
async function discoverLocal() {
  if (radio) {
    $('local-access').hidden = false;
    $('local-heading').textContent = 'Radio access';
    $('local-password-label').textContent = 'Saved Wi-Fi password';
    $('local-description').textContent = 'Enter the password for the Wi-Fi network saved on this Pico. Your radio session stays in this tab and expires after inactivity.';
    try {
      localIdentity = await radio.identity();
      $('local-status').textContent = `Pico ${localIdentity.device_id}`;
      notice('Log in to read or change radio settings.');
    } catch (error) { notice(error.message + '. Check the Pico address and your Wi-Fi connection, then reload.',true); }
    return true;
  }
  try {
    const response = await fetch('/local/v1/identity', {cache:'no-store', signal:AbortSignal.timeout(5000)});
    if (!response.ok) return false;
    localIdentity = await response.json();
    $('local-access').hidden = false;
    $('local-status').textContent = `Device ${localIdentity.device_id} · ${localIdentity.surface}`;
    try {
      const state = await local('status');
      if (state.wtp_session) session = state.wtp_session;
    } catch (_) { notice('Enter the local-access password to authorize this SoftAP browser.'); return true; }
    localAuthenticated = true; $('local-login').hidden = true;
    if (localIdentity.surface === 'provisioned_preclock') {
      try { await supplyPhoneTime(); }
      catch (e) { notice('Local session authorized, but phone time was rejected: ' + e.message + '.', true); }
    }
    return true;
  } catch (_) { return false; }
}
function controls(connected) {
  online = connected;
  $('refresh').disabled = busy;
  $('reload-config').disabled = busy || !online;
  const idle = online && snapshot && snapshot.job.owner_id === null && snapshot.job.output_active === false && !['armed','running','failed'].includes(snapshot.job.state);
  $('settings').disabled = busy || !idle;
  $('save-config').disabled = busy || !idle || writeState !== 'ready';
  $('read-saved').disabled = busy || !online || Boolean(localIdentity && !localAuthenticated);
  $('review-saved').disabled = busy || !online || writeState !== 'review';
  $('login-recovery').hidden = !radio;
  $('inspect-logins').disabled = busy;
  $('retire-login').disabled = busy || !retirementDiscovery || !$('retirement-target').value;
  $('consumer-setup').hidden = !radio;
  $('consumer-network-settings').disabled = busy || !idle || !localAuthenticated || Boolean(consumerAttempt);
  $('consumer-station-settings').disabled = $('consumer-network-settings').disabled;
  $('consumer-check-save').disabled = busy || !localAuthenticated || !consumerAttempt;
  $('restart').disabled = busy || !idle || !capabilities?.features?.restart;
  $('wifi-off').disabled = busy || !idle || !snapshot.network.enabled;
  $('job-settings').disabled = busy || !idle || snapshot.standalone.reboot_required;
  $('message-settings').disabled = $('job-settings').disabled || !capabilities?.message_jobs;
  $('abort').disabled = busy || !online || snapshot?.job.owner_id !== session || !['loaded','armed','running'].includes(snapshot.job.state);
  $('release').disabled = busy || !online || snapshot?.job.owner_id !== session || snapshot.job.output_active !== false || ['armed','running','failed'].includes(snapshot.job.state);
  for (const id of passwordFields) setPasswordVisible(id,$(id).type === 'text');
}
function fill(c) {
  currentConfig = c; dirty = false;
  const form = $('config').elements;
  for (const name of ['callsign','locator','power_dbm']) form[name].value = c?.station[name] ?? '';
  form.ssid.value = c?.wifi.ssid ?? '';
  form.ntp_ipv4.value = c?.wifi.ntp_ipv4 ?? 'pool.ntp.org';
  if (radio) {
    $('consumer-identity-help').hidden = false;
    for (const name of ['callsign','locator','power_dbm','ssid','password','ntp_ipv4']) form[name].readOnly = true;
    if (!consumerSetupDirty) {
      $('consumer-ssid').value = c?.wifi.ssid ?? '';
      $('consumer-time-server').value = c?.wifi.ntp_ipv4 ?? 'pool.ntp.org';
      $('consumer-callsign').value = c?.station.callsign ?? '';
      $('consumer-locator').value = c?.station.locator ?? '';
      $('consumer-power').value = c?.station.power_dbm ?? 37;
    }
  }
  clearPassword('config-password');
  form.enabled.checked = c?.enabled ?? false;
  form.schedules.value = (c?.schedules || [{period_s:120,phase_s:0}]).map(s => `${s.period_s} / ${s.phase_s}`).join('\n');
  fillPins(c?.pins);
  form.expiry.value = c?.expires_utc_s ? new Date(c.expires_utc_s * 1000).toISOString().slice(0,19) : '';
}
async function refresh(loadConfig = false) {
  // Keep this browser sequential so the other admitted client can progress.
  try {
    if (!capabilities) capabilities = (await api('capabilities')).data;
    if (!pinChoices) { try { pinChoices = (await api('pins')).data.choices; } catch (_) {} }
    snapshot = (await api('status')).data; expectedPause = false; observedAt = new Date().toLocaleTimeString();
    if (capabilitiesBoot && capabilitiesBoot !== snapshot.job.boot_id) capabilities = (await api('capabilities')).data;
    capabilitiesBoot = snapshot.job.boot_id;
    const s = snapshot.standalone, n = snapshot.network;
    $('state').textContent = snapshot.job.state;
    $('job-result').textContent = snapshot.job.job_id ? `Job ${snapshot.job.job_id}: ${snapshot.job.state} · observed ${observedAt}` : 'No loaded job · observed ' + observedAt;
    if (s.last_job === snapshot.job.job_id && Number.isInteger(s.wspr_frame) && s.wspr_frame > 0 && s.wspr_frame <= s.wspr_frames && [1,2].includes(s.wspr_frames)) $('job-result').textContent += ` · standalone WSPR frame ${s.wspr_frame} of ${s.wspr_frames}${s.wspr_pair_pending ? ' · pair in progress' : ''}`;
    $('output').textContent = snapshot.job.output_active === true ? 'Active' : snapshot.job.output_active === false ? 'Inactive' : 'Unknown';
    $('clock').textContent = `${s.clock_state} · ±${(Number(s.uncertainty_ns)/1e6).toFixed(2)} ms`;
    $('owner').textContent = snapshot.job.owner_id === session ? 'This browser' : snapshot.job.owner_id || 'Available';
    $('engine').textContent = s.engine;
    $('network').textContent = `${n.link_status === 3 ? 'Connected' : 'Disconnected'} · ${n.ipv4 || 'No address'}`;
    $('hostname').textContent = n.configured_hostname || 'IP-only deployment';
    const discovery = {unconfigured:'Not configured',waiting_address:'Waiting for Wi-Fi address',probing:'Checking hostname',active:'Advertised',conflict:'Hostname conflict',failed:'Unavailable'};
    $('discovery').textContent = discovery[n.mdns_state] || 'Unavailable';
    $('discovery-help').textContent = n.mdns_state === 'conflict' ? 'Another device is using this hostname. Resolve the duplicate, then retry with USB Console WIFI OFF and WIFI ON while idle. The device will not rename itself.' : n.mdns_reason === 'device_identity_mismatch' ? 'Credentials belong to a different device. Rebuild with this device’s certificate bundle and recover through USB Console.' : n.mdns_state === 'failed' ? 'Name discovery failed. Use the current IP address and check USB Console INFO.' : n.mdns_state === 'active' ? (radio ? 'Use this hostname or the current IP address on your local network.' : 'Use this hostname after DHCP address changes. An IP URL needs a matching certificate IP address.') : '';
    if (radio) {
      $('consumer-return').textContent = `On your normal Wi-Fi, open http://${n.configured_hostname || n.ipv4}/ or http://${n.ipv4}/. The Pico’s setup Wi-Fi is normally off while this connection is healthy.`;
      updateSetupReceipt();
    }
    $('recovery').textContent = !capabilities.active_job_connections ? 'Network connections pause while RF jobs are armed or running. The job owner can abort over an established WTP connection; physical USB Console ABORT can also stop a job. ' : '';
    $('recovery').textContent += !s.storage_healthy ? 'Storage fault. Recover through USB Console.' : s.reboot_required ? 'Network or pin settings saved. Use Restart device to apply them.' : s.suspended ? 'Standalone operation is suspended.' : '';
    if (loadConfig) { const c = await api('config'); const config=checkedConfig(c); revision = c.revision; fill(config); writeState = 'ready'; }
    updateProgress(); messagePreview();
    notice('Connected · Status updated ' + observedAt); controls(true);
  } catch (e) { snapshot = null; $('job-progress').textContent = 'Progress unavailable · status unknown'; $('state').textContent = 'Unknown · read failed'; $('output').textContent = 'Unknown'; for (const id of ['clock','owner','network','hostname','discovery']) $(id).textContent = 'Unknown'; $('discovery-help').textContent = ''; if (expectedPause) notice('RF job accepted. New network connections pause while armed or running. Use USB Console ABORT to stop it, or refresh after completion.'); else if (radio && !radio.authenticated) notice('Radio session ended. Log in again, then check status before repeating an interrupted action. Your edits are preserved.',true); else notice('Connection unavailable: ' + e.message + '. The connection limit may be reached. Check Wi-Fi and the client certificate, then refresh.', true); controls(false); }
}
async function action(fn) {
  if (busy) return;
  busy = true; controls(online);
  try { await fn(); } catch (e) {
    if ((e.serverResponse || e.unconfirmed) && (!radio || radio.authenticated)) await refresh();
    if (['revision_conflict','precondition_failed'].includes(e.code)) requireReadback();
    if (radio && !radio.authenticated) { localAuthenticated = false; $('local-login').hidden = false; $('local-logout').hidden = true; requireReadback(); }
    notice(e.message + (e.code ? ' (' + e.code + ')' : '') + (e.unconfirmed ? '. Outcome unconfirmed; no action was repeated.' : ''),true);
    $('local-status').textContent = localAuthenticated ? 'Authenticated. Request rejected; your edits are preserved.' : 'Connection or session unconfirmed. Inspect occupied logins if login cannot proceed; no action was repeated.';
  }
  finally { busy = false; controls(online); }
}
$('refresh').onclick = () => action(() => refresh());
$('local-login').onsubmit = event => { event.preventDefault(); return action(async () => {
  const password = $('local-password').value;
  setPasswordVisible('local-password',false);
  try {
    if (radio) {
      localIdentity = await radio.identity();
      await radio.login(password,localIdentity);
    } else await local('login','POST',{version:1,device_id:localIdentity.device_id,password});
  } finally { clearPassword('local-password'); }
  localAuthenticated = true; $('local-login').hidden = true;
  $('local-status').textContent = radio ? `Authenticated for Pico ${localIdentity.device_id}.` : 'Local session authenticated.';
  if (radio) $('local-logout').hidden = false;
  if (localIdentity.surface === 'provisioned_preclock') {
    try { await supplyPhoneTime(); }
    catch (e) { notice('Local session authorized, but phone time was rejected: ' + e.message + '.', true); return; }
  }
  if (dirty || writeState !== 'ready' && saveAttempt) { await refresh(); await readSavedKeepingDraft(); }
  else await refresh(true);
  notice(radio ? 'Radio session authorized. Check saved-state review before another save.' : 'Local SoftAP session authorized.');
}); };
$('inspect-logins').onclick = () => action(async () => {
  retirementDiscovery = null;
  const discovery = await radio.recovery();
  const identity = await radio.identity();
  if (discovery.device_id !== identity.device_id || discovery.boot_id !== identity.boot_id || discovery.generation !== identity.generation) throw new Error('Pico changed during login inspection');
  retirementDiscovery = discovery;
  const lost = radio.lostSession;
  $('retirement-target').replaceChildren(new Option('Choose a login explicitly',''),...discovery.sessions.map(s =>
    new Option(`${s.selector} · ${s.state}${lost?.selector === s.selector && lost.boot_id === discovery.boot_id ? ' · retained selector from this tab' : ''}`,s.selector)));
  $('retirement-status').textContent = `Pico ${discovery.device_id}; ${discovery.interface} at ${discovery.authority}. A login may belong to another operator. Retirement ends only that login and cancels its undelivered effects. Saved settings and radio jobs remain. Enter the current saved Wi-Fi password below, select a login, then retire it.`;
});
$('retirement-target').onchange = () => controls(online);
$('retire-login').onclick = () => action(async () => {
  const target = $('retirement-target').value;
  if (!retirementDiscovery || !target) throw new Error('Inspect and select an occupied login first');
  if (!confirm(`Retire login ${target} on Pico ${retirementDiscovery.device_id}? It may belong to another operator. Its unsent reply effects will be cancelled; saved settings and radio jobs remain.`)) return;
  try {
    $('retirement-status').textContent = 'Authenticating retirement…';
    const result = await radio.retire($('retirement-password').value,retirementDiscovery,target);
    $('retirement-status').textContent = result.present ? 'Selected login retired. Log in explicitly, then read saved settings. No save was repeated.' : 'Selected login is already absent. Log in explicitly and read saved settings. No replacement session was created.';
    if (!radio.authenticated) { localAuthenticated=false; $('local-login').hidden=false; $('local-logout').hidden=true; }
    requireReadback();
  } catch (e) { $('retirement-status').textContent = 'Retirement result unconfirmed or rejected. Keep this exact selection for a new explicit authenticated retirement; it cannot affect a later occupant. ' + e.message; throw e; }
  finally {clearPassword('retirement-password');}
});
$('read-saved').onclick = () => action(readSavedKeepingDraft);
$('review-saved').onclick = () => action(async () => {
  if (writeState !== 'review' || !savedReadback) return;
  const target = (await readApplication()).data.target;
  if (JSON.stringify(target) !== JSON.stringify(savedReadback.target)) {requireReadback();throw new Error('Pico changed; read saved settings again');}
  revision = savedReadback.revision; currentConfig = savedReadback.config; writeState='ready';
  $('save-reconcile-status').textContent = 'Fresh saved revision selected. Your draft is preserved. Save settings sends one new explicit mutation; concurrent changes can still refuse it.';
});
$('local-logout').onclick = () => action(async () => {
  clearPasswords();
  await radio.logout(); localAuthenticated = false;
  $('local-login').hidden = false; $('local-logout').hidden = true;
  snapshot = null; controls(false); notice('Logged out. Radio job state has not changed.');
});
$('consumer-power').replaceChildren(...[0,3,7,10,13,17,20,23,27,30,33,37,40,43,47,50,53,57,60]
  .map(power => new Option(String(power),String(power))));
for (const id of ['consumer-network-form','consumer-station-form']) $(id).oninput = () => { consumerSetupDirty = true; };
async function saveConsumer(kind) {
  setPasswordVisible('consumer-password',false);
  if (consumerAttempt) throw new Error('Check the previous saved result first');
  const status = $('consumer-save-status');
  status.textContent = 'Preparing your settings…';
  try {
    if (kind === 'station') {
      await readApplication();
      await reviewWspr({callsign:$('consumer-callsign').value.trim().toUpperCase(),
        locator:$('consumer-locator').value.trim().toUpperCase(),power_dbm:Number($('consumer-power').value)},'consumer-wspr-plan');
    }
    consumerAttempt = kind === 'network' ? await radio.prepareNetwork(localIdentity, {
      ssid:$('consumer-ssid').value,password:$('consumer-password').value,time_server:$('consumer-time-server').value.trim()
    }) : await radio.prepareStation(localIdentity, {
      callsign:$('consumer-callsign').value.trim().toUpperCase(),locator:$('consumer-locator').value.trim().toUpperCase(),powerDbm:Number($('consumer-power').value)
    });
    updateSetupReceipt();
    await radio.submitSetup(consumerAttempt);
    status.textContent = 'Settings accepted. The Pico may reconnect and restart. Keep this tab open or use the continuation link after joining the saved network. Log in, then select Check saved result.';
  } catch (error) {
    status.textContent = consumerAttempt ? 'The save result is unconfirmed. Keep this tab open or use the continuation link. Log in when the Pico returns and select Check saved result before sending another save.' : error.message;
    throw error;
  } finally { clearPassword('consumer-password'); }
}
$('consumer-network-form').onsubmit = event => { event.preventDefault(); return action(() => saveConsumer('network')); };
$('consumer-station-form').onsubmit = event => { event.preventDefault(); return action(() => saveConsumer('station')); };
$('consumer-check-save').onclick = () => action(async () => {
  const result = await radio.checkSetup(consumerAttempt);
  $('consumer-save-status').textContent = result === 'saved' ? 'Your settings were saved and verified.' :
    result === 'failed' ? 'These settings were not saved. You can correct them and try again.' :
    'The result is still unconfirmed. Wait for the Pico to return, log in and check again. No save has been repeated.';
  if (result !== 'unconfirmed') { consumerAttempt = null; updateSetupReceipt(); await refresh(); await readSavedKeepingDraft(); }
});
if (consumerAttempt) $('consumer-save-status').textContent = 'A pending save receipt was recovered. Log in, then select Check saved result. No save has been repeated.';
$('config').oninput = () => { dirty = true; };
$('reload-config').onclick = () => action(async () => {
  if (dirty && !confirm('Discard your unsaved changes and reload saved settings?')) return;
  await refresh(true);
});
$('config').onsubmit = event => { event.preventDefault(); setPasswordVisible('config-password',false); return action(async () => {
  const f = $('config').elements;
  const schedules = f.schedules.value.trim().split('\n').map(line => {
    if (!/^\s*\d+\s*\/\s*\d+\s*$/.test(line)) throw new Error('Use period / phase for each schedule');
    const [period_s,phase_s] = line.split('/').map(Number); return {period_s,phase_s};
  });
  const config = {version:1,enabled:f.enabled.checked,station:{callsign:f.callsign.value.trim().toUpperCase(),locator:f.locator.value.trim().toUpperCase(),power_dbm:Number(f.power_dbm.value)},wifi:{ssid:f.ssid.value,password:f.password.value || null,ntp_ipv4:f.ntp_ipv4.value.trim()},schedules,pins:pinChoices ? readPins() : currentConfig?.pins,expires_utc_s:f.expiry.value ? Date.parse(f.expiry.value + 'Z') / 1000 : 0};
  if (radio) {
    // These fields are read-only in this editor and can change through setup
    // while an unrelated editable draft survives. Use fresh saved authority.
    config.station = {...currentConfig.station};
    config.wifi = {...currentConfig.wifi,password:null};
  }
  // Advanced opt-ins are managed through CONFIG/API, outside the ordinary form.
  // A station/network edit must preserve the operator's saved choices.
  for (const name of ['allow_unqualified_frequency','allow_non_amateur_frequency']) {
    if (currentConfig?.[name] === true) config[name] = true;
  }
  await reviewWspr(config.station,'draft-wspr-plan');
  const result = await api(applicationVersion === 2 ? 'config/2' : 'config','PUT',config,revision); const confirmed=checkedConfig(result,false); revision = result.revision; fill(confirmed);
  await refresh(); notice(result.data.reboot_required ? 'Settings saved. Use Restart device to apply network or pin changes.' : 'Settings saved and applied.');
}); };
async function job(operation, body = {}) {
  const result = await api('jobs','POST',{session_id:session,request_id:requestId(),operation,body});
  return result.data;
}
$('job').onsubmit = event => { event.preventDefault(); return action(async () => {
  const file = $('job-file').files[0];
  if (!file || file.size > 30000) throw new Error('Choose a job JSON file of at most 30,000 bytes');
  const plan = JSON.parse(await file.text());
  checkPlanLimits(plan);
  const startMs = Date.parse($('start').value + 'Z');
  if (!Number.isFinite(startMs)) throw new Error('Choose a UTC start time');
  await job('HELLO',{versions:['WTP/1'],client_name:'WsprryPico browser',client_version:'1'});
  await job('CLAIM',{owner_id:session,lease_ms:30000});
  await job('LOAD',plan);
  await job('ARM',{job_id:plan.job_id,start_utc_ns:(BigInt(startMs)*1000000n).toString(),max_start_uncertainty_ns:capabilities.wtp.maximum_arm_uncertainty_ns});
  activePlan = {bootId:snapshot?.job.boot_id,jobId:plan.job_id,startMs,durationNs:BigInt(plan.total_duration_ns)};
  $('job-result').textContent = 'Job armed. Timing is now local to the Pico.';
  await observeAfterArm();
}); };
async function observeAfterArm() {
  if (!capabilities.active_job_connections) {
    expectedPause = true; controls(false); $('state').textContent = 'Armed · last confirmed'; $('output').textContent = 'Not observed during network pause';
    notice('Job armed. New network connections pause during RF execution. Use USB Console ABORT to stop the job, or refresh after completion.');
  } else await refresh();
}
$('abort').onclick = () => action(async () => { await job('ABORT',{job_id:snapshot.job.job_id}); await refresh(); });
$('release').onclick = () => action(async () => { await job('RELEASE'); await refresh(); });
$('restart').onclick = () => action(async () => {
  if (!confirm(dirty ? 'Restart using saved settings? Your unsaved edits will be discarded after reconnection.' : 'Restart the device? This page will reconnect when it is ready.')) return;
  const before = snapshot?.job.boot_id;
  if (!before) throw new Error('Refresh status before restarting');
  const saved = await api('config');
  // Exactly one mutation; a lost acknowledgement must never trigger another reset.
  await api('restart', 'POST', {}, saved.revision);
  snapshot = null; controls(false); $('state').textContent = 'Restart requested'; $('output').textContent = 'Unknown during restart';
  notice('Restart requested. Reconnecting…');
  const deadline = Date.now() + 90000;
  while (Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 2000));
    try {
      const observed = await api('status', 'GET', undefined, undefined, Math.max(1, Math.min(20000, deadline - Date.now())));
      if (observed.data.job.boot_id && observed.data.job.boot_id !== before) {
        capabilities = null; await refresh(true);
        if (online) { notice('Device restarted. Saved settings are active.'); return; }
      }
    } catch (_) { /* Remain unknown until an authenticated new boot is observed. */ }
  }
  throw new Error('Restart not confirmed. Refresh to check the device; another restart has not been sent');
});
$('wifi-off').onclick = () => action(async () => {
  if (!confirm('Disconnect Wi-Fi? Reconnect using USB Console or restart the device.')) return;
  const n = await api('network'); await api('network','PUT',{enabled:false},n.revision);
  snapshot = null; controls(false); notice('Wi-Fi disconnect requested. Refresh to verify; use USB Console or restart if Wi-Fi is unavailable.');
});
const morseAlphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/?.,-+=';
const morseCodes = ['.-','-...','-.-.','-..','.','..-.','--.','....','..','.---','-.-','.-..','--','-.','---','.--.','--.-','.-.','...','-','..-','...-','.--','-..-','-.--','--..','-----','.----','..---','...--','....-','.....','-....','--...','---..','----.','-..-.','..--..','.-.-.-','--..--','-....-','.-.-.','-...-'];
function nanoDecimal(text, label) {
  const value = String(text).trim();
  if (!/^\d+(\.\d{1,9})?$/.test(value)) throw new Error(label + ': use a positive number with at most nine decimal places');
  const [whole, fraction = ''] = value.split('.');
  const n = BigInt(whole)*1000000000n + BigInt(fraction.padEnd(9,'0'));
  if (n > 18446744073709551615n) throw new Error(label + ' is too large');
  return n;
}
function durationText(ns) {
  const negative = ns < 0n;
  const absolute = negative ? -ns : ns;
  const minutes = absolute / 60000000000n;
  const seconds = absolute / 1000000000n % 60n;
  const fraction = (absolute % 1000000000n).toString().padStart(9,'0').replace(/0+$/,'');
  return (negative ? '-' : '') + (minutes ? minutes + ' min ' : '') + seconds + (fraction ? '.' + fraction : '') + ' s';
}
function checkPlanLimits(plan) {
  const duration = BigInt(plan.total_duration_ns);
  const maximum = BigInt(capabilities.wtp.max_job_duration_ns);
  if (duration <= 0n || duration > maximum) throw new Error('Job duration is ' + durationText(duration) + '; this device allows ' + durationText(maximum) + '. Reduce the duration or repetition');
  if (!Array.isArray(plan.events) || !plan.events.length || plan.events.length > capabilities.wtp.max_events) throw new Error('This device allows at most ' + capabilities.wtp.max_events + ' events per job. Reduce the message complexity or repetition');
  return duration;
}
function messagePlan() {
  const text = $('message-text').value, mode = $('message-mode').value;
  if (!text || text.length > 32) throw new Error('Use 1–32 characters, including spaces. The message has ' + text.length);
  if (!['qrss','fskcw','dfcw'].includes(mode)) throw new Error('Choose QRSS, FSKCW or DFCW');
  const frequency = nanoDecimal($('message-frequency').value, 'Frequency');
  const shift = mode === 'qrss' ? 0n : nanoDecimal($('message-shift').value, 'Frequency shift');
  if (!frequency || (mode !== 'qrss' && (!shift || shift >= frequency))) throw new Error('Use a positive frequency and a smaller positive frequency shift');
  const dot = nanoDecimal($('message-dot').value, 'Dot length');
  const scaled = (id, label) => {
    const product = dot * nanoDecimal($(id).value, label);
    if (product % 1000000000n) throw new Error(label + ' must produce a whole number of nanoseconds');
    return product / 1000000000n;
  };
  const timing = {dot_ns:dot,dash_ns:scaled('message-dash','Dash length'),intra_gap_ns:scaled('message-intra','Element gap'),character_gap_ns:scaled('message-character','Character gap'),word_gap_ns:scaled('message-word','Word gap')};
  if (Object.values(timing).some(n=>n<=0n || n>18446744073709551615n)) throw new Error('Dot, dash and gap lengths must be positive and within the device timing range');
  const repeat = Number($('message-repeats').value), repeatGap = nanoDecimal($('message-gap').value,'Repeat gap');
  if (!Number.isInteger(repeat) || repeat < 1 || repeat > 512 || (repeat > 1 && !repeatGap)) throw new Error('Use 1–512 repeats and a positive gap between repeats');
  let duration = 0n, events = 0;
  for (let i = 0; i < text.length; ++i) {
    if (/[ \t\r\n\f\v]/.test(text[i])) continue;
    if (text.charCodeAt(i) > 127) throw new Error('Unsupported character: ' + text[i]);
    const code = morseCodes[morseAlphabet.indexOf(text[i].toUpperCase())];
    if (!code) throw new Error('Unsupported character: ' + text[i] + '. Use the alphabet shown above');
    for (let n = 0; n < code.length; ++n) {
      duration += mode === 'dfcw' || code[n] === '.' ? dot : timing.dash_ns; ++events;
      if (n+1 < code.length) { duration += timing.intra_gap_ns; ++events; }
    }
    let next = i+1; while (next < text.length && /[ \t\r\n\f\v]/.test(text[next])) ++next;
    if (next < text.length) { duration += next === i+1 ? timing.character_gap_ns : timing.word_gap_ns; ++events; }
  }
  if (!events) throw new Error('Include at least one Morse character');
  duration = duration*BigInt(repeat) + repeatGap*BigInt(repeat-1) + 1000n;
  events = events*repeat + repeat;
  const maximum = capabilities?.wtp?.max_job_duration_ns ? BigInt(capabilities.wtp.max_job_duration_ns) : 3600000000000n;
  if (duration > maximum || duration > 3600000000000n) throw new Error('Calculated duration: ' + durationText(duration) + '. Maximum: ' + durationText(maximum < 3600000000000n ? maximum : 3600000000000n) + '. Shorten the timing or reduce repeats');
  if (events > (capabilities?.wtp?.max_events || 512)) throw new Error(events + ' events exceed the device limit of ' + (capabilities?.wtp?.max_events || 512) + '. Reduce repetition or use a simpler message');
  return {duration,events,body:{mode,message:text,frequency_nhz:frequency.toString(),space_frequency_nhz:(mode==='qrss'?0n:frequency-shift).toString(),timing:Object.fromEntries(Object.entries(timing).map(([k,v])=>[k,v.toString()])),repeat_count:repeat,repeat_gap_ns:repeatGap.toString(),allow_frequency_adjustment:true}};
}
function messagePreview() {
  try { const p = messagePlan(); $('message-preview').textContent = durationText(p.duration) + ' · ' + p.events + ' / ' + (capabilities?.wtp?.max_events || 512) + ' events · ' + $('message-text').value.length + ' / 32 characters'; $('message-preview').classList.toggle('error',false); }
  catch (e) { $('message-preview').textContent = e.message; $('message-preview').classList.toggle('error',true); }
}
function updateProgress() {
  if (!activePlan || !snapshot || snapshot.job.boot_id !== activePlan.bootId || snapshot.job.job_id !== activePlan.jobId) { $('job-progress').textContent = ''; return; }
  if (snapshot.job.state !== 'running') { $('job-progress').textContent = 'Last confirmed: ' + snapshot.job.state; return; }
  const now = snapshot.standalone.utc_now_ns;
  if (!now) { $('job-progress').textContent = 'Running · refresh for the latest confirmed state'; return; }
  const elapsed = BigInt(now) - BigInt(activePlan.startMs)*1000000n;
  const bounded = elapsed < 0n ? 0n : elapsed > activePlan.durationNs ? activePlan.durationNs : elapsed;
  $('job-progress').textContent = 'Running · estimated ' + durationText(bounded) + ' of ' + durationText(activePlan.durationNs) + ' · ' + (Number(bounded*1000n/activePlan.durationNs)/10).toFixed(1) + '% · status checked ' + observedAt;
}
$('message-form').oninput = messagePreview;
$('message-form').onsubmit = event => { event.preventDefault(); return action(async () => {
  if (!capabilities?.message_jobs) throw new Error('This firmware does not support message submission');
  const plan = messagePlan(), startMs = Date.parse($('message-start').value + 'Z');
  if (!Number.isFinite(startMs)) throw new Error('Choose a UTC start time');
  plan.body.job_id = requestId();
  await job('HELLO',{versions:['WTP/1'],client_name:'WsprryPico browser',client_version:'1'});
  await job('CLAIM',{owner_id:session,lease_ms:30000});
  await job('LOAD_MESSAGE',plan.body);
  await job('ARM',{job_id:plan.body.job_id,start_utc_ns:(BigInt(startMs)*1000000n).toString(),max_start_uncertainty_ns:capabilities.wtp.maximum_arm_uncertainty_ns});
  activePlan = {bootId:snapshot?.job.boot_id,jobId:plan.body.job_id,startMs,durationNs:plan.duration};
  $('job-result').textContent = 'Message armed · ' + durationText(plan.duration) + '. Timing is now local to the Pico.';
  await observeAfterArm();
}); };
if (typeof setInterval === 'function') setInterval(() => {
  if (!busy && online && activePlan && ['armed','running'].includes(snapshot?.job.state)) action(() => refresh());
}, 5000);

action(async () => { await discoverLocal(); if ((!radio && !localIdentity) || localAuthenticated) await refresh(true); });

function readPins() {
  const f = $('config').elements;
  return {engine:'direct',rf_gp:Number(f.rf_gp.value),i2c_pair:null,
    button_gp:f.button_gp.value === '' ? null : Number(f.button_gp.value),
    amplifier_gp:null,lpf_gps:[],indicator:f.indicator.value,
    indicator_gp:f.indicator.value === 'external' ? Number(f.indicator_gp.value) : null,
    indicator_active_high:f.indicator_active_high.value === 'true'};
}
function pinOptions(select, role, nullable) {
  const selected = select.value;
  const owners = pinOwners(readPins(), role);
  const options = nullable ? [new Option('Disabled','')] : [];
  for (const gp of pinChoices?.eligible_gps || []) {
    const owner = owners.get(gp);
    const option = new Option('GP' + gp + (owner ? ' — used by ' + owner : ''),String(gp));
    option.disabled = Boolean(owner); options.push(option);
  }
  select.replaceChildren(...options); select.value = selected;
  if (!select.value || select.selectedOptions[0]?.disabled) {
    const available = options.find(option => !option.disabled);
    if (available) select.value = available.value;
  }
}
function lockPins() {
  if (!pinChoices) return;
  const f = $('config').elements;
  pinOptions(f.rf_gp,'RF output',false);
  pinOptions(f.button_gp,'Switch',true);
  pinOptions(f.indicator_gp,'Indicator',false);
  f.indicator_gp.disabled = f.indicator.value !== 'external';
  f.indicator_active_high.disabled = f.indicator.value !== 'external';
}
function fillPins(plan) {
  const f = $('config').elements;
  const p = plan || {rf_gp:2,button_gp:14,indicator:'onboard_led',indicator_gp:null,indicator_active_high:true};
  const gps = pinChoices?.eligible_gps || [2,14];
  for (const key of ['rf_gp','button_gp','indicator_gp']) {
    const options = key === 'button_gp' ? [new Option('Disabled','')] : [];
    f[key].replaceChildren(...options,...gps.map(gp=>new Option('GP'+gp,String(gp))));
    f[key].value = p[key] === null ? (key === 'button_gp' ? '' : '0') : String(p[key]);
  }
  f.indicator.value = p.indicator;
  f.indicator_active_high.value = String(p.indicator_active_high ?? true);
  $('pin-settings').disabled = !pinChoices;
  $('i2c-choices').textContent = pinChoices ? pinChoices.i2c_pairs.map(p=>`I²C${p.controller}: GP${p.sda_gp} SDA / GP${p.scl_gp} SCL`).join(' · ') : 'Pin selection is unavailable on this firmware.';
  lockPins();
}
for (const key of ['rf_gp','button_gp','indicator','indicator_gp']) $('config').elements[key].addEventListener('change',lockPins);

function wsprDraftFeedback(call,locator,id) {
  const output = $(id); if (!output) return;
  if (locator && !/^[A-R]{2}[0-9]{2}([A-X]{2})?$/.test(locator)) { output.textContent = 'Use a locator such as EM18 or EM18IG: fields A–R, two digits, then optional A–X subsquare. Your draft has not been saved.'; return; }
  if (call.startsWith('<') && locator.length !== 6) { output.textContent = 'A bracketed callsign needs a six-character locator. Your draft has not been saved.'; return; }
  const description = call.startsWith('<') ? 'Type 3 · one hash frame; receiver context is needed.' : call.includes('/') ?
    locator.length === 6 ? 'Type 2 then Type 3 · two frames in adjacent even-minute windows, 230.592 seconds total. Receiver hash context may be needed.' : 'Type 2 · one frame, without a locator.' :
    'Type 1 · one frame; first four locator characters on air, all six retained in settings.';
  output.textContent = 'Draft: ' + description + (/\/(?:[Q-Z]|0[0-9])$/.test(call) ? ' This Type 2 suffix has an ambiguous letter/numeric interpretation; receivers may choose either. Your requested call is retained.' : '') + ' The Pico validates encoding before saving.';
}
$('config').addEventListener('input', () => { const f=$('config').elements; wsprDraftFeedback(f.callsign.value.trim().toUpperCase(),f.locator.value.trim().toUpperCase(),'draft-wspr-plan'); });
$('consumer-station-form').addEventListener('input', () => wsprDraftFeedback($('consumer-callsign').value.trim().toUpperCase(),$('consumer-locator').value.trim().toUpperCase(),'consumer-wspr-plan'));
