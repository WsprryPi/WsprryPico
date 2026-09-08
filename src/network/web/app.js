'use strict';
const $ = id => document.getElementById(id);
const session = crypto.randomUUID().replaceAll('-', '');
let revision = '', currentConfig = null, snapshot = null, capabilities = null, busy = false, online = false, dirty = false, expectedPause = false;
const notice = (text, error = false) => { $('notice').textContent = text; $('notice').classList.toggle('error', error); };
async function api(path, method = 'GET', body, etag) {
  const headers = {};
  if (method !== 'GET') Object.assign(headers, {'Content-Type':'application/json','X-WsprryPico-Request':'1'});
  if (etag) headers['If-Match'] = etag;
  const response = await fetch('/api/v1/' + path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(12000), cache:'no-store'});
  const data = await response.json();
  if (!response.ok || data.ok === false) { const error = new Error(data.error?.code || 'Request rejected'); error.code = data.error?.code; throw error; }
  return {data, revision:response.headers.get('ETag')};
}
function controls(connected) {
  online = connected;
  $('refresh').disabled = busy;
  $('reload-config').disabled = busy || !online;
  const idle = online && snapshot && !snapshot.job.owner_id && !snapshot.job.output_active && !['armed','running','failed'].includes(snapshot.job.state);
  $('settings').disabled = busy || !idle;
  $('wifi-off').disabled = busy || !idle || !snapshot.network.enabled;
  $('job-settings').disabled = busy || !online || !snapshot || !!snapshot.job.owner_id || snapshot.standalone.reboot_required;
  $('abort').disabled = busy || !online || snapshot?.job.owner_id !== session || !['loaded','armed','running'].includes(snapshot.job.state);
  $('release').disabled = busy || !online || snapshot?.job.owner_id !== session || snapshot.job.output_active || ['armed','running','failed'].includes(snapshot.job.state);
}
function fill(c) {
  currentConfig = c; dirty = false;
  const form = $('config').elements;
  for (const name of ['callsign','locator','power_dbm']) form[name].value = c?.station[name] ?? '';
  for (const name of ['ssid','ntp_ipv4']) form[name].value = c?.wifi[name] ?? '';
  form.password.value = '';
  form.enabled.checked = c?.enabled ?? false;
  form.schedules.value = (c?.schedules || [{period_s:120,phase_s:0}]).map(s => `${s.period_s} / ${s.phase_s}`).join('\n');
  form.expiry.value = c?.expires_utc_s ? new Date(c.expires_utc_s * 1000).toISOString().slice(0,19) : '';
}
async function refresh(loadConfig = false) {
  // The Pico accepts one TLS connection at a time: keep requests sequential.
  try {
    if (!capabilities) capabilities = (await api('capabilities')).data;
    snapshot = (await api('status')).data; expectedPause = false;
    const s = snapshot.standalone, n = snapshot.network;
    $('state').textContent = snapshot.job.state;
    $('job-result').textContent = snapshot.job.job_id ? `Job ${snapshot.job.job_id}: ${snapshot.job.state} · last observed` : 'No loaded job · last observed';
    $('output').textContent = snapshot.job.output_active ? 'Active' : 'Inactive';
    $('clock').textContent = `${s.clock_state} · ±${(Number(s.uncertainty_ns)/1e6).toFixed(2)} ms`;
    $('owner').textContent = snapshot.job.owner_id === session ? 'This browser' : snapshot.job.owner_id || 'Available';
    $('engine').textContent = s.engine;
    $('network').textContent = `${n.link_status === 3 ? 'Connected' : 'Disconnected'} · ${n.ipv4 || 'No address'}`;
    $('recovery').textContent = !capabilities.active_job_connections ? 'Network connections pause while RF jobs are armed or running. The job owner can abort over an established WTP connection; physical USB Console ABORT can also stop a job. ' : '';
    $('recovery').textContent += !s.storage_healthy ? 'Storage fault. Recover through USB Console.' : s.reboot_required ? 'Settings saved. Restart the device through USB Console to apply them.' : s.suspended ? 'Standalone operation is suspended.' : '';
    if (loadConfig) { const c = await api('config'); revision = c.revision; fill(c.data.config); }
    notice('Connected · Status updated ' + new Date().toLocaleTimeString()); controls(true);
  } catch (e) { if (expectedPause) notice('RF job accepted. New network connections pause while armed or running. Use USB Console ABORT to stop it, or refresh after completion.'); else notice('Connection unavailable: ' + e.message + '. Check Wi-Fi and the client certificate, then refresh.', true); controls(false); }
}
async function action(fn) {
  busy = true; controls(online);
  try { await fn(); } catch (e) { await refresh(); notice(e.code === 'revision_conflict' ? 'Saved settings changed. Your edits are preserved. Reload saved settings to discard edits and obtain the latest revision.' : e.message + '. Status has been checked; an interrupted request may already have completed.', true); }
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
  await refresh(); notice('Settings saved. Restart through USB Console to apply them.');
}); };
async function job(operation, body = {}) {
  const result = await api('jobs','POST',{session_id:session,request_id:crypto.randomUUID().replaceAll('-',''),operation,body});
  return result.data;
}
$('job').onsubmit = event => { event.preventDefault(); return action(async () => {
  const file = $('job-file').files[0];
  if (!file || file.size > 30000) throw new Error('Choose a job JSON file smaller than 30,000 bytes');
  const plan = JSON.parse(await file.text());
  const startMs = Date.parse($('start').value + 'Z');
  if (!Number.isFinite(startMs)) throw new Error('Choose a UTC start time');
  await job('HELLO',{versions:['WTP/1'],client_name:'WsprryPico browser',client_version:'1'});
  await job('CLAIM',{owner_id:session,lease_ms:30000});
  await job('LOAD',plan);
  await job('ARM',{job_id:plan.job_id,start_utc_ns:(BigInt(startMs)*1000000n).toString(),max_start_uncertainty_ns:capabilities.wtp.maximum_arm_uncertainty_ns});
  $('job-result').textContent = 'Job armed. Timing is now local to the Pico.';
  if (!capabilities.active_job_connections) {
    expectedPause = true; controls(false); $('state').textContent = 'Armed · last confirmed'; $('output').textContent = 'Not observed during network pause';
    notice('Job armed. New network connections pause during RF execution. Use USB Console ABORT to stop the job, or refresh after completion.');
  } else await refresh();
}); };
$('abort').onclick = () => action(async () => { await job('ABORT',{job_id:snapshot.job.job_id}); await refresh(); });
$('release').onclick = () => action(async () => { await job('RELEASE'); await refresh(); });
$('wifi-off').onclick = () => action(async () => {
  if (!confirm('Disconnect Wi-Fi? Reconnect using USB Console or restart the device.')) return;
  const n = await api('network'); await api('network','PUT',{enabled:false},n.revision);
  snapshot = null; controls(false); notice('Wi-Fi disconnected. Use USB Console or restart to reconnect.');
});
action(() => refresh(true));
