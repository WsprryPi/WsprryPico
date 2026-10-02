import assert from 'node:assert/strict';
import {slotDigest} from './crypto.js';

const device = '00112233445566778899aabbccddeeff';
const boot = '102132435465768798a9bacbdcedfe0f';
const slot = '2031425364758697a8b9cadbecfd0e1f';
const picoPublic = '3p7bfXt9wbTTW2HC7OQ1Nz-DQ8hbeGdNrfx-FG-IK08';
const elements = new Map();
for (const name of ['credentials', 'checking', 'accepted', 'unconfirmed', 'connected', 'saved', 'retry',
                    'interrupted', 'unknown', 'service', 'browser', 'notice', 'device', 'page-title', 'setup-intro',
                    'setup-footer', 'wifi-form', 'ssid', 'password', 'time-server',
                    'password-toggle', 'password-slash', 'submit', 'change-connected',
                    'change-saved', 'retry-button', 'interrupted-button', 'unknown-button']) {
  elements.set(name, {hidden: true, textContent: '', value: '', type: 'password', disabled: false,
    attributes: {}, setAttribute(key, value) { this.attributes[key] = value; },
    events: {}, classList: {toggle() {}}, addEventListener(event, handler) {
      this.events[event] = handler;
    }});
}
elements.get('credentials').hidden = false;
elements.get('time-server').value = 'time.example.org';
elements.get('submit').disabled = true;
globalThis.document = {getElementById: (name) => elements.get(name)};
let reloads = 0;
globalThis.location = {origin: 'http://192.168.4.1', reload() { reloads++; }};
const timers = [];
globalThis.setTimeout = (callback, delay) => { timers.push({callback, delay}); return timers.length; };
globalThis.clearTimeout = (id) => { timers[id - 1].cleared = true; };
let status = {source: 'unprovisioned', generation: 0, slot_state: 'none',
  join: 'idle', address_ready: false, request_id_digest: null};
