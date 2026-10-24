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
const pageIdentity = WsprryPicoPresentation.create(document);
const canonicalHostname = WsprryPicoPresentation.canonicalHostname;
const passwordFields = ['local-password','config-password','consumer-password','retirement-password','pico-new-password','pico-confirm-password'];
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
  const name = id === 'local-password' ? $('local-password-label').textContent.replace(/^[A-Z]/,c => c.toLowerCase()) : id === 'retirement-password' ? 'Pico password' : id === 'pico-new-password' ? 'new Pico password' : id === 'pico-confirm-password' ? 'password confirmation' : 'Wi-Fi password';
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

const requestId = () => typeof crypto.randomUUID === 'function' ? crypto.randomUUID().replaceAll('-','') :
  [...crypto.getRandomValues(new Uint8Array(16))].map(b => b.toString(16).padStart(2,'0')).join('');
const radio = globalThis.WsprryPicoConsumerRadio?.createClient();
let session = requestId();
let activePlan = null, capabilitiesBoot = null, pinChoices = null;
let revision = '', currentConfig = null, snapshot = null, capabilities = null, busy = false, online = false, dirty = false, expectedPause = false, observedAt = '';
let picoPasswordState = null;
const supportsAmplifier = () => globalThis.WsprryAmplifier?.supported(capabilities?.amplifier_enable) === true;
let localIdentity = null, localAuthenticated = false;
let engineeringStationDirty = false, engineeringNetworkDirty = false;
let writeState = 'readback', savedReadback = null, saveAttempt = null, retirementDiscovery = null;

if ($('standalone-frequency-form')) $('standalone-frequency-form').onsubmit = event => event.preventDefault();
const frequencyEditor = globalThis.WsprryStandaloneFrequency && $('standalone-frequency') ? WsprryStandaloneFrequency.create({
  ranges:()=>capabilities?.wtp?.frequency_ranges,
  input:$('standalone-frequency'),read:$('standalone-frequency-read'),save:$('standalone-frequency-save'),discard:$('standalone-frequency-discard'),adopt:$('standalone-frequency-adopt'),status:$('standalone-frequency-status'),
  exchange:async (method,body,match)=>{if (!WsprryStandaloneFrequency.supported(capabilities?.standalone_frequency)) throw new Error('Standalone frequency configuration is unsupported.'); return api('standalone-frequency',method,body,match);},
  afterSave:()=>requireReadback()
}) : null;
if ($('rf-calibration-form')) $('rf-calibration-form').onsubmit = event => event.preventDefault();
const calibrationEditor = globalThis.WsprryRfCalibration && $('rf-manual-ppm') ? WsprryRfCalibration.create({
  input:$('rf-manual-ppm'),mode:$('rf-calibration-mode'),read:$('rf-calibration-read'),save:$('rf-calibration-save'),discard:$('rf-calibration-discard'),adopt:$('rf-calibration-adopt'),status:$('rf-calibration-status'),
  exchange:async (method,body,match)=>{if (!WsprryRfCalibration.supported(capabilities?.rf_calibration)) throw new Error('Calibration configuration is unsupported.'); return api('rf-calibration',method,body,match);},
  afterSave:()=>requireReadback()
}) : null;
if ($('gpio-drive-form')) $('gpio-drive-form').onsubmit = event => event.preventDefault();
const driveEditor = globalThis.WsprryGpioDrive && $('gpio-drive-select') ? WsprryGpioDrive.create({
  select:$('gpio-drive-select'),read:$('gpio-drive-read'),save:$('gpio-drive-save'),discard:$('gpio-drive-discard'),status:$('gpio-drive-status'),saveDraft:$('gpio-drive-save-draft'),applyDraft:$('gpio-drive-apply-draft'),draftStatus:$('gpio-drive-draft-status'),
  exchange:async (method,body,match,resource = 'gpio-drive')=>{if (!WsprryGpioDrive.supported(capabilities?.gpio_drive)) throw new Error('This firmware does not advertise supported drive configuration.'); return api(resource,method,body,match);},
  afterSave:()=>{requireReadback();}
  ,progressVersion:()=>supportsAmplifier() ? 3 : 2
}) : null;
let savedProgress = null, progressEpoch = 0, progressEditSerial = 0;
const progressEdits = new Map();
const progressUI = globalThis.WsprryPicoSavedProgress;
function supportsProgress() {
  const d = capabilities?.saved_progress;
  if (d === undefined) return false;
  if (!d || Object.keys(d).sort().join(',') !== 'apply,max_bytes,read,save,schema' ||
      d.schema !== 'transmitter-progress/1' || d.read !== '/api/v1/progress' ||
      d.save !== '/api/v1/progress/update' || d.apply !== '/api/v1/progress/apply' || d.max_bytes !== 2048 || !progressUI)
    throw new Error('Unknown saved-progress support. Your edits are preserved.');
  return true;
}
function progressUnit(control) {
  const station = {'consumer-callsign':'callsign','consumer-locator':'locator','consumer-power':'power_dbm'};
  if (station[control.id]) return station[control.id];
  const name = control.name;
  if (['rf_gp','button_gp','amplifier_gp','amplifier_active_high','indicator','indicator_gp','indicator_active_high'].includes(name)) return 'pins';
  if (['ssid','password'].includes(name)) return 'wifi';
  return name === 'expiry' ? 'expires_utc_s' : name;
}
function progressInputs(unit,station = false) {
  const f=$('config').elements;
  if (station) return [$('consumer-'+(unit==='power_dbm'?'power':unit))].filter(Boolean);
  const names=unit==='wifi' ? ['ssid','password'] : unit==='pins' ? ['rf_gp','button_gp','amplifier_gp','amplifier_active_high','indicator','indicator_gp','indicator_active_high'] : [unit==='expires_utc_s'?'expiry':unit];
  return names.map(name=>f[name]).filter(Boolean);
}
function editedProgress(event) {
  if (!event?.target) return;
  const unit = progressUnit(event.target);
  if (progressUI?.names.includes(unit)) {
    progressEdits.set(unit,++progressEditSerial);
    const message = $('progress-error-' + (event.target.id?.startsWith('consumer-') ? 'station-' : 'settings-') + unit);
    if (message) {message.textContent='Unsaved edit.';message.classList.toggle('error',false);for (const input of progressInputs(unit,event.target.id?.startsWith('consumer-'))) input.setAttribute?.('aria-invalid','false');}
  }
}
function checkedProgress(result, acknowledgement = false) {
  if (!result.revision || !progressUI?.valid(result.data,acknowledgement) ||
      result.data.target.boot_id !== snapshot?.job.boot_id ||
      localIdentity && result.data.target.device_id !== localIdentity.device_id) {
    requireReadback(); const error = new Error('Saved progress is unconfirmed. Your edits are preserved; read saved settings before another save.');
    error.unconfirmed = true; throw error;
  }
  return result;
}
function showProgress() {
  if (!savedProgress) return;
  const text = progressUI.summary(savedProgress.data);
  for (const id of ['progress-settings-status','progress-station-status','progress-engineering-station-status','progress-engineering-network-status']) if ($(id)) $(id).textContent = text;
  $('save-config').textContent = 'Save valid fields';
  if ($('save-station-progress')) $('save-station-progress').textContent = 'Save valid station fields';
  $('apply-progress').hidden = false;
  $('apply-progress').disabled = writeState !== 'ready' || savedProgress.data.draft_revision === '0' || !savedProgress.data.apply_domains.radio;
  for (const domain of ['station','network']) {
    $('apply-engineering-' + domain + '-progress').hidden = Boolean(radio);
    $('apply-engineering-' + domain + '-progress').disabled = writeState !== 'ready' || savedProgress.data.draft_revision === '0' || !savedProgress.data.apply_domains[domain];
    $('save-engineering-' + domain + '-progress').textContent = 'Save valid ' + domain + ' fields';
  }
  $('apply-station-progress').hidden = !radio;
  $('apply-station-progress').disabled = writeState !== 'ready' || savedProgress.data.draft_revision === '0' || !savedProgress.data.station_complete || !savedProgress.data.wspr_plan?.supported;
  $('settings-save-help').textContent = 'Save valid fields as progress, then explicitly apply saved settings. Incomplete drafts do not replace applied settings. Network and pin application can need a restart.';
  $('initial-config').textContent = 'Apply complete saved progress';
}
async function readProgress(fillDraft = false) {
  if (!supportsProgress()) return null;
  const epoch = ++progressEpoch;
  const result = checkedProgress(await api('progress'));
  if (epoch !== progressEpoch) throw new Error('Saved-progress read was superseded. Your edits are preserved.');
  savedProgress = result;
  if (fillDraft && !progressEdits.size && !consumerSetupDirty) {
    const f = $('config').elements, v = result.data.fields;
    for (const key of ['callsign','locator','power_dbm']) {
      f[key].value = result.data.station[key] ?? '';
      if (radio) $('consumer-' + (key === 'power_dbm' ? 'power' : key)).value = result.data.station[key] ?? '';
    }
    if (Object.hasOwn(v,'enabled')) f.enabled.checked = v.enabled === true;
    if (Object.hasOwn(v,'schedules')) f.schedules.value = Array.isArray(v.schedules) ? v.schedules.map(x=>`${x.period_s} / ${x.phase_s}`).join('\n') : '';
    if (Object.hasOwn(v,'expires_utc_s')) f.expiry.value = v.expires_utc_s ? new Date(v.expires_utc_s*1000).toISOString().slice(0,19) : '';
    if (v.pins) fillPins(v.pins);
    if (!radio && Object.hasOwn(v,'ntp_ipv4')) f.ntp_ipv4.value = v.ntp_ipv4 ?? '';
    if (!radio && v.wifi) f.ssid.value = v.wifi.ssid;
    wsprDraftFeedback(f.callsign.value,f.locator.value,'draft-wspr-plan');
    if (radio) wsprDraftFeedback(f.callsign.value,f.locator.value,'consumer-wspr-plan');
  }
  showProgress(); return result;
}
function fieldOutcome(unit,value,station,newer = false) {
  const f = $('config').elements;
  const input = station ? $('consumer-' + (unit === 'power_dbm' ? 'power' : unit)) :
    unit === 'pins' ? f.rf_gp : unit === 'wifi' ? f.ssid : unit === 'expires_utc_s' ? f.expiry : f[unit];
  if (!input) return;
  const id = 'progress-error-' + (station ? 'station-' : 'settings-') + unit;
  let message = $(id);
  if (!message) { message = document.createElement('small'); message.id = id; message.className = 'field-result'; (unit === 'enabled' ? input.closest('label') : input).insertAdjacentElement('afterend',message); }
  for (const field of progressInputs(unit,station)) {
    field.setAttribute('aria-describedby',[...new Set([...(field.getAttribute('aria-describedby') || '').split(' '),id].filter(Boolean))].join(' '));
    field.setAttribute('aria-invalid',String(!newer && value === 'invalid'));
  }
  message.textContent = progressUI.fieldOutcomeText(unit,value,newer);
  message.classList.toggle('error',value === 'invalid');
}
async function saveProgressFields(fields,station = false,output) {
  if (!Object.keys(fields).length) throw new Error('Edit a field before saving progress.');
  if (!savedProgress || writeState !== 'ready' || savedProgress.revision !== revision) throw new Error('Read and review saved settings before saving progress.');
  const edits = new Map(progressEdits), target = savedProgress.data.target;
  const body = {schema:'transmitter-progress/1',target,request_id:requestId(),fields};
  const epoch = ++progressEpoch;
  const result = checkedProgress(await api('progress/update','POST',body,revision),true);
  if (epoch !== progressEpoch || !progressUI.confirms(result.data,body)) {
    requireReadback(); const e = new Error('Save result unconfirmed. Your edits are preserved. Read saved settings before sending another save.');e.unconfirmed=true;throw e;
  }
  savedProgress = {data:{...result.data},revision:result.revision};
  delete savedProgress.data.outcomes; delete savedProgress.data.request_id;
  revision = result.revision;
  if (savedReadback) {
    savedReadback.progress = savedProgress.data;
    savedReadback.revision = revision;
    $('saved-readback').textContent = JSON.stringify({saved_config:savedReadback.config,saved_progress:savedProgress.data,application_at_last_read:savedReadback.application},null,2);
    showDraftComparison();
  }
  for (const [key,value] of Object.entries(result.data.outcomes)) {
    if (progressEdits.get(key) !== edits.get(key)) {
      fieldOutcome(key,value,station,true);
    } else {
      fieldOutcome(key,value,station);
      if (value !== 'invalid') progressEdits.delete(key);
    }
  }
  engineeringStationDirty = ['callsign','locator','power_dbm'].some(k=>progressEdits.has(k));
  engineeringNetworkDirty = ['wifi','ntp_ipv4'].some(k=>progressEdits.has(k));
  consumerSetupDirty = consumerNetworkDirty || (Boolean(radio) && engineeringStationDirty);
  dirty = progressEdits.size > 0;
  showProgress();
  const newer = Object.keys(fields).filter(k=>progressEdits.has(k) && progressEdits.get(k)!==edits.get(k));
  const text = progressUI.outcomeText(result.data.outcomes) + (newer.length ? ' Newer edits remain unsaved: ' + newer.map(k=>progressUI.labels[k]).join(', ') + '.' : '') + ' ' + progressUI.summary(result.data);
  $(output || (station ? 'progress-station-status' : 'progress-settings-status')).textContent = text;
  notice(text,Object.values(result.data.outcomes).includes('invalid'));
  return result.data.outcomes;
}
function progressNumber(text) {
  const value = Number(text);
  return text !== '' && Number.isInteger(value) && value >= 0 && value <= 2147483647 ? value : text;
}
function stationProgressEdits() {
  const fields = {};
  for (const key of ['callsign','locator','power_dbm']) if (progressEdits.has(key)) {
    const text = $('consumer-' + (key === 'power_dbm' ? 'power' : key)).value.trim();
    fields[key] = text === '' ? null : key === 'power_dbm' ? progressNumber(text) : text.toUpperCase();
  }
  return fields;
}
async function saveConfigProgress(domain = 'radio') {
  const f = $('config').elements, fields = {};
  for (const key of progressEdits.keys()) {
    if ((['callsign','locator','power_dbm'].includes(key) ? 'station' : ['wifi','ntp_ipv4'].includes(key) ? 'network' : 'radio') !== domain) continue;
    if (radio && ['callsign','locator','power_dbm','wifi','ntp_ipv4'].includes(key)) continue;
    if (key === 'pins') fields.pins = readPins();
    else if (key === 'wifi') fields.wifi = {ssid:f.ssid.value,password:f.password.value || null};
    else if (key === 'schedules') fields.schedules = f.schedules.value.trim() === '' ? [] : f.schedules.value.trim().split('\n').map(line=>{
      if (!/^\s*\d+\s*\/\s*\d+\s*$/.test(line)) return line;
      const [period_s,phase_s] = line.split('/').map(v=>progressNumber(v.trim()));return {period_s,phase_s};
    });
    else if (key === 'expires_utc_s') fields[key] = f.expiry.validity?.badInput ? 'invalid' : f.expiry.value ? progressNumber(String(Date.parse(f.expiry.value+'Z')/1000)) : 0;
    else if (key === 'enabled') fields.enabled = f.enabled.checked;
    else if (['callsign','locator','power_dbm','ntp_ipv4'].includes(key)) {
      const text = f[key].value.trim();
      fields[key] = key === 'power_dbm' && f[key].validity?.badInput ? 'invalid' : text === '' ? null : key === 'power_dbm' ? progressNumber(text) : key === 'ntp_ipv4' ? text : text.toUpperCase();
    }
  }
  const outcomes = await saveProgressFields(fields,false,domain === 'radio' ? 'progress-settings-status' : 'progress-engineering-' + domain + '-status');
  if (outcomes.wifi && outcomes.wifi !== 'invalid') clearPassword('config-password');
}

