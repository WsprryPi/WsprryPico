import {x25519} from '@noble/curves/ed25519.js';
import {sha256} from '@noble/hashes/sha2.js';
import {available} from './crypto.js';
import {claimPlaintext, sealOwnerClaim} from './owner-claim.js';

const host = 'http://192.168.4.1';
const p256 = globalThis.WsprryPicoOwnerKey;
const sections = ['owner-settings', 'owner-wifi-first', 'owner-checking', 'owner-saved',
  'owner-accepted', 'owner-unconfirmed', 'owner-retry', 'owner-service', 'owner-browser'];
const $ = (name) => document.getElementById(name);
const hex = (bytes) => [...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('');
const fromHex = (value, size) => {
  if (typeof value !== 'string' || !new RegExp(`^[0-9a-f]{${size * 2}}$`).test(value))
    throw new Error('invalid identifier');
  return Uint8Array.from({length: size}, (_, i) => parseInt(value.slice(2 * i, 2 * i + 2), 16));
};
const b64u = (bytes) => btoa(String.fromCharCode(...bytes))
  .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const fromB64u = (value, size) => {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_-]+$/.test(value))
    throw new Error('invalid encoded key');
  const bytes = Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/') +
    '='.repeat((4 - value.length % 4) % 4)), (c) => c.charCodeAt(0));
  if (bytes.length !== size || b64u(bytes) !== value) throw new Error('invalid encoded key');
  return bytes;
};
const random = (size) => {
  const bytes = new Uint8Array(size);
  crypto.getRandomValues(bytes);
  return bytes;
};
const show = (selected) => {
  for (const name of sections) $(name).hidden = name !== selected;
};
const notice = (message, error = false) => {
  $('notice').textContent = message;
  $('notice').classList.toggle('error', error);
};
let deviceId, status, submitted, polling = false, saving = false;
let complete = false, retryVisible = false;
let lastTimeHintMs;
let resultTimer, resultTimedOut = false;

function showPending() {
  if (resultTimedOut) {
    show('owner-unconfirmed');
    notice('This page could not confirm whether the station settings were saved.', true);
  } else if (submitted?.accepted) {
    show('owner-accepted');
    notice('The Pico received your station settings. Checking the saved result.');
  } else {
    show('owner-checking');
    notice('Checking the saved result. Keep this page open.');
  }
}

async function request(path, body, bootstrap = false, timeoutMs = 8000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const options = {cache: 'no-store', credentials: 'omit', redirect: 'error',
    signal: controller.signal};
  if (body) {
    options.method = 'POST';
    options.headers = {'Content-Type': 'application/json',
      [bootstrap ? 'X-WsprryPico-Bootstrap' : 'X-WsprryPico-Owner']: '1'};
    options.body = JSON.stringify(body);
  }
  try {
    const response = await fetch(host + path, options);
    if (!response.ok) throw new Error('Pico request failed');
    return await response.json();
  } finally { clearTimeout(timeout); }
}

async function hintTime() {
  const now = Date.now();
  if (!deviceId || !Number.isSafeInteger(now) ||
      (lastTimeHintMs !== undefined && now >= lastTimeHintMs &&
       now - lastTimeHintMs < 30000)) return;
  lastTimeHintMs = now;
  try {
    const challenge = await request('/api/bootstrap/v1/time', undefined, true, 2000);
    if (!/^[1-9][0-9]*$/.test(challenge.challenge_ns))
      throw new Error('invalid time challenge');
    const result = await request('/api/bootstrap/v1/time', {version: 1, device_id: deviceId,
      utc_ms: String(Date.now()), challenge_ns: challenge.challenge_ns}, true, 2000);
    if (result.state !== 'accepted') throw new Error('time challenge expired');
  } catch { lastTimeHintMs = now - 25000; /* Retry a lost hint in five seconds. */ }
}

function settings() {
  return {ssid: '', password: '',
    callsign: $('owner-callsign').value.trim().toUpperCase(),
    locator: $('owner-locator').value.trim().toUpperCase(),
    powerDbm: Number($('owner-power').value)};
}

function validStatus(value) {
  if (!value || value.version !== 1 || value.device_id !== deviceId ||
      !/^[0-9a-f]{32}$/.test(value.boot_id) ||
      typeof value.generation !== 'string' ||
      !/^(0|[1-9][0-9]*)$/.test(value.generation)) return false;
  const generation = BigInt(value.generation);
  if (generation > 0xffffffffffffffffn) return false;
  const expectedSource = value.source === 'unprovisioned'
    ? (generation === 0n ? 0 : 2)
    : value.source === 'network_only' ? 4
    : value.source === 'consumer' ? 5 : 255;
  return (value.source === 'unprovisioned' || value.source === 'network_only' ||
      value.source === 'consumer' || value.source === 'fault') &&
    value.profile_source === expectedSource &&
    (value.source === 'unprovisioned' || value.source === 'fault' || generation > 0n);
}

