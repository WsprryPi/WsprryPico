import {available} from './crypto.js';
import {recoveryKey, recoverySeal} from './recovery-crypto.js';
const $ = (s) => document.getElementById(s);
const host = 'http://192.168.4.1';
let identity, phrase, submitting = false, uncertain = false;
const notice = (s) => { $('notice').textContent = s; };
async function request(path, body) {
  const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const options = {cache: 'no-store', credentials: 'omit', redirect: 'error', signal: controller.signal};
    if (body) Object.assign(options, {method: 'POST', headers: {'Content-Type': 'application/json',
      'X-WsprryPico-Bootstrap': '1'}, body: JSON.stringify(body)});
    const response = await fetch(host + path, options);
    if (!response.ok) throw new Error('Reset unavailable; ensure transmission is stopped and no setup is in progress.');
    return await response.json();
  } finally { clearTimeout(timeout); }
}
function choose(full) {
  if (!identity || submitting || uncertain) return;
  phrase = full ? 'erase' : 'reset provisioning';
  $('operation').textContent = full ? 'Confirm full erase' : 'Confirm provisioning reset';
  $('consequences').textContent = full ? 'This clears network credentials, certificates, engineering access, Bluetooth bonds, station details, schedules and time watermark.' : 'This clears network credentials, certificates, engineering access and Bluetooth bonds. Station details, schedules and time watermark are preserved.';
  $('phrase-label').textContent = `Type ${phrase} exactly to confirm`;
  $('phrase').value = ''; $('confirm-one').checked = false; $('confirm-two').checked = false;
  $('execute').disabled = true; $('actions').hidden = true; $('confirm').hidden = false;
  $('operation').focus();
}
function update() {
  $('execute').disabled = submitting || uncertain || !$('confirm-one').checked ||
    !$('confirm-two').checked || $('phrase').value !== phrase;
}
$('provisioning').addEventListener('click', () => choose(false));
$('full').addEventListener('click', () => choose(true));
for (const id of ['confirm-one', 'confirm-two', 'phrase']) $(id).addEventListener('input', update);
$('cancel').addEventListener('click', () => {
  if (submitting || uncertain) return;
  $('phrase').value = ''; phrase = undefined; $('confirm').hidden = true; $('actions').hidden = false;
  $('provisioning').focus();
});
$('reset-form').addEventListener('submit', async (event) => {
  event.preventDefault(); update(); if ($('execute').disabled) return;
  submitting = true; update(); $('cancel').disabled = true;
  let key, submitted = false;
  try {
    key = recoveryKey();
    const start = await request('/api/recovery/v1/start', {version: 1, device_id: identity.device_id,
      browser_public_key: key.public, request_nonce: key.nonce});
    if (start.boot_id !== identity.boot_id) throw new Error('The Pico restarted. Reload before confirming a reset.');
    const body = recoverySeal(key, start, identity.device_id, phrase);
    $('phrase').value = ''; submitted = true;
    const result = await request('/api/recovery/v1/submit', body);
    if (result.state !== 'reset_pending') throw new Error('Reset result could not be confirmed.');
    uncertain = true; $('confirm').hidden = true;
    notice('Reset accepted. The Pico will restart. Reconnect to its setup Wi-Fi after restart.');
  } catch (error) {
    uncertain = submitted;
    notice(submitted ? 'Reset result unknown. Do not repeat the request. Wait for restart, then reconnect and check the Pico.' : error.message);
  } finally { key?.secret.fill(0); submitting = false; update(); if (!uncertain) $('cancel').disabled = false; }
});
(async () => {
  try {
    if (!available()) throw new Error('Open this page in a browser that supports encrypted setup.');
    identity = await request('/api/recovery/v1/status');
    if (!/^[0-9a-f]{32}$/.test(identity.device_id) || !/^[0-9a-f]{32}$/.test(identity.boot_id) || identity.pending)
      throw new Error('Recovery is unavailable or already in progress.');
    $('device').textContent = `Pico ${identity.device_id}`;
    $('provisioning').disabled = false; $('full').disabled = false;
    notice('Select a recovery action. Transmission must remain stopped.');
  } catch (error) { notice(error.message); }
})();
