import assert from 'node:assert/strict';
import {slotDigest} from './crypto.js';

const device = '00112233445566778899aabbccddeeff';
const boot = '102132435465768798a9bacbdcedfe0f';
const slot = '2031425364758697a8b9cadbecfd0e1f';
const picoPublic = '3p7bfXt9wbTTW2HC7OQ1Nz-DQ8hbeGdNrfx-FG-IK08';
const elements = new Map();
for (const name of ['ready', 'tap', 'credentials', 'checking', 'connected', 'saved', 'retry',
                    'service', 'safari', 'notice', 'device', 'start', 'retry-button', 'wifi-form',
                    'ssid', 'password', 'submit']) {
  elements.set(name, {hidden: true, textContent: '', value: '', disabled: false,
    events: {}, classList: {toggle() {}}, addEventListener(event, handler) {
      this.events[event] = handler;
    }});
}
globalThis.document = {getElementById: (name) => elements.get(name)};
globalThis.location = {origin: 'http://192.168.4.1'};
const timers = [];
globalThis.setTimeout = (callback, delay) => { timers.push({callback, delay}); return timers.length; };
let status = {source: 'unprovisioned', generation: 0, slot_state: 'none',
  slot_id_digest: null, join: 'idle', address_ready: false, request_id_digest: null};
let submit, ack, starts = 0;
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
    submit = body;
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

await import('./app.js');
await new Promise(setImmediate);
assert.equal(elements.get('ready').hidden, false);
assert.equal(elements.get('credentials').hidden, true);
await elements.get('start').events.click();
assert.equal(starts, 1);
assert.equal(elements.get('tap').hidden, false);

status = {...status, slot_state: 'granted', slot_id_digest: slotDigest(slot)};
const poll = timers.find((item) => item.delay === 1000);
assert.ok(poll);
await poll.callback();
assert.equal(elements.get('credentials').hidden, false);

elements.get('ssid').value = 'LabNet';
elements.get('password').value = 'test-only-password';
await elements.get('wifi-form').events.submit({preventDefault() {}});
assert.ok(submit);
assert.equal(elements.get('password').value, '');
assert.equal(elements.get('checking').hidden, false);

status = {...status, source: 'network_only', generation: 1, slot_state: 'terminal',
  join: 'connected', address_ready: true,
  request_id_digest: slotDigest(submit.request_id)};
const nextPoll = timers.findLast((item) => item.delay === 1000);
await nextPoll.callback();
assert.equal(elements.get('connected').hidden, false);
const acknowledge = timers.find((item) => item.delay === 250);
assert.ok(acknowledge);
await acknowledge.callback();
assert.equal(ack.request_id, submit.request_id);
assert.equal(ack.ack_tag.length, 43);

status = {...status, join: 'disconnected', address_ready: false,
  request_id_digest: null};
await timers.findLast((item) => item.delay === 1000).callback();
assert.equal(elements.get('saved').hidden, false);
assert.equal(elements.get('connected').hidden, true);

status = {...status, source: 'fault'};
await timers.findLast((item) => item.delay === 1000).callback();
assert.equal(elements.get('service').hidden, false);
assert.equal(elements.get('ssid').value, '');

globalThis.location.origin = 'http://example.invalid';
await import('./app.js?fallback');
assert.equal(elements.get('safari').hidden, false);
assert.equal(elements.get('credentials').hidden, true);
console.log('bootstrap browser flow and fallback passed');
