import {available, begin, seal, slotDigest} from './crypto.js';

const names = ['ready', 'tap', 'credentials', 'checking', 'connected', 'saved', 'retry', 'safari'];
const $ = (id) => document.getElementById(id);
const show = (name) => {
  for (const section of names) $(section).hidden = section !== name;
};
const notice = (message, error = false) => {
  $('notice').textContent = message;
  $('notice').classList.toggle('error', error);
};
const host = 'http://192.168.4.1';
let deviceId, pending, started, sealed, polling = false, acknowledged = false;
const hexId = (value) => typeof value === 'string' && /^[0-9a-f]{32}$/.test(value);
const durableJoin = (status) => status.source === 'network_only' &&
  typeof status.generation === 'number' && Number.isSafeInteger(status.generation) &&
  status.generation >= 1 && status.join === 'connected' && status.address_ready === true;

async function json(path, body) {
  const options = {cache: 'no-store', credentials: 'omit', redirect: 'error'};
  if (body) {
    options.method = 'POST';
    options.headers = {'Content-Type': 'application/json', 'X-WsprryPico-Bootstrap': '1'};
    options.body = JSON.stringify(body);
  }
  const response = await fetch(host + path, options);
  if (!response.ok) throw new Error('Pico request failed');
  return response.json();
}

function clearAttempt() {
  pending?.secretKey?.fill(0);
  pending = started = sealed = undefined;
  acknowledged = false;
  $('password').value = '';
}

async function acknowledge() {
  if (acknowledged || !started || !sealed) return;
  acknowledged = true;
  try {
    await json('/api/bootstrap/v1/ack', {version: 1, device_id: deviceId,
      boot_id: started.boot_id, slot_id: started.slot_id,
      request_id: sealed.submit.request_id, ack_tag: sealed.ackTag});
  } catch { /* The AP may withdraw after success; the durable result is unchanged. */ }
  clearAttempt();
}

async function update() {
  if (polling) return;
  polling = true;
  try {
    const status = await json('/api/bootstrap/v1/status');
    if (durableJoin(status) &&
        (!sealed || status.request_id_digest === sealed.requestDigest ||
         status.request_id_digest === null)) {
      show('connected');
      notice('The Pico joined the network and saved its Wi-Fi settings.');
      // Let the result render before acknowledging an AP withdrawal.
      setTimeout(acknowledge, 250);
    } else if (status.source === 'network_only' &&
               typeof status.generation === 'number' && status.generation >= 1 &&
               (!sealed || status.request_id_digest === sealed.requestDigest ||
                status.request_id_digest === null)) {
      show('saved');
      notice('Wi-Fi settings were saved, but the station connection is down.');
    } else if (started && status.slot_id_digest === slotDigest(started.slot_id)) {
      if (status.slot_state === 'granted' && !sealed) {
        show('credentials');
        notice('Pico confirmed. Enter your network name and password.');
      } else if (status.slot_state === 'terminal' && sealed &&
                 status.request_id_digest === sealed.requestDigest &&
                 status.source === 'unprovisioned') {
        show('retry');
        notice('The connection was not saved. Start a new attempt.', true);
        clearAttempt();
      }
    } else if (started && !sealed && status.slot_id_digest &&
               status.slot_id_digest !== slotDigest(started.slot_id)) {
      show('retry');
      notice('Another setup attempt is active. Wait for it to end, then try again.', true);
      clearAttempt();
    } else if (started && !sealed && status.slot_state === 'none') {
      show('retry');
      notice('The confirmation window ended. Start a new attempt.', true);
      clearAttempt();
    } else if (!started && durableJoin(status)) {
      show('connected');
      notice('The Pico is connected to the network.');
    }
  } catch {
    if (sealed) {
      show('checking');
      notice('Checking connection. Reconnect to the Pico Wi-Fi if this page lost it.');
    }
  } finally {
    polling = false;
    setTimeout(update, 1000);
  }
}

async function start() {
  clearAttempt();
  $('start').disabled = true;
  try {
    pending = begin();
    started = await json('/api/bootstrap/v1/start', {version: 1,
      device_id: deviceId, browser_public_key: pending.browserPublicKey,
      request_nonce: pending.requestNonce});
    if (started.device_id !== deviceId || !hexId(started.boot_id) ||
        !hexId(started.slot_id) || typeof started.pico_public_key !== 'string' ||
        !/^[A-Za-z0-9_-]{43}$/.test(started.pico_public_key))
      throw new Error('invalid Pico start');
    show('tap');
    notice('Tap and release BOOTSEL on this Pico.');
  } catch {
    show('retry');
    notice('Could not start confirmation. Wait for the current attempt to end, then try again.', true);
    clearAttempt();
  } finally { $('start').disabled = false; }
}

async function submit(event) {
  event.preventDefault();
  if (!pending || !started) return;
  const ssid = $('ssid').value, password = $('password').value;
  if (!/^[\x20-\x7e]{1,32}$/.test(ssid) || !/^[\x20-\x7e]{8,63}$/.test(password)) {
    notice('Use a 1–32 character network name and an 8–63 character password with printable characters.', true);
    return;
  }
  $('submit').disabled = true;
  try {
    sealed = seal(pending, started, deviceId, ssid, password);
    $('password').value = '';
    show('checking');
    notice('Trying your network and checking the saved result.');
    // A lost response must be reconciled by status; never replay this POST.
    await json('/api/bootstrap/v1/submit', sealed.submit);
  } catch {
    if (!sealed) {
      clearAttempt();
      notice('This attempt could not encrypt the network details. Start again.', true);
      show('retry');
    } else {
      show('checking');
      notice('Checking connection. Keep this page open.');
    }
  } finally { $('submit').disabled = false; }
}

async function boot() {
  $('start').addEventListener('click', start);
  $('retry-button').addEventListener('click', () => { clearAttempt(); show('ready'); notice('Ready for a fresh attempt.'); });
  $('wifi-form').addEventListener('submit', submit);
  if (location.origin !== host || typeof fetch !== 'function' || !available()) {
    show('safari');
    notice('This browser cannot run encrypted Wi-Fi setup.', true);
    return;
  }
  try {
    const identity = await json('/local/v1/identity');
    if (!hexId(identity.device_id)) throw new Error('invalid identity');
    deviceId = identity.device_id;
    $('device').textContent = 'Pico ' + deviceId.slice(-6);
    show('ready');
    notice('Ready to connect this Pico.');
    update();
  } catch {
    show('retry');
    notice('Could not read the Pico identity. Reconnect to its Wi-Fi and reload.', true);
  }
}
boot();
