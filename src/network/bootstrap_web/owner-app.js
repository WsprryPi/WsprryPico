import {x25519} from '@noble/curves/ed25519.js';
import {sha256} from '@noble/hashes/sha2.js';
import {available} from './crypto.js';
import {sealOwnerClaim} from './owner-claim.js';

const host = 'http://192.168.4.1';
const p256 = globalThis.WsprryPicoOwnerKey;
const sections = ['owner-ready', 'owner-tap', 'owner-settings', 'owner-checking',
  'owner-saved', 'owner-retry', 'owner-service', 'owner-safari'];
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
const keyName = (deviceId) => `WsprryPico/owner/v1/${deviceId}`;
let deviceId, status, started, pending, submitted, polling = false;

async function request(path, body) {
  const options = {cache: 'no-store', credentials: 'omit', redirect: 'error'};
  if (body) {
    options.method = 'POST';
    options.headers = {'Content-Type': 'application/json', 'X-WsprryPico-Owner': '1'};
    options.body = JSON.stringify(body);
  }
  const response = await fetch(host + path, options);
  if (!response.ok) throw new Error('Pico request failed');
  return response.json();
}

function ownerKey(device) {
  const name = keyName(device);
  let record = localStorage.getItem(name);
  let created = false;
  if (record === null) {
    const pair = p256.keygen();
    record = hex(pair.secretKey);
    pair.secretKey.fill(0);
    created = true;
    localStorage.setItem(name, record);
  }
  const saved = localStorage.getItem(name);
  if (saved !== record) throw new Error('owner key storage failed');
  const secret = fromHex(saved, 32);
  try {
    const publicKey = p256.getPublicKey(secret, false);
    if (publicKey.length !== 65 || publicKey[0] !== 4)
      throw new Error('invalid owner key');
    const challenge = random(32);
    const signature = p256.sign(challenge, secret);
    if (!p256.verify(signature, challenge, publicKey)) throw new Error('owner key self-test failed');
    return publicKey;
  } catch (error) {
    if (created) localStorage.removeItem(name);
    throw error;
  } finally {
    secret.fill(0);
  }
}

