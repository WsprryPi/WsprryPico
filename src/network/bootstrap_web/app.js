import {available, begin, seal} from './crypto.js';

const names = ['credentials', 'checking', 'connected', 'saved', 'retry', 'unknown', 'service', 'browser'];
const $ = (id) => document.getElementById(id);
const show = (name) => {
  for (const section of names) $(section).hidden = section !== name;
};
const notice = (message, error = false) => {
  $('notice').textContent = message;
  $('notice').classList.toggle('error', error);
};
const host = 'http://192.168.4.1';
let deviceId, pending, started, sealed, expectedGeneration, currentGeneration;
let polling = false, acknowledging = false, completed = false, saving = false;
const hexId = (value) => typeof value === 'string' && /^[0-9a-f]{32}$/.test(value);
const hasSavedNetwork = (status) =>
  status.source === 'network_only' || status.source === 'consumer';
const durableJoin = (status) => hasSavedNetwork(status) &&
  Number.isSafeInteger(status.generation) && status.generation >= 1 &&
  status.join === 'connected' && status.address_ready === true;

async function json(path, body) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  const options = {cache: 'no-store', credentials: 'omit', redirect: 'error',
    signal: controller.signal};
  if (body) {
    options.method = 'POST';
    options.headers = {'Content-Type': 'application/json', 'X-WsprryPico-Bootstrap': '1'};
    options.body = JSON.stringify(body);
  }
  try {
    const response = await fetch(host + path, options);
    if (!response.ok) throw new Error('Pico request failed');
    return await response.json();
  } finally { clearTimeout(timeout); }
}

function setPasswordVisible(visible) {
  $('password').type = visible ? 'text' : 'password';
  const toggle = $('password-toggle');
  const label = visible ? 'Hide Wi-Fi password' : 'Show Wi-Fi password';
  toggle.setAttribute('aria-label', label);
  toggle.setAttribute('aria-pressed', String(visible));
  toggle.title = label;
  $('password-slash').hidden = !visible;
}

function clearAttempt() {
  pending?.secretKey?.fill(0);
  pending = started = sealed = expectedGeneration = undefined;
  $('password').value = '';
  setPasswordVisible(false);
}

async function acknowledge() {
  if (acknowledging || !started || !sealed) return;
  acknowledging = true;
  try {
    await json('/api/bootstrap/v1/ack', {version: 1, device_id: deviceId,
      boot_id: started.boot_id, slot_id: started.slot_id,
      request_id: sealed.submit.request_id, ack_tag: sealed.ackTag});
  } catch { /* A lost ACK does not undo the verified journal save. */ }
  clearAttempt();
  acknowledging = false;
}

async function update() {
  if (polling) return;
  polling = true;
  try {
    const status = await json('/api/bootstrap/v1/status');
    if (!Number.isSafeInteger(status.generation) || status.generation < 0)
      throw new Error('invalid generation');
    currentGeneration = status.generation;
    if (status.source === 'fault') {
      show('service');
      notice('The Pico could not verify its saved setup state.', true);
      clearAttempt();
    } else if (sealed) {
      const saved = hasSavedNetwork(status) &&
        status.generation === expectedGeneration &&
        status.request_id_digest === sealed.requestDigest;
      if (saved) {
        completed = true;
        show(durableJoin(status) ? 'connected' : 'saved');
        notice(durableJoin(status) ? 'Wi-Fi saved and connected.' :
          'Wi-Fi saved. The station connection is down.');
        setTimeout(acknowledge, 250);
      } else if (hasSavedNetwork(status) && status.generation >= expectedGeneration &&
                 (status.slot_state === 'terminal' || status.slot_state === 'none')) {
        clearAttempt();
        show('unknown');
        notice('The Pico has a saved network, but this page cannot verify this attempt.', true);
      } else if (status.slot_state === 'terminal') {
        clearAttempt();
        show('retry');
        notice('The Wi-Fi connection was not saved. Check the details and try again.', true);
      } else if (status.slot_state === 'none' && !saving) {
        clearAttempt();
        show('unknown');
        notice('This page cannot verify the save. Reconnect to the Pico Wi-Fi and check again.', true);
      } else {
        show('checking');
        notice('Trying your network and checking the saved result.');
      }
    } else if (completed) {
      if (hasSavedNetwork(status)) {
        show(durableJoin(status) ? 'connected' : 'saved');
        notice(durableJoin(status) ? 'Wi-Fi saved and connected.' :
          'Wi-Fi saved. The station connection is down.');
      }
    } else if (status.source === 'unprovisioned' || hasSavedNetwork(status)) {
      $('submit').disabled = false;
      if (!$('credentials').hidden) notice(durableJoin(status) ?
        'Connected to a network. Enter new details to change it.' :
        'Enter your Wi-Fi network and password.');
    } else {
      show('service');
      notice('Wi-Fi setup is unavailable on this Pico.', true);
    }
  } catch {
    if (sealed) {
      show('checking');
      notice('Checking the saved result. Reconnect to the Pico Wi-Fi if needed.');
    }
  } finally {
    polling = false;
    setTimeout(update, 1000);
  }
}

