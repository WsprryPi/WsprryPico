import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {sha256} from '@noble/hashes/sha2.js';
import {hkdf} from '@noble/hashes/hkdf.js';
import {chacha20poly1305} from '@noble/ciphers/chacha.js';
import {x25519} from '@noble/curves/ed25519.js';
Object.defineProperty(globalThis, "crypto", {value:webcrypto,configurable:true});
const ids = ['device','notice','provisioning','full','operation','consequences','phrase-label',
  'phrase','confirm-one','confirm-two','execute','actions','confirm','cancel','reset-form'];
const elements = new Map(ids.map((id) => [id,{disabled:false,hidden:false,checked:false,value:'',events:{},
  focus(){},addEventListener(name,fn){this.events[name]=fn;}}]));
globalThis.document = {getElementById:(id)=>elements.get(id)};
const device = '00112233445566778899aabbccddeeff', boot = '102132435465768798a9bacbdcedfe0f';
const peer = x25519.keygen(); let posts=0, lose=false, reboot=false, startRequest;
const commands=[];
const modulePath=process.env.RECOVERY_SHIPPED ? './recovery-bundle.js' : './recovery-app.js';
globalThis.fetch = async (url, options) => {
  const path=new URL(url).pathname;
  if(path.endsWith('/status')) return {ok:true,json:async()=>({device_id:device,boot_id:boot,pending:false})};
  posts++;
  if(path.endsWith('/start')) {
    startRequest=JSON.parse(options.body);
    return {ok:true,json:async()=>({device_id:device,boot_id:reboot?'00'.repeat(16):boot,
      slot_id:'2031425364758697a8b9cadbecfd0e1f',pico_public_key:Buffer.from(peer.publicKey).toString('base64url')})};
  }
  assert.equal(path,'/api/recovery/v1/submit');
  const body=JSON.parse(options.body);
  assert.deepEqual(Object.keys(body).sort(),['version','device_id','boot_id','slot_id','request_id','aead_nonce','ciphertext','tag'].sort());
  assert.equal(body.version,1);assert.equal(body.device_id,device);assert.equal(body.boot_id,boot);
  const aad=Buffer.concat([Buffer.from('WsprryPico/Recovery/1\0'),Buffer.from(device,'hex'),
    Buffer.from(boot,'hex'),Buffer.from(body.slot_id,'hex'),Buffer.from(startRequest.browser_public_key,'base64url'),
    Buffer.from(peer.publicKey),Buffer.from(startRequest.request_nonce,'hex'),Buffer.from(body.request_id,'hex')]);
  const shared=x25519.getSharedSecret(peer.secretKey,Buffer.from(startRequest.browser_public_key,'base64url'));
  const key=hkdf(sha256,shared,sha256(aad),Buffer.from('WsprryPico recovery AEAD v1'),32);
  commands.push(Buffer.from(chacha20poly1305(key,Buffer.from(body.aead_nonce,'base64url'),aad).decrypt(
    Buffer.concat([Buffer.from(body.ciphertext,'base64url'),Buffer.from(body.tag,'base64url')]))).toString());
  shared.fill(0);key.fill(0);
  if(lose) throw Error('lost response');
  return {ok:true,json:async()=>({state:'reset_pending'})};
};
await import(modulePath); await new Promise((resolve)=>setImmediate(resolve));
const $=(s)=>elements.get(s);
$('full').events.click();
assert.equal($('operation').textContent,'Confirm user wipe');
assert.match($('consequences').textContent,/installed firmware stays/);
assert.match($('consequences').textContent,/restarts first-time setup/);
assert.equal($('phrase-label').textContent,'Type erase to confirm the user wipe');
assert.equal($('execute').textContent,'Confirm user wipe');
$('cancel').events.click();assert.equal(posts,0);assert.equal($('confirm').hidden,true);
$('provisioning').events.click();
assert.equal($('operation').textContent,'Confirm provisioning reset');
assert.equal($('execute').textContent,'Confirm reset');
assert.match($('consequences').textContent,/preserved/);
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
lose=false;
await import(modulePath+'?success');await new Promise((resolve)=>setImmediate(resolve));
$('full').events.click();
$('phrase').value='erase';$('phrase').events.input();assert.equal($('execute').disabled,true);
$('confirm-one').checked=true;$('confirm-one').events.input();assert.equal($('execute').disabled,true);
$('confirm-two').checked=true;$('confirm-two').events.input();assert.equal($('execute').disabled,false);
$('phrase').value='erase ';$('phrase').events.input();assert.equal($('execute').disabled,true);
$('phrase').value='erase';$('phrase').events.input();assert.equal($('execute').disabled,false);
await $('reset-form').events.submit({preventDefault(){}});assert.equal(posts,5);
assert.match($('notice').textContent,/User wipe accepted/);
assert.match($('notice').textContent,/restart first-time setup, keeping the installed firmware/);
assert.match($('notice').textContent,/Reconnect to setup Wi-Fi and configure it again/);
assert.deepEqual(commands,['1:1:reset provisioning','1:1:erase']);assert.equal($('confirm').hidden,true);
await $('reset-form').events.submit({preventDefault(){}});assert.equal(posts,5);

// A lost User wipe reply must retain the uncertainty lock for every action.
lose=true;
await import(modulePath+'?lost-wipe');await new Promise((resolve)=>setImmediate(resolve));
$('full').events.click();
$('phrase').value='erase';$('phrase').events.input();
$('confirm-two').checked=true;$('confirm-two').events.input();
assert.equal($('execute').disabled,true,'second checkbox alone cannot authorize a wipe');
await $('reset-form').events.submit({preventDefault(){}});assert.equal(posts,5);
$('confirm-one').checked=true;$('confirm-one').events.input();
await $('reset-form').events.submit({preventDefault(){}});assert.equal(posts,7);
assert.deepEqual(commands,['1:1:reset provisioning','1:1:erase','1:1:erase']);
assert.match($('notice').textContent,/unknown.*Do not repeat the request/);
assert.equal($('execute').disabled,true);assert.equal($('cancel').disabled,true);
const uncertainHeading=$('operation').textContent;
$('cancel').events.click();$('provisioning').events.click();$('full').events.click();
assert.equal($('operation').textContent,uncertainHeading);
$('phrase').value='erase';$('phrase').events.input();
await $('reset-form').events.submit({preventDefault(){}});assert.equal(posts,7);
assert.equal($('execute').disabled,true,'editing the phrase cannot unlock an uncertain wipe');
console.log('Recovery confirmations, cancellation, exact wire commands, boot changes, and no destructive replay passed');