function clearAttempt() {
  pending?.secretKey?.fill(0);
  pending = started = undefined;
  submitted = undefined;
  $('owner-password').value = '';
  $('owner-ssid').value = '';
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

async function update() {
  if (polling) return;
  polling = true;
  try {
    const current = await request('/api/owner/v1/claim/status');
    if (!validStatus(current)) throw new Error('wrong Pico status');
    status = current;
    if (current.source === 'fault') {
      clearAttempt();
      show('owner-service');
      notice('The Pico could not verify its setup state.', true);
    } else if (current.slot_state === 'reconcile') {
      show('owner-checking');
      notice('The Pico is resolving the saved result. Reconnect after it restarts.');
    } else if (current.source === 'consumer') {
      const expected = submitted &&
        BigInt(current.generation) === submitted.expectedGeneration &&
        current.request_id_digest === submitted.requestDigest;
      show('owner-saved');
      notice(expected ? 'Setup was saved. Final owner readback is pending.' :
        'A consumer profile is saved on this Pico. Final owner readback is pending.');
      pending?.secretKey?.fill(0);
      pending = undefined;
    } else if (started && current.slot_id_digest === started.digest) {
      if (current.slot_state === 'granted' && !submitted) {
        show('owner-settings');
        notice('Pico confirmed. Enter your settings.');
      } else if (current.slot_state === 'terminal' && submitted) {
        clearAttempt();
        show('owner-retry');
        notice('The Pico did not save this setup. Start a fresh attempt.', true);
      }
    } else if (started && current.slot_id_digest &&
               current.slot_id_digest !== started.digest) {
      clearAttempt();
      show('owner-retry');
      notice('Another setup attempt is active. Wait, then try again.', true);
    } else if (started && submitted && current.slot_state === 'none') {
      clearAttempt();
      show('owner-retry');
      notice('This setup was not saved. Start a new attempt.', true);
    } else if (started && !submitted && current.slot_state === 'none') {
      clearAttempt();
      show('owner-retry');
      notice('The confirmation window ended. Start again.', true);
    } else if (!started && current.claim_available &&
               (current.source === 'network_only' || current.source === 'unprovisioned')) {
      show('owner-ready');
    }
  } catch {
    if (submitted) {
      show('owner-checking');
      notice('Checking the saved result. Reconnect to the Pico Wi-Fi and reopen this page if needed.');
    }
  } finally {
    polling = false;
    setTimeout(update, 1000);
  }
}

async function start() {
  if (!status || !status.claim_available ||
      !['network_only', 'unprovisioned'].includes(status.source)) return;
  clearAttempt();
  $('owner-start').disabled = true;
  try {
    const ownerPublic = ownerKey(deviceId);
    const pair = x25519.keygen();
    pending = {secretKey: pair.secretKey, ownerPublic,
      browserPublic: pair.publicKey, browserNonce: hex(random(16))};
    started = await request('/api/owner/v1/claim/start', {
      version: 1, device_id: deviceId, owner_public_key: b64u(ownerPublic),
      browser_public_key: b64u(pair.publicKey), browser_nonce: pending.browserNonce,
      profile_source: status.profile_source, generation: status.generation,
    });
    if (started.version !== 1 || started.device_id !== deviceId ||
        !/^[0-9a-f]{32}$/.test(started.boot_id) ||
        !/^[0-9a-f]{32}$/.test(started.slot_id) ||
        started.profile_source !== status.profile_source ||
        started.generation !== status.generation ||
        started.owner_key_sha256 !== hex(sha256(ownerPublic)) ||
        started.browser_public_key !== b64u(pair.publicKey) ||
        started.browser_nonce !== pending.browserNonce ||
        fromB64u(started.pico_public_key, 32).length !== 32 ||
        started.physical_window_ms !== 60000)
      throw new Error('start binding changed');
    started.digest = hex(sha256(fromHex(started.slot_id, 16)));
    show('owner-tap');
    notice('Press and release BOOTSEL on the identifying Pico.');
  } catch {
    clearAttempt();
    show('owner-retry');
    notice('Could not begin setup. Reconnect and try again.', true);
  } finally { $('owner-start').disabled = false; }
}

async function submit(event) {
  event.preventDefault();
  if (!pending || !started || !status || status.slot_state !== 'granted') return;
  $('owner-submit').disabled = true;
  try {
    const requestId = hex(random(16));
    const nonce = random(12);
    const fields = {
      origin: host, deviceId, bootId: started.boot_id, slotId: started.slot_id,
      ownerPublicKey: pending.ownerPublic, browserPublicKey: pending.browserPublic,
      picoPublicKey: fromB64u(started.pico_public_key, 32),
      browserNonce: pending.browserNonce, requestId,
      source: started.profile_source, generation: started.generation,
    };
    const settings = {ssid: $('owner-ssid').value, password: $('owner-password').value,
      callsign: $('owner-callsign').value.trim().toUpperCase(),
      locator: $('owner-locator').value.trim().toUpperCase(),
      powerDbm: Number($('owner-power').value)};
    const envelope = sealOwnerClaim(fields, pending.secretKey, nonce, settings);
    submitted = {requestDigest: hex(sha256(fromHex(requestId, 16))),
      expectedGeneration: BigInt(started.generation) + 1n};
    $('owner-password').value = '';
    $('owner-ssid').value = '';
    $('owner-callsign').value = '';
    $('owner-locator').value = '';
    show('owner-checking');
    notice('Trying your network and checking the saved result.');
    // Unknown response is reconciled by read-only status. Never replay submit.
    await request('/api/owner/v1/claim/submit', {
      version: 1, device_id: deviceId, boot_id: started.boot_id,
      slot_id: started.slot_id, request_id: requestId, aead_nonce: b64u(nonce),
      ciphertext: envelope.ciphertext, tag: envelope.tag,
    });
  } catch {
    if (submitted) {
      show('owner-checking');
      notice('Checking the saved result. Keep this page open.');
    } else {
      clearAttempt();
      show('owner-retry');
      notice('Could not encrypt these settings. Start again.', true);
    }
  } finally { $('owner-submit').disabled = false; }
}

async function boot() {
  $('owner-start').addEventListener('click', start);
  $('owner-retry-button').addEventListener('click', () => {
    clearAttempt(); show('owner-ready'); notice('Ready for another attempt.');
  });
  $('owner-form').addEventListener('submit', submit);
  if (location.origin !== host || !available() || !p256 ||
      typeof localStorage === 'undefined') {
    show('owner-safari');
    notice('Open this page in Safari to save this phone’s owner key.', true);
    return;
  }
  try {
    const publicStatus = await request('/api/owner/v1/public-status');
    if (!publicStatus || !/^[0-9a-f]{32}$/.test(publicStatus.device_id))
      throw new Error('invalid Pico identity');
    deviceId = publicStatus.device_id;
    if (!validStatus(publicStatus)) throw new Error('invalid Pico state');
    // A storage read/write failure must appear before the physical prompt.
    const probe = `WsprryPico/storage-check/${deviceId}`;
    localStorage.setItem(probe, 'ok');
    if (localStorage.getItem(probe) !== 'ok') throw new Error('storage unavailable');
    localStorage.removeItem(probe);
    status = publicStatus;
    $('device').textContent = 'Pico ' + deviceId.slice(-6);
    if (status.source === 'consumer') {
      show('owner-saved');
      notice('A consumer profile is saved on this Pico. Final owner readback is pending.');
    } else if (status.claim_available) {
      show('owner-ready');
      notice('Ready to set up this Pico.');
    } else {
      show('owner-service');
      notice('Setup is temporarily unavailable on this Pico.', true);
    }
    update();
  } catch {
    show('owner-safari');
    notice('Could not verify the Pico or Safari storage. Reconnect and reopen this page.', true);
  }
}
boot();
