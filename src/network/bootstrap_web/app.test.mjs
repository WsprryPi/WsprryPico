import assert from 'node:assert/strict';
import {slotDigest} from './crypto.js';

const device = '00112233445566778899aabbccddeeff';
const boot = '102132435465768798a9bacbdcedfe0f';
const slot = '2031425364758697a8b9cadbecfd0e1f';
const picoPublic = '3p7bfXt9wbTTW2HC7OQ1Nz-DQ8hbeGdNrfx-FG-IK08';
const elements = new Map();
for (const name of ['credentials', 'checking', 'connected', 'saved', 'retry', 'unknown', 'service',
                    'browser', 'notice', 'device', 'wifi-form', 'ssid', 'password',
                    'password-toggle', 'password-slash', 'submit', 'change-connected',
                    'change-saved', 'retry-button', 'unknown-button']) {
  elements.set(name, {hidden: true, textContent: '', value: '', type: 'password', disabled: false,
    attributes: {}, setAttribute(key, value) { this.attributes[key] = value; },
    events: {}, classList: {toggle() {}}, addEventListener(event, handler) {
      this.events[event] = handler;
    }});
}
elements.get('credentials').hidden = false;
elements.get('submit').disabled = true;
globalThis.document = {getElementById: (name) => elements.get(name)};
globalThis.location = {origin: 'http://192.168.4.1', reload() {}};
const timers = [];
globalThis.setTimeout = (callback, delay) => { timers.push({callback, delay}); return timers.length; };
globalThis.clearTimeout = (id) => { timers[id - 1].cleared = true; };
let status = {source: 'unprovisioned', generation: 0, slot_state: 'none',
  join: 'idle', address_ready: false, request_id_digest: null};
let submitted, ack, starts = 0;
globalThis.fetch = async (url, options = {}) => {
  const path = new URL(url).pathname;
  if (path === '/local/v1/identity') return {ok: true, json: async () => ({device_id: device})};
  if (path === '/api/bootstrap/v1/status') return {ok: true, json: async () => status};
  const body = JSON.parse(options.body);
  if (path === '/api/bootstrap/v1/start') {
    starts++;
    assert.equal(body.device_id, device);
    assert.equal(body.browser_public_key.length, 43);
    return {ok: true, json: async () => ({device_id: device, boot_id: boot,
      slot_id: slot, pico_public_key: picoPublic})};
  }
  if (path === '/api/bootstrap/v1/submit') {
    submitted = body;
    assert.equal(body.device_id, device);
    assert.equal(body.ssid, undefined);
    assert.equal(body.password, undefined);
    assert.equal(options.headers['X-WsprryPico-Bootstrap'], '1');
    return {ok: true, json: async () => ({state: 'checking', generation: 0})};
  }
  if (path === '/api/bootstrap/v1/ack') {
    ack = body;
    return {ok: true, json: async () => ({state: 'accepted'})};
  }
  throw new Error('unexpected path ' + path);
};
const poll = async () => {
  const timer = timers.findLast((item) => item.delay === 1000);
  assert.ok(timer);
  await timer.callback();
};

await import('./app.js');
await new Promise(setImmediate);
assert.equal(elements.get('credentials').hidden, false);
assert.equal(elements.get('submit').disabled, false);
assert.equal(starts, 0); // Opening the page does not consume a setup slot.

elements.get('ssid').value = 'LabNet';
elements.get('password').value = 'test-only-password';
await elements.get('password-toggle').events.click();
assert.equal(elements.get('password').type, 'text');
assert.equal(elements.get('password-toggle').attributes['aria-label'], 'Hide Wi-Fi password');
await elements.get('wifi-form').events.submit({preventDefault() {}});
assert.equal(starts, 1);
assert.ok(submitted);
assert.equal(elements.get('password').value, '');
assert.equal(elements.get('password').type, 'password');
assert.equal(elements.get('checking').hidden, false);

status = {...status, source: 'network_only', generation: 1, slot_state: 'terminal',
  join: 'connected', address_ready: true,
  request_id_digest: slotDigest(submitted.request_id)};
await poll();
assert.equal(elements.get('connected').hidden, false);
await timers.findLast((item) => item.delay === 250).callback();
assert.equal(ack.request_id, submitted.request_id);
assert.equal(ack.ack_tag.length, 43);

elements.get('change-connected').events.click();
assert.equal(elements.get('credentials').hidden, false);
elements.get('ssid').value = 'NewNet';
elements.get('password').value = 'new-test-password';
await elements.get('wifi-form').events.submit({preventDefault() {}});
assert.equal(starts, 2);
status = {...status, generation: 2, slot_state: 'trial',
  request_id_digest: '0'.repeat(64)};
await poll();
assert.equal(elements.get('connected').hidden, true); // Foreign result is not our save.
status = {...status, slot_state: 'terminal'};
await poll();
assert.equal(elements.get('unknown').hidden, false); // Never call a foreign commit ours.
elements.get('change-connected').events.click();
elements.get('ssid').value = 'ThirdNet';
elements.get('password').value = 'third-test-password';
await elements.get('wifi-form').events.submit({preventDefault() {}});
assert.equal(starts, 3);
status = {...status, generation: 3, slot_state: 'terminal', join: 'disconnected', address_ready: false,
  request_id_digest: slotDigest(submitted.request_id)};
await poll();
assert.equal(elements.get('saved').hidden, false);

elements.get('change-saved').events.click();
elements.get('ssid').value = 'ThirdNet';
elements.get('password').value = 'third-test-password';
await elements.get('wifi-form').events.submit({preventDefault() {}});
status = {...status, slot_state: 'none', request_id_digest: null};
await poll();
assert.equal(elements.get('unknown').hidden, false); // Lost state is not a verified failure.

status = {...status, source: 'fault'};
await poll();
assert.equal(elements.get('service').hidden, false);
assert.equal(elements.get('password').value, '');

globalThis.location.origin = 'http://example.invalid';
await import('./app.js?fallback');
assert.equal(elements.get('browser').hidden, false);
assert.equal(elements.get('credentials').hidden, true);
console.log('immediate Wi-Fi form, password reveal, save reconciliation and browser fallback passed');
