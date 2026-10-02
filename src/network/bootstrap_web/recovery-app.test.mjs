import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {x25519} from '@noble/curves/ed25519.js';
Object.defineProperty(globalThis, "crypto", {value:webcrypto,configurable:true});
const ids = ['device','notice','provisioning','full','operation','consequences','phrase-label',
  'phrase','confirm-one','confirm-two','execute','actions','confirm','cancel','reset-form'];
const elements = new Map(ids.map((id) => [id,{disabled:false,hidden:false,checked:false,value:'',events:{},
  focus(){},addEventListener(name,fn){this.events[name]=fn;}}]));
globalThis.document = {getElementById:(id)=>elements.get(id)};
const device = '00112233445566778899aabbccddeeff', boot = '102132435465768798a9bacbdcedfe0f';
const peer = x25519.keygen(); let posts=0, lose=false, reboot=false;
globalThis.fetch = async (url, options) => {
  const path=new URL(url).pathname;
  if(path.endsWith('/status')) return {ok:true,json:async()=>({device_id:device,boot_id:boot,pending:false})};
  posts++;
  if(path.endsWith('/start')) return {ok:true,json:async()=>({device_id:device,boot_id:reboot?'00'.repeat(16):boot,
    slot_id:'2031425364758697a8b9cadbecfd0e1f',pico_public_key:Buffer.from(peer.publicKey).toString('base64url')})};
  if(lose) throw Error('lost response');
  return {ok:true,json:async()=>({state:'reset_pending'})};
};
await import('./recovery-app.js'); await new Promise((resolve)=>setImmediate(resolve));
const $=(s)=>elements.get(s);
$('provisioning').events.click();
$('phrase').value='reset provisioning'; $('phrase').events.input(); assert.equal($('execute').disabled,true);
$('confirm-one').checked=true;$('confirm-one').events.input();assert.equal($('execute').disabled,true);
$('confirm-two').checked=true;$('confirm-two').events.input();assert.equal($('execute').disabled,false);
$('phrase').value='erase';$('phrase').events.input();assert.equal($('execute').disabled,true);
$('phrase').value='reset provisioning';$('phrase').events.input();
reboot=true;await $('reset-form').events.submit({preventDefault(){}});assert.equal(posts,1);
assert.match($('notice').textContent,/restarted/); assert.equal($('cancel').disabled,false);
reboot=false;lose=true;await $('reset-form').events.submit({preventDefault(){}});assert.equal(posts,3);
assert.match($('notice').textContent,/unknown/);assert.equal($('execute').disabled,true);
await $('reset-form').events.submit({preventDefault(){}});$('full').events.click();assert.equal(posts,3);
console.log('Recovery browser confirmations, exact phrase, boot change and no destructive replay passed');
lose=false;
await import('./recovery-app.js?success');await new Promise((resolve)=>setImmediate(resolve));
$('full').events.click();$('confirm-one').checked=true;$('confirm-two').checked=true;
$('phrase').value='erase ';$('phrase').events.input();assert.equal($('execute').disabled,true);
$('phrase').value='erase';$('phrase').events.input();assert.equal($('execute').disabled,false);
await $('reset-form').events.submit({preventDefault(){}});assert.equal(posts,5);
assert.match($('notice').textContent,/accepted/);assert.equal($('confirm').hidden,true);
await $('reset-form').events.submit({preventDefault(){}});assert.equal(posts,5);
