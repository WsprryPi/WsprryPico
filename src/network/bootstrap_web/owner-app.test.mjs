import assert from 'node:assert/strict';
import {x25519} from '@noble/curves/ed25519.js';
import {sha256} from '@noble/hashes/sha2.js';

const device = '00112233445566778899aabbccddeeff';
const boot = '102132435465768798a9bacbdcedfe0f';
const slot = '2031425364758697a8b9cadbecfd0e1f';
const hex = (bytes) => Buffer.from(bytes).toString('hex');
const digest = (value) => hex(sha256(Buffer.from(value, 'hex')));
const peer = x25519.keygen();
const elements = new Map();
for (const name of ['owner-settings', 'owner-wifi-first', 'owner-checking', 'owner-saved',
                    'owner-retry', 'owner-service', 'owner-browser', 'notice', 'device',
                    'owner-identify', 'owner-retry-button', 'owner-form',
                    'owner-callsign', 'owner-locator',
                    'owner-power', 'owner-submit']) {
  elements.set(name, {hidden: true, textContent: '', value: '', type: 'password', disabled: false,
    attributes: {}, setAttribute(key, value) { this.attributes[key] = value; },
    events: {}, classList: {toggle() {}}, addEventListener(event, handler) {
      this.events[event] = handler;
    }});
}
elements.get('owner-settings').hidden = true; // The form waits for source status.
elements.get('owner-submit').disabled = true;
elements.get('owner-identify').disabled = true;
globalThis.document = {getElementById: (name) => elements.get(name)};
globalThis.location = {origin: 'http://192.168.4.1'};
Object.defineProperty(globalThis, 'localStorage', {
  configurable: true, get() { throw new Error('setup must not use phone storage'); },
});
const timers = new Map();
let nextTimer = 0;
globalThis.setTimeout = (callback, delay) => {
  const id = ++nextTimer;
  timers.set(id, {callback, delay});
  return id;
};
globalThis.clearTimeout = (id) => timers.delete(id);
const runTimer = async (delay) => {
  const found = [...timers].find(([, value]) => value.delay === delay);
  assert.ok(found, `missing ${delay} ms timer`);
  timers.delete(found[0]);
  await found[1].callback();
};
let status = {version: 1, device_id: device, boot_id: boot, source: 'network_only',
  profile_source: 4, generation: '1', owner_exists: false, claim_available: true,
  address_ready: true, clock_ready: true, slot_state: 'none', slot_id_digest: null,
  request_id_digest: null};
let start, submitted, identify, hangNextStatus = false;
let now = 1_800_000_000_000;
Date.now = () => now;
const timeHints = [];
globalThis.fetch = async (url, options = {}) => {
  const path = new URL(url).pathname;
  if (path === '/api/owner/v1/public-status') return {ok: true, json: async () => status};
  if (path === '/api/owner/v1/claim/status') {
    if (hangNextStatus) {
      hangNextStatus = false;
      return new Promise((resolve, reject) => {
        options.signal.addEventListener('abort', () => reject(new Error('timeout')), {once: true});
      });
    }
    return {ok: true, json: async () => status};
  }
  const body = JSON.parse(options.body);
  if (path === '/api/bootstrap/v1/time') {
    assert.equal(options.headers['X-WsprryPico-Bootstrap'], '1');
    assert.equal(body.device_id, device);
    timeHints.push(body.utc_ms);
    return {ok: true, json: async () => ({version: 1, state: 'accepted'})};
  }
  assert.equal(options.headers['X-WsprryPico-Owner'], '1');
  assert.equal(options.headers['Content-Type'], 'application/json');
  if (path === '/api/owner/v1/identify') {
    identify = body;
    return {ok: true, json: async () => ({version: 1, device_id: device,
      pattern: 'three_short_flashes', duration_ms: 10000})};
  }
  if (path === '/api/owner/v1/claim/start') {
    start = body;
    assert.equal(body.device_id, device);
    assert.equal(body.profile_source, status.profile_source);
    assert.equal(body.generation, status.generation);
    const transaction = Buffer.from(body.owner_public_key, 'base64url');
    assert.equal(transaction.length, 65);
    assert.equal(transaction[0], 4);
    return {ok: true, json: async () => ({version: 1, device_id: device, boot_id: boot,
      slot_id: slot, profile_source: body.profile_source, generation: body.generation,
      owner_key_sha256: hex(sha256(transaction)), browser_public_key: body.browser_public_key,
      browser_nonce: body.browser_nonce,
      pico_public_key: Buffer.from(peer.publicKey).toString('base64url')})};
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
assert.equal(elements.get('owner-settings').hidden, false);
assert.equal(elements.get('owner-submit').disabled, false);
assert.deepEqual(timeHints, [String(now)]);
await runTimer(1000);
assert.equal(timeHints.length, 1);
now += 30000;
await runTimer(1000);
assert.deepEqual(timeHints, [String(1_800_000_000_000), String(now)]);
await elements.get('owner-identify').events.click();
assert.equal(identify.device_id, device);
assert.equal(identify.boot_id, boot);
assert.match(elements.get('notice').textContent, /three quick LED flashes/);

const fill = () => {
  elements.get('owner-callsign').value = 'K1ABC';
  elements.get('owner-locator').value = 'FN20';
  elements.get('owner-power').value = '30';
};
fill();
await elements.get('owner-form').events.submit({preventDefault() {}});
assert.ok(start && submitted, elements.get('notice').textContent);
assert.equal(elements.get('owner-checking').hidden, false);
const firstTransaction = start.owner_public_key;
status = {...status, source: 'consumer', profile_source: 5, generation: '2',
  owner_exists: false, claim_available: true, slot_state: 'terminal',
  request_id_digest: digest(submitted.request_id)};
await runTimer(1000);
assert.equal(elements.get('owner-saved').hidden, false);
assert.match(elements.get('notice').textContent, /saved your station settings/);
await runTimer(1000);
assert.equal(elements.get('owner-saved').hidden, false); // Success stays visible.

// A fresh page on another phone can use the same portal without a saved key.
timers.clear();
for (const element of elements.values()) element.hidden = true;
elements.get('owner-settings').hidden = false;
status = {...status, slot_state: 'none'}; // The second phone opens after restart.
start = submitted = undefined;
await import('./owner-app.js?second-phone');
await new Promise(setImmediate);
assert.equal(elements.get('owner-settings').hidden, false);
assert.equal(elements.get('owner-submit').disabled, false);
fill();
await elements.get('owner-form').events.submit({preventDefault() {}});
assert.equal(start.profile_source, 5);
assert.equal(start.generation, '2');
assert.notEqual(start.owner_public_key, firstTransaction);
assert.ok(submitted);
status = {...status, generation: '3', request_id_digest: digest(submitted.request_id)};
await runTimer(1000);
assert.equal(elements.get('owner-saved').hidden, false);

// A stalled AP status fetch is aborted, allowing later polls to resume.
hangNextStatus = true;
const stalledPoll = runTimer(1000);
await new Promise(setImmediate);
await runTimer(8000);
await stalledPoll;
assert.ok([...timers.values()].some((timer) => timer.delay === 1000));
peer.secretKey.fill(0);
console.log('separate station setup, LED, another-phone update and polling recovery passed');