function validWsprPlan(p) {
  if (!p || Object.keys(p).sort().join(',') !== 'alternate_callsign,frame_types,frames,rationale,schema,slot_separation_s,supported,type2_ambiguous' ||
      p.schema !== 'wspr-plan/1' || typeof p.supported !== 'boolean' || typeof p.type2_ambiguous !== 'boolean' ||
      !Array.isArray(p.frame_types) || !Number.isInteger(p.frames) || p.frames !== p.frame_types.length ||
      p.slot_separation_s !== 120 || typeof p.rationale !== 'string' || p.rationale.length < 1 || p.rationale.length > 512) return false;
  if (p.supported ? !['type1','type2','type3','type2,type3'].includes(p.frame_types.join(',')) : p.frames !== 0) return false;
  return p.type2_ambiguous ? p.supported && p.frame_types[0] === 'type2' && typeof p.alternate_callsign === 'string' &&
    p.alternate_callsign.length <= 12 && /^[A-Z0-9]+\/[A-Z0-9]+$/.test(p.alternate_callsign) : p.alternate_callsign === null;
}
let hostnameState = null, hostnameDraft = false, hostnameUncertain = false, hostnameReviewReady = false;
let reconnectEpoch = 0, reconnectRunning = false, restartSent = false;
let returnReceipt = null;
let applicationVersion = 1;
async function readApplication() {
  try {
    const result = await api('application/2');
    if (Object.keys(result.data).sort().join(',') !== 'capabilities,hardware,reboot_required,recurrence,schema,station,target,wspr_plan' ||
        result.data.schema !== (supportsAmplifier() ? 'transmitter-application/4' : 'transmitter-application/2') ||
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
function showDraftComparison() {
  const output = $('draft-comparison');
  if (!savedReadback) return;
  const f = $('config').elements, c = savedReadback.config, p = savedReadback.progress;
  const draftPins = pinChoices ? readPins() : undefined;
  const value = x => x === undefined ? 'Not observed' : x === null ? 'Cleared / unset' : x === '' ? 'Empty' : String(x);
  const schedules = x => Array.isArray(x) ? x.map(s=>`${s.period_s} / ${s.phase_s}`).join('\n') : x;
  const expiry = x => x === undefined || x === null ? x : x ? new Date(x*1000).toISOString().slice(0,19) : '';
  // Sparse omission inherits complete saved settings; explicit null masks them.
  const progress = (key, saved) => !p ? undefined : Object.hasOwn(p.fields,key) ? p.fields[key] : saved;
  const member = (object, key) => object === null ? null : object?.[key];
  const rows = [];
  let matching = 0;
  const row = (group,label,draft,progressValue,saved) => {
    const values = [draft,progressValue,saved].map(value);
    if (values[0] === values[2] && (!p || values[1] === values[2])) { ++matching; return; }
    rows.push({group,label,values});
  };
  for (const [key,label] of [['callsign','Callsign'],['locator','Grid locator'],['power_dbm','Reported WSPR power (dBm)']])
    row('Station identity',label,radio ? $('consumer-'+(key === 'power_dbm' ? 'power' : key)).value : f[key].value,p?.station?.[key],c?.station?.[key]);
  row('Wi-Fi','Wi-Fi network',radio ? $('consumer-ssid').value : f.ssid.value,member(progress('wifi',c?.wifi),'ssid'),c?.wifi?.ssid);
  row('Wi-Fi','Time server',radio ? $('consumer-time-server').value : f.ntp_ipv4.value,progress('ntp_ipv4',c?.wifi?.ntp_ipv4),c?.wifi?.ntp_ipv4);
  row('Schedules and pins','Standalone schedule enabled',f.enabled.checked,progress('enabled',c?.enabled),c?.enabled);
  row('Schedules and pins','Schedules (period / phase, seconds)',f.schedules.value,schedules(progress('schedules',c?.schedules)),schedules(c?.schedules));
  row('Schedules and pins','Schedule expiry (UTC)',f.expiry.value,expiry(progress('expires_utc_s',c?.expires_utc_s)),expiry(c?.expires_utc_s));
  for (const [key,label] of [['rf_gp','RF GPIO'],['button_gp','Switch GPIO'],['amplifier_gp','Amplifier GPIO'],['amplifier_active_high','Amplifier active-high'],['indicator','TX indicator'],['indicator_gp','Indicator GPIO'],['indicator_active_high','Indicator active-high']]) {
    if (key === 'amplifier_active_high' && !supportsAmplifier()) continue;
    row('Schedules and pins',label,member(draftPins,key),member(progress('pins',c?.pins),key),c?.pins?.[key]);
  }
  const node = (tag,text) => { const element=document.createElement(tag);element.textContent=text;return element; };
  output.replaceChildren();
  output.append(node('p',rows.length ? `${rows.length} fields differ. ${matching} fields match the complete saved settings${p ? ' and effective saved progress' : ''}.` : `${matching} fields match. No differences in these fields.`));
  for (const group of ['Station identity','Wi-Fi','Schedules and pins']) {
    const fields=rows.filter(row=>row.group===group);
    if (!fields.length) continue;
    const section=node('div','');section.className='comparison-group';section.append(node('h3',group));
    for (const {label,values} of fields) {
      section.append(node('h4',label));
      const list=node('dl','');list.className='comparison-values';
      for (const [index,title] of [[0,'Browser draft:'],[1,'Saved progress:'],[2,'Complete saved settings:']]) {
        if (index===1 && (!p || values[1]===values[2])) continue;
        const pair=node('div','');pair.append(node('dt',title),node('dd',values[index]));list.append(pair);
      }
      section.append(list);
    }
    output.append(section);
  }
  // Never copy password text into comparison markup, including revealed inputs.
  if (radio ? $('consumer-password').value : f.password.value)
    output.append(node('p','A new Wi-Fi password is entered in this browser. Password values are hidden from this comparison.'));
  output.append(node('p',(p ? 'Omitted progress fields use the complete saved settings; cleared fields remain distinct.' : 'Saved progress was not observed.') + ' Drive and carrier calibration retain their separate readback controls.'));
}
async function readSavedKeepingDraft() {
  requireReadback();
  const before = await readApplication();
  const saved = await api('config');
  const progress = await readProgress();
  const config = checkedConfig(saved), after = await readApplication();
  if (progress && progress.revision !== saved.revision) throw new Error('Saved progress changed during readback');
  if (!before.data.target || JSON.stringify(before.data.target) !== JSON.stringify(after.data.target) ||
      before.revision !== saved.revision || after.revision !== saved.revision) throw new Error('Pico context or saved revision changed during readback');
  savedReadback = {target:after.data.target,revision:saved.revision,config,progress:progress?.data || null,application:after.data};
  showDraftComparison();
  if ($('saved-wspr-plan')) $('saved-wspr-plan').textContent = after.data.wspr_plan
    ? 'Saved plan: ' + after.data.wspr_plan.frame_types.join(' → ') + '. ' + after.data.wspr_plan.rationale
    : applicationVersion === 2 ? 'Saved plan: no station identity is configured.'
    : 'Saved plan: this firmware supports Type 1 only.';
  $('saved-readback').textContent = JSON.stringify({saved_config:config,saved_progress:progress?.data || null,application_at_last_read:after.data},null,2);
  $('saved-readback').hidden = false; writeState = 'review';
  $('saved-readback-details').hidden = false;
  const h = after.data.hardware;
  const pins = p => p === null || !p ? 'Unknown / unavailable' : `RF GP${p.rf_gp}; switch ${p.button_gp === null ? 'disabled' : 'GP' + p.button_gp}; indicator ${p.indicator}; amplifier ${p.amplifier_gp === null ? 'disabled' : 'GP' + p.amplifier_gp + (p.amplifier_active_high === false ? ' active-low' : ' active-high')}`;
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
let consumerAttempt = radio ? readSetupReceipt(globalThis.location?.hash) : null, consumerSetupDirty = false, consumerNetworkDirty = false;
function setupReceiptHash() {
  if (!consumerAttempt) return '';
  const {kind,device,generation,digest} = consumerAttempt;
  return '#save=' + encodeURIComponent(JSON.stringify({kind,device,generation,digest}));
}
function updateSetupReceipt() {
  const hash = setupReceiptHash();
  if (hash || location.hash.startsWith('#save='))
    try { history.replaceState(null,'',location.pathname + location.search + hash); } catch (_) {}
  const hostname = snapshot?.network.configured_hostname;
  const usable = typeof hostname === 'string' && /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.local$/.test(hostname);
  $('consumer-resume').hidden = !hash || !usable;
  if (hash && usable) $('consumer-resume').href = 'http://' + hostname + '/' + hash;
}
const notice = (text, error = false) => { $('notice').textContent = text; $('notice').classList.toggle('error', error); };
async function api(path, method = 'GET', body, etag, timeout = 30000) {
  if ((returnReceipt || consumerAttempt) && localIdentity) checkReturningDevice(localIdentity.device_id);
  const headers = {};
  if (localIdentity) headers['X-WsprryPico-Session'] = session;
  if (method !== 'GET') Object.assign(headers, {'Content-Type':'application/json','X-WsprryPico-Request':'1'});
  if (etag) headers['If-Match'] = etag;
  let response;
  const settingWrite = method !== 'GET' && ['config','config/2','config/update','config/update/2','schedules','station','station/2','hardware','progress/update','progress/apply'].includes(path);
  if (settingWrite) {
    if (writeState !== 'ready' || !revision) throw new Error('Read and review saved settings before a new save');
    // Bounded context; credentials are never retained in the attempt record.
    const intended = JSON.parse(JSON.stringify(body));
    for (const config of [intended,intended.config,intended.fields]) if (config?.wifi) config.wifi.password = null;
    saveAttempt = {target:localIdentity ? {...localIdentity} : snapshot?.job.boot_id,path,revision:etag,intended,sent:true};
  }
  try {
    const selected = supportsAmplifier() ? WsprryAmplifier.select(path,body) : {path,body};
    response = radio ? await radio.request(selected.path,method,selected.body,etag,timeout) :
      await fetch('/api/v1/' + selected.path, {method, headers, body: selected.body === undefined ? undefined : JSON.stringify(selected.body), signal: AbortSignal.timeout(timeout), cache:'no-store'});
  } catch (error) {
    if (error.local) { if (saveAttempt) saveAttempt.sent=false; throw error; }
    error.unconfirmed = true;
    if (settingWrite) requireReadback();
    markTitleStale();
    snapshot = null; $('state').textContent = 'Unknown · request unconfirmed';
    $('output').textContent = 'Unknown'; $('job-progress').textContent = 'Progress unavailable · request unconfirmed'; controls(false);
    if (radio && !radio.authenticated) { localAuthenticated = false; $('local-login').hidden = false; $('local-logout').hidden = true; $('local-status').textContent = 'Session ended or unconfirmed. Log in again; your draft is preserved.'; }
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
      storage_fault:'Settings storage could not be verified. Resolve storage health before another save',
      invalid_gpio_drive:'Choose 2, 4, 8 or 12 mA for GPIO drive strength',
      standalone_frequency_required:'Choose and save a standalone WSPR frequency before enabling schedules',
      invalid_wspr_frequency:'Enter a whole WSPR dial frequency in Hz, without commas or decimals',
      frequency_not_allowed:'The WSPR tones fall outside the engine limits or saved frequency permissions. Choose an allowed frequency',
      FREQUENCY_REJECTED:'A requested RF frequency is outside the engine limits or saved frequency permissions. Review the requested frequencies',
      revision_conflict:'Saved settings changed. Your edits are preserved. Read current saved settings and review them before a new save',
      precondition_failed:'Saved revision changed. Your edits are preserved. Read and review current saved settings',
      pin_conflict:`GP${data.gp} is already assigned to ${data.owner}; choose a different pin for ${data.role}`,
      invalid_gp:'Choose an exposed Pico GPIO from the listed options',
      unsupported_pin_adapter:'The selected pin adapter requires supported firmware and explicit capability negotiation',
      amplifier_view_required:'Read amplifier settings with an amplifier-aware client',
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
  if (returnReceipt && localIdentity) checkReturningDevice(localIdentity.device_id);
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
    $('local-password-label').textContent = 'Pico password';
    $('local-description').textContent = 'Enter the Pico password. By default, it is the Wi-Fi password saved on this Pico. Use your separate Pico password if you changed it. Your login stays in this tab and expires after inactivity.';
    try {
      localIdentity = await radio.identity();
      checkReturningDevice(localIdentity.device_id);
      pageIdentity.bind(localIdentity);
      await presentationTitle();
      $('local-status').textContent = 'Signed out. Enter the Pico password to log in.';
      notice('Log in to read or change radio settings.');
    } catch (error) { notice(error.message + '. Check the Pico address and your Wi-Fi connection, then reload.',true); }
    return true;
  }
  try {
    const response = await fetch('/local/v1/identity', {cache:'no-store', signal:AbortSignal.timeout(5000)});
    if (!response.ok) return false;
    localIdentity = await response.json();
    checkReturningDevice(localIdentity.device_id);
    $('local-access').hidden = false;
    pageIdentity.bind(localIdentity);
    $('local-status').textContent = 'Local access requires authentication.';
    try {
      const state = await local('status');
      if (state.wtp_session) session = state.wtp_session;
    } catch (_) { notice('Enter the local-access password to authorize this SoftAP browser.'); return true; }
    localAuthenticated = true; $('local-login').hidden = true;
    $('local-status').textContent = 'Local session authenticated.';
    if (localIdentity.surface === 'provisioned_preclock') {
      try { await supplyPhoneTime(); }
      catch (e) { notice('Local session authorized, but phone time was rejected: ' + e.message + '.', true); }
    }
    return true;
  } catch (_) { return false; }
}
function controls(connected) {
  online = connected;
  calibrationEditor?.setAvailability(!!connected && !busy && WsprryRfCalibration.supported(capabilities?.rf_calibration) && !!snapshot && snapshot.job.owner_id === null && snapshot.job.output_active === false && ['empty','complete','aborted','missed'].includes(snapshot.job.state));
  frequencyEditor?.setAvailability(!!connected && !busy && WsprryStandaloneFrequency.supported(capabilities?.standalone_frequency) && !!snapshot && snapshot.job.owner_id === null && snapshot.job.output_active === false && ['empty','complete','aborted','missed'].includes(snapshot.job.state));
  driveEditor?.setAvailability(!!connected && !busy && !!snapshot && snapshot.job.owner_id === null && snapshot.job.output_active === false && ['empty','complete','aborted','missed'].includes(snapshot.job.state));
  $('refresh').disabled = busy;
  $('reload-config').disabled = busy || !online;
  const idle = online && snapshot && snapshot.job.owner_id === null && snapshot.job.output_active === false && !['armed','running','failed'].includes(snapshot.job.state);
  $('settings').disabled = busy || !idle;
  for (const area of ['station','network']) {
    $('engineering-' + area + '-form').hidden = Boolean(radio);
    $('engineering-' + area + '-settings').disabled = Boolean(radio) || busy || !idle || writeState !== 'ready';
    $('consumer-' + area + '-form').hidden = !radio;
  }
  $('save-config').disabled = busy || !idle || writeState !== 'ready';
  $('initial-config').hidden = Boolean(radio) || currentConfig !== null;
  $('initial-config').disabled = busy || !idle || writeState !== 'ready';
  $('read-saved').disabled = busy || !online || Boolean(localIdentity && !localAuthenticated);
  $('review-saved').disabled = busy || !online || writeState !== 'review';
  $('login-recovery').hidden = !radio;
  $('inspect-logins').disabled = busy;
  $('retire-login').disabled = busy || !retirementDiscovery || !$('retirement-target').value;
  $('consumer-setup').hidden = !radio;
  $('consumer-network-settings').disabled = busy || !idle || !localAuthenticated || Boolean(consumerAttempt);
  $('consumer-station-settings').disabled = $('consumer-network-settings').disabled;
  $('consumer-check-save').disabled = busy || !localAuthenticated || !consumerAttempt;
  $('pico-password-settings').disabled = busy || !idle || !localAuthenticated || !picoPasswordState || Boolean(consumerAttempt);
  $('pico-password-default').disabled = $('pico-password-settings').disabled || picoPasswordState?.data.wifi_default !== false || !currentConfig?.wifi?.ssid && !$('consumer-ssid').value;
  $('hostname-settings').disabled = busy || !idle || !hostnameState?.writable;
  $('hostname-save').disabled = busy || !idle || !hostnameState?.writable || hostnameUncertain;
  $('hostname-default').disabled = $('hostname-save').disabled;
  $('hostname-review').hidden = !hostnameReviewReady;
  $('hostname-review').disabled = busy || !idle;
  $('restart').disabled = busy || !idle || !capabilities?.features?.restart || restartSent;
  if (hostnameState?.pending_restart) {
    $('consumer-network-settings').disabled = true;
    $('consumer-station-settings').disabled = true;
  }
  $('wifi-off').disabled = busy || !idle || !snapshot.network.enabled;
  $('job-settings').disabled = busy || !idle || snapshot.standalone.reboot_required;
  $('message-settings').disabled = $('job-settings').disabled || !capabilities?.message_jobs;
  $('message-availability').textContent = !online ? (radio && !localAuthenticated ? 'Log in above to prepare a message.' : 'Connection unavailable. Refresh status before preparing a message; RF output is unknown.') :
    busy ? 'Waiting for the current request to finish.' : !idle ? 'The transmitter is occupied or its job/output state does not permit a new job. Check Transmitter status above.' :
    snapshot.standalone.reboot_required ? 'Saved changes require a restart. Use Restart device in Wi-Fi/Host before preparing another job.' :
    !capabilities?.message_jobs ? 'This firmware does not advertise message jobs. A supported job file can still be used below.' :
    'Prepare a complete message below. Load and arm sends one explicit job; the Pico validates its timing and frequency.';
  $('abort').disabled = busy || !online || snapshot?.job.owner_id !== session || !['loaded','armed','running'].includes(snapshot.job.state);
  $('release').disabled = busy || !online || snapshot?.job.owner_id !== session || snapshot.job.output_active !== false || ['armed','running','failed'].includes(snapshot.job.state);
  if (savedProgress) {
    $('initial-config').disabled = busy || !idle || writeState !== 'ready' || !savedProgress.data.complete;
    $('apply-progress').disabled = busy || !idle || writeState !== 'ready' || savedProgress.data.draft_revision === '0' || !savedProgress.data.apply_domains.radio;
    for (const domain of ['station','network']) $('apply-engineering-' + domain + '-progress').disabled = busy || !idle || writeState !== 'ready' || savedProgress.data.draft_revision === '0' || !savedProgress.data.apply_domains[domain];
    $('apply-station-progress').disabled = busy || !idle || writeState !== 'ready' || savedProgress.data.draft_revision === '0' || !savedProgress.data.station_complete || !savedProgress.data.wspr_plan?.supported || Boolean(consumerAttempt);
    $('consumer-station-settings').disabled ||= writeState !== 'ready';
  }
  for (const id of passwordFields) setPasswordVisible(id,$(id).type === 'text');
}
function fill(c, network = c?.wifi) {
  currentConfig = c; dirty = false;
  const form = $('config').elements;
  if (!engineeringStationDirty) for (const name of ['callsign','locator','power_dbm']) form[name].value = c?.station[name] ?? '';
  if (!engineeringNetworkDirty) {
    form.ssid.value = network?.ssid ?? '';
    form.ntp_ipv4.value = network?.ntp_ipv4 ?? 'pool.ntp.org';
  }
  if (radio) {
    $('consumer-identity-help').hidden = false;
    for (const name of ['callsign','locator','power_dbm','ssid','password','ntp_ipv4']) form[name].readOnly = true;
    if (!consumerSetupDirty) {
      $('consumer-ssid').value = network?.ssid ?? '';
      $('consumer-time-server').value = network?.ntp_ipv4 ?? 'pool.ntp.org';
      $('consumer-callsign').value = c?.station.callsign ?? '';
      $('consumer-locator').value = c?.station.locator ?? '';
      $('consumer-power').value = c?.station.power_dbm ?? 37;
    }
  }
  if (!engineeringNetworkDirty) clearPassword('config-password');
  form.enabled.checked = c?.enabled ?? false;
  form.schedules.value = (c?.schedules || [{period_s:120,phase_s:0}]).map(s => `${s.period_s} / ${s.phase_s}`).join('\n');
  fillPins(c?.pins);
  form.expiry.value = c?.expires_utc_s ? new Date(c.expires_utc_s * 1000).toISOString().slice(0,19) : '';
}
async function refresh(loadConfig = false) {
  if (loadConfig) requireReadback();
  const identityRequest = pageIdentity.request();
  // Keep this browser sequential so the other admitted client can progress.
  try {
    if (!capabilities) capabilities = (await api('capabilities')).data;
    if (!pinChoices) { try { pinChoices = (await api('pins')).data.choices; } catch (_) {} }
    snapshot = (await api('status')).data; expectedPause = false; observedAt = new Date().toLocaleTimeString();
    if (capabilitiesBoot && capabilitiesBoot !== snapshot.job.boot_id) capabilities = (await api('capabilities')).data;
    if (capabilitiesBoot && capabilitiesBoot !== snapshot.job.boot_id) { driveEditor?.invalidate(); calibrationEditor?.invalidate(); frequencyEditor?.invalidate(); }
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
    await readHostname(identityRequest);
    const discovery = {unconfigured:'Not configured',waiting_address:'Waiting for Wi-Fi address',probing:'Checking hostname',active:'Advertised',conflict:'Hostname conflict',failed:'Unavailable'};
    $('discovery').textContent = discovery[n.mdns_state] || 'Unavailable';
    $('discovery-help').textContent = n.mdns_state === 'conflict' ? 'Another device is using this hostname. Resolve the duplicate, then retry with USB Console WIFI OFF and WIFI ON while idle. The device will not rename itself.' : n.mdns_reason === 'device_identity_mismatch' ? 'Credentials belong to a different device. Rebuild with this device’s certificate bundle and recover through USB Console.' : n.mdns_state === 'failed' ? 'Name discovery failed. Use the current IP address and check USB Console INFO.' : n.mdns_state === 'active' ? (radio ? 'Use this hostname or the current IP address on your local network.' : 'Use this hostname after DHCP address changes. An IP URL needs a matching certificate IP address.') : '';
    if (radio) {
      $('consumer-return').textContent = `On your normal Wi-Fi, open http://${n.configured_hostname || n.ipv4}/ or http://${n.ipv4}/. The Pico’s setup Wi-Fi is normally off while this connection is healthy.`;
      updateSetupReceipt();
    }
    $('recovery').textContent = !capabilities.active_job_connections ? 'Network connections pause while RF jobs are armed or running. The job owner can abort over an established WTP connection; physical USB Console ABORT can also stop a job. ' : '';
    $('recovery').textContent += !s.storage_healthy ? 'Storage fault. Recover through USB Console.' : s.reboot_required ? 'Network or pin settings saved. Use Restart device to apply them.' : s.suspended ? 'Standalone operation is suspended.' : '';
    if (s.frequency_required) $('recovery').textContent += ' Standalone transmission is blocked: choose and save a WSPR frequency in Schedules and radio pins, then explicitly enable schedules.';
    if (loadConfig) {
      const c = await api('config'); const config=checkedConfig(c);
      let network = config?.wifi;
      if (radio && !config) {
        const saved = (await api('consumer/setup/api/owner/v1/public-status')).data;
        if (saved.version !== 1 || saved.device_id !== localIdentity.device_id ||
            saved.boot_id !== localIdentity.boot_id || saved.generation !== localIdentity.generation ||
            ![4,5].includes(saved.profile_source) ||
            saved.network !== null && (typeof saved.network?.ssid !== 'string' || typeof saved.network?.time_server !== 'string'))
          throw new Error('Saved Wi-Fi could not be confirmed. Read the Pico identity and try again.');
        network = saved.network ? {ssid:saved.network.ssid,ntp_ipv4:saved.network.time_server} : undefined;
      }
      revision = c.revision; fill(config,network);
      const p = await readProgress(true); if (p && p.revision !== c.revision) throw new Error('Saved progress changed during reload'); writeState = 'ready'; $('save-reconcile-status').textContent = 'Saved settings reloaded into this browser. Review any new edits before saving.'; showProgress();
      if (radio) await readPicoPassword();
    }
    updateProgress(); messagePreview();
    notice('Connected · Status updated ' + observedAt); controls(true);
  } catch (e) { markTitleStale(); snapshot = null; $('job-progress').textContent = 'Progress unavailable · status unknown'; $('state').textContent = 'Unknown · read failed'; $('output').textContent = 'Unknown'; for (const id of ['clock','owner','network','hostname','discovery']) $(id).textContent = 'Unknown'; $('discovery-help').textContent = ''; if (expectedPause) notice('RF job accepted. New network connections pause while armed or running. Use USB Console ABORT to stop it, or refresh after completion.'); else if (radio && !radio.authenticated) { localAuthenticated=false; $('local-login').hidden=false; $('local-logout').hidden=true; $('local-status').textContent='Session ended. Log in again; your draft is preserved.'; notice('Radio session ended. Log in again, then check status before repeating an interrupted action. Your edits are preserved.',true); } else notice('Connection unavailable: ' + e.message + '. The connection limit may be reached. Check Wi-Fi and the client certificate, then refresh.', true); controls(false); }
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
async function readPicoPassword() {
  try {
    const result = await api('consumer/password');
    if (result.data.schema !== 'pico-password/1' || !result.revision ||
        result.data.target?.device_id !== localIdentity.device_id ||
        result.data.target?.boot_id !== localIdentity.boot_id ||
        typeof result.data.wifi_default !== 'boolean' || result.data.saved !== true)
      throw new Error('The Pico password setting could not be confirmed. Refresh before changing it.');
    picoPasswordState = result;
    $('pico-password-form').hidden = false;
    $('pico-password-status').textContent = result.data.wifi_default
      ? 'Using the default: the Wi-Fi password saved on this Pico.'
      : 'Using a separate Pico password. Changing Wi-Fi does not change it.';
  } catch (error) {
    picoPasswordState = null;
    $('pico-password-form').hidden = error.code === 'not_found';
    if (error.code !== 'not_found') throw error;
  }
}
function picoPasswordSignedOut(message) {
  radio.clear(); picoPasswordState = null; localAuthenticated = false;
  $('local-login').hidden = false; $('local-logout').hidden = true;
  snapshot = null; requireReadback(); controls(false); markTitleStale();
  $('pico-password-status').textContent = message;
  $('local-status').textContent = message;
  $('local-password').focus();
}
async function savePicoPassword(password) {
  if (!picoPasswordState) throw new Error('Read the Pico password setting before changing it.');
  try {
    const result = await api('consumer/password','PUT',{
      schema:'pico-password/1',target:picoPasswordState.data.target,password
    },picoPasswordState.revision);
    if (result.data.schema !== 'pico-password/1' || result.data.saved !== true ||
        result.data.wifi_default !== (password === null) ||
        result.data.target?.device_id !== localIdentity.device_id ||
        result.data.target?.boot_id !== localIdentity.boot_id)
      throw Object.assign(new Error('The Pico password save could not be confirmed.'),{unconfirmed:true});
    const message = password === null ? 'Pico password saved. Sign in with the saved Wi-Fi password.'
      : 'Pico password saved. Sign in with your new Pico password.';
    picoPasswordSignedOut(message); notice(message);
  } catch (error) {
    if (error.unconfirmed || error.code === 'password_save_unconfirmed') {
      picoPasswordSignedOut('Password change unconfirmed. Try signing in with the new password, then the previous password if refused. If neither works, restart the Pico and try again. Do not repeat the save automatically.');
      error.message = $('local-status').textContent;
    }
    throw error;
  } finally {
    clearPassword('pico-new-password'); clearPassword('pico-confirm-password');
  }
}
$('pico-password-form').onsubmit = event => {
  event.preventDefault();
  const password = $('pico-new-password').value, confirm = $('pico-confirm-password').value;
  const valid = /^[\x20-\x7e]{8,63}$/.test(password);
  const message = !valid ? 'Use 8–63 characters without accented letters or emoji.'
    : password !== confirm ? 'The Pico passwords do not match. Enter the same password twice.' : '';
  $('pico-password-error').textContent = message;
  for (const id of ['pico-new-password','pico-confirm-password']) $(id).setAttribute('aria-invalid',String(Boolean(message)));
  if (message) { $(!valid ? 'pico-new-password' : 'pico-confirm-password').focus(); return; }
  return action(() => savePicoPassword(password));
};
for (const id of ['pico-new-password','pico-confirm-password']) $(id).oninput = () => {
  $('pico-password-error').textContent = '';
  for (const field of ['pico-new-password','pico-confirm-password']) $(field).setAttribute('aria-invalid','false');
};
$('pico-password-default').onclick = () => action(() => savePicoPassword(null));
$('refresh').onclick = () => action(() => refresh());
$('local-login').onsubmit = event => { event.preventDefault(); return action(async () => {
  cancelReconnect();
  const password = $('local-password').value;
  setPasswordVisible('local-password',false);
  try {
    if (radio) {
      localIdentity = await radio.identity();
      checkReturningDevice(localIdentity.device_id);
      pageIdentity.bind(localIdentity);
      await radio.login(password,localIdentity);
    } else {
      const fresh = await fetch('/local/v1/identity', {cache:'no-store',credentials:'omit',redirect:'error',signal:AbortSignal.timeout(5000)});
      if (!fresh.ok) throw new Error('Read the local device identity before signing in.');
      localIdentity = await fresh.json();
      checkReturningDevice(localIdentity.device_id);
      pageIdentity.bind(localIdentity);
      await local('login','POST',{version:1,device_id:localIdentity.device_id,password});
    }
  } finally { clearPassword('local-password'); }
  localAuthenticated = true; $('local-login').hidden = true;
  $('local-status').textContent = radio ? 'Radio session authenticated.' : 'Local session authenticated.';
  if (radio) $('local-logout').hidden = false;
  if (localIdentity.surface === 'provisioned_preclock') {
    try { await supplyPhoneTime(); }
    catch (e) { notice('Local session authorized, but phone time was rejected: ' + e.message + '.', true); return; }
  }
  if (dirty || writeState !== 'ready' && saveAttempt) { await refresh(); await readSavedKeepingDraft(); }
  else await refresh(true);
  if (radio && !picoPasswordState && localAuthenticated) await readPicoPassword();
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
  $('retirement-status').textContent = `Pico ${discovery.device_id}; ${discovery.interface} at ${discovery.authority}. A login may belong to another operator. Retirement ends only that login and cancels its undelivered effects. Saved settings and radio jobs remain. Enter the current Pico password below, select a login, then retire it.`;
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
  cancelReconnect();
  markTitleStale();
  clearPasswords();
  await radio.logout(); localAuthenticated = false;
  $('local-login').hidden = false; $('local-logout').hidden = true;
  $('local-status').textContent = 'Signed out. Log in to read or change settings.';
  snapshot = null; controls(false); notice('Logged out. Radio job state has not changed.');
});
$('consumer-power').replaceChildren(new Option('Choose reported power',''),...[0,3,7,10,13,17,20,23,27,30,33,37,40,43,47,50,53,57,60]
  .map(power => new Option(String(power),String(power))));
for (const id of ['consumer-network-form','consumer-station-form']) $(id).oninput = event => { consumerSetupDirty = true; if (id === 'consumer-station-form') editedProgress(event); else consumerNetworkDirty = true; showDraftComparison(); };
async function saveConsumer(kind, savedStation) {
  setPasswordVisible('consumer-password',false);
  if (consumerAttempt) throw new Error('Check the previous saved result first');
  const status = $('consumer-save-status');
  status.textContent = 'Preparing your settings…';
  try {
    if (kind === 'station') {
      await readApplication();
      await reviewWspr(savedStation ? {callsign:savedStation.callsign,locator:savedStation.locator,power_dbm:savedStation.power_dbm} : {callsign:$('consumer-callsign').value.trim().toUpperCase(),
        locator:$('consumer-locator').value.trim().toUpperCase(),power_dbm:Number($('consumer-power').value)},'consumer-wspr-plan');
    }
    consumerAttempt = kind === 'network' ? await radio.prepareNetwork(localIdentity, {
      ssid:$('consumer-ssid').value,password:$('consumer-password').value,time_server:$('consumer-time-server').value.trim()
    }) : await radio.prepareStation(localIdentity, {
      ...(savedStation ? {callsign:savedStation.callsign,locator:savedStation.locator,powerDbm:savedStation.power_dbm,progressRevision:savedProgress.revision} : {callsign:$('consumer-callsign').value.trim().toUpperCase(),locator:$('consumer-locator').value.trim().toUpperCase(),powerDbm:Number($('consumer-power').value)})
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
$('consumer-station-form').onsubmit = event => { event.preventDefault(); return action(() => supportsProgress() ? saveProgressFields(stationProgressEdits(),true) : saveConsumer('station')); };
$('consumer-check-save').onclick = () => action(async () => {
  const result = await radio.checkSetup(consumerAttempt);
  $('consumer-save-status').textContent = result === 'saved' ? 'Your settings were saved and verified.' :
    result === 'failed' ? 'These settings were not saved. You can correct them and try again.' :
    'The result is still unconfirmed. Wait for the Pico to return, log in and check again. No save has been repeated.';
  if (result !== 'unconfirmed') { consumerAttempt = null; updateSetupReceipt(); await refresh(); await readSavedKeepingDraft(); }
});
if (consumerAttempt) $('consumer-save-status').textContent = 'A pending save receipt was recovered. Log in, then select Check saved result. No save has been repeated.';
$('config').oninput = event => { dirty = true; editedProgress(event); showDraftComparison(); };
$('reload-config').onclick = () => action(async () => {
  if ((dirty || engineeringStationDirty || engineeringNetworkDirty || consumerSetupDirty || progressEdits.size) && !confirm('Discard your unsaved changes and reload saved settings?')) return;
  progressEdits.clear(); dirty=false;
  engineeringStationDirty=false; engineeringNetworkDirty=false; consumerSetupDirty=false; consumerNetworkDirty=false;
  for (const result of document.querySelectorAll?.('.field-result') || []) {result.textContent = '';result.classList.toggle('error',false);}
  for (const input of document.querySelectorAll?.('[aria-invalid]') || []) input.removeAttribute('aria-invalid');
  await refresh(true);
});
$('config').onsubmit = event => { event.preventDefault(); setPasswordVisible('config-password',false); return action(async () => {
  if (supportsProgress()) return saveConfigProgress();
  const f = $('config').elements;
  const schedules = f.schedules.value.trim().split('\n').map(line => {
    if (!/^\s*\d+\s*\/\s*\d+\s*$/.test(line)) throw new Error('Use period / phase for each schedule');
    const [period_s,phase_s] = line.split('/').map(Number); return {period_s,phase_s};
  });
  if (!currentConfig) throw new Error('Complete station commissioning before saving schedules and pins');
  const config = {...currentConfig,enabled:f.enabled.checked,station:{...currentConfig.station},wifi:{...currentConfig.wifi,password:null},schedules,pins:pinChoices ? readPins() : currentConfig.pins,expires_utc_s:f.expiry.value ? Date.parse(f.expiry.value + 'Z') / 1000 : 0};
  // Advanced opt-ins are managed through CONFIG/API, outside the ordinary form.
  // A station/network edit must preserve the operator's saved choices.
  for (const name of ['allow_unqualified_frequency','allow_non_amateur_frequency']) {
    if (currentConfig?.[name] === true) config[name] = true;
  }
  // Broad legacy identities remain readable/preservable even when they cannot
  // transmit. Validate a changed identity; an unrelated save keeps its bytes.
  if (!currentConfig || ['callsign','locator','power_dbm'].some(key => config.station[key] !== currentConfig.station[key]))
    await reviewWspr(config.station,'draft-wspr-plan');
  const result = await api(applicationVersion === 2 ? 'config/2' : 'config','PUT',config,revision); const confirmed=checkedConfig(result,false); revision = result.revision; fill(confirmed);
  await refresh(); notice(result.data.reboot_required ? 'Settings saved. Use Restart device to apply network or pin changes.' : 'Settings saved and applied.');
}); };
async function applyProgressDomain(domain) {
  if (!savedProgress || writeState !== 'ready') throw new Error('Read and review saved progress before applying.');
  const result = await api('progress/apply','POST',{schema:'transmitter-progress/1',target:savedProgress.data.target,application:{draft_revision:savedProgress.data.draft_revision,domain}},savedProgress.revision);
  currentConfig = checkedConfig(result,false); revision = result.revision;
  await refresh(); await readSavedKeepingDraft();
  notice(result.data.reboot_required ? 'Saved progress applied. Network or pin changes need an explicit restart.' : 'Saved progress applied. Check the selected operation’s current status before transmitting.');
}
$('apply-progress').onclick = () => action(() => applyProgressDomain('radio'));
for (const domain of ['station','network']) $('apply-engineering-' + domain + '-progress').onclick = () => action(() => applyProgressDomain(domain));
$('apply-station-progress').onclick = () => action(async () => {
  if (!savedProgress || writeState !== 'ready') throw new Error('Read and review saved station progress before applying.');
  await saveConsumer('station',savedProgress.data.station);
});
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
  if (restartSent) return;
  if (!confirm('Restart using saved settings? This tab keeps your drafts. Sign in again when the Pico returns.')) return;
  const before = snapshot?.job.boot_id;
  if (!before) throw new Error('Refresh status before restarting');
  const named = await readHostname();
  const saved = await api('config');
  if (named && saved.revision !== named.revision) throw new Error('Saved settings changed. Refresh and review the intended hostname before restarting.');
  const expected = {device: snapshot.job.device_id || localIdentity?.device_id || named?.target.device_id,
    boot: before, name: named?.saved || snapshot.network.configured_hostname};
  if (!/^[0-9a-f]{32}$/.test(expected.device) || !canonicalHostname(expected.name))
    throw new Error('Read the confirmed device hostname before restarting.');
  returnReceipt = expected;
  showContinuation(expected);
  restartSent = true; // Sent once, including an unknown/lost acknowledgement.
  try { await api('restart', 'POST', {}, saved.revision); }
  catch (error) {
    if (error.serverResponse) { restartSent = false; throw error; }
    $('restart-status').textContent = 'Restart acknowledgement lost. Checking once; another restart will not be sent.';
  }
  snapshot = null; controls(false); markTitleStale();
  void monitorRestart(expected);
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
function messageFrequencyFields() {
  const mode = $('message-mode').value;
  $('message-frequency-label').textContent = mode === 'fskcw' ? 'Space frequency (Hz)' : mode === 'dfcw' ? 'Dot frequency (Hz)' : 'Carrier frequency (Hz)';
  $('message-frequency-help').textContent = mode === 'fskcw' ? 'Direct RF space frequency. Mark is above space by the positive shift; gaps within a message use space. Repeat gaps have RF off.' : mode === 'dfcw' ? 'Direct RF dot frequency. Dash is above dot by the positive shift; both use the selected dot length. Gaps have RF off.' : 'Direct RF carrier frequency. Dots and dashes use this frequency; gaps have RF off.';
  $('message-shift').disabled = mode === 'qrss';
  $('message-shift-help').textContent = mode === 'qrss' ? 'Unused in QRSS. Your shift entry is kept for FSKCW and DFCW.' : mode === 'fskcw' ? 'Positive shift in Hz: mark = space + shift.' : 'Positive shift in Hz: dash = dot + shift.';
}
function messageFrequencies(mode) {
  const fail = (id, text) => { const error = new Error(text); error.input = id; throw error; };
  const parse = (id, label) => { try { return nanoDecimal($(id).value,label); } catch (error) { error.input=id; throw error; } };
  const base = parse('message-frequency',mode === 'fskcw' ? 'Space frequency' : mode === 'dfcw' ? 'Dot frequency' : 'Carrier frequency');
  if (!base) fail('message-frequency','Enter a frequency greater than zero.');
  const shift = mode === 'qrss' ? 0n : parse('message-shift','Frequency shift');
  if (mode !== 'qrss' && !shift) fail('message-shift','Enter a frequency shift greater than zero.');
  const upper = base + shift;
  if (upper > 18446744073709551615n) fail('message-shift','Frequency plus shift is too large. Reduce the frequency or shift.');
  const states = mode === 'qrss' ? [['Carrier',base]] : mode === 'fskcw' ? [['Space',base],['Mark',upper]] : [['Dot',base],['Dash',upper]];
  const ranges = capabilities?.wtp?.frequency_ranges;
  for (const [name,frequency] of states) {
    if (Array.isArray(ranges) && !ranges.some(r => frequency >= BigInt(r.minimum_nhz) && frequency <= BigInt(r.maximum_nhz)))
      fail(frequency === base ? 'message-frequency' : 'message-shift',name + ' frequency is outside the available engine ranges. Choose a frequency and shift within those ranges.');
  }
  const hz = n => { const fraction=(n%1000000000n).toString().padStart(9,'0').replace(/0+$/,''); return n/1000000000n + (fraction ? '.'+fraction : '') + ' Hz'; };
  return {frequency:mode === 'fskcw' ? upper : base,second:mode === 'qrss' ? 0n : mode === 'fskcw' ? base : upper,preview:states.map(([name,n])=>name+' '+hz(n)).join(' · ')};
}
function messagePlan() {
  const text = $('message-text').value, mode = $('message-mode').value;
  if (!text || text.length > 32) throw new Error('Use 1–32 characters, including spaces. The message has ' + text.length);
  if (!['qrss','fskcw','dfcw'].includes(mode)) throw new Error('Choose QRSS, FSKCW or DFCW');
  const frequencies = messageFrequencies(mode);
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
  return {duration,events,frequencies:frequencies.preview,body:{mode,message:text,frequency_nhz:frequencies.frequency.toString(),space_frequency_nhz:frequencies.second.toString(),timing:Object.fromEntries(Object.entries(timing).map(([k,v])=>[k,v.toString()])),repeat_count:repeat,repeat_gap_ns:repeatGap.toString(),allow_frequency_adjustment:true}};
}
let messageEdited = false;
function messagePreview() {
  messageFrequencyFields();
  for (const id of ['message-frequency','message-shift']) $(id).setAttribute('aria-invalid','false');
  if (!messageEdited && !$('message-text').value) {
    $('message-preview').textContent = 'Enter a message and frequency to calculate its duration.';
    $('message-preview').classList.toggle('error',false); return;
  }
  try { const p = messagePlan(); $('message-preview').textContent = p.frequencies + ' · ' + durationText(p.duration) + ' · ' + p.events + ' / ' + (capabilities?.wtp?.max_events || 512) + ' events · ' + $('message-text').value.length + ' / 32 characters'; $('message-preview').classList.toggle('error',false); }
  catch (e) { $('message-preview').textContent = e.message; $('message-preview').classList.toggle('error',true); if (e.input) $(e.input).setAttribute('aria-invalid','true'); }
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
$('message-form').oninput = () => { messageEdited=true; $('message-result').textContent=''; messagePreview(); };
$('message-mode').onchange = () => { $('message-result').textContent=''; messagePreview(); };
messagePreview();
$('message-form').onsubmit = event => { event.preventDefault(); messageEdited=true; messagePreview(); return action(async () => {
  $('message-result').textContent = ''; $('message-result').classList.toggle('error',false);
  try {
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
  $('message-result').textContent = $('job-result').textContent;
  await observeAfterArm();
  } catch (error) {
    $('message-result').textContent = error.message.replace(/[.!?]$/,'') + (error.unconfirmed ? '. Outcome unconfirmed; no action was repeated.' : '.') + ' Your entries are preserved.';
    $('message-result').classList.toggle('error',true); throw error;
  }
}); };
if (typeof setInterval === 'function') setInterval(() => {
  if (!busy && online && activePlan && ['armed','running'].includes(snapshot?.job.state)) action(() => refresh());
}, 5000);

action(async () => { await discoverLocal(); if ((!radio && !localIdentity) || localAuthenticated) await refresh(true); });

function readPins() {
  const f = $('config').elements;
  return {engine:'direct',rf_gp:Number(f.rf_gp.value),i2c_pair:null,
    button_gp:f.button_gp.value === '' ? null : Number(f.button_gp.value),
    amplifier_gp:supportsAmplifier() && f.amplifier_gp.value !== '' ? Number(f.amplifier_gp.value) : null,
    ...(supportsAmplifier() ? {amplifier_active_high:f.amplifier_active_high.value === 'true'} : {}),
    lpf_gps:[],indicator:f.indicator.value,
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
  pinOptions(f.amplifier_gp,'Amplifier',true);
  pinOptions(f.indicator_gp,'Indicator',false);
  f.indicator_gp.disabled = f.indicator.value !== 'external';
  f.indicator_active_high.disabled = f.indicator.value !== 'external';
  f.amplifier_gp.disabled = !supportsAmplifier();
  f.amplifier_active_high.disabled = !supportsAmplifier() || f.amplifier_gp.value === '';
}
function fillPins(plan) {
  const f = $('config').elements;
  const p = plan || {rf_gp:2,button_gp:14,amplifier_gp:null,indicator:'onboard_led',indicator_gp:null,indicator_active_high:true};
  const gps = pinChoices?.eligible_gps || [2,14];
  for (const key of ['rf_gp','button_gp','amplifier_gp','indicator_gp']) {
    const optional = key === 'button_gp' || key === 'amplifier_gp';
    const options = optional ? [new Option('Disabled','')] : [];
    f[key].replaceChildren(...options,...gps.map(gp=>new Option('GP'+gp,String(gp))));
    f[key].value = p[key] === null ? (optional ? '' : '0') : String(p[key]);
  }
  f.indicator.value = p.indicator;
  f.indicator_active_high.value = String(p.indicator_active_high ?? true);
  f.amplifier_active_high.value = String(p.amplifier_active_high ?? true);
  $('pin-settings').disabled = !pinChoices;
  $('i2c-choices').textContent = pinChoices ? pinChoices.i2c_pairs.map(p=>`I²C${p.controller}: GP${p.sda_gp} SDA / GP${p.scl_gp} SCL`).join(' · ') : 'Pin selection is unavailable on this firmware.';
  lockPins();
}
for (const key of ['rf_gp','button_gp','amplifier_gp','indicator','indicator_gp']) $('config').elements[key].addEventListener('change',lockPins);

function wsprDraftFeedback(call,locator,id) {
  const output = $(id); if (!output) return;
  if (locator && !/^[A-R]{2}[0-9]{2}([A-X]{2})?$/.test(locator)) { output.textContent = 'Use a locator such as EM18 or EM18IG: fields A–R, two digits, then optional A–X subsquare. ' + (savedProgress ? 'Valid independent fields can still be saved.' : 'Your draft has not been saved.'); return; }
  if (call.startsWith('<') && locator.length !== 6) { output.textContent = 'A bracketed callsign needs a six-character locator. ' + (savedProgress ? 'Valid independent fields can still be saved.' : 'Your draft has not been saved.'); return; }
  const description = call.startsWith('<') ? 'Type 3 · one hash frame; receiver context is needed.' : call.includes('/') ?
    locator.length === 6 ? 'Type 2 then Type 3 · two frames in adjacent even-minute windows, 230.592 seconds total. Receiver hash context may be needed.' : 'Type 2 · one frame, without a locator.' :
    'Type 1 · one frame; first four locator characters on air, all six retained in settings.';
  output.textContent = 'Draft: ' + description + (/\/(?:[Q-Z]|0[0-9])$/.test(call) ? ' This Type 2 suffix has an ambiguous letter/numeric interpretation; receivers may choose either. Your requested call is retained.' : '') + (savedProgress ? ' The Pico validates encoding before applying saved station settings.' : ' The Pico validates encoding before saving.');
}
$('config').addEventListener('input', () => { const f=$('config').elements; wsprDraftFeedback(f.callsign.value.trim().toUpperCase(),f.locator.value.trim().toUpperCase(),'draft-wspr-plan'); });
$('consumer-station-form').addEventListener('input', () => wsprDraftFeedback($('consumer-callsign').value.trim().toUpperCase(),$('consumer-locator').value.trim().toUpperCase(),'consumer-wspr-plan'));

// P15.10: metadata never derives from the address bar, draft or browser storage.
function markTitleStale() { pageIdentity.stale(); }
function parseReturnReceipt() {
  const hash = globalThis.location?.hash || '';
  if (!hash.startsWith('#hostname-return=')) return;
  const args = new URLSearchParams(hash.slice(1));
  const value = args.get('hostname-return');
  try {
    const r = JSON.parse(value);
    if (value.length > 320 || Object.keys(r).sort().join(',') !== 'boot,device,name' ||
        !/^[0-9a-f]{32}$/.test(r.device) || !/^[0-9a-f]{32}$/.test(r.boot) ||
        canonicalHostname(r.name) !== r.name) throw new Error('Invalid return context');
    returnReceipt = r; restartSent = true;
  } catch { $('restart-status').textContent = 'Invalid hostname return context. Open the Pico directly and verify its identity.'; }
}
function checkReturningDevice(device) {
  if (returnReceipt && returnReceipt.device !== device || consumerAttempt && consumerAttempt.device !== device)
    throw new Error('This is a different Pico. Do not enter its password. Return to the original Pico by IP or setup Wi-Fi.');
}
const presentationTitle = () => pageIdentity.readPublic(localIdentity,fetch);
function showContinuation(expected) {
  const link = $('hostname-continue');
  // A navigation carries bounded nonsecret expectations, never login credentials.
  const destination = new URL(globalThis.location.href);
  destination.username = ''; destination.password = '';
  destination.hostname = expected.name;
  destination.pathname = radio ? '/' : destination.pathname;
  destination.search = '';
  destination.hash = new URLSearchParams({'hostname-return':JSON.stringify(expected)}).toString();
  link.href = destination.href; link.hidden = false;
  link.textContent = 'Continue at ' + expected.name + ' (sign in again)';
}
async function readHostname(token = pageIdentity.request()) {
  const context = snapshot;
  let result;
  try { result = await api('hostname'); }
  catch (error) {
    if (error.code !== 'not_found') throw error;
    // Legacy engineering status lacks a full ID; obtain the existing member target.
    let member;
    try { member=(await readApplication()).data.target; }
    catch (e) { if(e.code !== 'not_found') throw e; pageIdentity.unavailable(token); return null; }
    if (!pageIdentity.current(token)) return null;
    if (member?.boot_id !== context?.job.boot_id || localIdentity && member.device_id !== localIdentity.device_id)
      throw new Error('Device context changed while reading identity.');
    checkReturningDevice(member.device_id);
    const name=context?.network.configured_hostname;
    if (canonicalHostname(name) === name) {
      if(!pageIdentity.observe(token,member,name,{authenticated:true})) throw new Error('Device identity changed.');
    }
    else pageIdentity.unavailable(token,member);
    return null;
  }
  if (!pageIdentity.current(token)) return null;
  const d = result.data;
  if (d.schema !== 'transmitter-hostname/1' || !/^[0-9a-f]{32}$/.test(d.target?.device_id) ||
      d.target.boot_id !== context?.job.boot_id ||
      radio && d.target.boot_id !== localIdentity?.boot_id ||
      localIdentity && d.target.device_id !== localIdentity.device_id ||
      ![d.saved,d.active,d.default].every(n=>canonicalHostname(n) === n) ||
      typeof d.writable !== 'boolean' || typeof d.pending_restart !== 'boolean' ||
      d.pending_restart !== (d.saved !== d.active) || typeof d.reason !== 'string')
    throw new Error('Hostname state could not be verified. Your draft is preserved.');
  checkReturningDevice(d.target.device_id);
  if (!pageIdentity.observe(token,d.target,d.active,{authenticated:true,pending:d.pending_restart,saved:d.saved}))
    throw new Error('Device identity changed while reading hostname.');

  if (hostnameState && (hostnameState.target.device_id !== d.target.device_id ||
      hostnameState.target.boot_id !== d.target.boot_id || hostnameState.saved !== d.saved)) cancelReconnect();
  hostnameState = d; hostnameState.revision = result.revision;
  if (hostnameUncertain) hostnameReviewReady = true;
  if (!hostnameDraft) $('hostname-input').value = d.saved;
  $('hostname-status').textContent = 'Active: ' + d.active + '. Saved: ' + d.saved + '. ' +
    (d.pending_restart ? 'Restart is required to use the new address. This page may disconnect; sign in again when the Pico returns.' :
      d.writable ? 'The saved address is active for this boot.' : d.reason === 'complete_station_setup_first' ?
        'Complete station setup before choosing a hostname.' : 'This engineering name requires matching replacement credentials.');
  if (d.pending_restart) showContinuation({device:d.target.device_id,boot:d.target.boot_id,name:d.saved});
  else { $('hostname-continue').hidden=true; $('hostname-continue').href=''; }
  if (returnReceipt) {
    if (d.target.boot_id === returnReceipt.boot) $('restart-status').textContent = 'The original boot is still running. Restart has not been observed.';
    else if (d.active !== returnReceipt.name || d.saved !== returnReceipt.name)
      $('restart-status').textContent = 'A new boot was observed, but the intended hostname is not applied. Check saved settings.';
    else {
      $('restart-status').textContent = 'Same Pico and new boot confirmed. Hostname applied: ' + d.active +
        '. Name discovery and browser reachability are reported separately above.';
      returnReceipt = null; restartSent = false;
      globalThis.history?.replaceState(null,'',globalThis.location.pathname + globalThis.location.search);
    }
  }
  return d;
}
function cancelReconnect() {
  ++reconnectEpoch;
  reconnectRunning = false;
  $('restart-cancel').hidden = true;
}
async function monitorRestart(expected) {
  cancelReconnect(); const token = reconnectEpoch; reconnectRunning = true;
  $('restart-cancel').hidden = false;
  const deadline = Date.now() + 90000;
  while (token === reconnectEpoch && Date.now() < deadline) {
    for (let remaining=2; remaining>0; --remaining) {
      $('restart-status').textContent = 'Restart requested or outcome unknown. Next connection check in ' + remaining +
        ' seconds. You can cancel checks or continue at the saved hostname. Sign in again to verify the applied name.';
      await new Promise(resolve=>setTimeout(resolve,1000));
      if (token !== reconnectEpoch) return;
      if (Date.now() >= deadline) break;
    }
    if (Date.now() >= deadline) break;
    try {
      const observed = radio ? await radio.identity(Math.max(1, Math.min(5000, deadline - Date.now()))) : (await api('hostname','GET',undefined,undefined,2000)).data.target;
      if (token !== reconnectEpoch) return;
      checkReturningDevice(observed.device_id);
      if (observed.boot_id !== expected.boot) {
        cancelReconnect();
        if (!radio) { await refresh(false); return; }
        $('restart-status').textContent = 'A new boot was observed. Sign in again to verify the same Pico and applied hostname. Your drafts remain in this tab.';
        return;
      }
    } catch (error) {
      if (returnReceipt && /different Pico/.test(error.message)) {
        cancelReconnect(); $('restart-status').textContent = error.message; return;
      }
    }
  }
  if (token === reconnectEpoch) {
    cancelReconnect();
    $('restart-status').textContent = 'Restart could not be confirmed within 90 seconds. Continue at the saved hostname, use the current IP, or join setup Wi-Fi at 192.168.4.1. A duplicate name or certificate error needs correction. No additional restart was sent.';
  }
}
$('hostname-form').onsubmit = event => { event.preventDefault(); return action(async()=> {
  cancelReconnect();
  const name = canonicalHostname($('hostname-input').value);
  if (!name) { $('hostname-input').setAttribute('aria-invalid','true');$('hostname-error').textContent='Use a full .local hostname with 1–63 letters, digits or hyphens; start and end with a letter or digit.';throw new Error($('hostname-error').textContent); }
  if (hostnameUncertain || !hostnameState?.writable) throw new Error('Read the saved hostname before another save.');
  const expected = hostnameState;
  hostnameUncertain = true;
  try {
    const result = await api('hostname','PUT',{schema:'transmitter-hostname/1',target:expected.target,hostname:name},expected.revision);
    if (result.data.generation === expected.generation) { hostnameUncertain=false; hostnameDraft=false; await readHostname(); return; }
    hostnameDraft = false;
    $('hostname-status').textContent = 'Hostname save accepted as ' + name + '. Active for this boot: ' + expected.active + '. Restart is required. Log in again to read the saved result before restarting.';
    // Profile generations invalidate sessions; never replay this mutation.
    if (!radio) { await readHostname(); hostnameDraft = false; }
    else { await radio.logout().catch(()=>{}); localAuthenticated = false; $('local-login').hidden=false; $('local-logout').hidden=true; controls(false); }
    showContinuation({device:expected.target.device_id,boot:expected.target.boot_id,name});
    if (radio) {
      pageIdentity.observe(pageIdentity.request(),expected.target,expected.active,{authenticated:true,pending:true,saved:name});
      markTitleStale();
      $('local-status').textContent = 'Signed out after saving. Log in to read the saved hostname.';
    }
  } catch (error) {
    $('hostname-status').textContent = error.serverResponse ? 'The Pico refused the hostname save: ' + error.message + '. Your draft is preserved. Refresh to read and review saved state.' : 'Hostname save result is unconfirmed. Your draft is preserved. Log in and refresh to read saved state before another save.';
    throw error;
  }
}); };
$('hostname-default').onclick = () => {
  cancelReconnect();
  if (hostnameState?.writable && confirm('Use the stable default hostname ' + hostnameState.default + '? Save hostname to confirm.')) {
    $('hostname-input').value=hostnameState.default; hostnameDraft=true;
    $('hostname-input').setAttribute('aria-invalid','false'); $('hostname-error').textContent='';
  }
};
$('hostname-input').addEventListener('input',()=>{hostnameDraft=true;$('hostname-input').setAttribute('aria-invalid','false');$('hostname-error').textContent='';cancelReconnect();});
$('restart-cancel').onclick = () => { cancelReconnect(); $('restart-status').textContent='Reconnect checks canceled. No additional restart was sent. Use the continuation link or refresh after signing in.'; };
for (const id of ['config','consumer-network-form','consumer-station-form','message-form','job'])
  $(id).addEventListener('input',cancelReconnect);
$('hostname-continue').onclick = event => {
  if ((dirty || consumerSetupDirty || hostnameDraft || $('message-text').value || $('job-file').files?.length) &&
      !confirm('Continue to the new address? Unsaved drafts stay in this tab if you cancel. Continuing will discard them; copy anything you need first.')) event.preventDefault();
  else cancelReconnect();
};
globalThis.addEventListener?.('pagehide',()=>{clearPasswords();cancelReconnect();});
parseReturnReceipt();

$('hostname-review').onclick = () => { if (online && hostnameReviewReady && !busy) { hostnameUncertain=false; hostnameReviewReady=false; controls(online); } };

globalThis.addEventListener?.('hashchange',()=>{
  cancelReconnect(); returnReceipt=null; parseReturnReceipt();
  const receipt = readSetupReceipt(globalThis.location?.hash);
  if (receipt) { consumerAttempt=receipt; requireReadback(); }
  if ((returnReceipt || consumerAttempt) && localIdentity) {
    try { checkReturningDevice(localIdentity.device_id); }
    catch (error) { clearPasswords(); controls(false); notice(error.message,true); }
  }
});
