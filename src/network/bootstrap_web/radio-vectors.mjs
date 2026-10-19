// Deterministic, synthetic interoperability vectors; no test reruns or devices.
import fs from 'node:fs';
import {x25519} from '@noble/curves/ed25519.js';
import {sha256} from '@noble/hashes/sha2.js';
import {chacha20poly1305} from '@noble/ciphers/chacha.js';
import {authenticate,begin,b64,header,hex,join,seal,text} from './radio-crypto.js';
const id={version:1,device_id:'11'.repeat(16),boot_id:'22'.repeat(16),generation:'139',authentication:'saved_wifi_passphrase'};
const privateKey=Uint8Array.from({length:32},(_,i)=>i+1);
const grant={version:1,...id,session_id:'33'.repeat(16),public_key:b64(x25519.getPublicKey(privateKey)),challenge:'44'.repeat(16),login_ms:30000};
const pending=begin(Uint8Array.from({length:32},(_,i)=>i+65),new Uint8Array(16).fill(0x55));
const state=authenticate(pending,grant,'test-only-password',id);
const request={method:'GET',path:'/api/v1/config',if_match:null,body:null};
const value={status:200,etag:'"revision"',body:{config:{enabled:false}}};
const nonce=new Uint8Array(12); nonce[11]=1;
const h=header(state.session,1n);
const response=join(h,chacha20poly1305(state.keys.subarray(32),nonce,join(state.digest,h)).encrypt(text(JSON.stringify(value))));
const vector={version:1,device_id:id.device_id,boot_id:id.boot_id,generation:id.generation,session_id:grant.session_id,challenge:grant.challenge,
 browser_nonce:pending.nonce,browser_public_key:pending.public_key,pico_public_key:grant.public_key,pico_private_key_hex:hex(privateKey),
 password:'test-only-password',transcript_sha256:hex(state.digest),login_hex:hex(state.finish),request_hex:hex(seal(state,1n,request)),
 request_plain:JSON.stringify(request),response_hex:hex(response),response_plain:JSON.stringify(value),
 request_key_hex:hex(state.keys.subarray(0,32)),large_request_sha256:hex(sha256(seal(state,2n,{pad:'x'.repeat(32714)})))};
fs.writeFileSync(new URL('../../../engineering/protocol/Consumer-Radio-v1-vectors.json',import.meta.url),JSON.stringify(vector,null,2)+'\n');
state.keys.fill(0);state.digest.fill(0);
