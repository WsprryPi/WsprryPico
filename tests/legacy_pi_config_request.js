// Exercise the byte-identical legacy Pi producer; never contact a real device.
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const crypto = require('node:crypto');
const context = JSON.parse(fs.readFileSync(0, 'utf8'));
const fixture = path.join(__dirname, 'fixtures/pi-8454e21-wtp-management.js');
const source = fs.readFileSync(fixture);
const provenance = JSON.parse(fs.readFileSync(fixture.replace(/js$/, 'json'), 'utf8'));
if (crypto.createHash('sha256').update(source).digest('hex') !== provenance.sha256)
  throw new Error('Legacy Pi source provenance mismatch');
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    value:'', checked:false, disabled:false, hidden:false, textContent:'', listeners:{},
    setAttribute() {}, addEventListener(event, callback) { this.listeners[event] = callback; }
  });
  return elements.get(id);
}
const writes = [];
const root = {
  document:{readyState:'complete',getElementById:element,querySelectorAll:()=>[]},
  WtpUi:{developmentControlsVisible:true,read:()=>({Transport:'network'})},
  AbortController,setTimeout,clearTimeout,
  fetch:async (url, options) => {
    if (options.method !== 'GET') writes.push({method:options.method,path:url,
      body:JSON.parse(options.body),revision:options.headers['If-Match']});
    return {ok:true,status:200,headers:{get:()=>context.etag},json:async()=>context.response};
  }
};
root.window = root;
vm.runInNewContext(source.toString('utf8'), root, {filename:fixture});
(async () => {
  root.WtpManagement.setAvailability(true);
  await element('wtp-remote-load').listeners.click();
  element('wtp-remote-callsign').value = 'K1ABC';
  await element('wtp-remote-save').listeners.click();
  if (writes.length !== 1) throw new Error('Expected one actual Pi Save request');
  process.stdout.write(JSON.stringify(writes[0]));
})().catch(error => { console.error(error.message); process.exitCode = 1; });
