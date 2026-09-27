import assert from 'node:assert/strict';
import {x25519} from '@noble/curves/ed25519.js';
import {p256} from '@noble/curves/nist.js';
import {sha256} from '@noble/hashes/sha2.js';

const device = '00112233445566778899aabbccddeeff';
const boot = '102132435465768798a9bacbdcedfe0f';
const slot = '2031425364758697a8b9cadbecfd0e1f';
const hex = (bytes) => Buffer.from(bytes).toString('hex');
const digest = (value) => hex(sha256(Buffer.from(value, 'hex')));
const peer = x25519.keygen();
const elements = new Map();
for (const name of ['owner-ready', 'owner-arming', 'owner-tap', 'owner-settings', 'owner-checking',
                    'owner-saved', 'owner-retry', 'owner-service', 'owner-safari',
                    'notice', 'device', 'owner-start', 'owner-retry-button', 'owner-form',
                    'owner-ssid', 'owner-password', 'owner-callsign', 'owner-locator',
                    'owner-power', 'owner-submit']) {
  elements.set(name, {hidden: true, textContent: '', value: '', disabled: false,
    events: {}, classList: {toggle() {}}, addEventListener(event, handler) {
      this.events[event] = handler;
    }});
}
globalThis.document = {getElementById: (name) => elements.get(name)};
globalThis.location = {origin: 'http://192.168.4.1'};
const storage = new Map();
globalThis.localStorage = {
  getItem: (key) => storage.has(key) ? storage.get(key) : null,
  setItem: (key, value) => storage.set(key, value),
  removeItem: (key) => storage.delete(key),
};
const timers = [];
globalThis.setTimeout = (callback, delay) => { timers.push({callback, delay}); return timers.length; };
const runTimer = async (delay) => {
  const index = timers.findIndex((entry) => entry.delay === delay);
  assert.notEqual(index, -1);
  const [entry] = timers.splice(index, 1);
  await entry.callback();
};
const nextPoll = () => runTimer(1000);
let status = {version: 1, device_id: device, boot_id: boot, source: 'network_only',
  profile_source: 4, generation: '1', owner_exists: false, claim_available: true,
  address_ready: true, clock_ready: true, slot_state: 'none', slot_id_digest: null,
  request_id_digest: null};
let started, submitted;
globalThis.fetch = async (url, options = {}) => {
  const path = new URL(url).pathname;
  if (path === '/api/owner/v1/public-status' || path === '/api/owner/v1/claim/status')
    return {ok: true, json: async () => status};
  const body = JSON.parse(options.body);
  assert.equal(options.headers['X-WsprryPico-Owner'], '1');
  assert.equal(options.headers['Content-Type'], 'application/json');
  if (path === '/api/owner/v1/claim/start') {
    started = body;
    assert.equal(body.device_id, device);
    assert.equal(body.profile_source, 4);
    assert.equal(body.generation, '1');
    const owner = Buffer.from(body.owner_public_key, 'base64url');
    assert.equal(owner.length, 65);
    assert.equal(owner[0], 4);
    return {ok: true, json: async () => ({version: 1, device_id: device, boot_id: boot,
      slot_id: slot, profile_source: 4, generation: '1',
      owner_key_sha256: hex(sha256(owner)), browser_public_key: body.browser_public_key,
      browser_nonce: body.browser_nonce,
      pico_public_key: Buffer.from(peer.publicKey).toString('base64url'),
      physical_window_ms: 60000})};
  }
  if (path === '/api/owner/v1/claim/submit') {
    submitted = body;
    assert.equal(body.device_id, device);
    assert.equal(body.boot_id, boot);
    assert.equal(body.slot_id, slot);
    assert.equal(body.ssid, undefined);
    assert.equal(body.password, undefined);
    throw new Error('reply lost after complete request');
  }
  throw new Error('unexpected route ' + path);
};

await import('./owner-key.js');
await import('./owner-app.js');
await new Promise(setImmediate);
assert.equal(elements.get('owner-ready').hidden, false);
await elements.get('owner-start').events.click();
assert.equal(elements.get('owner-arming').hidden, false);
assert.equal(elements.get('owner-tap').hidden, true);
await runTimer(2000);
assert.equal(elements.get('owner-tap').hidden, false);
const savedKey = storage.get(`WsprryPico/owner/v1/${device}`);
assert.match(savedKey, /^[0-9a-f]{64}$/);
assert.deepEqual(Buffer.from(p256.getPublicKey(Buffer.from(savedKey, 'hex'), false)),
  Buffer.from(started.owner_public_key, 'base64url'));

status = {...status, slot_state: 'granted', slot_id_digest: digest(slot)};
await nextPoll();
assert.equal(elements.get('owner-settings').hidden, false);
elements.get('owner-ssid').value = 'LabNet';
elements.get('owner-password').value = 'test-only-password';
elements.get('owner-callsign').value = 'K1ABC';
elements.get('owner-locator').value = 'FN20';
elements.get('owner-power').value = '30';
await elements.get('owner-form').events.submit({preventDefault() {}});
assert.ok(submitted);
assert.equal(elements.get('owner-password').value, '');
assert.equal(elements.get('owner-checking').hidden, false);

status = {...status, slot_state: 'reconcile', request_id_digest: digest(submitted.request_id)};
await nextPoll();
assert.equal(elements.get('owner-checking').hidden, false);

status = {...status, source: 'consumer', profile_source: 5, generation: '2',
  owner_exists: true, claim_available: false, slot_state: 'terminal',
  request_id_digest: digest(submitted.request_id)};
await nextPoll();
assert.equal(elements.get('owner-saved').hidden, false);
assert.match(elements.get('notice').textContent, /Final owner readback is pending/);
assert.equal(storage.get(`WsprryPico/owner/v1/${device}`), savedKey);
status = {...status, source: 'fault', profile_source: 255};
await nextPoll();
assert.equal(elements.get('owner-service').hidden, false);
peer.secretKey.fill(0);
console.log('owner Safari claim flow and lost-submit reconciliation passed');
