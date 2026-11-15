import assert from 'node:assert/strict';

const device = '00112233445566778899aabbccddeeff';
const saved = {version: 1, device_id: device, boot_id: '1'.repeat(32),
  source: 'consumer', profile_source: 5, generation: '5',
  network: {ssid: 'Home Net', time_server: 'time.local'}};
let run = 0;
async function openPage(readback, editDuringRead = false, nameMode = 'ready') {
  const elements = new Map();
  for (const name of ['credentials', 'checking', 'accepted', 'unconfirmed', 'connected',
    'saved', 'retry', 'interrupted', 'unknown', 'service', 'browser', 'notice', 'device',
    'hostname','hostname-help','hostname-read-status','hostname-error','ssid-error','password-error','time-server-error','page-title', 'setup-intro', 'setup-footer', 'wifi-form', 'ssid', 'password',
    'time-server', 'password-toggle', 'password-slash', 'submit', 'change-connected',
    'change-saved', 'retry-button', 'interrupted-button', 'unknown-button']) {
    elements.set(name, {id: name, value: '', hidden: true, type: 'password', events: {},
      classList: {toggle() {}}, focus() {}, setAttribute() {}, toggleAttribute() {},
      addEventListener(event, handler) { this.events[event] = handler; }});
  }
  elements.get('time-server').value = 'pool.ntp.org';

  for (const id of ['setup-link-panel','setup-url','setup-hostname','copy-setup-link',
    'setup-copy-status','setup-link-state','setup-link-help','setup-link-edit','setup-link-result','next-connection']) {
    elements.set(id, {value:'',textContent:'',hidden:true,events:{},
      addEventListener(event,fn) { this.events[event]=fn; },
      append(child) { child.parentElement=this; }, removeAttribute(name) { delete this[name]; }});
  }
  globalThis.document = {getElementById: (name) => elements.get(name)};
  globalThis.location = {origin: 'http://192.168.4.1'};
  globalThis.setTimeout = () => 1;
  globalThis.clearTimeout = () => {};
  const writes = [];
  let release, releaseName;
  let nameReads = 0;
  globalThis.fetch = async (url, options = {}) => {
    const path = new URL(url, 'http://192.168.4.1').pathname;
    if (options.method === 'POST') writes.push(path);
    if (path === '/api/presentation/v1') {
      ++nameReads;
      if (nameMode === 'unavailable' || nameMode === 'retry' && nameReads === 1) return {ok:false};
      if (nameMode === 'ssid-edit' || nameMode === 'name-edit') await new Promise(resolve => { releaseName = resolve; });
      return {ok:true,json:async()=>({schema:'device-presentation/1',device_id:nameMode === 'wrong-device' ? 'f'.repeat(32) : device,boot_id:'1'.repeat(32),hostname:nameMode === 'malformed' ? 'bad.example' : 'current-pico.local'})};
    }
    if (path === '/local/v1/identity')
      return {ok: true, json: async () => ({device_id: device})};
    if (path === '/api/owner/v1/public-status') {
      assert.equal(options.cache, 'no-store');
      if (editDuringRead) await new Promise((resolve) => { release = resolve; });
      if (readback instanceof Error) throw readback;
      return {ok: true, json: async () => readback};
    }
    if (path === '/api/bootstrap/v1/status')
      return {ok: true, json: async () => ({source: readback.source === 'network_only' ? 'network_only' : 'consumer', generation: 5})};
    if (path === '/api/bootstrap/v1/time')
      return {ok: true, json: async () => options.body ? {state: 'accepted'} : {challenge_ns: '1'}};
    throw new Error('unexpected request ' + path);
  };
  await import('./app.js?prefill=' + ++run);
  await new Promise(setImmediate);
  if (nameMode === 'ssid-edit' || nameMode === 'name-edit') {
    const id = nameMode === 'ssid-edit' ? 'ssid' : 'hostname';
    elements.get(id).value = id === 'ssid' ? 'Typed Net' : 'my-draft';
    elements.get('wifi-form').events.input({target:elements.get(id)});
    releaseName();
    await new Promise(setImmediate);
  }
  if (editDuringRead) {
    elements.get('ssid').value = 'Typed Net';
    elements.get('time-server').value = 'typed.example.org';
    elements.get('password').value = 'typed-password';
    elements.get('wifi-form').events.input({target:elements.get('ssid')});
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

assert.equal((await openPage(saved)).get('hostname').value,'current-pico');
assert.equal((await openPage(saved,false,'retry')).get('hostname').value,'current-pico');
assert.equal((await openPage(saved,false,'ssid-edit')).get('hostname').value,'current-pico');
assert.equal((await openPage(saved,false,'name-edit')).get('hostname').value,'my-draft');
const unavailable=await openPage(saved,false,'unavailable');
assert.equal(unavailable.get('hostname').value,'');
assert.match(unavailable.get('hostname-read-status').textContent,/unavailable/);
console.log('Actual current-name value, retry, unrelated-edit independence, and hostname-draft preservation passed');

const consumer = await openPage(saved);
assert.equal(consumer.get('hostname').disabled,true);
consumer.get('hostname').value='ignored-draft';
consumer.get('wifi-form').events.input({target:consumer.get('hostname')});
assert.equal(consumer.get('setup-url').value,'http://current-pico.local/');
const draft = await openPage({...saved,source:'network_only'},false,'name-edit');
assert.equal(draft.get('setup-url').value,'http://my-draft.local/');
for (const [label,expected] of [['PicoC','http://picoc.local/'],['','http://current-pico.local/'],
  ['x'.repeat(63),'http://'+'x'.repeat(63)+'.local/'],['bad.local',''],['-bad',''],['K','']]) {
  draft.get('hostname').value=label;
  draft.get('wifi-form').events.input({target:draft.get('hostname')});
  assert.equal(draft.get('setup-url').value,expected);
  assert.equal(draft.get('copy-setup-link').disabled,!expected);
}
assert.equal(unavailable.get('setup-url').value,'');
assert.equal(unavailable.get('copy-setup-link').disabled,true);
console.log('Setup link draft, consumer authority, invalid name, blank retention, and missing metadata passed');

for (const mode of ['wrong-device','malformed']) {
  const rejected=await openPage({...saved,source:'network_only'},false,mode);
  assert.equal(rejected.get('setup-url').value,'');
  assert.equal(rejected.get('copy-setup-link').disabled,true);
}