function clearTransaction() {
  clearTimeout(resultTimer);
  resultTimedOut = false;
  submitted = undefined;
}

async function update() {
  if (polling) return;
  polling = true;
  const pending = submitted;
  try {
    const current = await request('/api/owner/v1/claim/status');
    if (!validStatus(current)) throw new Error('wrong Pico status');
    // A poll issued before this POST cannot decide the new attempt's outcome.
    if (saving || pending !== submitted) return;
    status = current;
    if (complete || retryVisible) return;
    if (current.source === 'fault') {
      clearTransaction();
      complete = true;
      show('owner-service');
      notice('The Pico could not verify its setup state.', true);
    } else if (submitted) {
      const saved = current.source === 'consumer' && current.slot_state !== 'reconcile' &&
        BigInt(current.generation) === submitted.expectedGeneration &&
        current.request_id_digest === submitted.requestDigest;
      if (saved) {
        clearTransaction();
        complete = true;
        show('owner-saved');
        notice('The Pico saved your station settings.');
      } else if (current.source === 'consumer' &&
                 BigInt(current.generation) >= submitted.expectedGeneration &&
                 current.request_id_digest !== submitted.requestDigest) {
        clearTransaction();
        complete = true;
        show('owner-service');
        notice('The saved result changed. Reload this page to check the Pico.', true);
      } else if (current.slot_state === 'terminal' ||
                 (current.slot_state === 'none' &&
                  BigInt(current.generation) < submitted.expectedGeneration)) {
        clearTransaction();
        retryVisible = true;
        show('owner-retry');
        notice('Setup was not saved. Check your settings and try again.', true);
      } else {
        showPending();
      }
    } else if (current.source === 'unprovisioned') {
      $('owner-submit').disabled = true;
      $('owner-identify').disabled = true;
      show('owner-wifi-first');
      notice('Connect the Pico to Wi-Fi before setting station details.');
    } else if (current.claim_available) {
      $('owner-submit').disabled = false;
      $('owner-identify').disabled = false;
      if (!$('owner-settings').hidden) return;
      show('owner-settings');
      notice(current.source === 'consumer' ?
        'Ready to update this Pico’s station details.' :
        'Ready to set this Pico’s station details.');
    } else {
      $('owner-submit').disabled = true;
      $('owner-identify').disabled = true;
      if (current.slot_state !== 'none') {
        retryVisible = true;
        show('owner-retry');
        notice('Another setup is in progress. Wait a moment and try again.', true);
      } else {
        show('owner-service');
        notice('Setup is temporarily unavailable on this Pico.', true);
      }
    }
  } catch {
    if (submitted && !saving && pending === submitted) showPending();
  } finally {
    if (!saving && !submitted) await hintTime();
    polling = false;
    setTimeout(update, 1000);
  }
}

async function identify() {
  if (!status?.claim_available || saving || submitted || complete) return;
  $('owner-identify').disabled = true;
  try {
    const result = await request('/api/owner/v1/identify', {version: 1,
      device_id: deviceId, boot_id: status.boot_id, request_id: hex(random(16))});
    if (result.version !== 1 || result.device_id !== deviceId ||
        result.pattern !== 'three_short_flashes') throw new Error('wrong Pico');
    notice('Watch for three quick LED flashes, repeated for about 10 seconds.');
  } catch {
    notice('Could not blink the LED. You can still save setup.', true);
  } finally {
    $('owner-identify').disabled = Boolean(saving || submitted || complete || retryVisible || !status?.claim_available);
  }
}