async function submit(event) {
  event.preventDefault();
  if (!deviceId || !Number.isSafeInteger(currentGeneration) ||
      currentGeneration >= Number.MAX_SAFE_INTEGER || saving) return;
  const ssid = $('ssid').value, password = $('password').value;
  if (!/^[\x20-\x7e]{1,32}$/.test(ssid) || !/^[\x20-\x7e]{8,63}$/.test(password)) {
    notice('Enter a 1–32 character network name and an 8–63 character Wi-Fi password.', true);
    return;
  }
  saving = true;
  $('submit').disabled = true;
  try {
    pending = begin();
    started = await json('/api/bootstrap/v1/start', {version: 1,
      device_id: deviceId, browser_public_key: pending.browserPublicKey,
      request_nonce: pending.requestNonce});
    if (started.device_id !== deviceId || !hexId(started.boot_id) ||
        !hexId(started.slot_id) || typeof started.pico_public_key !== 'string' ||
        !/^[A-Za-z0-9_-]{43}$/.test(started.pico_public_key))
      throw new Error('invalid Pico start');
    sealed = seal(pending, started, deviceId, ssid, password);
    expectedGeneration = currentGeneration + 1;
    $('password').value = '';
    setPasswordVisible(false);
    completed = false;
    show('checking');
    notice('Trying your network and checking the saved result.');
    // Reconcile a lost response by the exact request digest; never replay this POST.
    const result = await json('/api/bootstrap/v1/submit', sealed.submit);
    if (result.state === 'failed') {
      clearAttempt();
      show('retry');
      notice('The Wi-Fi connection was not saved. Check the details and try again.', true);
    }
  } catch {
    if (sealed) {
      show('checking');
      notice('Checking the saved result. Keep this page open.');
    } else {
      clearAttempt();
      show('retry');
      notice('Could not start Wi-Fi setup. Wait a moment, then try again.', true);
    }
  } finally {
    saving = false;
    $('submit').disabled = false;
  }
}

function change() {
  clearAttempt();
  completed = false;
  show('credentials');
  notice('Enter the Wi-Fi network this Pico should use.');
}

async function boot() {
  $('password-toggle').addEventListener('click', () =>
    setPasswordVisible($('password').type === 'password'));
  $('change-connected').addEventListener('click', change);
  $('change-saved').addEventListener('click', change);
  $('retry-button').addEventListener('click', change);
  $('unknown-button').addEventListener('click', () => location.reload());
  $('wifi-form').addEventListener('submit', submit);
  if (location.origin !== host || typeof fetch !== 'function' ||
      typeof AbortController !== 'function' || !available()) {
    show('browser');
    notice('This window cannot run encrypted setup. Open the Pico page in a regular browser.', true);
    return;
  }
  try {
    const identity = await json('/local/v1/identity');
    if (!hexId(identity.device_id)) throw new Error('invalid identity');
    deviceId = identity.device_id;
    $('device').textContent = 'Pico ' + deviceId.slice(-6);
    show('credentials');
    update();
  } catch {
    show('retry');
    notice('Could not read the Pico identity. Reconnect to its Wi-Fi and reload.', true);
  }
}
boot();
