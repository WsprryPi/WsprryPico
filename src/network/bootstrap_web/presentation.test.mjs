import assert from 'node:assert/strict';
import {titleFromDevice} from './presentation.js';
const device='1'.repeat(32);
globalThis.document={title:'Generic title'};
let metadata;
globalThis.fetch=async(url,options)=>{
  assert.equal(options.credentials,'omit');assert.equal(options.redirect,'error');
  return {ok:true,json:async()=>metadata};
};
for(const suffix of ['Wi-Fi setup','Station setup','Recovery']) {
  metadata={schema:'device-presentation/1',device_id:device,boot_id:'2'.repeat(32),hostname:'pico-a.local'};
  await titleFromDevice(suffix,device);assert.equal(document.title,'pico-a.local - '+suffix);
}
for(const hostname of ['<script>.local','K.local','x'.repeat(64)+'.local','other.example','A.local']) {
  document.title='Generic title';metadata.hostname=hostname;
  await titleFromDevice('Recovery',device);assert.equal(document.title,'Generic title');
}
metadata.hostname='pico-b.local';metadata.device_id='3'.repeat(32);
await titleFromDevice('Recovery',device);assert.equal(document.title,'Generic title');
console.log('Device-derived setup titles, wrong-device and malformed-name refusal passed');