let submitted, ack, starts = 0, dropStatus = false, holdStatus = false, releaseStatus;
let holdSubmit = false, releaseSubmit, failSubmit = false, failStart = false;
let busyStarts = 0;
let dropSubmitResponse = false;
let now = 1_800_000_000_000;
Date.now = () => now;
const timeHints = [];
let failNextTimeHint = false;
globalThis.fetch = async (url, options = {}) => {
  const path = new URL(url).pathname;
  if (path === '/local/v1/identity') return {ok: true, json: async () => ({device_id: device})};
  if (path === '/api/bootstrap/v1/status') {
    if (dropStatus) throw new Error('setup Wi-Fi disconnected');
    const snapshot = status;
    if (holdStatus) return new Promise((resolve) => {
      releaseStatus = () => resolve({ok: true, json: async () => snapshot});
    });
    return {ok: true, json: async () => snapshot};
  }
  if (path === '/api/bootstrap/v1/time' && !options.body)
    return {ok: true, json: async () => ({version: 1, challenge_ns: '1234567890'})};
  const body = JSON.parse(options.body);
  if (path === '/api/bootstrap/v1/time') {
    assert.equal(options.headers['X-WsprryPico-Bootstrap'], '1');
    assert.equal(body.device_id, device);
    assert.equal(body.challenge_ns, '1234567890');
    timeHints.push(body.utc_ms);
    if (failNextTimeHint) {
      failNextTimeHint = false;
      throw new Error('connection busy');
    }
    return {ok: true, json: async () => ({version: 1, state: 'accepted'})};
  }
  if (path === '/api/bootstrap/v1/start') {
    starts++;
    if (failStart) throw new Error('setup Wi-Fi disconnected');
    if (busyStarts > 0) {
      busyStarts--;
      return {ok: false, status: 409};
    }
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
    if (dropSubmitResponse) throw new Error('setup Wi-Fi disconnected');
    const response = {ok: true, json: async () => ({state: failSubmit ? 'failed' : 'checking', generation: 0,
      request_id_digest: slotDigest(body.request_id)})};
    if (holdSubmit) return new Promise((resolve) => { releaseSubmit = () => resolve(response); });
    return response;
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
assert.deepEqual(timeHints, [String(now)]); // No extra tap to seed the clock.
await poll();
assert.equal(timeHints.length, 1); // Not every status request.
now += 30000;
await poll();
assert.deepEqual(timeHints, [String(1_800_000_000_000), String(now)]);
failNextTimeHint = true;
now += 30000;
await poll();
assert.equal(timeHints.at(-1), String(now));
now += 4000;
await poll();
assert.equal(timeHints.length, 3);
now += 1000;
await poll();
assert.equal(timeHints.at(-1), String(now));
assert.equal(timeHints.length, 4); // Busy connection retries after five seconds.

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
assert.equal(elements.get('accepted').hidden, false);
assert.equal(elements.get('page-title').textContent, 'Wi-Fi settings accepted');
assert.equal(elements.get('setup-intro').hidden, true);
assert.equal(elements.get('setup-footer').hidden, true);
dropStatus = true;
await poll();
assert.equal(elements.get('accepted').hidden, false); // AP loss is not a failed POST.
assert.equal(elements.get('retry').hidden, true);
dropStatus = false;

status = {...status, source: 'network_only', generation: 1, slot_state: 'terminal',
  join: 'connected', address_ready: true,
  request_id_digest: slotDigest(submitted.request_id)};
await poll();
assert.equal(elements.get('connected').hidden, false);
assert.equal(elements.get('page-title').textContent, 'Wi-Fi connected');
await timers.findLast((item) => item.delay === 250).callback();
assert.equal(ack.request_id, submitted.request_id);
assert.equal(ack.ack_tag.length, 43);

elements.get('change-connected').events.click();
assert.equal(elements.get('credentials').hidden, false);
elements.get('ssid').value = 'NewNet';
elements.get('password').value = 'new-test-password';
holdStatus = true;
const stalePoll = poll();
await new Promise(setImmediate);
assert.ok(releaseStatus);
holdSubmit = true;
const secondSubmit = elements.get('wifi-form').events.submit({preventDefault() {}});
await new Promise(setImmediate);
assert.ok(releaseSubmit);
releaseStatus();
await stalePoll;
holdStatus = false;
await poll();
assert.equal(elements.get('retry').hidden, true); // Polling cannot clear a pending POST.
holdSubmit = false;
releaseSubmit();
await secondSubmit;
assert.equal(elements.get('accepted').hidden, false);
assert.equal(starts, 2);
status = {...status, generation: 2, slot_state: 'trial',
  request_id_digest: '0'.repeat(64),
  attempt_request_id_digest: slotDigest(submitted.request_id)};
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
assert.equal(elements.get('accepted').hidden, false); // Accepted POST survives lost AP state.

status = {...status, source: 'fault'};
await poll();
assert.equal(elements.get('service').hidden, false);
assert.equal(elements.get('password').value, '');

status = {...status, source: 'network_only', slot_state: 'none', generation: 3};
elements.get('change-saved').events.click();
elements.get('ssid').value = 'BadNet';
elements.get('password').value = 'bad-test-password';
failSubmit = true;
await elements.get('wifi-form').events.submit({preventDefault() {}});
assert.equal(elements.get('retry').hidden, false); // Explicit rejection is a known failure.
failSubmit = false;
elements.get('retry-button').events.click();
elements.get('ssid').value = 'LabNet';
elements.get('password').value = 'test-only-password';
dropSubmitResponse = true;
await elements.get('wifi-form').events.submit({preventDefault() {}});
assert.equal(elements.get('unconfirmed').hidden, false); // Response loss proves neither save nor failure.
dropSubmitResponse = false;
dropStatus = true;
await poll();
assert.equal(elements.get('unconfirmed').hidden, false);
dropStatus = false;
status = {...status, source: 'network_only', generation: 4, slot_state: 'terminal',
  join: 'connected', address_ready: true,
  request_id_digest: slotDigest(submitted.request_id)};
await poll();
assert.equal(elements.get('connected').hidden, false); // Exact readback resolves lost reply.

elements.get('change-connected').events.click();
elements.get('ssid').value = 'LabNet';
elements.get('password').value = 'test-only-password';
failStart = true;
await elements.get('wifi-form').events.submit({preventDefault() {}});
assert.equal(elements.get('interrupted').hidden, false); // No POST, so save is unknown.
assert.equal(elements.get('retry').hidden, true);
elements.get('interrupted-button').events.click();
assert.equal(reloads, 1); // Recover identity and generation before another save.

failStart = false;
busyStarts = 1;
elements.get('ssid').value = 'LabNet';
elements.get('password').value = 'correct-test-password';
const delayedStart = elements.get('wifi-form').events.submit({preventDefault() {}});
await new Promise(setImmediate);
assert.equal(elements.get('checking').hidden, false);
assert.match(elements.get('notice').textContent, /previous Wi-Fi attempt/);
await timers.findLast((item) => item.delay === 2000).callback();
await delayedStart;
assert.equal(elements.get('accepted').hidden, false); // A busy prior slot is retried without another Save.

// Ambiguous flash readback preserves the encrypted attempt until the exact
// committed journal is readable again after restart; it never sends another POST.
const startsBeforeReconcile = starts;
const submittedBeforeReconcile = submitted;
status = {...status, source: 'fault', generation: 0, slot_state: 'reconcile',
  request_id_digest: null, attempt_request_id_digest: slotDigest(submitted.request_id)};
await poll();
assert.equal(elements.get('unconfirmed').hidden, false);
assert.equal(elements.get('service').hidden, true);
assert.equal(elements.get('password').value, '');
assert.equal(starts, startsBeforeReconcile);
assert.equal(submitted, submittedBeforeReconcile);
status = {...status, source: 'network_only', generation: 5, slot_state: 'none',
  request_id_digest: slotDigest(submitted.request_id), attempt_request_id_digest: null};
await poll();
assert.equal(elements.get('connected').hidden, false);
assert.equal(starts, startsBeforeReconcile);
assert.equal(submitted, submittedBeforeReconcile);
elements.get('change-connected').events.click();
elements.get('ssid').value = 'ForeignResult';
elements.get('password').value = 'test-only-password';
await elements.get('wifi-form').events.submit({preventDefault() {}});

// A durable foreign result at the expected generation must never borrow
// our volatile attempt digest to announce a successful save.
status = {...status, generation: 6, slot_state: 'terminal',
  request_id_digest: '0'.repeat(64),
  attempt_request_id_digest: slotDigest(submitted.request_id)};
await poll();
assert.equal(elements.get('connected').hidden, true);
assert.equal(elements.get('unknown').hidden, false);
elements.get('change-connected').events.click();
elements.get('ssid').value = 'BadReplacement';
elements.get('password').value = 'test-only-password';
await elements.get('wifi-form').events.submit({preventDefault() {}});
status = {...status, generation: 6, slot_state: 'terminal',
  attempt_request_id_digest: slotDigest(submitted.request_id)};
await poll();
assert.equal(elements.get('retry').hidden, false); // Exact failed attempt on unchanged journal.

globalThis.location.origin = 'http://example.invalid';
await import('./app.js?fallback');
assert.equal(elements.get('browser').hidden, false);
assert.equal(elements.get('credentials').hidden, true);
console.log('Wi-Fi form, accepted POST, AP loss, stale poll, confirmed failure and fallback passed');
