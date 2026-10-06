import assert from 'node:assert/strict';

const device = '00112233445566778899aabbccddeeff';
const saved = {version: 1, device_id: device, boot_id: '1'.repeat(32),
  source: 'consumer', profile_source: 5, generation: '5',
  network: {ssid: 'Home Net', time_server: 'time.local'}};
let run = 0;
async function openPage(readback, editDuringRead = false) {
  const elements = new Map();
  for (const name of ['credentials', 'checking', 'accepted', 'unconfirmed', 'connected',
    'saved', 'retry', 'interrupted', 'unknown', 'service', 'browser', 'notice', 'device',
    'page-title', 'setup-intro', 'setup-footer', 'wifi-form', 'ssid', 'password',
    'time-server', 'password-toggle', 'password-slash', 'submit', 'change-connected',
    'change-saved', 'retry-button', 'interrupted-button', 'unknown-button']) {
    elements.set(name, {value: '', hidden: true, type: 'password', events: {},
      classList: {toggle() {}}, setAttribute() {},
      addEventListener(event, handler) { this.events[event] = handler; }});
  }
  elements.get('time-server').value = 'pool.ntp.org';
  globalThis.document = {getElementById: (name) => elements.get(name)};
  globalThis.location = {origin: 'http://192.168.4.1'};
  globalThis.setTimeout = () => 1;
  globalThis.clearTimeout = () => {};
  const writes = [];
  let release;
  globalThis.fetch = async (url, options = {}) => {
    const path = new URL(url).pathname;
    if (options.method === 'POST') writes.push(path);
    if (path === '/local/v1/identity')
      return {ok: true, json: async () => ({device_id: device})};
    if (path === '/api/owner/v1/public-status') {
      assert.equal(options.cache, 'no-store');
      if (editDuringRead) await new Promise((resolve) => { release = resolve; });
      if (readback instanceof Error) throw readback;
      return {ok: true, json: async () => readback};
    }
    if (path === '/api/bootstrap/v1/status')
      return {ok: true, json: async () => ({source: 'consumer', generation: 5})};
    if (path === '/api/bootstrap/v1/time')
      return {ok: true, json: async () => options.body ? {state: 'accepted'} : {challenge_ns: '1'}};
    throw new Error('unexpected request ' + path);
  };
  await import('./app.js?prefill=' + ++run);
  await new Promise(setImmediate);
  if (editDuringRead) {
    elements.get('ssid').value = 'Typed Net';
    elements.get('time-server').value = 'typed.example.org';
    elements.get('password').value = 'typed-password';
    elements.get('wifi-form').events.input();
    release();
    await new Promise(setImmediate);
  }
  assert.equal(elements.get('submit').disabled, false);
  assert.ok(writes.every((path) => path === '/api/bootstrap/v1/time'));
  return elements;
}

for (const source of ['consumer', 'network_only']) {
  const fields = await openPage({...saved, source, profile_source: source === 'consumer' ? 5 : 4});
  assert.equal(fields.get('ssid').value, 'Home Net');
  assert.equal(fields.get('time-server').value, 'time.local');
  assert.equal(fields.get('password').value, '');
}
for (const invalid of [
  {...saved, device_id: 'f'.repeat(32)}, {...saved, source: 'fault'},
  {...saved, network: null}, {...saved, generation: '0'},
  {...saved, profile_source: 3}, new Error('read unavailable')
]) {
  const fields = await openPage(invalid);
  assert.equal(fields.get('ssid').value, '');
  assert.equal(fields.get('time-server').value, 'pool.ntp.org');
}
const edited = await openPage(saved, true);
assert.equal(edited.get('ssid').value, 'Typed Net');
assert.equal(edited.get('time-server').value, 'typed.example.org');
assert.equal(edited.get('password').value, 'typed-password');
console.log('Saved network prefill, failed read and delayed user-edit protection passed');