async function submit(event) {
  event.preventDefault();
  if (!status?.claim_available || status.source === 'unprovisioned' || saving ||
      submitted || complete || retryVisible) return;
  const proposed = settings();
  try { claimPlaintext(proposed).fill(0); }
  catch {
    notice('Check the callsign, four-character grid and transmit power.', true);
    return;
  }
  saving = true;
  $('owner-submit').disabled = true;
  $('owner-identify').disabled = true;
  let browserSecret;
  try {
    // The P-256 point binds this one exchange and is never stored as an owner.
    const transaction = p256.keygen();
    const transactionPublic = p256.getPublicKey(transaction.secretKey, false);
    transaction.secretKey.fill(0);
    const pair = x25519.keygen();
    browserSecret = pair.secretKey;
    const browserNonce = hex(random(16));
    show('owner-checking');
    notice('Saving station settings.');
    const started = await request('/api/owner/v1/claim/start', {
      version: 1, device_id: deviceId, owner_public_key: b64u(transactionPublic),
      browser_public_key: b64u(pair.publicKey), browser_nonce: browserNonce,
      profile_source: status.profile_source, generation: status.generation,
    });
    if (started.version !== 1 || started.device_id !== deviceId ||
        !/^[0-9a-f]{32}$/.test(started.boot_id) ||
        !/^[0-9a-f]{32}$/.test(started.slot_id) ||
        started.profile_source !== status.profile_source ||
        started.generation !== status.generation ||
        started.owner_key_sha256 !== hex(sha256(transactionPublic)) ||
        started.browser_public_key !== b64u(pair.publicKey) ||
        started.browser_nonce !== browserNonce ||
        fromB64u(started.pico_public_key, 32).length !== 32)
      throw new Error('start binding changed');
    const requestId = hex(random(16));
    const nonce = random(12);
    const fields = {
      origin: host, deviceId, bootId: started.boot_id, slotId: started.slot_id,
      ownerPublicKey: transactionPublic, browserPublicKey: pair.publicKey,
      picoPublicKey: fromB64u(started.pico_public_key, 32),
      browserNonce, requestId, source: started.profile_source,
      generation: started.generation,
    };
    const envelope = sealOwnerClaim(fields, browserSecret, nonce, proposed);
    browserSecret = undefined;
    submitted = {requestDigest: hex(sha256(fromHex(requestId, 16))),
      expectedGeneration: BigInt(started.generation) + 1n, accepted: false};
    resultTimedOut = false;
    // 90 s station trial + 60 s lost-result restart, with room for fetches.
    resultTimer = setTimeout(() => {
      resultTimedOut = true;
      if (submitted) showPending();
    }, 180000);
    // The result may be lost when station association changes; reconcile by
    // status without replaying this one encrypted POST.
    const result = await request('/api/owner/v1/claim/submit', {
      version: 1, device_id: deviceId, boot_id: started.boot_id,
      slot_id: started.slot_id, request_id: requestId, aead_nonce: b64u(nonce),
      ciphertext: envelope.ciphertext, tag: envelope.tag,
    });
    if (result.version === 1 && result.state === 'failed') {
      clearTransaction();
      retryVisible = true;
      show('owner-retry');
      notice('The Pico rejected these settings. Check them and try again.', true);
    } else if (result.version === 1 && result.state === 'checking' &&
               result.request_id_digest === submitted.requestDigest) {
      submitted.accepted = true;
      showPending();
    } else {
      throw new Error('unconfirmed submit reply');
    }
  } catch {
    if (submitted) {
      showPending();
    } else {
      retryVisible = true;
      show('owner-retry');
      notice('Could not start setup. Wait a moment, then try again.', true);
    }
  } finally {
    browserSecret?.fill(0);
    saving = false;
    $('owner-submit').disabled = Boolean(submitted || complete || retryVisible || !status?.claim_available);
    $('owner-identify').disabled = Boolean(submitted || complete || retryVisible || !status?.claim_available);
  }
}

async function boot() {
  $('owner-identify').addEventListener('click', identify);
  $('owner-retry-button').addEventListener('click', () => {
    clearTransaction();
    retryVisible = false;
    show('owner-settings');
    notice('Check your settings, then save again.');
  });
  $('owner-form').addEventListener('submit', submit);
  if (location.origin !== host || !available() || !p256 ||
      typeof AbortController !== 'function') {
    show('owner-browser');
    notice('This window cannot run encrypted setup. Open the Pico page in a regular browser.', true);
    return;
  }
  try {
    // The document's last TCP acknowledgement may still occupy the AP slot.
    // Retry this initial read only; station submissions are never replayed.
    let publicStatus;
    for (let attempt = 0; attempt < 3; attempt++) {
      try { publicStatus = await request('/api/owner/v1/public-status'); break; }
      catch (error) {
        if (attempt === 2) throw error;
        await new Promise((resolve) => setTimeout(resolve, 250));
      }
    }
    if (!publicStatus || !/^[0-9a-f]{32}$/.test(publicStatus.device_id))
      throw new Error('invalid Pico identity');
    deviceId = publicStatus.device_id;
    if (!validStatus(publicStatus)) throw new Error('invalid Pico state');
    status = publicStatus;
    $('device').textContent = 'Pico ' + deviceId.slice(-6);
    if (status.source === 'unprovisioned') {
      show('owner-wifi-first');
      notice('Connect the Pico to Wi-Fi before setting station details.');
    } else if (status.claim_available) {
      $('owner-submit').disabled = false;
      $('owner-identify').disabled = false;
      show('owner-settings');
      notice(status.source === 'consumer' ?
        'Ready to update this Pico’s station details.' :
        'Ready to set this Pico’s station details.');
    } else {
      show('owner-service');
      notice('Setup is temporarily unavailable on this Pico.', true);
    }
    update();
  } catch {
    notice('Could not verify this Pico. Reconnect to its Wi-Fi and reload.', true);
  }
}
boot();
