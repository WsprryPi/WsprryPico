'use strict';
const $ = id => document.getElementById(id);
const session = crypto.randomUUID().replaceAll('-', '');
let activePlan = null, capabilitiesBoot = null;
let revision = '', currentConfig = null, snapshot = null, capabilities = null, busy = false, online = false, dirty = false, expectedPause = false, observedAt = '';
const notice = (text, error = false) => { $('notice').textContent = text; $('notice').classList.toggle('error', error); };
async function api(path, method = 'GET', body, etag, timeout = 30000) {
  const headers = {};
  if (method !== 'GET') Object.assign(headers, {'Content-Type':'application/json','X-WsprryPico-Request':'1'});
  if (etag) headers['If-Match'] = etag;
  const response = await fetch('/api/v1/' + path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(timeout), cache:'no-store'});
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    const code = data.error?.code;
    const explanation = {
      message_length_limit_32:'Use at most 32 characters, including spaces',
      unsupported_message_character:'The message contains a character outside the supported Morse alphabet',
      message_has_no_marks:'Include at least one Morse character',
      message_duration_overflow:'The timing or repetition is too large to calculate a finite job',
      invalid_message_timing_or_repetition:'Use positive dot, dash and gap lengths and a finite repeat count',
      resource_exhausted:'The Pico has insufficient free memory for this request. Check status before retrying'
    };
    let message = explanation[code] || code || 'Request rejected';
    if (code === 'message_duration_limit_exceeded') message = 'Calculated duration: ' + durationText(BigInt(data.calculated_duration_ns)) + '. Maximum: ' + durationText(BigInt(data.max_job_duration_ns));
    if (code === 'message_event_limit_exceeded') message = data.calculated_events + ' events exceed the device limit of ' + data.max_events + '. Reduce repetition or use a simpler message';
    const error = new Error(message); error.code = code; throw error;
  }
  return {data, revision:response.headers.get('ETag')};
}
function controls(connected) {
  online = connected;
  $('refresh').disabled = busy;
  $('reload-config').disabled = busy || !online;
  const idle = online && snapshot && snapshot.job.owner_id === null && snapshot.job.output_active === false && !['armed','running','failed'].includes(snapshot.job.state);
  $('settings').disabled = busy || !idle;
  $('restart').disabled = busy || !idle || !capabilities?.features?.restart;
  $('wifi-off').disabled = busy || !idle || !snapshot.network.enabled;
  $('job-settings').disabled = busy || !idle || snapshot.standalone.reboot_required;
  $('message-settings').disabled = $('job-settings').disabled || !capabilities?.message_jobs;
  $('abort').disabled = busy || !online || snapshot?.job.owner_id !== session || !['loaded','armed','running'].includes(snapshot.job.state);
  $('release').disabled = busy || !online || snapshot?.job.owner_id !== session || snapshot.job.output_active !== false || ['armed','running','failed'].includes(snapshot.job.state);
}
function fill(c) {
  currentConfig = c; dirty = false;
  const form = $('config').elements;
  for (const name of ['callsign','locator','power_dbm']) form[name].value = c?.station[name] ?? '';
  form.ssid.value = c?.wifi.ssid ?? '';
  form.ntp_ipv4.value = c?.wifi.ntp_ipv4 ?? 'pool.ntp.org';
  form.password.value = '';
  form.enabled.checked = c?.enabled ?? false;
  form.schedules.value = (c?.schedules || [{period_s:120,phase_s:0}]).map(s => `${s.period_s} / ${s.phase_s}`).join('\n');
  form.expiry.value = c?.expires_utc_s ? new Date(c.expires_utc_s * 1000).toISOString().slice(0,19) : '';
}
async function refresh(loadConfig = false) {
  // Keep this browser sequential so the other admitted client can progress.
  try {
    if (!capabilities) capabilities = (await api('capabilities')).data;
    snapshot = (await api('status')).data; expectedPause = false; observedAt = new Date().toLocaleTimeString();
    if (capabilitiesBoot && capabilitiesBoot !== snapshot.job.boot_id) capabilities = (await api('capabilities')).data;
    capabilitiesBoot = snapshot.job.boot_id;
    const s = snapshot.standalone, n = snapshot.network;
    $('state').textContent = snapshot.job.state;
    $('job-result').textContent = snapshot.job.job_id ? `Job ${snapshot.job.job_id}: ${snapshot.job.state} · observed ${observedAt}` : 'No loaded job · observed ' + observedAt;
    $('output').textContent = snapshot.job.output_active === true ? 'Active' : snapshot.job.output_active === false ? 'Inactive' : 'Unknown';
    $('clock').textContent = `${s.clock_state} · ±${(Number(s.uncertainty_ns)/1e6).toFixed(2)} ms`;
    $('owner').textContent = snapshot.job.owner_id === session ? 'This browser' : snapshot.job.owner_id || 'Available';
    $('engine').textContent = s.engine;
    $('network').textContent = `${n.link_status === 3 ? 'Connected' : 'Disconnected'} · ${n.ipv4 || 'No address'}`;
    $('hostname').textContent = n.configured_hostname || 'IP-only deployment';
    const discovery = {unconfigured:'Not configured',waiting_address:'Waiting for Wi-Fi address',probing:'Checking hostname',active:'Advertised',conflict:'Hostname conflict',failed:'Unavailable'};
    $('discovery').textContent = discovery[n.mdns_state] || 'Unavailable';
    $('discovery-help').textContent = n.mdns_state === 'conflict' ? 'Another device is using this hostname. Resolve the duplicate, then retry with USB Console WIFI OFF and WIFI ON while idle. The device will not rename itself.' : n.mdns_reason === 'device_identity_mismatch' ? 'Credentials belong to a different device. Rebuild with this device’s certificate bundle and recover through USB Console.' : n.mdns_state === 'failed' ? 'Name discovery failed. Check USB Console INFO; retry Wi-Fi while idle after resolving the reported cause.' : n.mdns_state === 'active' ? 'Use this hostname after DHCP address changes. An IP URL needs a matching certificate IP address.' : '';
    $('recovery').textContent = !capabilities.active_job_connections ? 'Network connections pause while RF jobs are armed or running. The job owner can abort over an established WTP connection; physical USB Console ABORT can also stop a job. ' : '';
    $('recovery').textContent += !s.storage_healthy ? 'Storage fault. Recover through USB Console.' : s.reboot_required ? 'Network settings saved. Use Restart device to apply them.' : s.suspended ? 'Standalone operation is suspended.' : '';
    if (loadConfig) { const c = await api('config'); revision = c.revision; fill(c.data.config); }
    updateProgress(); messagePreview();
    notice('Connected · Status updated ' + observedAt); controls(true);
  } catch (e) { snapshot = null; $('job-progress').textContent = 'Progress unavailable · status unknown'; $('state').textContent = 'Unknown · read failed'; $('output').textContent = 'Unknown'; for (const id of ['clock','owner','network','hostname','discovery']) $(id).textContent = 'Unknown'; $('discovery-help').textContent = ''; if (expectedPause) notice('RF job accepted. New network connections pause while armed or running. Use USB Console ABORT to stop it, or refresh after completion.'); else notice('Connection unavailable: ' + e.message + '. The connection limit may be reached. Check Wi-Fi and the client certificate, then refresh.', true); controls(false); }
}
async function action(fn) {
  busy = true; controls(online);
  try { await fn(); } catch (e) { await refresh(); notice(e.code === 'revision_conflict' ? 'Saved settings changed. Your edits are preserved. Reload saved settings to discard edits and obtain the latest revision.' : e.message + (online ? '. Status has been checked; an interrupted request may already have completed.' : '. Status remains unknown. Refresh to check whether the interrupted request completed.'), true); }
  finally { busy = false; controls(online); }
}
$('refresh').onclick = () => action(() => refresh());
$('config').oninput = () => { dirty = true; };
$('reload-config').onclick = () => action(async () => {
  if (dirty && !confirm('Discard your unsaved changes and reload saved settings?')) return;
  await refresh(true);
});
$('config').onsubmit = event => { event.preventDefault(); return action(async () => {
  const f = $('config').elements;
  const schedules = f.schedules.value.trim().split('\n').map(line => {
    if (!/^\s*\d+\s*\/\s*\d+\s*$/.test(line)) throw new Error('Use period / phase for each schedule');
    const [period_s,phase_s] = line.split('/').map(Number); return {period_s,phase_s};
  });
  const config = {version:1,enabled:f.enabled.checked,station:{callsign:f.callsign.value.trim().toUpperCase(),locator:f.locator.value.trim().toUpperCase(),power_dbm:Number(f.power_dbm.value)},wifi:{ssid:f.ssid.value,password:f.password.value || null,ntp_ipv4:f.ntp_ipv4.value.trim()},schedules,expires_utc_s:f.expiry.value ? Date.parse(f.expiry.value + 'Z') / 1000 : 0};
  const result = await api('config','PUT',config,revision); revision = result.revision; fill(result.data.config);
  await refresh(); notice(result.data.reboot_required ? 'Settings saved. Use Restart device to apply network changes.' : 'Settings saved and applied.');
}); };
async function job(operation, body = {}) {
  const result = await api('jobs','POST',{session_id:session,request_id:crypto.randomUUID().replaceAll('-',''),operation,body});
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
  plan.body.job_id = crypto.randomUUID().replaceAll('-','');
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

action(() => refresh(true));
